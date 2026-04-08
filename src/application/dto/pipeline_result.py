"""Pipeline result DTOs."""

from pydantic import BaseModel, Field


class MetricStatistics(BaseModel):
    """
    Statistics for a single metric.

    Attributes:
        mean: Mean value of the metric.
        std: Standard deviation.
        min: Minimum value.
        max: Maximum value.
        median: Median value.
    """

    mean: float = Field(..., description="Mean value of the metric")
    std: float = Field(..., description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    median: float = Field(..., description="Median value")


class PipelineModelResult(BaseModel):
    """
    Result for a single model in the pipeline.

    Attributes:
        model_name: Name identifier for the model.
        image_path: Path to the source image file.
        ground_truth_path: Path to the ground truth STEP file.
        generated_step_path: Path to the generated STEP file.
        generated_code_path: Path to the generated Python code file.
        pcd: Point Cloud Distance metric.
        hdd: Hausdorff Distance metric.
        iou: Intersection over Union metric (0.0 to 1.0).
        dsc: Dice Similarity Coefficient metric (0.0 to 1.0).
        topology_error: Topology error metric.
        topology_correct: Topology correctness metric.
        vlm_score: Vision Language Model score.
        total_iterations: Total number of iterations used.
        generation_time_seconds: Time taken for CAD generation in seconds.
        error: Error message if failed.
    """

    model_name: str = Field(..., description="Model name identifier")
    image_path: str = Field(..., description="Source image file path")
    ground_truth_path: str = Field(..., description="Ground truth STEP file path")
    generated_step_path: str | None = Field(
        default=None, description="Generated STEP file path"
    )
    generated_code_path: str | None = Field(
        default=None, description="Generated code file path"
    )
    pcd: float | None = Field(default=None, description="Point Cloud Distance")
    hdd: float | None = Field(default=None, description="Hausdorff Distance")
    iou: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Intersection over Union"
    )
    dsc: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Dice Similarity Coefficient"
    )
    topology_error: float | None = Field(
        default=None, description="Topology error metric"
    )
    topology_correct: float | None = Field(
        default=None, description="Topology correctness metric"
    )
    vlm_score: float | None = Field(
        default=None, description="Vision Language Model score"
    )
    total_iterations: int | None = Field(
        default=None, description="Total iterations used"
    )
    generation_time_seconds: float = Field(
        ..., description="CAD generation time in seconds"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class PipelineSummary(BaseModel):
    """
    Summary statistics for the pipeline run.

    Attributes:
        total_models: Total number of models processed.
        successful: Number of successful evaluations.
        failed: Number of failed evaluations.
        success_rate: Success rate (0.0 to 1.0).
        pcd_stats: Point Cloud Distance statistics.
        hdd_stats: Hausdorff Distance statistics.
        iou_stats: Intersection over Union statistics.
        dsc_stats: Dice Similarity Coefficient statistics.
        topology_error_stats: Topology error statistics.
        avg_generation_time: Average generation time in seconds.
    """

    total_models: int = Field(..., description="Total models processed")
    successful: int = Field(..., description="Successful evaluations")
    failed: int = Field(..., description="Failed evaluations")
    success_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)"
    )
    pcd_stats: MetricStatistics | None = Field(
        default=None, description="Point Cloud Distance statistics"
    )
    hdd_stats: MetricStatistics | None = Field(
        default=None, description="Hausdorff Distance statistics"
    )
    iou_stats: MetricStatistics | None = Field(
        default=None, description="Intersection over Union statistics"
    )
    dsc_stats: MetricStatistics | None = Field(
        default=None, description="Dice Similarity Coefficient statistics"
    )
    topology_error_stats: MetricStatistics | None = Field(
        default=None, description="Topology error statistics"
    )
    avg_generation_time: float | None = Field(
        default=None, description="Average generation time in seconds"
    )


class PipelineResult(BaseModel):
    """
    Complete result of pipeline execution.

    Attributes:
        method: Pipeline method name (e.g., 'refine', 'direct').
        input_dir: Input directory path.
        output_dir: Output directory path.
        results: Individual results for each model.
        summary: Summary statistics for the pipeline run.
    """

    method: str = Field(..., description="Pipeline method name")
    input_dir: str = Field(..., description="Input directory path")
    output_dir: str = Field(..., description="Output directory path")
    results: list[PipelineModelResult] = Field(
        default_factory=list, description="Individual results for each model"
    )
    summary: PipelineSummary = Field(
        ..., description="Summary statistics for the pipeline run"
    )
