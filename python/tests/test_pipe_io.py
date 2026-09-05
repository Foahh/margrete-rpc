import struct
import sys
import threading
import time
import uuid
from contextlib import contextmanager

import pytest
from margrete_rpc._proto import messages_pb2
from margrete_rpc._rpc.framing import encode_frame
from margrete_rpc._rpc.pipe import PipeRpcClient, pipe_path
from margrete_rpc.errors import MargreteTimeoutError

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="requires Windows named pipes")


@contextmanager
def pipe_server(handler):
    import win32file
    import win32pipe

    name = f"margrete-test-{uuid.uuid4()}"
    handle = win32pipe.CreateNamedPipe(
        pipe_path(name),
        win32pipe.PIPE_ACCESS_DUPLEX,
        win32pipe.PIPE_TYPE_BYTE,
        1,
        4096,
        4096,
        0,
        None,
    )
    release = threading.Event()
    errors = []

    def serve():
        try:
            win32pipe.ConnectNamedPipe(handle, None)
            handler(handle)
            release.wait(5)
        except Exception as exc:
            errors.append(exc)
        finally:
            win32file.CloseHandle(handle)

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    try:
        yield name
    finally:
        release.set()
        worker.join(2)
        assert not worker.is_alive()
        assert not errors


@pytest.mark.parametrize("partial_reply", [b"", b"\x10", struct.pack("<I", 16) + b"x"])
def test_pipe_request_times_out_on_incomplete_response(partial_reply):
    import win32file

    def respond(handle):
        win32file.ReadFile(handle, 4096)
        if partial_reply:
            win32file.WriteFile(handle, partial_reply)

    with pipe_server(respond) as name, PipeRpcClient(name, timeout=0.1) as client:
        started = time.monotonic()
        with pytest.raises(MargreteTimeoutError, match="timed out"):
            client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))
        assert time.monotonic() - started < 2
        assert client._connection is None


def test_pipe_write_times_out_when_server_does_not_read():
    with pipe_server(lambda handle: None) as name, PipeRpcClient(name, timeout=0.1) as client:
        request = messages_pb2.Envelope(
            apply_edit_request=messages_pb2.ApplyEditRequest(note_ids_delete=[1] * 100_000)
        )
        started = time.monotonic()
        with pytest.raises(MargreteTimeoutError, match="timed out"):
            client.request(request)
        assert time.monotonic() - started < 2
        assert client._connection is None


def test_pipe_connection_handles_multiple_fragmented_responses():
    import win32file

    def respond(handle):
        for request_id in (1, 2):
            win32file.ReadFile(handle, 4096)
            reply = encode_frame(
                messages_pb2.Envelope(
                    request_id=request_id, ping_response=messages_pb2.PingResponse()
                )
            )
            for byte in reply:
                win32file.WriteFile(handle, bytes([byte]))

    with pipe_server(respond) as name, PipeRpcClient(name, timeout=1) as client:
        for _ in range(2):
            response = client.request(
                messages_pb2.Envelope(ping_request=messages_pb2.PingRequest())
            )
            assert response.HasField("ping_response")
