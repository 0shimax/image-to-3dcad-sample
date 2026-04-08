"""Metrics calculator service interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from domain.value_objects.cad_structure_metrics import CadStructureMetrics


@dataclass(frozen=True)
class EvaluationMetrics:
    """
    Value object containing all evaluation metrics.

    Attributes:
        pcd: Point Cloud Distance.
        hdd: Hausdorff Distance.
        iou: Intersection over Union.
        dsc: Dice Similarity Coefficient.
        topology_error: Absolute Euler characteristic difference |gen - gt|, or None if not calculable.
        topology_correct: Topology correctness (1.0=correct, 0.0=incorrect), or None if not calculable.
        generated_euler: Euler characteristic of generated model, or None if not available.
        ground_truth_euler: Euler characteristic of ground truth, or None if not available.
        cad_structure: Drawing2CAD-style CAD structure metrics (optional).
    """

    pcd: float
    hdd: float
    iou: float
    dsc: float
    topology_error: int | None
    topology_correct: float | None
    generated_euler: int | None
    ground_truth_euler: int | None
    cad_structure: CadStructureMetrics | None = field(default=None)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "pcd": self.pcd,
            "hdd": self.hdd,
            "iou": self.iou,
            "dsc": self.dsc,
            "topology_error": self.topology_error,
            "topology_correct": self.topology_correct,
            "generated_euler": self.generated_euler,
            "ground_truth_euler": self.ground_truth_euler,
        }
        if self.cad_structure is not None:
            result["cad_structure"] = self.cad_structure.to_dict()
        return result


class MetricsCalculatorService(ABC):
    """
    Abstract service for calculating evaluation metrics.

    Compares generated CAD models against ground truth using
    geometric and topological metrics.
    """

    @abstractmethod
    async def calculate(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> EvaluationMetrics:
        """
        Calculate all evaluation metrics.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            EvaluationMetrics containing all calculated metrics.
        """
        pass

    @abstractmethod
    async def calculate_point_cloud_distance(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Point Cloud Distance (PCD).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            Point Cloud Distance value.
        """
        pass

    @abstractmethod
    async def calculate_hausdorff_distance(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Hausdorff Distance (HDD).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            Hausdorff Distance value.
        """
        pass

    @abstractmethod
    async def calculate_iou(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Intersection over Union (IoU).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            IoU value between 0 and 1.
        """
        pass

    @abstractmethod
    async def calculate_dice_coefficient(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Dice Similarity Coefficient (DSC).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            DSC value between 0 and 1.
        """
        pass

    @abstractmethod
    async def calculate_topology_metrics(
        self,
        generated_euler: int | None,
        ground_truth_euler: int | None,
    ) -> tuple[int | None, float | None]:
        """
        Calculate topology metrics.

        Args:
            generated_euler: Euler characteristic of generated model (or None).
            ground_truth_euler: Euler characteristic of ground truth (or None).

        Returns:
            Tuple of (topology_error, topology_correct).
            - topology_error: Absolute difference |gen - gt|, or None if not calculable
            - topology_correct: Binary indicator (1.0=correct, 0.0=incorrect), or None if not calculable
        """
        pass

    @abstractmethod
    async def calculate_cad_structure_metrics(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> CadStructureMetrics:
        """
        Calculate Drawing2CAD-style CAD structure metrics.

        Compares structural elements (sketch primitives, extrusions)
        between generated and ground truth models.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            CadStructureMetrics containing command, sketch, and extrusion accuracy.
        """
        pass
