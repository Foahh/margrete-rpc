from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TypeVar

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

__all__ = [
    "BeatChangeEvent",
    "BpmEvent",
    "Chart",
    "Direction",
    "ExAttr",
    "LongAttr",
    "Note",
    "NoteSpeedEvent",
    "NoteType",
    "TimelineSpeedEvent",
    "normalize_event_operations",
]


class NoteType(IntEnum):
    """Chart note kinds; values match :class:`messages_pb2.NoteType`."""

    UNKNOWN = messages_pb2.NOTE_TYPE_UNKNOWN
    TAP = messages_pb2.NOTE_TYPE_TAP
    EXTAP = messages_pb2.NOTE_TYPE_EXTAP
    FLICK = messages_pb2.NOTE_TYPE_FLICK
    DAMAGE = messages_pb2.NOTE_TYPE_DAMAGE
    HOLD = messages_pb2.NOTE_TYPE_HOLD
    SLIDE = messages_pb2.NOTE_TYPE_SLIDE
    AIR = messages_pb2.NOTE_TYPE_AIR
    AIRHOLD = messages_pb2.NOTE_TYPE_AIRHOLD
    AIRSLIDE = messages_pb2.NOTE_TYPE_AIRSLIDE
    AIRCRUSH = messages_pb2.NOTE_TYPE_AIRCRUSH
    CLICK = messages_pb2.NOTE_TYPE_CLICK


class LongAttr(IntEnum):
    """Long-note segment role; values match :class:`messages_pb2.LongAttr`."""

    NONE = messages_pb2.LONG_ATTR_NONE
    BEGIN = messages_pb2.LONG_ATTR_BEGIN
    STEP = messages_pb2.LONG_ATTR_STEP
    CONTROL = messages_pb2.LONG_ATTR_CONTROL
    CURVE_CONTROL = messages_pb2.LONG_ATTR_CURVE_CONTROL
    END = messages_pb2.LONG_ATTR_END
    END_NOACT = messages_pb2.LONG_ATTR_END_NOACT


class Direction(IntEnum):
    """Note facing / motion hint; values match :class:`messages_pb2.Direction`."""

    NONE = messages_pb2.DIRECTION_NONE
    AUTO = messages_pb2.DIRECTION_AUTO
    UP = messages_pb2.DIRECTION_UP
    DOWN = messages_pb2.DIRECTION_DOWN
    CENTER = messages_pb2.DIRECTION_CENTER
    LEFT = messages_pb2.DIRECTION_LEFT
    RIGHT = messages_pb2.DIRECTION_RIGHT
    UPLEFT = messages_pb2.DIRECTION_UPLEFT
    UPRIGHT = messages_pb2.DIRECTION_UPRIGHT
    DOWNLEFT = messages_pb2.DIRECTION_DOWNLEFT
    DOWNRIGHT = messages_pb2.DIRECTION_DOWNRIGHT
    ROTATE_LEFT = messages_pb2.DIRECTION_ROTATE_LEFT
    ROTATE_RIGHT = messages_pb2.DIRECTION_ROTATE_RIGHT
    INOUT = messages_pb2.DIRECTION_INOUT
    OUTIN = messages_pb2.DIRECTION_OUTIN


class ExAttr(IntEnum):
    """Extra note flags; values match :class:`messages_pb2.ExAttr`."""

    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


@dataclass
class BpmEvent:
    tick: int
    bpm: float

    @classmethod
    def from_proto(cls, pb: messages_pb2.BpmEvent) -> BpmEvent:
        return cls(tick=pb.tick, bpm=pb.bpm)

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.tick, bpm=self.bpm)


@dataclass
class BeatChangeEvent:
    bar: int
    beats_per_bar: int
    beat_unit: int

    @classmethod
    def from_proto(cls, pb: messages_pb2.BeatChangeEvent) -> BeatChangeEvent:
        return cls(bar=pb.bar, beats_per_bar=pb.beats_per_bar, beat_unit=pb.beat_unit)

    def to_proto(self) -> messages_pb2.BeatChangeEvent:
        return messages_pb2.BeatChangeEvent(
            bar=self.bar, beats_per_bar=self.beats_per_bar, beat_unit=self.beat_unit
        )


@dataclass
class TimelineSpeedEvent:
    tick: int
    timeline_id: int
    speed: float

    @classmethod
    def from_proto(cls, pb: messages_pb2.TimelineSpeedEvent) -> TimelineSpeedEvent:
        return cls(tick=pb.tick, timeline_id=pb.timeline_id, speed=pb.speed)

    def to_proto(self) -> messages_pb2.TimelineSpeedEvent:
        return messages_pb2.TimelineSpeedEvent(
            tick=self.tick, timeline_id=self.timeline_id, speed=self.speed
        )


