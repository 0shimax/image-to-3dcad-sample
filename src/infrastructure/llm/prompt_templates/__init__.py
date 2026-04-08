"""Prompt templates."""

from infrastructure.llm.prompt_templates.build123d_api_reference import (
    BUILD123D_API_REFERENCE,
)
from infrastructure.llm.prompt_templates.cad_generation import (
    BUILD123D_SYSTEM_PROMPT,
)
from infrastructure.llm.prompt_templates.technical_drawing import (
    TECHNICAL_DRAWING_SYSTEM_PROMPT,
    build_technical_drawing_with_examples_prompt,
)

__all__ = [
    "BUILD123D_API_REFERENCE",
    "BUILD123D_SYSTEM_PROMPT",
    "build_technical_drawing_with_examples_prompt",
    "TECHNICAL_DRAWING_SYSTEM_PROMPT",
]
