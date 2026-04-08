"""Evaluate model use case."""

from pathlib import Path

from domain.services.cad_renderer import CadRendererService
from domain.services.metrics_calculator import MetricsCalculatorService
from domain.value_objects.cad_code import CadCode

from application.dto.evaluation_result import (
    CadStructureMetricsDTO,
    EvaluationResult,
    ExtrusionAccuracyDTO,
    SketchPrimitiveAccuracyDTO,
)


class EvaluateModelUseCase:
    """
    Use case for evaluating a generated CAD model against ground truth.

    Calculates geometric and topological metrics.
    """

    def __init__(
        self,
        cad_renderer: CadRendererService,
        metrics_calculator: MetricsCalculatorService,
    ) -> None:
        """
        Initialize the use case.

        Args:
            cad_renderer: Service for rendering and exporting CAD models.
            metrics_calculator: Service for calculating metrics.
        """
        self._cad_renderer = cad_renderer
        self._metrics_calculator = metrics_calculator

    async def execute(
        self,
        cad_code: CadCode,
        ground_truth_step_path: Path,
        output_dir: Path,
    ) -> EvaluationResult:
        """
        Evaluate a CAD model against ground truth.

        Args:
            cad_code: Generated CAD code to evaluate.
            ground_truth_step_path: Path to ground truth STEP file.
            output_dir: Directory to save exported STEP file.

        Returns:
            EvaluationResult containing all metrics.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_step_path = output_dir / "generated.step"

        await self._cad_renderer.export_step(cad_code, generated_step_path)

        generated_euler = await self._cad_renderer.calculate_euler_characteristic(
            cad_code
        )

        metrics = await self._metrics_calculator.calculate(
            generated_step_path=generated_step_path,
            ground_truth_step_path=ground_truth_step_path,
        )

        cad_structure_dto = self._convert_cad_structure(metrics.cad_structure)

        return EvaluationResult(
            pcd=metrics.pcd,
            hdd=metrics.hdd,
            iou=metrics.iou,
            dsc=metrics.dsc,
            topology_error=metrics.topology_error,
            topology_correct=metrics.topology_correct,
            generated_euler=generated_euler.value,
            ground_truth_euler=metrics.ground_truth_euler,
            cad_structure=cad_structure_dto,
        )

    async def evaluate_step_files(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> EvaluationResult:
        """
        Evaluate two STEP files directly.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            EvaluationResult containing all metrics.
        """
        metrics = await self._metrics_calculator.calculate(
            generated_step_path=generated_step_path,
            ground_truth_step_path=ground_truth_step_path,
        )

        cad_structure_dto = self._convert_cad_structure(metrics.cad_structure)

        return EvaluationResult(
            pcd=metrics.pcd,
            hdd=metrics.hdd,
            iou=metrics.iou,
            dsc=metrics.dsc,
            topology_error=metrics.topology_error,
            topology_correct=metrics.topology_correct,
            generated_euler=metrics.generated_euler,
            ground_truth_euler=metrics.ground_truth_euler,
            cad_structure=cad_structure_dto,
        )

    def _convert_cad_structure(
        self, cad_structure
    ) -> CadStructureMetricsDTO | None:
        """
        Convert domain CadStructureMetrics to DTO.

        Args:
            cad_structure: Domain value object or None.

        Returns:
            CadStructureMetricsDTO or None.
        """
        if cad_structure is None:
            return None

        return CadStructureMetricsDTO(
            command_accuracy=cad_structure.command_accuracy,
            sketch_primitive=SketchPrimitiveAccuracyDTO(
                line=cad_structure.sketch_primitive.line,
                arc=cad_structure.sketch_primitive.arc,
                circle=cad_structure.sketch_primitive.circle,
            ),
            extrusion=ExtrusionAccuracyDTO(
                plane=cad_structure.extrusion.plane,
                transform=cad_structure.extrusion.transform,
                extent=cad_structure.extrusion.extent,
                overall=cad_structure.extrusion.overall,
            ),
        )
