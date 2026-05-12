from __future__ import annotations

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient


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

    def current_tick(self) -> int:
        response = self._transport.request(
            messages_pb2.Envelope(get_current_tick_request=messages_pb2.GetCurrentTickRequest())
        )
        return response.get_current_tick_response.tick
