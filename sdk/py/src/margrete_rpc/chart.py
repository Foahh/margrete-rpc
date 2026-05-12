from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol, runtime_checkable

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class Appendable(Protocol):
    def to_append_item(self) -> messages_pb2.AppendItem: ...

    def shifted(self, tick_offset: int) -> Appendable: ...


@runtime_checkable
class Note(Appendable, Protocol):
    def to_note_object(self) -> messages_pb2.NoteObject: ...


def _validate_base(tick: int, lane: int, width: int) -> None:
    if tick < 0:
        raise ValueError("tick must be non-negative")
    if width <= 0:
        raise ValueError("width must be positive")


def _lane_note(tick: int, lane: int, width: int, timeline: int) -> messages_pb2.LaneNote:
    _validate_base(tick, lane, width)
    return messages_pb2.LaneNote(tick=tick, lane=lane, width=width, timeline=timeline)


@dataclass(frozen=True)
class Tap:
    tick: int
    lane: int
    width: int = 1
    timeline: int = 0

    def to_note_object(self) -> messages_pb2.NoteObject:
        return messages_pb2.NoteObject(
            tap=messages_pb2.Tap(base=_lane_note(self.tick, self.lane, self.width, self.timeline))
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> Tap:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class ExTap:
    tick: int
    lane: int
    width: int = 1
    timeline: int = 0
    direction: int = messages_pb2.DIRECTION_UP

    def to_note_object(self) -> messages_pb2.NoteObject:
        return messages_pb2.NoteObject(
            ex_tap=messages_pb2.ExTap(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                direction=self.direction,
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> ExTap:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class Flick(Tap):
    def to_note_object(self) -> messages_pb2.NoteObject:
        return messages_pb2.NoteObject(
            flick=messages_pb2.Flick(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline)
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())


@dataclass(frozen=True)
class Damage(Tap):
    def to_note_object(self) -> messages_pb2.NoteObject:
        return messages_pb2.NoteObject(
            damage=messages_pb2.Damage(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline)
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())


@dataclass(frozen=True)
class Hold:
    tick: int
    lane: int
    width: int
    duration: int
    timeline: int = 0

    def to_note_object(self) -> messages_pb2.NoteObject:
        _validate_base(self.tick, self.lane, self.width)
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        return messages_pb2.NoteObject(
            hold=messages_pb2.Hold(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                duration=self.duration,
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> Hold:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class SlidePoint:
    dt: int
    lane: int
    width: int = 1
    attr: int = messages_pb2.LONG_ATTR_CONTROL


@dataclass(frozen=True)
class Slide:
    tick: int
    lane: int
    width: int
    points: list[SlidePoint]
    timeline: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))

    def to_note_object(self) -> messages_pb2.NoteObject:
        _validate_base(self.tick, self.lane, self.width)
        if len(self.points) < 2:
            raise ValueError("slide requires at least two points")
        return messages_pb2.NoteObject(
            slide=messages_pb2.Slide(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                points=[
                    messages_pb2.SlidePoint(
                        dt=point.dt,
                        lane=point.lane,
                        width=point.width,
                        attr=point.attr,
                    )
                    for point in self.points
                ],
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> Slide:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class Air:
    tick: int
    lane: int
    width: int = 1
    timeline: int = 0
    direction: int = messages_pb2.DIRECTION_UP
    ex_attr: int = messages_pb2.EX_ATTR_NONE

    def to_note_object(self) -> messages_pb2.NoteObject:
        return messages_pb2.NoteObject(
            air=messages_pb2.Air(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                direction=self.direction,
                ex_attr=self.ex_attr,
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> Air:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class AirHold:
    tick: int
    lane: int
    width: int
    duration: int
    height: int
    timeline: int = 0

    def to_note_object(self) -> messages_pb2.NoteObject:
        _validate_base(self.tick, self.lane, self.width)
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        return messages_pb2.NoteObject(
            air_hold=messages_pb2.AirHold(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                duration=self.duration,
                height=self.height,
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> AirHold:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class AirSlidePoint:
    dt: int
    lane: int
    height: int
    attr: int = messages_pb2.LONG_ATTR_CONTROL


@dataclass(frozen=True)
class AirSlide:
    tick: int
    lane: int
    width: int
    points: list[AirSlidePoint]
    timeline: int = 0
    air_direction: int = messages_pb2.DIRECTION_UP
    air_ex_attr: int = messages_pb2.EX_ATTR_NONE

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))

    def to_note_object(self) -> messages_pb2.NoteObject:
        _validate_base(self.tick, self.lane, self.width)
        if len(self.points) < 2:
            raise ValueError("air slide requires at least two points")
        return messages_pb2.NoteObject(
            air_slide=messages_pb2.AirSlide(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                air_direction=self.air_direction,
                air_ex_attr=self.air_ex_attr,
                points=[
                    messages_pb2.AirSlidePoint(
                        dt=point.dt,
                        lane=point.lane,
                        height=point.height,
                        attr=point.attr,
                    )
                    for point in self.points
                ],
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> AirSlide:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class AirCrushPoint:
    dt: int
    lane: int
    width: int
    height: int
    attr: int = messages_pb2.LONG_ATTR_CONTROL


@dataclass(frozen=True)
class AirCrush:
    tick: int
    lane: int
    width: int
    points: list[AirCrushPoint]
    timeline: int = 0
    variation_id: int = 0
    option_value: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))

    def to_note_object(self) -> messages_pb2.NoteObject:
        _validate_base(self.tick, self.lane, self.width)
        if len(self.points) < 2:
            raise ValueError("air crush requires at least two points")
        return messages_pb2.NoteObject(
            air_crush=messages_pb2.AirCrush(
                base=_lane_note(self.tick, self.lane, self.width, self.timeline),
                variation_id=self.variation_id,
                option_value=self.option_value,
                points=[
                    messages_pb2.AirCrushPoint(
                        dt=point.dt,
                        lane=point.lane,
                        width=point.width,
                        height=point.height,
                        attr=point.attr,
                    )
                    for point in self.points
                ],
            )
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(note=self.to_note_object())

    def shifted(self, tick_offset: int) -> AirCrush:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class BpmEvent:
    tick: int
    bpm: float

    def to_append_item(self) -> messages_pb2.AppendItem:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        if self.bpm <= 0:
            raise ValueError("bpm must be positive")
        return messages_pb2.AppendItem(
            event=messages_pb2.EventObject(bpm=messages_pb2.BpmEvent(tick=self.tick, bpm=self.bpm))
        )

    def shifted(self, tick_offset: int) -> BpmEvent:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class BeatEvent:
    bar: int
    beats_per_bar: int = 4
    beat_unit: int = 4

    def to_append_item(self) -> messages_pb2.AppendItem:
        if self.bar < 0:
            raise ValueError("bar must be non-negative")
        if self.beats_per_bar <= 0 or self.beat_unit <= 0:
            raise ValueError("beat values must be positive")
        return messages_pb2.AppendItem(
            event=messages_pb2.EventObject(
                beat=messages_pb2.BeatEvent(
                    bar=self.bar,
                    beats_per_bar=self.beats_per_bar,
                    beat_unit=self.beat_unit,
                )
            )
        )

    def shifted(self, tick_offset: int) -> BeatEvent:
        return self


@dataclass(frozen=True)
class ScrollSpeedEvent:
    tick: int
    timeline: int
    speed: float

    def to_append_item(self) -> messages_pb2.AppendItem:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        return messages_pb2.AppendItem(
            event=messages_pb2.EventObject(
                scroll_speed=messages_pb2.ScrollSpeedEvent(
                    tick=self.tick,
                    timeline=self.timeline,
                    speed=self.speed,
                )
            )
        )

    def shifted(self, tick_offset: int) -> ScrollSpeedEvent:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class NoteSpeedEvent:
    tick: int
    speed: float

    def to_append_item(self) -> messages_pb2.AppendItem:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        return messages_pb2.AppendItem(
            event=messages_pb2.EventObject(
                note_speed=messages_pb2.NoteSpeedEvent(tick=self.tick, speed=self.speed)
            )
        )

    def shifted(self, tick_offset: int) -> NoteSpeedEvent:
        return replace(self, tick=self.tick + tick_offset)


@dataclass(frozen=True)
class RawNoteNode:
    type: int
    long_attr: int = messages_pb2.LONG_ATTR_NONE
    direction: int = messages_pb2.DIRECTION_NONE
    ex_attr: int = messages_pb2.EX_ATTR_NONE
    variation_id: int = 0
    x: int = 0
    width: int = 1
    height: int = 0
    tick: int = 0
    timeline_id: int = 0
    option_value: int = 0
    children: list[RawNoteNode] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "children", tuple(self.children))

    def to_proto(self) -> messages_pb2.RawNoteNode:
        # x is horizontal position; tick/width follow the same rules as LaneNote bases.
        _validate_base(self.tick, self.x, self.width)
        return messages_pb2.RawNoteNode(
            type=self.type,
            long_attr=self.long_attr,
            direction=self.direction,
            ex_attr=self.ex_attr,
            variation_id=self.variation_id,
            x=self.x,
            width=self.width,
            height=self.height,
            tick=self.tick,
            timeline_id=self.timeline_id,
            option_value=self.option_value,
            children=[child.to_proto() for child in self.children],
        )

    def to_append_item(self) -> messages_pb2.AppendItem:
        return messages_pb2.AppendItem(raw_note=self.to_proto())

    def shifted(self, tick_offset: int) -> RawNoteNode:
        return replace(
            self,
            tick=self.tick + tick_offset,
            children=[child.shifted(tick_offset) for child in self.children],
        )
