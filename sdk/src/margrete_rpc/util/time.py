from __future__ import annotations

from fractions import Fraction

from margrete_rpc.model.tick import _TICKS_PER_BEAT


def bar_from_tick(tick: int, *, denominator: int | None = None) -> tuple[int, int]:
    if type(tick) is not int:
        raise TypeError(f"tick must be int, not {type(tick).__name__}")
    if tick < 0:
        raise ValueError("tick must be non-negative")

    if denominator is None:
        frac = Fraction(tick, _TICKS_PER_BEAT)
        return frac.numerator, frac.denominator

    if type(denominator) is not int:
        raise TypeError(f"denominator must be int or None, not {type(denominator).__name__}")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > _TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {_TICKS_PER_BEAT}")

    if tick == 0:
        return (0, 1)

    prod = tick * denominator
    if prod % _TICKS_PER_BEAT != 0:
        raise ValueError(
            "tick cannot be expressed exactly with the given denominator "
            f"(tick={tick}, denominator={denominator}, ticks_per_beat={_TICKS_PER_BEAT})"
        )
    return prod // _TICKS_PER_BEAT, denominator
