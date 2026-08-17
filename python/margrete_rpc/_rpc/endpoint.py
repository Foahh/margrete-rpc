from __future__ import annotations

from margrete_rpc._rpc.pipe import PipeRpcClient
from margrete_rpc._rpc.transport import RpcTransport
from margrete_rpc.trace import Tracer


def create_transport(pipe_name: str, timeout: float, tracer: Tracer) -> RpcTransport:
    return PipeRpcClient(pipe_name, timeout, tracer=tracer)


__all__ = ["create_transport"]
