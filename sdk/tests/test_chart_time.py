from __future__ import annotations

import pytest

from margrete_rpc.model.chart_time import Pos, t2p
from margrete_rpc.model.constant import TICKS_PER_BEAT
from margrete_rpc.model.event import BeatEvent


def test_t2p_origin_4_4():
    assert t2p(0, beat_events=[]) == Pos(0, 0, 0)


def test_t2p_second_beat_4_4():
    assert t2p(480, beat_events=[]) == Pos(0, 1, 0)


def test_t2p_second_bar_4_4():
    assert t2p(TICKS_PER_BEAT, beat_events=[]) == Pos(1, 0, 0)


def test_t2p_with_explicit_4_4_at_bar_zero():
    events = [BeatEvent(bar=0, beats_per_bar=4, beat_unit=4)]
    assert t2p(960, beat_events=events) == Pos(0, 2, 0)


def test_t2p_rejects_negative_tick():
    with pytest.raises(ValueError, match="tick"):
        t2p(-1, beat_events=[])
