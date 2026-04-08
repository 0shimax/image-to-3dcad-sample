"""Few-shot examples repository interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class FewShotExample:
    """
    Value object representing a few-shot example.

    Attributes:
        description: Description of what the code creates.
        code: The build123d code example.
    """

    description: str
    code: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "description": self.description,
            "code": self.code,
        }


class FewShotRepository(ABC):
    """
    Abstract repository for few-shot examples.

    Provides access to build123d code examples for prompting.
    """

    @abstractmethod
    def get_random_examples(self, n: int) -> list[FewShotExample]:
        """
        Get n random few-shot examples.

        Args:
            n: Number of examples to return.

        Returns:
            List of FewShotExample objects.
        """
        pass

    @abstractmethod
    def get_all_examples(self) -> list[FewShotExample]:
        """
        Get all available few-shot examples.

        Returns:
            List of all FewShotExample objects.
        """
        pass

    @abstractmethod
    def add_example(self, example: FewShotExample) -> None:
        """
        Add a new few-shot example.

        Args:
            example: Example to add.
        """
        pass
