from pathlib import Path

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_file
from pietto.semantic import analyze


EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."

EXPECTED_WARNINGS = {
    Path("examples/sources/users.pie"): (
        (
            "PIE-S2303",
            Severity.WARNING,
            11,
            1,
            "Source raw_events has no bound shape; row schema is unknown",
        ),
    ),
}


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_example_has_no_semantic_errors(path: Path) -> None:
    parse_result = parse_file(path)

    assert parse_result.diagnostics == (), _format_diagnostics(
        path,
        "parser",
        parse_result.diagnostics,
    )
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    errors = tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )

    assert errors == (), _format_diagnostics(path, "semantic", errors)


def test_committed_example_warnings_are_explicit_and_stable() -> None:
    actual: dict[Path, tuple[tuple[str, Severity, int, int, str], ...]] = {}

    for path in EXAMPLE_PATHS:
        parse_result = parse_file(path)
        assert parse_result.ast is not None
        warnings = tuple(
            (
                diagnostic.code,
                diagnostic.severity,
                diagnostic.location.line,
                diagnostic.location.column,
                diagnostic.message,
            )
            for diagnostic in analyze(parse_result.ast).diagnostics
            if diagnostic.severity is Severity.WARNING
        )
        if warnings:
            actual[path] = warnings

    assert actual == EXPECTED_WARNINGS


def _format_diagnostics(
    path: Path,
    stage: str,
    diagnostics: tuple[Diagnostic, ...],
) -> str:
    """Format example failures with paths and structured diagnostic details."""

    details = "\n".join(
        (
            f"{diagnostic.severity.value} {diagnostic.code} "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}"
        )
        for diagnostic in diagnostics
    )
    return f"{path} produced {stage} diagnostics:\n{details}"
