from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from margrete_rpc._proto import RPC_API_VERSION
from margrete_rpc.errors import MargreteVersionError


def client_version() -> str:
    """Return the installed Python client package version."""
    try:
        return version("margrete-rpc")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def plugin_api_is_compatible(api_version: int) -> bool:
    """Return whether a plugin RPC API version is supported by this client."""
    return api_version == RPC_API_VERSION


def ensure_compatible_api_version(api_version: int, *, server_version: str = "") -> None:
    """Raise if the connected plugin RPC API is not compatible with this client."""
    if plugin_api_is_compatible(api_version):
        return
    raise MargreteVersionError(
        client_api_version=RPC_API_VERSION,
        server_api_version=api_version,
        server_version=server_version,
    )


__all__ = [
    "RPC_API_VERSION",
    "client_version",
    "ensure_compatible_api_version",
    "plugin_api_is_compatible",
]
