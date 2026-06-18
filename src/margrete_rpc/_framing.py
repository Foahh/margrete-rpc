from __future__ import annotations

import struct

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.errors import MargreteProtocolError

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


__all__ = ["MAX_FRAME_SIZE", "decode_frame", "encode_frame"]
