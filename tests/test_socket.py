import socket
import struct
import threading
import time
from collections.abc import Callable

import pytest

from margrete_rpc._pipe import display_pipe_endpoint, normalize_pipe_endpoint
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient, decode_frame, encode_frame
from margrete_rpc.errors import MargreteProtocolError, MargreteRemoteError, MargreteTimeoutError


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = conn.recv(remaining)
        if not chunk:
            raise ConnectionError("socket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _recv_envelope(conn: socket.socket) -> messages_pb2.Envelope:
    header = _recv_exact(conn, 4)
    size = struct.unpack("<I", header)[0]
    payload = _recv_exact(conn, size)
    envelope = messages_pb2.Envelope()
    envelope.ParseFromString(payload)
    return envelope


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


def test_pipe_endpoint_helpers_round_trip_windows_pipe_path():
    path = "\\\\.\\pipe\\margrete-rpc-test"

    endpoint = display_pipe_endpoint(path)

    assert endpoint == "npipe://./pipe/margrete-rpc-test"
    assert normalize_pipe_endpoint(endpoint) == path


def test_client_maps_error_response_to_exception():
    port_holder: list[int] = []

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            conn, _ = srv.accept()
            with conn:
                header = conn.recv(4)
                size = struct.unpack("<I", header)[0]
                payload = conn.recv(size)
                request = messages_pb2.Envelope()
                request.ParseFromString(payload)
                response = messages_pb2.Envelope(
                    request_id=request.request_id,
                    error_response=messages_pb2.ErrorResponse(
                        code=messages_pb2.ERROR_CODE_INVALID_ARGUMENT,
                        message="bad request",
                    ),
                )
                conn.sendall(encode_frame(response))

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    while not port_holder:
        pass

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)

    with pytest.raises(MargreteRemoteError) as exc:
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    assert exc.value.code == messages_pb2.ERROR_CODE_INVALID_ARGUMENT
    assert str(exc.value) == "bad request"


def test_client_reuses_connection_for_multiple_requests():
    port_holder: list[int] = []
    ready = threading.Event()
    accepted_connections = 0

    def response_for(request: messages_pb2.Envelope) -> messages_pb2.Envelope:
        if request.HasField("ping_request"):
            return messages_pb2.Envelope(
                request_id=request.request_id,
                ping_response=messages_pb2.PingResponse(),
            )
        return messages_pb2.Envelope(
            request_id=request.request_id,
            status_response=messages_pb2.StatusResponse(server_name="test"),
        )

    def server(handler: Callable[[messages_pb2.Envelope], messages_pb2.Envelope]):
        nonlocal accepted_connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()
            conn, _ = srv.accept()
            accepted_connections += 1
            with conn:
                for _ in range(2):
                    request = _recv_envelope(conn)
                    conn.sendall(encode_frame(handler(request)))

    thread = threading.Thread(target=server, args=(response_for,), daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)
    ping = client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))
    status = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    client.close()
    thread.join(timeout=2.0)

    assert ping.HasField("ping_response")
    assert status.status_response.server_name == "test"
    assert accepted_connections == 1


def test_client_reconnects_after_server_closes_cached_connection():
    port_holder: list[int] = []
    ready = threading.Event()

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()

            conn, _ = srv.accept()
            with conn:
                request = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=request.request_id,
                            ping_response=messages_pb2.PingResponse(),
                        )
                    )
                )

            conn, _ = srv.accept()
            with conn:
                request = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=request.request_id,
                            status_response=messages_pb2.StatusResponse(server_name="reconnected"),
                        )
                    )
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)
    first = client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    with pytest.raises(MargreteProtocolError):
        client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))

    second = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    client.close()
    thread.join(timeout=2.0)

    assert first.HasField("ping_response")
    assert second.status_response.server_name == "reconnected"


