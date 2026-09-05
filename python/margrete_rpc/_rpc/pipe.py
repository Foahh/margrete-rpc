# pyright: reportMissingModuleSource=false

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, cast

from margrete_rpc._rpc.framed import ByteStream, FramedRpcClient
from margrete_rpc.errors import MargreteProtocolError, MargreteTimeoutError

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


@dataclass
class PipeStream:
    handle: Any
    timeout: float = 60.0
    _deadline: float = field(default=0.0, init=False, repr=False)

    def _transfer(self, buffer: Any, *, write: bool) -> int:
        import pywintypes
        import win32api
        import win32event
        import win32file
        import winerror

        overlapped = pywintypes.OVERLAPPED()
        event = win32event.CreateEvent(None, True, False, None)
        overlapped.hEvent = event
        try:
            operation = win32file.WriteFile if write else win32file.ReadFile
            operation(self.handle, buffer, overlapped)
            try:
                remaining = max(0.0, self._deadline - time.monotonic())
                wait = win32event.WaitForSingleObject(
                    overlapped.hEvent, min(int(remaining * 1000), 0xFFFFFFFE)
                )
                if wait == win32event.WAIT_TIMEOUT:
                    raise TimeoutError("pipe request timed out")
                return win32file.GetOverlappedResult(self.handle, overlapped, False)
            except BaseException:
                # Keep the buffer and OVERLAPPED alive until cancellation completes.
                win32file.CancelIo(self.handle)
                try:
                    win32file.GetOverlappedResult(self.handle, overlapped, True)
                except pywintypes.error as exc:
                    if exc.winerror != winerror.ERROR_OPERATION_ABORTED:
                        raise
                raise
        finally:
            win32api.CloseHandle(event)

    def read_exact(self, size: int) -> bytes:
        _require_windows()
        import pywintypes
        import win32file

        chunks: list[bytes] = []
        remaining = size
        try:
            while remaining:
                buffer = cast(Any, win32file.AllocateReadBuffer(remaining))
                count = self._transfer(buffer, write=False)
                if count == 0:
                    raise MargreteProtocolError("pipe closed before frame completed")
                chunks.append(bytes(buffer[:count]))
                remaining -= count
        except pywintypes.error as exc:
            raise MargreteProtocolError(f"pipe read failed: {exc}") from exc
        return b"".join(chunks)

    def write_all(self, data: bytes) -> None:
        _require_windows()
        import pywintypes

        self._deadline = time.monotonic() + max(self.timeout, 0.0)
        offset = 0
        try:
            while offset < len(data):
                written = self._transfer(data[offset:], write=True)
                if written == 0:
                    raise MargreteProtocolError("pipe closed before frame completed")
                offset += written
        except pywintypes.error as exc:
            raise MargreteProtocolError(f"pipe write failed: {exc}") from exc

    def close(self) -> None:
        _require_windows()
        import win32api

        win32api.CloseHandle(self.handle)


@dataclass
class PipeRpcClient(FramedRpcClient):
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
                    win32file.FILE_FLAG_OVERLAPPED,
                    None,
                )
                return PipeStream(handle, self.timeout)
            except pywintypes.error as exc:
                err = exc.winerror
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
