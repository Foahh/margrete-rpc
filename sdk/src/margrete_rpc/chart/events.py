from __future__ import annotations

from dataclasses import dataclass

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


@dataclass
class BpmEvent:
    """A tempo change.

    Attributes:
        t: Tick at which the tempo takes effect.
        bpm: Beats per minute from this tick onward.
    """

    t: int
    bpm: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.BpmEvent) -> BpmEvent:
        return cls(t=proto.tick, bpm=proto.bpm)

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.t, bpm=self.bpm)


@dataclass
class BeatEvent:
    """A time-signature change, anchored at a bar.

    The active set of beat events defines how ``(bar, beat, offset)`` positions map to
    absolute ticks (see :func:`margrete_rpc.chart.p2t`).

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


@dataclass
class TimelineSpeedEvent:
    """A scroll-speed change on a specific timeline.

    Attributes:
        til: Timeline id the speed applies to.
        t: Tick at which the speed takes effect.
        speed: Scroll-speed multiplier from this tick onward.
    """

    til: int
    t: int
    speed: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.TimelineSpeedEvent) -> TimelineSpeedEvent:
        return cls(t=proto.tick, til=proto.timeline_id, speed=proto.speed)

    def to_proto(self) -> messages_pb2.TimelineSpeedEvent:
        return messages_pb2.TimelineSpeedEvent(
            tick=self.t,
            timeline_id=self.til,
            speed=self.speed,
        )


@dataclass
class NoteSpeedEvent:
    """A note-speed change.

    Attributes:
        t: Tick at which the speed takes effect.
        speed: Note-speed multiplier from this tick onward.
    """

    t: int
    speed: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.NoteSpeedEvent) -> NoteSpeedEvent:
        return cls(t=proto.tick, speed=proto.speed)

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.t, speed=self.speed)
