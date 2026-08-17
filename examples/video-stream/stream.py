"""Stream a video as Margrete notes via RPC.

Two rendering modes are available, selected with --mode:

  mono  (default)  Each pixel becomes a tap (bright) or damage (dark) note.
                   Full grid coverage; note count = width x height per frame.
                   Best for high-contrast black-and-white footage.

  color            Each pixel is matched to the AirCrush palette via LAB
                   color space. Consecutive same-color pixels per column are
                   merged (run-length encoding) to reduce note count.
                   Best for colorful footage.

Canvas layout:
  x axis   : video columns, centered around lane 7.5
  tick axis : base_tick + row * tick_per_row  (row 0 = top of image = highest tick)

Usage:
  python stream.py [video] [--mode mono|color]
                   [--audio FILE] [--offset S]
                   [--width N] [--fps F] [--tick-per-row N] [--base-tick N]
                   [--dark-threshold L]

Examples:
  python stream.py a.mp4
  python stream.py b.mp4 --mode color
  python stream.py c.mp4 --mode color --width 24 --fps 24 --dark-threshold 35
"""

import argparse
import functools
import time
from collections.abc import Callable
from dataclasses import dataclass

import _color
import _mono
import _video
import numpy as np
import psutil
import sounddevice as sd
from margrete_rpc import Margrete
from margrete_rpc.chart.notes import RawNote

# A renderer maps (frame_bgr, base_tick, tick_per_row, x_offset) -> notes.
type FrameConverter = Callable[[np.ndarray, int, int, int], list[RawNote]]


@dataclass
class _FrameStat:
    rpc_ms: float
    note_count: int


def stream(
    video_path: str,
    frame_to_notes: FrameConverter,
    *,
    audio_path: str | None,
    offset: float,
    width: int,
    fps: float,
    tick_per_row: int,
    base_tick: int,
) -> None:
    print(f"Loading {video_path!r}  width={width}  fps={fps}")
    actual_fps, frames = _video.load_frames(video_path, width, fps)

    n_frames = len(frames)
    frame_h = frames[0].shape[0]
    x_offset = width // 2 - 8  # center visual columns around lane 7.5

    print(
        f"Canvas: {width}w x {frame_h}h"
        f"  tick_per_row={tick_per_row}  spans {frame_h * tick_per_row} ticks"
    )

    audio = _video.load_audio(audio_path, video_path, offset)
    print()

    proc = psutil.Process()
    mg = Margrete()
    print(mg.status())

    stats: list[_FrameStat] = []

    if audio is not None:
        sd.play(*audio)

    wall_start = time.perf_counter()

    try:
        for i, frame in enumerate(frames):
            notes = frame_to_notes(frame, base_tick, tick_per_row, x_offset)

            t0 = time.perf_counter()
            with mg.open_edit(snapshot=False, raw_notes=True, replace_all_notes=True) as tx:
                tx.chart.notes = notes
            rpc_ms = (time.perf_counter() - t0) * 1000

            stats.append(_FrameStat(rpc_ms, len(notes)))

            if i == 0 or (i + 1) % 30 == 0:
                mem_mb = proc.memory_info().rss / 1e6
                elapsed = time.perf_counter() - wall_start
                real_fps = (i + 1) / elapsed if elapsed > 0 else 0
                print(
                    f"  [{i + 1:4d}/{n_frames}]  notes={len(notes):5d}"
                    f"  rpc={rpc_ms:6.1f}ms  fps={real_fps:5.1f}  mem={mem_mb:.0f}MB"
                )

            target_elapsed = (i + 1) / actual_fps
            remaining = target_elapsed - (time.perf_counter() - wall_start)
            if remaining > 0:
                time.sleep(remaining)
    finally:
        if audio is not None:
            sd.stop()

    total = time.perf_counter() - wall_start
    rpc_ms_list = [s.rpc_ms for s in stats]
    avg_notes = sum(s.note_count for s in stats) / len(stats)

    print()
    print("--- Summary ---")
    print(f"Frames:       {n_frames}")
    print(f"Wall time:    {total:.2f}s")
    print(f"Target fps:   {actual_fps:.2f}  Real fps: {n_frames / total:.2f}")
    print(f"Avg notes/f:  {avg_notes:.0f}  (max {max(s.note_count for s in stats)})")
    print(
        f"RPC latency:  avg={sum(rpc_ms_list) / len(rpc_ms_list):.1f}ms"
        f"  min={min(rpc_ms_list):.1f}ms  max={max(rpc_ms_list):.1f}ms"
    )
    print(f"Final mem:    {proc.memory_info().rss / 1e6:.0f}MB")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("video", nargs="?", default="video.mp4", help="Path to video file")
    parser.add_argument(
        "--mode",
        choices=["mono", "color"],
        default="mono",
        help="Rendering mode: mono (tap/damage grid) or color (AirCrush, default: mono)",
    )
    parser.add_argument(
        "--audio",
        default=None,
        metavar="FILE",
        help="Audio file (default: extracted from video via ffmpeg, or <video>.wav)",
    )
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        metavar="S",
        help="A/V sync offset in seconds: "
        "+S trims audio start (video leads), "
        "-S pads silence (audio leads)",
    )
    parser.add_argument("--width", type=int, default=16, help="Canvas width in lanes (default 16)")
    parser.add_argument("--fps", type=float, default=30.0, help="Target playback frame rate")
    parser.add_argument(
        "--tick-per-row", type=int, default=10, help="Tick spacing between pixel rows"
    )
    parser.add_argument(
        "--base-tick", type=int, default=0, help="Tick position of the canvas top row"
    )
    parser.add_argument(
        "--dark-threshold",
        type=int,
        default=_color.DARK_L_THRESHOLD,
        metavar="L",
        help="[color mode] LAB L cutoff (0-255): "
        "pixels below this become BLACK (default %(default)s)",
    )
    args = parser.parse_args()

    if args.mode == "mono":
        frame_to_notes: FrameConverter = _mono.frame_to_notes
    else:
        frame_to_notes = functools.partial(
            _color.frame_to_notes, dark_threshold=args.dark_threshold
        )

    stream(
        args.video,
        frame_to_notes,
        audio_path=args.audio,
        offset=args.offset,
        width=args.width,
        fps=args.fps,
        tick_per_row=args.tick_per_row,
        base_tick=args.base_tick,
    )


if __name__ == "__main__":
    main()
