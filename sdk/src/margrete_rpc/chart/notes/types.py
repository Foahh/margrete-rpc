from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any, Literal

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

from ..constants import DEFAULT_H
from ..time import Division, Position, resolve_density, resolve_tick, t2p
from .color import (
    Color,
    ColorLike,
    ColorValue,
    color_to_value,
    color_value_from_proto,
)
from .direction import (
    AirDirection,
    AirDirectionLike,
    Direction,
    DirectionValue,
    ExtapDirection,
    ExtapDirectionLike,
    FlickDirection,
    FlickDirectionLike,
    direction_from_proto,
    direction_to_proto,
)


class NoteType(IntEnum):
    UNKNOWN = messages_pb2.NOTE_TYPE_UNKNOWN
    TAP = messages_pb2.NOTE_TYPE_TAP
    EXTAP = messages_pb2.NOTE_TYPE_EXTAP
    FLICK = messages_pb2.NOTE_TYPE_FLICK
    DAMAGE = messages_pb2.NOTE_TYPE_DAMAGE
    HOLD = messages_pb2.NOTE_TYPE_HOLD
    SLIDE = messages_pb2.NOTE_TYPE_SLIDE
    AIR = messages_pb2.NOTE_TYPE_AIR
    AIRHOLD = messages_pb2.NOTE_TYPE_AIRHOLD
    AIRSLIDE = messages_pb2.NOTE_TYPE_AIRSLIDE
    AIRCRUSH = messages_pb2.NOTE_TYPE_AIRCRUSH
    CLICK = messages_pb2.NOTE_TYPE_CLICK


class LongAttr(IntEnum):
    NONE = messages_pb2.LONG_ATTR_NONE
    BEGIN = messages_pb2.LONG_ATTR_BEGIN
    STEP = messages_pb2.LONG_ATTR_STEP
    CONTROL = messages_pb2.LONG_ATTR_CONTROL
    CURVE_CONTROL = messages_pb2.LONG_ATTR_CURVE_CONTROL
    END = messages_pb2.LONG_ATTR_END
    END_NOACT = messages_pb2.LONG_ATTR_END_NOACT


class JointKind(StrEnum):
    STEP = "step"
    CONTROL = "control"
    CURVE_CONTROL = "curve_control"


type JointKindLike = JointKind | Literal["step", "control", "curve_control"]


JOINT_KIND_TO_LONG_ATTR = {
    JointKind.STEP: LongAttr.STEP,
    JointKind.CONTROL: LongAttr.CONTROL,
    JointKind.CURVE_CONTROL: LongAttr.CURVE_CONTROL,
}

JOINT_KIND_FROM_LONG_ATTR = {value: key for key, value in JOINT_KIND_TO_LONG_ATTR.items()}


def joint_kind_to_long_attr(value: JointKindLike) -> LongAttr:
    return JOINT_KIND_TO_LONG_ATTR[JointKind(value)]


def joint_kind_from_long_attr(value: LongAttr) -> JointKind:
    return JOINT_KIND_FROM_LONG_ATTR[LongAttr(value)]


class ExAttr(IntEnum):
    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


def _enum_line(value: IntEnum | StrEnum) -> str:
    return f"{type(value).__name__}.{value.name}({value.value!r})"


