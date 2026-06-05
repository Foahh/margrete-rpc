from __future__ import annotations

import contextvars
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from fractions import Fraction

from .events import BeatEvent

TICKS_PER_BEAT = 1920

type Position = tuple[int, int, int]

type Tick = int | Position
type TickResolver = Callable[[Position], int]

type Division = int | tuple[int, int]


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
    return TICKS_PER_BEAT // ts.beat_unit * ts.beats_per_bar


class TimeCalculator:
    def __init__(self, beat_events: Iterable[BeatEvent]) -> None:
        self._segments = _build_time_signatures(beat_events)

    def t2p(self, tick: int) -> Position:
        tick = _require_int("tick", tick)
        if tick < 0:
            raise ValueError("tick must be non-negative")

        idx = self._find_segment_index(tick)
        ts = self._segments[idx]
        measure_len = _measure_length(ts)
        delta = tick - ts.tick
        bars_since = delta // measure_len
        remainder = delta % measure_len
        beat_tick = TICKS_PER_BEAT // ts.beat_unit
        beat = remainder // beat_tick
        offset = remainder % beat_tick
        return (ts.bar + bars_since, beat, offset)

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

    def p2t(self, bar: int, beat: int = 0, offset: int = 0) -> int:
        bar = _require_int("bar", bar)
        beat = _require_int("beat", beat)
        offset = _require_int("offset", offset)
        if bar < 0 or beat < 0 or offset < 0:
            raise ValueError("bar, beat, and offset must be non-negative")

        idx = self._find_segment_index_for_bar(bar)
        ts = self._segments[idx]
        measure_len = _measure_length(ts)
        beat_tick = TICKS_PER_BEAT // ts.beat_unit
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


def push_beat_events(beat_events: Iterable[BeatEvent]) -> contextvars.Token:
    """Install ``beat_events`` as the active beat events; returns a reset token."""
    return _active_beat_events.set(beat_events)


def pop_beat_events(token: contextvars.Token) -> None:
    """Restore the beat events that were active before the matching ``push_beat_events``."""
    _active_beat_events.reset(token)


def _resolve_beat_events(beat_events: Iterable[BeatEvent] | None) -> Iterable[BeatEvent]:
    if beat_events is not None:
        return beat_events
    ctx = _active_beat_events.get()
    return ctx if ctx is not None else ()


def t2p(tick: int, *, beat_events: Iterable[BeatEvent] | None = None) -> Position:
    return TimeCalculator(_resolve_beat_events(beat_events)).t2p(tick)


def p2t(
    bar: int,
    beat: int = 0,
    offset: int = 0,
    *,
    beat_events: Iterable[BeatEvent] | None = None,
) -> int:
    return TimeCalculator(_resolve_beat_events(beat_events)).p2t(bar, beat, offset)


_active_tick_resolver: contextvars.ContextVar[TickResolver | None] = contextvars.ContextVar(
    "margrete_active_tick_resolver", default=None
)


def push_tick_resolver(resolver: TickResolver) -> contextvars.Token:
    """Install ``resolver`` as the active position->tick resolver; returns a reset token."""
    return _active_tick_resolver.set(resolver)


def pop_tick_resolver(token: contextvars.Token) -> None:
    """Restore the resolver that was active before the matching ``push_tick_resolver``."""
    _active_tick_resolver.reset(token)


def resolve_tick(value: Tick) -> int:
    """Coerce a tick argument to an int.

    An int passes through unchanged. A ``(bar[, beat[, offset]])`` tuple is resolved
    against the active edit context (set by ``open_edit``); with no active context it
    falls back to a plain 4/4 time signature.
    """
    if isinstance(value, tuple):
        if not 1 <= len(value) <= 3:
            raise ValueError(
                "position tick must be a (bar,), (bar, beat), or (bar, beat, offset) tuple"
            )
        resolver = _active_tick_resolver.get()
        if resolver is not None:
            return resolver(value)
        return p2t(*value, beat_events=())
    return value


def d2t(numerator: int, denominator: int) -> int:
    if type(numerator) is not int or type(denominator) is not int:
        raise TypeError("numerator and denominator must be ints")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if denominator > TICKS_PER_BEAT:
        raise ValueError(f"denominator must not exceed {TICKS_PER_BEAT}")
    frac = Fraction(numerator * TICKS_PER_BEAT, denominator)
    if frac.denominator != 1:
        raise ValueError("beat division must resolve to a whole tick")
    return frac.numerator


def t2d(ticks: int) -> tuple[int, int]:
    """Convert a tick count to the reduced ``(numerator, denominator)`` beat fraction."""
    if type(ticks) is not int:
        raise TypeError("ticks must be int")
    if ticks < 0:
        raise ValueError("ticks must be non-negative")
    frac = Fraction(ticks, TICKS_PER_BEAT)
    return (frac.numerator, frac.denominator)


def resolve_density(value: Division) -> int:
    """Coerce a division argument to an int tick count.

    An int passes through unchanged. A ``(numerator, denominator)`` tuple is
    converted via ``d2t``.
    """
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("division must be a (numerator, denominator) tuple")
        return d2t(value[0], value[1])
    return value


__all__ = [
    "TICKS_PER_BEAT",
    "Division",
    "Position",
    "Tick",
    "TickResolver",
    "TimeCalculator",
    "t2p",
    "p2t",
    "push_beat_events",
    "pop_beat_events",
    "resolve_tick",
    "push_tick_resolver",
    "pop_tick_resolver",
    "d2t",
    "t2d",
    "resolve_density",
]
