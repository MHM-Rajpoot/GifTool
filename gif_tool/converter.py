from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import imageio
import numpy as np


@dataclass
class GifSettings:
    """Configuration for GIF conversion."""

    max_size_mb: int = 25
    max_length_sec: int = 60
    target_gif_sec: int = 15
    max_width: int = 480
    default_fps: float = 10.0
    max_fps: float = 10.0


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    duration: float | None


def validate_file(path: Path, settings: GifSettings) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_size_mb:
        raise ValueError(
            f"Input file is {size_mb:.2f} MB (> {settings.max_size_mb} MB limit)"
        )


def derive_output_path(input_path: Path, output: str | None) -> Path:
    if output:
        out_path = Path(output)
        return out_path if out_path.suffix.lower() == ".gif" else out_path.with_suffix(".gif")
    return input_path.with_suffix(".gif")


def probe_video(cap: cv2.VideoCapture) -> VideoMeta:
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = None
    if fps > 0 and frame_count > 0:
        duration = frame_count / fps
    return VideoMeta(fps=fps, frame_count=frame_count, duration=duration)


def read_frames(
    cap: cv2.VideoCapture,
    fps: float,
    clip_duration: float,
    settings: GifSettings,
) -> Tuple[List[np.ndarray], float]:
    frames: List[np.ndarray] = []
    target_frames = max(1, int(round(clip_duration * fps)))  # frames = t * fps
    frame_duration = 1.0 / fps if fps > 0 else 0.1

    while len(frames) < target_frames:
        ok, frame = cap.read()
        if not ok:
            break
        pos_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if pos_sec > settings.max_length_sec:
            raise ValueError("Video exceeds length limit")

        # Downscale wide frames to keep GIF size reasonable.
        h, w = frame.shape[:2]
        if w > settings.max_width:
            scale = settings.max_width / w
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(rgb)

    if not frames:
        raise ValueError("No frames could be read from the video")

    return frames, frame_duration


def convert_to_gif(
    input_path: Path,
    output_path: Path,
    override_fps: float | None = None,
    settings: GifSettings | None = None,
) -> Path:
    cfg = settings or GifSettings()
    validate_file(input_path, cfg)

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")

    try:
        meta = probe_video(cap)
        fps = meta.fps if meta.fps > 0 else cfg.default_fps
        if override_fps is not None and override_fps > 0:
            fps = override_fps
        fps = min(fps, cfg.max_fps)

        if meta.duration is not None and meta.duration > cfg.max_length_sec:
            raise ValueError(
                f"Video is {meta.duration:.2f}s (> {cfg.max_length_sec}s limit)"
            )

        clip_duration = min(cfg.target_gif_sec, meta.duration) if meta.duration else cfg.target_gif_sec
        logging.info("Processing video at %.1f fps for %.1f s", fps, clip_duration)
        frames, frame_duration = read_frames(cap, fps, clip_duration, cfg)
        logging.info("Extracted %d frames, writing GIF to %s", len(frames), output_path)

        imageio.mimsave(output_path, frames, format="GIF", duration=frame_duration, loop=0)
    finally:
        cap.release()

    return output_path