def test_client_serializes_concurrent_requests_on_one_connection():
    port_holder: list[int] = []
    ready = threading.Event()
    start = threading.Barrier(3)
    second_arrived_before_first_response = False

    def server():
        nonlocal second_arrived_before_first_response
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()

            conn, _ = srv.accept()
            with conn:
                first = _recv_envelope(conn)
                conn.settimeout(0.2)
                try:
                    _recv_envelope(conn)
                    second_arrived_before_first_response = True
                except TimeoutError:
                    pass
                finally:
                    conn.settimeout(None)

                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=first.request_id,
                            ping_response=messages_pb2.PingResponse(),
                        )
                    )
                )

                second = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=second.request_id,
                            status_response=messages_pb2.StatusResponse(server_name="serialized"),
                        )
                    )
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)
    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)
    responses: list[messages_pb2.Envelope] = []
    errors: list[BaseException] = []
    responses_lock = threading.Lock()

    def call(envelope: messages_pb2.Envelope) -> None:
        try:
            start.wait(timeout=2.0)
            response = client.request(envelope)
        except BaseException as exc:
            errors.append(exc)
        else:
            with responses_lock:
                responses.append(response)

    t1 = threading.Thread(
        target=call,
        args=(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()),),
    )
    t2 = threading.Thread(
        target=call,
        args=(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()),),
    )
    t1.start()
    t2.start()
    start.wait(timeout=2.0)
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)
    client.close()
    thread.join(timeout=2.0)

    assert errors == []
    assert len(responses) == 2
    assert not second_arrived_before_first_response


def test_timeout_closes_cached_connection_and_next_request_reconnects():
    port_holder: list[int] = []
    ready = threading.Event()
    ready_for_reconnect = threading.Event()

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()

            conn, _ = srv.accept()
            with conn:
                _recv_envelope(conn)
                time.sleep(0.4)
            ready_for_reconnect.set()

            conn, _ = srv.accept()
            with conn:
                request = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=request.request_id,
                            status_response=messages_pb2.StatusResponse(
                                server_name="after-timeout"
                            ),
                        )
                    )
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=0.1)
    with pytest.raises(MargreteTimeoutError):
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    assert ready_for_reconnect.wait(timeout=2.0)
    response = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    client.close()
    thread.join(timeout=2.0)

    assert response.status_response.server_name == "after-timeout"


def test_request_id_mismatch_closes_connection_and_next_request_reconnects():
    port_holder: list[int] = []
    ready = threading.Event()

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()

            conn, _ = srv.accept()
            with conn:
                request = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=request.request_id + 1,
                            ping_response=messages_pb2.PingResponse(),
                        )
                    )
                )

            conn, _ = srv.accept()
            with conn:
                request = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=request.request_id,
                            status_response=messages_pb2.StatusResponse(
                                server_name="after-mismatch"
                            ),
                        )
                    )
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)
    with pytest.raises(MargreteProtocolError, match="did not match"):
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    response = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    client.close()
    thread.join(timeout=2.0)

    assert response.status_response.server_name == "after-mismatch"


def test_remote_error_response_keeps_connection_usable():
    port_holder: list[int] = []
    ready = threading.Event()
    accepted_connections = 0

    def server():
        nonlocal accepted_connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_holder.append(srv.getsockname()[1])
            ready.set()

            conn, _ = srv.accept()
            accepted_connections += 1
            with conn:
                first = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=first.request_id,
                            error_response=messages_pb2.ErrorResponse(
                                code=messages_pb2.ERROR_CODE_INVALID_ARGUMENT,
                                message="bad request",
                            ),
                        )
                    )
                )

                second = _recv_envelope(conn)
                conn.sendall(
                    encode_frame(
                        messages_pb2.Envelope(
                            request_id=second.request_id,
                            status_response=messages_pb2.StatusResponse(server_name="still-open"),
                        )
                    )
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    client = SocketRpcClient(f"127.0.0.1:{port_holder[0]}", timeout=2.0)
    with pytest.raises(MargreteRemoteError):
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    response = client.request(messages_pb2.Envelope(status_request=messages_pb2.StatusRequest()))
    client.close()
    thread.join(timeout=2.0)

    assert response.status_response.server_name == "still-open"
    assert accepted_connections == 1


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
