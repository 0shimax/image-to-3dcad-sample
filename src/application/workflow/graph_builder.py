"""Graph builder for refinement workflow."""

from functools import partial
from typing import Literal

from langgraph.graph import END, StateGraph

from application.workflow.nodes.refinement_nodes import (
    evaluate_refinement_node,
    finalize_refinement_node,
    initialize_refinement_node,
    refine_code_node,
    render_refinement_node,
)
from application.workflow.workflow_state import RefinementState
from domain.repositories.few_shot_repository import FewShotRepository
from domain.services.cad_evaluator import CadEvaluatorService
from domain.services.cad_generator import CadGeneratorService
from domain.services.cad_renderer import CadRendererService


def create_refinement_graph(
    cad_generator: CadGeneratorService,
    cad_renderer: CadRendererService,
    cad_evaluator: CadEvaluatorService,
    few_shot_repository: FewShotRepository,
) -> StateGraph:
    """
    Create the LangGraph workflow for one-shot CAD generation.

    Args:
        cad_generator: Service for generating CAD code.
        cad_renderer: Service for rendering CAD models.
        cad_evaluator: Service for evaluating CAD models.
        few_shot_repository: Repository for few-shot examples.

    Returns:
        Compiled StateGraph for refinement workflow.
    """
    workflow = StateGraph(RefinementState)

    workflow.add_node(
        "initialize",
        partial(
            initialize_refinement_node,
            cad_generator=cad_generator,
            few_shot_repository=few_shot_repository,
        ),
    )
    workflow.add_node(
        "render",
        partial(
            render_refinement_node,
            cad_renderer=cad_renderer,
        ),
    )
    workflow.add_node(
        "evaluate",
        partial(
            evaluate_refinement_node,
            cad_evaluator=cad_evaluator,
        ),
    )
    workflow.add_node(
        "refine",
        partial(
            refine_code_node,
            cad_generator=cad_generator,
        ),
    )
    workflow.add_node(
        "finalize",
        partial(
            finalize_refinement_node,
            cad_renderer=cad_renderer,
        ),
    )

    workflow.set_entry_point("initialize")

    workflow.add_edge("initialize", "render")
    workflow.add_edge("render", "evaluate")

    def should_continue(
        state: RefinementState,
    ) -> Literal["refine", "finalize"]:
        """Determine if refinement should continue."""
        config = state["config"]
        current_score = state.get("current_score", 0.0)
        current_iteration = state.get(
            "current_iteration", 0
        )

        score_threshold = config.get("score_threshold", 0.8)
        max_iterations = config.get("max_iterations", 10)
        enable_feedback_loop = config.get(
            "enable_feedback_loop", True
        )

        if not enable_feedback_loop:
            return "finalize"

        if max_iterations <= 0:
            return "finalize"

        if current_score >= score_threshold:
            return "finalize"

        if current_iteration >= max_iterations:
            return "finalize"

        return "refine"

    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "refine": "refine",
            "finalize": "finalize",
        },
    )

    workflow.add_edge("refine", "render")
    workflow.add_edge("finalize", END)

    return workflow.compile()
