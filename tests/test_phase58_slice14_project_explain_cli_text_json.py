from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto._project_explain.text as project_text
import test_phase58_slice13_project_explain_runtime_builder as slice13
from pietto._project_explain.json_v1 import serialize_project_explain_json_document
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeBuildResult,
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)
from pietto._project_explain.text import render_project_explain_text


REPO_ROOT = Path(__file__).resolve().parents[1]


def _schema3_project(tmp_path: Path, name: str = "schema3") -> Path:
    return slice13._write_project(
        tmp_path,
        slice13._schema3_extension_manifest(),
        targets=True,
        name=name,
    )


def _diagnostic_project(tmp_path: Path) -> Path:
    return slice13._write_project(
        tmp_path,
        slice13._manifest(
            2,
            requirements=(slice13.EXTENSION_REQUIREMENT,),
        ),
        targets=True,
        name="diagnostic",
    )


def _counted_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> list[Path]:
    calls: list[Path] = []

    def build(root: str | Path) -> ProjectExplainRuntimeBuildResult:
        calls.append(Path(root))
        return _build_project_explain_runtime(root)

    monkeypatch.setattr(cli, "_build_project_explain_runtime", build)
    return calls


def test_project_default_and_explicit_text_are_identical_and_call_builder_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _schema3_project(tmp_path)
    expected = render_project_explain_text(
        _build_project_explain_runtime(root).envelope
    )
    calls = _counted_builder(monkeypatch)

    assert cli.main(["explain", "--project", str(root)]) == 0
    default = capsys.readouterr()
    assert default.out == expected and default.err == ""
    assert calls == [root]

    assert cli.main(["explain", "--project", str(root), "--format", "text"]) == 0
    explicit = capsys.readouterr()
    assert explicit == default
    assert calls == [root, root]


def test_project_json_success_is_exact_existing_serializer_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root = _schema3_project(tmp_path)
    envelope = _build_project_explain_runtime(root).envelope
    expected = serialize_project_explain_json_document(envelope)
    calls = _counted_builder(monkeypatch)

    assert cli.main(["explain", "--project", str(root), "--format", "json"]) == 0

    captured = capsysbinary.readouterr()
    assert captured.out == expected
    assert captured.err == b""
    assert calls == [root]
    assert captured.out.endswith(b"\n") and not captured.out.endswith(b"\n\n")
    assert captured.out.count(b"\n") == 1
    assert not captured.out.startswith(b"\xef\xbb\xbf")
    document = cast(dict[str, object], json.loads(captured.out))
    assert tuple(document) == ("format", "ok", "diagnostics", "payload")
    assert document["format"] == "pietto.project-explain.v1"
    assert document["ok"] is True and document["payload"] is not None
    assert {"outcome", "exit_code"}.isdisjoint(document)


@pytest.mark.parametrize(
    ("root_kind", "expected_outcome", "expected_exit"),
    (
        ("diagnostic", ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR, 1),
        ("resource", ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR, 2),
    ),
)
def test_project_json_failures_preserve_exact_structured_envelope_on_stdout(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
    root_kind: str,
    expected_outcome: ProjectExplainRuntimeOutcome,
    expected_exit: int,
) -> None:
    root = (
        _diagnostic_project(tmp_path)
        if root_kind == "diagnostic"
        else tmp_path / "missing"
    )
    result = _build_project_explain_runtime(root)
    assert result.outcome is expected_outcome
    expected = serialize_project_explain_json_document(result.envelope)

    assert (
        cli.main(["explain", "--project", str(root), "--format", "json"])
        == expected_exit
    )

    captured = capsysbinary.readouterr()
    assert captured.out == expected
    assert captured.err == b""
    document = cast(dict[str, object], json.loads(captured.out))
    assert document["ok"] is False
    assert document["payload"] is None
    assert cast(list[object], document["diagnostics"])


@pytest.mark.parametrize(
    ("root_kind", "expected_outcome", "expected_exit"),
    (
        ("diagnostic", ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR, 1),
        ("resource", ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR, 2),
    ),
)
def test_project_text_failures_render_only_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    root_kind: str,
    expected_outcome: ProjectExplainRuntimeOutcome,
    expected_exit: int,
) -> None:
    root = (
        _diagnostic_project(tmp_path)
        if root_kind == "diagnostic"
        else tmp_path / "missing"
    )
    result = _build_project_explain_runtime(root)
    assert result.outcome is expected_outcome

    assert cli.main(["explain", "--project", str(root)]) == expected_exit

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == render_project_explain_text(result.envelope)
    assert "status: failure" in captured.err
    assert "Payload\n  unavailable\n" in captured.err


