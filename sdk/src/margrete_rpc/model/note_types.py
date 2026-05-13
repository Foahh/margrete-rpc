from __future__ import annotations

from enum import IntEnum

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


