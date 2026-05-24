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


def _shift_air(air: object, *, t: int, x: int, w: int, h: int) -> None:
    from .hl import Air

    assert isinstance(air, Air)
    _apply_deltas(air._info, t=t, x=x, w=w, h=h)
    if air._long_action is not None:
        _shift_long_builder(air._long_action, t=t, x=x, w=w, h=h)


def _shift_ground(note: object, *, t: int, x: int, w: int, h: int) -> None:
    from .hl import Damage, Extap, Flick, Tap

    if not isinstance(note, (Tap, Extap, Flick, Damage)):
        raise TypeError(f"expected ground note, got {type(note).__name__}")
    _apply_deltas(note._info, t=t, x=x, w=w, h=h)
    if note._air is not None:
        _shift_air(note._air, t=t, x=x, w=w, h=h)


def _shift_long_builder(builder: object, *, t: int, x: int, w: int, h: int) -> None:
    from .hl import AirCrush, AirHold, AirSlide, Hold, Joint, Slide

    if not isinstance(builder, (Slide, Hold, AirSlide, AirHold, AirCrush)):
        raise TypeError(f"expected long builder, got {type(builder).__name__}")
    _apply_deltas(builder._info, t=t, x=x, w=w, h=h)
    for joint in builder._joints:
        if not isinstance(joint, Joint):
            continue
        _apply_deltas(joint._info, t=t, x=x, w=w, h=h)
        if joint.air is not None:
            _shift_air(joint.air, t=t, x=x, w=w, h=h)


def _shift_hl(note: object, *, t: int, x: int, w: int, h: int) -> object:
    if t == x == w == h == 0:
        return note
    from .hl import Air, AirCrush, AirHold, AirSlide, Damage, Extap, Flick, Hold, Slide, Tap

    if isinstance(note, (Tap, Extap, Flick, Damage)):
        _shift_ground(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, (Slide, Hold, AirSlide, AirHold, AirCrush)):
        _shift_long_builder(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, Air):
        _shift_air(note, t=t, x=x, w=w, h=h)
    else:
        raise TypeError(f"unsupported note type for shift: {type(note).__name__}")
    return note
