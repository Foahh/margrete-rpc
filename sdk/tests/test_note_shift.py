from margrete_rpc.chart.notes import (
    Air,
    AirCrush,
    AirDirection,
    AirHold,
    AirSlide,
    Color,
    ColorValue,
    Hold,
    Slide,
    Tap,
)
from margrete_rpc.chart.raw import RawNote


def _collect_geometry(note: RawNote) -> list[tuple[int, int, int, int]]:
    rows = [(int(note.t), note.x, note.w, note.h)]
    for child in note.children:
        rows.extend(_collect_geometry(child))
    return rows


def test_note_ground_with_air_and_air_slide_shifts_all_raw():
    tap = Tap(t=100, x=4, w=2).with_air(AirSlide(t=100, x=4, w=2, h=80).with_step(t=200, x=8, w=2, h=100))

    tap.shift(t=5, h=10)

    assert tap.t == 105
    air = tap._air
    assert isinstance(air, AirSlide)
    assert air.t == 105
    assert air.h == 90
    assert air.joints[-1].t == 205
    assert air.joints[-1].h == 110


def test_note_slide_shifts_begin_and_all_joints():
    slide = Slide(t=100, x=0, w=4).with_step(t=150, x=2, w=4).with_step(t=200, x=4, w=4)
    slide.shift(t=10, x=1, w=1, h=5)
    assert slide.t == 110
    assert slide.x == 1
    assert slide.w == 5
    assert slide._info.h == 85
    assert slide.joints[0].t == 160
    assert slide.joints[0].x == 3
    assert slide.joints[1].t == 210
    assert slide.joints[1].x == 5


def test_note_hold_and_slide_air_shift():
    hold = (
        Hold(t=50, x=1, w=3)
        .with_step(t=120, x=1, w=3)
        .with_air(AirHold(t=120, x=1, w=3, h=70).with_step(t=160, x=1, w=3, h=70))
    )
    hold.shift(t=3)

    assert hold.t == 53
    end = hold.joints[-1]
    assert end.t == 123
    assert isinstance(hold._air, AirHold)
    assert hold._air.t == 123
    assert hold._air.joints[-1].t == 163

    slide = Slide(t=10, x=0, w=2).with_step(t=30, x=4, w=2).with_air(Air(AirDirection.DOWN, t=30, x=4, w=2))
    slide.shift(h=20)
    assert slide._info.h == 100
    assert isinstance(slide._air, Air)


def test_note_air_crush_shifts_begin_controls_and_end():
    crush = (
        AirCrush(t=0, x=1, w=2, h=80, gap=5, color=Color.RED)
        .with_ctrl(t=50, x=2, w=2, h=90)
        .with_ctrl(t=100, x=3, w=2, h=70)
    )
    crush.shift(t=7, h=3)
    assert crush.t == 7
    assert crush.h == 83
    assert crush.joints[0].t == 57
    assert crush.joints[0].h == 93
    assert crush.joints[1].t == 107
    assert crush.joints[1].h == 73
    assert crush.gap == 5
    assert crush.color is ColorValue.RED


def test_shift_chaining_returns_same_object_and_composes():
    tap = Tap(t=10, x=4, w=2)
    result = tap.shift(t=5).shift(x=2)
    assert result is tap
    assert tap.t == 15
    assert tap.x == 6


def test_shift_does_not_validate_negative_tick_or_width():
    tap = Tap(t=5, x=0, w=2)
    tap.shift(t=-10_000, w=-5)
    assert tap.t == -9995
    assert tap.w == -3


def test_shift_callable_maps_every_tick_across_tree():
    air = AirSlide(t=100, x=2, w=4, h=80).with_step(t=200, x=8, w=2, h=100)
    slide = Slide(t=100, x=0, w=4).with_step(t=200, x=2, w=4).with_air(air)
    slide.shift(t=lambda v: v * 2)
    assert slide.t == 200
    assert slide.joints[0].t == 400
    assert slide._air.joints[-1].t == 400


def test_shift_callable_per_field_mixes_with_int_delta():
    tap = Tap(t=480, x=4, w=2)
    tap.shift(t=lambda v: v // 2, x=2)
    assert tap.t == 240
    assert tap.x == 6


def test_shift_air_slide_standalone_shifts_begin_and_joints():
    air = AirSlide(t=100, x=8, w=2, h=80).with_step(t=200, x=8, w=2, h=100)
    air.shift(t=5, h=10)
    assert air.t == 105
    assert air.h == 90
    assert air.joints[-1].t == 205
    assert air.joints[-1].h == 110


def test_shift_callable_raises_if_non_monotone():
    import pytest

    slide = Slide(t=100, x=0, w=4).with_step(t=500, x=2, w=4)
    with pytest.raises(ValueError, match="non-monotone"):
        slide.shift(t=lambda v: v % 480)
