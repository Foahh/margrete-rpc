import pytest

from margrete_rpc import Margrete
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Chart
from margrete_rpc.chart.notes import R, Tap


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def test_open_edit_sends_snapshot_true_and_commits_apply_edit():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    event_scan_lookahead_ticks=19200,
                    event_scan_til_ids=[0, 2],
                    notes=[
                        messages_pb2.Note(
                            id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=0, x=1, width=2
                        )
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit() as tx:
        tx.chart.notes[0].x = 5

    begin_request = transport.requests[0].begin_edit_request
    apply_request = transport.requests[1].apply_edit_request
    assert begin_request.snapshot is True
    assert apply_request.replace_all_notes is False
    assert len(apply_request.notes_upsert) == 1
    assert apply_request.notes_upsert[0].id == 1
    assert apply_request.notes_upsert[0].x == 5
    assert apply_request.bpm_ticks_delete == []


def test_ping_sends_request():
    transport = FakeTransport([messages_pb2.Envelope(ping_response=messages_pb2.PingResponse())])
    mg = Margrete(transport=transport)

    assert mg.ping() is None
    assert transport.requests[0].HasField("ping_request")


def test_undo_sends_request_and_returns_success():
    transport = FakeTransport(
        [messages_pb2.Envelope(undo_response=messages_pb2.UndoResponse(success=True))]
    )
    mg = Margrete(transport=transport)

    assert mg.undo() is True
    assert transport.requests[0].HasField("undo_request")


def test_redo_sends_request_and_returns_success():
    transport = FakeTransport(
        [messages_pb2.Envelope(redo_response=messages_pb2.RedoResponse(success=False))]
    )
    mg = Margrete(transport=transport)

    assert mg.redo() is False
    assert transport.requests[0].HasField("redo_request")


def test_current_tick_sends_request_and_returns_tick():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                current_tick_response=messages_pb2.CurrentTickResponse(current_tick=960)
            )
        ]
    )
    mg = Margrete(transport=transport)

    assert mg.current_tick() == 960
    assert transport.requests[0].HasField("current_tick_request")


def test_open_edit_absent_event_scan_til_ids_means_note_til_mode():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(current_tick=0, snapshot=True)
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)
    with mg.open_edit():
        pass
    assert not transport.requests[0].begin_edit_request.HasField("event_scan_til_ids")


def test_open_edit_explicit_event_scan_til_ids_sets_wrapper():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(current_tick=0, snapshot=True)
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)
    with mg.open_edit(event_scan_til_ids=[1, 2]):
        pass
    req = transport.requests[0].begin_edit_request
    assert req.HasField("event_scan_til_ids")
    assert list(req.event_scan_til_ids.ids) == [1, 2]


def test_open_edit_empty_event_scan_til_ids_sets_wrapper():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(current_tick=0, snapshot=True)
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)
    with mg.open_edit(event_scan_til_ids=[]):
        pass
    req = transport.requests[0].begin_edit_request
    assert req.HasField("event_scan_til_ids")
    assert list(req.event_scan_til_ids.ids) == []


def test_open_edit_snapshot_false_replaces_open_append_flow():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=480,
                    snapshot=False,
                    event_scan_lookahead_ticks=19200,
                    event_scan_til_ids=[0, 2],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit(snapshot=False) as tx:
        assert tx.current_tick == 480
        assert tx.chart.notes == []
        tx.chart.notes.append(Tap(t=480, x=2, w=1))
        tx.chart.notes.append(R.tap(t=720, x=4, w=1))

    begin_request = transport.requests[0].begin_edit_request
    apply_request = transport.requests[1].apply_edit_request
    assert begin_request.snapshot is False
    assert apply_request.replace_all_notes is False
    assert [note.tick for note in apply_request.notes_upsert] == [480, 720]


def test_open_edit_has_no_separate_raw_notes_method():
    mg = Margrete(transport=FakeTransport([]))

    assert not hasattr(mg, "open_edit_raw_notes")


def test_open_append_is_removed():
    mg = Margrete(transport=FakeTransport([]))

    assert not hasattr(mg, "open_append")


