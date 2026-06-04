from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model.chart_time import Position
from margrete_rpc.model.chart_time import p2t as _p2t
from margrete_rpc.model.chart_time import t2p as _t2p
from margrete_rpc.model.event import (
    BeatEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
    _last_by_key,
)
from margrete_rpc.model.note import MgNote, Note, UnsupportedNoteTree, wrap_mg_note


@dataclass
class ChartEvents:
    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatEvent] = field(default_factory=list)
    til: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed: list[NoteSpeedEvent] = field(default_factory=list)


@dataclass
class Chart:
    notes: list[Note] = field(default_factory=list)
    mg_notes: list[MgNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> Chart:
        notes: list[Note] = []
        mg_notes: list[MgNote] = []
        for proto in response.notes:
            mg_note = MgNote.from_proto(proto)
            try:
                notes.append(wrap_mg_note(mg_note))
            except UnsupportedNoteTree:
                mg_notes.append(mg_note)
        return cls(
            notes=notes,
            mg_notes=mg_notes,
            events=_events_from_response(response),
        )

    def t2p(self, tick: int) -> Position:
        return _t2p(tick, beat_events=self.events.beat)

    def p2t(self, bar: int, beat: int = 0, offset: int = 0) -> int:
        return _p2t(bar, beat, offset, beat_events=self.events.beat)


@dataclass
class MgChart:
    mg_notes: list[MgNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> MgChart:
        return cls(
            mg_notes=[MgNote.from_proto(note) for note in response.notes],
            events=_events_from_response(response),
        )

    def t2p(self, tick: int) -> Position:
        return _t2p(tick, beat_events=self.events.beat)

    def p2t(self, bar: int, beat: int = 0, offset: int = 0) -> int:
        return _p2t(bar, beat, offset, beat_events=self.events.beat)


def _events_from_response(response: messages_pb2.BeginEditResponse) -> ChartEvents:
    return ChartEvents(
        bpm=[BpmEvent.from_proto(event) for event in response.bpm_events],
        beat=[BeatEvent.from_proto(event) for event in response.beat_change_events],
        til=[TimelineSpeedEvent.from_proto(event) for event in response.timeline_speed_events],
        note_speed=[NoteSpeedEvent.from_proto(event) for event in response.note_speed_events],
    )


def normalize_event_operations(chart: Chart | MgChart) -> Chart | MgChart:
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
    if isinstance(chart, MgChart):
        return MgChart(mg_notes=chart.mg_notes, events=events)
    return Chart(notes=chart.notes, mg_notes=chart.mg_notes, events=events)
