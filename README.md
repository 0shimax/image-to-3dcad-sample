# Image-to-3DCAD: CAD Code Generation from Technical Drawings using VLM

A pipeline that generates build123d CAD code from technical drawing images using Vision Language Models (VLM), and evaluates the output against ground truth STEP files.

## Features

- **One-shot CAD generation**: Generate build123d CAD code from images via VLM (1-shot)
- **Automated evaluation**: Compare generated STEP files against ground truth using geometric metrics (PCD, HDD, IoU, DSC)
- **Topology metrics**: Evaluation based on Euler characteristic
- **Batch processing**: Process paired-format datasets with automatic report generation
- **Parallel execution**: Concurrent model processing with `asyncio.gather` and semaphore-based throttling
- **VLM integration**: Gemini models via Vertex AI
- **Local caching**: Cache VLM responses and CAD rendering results to reduce API calls

## Architecture

Clean architecture based on Domain-Driven Design (DDD):

```
src/
├── domain/                    # Domain layer (business logic)
│   ├── value_objects/         # Value objects (CadCode, MultiviewImage, etc.)
│   ├── services/              # Domain service interfaces
│   └── repositories/          # Repository interfaces
│
├── application/               # Application layer
│   ├── workflow/              # LangGraph workflow
│   │   ├── nodes/             # Workflow nodes
│   │   ├── graph_builder.py   # Graph construction
│   │   └── workflow_state.py  # State definitions
│   ├── use_cases/             # Use cases
│   ├── services/              # Report generation
│   └── dto/                   # Data transfer objects
│
├── infrastructure/            # Infrastructure layer
│   ├── llm/                   # VLM integration (google-genai + Vertex AI)
│   ├── cad/                   # CAD rendering (build123d)
│   ├── repositories/          # Repository implementations
│   └── services/              # Service implementations
│
└── presentation/              # Presentation layer
    └── cli/                   # CLI entry point
```

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

Create a `.env` file:

```bash
# Google Cloud project
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global

# Vertex AI model
VERTEX_AI_MODEL_NAME=gemini-3.1-flash-lite-preview
```

### 3. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 4. Run tests

```bash
uv run pytest tests/ -v
```

## Usage

### Run the pipeline

Process a paired-format dataset: image → CAD generation → evaluation against ground truth → report generation:

```bash
# Basic usage
uv run python -m presentation.cli.main pipeline \
    --input data/sample \
    --output-dir data/output/pipeline_results

# Process only the first 10 models
uv run python -m presentation.cli.main pipeline \
    --input data/sample \
    --limit 10 \
    --output-dir data/output/pipeline_results

# Reprocess even if output already exists
uv run python -m presentation.cli.main pipeline \
    --input data/sample \
    --output-dir data/output/pipeline_results \
    --no-skip-existing
```

**Options:**
- `--input, -i`: Input directory (paired format, required)
- `--output-dir, -o`: Output directory (default: `data/output/pipeline_{timestamp}`)
- `--limit, -l`: Maximum number of models to process
- `--no-skip-existing`: Reprocess models even if output exists
- `--model`: VLM model name (default: `VERTEX_AI_MODEL_NAME` env variable)

### Input directory format (paired)

```
input_dir/
├── images/
│   ├── model_a.jpg
│   ├── model_b.png
│   └── ...
└── step/
    ├── model_a.step  (or .stp)
    ├── model_b.step
    └── ...
```

### Output

```
output_dir/
├── {model_name}/           # Per-model output
│   ├── {model_name}.step   # Generated STEP file
│   ├── {model_name}.py     # Generated CAD code
│   └── result.json         # Individual results (with metrics)
├── report.md               # Markdown report
└── pipeline_result.json    # JSON report
```

### Evaluation metrics

| Metric | Description | Direction |
|--------|-------------|-----------|
| PCD | Point Cloud Distance | ↓ Lower is better |
| HDD | Hausdorff Distance | ↓ Lower is better |
| IoU | Intersection over Union | ↑ Higher is better |
| DSC | Dice Similarity Coefficient | ↑ Higher is better |
| Topology Error | Euler characteristic difference | ↓ Lower is better |

### Generate comparison report

Generate a report comparing results across multiple methods:

```bash
uv run python scripts/generate_comparison_report.py
```

## Pipeline flow

```
Input image → VLM (CAD code generation) → build123d (STEP export) → Evaluation against ground truth
```

1. **Input**: Paired-format dataset (images + ground truth STEP files)
2. **Generation**: VLM generates build123d CAD code from images (1-shot)
3. **Rendering**: build123d executes the CAD code and exports STEP files
4. **Evaluation**: Computes geometric metrics between generated and ground truth STEP files
5. **Report**: Outputs results as Markdown and JSON reports

## Sample data

`data/sample/` includes test cases from the NIST MBE PMI project.

```bash
# Quick test with sample data
uv run python -m presentation.cli.main pipeline \
    --input data/sample \
    --output-dir data/output/sample_results
```

## License

### Sample data (data/sample/)

The CAD models and STEP files in `data/sample/` were obtained from the [NIST MBE PMI Validation and Conformance Testing](https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-validation) project.

These files were created by NIST, a U.S. federal government agency, and are in the public domain under [Title 17 U.S.C. Section 105](https://www.govinfo.gov/content/pkg/USCODE-2021-title17/html/USCODE-2021-title17-chap1-sec105.htm).
