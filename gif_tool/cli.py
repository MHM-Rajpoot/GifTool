from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .converter import GifSettings, convert_to_gif, derive_output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a video to a GIF with basic validations and sensible defaults.",
    )
    parser.add_argument("input", help="Path to the source video file")
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
        "--target-duration",
        type=int,
        default=15,
        help="Target GIF duration in seconds (will trim if video is longer)",
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
        target_gif_sec=args.target_duration,
        max_width=args.max_width,
    )

    input_path = Path(args.input)
    output_path = derive_output_path(input_path, args.output)

    result_path = convert_to_gif(input_path, output_path, args.fps, settings)
    print(f"GIF written to {result_path}")


if __name__ == "__main__":
    main()
