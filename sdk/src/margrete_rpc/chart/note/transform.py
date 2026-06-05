from __future__ import annotations

import copy
import math
from collections.abc import Callable, Iterator, Sequence
from typing import Any, NamedTuple, cast

from ..time import Tick, resolve_tick
from .air import Air, AirHold, AirSlide
from .direction import Direction
from .ground import Damage, Extap, Flick, Tap, _GroundNote
from .joint import AirJoint, Joint
from .long import AirCrush, Hold, Slide
from .shared import AlignMode, Note
from .types import JointKind, JointKindLike

_DEFAULT_AIR_H = 80

type SlideLike = Slide | AirSlide | AirCrush
type LongLike = Slide | Hold | AirSlide | AirHold | AirCrush

_GROUND_TYPES = (Tap, Extap, Flick, Damage)
_MERGEABLE = (Slide, AirSlide, AirCrush)
_SPLITTABLE = (Slide, AirSlide, AirCrush)


class _Point(NamedTuple):
    t: int
    x: int
    w: int
    h: int | None
    kind: JointKind | None


# --------------------------------------------------------------------------- info walk


def _iter_infos(note: Note) -> Iterator[Any]:
    """Yield every ``NoteInfo`` reachable from a note builder (begin, joints, air)."""
    own_air_info = getattr(note, "_air_info", None)
    if own_air_info is not None:
        yield own_air_info
    yield note._info
    for joint in getattr(note, "_joints", ()) or ():
        yield joint._info
    air = getattr(note, "_air", None)
    if air is not None:
        air_info = getattr(air, "_air_info", None)
        if air_info is not None:
            yield air_info
        yield air._info
        for joint in getattr(air, "_joints", ()) or ():
            yield joint._info


# ------------------------------------------------------------------------------- clone


def _detach(note: Note) -> None:
    note._id = None
    for joint in getattr(note, "_joints", ()) or ():
        joint._id = None
    air = getattr(note, "_air", None)
    if air is not None:
        air._id = None
        if hasattr(air, "_air_id"):
            air._air_id = None
        for joint in getattr(air, "_joints", ()) or ():
            joint._id = None


def _clone[N: Note](note: N) -> N:
    new = copy.deepcopy(note)
    _detach(new)
    return new


def _clone_air(air: Air | AirSlide | AirHold) -> Air | AirSlide | AirHold:
    new = copy.deepcopy(air)
    new._id = None
    if hasattr(new, "_air_id"):
        new._air_id = None
    for joint in getattr(new, "_joints", ()) or ():
        joint._id = None
    return new


# -------------------------------------------------------------------------------- flip

_MIRROR_H = {
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
    Direction.UP_LEFT: Direction.UP_RIGHT,
    Direction.UP_RIGHT: Direction.UP_LEFT,
    Direction.DOWN_LEFT: Direction.DOWN_RIGHT,
    Direction.DOWN_RIGHT: Direction.DOWN_LEFT,
    Direction.ROTATE_LEFT: Direction.ROTATE_RIGHT,
    Direction.ROTATE_RIGHT: Direction.ROTATE_LEFT,
}


def _flip(note: Note, field: int) -> Note:
    for info in _iter_infos(note):
        info.x = field - info.x - info.w
        mirrored = _MIRROR_H.get(Direction(int(info.direction)))
        if mirrored is not None:
            info.direction = mirrored
    return note


# ------------------------------------------------------------------------------- align


def _snapper(step: int, mode: AlignMode) -> Callable[[int], int]:
    def snap(value: int) -> int:
        q = value / step
        if mode == "floor":
            n = math.floor(q)
        elif mode == "ceil":
            n = math.ceil(q)
        elif mode == "round":
            n = math.floor(q + 0.5)
        else:
            raise ValueError(f"unknown align mode: {mode!r}")
        return int(n) * step

    return snap


def _align(note: Note, interval: int | Tick, mode: AlignMode) -> Note:
    step = resolve_tick(interval)
    if step <= 0:
        raise ValueError("align interval must be positive")
    return note.shift(t=_snapper(step, mode))


# ------------------------------------------------------------------------------- scale


def _scale(note: Note, factor: float, pivot: int | Tick) -> Note:
    origin = int(resolve_tick(pivot))
    return note.shift(t=lambda v: round(origin + (v - origin) * factor))


# ----------------------------------------------------------------------------- convert


def _convert[T: Note](note: Note, target: type[T], overrides: dict[str, Any]) -> T:
    if not isinstance(target, type):
        raise TypeError("convert target must be a note class")
    if isinstance(note, _GROUND_TYPES) and issubclass(target, _GROUND_TYPES):
        return cast(T, _convert_ground(note, target, overrides))
    if isinstance(note, (Slide, Hold, AirSlide, AirHold)) and issubclass(
        target, (Slide, Hold, AirSlide, AirHold)
    ):
        return cast(T, _convert_long(note, target, overrides))
    raise ValueError(f"cannot convert {type(note).__name__} to {target.__name__}")


