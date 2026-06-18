from __future__ import annotations

import itertools
import socket
import struct
import threading
from dataclasses import dataclass, field
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.errors import MargreteProtocolError, MargreteRemoteError
from margrete_rpc.trace import NoopTracer, Tracer

MAX_FRAME_SIZE = 16 * 1024 * 1024


def encode_frame(envelope: messages_pb2.Envelope) -> bytes:
    payload = envelope.SerializeToString()
    if len(payload) > MAX_FRAME_SIZE:
        raise MargreteProtocolError(f"payload too large: {len(payload)} bytes")
    return struct.pack("<I", len(payload)) + payload


def decode_frame(frame: bytes) -> messages_pb2.Envelope:
    if len(frame) < 4:
        raise MargreteProtocolError("frame header is truncated")
    size = struct.unpack("<I", frame[:4])[0]
    if size > MAX_FRAME_SIZE:
        raise MargreteProtocolError(f"frame too large: {size} bytes")
    payload = frame[4:]
    if len(payload) != size:
        raise MargreteProtocolError("frame payload is truncated")
    envelope = messages_pb2.Envelope()
    envelope.ParseFromString(payload)
    return envelope


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise MargreteProtocolError("socket closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


@dataclass
class SocketRpcClient:
    endpoint: str
    timeout: float = 60.0
    tracer: Tracer = field(default_factory=NoopTracer)
    _sock: socket.socket | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        host, port_text = self.endpoint.rsplit(":", 1)
        self._host = host
        self._port = int(port_text)
        self._request_ids = itertools.count(1)

    def __enter__(self) -> SocketRpcClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        sock = self._sock
        self._sock = None
        if sock is not None:
            sock.close()

    def _connect_unlocked(self) -> socket.socket:
        if self._sock is None:
            sock = socket.create_connection((self._host, self._port), timeout=self.timeout)
            sock.settimeout(self.timeout)
            self._sock = sock
        return self._sock

    def request(self, envelope: messages_pb2.Envelope) -> messages_pb2.Envelope:
        span_name = next(
            (
                field_desc.name
                for field_desc, _ in envelope.ListFields()
                if field_desc.name != "request_id"
            ),
            "unknown",
        )
        request_id = next(self._request_ids)
        envelope.request_id = request_id
        with self.tracer.span(
            "margrete.rpc",
            attrs={
                "rpc.message": span_name,
                "rpc.request_id": request_id,
                "rpc.endpoint": self.endpoint,
            },
        ):
            with self._lock:
                try:
                    sock = self._connect_unlocked()
                    sock.sendall(encode_frame(envelope))
                    header = _recv_exact(sock, 4)
                    size = struct.unpack("<I", header)[0]
                    if size > MAX_FRAME_SIZE:
                        raise MargreteProtocolError(f"frame too large: {size} bytes")
                    response = messages_pb2.Envelope()
                    response.ParseFromString(_recv_exact(sock, size))
                    if response.request_id != request_id:
                        self._close_unlocked()
                        raise MargreteProtocolError(
                            f"response request_id {response.request_id} did not match {request_id}"
                        )
                except (OSError, MargreteProtocolError):
                    self._close_unlocked()
                    raise
                except Exception:
                    self._close_unlocked()
                    raise
            if response.HasField("error_response"):
                error = response.error_response
                raise MargreteRemoteError(error.code, error.message)
            return response
