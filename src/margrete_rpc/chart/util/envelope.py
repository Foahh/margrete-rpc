from __future__ import annotations

from .curve import Curve, Waypoint


def envelope(inner: Curve, outer: Curve, *, count: int = 2) -> Curve:
    """Weave a curve that oscillates between ``inner`` and ``outer`` over ``count`` legs.

    Both curves must share the same time span. An even ``count`` lands back on ``inner``
    (``count=2`` is one full cycle); an odd ``count`` ends on ``outer``.

    Raises:
        ValueError: If ``count < 1`` or the curves have different time spans.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    t0 = inner.waypoints[0].t
    t1 = inner.waypoints[-1].t
    if outer.waypoints[0].t != t0 or outer.waypoints[-1].t != t1:
        raise ValueError("inner and outer must share the same time span")

    span = t1 - t0
    turning: list[Waypoint] = []
    for j in range(count + 1):
        tick = round(t0 + j / count * span)
        source = inner if j % 2 == 0 else outer
        turning.append(source.at(tick))
    return Curve._of(tuple(turning))


__all__ = ["envelope"]
