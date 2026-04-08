"""Integration tests for pipeline CLI."""

import subprocess
from pathlib import Path


def test_pipeline_help() -> None:
    """Test pipeline help command."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "presentation.cli.main",
            "pipeline",
            "--help",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=30,
    )
    assert result.returncode == 0
    assert "--input" in result.stdout
    assert "--limit" in result.stdout
    assert "--output-dir" in result.stdout


def test_pipeline_missing_input() -> None:
    """Test pipeline with missing input."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "presentation.cli.main", "pipeline"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=30,
    )
    assert result.returncode != 0
    assert "required" in result.stderr.lower()


def test_pipeline_invalid_input_directory() -> None:
    """Test pipeline with non-existent input directory."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "presentation.cli.main",
            "pipeline",
            "--input",
            "/nonexistent/path/to/data",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=30,
    )
    assert result.returncode != 0
    combined_output = result.stdout.lower() + result.stderr.lower()
    assert "not found" in combined_output or "error" in combined_output
