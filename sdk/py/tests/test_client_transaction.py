from margrete_rpc import Margrete
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Tap


class FakeTransport:
    def __init__(self):
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        if envelope.HasField("get_current_tick_request"):
            return messages_pb2.Envelope(
                request_id=envelope.request_id,
                get_current_tick_response=messages_pb2.GetCurrentTickResponse(tick=960),
            )
        if envelope.HasField("ping_request"):
            return messages_pb2.Envelope(
                request_id=envelope.request_id,
                ping_response=messages_pb2.PingResponse(server_name="Margrete RPC"),
            )
        if envelope.HasField("append_transaction_request"):
            return messages_pb2.Envelope(
                request_id=envelope.request_id,
                append_transaction_response=messages_pb2.AppendTransactionResponse(appended_items=1),
            )
        raise AssertionError("unexpected request")


def test_current_tick_uses_transport_response():
    transport = FakeTransport()
    mg = Margrete("127.0.0.1:48731", transport=transport)

    assert mg.current_tick() == 960


def test_transaction_sends_one_batch_on_success():
    transport = FakeTransport()
    mg = Margrete("127.0.0.1:48731", transport=transport)

    with mg.transaction("batch") as chart:
        chart.append(Tap(tick=100, lane=4))

    request = transport.requests[-1].append_transaction_request
    assert request.transaction_name == "batch"
    assert len(request.items) == 1


def test_transaction_exception_sends_nothing():
    transport = FakeTransport()
    mg = Margrete("127.0.0.1:48731", transport=transport)

    try:
        with mg.transaction("batch") as chart:
            chart.append(Tap(tick=100, lane=4))
            raise RuntimeError("script failed")
    except RuntimeError:
        pass

    assert not transport.requests


def test_insert_at_tick_offsets_objects():
    transport = FakeTransport()
    mg = Margrete("127.0.0.1:48731", transport=transport)

    with mg.transaction("insert") as chart:
        chart.insert_at_tick(1000, [Tap(tick=0, lane=3)])

    item = transport.requests[-1].append_transaction_request.items[0]
    assert item.note.tap.base.tick == 1000
