"""Gallery of timing_easing_by_disp(): scroll speed driven by an easing's derivative.

Unlike timing_easing() which samples the curve's *value*, this samples its *slope*
and scales by base_speed. The accumulated scroll displacement then traces the easing
shape: speed is high where the curve rises steeply and low where it plateaus.

Sections:
  1  All compatible easings by displacement (circ excluded), base_speed=1.0, count=16.
  2  In-family (fast-at-start): in_sine/quad/cubic/quart/quint/expo derivatives.
  3  Out-family (fast-at-end): out_sine/quad/cubic/quart/quint/expo derivatives.
  4  Varying base_speed (0.5, 1.0, 1.5, 2.0, 3.0) for in_out_sine derivative.
  5  Subdivision coarseness — in_cubic derivative at count=4,8,16,32,64.

Usage (run from examples/generate/):
  python timing_easing_by_disp.py             # push to Margrete (replaces chart)
  python timing_easing_by_disp.py --dry-run   # summarize only; no connection needed
"""

from __future__ import annotations

from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.events import TimelineSpeedEvent
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import timing_easing_by_disp

from _common import (
    BEAT,
    EASING_NAMES,
    WIDTH,
    _Track,
    _summarize,
    make_arg_parser,
    push_gallery,
)

SECTION = 4 * BEAT
TIL = 0

# circ easings have a vertical tangent (infinite slope) at their endpoint, so the
# finite-difference derivative used by timing_easing_by_disp raises a math domain error.
_SAFE = [name for name in EASING_NAMES if "circ" not in name]


def _beat_taps(t0: int, t1: int, step: int = BEAT) -> list[Tap]:
    taps: list[Tap] = []
    t = t0
    while t < t1:
        taps.append(Tap(t=t, x=7, w=WIDTH))
        t += step
    return taps


def build_chart() -> tuple[list[ChartNote], list[TimelineSpeedEvent]]:
    track = _Track()
    notes: list[ChartNote] = []
    events: list[TimelineSpeedEvent] = []

    # ----------------------------------------------------------- Section 1: all compatible easings by displacement (circ excluded)
    for name in _SAFE:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing_by_disp(t0=t0, t1=t1, base_speed=1.0, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: in-family — fast at start, slowing at end (in_circ excluded)
    in_easings = ["in_sine", "in_quad", "in_cubic", "in_quart", "in_quint", "in_expo"]
    for name in in_easings:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing_by_disp(t0=t0, t1=t1, base_speed=1.0, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: out-family — slow at start, fast at end (out_circ excluded)
    out_easings = ["out_sine", "out_quad", "out_cubic", "out_quart", "out_quint", "out_expo"]
    for name in out_easings:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing_by_disp(t0=t0, t1=t1, base_speed=1.0, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: varying base_speed for in_out_sine derivative
    for base_speed in (0.5, 1.0, 1.5, 2.0, 3.0):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing_by_disp(
                t0=t0, t1=t1, base_speed=base_speed, count=16, easing="in_out_sine", til=TIL
            )
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: subdivision coarseness (in_cubic derivative)
    for count in (4, 8, 16, 32, 64):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing_by_disp(
                t0=t0, t1=t1, base_speed=1.0, count=count, easing="in_cubic", til=TIL
            )
        )

    return notes, events


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes, events = build_chart()
    _summarize(notes, events)
    if args.dry_run:
        return
    push_gallery("timing easing by disp gallery", notes, events)


if __name__ == "__main__":
    main()
