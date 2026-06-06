from __future__ import annotations

import pytest

from margrete_rpc import (
    AirCrush,
    AirHold,
    AirSlide,
    Color,
    ColorValue,
    Damage,
    Direction,
    Extap,
    Flick,
    Hold,
    JointKind,
    Slide,
    Tap,
    merge,
    split,
)
from margrete_rpc.chart.note import FIELD_WIDTH, wrap_node

# --------------------------------------------------------------------------- clone


def test_clone_is_deep_and_detached():
    slide = Slide(t=0, x=0, w=4, _id=9).step(100, x=4, w=4)
    slide.joints[0]._id = 11

    clone = slide.clone()

    assert clone is not slide
    assert clone._id is None
    assert clone.joints[0]._id is None
    assert slide._id == 9  # original untouched
    assert slide.joints[0]._id == 11

    clone.joints[0].x = 99
    assert slide.joints[0].x == 4  # deep copy, original unaffected


def test_clone_preserves_attached_air_detached():
    tap = Tap(t=0, x=4, w=2, _id=5).air(AirSlide(h=80).step(100, x=8, w=2, h=90))
    tap._air._air_id = 7

    clone = tap.clone()
    assert clone._air is not tap._air
    assert clone._air._air_id is None
    assert clone._air.joints[-1].h == 90


# ---------------------------------------------------------------------------- shift


def test_shifted_returns_detached_copy_without_touching_original():
    tap = Tap(t=10, x=4, w=2, _id=3)
    moved = tap.shifted(t=5, x=1)

    assert moved is not tap
    assert moved._id is None
    assert (moved.t, moved.x) == (15, 5)
    assert (tap.t, tap.x) == (10, 4)


def test_shift_callable_scales_every_tick():
    slide = Slide(t=100, x=0, w=4).step(150, x=2, w=4).step(200, x=4, w=4)
    result = slide.shift(t=lambda v: v * 2)

    assert result is slide
    assert slide.t == 200
    assert [int(j.t) for j in slide.joints] == [300, 400]


def test_shift_callable_and_int_compose_per_field():
    tap = Tap(t=480, x=4, w=2)
    tap.shift(t=lambda v: v // 2, x=1)
    assert tap.t == 240
    assert tap.x == 5


# ----------------------------------------------------------------------------- align


def test_align_snaps_to_nearest_by_default():
    assert Tap(t=503, x=0, w=2).aligned(480).t == 480
    assert Tap(t=720, x=0, w=2).aligned(480).t == 960


def test_align_floor_and_ceil_modes():
    assert Tap(t=500, x=0, w=2).aligned(480, mode="floor").t == 480
    assert Tap(t=500, x=0, w=2).aligned(480, mode="ceil").t == 960


def test_align_mutates_joints_too():
    slide = Slide(t=10, x=0, w=4).step(470, x=2, w=4).step(965, x=4, w=4)
    slide.align(480)
    assert slide.t == 0
    assert [int(j.t) for j in slide.joints] == [480, 960]


def test_align_rejects_non_positive_interval():
    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).align(0)


# ----------------------------------------------------------------------------- scale


def test_scale_multiplies_every_tick():
    slide = Slide(t=100, x=0, w=4).step(200, x=2, w=4)
    result = slide.scale(2)
    assert result is slide
    assert slide.t == 200
    assert int(slide.joints[-1].t) == 400


def test_scaled_returns_copy_and_supports_fractional_factor():
    tap = Tap(t=480, x=0, w=2)
    half = tap.scaled(0.5)
    assert half is not tap
    assert half.t == 240
    assert tap.t == 480  # original untouched


def test_scale_about_pivot_keeps_pivot_fixed():
    slide = Slide(t=100, x=0, w=4).step(300, x=2, w=4)
    slide.scale(2, pivot=100)
    assert slide.t == 100  # pivot stays put
    assert int(slide.joints[-1].t) == 500  # 100 + (300 - 100) * 2


# ------------------------------------------------------------------------------ flip


def test_flip_mirrors_lane_and_is_self_inverse():
    tap = Tap(t=0, x=1, w=2)
    flipped = tap.flipped()
    assert flipped.x == FIELD_WIDTH - 1 - 2
    assert flipped.flip().x == 1  # flipping twice restores
    assert tap.x == 1  # copy left original alone


