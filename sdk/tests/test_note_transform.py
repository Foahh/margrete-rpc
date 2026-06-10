from __future__ import annotations

import pytest

from margrete_rpc.chart.notes import (
    STANDARD_FIELD_WIDTH,
    AirCrush,
    AirHold,
    AirSlide,
    Color,
    ColorValue,
    Damage,
    Extap,
    Flick,
    Hold,
    JointKind,
    Slide,
    Tap,
    merge,
    split,
    wrap_raw_note,
)

# --------------------------------------------------------------------------- clone


def test_clone_is_deep_and_detached():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4)
    slide._id = 9
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
    tap = Tap(t=0, x=4, w=2, _id=5).with_air(
        AirSlide(t=0, x=4, w=2, h=80).with_step(t=100, x=8, w=2, h=90)
    )
    tap._air._id = 7

    clone = tap.clone()
    assert clone._air is not tap._air
    assert clone._air._id is None
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
    slide = Slide(t=100, x=0, w=4).with_step(t=150, x=2, w=4).with_step(t=200, x=4, w=4)
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
    slide = Slide(t=10, x=0, w=4).with_step(t=470, x=2, w=4).with_step(t=965, x=4, w=4)
    slide.align(480)
    assert slide.t == 0
    assert [int(j.t) for j in slide.joints] == [480, 960]


def test_align_rejects_non_positive_interval():
    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).align(0)


# ----------------------------------------------------------------------------- scale


def test_scale_multiplies_every_tick():
    slide = Slide(t=100, x=0, w=4).with_step(t=200, x=2, w=4)
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
    slide = Slide(t=100, x=0, w=4).with_step(t=300, x=2, w=4)
    slide.scale(2, pivot=100)
    assert slide.t == 100  # pivot stays put
    assert int(slide.joints[-1].t) == 500  # 100 + (300 - 100) * 2


# ------------------------------------------------------------------------------ flip


def test_flip_mirrors_lane_and_is_self_inverse():
    tap = Tap(t=0, x=1, w=2)
    flipped = tap.flipped()
    assert flipped.x == STANDARD_FIELD_WIDTH - 1 - 2
    assert flipped.flip().x == 1  # flipping twice restores
    assert tap.x == 1  # copy left original alone


def test_flip_swaps_left_right_directions():
    assert Extap(t=0, x=0, w=2, dir="left").flipped().dir.value == "right"
    assert Flick(t=0, x=0, w=2, dir="right").flipped().dir.value == "left"


def test_flip_custom_field_width():
    assert Tap(t=0, x=2, w=2).flipped(field=8).x == 8 - 2 - 2


def test_flip_recurses_into_joints_and_air():
    from margrete_rpc.chart.notes import Air, AirDirection

    slide = (
        Slide(t=0, x=0, w=2)
        .with_step(t=100, x=10, w=2)
        .with_air(Air(AirDirection.UP_LEFT, t=100, x=10, w=2))
    )
    slide.flip()
    assert slide.x == STANDARD_FIELD_WIDTH - 0 - 2
    assert slide.joints[0].x == STANDARD_FIELD_WIDTH - 10 - 2
    assert slide._air.dir.value == "up_right"


# --------------------------------------------------------------------------- convert


def test_converted_returns_detached_copy_without_touching_original():
    tap = Tap(t=120, x=4, w=2, _id=7)
    tap._info.til = 3
    flick = tap.converted(Flick, dir="left")

    assert isinstance(flick, Flick)
    assert isinstance(tap, Tap)  # original is left alone
    assert (int(flick.t), flick.x, flick.w) == (120, 4, 2)
    assert flick._info.til == 3
    assert flick.dir.value == "left"
    assert flick._id is None

    assert isinstance(flick.converted(Damage), Damage)


def test_converted_ground_preserves_attached_air_detached():
    tap = Tap(t=0, x=4, w=2, _id=4).with_air(
        AirSlide(t=0, x=4, w=2, h=80).with_step(t=100, x=8, w=2, h=90)
    )
    extap = tap.converted(Extap)
    assert isinstance(extap, Extap)
    assert extap._air is not tap._air
    assert extap._air._id is None
    assert extap._air.joints[-1].h == 90


def test_converted_slide_to_air_slide_and_back():
    slide = Slide(t=100, x=0, w=4).with_step(t=150, x=2, w=4).with_ctrl(t=200, x=4, w=4)
    air = slide.converted(AirSlide, h=80)

    assert isinstance(air, AirSlide)
    assert isinstance(slide, Slide)  # original unchanged
    assert (int(air.t), air.x, air.w) == (100, 0, 4)
    assert air.joints[-1].h == 80
    assert [(int(j.t), str(j.kind)) for j in air.joints] == [(150, "step"), (200, "control")]

    back = air.converted(Slide)
    assert isinstance(back, Slide)
    assert (int(back.t), back.x, back.w) == (100, 0, 4)
    assert [(int(j.t), str(j.kind)) for j in back.joints] == [(150, "step"), (200, "control")]


