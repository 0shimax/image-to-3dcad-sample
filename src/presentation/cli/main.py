"""Main CLI entry point for Image-to-3DCAD."""

import matplotlib

matplotlib.use("Agg")

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from application.services.report_generator import ReportGenerator
from application.use_cases.evaluate_model import EvaluateModelUseCase
from application.use_cases.refine_cad_from_pdf import RefineCadFromPdfUseCase
from application.use_cases.run_pipeline import (
    PipelineRequest,
    RunPipelineUseCase,
)
from infrastructure.cad.renderer_impl import CadRendererServiceImpl
from infrastructure.llm.cad_evaluator_impl import CadEvaluatorServiceImpl
from infrastructure.llm.cad_generator_impl import CadGeneratorServiceImpl
from infrastructure.llm.vlm_client import VlmClient
from infrastructure.repositories.few_shot_repository_impl import (
    FewShotRepositoryImpl,
)
from infrastructure.services.metrics_calculator_impl import (
    MetricsCalculatorServiceImpl,
)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description=("Image-to-3DCAD: VLMを用いた画像からのCADコード生成パイプライン"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # pipeline command
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run end-to-end pipeline on paired data",
    )
    pipeline_parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help=("Input directory (paired format with images/ and step/)"),
    )
    pipeline_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help=("Output directory (default: data/output/pipeline_{timestamp})"),
    )
    pipeline_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of models to process",
    )
    pipeline_parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        default=True,
        help="Process all models even if output exists",
    )
    pipeline_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="VLM model name (default: env VERTEX_AI_MODEL_NAME)",
    )

    return parser


def progress_callback(message: str, current: int, total: int) -> None:
    """Print progress updates."""
    print(f"[{current}/{total}] {message}")


async def run_pipeline(args: argparse.Namespace) -> None:
    """Run end-to-end pipeline on paired data."""
    model_display = args.model or "(from .env VERTEX_AI_MODEL_NAME)"

    # Set default output_dir if not specified
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"data/output/pipeline_{timestamp}")
    else:
        output_dir = args.output_dir

    print("Running pipeline...")
    print(f"  Input directory: {args.input}")
    print(f"  Output directory: {output_dir}")
    print(f"  Skip existing: {args.skip_existing}")
    print(f"  Model: {model_display}")
    if args.limit:
        print(f"  Limit: {args.limit}")
    print()

    # Validate input directory structure
    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}")
        sys.exit(1)
    images_dir = args.input / "images"
    step_dir = args.input / "step"
    if not images_dir.exists() or not step_dir.exists():
        print("Error: Input directory must contain 'images/' and 'step/' subdirectories")
        sys.exit(1)

    # Create service dependencies
    vlm_client = VlmClient(model_name=args.model)
    few_shot_repository = FewShotRepositoryImpl()
    cad_renderer = CadRendererServiceImpl()
    cad_generator = CadGeneratorServiceImpl(vlm_client, few_shot_repository, cad_renderer)
    cad_evaluator = CadEvaluatorServiceImpl(vlm_client)
    metrics_calculator = MetricsCalculatorServiceImpl()

    # Create use cases
    refine_use_case = RefineCadFromPdfUseCase(
        cad_generator=cad_generator,
        cad_renderer=cad_renderer,
        cad_evaluator=cad_evaluator,
        few_shot_repository=few_shot_repository,
    )

    evaluate_use_case = EvaluateModelUseCase(
        cad_renderer=cad_renderer,
        metrics_calculator=metrics_calculator,
    )

    pipeline_use_case = RunPipelineUseCase(
        refine_use_case=refine_use_case,
        evaluate_use_case=evaluate_use_case,
        progress_callback=progress_callback,
    )

    # Create request
    request = PipelineRequest(
        input_dir=args.input,
        output_dir=output_dir,
        limit=args.limit,
        skip_existing=args.skip_existing,
    )

    try:
        result = await pipeline_use_case.execute(request)

        # Generate reports
        report_generator = ReportGenerator()
        markdown_path = output_dir / "report.md"
        json_path = output_dir / "pipeline_result.json"

        report_generator.generate_markdown(result, markdown_path)
        report_generator.generate_json(result, json_path)

        # Print summary
        print("\n" + "=" * 60)
        print("Pipeline Complete!")
        print("=" * 60)
        print(f"Total models: {result.summary.total_models}")
        print(f"Successful: {result.summary.successful}")
        print(f"Failed: {result.summary.failed}")
        print(f"Success rate: {result.summary.success_rate * 100:.1f}%")

        if result.summary.avg_generation_time is not None:
            print(f"Average generation time: {result.summary.avg_generation_time:.2f}s")

        if result.summary.pcd_stats:
            print("\n" + "-" * 60)
            print("Metrics Summary")
            print("-" * 60)

            s = result.summary.pcd_stats
            print("\nPCD (Point Cloud Distance) - lower is better:")
            print(f"  Mean: {s.mean:.4f}, Std: {s.std:.4f}")

            if result.summary.hdd_stats:
                s = result.summary.hdd_stats
                print("\nHDD (Hausdorff Distance) - lower is better:")
                print(f"  Mean: {s.mean:.4f}, Std: {s.std:.4f}")

            if result.summary.iou_stats:
                s = result.summary.iou_stats
                print("\nIoU (Intersection over Union) - higher is better:")
                print(f"  Mean: {s.mean:.4f}, Std: {s.std:.4f}")

            if result.summary.dsc_stats:
                s = result.summary.dsc_stats
                print("\nDSC (Dice Similarity Coefficient) - higher is better:")
                print(f"  Mean: {s.mean:.4f}, Std: {s.std:.4f}")

        print("\n" + "-" * 60)
        print("Reports")
        print("-" * 60)
        print(f"Markdown report: {markdown_path}")
        print(f"JSON result: {json_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "pipeline":
        asyncio.run(run_pipeline(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