def test_flip_swaps_left_right_directions():
    assert Extap(t=0, x=0, w=2, direction="left").flipped().direction.value == "right"
    assert Flick(t=0, x=0, w=2, direction="right").flipped().direction.value == "left"


def test_flip_custom_field_width():
    assert Tap(t=0, x=2, w=2).flipped(field=8).x == 8 - 2 - 2


def test_flip_recurses_into_joints_and_air():
    slide = Slide(t=0, x=0, w=2).step(100, x=10, w=2).air("up_left")
    slide.flip()
    assert slide.x == FIELD_WIDTH - 0 - 2
    assert slide.joints[0].x == FIELD_WIDTH - 10 - 2
    assert slide._air.direction.value == "up_right"


# --------------------------------------------------------------------------- convert


def test_converted_returns_detached_copy_without_touching_original():
    tap = Tap(t=120, x=4, w=2, _id=7)
    tap._info.til = 3
    flick = tap.converted(Flick, direction="left")

    assert isinstance(flick, Flick)
    assert isinstance(tap, Tap)  # original is left alone
    assert (int(flick.t), flick.x, flick.w) == (120, 4, 2)
    assert flick._info.til == 3
    assert flick.direction.value == "left"
    assert flick._id is None

    assert isinstance(flick.converted(Damage), Damage)


def test_converted_ground_preserves_attached_air_detached():
    tap = Tap(t=0, x=4, w=2, _id=4).air(AirSlide(h=80).step(100, x=8, w=2, h=90))
    extap = tap.converted(Extap)
    assert isinstance(extap, Extap)
    assert extap._air is not tap._air
    assert extap._air._id is None
    assert extap._air.joints[-1].h == 90


def test_converted_slide_to_air_slide_and_back():
    slide = Slide(t=100, x=0, w=4).step(150, x=2, w=4).control(200, x=4, w=4)
    air = slide.converted(AirSlide, h=80, direction="down")

    assert isinstance(air, AirSlide)
    assert isinstance(slide, Slide)  # original unchanged
    assert (int(air._info.t), air._info.x, air._info.w) == (100, 0, 4)
    assert air._air_info.direction == Direction.DOWN
    assert air.joints[-1].h == 80
    assert [(int(j.t), str(j.kind)) for j in air.joints] == [(150, "step"), (200, "control")]

    back = air.converted(Slide)
    assert isinstance(back, Slide)
    assert (int(back.t), back.x, back.w) == (100, 0, 4)
    assert [(int(j.t), str(j.kind)) for j in back.joints] == [(150, "step"), (200, "control")]


def test_converted_hold_to_air_hold():
    hold = Hold(t=0, x=1, w=3).step(120, x=1, w=3)
    air = hold.converted(AirHold, h=70)
    assert isinstance(air, AirHold)
    assert air.joints[-1].h == 70


def test_converted_hold_to_slide():
    hold = Hold(t=0, x=1, w=3).step(120, x=1, w=3)
    slide = hold.converted(Slide)
    assert isinstance(slide, Slide)
    assert (int(slide.t), slide.x, slide.w) == (0, 1, 3)
    assert int(slide.joints[-1].t) == 120


def test_converted_slide_to_aircrush():
    slide = Slide(t=0, x=0, w=4).step(100, x=2, w=4)
    crush = slide.converted(AirCrush, h=80, density=4)
    assert isinstance(crush, AirCrush)
    assert crush.h == 80
    assert crush.density == 4
    assert int(crush.joints[-1].t) == 100


def test_converted_aircrush_to_airslide():
    crush = AirCrush(t=0, x=2, w=2, h=80, density=5).control(100, x=4, w=2, h=100)
    air = crush.converted(AirSlide, direction="up")
    assert isinstance(air, AirSlide)
    assert (int(air._info.t), air._info.x, air._info.w) == (0, 2, 2)
    assert air.joints[-1].h == 100
    assert air._id is None  # detached


def test_convert_cross_shape_raises():
    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).converted(Slide)
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=2).step(100, x=2, w=2).converted(Tap)
    # Slide-like group cannot convert to Hold or AirHold
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=4).step(100, x=2, w=4).converted(Hold)
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=4).step(100, x=2, w=4).converted(AirHold)
    with pytest.raises(ValueError):
        AirCrush(t=0, x=0, w=2, h=80, density=4).control(100, x=2, w=2, h=80).converted(Hold)


# ----------------------------------------------------------------------------- merge


