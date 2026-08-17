"""Gallery of the rain() function: scattered short AirCrush traces across a time range.

Sections:
  1  Dense uniform rain — step=1/16, length=1/16, across the full x/h range.
  2  Sparse drops — step=1/2, length=1/4; widely-spaced, longer-lasting drops.
  3  Wide-field rain — step=1/8, full 16-lane span (x_range 0..15).
  4  Color gallery — one burst per COLORS color in its own lane band.
  5  Height-band strips — five narrow h_range windows stacked vertically.
  6  Length variation — same step, lengths 1/4, 1/8, 1/16, 1/32 side-by-side.

Usage (run from examples/generate/):
  python rain.py             # push to Margrete (replaces chart)
  python rain.py --dry-run   # summarize only; no connection needed
"""

from __future__ import annotations

from _common import (
    BEAT,
    COLORS,
    H_HIGH,
    H_LOW,
    LEFT,
    RIGHT,
    SPAN,
    WIDTH,
    _summarize,
    _Track,
    make_arg_parser,
    push_gallery,
)
from margrete_rpc.chart import ChartNote
from margrete_rpc.chart.util import rain

SECTION = 4 * SPAN  # each section spans 4 beats


def build_notes() -> list[ChartNote]:
    track = _Track()
    notes: list[ChartNote] = []

    # ----------------------------------------------------------- Section 1: dense uniform rain
    t0, t1 = track.slot(SECTION)
    notes.extend(
        rain(
            t0=t0,
            t1=t1,
            step=(1, 16),
            length=(1, 16),
            x_range=(LEFT, RIGHT),
            h_range=(H_LOW, H_HIGH),
            w=1,
            seed=42,
        )
    )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 2: sparse drops
    t0, t1 = track.slot(SECTION)
    notes.extend(
        rain(
            t0=t0,
            t1=t1,
            step=(1, 2),
            length=(1, 4),
            x_range=(LEFT, RIGHT),
            h_range=(H_LOW, H_HIGH),
            w=WIDTH,
            seed=7,
        )
    )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 3: wide-field rain (full 16 lanes)
    t0, t1 = track.slot(SECTION)
    notes.extend(
        rain(
            t0=t0,
            t1=t1,
            step=(1, 8),
            x_range=(0, 15),
            h_range=(H_LOW, H_HIGH),
            w=1,
            seed=99,
        )
    )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 4: color gallery (one burst per color in its own lane band)
    band_w = (RIGHT - LEFT) // len(COLORS)
    for i, color in enumerate(COLORS):
        x_lo = LEFT + i * band_w
        x_hi = min(x_lo + band_w, RIGHT)
        t0, t1 = track.slot(2 * SPAN)
        notes.extend(
            rain(
                t0=t0,
                t1=t1,
                step=(1, 8),
                x_range=(x_lo, x_hi),
                h_range=(H_LOW, H_HIGH),
                w=1,
                color=color,
                seed=i * 13,
            )
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 5: narrow height-band strips
    h_span = H_HIGH - H_LOW
    heights = [
        (H_LOW, H_LOW + h_span // 5),
        (H_LOW + h_span // 5, H_LOW + 2 * h_span // 5),
        (H_LOW + 2 * h_span // 5, H_LOW + 3 * h_span // 5),
        (H_LOW + 3 * h_span // 5, H_LOW + 4 * h_span // 5),
        (H_LOW + 4 * h_span // 5, H_HIGH),
    ]
    for h_lo, h_hi in heights:
        t0, t1 = track.slot(2 * SPAN)
        notes.extend(
            rain(
                t0=t0,
                t1=t1,
                step=(1, 8),
                x_range=(LEFT, RIGHT),
                h_range=(h_lo, h_hi),
                w=1,
                seed=h_lo,
            )
        )

    track.skip(BEAT)

    # ----------------------------------------------------------- Section 6: length variation (same step=1/8, varying length)
    for length_frac in ((1, 4), (1, 8), (1, 16), (1, 32)):
        t0, t1 = track.slot(2 * SPAN)
        notes.extend(
            rain(
                t0=t0,
                t1=t1,
                step=(1, 8),
                length=length_frac,
                x_range=(LEFT, RIGHT),
                h_range=(H_LOW, H_HIGH),
                w=1,
                seed=101,
            )
        )

    return notes


def main() -> None:
    parser = make_arg_parser(__doc__ or "")
    args = parser.parse_args()
    notes = build_notes()
    _summarize(notes)
    if args.dry_run:
        return
    push_gallery("rain gallery", notes)


if __name__ == "__main__":
    main()
