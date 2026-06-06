import pytest

from margrete_rpc import Margrete
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Chart, N, Tap


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def test_open_edit_sends_scan_true_and_commits_apply_edit():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
                    event_scan_extra_tick=19200,
                    event_scan_til=[0, 2],
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

    with mg.open_edit("move") as tx:
        tx.chart.notes[0].x = 5

    begin_request = transport.requests[0].begin_edit_request
    apply_request = transport.requests[1].apply_edit_request
    assert begin_request.scan is True
    assert apply_request.name == "move"
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


def test_open_edit_sends_event_scan_note_til_only():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=0, scan=True, event_scan_note_til_only=True
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)
    with mg.open_edit("til-opt", event_scan_note_til_only=True):
        pass
    assert transport.requests[0].begin_edit_request.event_scan_note_til_only is True


def test_open_edit_scan_false_replaces_open_append_flow():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=480,
                    scan=False,
                    event_scan_extra_tick=19200,
                    event_scan_til=[0, 2],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("append", scan=False) as tx:
        assert tx.current_tick == 480
        assert tx.chart.notes == []
        assert tx.chart.nodes == []
        tx.chart.notes.append(Tap(480, 2, 1))
        tx.chart.nodes.append(N.tap(720, 4, 1))

    begin_request = transport.requests[0].begin_edit_request
    apply_request = transport.requests[1].apply_edit_request
    assert begin_request.scan is False
    assert apply_request.replace_all_notes is False
    assert [note.tick for note in apply_request.notes_upsert] == [480, 720]


def test_open_edit_has_no_separate_raw_method():
    mg = Margrete(transport=FakeTransport([]))

    assert not hasattr(mg, "open_edit_raw")


def test_open_append_is_removed():
    mg = Margrete(transport=FakeTransport([]))

    assert not hasattr(mg, "open_append")


def test_scan_false_rejects_existing_note_ids_before_commit_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(current_tick=480, scan=False)
            )
        ]
    )
    mg = Margrete(transport=transport)

    with pytest.raises(ValueError, match="scan=false transactions cannot send existing note ids"):
        with mg.open_edit("bad", scan=False) as tx:
            note = N.tap(480, 2, 1)
            note._id = 99
            tx.chart.nodes.append(note)

    assert len(transport.requests) == 1


def test_noop_scanned_edit_skips_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
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

    with mg.open_edit("noop"):
        pass

    assert len(transport.requests) == 1


def test_scanned_bpm_value_edit_with_same_tick_sends_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
                    bpm_events=[messages_pb2.BpmEvent(tick=0, bpm=120.0)],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("bpm") as tx:
        tx.chart.events.bpm[0].bpm = 180.0

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.bpm_upsert[0].bpm == 180.0


def test_scanned_timeline_speed_value_edit_with_same_key_sends_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
                    timeline_speed_events=[
                        messages_pb2.TimelineSpeedEvent(tick=0, timeline_id=2, speed=1.0)
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("til") as tx:
        tx.chart.events.til[0].speed = 1.5

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.til_upsert[0].speed == 1.5


def test_scanned_note_edit_uses_id_upsert_when_children_unchanged():

    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
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

    with mg.open_edit("ids", raw=True) as tx:
        assert isinstance(tx.chart, Chart)
        tx.chart.nodes[0].x = 3

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.notes_upsert[0].id == 1
    assert apply_request.notes_upsert[0].x == 3
    assert apply_request.note_ids_delete == []


def _hold_with_end_response() -> messages_pb2.Envelope:
    return messages_pb2.Envelope(
        begin_edit_response=messages_pb2.BeginEditResponse(
            current_tick=960,
            scan=True,
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


def test_scanned_note_edit_modifies_child_in_place_when_ids_preserved():
    transport = FakeTransport(
        [
            _hold_with_end_response(),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("child", raw=True) as tx:
        tx.chart.nodes[0].children[0].t = 500

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.note_ids_delete == []
    assert len(apply_request.notes_upsert) == 1
    assert apply_request.notes_upsert[0].id == 1
    assert apply_request.notes_upsert[0].children[0].id == 2
    assert apply_request.notes_upsert[0].children[0].tick == 500


def test_scanned_note_edit_rebuilds_tree_when_id_structure_changes():
    transport = FakeTransport(
        [
            _hold_with_end_response(),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("child", raw=True) as tx:
        tx.chart.nodes[0].children.insert(0, N.hold_end(240, 1, 2))

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is False
    assert apply_request.note_ids_delete == [1]
    assert len(apply_request.notes_upsert) == 1
    assert not apply_request.notes_upsert[0].HasField("id")
    assert len(apply_request.notes_upsert[0].children) == 2


def test_scanned_unchanged_events_send_no_deletes():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    scan=True,
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

    with mg.open_edit("note-only") as tx:
        tx.chart.notes[0].x = 5

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.bpm_ticks_delete == []
    assert apply_request.bpm_upsert == []
