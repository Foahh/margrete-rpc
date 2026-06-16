from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart.chart import Chart, ChartEvents, ChartNote
from margrete_rpc.chart.notes import RawNote


@dataclass
class EditSnapshot:
    notes_signature: bytes = b""
    events_signature: bytes = b""
    notes: list[RawNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)


def capture_edit_snapshot(chart: Chart) -> EditSnapshot:
    normalized_events = chart.events.normalized()
    return EditSnapshot(
        notes_signature=_notes_signature(_final_notes_without_ids(chart)),
        events_signature=_event_signature_from_events(normalized_events),
        notes=[_clone_raw(note) for note in _final_notes(chart)],
        events=_clone_chart_events(normalized_events),
    )


def build_apply_edit_request(
    chart: Chart,
    *,
    snapshot_enabled: bool,
    replace_all_notes: bool,
    snapshot: EditSnapshot | None,
) -> messages_pb2.ApplyEditRequest | None:
    normalized_events = chart.events.normalized()
    request = messages_pb2.ApplyEditRequest()

    if replace_all_notes:
        final_notes = _final_notes_without_ids(chart)
        request.replace_all_notes = True
        request.notes_upsert.extend(note.to_proto() for note in final_notes)
        _append_all_event_upserts(request, normalized_events)
        return request

    if snapshot_enabled:
        snapshot = snapshot or EditSnapshot()
        final_notes = _final_notes_without_ids(chart)
        final_events_sig = _event_signature_from_events(normalized_events)
        if (
            _notes_signature(final_notes) == snapshot.notes_signature
            and final_events_sig == snapshot.events_signature
        ):
            return None

        request.replace_all_notes = False
        _append_scanned_note_diffs(request, snapshot.notes, _final_notes(chart))
        _append_scanned_event_diffs(request, snapshot.events, normalized_events)
        return request

    final_notes = _final_notes(chart)
    if _has_existing_note_id(final_notes):
        raise ValueError("snapshot=false transactions cannot send existing note ids")

    request.replace_all_notes = False
    request.notes_upsert.extend(note.to_proto() for note in final_notes)
    _append_all_event_upserts(request, normalized_events)
    return request


def _note_to_raw(note: ChartNote) -> RawNote:
    if isinstance(note, RawNote):
        return note
    return note.to_raw()


def _final_notes(chart: Chart) -> list[RawNote]:
    return [_note_to_raw(note) for note in chart.notes]


def _strip_note_ids(note: RawNote) -> RawNote:
    return RawNote(
        info=note.info.copy(),
        children=[_strip_note_ids(child) for child in note.children],
    )


def _final_notes_without_ids(chart: Chart) -> list[RawNote]:
    return [_strip_note_ids(note) for note in _final_notes(chart)]


def _notes_signature(notes: list[RawNote]) -> bytes:
    return b"\n".join(note.to_proto().SerializeToString() for note in notes)


def _event_signature_from_events(events: ChartEvents) -> bytes:
    ev = events
    bpm = sorted(ev.bpm, key=lambda event: int(event.t))
    beat = sorted(ev.beat, key=lambda event: int(event.bar))
    til = sorted(ev.til, key=lambda event: (int(event.t), int(event.til)))
    note_speed = sorted(ev.note_speed, key=lambda event: int(event.t))
    return b"\x1e".join(
        [
            b"\x1f".join(event.to_proto().SerializeToString() for event in bpm),
            b"\x1f".join(event.to_proto().SerializeToString() for event in beat),
            b"\x1f".join(event.to_proto().SerializeToString() for event in til),
            b"\x1f".join(event.to_proto().SerializeToString() for event in note_speed),
        ]
    )


def _has_existing_note_id(notes: list[RawNote]) -> bool:
    for note in notes:
        if note._id is not None or _has_existing_note_id(note.children):
            return True
    return False


def _clone_raw(note: RawNote) -> RawNote:
    return RawNote.from_proto(note.to_proto())


def _clone_chart_events(events: ChartEvents) -> ChartEvents:
    from margrete_rpc.chart.events import BeatEvent, BpmEvent, NoteSpeedEvent, TimelineSpeedEvent

    return ChartEvents(
        bpm=[BpmEvent.from_proto(event.to_proto()) for event in events.bpm],
        beat=[BeatEvent.from_proto(event.to_proto()) for event in events.beat],
        til=[TimelineSpeedEvent.from_proto(event.to_proto()) for event in events.til],
        note_speed=[NoteSpeedEvent.from_proto(event.to_proto()) for event in events.note_speed],
    )


def _note_tree_sig(note: RawNote) -> bytes:
    return _strip_note_ids(note).to_proto().SerializeToString()


type IdStructure = tuple[int | None, tuple["IdStructure", ...]]


def _id_structure(note: RawNote) -> IdStructure:
    return (note._id, tuple(_id_structure(child) for child in note.children))


def _children_id_structure(note: RawNote) -> tuple[IdStructure, ...]:
    return tuple(_id_structure(child) for child in note.children)


def _append_scanned_note_diffs(
    request: messages_pb2.ApplyEditRequest,
    orig_notes: list[RawNote],
    final_notes: list[RawNote],
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
    orig_bpm = {int(event.t): event for event in orig_events.bpm}
    final_bpm = {int(event.t): event for event in final_events.bpm}
    for t in orig_bpm:
        if t not in final_bpm:
            request.bpm_ticks_delete.append(t)
    for t, event in final_bpm.items():
        if (
            t not in orig_bpm
            or event.to_proto().SerializeToString() != orig_bpm[t].to_proto().SerializeToString()
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

    orig_til = {(int(event.t), int(event.til)): event for event in orig_events.til}
    final_til = {(int(event.t), int(event.til)): event for event in final_events.til}
    for key in orig_til:
        if key not in final_til:
            t, til = key
            request.til_keys_delete.append(messages_pb2.TimelineSpeedKey(tick=t, timeline_id=til))
    for key, event in final_til.items():
        if (
            key not in orig_til
            or event.to_proto().SerializeToString() != orig_til[key].to_proto().SerializeToString()
        ):
            request.til_upsert.append(event.to_proto())

    orig_note_speed = {int(event.t): event for event in orig_events.note_speed}
    final_note_speed = {int(event.t): event for event in final_events.note_speed}
    for t in orig_note_speed:
        if t not in final_note_speed:
            request.note_speed_ticks_delete.append(t)
    for t, event in final_note_speed.items():
        if (
            t not in orig_note_speed
            or event.to_proto().SerializeToString()
            != orig_note_speed[t].to_proto().SerializeToString()
        ):
            request.note_speed_upsert.append(event.to_proto())


def _append_all_event_upserts(
    request: messages_pb2.ApplyEditRequest,
    events: ChartEvents,
) -> None:
    request.bpm_upsert.extend(event.to_proto() for event in events.bpm)
    request.beat_upsert.extend(event.to_proto() for event in events.beat)
    request.til_upsert.extend(event.to_proto() for event in events.til)
    request.note_speed_upsert.extend(event.to_proto() for event in events.note_speed)
