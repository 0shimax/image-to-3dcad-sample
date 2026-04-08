"""CAD code value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CadCode:
    """
    Value object representing CAD code (build123d Python code).

    Attributes:
        code: The Python code string for build123d CAD model.
    """

    code: str

    def __post_init__(self) -> None:
        """Validate the CAD code."""
        if not self.code or not self.code.strip():
            raise ValueError("CAD code cannot be empty")

    def to_dict(self) -> dict:
        """
        Serialize to dictionary.

        Returns:
            Dictionary representation of the CAD code.
        """
        return {"code": self.code}

    @classmethod
    def from_dict(cls, data: dict) -> "CadCode":
        """
        Create CadCode from dictionary.

        Args:
            data: Dictionary containing 'code' key.

        Returns:
            CadCode instance.
        """
        return cls(code=data["code"])
