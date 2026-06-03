import json
import socket
import struct
import threading
from pathlib import Path

import pytest

from margrete_rpc import Margrete, MargreteDiscoveryError, list_instances
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import encode_frame
from margrete_rpc.discovery import discovery_dir, resolve_endpoint


def _write_record(base: Path, instance_id: str, endpoint: str) -> None:
    directory = base / "MargreteRPC" / "instances"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{instance_id}.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "instance_id": instance_id,
                "pid": 123,
                "endpoint": endpoint,
                "plugin_version": "0.1.0",
                "log": "margrete-rpc.log",
            }
        ),
        encoding="utf-8",
    )


def _start_ping_server() -> str:
    port_holder: list[int] = []

    def server() -> None:
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
                    ping_response=messages_pb2.PingResponse(server_name="Margrete RPC"),
                )
                conn.sendall(encode_frame(response))

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    while not port_holder:
        pass
    return f"127.0.0.1:{port_holder[0]}"


def test_discovery_dir_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert discovery_dir() == tmp_path / "MargreteRPC" / "instances"


def test_list_instances_loads_records_without_validation(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _write_record(tmp_path, "one", "127.0.0.1:49000")

    instances = list_instances(validate=False)

    assert len(instances) == 1
    assert instances[0].instance_id == "one"
    assert instances[0].endpoint == "127.0.0.1:49000"


def test_list_instances_filters_stale_records(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _write_record(tmp_path, "stale", "127.0.0.1:1")

    assert list_instances(validate=True, timeout=0.1) == []


def test_resolve_endpoint_uses_single_live_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    endpoint = _start_ping_server()
    _write_record(tmp_path, "live", endpoint)

    assert resolve_endpoint(timeout=1.0) == endpoint


def test_resolve_endpoint_rejects_ambiguous_instances(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    first = _start_ping_server()
    second = _start_ping_server()
    _write_record(tmp_path, "first", first)
    _write_record(tmp_path, "second", second)

    with pytest.raises(MargreteDiscoveryError, match="multiple"):
        resolve_endpoint(timeout=1.0)


def test_margrete_requires_single_discovered_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    with pytest.raises(MargreteDiscoveryError, match="no running"):
        Margrete(timeout=0.1)
