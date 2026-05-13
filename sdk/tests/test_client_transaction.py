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
