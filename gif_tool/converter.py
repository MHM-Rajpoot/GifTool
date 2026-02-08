from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import imageio
from PIL import Image as PILImage
import numpy as np


@dataclass
class GifSettings:
    """Configuration for GIF conversion."""

    max_size_mb: int = 25
    max_length_sec: int = 60
    max_width: int = 480
    default_fps: float = 10.0
    max_fps: float = 10.0


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    duration: float | None


def validate_input(path: Path, settings: GifSettings) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    # If given a file, validate size. If a directory, ensure it contains images.
    if path.is_file():
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > settings.max_size_mb:
            raise ValueError(
                f"Input file is {size_mb:.2f} MB (> {settings.max_size_mb} MB limit)"
            )


def _collect_image_files(folder: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif", ".gif"}
    imgs = sorted([p for p in folder.iterdir() if p.suffix.lower() in exts and p.is_file()])
    return imgs


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
    per_image_duration: float | None = None,
) -> Path:
    cfg = settings or GifSettings()
    # If input is a directory of images, create GIF from images.
    if input_path.is_dir():
        imgs = _collect_image_files(input_path)
        if not imgs:
            raise ValueError(f"No image files found in folder: {input_path}")

        # Use provided per-image duration (CLI default is 1.0s).
        if per_image_duration is None:
            per_image_duration = 1.0

        frames: list[np.ndarray] = []
        target_h = target_w = None

        for p in imgs:
            img = imageio.imread(p)
            if img.ndim == 2:
                img = np.stack([img, img, img], axis=2)
            if img.shape[2] == 4:
                img = img[:, :, :3]

            h, w = img.shape[:2]
            if w > cfg.max_width:
                scale = cfg.max_width / w
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                h, w = img.shape[:2]

            if target_h is None:
                target_h, target_w = h, w
            else:
                if (h, w) != (target_h, target_w):
                    img = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)

            frames.append(img)

        logging.info(
            "Collected %d images, per-image duration=%.3fs, writing GIF to %s",
            len(frames),
            per_image_duration,
            output_path,
        )
        # Write using Pillow to ensure per-frame durations are stored (ms).
        pil_frames = [PILImage.fromarray(f) for f in frames]
        durations_ms = [int(per_image_duration * 1000)] * len(pil_frames)
        first, rest = pil_frames[0], pil_frames[1:]
        first.save(
            output_path,
            save_all=True,
            append_images=rest,
            duration=durations_ms,
            loop=0,
            format="GIF",
        )
        return output_path

    # Otherwise treat input as a video file
    validate_input(input_path, cfg)

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

        # For videos, keep the full video length (up to max_length_sec); do not use a target duration.
        clip_duration = min(meta.duration, cfg.max_length_sec) if meta.duration else cfg.max_length_sec
        logging.info("Processing video at %.1f fps for %.1f s", fps, clip_duration)
        frames, frame_duration = read_frames(cap, fps, clip_duration, cfg)
        logging.info("Extracted %d frames, writing GIF to %s", len(frames), output_path)

        imageio.mimsave(output_path, frames, format="GIF", duration=frame_duration, loop=0)
    finally:
        cap.release()

    return output_path
