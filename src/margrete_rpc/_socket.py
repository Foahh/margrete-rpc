from __future__ import annotations

import socket
from dataclasses import dataclass, field

from margrete_rpc._framed_client import ByteStream, FramedRpcClient
from margrete_rpc._framing import MAX_FRAME_SIZE, decode_frame, encode_frame
from margrete_rpc.errors import MargreteProtocolError
from margrete_rpc.trace import NoopTracer, Tracer


@dataclass
class SocketStream:
    sock: socket.socket

    def read_exact(self, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise MargreteProtocolError("socket closed before frame completed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def write_all(self, data: bytes) -> None:
        self.sock.sendall(data)

    def close(self) -> None:
        self.sock.close()


@dataclass
class SocketRpcClient(FramedRpcClient):
    endpoint: str
    timeout: float = 60.0
    tracer: Tracer = field(default_factory=NoopTracer)

    def __post_init__(self) -> None:
        super().__post_init__()
        host, port_text = self.endpoint.rsplit(":", 1)
        self._host = host
        self._port = int(port_text)

    def _open_connection(self) -> ByteStream:
        sock = socket.create_connection((self._host, self._port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        return SocketStream(sock)


__all__ = ["MAX_FRAME_SIZE", "SocketRpcClient", "decode_frame", "encode_frame"]
