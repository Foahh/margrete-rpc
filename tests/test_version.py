import re
import tomllib
from pathlib import Path

import pytest

from margrete_rpc import Margrete, MargreteVersionError
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._version import RPC_API_VERSION, plugin_api_is_compatible


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def _status_response(api_version: int, server_version: str = "0.1.0") -> messages_pb2.Envelope:
    return messages_pb2.Envelope(
        status_response=messages_pb2.StatusResponse(
            server_name="Margrete RPC",
            server_version=server_version,
            api_version=api_version,
        )
    )


def test_python_and_plugin_release_versions_match():
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    plugin_version = (root / "plugin" / "config" / "VERSION").read_text(encoding="utf-8")

    assert project["project"]["version"] == plugin_version.strip()


def test_python_and_plugin_rpc_api_versions_match():
    root = Path(__file__).parents[1]
    meta_template = (root / "plugin" / "config" / "meta.h.in").read_text(encoding="utf-8")
    match = re.search(r"^#define RPC_API_VERSION (\d+)$", meta_template, re.MULTILINE)

    assert match is not None
    assert int(match.group(1)) == RPC_API_VERSION


def test_plugin_api_compatibility_allows_supported_api():
    assert plugin_api_is_compatible(RPC_API_VERSION)


def test_plugin_api_compatibility_rejects_old_or_new_api():
    assert not plugin_api_is_compatible(0)
    assert not plugin_api_is_compatible(RPC_API_VERSION + 1)


def test_margrete_can_force_version_check_for_custom_transport():
    transport = FakeTransport([_status_response(RPC_API_VERSION)])

    Margrete(transport=transport, ensure_version=True)

    assert transport.requests[0].HasField("status_request")


def test_margrete_rejects_incompatible_plugin_api_version():
    transport = FakeTransport([_status_response(0, server_version="0.1.0")])

    with pytest.raises(MargreteVersionError) as exc:
        Margrete(transport=transport, ensure_version=True)

    assert exc.value.server_api_version == 0
    assert exc.value.client_api_versions == frozenset({RPC_API_VERSION})
    assert exc.value.server_version == "0.1.0"
    assert "RPC API 0" in str(exc.value)


def test_margrete_skips_version_check_for_custom_transport_by_default():
    transport = FakeTransport([])

    Margrete(transport=transport)

    assert transport.requests == []
