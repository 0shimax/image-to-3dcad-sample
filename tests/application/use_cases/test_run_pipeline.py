"""Tests for RunPipelineUseCase."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from application.dto.pipeline_result import MetricStatistics
from application.use_cases.run_pipeline import (
    PipelineRequest,
    RunPipelineUseCase,
)


class TestPipelineRequest:
    """Tests for PipelineRequest dataclass."""

    def test_pipeline_request_creation(self):
        """Test basic PipelineRequest creation with required fields."""
        request = PipelineRequest(
            input_dir=Path("/path/to/input"),
            output_dir=Path("/path/to/output"),
        )
        assert request.input_dir == Path("/path/to/input")
        assert request.output_dir == Path("/path/to/output")

    def test_pipeline_request_with_defaults(self):
        """Test PipelineRequest default values."""
        request = PipelineRequest(
            input_dir=Path("/input"),
            output_dir=Path("/output"),
        )
        assert request.limit is None
        assert request.num_few_shot_examples == 5
        assert request.temperature == 0.5
        assert request.skip_existing is True

    def test_pipeline_request_with_custom_values(self):
        """Test PipelineRequest with custom values."""
        request = PipelineRequest(
            input_dir=Path("/input"),
            output_dir=Path("/output"),
            limit=100,
            num_few_shot_examples=10,
            temperature=0.7,
            skip_existing=False,
        )
        assert request.limit == 100
        assert request.num_few_shot_examples == 10
        assert request.temperature == 0.7
        assert request.skip_existing is False


class TestDiscoverFilePairs:
    """Tests for file pair discovery."""

    def test_discover_file_pairs_with_paired_format(self):
        """Test file pair discovery with paired directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)
            images_dir = input_dir / "images"
            step_dir = input_dir / "step"
            images_dir.mkdir()
            step_dir.mkdir()

            # Create matching pairs
            (images_dir / "model_a.jpg").touch()
            (step_dir / "model_a.step").touch()
            (images_dir / "model_b.png").touch()
            (step_dir / "model_b.stp").touch()

            use_case = RunPipelineUseCase(
                refine_use_case=MagicMock(),
                evaluate_use_case=MagicMock(),
            )

            pairs = use_case._discover_file_pairs(input_dir)

            assert len(pairs) == 2
            model_names = {pair[2] for pair in pairs}
            assert model_names == {"model_a", "model_b"}

    def test_discover_file_pairs_ignores_unmatched_files(self):
        """Test that unmatched files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)
            images_dir = input_dir / "images"
            step_dir = input_dir / "step"
            images_dir.mkdir()
            step_dir.mkdir()

            (images_dir / "model_a.jpg").touch()
            (step_dir / "model_a.step").touch()
            (images_dir / "orphan_image.jpg").touch()
            (step_dir / "orphan_step.step").touch()

            use_case = RunPipelineUseCase(
                refine_use_case=MagicMock(),
                evaluate_use_case=MagicMock(),
            )

            pairs = use_case._discover_file_pairs(input_dir)

            assert len(pairs) == 1
            assert pairs[0][2] == "model_a"

    def test_discover_file_pairs_empty_directory(self):
        """Test discovery with empty directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)
            images_dir = input_dir / "images"
            step_dir = input_dir / "step"
            images_dir.mkdir()
            step_dir.mkdir()

            use_case = RunPipelineUseCase(
                refine_use_case=MagicMock(),
                evaluate_use_case=MagicMock(),
            )

            pairs = use_case._discover_file_pairs(input_dir)
            assert len(pairs) == 0


class TestCalcStats:
    """Tests for statistics calculation."""

    def test_calc_stats_basic(self):
        """Test basic statistics calculation."""
        use_case = RunPipelineUseCase(
            refine_use_case=MagicMock(),
            evaluate_use_case=MagicMock(),
        )

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = use_case._calc_stats(values)

        assert isinstance(stats, MetricStatistics)
        assert stats.mean == 3.0
        assert stats.median == 3.0
        assert stats.min == 1.0
        assert stats.max == 5.0

    def test_calc_stats_single_value(self):
        """Test statistics with single value."""
        use_case = RunPipelineUseCase(
            refine_use_case=MagicMock(),
            evaluate_use_case=MagicMock(),
        )

        values = [5.0]
        stats = use_case._calc_stats(values)

        assert stats.mean == 5.0
        assert stats.median == 5.0
        assert stats.min == 5.0
        assert stats.max == 5.0
        assert stats.std == 0.0

    def test_calc_stats_empty_returns_none(self):
        """Test statistics with empty values returns None."""
        use_case = RunPipelineUseCase(
            refine_use_case=MagicMock(),
            evaluate_use_case=MagicMock(),
        )

        stats = use_case._calc_stats([])
        assert stats is None
