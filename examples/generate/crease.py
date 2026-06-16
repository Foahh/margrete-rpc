"""Gallery of the crease() function: zigzag curves around various base paths.

Sections:
  1  Straight horizontal base — count=2,3,4,6,8,12 zigzag legs at x_range=3.
  2  Curved base (out_quad sweep) — count=4 legs, x_range varies from 1 to 6.
  3  Diagonal base with h_range — combined lane+height zigzag output as AirCrush.
  4  Height-only zigzag — x_range=0, h_range drives AirSlide oscillation with Tap parents.
  5  Large-amplitude crease clamped to field; double-crease (crease of a crease).

Usage (run from examples/generate/):
  python crease.py            # push to Margrete (replaces chart)
  python crease.py --dry-run  # summarize only; no connection needed
"""

from __future__ import annotations

from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import Curve, crease

from _common import (
    BEAT,
    COLORS,
    DOUBLE,
    H_HIGH,
    H_LOW,
    LEFT,
    RIGHT,
    SEGMENT_GAP,
    SPAN,
    WIDTH,
    _Track,
    _summarize,
    make_arg_parser,
    push_gallery,
)


def build_notes() -> list[ChartNote]:
    track = _Track()
    notes: list[ChartNote] = []

    # ----------------------------------------------------------- Section 1: straight base, varying count
    # Even count returns to the base's far end; odd count ends at the shifted side.
    for count in (2, 3, 4, 6, 8, 12):
        t0, t1 = track.slot(SPAN)
        base = Curve(t=t0, x=4).to(t=t1, x=12)
        notes.append(crease(base, count=count, x_range=3).to_slide(w=WIDTH))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: curved base (out_quad), varying x_range
    for x_range in (1, 2, 3, 4, 6):
        t0, t1 = track.slot(SPAN)
        base = Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT, ease_x="out_quad")
        notes.append(crease(base, count=4, x_range=x_range).to_slide(w=WIDTH).clamp_w())

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: diagonal base + h_range → AirCrush
    for i, count in enumerate((2, 3, 4, 6, 8)):
        t0, t1 = track.slot(SPAN)
        base = Curve(t=t0, x=LEFT, h=H_LOW).to(t=t1, x=RIGHT, h=H_HIGH)
        color = COLORS[i % len(COLORS)]
        notes.append(
            crease(base, count=count, x_range=2, h_range=15)
            .to_air_crush(w=WIDTH, gap=SEGMENT_GAP, color=color)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: height-only zigzag → AirSlide (x_range=0)
    # x tracks the base normally; only height oscillates by ±h_range.
    for count in (2, 3, 4, 6, 8):
        t0, t1 = track.slot(SPAN)
        base = Curve(t=t0, x=LEFT, h=H_LOW).to(t=t1, x=RIGHT, h=H_HIGH)
        air_slide = crease(base, count=count, x_range=0, h_range=20).to_air_slide(w=WIDTH)
        notes.append(Tap(t=int(air_slide.t), x=air_slide.x, w=WIDTH).add_air(air_slide))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: large amplitude + clamp; double-crease
    # Large amplitude: x_range=8 sends points well outside the field; clamp_w brings them back.
    t0, t1 = track.slot(DOUBLE)
    base = Curve(t=t0, x=6).to(t=t1, x=10)
    notes.append(crease(base, count=6, x_range=8).to_slide(w=WIDTH).clamp_w())

    # Double crease: apply crease twice to produce a finer secondary zigzag.
    t0, t1 = track.slot(DOUBLE)
    base = Curve(t=t0, x=4).to(t=t1, x=12)
    first = crease(base, count=4, x_range=3)
    notes.append(crease(first, count=3, x_range=1).to_slide(w=WIDTH).clamp_w())

    # Crease on an eased base → AirSlide with Tap parent.
    t0, t1 = track.slot(DOUBLE)
    base = Curve(t=t0, x=LEFT, h=H_LOW).to(
        t=t1, x=RIGHT, h=H_HIGH, ease_x="in_out_cubic", ease_h="in_out_cubic"
    )
    air_slide = crease(base, count=5, x_range=2, h_range=10).to_air_slide(w=WIDTH)
    notes.append(Tap(t=int(air_slide.t), x=air_slide.x, w=WIDTH).add_air(air_slide))

    return notes


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes = build_notes()
    _summarize(notes)
    if args.dry_run:
        return
    push_gallery("crease gallery", notes)


if __name__ == "__main__":
    main()
