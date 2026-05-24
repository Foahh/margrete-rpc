from __future__ import annotations

from dataclasses import dataclass, field
from typing import overload

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model.chart_time import Pos, p2t as _p2t, t2p as _t2p
from margrete_rpc.model.event import (
    BeatEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
    _last_by_key,
)
from margrete_rpc.model.note import HLNote, LLNote, UnsupportedNoteTree, wrap_ll_note


@dataclass
class ChartEvents:
    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatEvent] = field(default_factory=list)
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

    def t2p(self, tick: int) -> Pos:
        return _t2p(tick, beat_events=self.events.beat)

    @overload
    def p2t(self, pos: Pos) -> int: ...

    @overload
    def p2t(self, bar: int, beat: int, offset: int) -> int: ...

    def p2t(
        self,
        pos_or_bar: Pos | int,
        beat: int | None = None,
        offset: int | None = None,
    ) -> int:
        if isinstance(pos_or_bar, Pos):
            if beat is not None or offset is not None:
                raise TypeError("p2t accepts either Pos or (bar, beat, offset), not both")
            return _p2t(pos_or_bar, beat_events=self.events.beat)
        if beat is None or offset is None:
            raise TypeError("p2t(bar, beat, offset) requires three int arguments")
        return _p2t(pos_or_bar, beat, offset, beat_events=self.events.beat)


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

    def t2p(self, tick: int) -> Pos:
        return _t2p(tick, beat_events=self.events.beat)

    @overload
    def p2t(self, pos: Pos) -> int: ...

    @overload
    def p2t(self, bar: int, beat: int, offset: int) -> int: ...

    def p2t(
        self,
        pos_or_bar: Pos | int,
        beat: int | None = None,
        offset: int | None = None,
    ) -> int:
        if isinstance(pos_or_bar, Pos):
            if beat is not None or offset is not None:
                raise TypeError("p2t accepts either Pos or (bar, beat, offset), not both")
            return _p2t(pos_or_bar, beat_events=self.events.beat)
        if beat is None or offset is None:
            raise TypeError("p2t(bar, beat, offset) requires three int arguments")
        return _p2t(pos_or_bar, beat, offset, beat_events=self.events.beat)


def _events_from_response(response: messages_pb2.BeginEditResponse) -> ChartEvents:
    return ChartEvents(
        bpm=[BpmEvent.from_proto(event) for event in response.bpm_events],
        beat=[BeatEvent.from_proto(event) for event in response.beat_change_events],
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
