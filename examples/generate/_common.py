"""Shared constants, layout helpers, and CLI boilerplate for the generate/ gallery scripts."""

from __future__ import annotations

import argparse

from margrete_rpc import Margrete
from margrete_rpc.chart import TICK_RESOLUTION, ChartNote, div_to_tick
from margrete_rpc.chart.events import TimelineSpeedEvent
from margrete_rpc.chart.notes import ColorValue
from margrete_rpc.chart.util import EASINGS

# ------------------------------------------------------------------------------- timing constants

BEAT = TICK_RESOLUTION  # 1920 ticks — one whole note
HALF = BEAT // 2
DOUBLE = 2 * BEAT
GAP = div_to_tick(1, 8)  # 1/8-beat gap between consecutive notes
SPAN = BEAT  # default note duration: one beat

# ------------------------------------------------------------------------------- layout constants

SEGMENT_GAP: tuple[int, int] = (1, 8)  # air-crush segment gap as a beat fraction
WIDTH = 2  # constant lane width for generated notes
LEFT, RIGHT = 1, 13  # lane sweep range within the 16-lane field
H_LOW, H_HIGH = 20, 120  # air-height sweep range

EASING_NAMES: list[str] = list(EASINGS)

COLORS: list[ColorValue] = [
    ColorValue.RED,
    ColorValue.ORANGE,
    ColorValue.YELLOW,
    ColorValue.GREEN,
    ColorValue.SKY,
    ColorValue.BLUE,
    ColorValue.VIOLET,
    ColorValue.PINK,
]

# ------------------------------------------------------------------------------- layout helpers


class _Track:
    """Moving cursor that hands out consecutive [t0, t1] time slots separated by GAP."""

    def __init__(self, start: int = 0) -> None:
        self.t = start

    def slot(self, span: int = SPAN) -> tuple[int, int]:
        """Return ``(t0, t1)`` for the next slot and advance the cursor past the gap."""
        t0 = self.t
        t1 = t0 + span
        self.t = t1 + GAP
        return t0, t1

    def skip(self, ticks: int = BEAT) -> None:
        """Advance the cursor by ``ticks`` without allocating a slot."""
        self.t += ticks


def _sweep(index: int) -> tuple[int, int]:
    """Alternate the lane direction so successive notes zig-zag LEFT↔RIGHT."""
    return (LEFT, RIGHT) if index % 2 == 0 else (RIGHT, LEFT)


# ------------------------------------------------------------------------------- I/O


def _summarize(
    notes: list[ChartNote],
    events: list[TimelineSpeedEvent] | None = None,
) -> None:
    counts: dict[str, int] = {}
    for note in notes:
        counts[type(note).__name__] = counts.get(type(note).__name__, 0) + 1
    print(f"Generated {len(notes)} notes:")
    for name, count in sorted(counts.items()):
        print(f"  {name:10s} {count}")
    if events:
        print(f"Generated {len(events)} timing events.")


def make_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and summarize without connecting to Margrete.",
    )
    return parser


def push_gallery(
    label: str,
    notes: list[ChartNote],
    events: list[TimelineSpeedEvent] | None = None,
) -> None:
    """Connect to Margrete and replace the chart with ``notes`` and optional ``events``."""
    mg = Margrete()
    print(mg.status())
    with mg.open_edit(
        replace_all_notes=True,
        replace_all_events=True,
        event_scan_til_ids=[],
    ) as tx:
        tx.chart.notes = notes
        if events:
            tx.chart.tils = events
    print(f"Pushed '{label}' to Margrete (replaced the existing chart).")
