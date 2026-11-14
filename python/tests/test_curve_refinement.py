import math

import pytest
from margrete_rpc.chart.util import Curve, Waypoint


def _quality(path: Curve, points: tuple[Waypoint, ...], axis: str) -> tuple[float, float, float]:
    first, last = path.waypoints
    ease = last.ease_x if axis == "x" else last.ease_h
    start, delta = getattr(first, axis), getattr(last, axis) - getattr(first, axis)
    squared = peak = 0.0
    slopes = []
    for a, b in zip(points, points[1:]):
        slope = (getattr(b, axis) - getattr(a, axis)) / (b.t - a.t)
        slopes.append(slope)
        for t in range(a.t, b.t):
            actual = getattr(a, axis) + slope * (t - a.t)
            ideal = start + delta * ease.solve((t - first.t) / (last.t - first.t))
            error = abs(actual - ideal)
            squared += error**2
            peak = max(peak, error)
    variation = sum(abs(b - a) for a, b in zip(slopes, slopes[1:]))
    return (squared / (last.t - first.t)) ** 0.5, peak, variation


@pytest.mark.parametrize("reverse", [False, True])
def test_height_refinement_improves_existing_fit_without_more_nodes(reverse: bool) -> None:
    baseline = [
        (0, 20),
        (25, 20),
        (95, 22),
        (210, 31),
        (350, 49),
        (645, 96),
        (780, 112),
        (890, 119),
        (945, 120),
        (960, 120),
    ]
    if reverse:
        baseline = [(t, 140 - h) for t, h in baseline]
    path = Curve(t=0, x=4, h=baseline[0][1]).to(t=960, x=4, h=baseline[-1][1], ease_h="in_out_sine")
    before = tuple(Waypoint(t, 4, h) for t, h in baseline)
    after = path.points()
    old, new = _quality(path, before, "h"), _quality(path, after, "h")
    assert len(after) <= len(before)
    assert new[0] < old[0] * 0.8
    assert new[1] <= old[1] + 1e-9
    assert new[2] <= old[2] + 1e-9


def test_joint_refinement_improves_both_axes() -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=12, h=120, ease_x="in_out_sine", ease_h="in_quad")
    baseline = [
        (0, 0, 20),
        (40, 0, 20),
        (150, 1, 22),
        (180, 1, 24),
        (260, 2, 27),
        (325, 3, 31),
        (380, 4, 36),
        (430, 5, 40),
        (485, 6, 46),
        (535, 7, 51),
        (585, 8, 57),
        (645, 9, 65),
        (705, 10, 74),
        (785, 11, 87),
        (900, 12, 108),
        (960, 12, 120),
    ]
    before = tuple(Waypoint(*p) for p in baseline)
    after = path.points()
    assert len(after) <= len(before)
    for axis in ("x", "h"):
        old, new = _quality(path, before, axis), _quality(path, after, axis)
        assert new[0] < old[0] * 0.8
        assert new[1] <= old[1] + 1e-9
        assert new[2] <= old[2] + 1e-9


def test_refinement_keeps_height_pause_boundaries() -> None:
    def pause(t: float) -> float:
        if t < 0.25:
            return 2 * t
        if t <= 0.75:
            return 0.5
        return 2 * t - 1

    path = Curve(t=0, x=0, h=20).to(t=960, x=12, h=120, ease_h=pause)
    points = path.points()
    assert any(p.t == 240 and p.h == 70 for p in points)
    assert any(p.t == 720 and p.h == 70 for p in points)
    assert all(p.h == 70 for p in points if 240 <= p.t <= 720)


def test_refinement_checks_error_between_grid_ticks() -> None:
    # The added ripple vanishes on the 5-tick grid but peaks between its samples.
    def ripple(t: float) -> float:
        return t * t + 0.01 * math.sin(math.pi * 960 * t / 5) ** 2

    path = Curve(t=0, x=4, h=20).to(t=960, x=4, h=120, ease_h=ripple)
    baseline = [
        (0, 20),
        (35, 20),
        (150, 22),
        (325, 31),
        (490, 46),
        (640, 64),
        (810, 91),
        (955, 119),
        (960, 120),
    ]
    before = tuple(Waypoint(t, 4, h) for t, h in baseline)
    after = path.points()
    old, new = _quality(path, before, "h"), _quality(path, after, "h")
    assert old[1] > 1  # A grid-only half-unit bound would miss this peak.
    assert len(after) <= len(before)
    assert new[0] < old[0]
    assert new[1] <= old[1] + 1e-9
    assert new[2] <= old[2] + 1e-9


def test_refinement_keeps_off_grid_anchors_and_height_turn() -> None:
    def peak(t: float) -> float:
        return 6 * t if t <= 0.25 else 1.5 - (t - 0.25) * 2 / 3

    path = (
        Curve(t=3, x=0, h=20)
        .to(t=963, x=12, h=120, ease_h=peak)
        .to(t=1447, x=6, h=80, ease_x="out_cubic", ease_h="in_quad")
    )
    points = path.points(grid=3)
    by_tick = {p.t: (p.x, p.h) for p in points}
    assert by_tick[3] == (0, 20)
    assert by_tick[243] == (3, 170)
    assert by_tick[963] == (12, 120)
    assert by_tick[1447] == (6, 80)
    assert all(p.t % 3 == 0 for p in points[1:-1])


def test_coarse_grid_refinement_does_not_scan_every_tick_of_long_leg() -> None:
    calls = 0

    def ease(t: float) -> float:
        nonlocal calls
        calls += 1
        return (1 - math.cos(math.pi * t)) / 2

    points = Curve(t=0, x=4, h=20).to(t=100_000_000, x=4, h=120, ease_h=ease).points(grid=1_000_000)
    assert len(points) > 2
    assert all(p.t % 1_000_000 == 0 for p in points)
    assert calls < 10_000
