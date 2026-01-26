# gif-tool

CLI and library to convert videos to GIFs with size and duration safeguards.

## Installation

```bash
pip install .
```

## CLI

```bash
gif-tool input.mp4 -o output.gif --fps 10 --verbose
```

## Library

```python
from pathlib import Path
from gif_tool import convert_to_gif, GifSettings

convert_to_gif(Path("input.mp4"), Path("output.gif"), override_fps=10.0, settings=GifSettings())
```
