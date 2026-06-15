from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ..constants import DEFAULT_AIRCRUSH_GAP, DEFAULT_H
from ..notes import AirCrush, AirHold, AirSlide, ColorLike, ColorValue, Hold, Slide
from ..time import IntervalLike, PositionLike, resolve_tick
from .easing import EaseLike, Easing, resolve_easing

_LINEAR = resolve_easing("linear")

type SlideLike = Slide | Hold | AirSlide | AirHold | AirCrush
"""A long note whose path (begin + joints) can be loaded into a :class:`Curve`."""


@dataclass(frozen=True, slots=True)
class Waypoint:
    """One control point on a :class:`Curve`: tick, lane, height, and per-axis easing of the incoming leg.

    ``ease_x`` and ``ease_h`` are ignored on the first waypoint (no incoming leg).
    ``h`` is ignored when materializing a ground :class:`Slide`.
    """

    t: int
    x: int
    h: int
    ease_x: Easing = _LINEAR
    ease_h: Easing = _LINEAR


class Curve:
    """A width-agnostic slide path built by chaining eased legs between :class:`Waypoint`s.

    Start with ``Curve(t=..., x=..., h=...)`` then chain :meth:`to` to add legs. Materialize
    to a note with :meth:`to_slide`, :meth:`to_air_slide`, or :meth:`to_air_crush` (each
    applies a constant width ``w``). Load an existing note's path with :meth:`from_note`.

    Args:
        t: Start tick or position tuple.
        x: Start lane.
        h: Start height; defaults to :data:`DEFAULT_H`.
    """

    __slots__ = ("waypoints",)

    waypoints: tuple[Waypoint, ...]

    def __init__(self, *, t: int | PositionLike, x: int, h: int | None = None) -> None:
        self.waypoints = (Waypoint(resolve_tick(t), x, DEFAULT_H if h is None else h),)

    @classmethod
    def _of(cls, waypoints: tuple[Waypoint, ...]) -> Curve:
        """Build a ``Curve`` directly from control waypoints (internal; validates ticks)."""
        if not waypoints:
            raise ValueError("a Curve needs at least one waypoint")
        for a, b in zip(waypoints, waypoints[1:]):
            if b.t <= a.t:
                raise ValueError("waypoint ticks must be strictly increasing")
        self = cls.__new__(cls)
        self.waypoints = waypoints
        return self

    @classmethod
    def from_note(cls, note: SlideLike) -> Curve:
        """Load a slide-like long note's path as editable control waypoints with linear legs.

        Width is dropped; height defaults to :data:`DEFAULT_H` where not present.
        """
        points = [Waypoint(int(note.t), note.x, getattr(note, "h", DEFAULT_H))]
        for joint in note.joints:
            points.append(Waypoint(int(joint.t), joint.x, getattr(joint, "h", DEFAULT_H)))
        return cls._of(tuple(points))

    def __len__(self) -> int:
        return len(self.waypoints)

    def __iter__(self) -> Iterator[Waypoint]:
        return iter(self.waypoints)

    def to(
        self,
        *,
        t: int | PositionLike,
        x: int,
        h: int | None = None,
        ease_x: EaseLike = "linear",
        ease_h: EaseLike = "linear",
    ) -> Curve:
        """Add one eased leg to ``(t, x, h)`` and return the extended curve.

        ``h`` defaults to the current end height (constant-height leg).

        Raises:
            ValueError: If ``t`` is not later than the last waypoint's tick.
        """
        last = self.waypoints[-1]
        t1 = resolve_tick(t)
        if t1 <= last.t:
            raise ValueError("each .to(t=...) must be later than the current end tick")
        h1 = last.h if h is None else h
        waypoint = Waypoint(t1, x, h1, resolve_easing(ease_x), resolve_easing(ease_h))
        return Curve._of((*self.waypoints, waypoint))

    def points(self) -> tuple[Waypoint, ...]:
        """Quantize the path into integer waypoints (useful to preview before materializing).

        Raises:
            ValueError: If the curve has no legs yet (only an anchor).
        """
        if len(self.waypoints) < 2:
            raise ValueError("add at least one .to(...) leg before materializing a Curve")
        out: list[Waypoint] = []
        for a, b in zip(self.waypoints, self.waypoints[1:]):
            leg = _sample_segment(a.t, a.x, a.h, b.t, b.x, b.h, b.ease_x, b.ease_h)
            out.extend(leg[1:] if out else leg)
        return tuple(out)

    def _path(self) -> tuple[Waypoint, list[Waypoint], Waypoint]:
        """Quantize, then split into ``(first, interior, last)`` (always >= 2 points)."""
        first, *mid, last = self.points()
        return first, mid, last

    def to_slide(self, *, w: int, til: int = 0) -> Slide:
        """Materialize as a ground :class:`Slide` of constant width ``w`` (height ignored)."""
        first, mid, last = self._path()
        slide = Slide(t=first.t, x=first.x, w=w)
        slide.til = til
        for wp in mid:
            slide.add_ctrl(t=wp.t, x=wp.x, w=w)
        slide.add_step(t=last.t, x=last.x, w=w)
        return slide

    def to_air_slide(self, *, w: int, til: int = 0) -> AirSlide:
        """Materialize as an :class:`AirSlide` of constant width ``w``."""
        first, mid, last = self._path()
        air = AirSlide(t=first.t, x=first.x, w=w, h=first.h)
        air.til = til
        for wp in mid:
            air.add_ctrl(t=wp.t, x=wp.x, w=w, h=wp.h)
        air.add_step(t=last.t, x=last.x, w=w, h=last.h)
        return air

    def to_air_crush(
        self,
        *,
        w: int,
        gap: int | IntervalLike = DEFAULT_AIRCRUSH_GAP,
        color: ColorLike | int = ColorValue.DEFAULT,
        til: int = 0,
    ) -> AirCrush:
        """Materialize as an :class:`AirCrush` of constant width ``w``."""
        first, mid, last = self._path()
        crush = AirCrush(t=first.t, x=first.x, w=w, h=first.h, gap=gap, color=color)
        crush.til = til
        for wp in (*mid, last):
            crush.add_ctrl(t=wp.t, x=wp.x, w=w, h=wp.h)
        return crush

    def at(self, tick: int) -> Waypoint:
        """Evaluate the eased path at ``tick``, clamped to the curve's endpoints."""
        wps = self.waypoints
        if tick <= wps[0].t:
            return Waypoint(wps[0].t, wps[0].x, wps[0].h)
        if tick >= wps[-1].t:
            return Waypoint(wps[-1].t, wps[-1].x, wps[-1].h)
        for a, b in zip(wps, wps[1:]):
            if a.t <= tick <= b.t:
                p = (tick - a.t) / (b.t - a.t)
                x = round(a.x + b.ease_x.solve(p) * (b.x - a.x))
                h = round(a.h + b.ease_h.solve(p) * (b.h - a.h))
                return Waypoint(tick, x, h)
        return Waypoint(wps[-1].t, wps[-1].x, wps[-1].h)

    def then(self, other: Curve) -> Curve:
        """Concatenate ``other`` after this curve; a shared seam tick is de-duplicated.

        Raises:
            ValueError: If ``other`` starts before this curve ends.
        """
        if other.waypoints[0].t < self.waypoints[-1].t:
            raise ValueError("other curve starts before this curve ends")
        tail = other.waypoints
        if tail[0].t == self.waypoints[-1].t:
            tail = tail[1:]
        return Curve._of((*self.waypoints, *tail))

    def __add__(self, other: Curve) -> Curve:
        return self.then(other)


