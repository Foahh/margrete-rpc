from __future__ import annotations


class MargreteError(Exception):
    """Base class for all errors raised by ``margrete_rpc``.

    Catch this to handle any client-side failure regardless of cause.
    """


class MargreteProtocolError(MargreteError):
    """Raised when a server response cannot be parsed (invalid RPC/protobuf framing)."""


class MargreteTimeoutError(MargreteError, TimeoutError):
    """Raised when connecting to or waiting for the plugin exceeds the client timeout."""


class MargreteDiscoveryError(MargreteError):
    """Raised when no single Margrete RPC instance can be resolved.

    Occurs when named-pipe discovery finds zero or multiple instances.
    """


class MargreteVersionError(MargreteError):
    """Raised when the Python client and plugin RPC API versions are not compatible.

    Attributes:
        client_api_version: RPC API version required by this Python client.
        server_api_version: RPC API version reported by the plugin.
        server_version: Plugin product version reported by Margrete, if available.
    """

    def __init__(
        self,
        *,
        client_api_version: int,
        server_api_version: int,
        server_version: str = "",
    ) -> None:
        """Create the error from the local client and remote plugin API versions."""
        plugin_detail = f" plugin {server_version}" if server_version else " plugin"
        super().__init__(
            "margrete-rpc Python client requires RPC API "
            f"{client_api_version}, but Margrete RPC{plugin_detail} reports RPC API "
            f"{server_api_version}. Install matching margrete-rpc Python and plugin releases."
        )
        self.client_api_version = client_api_version
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
