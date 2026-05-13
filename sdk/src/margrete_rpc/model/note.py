from __future__ import annotations

from margrete_rpc.model.hl_note import (
    AirCrush,
    Damage,
    Extap,
    Flick,
    HLNote,
    Hold,
    Slide,
    Tap,
    UnsupportedNoteTree,
    wrap_ll_note,
)
from margrete_rpc.model.ll_note import L, LLNote, NoteInfo
from margrete_rpc.model.note_types import (
    _TICKS_PER_BEAT,
    AirColor,
    AirCrushColor,
    AirCrushOption,
    AirDirection,
    ExAttr,
    ExtapDirection,
    FlickDirection,
    LongAttr,
    NoteType,
)

__all__ = [
    "_TICKS_PER_BEAT",
    "AirColor",
    "AirDirection",
    "AirCrush",
    "AirCrushColor",
    "AirCrushOption",
    "Damage",
    "ExAttr",
    "Extap",
    "ExtapDirection",
    "Flick",
    "FlickDirection",
    "HLNote",
    "Hold",
    "L",
    "LLNote",
    "LongAttr",
    "NoteInfo",
    "NoteType",
    "Slide",
    "Tap",
    "UnsupportedNoteTree",
    "wrap_ll_note",
]
