# gif-tool

CLI and library to convert videos, folders of images, or folders of videos into GIFs with sensible defaults and safeguards.

**Installation**

- Install: `pip install .`

**CLI Usage**

- Convert a single video to GIF:

  ```bash
  python main.py input.mp4 -o output.gif --fps 10 --verbose
  ```

- Convert a folder of images to one GIF:

  ```bash
  python main.py path/to/images_folder -o output.gif --per-image-duration 2.5
  ```

- Convert a folder of videos into a sibling `gif/` folder:

  ```bash
  python main.py videos --batch-videos --verbose
  ```

- Convert a folder of videos into a specific output directory:

  ```bash
  python main.py videos --batch-videos --output-dir gif --max-size-mb 100 --max-frames 150 --verbose
  ```

**Important CLI flags**

- `-o, --output`: Output GIF path for single video or image-folder conversion.
- `--batch-videos`: Convert all supported video files in the input folder into GIFs.
- `--output-dir`: Output directory for batch video conversion. Defaults to a sibling `gif/` folder.
- `--fps`: Target output GIF fps for video conversion before any automatic reduction.
- `--max-width`: Max output frame width in pixels (default: 480).
- `--max-duration`: Reject input videos longer than this many seconds (default: 60).
- `--max-frames`: Approximate maximum frames per video GIF. Longer videos automatically use a lower FPS to stay near this limit (default: 150).
- `--max-size-mb`: Reject input files larger than this many MB (default: 25).
- `--per-image-duration`: Seconds to display each image when input is a folder of images (default: `1.0`).
- `--verbose`: Enable verbose logging.

**Notes**

- Folder input keeps its original meaning by default: a directory is treated as an image sequence unless you pass `--batch-videos`.
- Supported batch video extensions are `.mov`, `.mp4`, `.avi`, `.mkv`, `.webm`, and `.m4v`.
- In batch mode, the tool creates the output directory if needed, overwrites existing GIFs with the same name, and continues processing even if one file fails.
- Video GIFs are sampled across the full clip instead of reading every source frame. By default the tool aims for up to `10` FPS, but longer videos automatically drop to a lower FPS so the GIF stays near `150` frames total.
- For image-folder inputs, `gif-tool` collects common image file types and resizes them to a common frame size before writing a GIF where each frame uses the specified per-image duration.

**Library Usage**

```python
from pathlib import Path

from gif_tool import (
    BatchConversionError,
    GifSettings,
    convert_to_gif,
    convert_video_folder_to_gifs,
    derive_batch_output_dir,
)

settings = GifSettings(max_size_mb=25, max_length_sec=60, max_width=480, max_frames=150)

# Video -> GIF
convert_to_gif(Path("input.mp4"), Path("output.gif"), override_fps=10.0, settings=settings)

# Folder of images -> GIF
convert_to_gif(Path("images_folder"), Path("output.gif"), settings=settings, per_image_duration=2.5)

# Folder of videos -> gif/
input_dir = Path("videos")
output_dir = derive_batch_output_dir(input_dir, None)

try:
    convert_video_folder_to_gifs(input_dir, output_dir, override_fps=10.0, settings=settings)
except BatchConversionError as exc:
    print(f"Converted {len(exc.successes)} GIFs before failures")
    for failure in exc.failures:
        print(f"{failure.input_path}: {failure.error}")
```

**Dependencies**

- `imageio`
- `numpy`
- `opencv-python`
- `Pillow`

**Try it**

- Convert the example images with a 3 second frame duration:

  ```bash
  python main.py imgs -o imgs_output.gif --per-image-duration 3
  ```

- Convert the example videos into `gif/`:

  ```bash
  python main.py videos --batch-videos --output-dir gif --max-size-mb 100 --max-frames 150 --verbose
  ```

See `gif_tool/cli.py` and `gif_tool/converter.py` for implementation details.
