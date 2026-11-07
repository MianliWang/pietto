from pathlib import Path

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_file
from pietto.semantic import analyze


EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."

EXPECTED_WARNINGS = {
    Path("examples/sources/users.pietto"): (
        (
            "PIE-S2303",
            Severity.WARNING,
            6,
            1,
            "Source raw_events has no bound shape; row schema is unknown",
        ),
    ),
}


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_example_parses_and_analyzes_with_only_its_expected_warnings(
    path: Path,
) -> None:
    parse_result = parse_file(path)

    assert parse_result.diagnostics == (), _format_diagnostics(
        path,
        "parser",
        parse_result.diagnostics,
    )
    assert parse_result.ast is not None

    diagnostics = analyze(parse_result.ast).diagnostics
    errors = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    warnings = tuple(
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.location.line,
            diagnostic.location.column,
            diagnostic.message,
        )
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.WARNING
    )

    assert errors == (), _format_diagnostics(path, "semantic", errors)
    assert warnings == EXPECTED_WARNINGS.get(path, ())


def test_every_expected_example_warning_names_a_committed_example() -> None:
    assert set(EXPECTED_WARNINGS) <= set(EXAMPLE_PATHS)
    assert all(EXPECTED_WARNINGS.values())


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
