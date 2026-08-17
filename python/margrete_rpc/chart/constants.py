STANDARD_FIELD_WIDTH = 16
"""Width of the standard playfield in lane units."""

STANDARD_FLIP_LANE = STANDARD_FIELD_WIDTH // 2
"""Lane axis used by default for horizontal note flipping."""

DEFAULT_H = 80
"""Default air-note height (``h``) in editor units."""

AIRCRUSH_GAP_TRACELIKE = 0
"""AirTrace mode: line only."""

AIRCRUSH_GAP_HEADONLY = 0x7FFFFFFF
"""Head-only mode: only one step at the head."""

DEFAULT_AIRCRUSH_GAP = AIRCRUSH_GAP_TRACELIKE
"""Default AirCrush gap: :data:`AIRCRUSH_GAP_TRACELIKE`."""

TICK_RESOLUTION = 1920
"""Tick resolution: the number of ticks in one whole note (1/1)."""
