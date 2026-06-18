from __future__ import annotations

from margrete_rpc._pipe import PipeRpcClient
from margrete_rpc._socket import SocketRpcClient
from margrete_rpc._transport import RpcTransport
from margrete_rpc.trace import Tracer


def create_transport(endpoint: str, timeout: float, tracer: Tracer) -> RpcTransport:
    if endpoint.startswith("npipe://") or endpoint.startswith("\\\\.\\pipe\\"):
        return PipeRpcClient(endpoint, timeout, tracer=tracer)
    if endpoint.startswith("tcp://"):
        endpoint = endpoint.removeprefix("tcp://")
    return SocketRpcClient(endpoint, timeout, tracer=tracer)


__all__ = ["create_transport"]
