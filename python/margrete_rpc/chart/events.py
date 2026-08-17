from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from margrete_rpc._proto import messages_pb2

if TYPE_CHECKING:
    from .time import Position, PositionLike


def _resolve_event_tick(value: int | PositionLike) -> int:
    from .time import resolve_tick

    return resolve_tick(value)


def _event_tick_to_pos(tick: int) -> Position:
    from .time import tick_to_pos

    return tick_to_pos(tick)


class _TickedEvent:
    __slots__ = ("_t",)

    _t: int

    @property
    def t(self) -> int:
        return self._t

    @t.setter
    def t(self, value: int | PositionLike) -> None:
        self._t = _resolve_event_tick(value)

    @property
    def p(self) -> Position:
        return _event_tick_to_pos(self._t)


class BpmEvent(_TickedEvent):
    """A tempo change.

    Attributes:
        t: Tick or position at which the tempo takes effect.
        p: Timing as a ``(bar, beat, offset)`` :class:`Position`; read-only view of ``t``.
        bpm: Beats per minute from this tick onward.
    """

    __slots__ = ("bpm",)

    bpm: float

    def __init__(self, t: int | PositionLike, bpm: float) -> None:
        self.t = t
        self.bpm = bpm

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BpmEvent):
            return NotImplemented
        return self.t == other.t and self.bpm == other.bpm

    def __repr__(self) -> str:
        return f"BpmEvent(t={self.t!r}, bpm={self.bpm!r})"

    @classmethod
    def from_proto(cls, proto: messages_pb2.BpmEvent) -> BpmEvent:
        return cls(t=proto.tick, bpm=proto.bpm)

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.t, bpm=self.bpm)


@dataclass(slots=True)
class BeatEvent:
    """A time-signature change, anchored at a bar.

    The active set of beat events defines how ``(bar, beat, offset)`` positions map to
    absolute ticks (see :func:`margrete_rpc.chart.pos_to_tick`).

    Attributes:
        bar: Zero-based bar index from which this signature applies.
        beats_per_bar: Numerator of the time signature (beats per measure).
        beat_unit: Denominator of the time signature (note value of one beat, e.g. 4).
    """

    bar: int
    beats_per_bar: int
    beat_unit: int

    @classmethod
    def from_proto(cls, proto: messages_pb2.BeatChangeEvent) -> BeatEvent:
        return cls(bar=proto.bar, beats_per_bar=proto.beats_per_bar, beat_unit=proto.beat_unit)

    def to_proto(self) -> messages_pb2.BeatChangeEvent:
        return messages_pb2.BeatChangeEvent(
            bar=self.bar,
            beats_per_bar=self.beats_per_bar,
            beat_unit=self.beat_unit,
        )


class TimelineSpeedEvent(_TickedEvent):
    """A scroll-speed change on a specific timeline.

    Attributes:
        til: Timeline id the speed applies to.
        t: Tick or position at which the speed takes effect.
        p: Timing as a ``(bar, beat, offset)`` :class:`Position`; read-only view of ``t``.
        speed: Scroll-speed multiplier from this tick onward.
    """

    __slots__ = ("til", "speed")

    til: int
    speed: float

    def __init__(self, til: int, t: int | PositionLike, speed: float) -> None:
        self.til = til
        self.t = t
        self.speed = speed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimelineSpeedEvent):
            return NotImplemented
        return self.til == other.til and self.t == other.t and self.speed == other.speed

    def __repr__(self) -> str:
        return f"TimelineSpeedEvent(til={self.til!r}, t={self.t!r}, speed={self.speed!r})"

    @classmethod
    def from_proto(cls, proto: messages_pb2.TimelineSpeedEvent) -> TimelineSpeedEvent:
        return cls(t=proto.tick, til=proto.timeline_id, speed=proto.speed)

    def to_proto(self) -> messages_pb2.TimelineSpeedEvent:
        return messages_pb2.TimelineSpeedEvent(
            tick=self.t,
            timeline_id=self.til,
            speed=self.speed,
        )


class NoteSpeedEvent(_TickedEvent):
    """A note-speed change.

    Attributes:
        t: Tick or position at which the speed takes effect.
        p: Timing as a ``(bar, beat, offset)`` :class:`Position`; read-only view of ``t``.
        speed: Note-speed multiplier from this tick onward.
    """

    __slots__ = ("speed",)

    speed: float

    def __init__(self, t: int | PositionLike, speed: float) -> None:
        self.t = t
        self.speed = speed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoteSpeedEvent):
            return NotImplemented
        return self.t == other.t and self.speed == other.speed

    def __repr__(self) -> str:
        return f"NoteSpeedEvent(t={self.t!r}, speed={self.speed!r})"

    @classmethod
    def from_proto(cls, proto: messages_pb2.NoteSpeedEvent) -> NoteSpeedEvent:
        return cls(t=proto.tick, speed=proto.speed)

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.t, speed=self.speed)
