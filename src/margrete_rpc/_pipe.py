# pyright: reportMissingModuleSource=false

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, cast

from margrete_rpc._framed_client import ByteStream, FramedRpcClient
from margrete_rpc.errors import MargreteProtocolError, MargreteTimeoutError
from margrete_rpc.trace import NoopTracer, Tracer


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("named pipe transport is only available on Windows")


def normalize_pipe_endpoint(endpoint: str) -> str:
    if endpoint.startswith("npipe://./pipe/"):
        return "\\\\.\\pipe\\" + endpoint.removeprefix("npipe://./pipe/")
    if endpoint.startswith("npipe://"):
        value = endpoint.removeprefix("npipe://")
        if value.startswith("./"):
            value = value[2:]
        if value.startswith("pipe/"):
            return "\\\\.\\pipe\\" + value.removeprefix("pipe/")
    return endpoint


def display_pipe_endpoint(path: str) -> str:
    prefix = "\\\\.\\pipe\\"
    if path.startswith(prefix):
        return "npipe://./pipe/" + path.removeprefix(prefix)
    return path


def _winerror(exc: BaseException) -> int | None:
    return getattr(exc, "winerror", None) or (exc.args[0] if exc.args else None)


@dataclass
class PipeStream:
    handle: Any

    def read_exact(self, size: int) -> bytes:
        _require_windows()
        import win32file

        chunks: list[bytes] = []
        remaining = size
        while remaining:
            _, chunk = win32file.ReadFile(self.handle, remaining)
            chunk = cast(bytes, chunk)
            if not chunk:
                raise MargreteProtocolError("pipe closed before frame completed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def write_all(self, data: bytes) -> None:
        _require_windows()
        import win32file

        offset = 0
        while offset < len(data):
            _, written = win32file.WriteFile(self.handle, data[offset:])
            if written == 0:
                raise MargreteProtocolError("pipe closed before frame completed")
            offset += written

    def close(self) -> None:
        _require_windows()
        import win32api

        win32api.CloseHandle(self.handle)


@dataclass
class PipeRpcClient(FramedRpcClient):
    endpoint: str
    timeout: float = 60.0
    tracer: Tracer = field(default_factory=NoopTracer)

    def __post_init__(self) -> None:
        super().__post_init__()
        self._path = normalize_pipe_endpoint(self.endpoint)

    def _open_connection(self) -> ByteStream:
        _require_windows()
        import pywintypes
        import win32file
        import win32pipe
        import winerror

        retryable_errors = {
            winerror.ERROR_FILE_NOT_FOUND,
            winerror.ERROR_PIPE_BUSY,
            winerror.ERROR_SEM_TIMEOUT,
        }
        timeout_ms = max(1, min(int(self.timeout * 1000), 0xFFFFFFFF))
        try:
            handle = win32file.CreateFile(
                self._path,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
        except pywintypes.error as exc:
            if _winerror(exc) not in retryable_errors:
                raise
            try:
                win32pipe.WaitNamedPipe(self._path, timeout_ms)
            except pywintypes.error as wait_exc:
                if _winerror(wait_exc) in retryable_errors:
                    raise MargreteTimeoutError(
                        f"timed out connecting to pipe {self.endpoint}"
                    ) from wait_exc
                raise
            handle = win32file.CreateFile(
                self._path,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
        return PipeStream(handle)


__all__ = ["PipeRpcClient", "display_pipe_endpoint", "normalize_pipe_endpoint"]
