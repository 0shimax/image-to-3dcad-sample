"""Tests for ReportGenerator service."""

import json
from pathlib import Path

import pytest

from application.dto.pipeline_result import (
    MetricStatistics,
    PipelineModelResult,
    PipelineResult,
    PipelineSummary,
)
from application.services.report_generator import ReportGenerator


@pytest.fixture
def sample_pipeline_result() -> PipelineResult:
    """Create a sample PipelineResult for testing."""
    return PipelineResult(
        method="simple",
        input_dir="/path/to/input",
        output_dir="/path/to/output",
        results=[
            PipelineModelResult(
                model_name="model_001",
                image_path="/path/to/input/model_001/image.png",
                ground_truth_path="/path/to/input/model_001/model.step",
                generated_step_path="/path/to/output/model_001/generated.step",
                generated_code_path="/path/to/output/model_001/generated.py",
                pcd=0.05,
                hdd=0.10,
                iou=0.85,
                dsc=0.90,
                generation_time_seconds=15.5,
                error=None,
            ),
            PipelineModelResult(
                model_name="model_002",
                image_path="/path/to/input/model_002/image.png",
                ground_truth_path="/path/to/input/model_002/model.step",
                generated_step_path="/path/to/output/model_002/generated.step",
                generated_code_path="/path/to/output/model_002/generated.py",
                pcd=0.08,
                hdd=0.15,
                iou=0.75,
                dsc=0.80,
                generation_time_seconds=20.0,
                error=None,
            ),
            PipelineModelResult(
                model_name="model_003",
                image_path="/path/to/input/model_003/image.png",
                ground_truth_path="/path/to/input/model_003/model.step",
                generated_step_path=None,
                generated_code_path=None,
                pcd=None,
                hdd=None,
                iou=None,
                dsc=None,
                generation_time_seconds=5.0,
                error="CAD generation failed",
            ),
        ],
        summary=PipelineSummary(
            total_models=3,
            successful=2,
            failed=1,
            success_rate=0.6667,
            pcd_stats=MetricStatistics(
                mean=0.065,
                std=0.015,
                min=0.05,
                max=0.08,
                median=0.065,
            ),
            hdd_stats=MetricStatistics(
                mean=0.125,
                std=0.025,
                min=0.10,
                max=0.15,
                median=0.125,
            ),
            iou_stats=MetricStatistics(
                mean=0.80,
                std=0.05,
                min=0.75,
                max=0.85,
                median=0.80,
            ),
            dsc_stats=MetricStatistics(
                mean=0.85,
                std=0.05,
                min=0.80,
                max=0.90,
                median=0.85,
            ),
            avg_generation_time=13.5,
        ),
    )


class TestReportGeneratorMarkdown:
    """Tests for Markdown report generation."""

    def test_generate_markdown_creates_file(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.md"
        generator.generate_markdown(sample_pipeline_result, output_path)
        assert output_path.exists()

    def test_generate_markdown_contains_title(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.md"
        generator.generate_markdown(sample_pipeline_result, output_path)
        content = output_path.read_text()
        assert "# Pipeline Evaluation Report" in content

    def test_generate_markdown_contains_method_info(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.md"
        generator.generate_markdown(sample_pipeline_result, output_path)
        content = output_path.read_text()
        assert "simple" in content

    def test_generate_markdown_contains_summary_section(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.md"
        generator.generate_markdown(sample_pipeline_result, output_path)
        content = output_path.read_text()
        assert "## Summary" in content
        assert "Total: 3" in content
        assert "Successful: 2" in content

    def test_generate_markdown_contains_failed_models(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.md"
        generator.generate_markdown(sample_pipeline_result, output_path)
        content = output_path.read_text()
        assert "## Failed Models" in content
        assert "model_003" in content


class TestReportGeneratorJSON:
    """Tests for JSON report generation."""

    def test_generate_json_creates_file(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.json"
        generator.generate_json(sample_pipeline_result, output_path)
        assert output_path.exists()

    def test_generate_json_valid_json(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.json"
        generator.generate_json(sample_pipeline_result, output_path)
        content = output_path.read_text()
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_generate_json_contains_pipeline_data(
        self,
        sample_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        generator = ReportGenerator()
        output_path = tmp_path / "report.json"
        generator.generate_json(sample_pipeline_result, output_path)
        content = output_path.read_text()
        data = json.loads(content)
        assert data["method"] == "simple"
        assert len(data["results"]) == 3
        assert data["summary"]["total_models"] == 3
