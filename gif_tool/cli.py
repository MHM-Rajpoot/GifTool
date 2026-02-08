from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .converter import GifSettings, convert_to_gif, derive_output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a video or a directory of images to a GIF with sensible defaults.",
    )
    parser.add_argument("input", help="Path to the source video file or directory of images")
    parser.add_argument(
        "-o",
        "--output",
        help="Output GIF path (default: alongside input with .gif extension)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Override output GIF fps (default: min(source fps, 10))",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=480,
        help="Max output frame width (pixels); larger frames are downscaled",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=60,
        help="Reject videos longer than this many seconds",
    )
    parser.add_argument(
        "--per-image-duration",
        type=float,
        default=1.0,
        help="Seconds to display each image when input is a folder (default: 1.0)",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=25,
        help="Reject input files larger than this many MB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    settings = GifSettings(
        max_size_mb=args.max_size_mb,
        max_length_sec=args.max_duration,
        max_width=args.max_width,
    )
    per_image_duration = args.per_image_duration

    input_path = Path(args.input)
    output_path = derive_output_path(input_path, args.output)

    result_path = convert_to_gif(input_path, output_path, args.fps, settings, per_image_duration)
    print(f"GIF written to {result_path}")


if __name__ == "__main__":
    main()
