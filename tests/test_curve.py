import pytest

from margrete_rpc.chart.constants import DEFAULT_H
from margrete_rpc.chart.notes import (
    AirCrush,
    AirSlide,
    ColorValue,
    JointKind,
    RawNote,
    Slide,
    wrap_raw_note,
)
from margrete_rpc.chart.time import Division, div_to_tick
from margrete_rpc.chart.util import Curve, Waypoint, crease, envelope, rain
from margrete_rpc.chart.util.easing import EASINGS


def _ideal_x(path_t0: int, path_t1: int, x0: int, x1: int, ease_name: str, t: int) -> float:
    p = (t - path_t0) / (path_t1 - path_t0)
    return x0 + EASINGS[ease_name].solve(p) * (x1 - x0)


def test_anchor_alone_cannot_materialize() -> None:
    # A bare Curve(...) has a single waypoint: it is an anchor, not yet a usable path.
    anchor = Curve(t=0, x=0, h=40)
    assert isinstance(anchor, Curve)
    assert len(anchor) == 1
    with pytest.raises(ValueError):
        anchor.points()
    with pytest.raises(ValueError):
        anchor.to_slide(w=2)


def test_to_stores_sparse_control_waypoints() -> None:
    # .to() records one control waypoint per leg; nothing is sampled until points().
    path = Curve(t=0, x=0, h=40).to(t=960, x=12, h=120, ease_x="in_out_sine")
    assert len(path) == 2
    assert path.waypoints[0] == Waypoint(0, 0, 40)
    assert (path.waypoints[-1].t, path.waypoints[-1].x, path.waypoints[-1].h) == (960, 12, 120)
    # The per-axis easing of the leg is stored on the arriving waypoint.
    assert path.waypoints[-1].ease_x is EASINGS["in_out_sine"]
    assert path.waypoints[-1].ease_h is EASINGS["linear"]


def test_waypoint_resolves_position_and_easing_inputs() -> None:
    point = Waypoint((0, 2), 6, 40, ease_x="out_cubic", ease_h="in_sine")

    assert point.t == 960
    assert point.p == (0, 2, 0)
    assert point.ease_x is EASINGS["out_cubic"]
    assert point.ease_h is EASINGS["in_sine"]


def test_waypoint_assignment_resolves_position_and_easing_inputs() -> None:
    point = Waypoint(0, 0, 40)

    point.t = (1, 0)
    point.ease_x = "out_cubic"
    point.ease_h = "in_sine"

    assert point.t == 1920
    assert point.p == (1, 0, 0)
    assert point.ease_x is EASINGS["out_cubic"]
    assert point.ease_h is EASINGS["in_sine"]


def test_points_endpoints_exact() -> None:
    path = Curve(t=0, x=0, h=40).to(t=960, x=12, h=120, ease_x="in_out_sine")
    pts = path.points()
    assert (pts[0].t, pts[0].x, pts[0].h) == (0, 0, 40)
    assert (pts[-1].t, pts[-1].x, pts[-1].h) == (960, 12, 120)


def test_points_strictly_increasing_integer_ticks() -> None:
    pts = Curve(t=0, x=0).to(t=960, x=10, ease_x="in_out_cubic").points()
    ticks = [wp.t for wp in pts]
    assert ticks == sorted(set(ticks))
    assert all(isinstance(wp.t, int) for wp in pts)
    assert all(isinstance(wp.x, int) and isinstance(wp.h, int) for wp in pts)


def test_default_height_constant() -> None:
    path = Curve(t=0, x=0).to(t=480, x=8)
    assert all(wp.h == DEFAULT_H for wp in path.points())


def test_single_height_constant() -> None:
    # Height supplied on the anchor, omitted on the leg: held constant throughout.
    path = Curve(t=0, x=0, h=55).to(t=480, x=8)
    assert all(wp.h == 55 for wp in path.points())


def test_smaller_delta_axis_drives_no_flat_runs() -> None:
    # x moves 12 lanes, h moves 100 units: the smaller-delta axis (x) drives sampling, so x
    # advances one lane per joint -- no long flat X runs that would look like a blocky
    # staircase in the main view -- and the joint count tracks the x delta, not the h delta.
    pts = Curve(t=0, x=1, h=20).to(t=960, x=13, h=120, ease_h="in_out_sine").points()
    xs = [wp.x for wp in pts]
    assert xs == sorted(xs)
    assert all(b > a for a, b in zip(xs, xs[1:]))  # strictly increasing: no repeated X
    assert len(pts) <= 20  # far fewer than the ~100 the height delta would force


