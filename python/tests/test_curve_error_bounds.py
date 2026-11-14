import math
import random

import pytest
from margrete_rpc.chart.util import Curve, Waypoint
from margrete_rpc.chart.util.curve import _ErrorSums


@pytest.mark.parametrize("origin", [0, 20, 2**31, -(2**31), 2**45])
@pytest.mark.parametrize("span", [960, 100_000_000])
def test_error_bound_never_exceeds_direct_scan(origin: int, span: int) -> None:
    rng = random.Random(20261114)
    start = 2**40 + 3
    ticks = [start, *(start + t for t in sorted(rng.sample(range(1, span), 200))), start + span]
    reals = [
        (
            origin + 12 * (t - start) / span,
            origin - 100 * math.sin(math.pi / 2 * (t - start) / span),
        )
        for t in ticks
    ]
    sums = _ErrorSums(ticks, reals)
    ranges = [(0, len(ticks) - 1), (0, 1), (len(ticks) - 2, len(ticks) - 1)]
    ranges.extend(tuple(sorted(rng.sample(range(len(ticks)), 2))) for _ in range(100))
    for lo, hi in ranges:
        a, b = (Waypoint(ticks[j], round(reals[j][0]), round(reals[j][1])) for j in (lo, hi))
        lower = sums.lower_bounds(a, b, lo, hi)
        for axis, va, vb in ((0, a.x, b.x), (1, a.h, b.h)):
            slope = (vb - va) / (b.t - a.t)
            exact = sum(
                (va + (ticks[j] - a.t) * slope - reals[j][axis]) ** 2 * (ticks[j + 1] - ticks[j])
                for j in range(lo, hi)
            )
            assert lower[axis] <= exact


def test_zero_error_axis_has_exact_zero_bound() -> None:
    ticks = [3, 5, 10, 15, 19]
    reals = [(4.0, 20.0)] * len(ticks)
    bounds = _ErrorSums(ticks, reals).lower_bounds(Waypoint(3, 4, 20), Waypoint(19, 4, 20), 0, 4)
    assert bounds == (0.0, 0.0)


def test_error_bound_handles_nearly_perfect_chord() -> None:
    ticks = list(range(1001))
    reals = [(12 * t / 1000, 120 - 100 * t / 1000) for t in ticks]
    reals[500] = (reals[500][0] + 1e-10, reals[500][1] - 1e-10)
    lower = _ErrorSums(ticks, reals).lower_bounds(
        Waypoint(0, 0, 120), Waypoint(1000, 12, 20), 0, 1000
    )
    assert all(bound <= 1e-20 for bound in lower)


@pytest.mark.parametrize(
    "x,h,ex,eh,expected",
    [
        (
            0,
            120,
            "linear",
            "in_out_sine",
            [
                (0, 0, 20),
                (35, 0, 20),
                (130, 0, 24),
                (220, 0, 32),
                (335, 0, 47),
                (630, 0, 94),
                (750, 0, 109),
                (850, 0, 117),
                (925, 0, 120),
                (960, 0, 120),
            ],
        ),
        (
            12,
            120,
            "in_out_sine",
            "in_quad",
            [
                (0, 0, 20),
                (50, 0, 20),
                (175, 1, 23),
                (190, 1, 24),
                (255, 2, 27),
                (320, 3, 31),
                (375, 4, 35),
                (430, 5, 40),
                (480, 6, 45),
                (535, 7, 51),
                (585, 8, 57),
                (645, 9, 65),
                (705, 10, 74),
                (775, 11, 85),
                (875, 12, 103),
                (960, 12, 120),
            ],
        ),
        (
            12,
            20,
            "out_cubic",
            "linear",
            [
                (0, 0, 20),
                (120, 4, 20),
                (155, 5, 20),
                (245, 7, 20),
                (295, 8, 20),
                (355, 9, 20),
                (430, 10, 20),
                (530, 11, 20),
                (755, 12, 20),
                (960, 12, 20),
            ],
        ),
    ],
)
def test_refinement_preserves_output_before_performance_optimization(
    x: int, h: int, ex: str, eh: str, expected: list[tuple[int, int, int]]
) -> None:
    path = Curve(t=0, x=0, h=20).to(t=960, x=x, h=h, ease_x=ex, ease_h=eh)
    assert [(p.t, p.x, p.h) for p in path.points()] == expected
