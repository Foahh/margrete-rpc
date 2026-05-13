import pytest

from margrete_rpc.model.tick import _TICKS_PER_BEAT
from margrete_rpc.util.time import bar_from_tick


def test_bar_from_tick_reduced_fraction():
    assert bar_from_tick(240) == (1, 8)
    assert bar_from_tick(480) == (1, 4)
    assert bar_from_tick(1920) == (1, 1)
    assert bar_from_tick(300) == (5, 32)


def test_bar_from_tick_zero():
    assert bar_from_tick(0) == (0, 1)


def test_bar_from_tick_fixed_denominator():
    assert bar_from_tick(240, denominator=8) == (1, 8)
    assert bar_from_tick(240, denominator=32) == (4, 32)


def test_bar_from_tick_zero_ignores_requested_denominator():
    assert bar_from_tick(0, denominator=16) == (0, 1)


def test_bar_from_tick_fixed_denominator_rejects_inexact():
    with pytest.raises(ValueError, match="cannot be expressed exactly"):
        bar_from_tick(241, denominator=8)


def test_bar_from_tick_rejects_negative_tick():
    with pytest.raises(ValueError, match="non-negative"):
        bar_from_tick(-1)


def test_bar_from_tick_rejects_bad_denominator():
    with pytest.raises(ValueError, match="positive"):
        bar_from_tick(240, denominator=0)
    with pytest.raises(ValueError, match="must not exceed"):
        bar_from_tick(240, denominator=_TICKS_PER_BEAT + 1)


def test_bar_from_tick_rejects_non_int_tick():
    with pytest.raises(TypeError, match="tick must be int"):
        bar_from_tick(True)  # type: ignore[arg-type]


def test_bar_from_tick_rejects_non_int_denominator():
    with pytest.raises(TypeError, match="denominator must be int"):
        bar_from_tick(240, denominator=8.0)  # type: ignore[arg-type]
