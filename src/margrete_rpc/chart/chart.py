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
from margrete_rpc.chart.notes import Note, RawNote, UnsupportedNoteTree
from margrete_rpc.chart.notes.wrap import wrap_raw_note

type ChartNote = Note | RawNote
"""A note in a chart: either a typed :class:`Note` or a raw :class:`RawNote` tree.

Typed notes are produced by default; a :class:`RawNote` appears when the edit was opened
with ``raw_notes=True`` or when a note's structure is not recognised by the typed wrappers.
"""


@dataclass
class ChartEvents:
    """Timeline events of a chart, grouped by kind.

    Attributes:
        bpm: Tempo changes (:class:`BpmEvent`).
        beat: Time-signature changes (:class:`BeatEvent`); these drive position<->tick
            conversion.
        til: Timeline-speed events (:class:`TimelineSpeedEvent`).
        note_speed: Note-speed events (:class:`NoteSpeedEvent`).
    """

    bpm: list[BpmEvent] = field(default_factory=list)
    beat: list[BeatEvent] = field(default_factory=list)
    til: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed: list[NoteSpeedEvent] = field(default_factory=list)

    def normalized(self) -> ChartEvents:
        """Return a copy keeping only the last event for each duplicate key.

        Collapses events that share the same position (tick/bar) so each timeline slot
        holds a single event.
        """
        return ChartEvents(
            bpm=_last_by_key(self.bpm, lambda event: event.t),
            beat=_last_by_key(self.beat, lambda event: event.bar),
            til=_last_by_key(
                self.til,
                lambda event: (event.t, event.til),
            ),
            note_speed=_last_by_key(self.note_speed, lambda event: event.t),
        )


@dataclass
class Chart:
    """The notes and timeline events of the chart being edited.

    Obtained via :attr:`EditTransaction.chart`. Append, remove, or mutate items in
    :attr:`notes` to describe an edit; :attr:`events` holds the read-mostly timeline.

    Attributes:
        notes: The chart's notes (typed :class:`Note` objects, or :class:`RawNote`).
        events: The chart's :class:`ChartEvents`.
    """

    notes: list[ChartNote] = field(default_factory=list)
    events: ChartEvents = field(default_factory=ChartEvents)

    @classmethod
    def from_begin_edit_response(
        cls,
        response: messages_pb2.BeginEditResponse,
        *,
        raw_notes: bool = False,
    ) -> Chart:
        """Build a :class:`Chart` from a begin-edit RPC response.

        Args:
            response: The protobuf payload returned when an edit is opened.
            raw_notes: Keep every note as a :class:`RawNote` instead of wrapping into typed
                notes. Notes whose structure is unsupported stay raw regardless.
        """
        notes: list[ChartNote] = []
        for proto in response.notes:
            raw_note = RawNote.from_proto(proto)
            if raw_notes:
                notes.append(raw_note)
                continue
            try:
                notes.append(wrap_raw_note(raw_note))
            except UnsupportedNoteTree:
                notes.append(raw_note)
        return cls(
            notes=notes,
            events=_events_from_response(response),
        )

    def normalized_events(self) -> Chart:
        """Return a copy with the same notes but :meth:`ChartEvents.normalized` events."""
        return Chart(notes=self.notes, events=self.events.normalized())


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
