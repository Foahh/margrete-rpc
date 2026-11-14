import math

import pytest
from margrete_rpc.chart.notes import AirSlide, RawNote
from margrete_rpc.chart.util import EASINGS, Curve, Waypoint


def _reconstruct(points: tuple[Waypoint, ...], tick: int, axis: str) -> float:
    for a, b in zip(points, points[1:]):
        if a.t <= tick <= b.t:
            return getattr(a, axis) + (getattr(b, axis) - getattr(a, axis)) * (tick - a.t) / (
                b.t - a.t
            )
    raise AssertionError(f"tick outside path: {tick}")


@pytest.mark.parametrize("ease", sorted(EASINGS))
@pytest.mark.parametrize("grid", [1, 5, 20])
@pytest.mark.parametrize("dx,dh", [(0, 100), (2, 100), (12, 4)])
@pytest.mark.parametrize("direction", [-1, 1])
def test_both_axes_fit_within_half_unit_at_grid_samples(
    ease: str, grid: int, dx: int, dh: int, direction: int
) -> None:
    x0, h0 = (0, 20) if direction == 1 else (12, 120)
    path = Curve(t=3, x=x0, h=h0).to(
        t=963, x=x0 + direction * dx, h=h0 + direction * dh, ease_x="in_quad", ease_h=ease
    )
    points = path.points(grid=grid)
    assert [p.t for p in points] == sorted({p.t for p in points})
    assert all(p.t % grid == 0 for p in points[1:-1])
    assert all((b.x - a.x) * direction >= 0 for a, b in zip(points, points[1:]))
    assert all((b.h - a.h) * direction >= 0 for a, b in zip(points, points[1:]))
    for tick in range((3 // grid + 1) * grid, 963, grid):
        f = (tick - 3) / 960
        ideal_x = x0 + direction * dx * f**2
        ideal_h = h0 + direction * dh * EASINGS[ease].solve(f)
        assert abs(_reconstruct(points, tick, "x") - ideal_x) <= 0.5 + 1e-9
        assert abs(_reconstruct(points, tick, "h") - ideal_h) <= 0.5 + 1e-9


@pytest.mark.parametrize("grid", [1, 5, 20])
@pytest.mark.parametrize("h0,h1", [(20, 120), (120, 20)])
def test_dense_height_curve_has_no_quantization_slope_spikes(grid: int, h0: int, h1: int) -> None:
    path = Curve(t=0, x=4, h=h0).to(t=960, x=4, h=h1, ease_h="in_out_sine")
    points = path.points(grid=grid)
    slopes = [(b.h - a.h) / (b.t - a.t) for a, b in zip(points, points[1:])]
    # The ideal sine's total slope variation is pi * height_delta / duration.
    variation = sum(abs(b - a) for a, b in zip(slopes, slopes[1:]))
    assert variation <= 1.3 * math.pi * abs(h1 - h0) / 960
    assert len(points) <= 15


@pytest.mark.parametrize("ease", ["sine", "quad", "cubic", "quart", "quint", "circ", "expo"])
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("end", ["in", "out"])
def test_endpoint_plateau_reduces_reconstruction_error(ease: str, direction: int, end: str) -> None:
    name = f"{end}_{ease}"
    path = Curve(t=3, x=0).to(t=963, x=12 * direction, ease_x=name)
    points = path.points()
    index = 1 if end == "in" else len(points) - 2
    anchor = points[0] if end == "in" else points[-1]
    assert points[index].x == anchor.x
    assert 3 < points[index].t < 963
    assert points[index].t % 5 == 0
    without = points[:index] + points[index + 1 :]

    def error(samples: tuple[Waypoint, ...]) -> float:
        return sum(
            (_reconstruct(samples, t, "x") - 12 * direction * EASINGS[name].solve((t - 3) / 960))
            ** 2
            for t in range(3, 964)
        )

    assert error(points) < error(without)


@pytest.mark.parametrize("method", ["to_air_slide", "to_air_crush"])
def test_air_materialization_serializes_fitted_height(method: str) -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=2, h=120, ease_h="out_cubic")
    note = getattr(path, method)(w=3)
    note.validate()
    raw = RawNote.from_proto(note.to_raw().to_proto())
    if isinstance(note, AirSlide):
        raw = raw.children[0]
    actual = [(p.t, p.x, p.h) for p in [raw, *raw.children]]
    assert actual == [(p.t, p.x, p.h) for p in path.points()]
    assert abs(_reconstruct(path.points(), 240, "h") - 77.8125) <= 0.5


def test_custom_height_overshoot_with_sparse_lane_motion() -> None:
    c = 1.70158
    path = Curve(t=0, x=0, h=20).to(
        t=960,
        x=2,
        h=120,
        ease_h=lambda t: 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2,
    )
    points = path.points()
    assert max(p.h for p in points) > 120
    assert (points[-1].t, points[-1].x, points[-1].h) == (960, 2, 120)
    for t in range(0, 961, 5):
        ideal = 20 + 100 * path.waypoints[-1].ease_h.solve(t / 960)
        assert abs(_reconstruct(points, t, "h") - ideal) <= 0.5 + 1e-9
