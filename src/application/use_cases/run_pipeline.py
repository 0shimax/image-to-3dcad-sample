"""Run pipeline use case for processing paired format data."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from application.dto.pipeline_result import (
    MetricStatistics,
    PipelineModelResult,
    PipelineResult,
    PipelineSummary,
)
from application.use_cases.evaluate_model import EvaluateModelUseCase
from application.use_cases.refine_cad_from_pdf import (
    RefineCadFromPdfUseCase,
    RefinementRequest,
)


@dataclass
class PipelineRequest:
    """
    Request for pipeline execution.

    Attributes:
        input_dir: Input directory containing paired format data.
        output_dir: Output directory for generated CAD files.
        limit: Maximum number of models to process (None for all).
        num_few_shot_examples: Number of few-shot examples to use.
        temperature: Temperature for LLM generation.
        skip_existing: Skip models with existing output.
    """

    input_dir: Path
    output_dir: Path
    limit: int | None = None
    num_few_shot_examples: int = 5
    temperature: float = 0.5
    skip_existing: bool = True


# Type alias for progress callback
ProgressCallback = Callable[[str, int, int], None]


class RunPipelineUseCase:
    """
    Use case for running the pipeline on paired format data.

    This use case:
    1. Discovers file pairs in paired format (images/ and step/ subdirs)
    2. Processes each model through one-shot CAD generation
    3. Evaluates generated CAD against ground truth
    4. Returns PipelineResult with all results and summary statistics
    """

    def __init__(
        self,
        refine_use_case: RefineCadFromPdfUseCase,
        evaluate_use_case: EvaluateModelUseCase,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._refine_use_case = refine_use_case
        self._evaluate_use_case = evaluate_use_case
        self._progress_callback = progress_callback

    async def execute(self, request: PipelineRequest) -> PipelineResult:
        """Execute the pipeline on all discovered file pairs."""
        pairs = self._discover_file_pairs(request.input_dir)

        if request.limit is not None:
            pairs = pairs[: request.limit]

        request.output_dir.mkdir(parents=True, exist_ok=True)

        total = len(pairs)
        sem = asyncio.Semaphore(4)

        async def _process_with_progress(
            idx: int,
            image_path: Path,
            step_path: Path,
            model_name: str,
        ) -> PipelineModelResult:
            if self._progress_callback:
                self._progress_callback(model_name, idx + 1, total)

            model_output_dir = request.output_dir / model_name

            if request.skip_existing:
                existing = self._load_existing_result(
                    model_name,
                    image_path,
                    step_path,
                    model_output_dir,
                )
                if existing is not None:
                    return existing

            async with sem:
                return await self._process_single_model(
                    image_path=image_path,
                    step_path=step_path,
                    model_name=model_name,
                    output_dir=model_output_dir,
                    request=request,
                )

        results = await asyncio.gather(
            *(
                _process_with_progress(idx, img, stp, name)
                for idx, (img, stp, name) in enumerate(pairs)
            )
        )

        summary = self._calculate_summary(list(results))

        return PipelineResult(
            method="simple",
            input_dir=str(request.input_dir),
            output_dir=str(request.output_dir),
            results=results,
            summary=summary,
        )

    def _discover_file_pairs(self, input_dir: Path) -> list[tuple[Path, Path, str]]:
        """
        Discover image/step file pairs in paired format.

        paired format:
            input_dir/
            ├── images/
            │   ├── model_a.jpg
            │   └── model_b.png
            └── step/
                ├── model_a.step
                └── model_b.stp
        """
        images_dir = input_dir / "images"
        step_dir = input_dir / "step"

        if not images_dir.exists() or not step_dir.exists():
            return []

        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf"}
        images_by_name: dict[str, Path] = {}
        for img_file in images_dir.iterdir():
            if img_file.is_file() and img_file.suffix.lower() in image_extensions:
                images_by_name[img_file.stem] = img_file

        step_extensions = {".step", ".stp"}
        steps_by_name: dict[str, Path] = {}
        for step_file in step_dir.iterdir():
            if step_file.is_file() and step_file.suffix.lower() in step_extensions:
                steps_by_name[step_file.stem] = step_file

        pairs: list[tuple[Path, Path, str]] = []
        common_names = set(images_by_name.keys()) & set(steps_by_name.keys())

        for name in sorted(common_names):
            pairs.append((images_by_name[name], steps_by_name[name], name))

        return pairs

    async def _process_single_model(
        self,
        image_path: Path,
        step_path: Path,
        model_name: str,
        output_dir: Path,
        request: PipelineRequest,
    ) -> PipelineModelResult:
        """Process a single model through generation and evaluation."""
        output_dir.mkdir(parents=True, exist_ok=True)
        start_time = time.time()

        try:
            refinement_request = RefinementRequest(
                pdf_path=image_path,
                output_dir=output_dir,
                max_iterations=1,
                num_few_shot_examples=request.num_few_shot_examples,
                temperature=request.temperature,
                enable_feedback_loop=False,
            )
            refinement_result = await self._refine_use_case.execute(refinement_request)

            generation_time = time.time() - start_time

            if refinement_result.error is not None:
                return PipelineModelResult(
                    model_name=model_name,
                    image_path=str(image_path),
                    ground_truth_path=str(step_path),
                    generated_step_path=None,
                    generated_code_path=None,
                    generation_time_seconds=generation_time,
                    error=refinement_result.error,
                )

            generated_step_path = refinement_result.step_path
            generated_code_path = refinement_result.code_path

            if generated_step_path is None or not generated_step_path.exists():
                return PipelineModelResult(
                    model_name=model_name,
                    image_path=str(image_path),
                    ground_truth_path=str(step_path),
                    generated_step_path=None,
                    generated_code_path=str(generated_code_path)
                    if generated_code_path
                    else None,
                    total_iterations=refinement_result.total_iterations,
                    vlm_score=refinement_result.final_score,
                    generation_time_seconds=generation_time,
                    error="Failed to generate STEP file",
                )

            eval_result = await self._evaluate_use_case.evaluate_step_files(
                generated_step_path=generated_step_path,
                ground_truth_step_path=step_path,
            )

            model_result = PipelineModelResult(
                model_name=model_name,
                image_path=str(image_path),
                ground_truth_path=str(step_path),
                generated_step_path=str(generated_step_path),
                generated_code_path=str(generated_code_path)
                if generated_code_path
                else None,
                pcd=eval_result.pcd,
                hdd=eval_result.hdd,
                iou=eval_result.iou,
                dsc=eval_result.dsc,
                topology_error=eval_result.topology_error,
                topology_correct=eval_result.topology_correct,
                vlm_score=refinement_result.final_score,
                total_iterations=refinement_result.total_iterations,
                generation_time_seconds=generation_time,
                error=None,
            )

            self._save_result_metadata(output_dir, model_result)
            return model_result

        except Exception as e:
            generation_time = time.time() - start_time
            return PipelineModelResult(
                model_name=model_name,
                image_path=str(image_path),
                ground_truth_path=str(step_path),
                generated_step_path=None,
                generated_code_path=None,
                generation_time_seconds=generation_time,
                error=str(e),
            )

    def _load_existing_result(
        self,
        model_name: str,
        image_path: Path,
        step_path: Path,
        output_dir: Path,
    ) -> PipelineModelResult | None:
        """Load result from existing output directory."""
        result_file = output_dir / "result.json"
        if not result_file.exists():
            return None

        try:
            with open(result_file, encoding="utf-8") as f:
                data = json.load(f)
            return PipelineModelResult.model_validate(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _save_result_metadata(
        self,
        output_dir: Path,
        model_result: PipelineModelResult,
    ) -> None:
        """Save result metadata to JSON file."""
        result_file = output_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(model_result.model_dump(), f, indent=2)

    def _calculate_summary(self, results: list[PipelineModelResult]) -> PipelineSummary:
        """Calculate summary statistics from results."""
        total = len(results)
        successful = sum(1 for r in results if r.error is None)
        failed = total - successful

        pcd_values = [r.pcd for r in results if r.pcd is not None]
        hdd_values = [r.hdd for r in results if r.hdd is not None]
        iou_values = [r.iou for r in results if r.iou is not None]
        dsc_values = [r.dsc for r in results if r.dsc is not None]
        topology_error_values = [
            r.topology_error for r in results if r.topology_error is not None
        ]
        generation_times = [r.generation_time_seconds for r in results]

        return PipelineSummary(
            total_models=total,
            successful=successful,
            failed=failed,
            success_rate=successful / total if total > 0 else 0.0,
            pcd_stats=self._calc_stats(pcd_values),
            hdd_stats=self._calc_stats(hdd_values),
            iou_stats=self._calc_stats(iou_values),
            dsc_stats=self._calc_stats(dsc_values),
            topology_error_stats=self._calc_stats(
                [float(v) for v in topology_error_values]
            ),
            avg_generation_time=float(np.mean(generation_times))
            if generation_times
            else None,
        )

    def _calc_stats(self, values: list[float]) -> MetricStatistics | None:
        """Calculate statistics for a list of values."""
        if not values:
            return None

        arr = np.array(values)
        return MetricStatistics(
            mean=float(np.mean(arr)),
            std=float(np.std(arr)),
            min=float(np.min(arr)),
            max=float(np.max(arr)),
            median=float(np.median(arr)),
        )