def test_height_drives_when_it_has_smaller_delta() -> None:
    # When height has the smaller delta, it drives instead and gains no flat runs.
    pts = Curve(t=0, x=0, h=0).to(t=960, x=12, h=4, ease_h="in_out_sine").points()
    hs = [wp.h for wp in pts]
    assert hs == sorted(hs)
    assert all(b > a for a, b in zip(hs, hs[1:]))


def test_eased_driver_has_no_flat_start_run() -> None:
    # A flat-starting easing must not emit two joints at the same lane (the j1 == j2 == 0 then
    # j3 == 1 artifact): the driver advances by one lane every joint, never repeating a value.
    pts = Curve(t=0, x=0).to(t=960, x=12, ease_x="in_quad").points()
    xs = [wp.x for wp in pts]
    assert all(b != a for a, b in zip(xs, xs[1:]))  # no flat lane segments anywhere


def test_non_monotonic_easing_overshoots() -> None:
    # A back-out easing overshoots above 1 before settling; forward sampling captures the
    # turning point as interior joints past the target lane -- impossible under value inversion.
    c1 = 1.70158
    out_back = lambda t: 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2  # noqa: E731
    pts = Curve(t=0, x=0).to(t=960, x=10, ease_x=out_back).points()
    assert (pts[0].t, pts[0].x) == (0, 0)
    assert (pts[-1].t, pts[-1].x) == (960, 10)
    assert any(wp.x > 10 for wp in pts)  # overshoot beyond the endpoint is materialized


def test_linear_collapses_to_endpoints() -> None:
    # A straight (linear) leg is exactly collinear everywhere, so it reduces to just its ends.
    pts = Curve(t=0, x=0, h=20).to(t=960, x=12, h=80).points()
    assert len(pts) == 2
    assert (pts[0].t, pts[0].x, pts[0].h) == (0, 0, 20)
    assert (pts[-1].t, pts[-1].x, pts[-1].h) == (960, 12, 80)


def test_sampling_error_within_half_lane() -> None:
    t0, t1, x0, x1 = 0, 960, 0, 15
    pts = Curve(t=t0, x=x0).to(t=t1, x=x1, ease_x="in_out_sine").points()
    for wp in pts:
        assert abs(wp.x - _ideal_x(t0, t1, x0, x1, "in_out_sine", wp.t)) <= 0.5


def test_closeness_to_ideal_curve() -> None:
    t0, t1, x0, x1 = 0, 960, 0, 15
    pts = Curve(t=t0, x=x0).to(t=t1, x=x1, ease_x="in_out_sine").points()
    for wp in pts:
        assert abs(wp.x - _ideal_x(t0, t1, x0, x1, "in_out_sine", wp.t)) <= 1.0


def test_linear_easing_is_collinear() -> None:
    pts = Curve(t=0, x=0).to(t=800, x=8).points()
    first, last = pts[0], pts[-1]
    slope = (last.x - first.x) / (last.t - first.t)
    for wp in pts:
        assert abs(wp.x - (first.x + slope * (wp.t - first.t))) <= 1.0


def test_multi_joint_chain_dedups_seam_and_keeps_endpoints() -> None:
    pts = (
        Curve(t=0, x=1, h=20)
        .to(t=480, x=7, h=70, ease_x="in_out_sine")
        .to(t=960, x=13, h=120, ease_x="out_quad")
    ).points()
    ticks = [wp.t for wp in pts]
    assert ticks == sorted(set(ticks))  # monotonic, no duplicate ticks
    assert all(b > a for a, b in zip(ticks, ticks[1:]))
    assert ticks.count(480) == 1  # the seam waypoint appears exactly once
    assert (pts[0].t, pts[0].x, pts[0].h) == (0, 1, 20)
    assert (pts[-1].t, pts[-1].x, pts[-1].h) == (960, 13, 120)
    seam = next(wp for wp in pts if wp.t == 480)
    assert (seam.x, seam.h) == (7, 70)  # interior leg endpoint is exact


