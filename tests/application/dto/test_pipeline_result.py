"""Tests for pipeline result DTO."""

from application.dto.pipeline_result import (
    MetricStatistics,
    PipelineModelResult,
    PipelineResult,
    PipelineSummary,
)


def test_metric_statistics_creation():
    stats = MetricStatistics(
        mean=0.5,
        std=0.1,
        min=0.3,
        max=0.7,
        median=0.5,
    )
    assert stats.mean == 0.5
    assert stats.std == 0.1


def test_pipeline_model_result_creation():
    result = PipelineModelResult(
        model_name="test_model",
        image_path="/path/to/image.jpg",
        ground_truth_path="/path/to/model.step",
        generated_step_path="/path/to/generated.step",
        generated_code_path="/path/to/code.py",
        pcd=0.1,
        hdd=0.2,
        iou=0.8,
        dsc=0.85,
        generation_time_seconds=10.5,
        error=None,
    )
    assert result.model_name == "test_model"
    assert result.pcd == 0.1


def test_pipeline_summary_creation():
    summary = PipelineSummary(
        total_models=10,
        successful=8,
        failed=2,
        success_rate=0.8,
        pcd_stats=MetricStatistics(
            mean=0.1, std=0.02, min=0.05, max=0.2, median=0.1
        ),
        hdd_stats=MetricStatistics(
            mean=0.2, std=0.03, min=0.1, max=0.3, median=0.2
        ),
        iou_stats=MetricStatistics(
            mean=0.8, std=0.05, min=0.7, max=0.9, median=0.8
        ),
        dsc_stats=MetricStatistics(
            mean=0.85, std=0.04, min=0.75, max=0.95, median=0.85
        ),
    )
    assert summary.success_rate == 0.8


def test_pipeline_result_to_dict():
    result = PipelineResult(
        method="simple",
        input_dir="/path/to/input",
        output_dir="/path/to/output",
        results=[],
        summary=PipelineSummary(
            total_models=0,
            successful=0,
            failed=0,
            success_rate=0.0,
            pcd_stats=None,
            hdd_stats=None,
            iou_stats=None,
            dsc_stats=None,
        ),
    )
    data = result.model_dump()
    assert data["method"] == "simple"
