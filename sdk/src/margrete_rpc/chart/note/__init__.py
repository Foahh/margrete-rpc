from __future__ import annotations

from .color import (
    AirCrushColor,
    AirCrushColorLike,
    AirCrushColorValue,
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
)
from ._air import Air, AirHold, AirSlide
from ._ground import Damage, Extap, Flick, Tap
from ._joint import Joint
from ._long import AirCrush, Hold, Slide
from ._shared import Note, UnsupportedNoteTree
from ._wrap import wrap_mg_note
from .mg import M, MgNote
from .types import (
    ExAttr,
    LongAttr,
    NoteInfo,
    NoteType,
)

__all__ = [
    "Air",
    "AirCrush",
    "AirHold",
    "AirSlide",
    "AirCrushColor",
    "AirCrushColorLike",
    "AirCrushColorValue",
    "AirDirection",
    "AirDirectionLike",
    "Direction",
    "DirectionValue",
    "Damage",
    "ExAttr",
    "Extap",
    "ExtapDirection",
    "ExtapDirectionLike",
    "Flick",
    "FlickDirection",
    "FlickDirectionLike",
    "Note",
    "Hold",
    "Joint",
    "M",
    "MgNote",
    "LongAttr",
    "NoteInfo",
    "NoteType",
    "Slide",
    "Tap",
    "UnsupportedNoteTree",
    "wrap_mg_note",
]
