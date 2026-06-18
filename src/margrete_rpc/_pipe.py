from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass, field

from margrete_rpc._framed_client import ByteStream, FramedRpcClient
from margrete_rpc.errors import MargreteProtocolError, MargreteTimeoutError
from margrete_rpc.trace import NoopTracer, Tracer

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
ERROR_FILE_NOT_FOUND = 2
ERROR_PIPE_BUSY = 231
ERROR_SEM_TIMEOUT = 121


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


class _Kernel32:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("named pipe transport is only available on Windows")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32 = kernel32
        self.CreateFileW = kernel32.CreateFileW
        self.CreateFileW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        self.CreateFileW.restype = ctypes.c_void_p
        self.ReadFile = kernel32.ReadFile
        self.ReadFile.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        ]
        self.ReadFile.restype = ctypes.c_int
        self.WriteFile = kernel32.WriteFile
        self.WriteFile.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        ]
        self.WriteFile.restype = ctypes.c_int
        self.CloseHandle = kernel32.CloseHandle
        self.CloseHandle.argtypes = [ctypes.c_void_p]
        self.CloseHandle.restype = ctypes.c_int
        self.WaitNamedPipeW = kernel32.WaitNamedPipeW
        self.WaitNamedPipeW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        self.WaitNamedPipeW.restype = ctypes.c_int

    def last_error(self) -> int:
        return ctypes.get_last_error()


_kernel32: _Kernel32 | None = None


def _win32() -> _Kernel32:
    global _kernel32
    if _kernel32 is None:
        _kernel32 = _Kernel32()
    return _kernel32


def _raise_last_error(prefix: str) -> None:
    code = _win32().last_error()
    raise OSError(code, f"{prefix} failed with Windows error {code}")


@dataclass
class PipeStream:
    handle: int

    def read_exact(self, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            buffer = ctypes.create_string_buffer(remaining)
            read = ctypes.c_uint32(0)
            ok = _win32().ReadFile(
                ctypes.c_void_p(self.handle),
                buffer,
                remaining,
                ctypes.byref(read),
                None,
            )
            if not ok:
                _raise_last_error("ReadFile")
            if read.value == 0:
                raise MargreteProtocolError("pipe closed before frame completed")
            chunks.append(buffer.raw[: read.value])
            remaining -= read.value
        return b"".join(chunks)

    def write_all(self, data: bytes) -> None:
        offset = 0
        while offset < len(data):
            chunk = data[offset:]
            buffer = ctypes.create_string_buffer(chunk)
            written = ctypes.c_uint32(0)
            ok = _win32().WriteFile(
                ctypes.c_void_p(self.handle),
                buffer,
                len(chunk),
                ctypes.byref(written),
                None,
            )
            if not ok:
                _raise_last_error("WriteFile")
            if written.value == 0:
                raise MargreteProtocolError("pipe closed before frame completed")
            offset += written.value

    def close(self) -> None:
        _win32().CloseHandle(ctypes.c_void_p(self.handle))


@dataclass
class PipeRpcClient(FramedRpcClient):
    endpoint: str
    timeout: float = 60.0
    tracer: Tracer = field(default_factory=NoopTracer)

    def __post_init__(self) -> None:
        super().__post_init__()
        self._path = normalize_pipe_endpoint(self.endpoint)

    def _open_connection(self) -> ByteStream:
        timeout_ms = max(1, min(int(self.timeout * 1000), 0xFFFFFFFF))
        handle = _win32().CreateFileW(
            self._path,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            code = _win32().last_error()
            if code in {ERROR_FILE_NOT_FOUND, ERROR_PIPE_BUSY, ERROR_SEM_TIMEOUT}:
                if not _win32().WaitNamedPipeW(self._path, timeout_ms):
                    raise MargreteTimeoutError(f"timed out connecting to pipe {self.endpoint}")
                handle = _win32().CreateFileW(
                    self._path,
                    GENERIC_READ | GENERIC_WRITE,
                    0,
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None,
                )
            if handle == INVALID_HANDLE_VALUE:
                _raise_last_error("CreateFileW")
        return PipeStream(int(handle))


__all__ = ["PipeRpcClient", "display_pipe_endpoint", "normalize_pipe_endpoint"]
