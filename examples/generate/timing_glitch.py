"""Gallery of timing_glitch(): scroll-speed glitch and stutter effects on TIL 0.

Each section places Tap notes as beat markers and applies timing_glitch() across
the same span so the scroll distortion is visible in Margrete.

Sections:
  1  Freeze glitch (base_speed=0.0, speed_range=1.0) — count=1,2,4,8,16 spikes.
  2  Jitter (base_speed=1.0) — speed_range=0.25,0.5,0.75,1.0,2.0 at count=8.
  3  Reverse thrust (base_speed=2.0, speed_range=1.5) — count=2,4,8,12,16.
  4  Dense fast glitch — count=32, speed_range=0.5, taps at 1/4-beat grid.
  5  Extreme swings (base_speed=1.0, speed_range=4.0) — count=4,6,8,10,12.

Usage (run from examples/generate/):
  python timing_glitch.py             # push to Margrete (replaces chart)
  python timing_glitch.py --dry-run   # summarize only; no connection needed
"""

from __future__ import annotations

from _common import (
    BEAT,
    WIDTH,
    _summarize,
    _Track,
    make_arg_parser,
    push_gallery,
)
from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.events import TimelineSpeedEvent
from margrete_rpc.chart.notes import Tap
from margrete_rpc.chart.util import timing_glitch

SECTION = 4 * BEAT  # each section occupies 4 beats
TIL = 0  # all notes and events on the main timeline


def _beat_taps(t0: int, t1: int, step: int = BEAT) -> list[Tap]:
    """Tap notes at every ``step`` ticks within ``[t0, t1)`` as visual reference."""
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

    # ----------------------------------------------------------- Section 1: freeze glitch (speed drops to 0)
    for count in (1, 2, 4, 8, 16):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_glitch(t0=t0, t1=t1, count=count, speed_range=1.0, base_speed=0.0, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: jitter around normal speed
    for speed_range in (0.25, 0.5, 0.75, 1.0, 2.0):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_glitch(t0=t0, t1=t1, count=8, speed_range=speed_range, base_speed=1.0, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: reverse thrust (high base speed with large swings)
    for count in (2, 4, 8, 12, 16):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_glitch(t0=t0, t1=t1, count=count, speed_range=1.5, base_speed=2.0, til=TIL)
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: dense fast glitch (32 spikes)
    t0, t1 = track.slot(SECTION)
    notes.extend(_beat_taps(t0, t1, step=BEAT // 4))
    events.extend(timing_glitch(t0=t0, t1=t1, count=32, speed_range=0.5, base_speed=1.0, til=TIL))

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: extreme swings (speed_range=4.0)
    for count in (4, 6, 8, 10, 12):
        t0, t1 = track.slot(SECTION)
        notes.extend(_beat_taps(t0, t1))
        events.extend(
            timing_glitch(t0=t0, t1=t1, count=count, speed_range=4.0, base_speed=1.0, til=TIL)
        )

    return notes, events


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes, events = build_chart()
    _summarize(notes, events)
    if args.dry_run:
        return
    push_gallery("timing glitch gallery", notes, events)


if __name__ == "__main__":
    main()
