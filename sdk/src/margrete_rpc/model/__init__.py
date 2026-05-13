"""Domain models."""

from margrete_rpc.model.chart import Chart, ChartEvents, LLChart, normalize_event_operations
from margrete_rpc.model.event import (
    BeatChangeEvent,
    BpmEvent,
    NoteSpeedEvent,
    TimelineSpeedEvent,
)
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
)
from margrete_rpc.model.ll_note import L, LLNote, NoteInfo
from margrete_rpc.model.note import (
    AirColor,
    AirCrushColor,
    AirCrushOption,
    Direction,
    ExAttr,
    LongAttr,
    NoteType,
)

__all__ = [
    "AirColor",
    "AirCrush",
    "AirCrushColor",
    "AirCrushOption",
    "BeatChangeEvent",
    "BpmEvent",
    "Chart",
    "ChartEvents",
    "Damage",
    "Direction",
    "ExAttr",
    "Extap",
    "Flick",
    "HLNote",
    "Hold",
    "L",
    "LLChart",
    "LLNote",
    "LongAttr",
    "NoteInfo",
    "NoteSpeedEvent",
    "NoteType",
    "Slide",
    "Tap",
    "TimelineSpeedEvent",
    "UnsupportedNoteTree",
    "normalize_event_operations",
]