def test_chained_to_matches_independent_then() -> None:
    chained = (
        Curve(t=0, x=0, h=20)
        .to(t=480, x=6, h=60, ease_x="in_out_sine")
        .to(t=960, x=12, h=120, ease_x="out_quad")
    )
    first = Curve(t=0, x=0, h=20).to(t=480, x=6, h=60, ease_x="in_out_sine")
    second = Curve(t=480, x=6, h=60).to(t=960, x=12, h=120, ease_x="out_quad")
    # Control waypoints (with their easing) match, and so does the quantized path.
    assert chained.waypoints == first.then(second).waypoints
    assert chained.points() == first.then(second).points()


def test_per_leg_easing_is_independent() -> None:
    # First leg is linear (collinear within its span); second leg eases.
    pts = Curve(t=0, x=0).to(t=480, x=8).to(t=960, x=0, ease_x="in_out_sine").points()
    leg1 = [wp for wp in pts if wp.t <= 480]
    first, last = leg1[0], leg1[-1]
    slope = (last.x - first.x) / (last.t - first.t)
    for wp in leg1:
        assert abs(wp.x - (first.x + slope * (wp.t - first.t))) <= 1.0


def test_to_inherits_previous_height() -> None:
    path = Curve(t=0, x=0, h=40).to(t=480, x=6).to(t=960, x=12)
    assert all(wp.h == 40 for wp in path.points())


def test_to_varies_height_when_given() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=6, h=80, ease_h="in_out_sine")
    assert path.waypoints[0].h == 20
    assert path.waypoints[-1].h == 80


def test_at_applies_leg_easing() -> None:
    path = Curve(t=0, x=0, h=0).to(t=960, x=12, h=120, ease_x="in_out_sine")
    sampled = path.at(480)
    assert sampled.t == 480
    assert abs(sampled.x - _ideal_x(0, 960, 0, 12, "in_out_sine", 480)) <= 1.0
    # Clamped outside the span to the endpoints.
    assert (path.at(-100).t, path.at(-100).x) == (0, 0)
    assert (path.at(9999).t, path.at(9999).x) == (960, 12)


def test_to_slide_joint_kinds_and_width() -> None:
    slide = Curve(t=0, x=0).to(t=960, x=12, ease_x="in_out_sine").to_slide(w=3)
    assert isinstance(slide, Slide)
    assert slide.w == 3
    assert all(j.w == 3 for j in slide.joints)
    assert all(j.kind is JointKind.CONTROL for j in slide.joints[:-1])
    assert slide.joints[-1].kind is JointKind.STEP
    slide.validate()


def test_to_slide_preserves_height_in_raw_fields() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=6, h=90, ease_h="in_out_sine")
    slide = path.to_slide(w=2)

    assert slide._info.h == 20
    assert slide.joints[-1]._info.h == 90
    raw = slide.to_raw()
    assert raw.h == 20
    assert raw.children[-1].h == 90

    round_trip = Curve.from_note(slide)
    assert round_trip.waypoints[0].h == 20
    assert round_trip.waypoints[-1].h == 90


def test_to_air_slide_carries_height() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=6, h=90, ease_h="in_out_sine")
    air = path.to_air_slide(w=2)
    assert isinstance(air, AirSlide)
    assert air.h == 20
    assert all(j.w == 2 for j in air.joints)
    assert air.joints[-1].kind is JointKind.STEP
    assert air.joints[-1].h == 90  # type: ignore[attr-defined]
    air.validate()


def test_to_air_crush_all_control_with_gap_and_color() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=8, h=80)
    crush = path.to_air_crush(w=2, gap=(1, 16), color="red")
    assert isinstance(crush, AirCrush)
    assert all(j.kind is JointKind.CONTROL for j in crush.joints)
    assert crush.gap == div_to_tick(1, 16)
    assert crush.interval == Division(1, 16)
    assert crush.color == ColorValue.RED
    assert all(j.w == 2 for j in crush.joints)
    crush.validate()


def test_curve_accepts_position_like() -> None:
    path = Curve(t=(0, 0, 0), x=0).to(t=(0, 2, 0), x=4)
    assert path.waypoints[0].t == 0
    assert path.waypoints[-1].t == 960  # two beats at 4/4 default


