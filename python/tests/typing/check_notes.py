"""Static regression checks run by Pyright through pyproject.toml."""

# pyright: reportUnnecessaryTypeIgnoreComment=error

from margrete_rpc.chart.notes import (
    Air,
    AirCrush,
    AirHold,
    AirSlide,
    Damage,
    Extap,
    Flick,
    Hold,
    Slide,
    Tap,
)
from margrete_rpc.chart.notes.transform import merge, split
from typing_extensions import assert_type


class CustomTap(Tap):
    pass


def check_note_types(
    tap: Tap,
    damage: Damage,
    extap: Extap,
    flick: Flick,
    air: Air,
    slide: Slide,
    hold: Hold,
    air_slide: AirSlide,
    air_hold: AirHold,
    crush: AirCrush,
    custom: CustomTap,
) -> None:
    assert_type(tap.converted(Flick), Flick)
    assert_type(damage.converted(Tap), Tap)
    assert_type(extap.converted(Air), Air)
    assert_type(flick.converted(Damage), Damage)
    assert_type(air.converted(Extap), Extap)
    assert_type(slide.converted(AirSlide), AirSlide)
    assert_type(hold.converted(AirHold), AirHold)
    assert_type(air_slide.converted(Slide), Slide)
    assert_type(air_hold.converted(AirCrush), AirCrush)
    assert_type(crush.converted(AirSlide), AirSlide)

    assert_type(tap.shifted(t=1).clone(), Tap)
    assert_type(custom.shifted(t=1).clone(), CustomTap)
    assert_type(slide.add_step(t=480, x=0, w=1), Slide)
    assert_type(air_slide.with_step(t=480, x=0, w=1, h=80), AirSlide)
    assert_type(hold.with_step(t=480, x=0, w=1), Hold)
    assert_type(merge([slide, slide]), Slide)
    assert_type(merge([air_slide, air_slide]), AirSlide)
    assert_type(split(crush, 240), tuple[AirCrush, AirCrush])

    # Invalid conversions must keep producing type errors.
    tap.converted(Slide)  # pyright: ignore[reportArgumentType]
    slide.converted(Tap)  # pyright: ignore[reportArgumentType]
    tap.converted(Tap)  # pyright: ignore[reportArgumentType]
