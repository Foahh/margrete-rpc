"""Gallery of generated curved slides, air-slides and air-crushes.

Builds a long, scrollable sequence that exercises the whole slide-generator API
(``margrete_rpc.chart.util``) so the results can be eyeballed inside Margrete:

  * Section 1 - a ground ``Slide`` per easing (x-axis sweep), covering every family.
  * Section 2 - an ``AirSlide`` per easing on the height axis, each attached to a
                ``Tap`` parent.
  * Section 3 - an ``AirCrush`` per easing, cycling through colors.
  * Section 4 - ``envelope`` weaves between two boundary paths at a few cycle counts.
  * Section 5 - a single multi-joint ``Curve`` chained with ``.to()`` (per-leg easing).

Everything starts at tick 0 and consecutive notes are separated by a 1/8-beat gap.

Usage:
  python main.py             # generate and push to the running Margrete (replaces chart)
  python main.py --dry-run   # just build and print a summary, no connection needed
"""

import argparse

from margrete_rpc import Margrete
from margrete_rpc.chart import TICK_RESOLUTION, ChartNote, d2t
from margrete_rpc.chart.notes import ColorValue, Tap
from margrete_rpc.chart.util import EASINGS, Curve, envelope

# --- Layout knobs ------------------------------------------------------------

BEAT = TICK_RESOLUTION  # one whole note in ticks (1920)
SPAN = BEAT  # each generated note lasts one beat
GAP = d2t(1, 8)  # 1/8-beat gap between consecutive notes
SEGMENT_GAP = (1, 8)  # air-crush internal segment gap (1/8 beat)

WIDTH = 2  # constant width applied to every generated note
LEFT, RIGHT = 1, 13  # lane sweep range within the 16-lane field
H_LOW, H_HIGH = 20, 120  # air-height sweep range

# All registered easings, in family order: linear, sine, quad, cubic, quart,
# quint, expo, circ (each as in_/out_/in_out_).
EASING_NAMES = list(EASINGS)

# A vivid palette to cycle the air-crush colors through.
COLORS = [
    ColorValue.RED,
    ColorValue.ORANGE,
    ColorValue.YELLOW,
    ColorValue.GREEN,
    ColorValue.SKY,
    ColorValue.BLUE,
    ColorValue.VIOLET,
    ColorValue.PINK,
]


class _Track:
    """A moving cursor that hands out consecutive [t0, t1] slots separated by ``GAP``."""

    def __init__(self) -> None:
        self.t = 0

    def slot(self, span: int = SPAN) -> tuple[int, int]:
        t0 = self.t
        t1 = t0 + span
        self.t = t1 + GAP
        return t0, t1


def _sweep(index: int) -> tuple[int, int]:
    """Alternate the lane sweep direction so successive notes zig-zag."""
    return (LEFT, RIGHT) if index % 2 == 0 else (RIGHT, LEFT)


def build_notes() -> list[ChartNote]:
    """Build the full gallery of generated notes (pure; needs no live Margrete)."""
    track = _Track()
    notes: list[ChartNote] = []

    # Section 1: ground slides, one per easing on the lane axis.
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        path = Curve(t=t0, x=x0).to(t=t1, x=x1, ease_x=name)
        notes.append(path.to_slide(w=WIDTH))

    # Section 2: air-slides, one per easing on the height axis, each on a Tap parent.
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        path = Curve(t=t0, x=x0, h=H_LOW).to(
            t=t1, x=x1, h=H_HIGH, ease_x="in_out_sine", ease_h=name
        )
        air = path.to_air_slide(w=WIDTH)
        begin = path.waypoints[0]
        parent = Tap(t=begin.t, x=begin.x, w=WIDTH).add_air(air)
        notes.append(parent)

    # Section 3: air-crushes, one per easing, cycling colors, with a 1/8 segment gap.
    for i, name in enumerate(EASING_NAMES):
        t0, t1 = track.slot()
        x0, x1 = _sweep(i)
        path = Curve(t=t0, x=x0, h=H_LOW).to(
            t=t1, x=x1, h=H_HIGH, ease_x=name, ease_h="in_out_sine"
        )
        color = COLORS[i % len(COLORS)]
        notes.append(path.to_air_crush(w=WIDTH, gap=SEGMENT_GAP, color=color))

    # Section 4: envelope weaves between two straight boundaries.
    for cycles in (1, 2, 3, 4, 5, 6, 7, 8):
        t0, t1 = track.slot(2 * SPAN)
        inner = Curve(t=t0, x=0).to(t=t1, x=8, ease_x="in_sine")
        outer = Curve(t=t0, x=6).to(t=t1, x=15, ease_x="out_sine")
        notes.append(envelope(inner, outer, count=cycles).to_slide(w=2).clamp())

    # Section 5: a single multi-joint curve built by chaining .to(), each leg eased on its own.
    t0, t1 = track.slot(2 * SPAN)
    mid = (t0 + t1) // 2
    notes.append(
        Curve(t=t0, x=LEFT)
        .to(t=mid, x=RIGHT, ease_x="out_quad")
        .to(t=t1, x=LEFT, ease_x="in_quad")
        .to_slide(w=WIDTH)
    )

    return notes


def _summarize(notes: list[ChartNote]) -> None:
    counts: dict[str, int] = {}
    for note in notes:
        counts[type(note).__name__] = counts.get(type(note).__name__, 0) + 1
    print(f"Generated {len(notes)} notes:")
    for name, count in sorted(counts.items()):
        print(f"  {name:10s} {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and summarize the notes without connecting to Margrete.",
    )
    args = parser.parse_args()

    notes = build_notes()
    _summarize(notes)

    if args.dry_run:
        return

    mg = Margrete()
    print(mg.status())
    with mg.open_edit(replace_all=True) as tx:
        tx.chart.notes = notes
    print("Pushed the slide gallery to Margrete (replaced the existing chart).")


if __name__ == "__main__":
    main()
