from __future__ import annotations

from dataclasses import dataclass, field

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

from ..time import Tick
from .color import ColorLike, ColorValue
from .direction import (
    AirDirection,
    AirDirectionLike,
    ExtapDirection,
    ExtapDirectionLike,
    FlickDirection,
    FlickDirectionLike,
)
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
    dir = _info_property("direction")
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
                direction=proto.direction,
                ex_attr=ExAttr(proto.ex_attr),
                variation_id=proto.variation_id,
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
            direction=self.dir,
            ex_attr=int(self.ex_attr),
            variation_id=int(self.variation_id),
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


def _format_node(note: Node, *, indent: int = 0) -> str:
    prefix = "  " * indent
    id_part = f"id={note._id}, " if note._id is not None else ""
    line = f"{prefix}N({id_part}info={note.info!s})"
    if not note.children:
        return line
    return line + "\n" + "\n".join(_format_node(c, indent=indent + 1) for c in note.children)


class N:
    @staticmethod
    def _node(
        note_type: NoteType,
        long_attr: LongAttr,
        t: Tick,
        x: int,
        w: int,
        *,
        h: int | None = None,
        til: int | None = None,
        dir: object | None = None,
        inverted: bool | None = None,
        gap: int | tuple[int, int] | None = None,
        color: ColorLike | int | None = None,
    ) -> Node:
        node = Node(info=NoteInfo(type=note_type, long_attr=long_attr, x=x, w=w))
        node.t = t
        if h is not None:
            node.h = h
        if til is not None:
            node.til = til
        if dir is not None:
            node.dir = dir
        if inverted is not None:
            node.ex_attr = ExAttr.INVERT if inverted else ExAttr.NONE
        if gap is not None:
            node.option_value = gap
        if color is not None:
            node.variation_id = color
        return node

    # --------------------------------------------------------------------- ground

    @staticmethod
    def tap(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.TAP, LongAttr.NONE, t, x, w, til=til)

    @staticmethod
    def extap(
        t: Tick,
        x: int,
        w: int,
        *,
        dir: ExtapDirectionLike | int = ExtapDirection.UP,
        til: int | None = None,
    ) -> Node:
        return N._node(NoteType.EXTAP, LongAttr.NONE, t, x, w, dir=dir, til=til)

    @staticmethod
    def flick(
        t: Tick,
        x: int,
        w: int,
        *,
        dir: FlickDirectionLike | int = FlickDirection.AUTO,
        til: int | None = None,
    ) -> Node:
        return N._node(NoteType.FLICK, LongAttr.NONE, t, x, w, dir=dir, til=til)

    @staticmethod
    def damage(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.DAMAGE, LongAttr.NONE, t, x, w, til=til)

    # ----------------------------------------------------------------- ground long

    @staticmethod
    def hold_begin(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.HOLD, LongAttr.BEGIN, t, x, w, til=til)

    @staticmethod
    def hold_end(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.HOLD, LongAttr.END, t, x, w, til=til)

    @staticmethod
    def slide_begin(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.SLIDE, LongAttr.BEGIN, t, x, w, til=til)

    @staticmethod
    def slide_step(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.SLIDE, LongAttr.STEP, t, x, w, til=til)

    @staticmethod
    def slide_control(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.SLIDE, LongAttr.CONTROL, t, x, w, til=til)

    @staticmethod
    def slide_curve_control(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.SLIDE, LongAttr.CURVE_CONTROL, t, x, w, til=til)

    @staticmethod
    def slide_end(t: Tick, x: int, w: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.SLIDE, LongAttr.END, t, x, w, til=til)

    # ------------------------------------------------------------------------- air

    @staticmethod
    def air(
        t: Tick,
        x: int,
        w: int,
        *,
        dir: AirDirectionLike | int = AirDirection.UP,
        inverted: bool = False,
        til: int | None = None,
    ) -> Node:
        return N._node(NoteType.AIR, LongAttr.NONE, t, x, w, dir=dir, inverted=inverted, til=til)

    # -------------------------------------------------------------------- air slide

    @staticmethod
    def air_slide_begin(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.BEGIN, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_step(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.STEP, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_control(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_curve_control(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.CURVE_CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_end(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.END, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_end_noact(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRSLIDE, LongAttr.END_NOACT, t, x, w, h=h, til=til)

    # --------------------------------------------------------------------- air hold

    @staticmethod
    def air_hold_begin(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRHOLD, LongAttr.BEGIN, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_step(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRHOLD, LongAttr.STEP, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_end(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRHOLD, LongAttr.END, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_end_noact(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRHOLD, LongAttr.END_NOACT, t, x, w, h=h, til=til)

    # -------------------------------------------------------------------- air crush

    @staticmethod
    def air_crush_begin(
        t: Tick,
        x: int,
        w: int,
        h: int,
        gap: int | tuple[int, int] = 0,
        color: ColorLike | int = ColorValue.DEFAULT,
        *,
        til: int | None = None,
    ) -> Node:
        return N._node(
            NoteType.AIRCRUSH, LongAttr.BEGIN, t, x, w, h=h, gap=gap, color=color, til=til
        )

    @staticmethod
    def air_crush_control(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRCRUSH, LongAttr.CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_crush_end(t: Tick, x: int, w: int, h: int, *, til: int | None = None) -> Node:
        return N._node(NoteType.AIRCRUSH, LongAttr.END, t, x, w, h=h, til=til)
