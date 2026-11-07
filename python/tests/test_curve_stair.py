import pytest
from margrete_rpc.chart.notes import AirSlide, RawNote
from margrete_rpc.chart.util import EASINGS, Curve


@pytest.mark.parametrize("ease", sorted(EASINGS))
@pytest.mark.parametrize("x0,x1", [(-1, 13), (13, -1)])
@pytest.mark.parametrize("grid", [1, 5])
def test_stair_supports_all_builtin_easings(ease: str, x0: int, x1: int, grid: int) -> None:
    pts = Curve(t=0, x=x0).to(t=960, x=x1, ease_x=ease).points(mode="stair", grid=grid)
    assert (pts[0].t, pts[0].x) == (0, x0)
    assert (pts[-1].t, pts[-1].x) == (960, x1)
    assert any(a.x == b.x for a, b in zip(pts, pts[1:]))
    assert any(a.x != b.x for a, b in zip(pts, pts[1:]))
    assert all((b.x - a.x) * (x1 - x0) >= 0 for a, b in zip(pts, pts[1:]))
    assert all(wp.t % grid == 0 for wp in pts)


def test_linear_stair_keeps_platforms_and_short_ramps() -> None:
    path = Curve(t=0, x=0).to(t=40, x=2)
    pts = path.points(mode="stair")
    assert [(wp.t, wp.x) for wp in pts] == [(0, 0), (10, 0), (15, 1), (25, 1), (30, 2), (40, 2)]
    assert path.points() == path.points(mode="smooth")
    assert len(path.points()) == 2


def test_stair_applies_to_height_only() -> None:
    pts = Curve(t=0, x=4, h=20).to(t=240, x=4, h=26).points(mode="stair")
    assert all(wp.x == 4 for wp in pts)
    assert {wp.h for wp in pts} == set(range(20, 27))
    assert any(a.h == b.h for a, b in zip(pts, pts[1:]))


@pytest.mark.parametrize("method", ["to_slide", "to_air_slide", "to_air_crush"])
@pytest.mark.parametrize("ease", ["linear", "in_out_cubic"])
def test_stair_materializers_match_preview_after_serialization(method: str, ease: str) -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=12, h=80, ease_x=ease, ease_h="out_quad")
    note = getattr(path, method)(w=3, grid=10, mode="stair")
    note.validate()
    raw = RawNote.from_proto(note.to_raw().to_proto())
    if isinstance(note, AirSlide):
        raw = raw.children[0]
    actual = [(point.t, point.x, point.h) for point in [raw, *raw.children]]
    expected = [(wp.t, wp.x, wp.h) for wp in path.points(grid=10, mode="stair")]
    assert actual == expected


def test_stair_keeps_off_grid_anchors_and_turns() -> None:
    path = Curve(t=3, x=0).to(t=87, x=12, ease_x="out_quad").to(t=137, x=4)
    pts = path.points(mode="stair")
    ticks = [wp.t for wp in pts]
    assert ticks == sorted(set(ticks))
    assert [(wp.t, wp.x) for wp in pts if wp.t in (3, 87, 137)] == [(3, 0), (87, 12), (137, 4)]
    assert all(wp.t % 5 == 0 for wp in pts if wp.t not in (3, 87, 137))


@pytest.mark.parametrize("grid", [1, 5, 20])
def test_stair_short_legs_remain_valid(grid: int) -> None:
    path = Curve(t=3, x=0).to(t=4, x=8).to(t=8, x=12)
    pts = path.points(mode="stair", grid=grid)
    assert [wp.t for wp in pts] == sorted({wp.t for wp in pts})
    assert (pts[0].t, pts[-1].t) == (3, 8)
    path.to_slide(w=2, mode="stair", grid=grid).validate()


def test_stair_custom_easing_keeps_overshoot_and_return() -> None:
    c = 1.70158
    out_back = lambda t: 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2  # noqa: E731
    pts = Curve(t=0, x=0).to(t=960, x=10, ease_x=out_back).points(mode="stair")
    assert max(wp.x for wp in pts) > 10
    assert (pts[-1].t, pts[-1].x) == (960, 10)
    assert any(a.x > b.x for a, b in zip(pts, pts[1:]))


def test_stair_constant_path_collapses() -> None:
    pts = Curve(t=0, x=4, h=80).to(t=960, x=4, h=80).points(mode="stair")
    assert [(wp.t, wp.x, wp.h) for wp in pts] == [(0, 4, 80), (960, 4, 80)]


@pytest.mark.parametrize("method", ["points", "to_slide", "to_air_slide", "to_air_crush"])
def test_rejects_unknown_curve_mode(method: str) -> None:
    path = Curve(t=0, x=0).to(t=960, x=12)
    kwargs = {} if method == "points" else {"w": 3}
    with pytest.raises(ValueError, match="mode"):
        getattr(path, method)(mode="stairs", **kwargs)


def test_stair_rejects_invalid_grid() -> None:
    with pytest.raises(ValueError, match="grid"):
        Curve(t=0, x=0).to(t=960, x=12).points(mode="stair", grid=0)
