"""Emit one exact Project Explain differential observation from real inputs."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys

from _pietto_project_explain_scenarios import (
    EXTENSION_REQUIREMENT,
    _fact,
    _manifest,
    _multi_package_multi_target_project,
    _profile,
    _target,
    _write_single_project,
)
from pietto._project_explain.json_v1 import (
    project_explain_envelope_to_json_value,
    serialize_project_explain_json_document,
)
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)
from pietto._project_explain.text import render_project_explain_text


OBSERVATION_FORMAT = "pietto.project-explain-differential.v1"
SCENARIO_ORDER = ("matrix", "empty", "portable", "diagnostic", "resource")
_CLI_CODE = (
    "import sys\nfrom pietto.cli import main\nraise SystemExit(main(sys.argv[1:]))\n"
)


def _run_cli(
    arguments: tuple[str, ...], cwd: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (sys.executable, "-c", _CLI_CODE, *arguments),
        check=False,
        capture_output=True,
        cwd=cwd,
        env=os.environ.copy(),
    )


def _project_observation(root: Path, cwd: Path) -> dict[str, object]:
    result = _build_project_explain_runtime(root)
    json_document = serialize_project_explain_json_document(result.envelope)
    text_document = render_project_explain_text(result.envelope).encode()
    expected_exit = {
        ProjectExplainRuntimeOutcome.SUCCESS: 0,
        ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR: 1,
        ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR: 2,
    }[result.outcome]
    json_cli = _run_cli(
        ("explain", "--project", root.as_posix(), "--format", "json"),
        cwd,
    )
    text_cli = _run_cli(("explain", "--project", root.as_posix()), cwd)
    if result.outcome is ProjectExplainRuntimeOutcome.SUCCESS:
        expected_text_stdout, expected_text_stderr = text_document, b""
    else:
        expected_text_stdout, expected_text_stderr = b"", text_document
    assert (
        json_cli.returncode,
        json_cli.stdout,
        json_cli.stderr,
    ) == (expected_exit, json_document, b"")
    assert (
        text_cli.returncode,
        text_cli.stdout,
        text_cli.stderr,
    ) == (expected_exit, expected_text_stdout, expected_text_stderr)
    assert json_document.endswith(b"\n") and not json_document.endswith(b"\n\n")
    assert not json_document.startswith(b"\xef\xbb\xbf")
    assert text_document.endswith(b"\n") and not text_document.endswith(b"\n\n")
    return {
        "runtime_outcome": result.outcome.value,
        "structured": project_explain_envelope_to_json_value(result.envelope),
        "json_document": json_document.decode("utf-8"),
        "text_document": text_document.decode("utf-8"),
        "cli_json_exit": json_cli.returncode,
        "cli_text_exit": text_cli.returncode,
    }


def _single_file_observation(workspace: Path) -> dict[str, object]:
    source = workspace / "single.pietto"
    source.write_text("shape Row:\n    id: Int not null\n", encoding="utf-8")
    text_cli = _run_cli(("explain", "single.pietto"), workspace)
    json_cli = _run_cli(
        ("explain", "single.pietto", "--format", "json"),
        workspace,
    )
    assert text_cli.returncode == json_cli.returncode == 0
    assert text_cli.stderr == json_cli.stderr == b""
    assert text_cli.stdout.endswith(b"\n")
    assert json_cli.stdout.endswith(b"\n") and not json_cli.stdout.endswith(b"\n\n")
    return {
        "text_document": text_cli.stdout.decode("utf-8"),
        "json_document": json_cli.stdout.decode("utf-8"),
        "text_exit": text_cli.returncode,
        "json_exit": json_cli.returncode,
    }


def _projects(workspace: Path) -> dict[str, Path]:
    matrix = _multi_package_multi_target_project(workspace, "matrix")
    empty = _write_single_project(
        workspace,
        _manifest(2, requirements=(EXTENSION_REQUIREMENT,)),
        name="empty",
    )
    portable = _write_single_project(
        workspace,
        _manifest(1),
        profiles=(_profile("base", "18"),),
        targets=(_target("base", "18", None),),
        name="portable",
    )
    diagnostic = _write_single_project(
        workspace,
        _manifest(2, requirements=(EXTENSION_REQUIREMENT,)),
        profiles=(
            _profile("base", "18"),
            _profile(
                "vector",
                "18",
                kind="overlay",
                facts=(
                    _fact(
                        "supported",
                        "extension_signature",
                        operation="vector-native-type",
                        dialect="postgresql",
                        extension="vector",
                    ),
                ),
            ),
        ),
        targets=(_target("base", "18", "vector"),),
        name="diagnostic",
    )
    return {
        "matrix": matrix,
        "empty": empty,
        "portable": portable,
        "diagnostic": diagnostic,
        "resource": workspace / "missing",
    }


def observation(workspace: Path) -> dict[str, object]:
    """Return the complete ordered observation without environmental metadata."""

    workspace.mkdir(parents=True, exist_ok=True)
    cwd = workspace / "cwd"
    cwd.mkdir()
    projects = _projects(workspace)
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "scenarios": {
            name: _project_observation(projects[name], cwd) for name in SCENARIO_ORDER
        },
        "single_file": _single_file_observation(workspace),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    namespace = parser.parse_args(argv)
    document = (
        json.dumps(
            observation(namespace.workspace),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    sys.stdout.buffer.write(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
