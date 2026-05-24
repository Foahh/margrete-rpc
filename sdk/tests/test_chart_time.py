from __future__ import annotations

import pytest

from margrete_rpc.model.chart_time import Pos, p2t, t2p
from margrete_rpc.model.constant import TICKS_PER_BEAT
from margrete_rpc.model.event import BeatEvent


def test_t2p_origin_4_4():
    assert t2p(0, beat_events=[]) == Pos(0, 0, 0)


def test_t2p_second_beat_4_4():
    # beat_tick = 1920 // 4 = 480
    assert t2p(480, beat_events=[]) == Pos(0, 1, 0)


def test_t2p_second_bar_4_4():
    assert t2p(TICKS_PER_BEAT, beat_events=[]) == Pos(1, 0, 0)


def test_t2p_with_explicit_4_4_at_bar_zero():
    events = [BeatEvent(bar=0, beats_per_bar=4, beat_unit=4)]
    assert t2p(960, beat_events=events) == Pos(0, 2, 0)


def test_t2p_rejects_negative_tick():
    with pytest.raises(ValueError, match="tick"):
        t2p(-1, beat_events=[])


def test_p2t_pos_form_4_4():
    assert p2t(Pos(0, 2, 0), beat_events=[]) == 960


def test_p2t_three_int_form_4_4():
    assert p2t(1, 0, 0, beat_events=[]) == TICKS_PER_BEAT


def test_round_trip_ticks_4_4():
    for tick in (0, 1, 479, 480, 960, 1919, 1920, 5000):
        assert p2t(t2p(tick, beat_events=[]), beat_events=[]) == tick


def test_round_trip_positions_4_4():
    for pos in (Pos(0, 0, 0), Pos(0, 3, 479), Pos(2, 1, 100)):
        assert t2p(p2t(pos, beat_events=[]), beat_events=[]) == pos


def test_t2p_time_signature_change_at_bar_4():
    events = [BeatEvent(bar=4, beats_per_bar=3, beat_unit=4)]
    assert t2p(7680, beat_events=events) == Pos(4, 0, 0)
    assert t2p(7680 + 480, beat_events=events) == Pos(4, 1, 0)
    assert p2t(4, 1, 0, beat_events=events) == 7680 + 480


def test_p2t_rejects_beat_out_of_range():
    with pytest.raises(ValueError, match="beat"):
        p2t(Pos(0, 4, 0), beat_events=[])


def test_p2t_rejects_offset_out_of_range():
    with pytest.raises(ValueError, match="offset"):
        p2t(Pos(0, 0, 480), beat_events=[])
