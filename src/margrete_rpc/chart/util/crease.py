from __future__ import annotations

from .curve import Curve, Waypoint


def crease(base: Curve, *, count: int, x_range: int, h_range: int = 0) -> Curve:
    """Zigzag a curve around ``base`` with ``count`` legs and lane amplitude ``x_range``.

    The first and last turning points land exactly on ``base``; interior points alternate
    between ``+x_range`` and ``-x_range`` offsets. ``h_range`` applies the same offset to
    height.

    Raises:
        ValueError: If ``count < 2`` or the time span is too small for ``count`` legs.
    """
    if count < 2:
        raise ValueError("count must be at least 2")
    t0 = base.waypoints[0].t
    t1 = base.waypoints[-1].t
    span = t1 - t0
    turning: list[Waypoint] = []
    for j in range(count + 1):
        tick = round(t0 + j / count * span)
        wp = base.at(tick)
        if j == 0 or j == count:
            sign = 0
        else:
            sign = 1 if j % 2 == 1 else -1
        turning.append(Waypoint(wp.t, wp.x + sign * x_range, wp.h + sign * h_range))
    return Curve._of(tuple(turning))


__all__ = ["crease"]