def _convert_ground(note: _GroundNote, target: type[Note], overrides: dict[str, Any]) -> Note:
    new = target(int(note.t), note.x, note.w)  # type: ignore[call-arg]
    new._info.til = note._info.til
    new._info.ex_attr = note._info.ex_attr
    if isinstance(new, Extap):
        if "direction" in overrides:
            new.direction = overrides["direction"]
        elif isinstance(note, Extap):
            try:
                new.direction = note.direction
            except (ValueError, TypeError):
                pass
    if getattr(note, "_air", None) is not None:
        new._air = _clone_air(note._air)
    new._id = None
    return new


def _read_long(note: LongLike) -> tuple[_Point, list[_Point]]:
    info = note._info
    begin = _Point(int(info.t), info.x, info.w, info.h, None)
    joints: list[_Point] = []
    for joint in note._joints:
        h = joint.h if isinstance(joint, AirJoint) else None
        joints.append(_Point(int(joint.t), joint.x, joint.w, h, joint.kind))
    return begin, joints


def _add_kind(note: LongLike, kind: JointKindLike | None, t: int, x: int, w: int, h: int) -> None:
    resolved = JointKind(kind) if kind is not None else JointKind.STEP
    if resolved is JointKind.STEP:
        note._add_step(t, x, w, h)
    elif resolved is JointKind.CONTROL:
        note._add_control(t, x, w, h)
    else:
        note._add_curve_control(t, x, w, h)


def _convert_long(note: LongLike, target: type[Note], overrides: dict[str, Any]) -> LongLike:
    begin, joints = _read_long(note)
    if not joints:
        raise ValueError("long note requires at least one joint to convert")
    new: LongLike
    if issubclass(target, (Slide, Hold)):
        new = _build_ground_long(target, begin, joints)
    else:
        new = _build_air_long(note, target, begin, joints, overrides)
    new._info.til = note._info.til
    new._id = None
    return new


def _build_ground_long(target: type[Note], begin: _Point, joints: list[_Point]) -> Slide | Hold:
    if issubclass(target, Hold):
        end = joints[-1]
        hold = Hold(begin.t, begin.x, begin.w)
        hold._add_step(end.t, end.x, end.w, 800)
        return hold
    slide = Slide(begin.t, begin.x, begin.w)
    for point in joints:
        _add_kind(slide, point.kind, point.t, point.x, point.w, 800)
    return slide


def _build_air_long(
    note: LongLike,
    target: type[Note],
    begin: _Point,
    joints: list[_Point],
    overrides: dict[str, Any],
) -> AirSlide | AirHold:
    is_air_source = isinstance(note, (AirSlide, AirHold))
    h0 = overrides.get("h")
    if h0 is None:
        h0 = begin.h if is_air_source else _DEFAULT_AIR_H
    new: AirSlide | AirHold = AirSlide(h=h0) if issubclass(target, AirSlide) else AirHold(h=h0)
    new._info.t = begin.t
    new._info.x = begin.x
    new._info.w = begin.w
    if "direction" in overrides:
        new._air_info.direction = overrides["direction"]
    elif isinstance(note, (AirSlide, AirHold)):
        new._air_info.direction = note._air_info.direction
    for point in joints:
        jh = point.h if point.h is not None else h0
        _add_kind(new, point.kind, point.t, point.x, point.w, jh)
    return new


# ------------------------------------------------------------------------------- merge


def _joint_h(point: _Point) -> int:
    return point.h if point.h is not None else 800


def _resolve_join[T: SlideLike](
    join: JointKindLike | Callable[[T, T], JointKindLike],
    prev: T,
    nxt: T,
    note_type: type,
) -> JointKind:
    if note_type is AirCrush:
        return JointKind.CONTROL
    if callable(join):
        return JointKind(join(prev, nxt))
    return JointKind(join)


