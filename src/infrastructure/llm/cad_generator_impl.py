"""CAD generator service implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from domain.repositories.few_shot_repository import FewShotRepository
from domain.services.cad_code_validator import Build123dCodeValidator
from domain.services.cad_generator import CadGeneratorService
from domain.value_objects.cad_code import CadCode
from domain.value_objects.technical_drawing_image import TechnicalDrawingImage
from infrastructure.llm.prompt_templates.cad_generation import (
    BUILD123D_SYSTEM_PROMPT,
)
from infrastructure.llm.prompt_templates.technical_drawing import (
    TECHNICAL_DRAWING_SYSTEM_PROMPT,
    build_technical_drawing_with_examples_prompt,
)
from infrastructure.llm.vlm_client import VlmClient

if TYPE_CHECKING:
    from domain.services.cad_renderer import CadRendererService

MAX_FIX_RETRIES = 3


class CadGeneratorServiceImpl(CadGeneratorService):
    """Implementation of CAD generator service using VLM."""

    def __init__(
        self,
        vlm_client: VlmClient,
        few_shot_repository: FewShotRepository,
        cad_renderer: CadRendererService | None = None,
    ) -> None:
        """
        Initialize the service.

        Args:
            vlm_client: VLM client for text generation.
            few_shot_repository: Repository for few-shot examples.
            cad_renderer: Optional renderer for code validation.
        """
        self._vlm_client = vlm_client
        self._few_shot_repository = few_shot_repository
        self._cad_renderer = cad_renderer
        self._static_validator = Build123dCodeValidator()

    async def generate_from_technical_drawing(
        self,
        drawing: TechnicalDrawingImage,
        num_candidates: int,
        num_few_shot_examples: int,
        temperature: float,
    ) -> list[CadCode]:
        """
        Generate CAD code from technical drawing PDF.

        Args:
            drawing: Technical drawing with source PDF path.
            num_candidates: Number of CAD code candidates to generate.
            num_few_shot_examples: Number of few-shot examples to include.
            temperature: LLM temperature for generation.

        Returns:
            List of generated CAD codes.
        """
        examples = self._few_shot_repository.get_random_examples(num_few_shot_examples)
        examples_dict = [e.to_dict() for e in examples]

        generation_prompt = build_technical_drawing_with_examples_prompt(
            model_name=drawing.model_name,
            few_shot_examples=examples_dict,
        )

        # Use PDF directly instead of converted images
        pdf_path = drawing.source_pdf_path

        cad_codes = []
        for i in range(num_candidates):
            response = await self._vlm_client.generate_with_files(
                prompt=generation_prompt,
                file_paths=[pdf_path],
                system_prompt=TECHNICAL_DRAWING_SYSTEM_PROMPT,
                temperature=temperature,
            )

            code = self._extract_code(response)
            cad_code = CadCode(code=code)

            # Validate and fix code if renderer is available
            if self._cad_renderer is not None:
                cad_code = await self._validate_and_fix_code(
                    cad_code=cad_code,
                    temperature=temperature,
                    candidate_index=i + 1,
                )

            cad_codes.append(cad_code)

        return cad_codes

    async def _validate_and_fix_code(
        self,
        cad_code: CadCode,
        temperature: float,
        candidate_index: int = 1,
    ) -> CadCode:
        """
        Validate CAD code and fix errors if needed.

        Runs static validation first (fast, regex-based) to auto-fix known
        issues, then falls back to subprocess execution for full validation.

        Args:
            cad_code: CAD code to validate.
            temperature: LLM temperature for fix generation.
            candidate_index: Index of current candidate for logging.

        Returns:
            Valid CAD code (original or fixed).

        Raises:
            Exception: If code cannot be fixed after max retries.
        """
        if self._cad_renderer is None:
            return cad_code

        current_code = cad_code

        # Static validation and auto-fix before subprocess execution
        static_result = self._static_validator.validate_and_fix(current_code.code)
        if static_result.fixed_code is not None:
            print(
                f"[STATIC-FIX] Candidate {candidate_index}: "
                f"Applied auto-fixes to generated code"
            )
            current_code = CadCode(code=static_result.fixed_code)

        for attempt in range(MAX_FIX_RETRIES + 1):
            is_valid, error_message = await self._cad_renderer.validate_code(current_code)

            if is_valid:
                if attempt > 0:
                    print(
                        f"[FIX] Candidate {candidate_index}: "
                        f"Code fixed successfully after {attempt} attempt(s)"
                    )
                return current_code

            if attempt < MAX_FIX_RETRIES:
                print(
                    f"[FIX] Candidate {candidate_index} (attempt {attempt + 1}): "
                    f"{error_message}"
                )
                print("[FIX] Attempting to fix code...")

                # Enhance error message with static analysis context
                static_check = self._static_validator.validate(current_code.code)
                static_context = self._static_validator.format_issues_for_llm(
                    static_check
                )
                enhanced_error = error_message or "Unknown error"
                if static_context:
                    enhanced_error += f"\n\n{static_context}"

                current_code = await self.fix_code_error(
                    cad_code=current_code,
                    error_message=enhanced_error,
                    temperature=temperature,
                )

                # Apply static auto-fixes to the LLM-fixed code too
                fix_result = self._static_validator.validate_and_fix(current_code.code)
                if fix_result.fixed_code is not None:
                    current_code = CadCode(code=fix_result.fixed_code)
            else:
                print(
                    f"[FIX] Candidate {candidate_index}: "
                    f"Failed to fix code after {MAX_FIX_RETRIES} attempts"
                )
                raise Exception(
                    f"Failed to generate valid code after {MAX_FIX_RETRIES} fix attempts. "
                    f"Last error: {error_message}"
                )

        return current_code

    async def fix_code_error(
        self,
        cad_code: CadCode,
        error_message: str,
        temperature: float,
    ) -> CadCode:
        """
        Fix errors in CAD code based on error message.

        Args:
            cad_code: CAD code with errors.
            error_message: Error message from code execution.
            temperature: LLM temperature for generation.

        Returns:
            Fixed CAD code.
        """
        fix_prompt = f"""The following build123d code has an error. Fix the code.

