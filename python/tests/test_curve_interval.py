import pytest
from margrete_rpc.chart.notes import AirSlide, RawNote
from margrete_rpc.chart.time import Division, DivisionLike
from margrete_rpc.chart.util import Curve, CurveMode


@pytest.mark.parametrize("interval", [120, (1, 16), Division(1, 16)])
def test_fixed_linear_samples_keep_requested_spacing(interval: int | DivisionLike) -> None:
    path = Curve(t=0, x=2, h=20).to(t=240, x=8, h=80)
    pts = path.points(interval=interval)
    assert [(wp.t, wp.x, wp.h) for wp in pts] == [(0, 2, 20), (120, 5, 50), (240, 8, 80)]


@pytest.mark.parametrize("ramp", [1, 5, 30])
def test_fixed_stair_holds_until_ramp_before_next_sample(ramp: int) -> None:
    path = Curve(t=0, x=2, h=20).to(t=240, x=8, h=80)
    pts = path.points(interval=(1, 16), mode="stair", ramp=ramp)
    assert [(wp.t, wp.x, wp.h) for wp in pts] == [
        (0, 2, 20),
        (120 - ramp, 2, 20),
        (120, 5, 50),
        (240 - ramp, 5, 50),
        (240, 8, 80),
    ]


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_samples_evaluate_original_easing_on_both_axes(mode: CurveMode) -> None:
    path = Curve(t=0, x=0, h=20).to(t=480, x=12, h=116, ease_x="in_quad", ease_h="out_quad")
    pts = path.points(interval=120, mode=mode)
    assert [(wp.t, wp.x, wp.h) for wp in pts if wp.t % 120 == 0] == [
        (0, 0, 20),
        (120, 1, 62),
        (240, 3, 92),
        (360, 7, 110),
        (480, 12, 116),
    ]


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_sampling_phase_spans_legs_and_preserves_off_grid_anchors(mode: CurveMode) -> None:
    path = (
        Curve(t=3, x=0, h=20)
        .to(t=143, x=8, h=60, ease_x="in_quad")
        .to(t=303, x=2, h=80, ease_x="out_sine")
    )
    pts = path.points(interval=120, mode=mode)
    samples = [3, 123, 143, 243, 303]
    ticks = [wp.t for wp in pts]
    assert ticks == (samples if mode == "smooth" else [3, 118, 123, 138, 143, 238, 243, 298, 303])
    assert [(wp.t, wp.x, wp.h) for wp in pts if wp.t in samples] == [
        (tick, path.at(tick).x, path.at(tick).h) for tick in samples
    ]


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_sampling_deduplicates_anchors_on_sample_ticks(mode: CurveMode) -> None:
    path = Curve(t=3, x=0).to(t=123, x=12).to(t=243, x=4)
    pts = path.points(interval=120, mode=mode)
    ticks = [wp.t for wp in pts]
    assert ticks == sorted(set(ticks))
    assert ticks.count(123) == 1
    assert next(wp.x for wp in pts if wp.t == 123) == 12


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_sampling_keeps_partial_final_interval(mode: CurveMode) -> None:
    pts = Curve(t=0, x=0).to(t=250, x=15).points(interval=120, mode=mode)
    expected = [0, 120, 240, 250] if mode == "smooth" else [0, 115, 120, 235, 240, 245, 250]
    assert [wp.t for wp in pts] == expected
    assert pts[-1].x == 15


@pytest.mark.parametrize("interval", [2, 100])
def test_fixed_stair_short_segments_clip_ramps(interval: int) -> None:
    path = Curve(t=3, x=0).to(t=4, x=8).to(t=9, x=12)
    pts = path.points(interval=interval, mode="stair", ramp=10)
    assert [wp.t for wp in pts] == ([3, 4, 5, 7, 9] if interval == 2 else [3, 4, 9])
    path.to_slide(w=2, interval=interval, mode="stair", ramp=10).validate()


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_samples_with_equal_values_stay_flat(mode: CurveMode) -> None:
    pts = Curve(t=0, x=4, h=80).to(t=500, x=4).points(interval=120, mode=mode)
    assert [wp.t for wp in pts] == [0, 120, 240, 360, 480, 500]
    assert all((wp.x, wp.h) == (4, 80) for wp in pts)


