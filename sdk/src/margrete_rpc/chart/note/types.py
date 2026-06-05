from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum, StrEnum
from typing import Any

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

from .color import (
    AirCrushColor,
    AirCrushColorLike,
    AirCrushColorValue,
    air_crush_color_from_value,
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


class ExAttr(IntEnum):
    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


def _enum_line(value: IntEnum | StrEnum) -> str:
    return f"{type(value).__name__}.{value.name}({value.value!r})"


@dataclass
class NoteInfo:
    type: NoteType = NoteType.UNKNOWN
    long_attr: LongAttr = LongAttr.NONE
    direction: DirectionValue = AirDirection.UP
    ex_attr: ExAttr = ExAttr.NONE
    variation_id: AirCrushColorValue = 0
    x: int = 0
    w: int = 0
    h: int = 80
    t: int = 0
    til: int = 0

    option_value: int = 0
    """
    TRACE = 0

    HEAD_ONLY = 0x7FFFFFFF
    """

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "t" and isinstance(value, tuple):
            from ..time import resolve_tick

            value = resolve_tick(value)
        object.__setattr__(self, name, value)

    def copy(self, **changes: Any) -> NoteInfo:
        return replace(self, **changes)

    def __str__(self) -> str:
        return _format_note_info(self)

    __repr__ = __str__


def _direction_line(info: NoteInfo) -> str:
    d = info.direction
    if isinstance(d, StrEnum):
        return _enum_line(d)
    direction = direction_from_proto(info.type, int(d))
    if isinstance(direction, StrEnum):
        return _enum_line(direction)
    return repr(direction)


def _variation_line(info: NoteInfo) -> str:
    v = info.variation_id
    if isinstance(v, StrEnum):
        return _enum_line(v)
    if info.type is NoteType.AIRCRUSH:
        color = air_crush_color_from_value(int(v))
        return _enum_line(color) if isinstance(color, StrEnum) else repr(color)
    if info.type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        return repr(int(v))
    return repr(v)


def _format_note_info(info: NoteInfo) -> str:
    parts = [
        f"type={_enum_line(info.type)}",
        f"long_attr={_enum_line(info.long_attr)}",
        f"t={info.t}",
        f"x={info.x}",
        f"w={info.w}",
        f"h={info.h}",
        f"direction={_direction_line(info)}",
        f"ex_attr={_enum_line(info.ex_attr)}",
        f"variation_id={_variation_line(info)}",
        f"til={info.til}",
        f"option_value={info.option_value}",
    ]
    return "NI(" + ", ".join(parts) + ")"


__all__ = [
    "AirCrushColor",
    "AirCrushColorLike",
    "AirCrushColorValue",
    "AirDirection",
    "AirDirectionLike",
    "Direction",
    "DirectionValue",
    "ExAttr",
    "ExtapDirection",
    "ExtapDirectionLike",
    "FlickDirection",
    "FlickDirectionLike",
    "LongAttr",
    "NoteInfo",
    "NoteType",
    "direction_from_proto",
    "direction_to_proto",
]
