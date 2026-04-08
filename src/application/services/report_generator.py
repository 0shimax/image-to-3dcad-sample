"""Report generator service for pipeline results."""

import json
from datetime import datetime
from pathlib import Path

from application.dto.pipeline_result import PipelineResult


class ReportGenerator:
    """
    Generate reports from pipeline results.

    This service generates Markdown and JSON reports from
    PipelineResult data.
    """

    def generate_markdown(self, result: PipelineResult, output_path: Path) -> None:
        """
        Generate Markdown report.

        Args:
            result: Pipeline execution result.
            output_path: Path to save the report.
        """
        lines: list[str] = []

        # Title
        lines.append("# Pipeline Evaluation Report")
        lines.append("")

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"Generated: {timestamp}")
        lines.append("")

        # Configuration info
        lines.append("## Configuration")
        lines.append("")
        lines.append(f"- **Method:** {result.method}")
        lines.append(f"- **Input Directory:** {result.input_dir}")
        lines.append(f"- **Output Directory:** {result.output_dir}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total: {result.summary.total_models}")
        lines.append(f"- Successful: {result.summary.successful}")
        lines.append(f"- Failed: {result.summary.failed}")
        lines.append(f"- Success Rate: {result.summary.success_rate * 100:.2f}%")
        if result.summary.avg_generation_time is not None:
            lines.append(
                f"- Average Generation Time: {result.summary.avg_generation_time:.2f}s"
            )
        lines.append("")

        # Metrics Summary table
        lines.append("## Metrics Summary")
        lines.append("")
        lines.append("| Metric | Mean | Std | Min | Max | Median |")
        lines.append("|--------|------|-----|-----|-----|--------|")

        metrics = [
            ("PCD", result.summary.pcd_stats),
            ("HDD", result.summary.hdd_stats),
            ("IoU", result.summary.iou_stats),
            ("DSC", result.summary.dsc_stats),
        ]

        for metric_name, stats in metrics:
            if stats is not None:
                lines.append(
                    f"| {metric_name} | {stats.mean:.4f} | {stats.std:.4f} | "
                    f"{stats.min:.4f} | {stats.max:.4f} | {stats.median:.4f} |"
                )
            else:
                lines.append(f"| {metric_name} | N/A | N/A | N/A | N/A | N/A |")

        lines.append("")

        # Individual Results table
        lines.append("## Individual Results")
        lines.append("")
        lines.append("| Model | PCD | HDD | IoU | DSC | Time (s) | Status |")
        lines.append("|-------|-----|-----|-----|-----|----------|--------|")

        for model_result in result.results:
            pcd = f"{model_result.pcd:.4f}" if model_result.pcd is not None else "N/A"
            hdd = f"{model_result.hdd:.4f}" if model_result.hdd is not None else "N/A"
            iou = f"{model_result.iou:.4f}" if model_result.iou is not None else "N/A"
            dsc = f"{model_result.dsc:.4f}" if model_result.dsc is not None else "N/A"
            time_str = f"{model_result.generation_time_seconds:.2f}"
            status = "Failed" if model_result.error else "Success"
            lines.append(
                f"| {model_result.model_name} | {pcd} | {hdd} | "
                f"{iou} | {dsc} | {time_str} | {status} |"
            )

        lines.append("")

        # Failed Models section
        failed_models = [r for r in result.results if r.error is not None]
        if failed_models:
            lines.append("## Failed Models")
            lines.append("")
            for model_result in failed_models:
                lines.append(f"### {model_result.model_name}")
                lines.append("")
                lines.append(f"**Error:** {model_result.error}")
                lines.append("")

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines))

    def generate_json(self, result: PipelineResult, output_path: Path) -> None:
        """
        Generate JSON report.

        Args:
            result: Pipeline execution result.
            output_path: Path to save the report.
        """
        # Get all data from PipelineResult via model_dump()
        data = result.model_dump()

        # Add generated timestamp
        data["generated_at"] = datetime.now().isoformat()

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
