from __future__ import annotations

import itertools
import socket
import struct
from dataclasses import dataclass

from margrete_rpc._errors import MargreteProtocolError, MargreteRemoteError
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

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
    timeout: float = 5.0

    def __post_init__(self) -> None:
        host, port_text = self.endpoint.rsplit(":", 1)
        self._host = host
        self._port = int(port_text)
        self._request_ids = itertools.count(1)

    def request(self, envelope: messages_pb2.Envelope) -> messages_pb2.Envelope:
        request_id = next(self._request_ids)
        envelope.request_id = request_id
        with socket.create_connection((self._host, self._port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(encode_frame(envelope))
            header = _recv_exact(sock, 4)
            size = struct.unpack("<I", header)[0]
            if size > MAX_FRAME_SIZE:
                raise MargreteProtocolError(f"frame too large: {size} bytes")
            response = messages_pb2.Envelope()
            response.ParseFromString(_recv_exact(sock, size))
        if response.request_id != request_id:
            raise MargreteProtocolError(
                f"response request_id {response.request_id} did not match {request_id}"
            )
        if response.HasField("error_response"):
            error = response.error_response
            raise MargreteRemoteError(error.code, error.message)
        return response
