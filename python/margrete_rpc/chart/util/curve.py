from __future__ import annotations

from array import array
from collections.abc import Iterator
from math import fsum, inf
from typing import Literal, TypeAlias

from ..constants import DEFAULT_AIRCRUSH_GAP, DEFAULT_H
from ..notes import AirCrush, AirHold, AirSlide, ColorLike, ColorValue, Hold, Slide
from ..time import DivisionLike, Position, PositionLike, resolve_division, resolve_tick, tick_to_pos
from .easing import EaseLike, Easing, resolve_easing

_LINEAR = resolve_easing("linear")

CurveMode: TypeAlias = Literal["smooth", "stair"]
"""How a curve is sampled into note joints."""

SlideLike: TypeAlias = Slide | Hold | AirSlide | AirHold | AirCrush
"""A long note whose path (begin + joints) can be loaded into a :class:`Curve`."""


class Waypoint:
    """One control point on a :class:`Curve`: tick, lane, height, and per-axis leg easing.

    ``ease_x`` and ``ease_h`` are ignored on the first waypoint (no incoming leg).
    """

    __slots__ = ("_ease_h", "_ease_x", "_t", "h", "x")

    _t: int
    x: int
    h: int
    _ease_x: Easing
    _ease_h: Easing

    def __init__(
        self,
        t: int | PositionLike,
        x: int,
        h: int,
        ease_x: EaseLike = _LINEAR,
        ease_h: EaseLike = _LINEAR,
    ) -> None:
        self.t = t
        self.x = x
        self.h = h
        self.ease_x = ease_x
        self.ease_h = ease_h

    @property
    def t(self) -> int:
        return self._t

    @t.setter
    def t(self, value: int | PositionLike) -> None:
        self._t = resolve_tick(value)

    @property
    def p(self) -> Position:
        """Timing as a ``(bar, beat, offset)`` :class:`Position`; the read-only view of ``t``."""
        return tick_to_pos(self.t)

    @property
    def ease_x(self) -> Easing:
        return self._ease_x

    @ease_x.setter
    def ease_x(self, value: EaseLike) -> None:
        self._ease_x = resolve_easing(value)

    @property
    def ease_h(self) -> Easing:
        return self._ease_h

    @ease_h.setter
    def ease_h(self, value: EaseLike) -> None:
        self._ease_h = resolve_easing(value)

    def __repr__(self) -> str:
        return (
            f"Waypoint(t={self.t!r}, x={self.x!r}, h={self.h!r}, "
            f"ease_x={self.ease_x!r}, ease_h={self.ease_h!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Waypoint):
            return NotImplemented
        return (
            self.t == other.t
            and self.x == other.x
            and self.h == other.h
            and self.ease_x == other.ease_x
            and self.ease_h == other.ease_h
        )


class Curve:
    """A width-agnostic slide path built by chaining eased legs between :class:`Waypoint`s.

    Start with ``Curve(t=..., x=..., h=...)`` then chain :meth:`to` to add legs. Materialize
    to a note with :meth:`to_slide`, :meth:`to_air_slide`, or :meth:`to_air_crush` (each
    applies a constant width ``w``). Load an existing note's path with :meth:`from_note`.

    Args:
        t: Start tick or tuple.
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

    def _copy(self) -> Curve:
        """Copy control waypoints so edits to a derived curve cannot change its source."""
        return Curve._of(
            tuple(Waypoint(wp.t, wp.x, wp.h, wp.ease_x, wp.ease_h) for wp in self.waypoints)
        )

    @classmethod
    def from_note(cls, note: SlideLike) -> Curve:
        """Load a long note's path as editable control waypoints with linear legs.

        Args:
            note: A :class:`Slide`, :class:`Hold`, :class:`AirSlide`, :class:`AirHold`,
                or :class:`AirCrush`.

        Returns:
            A new :class:`Curve` spanning the note's begin point through its joints.
            Width is dropped; height defaults to :data:`DEFAULT_H` where not present.
        """
        points = [Waypoint(int(note.t), note.x, _stored_height(note))]
        for joint in note.joints:
            points.append(Waypoint(int(joint.t), joint.x, _stored_height(joint)))
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

        Args:
            t: Target tick or tuple.
            x: Target lane.
            h: Target height; defaults to the current end height (constant-height leg).
            ease_x: Lane easing for this leg.
            ease_h: Height easing for this leg.

        Returns:
            A new :class:`Curve` with this leg appended.

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

    def points(
        self,
        *,
        grid: int | None = None,
        mode: CurveMode = "smooth",
        interval: int | DivisionLike | None = None,
        ramp: int | None = None,
    ) -> tuple[Waypoint, ...]:
        """Quantize the path into integer waypoints.

        Auto smooth sampling fits both axes within half a unit at the grid samples.
        Flat endpoint approaches are added when they improve the fit.
        Joint positions are refined against finer samples, constraining each leg's
        error and slope variation on both axes while keeping turns and pauses fixed.

        Args:
            grid: Auto-sampling tick grid; omitted uses ``5``. Mutually exclusive with ``interval``.
            mode: ``"smooth"`` follows the curve; ``"stair"`` keeps integer plateaus
                linked by short ramps, including for linear legs.
            interval: Fixed spacing in ticks or a whole-note fraction, e.g. ``(1, 16)``.
                Measured from the curve start across all legs; ``None`` uses auto sampling.
            ramp: Duration of the sloped segment between steps, in ticks (default ``5``).
                Requires ``mode="stair"`` and ``interval``; capped by the gap between samples.

        Returns:
            All sampled waypoints in order; useful to preview the realized joints before
            calling a ``to_*`` materializer.

        Raises:
            ValueError: If the curve has no legs, a duration is non-positive, or options are invalid.
            TypeError: If a duration does not resolve to an integer.
        """
        if len(self.waypoints) < 2:
            raise ValueError("add at least one .to(...) leg before materializing a Curve")
        if grid is not None and interval is not None:
            raise ValueError("grid and interval are mutually exclusive")
        if mode not in ("smooth", "stair"):
            raise ValueError(f"unknown curve mode: {mode!r}")
        if ramp is not None:
            if interval is None or mode != "stair":
                raise ValueError("ramp requires mode='stair' and interval")
            if type(ramp) is not int:
                raise TypeError("ramp must be an int")
            if ramp < 1:
                raise ValueError("ramp must be at least 1")
        if interval is not None:
            step = resolve_division(interval)
            if type(step) is not int:
                raise TypeError("interval must be an int or a (numerator, denominator) tuple")
            if step < 1:
                raise ValueError("interval must be positive")
            return _sample_interval(self.waypoints, step, 5 if ramp is None else ramp, mode)
        grid = 5 if grid is None else grid
        if type(grid) is not int:
            raise TypeError("grid must be an int")
        if grid < 1:
            raise ValueError("grid must be at least 1")
        out: list[Waypoint] = []
        for a, b in zip(self.waypoints, self.waypoints[1:]):
            leg = _sample_segment(a.t, a.x, a.h, b.t, b.x, b.h, b.ease_x, b.ease_h, grid, mode)
            out.extend(leg[1:] if out else leg)
        return tuple(out)

    def _path(
        self,
        grid: int | None,
        mode: CurveMode,
        interval: int | DivisionLike | None,
        ramp: int | None,
    ) -> tuple[Waypoint, list[Waypoint], Waypoint]:
        """Quantize, then split into ``(first, interior, last)`` (always >= 2 points)."""
        first, *mid, last = self.points(grid=grid, mode=mode, interval=interval, ramp=ramp)
        return first, mid, last

    def to_slide(
        self,
        *,
        w: int,
        til: int = 0,
        grid: int | None = None,
        mode: CurveMode = "smooth",
        interval: int | DivisionLike | None = None,
        ramp: int | None = None,
    ) -> Slide:
        """Materialize as a ground :class:`Slide`.

        Args:
            w: Constant lane width for every joint.
            til: Timeline index assigned to the note.
            grid: Auto-sampling tick grid; mutually exclusive with ``interval``. See :meth:`points`.
            mode: ``"smooth"`` (default) or ``"stair"``. See :meth:`points`.
            interval: Fixed sampling spacing; ``None`` for automatic. See :meth:`points`.
            ramp: Duration of the sloped segment between steps, in ticks. See :meth:`points`.

        Returns:
            A :class:`Slide` whose joints follow the quantized path. Height is preserved
            in the underlying raw note fields.
        """
        first, mid, last = self._path(grid, mode, interval, ramp)
        slide = Slide(t=first.t, x=first.x, w=w)
        slide._info.h = first.h
        slide.til = til
        for wp in mid:
            slide.add_ctrl(t=wp.t, x=wp.x, w=w)
            slide.joints[-1]._info.h = wp.h
        slide.add_step(t=last.t, x=last.x, w=w)
        slide.joints[-1]._info.h = last.h
        return slide

    def to_air_slide(
        self,
        *,
        w: int,
        til: int = 0,
        grid: int | None = None,
        mode: CurveMode = "smooth",
        interval: int | DivisionLike | None = None,
        ramp: int | None = None,
    ) -> AirSlide:
        """Materialize as an :class:`AirSlide`.

        Args:
            w: Constant lane width for every joint.
            til: Timeline index assigned to the note.
            grid: Auto-sampling tick grid; mutually exclusive with ``interval``. See :meth:`points`.
            mode: ``"smooth"`` (default) or ``"stair"``. See :meth:`points`.
            interval: Fixed sampling spacing; ``None`` for automatic. See :meth:`points`.
            ramp: Duration of the sloped segment between steps, in ticks. See :meth:`points`.

        Returns:
            An :class:`AirSlide` whose joints follow the quantized path.
        """
        first, mid, last = self._path(grid, mode, interval, ramp)
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
        gap: int | DivisionLike = DEFAULT_AIRCRUSH_GAP,
        color: ColorLike | int = ColorValue.DEFAULT,
        til: int = 0,
        grid: int | None = None,
        mode: CurveMode = "smooth",
        interval: int | DivisionLike | None = None,
        ramp: int | None = None,
    ) -> AirCrush:
        """Materialize as an :class:`AirCrush`.

        Args:
            w: Constant lane width for every joint.
            gap: Segment gap. Also accepts
                :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_TRACELIKE` and
                :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_HEADONLY`.
            color: Crush particle color.
            til: Timeline index assigned to the note.
            grid: Auto-sampling tick grid; mutually exclusive with ``interval``. See :meth:`points`.
            mode: ``"smooth"`` (default) or ``"stair"``. See :meth:`points`.
            interval: Fixed sampling spacing; ``None`` for automatic. See :meth:`points`.
            ramp: Duration of the sloped segment between steps, in ticks. See :meth:`points`.

        Returns:
            An :class:`AirCrush` whose joints follow the quantized path.
        """
        first, mid, last = self._path(grid, mode, interval, ramp)
        crush = AirCrush(t=first.t, x=first.x, w=w, h=first.h, gap=gap, color=color)
        crush.til = til
        for wp in (*mid, last):
            crush.add_ctrl(t=wp.t, x=wp.x, w=w, h=wp.h)
        return crush

    def at(self, tick: int) -> Waypoint:
        """Evaluate the eased path at ``tick``, rounding lane and height to integers.

        Use :meth:`points` for joint generation; dense ``at()`` samples can form a staircase.

        Args:
            tick: The tick to evaluate; clamped to ``[first.t, last.t]``.

        Returns:
            A :class:`Waypoint` with interpolated ``(x, h)`` at ``tick``.
        """
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
        """Concatenate ``other`` after this curve.

        Args:
            other: The curve to append; may share the seam tick with this curve's end.

        Returns:
            A new :class:`Curve` with ``other``'s waypoints appended; a shared seam tick
            is de-duplicated.

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


_LINEAR_TOL = 1e-9
"""Float-noise tolerance for linearity and pause detection."""


def _sample_interval(
    waypoints: tuple[Waypoint, ...], interval: int, ramp: int, mode: CurveMode
) -> tuple[Waypoint, ...]:
    """Keep fixed samples and anchors, adding a short ramp before each stair change."""
    first = waypoints[0]
    samples = [Waypoint(first.t, first.x, first.h)]
    for a, b in zip(waypoints, waypoints[1:]):
        if b.t <= a.t:
            raise ValueError("waypoint ticks must be strictly increasing")
        start = first.t + ((a.t - first.t) // interval + 1) * interval
        for t in range(start, b.t, interval):
            p = (t - a.t) / (b.t - a.t)
            x = round(a.x + b.ease_x.solve(p) * (b.x - a.x))
            h = round(a.h + b.ease_h.solve(p) * (b.h - a.h))
            samples.append(Waypoint(t, x, h))
        samples.append(Waypoint(b.t, b.x, b.h))
    if mode == "smooth":
        return tuple(samples)

    out = [samples[0]]
    for a, b in zip(samples, samples[1:]):
        ramp_start = b.t - ramp
        if ramp_start > a.t and (a.x, a.h) != (b.x, b.h):
            out.append(Waypoint(ramp_start, a.x, a.h))
        out.append(b)
    return tuple(out)


def _collinear(a: Waypoint, b: Waypoint, c: Waypoint) -> bool:
    """Whether ``b`` lies exactly on segment ``a -> c`` on both the x and h axes (integers).

    Uses integer cross-products so the test is exact: dropping such a ``b`` leaves Margrete's
    linear reconstruction unchanged (a lossless simplification).
    """
    dt_ab, dt_ac = b.t - a.t, c.t - a.t
    return (b.x - a.x) * dt_ac == (c.x - a.x) * dt_ab and (b.h - a.h) * dt_ac == (c.h - a.h) * dt_ab


def _is_linear(reals: list[tuple[int, float, float]]) -> bool:
    """Whether every real sample lies on the chord between the endpoints (both axes)."""
    ta, xa, ha = reals[0]
    tc, xc, hc = reals[-1]
    dt = tc - ta
    for t, x, h in reals[1:-1]:
        f = (t - ta) / dt
        if abs(x - (xa + f * (xc - xa))) > _LINEAR_TOL:
            return False
        if abs(h - (ha + f * (hc - ha))) > _LINEAR_TOL:
            return False
    return True


def _drop_collinear(pts: list[Waypoint]) -> tuple[Waypoint, ...]:
    """Drop interior waypoints that lie exactly on the chord through their neighbours.

    Keeps the running kept point as the anchor so an entire collinear run collapses, leaving
    Margrete's linear reconstruction unchanged (a lossless simplification).
    """
    out = [pts[0]]
    for cur, nxt in zip(pts[1:-1], pts[2:]):
        if not _collinear(out[-1], cur, nxt):
            out.append(cur)
    out.append(pts[-1])
    return tuple(out)


def _pause_boundary(a: float, b: float, c: float) -> bool:
    """Detect entry to or exit from a real plateau, ignoring floating-point noise."""
    return (a == b and abs(c - b) > _LINEAR_TOL) or (b == c and abs(b - a) > _LINEAR_TOL)


def _sample_segment(
    t0: int,
    x0: int,
    h0: int,
    t1: int,
    x1: int,
    h1: int,
    ease_x: Easing,
    ease_h: Easing,
    grid: int = 1,
    mode: CurveMode = "smooth",
) -> tuple[Waypoint, ...]:
    """Sample eased geometry in the requested mode, keeping endpoints exact."""
    if t1 <= t0:
        raise ValueError("segment end tick must be later than its start")
    span = t1 - t0
    interior = range(((t0 // grid) + 1) * grid, t1, grid)
    reals = [
        (
            t,
            x0 + ease_x.solve((t - t0) / span) * (x1 - x0),
            h0 + ease_h.solve((t - t0) / span) * (h1 - h0),
        )
        for t in interior
    ]
    reals = [(t0, float(x0), float(h0)), *reals, (t1, float(x1), float(h1))]
    if mode == "stair":
        return _drop_collinear([Waypoint(t, round(x), round(h)) for t, x, h in reals])
    if _is_linear(reals):
        return (Waypoint(t0, x0, h0), Waypoint(t1, x1, h1))

    # Retain lane crossings when lanes are the coarser axis; height-only paths
    # need error-based spacing instead of a joint for every integer height.
    dx, dh = abs(x1 - x0), abs(h1 - h0)
    keep_lanes = dx > 0 and (dh == 0 or dx <= dh)
    last_x = x0
    anchors = [0]
    fixed = {t0, t1}
    for i, ((_, px, ph), (_, rx, rh), (_, qx, qh)) in enumerate(
        zip(reals, reals[1:], reals[2:]), 1
    ):
        turns_x = px < rx > qx or px > rx < qx
        turns_h = ph < rh > qh or ph > rh < qh
        pause = _pause_boundary(px, rx, qx) or _pause_boundary(ph, rh, qh)
        crossing = keep_lanes and (rx >= last_x + 1 or rx <= last_x - 1)
        if turns_x or turns_h or pause or crossing:
            anchors.append(i)
            last_x = round(rx)
        if turns_x or turns_h or pause:
            fixed.add(reals[i][0])
    anchors.append(len(reals) - 1)

    pts = [Waypoint(t0, x0, h0)]
    for start, end in zip(anchors, anchors[1:]):
        pts.extend(_fit_samples(reals[start : end + 1])[1:])
    _fit_endpoints(pts, reals)
    pts = list(_drop_collinear(pts))
    _refine_points(pts, fixed, grid, ease_x, ease_h)
    return _drop_collinear(pts)


def _fit_samples(reals: list[tuple[int, float, float]]) -> list[Waypoint]:
    """Fit long quantized chords within half a unit on both axes at each grid sample."""
    t, x, h = reals[0]
    out = [Waypoint(t, round(x), round(h))]
    start = 0
    while start < len(reals) - 1:
        a = out[-1]
        low_x = low_h = -inf
        high_x = high_h = inf
        end = start + 1
        for i in range(start + 1, len(reals)):
            t, x, h = reals[i]
            dt = t - a.t
            sx, sh = (round(x) - a.x) / dt, (round(h) - a.h) / dt
            if (
                low_x - _LINEAR_TOL / dt <= sx <= high_x + _LINEAR_TOL / dt
                and low_h - _LINEAR_TOL / dt <= sh <= high_h + _LINEAR_TOL / dt
            ):
                end = i
            # Every intervening sample constrains the slope of future chords.
            low_x = max(low_x, (x - a.x - 0.5) / dt)
            high_x = min(high_x, (x - a.x + 0.5) / dt)
            low_h = max(low_h, (h - a.h - 0.5) / dt)
            high_h = min(high_h, (h - a.h + 0.5) / dt)
            if low_x > high_x or low_h > high_h:
                break
        t, x, h = reals[end]
        out.append(Waypoint(t, round(x), round(h)))
        start = end
    return out


def _fit_endpoints(pts: list[Waypoint], reals: list[tuple[int, float, float]]) -> None:
    """Add flat endpoint approaches when they reduce squared reconstruction error."""
    a, b = pts[-2:]
    tail = [(t - a.t, x, h) for t, x, h in reals if a.t <= t <= b.t]
    offset = _fit_tail(tail)
    if offset is not None:
        pts.insert(-1, Waypoint(a.t + offset, b.x, b.h))

    a, b = pts[:2]
    head = [(b.t - t, x, h) for t, x, h in reversed(reals) if a.t <= t <= b.t]
    offset = _fit_tail(head)
    if offset is not None:
        pts.insert(1, Waypoint(b.t - offset, a.x, a.h))


def _fit_tail(reals: list[tuple[int, float, float]]) -> int | None:
    """Choose a grid-aligned terminal plateau using prefix sums for squared error."""
    _, x0, h0 = reals[0]
    _, x1, h1 = reals[-1]
    x0, h0, x1, h1 = round(x0), round(h0), round(x1), round(h1)
    dx, dh = x1 - x0, h1 - h0
    if dx == dh == 0:
        return None

    terminal = len(reals) - 1
    while terminal > 0 and (round(reals[terminal - 1][1]), round(reals[terminal - 1][2])) == (
        x1,
        h1,
    ):
        terminal -= 1

    low_x = low_h = -inf
    high_x = high_h = inf
    sum_t = sum_t2 = sum_p = sum_tp = 0.0
    best_score = inf
    best_tick = None
    baseline = 0.0
    for i, (t, x, h) in enumerate(reals):
        projection = (x0 - x1) * (x - x1) + (h0 - h1) * (h - h1)
        sum_t += t
        sum_t2 += t * t
        sum_p += projection
        sum_tp += t * projection
        if t == 0:
            continue
        # The omitted sum of squared real values is common to all candidates.
        score = (dx * dx + dh * dh) * (i + 1 - 2 * sum_t / t + sum_t2 / (t * t)) - 2 * (
            sum_p - sum_tp / t
        )
        if i == len(reals) - 1:
            baseline = score
        elif (
            i >= terminal
            and low_x - _LINEAR_TOL / t <= dx / t <= high_x + _LINEAR_TOL / t
            and low_h - _LINEAR_TOL / t <= dh / t <= high_h + _LINEAR_TOL / t
            and score < best_score
        ):
            best_score, best_tick = score, t
        low_x = max(low_x, (x - x0 - 0.5) / t)
        high_x = min(high_x, (x - x0 + 0.5) / t)
        low_h = max(low_h, (h - h0 - 0.5) / t)
        high_h = min(high_h, (h - h0 + 0.5) / t)
    return best_tick if best_score < baseline - _LINEAR_TOL * max(1, abs(baseline)) else None


def _slope_variation(points: list[Waypoint]) -> tuple[float, float]:
    slopes = [
        ((b.x - a.x) / (b.t - a.t), (b.h - a.h) / (b.t - a.t)) for a, b in zip(points, points[1:])
    ]
    return (
        sum(abs(b[0] - a[0]) for a, b in zip(slopes, slopes[1:])),
        sum(abs(b[1] - a[1]) for a, b in zip(slopes, slopes[1:])),
    )


def _local_variation(
    left: tuple[float, float],
    right: tuple[float, float],
    before: tuple[float, float] | None,
    after: tuple[float, float] | None,
) -> tuple[float, float]:
    x, h = abs(right[0] - left[0]), abs(right[1] - left[1])
    if before is not None:
        x, h = abs(left[0] - before[0]) + x, abs(left[1] - before[1]) + h
    if after is not None:
        x, h = x + abs(after[0] - right[0]), h + abs(after[1] - right[1])
    return x, h


class _ErrorSums:
    """Conservative squared-error bounds for pruning; accepted moves still use exact scans."""

    def __init__(self, ticks: list[int], reals: list[tuple[float, float]]) -> None:
        self.start, self.span = ticks[0], ticks[-1] - ticks[0]
        self.origin = reals[0]
        self.extent = tuple(max(abs(p[axis] - self.origin[axis]) for p in reals) for axis in (0, 1))
        self.roundoff = (len(ticks) + 16) * 2.0**-48
        # Weighted sums of u, u², x, x², ux, h, h², uh; u is relative leg time.
        previous = (0.0,) * 8
        sums = array("d", previous)
        for i, (t, end) in enumerate(zip(ticks, ticks[1:])):
            u, w = (t - self.start) / self.span, end - t
            x, h = reals[i][0] - self.origin[0], reals[i][1] - self.origin[1]
            values = (u, u * u, x, x * x, u * x, h, h * h, u * h)
            previous = tuple(a + w * b for a, b in zip(previous, values))
            sums.extend(previous)
        self.sums = sums

    def lower_bounds(self, a: Waypoint, b: Waypoint, lo: int, hi: int) -> tuple[float, float]:
        start, end = self.sums[lo * 8 : lo * 8 + 8], self.sums[hi * 8 : hi * 8 + 8]
        dt = b.t - a.t
        u = (a.t - self.start) / self.span
        su, suu = end[0] - start[0], end[1] - start[1]
        bounds = []
        for axis, offset, va, vb in ((0, 2, a.x, b.x), (1, 5, a.h, b.h)):
            if end[offset + 1] == 0 and va == vb == self.origin[axis]:
                bounds.append(0.0)
                continue
            slope = (vb - va) * self.span / dt
            intercept = va - self.origin[axis] - slope * u
            sv, svv, suv = (end[j] - start[j] for j in range(offset, offset + 3))
            terms = (
                intercept * intercept * dt,
                2 * intercept * slope * su,
                slope * slope * suu,
                -2 * intercept * sv,
                svv,
                -2 * slope * suv,
            )
            # Include prefix cancellation and coefficient rounding in the bound.
            scale = (
                abs(terms[0])
                + 2 * abs(intercept * slope) * (abs(start[0]) + abs(end[0]))
                + slope * slope * (abs(start[1]) + abs(end[1]))
                + 2 * abs(intercept) * (abs(start[offset]) + abs(end[offset]))
                + abs(start[offset + 1])
                + abs(end[offset + 1])
                + 2 * abs(slope) * (abs(start[offset + 2]) + abs(end[offset + 2]))
            )
            # The exact scan adds the absolute coordinate before subtracting the
            # sample. Account for that rounding too, especially far from zero.
            residual = (
                max(abs(va - self.origin[axis]), abs(vb - self.origin[axis])) + self.extent[axis]
            )
            rounding = 2.0**-48 * (
                abs(va) + abs(vb - va) + abs(self.origin[axis]) + self.extent[axis]
            )
            bounds.append(
                fsum(terms)
                - self.roundoff * max(1.0, scale)
                - dt * rounding * (2 * residual + rounding)
            )
        return bounds[0], bounds[1]


def _refine_points(
    pts: list[Waypoint], fixed: set[int], grid: int, ease_x: Easing, ease_h: Easing
) -> None:
    """Move grid joints to reduce error without worsening either axis or its slope variation."""
    if len(pts) <= 2:
        return
    first, last = pts[0], pts[-1]
    start_tick = first.t
    span = last.t - start_tick
    # Check between grid samples without expanding coarse, long legs to every tick.
    check_step = max(1, min(grid // 4, span // 4096))
    ticks = sorted(
        set(range(start_tick, last.t, check_step))
        | set(range((start_tick // grid + 1) * grid, last.t, grid))
        | {last.t}
    )
    sample_index = {t: i for i, t in enumerate(ticks)}
    reals = [
        (
            first.x + ease_x.solve((t - start_tick) / span) * (last.x - first.x),
            first.h + ease_h.solve((t - start_tick) / span) * (last.h - first.h),
        )
        for t in ticks
    ]
    reals[0], reals[-1] = (float(first.x), float(first.h)), (float(last.x), float(last.h))
    error_sums = _ErrorSums(ticks, reals)
    vertices = {p.t: p for p in pts}

    # Each axis records time-weighted squared error, probe peak and grid peak.
    cache: dict[tuple[int, int], tuple[tuple[float, float, float], ...]] = {}
    bound_cache: dict[tuple[int, int], tuple[float, float]] = {}
    limits: tuple[tuple[float, float, float], ...] | None = None

    def lower_bound(a: Waypoint, b: Waypoint) -> tuple[float, float]:
        key = (a.t, b.t)
        if key in cache:
            exact = cache[key]
            return exact[0][0], exact[1][0]
        if key not in bound_cache:
            bound_cache[key] = error_sums.lower_bounds(a, b, sample_index[a.t], sample_index[b.t])
        return bound_cache[key]

    def error(a: Waypoint, b: Waypoint) -> tuple[tuple[float, float, float], ...]:
        key = (a.t, b.t)
        if key not in cache:
            ta, tb = key
            dt = tb - ta
            sx, sh = (b.x - a.x) / dt, (b.h - a.h) / dt
            ax, ah = a.x, a.h
            bound_x, bound_h = (limits[0][1], limits[1][1]) if limits else (inf, inf)
            bound_grid_x, bound_grid_h = (limits[0][2], limits[1][2]) if limits else (inf, inf)
            square_x = square_h = peak_x = peak_h = grid_x = grid_h = 0.0
            for j in range(sample_index[ta], sample_index[tb] + 1):
                t = ticks[j]
                x, h = reals[j]
                ex, eh = abs(ax + (t - ta) * sx - x), abs(ah + (t - ta) * sh - h)
                if (
                    ex > bound_x + _LINEAR_TOL
                    or eh > bound_h + _LINEAR_TOL
                    or (
                        t % grid == 0
                        and (ex > bound_grid_x + _LINEAR_TOL or eh > bound_grid_h + _LINEAR_TOL)
                    )
                ):
                    cache[key] = ((inf, inf, inf), (inf, inf, inf))
                    return cache[key]
                # Count a shared joint once in the path's squared error.
                if t < tb:
                    weight = ticks[j + 1] - t
                    square_x += ex * ex * weight
                    square_h += eh * eh * weight
                if ex > peak_x:
                    peak_x = ex
                if eh > peak_h:
                    peak_h = eh
                if t % grid == 0:
                    if ex > grid_x:
                        grid_x = ex
                    if eh > grid_h:
                        grid_h = eh
            cache[key] = ((square_x, peak_x, grid_x), (square_h, peak_h, grid_h))
        return cache[key]

    def directions(a: Waypoint, b: Waypoint) -> tuple[int, int]:
        return (b.x > a.x) - (b.x < a.x), (b.h > a.h) - (b.h < a.h)

    edges = [error(a, b) for a, b in zip(pts, pts[1:])]
    squared = tuple(sum(edge[axis][0] for edge in edges) for axis in (0, 1))
    limits = tuple(
        (squared[axis], max(e[axis][1] for e in edges), max(e[axis][2] for e in edges))
        for axis in (0, 1)
    )
    variation = _slope_variation(pts)
    variation_limit = variation
    slopes = [((b.x - a.x) / (b.t - a.t), (b.h - a.h) / (b.t - a.t)) for a, b in zip(pts, pts[1:])]
    for sweep in range(8):
        changed = False
        indices = range(1, len(pts) - 1)
        for i in indices if sweep % 2 == 0 else reversed(indices):
            a, cur, b = pts[i - 1 : i + 2]
            if cur.t in fixed:
                continue
            candidates = {cur.t + step * grid for step in range(-8, 9)}
            candidates.update(
                round((a.t + (b.t - a.t) * step / 16) / grid) * grid for step in range(1, 16)
            )
            before = slopes[i - 2] if i >= 2 else None
            after = slopes[i + 1] if i + 1 < len(slopes) else None
            old_variation = _local_variation(slopes[i - 1], slopes[i], before, after)
            base_squared = tuple(
                squared[axis] - edges[i - 1][axis][0] - edges[i][axis][0] for axis in (0, 1)
            )
            best, best_squared, best_variation = cur, squared, variation
            best_edges = edges[i - 1 : i + 1]
            best_slopes = slopes[i - 1 : i + 1]
            for t in sorted(candidates):
                if t == cur.t or not a.t < t < b.t:
                    continue
                candidate = vertices.get(t)
                if candidate is None:
                    x, h = reals[sample_index[t]]
                    candidate = vertices[t] = Waypoint(t, round(x), round(h))
                if directions(a, candidate) != directions(a, cur) or directions(
                    candidate, b
                ) != directions(cur, b):
                    continue
                left_slope = ((candidate.x - a.x) / (t - a.t), (candidate.h - a.h) / (t - a.t))
                right_slope = ((b.x - candidate.x) / (b.t - t), (b.h - candidate.h) / (b.t - t))
                local_variation = _local_variation(left_slope, right_slope, before, after)
                new_variation = tuple(
                    variation[axis] - old_variation[axis] + local_variation[axis] for axis in (0, 1)
                )
                if any(
                    new_variation[axis] > variation_limit[axis] + _LINEAR_TOL for axis in (0, 1)
                ):
                    continue
                lower_left = lower_bound(a, candidate)
                lower_right = lower_bound(candidate, b)
                lower = tuple(base_squared[j] + lower_left[j] + lower_right[j] for j in (0, 1))
                if sum(lower) >= sum(best_squared) - _LINEAR_TOL or any(
                    lower[j] > limits[j][0] + _LINEAR_TOL for j in (0, 1)
                ):
                    continue
                left = error(a, candidate)
                if left[0][0] == inf:
                    continue
                right = error(candidate, b)
                if right[0][0] == inf:
                    continue
                pair = [left, right]
                new_squared = tuple(
                    squared[axis]
                    - edges[i - 1][axis][0]
                    - edges[i][axis][0]
                    + pair[0][axis][0]
                    + pair[1][axis][0]
                    for axis in (0, 1)
                )
                if sum(new_squared) >= sum(best_squared) - _LINEAR_TOL:
                    continue
                if any(
                    new_squared[axis] > limits[axis][0] + _LINEAR_TOL
                    or max(e[axis][1] for e in pair) > limits[axis][1] + _LINEAR_TOL
                    or max(e[axis][2] for e in pair) > limits[axis][2] + _LINEAR_TOL
                    for axis in (0, 1)
                ):
                    continue
                best, best_squared, best_variation, best_edges = (
                    candidate,
                    new_squared,
                    new_variation,
                    pair,
                )
                best_slopes = [left_slope, right_slope]
            if best is not cur:
                pts[i] = best
                squared, variation = best_squared, best_variation
                edges[i - 1 : i + 1] = best_edges
                slopes[i - 1 : i + 1] = best_slopes
                changed = True
        if not changed:
            break


def _stored_height(obj: object) -> int:
    """Read the raw stored height, including from ground notes without public ``h``."""
    return int(getattr(getattr(obj, "_info", None), "h", DEFAULT_H))


__all__ = ["Curve", "CurveMode", "SlideLike", "Waypoint"]
