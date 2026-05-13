from __future__ import annotations

from fractions import Fraction
from typing import TypeAlias

from margrete_rpc.model.note_types import _TICKS_PER_BEAT

TickDelta: TypeAlias = int | tuple[int, int]


def tick_delta(value: TickDelta) -> int:
    if type(value) is int:
        return value
    if type(value) is not tuple or len(value) != 2:
        raise TypeError("tick delta tuple must be exactly (int, int)")
    numerator, denominator = value
    if type(numerator) is not int or type(denominator) is not int:
        raise TypeError("tick delta tuple must be (int, int)")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > _TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {_TICKS_PER_BEAT}")
    tick = Fraction(numerator * _TICKS_PER_BEAT, denominator)
    if tick.denominator != 1:
        raise ValueError("beat division must resolve to a whole tick")
    return tick.numerator


class MusicalTick:
    """Integer tick with in-place ``+=`` / ``-=`` using int or beat-fraction (int, int)."""

    __slots__ = ("_value",)

    def __init__(self, initial: int | MusicalTick = 0) -> None:
        if type(initial) is int:
            v = initial
        elif isinstance(initial, MusicalTick):
            v = int(initial)
        else:
            raise TypeError(f"MusicalTick initial value must be int or MusicalTick, got {type(initial)!r}")
        if v < 0:
            raise ValueError("tick must be non-negative")
        object.__setattr__(self, "_value", v)

    def __int__(self) -> int:
        return self._value

    def __index__(self) -> int:
        return self._value

    def __repr__(self) -> str:
        return repr(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MusicalTick):
            return self._value == other._value
        if type(other) is int:
            return self._value == other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, MusicalTick):
            return self._value < other._value
        if type(other) is int:
            return self._value < other
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, MusicalTick):
            return self._value <= other._value
        if type(other) is int:
            return self._value <= other
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, MusicalTick):
            return self._value > other._value
        if type(other) is int:
            return self._value > other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, MusicalTick):
            return self._value >= other._value
        if type(other) is int:
            return self._value >= other
        return NotImplemented

    def __iadd__(self, other: TickDelta) -> MusicalTick:
        new = self._value + tick_delta(other)
        if new < 0:
            raise ValueError("tick must be non-negative")
        self._value = new
        return self

    def __isub__(self, other: TickDelta) -> MusicalTick:
        new = self._value - tick_delta(other)
        if new < 0:
            raise ValueError("tick must be non-negative")
        self._value = new
        return self

    def __add__(self, other: TickDelta) -> int:
        return self._value + tick_delta(other)

    def __radd__(self, other: int) -> int:
        if type(other) is not int:
            return NotImplemented
        return other + self._value

    def __sub__(self, other: TickDelta) -> int:
        return self._value - tick_delta(other)

    def __rsub__(self, other: int) -> int:
        if type(other) is not int:
            return NotImplemented
        return other - self._value
