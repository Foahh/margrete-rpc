from __future__ import annotations

from enum import StrEnum
from typing import Literal

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

class AirCrushColor(StrEnum):
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


type AirCrushColorLike = (
    AirCrushColor
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
type AirCrushColorValue = AirCrushColor | int


AIR_CRUSH_COLOR_TO_VALUE = {
    AirCrushColor.DEFAULT: messages_pb2.AIR_CRUSH_COLOR_DEFAULT,
    AirCrushColor.RED: messages_pb2.AIR_CRUSH_COLOR_RED,
    AirCrushColor.ORANGE: messages_pb2.AIR_CRUSH_COLOR_ORANGE,
    AirCrushColor.YELLOW: messages_pb2.AIR_CRUSH_COLOR_YELLOW,
    AirCrushColor.GREEN: messages_pb2.AIR_CRUSH_COLOR_GREEN,
    AirCrushColor.SKY: messages_pb2.AIR_CRUSH_COLOR_SKY,
    AirCrushColor.BLUE: messages_pb2.AIR_CRUSH_COLOR_BLUE,
    AirCrushColor.VIOLET: messages_pb2.AIR_CRUSH_COLOR_VIOLET,
    AirCrushColor.PINK: messages_pb2.AIR_CRUSH_COLOR_PINK,
    AirCrushColor.WHITE: messages_pb2.AIR_CRUSH_COLOR_WHITE,
    AirCrushColor.BLACK: messages_pb2.AIR_CRUSH_COLOR_BLACK,
    AirCrushColor.GRASS: messages_pb2.AIR_CRUSH_COLOR_GRASS,
    AirCrushColor.SKY_BLUE: messages_pb2.AIR_CRUSH_COLOR_SKY_BLUE,
    AirCrushColor.COBALT_BLUE: messages_pb2.AIR_CRUSH_COLOR_COBALT_BLUE,
    AirCrushColor.PURPLE: messages_pb2.AIR_CRUSH_COLOR_PURPLE,
    AirCrushColor.NONE: messages_pb2.AIR_CRUSH_COLOR_NONE,
}

AIR_CRUSH_COLOR_FROM_VALUE = {value: key for key, value in AIR_CRUSH_COLOR_TO_VALUE.items()}


def air_crush_color_from_value(value: int) -> AirCrushColorValue:
    return AIR_CRUSH_COLOR_FROM_VALUE.get(value, value)


def air_crush_color_to_value(value: AirCrushColorValue | str) -> int:
    if isinstance(value, str):
        value = AirCrushColor(value)
    if isinstance(value, AirCrushColor):
        return AIR_CRUSH_COLOR_TO_VALUE[value]
    return int(value)


__all__ = [
    "AirCrushColor",
    "AirCrushColorLike",
    "AirCrushColorValue",
    "air_crush_color_from_value",
    "air_crush_color_to_value",
]
