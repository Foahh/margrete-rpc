"""Gallery of the envelope() function: curves that weave between two boundary paths.

Sections:
  1  Parallel straight boundaries — count=1..8 oscillations; even count ends on inner.
  2  Same-direction curved boundaries — in_sine inner, out_sine outer.
  3  Opposite-direction boundaries — inner sweeps L→R, outer sweeps R→L (cross-over).
  4  Asymmetric speeds — slow inner (in_out_sine) vs fast outer (in_out_expo).
  5  AirSlide output from envelope, paired with Tap parents.

Usage (run from examples/generate/):
  python envelop.py           # push to Margrete (replaces chart)
  python envelop.py --dry-run # summarize only; no connection needed
"""

from __future__ import annotations

from _common import (
    BEAT,
    DOUBLE,
    H_HIGH,
    H_LOW,
    LEFT,
    RIGHT,
    WIDTH,
    _summarize,
    _Track,
    make_arg_parser,
    push_gallery,
)

from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import Curve, envelope


def build_notes() -> list[ChartNote]:
    track = _Track()
    notes: list[ChartNote] = []

    # ----------------------------------------------------------- Section 1: parallel straight boundaries, count=1..8
    # Even count ends back on the inner boundary; odd count ends on outer.
    for count in range(1, 9):
        t0, t1 = track.slot(DOUBLE)
        inner = Curve(t=t0, x=LEFT).to(t=t1, x=LEFT + 4)
        outer = Curve(t=t0, x=RIGHT - 4).to(t=t1, x=RIGHT)
        notes.append(envelope(inner, outer, count=count).to_slide(w=WIDTH).clamp())

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: curved boundaries (in_sine inner, out_sine outer)
    for count in (2, 3, 4, 6, 8):
        t0, t1 = track.slot(DOUBLE)
        inner = Curve(t=t0, x=1).to(t=t1, x=6, ease_x="in_sine")
        outer = Curve(t=t0, x=7).to(t=t1, x=13, ease_x="out_sine")
        notes.append(envelope(inner, outer, count=count).to_slide(w=WIDTH).clamp())

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: opposite-direction boundaries (cross-over)
    # inner sweeps L→R, outer sweeps R→L; the weave crosses through the centre.
    for count in (2, 4, 6, 8, 12):
        t0, t1 = track.slot(DOUBLE)
        inner = Curve(t=t0, x=LEFT).to(t=t1, x=RIGHT)
        outer = Curve(t=t0, x=RIGHT).to(t=t1, x=LEFT)
        notes.append(envelope(inner, outer, count=count).to_slide(w=WIDTH).clamp())

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: asymmetric speeds (slow inner, fast outer)
    for count in (3, 5, 7, 9, 11):
        t0, t1 = track.slot(DOUBLE)
        inner = Curve(t=t0, x=3).to(t=t1, x=5, ease_x="in_out_sine")
        outer = Curve(t=t0, x=8).to(t=t1, x=13, ease_x="in_out_expo")
        notes.append(envelope(inner, outer, count=count).to_slide(w=WIDTH).clamp())

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: AirSlide output from envelope
    for count in (2, 3, 4, 5, 6):
        t0, t1 = track.slot(DOUBLE)
        inner = Curve(t=t0, x=LEFT, h=H_LOW).to(t=t1, x=LEFT + 6, h=H_LOW + 20)
        outer = Curve(t=t0, x=RIGHT - 6, h=H_HIGH - 20).to(t=t1, x=RIGHT, h=H_HIGH)
        air = envelope(inner, outer, count=count).to_air_slide(w=WIDTH)
        notes.append(Tap(t=int(air.t), x=air.x, w=WIDTH).add_air(air))

    return notes


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes = build_notes()
    _summarize(notes)
    if args.dry_run:
        return
    push_gallery("envelope gallery", notes)


if __name__ == "__main__":
    main()
