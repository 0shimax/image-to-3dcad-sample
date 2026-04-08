"""Code validation result value objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeValidationIssue:
    """
    A single validation issue found in build123d code.

    Attributes:
        pattern_name: Identifier for the error pattern (e.g., "missing_import").
        severity: Either "error" or "warning".
        message: Human-readable description of the issue.
        suggested_fix: Auto-fix suggestion if available, None otherwise.
    """

    pattern_name: str
    severity: str
    message: str
    suggested_fix: str | None = None


@dataclass(frozen=True)
class CodeValidationResult:
    """
    Result of static code validation.

    Attributes:
        is_valid: True if no errors were found (warnings are OK).
        issues: Tuple of all issues found.
        fixed_code: Auto-fixed code if fixes were applied, None otherwise.
    """

    is_valid: bool
    issues: tuple[CodeValidationIssue, ...]
    fixed_code: str | None = None
