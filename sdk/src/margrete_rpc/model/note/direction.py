from __future__ import annotations

from enum import StrEnum
from typing import Literal, SupportsInt

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


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


def _note_type_value(note_type: SupportsInt) -> int:
    return int(note_type)


def direction_from_proto(note_type: SupportsInt, value: int) -> DirectionValue:
    note_type_value = _note_type_value(note_type)
    if note_type_value in (
        messages_pb2.NOTE_TYPE_AIR,
        messages_pb2.NOTE_TYPE_AIRSLIDE,
        messages_pb2.NOTE_TYPE_AIRHOLD,
    ):
        return AIR_DIRECTION_FROM_PROTO.get(value, value)
    if note_type_value == messages_pb2.NOTE_TYPE_EXTAP:
        return EXTAP_DIRECTION_FROM_PROTO.get(value, value)
    if note_type_value == messages_pb2.NOTE_TYPE_FLICK:
        return FLICK_DIRECTION_FROM_PROTO.get(value, value)
    return AIR_DIRECTION_FROM_PROTO.get(value, value)


def direction_to_proto(note_type: SupportsInt, value: DirectionValue | str) -> int:
    if isinstance(value, AirDirection):
        return AIR_DIRECTION_TO_PROTO[value]
    if isinstance(value, ExtapDirection):
        return EXTAP_DIRECTION_TO_PROTO[value]
    if isinstance(value, FlickDirection):
        return FLICK_DIRECTION_TO_PROTO[value]

    note_type_value = _note_type_value(note_type)
    if note_type_value in (
        messages_pb2.NOTE_TYPE_AIR,
        messages_pb2.NOTE_TYPE_AIRSLIDE,
        messages_pb2.NOTE_TYPE_AIRHOLD,
    ):
        if isinstance(value, str):
            return AIR_DIRECTION_TO_PROTO[AirDirection(value)]
    elif note_type_value == messages_pb2.NOTE_TYPE_EXTAP:
        if isinstance(value, str):
            return EXTAP_DIRECTION_TO_PROTO[ExtapDirection(value)]
    elif note_type_value == messages_pb2.NOTE_TYPE_FLICK:
        if isinstance(value, str):
            return FLICK_DIRECTION_TO_PROTO[FlickDirection(value)]
    return int(value)


__all__ = [
    "AirDirection",
    "AirDirectionLike",
    "Direction",
    "DirectionValue",
    "ExtapDirection",
    "ExtapDirectionLike",
    "FlickDirection",
    "FlickDirectionLike",
    "direction_from_proto",
    "direction_to_proto",
]