def test_fixed_stair_height_only_has_ramps() -> None:
    pts = Curve(t=0, x=4, h=0).to(t=240, x=4, h=6).points(interval=120, mode="stair")
    assert [(wp.t, wp.h) for wp in pts] == [(0, 0), (115, 0), (120, 3), (235, 3), (240, 6)]
    assert all(wp.x == 4 for wp in pts)


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_fixed_sampling_supports_custom_overshoot(mode: CurveMode) -> None:
    c = 1.70158
    out_back = lambda t: 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2  # noqa: E731
    pts = Curve(t=0, x=0).to(t=960, x=10, ease_x=out_back).points(interval=240, mode=mode)
    assert max(wp.x for wp in pts) > 10
    assert (pts[-1].t, pts[-1].x) == (960, 10)


@pytest.mark.parametrize("mode", ["smooth", "stair"])
@pytest.mark.parametrize("method", ["to_slide", "to_air_slide", "to_air_crush"])
def test_fixed_materializers_match_preview_after_serialization(
    mode: CurveMode, method: str
) -> None:
    path = Curve(t=0, x=12, h=80).to(t=960, x=0, h=20, ease_x="in_out_cubic")
    ramp = 17 if mode == "stair" else None
    note = getattr(path, method)(w=3, interval=(1, 16), mode=mode, ramp=ramp)
    note.validate()
    raw = RawNote.from_proto(note.to_raw().to_proto())
    if isinstance(note, AirSlide):
        raw = raw.children[0]
    assert [(point.t, point.x, point.h) for point in [raw, *raw.children]] == [
        (wp.t, wp.x, wp.h) for wp in path.points(interval=120, mode=mode, ramp=ramp)
    ]


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_none_interval_uses_auto_sampling(mode: CurveMode) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12, ease_x="in_out_cubic")
    assert path.points(mode=mode, interval=None) == path.points(mode=mode)


@pytest.mark.parametrize("interval", [0, -1, (0, 16), (-1, 16), (1, 0), (1, -16), (1, 2, 3)])
@pytest.mark.parametrize("method", ["points", "to_slide", "to_air_slide", "to_air_crush"])
def test_invalid_interval_values_rejected(interval: object, method: str) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12)
    kwargs = {} if method == "points" else {"w": 3}
    with pytest.raises(ValueError):
        getattr(path, method)(interval=interval, **kwargs)


@pytest.mark.parametrize("interval", [True, 1.5, "1/16"])
def test_invalid_interval_types_rejected(interval: object) -> None:
    with pytest.raises(TypeError, match="interval"):
        Curve(t=0, x=0).to(t=960, x=12).points(interval=interval)  # type: ignore[arg-type]


@pytest.mark.parametrize("grid,error", [(0, ValueError), (-1, ValueError), (1.5, TypeError)])
def test_auto_sampling_validates_grid(grid: int, error: type[Exception]) -> None:
    with pytest.raises(error, match="grid"):
        Curve(t=0, x=0).to(t=960, x=12).points(grid=grid)


@pytest.mark.parametrize("interval", [120, (1, 16)])
@pytest.mark.parametrize("mode", ["smooth", "stair"])
@pytest.mark.parametrize("method", ["points", "to_slide", "to_air_slide", "to_air_crush"])
def test_grid_and_interval_are_mutually_exclusive(
    interval: int | DivisionLike, mode: CurveMode, method: str
) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12)
    kwargs = {} if method == "points" else {"w": 3}
    with pytest.raises(ValueError, match="grid and interval are mutually exclusive"):
        getattr(path, method)(grid=5, interval=interval, mode=mode, **kwargs)


@pytest.mark.parametrize("mode", ["smooth", "stair"])
def test_omitted_or_none_grid_uses_context_default(mode: CurveMode) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12, ease_x="in_out_cubic")
    assert (
        path.points(mode=mode)
        == path.points(mode=mode, grid=None)
        == path.points(mode=mode, grid=5)
    )
    assert path.points(mode=mode, interval=120) == path.points(mode=mode, interval=120, grid=None)


@pytest.mark.parametrize(
    "ramp,error", [(0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)]
)
@pytest.mark.parametrize("method", ["points", "to_slide", "to_air_slide", "to_air_crush"])
def test_invalid_ramp_rejected(ramp: int, error: type[Exception], method: str) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12)
    kwargs = {} if method == "points" else {"w": 3}
    with pytest.raises(error, match="ramp"):
        getattr(path, method)(mode="stair", interval=120, ramp=ramp, **kwargs)


@pytest.mark.parametrize("mode,interval", [("smooth", None), ("smooth", 120), ("stair", None)])
def test_ramp_requires_fixed_interval_stairs(mode: CurveMode, interval: int | None) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12)
    with pytest.raises(ValueError, match="ramp requires"):
        path.points(mode=mode, interval=interval, ramp=5)
