from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model import Chart, LLChart, LLNote, normalize_event_operations
from margrete_rpc.model.chart import ChartEvents
from margrete_rpc.model.chart_time import Position, pop_tick_resolver, push_tick_resolver
from margrete_rpc.trace import NoopTracer, Tracer


def _final_notes(chart: Chart | LLChart) -> list[LLNote]:
    if isinstance(chart, LLChart):
        return chart.raw_notes
    return [note.to_ll() for note in chart.notes] + chart.raw_notes


def _strip_note_ids(note: LLNote) -> LLNote:
    return LLNote(
        info=note.info.copy(),
        children=[_strip_note_ids(child) for child in note.children],
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


def _has_existing_note_id(notes: list[LLNote]) -> bool:
    for note in notes:
        if note._id is not None or _has_existing_note_id(note.children):
            return True
    return False


def _clone_ll_note(note: LLNote) -> LLNote:
    return LLNote.from_proto(note.to_proto())


def _clone_chart_events(events: ChartEvents) -> ChartEvents:
    from margrete_rpc.model.event import BeatEvent, BpmEvent, NoteSpeedEvent, TimelineSpeedEvent

    return ChartEvents(
        bpm=[BpmEvent.from_proto(event.to_proto()) for event in events.bpm],
        beat=[BeatEvent.from_proto(event.to_proto()) for event in events.beat],
        til=[TimelineSpeedEvent.from_proto(event.to_proto()) for event in events.til],
        note_speed=[NoteSpeedEvent.from_proto(event.to_proto()) for event in events.note_speed],
    )


def _note_tree_sig(note: LLNote) -> bytes:
    return _strip_note_ids(note).to_proto().SerializeToString()


def _id_structure(note: LLNote) -> tuple[int | None, tuple]:
    return (note._id, tuple(_id_structure(child) for child in note.children))


def _children_id_structure(note: LLNote) -> tuple:
    return tuple(_id_structure(child) for child in note.children)


def _append_scanned_note_diffs(
    request: messages_pb2.ApplyEditRequest,
    orig_notes: list[LLNote],
    final_notes: list[LLNote],
) -> None:
    orig_by_id = {note._id: note for note in orig_notes if note._id is not None}
    final_ids = {note._id for note in final_notes if note._id is not None}

    for note_id in orig_by_id:
        if note_id not in final_ids:
            request.note_ids_delete.append(note_id)

    for note in final_notes:
        if note._id is None:
            request.notes_upsert.append(_strip_note_ids(note).to_proto())
            continue
        orig = orig_by_id.get(note._id)
        if orig is None:
            request.notes_upsert.append(_strip_note_ids(note).to_proto())
            continue
        if _note_tree_sig(orig) == _note_tree_sig(note):
            continue
        if _children_id_structure(orig) == _children_id_structure(note):
            request.notes_upsert.append(note.to_proto())
        else:
            request.note_ids_delete.append(note._id)
            request.notes_upsert.append(_strip_note_ids(note).to_proto())


def _append_scanned_event_diffs(
    request: messages_pb2.ApplyEditRequest,
    orig_events: ChartEvents,
    final_events: ChartEvents,
) -> None:
    orig_bpm = {int(event.tick): event for event in orig_events.bpm}
    final_bpm = {int(event.tick): event for event in final_events.bpm}
    for tick in orig_bpm:
        if tick not in final_bpm:
            request.bpm_ticks_delete.append(tick)
    for tick, event in final_bpm.items():
        if (
            tick not in orig_bpm
            or event.to_proto().SerializeToString() != orig_bpm[tick].to_proto().SerializeToString()
        ):
            request.bpm_upsert.append(event.to_proto())

    orig_beat = {int(event.bar): event for event in orig_events.beat}
    final_beat = {int(event.bar): event for event in final_events.beat}
    for bar in orig_beat:
        if bar not in final_beat:
            request.beat_bars_delete.append(bar)
    for bar, event in final_beat.items():
        if (
            bar not in orig_beat
            or event.to_proto().SerializeToString() != orig_beat[bar].to_proto().SerializeToString()
        ):
            request.beat_upsert.append(event.to_proto())

    orig_til = {(int(event.tick), int(event.timeline_id)): event for event in orig_events.til}
    final_til = {(int(event.tick), int(event.timeline_id)): event for event in final_events.til}
    for key in orig_til:
        if key not in final_til:
            tick, timeline_id = key
            request.til_keys_delete.append(
                messages_pb2.TimelineSpeedKey(tick=tick, timeline_id=timeline_id)
            )
    for key, event in final_til.items():
        if (
            key not in orig_til
            or event.to_proto().SerializeToString() != orig_til[key].to_proto().SerializeToString()
        ):
            request.til_upsert.append(event.to_proto())

    orig_note_speed = {int(event.tick): event for event in orig_events.note_speed}
    final_note_speed = {int(event.tick): event for event in final_events.note_speed}
    for tick in orig_note_speed:
        if tick not in final_note_speed:
            request.note_speed_ticks_delete.append(tick)
    for tick, event in final_note_speed.items():
        if (
            tick not in orig_note_speed
            or event.to_proto().SerializeToString()
            != orig_note_speed[tick].to_proto().SerializeToString()
        ):
            request.note_speed_upsert.append(event.to_proto())


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
    _orig_notes: list[LLNote] | None = None
    _orig_events: ChartEvents | None = None
    _resolver_token: object | None = None

    def _resolve_position(self, pos: Position) -> int:
        return self.chart.p2t(*pos)

    def __enter__(self) -> EditTransaction:
        if self.tracer is None:
            self.tracer = NoopTracer()
        self._span_active = self.tracer.span(
            "margrete.tx",
            attrs={"tx.type": self.tx_type, "tx.name": self.name},
        )
        self._span_active.__enter__()
        self._resolver_token = push_tick_resolver(self._resolve_position)

        if self.scan:
            self._orig_notes = [_clone_ll_note(note) for note in _final_notes(self.chart)]
            self._orig_notes_sig = _notes_signature(_final_notes_without_ids(self.chart))
            normalized = normalize_event_operations(self.chart)
            self._orig_events = _clone_chart_events(normalized.events)
            self._orig_events_sig = _event_signature_from_chart(normalized)
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

                    request.replace_all_notes = False
                    _append_scanned_note_diffs(
                        request,
                        self._orig_notes or [],
                        _final_notes(self.chart),
                    )
                    _append_scanned_event_diffs(
                        request,
                        self._orig_events or ChartEvents(),
                        normalized.events,
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
            if self._resolver_token is not None:
                pop_tick_resolver(self._resolver_token)
                self._resolver_token = None
            if self._span_active is not None:
                self._span_active.__exit__(exc_type, exc, tb)
                self._span_active = None
