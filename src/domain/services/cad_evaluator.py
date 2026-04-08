"""CAD evaluator service interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaluationResult:
    """
    Result of CAD evaluation.

    Attributes:
        score: Similarity score between 0.0 and 1.0.
        feedback: Detailed feedback for improvement.
        reasoning: Chain-of-thought reasoning for the evaluation.
    """

    score: float
    feedback: str
    reasoning: str


class CadEvaluatorService(ABC):
    """
    Abstract interface for CAD evaluation service.

    Compares rendered CAD images with input technical drawing
    and provides a similarity score with feedback.
    """

    @abstractmethod
    async def evaluate(
        self,
        input_pdf_path: Path,
        rendered_image_paths: list[Path],
        cad_code: str,
    ) -> EvaluationResult:
        """
        Evaluate rendered CAD model against input technical drawing.

        Args:
            input_pdf_path: Path to the input technical drawing PDF.
            rendered_image_paths: Paths to rendered multiview images.
            cad_code: Current CAD code for context.

        Returns:
            EvaluationResult with score, feedback, and reasoning.
        """
        pass