def test_converted_hold_to_air_hold():
    hold = Hold(t=0, x=1, w=3).with_step(t=120, x=1, w=3)
    air = hold.converted(AirHold, h=70)
    assert isinstance(air, AirHold)
    assert air.joints[-1].h == 70


def test_converted_hold_to_slide():
    hold = Hold(t=0, x=1, w=3).with_step(t=120, x=1, w=3)
    slide = hold.converted(Slide)
    assert isinstance(slide, Slide)
    assert (int(slide.t), slide.x, slide.w) == (0, 1, 3)
    assert int(slide.joints[-1].t) == 120


def test_converted_slide_to_aircrush():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    crush = slide.converted(AirCrush, h=80, gap_t=4)
    assert isinstance(crush, AirCrush)
    assert crush.h == 80
    assert crush.gap_t == 4
    assert int(crush.joints[-1].t) == 100


def test_converted_aircrush_to_airslide():
    crush = AirCrush(t=0, x=2, w=2, h=80, gap_t=5).with_ctrl(t=100, x=4, w=2, h=100)
    air = crush.converted(AirSlide)
    assert isinstance(air, AirSlide)
    assert (int(air.t), air.x, air.w) == (0, 2, 2)
    assert air.joints[-1].h == 100
    assert air._id is None  # detached


def test_convert_cross_shape_raises():
    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).converted(Slide)
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=2).with_step(t=100, x=2, w=2).converted(Tap)
    # Slide-like group cannot convert to Hold or AirHold
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4).converted(Hold)
    with pytest.raises(ValueError):
        Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4).converted(AirHold)
    with pytest.raises(ValueError):
        AirCrush(t=0, x=0, w=2, h=80, gap_t=4).with_ctrl(t=100, x=2, w=2, h=80).converted(Hold)


def test_convert_with_air_to_non_attachable_target_drops_air_silently():
    from margrete_rpc.chart.notes import Air, AirDirection

    slide = (
        Slide(t=0, x=0, w=4)
        .with_step(t=100, x=2, w=4)
        .with_air(Air(AirDirection.UP, t=100, x=2, w=4))
    )
    crush = slide.converted(AirCrush, h=80, gap_t=4)
    assert isinstance(crush, AirCrush)
    assert getattr(crush, "_air", None) is None


def test_convert_with_air_to_attachable_target_carries_air():
    hold = (
        Hold(t=0, x=1, w=3)
        .with_step(t=120, x=1, w=3)
        .with_air(AirSlide(t=120, x=1, w=3, h=80).with_step(t=150, x=4, w=2, h=90))
    )
    slide = hold.converted(Slide)
    assert isinstance(slide, Slide)
    assert slide._air is not None
    assert slide._air is not hold._air
    assert slide._air.joints[-1].h == 90


# ----------------------------------------------------------------------------- merge


def test_merge_as_steps_concatenates_joints():
    a = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).with_step(t=300, x=6, w=4)
    merged = merge([a, b], join=JointKind.STEP)

    assert isinstance(merged, Slide)
    assert merged._id is None
    assert [(int(j.t), str(j.kind)) for j in merged.joints] == [
        (100, "step"),
        (200, "step"),
        (300, "step"),
    ]
    merged.to_raw()  # stays a valid slide


def test_merge_as_control_points():
    a = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).with_step(t=300, x=6, w=4)
    merged = merge([a, b], join="control")
    assert [str(j.kind) for j in merged.joints] == ["control", "control", "step"]


def test_merge_custom_strategy_callable():
    a = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).with_step(t=300, x=6, w=4)
    merged = merge([a, b], join=lambda prev, nxt: JointKind.CONTROL)
    assert str(merged.joints[0].kind) == "control"


def test_merge_sorts_unordered_input_by_start_tick():
    a = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    b = Slide(t=200, x=4, w=4).with_step(t=300, x=6, w=4)
    merged = merge([b, a], join=JointKind.STEP)  # given out of order
    assert isinstance(merged, Slide)
    assert [int(j.t) for j in merged.joints] == [100, 200, 300]


def test_merge_rejects_mismatched_types_and_overlap():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4)
    crush = AirCrush(t=200, x=0, w=2, h=80, gap_t=4).with_ctrl(t=300, x=2, w=2, h=80)
    with pytest.raises(TypeError):
        merge([slide, crush])
    with pytest.raises(ValueError):  # second note starts before the first ends
        merge(
            [
                Slide(t=0, x=0, w=4).with_step(t=100, x=2, w=4),
                Slide(t=50, x=4, w=4).with_step(t=150, x=6, w=4),
            ]
        )


def test_merge_single_note_returns_detached_clone():
    a = Slide(t=0, x=0, w=4, _id=8).with_step(t=100, x=2, w=4)
    merged = merge([a])
    assert merged is not a
    assert merged._id is None


# ----------------------------------------------------------------------------- split


