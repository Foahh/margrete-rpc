# pyright: reportMissingModuleSource=false

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, cast

from margrete_rpc._rpc.framed import ByteStream, FramedRpcClient
from margrete_rpc.errors import MargreteProtocolError, MargreteTimeoutError
from margrete_rpc.trace import NoopTracer, Tracer

_WIN32_PIPE_PREFIX = "\\\\.\\pipe\\"
_RETRY_SLEEP_S = 0.02


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("named pipe transport is only available on Windows")


def pipe_path(pipe_name: str) -> str:
    """Return the Win32 path ``\\\\.\\pipe\\{pipe_name}``."""
    if pipe_name.startswith(_WIN32_PIPE_PREFIX):
        return pipe_name
    return _WIN32_PIPE_PREFIX + pipe_name


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
        try:
            while remaining:
                _, chunk = win32file.ReadFile(self.handle, remaining)
                chunk = cast(bytes, chunk)
                if not chunk:
                    raise MargreteProtocolError("pipe closed before frame completed")
                chunks.append(chunk)
                remaining -= len(chunk)
        except MargreteProtocolError:
            raise
        except Exception as exc:
            if _winerror(exc) is None:
                raise
            raise MargreteProtocolError(f"pipe read failed: {exc}") from exc
        return b"".join(chunks)

    def write_all(self, data: bytes) -> None:
        _require_windows()
        import win32file

        offset = 0
        try:
            while offset < len(data):
                _, written = win32file.WriteFile(self.handle, data[offset:])
                if written == 0:
                    raise MargreteProtocolError("pipe closed before frame completed")
                offset += written
        except MargreteProtocolError:
            raise
        except Exception as exc:
            if _winerror(exc) is None:
                raise
            raise MargreteProtocolError(f"pipe write failed: {exc}") from exc

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
        self._path = pipe_path(self.endpoint)

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
        deadline = time.monotonic() + max(self.timeout, 0.0)
        while True:
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
                return PipeStream(handle)
            except pywintypes.error as exc:
                err = _winerror(exc)
                remaining = deadline - time.monotonic()
                if err not in retryable_errors or remaining <= 0:
                    if err in retryable_errors:
                        raise MargreteTimeoutError(
                            f"timed out connecting to pipe {self.endpoint}"
                        ) from exc
                    raise MargreteProtocolError(f"pipe connect failed: {exc}") from exc
                if err == winerror.ERROR_PIPE_BUSY:
                    try:
                        win32pipe.WaitNamedPipe(
                            self._path,
                            max(1, min(int(remaining * 1000), 0xFFFFFFFF)),
                        )
                    except pywintypes.error:
                        time.sleep(min(_RETRY_SLEEP_S, remaining))
                else:
                    # WaitNamedPipe returns immediately when no instance is listening.
                    time.sleep(min(_RETRY_SLEEP_S, remaining))


__all__ = ["PipeRpcClient", "pipe_path"]