def test_snapshot_false_rejects_existing_note_ids_before_commit_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(current_tick=480, snapshot=False)
            )
        ]
    )
    mg = Margrete(transport=transport)

    with pytest.raises(ValueError, match="snapshot=false transactions cannot send existing note ids"):
        with mg.open_edit(snapshot=False) as tx:
            note = R.tap(t=480, x=2, w=1)
            note._id = 99
            tx.chart.notes.append(note)

    assert len(transport.requests) == 1


def test_noop_snapshot_edit_skips_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    notes=[
                        messages_pb2.Note(
                            id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=0, x=0, width=1
                        )
                    ],
                )
            )
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit():
        pass

    assert len(transport.requests) == 1


def test_snapshot_bpm_value_edit_with_same_tick_sends_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    bpm_events=[messages_pb2.BpmEvent(tick=0, bpm=120.0)],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit() as tx:
        tx.chart.events.bpm[0].bpm = 180.0

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.bpm_upsert[0].bpm == 180.0


def test_snapshot_timeline_speed_value_edit_with_same_key_sends_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    timeline_speed_events=[
                        messages_pb2.TimelineSpeedEvent(tick=0, timeline_id=2, speed=1.0)
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit() as tx:
        tx.chart.events.til[0].speed = 1.5

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.til_upsert[0].speed == 1.5


def test_snapshot_note_edit_uses_id_upsert_when_children_unchanged():

    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    notes=[
                        messages_pb2.Note(
                            id=1,
                            type=messages_pb2.NOTE_TYPE_HOLD,
                            tick=0,
                            x=1,
                            width=2,
                            children=[
                                messages_pb2.Note(
                                    id=2,
                                    type=messages_pb2.NOTE_TYPE_HOLD,
                                    tick=480,
                                    x=1,
                                    width=2,
                                )
                            ],
                        )
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit(raw_notes=True) as tx:
        assert isinstance(tx.chart, Chart)
        tx.chart.notes[0].x = 3

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.notes_upsert[0].id == 1
    assert apply_request.notes_upsert[0].x == 3
    assert apply_request.note_ids_delete == []


def _hold_with_end_response() -> messages_pb2.Envelope:
    return messages_pb2.Envelope(
        begin_edit_response=messages_pb2.BeginEditResponse(
            current_tick=960,
            snapshot=True,
            notes=[
                messages_pb2.Note(
                    id=1,
                    type=messages_pb2.NOTE_TYPE_HOLD,
                    tick=0,
                    x=1,
                    width=2,
                    children=[
                        messages_pb2.Note(
                            id=2,
                            type=messages_pb2.NOTE_TYPE_HOLD,
                            tick=480,
                            x=1,
                            width=2,
                        )
                    ],
                )
            ],
        )
    )


def test_snapshot_note_edit_modifies_child_in_place_when_ids_preserved():
    transport = FakeTransport(
        [
            _hold_with_end_response(),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit(raw_notes=True) as tx:
        tx.chart.notes[0].children[0].t = 500

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.note_ids_delete == []
    assert len(apply_request.notes_upsert) == 1
    assert apply_request.notes_upsert[0].id == 1
    assert apply_request.notes_upsert[0].children[0].id == 2
    assert apply_request.notes_upsert[0].children[0].tick == 500


def test_snapshot_note_edit_rebuilds_tree_when_id_structure_changes():
    transport = FakeTransport(
        [
            _hold_with_end_response(),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit(raw_notes=True) as tx:
        tx.chart.notes[0].children.insert(0, R.hold_end(t=240, x=1, w=2))

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.note_ids_delete == [1]
    assert len(apply_request.notes_upsert) == 1
    assert not apply_request.notes_upsert[0].HasField("id")
    assert len(apply_request.notes_upsert[0].children) == 2


def test_snapshot_unchanged_events_send_no_deletes():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    snapshot=True,
                    notes=[
                        messages_pb2.Note(
                            id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=0, x=0, width=1
                        )
                    ],
                    bpm_events=[messages_pb2.BpmEvent(tick=0, bpm=120.0)],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit() as tx:
        tx.chart.notes[0].x = 5

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.bpm_ticks_delete == []
    assert apply_request.bpm_upsert == []
