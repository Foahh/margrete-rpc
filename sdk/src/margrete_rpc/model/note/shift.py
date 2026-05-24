from __future__ import annotations

from .ll import LLNote
from .types import NoteInfo


def _apply_deltas(info: NoteInfo, *, t: int, x: int, w: int, h: int) -> None:
    info.tick = int(info.tick) + t
    info.x += x
    info.width += w
    info.height += h


def _shift_ll(note: LLNote, *, t: int, x: int, w: int, h: int) -> LLNote:
    if t == x == w == h == 0:
        return note
    _apply_deltas(note.info, t=t, x=x, w=w, h=h)
    for child in note.children:
        _shift_ll(child, t=t, x=x, w=w, h=h)
    return note
