from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model import Chart, LLChart, LLNote, normalize_event_operations
from margrete_rpc.trace import NoopTracer, Tracer


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


def _event_signature_from_chart(chart: Chart | LLChart) -> bytes:
    ev = chart.events
    bpm = sorted(ev.bpm, key=lambda event: int(event.tick))
    beat = sorted(ev.beat, key=lambda event: int(event.bar))
    til = sorted(ev.til, key=lambda event: (int(event.tick), int(event.timeline_id)))
    note_speed = sorted(ev.note_speed, key=lambda event: int(event.tick))
    return b"\x1e".join(
        [
            b"\x1f".join(event.to_proto().SerializeToString() for event in bpm),
            b"\x1f".join(event.to_proto().SerializeToString() for event in beat),
            b"\x1f".join(event.to_proto().SerializeToString() for event in til),
            b"\x1f".join(event.to_proto().SerializeToString() for event in note_speed),
        ]
    )


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
    scan: bool
    tracer: Tracer | None = None
    tx_type: str = "edit"
    _span_active: object | None = None

    _orig_notes_sig: bytes = b""
    _orig_events_sig: bytes = b""
    _orig_bpm_ticks: set[int] | None = None
    _orig_beat_bars: set[int] | None = None
    _orig_til_keys: set[tuple[int, int]] | None = None
    _orig_note_speed_ticks: set[int] | None = None

    def __enter__(self) -> EditTransaction:
        if self.tracer is None:
            self.tracer = NoopTracer()
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()

        if self.scan:
            self._orig_notes_sig = _notes_signature(_final_notes_without_ids(self.chart))
            normalized = normalize_event_operations(self.chart)
            self._orig_events_sig = _event_signature_from_chart(normalized)
            bpm, beat, til, note_speed = _event_keys_from_chart(normalized)
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
                normalized = normalize_event_operations(self.chart)
                request = messages_pb2.ApplyEditRequest(name=self.name)

                if self.scan:
                    final_notes = _final_notes_without_ids(self.chart)
                    final_events_sig = _event_signature_from_chart(normalized)
                    if (
                        _notes_signature(final_notes) == self._orig_notes_sig
                        and final_events_sig == self._orig_events_sig
                    ):
                        return False

                    request.replace_all_notes = True
                    request.notes_upsert.extend(note.to_proto() for note in final_notes)
                    request.bpm_ticks_delete.extend(sorted(self._orig_bpm_ticks or set()))
                    request.beat_bars_delete.extend(sorted(self._orig_beat_bars or set()))
                    request.til_keys_delete.extend(
                        messages_pb2.TimelineSpeedKey(tick=tick, timeline_id=timeline_id)
                        for (tick, timeline_id) in sorted(self._orig_til_keys or set())
                    )
                    request.note_speed_ticks_delete.extend(
                        sorted(self._orig_note_speed_ticks or set())
                    )
                else:
                    final_notes = _final_notes(self.chart)
                    if _has_existing_note_id(final_notes):
                        raise ValueError("scan=false transactions cannot send existing note ids")
                    request.replace_all_notes = False
                    request.notes_upsert.extend(note.to_proto() for note in final_notes)

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
                    self.transport.request(messages_pb2.Envelope(apply_edit_request=request))
            return False
        finally:
            if self._span_active is not None:
                self._span_active.__exit__(exc_type, exc, tb)
                self._span_active = None
