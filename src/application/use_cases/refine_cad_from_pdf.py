"""Refine CAD from PDF use case with feedback loop."""

from dataclasses import dataclass
from pathlib import Path

from application.workflow.graph_builder import create_refinement_graph
from application.workflow.workflow_state import RefinementState
from domain.repositories.few_shot_repository import FewShotRepository
from domain.services.cad_evaluator import CadEvaluatorService
from domain.services.cad_generator import CadGeneratorService
from domain.services.cad_renderer import CadRendererService


@dataclass
class RefinementRequest:
    """Request for refinement workflow."""

    pdf_path: Path
    output_dir: Path
    score_threshold: float = 0.8
    max_iterations: int = 10
    num_few_shot_examples: int = 5
    temperature: float = 0.5
    enable_feedback_loop: bool = True  # Set to False for 1-shot generation


@dataclass
class RefinementResult:
    """Result of refinement workflow."""

    final_code: str | None
    final_score: float
    total_iterations: int
    output_dir: Path
    step_path: Path | None
    code_path: Path | None
    error: str | None


class RefineCadFromPdfUseCase:
    """
    Use case for refining CAD code from PDF using feedback loop.

    This workflow:
    1. Generates initial CAD code from technical drawing
    2. Renders the CAD model
    3. Evaluates the render against the input drawing using LLM
    4. Refines the code based on feedback
    5. Repeats until score threshold is met or max iterations reached
    """

    def __init__(
        self,
        cad_generator: CadGeneratorService,
        cad_renderer: CadRendererService,
        cad_evaluator: CadEvaluatorService,
        few_shot_repository: FewShotRepository,
    ) -> None:
        """
        Initialize the use case.

        Args:
            cad_generator: Service for generating CAD code.
            cad_renderer: Service for rendering CAD models.
            cad_evaluator: Service for evaluating CAD models.
            few_shot_repository: Repository for few-shot examples.
        """
        self._cad_generator = cad_generator
        self._cad_renderer = cad_renderer
        self._cad_evaluator = cad_evaluator
        self._few_shot_repository = few_shot_repository

    async def execute(self, request: RefinementRequest) -> RefinementResult:
        """
        Execute the refinement workflow.

        Args:
            request: Refinement request with parameters.

        Returns:
            RefinementResult with final code and metrics.
        """
        # Create output directory
        request.output_dir.mkdir(parents=True, exist_ok=True)

        # Get model name from PDF filename
        model_name = request.pdf_path.stem

        # Build config
        config = {
            "score_threshold": request.score_threshold,
            "max_iterations": request.max_iterations,
            "num_few_shot_examples": request.num_few_shot_examples,
            "temperature": request.temperature,
            "enable_feedback_loop": request.enable_feedback_loop,
        }

        # Create initial state
        initial_state: RefinementState = {
            "input_pdf_path": str(request.pdf_path),
            "model_name": model_name,
            "config": config,
            "output_dir": str(request.output_dir),
            "current_iteration": 0,
            "current_code": "",
            "current_multiview_paths": [],
            "current_score": 0.0,
            "current_feedback": "",
            "iterations_history": [],
            "final_code": None,
            "error": None,
            "status": "starting",
        }

        # Create and run workflow
        graph = create_refinement_graph(
            cad_generator=self._cad_generator,
            cad_renderer=self._cad_renderer,
            cad_evaluator=self._cad_evaluator,
            few_shot_repository=self._few_shot_repository,
        )

        final_state = await graph.ainvoke(initial_state)

        # Build result
        iterations_history = final_state.get("iterations_history", [])
        total_iterations = len(iterations_history)

        step_path = request.output_dir / f"{model_name}.step"
        code_path = request.output_dir / f"{model_name}.py"

        return RefinementResult(
            final_code=final_state.get("final_code"),
            final_score=final_state.get("current_score", 0.0),
            total_iterations=total_iterations,
            output_dir=request.output_dir,
            step_path=step_path if step_path.exists() else None,
            code_path=code_path if code_path.exists() else None,
            error=final_state.get("error"),
        )
