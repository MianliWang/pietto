"""Private JSON v2 serializers for project check results."""

from __future__ import annotations

import json
from collections.abc import Mapping

from pietto import cli_json
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParseCheckResult,
)
from pietto.errors import Diagnostic

_PROJECT_JSON_V2_VERSION = 2
_COMMAND = "check"
_MODE = "project"
_JSON_INPUT_KIND = "source"
_JSON_INPUT_STATUSES = frozenset({"parsed", "error"})


def project_check_result_to_json_dict(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> dict[str, object]:
    """Build one project JSON v2 check result."""

    inputs = _inputs_to_json_list(result)
    diagnostics = _diagnostics_to_json_list(result)
    counters = _check_counters(inputs)

    return {
        "schema_version": _PROJECT_JSON_V2_VERSION,
        "command": _COMMAND,
        "mode": _MODE,
        "ok": result.ok,
        "project": _project_to_json_dict(result),
        "inputs": inputs,
        "diagnostics": diagnostics,
        "cli_errors": [_cli_error_to_json_dict(error) for error in result.errors],
        "result": {
            "check": counters,
        },
    }


def render_project_json_document(document: Mapping[str, object]) -> str:
    """Render exactly one ASCII project JSON v2 document plus one newline."""

    return f"{json.dumps(document, ensure_ascii=True)}\n"


def _project_to_json_dict(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> dict[str, object]:
    root = result.root.path if result.root is not None else None
    config_path = result.config_path.path if result.config_path is not None else None
    return {
        "root": root,
        "config_path": config_path,
    }


def _inputs_to_json_list(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> list[dict[str, object]]:
    if isinstance(result, ProjectDiscoveryResult):
        if result.inputs:
            raise ValueError(
                "project input JSON serialization requires parse-only project check"
            )
        return []

    inputs: list[dict[str, object]] = []
    for project_input in result.inputs:
        if project_input.status not in _JSON_INPUT_STATUSES:
            if result.errors:
                return []
            raise ValueError(
                f"project input status is not JSON-reportable: {project_input.status}"
            )
        inputs.append(_input_to_json_dict(project_input))
    return inputs


def _input_to_json_dict(project_input: ProjectInput) -> dict[str, object]:
    return {
        "path": project_input.path,
        "kind": _JSON_INPUT_KIND,
        "status": project_input.status,
    }


def _diagnostics_to_json_list(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> list[dict[str, object]]:
    if not isinstance(result, ProjectParseCheckResult):
        return []
    return [_diagnostic_to_json_dict(diagnostic) for diagnostic in result.diagnostics]


def _diagnostic_to_json_dict(diagnostic: Diagnostic) -> dict[str, object]:
    diagnostic_json = cli_json.diagnostic_to_json_dict(diagnostic)
    diagnostic_json["related_locations"] = []
    return diagnostic_json


def _check_counters(inputs: list[dict[str, object]]) -> dict[str, int]:
    files_ok = sum(1 for project_input in inputs if project_input["status"] == "parsed")
    files_with_errors = sum(
        1 for project_input in inputs if project_input["status"] == "error"
    )
    return {
        "files_total": len(inputs),
        "files_ok": files_ok,
        "files_with_errors": files_with_errors,
    }


def _cli_error_to_json_dict(error: ProjectDiscoveryError) -> dict[str, object]:
    return {
        "kind": error.kind.value,
        "message": error.message,
        "path": error.path,
    }
