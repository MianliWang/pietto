"""Private JSON v2 serializers for project check results."""

from __future__ import annotations

import json
from collections.abc import Mapping

from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryResult

_PROJECT_JSON_V2_VERSION = 2
_COMMAND = "check"
_MODE = "project"
_FILES_TOTAL = 0
_FILES_OK = 0
_FILES_WITH_ERRORS = 0


def project_check_result_to_json_dict(
    discovery_result: ProjectDiscoveryResult,
) -> dict[str, object]:
    """Build one project JSON v2 check result for root/config discovery only."""

    if discovery_result.inputs:
        raise ValueError(
            "project input JSON serialization is deferred until project source "
            "parsing exists"
        )

    return {
        "schema_version": _PROJECT_JSON_V2_VERSION,
        "command": _COMMAND,
        "mode": _MODE,
        "ok": discovery_result.ok,
        "project": _project_to_json_dict(discovery_result),
        "inputs": [],
        "diagnostics": [],
        "cli_errors": [
            _cli_error_to_json_dict(error) for error in discovery_result.errors
        ],
        "result": {
            "check": {
                "files_total": _FILES_TOTAL,
                "files_ok": _FILES_OK,
                "files_with_errors": _FILES_WITH_ERRORS,
            }
        },
    }


def render_project_json_document(document: Mapping[str, object]) -> str:
    """Render exactly one ASCII project JSON v2 document plus one newline."""

    return f"{json.dumps(document, ensure_ascii=True)}\n"


def _project_to_json_dict(
    discovery_result: ProjectDiscoveryResult,
) -> dict[str, object]:
    root = discovery_result.root.path if discovery_result.root is not None else None
    config_path = (
        discovery_result.config_path.path
        if discovery_result.config_path is not None
        else None
    )
    return {
        "root": root,
        "config_path": config_path,
    }


def _cli_error_to_json_dict(error: ProjectDiscoveryError) -> dict[str, object]:
    return {
        "kind": error.kind.value,
        "message": error.message,
        "path": error.path,
    }
