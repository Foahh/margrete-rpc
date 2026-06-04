from __future__ import annotations

from dataclasses import dataclass

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


@dataclass
class BpmEvent:
    t: int
    bpm: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.BpmEvent) -> BpmEvent:
        return cls(t=proto.tick, bpm=proto.bpm)

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.t, bpm=self.bpm)


@dataclass
class BeatEvent:
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
    t: int
    speed: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.NoteSpeedEvent) -> NoteSpeedEvent:
        return cls(t=proto.tick, speed=proto.speed)

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.t, speed=self.speed)


def _last_by_key[T](items: list[T], key) -> list[T]:
    by_key = {}
    for item in items:
        by_key[key(item)] = item
    return list(by_key.values())
