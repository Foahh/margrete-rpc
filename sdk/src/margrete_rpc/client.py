from __future__ import annotations

from dataclasses import dataclass

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient
from margrete_rpc.discovery import resolve_endpoint
from margrete_rpc.chart import Chart, MgChart
from margrete_rpc.trace import NoopTracer, Tracer
from margrete_rpc.transaction import EditTransaction


@dataclass(frozen=True)
class ServerStatus:
    server_name: str
    server_version: str
    server_build_time: str
    instance_id: str
    uptime: int
    pid: int
    log_path: str
    config_path: str


class Margrete:
    def __init__(
        self,
        endpoint: str | None = None,
        *,
        instance_id: str | None = None,
        timeout: float = 60.0,
        transport=None,
        tracer: Tracer | None = None,
    ) -> None:
        self._tracer = tracer if tracer is not None else NoopTracer()
        if transport is not None:
            if endpoint is not None or instance_id is not None:
                raise ValueError("endpoint and instance_id cannot be used with transport")
            self._transport = transport
        else:
            if endpoint is not None and instance_id is not None:
                raise ValueError("pass endpoint or instance_id, not both")
            if endpoint is None:
                endpoint = resolve_endpoint(instance_id, timeout=min(timeout, 1.0))
            self._transport = SocketRpcClient(endpoint, timeout, tracer=self._tracer)

    def ping(self) -> None:
        with self._tracer.span("margrete.client.ping"):
            self._transport.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    def status(self) -> ServerStatus:
        with self._tracer.span("margrete.client.status"):
            response = self._transport.request(
                messages_pb2.Envelope(status_request=messages_pb2.StatusRequest())
            )
        status = response.status_response
        return ServerStatus(
            server_name=status.server_name,
            server_version=status.server_version,
            server_build_time=status.server_build_time,
            instance_id=status.instance_id,
            uptime=status.uptime,
            pid=status.pid,
            log_path=status.log_path,
            config_path=status.config_path,
        )

    def undo(self) -> bool:
        with self._tracer.span("margrete.client.undo"):
            response = self._transport.request(
                messages_pb2.Envelope(undo_request=messages_pb2.UndoRequest())
            )
        return response.undo_response.success

    def redo(self) -> bool:
        with self._tracer.span("margrete.client.redo"):
            response = self._transport.request(
                messages_pb2.Envelope(redo_request=messages_pb2.RedoRequest())
            )
        return response.redo_response.success

    def current_tick(self) -> int:
        with self._tracer.span("margrete.client.current_tick"):
            response = self._transport.request(
                messages_pb2.Envelope(current_tick_request=messages_pb2.CurrentTickRequest())
            )
        return response.current_tick_response.current_tick

    def open_edit(
        self,
        name: str,
        *,
        event_scan_extra_tick: int | None = None,
        event_scan_til: list[int] | None = None,
        event_scan_note_til_only: bool = False,
        scan: bool = True,
        raw: bool = False,
        replace_all: bool = False,
    ) -> EditTransaction:
        tx_type = "edit_raw" if raw else "edit"
        with self._tracer.span("margrete.tx.begin", attrs={"tx.type": tx_type, "tx.name": name}):
            req = messages_pb2.BeginEditRequest(
                name=name, scan=scan, event_scan_note_til_only=event_scan_note_til_only
            )
            if event_scan_extra_tick is not None:
                req.event_scan_extra_tick = event_scan_extra_tick
            if event_scan_til is not None:
                req.event_scan_til.extend(event_scan_til)
            response = self._transport.request(messages_pb2.Envelope(begin_edit_request=req))
        begin = response.begin_edit_response
        chart = (
            MgChart.from_begin_edit_response(begin)
            if raw
            else Chart.from_begin_edit_response(begin)
        )
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=chart,
            scan=begin.scan,
            tracer=self._tracer,
            tx_type=tx_type,
            replace_all_notes=replace_all,
        )
