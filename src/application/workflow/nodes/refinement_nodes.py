"""Refinement workflow nodes for feedback-loop CAD generation."""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from application.workflow.workflow_state import IterationState, RefinementState
from domain.value_objects.cad_code import CadCode
from domain.value_objects.technical_drawing_image import TechnicalDrawingImage

if TYPE_CHECKING:
    from domain.repositories.few_shot_repository import FewShotRepository
    from domain.services.cad_evaluator import CadEvaluatorService
    from domain.services.cad_generator import CadGeneratorService
    from domain.services.cad_renderer import CadRendererService


async def initialize_refinement_node(
    state: RefinementState,
    cad_generator: "CadGeneratorService",
    few_shot_repository: "FewShotRepository",
) -> dict:
    """
    Generate initial CAD code from technical drawing.

    Args:
        state: Current workflow state.
        cad_generator: Service for generating CAD code.
        few_shot_repository: Repository for few-shot examples.

    Returns:
        Updated state with initial CAD code.
    """
    print("[INIT] Generating initial CAD code...")

    pdf_path = Path(state["input_pdf_path"])
    model_name = state["model_name"]
    config = state["config"]

    # Create TechnicalDrawingImage for the generator
    # image_paths is empty tuple since we pass PDF directly
    drawing = TechnicalDrawingImage(
        model_name=model_name,
        source_pdf_path=pdf_path,
        image_paths=(),
    )

    cad_codes = await cad_generator.generate_from_technical_drawing(
        drawing=drawing,
        num_candidates=1,
        num_few_shot_examples=config.get("num_few_shot_examples", 5),
        temperature=config.get("temperature", 0.5),
    )

    if not cad_codes:
        return {
            "error": "Failed to generate initial CAD code",
            "status": "error",
        }

    initial_code = cad_codes[0].code
    print(f"[INIT] Initial code generated ({len(initial_code)} chars)")

    return {
        "current_code": initial_code,
        "current_iteration": 0,
        "status": "initialized",
    }


async def render_refinement_node(
    state: RefinementState,
    cad_renderer: "CadRendererService",
) -> dict:
    """
    Render the current CAD code to multiview images.

    Args:
        state: Current workflow state.
        cad_renderer: Service for rendering CAD models.

    Returns:
        Updated state with rendered image paths.
    """
    iteration = state["current_iteration"]
    print(f"[RENDER] Iteration {iteration}: Rendering CAD model...")

    output_dir = Path(state["output_dir"])
    iter_dir = output_dir / f"iteration_{iteration}"
    iter_dir.mkdir(parents=True, exist_ok=True)

    cad_code = CadCode(code=state["current_code"])

    try:
        multiview_image = await cad_renderer.render(
            cad_code=cad_code,
            output_dir=iter_dir,
            individual_id=f"iter_{iteration}",
        )

        image_paths = [str(p) for p in multiview_image.get_all_paths()]
        print(f"[RENDER] Rendered {len(image_paths)} views")

        return {
            "current_multiview_paths": image_paths,
            "status": "rendered",
        }

    except Exception as e:
        print(f"[RENDER] Error: {e}")
        return {
            "current_multiview_paths": [],
            "error": f"Render failed: {str(e)}",
            "status": "render_error",
        }


async def evaluate_refinement_node(
    state: RefinementState,
    cad_evaluator: "CadEvaluatorService",
) -> dict:
    """
    Evaluate the rendered model against the input drawing.

    Args:
        state: Current workflow state.
        cad_evaluator: Service for evaluating CAD models.

    Returns:
        Updated state with evaluation score and feedback.
    """
    iteration = state["current_iteration"]
    print(f"[EVAL] Iteration {iteration}: Evaluating model...")

    # Check for render error
    if state.get("status") == "render_error":
        return {
            "current_score": 0.0,
            "current_feedback": f"Render failed: {state.get('error', 'Unknown error')}",
            "status": "evaluated",
        }

    pdf_path = Path(state["input_pdf_path"])
    multiview_paths = [Path(p) for p in state["current_multiview_paths"]]

    if not multiview_paths:
        return {
            "current_score": 0.0,
            "current_feedback": "No rendered images available for evaluation",
            "status": "evaluated",
        }

    result = await cad_evaluator.evaluate(
        input_pdf_path=pdf_path,
        rendered_image_paths=multiview_paths,
        cad_code=state["current_code"],
    )

    print(f"[EVAL] Score: {result.score:.2f}")
    print(f"[EVAL] Feedback: {result.feedback[:100]}...")

    # Save iteration to history
    iteration_state: IterationState = {
        "iteration": iteration,
        "cad_code": state["current_code"],
        "multiview_paths": state["current_multiview_paths"],
        "score": result.score,
        "feedback": result.feedback,
        "error": state.get("error"),
    }

    return {
        "current_score": result.score,
        "current_feedback": result.feedback,
        "iterations_history": [iteration_state],
        "status": "evaluated",
    }


