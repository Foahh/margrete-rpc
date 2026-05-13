from __future__ import annotations

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient
from margrete_rpc.model import Chart, LLChart
from margrete_rpc.transaction import AppendTransaction, EditTransaction


class Margrete:
    def __init__(
        self, endpoint: str = "127.0.0.1:48731", *, timeout: float = 5.0, transport=None
    ) -> None:
        self._transport = transport if transport is not None else SocketRpcClient(endpoint, timeout)

    def ping(self) -> str:
        response = self._transport.request(
            messages_pb2.Envelope(ping_request=messages_pb2.PingRequest())
        )
        return response.ping_response.server_name

    def open_edit(self, name: str) -> EditTransaction:
        response = self._transport.request(
            messages_pb2.Envelope(begin_edit_request=messages_pb2.BeginEditRequest(name=name))
        )
        begin = response.begin_edit_response
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=Chart.from_begin_edit_response(begin),
            event_scan_until_tick=begin.event_scan_until_tick,
            event_scan_timeline_ids=list(begin.event_scan_timeline_ids),
        )

    def open_edit_ll(self, name: str) -> EditTransaction:
        response = self._transport.request(
            messages_pb2.Envelope(begin_edit_request=messages_pb2.BeginEditRequest(name=name))
        )
        begin = response.begin_edit_response
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=LLChart.from_begin_edit_response(begin),
            event_scan_until_tick=begin.event_scan_until_tick,
            event_scan_timeline_ids=list(begin.event_scan_timeline_ids),
        )

    def open_append(self, name: str) -> AppendTransaction:
        response = self._transport.request(
            messages_pb2.Envelope(begin_append_request=messages_pb2.BeginAppendRequest(name=name))
        )
        return AppendTransaction(
            name=name,
            transport=self._transport,
            current_tick=response.begin_append_response.current_tick,
            chart=Chart(),
        )
