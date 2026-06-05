from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart.events import (
    BeatEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
)
from margrete_rpc.chart.note import Node, Note, UnsupportedNoteTree, wrap_node


@dataclass
class ChartEvents:
    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatEvent] = field(default_factory=list)
    til: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed: list[NoteSpeedEvent] = field(default_factory=list)


@dataclass
class Chart:
    notes: list[Note] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(
        cls,
        response: messages_pb2.BeginEditResponse,
        *,
        raw: bool = False,
    ) -> Chart:
        if raw:
            return cls(
                nodes=[Node.from_proto(note) for note in response.notes],
                events=_events_from_response(response),
            )

        notes: list[Note] = []
        nodes: list[Node] = []
        for proto in response.notes:
            node = Node.from_proto(proto)
            try:
                notes.append(wrap_node(node))
            except UnsupportedNoteTree:
                nodes.append(node)
        return cls(
            notes=notes,
            nodes=nodes,
            events=_events_from_response(response),
        )


def _last_by_key[T, K: Hashable](items: list[T], key: Callable[[T], K]) -> list[T]:
    by_key: dict[K, T] = {}
    for item in items:
        by_key[key(item)] = item
    return list(by_key.values())


def _events_from_response(response: messages_pb2.BeginEditResponse) -> ChartEvents:
    return ChartEvents(
        bpm=[BpmEvent.from_proto(event) for event in response.bpm_events],
        beat=[BeatEvent.from_proto(event) for event in response.beat_change_events],
        til=[TimelineSpeedEvent.from_proto(event) for event in response.timeline_speed_events],
        note_speed=[NoteSpeedEvent.from_proto(event) for event in response.note_speed_events],
    )


def normalize_event_operations(chart: Chart) -> Chart:
    ev = chart.events
    events = ChartEvents(
        bpm=_last_by_key(ev.bpm, lambda event: event.t),
        beat=_last_by_key(ev.beat, lambda event: event.bar),
        til=_last_by_key(
            ev.til,
            lambda event: (event.t, event.til),
        ),
        note_speed=_last_by_key(ev.note_speed, lambda event: event.t),
    )
    return Chart(notes=chart.notes, nodes=chart.nodes, events=events)
