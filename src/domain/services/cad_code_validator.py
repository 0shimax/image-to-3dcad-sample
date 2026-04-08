"""Static CAD code validator for build123d code."""

import re

from domain.value_objects.code_validation_result import (
    CodeValidationIssue,
    CodeValidationResult,
)


class Build123dCodeValidator:
    """
    Static validator for build123d Python code.

    Performs regex-based checks for common errors and
    applies auto-fixes where possible.
    """

    def validate(self, code: str) -> CodeValidationResult:
        """
        Validate build123d code for common issues.

        Args:
            code: Python code string to validate.

        Returns:
            CodeValidationResult with issues found.
        """
        issues: list[CodeValidationIssue] = []

        if "from build123d import" not in code:
            issues.append(
                CodeValidationIssue(
                    pattern_name="missing_import",
                    severity="error",
                    message="Missing 'from build123d import *'",
                    suggested_fix="from build123d import *",
                )
            )

        if not re.search(r"result\s*=", code):
            issues.append(
                CodeValidationIssue(
                    pattern_name="missing_result",
                    severity="error",
                    message=("Missing 'result' variable assignment"),
                )
            )

        # Check for lowercase Vector attributes
        if re.search(r"\.center\(\)\.[xyz]\b", code):
            issues.append(
                CodeValidationIssue(
                    pattern_name="lowercase_vector",
                    severity="error",
                    message=("Use uppercase .X, .Y, .Z for Vector properties"),
                )
            )

        # Check lowercase Rotation kwargs
        if re.search(r"Rotation\([^)]*[xyz]\s*=", code):
            issues.append(
                CodeValidationIssue(
                    pattern_name="lowercase_rotation",
                    severity="error",
                    message=("Use uppercase kwargs Rotation(X=, Y=, Z=)"),
                )
            )

        has_errors = any(i.severity == "error" for i in issues)
        return CodeValidationResult(
            is_valid=not has_errors,
            issues=tuple(issues),
        )

    def validate_and_fix(self, code: str) -> CodeValidationResult:
        """
        Validate and auto-fix build123d code where possible.

        Args:
            code: Python code string to validate and fix.

        Returns:
            CodeValidationResult with fixed_code if fixes
            were applied.
        """
        result = self.validate(code)
        if result.is_valid:
            return result

        fixed = code
        applied_fixes = False

        # Auto-fix missing import
        if "from build123d import" not in fixed:
            fixed = "from build123d import *\n" + fixed
            applied_fixes = True

        # Auto-fix lowercase vector attributes
        fixed_vec = re.sub(r"\.center\(\)\.x\b", ".center().X", fixed)
        fixed_vec = re.sub(r"\.center\(\)\.y\b", ".center().Y", fixed_vec)
        fixed_vec = re.sub(r"\.center\(\)\.z\b", ".center().Z", fixed_vec)
        if fixed_vec != fixed:
            fixed = fixed_vec
            applied_fixes = True

        if applied_fixes:
            return CodeValidationResult(
                is_valid=result.is_valid,
                issues=result.issues,
                fixed_code=fixed,
            )

        return result

    def format_issues_for_llm(self, result: CodeValidationResult) -> str:
        """
        Format validation issues for LLM context.

        Args:
            result: Validation result to format.

        Returns:
            Formatted string describing issues.
        """
        if not result.issues:
            return ""

        lines = ["Static analysis found these issues:"]
        for issue in result.issues:
            lines.append(f"- [{issue.severity}] {issue.message}")
        return "\n".join(lines)
