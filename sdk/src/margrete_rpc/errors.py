from __future__ import annotations


class MargreteError(Exception):
    """Base exception for margrete_rpc."""


class MargreteProtocolError(MargreteError):
    """Raised when the TCP/protobuf framing is invalid."""


class MargreteDiscoveryError(MargreteError):
    """Raised when a running plugin instance cannot be selected."""


class MargreteRemoteError(MargreteError):
    """Raised when the plugin returns an ErrorResponse."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
