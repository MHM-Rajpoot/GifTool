from .converter import (
    BatchConversionError,
    BatchConversionFailure,
    GifSettings,
    convert_to_gif,
    convert_video_folder_to_gifs,
    derive_batch_output_dir,
    derive_output_path,
)

__all__ = [
    "BatchConversionError",
    "BatchConversionFailure",
    "GifSettings",
    "convert_to_gif",
    "convert_video_folder_to_gifs",
    "derive_batch_output_dir",
    "derive_output_path",
]
