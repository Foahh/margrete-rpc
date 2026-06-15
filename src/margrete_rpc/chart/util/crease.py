from __future__ import annotations

from .curve import Curve, Waypoint


def crease(base: Curve, *, count: int, x_range: int, h_range: int = 0) -> Curve:
    """Zigzag a curve around ``base`` with alternating lane offsets.

    The first and last turning points land exactly on ``base``; interior points alternate
    between ``+x_range`` and ``-x_range`` offsets. ``h_range`` applies the same offsets
    to height.

    Args:
        base: The curve to zigzag around.
        count: Number of legs (at least 2).
        x_range: Lane offset amplitude for interior turning points.
        h_range: Height offset amplitude, in phase with ``x_range``.

    Returns:
        A new :class:`Curve` with ``count`` linear legs zigzagging around ``base``.

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
