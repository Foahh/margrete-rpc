from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

from .types import (
    AirCrushOption,
    AirDirection,
    ExAttr,
    ExtapDirection,
    FlickDirection,
    LongAttr,
    NoteInfo,
    NoteType,
)


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

    def __str__(self) -> str:
        return _format_ll_note(self, indent=0)

    __repr__ = __str__

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
                direction=cast(AirDirection | ExtapDirection | FlickDirection, proto.direction),
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
            variation_id=int(self.variation_id),
            x=self.x,
            width=self.width,
            height=self.height,
            tick=int(self.tick),
            timeline_id=self.timeline_id,
            option_value=int(self.option_value),
        )
        if self.id is not None:
            proto.id = self.id
        proto.children.extend(child.to_proto() for child in self.children)
        return proto

    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> LLNote:
        from .shift import _shift_ll

        return _shift_ll(self, t=t, x=x, w=w, h=h)


def _format_ll_note(note: LLNote, *, indent: int = 0) -> str:
    prefix = "  " * indent
    id_part = f"id={note.id}, " if note.id is not None else ""
    line = f"{prefix}LLNote({id_part}info={note.info!s})"
    if not note.children:
        return line
    return line + "\n" + "\n".join(_format_ll_note(c, indent=indent + 1) for c in note.children)


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
        long_attr: LongAttr,
        tick: int,
        x: int,
        width: int,
        height: int,
        option_value: AirCrushOption | int,
        **kwargs,
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
        tick: int, x: int, width: int, height: int, option_value: AirCrushOption | int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(LongAttr.BEGIN, tick, x, width, height, option_value, **kwargs)

    @staticmethod
    def air_crush_control(
        tick: int, x: int, width: int, height: int, option_value: AirCrushOption | int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(
            LongAttr.CONTROL, tick, x, width, height, option_value, **kwargs
        )

    @staticmethod
    def air_crush_end(
        tick: int, x: int, width: int, height: int, option_value: AirCrushOption | int, **kwargs
    ) -> LLNote:
        return L._air_crush_segment(LongAttr.END, tick, x, width, height, option_value, **kwargs)
