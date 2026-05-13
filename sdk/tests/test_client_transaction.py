import pytest

from margrete_rpc import L, Margrete, Tap
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


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
    assert apply_request.replace_all_notes is True
    assert len(apply_request.notes_upsert) == 1
    assert not apply_request.notes_upsert[0].HasField("id")


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
        assert tx.chart.raw_notes == []
        tx.chart.notes.append(Tap(480, 2, 1))
        tx.chart.raw_notes.append(L.tap(720, 4, 1))

    begin_request = transport.requests[0].begin_edit_request
    apply_request = transport.requests[1].apply_edit_request
    assert begin_request.scan is False
    assert apply_request.replace_all_notes is False
    assert [note.tick for note in apply_request.notes_upsert] == [480, 720]


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
            note = L.tap(480, 2, 1)
            note.id = 99
            tx.chart.raw_notes.append(note)

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


def test_scanned_replace_all_notes_strips_root_and_child_note_ids():
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

    with mg.open_edit_ll("ids") as tx:
        tx.chart.raw_notes[0].x = 3

    apply_request = transport.requests[1].apply_edit_request
    assert apply_request.replace_all_notes is True
    assert not apply_request.notes_upsert[0].HasField("id")
    assert not apply_request.notes_upsert[0].children[0].HasField("id")