def test_merge_as_steps_concatenates_joints():
    a = Slide(t=0, x=0, w=4).step(100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).step(300, x=6, w=4)
    merged = merge([a, b], join=JointKind.STEP)

    assert isinstance(merged, Slide)
    assert merged._id is None
    assert [(int(j.t), str(j.kind)) for j in merged.joints] == [
        (100, "step"),
        (200, "step"),
        (300, "step"),
    ]
    merged.to_node()  # stays a valid slide


def test_merge_as_control_points():
    a = Slide(t=0, x=0, w=4).step(100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).step(300, x=6, w=4)
    merged = merge([a, b], join="control")
    assert [str(j.kind) for j in merged.joints] == ["control", "control", "step"]


def test_merge_custom_strategy_callable():
    a = Slide(t=0, x=0, w=4).step(100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).step(300, x=6, w=4)
    merged = merge([a, b], join=lambda prev, nxt: JointKind.CONTROL)
    assert str(merged.joints[0].kind) == "control"


def test_merge_sorts_unordered_input_by_start_tick():
    a = Slide(t=0, x=0, w=4).step(100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).step(300, x=6, w=4)
    merged = merge([b, a], join=JointKind.STEP)  # given out of order
    assert isinstance(merged, Slide)
    assert [int(j.t) for j in merged.joints] == [100, 200, 300]


def test_merge_rejects_mismatched_types_and_overlap():
    slide = Slide(0, 0, 4).step(100, 2, 4)
    crush = AirCrush(200, 0, 2, h=80, density=4).control(300, 2, 2, h=80)
    with pytest.raises(TypeError):
        merge([slide, crush])
    with pytest.raises(ValueError):  # second note starts before the first ends
        merge([Slide(0, 0, 4).step(100, 2, 4), Slide(50, 4, 4).step(150, 6, 4)])


def test_merge_single_note_returns_detached_clone():
    a = Slide(t=0, x=0, w=4, _id=8).step(100, x=2, w=4)
    merged = merge([a])
    assert merged is not a
    assert merged._id is None


# ----------------------------------------------------------------------------- split


def test_split_at_existing_joint():
    slide = Slide(t=0, x=0, w=4).step(100, x=4, w=4).step(200, x=8, w=4)
    first, second = split(slide, slide.joints[0])

    assert int(first.joints[-1].t) == 100
    assert (int(second.t), second.x) == (100, 4)
    assert [int(j.t) for j in second.joints] == [200]
    first.to_node()
    second.to_node()


def test_split_at_tick_interpolates_mid_segment():
    slide = Slide(t=0, x=0, w=4).step(100, x=4, w=4).step(200, x=8, w=4)
    first, second = split(slide, 50)

    # halfway between (0,0) and (100,4) -> x == 2
    assert (int(first.joints[-1].t), first.joints[-1].x) == (50, 2)
    assert (int(second.t), second.x) == (50, 2)
    assert [int(j.t) for j in second.joints] == [100, 200]


def test_split_then_merge_round_trips_air_crush():
    crush = (
        AirCrush(t=0, x=2, w=2, h=80, density=5, color=Color.RED)
        .control(100, x=4, w=2, h=100)
        .control(200, x=6, w=2, h=120)
    )
    first, second = split(crush, 100)
    assert first.density == 5
    assert first.color is ColorValue.RED

    merged = merge([first, second])
    assert [(int(j.t), j.x, j.w, j.h) for j in merged.joints] == [
        (int(j.t), j.x, j.w, j.h) for j in crush.joints
    ]
    merged.to_node()


def test_split_errors():
    with pytest.raises(ValueError):
        split(Slide(t=0, x=0, w=4).step(100, x=4, w=4), 50)  # only one joint
    with pytest.raises(ValueError):
        split(Slide(0, 0, 4).step(100, 4, 4).step(200, 8, 4), 500)  # tick out of range
    with pytest.raises(TypeError):
        split(Hold(0, 1, 3).step(100, 1, 3), 50)  # holds are not splittable


# ----------------------------------------------------------------- round-trip safety


def test_produced_notes_round_trip_through_node():
    slide = Slide(t=0, x=0, w=4).step(100, x=4, w=4).step(200, x=8, w=4)
    first, second = split(slide, 100)
    merged = merge([first, second])
    for note in (first, second, merged, slide.flipped(), slide.shifted(t=480)):
        assert wrap_node(note.to_node()) is not None
