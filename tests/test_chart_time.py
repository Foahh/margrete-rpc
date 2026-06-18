from __future__ import annotations

import pytest

from margrete_rpc.chart.events import BeatEvent
from margrete_rpc.chart.time import (
    TICK_RESOLUTION,
    div_to_tick,
    pop_beat_events,
    pos_to_tick,
    push_beat_events,
    resolve_division,
    tick_to_div,
    tick_to_pos,
)


def test_tick_to_pos_origin_4_4():
    assert tick_to_pos(0, beat_events=[]) == (0, 0, 0)


def test_tick_to_pos_second_beat_4_4():
    # beat_tick = 1920 // 4 = 480
    assert tick_to_pos(480, beat_events=[]) == (0, 1, 0)


def test_tick_to_pos_second_bar_4_4():
    assert tick_to_pos(TICK_RESOLUTION, beat_events=[]) == (1, 0, 0)


def test_tick_to_pos_with_explicit_4_4_at_bar_zero():
    events = [BeatEvent(bar=0, beats_per_bar=4, beat_unit=4)]
    assert tick_to_pos(960, beat_events=events) == (0, 2, 0)


def test_tick_to_pos_rejects_negative_tick():
    with pytest.raises(ValueError, match="tick"):
        tick_to_pos(-1, beat_events=[])


def test_pos_to_tick_bar_beat_offset_4_4():
    assert pos_to_tick(1, 0, 0, beat_events=[]) == TICK_RESOLUTION


def test_pos_to_tick_defaults_beat_and_offset():
    assert pos_to_tick(1, beat_events=[]) == TICK_RESOLUTION


def test_round_trip_ticks_4_4():
    for tick in (0, 1, 479, 480, 960, 1919, 1920, 5000):
        assert pos_to_tick(*tick_to_pos(tick, beat_events=[]), beat_events=[]) == tick


def test_round_trip_positions_4_4():
    for pos in ((0, 0, 0), (0, 3, 479), (2, 1, 100)):
        assert tick_to_pos(pos_to_tick(*pos, beat_events=[]), beat_events=[]) == pos


def test_tick_to_pos_time_signature_change_at_bar_4():
    events = [BeatEvent(bar=4, beats_per_bar=3, beat_unit=4)]
    assert tick_to_pos(7680, beat_events=events) == (4, 0, 0)
    assert tick_to_pos(7680 + 480, beat_events=events) == (4, 1, 0)
    assert pos_to_tick(4, 1, 0, beat_events=events) == 7680 + 480


def test_pos_to_tick_rejects_beat_out_of_range():
    with pytest.raises(ValueError, match="beat"):
        pos_to_tick(0, 4, 0, beat_events=[])


def test_pos_to_tick_rejects_offset_out_of_range():
    with pytest.raises(ValueError, match="offset"):
        pos_to_tick(0, 0, 480, beat_events=[])


def test_tick_to_pos_pos_to_tick_use_context_beat_events():
    events = [BeatEvent(bar=0, beats_per_bar=3, beat_unit=4)]
    token = push_beat_events(events)
    try:
        # 3/4: bar length = 3 * 480 = 1440
        assert tick_to_pos(1440) == (1, 0, 0)
        assert pos_to_tick(1) == 1440
    finally:
        pop_beat_events(token)
    # After popping, falls back to 4/4 default
    assert tick_to_pos(1920) == (1, 0, 0)


def test_explicit_beat_events_override_context():
    events_3_4 = [BeatEvent(bar=0, beats_per_bar=3, beat_unit=4)]
    token = push_beat_events(events_3_4)
    try:
        assert tick_to_pos(1920, beat_events=[]) == (1, 0, 0)  # explicit [] => 4/4
    finally:
        pop_beat_events(token)


def test_tick_to_pos_rejects_duplicate_beat_bar():
    events = [
        BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
        BeatEvent(bar=4, beats_per_bar=3, beat_unit=4),
        BeatEvent(bar=4, beats_per_bar=6, beat_unit=8),
    ]
    with pytest.raises(ValueError, match="duplicate BeatEvent bar 4"):
        tick_to_pos(0, beat_events=events)


def test_tick_to_pos_context_rejects_duplicate_beat_bar():
    events = [
        BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
        BeatEvent(bar=0, beats_per_bar=3, beat_unit=4),
    ]
    token = push_beat_events(events)
    try:
        with pytest.raises(ValueError, match="duplicate BeatEvent bar 0"):
            tick_to_pos(0)
    finally:
        pop_beat_events(token)


# --- div_to_tick / tick_to_div / resolve_division ---


def test_div_to_tick_1_over_384():
    # (1/384) * 1920 = 5
    assert div_to_tick(1, 384) == 5


def test_div_to_tick_1_over_4():
    assert div_to_tick(1, 4) == TICK_RESOLUTION // 4


def test_div_to_tick_whole_beat():
    assert div_to_tick(1, 1) == TICK_RESOLUTION


def test_div_to_tick_quantizes_non_integer_division():
    assert div_to_tick(1, 7) == TICK_RESOLUTION // 7


def test_div_to_tick_clamps_positive_sub_tick_division():
    assert div_to_tick(1, TICK_RESOLUTION + 1) == 1
    assert div_to_tick(1, 2048) == 1


def test_div_to_tick_rejects_zero_denominator():
    with pytest.raises(ValueError, match="positive"):
        div_to_tick(1, 0)


def test_tick_to_div_round_trip():
    for ticks in (0, 1, 5, 480, 960, 1920, 3840):
        n, d = tick_to_div(ticks)
        assert div_to_tick(n, d) == ticks


def test_tick_to_div_reduces_fraction():
    assert tick_to_div(5) == (1, 384)
    assert tick_to_div(480) == (1, 4)
    assert tick_to_div(1920) == (1, 1)


def test_tick_to_div_rejects_non_int():
    with pytest.raises(TypeError):
        tick_to_div(1.5)  # type: ignore[arg-type]


def test_tick_to_div_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        tick_to_div(-1)


def test_resolve_division_passes_int_through():
    assert resolve_division(5) == 5
    assert resolve_division(0) == 0


def test_resolve_division_tuple():
    assert resolve_division((1, 384)) == 5
    assert resolve_division((1, 4)) == TICK_RESOLUTION // 4


def test_resolve_division_rejects_wrong_tuple_length():
    with pytest.raises(ValueError, match="numerator, denominator"):
        resolve_division((1, 2, 3))  # type: ignore[arg-type]


def test_noteinfo_option_value_accepts_division_tuple():
    from margrete_rpc.chart.notes.types import NoteInfo

    info = NoteInfo(option_value=(1, 384))
    assert info.option_value == 5

    info.option_value = (1, 4)
    assert info.option_value == TICK_RESOLUTION // 4


def test_aircrush_gap_accepts_division_tuple():
    from margrete_rpc.chart.notes import AirCrush
    from margrete_rpc.chart.time import Division

    note = AirCrush(t=0, x=0, w=4, h=80, gap=(1, 384))
    assert note.gap == 5
    assert note.interval == Division(1, 384)
    assert note.interval.numerator == 1
    assert note.interval.denominator == 384

    note.gap = (1, 4)
    assert note.gap == TICK_RESOLUTION // 4