def merge[T: SlideLike](
    notes: Sequence[T],
    *,
    join: JointKindLike | Callable[[T, T], JointKindLike] = JointKind.STEP,
) -> T:
    """Combine slides / air-slides / air-crushes into one."""
    items = list(notes)
    if not items:
        raise ValueError("merge requires at least one note")
    note_type = type(items[0])
    if not isinstance(items[0], _MERGEABLE):
        raise TypeError(
            f"cannot merge {note_type.__name__}; merge supports Slide, AirSlide, AirCrush"
        )
    for note in items:
        if type(note) is not note_type:
            raise TypeError("all notes to merge must be the same type")
        if not note._joints:
            raise ValueError("each note to merge must have at least one joint")
    items.sort(key=lambda note: int(note._info.t))
    for prev, nxt in zip(items, items[1:]):
        if int(nxt._info.t) < int(prev._joints[-1].t):
            raise ValueError("notes to merge must not overlap")

    result = _clone(items[0])
    for prev, nxt in zip(items, items[1:]):
        seam = _resolve_join(join, prev, nxt, note_type)
        result._joints[-1].kind = seam
        if int(nxt._info.t) > int(result._joints[-1].t):
            nb_h = int(nxt._info.h) if isinstance(nxt, (AirSlide, AirCrush)) else 800
            _add_kind(result, seam, int(nxt._info.t), nxt._info.x, nxt._info.w, nb_h)
        for joint in nxt._joints:
            jh = joint.h if isinstance(joint, AirJoint) else 800
            _add_kind(result, joint.kind, int(joint.t), joint.x, joint.w, jh)
    result.validate()
    return result


# ------------------------------------------------------------------------------- split


def _interpolate(a: _Point, b: _Point, ts: int) -> _Point:
    span = b.t - a.t
    f = (ts - a.t) / span
    x = round(a.x + (b.x - a.x) * f)
    w = max(1, round(a.w + (b.w - a.w) * f))
    if a.h is not None and b.h is not None:
        h: int | None = round(a.h + (b.h - a.h) * f)
    else:
        h = a.h if a.h is not None else b.h
    return _Point(ts, x, w, h, None)


def _locate_split(
    note: SlideLike, begin: _Point, joints: list[_Point], at: Joint | int | Tick
) -> tuple[_Point, list[_Point], list[_Point]]:
    if isinstance(at, Joint):
        try:
            idx = note._joints.index(at)
        except ValueError as exc:
            raise ValueError("split joint is not part of this note") from exc
        if idx == len(joints) - 1:
            raise ValueError("cannot split at the final joint")
        return joints[idx], joints[:idx], joints[idx + 1 :]

    ts = int(resolve_tick(at))
    if not begin.t < ts < joints[-1].t:
        raise ValueError("split tick must fall strictly inside the note")
    for idx, point in enumerate(joints):
        if point.t == ts:
            if idx == len(joints) - 1:
                raise ValueError("cannot split at the final joint")
            return point, joints[:idx], joints[idx + 1 :]
    anchors = [begin, *joints]
    for a, b in zip(anchors, anchors[1:]):
        if a.t < ts < b.t:
            split_point = _interpolate(a, b, ts)
            left = [p for p in joints if p.t < ts]
            right = [p for p in joints if p.t > ts]
            return split_point, left, right
    raise ValueError("could not locate split segment")


def split[T: SlideLike](note: T, at: Joint | int | Tick) -> tuple[T, T]:
    """Divide a slide / air-slide / air-crush into two at a joint or tick."""
    if not isinstance(note, _SPLITTABLE):
        raise TypeError(
            f"cannot split {type(note).__name__}; split supports Slide, AirSlide, AirCrush"
        )
    if len(note._joints) < 2:
        raise ValueError("note must have at least two joints to split")

    begin, joints = _read_long(note)
    split_point, left, right = _locate_split(note, begin, joints, at)

    if isinstance(note, AirCrush):
        first_end = JointKind.CONTROL
    elif split_point.kind in (JointKind.STEP, JointKind.CONTROL):
        first_end = split_point.kind
    else:
        first_end = JointKind.STEP

    first = _new_long_like(note, begin)
    for point in left:
        _add_kind(first, point.kind, point.t, point.x, point.w, _joint_h(point))
    _add_kind(first, first_end, split_point.t, split_point.x, split_point.w, _joint_h(split_point))

    second_begin = _Point(split_point.t, split_point.x, split_point.w, split_point.h, None)
    second = _new_long_like(note, second_begin)
    for point in right:
        _add_kind(second, point.kind, point.t, point.x, point.w, _joint_h(point))

    first.validate()
    second.validate()
    return cast(T, first), cast(T, second)


def _new_long_like(note: SlideLike, point: _Point) -> SlideLike:
    if isinstance(note, Slide):
        new: SlideLike = Slide(point.t, point.x, point.w)
    elif isinstance(note, AirCrush):
        h = point.h if point.h is not None else int(note._info.h)
        new = AirCrush(point.t, point.x, point.w, h=h, density=note.density, color=note.color)
    elif isinstance(note, AirSlide):
        h = point.h if point.h is not None else int(note._info.h)
        air = AirSlide(h=h)
        air._info.t = point.t
        air._info.x = point.x
        air._info.w = point.w
        air._air_info.direction = note._air_info.direction
        new = air
    else:
        raise TypeError(f"cannot rebuild {type(note).__name__}")
    new._info.til = note._info.til
    return new


__all__ = ["merge", "split"]
