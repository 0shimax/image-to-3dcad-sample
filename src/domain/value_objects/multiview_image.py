"""Multiview image value object."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MultiviewImage:
    """
    Value object representing a multiview rendering of a CAD model.

    Attributes:
        front_view: Path to front view image.
        top_view: Path to top view image.
        side_view: Path to side view image.
        isometric_view: Path to isometric view image.
    """

    front_view: Path
    top_view: Path
    side_view: Path
    isometric_view: Path

    def __post_init__(self) -> None:
        """Validate that all paths are provided."""
        for field_name in ["front_view", "top_view", "side_view", "isometric_view"]:
            path = getattr(self, field_name)
            if path is None:
                raise ValueError(f"{field_name} cannot be None")

    def get_all_paths(self) -> list[Path]:
        """
        Get all view paths as a list.

        Returns:
            List of all view paths.
        """
        return [
            self.front_view,
            self.top_view,
            self.side_view,
            self.isometric_view,
        ]

    def to_dict(self) -> dict:
        """
        Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "front_view": str(self.front_view),
            "top_view": str(self.top_view),
            "side_view": str(self.side_view),
            "isometric_view": str(self.isometric_view),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiviewImage":
        """
        Create MultiviewImage from dictionary.

        Args:
            data: Dictionary containing view paths.

        Returns:
            MultiviewImage instance.
        """
        return cls(
            front_view=Path(data["front_view"]),
            top_view=Path(data["top_view"]),
            side_view=Path(data["side_view"]),
            isometric_view=Path(data["isometric_view"]),
        )