def test_anchor_to_rejects_non_increasing_tick() -> None:
    with pytest.raises(ValueError):
        Curve(t=480, x=0).to(t=480, x=4)
    with pytest.raises(ValueError):
        Curve(t=480, x=0).to(t=0, x=4)


def test_extend_rejects_non_increasing_tick() -> None:
    path = Curve(t=0, x=0).to(t=480, x=4)
    with pytest.raises(ValueError):
        path.to(t=480, x=8)


def test_then_dedups_seam() -> None:
    a = Curve(t=0, x=0).to(t=480, x=4)
    b = Curve(t=480, x=4).to(t=960, x=0)
    joined = a.then(b)
    assert joined.waypoints[0].t == 0
    assert joined.waypoints[-1].t == 960
    seam = [wp for wp in joined if wp.t == 480]
    assert len(seam) == 1
    assert (a + b).waypoints == joined.waypoints


def test_then_rejects_overlap() -> None:
    a = Curve(t=0, x=0).to(t=480, x=4)
    b = Curve(t=240, x=4).to(t=720, x=0)
    with pytest.raises(ValueError):
        a.then(b)


def test_from_note_loads_slide_path() -> None:
    slide = Curve(t=0, x=0).to(t=480, x=6).to(t=960, x=12).to_slide(w=2)
    curve = Curve.from_note(slide)
    # Control waypoints mirror the note's begin + joints.
    assert (curve.waypoints[0].t, curve.waypoints[0].x) == (0, 0)
    assert (curve.waypoints[-1].t, curve.waypoints[-1].x) == (960, 12)
    # Re-materializing reproduces the same joint geometry (linear legs round-trip).
    again = curve.to_slide(w=2)
    assert [(int(j.t), j.x) for j in again.joints] == [(int(j.t), j.x) for j in slide.joints]


def test_from_note_waypoint_easing_can_be_edited() -> None:
    slide = Curve(t=0, x=0).to(t=960, x=12).to_slide(w=2)
    curve = Curve.from_note(slide)

    curve.waypoints[-1].ease_x = "in_quad"

    assert curve.waypoints[-1].ease_x is EASINGS["in_quad"]
    assert curve.at(480).x == 3
    assert len(curve.points()) > 2


def test_from_note_air_crush_carries_height() -> None:
    crush = Curve(t=0, x=0, h=20).to(t=960, x=8, h=80).to_air_crush(w=2)
    curve = Curve.from_note(crush)
    assert curve.waypoints[0].h == 20
    assert any(wp.h == 80 for wp in curve.waypoints)


def test_envelope_full_cycle_starts_and_ends_on_inner() -> None:
    inner = Curve(t=0, x=2).to(t=960, x=2)
    outer = Curve(t=0, x=10).to(t=960, x=10)
    weave = envelope(inner, outer, count=8)  # even count -> lands back on inner
    ticks = [wp.t for wp in weave]
    assert ticks == sorted(set(ticks))  # monotonic integer ticks
    assert weave.waypoints[0].x == 2  # starts on inner
    assert weave.waypoints[-1].x == 2  # ends on inner
    assert any(wp.x == 10 for wp in weave)  # reaches the outer boundary


def test_envelope_odd_count_stops_on_outer() -> None:
    inner = Curve(t=0, x=2).to(t=960, x=2)
    outer = Curve(t=0, x=10).to(t=960, x=10)
    weave = envelope(inner, outer, count=3)  # odd count -> stops out on outer
    assert weave.waypoints[0].x == 2
    assert weave.waypoints[-1].x == 10


def test_envelope_default_is_one_full_cycle() -> None:
    inner = Curve(t=0, x=2).to(t=960, x=2)
    outer = Curve(t=0, x=10).to(t=960, x=10)
    weave = envelope(inner, outer)  # default count=2
    assert [wp.x for wp in weave.waypoints] == [2, 10, 2]


def test_envelope_rejects_mismatched_span() -> None:
    inner = Curve(t=0, x=2).to(t=960, x=2)
    outer = Curve(t=0, x=10).to(t=480, x=10)
    with pytest.raises(ValueError):
        envelope(inner, outer)


def test_envelope_rejects_bad_count() -> None:
    inner = Curve(t=0, x=2).to(t=960, x=2)
    outer = Curve(t=0, x=10).to(t=960, x=10)
    with pytest.raises(ValueError):
        envelope(inner, outer, count=0)


