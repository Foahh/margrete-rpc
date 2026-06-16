from __future__ import annotations

from typing import Protocol

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class RpcTransport(Protocol):
    """Low-level transport for sending and receiving protobuf :class:`Envelope` messages."""

    def request(self, envelope: messages_pb2.Envelope) -> messages_pb2.Envelope: ...


__all__ = ["RpcTransport"]
