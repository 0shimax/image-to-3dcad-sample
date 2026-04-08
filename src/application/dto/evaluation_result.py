"""Evaluation result DTO."""

from pydantic import BaseModel, Field


class SketchPrimitiveAccuracyDTO(BaseModel):
    """DTO for sketch primitive accuracy metrics."""

    line: float = Field(..., ge=0.0, le=1.0, description="Line accuracy")
    arc: float = Field(..., ge=0.0, le=1.0, description="Arc accuracy")
    circle: float = Field(..., ge=0.0, le=1.0, description="Circle accuracy")


class ExtrusionAccuracyDTO(BaseModel):
    """DTO for extrusion accuracy metrics."""

    plane: float = Field(..., ge=0.0, le=1.0, description="Plane accuracy")
    transform: float = Field(..., ge=0.0, le=1.0, description="Transform accuracy")
    extent: float = Field(..., ge=0.0, le=1.0, description="Extent accuracy")
    overall: float = Field(..., ge=0.0, le=1.0, description="Overall extrusion accuracy")


class CadStructureMetricsDTO(BaseModel):
    """DTO for Drawing2CAD-style CAD structure metrics."""

    command_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="Command accuracy"
    )
    sketch_primitive: SketchPrimitiveAccuracyDTO = Field(
        ..., description="Sketch primitive accuracy"
    )
    extrusion: ExtrusionAccuracyDTO = Field(..., description="Extrusion accuracy")


class EvaluationResult(BaseModel):
    """
    Result DTO for evaluation metrics.

    Attributes:
        pcd: Point Cloud Distance.
        hdd: Hausdorff Distance.
        iou: Intersection over Union.
        dsc: Dice Similarity Coefficient.
        topology_error: Absolute Euler characteristic difference |gen - gt|.
        topology_correct: Topology correctness (1.0=correct, 0.0=incorrect).
        generated_euler: Euler characteristic of generated model.
        ground_truth_euler: Euler characteristic of ground truth.
        cad_structure: Drawing2CAD-style CAD structure metrics.
    """

    pcd: float = Field(..., description="Point Cloud Distance")
    hdd: float = Field(..., description="Hausdorff Distance")
    iou: float = Field(..., ge=0.0, le=1.0, description="Intersection over Union")
    dsc: float = Field(..., ge=0.0, le=1.0, description="Dice Similarity Coefficient")
    topology_error: int | None = Field(default=None, ge=0, description="Absolute Euler characteristic difference |gen - gt| (or null if not calculable)")
    topology_correct: float | None = Field(default=None, description="Topology correctness: 1.0 if Euler match, 0.0 otherwise (or null if not calculable)")
    generated_euler: int | None = Field(default=None, description="Generated Euler")
    ground_truth_euler: int | None = Field(
        default=None, description="Ground Truth Euler"
    )
    cad_structure: CadStructureMetricsDTO | None = Field(
        default=None, description="Drawing2CAD structure metrics"
    )