Current Code:
```python
{cad_code.code}
```

Error Message:
{error_message}

Common fixes:
1. extrude: Call `extrude(amount=X)` AFTER BuildSketch closes, NOT inside it. NEVER pass a sketch object.
2. Plane: Use `Plane.XY.offset(z)` NOT `Plane(face)` or `Plane(variable)`
3. Mode: Use `mode=Mode.SUBTRACT` for cutting operations (holes, pockets)
4. Result: Ensure `result = part.part` is at the end, outside all `with` blocks
5. Import: `from build123d import *` must be at line 1 with no indentation
6. Context: ALL shape operations must be inside `with BuildPart():`
7. Parameters: RegularPolygon uses `side_count=` not `sides=`
8. Locations: Use `with Locations((x,y)):` not `Locations.current`
9. fillet/chamfer: These can fail on certain edges -- wrap in try/except to prevent crashes
10. Vector: Use UPPERCASE .X, .Y, .Z (not .x, .y, .z) for Vector properties -- e.g. edge.center().X
11. Rotation: Use UPPERCASE kwargs Rotation(X=, Y=, Z=) NOT Rotation(x=, y=, z=)
12. Plane context: Use `with BuildSketch(Plane.XY.offset(z)):` NOT `with Plane.XY.offset(z):` -- Plane is NOT a context manager
13. Locations: Use float tuples `Locations((x,y))` NOT `Locations(Vector(...))` or `Locations(face.center())`

Output ONLY the fixed Python code.
The code must define a variable 'result' containing the final Part.

```python
"""
        response = await self._vlm_client.generate_text(
            prompt=fix_prompt,
            system_prompt=BUILD123D_SYSTEM_PROMPT,
            temperature=temperature,
        )

        code = self._extract_code(response)
        return CadCode(code=code)

    def _extract_code(self, response: str) -> str:
        """
        Extract Python code from LLM response.

        Args:
            response: Raw LLM response.

        Returns:
            Extracted Python code.
        """
        code_pattern = r"```python\s*(.*?)\s*```"
        matches = re.findall(code_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        code_pattern2 = r"```\s*(.*?)\s*```"
        matches2 = re.findall(code_pattern2, response, re.DOTALL)

        if matches2:
            return matches2[0].strip()

        return response.strip()
