from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum, StrEnum
from typing import Any, Literal

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


class AirDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"


class ExtapDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    IN_OUT = "in_out"
    OUT_IN = "out_in"


class FlickDirection(StrEnum):
    AUTO = "auto"
    LEFT = "left"
    RIGHT = "right"


type AirDirectionLike = (
    AirDirection
    | Literal[
        "up",
        "down",
        "up_left",
        "up_right",
        "down_left",
        "down_right",
    ]
)
type ExtapDirectionLike = (
    ExtapDirection
    | Literal[
        "up",
        "down",
        "center",
        "left",
        "right",
        "rotate_left",
        "rotate_right",
        "in_out",
        "out_in",
    ]
)
type FlickDirectionLike = FlickDirection | Literal["auto", "left", "right"]
type Direction = AirDirection | ExtapDirection | FlickDirection
type DirectionValue = Direction | int


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


AIR_DIRECTION_TO_PROTO = {
    AirDirection.UP: messages_pb2.DIRECTION_UP,
    AirDirection.DOWN: messages_pb2.DIRECTION_DOWN,
    AirDirection.UP_LEFT: messages_pb2.DIRECTION_UPLEFT,
    AirDirection.UP_RIGHT: messages_pb2.DIRECTION_UPRIGHT,
    AirDirection.DOWN_LEFT: messages_pb2.DIRECTION_DOWNLEFT,
    AirDirection.DOWN_RIGHT: messages_pb2.DIRECTION_DOWNRIGHT,
}

EXTAP_DIRECTION_TO_PROTO = {
    ExtapDirection.UP: messages_pb2.DIRECTION_UP,
    ExtapDirection.DOWN: messages_pb2.DIRECTION_DOWN,
    ExtapDirection.CENTER: messages_pb2.DIRECTION_CENTER,
    ExtapDirection.LEFT: messages_pb2.DIRECTION_LEFT,
    ExtapDirection.RIGHT: messages_pb2.DIRECTION_RIGHT,
    ExtapDirection.ROTATE_LEFT: messages_pb2.DIRECTION_ROTATE_LEFT,
    ExtapDirection.ROTATE_RIGHT: messages_pb2.DIRECTION_ROTATE_RIGHT,
    ExtapDirection.IN_OUT: messages_pb2.DIRECTION_INOUT,
    ExtapDirection.OUT_IN: messages_pb2.DIRECTION_OUTIN,
}

FLICK_DIRECTION_TO_PROTO = {
    FlickDirection.AUTO: messages_pb2.DIRECTION_AUTO,
    FlickDirection.LEFT: messages_pb2.DIRECTION_LEFT,
    FlickDirection.RIGHT: messages_pb2.DIRECTION_RIGHT,
}

AIR_DIRECTION_FROM_PROTO = {value: key for key, value in AIR_DIRECTION_TO_PROTO.items()}
EXTAP_DIRECTION_FROM_PROTO = {value: key for key, value in EXTAP_DIRECTION_TO_PROTO.items()}
FLICK_DIRECTION_FROM_PROTO = {value: key for key, value in FLICK_DIRECTION_TO_PROTO.items()}


def _enum_line(value: IntEnum | StrEnum) -> str:
    return f"{type(value).__name__}.{value.name}({value.value!r})"


@dataclass
class NoteInfo:
    type: NoteType = NoteType.UNKNOWN
    long_attr: LongAttr = LongAttr.NONE
    direction: DirectionValue = AirDirection.UP
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
    if isinstance(d, StrEnum):
        return _enum_line(d)
    direction = direction_from_proto(info.type, int(d))
    if isinstance(direction, StrEnum):
        return _enum_line(direction)
    return repr(direction)


def direction_from_proto(note_type: NoteType, value: int) -> DirectionValue:
    if note_type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        return AIR_DIRECTION_FROM_PROTO.get(value, value)
    if note_type is NoteType.EXTAP:
        return EXTAP_DIRECTION_FROM_PROTO.get(value, value)
    if note_type is NoteType.FLICK:
        return FLICK_DIRECTION_FROM_PROTO.get(value, value)
    return AIR_DIRECTION_FROM_PROTO.get(value, value)


def direction_to_proto(note_type: NoteType, value: DirectionValue | str) -> int:
    if isinstance(value, AirDirection):
        return AIR_DIRECTION_TO_PROTO[value]
    if isinstance(value, ExtapDirection):
        return EXTAP_DIRECTION_TO_PROTO[value]
    if isinstance(value, FlickDirection):
        return FLICK_DIRECTION_TO_PROTO[value]
    if note_type in (NoteType.AIR, NoteType.AIRSLIDE, NoteType.AIRHOLD):
        if isinstance(value, str):
            return AIR_DIRECTION_TO_PROTO[AirDirection(value)]
    elif note_type is NoteType.EXTAP:
        if isinstance(value, str):
            return EXTAP_DIRECTION_TO_PROTO[ExtapDirection(value)]
    elif note_type is NoteType.FLICK:
        if isinstance(value, str):
            return FLICK_DIRECTION_TO_PROTO[FlickDirection(value)]
    return int(value)


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
