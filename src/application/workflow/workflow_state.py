"""Workflow state definitions."""

from typing import TypedDict, Annotated
from operator import add


class IterationState(TypedDict, total=False):
    """State for a single iteration in refinement workflow."""

    iteration: int
    cad_code: str
    multiview_paths: list[str]
    score: float
    feedback: str
    error: str | None


class RefinementState(TypedDict, total=False):
    """
    Main workflow state for feedback-loop refinement.

    Attributes:
        input_pdf_path: Path to input technical drawing PDF.
        model_name: Name of the model being generated.
        config: Refinement configuration.
        output_dir: Output directory path.
        current_iteration: Current iteration number.
        current_code: Current CAD code.
        current_multiview_paths: Paths to current rendered images.
        current_score: Current evaluation score.
        current_feedback: Current feedback from evaluator.
        iterations_history: History of all iterations.
        final_code: Final CAD code that passed threshold.
        error: Error message if any.
        status: Current workflow status.
    """

    input_pdf_path: str
    model_name: str
    config: dict
    output_dir: str
    current_iteration: int
    current_code: str
    current_multiview_paths: list[str]
    current_score: float
    current_feedback: str
    iterations_history: Annotated[list[IterationState], add]
    final_code: str | None
    error: str | None
    status: str