async def refine_code_node(
    state: RefinementState,
    cad_generator: "CadGeneratorService",
) -> dict:
    """
    Refine CAD code based on evaluation feedback.

    Args:
        state: Current workflow state.
        cad_generator: Service for generating CAD code.

    Returns:
        Updated state with refined CAD code.
    """
    iteration = state["current_iteration"]
    print(f"[REFINE] Iteration {iteration}: Refining code based on feedback...")

    feedback = state["current_feedback"]
    current_code = state["current_code"]
    config = state["config"]

    # Use fix_code_error with feedback as error message
    cad_code = CadCode(code=current_code)

    # Create a refinement prompt that includes the feedback
    refined_code = await cad_generator.fix_code_error(
        cad_code=cad_code,
        error_message=f"Evaluation feedback for improvement:\n{feedback}",
        temperature=config.get("temperature", 0.5),
    )

    print(f"[REFINE] Code refined ({len(refined_code.code)} chars)")

    return {
        "current_code": refined_code.code,
        "current_iteration": iteration + 1,
        "status": "refined",
    }


async def finalize_refinement_node(
    state: RefinementState,
    cad_renderer: "CadRendererService",
) -> dict:
    """
    Finalize the refinement process and export results.

    Args:
        state: Current workflow state.
        cad_renderer: Service for rendering and exporting CAD.

    Returns:
        Updated state with final results.
    """
    print("[FINALIZE] Finalizing refinement process...")

    output_dir = Path(state["output_dir"])
    model_name = state["model_name"]
    config = state["config"]

    # Select best iteration from history (highest score among successful executions)
    iterations_history = state.get("iterations_history", [])
    best_iteration = None
    for iteration in iterations_history:
        if iteration.get("error") is not None:
            continue
        score = iteration.get("score", 0.0)
        if best_iteration is None or score > best_iteration.get("score", 0.0):
            best_iteration = iteration

    if best_iteration is not None:
        final_code = best_iteration["cad_code"]
        final_score = best_iteration["score"]
        selected_iter = best_iteration["iteration"]
        print(
            f"[FINALIZE] Selected iteration {selected_iter} "
            f"with best score {final_score:.2f}"
        )
    else:
        # Fallback: use current code if history is empty
        final_code = state["current_code"]
        final_score = state.get("current_score", 0.0)
        print(
            f"[FINALIZE] No valid history, using current code (score: {final_score:.2f})"
        )

    # Save final code
    code_path = output_dir / f"{model_name}.py"
    code_path.write_text(final_code, encoding="utf-8")
    print(f"[FINALIZE] Code saved to: {code_path}")

    # Export STEP file
    step_path = output_dir / f"{model_name}.step"
    try:
        cad_code = CadCode(code=final_code)
        await cad_renderer.export_step(
            cad_code=cad_code,
            output_path=step_path,
        )
        print(f"[FINALIZE] STEP file saved to: {step_path}")
    except Exception as e:
        print(f"[FINALIZE] Warning: Failed to export STEP: {e}")

    # Render final images
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    # For no-feedback mode (1-shot), reuse the iteration_0 renders as final
    enable_feedback_loop = config.get("enable_feedback_loop", True)
    current_iteration = state.get("current_iteration", 0)

    if not enable_feedback_loop and current_iteration <= 1:
        # Reuse iteration_0 renders as final result
        iter_0_dir = output_dir / "iteration_0"
        if iter_0_dir.exists():
            try:
                # Copy iteration_0 renders to final directory
                for src_file in iter_0_dir.glob("*"):
                    if src_file.is_file():
                        dst_file = final_dir / src_file.name
                        shutil.copy2(src_file, dst_file)
                print("[FINALIZE] Reused iteration_0 renders as final (no-feedback mode)")
            except Exception as e:
                print(f"[FINALIZE] Warning: Failed to copy iteration_0 renders: {e}")
                # Fallback to re-rendering
                try:
                    await cad_renderer.render(
                        cad_code=cad_code,
                        output_dir=final_dir,
                        individual_id=model_name,
                    )
                    print(f"[FINALIZE] Final renders saved to: {final_dir}")
                except Exception as render_e:
                    print(
                        f"[FINALIZE] Warning: Failed to render final images: {render_e}"
                    )
        else:
            # iteration_0 directory doesn't exist, render normally
            try:
                await cad_renderer.render(
                    cad_code=cad_code,
                    output_dir=final_dir,
                    individual_id=model_name,
                )
                print(f"[FINALIZE] Final renders saved to: {final_dir}")
            except Exception as e:
                print(f"[FINALIZE] Warning: Failed to render final images: {e}")
    else:
        # Normal feedback mode: re-render for final
        try:
            await cad_renderer.render(
                cad_code=cad_code,
                output_dir=final_dir,
                individual_id=model_name,
            )
            print(f"[FINALIZE] Final renders saved to: {final_dir}")
        except Exception as e:
            print(f"[FINALIZE] Warning: Failed to render final images: {e}")

    iterations = len(state.get("iterations_history", []))
    print(f"[FINALIZE] Completed after {iterations} iterations")
    print(f"[FINALIZE] Final score: {final_score:.2f}")

    return {
        "final_code": final_code,
        "status": "completed",
    }
