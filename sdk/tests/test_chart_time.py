from __future__ import annotations

import pytest

from margrete_rpc.chart.events import BeatEvent
from margrete_rpc.chart.time import (
    TICKS_PER_BEAT,
    d2t,
    p2t,
    pop_beat_events,
    push_beat_events,
    resolve_density,
    t2d,
    t2p,
)


def test_t2p_origin_4_4():
    assert t2p(0, beat_events=[]) == (0, 0, 0)


def test_t2p_second_beat_4_4():
    # beat_tick = 1920 // 4 = 480
    assert t2p(480, beat_events=[]) == (0, 1, 0)


def test_t2p_second_bar_4_4():
    assert t2p(TICKS_PER_BEAT, beat_events=[]) == (1, 0, 0)


def test_t2p_with_explicit_4_4_at_bar_zero():
    events = [BeatEvent(bar=0, beats_per_bar=4, beat_unit=4)]
    assert t2p(960, beat_events=events) == (0, 2, 0)


def test_t2p_rejects_negative_tick():
    with pytest.raises(ValueError, match="tick"):
        t2p(-1, beat_events=[])


def test_p2t_bar_beat_offset_4_4():
    assert p2t(1, 0, 0, beat_events=[]) == TICKS_PER_BEAT


def test_p2t_defaults_beat_and_offset():
    assert p2t(1, beat_events=[]) == TICKS_PER_BEAT


def test_round_trip_ticks_4_4():
    for tick in (0, 1, 479, 480, 960, 1919, 1920, 5000):
        assert p2t(*t2p(tick, beat_events=[]), beat_events=[]) == tick


def test_round_trip_positions_4_4():
    for pos in ((0, 0, 0), (0, 3, 479), (2, 1, 100)):
        assert t2p(p2t(*pos, beat_events=[]), beat_events=[]) == pos


def test_t2p_time_signature_change_at_bar_4():
    events = [BeatEvent(bar=4, beats_per_bar=3, beat_unit=4)]
    assert t2p(7680, beat_events=events) == (4, 0, 0)
    assert t2p(7680 + 480, beat_events=events) == (4, 1, 0)
    assert p2t(4, 1, 0, beat_events=events) == 7680 + 480


def test_p2t_rejects_beat_out_of_range():
    with pytest.raises(ValueError, match="beat"):
        p2t(0, 4, 0, beat_events=[])


def test_p2t_rejects_offset_out_of_range():
    with pytest.raises(ValueError, match="offset"):
        p2t(0, 0, 480, beat_events=[])


def test_t2p_p2t_use_context_beat_events():
    events = [BeatEvent(bar=0, beats_per_bar=3, beat_unit=4)]
    token = push_beat_events(events)
    try:
        # 3/4: bar length = 3 * 480 = 1440
        assert t2p(1440) == (1, 0, 0)
        assert p2t(1) == 1440
    finally:
        pop_beat_events(token)
    # After popping, falls back to 4/4 default
    assert t2p(1920) == (1, 0, 0)


def test_explicit_beat_events_override_context():
    events_3_4 = [BeatEvent(bar=0, beats_per_bar=3, beat_unit=4)]
    token = push_beat_events(events_3_4)
    try:
        assert t2p(1920, beat_events=[]) == (1, 0, 0)  # explicit [] => 4/4
    finally:
        pop_beat_events(token)


def test_t2p_rejects_duplicate_beat_bar():
    events = [
        BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
        BeatEvent(bar=4, beats_per_bar=3, beat_unit=4),
        BeatEvent(bar=4, beats_per_bar=6, beat_unit=8),
    ]
    with pytest.raises(ValueError, match="duplicate BeatEvent bar 4"):
        t2p(0, beat_events=events)


def test_t2p_context_rejects_duplicate_beat_bar():
    events = [
        BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
        BeatEvent(bar=0, beats_per_bar=3, beat_unit=4),
    ]
    token = push_beat_events(events)
    try:
        with pytest.raises(ValueError, match="duplicate BeatEvent bar 0"):
            t2p(0)
    finally:
        pop_beat_events(token)


# --- d2t / t2d / resolve_density ---


def test_d2t_1_over_384():
    # (1/384) * 1920 = 5
    assert d2t(1, 384) == 5


def test_d2t_1_over_4():
    assert d2t(1, 4) == TICKS_PER_BEAT // 4


def test_d2t_whole_beat():
    assert d2t(1, 1) == TICKS_PER_BEAT


def test_d2t_rejects_non_integer_division():
    with pytest.raises(ValueError, match="whole tick"):
        d2t(1, 7)


def test_d2t_rejects_zero_denominator():
    with pytest.raises(ValueError, match="positive"):
        d2t(1, 0)


def test_t2d_round_trip():
    for ticks in (0, 1, 5, 480, 960, 1920, 3840):
        n, d = t2d(ticks)
        assert d2t(n, d) == ticks


def test_t2d_reduces_fraction():
    assert t2d(5) == (1, 384)
    assert t2d(480) == (1, 4)
    assert t2d(1920) == (1, 1)


def test_t2d_rejects_non_int():
    with pytest.raises(TypeError):
        t2d(1.5)  # type: ignore[arg-type]


def test_t2d_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        t2d(-1)


def test_resolve_density_passes_int_through():
    assert resolve_density(5) == 5
    assert resolve_density(0) == 0


def test_resolve_density_tuple():
    assert resolve_density((1, 384)) == 5
    assert resolve_density((1, 4)) == TICKS_PER_BEAT // 4


def test_resolve_density_rejects_wrong_tuple_length():
    with pytest.raises(ValueError, match="numerator, denominator"):
        resolve_density((1, 2, 3))  # type: ignore[arg-type]


def test_noteinfo_option_value_accepts_division_tuple():
    from margrete_rpc.chart.notes.types import NoteInfo

    info = NoteInfo(option_value=(1, 384))
    assert info.option_value == 5

    info.option_value = (1, 4)
    assert info.option_value == TICKS_PER_BEAT // 4


def test_aircrush_gap_accepts_division_tuple():
    from margrete_rpc.chart.notes import AirCrush

    note = AirCrush(0, 0, 4, h=80, gap=(1, 384))
    assert note.gap == 5

    note.gap = (1, 4)
    assert note.gap == TICKS_PER_BEAT // 4
