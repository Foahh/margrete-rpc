from __future__ import annotations


class MargreteError(Exception):
    """Base exception for margrete_rpc."""


class MargreteProtocolError(MargreteError):
    """Raised when the TCP/protobuf framing is invalid."""


class MargreteRemoteError(MargreteError):
    """Raised when the plugin returns an ErrorResponse."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
