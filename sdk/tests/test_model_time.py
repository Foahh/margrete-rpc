import pytest

from margrete_rpc.model.note.time import TICKS_PER_BEAT, b2t, beats_to_ticks, t2b, ticks_to_beats


def test_ticks_to_beats_reduced_fraction():
    assert ticks_to_beats(240) == (1, 8)
    assert ticks_to_beats(480) == (1, 4)
    assert ticks_to_beats(1920) == (1, 1)
    assert ticks_to_beats(300) == (5, 32)


def test_ticks_to_beats_zero():
    assert ticks_to_beats(0) == (0, 1)


def test_ticks_to_beats_fixed_denominator():
    assert ticks_to_beats(240, denominator=8) == (1, 8)
    assert ticks_to_beats(240, denominator=32) == (4, 32)


def test_ticks_to_beats_zero_ignores_requested_denominator():
    assert ticks_to_beats(0, denominator=16) == (0, 1)


def test_ticks_to_beats_fixed_denominator_rejects_inexact():
    with pytest.raises(ValueError, match="cannot be expressed exactly"):
        ticks_to_beats(241, denominator=8)


def test_ticks_to_beats_rejects_negative_tick():
    with pytest.raises(ValueError, match="non-negative"):
        ticks_to_beats(-1)


def test_ticks_to_beats_rejects_bad_denominator():
    with pytest.raises(ValueError, match="positive"):
        ticks_to_beats(240, denominator=0)
    with pytest.raises(ValueError, match="must not exceed"):
        ticks_to_beats(240, denominator=TICKS_PER_BEAT + 1)


def test_ticks_to_beats_rejects_non_int_tick():
    with pytest.raises(TypeError, match="tick must be int"):
        ticks_to_beats(True)  # type: ignore[arg-type]


def test_ticks_to_beats_rejects_non_int_denominator():
    with pytest.raises(TypeError, match="denominator must be int"):
        ticks_to_beats(240, denominator=8.0)  # type: ignore[arg-type]


def test_b2t_and_t2b_aliases():
    assert b2t((1, 8)) == 240
    assert t2b(240) == (1, 8)
    assert b2t is beats_to_ticks
    assert t2b is ticks_to_beats
