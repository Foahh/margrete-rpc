from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model.event import (
    BeatChangeEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
    _last_by_key,
)
from margrete_rpc.model.hl_note import HLNote, UnsupportedNoteTree, wrap_ll_note
from margrete_rpc.model.ll_note import LLNote


@dataclass
class ChartEvents:
    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatChangeEvent] = field(default_factory=list)
    til: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed: list[NoteSpeedEvent] = field(default_factory=list)


@dataclass
class Chart:
    notes: list[HLNote] = field(default_factory=list)
    raw_notes: list[LLNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> Chart:
        notes: list[HLNote] = []
        raw_notes: list[LLNote] = []
        for proto in response.notes:
            ll_note = LLNote.from_proto(proto)
            try:
                notes.append(wrap_ll_note(ll_note))
            except UnsupportedNoteTree:
                raw_notes.append(ll_note)
        return cls(
            notes=notes,
            raw_notes=raw_notes,
            events=_events_from_response(response),
        )


@dataclass
class LLChart:
    raw_notes: list[LLNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> LLChart:
        return cls(
            raw_notes=[LLNote.from_proto(note) for note in response.notes],
            events=_events_from_response(response),
        )


def _events_from_response(response: messages_pb2.BeginEditResponse) -> ChartEvents:
    return ChartEvents(
        bpm=[BpmEvent.from_proto(event) for event in response.bpm_events],
        beat=[BeatChangeEvent.from_proto(event) for event in response.beat_change_events],
        til=[TimelineSpeedEvent.from_proto(event) for event in response.timeline_speed_events],
        note_speed=[NoteSpeedEvent.from_proto(event) for event in response.note_speed_events],
    )


def normalize_event_operations(chart: Chart | LLChart) -> Chart | LLChart:
    ev = chart.events
    events = ChartEvents(
        bpm=_last_by_key(ev.bpm, lambda event: event.tick),
        beat=_last_by_key(ev.beat, lambda event: event.bar),
        til=_last_by_key(
            ev.til,
            lambda event: (event.tick, event.timeline_id),
        ),
        note_speed=_last_by_key(ev.note_speed, lambda event: event.tick),
    )
    if isinstance(chart, LLChart):
        return LLChart(raw_notes=chart.raw_notes, events=events)
    return Chart(notes=chart.notes, raw_notes=chart.raw_notes, events=events)
