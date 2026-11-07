from __future__ import annotations

import contextvars
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple, TypeAlias

from .constants import TICK_RESOLUTION as TICK_RESOLUTION
from .events import BeatEvent


class Position(NamedTuple):
    """A musical position as ``(bar, beat, offset)``.

    All components are zero-based; ``offset`` is in ticks within the beat. This is the
    resolved view of a tick (see :func:`tick_to_pos`); to convert back to an absolute tick use
    :func:`pos_to_tick` or pass it where a :data:`PositionLike` is accepted."""

    bar: int
    beat: int
    offset: int


PositionLike: TypeAlias = Position | tuple[int] | tuple[int, int] | tuple[int, int, int]
"""An input position as ``(bar,)``, ``(bar, beat)``, or ``(bar, beat, offset)``.

The accepted, loose form for arguments; missing components default to zero. Resolved to an
absolute tick against the chart's beat events (see :func:`pos_to_tick`). Functions return the
canonical 3-field :class:`Position`."""

TickResolver: TypeAlias = Callable[[PositionLike], int]
"""A function mapping a :data:`PositionLike` to an absolute tick.

Installed via :func:`push_tick_resolver` so positions resolve against a chart's beat
events without threading them through every call."""


class Division(NamedTuple):
    """A duration as a fraction of a whole note.

    ``Division(1, 4)`` is a quarter note, regardless of the time signature. Convert to ticks
    with :func:`div_to_tick` or pass it where a :data:`DivisionLike` is accepted.
    """

    numerator: int
    denominator: int


DivisionLike: TypeAlias = Division | tuple[int, int]
"""A ``(numerator, denominator)`` fraction of a whole note, e.g. ``(1, 4)`` for a quarter.

Arguments typed ``int | DivisionLike`` also accept a duration in ticks. Fractional durations
are quantized by :func:`div_to_tick`; they do not depend on the chart's time signature.
"""


@dataclass(frozen=True, slots=True)
class _TimeSignature:
    bar: int
    tick: int
    beats_per_bar: int
    beat_unit: int


def _require_int(name: str, value: object) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be int, not {type(value).__name__}")
    return value


def _assert_unique_beat_bars(events: list[BeatEvent]) -> None:
    seen: set[int] = set()
    for event in events:
        if event.bar in seen:
            raise ValueError(f"duplicate BeatEvent bar {event.bar}")
        seen.add(event.bar)


def _build_time_signatures(beat_events: Iterable[BeatEvent]) -> list[_TimeSignature]:
    ordered = sorted(
        (e for e in beat_events if e.bar >= 0),
        key=lambda e: e.bar,
    )
    _assert_unique_beat_bars(ordered)
    segments: list[_TimeSignature] = []
    if ordered and ordered[0].bar == 0:
        first = ordered[0]
        segments.append(_TimeSignature(0, 0, first.beats_per_bar, first.beat_unit))
        rest = ordered[1:]
    else:
        segments.append(_TimeSignature(0, 0, 4, 4))
        rest = ordered

    for event in rest:
        prev = segments[-1]
        measure_len = _measure_length(prev)
        tick = prev.tick + measure_len * (event.bar - prev.bar)
        segments.append(_TimeSignature(event.bar, tick, event.beats_per_bar, event.beat_unit))
    return segments


def _measure_length(ts: _TimeSignature) -> int:
    return TICK_RESOLUTION // ts.beat_unit * ts.beats_per_bar


