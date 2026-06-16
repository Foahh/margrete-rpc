from __future__ import annotations


class MargreteError(Exception):
    """Base class for all errors raised by ``margrete_rpc``.

    Catch this to handle any client-side failure regardless of cause.
    """


class MargreteProtocolError(MargreteError):
    """Raised when a server response cannot be parsed (invalid TCP/protobuf framing)."""


class MargreteDiscoveryError(MargreteError):
    """Raised when no single Margrete RPC instance can be resolved.

    Occurs when discovery finds zero or multiple instances, or a named instance is missing
    or unreachable.
    """


class MargreteRemoteError(MargreteError):
    """Raised when the plugin reports an error in response to a request.

    Attributes:
        code: The error code returned by the plugin.
    """

    def __init__(self, code: int, message: str) -> None:
        """Create the error from the plugin's ``code`` and ``message``."""
        super().__init__(message)
        self.code = code
