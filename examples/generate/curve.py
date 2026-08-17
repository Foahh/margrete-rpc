"""Gallery of the Curve API: ground slides, air-slides, air-crushes, and custom easings.

Sections:
  1  Ground Slide per easing — 21 notes sweeping the x-axis (alternating direction).
  2  AirSlide per easing on the height axis — each attached to a Tap parent.
  3  AirCrush per easing — cycling through COLORS with progressively tighter segment gaps.
  4  Complex multi-joint shapes — S-curve, W-bounce, rising zigzag, diagonal with steps.
  5  Curve.then() / + concatenation — two or three legs joined at a seam, incl. AirCrush.
  6  Custom callable easings — bounce, overshoot, sine-squared, elastic, stepped.

Usage (run from examples/generate/):
  python curve.py             # push to Margrete (replaces chart)
  python curve.py --dry-run   # summarize only; no connection needed
"""

from __future__ import annotations

import math

from _common import (
    BEAT,
    COLORS,
    DOUBLE,
    EASING_NAMES,
    H_HIGH,
    H_LOW,
    LEFT,
    RIGHT,
    SEGMENT_GAP,
    WIDTH,
    _summarize,
    _sweep,
    _Track,
    make_arg_parser,
    push_gallery,
)
from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import Curve

HALF = BEAT // 2


