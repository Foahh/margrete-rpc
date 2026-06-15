from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any, Protocol

TraceAttrs = Mapping[str, Any]
"""Arbitrary key/value attributes attached to a trace span."""


class Tracer(Protocol):
    """Observability hook for the client; pass one to :class:`Margrete`.

    Implementations wrap each RPC in a span. The SDK ships :class:`NoopTracer` (default)
    and :class:`CallbackTracer`.
    """

    def span(
        self,
        name: str,
        *,
        attrs: TraceAttrs | None = None,
    ) -> AbstractContextManager[None]:
        """Return a context manager wrapping one traced operation named ``name``."""
        ...


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """A completed span emitted by :class:`CallbackTracer`.

    Attributes:
        name: The span name (e.g. ``"margrete.tx.apply"``).
        start_ns: Start time from a monotonic clock, in nanoseconds.
        end_ns: End time from a monotonic clock, in nanoseconds.
        attrs: Attributes attached when the span was opened.
        error_type: Exception class name if the span ended with an error, else ``None``.
        error_message: Exception message if the span ended with an error, else ``None``.
    """

    name: str
    start_ns: int
    end_ns: int
    attrs: dict[str, Any]
    error_type: str | None = None
    error_message: str | None = None

    @property
    def duration_s(self) -> float:
        """The span's wall-clock duration in seconds."""
        return (self.end_ns - self.start_ns) / 1_000_000_000.0


class NoopTracer:
    """A :class:`Tracer` that does nothing; the default when no tracer is supplied."""

    @contextmanager
    def span(self, name: str, *, attrs: TraceAttrs | None = None) -> Generator[None]:
        """Yield immediately without recording anything."""
        yield


class CallbackTracer:
    """A :class:`Tracer` that emits a :class:`TraceEvent` for each completed span."""

    def __init__(self, emit: Callable[[TraceEvent], None]) -> None:
        """Create a tracer that calls ``emit`` with a :class:`TraceEvent` per span."""
        self._emit = emit

    @contextmanager
    def span(self, name: str, *, attrs: TraceAttrs | None = None) -> Generator[None]:
        """Time the wrapped block and emit a :class:`TraceEvent`, recording any exception."""
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
