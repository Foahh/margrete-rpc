from __future__ import annotations

import itertools
import struct
import threading
from dataclasses import dataclass, field
from types import TracebackType
from typing import Protocol

from margrete_rpc._framing import MAX_FRAME_SIZE, encode_frame
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.errors import MargreteProtocolError, MargreteRemoteError, MargreteTimeoutError
from margrete_rpc.trace import NoopTracer, Tracer


class ByteStream(Protocol):
    def read_exact(self, size: int) -> bytes: ...

    def write_all(self, data: bytes) -> None: ...

    def close(self) -> None: ...


@dataclass
class FramedRpcClient:
    endpoint: str
    timeout: float = 60.0
    tracer: Tracer = field(default_factory=NoopTracer)
    _connection: ByteStream | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self._request_ids = itertools.count(1)

    def __enter__(self) -> FramedRpcClient:
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

    def _open_connection(self) -> ByteStream:
        raise NotImplementedError

    def _close_unlocked(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _connect_unlocked(self) -> ByteStream:
        if self._connection is None:
            self._connection = self._open_connection()
        return self._connection

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
                    connection = self._connect_unlocked()
                    connection.write_all(encode_frame(envelope))
                    header = connection.read_exact(4)
                    size = struct.unpack("<I", header)[0]
                    if size > MAX_FRAME_SIZE:
                        raise MargreteProtocolError(f"frame too large: {size} bytes")
                    response = messages_pb2.Envelope()
                    response.ParseFromString(connection.read_exact(size))
                    if response.request_id != request_id:
                        self._close_unlocked()
                        raise MargreteProtocolError(
                            f"response request_id {response.request_id} did not match {request_id}"
                        )
                except TimeoutError as exc:
                    self._close_unlocked()
                    raise MargreteTimeoutError(
                        f"timed out while waiting for {span_name} response from {self.endpoint}"
                    ) from exc
                except OSError as exc:
                    self._close_unlocked()
                    raise MargreteProtocolError(f"transport error: {exc}") from exc
                except MargreteProtocolError:
                    self._close_unlocked()
                    raise
                except Exception:
                    self._close_unlocked()
                    raise
            if response.HasField("error_response"):
                error = response.error_response
                raise MargreteRemoteError(error.code, error.message)
            return response


__all__ = ["ByteStream", "FramedRpcClient"]
