from __future__ import annotations

from ..events import TimelineSpeedEvent
from ..time import PositionLike, resolve_tick
from .easing import EaseLike, resolve_easing


def timing_glitch(
    *,
    t0: int | PositionLike,
    t1: int | PositionLike,
    count: int,
    speed_range: float,
    base_speed: float,
    spike_ticks: int = 5,
    til: int = 0,
) -> list[TimelineSpeedEvent]:
    """Generate a glitch/stutter of scroll-speed spikes across ``[t0, t1)``.

    ``count`` evenly-spaced spikes are emitted. Each spike is a :class:`TimelineSpeedEvent`
    whose speed alternates ``base_speed - speed_range``, ``base_speed + speed_range``, ... ,
    followed ``spike_ticks`` later by a reset event back to ``base_speed``. Pass
    ``base_speed=0.0`` for a freeze-style glitch or ``base_speed=1.0`` for jitter around normal
    scroll.

    Args:
        t0: Start tick or position; the first spike begins here.
        t1: End tick or position; no spike starts at or after it.
        count: Number of spikes to generate (at least 1).
        speed_range: Magnitude of each spike's deviation from ``base_speed``.
        base_speed: Rest speed the glitch snaps back to between spikes.
        spike_ticks: How many ticks each spike is held before its reset (at least 1). Defaults
            to 5, pass ``1`` for the shortest possible impulse.
        til: Timeline (TIL) index assigned to every event.

    Returns:
        The generated events in time order (two per spike: the spike then its reset).

    Raises:
        ValueError: If ``count < 1``, ``spike_ticks < 1``, or ``t1 <= t0``.
    """
    start = resolve_tick(t0)
    end = resolve_tick(t1)
    if count < 1:
        raise ValueError("count must be at least 1")
    if spike_ticks < 1:
        raise ValueError("spike_ticks must be at least 1")
    if end <= start:
        raise ValueError("t1 must be later than t0")

    span = end - start
    events: list[TimelineSpeedEvent] = []
    sign = -1
    for i in range(count):
        t = start + round(i * span / count)
        events.append(TimelineSpeedEvent(til=til, t=t, speed=base_speed + sign * speed_range))
        events.append(TimelineSpeedEvent(til=til, t=t + spike_ticks, speed=base_speed))
        sign = -sign
    return events


def timing_easing(
    *,
    t0: int | PositionLike,
    t1: int | PositionLike,
    start_speed: float,
    end_speed: float,
    count: int,
    easing: EaseLike = "linear",
    til: int = 0,
) -> list[TimelineSpeedEvent]:
    """Ramp scroll speed from ``start_speed`` to ``end_speed`` along an easing curve.

    The speed value itself is sampled from the easing curve at ``count + 1`` evenly-spaced
    points, so the first event lands on ``start_speed`` and the last on ``end_speed``. Use
    ``easing="linear"`` for a straight ramp.

    Args:
        t0: Start tick or position (first event).
        t1: End tick or position (last event).
        start_speed: Speed at ``t0``.
        end_speed: Speed at ``t1``.
        count: Number of subdivisions; yields ``count + 1`` events (at least 1).
        easing: Easing applied to the ramp (name, :class:`Easing`, or callable).
        til: Timeline (TIL) index assigned to every event.

    Returns:
        The generated events in time order.

    Raises:
        ValueError: If ``count < 1`` or ``t1 <= t0``.
    """
    start = resolve_tick(t0)
    end = resolve_tick(t1)
    if count < 1:
        raise ValueError("count must be at least 1")
    if end <= start:
        raise ValueError("t1 must be later than t0")

    ease = resolve_easing(easing)
    span = end - start
    delta = end_speed - start_speed
    events: list[TimelineSpeedEvent] = []
    for i in range(count + 1):
        p = i / count
        t = start + round(p * span)
        events.append(TimelineSpeedEvent(til=til, t=t, speed=start_speed + delta * ease.solve(p)))
    return events


def timing_easing_by_disp(
    *,
    t0: int | PositionLike,
    t1: int | PositionLike,
    base_speed: float,
    count: int,
    easing: EaseLike,
    til: int = 0,
) -> list[TimelineSpeedEvent]:
    """Generate speeds whose integrated displacement follows an easing curve.


    Args:
        t0: Start tick or position (first event).
        t1: End tick or position (last event).
        base_speed: Speed that covers the full span when the curve rises linearly across it.
        count: Number of subdivisions; yields ``count + 1`` events (at least 1).
        easing: Easing whose rise drives the speed (name, :class:`Easing`, or callable).
        til: Timeline (TIL) index assigned to every event.

    Returns:
        The generated events in time order.

    Raises:
        ValueError: If ``count < 1`` or ``t1 <= t0``.
    """
    start = resolve_tick(t0)
    end = resolve_tick(t1)
    if count < 1:
        raise ValueError("count must be at least 1")
    if end <= start:
        raise ValueError("t1 must be later than t0")

    ease = resolve_easing(easing)
    span = end - start
    ticks = [start + round(i / count * span) for i in range(count + 1)]
    values = [ease.solve(i / count) for i in range(count + 1)]
    events: list[TimelineSpeedEvent] = []
    for i in range(count + 1):
        if i < count:
            dt = ticks[i + 1] - ticks[i]
            speed = base_speed * span * (values[i + 1] - values[i]) / dt if dt else 0.0
        else:
            speed = events[-1].speed
        events.append(TimelineSpeedEvent(til=til, t=ticks[i], speed=speed))
    return events


__all__ = ["timing_easing", "timing_easing_by_disp", "timing_glitch"]
