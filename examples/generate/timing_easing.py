"""Gallery of timing_easing(): scroll speed ramped along an easing curve.

The speed value itself is sampled from the easing at count+1 evenly-spaced points.
Tap notes serve as beat-boundary reference markers in each section.

Sections:
  1  All 21 easings — acceleration ramp (0.5 → 2.0), count=16.
  2  All 21 easings — deceleration ramp (2.0 → 0.5), count=16.
  3  Speed extremes (0.0 → 3.0) — selected easings that make the range dramatic.
  4  Subdivision comparison — in_cubic ramp at count=4,8,16,32,64.
  5  Velocity-range contrast — in_expo at narrow/moderate/wide/extreme speed pairs.

Usage (run from examples/generate/):
  python timing_easing.py             # push to Margrete (replaces chart)
  python timing_easing.py --dry-run   # summarize only; no connection needed
"""

from __future__ import annotations

from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.events import TimelineSpeedEvent
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import timing_easing

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

    # ----------------------------------------------------------- Section 1: all easings, acceleration (0.5 → 2.0)
    for name in EASING_NAMES:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing(t0=t0, t1=t1, start_speed=0.5, end_speed=2.0, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: all easings, deceleration (2.0 → 0.5)
    for name in EASING_NAMES:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing(t0=t0, t1=t1, start_speed=2.0, end_speed=0.5, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: speed extremes (0.0 → 3.0)
    extreme_easings = [
        "linear", "in_expo", "out_expo", "in_out_expo",
        "in_circ", "out_circ", "in_out_circ",
    ]
    for name in extreme_easings:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing(t0=t0, t1=t1, start_speed=0.0, end_speed=3.0, count=16, easing=name, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: subdivision comparison (in_cubic, count=4..64)
    for count in (4, 8, 16, 32, 64):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing(t0=t0, t1=t1, start_speed=0.5, end_speed=2.0, count=count, easing="in_cubic", til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: velocity-range contrast (in_expo)
    speed_pairs = [
        (0.8, 1.2),   # very narrow
        (0.5, 1.5),   # moderate
        (0.2, 2.0),   # wide
        (0.0, 2.5),   # starts from freeze
        (0.5, 3.0),   # reaches fast
    ]
    for start, end in speed_pairs:
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_easing(t0=t0, t1=t1, start_speed=start, end_speed=end, count=16, easing="in_expo", til=TIL)
        )

    return notes, events


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes, events = build_chart()
    _summarize(notes, events)
    if args.dry_run:
        return
    push_gallery("timing easing gallery", notes, events)


if __name__ == "__main__":
    main()
