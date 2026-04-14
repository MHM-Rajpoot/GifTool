from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from .converter import (
    BatchConversionError,
    GifSettings,
    convert_to_gif,
    convert_video_folder_to_gifs,
    derive_batch_output_dir,
    derive_output_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a video, a directory of images, or a folder of videos to GIFs.",
    )
    parser.add_argument(
        "input",
        help="Path to the source video file, directory of images, or folder of videos with --batch-videos",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output GIF path (default: alongside input with .gif extension)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch video conversion (default: sibling 'gif' folder)",
    )
    parser.add_argument(
        "--batch-videos",
        action="store_true",
        help="Convert all supported video files in the input folder into GIFs",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Target output GIF fps before automatic frame-budget reduction",
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
        "--max-frames",
        type=int,
        default=150,
        help="Approximate maximum frames per video GIF before fps is reduced automatically",
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
        max_frames=args.max_frames,
    )
    per_image_duration = args.per_image_duration

    input_path = Path(args.input)

    if args.batch_videos:
        if args.output:
            parser.error("--output cannot be used with --batch-videos; use --output-dir instead")
        if not input_path.is_dir():
            parser.error("--batch-videos requires the input path to be a directory")

        output_dir = derive_batch_output_dir(input_path, args.output_dir)
        try:
            result_paths = convert_video_folder_to_gifs(
                input_path,
                output_dir,
                override_fps=args.fps,
                settings=settings,
            )
        except BatchConversionError as exc:
            for result_path in exc.successes:
                print(f"GIF written to {result_path}")
            print(
                f"Batch finished with {len(exc.failures)} failure(s).",
                file=sys.stderr,
            )
            for failure in exc.failures:
                print(
                    f"FAILED: {failure.input_path} -> {failure.error}",
                    file=sys.stderr,
                )
            raise SystemExit(1)
        except (FileNotFoundError, ValueError) as exc:
            parser.exit(1, f"ERROR: {exc}\n")

        for result_path in result_paths:
            print(f"GIF written to {result_path}")
        print(f"Converted {len(result_paths)} video(s) into {output_dir}")
        return

    if args.output_dir:
        parser.error("--output-dir can only be used with --batch-videos")

    output_path = derive_output_path(input_path, args.output)
    try:
        result_path = convert_to_gif(input_path, output_path, args.fps, settings, per_image_duration)
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"GIF written to {result_path}")


if __name__ == "__main__":
    main()
