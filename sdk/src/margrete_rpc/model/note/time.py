from __future__ import annotations

from fractions import Fraction

from .types import AirCrushOption, NoteInfo

TICKS_PER_BEAT = 1920

type TickDelta = int | tuple[int, int]


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


def beats_to_ticks(value: TickDelta) -> int:
    if type(value) is int:
        return value
    if type(value) is not tuple or len(value) != 2:
        raise TypeError("beat fraction must be int or tuple of two ints")
    numerator, denominator = value
    if type(numerator) is not int or type(denominator) is not int:
        raise TypeError("beat fraction tuple must be (int, int)")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {TICKS_PER_BEAT}")
    frac = Fraction(numerator * TICKS_PER_BEAT, denominator)
    if frac.denominator != 1:
        raise ValueError("beat division must resolve to a whole tick")
    return frac.numerator


class Tick:
    """Integer tick with in-place ``+=`` / ``-=`` using int or beat-fraction ``(int, int)``."""

    __slots__ = ("_value",)

    def __init__(self, initial: int | Tick = 0) -> None:
        if type(initial) is int:
            v = initial
        elif isinstance(initial, Tick):
            v = int(initial)
        else:
            raise TypeError(f"Tick initial value must be int or Tick, got {type(initial)!r}")
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
        if isinstance(other, Tick):
            return self._value == other._value
        if type(other) is int:
            return self._value == other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Tick):
            return self._value < other._value
        if type(other) is int:
            return self._value < other
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Tick):
            return self._value <= other._value
        if type(other) is int:
            return self._value <= other
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Tick):
            return self._value > other._value
        if type(other) is int:
            return self._value > other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Tick):
            return self._value >= other._value
        if type(other) is int:
            return self._value >= other
        return NotImplemented

    def __iadd__(self, other: TickDelta) -> Tick:
        new = self._value + beats_to_ticks(other)
        if new < 0:
            raise ValueError("tick must be non-negative")
        self._value = new
        return self

    def __isub__(self, other: TickDelta) -> Tick:
        new = self._value - beats_to_ticks(other)
        if new < 0:
            raise ValueError("tick must be non-negative")
        self._value = new
        return self

    def __add__(self, other: TickDelta) -> int:
        return self._value + beats_to_ticks(other)

    def __radd__(self, other: int) -> int:
        if type(other) is not int:
            return NotImplemented
        return other + self._value

    def __sub__(self, other: TickDelta) -> int:
        return self._value - beats_to_ticks(other)

    def __rsub__(self, other: int) -> int:
        if type(other) is not int:
            return NotImplemented
        return other - self._value


class CrushDensity(Tick):
    """:class:`Tick` view for AIRCRUSH density stored in ``NoteInfo.option_value``."""

    __slots__ = ("_info",)

    def __init__(self, info: NoteInfo) -> None:
        object.__setattr__(self, "_info", info)
        super().__init__(CrushDensity._raw(info))

    @staticmethod
    def _raw(info: NoteInfo) -> int:
        return int(info.__dict__["option_value"])

    def __int__(self) -> int:
        return CrushDensity._raw(self._info)

    def __index__(self) -> int:
        return int(self)

    def __repr__(self) -> str:
        return repr(int(self))

    def _reject_head_only(self) -> None:
        if CrushDensity._raw(self._info) == int(AirCrushOption.HEAD_ONLY):
            raise ValueError("cannot adjust numeric density while AirCrushOption.HEAD_ONLY is set")

    def __iadd__(self, other: TickDelta) -> CrushDensity:
        self._reject_head_only()
        new = int(self) + beats_to_ticks(other)
        if new < 0:
            raise ValueError("density must be non-negative")
        self._info.__dict__["option_value"] = new
        object.__setattr__(self, "_value", new)
        return self

    def __isub__(self, other: TickDelta) -> CrushDensity:
        self._reject_head_only()
        new = int(self) - beats_to_ticks(other)
        if new < 0:
            raise ValueError("density must be non-negative")
        self._info.__dict__["option_value"] = new
        object.__setattr__(self, "_value", new)
        return self


__all__ = [
    "CrushDensity",
    "Tick",
    "TickDelta",
    "TICKS_PER_BEAT",
    "beats_to_ticks",
    "ticks_to_beats",
]
