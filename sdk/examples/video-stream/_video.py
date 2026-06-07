"""Shared video frame decoding and audio loading."""

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf


def load_frames(
    video_path: str, target_width: int, target_fps: float
) -> tuple[float, list[np.ndarray]]:
    """Decode a video, resample to *target_fps*, resize to *target_width*.

    Returns ``(actual_fps, frames)`` where each frame is a BGR uint8 array of
    shape ``(H, W, 3)``.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise OSError(f"Cannot open video: {video_path}")

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_height = int(target_width / (orig_w / orig_h))

    print(
        f"  {orig_w}x{orig_h} -> {target_width}x{target_height}"
        f"  {original_fps:.2f}fps -> {target_fps}fps"
        f"  {total_frames} source frames"
    )

    frames: list[np.ndarray] = []
    accumulator = 0.0
    processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        accumulator += target_fps / original_fps
        processed += 1
        if accumulator >= 1.0:
            resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            frames.append(resized)
            accumulator -= 1.0
        if processed % 500 == 0:
            print(f"  {processed}/{total_frames} -> {len(frames)} frames")

    cap.release()
    print(f"  Done: {len(frames)} frames")
    return target_fps, frames


def load_audio(
    audio_path: str | None, video_path: str, offset: float
) -> tuple[np.ndarray, int] | None:
    """Load audio, applying *offset* for A/V sync.

    Resolution order:
    1. ``--audio`` explicit path
    2. ffmpeg extraction from the video (if ffmpeg is on PATH)
    3. ``<video>.wav`` sidecar file

    A positive *offset* trims the audio start (video leads).
    A negative *offset* pads silence before audio (audio leads).
    Returns ``None`` when no audio source is found.
    """
    source: str | None = None
    data: np.ndarray | None = None
    samplerate = 44100

    if audio_path is not None:
        data, samplerate = sf.read(audio_path, dtype="float32")
        source = audio_path
    else:
        extracted = _extract_via_ffmpeg(video_path)
        if extracted is not None:
            data, samplerate = extracted
            source = video_path
        else:
            wav = Path(video_path).with_suffix(".wav")
            if wav.exists():
                data, samplerate = sf.read(str(wav), dtype="float32")
                source = str(wav)

    if data is None or source is None:
        print("Audio: no source found, running silent")
        return None

    data = _apply_offset(data, samplerate, offset)
    print(
        f"Audio: {source!r}  {samplerate}Hz  {len(data) / samplerate:.1f}s  offset={offset:+.3f}s"
    )
    return data, samplerate


def _extract_via_ffmpeg(video_path: str) -> tuple[np.ndarray, int] | None:
    if shutil.which("ffmpeg") is None:
        return None
    samplerate = 44100
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",
            "-ar",
            str(samplerate),
            "-ac",
            "2",
            "-f",
            "f32le",
            "pipe:1",
            "-loglevel",
            "error",
        ],
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout:
        if result.stderr:
            print(f"Audio: ffmpeg: {result.stderr.decode(errors='replace').strip()}")
        return None
    data = np.frombuffer(result.stdout, dtype=np.float32).reshape(-1, 2)
    return data, samplerate


def _apply_offset(data: np.ndarray, samplerate: int, offset: float) -> np.ndarray:
    if offset > 0:
        skip = min(int(offset * samplerate), len(data))
        return data[skip:]
    if offset < 0:
        silence_shape = (int(abs(offset) * samplerate), *data.shape[1:])
        return np.concatenate([np.zeros(silence_shape, dtype=data.dtype), data])
    return data
