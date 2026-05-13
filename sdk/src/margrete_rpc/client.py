from __future__ import annotations

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient
from margrete_rpc.model import Chart, LLChart
from margrete_rpc.trace import NoopTracer, Tracer
from margrete_rpc.transaction import EditTransaction


class Margrete:
    def __init__(
        self,
        endpoint: str = "127.0.0.1:48731",
        *,
        timeout: float = 60.0,
        transport=None,
        tracer: Tracer | None = None,
    ) -> None:
        self._tracer = tracer if tracer is not None else NoopTracer()
        if transport is not None:
            self._transport = transport
        else:
            self._transport = SocketRpcClient(endpoint, timeout, tracer=self._tracer)

    def ping(self) -> str:
        with self._tracer.span("margrete.client.ping"):
            response = self._transport.request(
                messages_pb2.Envelope(ping_request=messages_pb2.PingRequest())
            )
        return response.ping_response.server_name

    def open_edit(
        self,
        name: str,
        *,
        event_scan_extra_tick: int | None = None,
        event_scan_til: list[int] | None = None,
        event_scan_note_til_only: bool = False,
        scan: bool = True,
    ) -> EditTransaction:
        with self._tracer.span("margrete.tx.begin", attrs={"tx.type": "edit", "tx.name": name}):
            req = messages_pb2.BeginEditRequest(
                name=name, scan=scan, event_scan_note_til_only=event_scan_note_til_only
            )
            if event_scan_extra_tick is not None:
                req.event_scan_extra_tick = event_scan_extra_tick
            if event_scan_til is not None:
                req.event_scan_til.extend(event_scan_til)
            response = self._transport.request(messages_pb2.Envelope(begin_edit_request=req))
        begin = response.begin_edit_response
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=Chart.from_begin_edit_response(begin),
            scan=begin.scan,
            tracer=self._tracer,
            tx_type="edit",
        )

    def open_edit_ll(
        self,
        name: str,
        *,
        event_scan_extra_tick: int | None = None,
        event_scan_til: list[int] | None = None,
        event_scan_note_til_only: bool = False,
        scan: bool = True,
    ) -> EditTransaction:
        with self._tracer.span("margrete.tx.begin", attrs={"tx.type": "edit_ll", "tx.name": name}):
            req = messages_pb2.BeginEditRequest(
                name=name, scan=scan, event_scan_note_til_only=event_scan_note_til_only
            )
            if event_scan_extra_tick is not None:
                req.event_scan_extra_tick = event_scan_extra_tick
            if event_scan_til is not None:
                req.event_scan_til.extend(event_scan_til)
            response = self._transport.request(messages_pb2.Envelope(begin_edit_request=req))
        begin = response.begin_edit_response
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=LLChart.from_begin_edit_response(begin),
            scan=begin.scan,
            tracer=self._tracer,
            tx_type="edit_ll",
        )