def test_explain_parser_enforces_file_xor_project_and_exact_formats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "input.pietto"
    source.write_text("shape Row:\n    id: Int not null\n", encoding="utf-8")

    def unexpected(_root: str | Path) -> ProjectExplainRuntimeBuildResult:
        raise AssertionError("parser/file mode must not enter project runtime")

    monkeypatch.setattr(cli, "_build_project_explain_runtime", unexpected)
    assert cli.main(["explain"]) == 2
    missing = capsys.readouterr()
    assert missing.out == ""
    assert "the following arguments are required: path" in missing.err

    assert cli.main(["explain", str(source), "--project", str(tmp_path)]) == 2
    both = capsys.readouterr()
    assert both.out == ""
    assert "path and --project are mutually exclusive" in both.err

    assert cli.main(["explain", "--project", str(tmp_path), "--format", "yaml"]) == 2
    invalid = capsys.readouterr()
    assert invalid.out == ""
    assert "invalid choice" in invalid.err

    assert cli.main(["explain", "--help"]) == 0
    help_output = capsys.readouterr()
    assert "usage: pietto explain" in help_output.out
    assert "--project PROJECT" in help_output.out
    assert "--format {text,json}" in help_output.out
    assert help_output.err == ""

    assert cli.main(["explain", str(source)]) == 0
    file_mode = capsys.readouterr()
    assert file_mode.err == ""
    assert file_mode.out.startswith("Semantic Metadata Artifact v1\n")


def test_explicit_empty_target_project_is_successfully_and_truthfully_rendered(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = slice13._write_project(
        tmp_path,
        slice13._manifest(1),
        targets=False,
        name="empty-target",
    )

    assert cli.main(["explain", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Targets (0)\n    none" in captured.out
    assert "Package Target Evaluations (0)\n    none" in captured.out
    assert "Matrix Rows (0)\n    none" in captured.out
    assert "project: indeterminate reason=no-evaluated-targets requirements=0" in (
        captured.out
    )
    assert "unknown" not in captured.out.lower()
    assert "blocked" not in captured.out.lower()


def test_text_renderer_is_structured_deterministic_safe_and_private(
    tmp_path: Path,
) -> None:
    envelope = _build_project_explain_runtime(_schema3_project(tmp_path)).envelope
    first = render_project_explain_text(envelope)
    second = render_project_explain_text(envelope)

    assert first == second
    assert first.endswith("\n") and not first.endswith("\n\n")
    headings = (
        "Diagnostics (0)",
        "Packages (1)",
        "Capability Requirements",
        "Compatibility",
        "Extension Catalog Evidence (1)",
        "Portability",
        "Requirement Explanations (1)",
    )
    assert tuple(first.index(heading) for heading in headings) == tuple(
        sorted(first.index(heading) for heading in headings)
    )
    for required in (
        "Project Explain Artifact v1\n",
        "format: pietto.project-explain.v1\n",
        "status: success\n",
        "selection=selected",
        "status=satisfied",
        "project: portable",
        "selector=native_type:extension_native:vector owner=vector",
    ):
        assert required in first
    assert " object at 0x" not in first
    assert "ProjectExplainRuntimeOutcome" not in first
    assert project_text.__all__ == ()


def test_cli_dependency_direction_is_narrow_and_does_not_duplicate_runtime() -> None:
    source = (REPO_ROOT / "src/pietto/cli.py").read_text(encoding="utf-8")
    text_source = Path(project_text.__file__).read_text(encoding="utf-8")
    assert source.count("_build_project_explain_runtime(root)") == 1
    assert "serialize_project_explain_json_document(result.envelope)" in source
    assert "render_project_explain_text(result.envelope)" in source
    assert "json.dumps" not in source
    for forbidden in (
        "def _locate_root_package",
        "def _build_package_load_plan",
        "def select_extension_catalog",
        "def check_package_capability_requirements",
        "def _compose_project_explain_payload",
    ):
        assert forbidden not in source
        assert forbidden not in text_source
    assert "repr(" not in text_source
    assert "dataclasses.asdict" not in source


def test_spec_and_installed_cli_smoke_own_the_exact_slice14_surface() -> None:
    spec = (
        REPO_ROOT / "docs/spec/phase58-slice14-project-explain-cli-text-json-v1.md"
    ).read_text(encoding="utf-8")
    for required in (
        "pietto explain --project <root> [--format text|json]",
        "SUCCESS                 -> 0",
        "DIAGNOSTIC_ERROR        -> 1",
        "USAGE_OR_RESOURCE_ERROR -> 2",
        "serialize_project_explain_json_document",
        "render_project_explain_text",
        "Project JSON diagnostic failure | exact envelope | empty | 1",
        "Project text usage/resource failure | empty | exact human failure | 2",
        "Slice 15 remains next and unstarted",
        "PHASE58_SLICE14_SELF_OWNED_OPEN = 0",
    ):
        assert required in spec
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    for required in (
        'f"{prefix}/_project_explain/text.py"',
        "import pietto._project_explain.text",
        '"installed CLI project explain text"',
        '"installed CLI project explain JSON v1"',
        '"pietto.project-explain.v1"',
        "no-evaluated-targets",
    ):
        assert required in smoke
