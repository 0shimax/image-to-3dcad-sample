"""Technical drawing image value object."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TechnicalDrawingImage:
    """
    Represents a technical drawing converted from PDF.

    Attributes:
        model_name: Name identifier for the model.
        source_pdf_path: Path to the source PDF file.
        image_paths: Tuple of paths to converted images.
    """

    model_name: str
    source_pdf_path: Path
    image_paths: tuple[Path, ...] = ()