def build_notes() -> list[ChartNote]:
    track = _Track()
    notes: list[ChartNote] = []

    # ----------------------------------------------------------- Section 1: Slide per easing (x-axis)
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        notes.append(Curve(t=t0, x=x0).to(t=t1, x=x1, ease_x=name).to_slide(w=WIDTH))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: AirSlide per easing (height axis)
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        path = Curve(t=t0, x=x0, h=H_LOW).to(
            t=t1, x=x1, h=H_HIGH, ease_x="in_out_sine", ease_h=name
        )
        air = path.to_air_slide(w=WIDTH)
        wp0 = path.waypoints[0]
        notes.append(Tap(t=wp0.t, x=wp0.x, w=WIDTH).add_air(air))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: AirCrush per easing (x + h, cycling colors and gap)
    gaps: list[tuple[int, int]] = [(1, 8), (1, 12), (1, 16), (1, 24), (1, 32)]
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        path = Curve(t=t0, x=x0, h=H_LOW).to(
            t=t1, x=x1, h=H_HIGH, ease_x=name, ease_h="in_out_sine"
        )
        notes.append(
            path.to_air_crush(w=WIDTH, gap=gaps[i % len(gaps)], color=COLORS[i % len(COLORS)])
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: complex multi-joint shapes
    # S-curve: smooth reversal with opposite-family easings on each half
    t0, t1 = track.slot(DOUBLE)
    mid = (t0 + t1) // 2
    notes.append(
        Curve(t=t0, x=LEFT)
        .to(t=mid, x=RIGHT, ease_x="out_cubic")
        .to(t=t1, x=LEFT, ease_x="in_cubic")
        .to_slide(w=WIDTH)
    )

    # W-bounce: four-leg quad oscillation
    t0, t1 = track.slot(DOUBLE)
    q = (t1 - t0) // 4
    notes.append(
        Curve(t=t0, x=LEFT)
        .to(t=t0 + q, x=RIGHT, ease_x="out_quad")
        .to(t=t0 + 2 * q, x=LEFT, ease_x="in_quad")
        .to(t=t0 + 3 * q, x=RIGHT, ease_x="out_quad")
        .to(t=t1, x=LEFT, ease_x="in_quad")
        .to_slide(w=WIDTH)
    )

    # Rising zigzag: x and h move on opposite easing families each leg
    t0, t1 = track.slot(DOUBLE)
    q = (t1 - t0) // 4
    h_mid = (H_LOW + H_HIGH) // 2
    _zz = (
        Curve(t=t0, x=LEFT, h=H_LOW)
        .to(t=t0 + q, x=RIGHT, h=h_mid, ease_x="out_sine", ease_h="in_sine")
        .to(t=t0 + 2 * q, x=LEFT, h=h_mid, ease_x="in_sine", ease_h="out_sine")
        .to(t=t0 + 3 * q, x=RIGHT, h=H_HIGH, ease_x="out_sine", ease_h="in_sine")
        .to(t=t1, x=LEFT, h=H_HIGH, ease_x="in_sine")
        .to_air_slide(w=WIDTH)
    )
    notes.append(Tap(t=int(_zz.t), x=_zz.x, w=WIDTH).add_air(_zz))

    # Gentle diagonal split into three eased thirds
    t0, t1 = track.slot(DOUBLE)
    q = (t1 - t0) // 3
    notes.append(
        Curve(t=t0, x=2)
        .to(t=t0 + q, x=5, ease_x="in_out_sine")
        .to(t=t0 + 2 * q, x=9, ease_x="in_out_sine")
        .to(t=t1, x=12, ease_x="in_out_sine")
        .to_slide(w=WIDTH)
    )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: Curve.then() / + concatenation
    # Two independent curves joined at their shared endpoint (operator +)
    t0, t1 = track.slot(DOUBLE)
    mid = (t0 + t1) // 2
    leg_a = Curve(t=t0, x=LEFT).to(t=mid, x=RIGHT, ease_x="out_expo")
    leg_b = Curve(t=mid, x=RIGHT).to(t=t1, x=LEFT, ease_x="in_expo")
    notes.append((leg_a + leg_b).to_slide(w=WIDTH))

    # Three segments chained with .then()
    t0, t1 = track.slot(DOUBLE)
    ta = t0 + (t1 - t0) // 3
    tb = t0 + 2 * (t1 - t0) // 3
    seg1 = Curve(t=t0, x=LEFT).to(t=ta, x=RIGHT, ease_x="in_circ")
    seg2 = Curve(t=ta, x=RIGHT).to(t=tb, x=4, ease_x="out_circ")
    seg3 = Curve(t=tb, x=4).to(t=t1, x=RIGHT, ease_x="in_out_circ")
    notes.append(seg1.then(seg2).then(seg3).to_slide(w=WIDTH))

    # AirCrush from two concatenated segments (height arcs up then down)
    t0, t1 = track.slot(DOUBLE)
    mid = (t0 + t1) // 2
    arc_up = Curve(t=t0, x=LEFT, h=H_LOW).to(
        t=mid, x=RIGHT, h=H_HIGH, ease_x="out_quint", ease_h="in_quint"
    )
    arc_dn = Curve(t=mid, x=RIGHT, h=H_HIGH).to(
        t=t1, x=LEFT, h=H_LOW, ease_x="in_quint", ease_h="out_quint"
    )
    notes.append((arc_up + arc_dn).to_air_crush(w=WIDTH, gap=SEGMENT_GAP, color=COLORS[4]))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 6: custom callable easings
    # Bounce: decelerating with two small bounces at the end
    def bounce(t: float) -> float:
        if t < 1 / 2.75:
            return 7.5625 * t * t
        if t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375

    t0, t1 = track.slot()
    notes.append(Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT, ease_x=bounce).to_slide(w=WIDTH))

    # Overshoot / "back" easing: goes slightly past the target before settling
    def overshoot(t: float) -> float:
        c1 = 1.70158
        c3 = c1 + 1.0
        return c3 * t * t * t - c1 * t * t

    t0, t1 = track.slot()
    notes.append(Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT, ease_x=overshoot).to_slide(w=WIDTH))

    # Sine-squared: faster than regular sine at both ends
    def sine_squared(t: float) -> float:
        s = math.sin(t * math.pi / 2)
        return s * s

    t0, t1 = track.slot()
    notes.append(Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT, ease_x=sine_squared).to_slide(w=WIDTH))

    # Elastic: spring-like with oscillating overshoot (wrapped in Tap parent)
    def elastic(t: float) -> float:
        if t <= 0:
            return 0.0
        if t >= 1:
            return 1.0
        c4 = 2 * math.pi / 3
        return -(2 ** (10 * t - 10)) * math.sin((t * 10 - 10.75) * c4)

    t0, t1 = track.slot()
    _el = (
        Curve(t=t0, x=LEFT, h=H_LOW)
        .to(t=t1, x=RIGHT, h=H_HIGH, ease_x=elastic, ease_h="in_out_sine")
        .to_air_slide(w=WIDTH)
    )
    notes.append(Tap(t=int(_el.t), x=_el.x, w=WIDTH).add_air(_el))

    # Stepped: discrete jumps at quarter-beat boundaries
    def stepped_4(t: float) -> float:
        return math.floor(t * 4) / 4 if t < 1 else 1.0

    t0, t1 = track.slot()
    notes.append(Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT, ease_x=stepped_4).to_slide(w=WIDTH))

    return notes


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes = build_notes()
    _summarize(notes)
    if args.dry_run:
        return
    push_gallery("curve gallery", notes)


if __name__ == "__main__":
    main()
