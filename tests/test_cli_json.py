from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.cli_json import (
    CliError,
    OutputStatus,
    artifact_to_json_dict,
    check_result_to_json_dict,
    cli_error_to_json_dict,
    diagnostic_to_json_dict,
    emit_sql_result_to_json_dict,
    render_json_document,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.sql import SqlArtifact, SqlArtifactKind


def test_diagnostic_serialization_has_fixed_fields_and_lowercase_severity() -> None:
    diagnostic = _diagnostic(
        severity=Severity.WARNING,
        path="example.pie",
        end_line=3,
        end_column=8,
        suggestion="Add explicit nullability.",
    )

    assert diagnostic_to_json_dict(diagnostic) == {
        "code": "PIE-S2005",
        "severity": "warning",
        "message": "Implicit nullability",
        "location": {
            "path": "example.pie",
            "line": 2,
            "column": 12,
            "end_line": 3,
            "end_column": 8,
        },
        "suggestion": "Add explicit nullability.",
    }


def test_diagnostic_location_uses_fallback_and_preserves_null_fields() -> None:
    diagnostic = _diagnostic(
        severity=Severity.WARNING,
        path=None,
    )

    result = diagnostic_to_json_dict(
        diagnostic,
        fallback_path=Path("fallback.pie"),
    )

    assert result["location"] == {
        "path": "fallback.pie",
        "line": 2,
        "column": 12,
        "end_line": None,
        "end_column": None,
    }
    assert result["suggestion"] is None


def test_diagnostic_location_can_be_null_without_fake_coordinates() -> None:
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="Unsupported backend emission case.",
        location=cast(SourceLocation, None),
    )

    result = diagnostic_to_json_dict(
        diagnostic,
        fallback_path="fallback.pie",
    )

    assert result["location"] is None


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_documented_severity_strings_are_supported(severity: str) -> None:
    diagnostic = Diagnostic(
        code="PIE-S2005",
        severity=cast(Severity, severity),
        message="message",
        location=SourceLocation(path=None, line=1, column=1),
    )

    assert diagnostic_to_json_dict(diagnostic)["severity"] == severity


def test_cli_error_serialization_has_fixed_fields_and_nullable_path() -> None:
    assert cli_error_to_json_dict(CliError(kind="usage", message="missing path")) == {
        "kind": "usage",
        "message": "missing path",
        "path": None,
    }
    assert cli_error_to_json_dict(
        CliError(
            kind="file_read",
            message="not found",
            path=Path("missing.pie"),
        )
    ) == {
        "kind": "file_read",
        "message": "not found",
        "path": "missing.pie",
    }


@pytest.mark.parametrize(
    "kind",
    [
        "file_read",
        "output_path",
        "output_write",
        "usage",
        "unsupported_dialect",
    ],
)
def test_documented_cli_error_kinds_are_supported(kind: str) -> None:
    assert CliError(kind=kind, message="message").kind == kind


def test_unsupported_cli_error_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported CLI error kind"):
        CliError(kind="unknown", message="message")


def test_check_result_ok_is_computed_from_diagnostics_and_cli_errors() -> None:
    warning = _diagnostic(severity=Severity.WARNING, path=None)
    error = _diagnostic(severity=Severity.ERROR, path=None)
    cli_error = CliError(kind="file_read", message="not found")

    assert check_result_to_json_dict(path=None)["ok"] is True
    assert (
        check_result_to_json_dict(
            path="example.pie",
            diagnostics=(warning,),
        )["ok"]
        is True
    )
    assert (
        check_result_to_json_dict(
            path="example.pie",
            diagnostics=(error,),
        )["ok"]
        is False
    )
    assert (
        check_result_to_json_dict(
            path=None,
            cli_errors=(cli_error,),
        )["ok"]
        is False
    )


def test_check_result_has_stable_top_level_schema_and_no_package_version() -> None:
    result = check_result_to_json_dict(path=Path("example.pie"))

    assert result == {
        "schema_version": 1,
        "command": "check",
        "ok": True,
        "path": "example.pie",
        "diagnostics": [],
        "cli_errors": [],
    }
    assert "version" not in result
    assert "package_version" not in result


def test_artifact_serialization_preserves_raw_sql_text() -> None:
    artifact = _artifact("active_users", "SELECT '\\n\x1b\x00\x7f雪'")

    assert artifact_to_json_dict(artifact) == {
        "kind": "relation",
        "name": "active_users",
        "sql": "SELECT '\\n\x1b\x00\x7f雪'",
    }


def test_emit_sql_result_preserves_artifacts_and_diagnostics_in_order() -> None:
    first = _artifact("first", "SELECT 1")
    second = _artifact("second", "SELECT 2")
    warning = _diagnostic(
        severity=Severity.WARNING,
        path=None,
        code="PIE-S2005",
        message="first warning",
    )
    error = _diagnostic(
        severity=Severity.ERROR,
        path="backend.pie",
        code="PIE-B1000",
        message="backend error",
    )

    result = emit_sql_result_to_json_dict(
        path=Path("input.pie"),
        dialect="postgres",
        diagnostics=(warning, error),
        artifacts=(first, second),
    )

    assert result["ok"] is False
    assert [item["name"] for item in result["artifacts"]] == ["first", "second"]
    assert [item["code"] for item in result["diagnostics"]] == [
        "PIE-S2005",
        "PIE-B1000",
    ]
    assert result["diagnostics"][0]["location"]["path"] == "input.pie"


@pytest.mark.parametrize("written", [True, False])
def test_emit_sql_result_serializes_output_status(written: bool) -> None:
    result = emit_sql_result_to_json_dict(
        path="input.pie",
        dialect="postgres",
        output=OutputStatus(path=Path("out.sql"), written=written),
    )

    assert result["output"] == {
        "path": "out.sql",
        "written": written,
    }


def test_emit_sql_result_has_nullable_path_dialect_and_output() -> None:
    result = emit_sql_result_to_json_dict(path=None, dialect=None)

    assert result == {
        "schema_version": 1,
        "command": "emit-sql",
        "ok": True,
        "path": None,
        "dialect": None,
        "diagnostics": [],
        "cli_errors": [],
        "artifacts": [],
        "output": None,
    }


def test_json_document_has_one_newline_and_round_trips_controls_unicode() -> None:
    value = 'quote" slash\\ newline\n esc\x1b nul\x00 del\x7f snow雪'
    document = render_json_document(
        check_result_to_json_dict(
            path=value,
            cli_errors=(CliError(kind="usage", message=value, path=value),),
        )
    )

    assert document.endswith("\n")
    assert not document.endswith("\n\n")
    assert "\x1b" not in document
    assert "\x00" not in document
    assert "\x7f" not in document
    assert "雪" not in document
    parsed = json.loads(document)
    assert parsed["path"] == value
    assert parsed["cli_errors"][0]["message"] == value


def test_json_helpers_are_not_wired_into_cli_behavior() -> None:
    source = inspect.getsource(cli)

    assert "cli_json" not in source
    assert "--format" not in source


def _diagnostic(
    *,
    severity: Severity,
    path: str | None,
    code: str = "PIE-S2005",
    message: str = "Implicit nullability",
    end_line: int | None = None,
    end_column: int | None = None,
    suggestion: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        location=SourceLocation(
            path=path,
            line=2,
            column=12,
            end_line=end_line,
            end_column=end_column,
        ),
        suggestion=suggestion,
    )


def _artifact(name: str, sql: str) -> SqlArtifact:
    return SqlArtifact(
        name=name,
        kind=SqlArtifactKind.RELATION,
        sql=sql,
    )
