from __future__ import annotations

from fractions import Fraction

TICKS_PER_BEAT = 1920


def ticks_to_beats(tick: int, *, denominator: int | None = None) -> tuple[int, int]:
    if type(tick) is not int:
        raise TypeError(f"tick must be int, not {type(tick).__name__}")
    if tick < 0:
        raise ValueError("tick must be non-negative")

    if denominator is None:
        frac = Fraction(tick, TICKS_PER_BEAT)
        return frac.numerator, frac.denominator

    if type(denominator) is not int:
        raise TypeError(f"denominator must be int or None, not {type(denominator).__name__}")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {TICKS_PER_BEAT}")

    if tick == 0:
        return (0, 1)

    prod = tick * denominator
    if prod % TICKS_PER_BEAT != 0:
        raise ValueError(
            "tick cannot be expressed exactly with the given denominator "
            f"(tick={tick}, denominator={denominator}, ticks_per_beat={TICKS_PER_BEAT})"
        )
    return prod // TICKS_PER_BEAT, denominator


def beats_to_ticks(beat: tuple[int, int]) -> int:
    if type(beat) is not tuple or len(beat) != 2:
        raise TypeError("beat must be a tuple of two ints")
    numerator, denominator = beat
    if type(numerator) is not int or type(denominator) is not int:
        raise TypeError("beat tuple must be (int, int)")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {TICKS_PER_BEAT}")
    frac = Fraction(numerator * TICKS_PER_BEAT, denominator)
    if frac.denominator != 1:
        raise ValueError("beat division must resolve to a whole tick")
    return frac.numerator


b2t = beats_to_ticks
t2b = ticks_to_beats

__all__ = [
    "TICKS_PER_BEAT",
    "b2t",
    "beats_to_ticks",
    "t2b",
    "ticks_to_beats",
]
