from __future__ import annotations


class MargreteError(Exception):
    """Base class for all errors raised by ``margrete_rpc``.

    Catch this to handle any client-side failure regardless of cause.
    """


class MargreteProtocolError(MargreteError):
    """Raised when a server response cannot be parsed (invalid TCP/protobuf framing)."""


class MargreteTimeoutError(MargreteError, TimeoutError):
    """Raised when connecting to or waiting for the plugin exceeds the client timeout."""


class MargreteDiscoveryError(MargreteError):
    """Raised when no single Margrete RPC instance can be resolved.

    Occurs when discovery finds zero or multiple instances, or a named instance is missing
    or unreachable.
    """


class MargreteVersionError(MargreteError):
    """Raised when the Python client and plugin RPC API versions are not compatible.

    Attributes:
        client_api_versions: RPC API versions supported by this Python client.
        server_api_version: RPC API version reported by the plugin.
        server_version: Plugin product version reported by Margrete, if available.
    """

    def __init__(
        self,
        *,
        client_api_versions: set[int] | frozenset[int],
        server_api_version: int,
        server_version: str = "",
    ) -> None:
        """Create the error from the local client and remote plugin API versions."""
        supported = ", ".join(str(version) for version in sorted(client_api_versions))
        plugin_detail = f" plugin {server_version}" if server_version else " plugin"
        super().__init__(
            "margrete-rpc Python client supports RPC API "
            f"{supported}, but Margrete RPC{plugin_detail} reports RPC API "
            f"{server_api_version}. Install matching margrete-rpc Python and plugin releases, "
            "or pass ensure_version=False if you intentionally want to bypass this check."
        )
        self.client_api_versions = frozenset(client_api_versions)
        self.server_api_version = server_api_version
        self.server_version = server_version


class MargreteRemoteError(MargreteError):
    """Raised when the plugin reports an error in response to a request.

    Attributes:
        code: The error code returned by the plugin.
    """

    def __init__(self, code: int, message: str) -> None:
        """Create the error from the plugin's ``code`` and ``message``."""
        super().__init__(message)
        self.code = code
