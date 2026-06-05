from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

from ..time import Tick
from .color import (
    air_crush_color_from_value,
    air_crush_color_to_value,
)
from .direction import direction_from_proto, direction_to_proto
from .types import (
    ExAttr,
    LongAttr,
    NoteInfo,
    NoteType,
)


def _info_property(name: str):
    def getter(self: Node):
        return getattr(self.info, name)

    def setter(self: Node, value):
        setattr(self.info, name, value)

    return property(getter, setter)


@dataclass
class Node:
    info: NoteInfo = field(default_factory=NoteInfo)
    children: list[Node] = field(default_factory=list)
    _id: int | None = field(default=None)

    type = _info_property("type")
    long_attr = _info_property("long_attr")
    direction = _info_property("direction")
    ex_attr = _info_property("ex_attr")
    variation_id = _info_property("variation_id")
    x = _info_property("x")
    option_value = _info_property("option_value")
    t = _info_property("t")
    w = _info_property("w")
    h = _info_property("h")
    til = _info_property("til")

    def __str__(self) -> str:
        return _format_node(self, indent=0)

    __repr__ = __str__

    def child(self, *children: Node) -> Node:
        self.children = list(children)
        return self

    @classmethod
    def from_proto(cls, proto: messages_pb2.Note) -> Node:
        return cls(
            _id=proto.id if proto.HasField("id") else None,
            info=NoteInfo(
                type=NoteType(proto.type),
                long_attr=LongAttr(proto.long_attr),
                direction=direction_from_proto(NoteType(proto.type), proto.direction),
                ex_attr=ExAttr(proto.ex_attr),
                variation_id=air_crush_color_from_value(proto.variation_id)
                if proto.type == messages_pb2.NOTE_TYPE_AIRCRUSH
                else proto.variation_id,
                x=proto.x,
                w=proto.width,
                h=proto.height,
                t=proto.tick,
                til=proto.timeline_id,
                option_value=proto.option_value,
            ),
            children=[cls.from_proto(child) for child in proto.children],
        )

    def to_proto(self) -> messages_pb2.Note:
        proto = messages_pb2.Note(
            type=int(self.type),
            long_attr=int(self.long_attr),
            direction=direction_to_proto(self.type, self.direction),
            ex_attr=int(self.ex_attr),
            variation_id=air_crush_color_to_value(self.variation_id),
            x=self.x,
            width=self.w,
            height=self.h,
            tick=int(self.t),
            timeline_id=self.til,
            option_value=self.option_value,
        )
        if self._id is not None:
            proto.id = self._id
        proto.children.extend(child.to_proto() for child in self.children)
        return proto

    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> Node:
        from .shift import _shift_node

        return _shift_node(self, t=t, x=x, w=w, h=h)


def _format_node(note: Node, *, indent: int = 0) -> str:
    prefix = "  " * indent
    id_part = f"id={note._id}, " if note._id is not None else ""
    line = f"{prefix}N({id_part}info={note.info!s})"
    if not note.children:
        return line
    return line + "\n" + "\n".join(_format_node(c, indent=indent + 1) for c in note.children)


class N:
    @staticmethod
    def tap(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.TAP,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def extap(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.EXTAP,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def flick(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.FLICK,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def damage(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.DAMAGE,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def _segment(
        note_type: NoteType,
        long_attr: LongAttr,
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=note_type,
                long_attr=long_attr,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def hold_begin(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.HOLD, LongAttr.BEGIN, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def hold_end(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.HOLD, LongAttr.END, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def slide_begin(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.SLIDE, LongAttr.BEGIN, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def slide_step(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.SLIDE, LongAttr.STEP, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def slide_control(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.SLIDE,
            LongAttr.CONTROL,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def slide_curve_control(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.SLIDE,
            LongAttr.CURVE_CONTROL,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def slide_end(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.SLIDE, LongAttr.END, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air(
        t: Tick,
        x: int,
        w: int,
        *,
        h: int = 800,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.AIR,
                t=t,
                x=x,
                w=w,
                h=h,
                **kwargs,
            )
        )

    @staticmethod
    def air_slide_begin(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRSLIDE, LongAttr.BEGIN, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_slide_step(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRSLIDE, LongAttr.STEP, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_slide_control(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.AIRSLIDE,
            LongAttr.CONTROL,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def air_slide_curve_control(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.AIRSLIDE,
            LongAttr.CURVE_CONTROL,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def air_slide_end(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRSLIDE, LongAttr.END, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_slide_end_noact(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.AIRSLIDE,
            LongAttr.END_NOACT,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def air_hold_begin(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRHOLD, LongAttr.BEGIN, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_hold_step(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRHOLD, LongAttr.STEP, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_hold_end(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(NoteType.AIRHOLD, LongAttr.END, t, x, w, h, til=til, **kwargs)

    @staticmethod
    def air_hold_end_noact(
        t: Tick,
        x: int,
        w: int,
        h: int,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._segment(
            NoteType.AIRHOLD,
            LongAttr.END_NOACT,
            t,
            x,
            w=w,
            h=h,
            til=til,
            **kwargs,
        )

    @staticmethod
    def _air_crush_segment(
        long_attr: LongAttr,
        t: Tick,
        x: int,
        w: int,
        h: int,
        option_value: int = 0,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        if til is not None:
            kwargs["til"] = til
        return Node(
            info=NoteInfo(
                type=NoteType.AIRCRUSH,
                long_attr=long_attr,
                t=t,
                x=x,
                w=w,
                h=h,
                option_value=option_value,
                **kwargs,
            )
        )

    @staticmethod
    def air_crush_begin(
        t: Tick,
        x: int,
        w: int,
        h: int,
        option_value: int = 0,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._air_crush_segment(
            LongAttr.BEGIN,
            t,
            x,
            w,
            h,
            option_value,
            til=til,
            **kwargs,
        )

    @staticmethod
    def air_crush_control(
        t: Tick,
        x: int,
        w: int,
        h: int,
        option_value: int = 0,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._air_crush_segment(
            LongAttr.CONTROL,
            t,
            x,
            w,
            h,
            option_value,
            til=til,
            **kwargs,
        )

    @staticmethod
    def air_crush_end(
        t: Tick,
        x: int,
        w: int,
        h: int,
        option_value: int = 0,
        *,
        til: int | None = None,
        **kwargs,
    ) -> Node:
        return N._air_crush_segment(
            LongAttr.END,
            t,
            x,
            w,
            h,
            option_value,
            til=til,
            **kwargs,
        )
