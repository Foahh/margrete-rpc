from __future__ import annotations

from collections.abc import Iterator

from ..constants import DEFAULT_AIRCRUSH_GAP, DEFAULT_H
from ..notes import AirCrush, AirHold, AirSlide, ColorLike, ColorValue, Hold, Slide
from ..time import DivisionLike, Position, PositionLike, resolve_tick, tick_to_pos
from .easing import EaseLike, Easing, resolve_easing

_LINEAR = resolve_easing("linear")

type SlideLike = Slide | Hold | AirSlide | AirHold | AirCrush
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

    def points(self) -> tuple[Waypoint, ...]:
        """Quantize the path into integer waypoints.

        Returns:
            All sampled waypoints in order; useful to preview the realized joints before
            calling a ``to_*`` materializer.

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
        """Materialize as a ground :class:`Slide`.

        Args:
            w: Constant lane width for every joint.
            til: Timeline index assigned to the note.

        Returns:
            A :class:`Slide` whose joints follow the quantized path. Height is preserved
            in the underlying raw note fields.
        """
        first, mid, last = self._path()
        slide = Slide(t=first.t, x=first.x, w=w)
        slide._info.h = first.h
        slide.til = til
        for wp in mid:
            slide.add_ctrl(t=wp.t, x=wp.x, w=w)
            slide.joints[-1]._info.h = wp.h
        slide.add_step(t=last.t, x=last.x, w=w)
        slide.joints[-1]._info.h = last.h
        return slide

    def to_air_slide(self, *, w: int, til: int = 0) -> AirSlide:
        """Materialize as an :class:`AirSlide`.

        Args:
            w: Constant lane width for every joint.
            til: Timeline index assigned to the note.

        Returns:
            An :class:`AirSlide` whose joints follow the quantized path.
        """
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
        gap: int | DivisionLike = DEFAULT_AIRCRUSH_GAP,
        color: ColorLike | int = ColorValue.DEFAULT,
        til: int = 0,
    ) -> AirCrush:
        """Materialize as an :class:`AirCrush`.

        Args:
            w: Constant lane width for every joint.
            gap: Segment gap. Also accepts
                :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_TRACELIKE` and
                :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_HEADONLY`.
            color: Crush particle color.
            til: Timeline index assigned to the note.

        Returns:
            An :class:`AirCrush` whose joints follow the quantized path.
        """
        first, mid, last = self._path()
        crush = AirCrush(t=first.t, x=first.x, w=w, h=first.h, gap=gap, color=color)
        crush.til = til
        for wp in (*mid, last):
            crush.add_ctrl(t=wp.t, x=wp.x, w=w, h=wp.h)
        return crush

    def at(self, tick: int) -> Waypoint:
        """Evaluate the eased path at ``tick``.

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
"""Real-space deviation under which a leg is treated as exactly linear (float-noise slack)."""


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
    """Quantize an eased segment to integer waypoints driven by the smaller-delta axis."""
    if t1 <= t0:
        raise ValueError("segment end tick must be later than its start")
    span = t1 - t0
    reals = [
        (
            t,
            x0 + ease_x.solve((t - t0) / span) * (x1 - x0),
            h0 + ease_h.solve((t - t0) / span) * (h1 - h0),
        )
        for t in range(t0, t1 + 1)
    ]
    if _is_linear(reals):
        return (Waypoint(t0, x0, h0), Waypoint(t1, x1, h1))

    dx, dh = abs(x1 - x0), abs(h1 - h0)
    drive_x = dh == 0 or (dx != 0 and dx <= dh)

    pts = [Waypoint(t0, x0, h0)]
    last = x0 if drive_x else h0
    for t, rx, rh in reals[1:-1]:
        v = rx if drive_x else rh
        if v >= last + 1 or v <= last - 1:  # driver has reached the next integer level
            nx, nh = round(rx), round(rh)
            pts.append(Waypoint(t, nx, nh))
            last = nx if drive_x else nh
    pts.append(Waypoint(t1, x1, h1))

    out = [pts[0]]
    for cur, nxt in zip(pts[1:-1], pts[2:]):
        if not _collinear(out[-1], cur, nxt):
            out.append(cur)
    out.append(pts[-1])
    return tuple(out)


def _stored_height(obj: object) -> int:
    """Read the raw stored height, including from ground notes without public ``h``."""
    return int(getattr(getattr(obj, "_info", None), "h", DEFAULT_H))


__all__ = ["Curve", "SlideLike", "Waypoint"]
