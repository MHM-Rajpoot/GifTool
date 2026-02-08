# gif-tool

CLI and library to convert videos or a folder of images into GIFs, with sensible defaults and safeguards.

**Installation**
 - **Install**: `pip install .`

**CLI Usage**

 - Convert a video to GIF:

	 ```bash
	 python main.py input.mp4 -o output.gif --fps 10 --verbose
	 ```

 - Convert a folder of images to GIF (use `--per-image-duration` to set seconds per image):

	 ```bash
	 python main.py path/to/images_folder -o output.gif --per-image-duration 2.5
	 ```

**Important CLI flags**

 - **`-o, --output`**: Output GIF path (defaults to input path with .gif).
 - **`--fps`**: Override output GIF fps when converting from video (default: auto / capped).
 - **`--max-width`**: Max output frame width in pixels (default: 480).
 - **`--max-duration`**: Reject input videos longer than this many seconds (default: 60).
 - **`--max-size-mb`**: Reject large input files (default: 25 MB).
 - **`--per-image-duration`**: Seconds to display each image when input is a folder. This is the single timing option for image-folder inputs (default: `1.0`).
 - **`--verbose`**: Enable verbose logging.

**Notes**

 - When the input is a directory, `gif-tool` collects common image file types (`.jpg`, `.png`, `.bmp`, `.webp`, `.tiff`, `.gif`) and resizes them to a common frame size (respecting `--max-width`) before writing a GIF where each frame uses the specified per-image duration.
 - For video inputs, the tool reads frames at the source (or overridden) FPS, trims to `--max-duration` if necessary, and writes a GIF.

**Library Usage**

 - Programmatic call (new signature — `per_image_duration` is used for folder inputs):

	 ```python
	 from pathlib import Path
	 from gif_tool import convert_to_gif, GifSettings

	 settings = GifSettings(max_size_mb=25, max_length_sec=60, max_width=480)

	 # Video -> GIF
	 convert_to_gif(Path("input.mp4"), Path("output.gif"), override_fps=10.0, settings=settings)

	 # Folder of images -> GIF, each image shown for 2.5 seconds
	 convert_to_gif(Path("images_folder"), Path("output.gif"), settings=settings, per_image_duration=2.5)
	 ```

**Dependencies**

 - `imageio`, `Pillow` (used for final GIF write for image folders), and `opencv-python` (for video reading and resizing).

**Try it**

 - Convert images in `imgs/` with 3s per image:

	 ```bash
	 python main.py imgs -o imgs_output.gif --per-image-duration 3
	 ```

 - Convert a video and limit size/length:

	 ```bash
	 python main.py video.mp4 -o video.gif --fps 10 --max-size-mb 50 --max-duration 30
	 ```

See `gif_tool/cli.py` and `gif_tool/converter.py` for implementation details.
