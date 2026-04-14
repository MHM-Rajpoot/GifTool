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
    max_frames: int = 150


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    duration: float | None


@dataclass
class BatchConversionFailure:
    input_path: Path
    error: str


class BatchConversionError(RuntimeError):
    def __init__(
        self,
        successes: list[Path],
        failures: list[BatchConversionFailure],
    ) -> None:
        self.successes = successes
        self.failures = failures
        super().__init__(
            f"Converted {len(successes)} video(s) with {len(failures)} failure(s)"
        )


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


def _collect_video_files(folder: Path) -> list[Path]:
    exts = {".mov", ".mp4", ".avi", ".mkv", ".webm", ".m4v"}
    videos = sorted(
        [p for p in folder.iterdir() if p.suffix.lower() in exts and p.is_file()]
    )
    return videos


def derive_output_path(input_path: Path, output: str | None) -> Path:
    if output:
        out_path = Path(output)
        return out_path if out_path.suffix.lower() == ".gif" else out_path.with_suffix(".gif")
    return input_path.with_suffix(".gif")


def derive_batch_output_dir(input_dir: Path, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    return input_dir.parent / "gif"


def probe_video(cap: cv2.VideoCapture) -> VideoMeta:
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = None
    if fps > 0 and frame_count > 0:
        duration = frame_count / fps
    return VideoMeta(fps=fps, frame_count=frame_count, duration=duration)


def resolve_output_fps(
    meta: VideoMeta,
    settings: GifSettings,
    override_fps: float | None = None,
) -> float:
    fps = meta.fps if meta.fps > 0 else settings.default_fps
    if override_fps is not None and override_fps > 0:
        fps = override_fps
    fps = min(fps, settings.max_fps)

    if meta.duration and meta.duration > 0 and settings.max_frames > 0:
        budget_fps = settings.max_frames / meta.duration
        min_useful_fps = 1.0 / meta.duration
        auto_fps = max(min_useful_fps, budget_fps)
        if auto_fps < fps:
            logging.info(
                "Reducing fps from %.2f to %.2f to stay within ~%d frames for %.2fs video",
                fps,
                auto_fps,
                settings.max_frames,
                meta.duration,
            )
            fps = auto_fps

    return fps


def read_frames(
    cap: cv2.VideoCapture,
    fps: float,
    clip_duration: float,
    settings: GifSettings,
) -> Tuple[List[np.ndarray], float]:
    frames: List[np.ndarray] = []
    frame_duration = 1.0 / fps if fps > 0 else 0.1
    next_sample_time = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        pos_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if pos_sec > settings.max_length_sec:
            raise ValueError("Video exceeds length limit")
        if clip_duration > 0 and pos_sec > clip_duration:
            break
        if frames and pos_sec + 1e-9 < next_sample_time:
            continue

        # Downscale wide frames to keep GIF size reasonable.
        h, w = frame.shape[:2]
        if w > settings.max_width:
            scale = settings.max_width / w
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(rgb)
        next_sample_time += frame_duration
        if clip_duration > 0 and next_sample_time > clip_duration:
            break

    if not frames:
        raise ValueError("No frames could be read from the video")

    return frames, clip_duration / len(frames) if clip_duration > 0 else frame_duration


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

        if meta.duration is not None and meta.duration > cfg.max_length_sec:
            raise ValueError(
                f"Video is {meta.duration:.2f}s (> {cfg.max_length_sec}s limit)"
            )

        # For videos, keep the full video length (up to max_length_sec); do not use a target duration.
        clip_duration = min(meta.duration, cfg.max_length_sec) if meta.duration else cfg.max_length_sec
        fps = resolve_output_fps(meta, cfg, override_fps)
        logging.info("Processing video at %.1f fps for %.1f s", fps, clip_duration)
        frames, frame_duration = read_frames(cap, fps, clip_duration, cfg)
        logging.info("Extracted %d frames, writing GIF to %s", len(frames), output_path)

        imageio.mimsave(output_path, frames, format="GIF", duration=frame_duration, loop=0)
    finally:
        cap.release()

    return output_path


def convert_video_folder_to_gifs(
    input_dir: Path,
    output_dir: Path,
    override_fps: float | None = None,
    settings: GifSettings | None = None,
) -> list[Path]:
    cfg = settings or GifSettings()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")
    if not input_dir.is_dir():
        raise ValueError(f"Batch video input must be a directory: {input_dir}")

    videos = _collect_video_files(input_dir)
    if not videos:
        raise ValueError(f"No video files found in folder: {input_dir}")

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"Output path must be a directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    converted: list[Path] = []
    failures: list[BatchConversionFailure] = []

    for video_path in videos:
        gif_path = output_dir / f"{video_path.stem}.gif"
        try:
            logging.info("Converting %s -> %s", video_path, gif_path)
            converted.append(
                convert_to_gif(
                    video_path,
                    gif_path,
                    override_fps=override_fps,
                    settings=cfg,
                )
            )
        except Exception as exc:
            logging.error("Failed to convert %s: %s", video_path, exc)
            failures.append(BatchConversionFailure(video_path, str(exc)))

    if failures:
        raise BatchConversionError(converted, failures)

    return converted
