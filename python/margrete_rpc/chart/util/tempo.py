"""BPM tools for adjusting duration and dividing time into equal intervals.

Generate an adjustment, then call its ``apply(bpms)`` method to update a BPM list.
BPM changes affect every note in the adjusted range.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from ..events import BpmEvent
from ..time import TICK_RESOLUTION, DivisionLike, PositionLike, resolve_tick

_MS_PER_TICK = Fraction(60_000, TICK_RESOLUTION // 4)
_MAX_TICK = 2**31 - 1


@dataclass(frozen=True, slots=True)
class BpmPulseResult:
    """Result of ``bpm_pulse``.

    All positions are absolute ticks.

    Attributes:
        start: Start of the first part, at the position specified by ``t``.
        pivot: End of the first part; the second part starts here.
        end: End of the full range specified by ``span``.
        events: Generated BPM events, ending with the starting BPM at ``end``.
    """

    start: int
    pivot: int
    end: int
    events: tuple[BpmEvent, ...]

    def apply(self, bpms: list[BpmEvent]) -> None:
        """Replace BPMs in the range, preserving an existing BPM at ``end``.

        Args:
            bpms: List to update in place, still using the original BPM throughout
                the range.

        Raises:
            ValueError: If the generated events are invalid or the target BPMs
                conflict with this adjustment. Failure leaves the list untouched.
        """
        _apply(bpms, self.start, self.end, self.events)


@dataclass(frozen=True, slots=True)
class BpmDivisionResult:
    """Result of ``bpm_divide``.

    All positions are absolute ticks.

    Attributes:
        ticks: Start of each of the ``count`` time intervals, in order. You can
            place notes at these positions. The range's end is excluded.
        end: End of the full range. The last interval runs from ``ticks[-1]``
            to this position.
        events: Generated BPM events, ending with the starting BPM at ``end``.
            Adjacent intervals with the same BPM share an event.
    """

    ticks: tuple[int, ...]
    end: int
    events: tuple[BpmEvent, ...]

    @property
    def start(self) -> int:
        """Start of the full range, equal to ``ticks[0]``."""
        return self.ticks[0]

    def apply(self, bpms: list[BpmEvent]) -> None:
        """Replace BPMs in the range, preserving an existing BPM at ``end``.

        Args:
            bpms: List to update in place, still using the original BPM throughout
                the range.

        Raises:
            ValueError: If the generated events are invalid or the target BPMs
                conflict with this adjustment. Failure leaves the list untouched.
        """
        _apply(bpms, self.start, self.end, self.events)


def _integer(name: str, value: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    return value


def _positive_fraction(name: str, value: float | Fraction) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise TypeError(f"{name} must be an int, float, or Fraction")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be finite and positive")
    result = Fraction(value)
    if result <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _bpm_float(value: Fraction) -> float:
    try:
        result = float(value)
    except OverflowError:
        raise ValueError("BPM cannot be represented as a finite positive float") from None
    if not math.isfinite(result) or result <= 0:
        raise ValueError("BPM cannot be represented as a finite positive float")
    return result


def _duration_ticks(name: str, value: int | DivisionLike, grid: int) -> int:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError(f"{name} must be a (numerator, denominator) tuple")
        numerator = _integer(f"{name} numerator", value[0])
        denominator = _integer(f"{name} denominator", value[1])
        if denominator <= 0:
            raise ValueError(f"{name} denominator must be positive")
        ticks = Fraction(numerator * TICK_RESOLUTION, denominator)
    else:
        ticks = Fraction(_integer(name, value))
    if ticks <= 0:
        raise ValueError(f"{name} must be positive")
    if ticks.denominator != 1 or ticks % grid:
        raise ValueError(f"{name} must be an exact multiple of grid={grid} ticks")
    return int(ticks)


def _start_tick(t: int | PositionLike, grid: int) -> int:
    if _integer("grid", grid) <= 0:
        raise ValueError("grid must be positive")
    start = resolve_tick(t)
    _check_tick(start)
    if start % grid:
        raise ValueError(f"t must be an absolute multiple of grid={grid} ticks")
    return start


def _check_tick(tick: int) -> None:
    if not 0 <= _integer("tick", tick) <= _MAX_TICK:
        raise ValueError(f"tick must be between 0 and {_MAX_TICK}")


def _window(
    bpms: Iterable[BpmEvent], start: int, end: int
) -> tuple[list[BpmEvent], Fraction, BpmEvent]:
    _check_tick(end)
    by_tick = {event.t: event for event in bpms}
    ordered = sorted(by_tick.values(), key=lambda event: event.t)
    for event in ordered:
        _check_tick(event.t)
        _bpm_float(_positive_fraction("source BPM", event.bpm))
    active: BpmEvent | None = None
    for event in ordered:
        if event.t <= start:
            active = event
        elif event.t < end:
            if active is not None and event.bpm != active.bpm:
                raise ValueError(f"BPM change conflicts with window at tick {event.t}")
    if active is None:
        raise ValueError(f"no effective BPM at or before tick {start}")
    base = Fraction(active.bpm)
    restore = next((event for event in ordered if event.t == end), None)
    if restore is None:
        restore = BpmEvent(t=end, bpm=_bpm_float(base))
    return ordered, base, restore


def _make_events(
    points: tuple[int, ...], bpms: tuple[Fraction, ...], base: Fraction
) -> tuple[BpmEvent, ...]:
    events: list[BpmEvent] = []
    for start, exact_bpm in zip(points[:-1], bpms, strict=True):
        bpm = _bpm_float(exact_bpm)
        if not events or events[-1].bpm != bpm:
            events.append(BpmEvent(t=start, bpm=bpm))
    events.append(BpmEvent(t=points[-1], bpm=_bpm_float(base)))
    return tuple(events)


def _apply(bpms: list[BpmEvent], start: int, end: int, events: tuple[BpmEvent, ...]) -> None:
    _check_tick(start)
    _check_tick(end)
    if end <= start or not events or events[0].t != start or events[-1].t != end:
        raise ValueError("BPM events must cover the adjustment's full range")
    for event in events:
        _check_tick(event.t)
        _bpm_float(_positive_fraction("generated BPM", event.bpm))
    if any(a.t >= b.t for a, b in zip(events, events[1:])):
        raise ValueError("BPM event ticks must be strictly increasing")
    original, base, restore = _window(bpms, start, end)
    if Fraction(events[-1].bpm) != base:
        raise ValueError("target BPM differs from the adjustment's original BPM")
    replacement = [event for event in original if event.t < start]
    replacement.extend(BpmEvent(t=event.t, bpm=event.bpm) for event in events[:-1])
    replacement.append(restore)
    replacement.extend(event for event in original if event.t > end)
    bpms[:] = replacement


def bpm_pulse(
    bpms: Iterable[BpmEvent],
    *,
    t: int | PositionLike,
    length: int | DivisionLike,
    span: int | DivisionLike,
    bpm_scale: float | Fraction | None = None,
    duration_ms: float | Fraction | None = None,
    grid: int = 5,
) -> BpmPulseResult:
    """Shorten or lengthen one part, then adjust the next to preserve the total duration.

    The original BPM must be constant throughout the range.

    Args:
        bpms: Source BPM events, read without modification. At duplicate ticks,
            the last event wins.
        t: Start tick or musical position such as ``(24, 0)``. Position tuples
            use the active edit's time signatures, or 4/4 outside an edit,
            via ``resolve_tick``.
        length: Positive length of the first part, in ticks or as a whole-note
            fraction, such as ``5`` or ``(1, 384)``.
        span: Total length of both parts, using the same formats as ``length``.
            Must be greater than ``length``.
        bpm_scale: Positive multiplier for the first part's BPM. ``100`` makes
            it take 1/100 of its original time; ``0.5`` makes it take twice as
            long. Supply exactly one of ``bpm_scale`` and ``duration_ms``.
        duration_ms: Time the first part should take in milliseconds. Must be
            positive and less than the full range's original duration, leaving
            time for the second part.
        grid: Positive tick spacing for all positions. Defaults to ``5``
            (1/384 of a whole note); pass ``grid=1`` for full resolution.
            ``t``, ``length``, and ``span`` must convert to exact multiples
            of ``grid`` ticks.

    Returns:
        BpmPulseResult: Generated adjustment; call ``apply(bpms)`` to update a BPM list.

    Raises:
        TypeError: If an argument has an unsupported type.
        ValueError: If a value is invalid, a position cannot fit ``grid`` or the
            tick range, source BPM events are missing or conflicting, or the
            first part leaves no time for the second part.
    """
    if (bpm_scale is None) == (duration_ms is None):
        raise ValueError("supply exactly one of bpm_scale and duration_ms")
    start = _start_tick(t, grid)
    first = _duration_ticks("length", length, grid)
    total = _duration_ticks("span", span, grid)
    if first >= total:
        raise ValueError("length must be less than span")
    pivot, end = start + first, start + total
    _, base, _ = _window(bpms, start, end)
    target_total = _MS_PER_TICK * total / base
    if bpm_scale is not None:
        first_bpm = base * _positive_fraction("bpm_scale", bpm_scale)
        target_first = _MS_PER_TICK * first / first_bpm
    else:
        assert duration_ms is not None
        target_first = _positive_fraction("duration_ms", duration_ms)
        first_bpm = _MS_PER_TICK * first / target_first
    remaining = target_total - target_first
    if remaining <= 0:
        raise ValueError("first-part duration must be less than the original total duration")
    compensation_bpm = _MS_PER_TICK * (total - first) / remaining
    events = _make_events((start, pivot, end), (first_bpm, compensation_bpm), base)
    return BpmPulseResult(start=start, pivot=pivot, end=end, events=events)


def bpm_divide(
    bpms: Iterable[BpmEvent],
    *,
    t: int | PositionLike,
    span: int | DivisionLike,
    count: int,
    step: int | DivisionLike | None = None,
    grid: int = 5,
) -> BpmDivisionResult:
    """Divide a range's original duration into ``count`` equal time intervals.

    The original BPM must be constant throughout the range.

    Args:
        bpms: Source BPM events, read without modification. At duplicate ticks,
            the last event wins.
        t: Start tick or musical position such as ``(24, 2)``. Position tuples
            use the active edit's time signatures, or 4/4 outside an edit,
            via ``resolve_tick``.
        span: Positive length of the full range, in ticks or as a whole-note
            fraction, such as ``240`` or ``(1, 8)``.
        count: Number of equal time intervals, at least ``1``.
        step: Spacing between returned positions, in ticks or as a whole-note
            fraction, such as ``30`` or ``(1, 64)``. Sets the length of the first
            ``count - 1`` intervals; the final interval uses the remaining ticks
            and must have a positive length. If omitted, evenly spaced positions
            round to the nearest ``grid`` multiple, with ties rounded forward.
        grid: Positive tick spacing for all positions. Defaults to ``5``
            (1/384 of a whole note); pass ``grid=1`` for full resolution.
            ``t``, ``span``, and an explicit ``step`` must convert to exact
            multiples of ``grid`` ticks.

    Returns:
        BpmDivisionResult: Generated adjustment; call ``apply(bpms)`` to update a BPM list.

    Raises:
        TypeError: If an argument has an unsupported type.
        ValueError: If a value is invalid, a position cannot fit ``grid`` or the
            tick range, source BPM events are missing or conflicting,
            or the range cannot fit ``count`` intervals with the chosen ``grid``
            and ``step``.
    """
    start = _start_tick(t, grid)
    total = _duration_ticks("span", span, grid)
    if _integer("count", count) < 1:
        raise ValueError("count must be positive")
    if count > total // grid:
        raise ValueError("span is too short for count intervals on this grid")
    end = start + total
    _, base, _ = _window(bpms, start, end)
    if step is None:
        units = total // grid
        ticks = tuple(start + ((2 * i * units + count) // (2 * count)) * grid for i in range(count))
    else:
        spacing = _duration_ticks("step", step, grid)
        if spacing * (count - 1) >= total:
            raise ValueError("step must leave a positive final interval within span")
        ticks = tuple(start + i * spacing for i in range(count))
    points = (*ticks, end)
    interval_bpms = tuple(base * count * (b - a) / total for a, b in zip(points, points[1:]))
    events = _make_events(points, interval_bpms, base)
    return BpmDivisionResult(ticks=ticks, end=end, events=events)


__all__ = ["BpmDivisionResult", "BpmPulseResult", "bpm_divide", "bpm_pulse"]
