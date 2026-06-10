from __future__ import annotations

from collections.abc import Callable

from ..time import Tick, resolve_tick
from .types import NoteInfo

type Delta = int | Callable[[int], int]
type TickDelta = Tick | Callable[[int], int]


def _combine(value: int, delta: Delta) -> int:
    """Apply a delta to a field value: add an int, or map through a callable."""
    if callable(delta):
        return delta(int(value))
    return int(value) + delta


def _combine_tick(value: int, delta: TickDelta) -> int:
    """Apply a tick delta: add a resolved tick, or map through a callable."""
    if callable(delta):
        return delta(int(value))
    return int(value) + resolve_tick(delta)


def _apply_deltas(info: NoteInfo, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    info.t = _combine_tick(info.t, t)
    info.x = _combine(info.x, x)
    info.w = _combine(info.w, w)
    info.h = _combine(info.h, h)


def _shift_joint(joint: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    from .joint import Joint

    assert isinstance(joint, Joint)
    _apply_deltas(joint._info, t=t, x=x, w=w, h=h)


def _shift_attachable_air(air: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    from .air import Air, AirHold, AirSlide

    if isinstance(air, Air):
        _apply_deltas(air._info, t=t, x=x, w=w, h=h)
        return
    if not isinstance(air, (AirSlide, AirHold)):
        raise TypeError(f"expected attachable air, got {type(air).__name__}")
    _apply_deltas(air._info, t=t, x=x, w=w, h=h)
    for joint in air._joints:
        _shift_joint(joint, t=t, x=x, w=w, h=h)


def _shift_ground(note: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    from .ground import Damage, Extap, Flick, Tap

    if not isinstance(note, (Tap, Extap, Flick, Damage)):
        raise TypeError(f"expected ground note, got {type(note).__name__}")
    _apply_deltas(note._info, t=t, x=x, w=w, h=h)
    if note._air is not None:
        _shift_attachable_air(note._air, t=t, x=x, w=w, h=h)


def _shift_long_builder(builder: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    from .long import AirCrush, Hold, Slide

    if not isinstance(builder, (Slide, Hold, AirCrush)):
        raise TypeError(f"expected long builder, got {type(builder).__name__}")
    _apply_deltas(builder._info, t=t, x=x, w=w, h=h)
    for joint in builder._joints:
        _shift_joint(joint, t=t, x=x, w=w, h=h)
    if isinstance(builder, (Slide, Hold)) and builder._air is not None:
        _shift_attachable_air(builder._air, t=t, x=x, w=w, h=h)


def _shift_air_long(note: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> None:
    from .air import AirHold, AirSlide

    if not isinstance(note, (AirSlide, AirHold)):
        raise TypeError(f"expected air long, got {type(note).__name__}")
    _apply_deltas(note._info, t=t, x=x, w=w, h=h)
    for joint in note._joints:
        _shift_joint(joint, t=t, x=x, w=w, h=h)


def _is_noop(delta: TickDelta) -> bool:
    return not callable(delta) and delta == 0


def _check_joint_order(note: object) -> None:
    for obj in (note, getattr(note, "_air", None)):
        if obj is None:
            continue
        info = getattr(obj, "_info", None)
        joints = getattr(obj, "_joints", ())
        if not joints:
            continue
        prev = int(info.t) if info is not None else None
        for j in joints:
            jt = int(j.t)
            if prev is not None and jt <= prev:
                raise ValueError(
                    f"t callable produced non-monotone joint ordering: tick {jt} <= {prev}"
                )
            prev = jt


def _shift_note(note: object, *, t: TickDelta, x: Delta, w: Delta, h: Delta) -> object:
    if _is_noop(t) and _is_noop(x) and _is_noop(w) and _is_noop(h):
        return note
    from .air import Air, AirHold, AirSlide
    from .ground import Damage, Extap, Flick, Tap
    from .long import AirCrush, Hold, Slide

    if isinstance(note, (Tap, Extap, Flick, Damage)):
        _shift_ground(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, (Slide, Hold, AirCrush)):
        _shift_long_builder(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, (AirSlide, AirHold)):
        _shift_air_long(note, t=t, x=x, w=w, h=h)
    elif isinstance(note, Air):
        _apply_deltas(note._info, t=t, x=x, w=w, h=h)
    else:
        raise TypeError(f"unsupported note type for shift: {type(note).__name__}")
    if callable(t):
        _check_joint_order(note)
    return note
