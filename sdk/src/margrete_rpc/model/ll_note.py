from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model.note_types import (
    _TICKS_PER_BEAT,
    Direction,
    ExAttr,
    LongAttr,
    NoteType,
)


@dataclass
class NoteInfo:
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

    def copy(self, **changes: Any) -> NoteInfo:
        return replace(self, **changes)


def _info_property(name: str):
    def getter(self: LLNote):
        return getattr(self.info, name)

    def setter(self: LLNote, value):
        setattr(self.info, name, value)

    return property(getter, setter)


@dataclass
class LLNote:
    info: NoteInfo = field(default_factory=NoteInfo)
    children: list[LLNote] = field(default_factory=list)
    id: int | None = None

    type = _info_property("type")
    long_attr = _info_property("long_attr")
    direction = _info_property("direction")
    ex_attr = _info_property("ex_attr")
    variation_id = _info_property("variation_id")
    x = _info_property("x")
    width = _info_property("width")
    height = _info_property("height")
    tick = _info_property("tick")
    timeline_id = _info_property("timeline_id")
    option_value = _info_property("option_value")

    @property
    def bar(self) -> tuple[int, int]:
        fraction = Fraction(self.tick, _TICKS_PER_BEAT)
        return fraction.numerator, fraction.denominator

    @bar.setter
    def bar(self, value: tuple[int, int]) -> None:
        numerator, denominator = value
        tick = Fraction(numerator * _TICKS_PER_BEAT, denominator)
        if tick.denominator != 1:
            raise ValueError("beat division must resolve to a whole tick")
        self.tick = tick.numerator

    def child(self, *children: LLNote) -> LLNote:
        self.children = list(children)
        return self

    @classmethod
    def from_proto(cls, proto: messages_pb2.Note) -> LLNote:
        return cls(
            id=proto.id if proto.HasField("id") else None,
            info=NoteInfo(
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
            ),
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


class L:
    @staticmethod
    def tap(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return LLNote(
            info=NoteInfo(type=NoteType.TAP, tick=tick, x=x, width=width, height=height, **kwargs)
        )

    @staticmethod
    def extap(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return LLNote(
            info=NoteInfo(type=NoteType.EXTAP, tick=tick, x=x, width=width, height=height, **kwargs)
        )

    @staticmethod
    def flick(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return LLNote(
            info=NoteInfo(type=NoteType.FLICK, tick=tick, x=x, width=width, height=height, **kwargs)
        )

    @staticmethod
    def damage(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return LLNote(
            info=NoteInfo(
                type=NoteType.DAMAGE, tick=tick, x=x, width=width, height=height, **kwargs
            )
        )

    @staticmethod
    def _segment(
        note_type: NoteType,
        long_attr: LongAttr,
        tick: int,
        x: int,
        width: int,
        height: int,
        **kwargs,
    ) -> LLNote:
        return LLNote(
            info=NoteInfo(
                type=note_type,
                long_attr=long_attr,
                tick=tick,
                x=x,
                width=width,
                height=height,
                **kwargs,
            )
        )

    @staticmethod
    def hold_begin(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.HOLD, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @staticmethod
    def hold_end(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.HOLD, LongAttr.END, tick, x, width, height, **kwargs)

    @staticmethod
    def slide_begin(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.SLIDE, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @staticmethod
    def slide_step(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.SLIDE, LongAttr.STEP, tick, x, width, height, **kwargs)

    @staticmethod
    def slide_control(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.SLIDE, LongAttr.CONTROL, tick, x, width, height, **kwargs)

    @staticmethod
    def slide_curve_control(
        tick: int, x: int, width: int, *, height: int = 800, **kwargs
    ) -> LLNote:
        return L._segment(NoteType.SLIDE, LongAttr.CURVE_CONTROL, tick, x, width, height, **kwargs)

    @staticmethod
    def slide_end(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return L._segment(NoteType.SLIDE, LongAttr.END, tick, x, width, height, **kwargs)

    @staticmethod
    def air(tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> LLNote:
        return LLNote(
            info=NoteInfo(type=NoteType.AIR, tick=tick, x=x, width=width, height=height, **kwargs)
        )

    @staticmethod
    def air_slide_begin(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRSLIDE, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @staticmethod
    def air_slide_step(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRSLIDE, LongAttr.STEP, tick, x, width, height, **kwargs)

    @staticmethod
    def air_slide_control(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRSLIDE, LongAttr.CONTROL, tick, x, width, height, **kwargs)

    @staticmethod
    def air_slide_curve_control(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(
            NoteType.AIRSLIDE, LongAttr.CURVE_CONTROL, tick, x, width, height, **kwargs
        )

    @staticmethod
    def air_slide_end(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRSLIDE, LongAttr.END, tick, x, width, height, **kwargs)

    @staticmethod
    def air_slide_end_noact(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRSLIDE, LongAttr.END_NOACT, tick, x, width, height, **kwargs)

    @staticmethod
    def air_hold_begin(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRHOLD, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @staticmethod
    def air_hold_step(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRHOLD, LongAttr.STEP, tick, x, width, height, **kwargs)

    @staticmethod
    def air_hold_end(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRHOLD, LongAttr.END, tick, x, width, height, **kwargs)

    @staticmethod
    def air_hold_end_noact(tick: int, x: int, width: int, height: int, **kwargs) -> LLNote:
        return L._segment(NoteType.AIRHOLD, LongAttr.END_NOACT, tick, x, width, height, **kwargs)

    @staticmethod
    def _air_crush_segment(
        long_attr: LongAttr, tick: int, x: int, width: int, height: int, option_value: int, **kwargs
    ) -> LLNote:
        return LLNote(
            info=NoteInfo(
                type=NoteType.AIRCRUSH,
                long_attr=long_attr,
                tick=tick,
                x=x,
                width=width,
                height=height,
                option_value=int(option_value),
                **kwargs,
            )
        )

    @staticmethod
    def air_crush_begin(
        tick: int, x: int, width: int, height: int, option_value: int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(LongAttr.BEGIN, tick, x, width, height, option_value, **kwargs)

    @staticmethod
    def air_crush_control(
        tick: int, x: int, width: int, height: int, option_value: int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(
            LongAttr.CONTROL, tick, x, width, height, option_value, **kwargs
        )

    @staticmethod
    def air_crush_end(
        tick: int, x: int, width: int, height: int, option_value: int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(LongAttr.END, tick, x, width, height, option_value, **kwargs)
