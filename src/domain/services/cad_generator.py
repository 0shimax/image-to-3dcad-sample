"""CAD generator service interface."""

from abc import ABC, abstractmethod

from domain.value_objects.cad_code import CadCode
from domain.value_objects.technical_drawing_image import (
    TechnicalDrawingImage,
)


class CadGeneratorService(ABC):
    """Abstract service for generating CAD code."""

    @abstractmethod
    async def generate_from_technical_drawing(
        self,
        drawing: TechnicalDrawingImage,
        num_candidates: int,
        num_few_shot_examples: int,
        temperature: float,
    ) -> list[CadCode]:
        """
        Generate CAD code from technical drawing images.

        Args:
            drawing: Technical drawing images converted from PDF.
            num_candidates: Number of CAD code candidates.
            num_few_shot_examples: Number of few-shot examples.
            temperature: LLM temperature for generation.

        Returns:
            List of generated CAD codes.
        """
        pass

    @abstractmethod
    async def fix_code_error(
        self,
        cad_code: CadCode,
        error_message: str,
        temperature: float,
    ) -> CadCode:
        """
        Fix errors in CAD code based on error message.

        Args:
            cad_code: CAD code with errors.
            error_message: Error message from code execution.
            temperature: LLM temperature for generation.

        Returns:
            Fixed CAD code.
        """
        pass
