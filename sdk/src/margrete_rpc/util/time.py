from __future__ import annotations

from fractions import Fraction

from margrete_rpc.model.constant import TICKS_PER_BEAT


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

__all__ = [
    "b2t",
    "beats_to_ticks",
]