@dataclass
class NoteSpeedEvent:
    tick: int
    speed: float

    @classmethod
    def from_proto(cls, pb: messages_pb2.NoteSpeedEvent) -> NoteSpeedEvent:
        return cls(tick=pb.tick, speed=pb.speed)

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.tick, speed=self.speed)


@dataclass
class Note:
    type: NoteType
    long_attr: LongAttr
    direction: Direction
    ex_attr: ExAttr
    variation_id: int
    x: int
    width: int
    height: int
    tick: int
    timeline_id: int
    option_value: int
    children: list[Note] = field(default_factory=list)
    id: int | None = None

    @classmethod
    def tap(
        cls,
        tick: int,
        *,
        x: int = 0,
        width: int = 1,
        height: int = 1,
        timeline_id: int = 0,
        variation_id: int = 0,
        option_value: int = 0,
        id: int | None = None,
        children: list[Note] | None = None,
    ) -> Note:
        return cls(
            type=NoteType.TAP,
            long_attr=LongAttr.NONE,
            direction=Direction.NONE,
            ex_attr=ExAttr.NONE,
            variation_id=variation_id,
            x=x,
            width=width,
            height=height,
            tick=tick,
            timeline_id=timeline_id,
            option_value=option_value,
            children=list(children) if children is not None else [],
            id=id,
        )

    @classmethod
    def from_proto(cls, pb: messages_pb2.Note) -> Note:
        return cls(
            type=NoteType(pb.type),
            long_attr=LongAttr(pb.long_attr),
            direction=Direction(pb.direction),
            ex_attr=ExAttr(pb.ex_attr),
            variation_id=pb.variation_id,
            x=pb.x,
            width=pb.width,
            height=pb.height,
            tick=pb.tick,
            timeline_id=pb.timeline_id,
            option_value=pb.option_value,
            children=[cls.from_proto(c) for c in pb.children],
            id=pb.id if pb.HasField("id") else None,
        )

    def to_proto(self) -> messages_pb2.Note:
        n = messages_pb2.Note(
            type=int(self.type),
            long_attr=int(self.long_attr),
            direction=int(self.direction),
            ex_attr=int(self.ex_attr),
            variation_id=self.variation_id,
            x=self.x,
            width=self.width,
            height=self.height,
            tick=self.tick,
            timeline_id=self.timeline_id,
            option_value=self.option_value,
            children=[c.to_proto() for c in self.children],
        )
        if self.id is not None:
            n.id = self.id
        return n


@dataclass
class Chart:
    current_tick: int
    notes: list[Note]
    bpm_events: list[BpmEvent] = field(default_factory=list)
    beat_change_events: list[BeatChangeEvent] = field(default_factory=list)
    timeline_speed_events: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed_events: list[NoteSpeedEvent] = field(default_factory=list)

    @classmethod
    def from_begin_edit_response(cls, pb: messages_pb2.BeginEditResponse) -> Chart:
        return cls(
            current_tick=pb.current_tick,
            notes=[Note.from_proto(n) for n in pb.notes],
        )


_K = TypeVar("_K")
_V = TypeVar("_V")


def _last_by_key(pairs: Iterable[tuple[_K, _V]]) -> dict[_K, _V]:
    """Return a mapping of key → value, keeping the last value for each key."""
    out: dict[_K, _V] = {}
    for k, v in pairs:
        out[k] = v
    return out


def normalize_event_operations(
    bpm_events: Iterable[BpmEvent],
    beat_change_events: Iterable[BeatChangeEvent],
    timeline_speed_events: Iterable[TimelineSpeedEvent],
    note_speed_events: Iterable[NoteSpeedEvent],
) -> tuple[list[BpmEvent], list[BeatChangeEvent], list[TimelineSpeedEvent], list[NoteSpeedEvent]]:
    """Collapse duplicate event keys (last wins) and return time-ordered lists."""
    bpm_map = _last_by_key((e.tick, e) for e in bpm_events)
    beat_map = _last_by_key((e.bar, e) for e in beat_change_events)
    timeline_map = _last_by_key(((e.tick, e.timeline_id), e) for e in timeline_speed_events)
    note_speed_map = _last_by_key((e.tick, e) for e in note_speed_events)

    nb = [bpm_map[t] for t in sorted(bpm_map)]
    nbc = [beat_map[b] for b in sorted(beat_map)]
    nt = [timeline_map[k] for k in sorted(timeline_map)]
    nn = [note_speed_map[t] for t in sorted(note_speed_map)]

    return nb, nbc, nt, nn
