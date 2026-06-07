"""Mono renderer: threshold each frame to tap (bright) and damage (dark) notes.

One note per pixel. Brightness is measured by Otsu's method on the grayscale
frame, so the threshold adapts to each frame's histogram automatically.
"""

import cv2
import numpy as np

from margrete_rpc.chart.raw import R, RawNote


def frame_to_notes(
    frame_bgr: np.ndarray,
    base_tick: int,
    tick_per_row: int,
    x_offset: int,
) -> list[RawNote]:
    """Convert a BGR frame to a full grid of tap / damage notes.

    Row 0 (top of image) maps to the highest tick so the video reads top-to-bottom
    as the playfield scrolls upward.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bitmap = binary.astype(bool)

    notes: list[RawNote] = []
    rows, cols = bitmap.shape
    for row in range(rows):
        t = base_tick + (rows - 1 - row) * tick_per_row
        for col in range(cols):
            x = col - x_offset
            notes.append(R.tap(t, x, 1) if bitmap[row, col] else R.damage(t, x, 1))
    return notes
