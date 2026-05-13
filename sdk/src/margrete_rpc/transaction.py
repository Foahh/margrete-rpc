from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model import Chart, LLChart, LLNote, normalize_event_operations
from margrete_rpc.trace import NoopTracer, Tracer


def _extend_events(request, chart: Chart | LLChart) -> None:
    normalized = normalize_event_operations(chart)
    ev = normalized.events
    request.bpm_events.extend(event.to_proto() for event in ev.bpm)
    request.beat_change_events.extend(event.to_proto() for event in ev.beat)
    request.timeline_speed_events.extend(event.to_proto() for event in ev.til)
    request.note_speed_events.extend(event.to_proto() for event in ev.note_speed)


def _final_notes(chart: Chart | LLChart) -> list[LLNote]:
    if isinstance(chart, LLChart):
        return chart.raw_notes
    return [note.to_ll() for note in chart.notes] + chart.raw_notes


def _has_existing_note_id(notes: list[LLNote]) -> bool:
    for note in notes:
        if note.id is not None or _has_existing_note_id(note.children):
            return True
    return False


@dataclass
class EditTransaction:
    name: str
    transport: object
    current_tick: int
    chart: Chart | LLChart
    event_scan_until_tick: int
    event_scan_max_til: int
    tracer: Tracer | None = None
    tx_type: str = "edit"
    _span_active: object | None = None

    def __enter__(self) -> EditTransaction:
        if self.tracer is None:
            self.tracer = NoopTracer()
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if self.tracer is None:
            self.tracer = NoopTracer()
        try:
            if exc_type is None:
                request = messages_pb2.ApplyEditPatchRequest(name=self.name)
                request.event_scan_until_tick = self.event_scan_until_tick
                request.event_scan_max_til = self.event_scan_max_til
                request.notes.extend(note.to_proto() for note in _final_notes(self.chart))
                _extend_events(request, self.chart)
                with self.tracer.span(
                    "margrete.tx.apply",
                    attrs={"tx.type": self.tx_type, "tx.name": self.name},
                ):
                    self.transport.request(messages_pb2.Envelope(apply_edit_patch_request=request))
            return False
        finally:
            if self._span_active is not None:
                self._span_active.__exit__(exc_type, exc, tb)
                self._span_active = None


@dataclass
class AppendTransaction:
    name: str
    transport: object
    current_tick: int
    chart: Chart
    tracer: Tracer | None = None
    tx_type: str = "append"
    _span_active: object | None = None

    def __enter__(self) -> AppendTransaction:
        if self.tracer is None:
            self.tracer = NoopTracer()
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if self.tracer is None:
            self.tracer = NoopTracer()
        try:
            if exc_type is None:
                final_notes = _final_notes(self.chart)
                if _has_existing_note_id(final_notes):
                    raise ValueError("append transactions cannot send existing note ids")
                request = messages_pb2.ApplyAppendPatchRequest(name=self.name)
                request.notes.extend(note.to_proto() for note in final_notes)
                _extend_events(request, self.chart)
                with self.tracer.span(
                    "margrete.tx.apply",
                    attrs={"tx.type": self.tx_type, "tx.name": self.name},
                ):
                    self.transport.request(
                        messages_pb2.Envelope(apply_append_patch_request=request)
                    )
            return False
        finally:
            if self._span_active is not None:
                self._span_active.__exit__(exc_type, exc, tb)
                self._span_active = None
