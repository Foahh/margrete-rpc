from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TypeVar

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class NoteType(IntEnum):
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
    NONE = messages_pb2.LONG_ATTR_NONE
    BEGIN = messages_pb2.LONG_ATTR_BEGIN
    STEP = messages_pb2.LONG_ATTR_STEP
    CONTROL = messages_pb2.LONG_ATTR_CONTROL
    CURVE_CONTROL = messages_pb2.LONG_ATTR_CURVE_CONTROL
    END = messages_pb2.LONG_ATTR_END
    END_NOACT = messages_pb2.LONG_ATTR_END_NOACT


class Direction(IntEnum):
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
    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


@dataclass
class Note:
    type: NoteType = NoteType.UNKNOWN
    long_attr: LongAttr = LongAttr.NONE
    direction: Direction = Direction.NONE
    ex_attr: ExAttr = ExAttr.NONE
    variation_id: int = 0
    x: int = 0
    width: int = 0
    height: int = 0
    tick: int = 0
    timeline_id: int = 0
    option_value: int = 0
    children: list[Note] = field(default_factory=list)
    id: int | None = None

    @classmethod
    def tap(cls, *, tick: int, x: int, width: int = 1, **kwargs) -> Note:
        return cls(type=NoteType.TAP, tick=tick, x=x, width=width, **kwargs)

    @classmethod
    def from_proto(cls, proto: messages_pb2.Note) -> Note:
        return cls(
            id=proto.id if proto.HasField("id") else None,
            type=NoteType(proto.type),
            long_attr=LongAttr(proto.long_attr),
            direction=Direction(proto.direction),
            ex_attr=ExAttr(proto.ex_attr),
            variation_id=proto.variation_id,
            x=proto.x,
            width=proto.width,
            height=proto.height,
            tick=proto.tick,
            timeline_id=proto.timeline_id,
            option_value=proto.option_value,
            children=[cls.from_proto(child) for child in proto.children],
        )

    def to_proto(self) -> messages_pb2.Note:
        proto = messages_pb2.Note(
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
        )
        if self.id is not None:
            proto.id = self.id
        proto.children.extend(child.to_proto() for child in self.children)
        return proto


@dataclass(frozen=True)
class BpmEvent:
    tick: int
    bpm: float

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.tick, bpm=self.bpm)


@dataclass(frozen=True)
class BeatChangeEvent:
    bar: int
    beats_per_bar: int
    beat_unit: int

    def to_proto(self) -> messages_pb2.BeatChangeEvent:
        return messages_pb2.BeatChangeEvent(
            bar=self.bar,
            beats_per_bar=self.beats_per_bar,
            beat_unit=self.beat_unit,
        )


@dataclass(frozen=True)
class TimelineSpeedEvent:
    tick: int
    timeline_id: int
    speed: float

    def to_proto(self) -> messages_pb2.TimelineSpeedEvent:
        return messages_pb2.TimelineSpeedEvent(
            tick=self.tick,
            timeline_id=self.timeline_id,
            speed=self.speed,
        )


@dataclass(frozen=True)
class NoteSpeedEvent:
    tick: int
    speed: float

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.tick, speed=self.speed)


@dataclass
class Chart:
    notes: list[Note] = field(default_factory=list)
    bpm_events: list[BpmEvent] = field(default_factory=list)
    beat_change_events: list[BeatChangeEvent] = field(default_factory=list)
    timeline_speed_events: list[TimelineSpeedEvent] = field(default_factory=list)
    note_speed_events: list[NoteSpeedEvent] = field(default_factory=list)

    @classmethod
    def from_begin_edit_response(cls, response: messages_pb2.BeginEditResponse) -> Chart:
        return cls(notes=[Note.from_proto(note) for note in response.notes])


T = TypeVar("T")


def _last_by_key(items: list[T], key) -> list[T]:
    by_key = {}
    for item in items:
        by_key[key(item)] = item
    return list(by_key.values())


def normalize_event_operations(chart: Chart) -> Chart:
    return Chart(
        notes=chart.notes,
        bpm_events=_last_by_key(chart.bpm_events, lambda event: event.tick),
        beat_change_events=_last_by_key(chart.beat_change_events, lambda event: event.bar),
        timeline_speed_events=_last_by_key(
            chart.timeline_speed_events,
            lambda event: (event.tick, event.timeline_id),
        ),
        note_speed_events=_last_by_key(chart.note_speed_events, lambda event: event.tick),
    )
