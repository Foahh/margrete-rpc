"""Color renderer: LAB-quantize each frame to AirCrush notes.

Each pixel is matched to the nearest AirCrush palette color in LAB space.
Consecutive same-color pixels in a column are merged into a single
AirCrush begin/end pair (run-length encoding) to reduce note count.

Achromatic pixels (low chroma) are decided by brightness alone:
  - bright  -> WHITE
  - dim     -> BLACK
Anything below ``dark_threshold`` (L in OpenCV 0-255 scale) also becomes BLACK.
"""

import cv2
import numpy as np
from margrete_rpc.chart.notes import R, RawNote
from margrete_rpc.chart.notes.color import Color

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# Approximate sRGB values for each AirCrush color, matched from in-editor
# swatches.  WHITE and BLACK lead the list and are the targets for achromatic
# pixels; they are excluded from the hue match so saturated pixels never snap
# to them.

_PALETTE: list[tuple[Color, tuple[int, int, int]]] = [
    (Color.WHITE, (255, 255, 255)),  # index 0: bright-neutral target only
    (Color.BLACK, (0, 0, 0)),  # index 1: dark-neutral target only
    (Color.RED, (220, 20, 20)),
    (Color.ORANGE, (255, 100, 0)),
    (Color.YELLOW, (255, 200, 0)),
    (Color.GRASS, (120, 220, 0)),
    (Color.GREEN, (0, 185, 0)),
    (Color.SKY, (0, 200, 240)),
    (Color.SKY_BLUE, (30, 140, 255)),
    (Color.COBALT_BLUE, (0, 70, 200)),
    (Color.BLUE, (10, 20, 180)),
    (Color.VIOLET, (120, 0, 210)),
    (Color.PURPLE, (170, 0, 200)),
    (Color.PINK, (255, 30, 160)),
]

_WHITE_IDX = 0
_BLACK_IDX = 1
_COLORS: list[Color] = [c for c, _ in _PALETTE]

# ---------------------------------------------------------------------------
# Quantization thresholds (OpenCV 8-bit LAB: L, a, b each 0-255; a/b neutral
# at 128; "chroma" = distance of (a, b) from the neutral point).
# ---------------------------------------------------------------------------
DARK_L_THRESHOLD = 40  # L below this -> BLACK regardless of chroma
_NEUTRAL_CHROMA = 14  # chroma below this -> achromatic (no usable hue)
_NEUTRAL_BRIGHT = 150  # achromatic & L >= this -> WHITE; dimmer -> BLACK
# Amplify a/b before the hue match so desaturated warm tones land on a warm
# palette entry rather than snapping to whichever entry shares their lightness.
_CHROMA_BOOST = 2.3

# ---------------------------------------------------------------------------
# Pre-computed LAB palette (built once at import time)
# ---------------------------------------------------------------------------


def _build_lab_palette() -> np.ndarray:
    labs = []
    for _, rgb in _PALETTE:
        bgr = np.array([[rgb[2], rgb[1], rgb[0]]], dtype=np.uint8).reshape(1, 1, 3)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(3).astype(np.float32)
        labs.append(lab)
    return np.array(labs)  # (N, 3)


_LAB_PALETTE: np.ndarray = _build_lab_palette()
_CHROMA_LAB: np.ndarray = _LAB_PALETTE[2:]  # hue-match palette: WHITE + BLACK excluded

# ---------------------------------------------------------------------------
# AirCrush geometry
# ---------------------------------------------------------------------------
_AC_W = 2  # note width; visual line appears at x + 0.5
_AC_H = 500  # crush line height in air space


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def frame_to_notes(
    frame_bgr: np.ndarray,
    base_tick: int,
    tick_per_row: int,
    x_offset: int,
    *,
    dark_threshold: int = DARK_L_THRESHOLD,
) -> list[RawNote]:
    """Convert a BGR frame to AirCrush notes with run-length encoding per column."""
    color_idx = _quantize_frame(frame_bgr, dark_threshold)  # (H, W) int32
    rows, cols = color_idx.shape
    notes: list[RawNote] = []
    for col in range(cols):
        x = col - x_offset
        notes.extend(_col_to_aircrush(color_idx[:, col], x, base_tick, tick_per_row, rows))
    return notes


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _quantize_frame(frame_bgr: np.ndarray, dark_threshold: int) -> np.ndarray:
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    pixels = lab.reshape(-1, 3)
    lum = pixels[:, 0]
    a = pixels[:, 1] - 128.0
    b = pixels[:, 2] - 128.0
    chroma = np.sqrt(a * a + b * b)

    # Hue match on chroma-boosted color against the chromatic subset of the palette.
    boosted = np.stack([lum, 128.0 + a * _CHROMA_BOOST, 128.0 + b * _CHROMA_BOOST], axis=1)
    dists = np.sum((boosted[:, np.newaxis] - _CHROMA_LAB[np.newaxis]) ** 2, axis=2)
    indices = np.argmin(dists, axis=1) + 2  # +2: _CHROMA_LAB skips WHITE + BLACK

    neutral = chroma < _NEUTRAL_CHROMA
    indices[neutral & (lum >= _NEUTRAL_BRIGHT)] = _WHITE_IDX
    indices[neutral & (lum < _NEUTRAL_BRIGHT)] = _BLACK_IDX
    indices[lum < dark_threshold] = _BLACK_IDX

    return indices.reshape(h, w)


def _col_to_aircrush(
    col_indices: np.ndarray,
    x: int,
    base_tick: int,
    tick_per_row: int,
    rows: int,
) -> list[RawNote]:
    """Run-length encode one column into AirCrush begin/end pairs."""
    notes: list[RawNote] = []
    i = 0
    while i < rows:
        idx = int(col_indices[i])
        j = i + 1
        while j < rows and int(col_indices[j]) == idx:
            j += 1

        color = _COLORS[idx]
        # Row i is the top of this run (highest tick); row j-1 is the bottom.
        t_begin = base_tick + (rows - j) * tick_per_row
        t_end = base_tick + (rows - i) * tick_per_row
        begin = R.air_crush_begin(t_begin, x, _AC_W, _AC_H, color=color)
        end = R.air_crush_end(t_end, x, _AC_W, _AC_H)
        begin.child(end)
        notes.append(begin)

        i = j
    return notes
