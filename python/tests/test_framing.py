import struct

import pytest
from margrete_rpc._proto import messages_pb2
from margrete_rpc._rpc.framed import FramedRpcClient
from margrete_rpc._rpc.framing import decode_frame, encode_frame
from margrete_rpc._rpc.pipe import pipe_path
from margrete_rpc.discovery import pipe_name_for
from margrete_rpc.errors import MargreteProtocolError, MargreteRemoteError


def test_encode_decode_frame_round_trips_envelope():
    envelope = messages_pb2.Envelope(
        request_id=7,
        ping_request=messages_pb2.PingRequest(),
    )

    frame = encode_frame(envelope)
    decoded = decode_frame(frame)

    assert decoded.request_id == 7
    assert decoded.HasField("ping_request")


def test_decode_frame_rejects_truncated_payload():
    frame = struct.pack("<I", 12) + b"abc"

    with pytest.raises(MargreteProtocolError, match="truncated"):
        decode_frame(frame)


def test_pipe_path_prefixes_win32_name():
    assert pipe_path("margrete-0421") == "\\\\.\\pipe\\margrete-0421"
    assert pipe_path("\\\\.\\pipe\\margrete-0421") == "\\\\.\\pipe\\margrete-0421"


def test_pipe_name_for_accepts_digits_and_full_name():
    assert pipe_name_for("0421") == "margrete-0421"
    assert pipe_name_for("margrete-0421") == "margrete-0421"
    assert pipe_name_for(" 0007 ") == "margrete-0007"


def test_pipe_name_for_rejects_invalid_names():
    with pytest.raises(ValueError, match="0421 or margrete-0421"):
        pipe_name_for("421")
    with pytest.raises(ValueError, match="0421 or margrete-0421"):
        pipe_name_for("npipe://./pipe/margrete-0421")


class _ScriptedStream:
    def __init__(self, replies: list[bytes]) -> None:
        self._buf = bytearray()
        for reply in replies:
            self._buf.extend(reply)
        self.writes: list[bytes] = []
        self.closed = False

    def read_exact(self, size: int) -> bytes:
        if len(self._buf) < size:
            raise MargreteProtocolError("pipe closed before frame completed")
        data = bytes(self._buf[:size])
        del self._buf[:size]
        return data

    def write_all(self, data: bytes) -> None:
        self.writes.append(data)

    def close(self) -> None:
        self.closed = True


class _FakeClient(FramedRpcClient):
    def __init__(self, stream: _ScriptedStream) -> None:
        super().__init__(endpoint="margrete-0000")
        self._stream = stream

    def _open_connection(self) -> _ScriptedStream:
        return self._stream


def test_client_maps_error_response_to_exception():
    request_id = 1
    reply = encode_frame(
        messages_pb2.Envelope(
            request_id=request_id,
            error_response=messages_pb2.ErrorResponse(
                code=messages_pb2.ERROR_CODE_INVALID_ARGUMENT,
                message="bad request",
            ),
        )
    )
    stream = _ScriptedStream([reply])
    client = _FakeClient(stream)

    with pytest.raises(MargreteRemoteError) as exc:
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    assert exc.value.code == messages_pb2.ERROR_CODE_INVALID_ARGUMENT
    assert str(exc.value) == "bad request"


def test_request_id_mismatch_closes_connection():
    reply = encode_frame(
        messages_pb2.Envelope(
            request_id=99,
            ping_response=messages_pb2.PingResponse(),
        )
    )
    stream = _ScriptedStream([reply])
    client = _FakeClient(stream)

    with pytest.raises(MargreteProtocolError, match="did not match"):
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    assert stream.closed is True


def test_remote_error_response_keeps_connection_usable():
    error = encode_frame(
        messages_pb2.Envelope(
            request_id=1,
            error_response=messages_pb2.ErrorResponse(
                code=messages_pb2.ERROR_CODE_INVALID_ARGUMENT,
                message="bad request",
            ),
        )
    )
    ok = encode_frame(
        messages_pb2.Envelope(
            request_id=2,
            status_response=messages_pb2.StatusResponse(server_name="still-open"),
        )
    )
    stream = _ScriptedStream([error, ok])
    client = _FakeClient(stream)

    with pytest.raises(MargreteRemoteError):
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    response = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    assert response.status_response.server_name == "still-open"
    assert stream.closed is False


def test_generated_chart_transaction_messages_exist():
    note = messages_pb2.Note(
        id=7,
        type=messages_pb2.NOTE_TYPE_TAP,
        tick=960,
        x=4,
        width=1,
    )
    note.children.add(type=messages_pb2.NOTE_TYPE_AIR, tick=1000, x=4)

    begin_edit = messages_pb2.Envelope(begin_edit_request=messages_pb2.BeginEditRequest())
    apply_edit = messages_pb2.Envelope(
        apply_edit_request=messages_pb2.ApplyEditRequest(
            notes_upsert=[note],
            bpm_upsert=[messages_pb2.BpmEvent(tick=0, bpm=180.0)],
        )
    )

    assert begin_edit.HasField("begin_edit_request")
    assert apply_edit.HasField("apply_edit_request")
    assert (
        apply_edit.apply_edit_request.notes_upsert[0].children[0].type == messages_pb2.NOTE_TYPE_AIR
    )
    assert apply_edit.apply_edit_request.bpm_upsert[0].bpm == 180.0
