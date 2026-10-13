from __future__ import annotations

import json
from typing import cast

import pytest

from pietto._project.json_v2 import (
    project_check_result_to_json_dict,
    render_project_json_document,
)
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParseCheckResult,
    ProjectRoot,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

_TOP_LEVEL_KEYS = (
    "schema_version",
    "command",
    "mode",
    "ok",
    "project",
    "inputs",
    "diagnostics",
    "cli_errors",
    "result",
)


def test_project_json_v2_success_shape_and_rendering_are_locked() -> None:
    document = project_check_result_to_json_dict(
        ProjectParseCheckResult(
            root=ProjectRoot(path="."),
            config_path=ProjectConfigPath(path="pietto.toml"),
            inputs=(
                ProjectInput(path="models/users.pietto", status="parsed"),
                ProjectInput(path="reports/broken.pietto", status="error"),
            ),
            errors=(),
            diagnostics=(
                Diagnostic(
                    code="PIE-P1000",
                    severity=Severity.ERROR,
                    message="mismatched input",
                    location=SourceLocation(
                        path="reports/broken.pietto",
                        line=1,
                        column=7,
                    ),
                ),
            ),
        )
    )

    assert tuple(document) == _TOP_LEVEL_KEYS
    assert document == {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": False,
        "project": {
            "root": ".",
            "config_path": "pietto.toml",
        },
        "inputs": [
            {
                "path": "models/users.pietto",
                "kind": "source",
                "status": "parsed",
            },
            {
                "path": "reports/broken.pietto",
                "kind": "source",
                "status": "error",
            },
        ],
        "diagnostics": [
            {
                "code": "PIE-P1000",
                "severity": "error",
                "message": "mismatched input",
                "location": {
                    "path": "reports/broken.pietto",
                    "line": 1,
                    "column": 7,
                    "end_line": None,
                    "end_column": None,
                },
                "suggestion": None,
                "related_locations": [],
            }
        ],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 2,
                "files_ok": 1,
                "files_with_errors": 1,
            }
        },
    }

    rendered = render_project_json_document(document)
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")
    assert json.loads(rendered) == document


def test_project_json_v2_appends_semantic_diagnostics_without_shape_change() -> None:
    document = project_check_result_to_json_dict(
        ProjectParseCheckResult(
            root=ProjectRoot(path="."),
            config_path=ProjectConfigPath(path="pietto.toml"),
            inputs=(ProjectInput(path="models/users.pietto", status="parsed"),),
            errors=(),
            diagnostics=(),
        ),
        semantic_diagnostics=(
            Diagnostic(
                code="PIE-S2301",
                severity=Severity.ERROR,
                message="Unknown relation: missing",
                location=SourceLocation(
                    path="models/users.pietto",
                    line=2,
                    column=5,
                ),
            ),
        ),
    )

    assert tuple(document) == _TOP_LEVEL_KEYS
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "models/users.pietto",
            "kind": "source",
            "status": "parsed",
        }
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    assert document["diagnostics"] == [
        {
            "code": "PIE-S2301",
            "severity": "error",
            "message": "Unknown relation: missing",
            "location": {
                "path": "models/users.pietto",
                "line": 2,
                "column": 5,
                "end_line": None,
                "end_column": None,
            },
            "suggestion": None,
            "related_locations": [],
        }
    ]


def test_project_json_v2_root_failure_uses_nullable_project_identity() -> None:
    document = project_check_result_to_json_dict(
        ProjectDiscoveryResult(
            root=None,
            config_path=None,
            inputs=(),
            errors=(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_ROOT,
                    "Project root must be an existing directory.",
                    None,
                ),
            ),
        )
    )

    assert tuple(document) == _TOP_LEVEL_KEYS
    assert document["ok"] is False
    assert document["project"] == {"root": None, "config_path": None}
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "project_root",
            "message": "Project root must be an existing directory.",
            "path": None,
        }
    ]
    check = cast(dict[str, int], cast(dict[str, object], document["result"])["check"])
    assert check == {
        "files_total": 0,
        "files_ok": 0,
        "files_with_errors": 0,
    }


@pytest.mark.parametrize(
    "message",
    [
        "Project configuration file is required.",
        "Project configuration path must be a regular file.",
    ],
)
def test_project_json_v2_config_failure_keeps_attributable_config_path(
    message: str,
) -> None:
    document = project_check_result_to_json_dict(
        ProjectDiscoveryResult(
            root=ProjectRoot(path="."),
            config_path=ProjectConfigPath(path="pietto.toml"),
            inputs=(),
            errors=(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.CONFIG_READ,
                    message,
                    "pietto.toml",
                ),
            ),
        )
    )

    assert document["ok"] is False
    assert document["project"] == {"root": ".", "config_path": "pietto.toml"}
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "config_read",
            "message": message,
            "path": "pietto.toml",
        }
    ]


def test_project_json_v2_rendering_is_ascii_safe() -> None:
    document = project_check_result_to_json_dict(
        ProjectDiscoveryResult(
            root=ProjectRoot(path="."),
            config_path=ProjectConfigPath(path="pietto.toml"),
            inputs=(),
            errors=(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.CONFIG_READ,
                    "配置失败",
                    "pietto.toml",
                ),
            ),
        )
    )

    rendered = render_project_json_document(document)

    assert "配置失败" not in rendered
    assert "\\u914d\\u7f6e\\u5931\\u8d25" in rendered
    assert json.loads(rendered)["cli_errors"][0]["message"] == "配置失败"


@pytest.mark.parametrize("status", ["selected", "parsed", "error"])
def test_project_json_v2_fails_closed_for_non_parse_discovery_inputs(
    status: str,
) -> None:
    discovery_result = ProjectDiscoveryResult(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(ProjectInput(path="models/users.pietto", status=status),),
        errors=(),
    )

    with pytest.raises(
        ValueError,
        match="project input JSON serialization requires parse-only project check",
    ):
        project_check_result_to_json_dict(discovery_result)
