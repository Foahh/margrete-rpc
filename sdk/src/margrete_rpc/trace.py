from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any, Protocol

TraceAttrs = Mapping[str, Any]


class Tracer(Protocol):
    def span(
        self,
        name: str,
        *,
        attrs: TraceAttrs | None = None,
    ) -> AbstractContextManager[None]: ...


@dataclass(frozen=True, slots=True)
class TraceEvent:
    name: str
    start_ns: int
    end_ns: int
    attrs: dict[str, Any]
    error_type: str | None = None
    error_message: str | None = None

    @property
    def duration_s(self) -> float:
        return (self.end_ns - self.start_ns) / 1_000_000_000.0


class NoopTracer:
    @contextmanager
    def span(self, name: str, *, attrs: TraceAttrs | None = None) -> Generator[None]:
        yield


class CallbackTracer:
    def __init__(self, emit: Callable[[TraceEvent], None]) -> None:
        self._emit = emit

    @contextmanager
    def span(self, name: str, *, attrs: TraceAttrs | None = None) -> Generator[None]:
        start_ns = perf_counter_ns()
        try:
            yield
        except Exception as e:
            end_ns = perf_counter_ns()
            self._emit(
                TraceEvent(
                    name=name,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    attrs=dict(attrs or {}),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            )
            raise
        else:
            end_ns = perf_counter_ns()
            self._emit(
                TraceEvent(
                    name=name,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    attrs=dict(attrs or {}),
                )
            )