def _axis_ticks(t0: int, t1: int, v0: int, v1: int, ease: Easing) -> list[int]:
    """Ticks at which an axis going ``v0 -> v1`` (eased) crosses each integer value."""
    if v0 == v1:
        return []
    span = t1 - t0
    dv = v1 - v0
    step = 1 if dv > 0 else -1
    ticks: list[int] = []
    for v in range(v0, v1 + step, step):
        pv = (v - v0) / dv
        progress = min(1.0, max(0.0, ease.inverse(pv)))
        ticks.append(t0 + round(progress * span))
    return ticks


def _driver_ticks(
    t0: int,
    x0: int,
    h0: int,
    t1: int,
    x1: int,
    h1: int,
    ease_x: Easing,
    ease_h: Easing,
) -> list[int]:
    """Candidate ticks from the axis with the smaller integer delta (the "driver").

    Sampling the smaller-delta axis keeps the larger-delta axis smooth under Margrete's linear
    interpolation between joints, avoiding a blocky staircase in the main view.
    """
    dx = abs(x1 - x0)
    dh = abs(h1 - h0)
    if dx == 0 and dh == 0:
        return []
    if dh == 0 or (dx != 0 and dx <= dh):
        return _axis_ticks(t0, t1, x0, x1, ease_x)
    return _axis_ticks(t0, t1, h0, h1, ease_h)


def _sample_segment(
    t0: int,
    x0: int,
    h0: int,
    t1: int,
    x1: int,
    h1: int,
    ease_x: Easing,
    ease_h: Easing,
) -> tuple[Waypoint, ...]:
    """Quantize an eased segment to integer waypoints driven by the smaller-delta axis.

    Consecutive waypoints with identical ``(x, h)`` are dropped; endpoints are always kept.
    """
    if t1 <= t0:
        raise ValueError("segment end tick must be later than its start")
    span = t1 - t0
    candidates = {t0, t1}
    candidates.update(_driver_ticks(t0, x0, h0, t1, x1, h1, ease_x, ease_h))
    ordered = sorted(t for t in candidates if t0 <= t <= t1)

    out: list[Waypoint] = []
    for index, t in enumerate(ordered):
        pt = (t - t0) / span
        x = round(x0 + ease_x.solve(pt) * (x1 - x0))
        h = round(h0 + ease_h.solve(pt) * (h1 - h0))
        is_end = index == len(ordered) - 1
        if out and not is_end and out[-1].x == x and out[-1].h == h:
            continue
        out.append(Waypoint(t, x, h))
    return tuple(out)


__all__ = ["Curve", "SlideLike", "Waypoint"]
