"""Internal serializers for the CLI JSON v1 contract.

The normative machine-readable interface is documented in
``docs/spec/cli-json-v1.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.sql import SqlArtifact

_SCHEMA_VERSION = 1
_CLI_ERROR_KINDS = frozenset(
    {
        "file_read",
        "output_path",
        "output_write",
        "usage",
        "unsupported_dialect",
    }
)
_SEVERITIES = frozenset({"error", "warning", "info"})


@dataclass(frozen=True, slots=True)
class CliError:
    """One handled CLI error that is separate from compiler diagnostics."""

    kind: str
    message: str
    path: str | Path | None = None

    def __post_init__(self) -> None:
        """Reject unstable CLI error kinds at the serialization boundary."""

        if self.kind not in _CLI_ERROR_KINDS:
            raise ValueError(f"Unsupported CLI error kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class OutputStatus:
    """The requested SQL output path and whether it was written."""

    path: str | Path
    written: bool


def diagnostic_to_json_dict(
    diagnostic: Diagnostic,
    *,
    fallback_path: str | Path | None = None,
) -> dict[str, object]:
    """Serialize one diagnostic using the stable JSON v1 field set."""

    location = cast(SourceLocation | None, diagnostic.location)
    return {
        "code": diagnostic.code,
        "severity": _severity_value(diagnostic.severity),
        "message": diagnostic.message,
        "location": _location_to_json_dict(
            location,
            fallback_path=fallback_path,
        ),
        "suggestion": diagnostic.suggestion,
    }


def cli_error_to_json_dict(error: CliError) -> dict[str, object]:
    """Serialize one handled CLI error without inventing a diagnostic code."""

    return {
        "kind": error.kind,
        "message": error.message,
        "path": _path_text(error.path),
    }


def artifact_to_json_dict(artifact: SqlArtifact) -> dict[str, object]:
    """Serialize one SQL artifact without changing its SQL text."""

    return {
        "kind": artifact.kind.value,
        "name": artifact.name,
        "sql": artifact.sql,
    }


def check_result_to_json_dict(
    *,
    path: str | Path | None,
    diagnostics: Sequence[Diagnostic] = (),
    cli_errors: Sequence[CliError] = (),
) -> dict[str, object]:
    """Build one complete JSON-compatible check result."""

    return {
        "schema_version": _SCHEMA_VERSION,
        "command": "check",
        "ok": _result_is_ok(diagnostics, cli_errors),
        "path": _path_text(path),
        "diagnostics": [
            diagnostic_to_json_dict(diagnostic, fallback_path=path)
            for diagnostic in diagnostics
        ],
        "cli_errors": [cli_error_to_json_dict(error) for error in cli_errors],
    }


def emit_sql_result_to_json_dict(
    *,
    path: str | Path | None,
    dialect: str | None,
    diagnostics: Sequence[Diagnostic] = (),
    cli_errors: Sequence[CliError] = (),
    artifacts: Sequence[SqlArtifact] = (),
    output: OutputStatus | None = None,
) -> dict[str, object]:
    """Build one complete JSON-compatible emit-sql result."""

    return {
        "schema_version": _SCHEMA_VERSION,
        "command": "emit-sql",
        "ok": _result_is_ok(diagnostics, cli_errors),
        "path": _path_text(path),
        "dialect": dialect,
        "diagnostics": [
            diagnostic_to_json_dict(diagnostic, fallback_path=path)
            for diagnostic in diagnostics
        ],
        "cli_errors": [cli_error_to_json_dict(error) for error in cli_errors],
        "artifacts": [artifact_to_json_dict(artifact) for artifact in artifacts],
        "output": _output_to_json_dict(output),
    }


def render_json_document(document: Mapping[str, object]) -> str:
    """Render exactly one ASCII JSON document followed by one newline."""

    return f"{json.dumps(document, ensure_ascii=True)}\n"


def _location_to_json_dict(
    location: SourceLocation | None,
    *,
    fallback_path: str | Path | None,
) -> dict[str, object] | None:
    """Serialize one optional source location without fabricating coordinates."""

    if location is None:
        return None
    path = location.path if location.path is not None else _path_text(fallback_path)
    return {
        "path": path,
        "line": location.line,
        "column": location.column,
        "end_line": location.end_line,
        "end_column": location.end_column,
    }


def _output_to_json_dict(output: OutputStatus | None) -> dict[str, object] | None:
    """Serialize optional SQL output status."""

    if output is None:
        return None
    return {
        "path": str(output.path),
        "written": output.written,
    }


def _result_is_ok(
    diagnostics: Sequence[Diagnostic],
    cli_errors: Sequence[CliError],
) -> bool:
    """Compute JSON semantic success independently from process exit codes."""

    return not cli_errors and all(
        _severity_value(diagnostic.severity) != Severity.ERROR.value
        for diagnostic in diagnostics
    )


def _severity_value(severity: Severity | str) -> str:
    """Return and validate one stable lowercase severity string."""

    value = severity.value if isinstance(severity, Severity) else str(severity).lower()
    if value not in _SEVERITIES:
        raise ValueError(f"Unsupported diagnostic severity: {value}")
    return value


def _path_text(path: str | Path | None) -> str | None:
    """Normalize an optional path for JSON-compatible output."""

    return str(path) if path is not None else None
