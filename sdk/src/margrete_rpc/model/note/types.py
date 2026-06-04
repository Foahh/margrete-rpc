from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Any, cast

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


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


class AirDirection(IntEnum):
    UP = messages_pb2.DIRECTION_UP
    DOWN = messages_pb2.DIRECTION_DOWN
    UPLEFT = messages_pb2.DIRECTION_UPLEFT
    UPRIGHT = messages_pb2.DIRECTION_UPRIGHT
    DOWNLEFT = messages_pb2.DIRECTION_DOWNLEFT
    DOWNRIGHT = messages_pb2.DIRECTION_DOWNRIGHT


class ExtapDirection(IntEnum):
    UP = messages_pb2.DIRECTION_UP
    DOWN = messages_pb2.DIRECTION_DOWN
    CENTER = messages_pb2.DIRECTION_CENTER
    LEFT = messages_pb2.DIRECTION_LEFT
    RIGHT = messages_pb2.DIRECTION_RIGHT
    ROTATE_LEFT = messages_pb2.DIRECTION_ROTATE_LEFT
    ROTATE_RIGHT = messages_pb2.DIRECTION_ROTATE_RIGHT
    INOUT = messages_pb2.DIRECTION_INOUT
    OUTIN = messages_pb2.DIRECTION_OUTIN


class FlickDirection(IntEnum):
    AUTO = messages_pb2.DIRECTION_AUTO
    LEFT = messages_pb2.DIRECTION_LEFT
    RIGHT = messages_pb2.DIRECTION_RIGHT


class ExAttr(IntEnum):
    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


class AirCrushOption(IntEnum):
    TRACELIKE = 0
    HEAD_ONLY = 0x7FFFFFFF


class AirCrushColor(IntEnum):
    DEF = 0
    RED = 1
    ORN = 2
    YEL = 3
    GRN = 4
    AQA = 5
    BLU = 6
    PPL = 7
    VLT = 8
    PPL_ALT = 9
    GRY = 10
    BLK = 11
    LIM = 12
    CYN = 13
    DGR = 14
    PNK = 15
    NON = 35


def _enum_line(value: IntEnum) -> str:
    return f"{type(value).__name__}.{value.name}({int(value)})"


@dataclass
class NoteInfo:
    type: NoteType = NoteType.UNKNOWN
    long_attr: LongAttr = LongAttr.NONE
    direction: AirDirection | ExtapDirection | FlickDirection = cast(
        AirDirection | ExtapDirection | FlickDirection, messages_pb2.DIRECTION_UP
    )
    ex_attr: ExAttr = ExAttr.NONE
    variation_id: AirCrushColor | int = 0
    x: int = 0
    width: int = 0
    height: int = 80
    tick: int = 0
    timeline_id: int = 0
    option_value: AirCrushOption | int = 0

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "tick" and isinstance(value, tuple):
            from ..chart_time import resolve_tick

            value = resolve_tick(value)
        object.__setattr__(self, name, value)

    def copy(self, **changes: Any) -> NoteInfo:
        return replace(self, **changes)

    def __str__(self) -> str:
        return _format_note_info(self)

    __repr__ = __str__


def _direction_line(info: NoteInfo) -> str:
    d = info.direction
    if isinstance(d, IntEnum):
        return _enum_line(d)
    raw = int(d)
    if info.type is NoteType.FLICK:
        try:
            return _enum_line(FlickDirection(raw))
        except ValueError:
            return repr(raw)
    if info.type is NoteType.EXTAP:
        try:
            return _enum_line(ExtapDirection(raw))
        except ValueError:
            return repr(raw)
    if info.type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        try:
            return _enum_line(AirDirection(raw))
        except ValueError:
            return repr(raw)
    return repr(raw)


def _variation_line(info: NoteInfo) -> str:
    v = info.variation_id
    if isinstance(v, IntEnum):
        return _enum_line(v)
    if info.type is NoteType.AIRCRUSH:
        try:
            return _enum_line(AirCrushColor(int(v)))
        except ValueError:
            return repr(v)
    if info.type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        return repr(int(v))
    return repr(v)


def _option_line(info: NoteInfo) -> str:
    o = info.option_value
    if isinstance(o, IntEnum):
        return _enum_line(o)
    if info.type is NoteType.AIRCRUSH:
        try:
            return _enum_line(AirCrushOption(int(o)))
        except ValueError:
            return repr(o)
    return repr(o)


def _format_note_info(info: NoteInfo) -> str:
    parts = [
        f"type={_enum_line(info.type)}",
        f"long_attr={_enum_line(info.long_attr)}",
        f"tick={info.tick}",
        f"x={info.x}",
        f"width={info.width}",
        f"height={info.height}",
        f"direction={_direction_line(info)}",
        f"ex_attr={_enum_line(info.ex_attr)}",
        f"variation_id={_variation_line(info)}",
        f"timeline_id={info.timeline_id}",
        f"option_value={_option_line(info)}",
    ]
    return "NoteInfo(" + ", ".join(parts) + ")"


__all__ = [
    "AirCrushColor",
    "AirCrushOption",
    "AirDirection",
    "ExAttr",
    "ExtapDirection",
    "FlickDirection",
    "LongAttr",
    "NoteInfo",
    "NoteType",
]
