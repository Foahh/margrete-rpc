from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model.ll.event import (
    BeatChangeEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
    _last_by_key,
)
from margrete_rpc.model.ll.note import Note


@dataclass
class ChartEvents:
    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatChangeEvent] = field(default_factory=list)
    til: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed: list[NoteSpeedEvent] = field(default_factory=list)


@dataclass
class Chart:
    notes: list[Note] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> Chart:
        return cls(
            notes=[Note.from_proto(note) for note in response.notes],
            events=ChartEvents(
                bpm=[BpmEvent.from_proto(event) for event in response.bpm_events],
                beat=[
                    BeatChangeEvent.from_proto(event) for event in response.beat_change_events
                ],
                til=[
                    TimelineSpeedEvent.from_proto(event)
                    for event in response.timeline_speed_events
                ],
                note_speed=[
                    NoteSpeedEvent.from_proto(event) for event in response.note_speed_events
                ],
            ),
        )


def normalize_event_operations(chart: Chart) -> Chart:
    ev = chart.events
    return Chart(
        notes=chart.notes,
        events=ChartEvents(
            bpm=_last_by_key(ev.bpm, lambda event: event.tick),
            beat=_last_by_key(ev.beat, lambda event: event.bar),
            til=_last_by_key(
                ev.til,
                lambda event: (event.tick, event.timeline_id),
            ),
            note_speed=_last_by_key(ev.note_speed, lambda event: event.tick),
        ),
    )