class TimeCalculator:
    """Convert between ticks and positions using a snapshot of time-signature events.

    Events are sorted by bar; negative bars are ignored and duplicate non-negative bars
    raise ``ValueError``. Bars before the first event use 4/4. Rebuild the calculator after
    changing the events, or use :func:`tick_to_pos` and :func:`pos_to_tick`, which construct
    one per call.
    """

    def __init__(self, beat_events: Iterable[BeatEvent]) -> None:
        """Build a calculator from a chart's beat (time-signature) events."""
        self._segments = _build_time_signatures(beat_events)

    def tick_to_pos(self, tick: int) -> Position:
        """Convert an absolute tick to a ``(bar, beat, offset)`` position.

        Args:
            tick: Non-negative absolute tick from the chart start.

        Returns:
            The ``(bar, beat, offset)`` position of ``tick``.

        Raises:
            ValueError: If ``tick`` is negative.
        """
        tick = _require_int("tick", tick)
        if tick < 0:
            raise ValueError("tick must be non-negative")

        idx = self._find_segment_index(tick)
        ts = self._segments[idx]
        measure_len = _measure_length(ts)
        delta = tick - ts.tick
        bars_since = delta // measure_len
        remainder = delta % measure_len
        beat_tick = TICK_RESOLUTION // ts.beat_unit
        beat = remainder // beat_tick
        offset = remainder % beat_tick
        return Position(ts.bar + bars_since, beat, offset)

    def _find_segment_index(self, tick: int) -> int:
        segments = self._segments
        low, high = 0, len(segments) - 1
        while low <= high:
            mid = (low + high) // 2
            if segments[mid].tick <= tick:
                if mid == len(segments) - 1 or segments[mid + 1].tick > tick:
                    return mid
                low = mid + 1
            else:
                high = mid - 1
        raise ValueError(f"tick {tick} is before all time signatures")

    def pos_to_tick(self, bar: int, beat: int = 0, offset: int = 0) -> int:
        """Convert a ``(bar, beat, offset)`` position to an absolute tick.

        Args:
            bar: Zero-based bar index.
            beat: Zero-based beat within the bar.
            offset: Tick offset within the beat.

        Returns:
            The absolute tick from the chart start.

        Raises:
            ValueError: If any component is negative or out of range for the bar's time
                signature.
        """
        bar = _require_int("bar", bar)
        beat = _require_int("beat", beat)
        offset = _require_int("offset", offset)
        if bar < 0 or beat < 0 or offset < 0:
            raise ValueError("bar, beat, and offset must be non-negative")

        idx = self._find_segment_index_for_bar(bar)
        ts = self._segments[idx]
        measure_len = _measure_length(ts)
        beat_tick = TICK_RESOLUTION // ts.beat_unit
        if beat >= ts.beats_per_bar:
            raise ValueError(
                f"beat {beat} out of range for {ts.beats_per_bar} beats per bar at bar {bar}"
            )
        if offset >= beat_tick:
            raise ValueError(
                f"offset {offset} out of range for beat length {beat_tick} at bar {bar}"
            )
        return ts.tick + (bar - ts.bar) * measure_len + beat * beat_tick + offset

    def _find_segment_index_for_bar(self, bar: int) -> int:
        segments = self._segments
        idx = 0
        for i, seg in enumerate(segments):
            if seg.bar <= bar:
                idx = i
            else:
                break
        return idx


_active_beat_events: contextvars.ContextVar[Iterable[BeatEvent] | None] = contextvars.ContextVar(
    "margrete_active_beat_events", default=None
)


def push_beat_events(
    beat_events: Iterable[BeatEvent],
) -> contextvars.Token[Iterable[BeatEvent] | None]:
    """Install ``beat_events`` as the active beat events for position resolution.

    While active, :func:`tick_to_pos` and :func:`pos_to_tick` use these events when none are passed
    explicitly. :class:`EditTransaction` does this automatically for the duration of an
    edit.

    Args:
        beat_events: The time-signature events to make active.

    Returns:
        A token to pass to :func:`pop_beat_events` to restore the previous events.
    """
    return _active_beat_events.set(beat_events)


def pop_beat_events(token: contextvars.Token[Iterable[BeatEvent] | None]) -> None:
    """Restore the beat events active before the matching :func:`push_beat_events`."""
    _active_beat_events.reset(token)


def _resolve_beat_events(beat_events: Iterable[BeatEvent] | None) -> Iterable[BeatEvent]:
    if beat_events is not None:
        return beat_events
    ctx = _active_beat_events.get()
    return ctx if ctx is not None else ()


def tick_to_pos(tick: int, *, beat_events: Iterable[BeatEvent] | None = None) -> Position:
    """Convert an absolute tick to a ``(bar, beat, offset)`` position.

    Args:
        tick: Non-negative absolute tick from the chart start.
        beat_events: Time-signature events to resolve against; falls back to the active
            events (see :func:`push_beat_events`), then to a default 4/4 signature.

    Returns:
        The ``(bar, beat, offset)`` position of ``tick``.
    """
    return TimeCalculator(_resolve_beat_events(beat_events)).tick_to_pos(tick)


def pos_to_tick(
    bar: int,
    beat: int = 0,
    offset: int = 0,
    *,
    beat_events: Iterable[BeatEvent] | None = None,
) -> int:
    """Convert a ``(bar, beat, offset)`` position to an absolute tick.

    Args:
        bar: Zero-based bar index.
        beat: Zero-based beat within the bar.
        offset: Tick offset within the beat.
        beat_events: Time-signature events to resolve against; falls back to the active
            events (see :func:`push_beat_events`), then to a default 4/4 signature.

    Returns:
        The absolute tick from the chart start.
    """
    return TimeCalculator(_resolve_beat_events(beat_events)).pos_to_tick(bar, beat, offset)


