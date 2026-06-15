from __future__ import annotations

import contextvars
from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._transport import RpcTransport
from margrete_rpc.chart import Chart
from margrete_rpc.chart.diff import (
    EditSnapshot,
    build_apply_edit_request,
    capture_edit_snapshot,
)
from margrete_rpc.chart.events import BeatEvent
from margrete_rpc.chart.time import (
    PositionLike,
    TickResolver,
    p2t,
    pop_beat_events,
    pop_tick_resolver,
    push_beat_events,
    push_tick_resolver,
)
from margrete_rpc.trace import NoopTracer, Tracer


@dataclass
class EditTransaction:
    """A scoped, atomic edit of a Margrete chart.

    Created by :meth:`Margrete.open_edit` and used as a context manager. Entering the
    ``with`` block snapshots the chart (when ``scan`` is enabled) and installs the chart's
    beat events as the active position context, so bare ``(bar, beat, offset)`` positions
    passed to note constructors resolve to ticks. Mutate :attr:`chart` inside the block;
    on clean exit the changes are diffed and sent to Margrete as one undoable edit, and if
    the block raises, nothing is applied.

    Attributes:
        name: Label for the edit, shown in Margrete's undo history.
        current_tick: The editor playhead tick captured when the transaction opened.
        chart: The loaded :class:`~margrete_rpc.chart.Chart`; mutate its ``notes`` and
            ``events`` to describe the edit.
        scan: Whether a baseline snapshot was captured for diffing.
        replace_all_notes: Replace all notes on apply instead of sending a diff.
    """

    name: str
    transport: RpcTransport
    current_tick: int
    chart: Chart
    scan: bool
    tracer: Tracer = field(default_factory=NoopTracer)
    tx_type: str = "edit"
    replace_all_notes: bool = False
    _span_active: AbstractContextManager[None] | None = None

    _snapshot: EditSnapshot | None = None
    _resolver_token: contextvars.Token[TickResolver | None] | None = None
    _beat_events_token: contextvars.Token[Iterable[BeatEvent] | None] | None = None

    def _resolve_position(self, pos: PositionLike) -> int:
        return p2t(*pos, beat_events=self.chart.events.beat)

    def __enter__(self) -> EditTransaction:
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()
        self._beat_events_token = push_beat_events(self.chart.events.beat)
        self._resolver_token = push_tick_resolver(self._resolve_position)

        if self.scan:
            self._snapshot = capture_edit_snapshot(self.chart)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is None:
                request = build_apply_edit_request(
                    self.name,
                    self.chart,
                    scan=self.scan,
                    replace_all_notes=self.replace_all_notes,
                    snapshot=self._snapshot,
                )
                if request is not None:
                    with self.tracer.span(
                        "margrete.tx.apply",
                        attrs={"tx.type": self.tx_type, "tx.name": self.name},
                    ):
                        self.transport.request(messages_pb2.Envelope(apply_edit_request=request))
            return False
        finally:
            if self._resolver_token is not None:
                pop_tick_resolver(self._resolver_token)
                self._resolver_token = None
            if self._beat_events_token is not None:
                pop_beat_events(self._beat_events_token)
                self._beat_events_token = None
            if self._span_active is not None:
                self._span_active.__exit__(exc_type, exc, tb)
                self._span_active = None
