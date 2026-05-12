import pytest

from margrete_rpc import BpmEvent, Margrete, Note
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def test_open_edit_fetches_snapshot_and_sends_final_note_tree():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    event_scan_until_tick=4800,
                    event_scan_timeline_ids=[0, 2],
                    notes=[messages_pb2.Note(id=1, type=messages_pb2.NOTE_TYPE_TAP, x=1)],
                )
            ),
            messages_pb2.Envelope(apply_edit_patch_response=messages_pb2.ApplyEditPatchResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("move") as tx:
        assert tx.current_tick == 960
        tx.chart.notes[0].x = 5
        tx.chart.bpm_events.append(BpmEvent(tick=0, bpm=180.0))
        tx.chart.bpm_events.append(BpmEvent(tick=0, bpm=185.0))

    assert transport.requests[0].begin_edit_request.name == "move"
    request = transport.requests[1].apply_edit_patch_request
    assert request.name == "move"
    assert request.event_scan_until_tick == 4800
    assert list(request.event_scan_timeline_ids) == [0, 2]
    assert request.notes[0].id == 1
    assert request.notes[0].x == 5
    assert list(request.bpm_events) == [messages_pb2.BpmEvent(tick=0, bpm=185.0)]


def test_open_append_fetches_only_current_tick_and_sends_appended_notes():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_append_response=messages_pb2.BeginAppendResponse(current_tick=480)
            ),
            messages_pb2.Envelope(
                apply_append_patch_response=messages_pb2.ApplyAppendPatchResponse()
            ),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_append("append") as tx:
        assert tx.current_tick == 480
        assert tx.chart.notes == []
        tx.chart.notes.append(Note.tap(480, 2, 1))

    assert transport.requests[0].HasField("begin_append_request")
    request = transport.requests[1].apply_append_patch_request
    assert request.name == "append"
    assert request.notes[0].tick == 480


def test_open_append_rejects_existing_note_ids_before_commit_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_append_response=messages_pb2.BeginAppendResponse(current_tick=480)
            )
        ]
    )
    mg = Margrete(transport=transport)

    with pytest.raises(ValueError, match="append transactions cannot send existing note ids"):
        with mg.open_append("bad") as tx:
            tx.chart.notes.append(Note.tap(480, 2, 1, id=99))

    assert len(transport.requests) == 1


def test_transaction_exception_skips_apply_request():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_append_response=messages_pb2.BeginAppendResponse(current_tick=480)
            )
        ]
    )
    mg = Margrete(transport=transport)

    with pytest.raises(RuntimeError, match="boom"):
        with mg.open_append("append") as tx:
            tx.chart.notes.append(Note.tap(480, 2, 1))
            raise RuntimeError("boom")

    assert len(transport.requests) == 1