def test_crease_anchors_both_ends() -> None:
    base = Curve(t=0, x=6).to(t=960, x=6)
    woven = crease(base, count=4, x_range=3)
    ticks = [wp.t for wp in woven]
    assert ticks == sorted(set(ticks))  # strictly increasing integer ticks
    assert woven.waypoints[0].x == 6  # first turning point on the base
    assert woven.waypoints[-1].x == 6  # last turning point on the base
    interior = [wp.x for wp in woven.waypoints[1:-1]]
    assert 9 in interior  # reaches +x_range
    assert 3 in interior  # reaches -x_range


def test_crease_height_in_phase() -> None:
    base = Curve(t=0, x=6, h=80).to(t=960, x=6, h=80)
    woven = crease(base, count=4, x_range=3, h_range=20)
    for wp in woven.waypoints[1:-1]:
        # height offset shares the lane offset's sign
        assert (wp.x - 6 > 0) == (wp.h - 80 > 0)
    assert woven.waypoints[0].h == 80  # endpoints keep the base height
    assert woven.waypoints[-1].h == 80


def test_crease_default_h_range_leaves_height() -> None:
    base = Curve(t=0, x=6, h=80).to(t=960, x=6, h=80)
    woven = crease(base, count=4, x_range=3)
    assert all(wp.h == 80 for wp in woven.waypoints)


def test_crease_rejects_bad_count() -> None:
    base = Curve(t=0, x=6).to(t=960, x=6)
    with pytest.raises(ValueError):
        crease(base, count=1, x_range=3)


def test_crease_materializes() -> None:
    base = Curve(t=0, x=6).to(t=960, x=6)
    crease(base, count=4, x_range=3).to_slide(w=2).validate()


def test_materialized_notes_survive_raw_round_trip() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=10, h=80, ease_x="in_out_sine")
    # Slide and AirCrush have a self-contained root that wrap_raw_note accepts directly.
    for note in (path.to_slide(w=2), path.to_air_crush(w=2)):
        restored = RawNote.from_proto(note.to_raw().to_proto())
        wrap_raw_note(restored).validate()
    # AirSlide serializes as an AIR-rooted tree (meant to attach to a ground note); just
    # confirm it validates and serializes without error.
    air = path.to_air_slide(w=2)
    air.validate()
    RawNote.from_proto(air.to_raw().to_proto())


def test_rain_drops_step_and_stay_in_bounds() -> None:
    drops = rain(t0=0, t1=960, step=240, x_range=(2, 8), h_range=(40, 120), w=2, seed=0)
    assert [d.t for d in drops] == [0, 240, 480, 720]  # one drop per step within [t0, t1)
    for drop in drops:
        assert 2 <= drop.x <= 8
        assert 40 <= drop.h <= 120
        assert len(drop.joints) == 1  # a flat begin -> single step trace
        step = drop.joints[-1]
        assert step.x == drop.x
        assert step.h == drop.h  # type: ignore[attr-defined]  # the drop is level
        drop.validate()


def test_rain_default_length_fills_step_and_truncates_at_end() -> None:
    drops = rain(t0=0, t1=500, step=200, x_range=(0, 4), seed=1)
    assert [d.t for d in drops] == [0, 200, 400]
    assert drops[0].joints[-1].t == 200  # default length == step
    assert drops[-1].joints[-1].t == 500  # final drop truncated at t1, never past it


def test_rain_constant_default_height() -> None:
    drops = rain(t0=0, t1=480, step=240, x_range=(0, 4), seed=2)
    assert all(d.h == DEFAULT_H for d in drops)


def test_rain_is_seed_reproducible() -> None:
    a = rain(t0=0, t1=1920, step=120, x_range=(0, 10), h_range=(0, 200), seed=7)
    b = rain(t0=0, t1=1920, step=120, x_range=(0, 10), h_range=(0, 200), seed=7)
    assert [(d.t, d.x, d.h) for d in a] == [(d.t, d.x, d.h) for d in b]


def test_rain_rejects_bad_range_and_step() -> None:
    with pytest.raises(ValueError):
        rain(t0=960, t1=0, step=240, x_range=(0, 4))
    with pytest.raises(ValueError):
        rain(t0=0, t1=960, step=0, x_range=(0, 4))
