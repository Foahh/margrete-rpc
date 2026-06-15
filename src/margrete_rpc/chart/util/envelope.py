from __future__ import annotations

from .curve import Curve, Waypoint


def envelope(inner: Curve, outer: Curve, *, count: int = 2) -> Curve:
    """Weave a curve that oscillates between two boundary curves over ``count`` legs.

    ``inner`` and ``outer`` must span the same ``[T0, T1]``. The weave starts on ``inner`` and
    places ``count + 1`` evenly spaced turning points at ``s = j / count`` for ``j = 0 .. count``,
    sampling ``inner`` at even ``j`` and ``outer`` at odd ``j`` (via :meth:`Curve.at`). Each
    turn is one straight, linear leg; the quantization to the grid happens later, when the
    woven curve is materialized.

    ``count`` is the number of legs (half-cycles), so the weave can stop at any turning point
    rather than only after whole cycles: an even ``count`` lands back on ``inner`` (``count``
    of 2 is one full cycle), while an odd ``count`` ends out on ``outer``.

    Args:
        inner: The boundary the weave starts on.
        outer: The opposite boundary, sharing ``inner``'s time span.
        count: Number of legs in the weave (at least 1). Defaults to 2 (one full cycle).

    Returns:
        The woven curve, as control waypoints joined by linear legs.

    Raises:
        ValueError: If ``count < 1`` or the two curves do not share the same time span.
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