_active_tick_resolver: contextvars.ContextVar[TickResolver | None] = contextvars.ContextVar(
    "margrete_active_tick_resolver", default=None
)


def push_tick_resolver(resolver: TickResolver) -> contextvars.Token[TickResolver | None]:
    """Install ``resolver`` as the active position->tick resolver.

    While active, :func:`resolve_tick` uses it to turn :data:`Position` tuples into ticks.
    :class:`EditTransaction` installs a resolver bound to the chart's beat events.

    Args:
        resolver: The position-to-tick function to make active.

    Returns:
        A token to pass to :func:`pop_tick_resolver` to restore the previous resolver.
    """
    return _active_tick_resolver.set(resolver)


def pop_tick_resolver(token: contextvars.Token[TickResolver | None]) -> None:
    """Restore the resolver active before the matching :func:`push_tick_resolver`."""
    _active_tick_resolver.reset(token)


def resolve_tick(value: int | PositionLike) -> int:
    """Coerce a tick-or-position argument to an absolute tick.

    Args:
        value: An int tick (returned unchanged) or a :data:`PositionLike` tuple, resolved via
            the active tick resolver (see :func:`push_tick_resolver`) or, if none is set,
            a default 4/4 signature.

    Returns:
        The absolute tick.
    """
    if isinstance(value, tuple):
        if not 1 <= len(value) <= 3:
            raise ValueError(
                "position tick must be a (bar,), (bar, beat), or (bar, beat, offset) tuple"
            )
        resolver = _active_tick_resolver.get()
        if resolver is not None:
            return resolver(value)
        return pos_to_tick(*value, beat_events=())
    return value


def div_to_tick(numerator: int, denominator: int) -> int:
    """Convert a fraction of a whole note to ticks.

    For example ``div_to_tick(1, 4)`` is the ticks in a quarter note and
    ``div_to_tick(1, 1)`` equals ``TICK_RESOLUTION``. Fractional ticks round down; positive
    durations smaller than one tick become one tick. Zero and negative numerators are
    accepted.

    Args:
        numerator: Fraction numerator (number of divisions).
        denominator: Fraction denominator.

    Returns:
        The duration in ticks.

    Raises:
        TypeError: If either argument is not an int (booleans are rejected).
        ValueError: If the denominator is non-positive.
    """
    if type(numerator) is not int or type(denominator) is not int:
        raise TypeError("numerator and denominator must be ints")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    ticks = numerator * TICK_RESOLUTION // denominator
    if numerator > 0:
        return max(1, ticks)
    return ticks


def tick_to_div(ticks: int) -> Division:
    """Express a non-negative tick count as a reduced fraction of a whole note.

    ``TICK_RESOLUTION`` ticks gives ``Division(1, 1)``; a quarter note gives
    ``Division(1, 4)``. Converting the result with :func:`div_to_tick` preserves the tick
    count, but cannot recover a fraction that was quantized on its way to ticks.

    Args:
        ticks: Non-negative duration in ticks.

    Returns:
        The reduced ``(numerator, denominator)`` whole-note fraction.

    Raises:
        TypeError: If ``ticks`` is not an int (booleans are rejected).
        ValueError: If ``ticks`` is negative.
    """
    if type(ticks) is not int:
        raise TypeError("ticks must be int")
    if ticks < 0:
        raise ValueError("ticks must be non-negative")
    frac = Fraction(ticks, TICK_RESOLUTION)
    return Division(frac.numerator, frac.denominator)


def resolve_division(value: int | DivisionLike) -> int:
    """Coerce a tick-count-or-fraction argument to an int tick count.

    Args:
        value: An int tick count (returned unchanged) or a :data:`DivisionLike`
            whole-note fraction, converted via :func:`div_to_tick`.

    Returns:
        The duration in ticks.
    """
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("interval must be a (numerator, denominator) tuple")
        return div_to_tick(value[0], value[1])
    return value


__all__ = [
    "TICK_RESOLUTION",
    "Division",
    "DivisionLike",
    "Position",
    "PositionLike",
    "TickResolver",
    "TimeCalculator",
    "tick_to_pos",
    "pos_to_tick",
    "push_beat_events",
    "pop_beat_events",
    "resolve_tick",
    "push_tick_resolver",
    "pop_tick_resolver",
    "div_to_tick",
    "tick_to_div",
    "resolve_division",
]
