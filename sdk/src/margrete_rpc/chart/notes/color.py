from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2


class Color(IntEnum):
    DEFAULT = messages_pb2.COLOR_DEFAULT
    RED = messages_pb2.COLOR_RED
    ORANGE = messages_pb2.COLOR_ORANGE
    YELLOW = messages_pb2.COLOR_YELLOW
    GREEN = messages_pb2.COLOR_GREEN
    SKY = messages_pb2.COLOR_SKY
    BLUE = messages_pb2.COLOR_BLUE
    VIOLET = messages_pb2.COLOR_VIOLET
    PINK = messages_pb2.COLOR_PINK
    WHITE = messages_pb2.COLOR_WHITE
    BLACK = messages_pb2.COLOR_BLACK
    GRASS = messages_pb2.COLOR_GRASS
    SKY_BLUE = messages_pb2.COLOR_SKY_BLUE
    COBALT_BLUE = messages_pb2.COLOR_COBALT_BLUE
    PURPLE = messages_pb2.COLOR_PURPLE
    NONE = messages_pb2.COLOR_NONE


class ColorValue(StrEnum):
    DEFAULT = "default"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    SKY = "sky"
    BLUE = "blue"
    VIOLET = "violet"
    PINK = "pink"
    WHITE = "white"
    BLACK = "black"
    GRASS = "grass"
    SKY_BLUE = "sky_blue"
    COBALT_BLUE = "cobalt_blue"
    PURPLE = "purple"
    NONE = "none"


type ColorLike = (
    ColorValue
    | Color
    | Literal[
        "default",
        "red",
        "orange",
        "yellow",
        "green",
        "sky",
        "blue",
        "violet",
        "pink",
        "white",
        "black",
        "grass",
        "sky_blue",
        "cobalt_blue",
        "purple",
        "none",
    ]
)


COLOR_VALUE_TO_PROTO = {
    ColorValue.DEFAULT: Color.DEFAULT,
    ColorValue.RED: Color.RED,
    ColorValue.ORANGE: Color.ORANGE,
    ColorValue.YELLOW: Color.YELLOW,
    ColorValue.GREEN: Color.GREEN,
    ColorValue.SKY: Color.SKY,
    ColorValue.BLUE: Color.BLUE,
    ColorValue.VIOLET: Color.VIOLET,
    ColorValue.PINK: Color.PINK,
    ColorValue.WHITE: Color.WHITE,
    ColorValue.BLACK: Color.BLACK,
    ColorValue.GRASS: Color.GRASS,
    ColorValue.SKY_BLUE: Color.SKY_BLUE,
    ColorValue.COBALT_BLUE: Color.COBALT_BLUE,
    ColorValue.PURPLE: Color.PURPLE,
    ColorValue.NONE: Color.NONE,
}

COLOR_VALUE_FROM_PROTO = {value: key for key, value in COLOR_VALUE_TO_PROTO.items()}


def color_from_value(value: int) -> Color | int:
    try:
        return Color(value)
    except ValueError:
        return value


def color_value_from_proto(value: int) -> ColorValue | int:
    color = color_from_value(value)
    if isinstance(color, Color):
        return COLOR_VALUE_FROM_PROTO[color]
    return color


def color_to_value(value: ColorLike | int) -> int:
    if isinstance(value, Color):
        return int(value)
    if isinstance(value, ColorValue):
        return int(COLOR_VALUE_TO_PROTO[value])
    if isinstance(value, str):
        return int(COLOR_VALUE_TO_PROTO[ColorValue(value)])
    return int(value)


__all__ = [
    "Color",
    "ColorLike",
    "ColorValue",
    "color_from_value",
    "color_value_from_proto",
    "color_to_value",
]
