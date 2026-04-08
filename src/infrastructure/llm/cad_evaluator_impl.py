"""CAD evaluator service implementation."""

import re
from pathlib import Path

from domain.services.cad_evaluator import CadEvaluatorService, EvaluationResult
from infrastructure.llm.vlm_client import VlmClient

EVALUATOR_SYSTEM_PROMPT = """You are an expert mechanical engineer evaluating how well a \
generated 3D CAD model matches a mechanical engineering drawing.

You will be shown:
1. The original mechanical engineering drawing (PDF) - can be one of these formats:
   - Single isometric/oblique view (oblique view from above): one image showing the part from an angle
   - Single PDF with multiple orthographic views (front, side, top views, etc.): front, top, side, section views
   - Multiple PDFs: each showing a different viewing angle
2. Rendered views of the generated 3D CAD model (multiview images)

Your task is to:
1. Analyze the mechanical drawing to understand the intended part geometry
2. Compare the rendered model views with the drawing
3. Identify matches and discrepancies in the mechanical part features
4. Provide a similarity score and detailed feedback for improvement

Evaluation criteria for mechanical parts:

A. Drawing Similarity (how well the model matches the drawing):
- Overall shape and proportions of the part
- Dimensional accuracy (lengths, widths, heights, diameters)
- Feature completeness:
  - Holes (through holes, blind holes, counterbores, countersinks)
  - Slots, grooves, and keyways
  - Chamfers and fillets
  - Threads (internal/external)
  - Bosses, ribs, and pockets
- Geometric relationships between features
- Symmetry and alignment
- Wall thicknesses and material distribution

B. Mechanical Functionality (does the part work as a mechanical component):
- Structural integrity: sufficient wall thickness, no critically thin sections
- Load-bearing capability: adequate material at stress concentration points
- Hole sizing: appropriate for fasteners (M3, M4, M5, M6, etc.)
- Clearances: proper fit and assembly considerations
- Manufacturability: can be machined, cast, or 3D printed
- No impossible geometry: no self-intersecting or floating features
- Practical proportions: features are realistically sized for mechanical use

Output format (MUST follow exactly):
REASONING: [Your detailed analysis comparing the mechanical drawing and rendered model]
SCORE: [A number between 0.0 and 1.0, where 1.0 means perfect match]
FEEDBACK: [Specific, actionable feedback for improving the CAD code to better match the mechanical drawing]

Example output:
REASONING: The base plate shape matches the drawing. However, the mounting holes are \
missing, the central bore diameter appears smaller than specified, and the chamfer \
on the edges is not present. From a mechanical functionality perspective, the wall \
thickness near the bore is too thin (only 2mm) which could cause structural failure \
under load.
SCORE: 0.45
FEEDBACK: [Drawing Issues] 1) Add 4x M6 mounting holes at the corner positions shown \
in the top view. 2) Increase the central bore diameter from 20mm to 25mm as specified. \
3) Add 2mm x 45° chamfers on all top edges. [Mechanical Issues] 4) Increase wall \
thickness around the central bore to at least 5mm for structural integrity. \
5) Ensure hole positions allow sufficient edge distance (min 2x hole diameter) to \
prevent crack propagation.
"""


class CadEvaluatorServiceImpl(CadEvaluatorService):
    """Implementation of CAD evaluator service using VLM."""

    def __init__(self, vlm_client: VlmClient) -> None:
        """
        Initialize the service.

        Args:
            vlm_client: VLM client for multimodal evaluation.
        """
        self._vlm_client = vlm_client

    async def evaluate(
        self,
        input_pdf_path: Path,
        rendered_image_paths: list[Path],
        cad_code: str,
    ) -> EvaluationResult:
        """
        Evaluate rendered CAD model against input technical drawing.

        Args:
            input_pdf_path: Path to the input technical drawing PDF.
            rendered_image_paths: Paths to rendered multiview images.
            cad_code: Current CAD code for context.

        Returns:
            EvaluationResult with score, feedback, and reasoning.
        """
        prompt = self._build_evaluation_prompt(cad_code)

        # Combine PDF and rendered images
        file_paths = [input_pdf_path] + list(rendered_image_paths)

        response = await self._vlm_client.generate_with_files(
            prompt=prompt,
            file_paths=file_paths,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            temperature=0.3,
        )

        return self._parse_response(response)

    def _build_evaluation_prompt(self, cad_code: str) -> str:
        """Build the evaluation prompt."""
        return f"""Compare the mechanical engineering drawing (first image/PDF) with the \
rendered 3D CAD model views (subsequent images).

The 3D mechanical part was generated from this build123d code:
```python
{cad_code}
```

Evaluate how well the rendered mechanical part matches the engineering drawing.

A. Drawing Similarity - Pay attention to:
- Overall part geometry and dimensions
- Mechanical features (holes, slots, chamfers, fillets, threads)
- Feature positions and relationships

B. Mechanical Functionality - Also evaluate:
- Is this a structurally sound mechanical part?
- Are wall thicknesses adequate for load-bearing?
- Are hole sizes appropriate for standard fasteners?
- Is the geometry manufacturable (no impossible features)?
- Would this part function correctly in a mechanical assembly?

Provide your analysis in the required format: REASONING, SCORE, and FEEDBACK.
The SCORE should reflect BOTH drawing similarity AND mechanical functionality.

The FEEDBACK should be specific and actionable, organized into two categories:
- [Drawing Issues]: Changes needed to match the engineering drawing
- [Mechanical Issues]: Changes needed for proper mechanical functionality (structural \
integrity, manufacturability, proper sizing for fasteners, adequate wall thickness, etc.)
"""

    def _parse_response(self, response: str) -> EvaluationResult:
        """Parse the evaluation response."""
        # Extract reasoning
        reasoning_match = re.search(
            r"REASONING:\s*(.*?)(?=SCORE:|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        reasoning = (
            reasoning_match.group(1).strip()
            if reasoning_match
            else "No reasoning provided"
        )

        # Extract score
        score_match = re.search(
            r"SCORE:\s*([\d.]+)",
            response,
            re.IGNORECASE,
        )
        if score_match:
            try:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                score = 0.0
        else:
            score = 0.0

        # Extract feedback
        feedback_match = re.search(
            r"FEEDBACK:\s*(.*?)$",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        feedback = (
            feedback_match.group(1).strip()
            if feedback_match
            else "No feedback provided"
        )

        return EvaluationResult(
            score=score,
            feedback=feedback,
            reasoning=reasoning,
        )
