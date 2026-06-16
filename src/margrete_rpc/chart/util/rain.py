from __future__ import annotations

import random

from ..constants import DEFAULT_AIRCRUSH_GAP, DEFAULT_H
from ..notes import AirCrush, ColorLike, ColorValue
from ..time import DivisionLike, PositionLike, resolve_division, resolve_tick


def rain(
    *,
    t0: int | PositionLike,
    t1: int | PositionLike,
    step: int | DivisionLike,
    x_range: tuple[int, int],
    h_range: tuple[int, int] = (DEFAULT_H, DEFAULT_H),
    length: int | DivisionLike | None = None,
    w: int = 1,
    gap: int | DivisionLike = DEFAULT_AIRCRUSH_GAP,
    color: ColorLike | int = ColorValue.DEFAULT,
    til: int = 0,
    seed: int | None = None,
) -> list[AirCrush]:
    """Scatter short :class:`AirCrush` traces across ``[t0, t1)`` like falling rain.

    A drop starts every ``step`` ticks at a random lane within ``x_range`` and height within
    ``h_range`` (both inclusive). ``length`` is each drop's duration; defaults to ``step``.
    Drops that would extend past ``t1`` are truncated. Pass ``seed`` for a reproducible stream.

    Args:
        t0: Start tick or position; the first drop begins here.
        t1: End tick or position; no drop starts at or after it.
        step: Spacing between drop starts (tick count or beat fraction).
        x_range: Inclusive ``(lo, hi)`` lane bounds for each drop.
        h_range: Inclusive ``(lo, hi)`` height bounds; defaults to a constant :data:`DEFAULT_H`.
        length: Drop duration (tick count or beat fraction); defaults to ``step``.
        w: Constant width of every drop.
        gap: Segment gap passed to each :class:`AirCrush`.
        color: Crush color for every drop.
        til: Timeline (TIL) index assigned to every drop.
        seed: Seed for the random stream; ``None`` is non-deterministic.

    Returns:
        The generated drops in time order.

    Raises:
        ValueError: If ``t1 <= t0`` or ``step``/``length`` resolve to a non-positive duration.
    """
    start = resolve_tick(t0)
    end = resolve_tick(t1)
    if end <= start:
        raise ValueError("t1 must be later than t0")
    step_ticks = resolve_division(step)
    if step_ticks <= 0:
        raise ValueError("step must be a positive duration")
    length_ticks = step_ticks if length is None else resolve_division(length)
    if length_ticks <= 0:
        raise ValueError("length must be a positive duration")

    x_lo, x_hi = sorted(x_range)
    h_lo, h_hi = sorted(h_range)
    rng = random.Random(seed)

    drops: list[AirCrush] = []
    current = start
    while current < end:
        drop_end = min(current + length_ticks, end)
        x = rng.randint(x_lo, x_hi)
        h = rng.randint(h_lo, h_hi)
        crush = AirCrush(t=current, x=x, w=w, h=h, gap=gap, color=color)
        crush.til = til
        crush.add_ctrl(t=drop_end, x=x, w=w, h=h)
        drops.append(crush)
        current += step_ticks
    return drops


__all__ = ["rain"]