class NoteInfo:
    def __init__(
        self,
        type: NoteType = NoteType.UNKNOWN,
        long_attr: LongAttr = LongAttr.NONE,
        direction: DirectionValue | str = Direction.UP,
        ex_attr: ExAttr = ExAttr.NONE,
        variation_id: ColorLike | int = Color.DEFAULT,
        x: int = 0,
        w: int = 0,
        h: int = DEFAULT_H,
        t: int = 0,
        til: int = 0,
        option_value: Division = 0,
        *,
        p: Position | None = None,
    ) -> None:
        self.type = type
        self.long_attr = long_attr
        self.ex_attr = ex_attr
        self.x = x
        self.w = w
        self.h = h
        self.til = til
        self._direction = Direction(direction_to_proto(type, direction))
        self._variation_id = Color(color_to_value(variation_id))
        self._t = resolve_tick(p) if p is not None else t
        self._option_value = resolve_density(option_value)

    @property
    def direction(self) -> Direction:
        return self._direction

    @direction.setter
    def direction(self, value: DirectionValue | str) -> None:
        self._direction = Direction(direction_to_proto(self.type, value))

    @property
    def variation_id(self) -> Color:
        return self._variation_id

    @variation_id.setter
    def variation_id(self, value: ColorLike | int) -> None:
        self._variation_id = Color(color_to_value(value))

    @property
    def t(self) -> int:
        return self._t

    @t.setter
    def t(self, value: int) -> None:
        self._t = value

    @property
    def p(self) -> Position:
        return t2p(self._t)

    @p.setter
    def p(self, value: Position) -> None:
        self._t = resolve_tick(value)

    @property
    def option_value(self) -> int:
        return self._option_value

    @option_value.setter
    def option_value(self, value: Division) -> None:
        self._option_value = resolve_density(value)

    def copy(self, **changes: Any) -> NoteInfo:
        return NoteInfo(
            type=changes.get("type", self.type),
            long_attr=changes.get("long_attr", self.long_attr),
            direction=changes.get("direction", self.direction),
            ex_attr=changes.get("ex_attr", self.ex_attr),
            variation_id=changes.get("variation_id", self.variation_id),
            x=changes.get("x", self.x),
            w=changes.get("w", self.w),
            h=changes.get("h", self.h),
            t=changes.get("t", self.t),
            p=changes.get("p"),
            til=changes.get("til", self.til),
            option_value=changes.get("option_value", self.option_value),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoteInfo):
            return NotImplemented
        return (
            self.type == other.type
            and self.long_attr == other.long_attr
            and self.direction == other.direction
            and self.ex_attr == other.ex_attr
            and self.variation_id == other.variation_id
            and self.x == other.x
            and self.w == other.w
            and self.h == other.h
            and self.t == other.t
            and self.til == other.til
            and self.option_value == other.option_value
        )

    def __str__(self) -> str:
        return _format_note_info(self)

    __repr__ = __str__


def _direction_line(info: NoteInfo) -> str:
    direction = direction_from_proto(info.type, int(info.direction))
    if isinstance(direction, StrEnum):
        return _enum_line(direction)
    return repr(direction)


def _variation_line(info: NoteInfo) -> str:
    if info.type is NoteType.AIRCRUSH:
        color = color_value_from_proto(int(info.variation_id))
        return _enum_line(color) if isinstance(color, StrEnum) else repr(color)
    if info.type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        return repr(int(info.variation_id))
    return repr(info.variation_id)


def _format_note_info(info: NoteInfo) -> str:
    parts = [
        f"type={_enum_line(info.type)}",
        f"long_attr={_enum_line(info.long_attr)}",
        f"t={info.t}",
        f"x={info.x}",
        f"w={info.w}",
        f"h={info.h}",
        f"dir={_direction_line(info)}",
        f"ex_attr={_enum_line(info.ex_attr)}",
        f"variation_id={_variation_line(info)}",
        f"til={info.til}",
        f"option_value={info.option_value}",
    ]
    return "(" + ", ".join(parts) + ")"


__all__ = [
    "Color",
    "ColorLike",
    "ColorValue",
    "AirDirection",
    "AirDirectionLike",
    "Direction",
    "DirectionValue",
    "ExAttr",
    "ExtapDirection",
    "ExtapDirectionLike",
    "FlickDirection",
    "FlickDirectionLike",
    "JointKind",
    "JointKindLike",
    "LongAttr",
    "NoteInfo",
    "NoteType",
    "direction_from_proto",
    "direction_to_proto",
    "joint_kind_from_long_attr",
    "joint_kind_to_long_attr",
]
