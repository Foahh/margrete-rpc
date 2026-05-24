from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from margrete_rpc.model.constant import TICKS_PER_BEAT
from margrete_rpc.model.event import BeatEvent


@dataclass(frozen=True, slots=True)
class Pos:
    bar: int
    beat: int
    offset: int


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


def _build_time_signatures(beat_events: Iterable[BeatEvent]) -> list[_TimeSignature]:
    ordered = sorted(
        (e for e in beat_events if e.bar >= 0),
        key=lambda e: e.bar,
    )
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
        segments.append(
            _TimeSignature(event.bar, tick, event.beats_per_bar, event.beat_unit)
        )
    return segments


def _measure_length(ts: _TimeSignature) -> int:
    return TICKS_PER_BEAT // ts.beat_unit * ts.beats_per_bar


class ChartTime:
    def __init__(self, beat_events: Iterable[BeatEvent]) -> None:
        self._segments = _build_time_signatures(beat_events)

    def t2p(self, tick: int) -> Pos:
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
        return Pos(ts.bar + bars_since, beat, offset)

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


def t2p(tick: int, *, beat_events: Iterable[BeatEvent]) -> Pos:
    return ChartTime(beat_events).t2p(tick)


__all__ = ["ChartTime", "Pos", "t2p"]
