from __future__ import annotations

from .types import NoteInfo


def _apply_deltas(info: NoteInfo, *, t: int, x: int, w: int, h: int) -> None:
    info.t = int(info.t) + t
    info.x += x
    info.w += w
    info.h += h


def _shift_joint(joint: object, *, t: int, x: int, w: int, h: int) -> None:
    from .joint import Joint

    assert isinstance(joint, Joint)
    joint._info.t = int(joint._info.t) + t
    joint._info.x += x
    joint._info.w += w
    joint._info.h += h


def _shift_attachable_air(air: object, *, t: int, x: int, w: int, h: int) -> None:
    from .air import Air, AirHold, AirSlide

    if isinstance(air, Air):
        return
    if not isinstance(air, (AirSlide, AirHold)):
        raise TypeError(f"expected attachable air, got {type(air).__name__}")
    air._air_info.h += h
    air._info.h += h
    for joint in air._joints:
        _shift_joint(joint, t=t, x=x, w=w, h=h)


def _shift_ground(note: object, *, t: int, x: int, w: int, h: int) -> None:
    from .ground import Damage, Extap, Flick, Tap

    if not isinstance(note, (Tap, Extap, Flick, Damage)):
        raise TypeError(f"expected ground note, got {type(note).__name__}")
    _apply_deltas(note._info, t=t, x=x, w=w, h=h)
    if note._air is not None:
        _shift_attachable_air(note._air, t=t, x=x, w=w, h=h)


def _shift_long_builder(builder: object, *, t: int, x: int, w: int, h: int) -> None:
    from .long import AirCrush, Hold, Slide

    if not isinstance(builder, (Slide, Hold, AirCrush)):
        raise TypeError(f"expected long builder, got {type(builder).__name__}")
    _apply_deltas(builder._info, t=t, x=x, w=w, h=h)
    for joint in builder._joints:
        _shift_joint(joint, t=t, x=x, w=w, h=h)
    if isinstance(builder, (Slide, Hold)) and builder._air is not None:
        _shift_attachable_air(builder._air, t=t, x=x, w=w, h=h)


def _shift_note(note: object, *, t: int, x: int, w: int, h: int) -> object:
    if t == x == w == h == 0:
        return note
    from .ground import Damage, Extap, Flick, Tap
    from .long import AirCrush, Hold, Slide

    if isinstance(note, (Tap, Extap, Flick, Damage)):
        _shift_ground(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, (Slide, Hold, AirCrush)):
        _shift_long_builder(note, t=t, x=x, w=w, h=h)
    else:
        raise TypeError(f"unsupported note type for shift: {type(note).__name__}")
    return note
