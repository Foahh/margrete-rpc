import tomllib
from pathlib import Path

import pytest
from margrete_rpc import Margrete, MargreteVersionError
from margrete_rpc._proto import messages_pb2
from margrete_rpc._version import RPC_API_VERSION, plugin_api_is_compatible


class FakeTransport:
    def __init__(self, responses, *, api_version: int = RPC_API_VERSION):
        self.responses = list(responses)
        self.requests = []
        self.api_version = api_version

    def request(self, envelope):
        self.requests.append(envelope)
        if envelope.HasField("status_request"):
            return messages_pb2.Envelope(
                status_response=messages_pb2.StatusResponse(
                    server_version="0.1.0",
                    api_version=self.api_version,
                )
            )
        return self.responses.pop(0)


def test_python_and_plugin_release_versions_match():
    root = Path(__file__).parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    cargo = tomllib.loads((root / "plugin" / "Cargo.toml").read_text(encoding="utf-8"))

    assert project["project"]["version"] == cargo["package"]["version"]


def test_python_and_plugin_rpc_api_versions_match():
    root = Path(__file__).parents[2]
    api_version = int((root / "proto" / "API_VERSION").read_text(encoding="utf-8").strip())

    assert api_version == RPC_API_VERSION


def test_plugin_api_compatibility_allows_supported_api():
    assert plugin_api_is_compatible(RPC_API_VERSION)


def test_plugin_api_compatibility_rejects_old_or_new_api():
    assert not plugin_api_is_compatible(0)
    assert not plugin_api_is_compatible(RPC_API_VERSION + 1)


def test_margrete_checks_version_for_custom_transport():
    transport = FakeTransport([])

    Margrete(transport=transport)

    assert transport.requests[0].HasField("status_request")


def test_margrete_rejects_incompatible_plugin_api_version():
    transport = FakeTransport([], api_version=0)

    with pytest.raises(MargreteVersionError) as exc:
        Margrete(transport=transport)

    assert exc.value.server_api_version == 0
    assert exc.value.client_api_version == RPC_API_VERSION
    assert exc.value.server_version == "0.1.0"
    assert "RPC API 0" in str(exc.value)
