"""Static checks for curve sampling options."""

# pyright: reportUnnecessaryTypeIgnoreComment=error

from margrete_rpc.chart.notes import AirCrush, AirSlide, Slide
from margrete_rpc.chart.time import DivisionLike
from margrete_rpc.chart.util import Curve, CurveMode, Waypoint
from typing_extensions import assert_type


def check_curve_sampling(
    path: Curve, mode: CurveMode = "stair", interval: int | DivisionLike | None = (1, 16)
) -> None:
    assert_type(path.points(mode=mode, interval=interval), tuple[Waypoint, ...])
    assert_type(path.to_slide(w=4, mode=mode, interval=interval), Slide)
    assert_type(path.to_air_slide(w=4, mode=mode, interval=interval), AirSlide)
    assert_type(path.to_air_crush(w=4, mode=mode, interval=interval), AirCrush)
    path.points(mode="stairs")  # pyright: ignore[reportArgumentType]
    path.to_slide(w=4, mode="stairs")  # pyright: ignore[reportArgumentType]
    path.to_air_slide(w=4, mode="stairs")  # pyright: ignore[reportArgumentType]
    path.to_air_crush(w=4, mode="stairs")  # pyright: ignore[reportArgumentType]
    path.points(interval="1/16")  # pyright: ignore[reportArgumentType]
    path.to_slide(w=4, interval="1/16")  # pyright: ignore[reportArgumentType]
    path.to_air_slide(w=4, interval="1/16")  # pyright: ignore[reportArgumentType]
    path.to_air_crush(w=4, interval="1/16")  # pyright: ignore[reportArgumentType]


def check_fixed_stair_ramp(path: Curve) -> None:
    assert_type(path.points(grid=None, mode="stair", interval=120, ramp=10), tuple[Waypoint, ...])
    assert_type(path.to_slide(w=4, mode="stair", interval=(1, 16), ramp=10), Slide)
    assert_type(path.to_air_slide(w=4, mode="stair", interval=(1, 16), ramp=10), AirSlide)
    assert_type(path.to_air_crush(w=4, mode="stair", interval=(1, 16), ramp=10), AirCrush)
    path.points(mode="stair", interval=120, ramp="5")  # pyright: ignore[reportArgumentType]