def test_split_at_existing_joint():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4).with_step(t=200, x=8, w=4)
    first, second = split(slide, slide.joints[0])

    assert int(first.joints[-1].t) == 100
    assert (int(second.t), second.x) == (100, 4)
    assert [int(j.t) for j in second.joints] == [200]
    first.to_raw()
    second.to_raw()


def test_split_at_tick_interpolates_mid_segment():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4).with_step(t=200, x=8, w=4)
    first, second = split(slide, 50)

    # halfway between (0,0) and (100,4) -> x == 2
    assert (int(first.joints[-1].t), first.joints[-1].x) == (50, 2)
    assert (int(second.t), second.x) == (50, 2)
    assert [int(j.t) for j in second.joints] == [100, 200]


def test_split_then_merge_round_trips_air_crush():
    crush = (
        AirCrush(t=0, x=2, w=2, h=80, gap_t=5, color=Color.RED)
        .with_ctrl(t=100, x=4, w=2, h=100)
        .with_ctrl(t=200, x=6, w=2, h=120)
    )
    first, second = split(crush, 100)
    assert first.gap_t == 5
    assert first.color is ColorValue.RED

    merged = merge([first, second])
    assert [(int(j.t), j.x, j.w, j.h) for j in merged.joints] == [
        (int(j.t), j.x, j.w, j.h) for j in crush.joints
    ]
    merged.to_raw()


def test_split_errors():
    with pytest.raises(ValueError):
        split(Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4), 50)  # only one joint
    with pytest.raises(ValueError):
        split(
            Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4).with_step(t=200, x=8, w=4), 500
        )  # tick out of range
    with pytest.raises(TypeError):
        split(Hold(t=0, x=1, w=3).with_step(t=100, x=1, w=3), 50)  # holds are not splittable


# --------------------------------------------------------------------------- clamp_w


def test_clamp_w_left_moves_x_and_shrinks_w():
    tap = Tap(t=0, x=2, w=4)
    tap.clamp_w(left=4)
    assert tap.x == 4
    assert tap.w == 2  # was 4, lost 2 from left side


def test_clamp_w_left_minimum_width_one():
    tap = Tap(t=0, x=0, w=1)
    tap.clamp_w(left=3)
    assert tap.x == 3
    assert tap.w == 1


def test_clamp_w_right_shrinks_w():
    tap = Tap(t=0, x=13, w=5)
    tap.clamp_w(right=16)
    assert tap.x == 13
    assert tap.w == 3  # 16 - 13


def test_clamp_w_right_note_entirely_past_boundary():
    tap = Tap(t=0, x=16, w=2)
    tap.clamp_w(right=16)
    assert tap.x == 15
    assert tap.w == 1


def test_clamp_w_no_change_when_within_bounds():
    tap = Tap(t=0, x=4, w=4)
    tap.clamp_w(left=0, right=STANDARD_FIELD_WIDTH)
    assert tap.x == 4
    assert tap.w == 4


def test_clamped_w_returns_copy_leaves_original():
    tap = Tap(t=0, x=0, w=6)
    result = tap.clamped_w(left=2)
    assert result is not tap
    assert result._id is None
    assert result.x == 2
    assert result.w == 4
    assert tap.x == 0  # original untouched


def test_clamp_w_slide_applies_to_all_joints():
    slide = Slide(t=0, x=1, w=3).with_step(t=100, x=13, w=5).with_step(t=200, x=0, w=8)
    slide.clamp_w(left=2, right=15)
    assert slide.x == 2 and slide.w == 2  # x was 1 -> 2, w was 3 -> 3-(2-1)=2
    assert slide.joints[0].x == 13 and slide.joints[0].w == 2  # 13+5=18 > 15 -> w=15-13=2
    assert slide.joints[1].x == 2 and slide.joints[1].w == 6  # x=0 -> 2, w=8-2=6; 2+6=8 <= 15


def test_clamp_w_tap_with_air_clamps_air_too():
    from margrete_rpc.chart.notes import Air, AirDirection

    tap = Tap(t=0, x=0, w=6).with_air(Air(AirDirection.UP, t=0, x=0, w=6))
    tap.clamp_w(left=2, right=14)
    assert tap.x == 2 and tap.w == 4
    assert tap._air.x == 2 and tap._air.w == 4


def test_clamp_w_rejects_invalid_bounds():
    import pytest

    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).clamp_w(left=8, right=4)
    with pytest.raises(ValueError):
        Tap(t=0, x=0, w=2).clamp_w(left=4, right=4)


# ----------------------------------------------------------------- round-trip safety


def test_produced_notes_round_trip_through_raw():
    slide = Slide(t=0, x=0, w=4).with_step(t=100, x=4, w=4).with_step(t=200, x=8, w=4)
    first, second = split(slide, 100)
    merged = merge([first, second])
    for note in (first, second, merged, slide.flipped(), slide.shifted(t=480)):
        assert wrap_raw_note(note.to_raw()) is not None
