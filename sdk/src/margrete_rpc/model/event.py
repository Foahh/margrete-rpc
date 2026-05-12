from __future__ import annotations

from dataclasses import dataclass

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


@dataclass
class BpmEvent:
    tick: int
    bpm: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.BpmEvent) -> BpmEvent:
        return cls(tick=proto.tick, bpm=proto.bpm)

    def to_proto(self) -> messages_pb2.BpmEvent:
        return messages_pb2.BpmEvent(tick=self.tick, bpm=self.bpm)


@dataclass
class BeatChangeEvent:
    bar: int
    beats_per_bar: int
    beat_unit: int

    @classmethod
    def from_proto(cls, proto: messages_pb2.BeatChangeEvent) -> BeatChangeEvent:
        return cls(bar=proto.bar, beats_per_bar=proto.beats_per_bar, beat_unit=proto.beat_unit)

    def to_proto(self) -> messages_pb2.BeatChangeEvent:
        return messages_pb2.BeatChangeEvent(
            bar=self.bar,
            beats_per_bar=self.beats_per_bar,
            beat_unit=self.beat_unit,
        )


@dataclass
class TimelineSpeedEvent:
    timeline_id: int
    tick: int
    speed: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.TimelineSpeedEvent) -> TimelineSpeedEvent:
        return cls(tick=proto.tick, timeline_id=proto.timeline_id, speed=proto.speed)

    def to_proto(self) -> messages_pb2.TimelineSpeedEvent:
        return messages_pb2.TimelineSpeedEvent(
            tick=self.tick,
            timeline_id=self.timeline_id,
            speed=self.speed,
        )


@dataclass
class NoteSpeedEvent:
    tick: int
    speed: float

    @classmethod
    def from_proto(cls, proto: messages_pb2.NoteSpeedEvent) -> NoteSpeedEvent:
        return cls(tick=proto.tick, speed=proto.speed)

    def to_proto(self) -> messages_pb2.NoteSpeedEvent:
        return messages_pb2.NoteSpeedEvent(tick=self.tick, speed=self.speed)


def _last_by_key[T](items: list[T], key) -> list[T]:
    by_key = {}
    for item in items:
        by_key[key(item)] = item
    return list(by_key.values())
