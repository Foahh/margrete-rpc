import pytest

from margrete_rpc import BpmEvent, L, Margrete, NoteType, Tap
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def test_open_edit_exposes_high_level_and_raw_notes_then_commits_both():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    event_scan_until_tick=4800,
                    event_scan_max_til=2,
                    notes=[
                        messages_pb2.Note(
                            id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=0, x=1, width=2
                        ),
                        messages_pb2.Note(id=2, type=messages_pb2.NOTE_TYPE_UNKNOWN, tick=120),
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_patch_response=messages_pb2.ApplyEditPatchResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("move") as tx:
        assert tx.current_tick == 960
        assert isinstance(tx.chart.notes[0], Tap)
        assert tx.chart.raw_notes[0].type is NoteType.UNKNOWN
        tx.chart.notes[0].x = 5
        tx.chart.raw_notes[0].x = 9
        tx.chart.events.bpm.append(BpmEvent(tick=0, bpm=185.0))

    request = transport.requests[1].apply_edit_patch_request
    assert request.notes[0].id == 1
    assert request.notes[0].x == 5
    assert request.notes[1].id == 2
    assert request.notes[1].x == 9
    assert list(request.bpm_events) == [messages_pb2.BpmEvent(tick=0, bpm=185.0)]
    assert request.event_scan_until_tick == 4800
    assert request.event_scan_max_til == 2


def test_open_append_commits_high_level_notes_and_raw_notes():
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
        tx.chart.notes.append(Tap(480, 2, 1))
        tx.chart.raw_notes.append(L.tap(720, 4, 1))

    request = transport.requests[1].apply_append_patch_request
    assert [note.tick for note in request.notes] == [480, 720]


def test_open_edit_ll_exposes_only_raw_notes():
    transport = FakeTransport(
        [
            messages_pb2.Envelope(
                begin_edit_response=messages_pb2.BeginEditResponse(
                    current_tick=960,
                    notes=[
                        messages_pb2.Note(
                            id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=0, x=1, width=2
                        )
                    ],
                )
            ),
            messages_pb2.Envelope(apply_edit_patch_response=messages_pb2.ApplyEditPatchResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit_ll("raw") as tx:
        assert not hasattr(tx.chart, "notes")
        tx.chart.raw_notes[0].x = 8

    request = transport.requests[1].apply_edit_patch_request
    assert request.notes[0].x == 8


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
            note = L.tap(480, 2, 1)
            note.id = 99
            tx.chart.raw_notes.append(note)

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
            tx.chart.notes.append(Tap(480, 2, 1))
            raise RuntimeError("boom")

    assert len(transport.requests) == 1
