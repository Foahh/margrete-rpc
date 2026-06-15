from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal, SupportsInt

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class Direction(IntEnum):
    """The full set of note directions as wire-level integer codes.

    Each note type uses a relevant subset, exposed through the readable string enums
    :class:`AirDirection`, :class:`ExtapDirection`, and :class:`FlickDirection`.
    """

    NONE = messages_pb2.DIRECTION_NONE
    AUTO = messages_pb2.DIRECTION_AUTO
    UP = messages_pb2.DIRECTION_UP
    DOWN = messages_pb2.DIRECTION_DOWN
    CENTER = messages_pb2.DIRECTION_CENTER
    LEFT = messages_pb2.DIRECTION_LEFT
    RIGHT = messages_pb2.DIRECTION_RIGHT
    UP_LEFT = messages_pb2.DIRECTION_UPLEFT
    UP_RIGHT = messages_pb2.DIRECTION_UPRIGHT
    DOWN_LEFT = messages_pb2.DIRECTION_DOWNLEFT
    DOWN_RIGHT = messages_pb2.DIRECTION_DOWNRIGHT
    ROTATE_LEFT = messages_pb2.DIRECTION_ROTATE_LEFT
    ROTATE_RIGHT = messages_pb2.DIRECTION_ROTATE_RIGHT
    IN_OUT = messages_pb2.DIRECTION_INOUT
    OUT_IN = messages_pb2.DIRECTION_OUTIN


class AirDirection(StrEnum):
    """Direction of an :class:`Air` note (and air long notes), as a readable string."""

    UP = "up"
    DOWN = "down"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"


class ExtapDirection(StrEnum):
    """Direction of an :class:`Extap` note, as a readable string."""

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
    """Direction of a :class:`Flick` note; ``AUTO`` lets the editor choose."""

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
type DirectionValue = AirDirection | ExtapDirection | FlickDirection | Direction | int
"""Any accepted direction spec: one of the typed direction enums, :class:`Direction`, or a
raw int code."""


AIR_DIRECTION_TO_PROTO = {
    AirDirection.UP: Direction.UP,
    AirDirection.DOWN: Direction.DOWN,
    AirDirection.UP_LEFT: Direction.UP_LEFT,
    AirDirection.UP_RIGHT: Direction.UP_RIGHT,
    AirDirection.DOWN_LEFT: Direction.DOWN_LEFT,
    AirDirection.DOWN_RIGHT: Direction.DOWN_RIGHT,
}

EXTAP_DIRECTION_TO_PROTO = {
    ExtapDirection.UP: Direction.UP,
    ExtapDirection.DOWN: Direction.DOWN,
    ExtapDirection.CENTER: Direction.CENTER,
    ExtapDirection.LEFT: Direction.LEFT,
    ExtapDirection.RIGHT: Direction.RIGHT,
    ExtapDirection.ROTATE_LEFT: Direction.ROTATE_LEFT,
    ExtapDirection.ROTATE_RIGHT: Direction.ROTATE_RIGHT,
    ExtapDirection.IN_OUT: Direction.IN_OUT,
    ExtapDirection.OUT_IN: Direction.OUT_IN,
}

FLICK_DIRECTION_TO_PROTO = {
    FlickDirection.AUTO: Direction.AUTO,
    FlickDirection.LEFT: Direction.LEFT,
    FlickDirection.RIGHT: Direction.RIGHT,
}

AIR_DIRECTION_FROM_PROTO = {int(value): key for key, value in AIR_DIRECTION_TO_PROTO.items()}
EXTAP_DIRECTION_FROM_PROTO = {int(value): key for key, value in EXTAP_DIRECTION_TO_PROTO.items()}
FLICK_DIRECTION_FROM_PROTO = {int(value): key for key, value in FLICK_DIRECTION_TO_PROTO.items()}


def _note_type_value(note_type: SupportsInt) -> int:
    return int(note_type)


def _direction_enum_from_value(value: int) -> Direction | int:
    try:
        return Direction(value)
    except ValueError:
        return value


def direction_from_proto(note_type: SupportsInt, value: int) -> DirectionValue:
    """Map a wire direction code to the typed direction enum for ``note_type``.

    Falls back to :class:`Direction` (or the raw int) when the value has no named form.
    """
    note_type_value = _note_type_value(note_type)
    if note_type_value in (
        messages_pb2.NOTE_TYPE_AIR,
        messages_pb2.NOTE_TYPE_AIRSLIDE,
        messages_pb2.NOTE_TYPE_AIRHOLD,
    ):
        return AIR_DIRECTION_FROM_PROTO.get(value, _direction_enum_from_value(value))
    if note_type_value == messages_pb2.NOTE_TYPE_EXTAP:
        return EXTAP_DIRECTION_FROM_PROTO.get(value, _direction_enum_from_value(value))
    if note_type_value == messages_pb2.NOTE_TYPE_FLICK:
        return FLICK_DIRECTION_FROM_PROTO.get(value, _direction_enum_from_value(value))
    return AIR_DIRECTION_FROM_PROTO.get(value, _direction_enum_from_value(value))


def direction_to_proto(note_type: SupportsInt, value: DirectionValue | str) -> int:
    """Convert a direction spec (enum, string, or int) to its wire code for ``note_type``."""
    if isinstance(value, AirDirection):
        return int(AIR_DIRECTION_TO_PROTO[value])
    if isinstance(value, ExtapDirection):
        return int(EXTAP_DIRECTION_TO_PROTO[value])
    if isinstance(value, FlickDirection):
        return int(FLICK_DIRECTION_TO_PROTO[value])
    if isinstance(value, Direction):
        return int(value)

    note_type_value = _note_type_value(note_type)
    if note_type_value in (
        messages_pb2.NOTE_TYPE_AIR,
        messages_pb2.NOTE_TYPE_AIRSLIDE,
        messages_pb2.NOTE_TYPE_AIRHOLD,
    ):
        if isinstance(value, str):
            return int(AIR_DIRECTION_TO_PROTO[AirDirection(value)])
    elif note_type_value == messages_pb2.NOTE_TYPE_EXTAP:
        if isinstance(value, str):
            return int(EXTAP_DIRECTION_TO_PROTO[ExtapDirection(value)])
    elif note_type_value == messages_pb2.NOTE_TYPE_FLICK:
        if isinstance(value, str):
            return int(FLICK_DIRECTION_TO_PROTO[FlickDirection(value)])
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
