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


def _strip_note_ids(note: LLNote) -> LLNote:
    return LLNote(
        info=note.info.copy(),
        children=[_strip_note_ids(child) for child in note.children],
        id=None,
    )


def _final_notes_without_ids(chart: Chart | LLChart) -> list[LLNote]:
    return [_strip_note_ids(note) for note in _final_notes(chart)]


def _notes_signature(notes: list[LLNote]) -> bytes:
    return b"\n".join(note.to_proto().SerializeToString() for note in notes)


def _event_keys_from_chart(
    chart: Chart | LLChart,
) -> tuple[set[int], set[int], set[tuple[int, int]], set[int]]:
    ev = chart.events
    bpm_ticks = {int(e.tick) for e in ev.bpm}
    beat_bars = {int(e.bar) for e in ev.beat}
    til_keys = {(int(e.tick), int(e.timeline_id)) for e in ev.til}
    note_speed_ticks = {int(e.tick) for e in ev.note_speed}
    return bpm_ticks, beat_bars, til_keys, note_speed_ticks


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
    event_scan_extra_tick: int
    event_scan_til: list[int]
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
                request.event_scan_extra_tick = self.event_scan_extra_tick
                request.event_scan_til.extend(self.event_scan_til)
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
class EditDeltaTransaction:
    name: str
    transport: object
    current_tick: int
    chart: Chart | LLChart
    event_scan_extra_tick: int
    event_scan_til: list[int]
    tracer: Tracer | None = None
    tx_type: str = "edit_delta"
    _span_active: object | None = None

    _orig_notes_sig: bytes = b""
    _orig_bpm_ticks: set[int] | None = None
    _orig_beat_bars: set[int] | None = None
    _orig_til_keys: set[tuple[int, int]] | None = None
    _orig_note_speed_ticks: set[int] | None = None

    def __enter__(self) -> EditDeltaTransaction:
        if self.tracer is None:
            self.tracer = NoopTracer()
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()

        self._orig_notes_sig = _notes_signature(_final_notes_without_ids(self.chart))
        bpm, beat, til, note_speed = _event_keys_from_chart(normalize_event_operations(self.chart))
        self._orig_bpm_ticks = bpm
        self._orig_beat_bars = beat
        self._orig_til_keys = til
        self._orig_note_speed_ticks = note_speed
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
                if (
                    self._orig_bpm_ticks is None
                    or self._orig_beat_bars is None
                    or self._orig_til_keys is None
                    or self._orig_note_speed_ticks is None
                ):
                    raise RuntimeError("delta transaction missing original snapshot keys")

                normalized = normalize_event_operations(self.chart)
                final_notes = _final_notes_without_ids(self.chart)
                final_notes_sig = _notes_signature(final_notes)

                final_bpm, final_beat, final_til, final_note_speed = _event_keys_from_chart(
                    normalized
                )
                if (
                    final_notes_sig == self._orig_notes_sig
                    and final_bpm == self._orig_bpm_ticks
                    and final_beat == self._orig_beat_bars
                    and final_til == self._orig_til_keys
                    and final_note_speed == self._orig_note_speed_ticks
                ):
                    return False

                request = messages_pb2.ApplyEditDeltaRequest(name=self.name)

                # Notes: clean semantics, no note-id lookups: replace everything.
                request.replace_all_notes = True
                request.notes_upsert.extend(note.to_proto() for note in final_notes)

                # Events: replace by explicit deletes (snapshot) + upserts (final). No scanning.
                request.bpm_ticks_delete.extend(sorted(self._orig_bpm_ticks))
                request.beat_bars_delete.extend(sorted(self._orig_beat_bars))
                request.til_keys_delete.extend(
                    messages_pb2.TimelineSpeedKey(tick=tick, timeline_id=timeline_id)
                    for (tick, timeline_id) in sorted(self._orig_til_keys)
                )
                request.note_speed_ticks_delete.extend(sorted(self._orig_note_speed_ticks))

                request.bpm_upsert.extend(event.to_proto() for event in normalized.events.bpm)
                request.beat_upsert.extend(event.to_proto() for event in normalized.events.beat)
                request.til_upsert.extend(event.to_proto() for event in normalized.events.til)
                request.note_speed_upsert.extend(
                    event.to_proto() for event in normalized.events.note_speed
                )

                with self.tracer.span(
                    "margrete.tx.apply",
                    attrs={"tx.type": self.tx_type, "tx.name": self.name},
                ):
                    self.transport.request(messages_pb2.Envelope(apply_edit_delta_request=request))
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
