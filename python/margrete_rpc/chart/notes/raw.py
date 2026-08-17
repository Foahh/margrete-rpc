from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from margrete_rpc._proto import messages_pb2

from ..time import DivisionLike, Position, PositionLike, resolve_division, resolve_tick
from .color import Color, ColorLike, ColorValue
from .direction import (
    AirDirection,
    AirDirectionLike,
    Direction,
    DirectionValue,
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


@dataclass(slots=True)
class RawNote:
    """A note as a raw protobuf tree: a :class:`NoteInfo` plus child notes.

    This is the low-level model used when an edit is opened with ``raw_notes=True`` and the
    target of :meth:`Note.to_raw`. Long notes are represented as a begin node with joint
    children. The convenience properties (``type``, ``t``, ``x``, ``w``, ...) read and
    write the underlying :attr:`info`. Prefer the typed notes for authoring; use
    :class:`R` to build raw trees by hand.

    Attributes:
        info: The note's fields (:class:`NoteInfo`).
        children: Child raw notes (e.g. a long note's joints, or an attached air).
    """

    info: NoteInfo = field(default_factory=NoteInfo)
    children: list[RawNote] = field(default_factory=list)
    _id: int | None = field(default=None)

    @property
    def type(self) -> NoteType:
        """The note type (:class:`NoteType`); view of ``info.type``."""
        return self.info.type

    @type.setter
    def type(self, value: NoteType) -> None:
        self.info.type = value

    @property
    def long_attr(self) -> LongAttr:
        return self.info.long_attr

    @long_attr.setter
    def long_attr(self, value: LongAttr) -> None:
        self.info.long_attr = value

    @property
    def dir(self) -> Direction:
        return self.info.direction

    @dir.setter
    def dir(self, value: DirectionValue | str) -> None:
        self.info.direction = value

    @property
    def ex_attr(self) -> ExAttr:
        return self.info.ex_attr

    @ex_attr.setter
    def ex_attr(self, value: ExAttr) -> None:
        self.info.ex_attr = value

    @property
    def variation_id(self) -> Color:
        return self.info.variation_id

    @variation_id.setter
    def variation_id(self, value: ColorLike | int) -> None:
        self.info.variation_id = value

    @property
    def x(self) -> int:
        return self.info.x

    @x.setter
    def x(self, value: int) -> None:
        self.info.x = value

    @property
    def option_value(self) -> int:
        return self.info.option_value

    @option_value.setter
    def option_value(self, value: int | DivisionLike) -> None:
        self.info.option_value = value

    @property
    def t(self) -> int:
        return self.info.t

    @t.setter
    def t(self, value: int | PositionLike) -> None:
        self.info.t = value

    @property
    def p(self) -> Position:
        return self.info.p

    @property
    def w(self) -> int:
        return self.info.w

    @w.setter
    def w(self, value: int) -> None:
        self.info.w = value

    @property
    def h(self) -> int:
        return self.info.h

    @h.setter
    def h(self, value: int) -> None:
        self.info.h = value

    @property
    def til(self) -> int:
        return self.info.til

    @til.setter
    def til(self, value: int) -> None:
        self.info.til = value

    def __str__(self) -> str:
        return _format_raw(self, indent=0)

    __repr__ = __str__

    def child(self, *children: RawNote) -> RawNote:
        """Set this note's children to ``children`` and return ``self`` (for chaining)."""
        self.children = list(children)
        return self

    @classmethod
    def from_proto(cls, proto: messages_pb2.Note) -> RawNote:
        """Build a :class:`RawNote` (and its subtree) from a protobuf ``Note``."""
        return cls(
            _id=proto.id if proto.HasField("id") else None,
            info=NoteInfo(
                type=NoteType(proto.type),
                long_attr=LongAttr(proto.long_attr),
                direction=int(proto.direction),
                ex_attr=ExAttr(proto.ex_attr),
                variation_id=int(proto.variation_id),
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
        """Serialize this note (and its subtree) to a protobuf ``Note``."""
        proto = messages_pb2.Note(
            type=cast("messages_pb2.NoteType", int(self.type)),
            long_attr=cast("messages_pb2.LongAttr", int(self.long_attr)),
            direction=cast("messages_pb2.Direction", int(self.dir)),
            ex_attr=cast("messages_pb2.ExAttr", int(self.ex_attr)),
            variation_id=cast("messages_pb2.Color", int(self.variation_id)),
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


def _format_raw(note: RawNote, *, indent: int = 0) -> str:
    prefix = "  " * indent
    id_part = f"id={note._id}, " if note._id is not None else ""
    line = f"{prefix}Raw({id_part}info={note.info!s})"
    if not note.children:
        return line
    return line + "\n" + "\n".join(_format_raw(c, indent=indent + 1) for c in note.children)


class R:
    """Factory namespace for building :class:`RawNote` trees node-by-node.

    Each static method returns a single :class:`RawNote` for one node of a chart structure,
    named ``<note>[_<segment>]`` (e.g. :meth:`tap`, :meth:`slide_begin`, :meth:`slide_step`,
    :meth:`air_crush_end`). Assemble long notes by attaching segment nodes as children via
    :meth:`RawNote.child`. Intended for raw editing and tests; typed notes are easier for
    normal authoring.
    """

    @staticmethod
    def _raw(
        note_type: NoteType,
        long_attr: LongAttr,
        t: int | PositionLike,
        x: int,
        w: int,
        *,
        h: int | None = None,
        til: int | None = None,
        dir: DirectionValue | str | None = None,
        inverted: bool | None = None,
        gap: int | None = None,
        color: ColorLike | int | None = None,
    ) -> RawNote:
        note = RawNote(info=NoteInfo(type=note_type, long_attr=long_attr, x=x, w=w))
        note.t = resolve_tick(t)
        if h is not None:
            note.h = h
        if til is not None:
            note.til = til
        if dir is not None:
            note.dir = dir
        if inverted is not None:
            note.ex_attr = ExAttr.INVERT if inverted else ExAttr.NONE
        if gap is not None:
            note.option_value = gap
        if color is not None:
            note.variation_id = color
        return note

    # --------------------------------------------------------------------- ground

    @staticmethod
    def tap(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.TAP, LongAttr.NONE, t, x, w, til=til)

    @staticmethod
    def extap(
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        dir: ExtapDirectionLike | int = ExtapDirection.UP,
        til: int | None = None,
    ) -> RawNote:
        return R._raw(NoteType.EXTAP, LongAttr.NONE, t, x, w, dir=dir, til=til)

    @staticmethod
    def flick(
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        dir: FlickDirectionLike | int = FlickDirection.AUTO,
        til: int | None = None,
    ) -> RawNote:
        return R._raw(NoteType.FLICK, LongAttr.NONE, t, x, w, dir=dir, til=til)

    @staticmethod
    def damage(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.DAMAGE, LongAttr.NONE, t, x, w, til=til)

    # ----------------------------------------------------------------- ground long

    @staticmethod
    def hold_begin(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.HOLD, LongAttr.BEGIN, t, x, w, til=til)

    @staticmethod
    def hold_end(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.HOLD, LongAttr.END, t, x, w, til=til)

    @staticmethod
    def slide_begin(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.SLIDE, LongAttr.BEGIN, t, x, w, til=til)

    @staticmethod
    def slide_step(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.SLIDE, LongAttr.STEP, t, x, w, til=til)

    @staticmethod
    def slide_control(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.SLIDE, LongAttr.CONTROL, t, x, w, til=til)

    @staticmethod
    def slide_curve_control(
        *, t: int | PositionLike, x: int, w: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.SLIDE, LongAttr.CURVE_CONTROL, t, x, w, til=til)

    @staticmethod
    def slide_end(*, t: int | PositionLike, x: int, w: int, til: int | None = None) -> RawNote:
        return R._raw(NoteType.SLIDE, LongAttr.END, t, x, w, til=til)

    # ------------------------------------------------------------------------- air

    @staticmethod
    def air(
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        dir: AirDirectionLike | int = AirDirection.UP,
        inverted: bool = False,
        til: int | None = None,
    ) -> RawNote:
        return R._raw(NoteType.AIR, LongAttr.NONE, t, x, w, dir=dir, inverted=inverted, til=til)

    # -------------------------------------------------------------------- air slide

    @staticmethod
    def air_slide_begin(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.BEGIN, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_step(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.STEP, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_control(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_curve_control(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.CURVE_CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_end(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.END, t, x, w, h=h, til=til)

    @staticmethod
    def air_slide_end_noact(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRSLIDE, LongAttr.END_NOACT, t, x, w, h=h, til=til)

    # --------------------------------------------------------------------- air hold

    @staticmethod
    def air_hold_begin(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRHOLD, LongAttr.BEGIN, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_step(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRHOLD, LongAttr.STEP, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_end(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRHOLD, LongAttr.END, t, x, w, h=h, til=til)

    @staticmethod
    def air_hold_end_noact(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRHOLD, LongAttr.END_NOACT, t, x, w, h=h, til=til)

    # -------------------------------------------------------------------- air crush

    @staticmethod
    def air_crush_begin(
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        h: int,
        gap: int | DivisionLike = 0,
        color: ColorLike | int = ColorValue.DEFAULT,
        til: int | None = None,
    ) -> RawNote:
        return R._raw(
            NoteType.AIRCRUSH,
            LongAttr.BEGIN,
            t,
            x,
            w,
            h=h,
            gap=resolve_division(gap),
            color=color,
            til=til,
        )

    @staticmethod
    def air_crush_control(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRCRUSH, LongAttr.CONTROL, t, x, w, h=h, til=til)

    @staticmethod
    def air_crush_end(
        *, t: int | PositionLike, x: int, w: int, h: int, til: int | None = None
    ) -> RawNote:
        return R._raw(NoteType.AIRCRUSH, LongAttr.END, t, x, w, h=h, til=til)


__all__ = ["R", "RawNote"]
