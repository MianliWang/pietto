from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import json
from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.semantic as semantic_api
from _static_audit_helpers import normalized_text as _normalized
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import Script
from pietto.errors import Diagnostic, Severity, SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-45-project-wide-semantic-model-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md"


def test_project_semantic_scaffold_types_are_frozen_slots_dataclasses() -> None:
    for model_type in (
        ProjectSemanticCatalog,
        ProjectSemanticModel,
        ProjectSemanticResult,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    result = ProjectSemanticResult(root=None, config_path=None, model=None)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "diagnostics", ())


def test_project_semantic_catalog_is_empty_placeholder_only() -> None:
    catalog = ProjectSemanticCatalog()

    assert fields(ProjectSemanticCatalog) == ()
    assert ProjectSemanticCatalog.__slots__ == ()
    assert not hasattr(catalog, "__dict__")
    for deferred_field in (
        "type_symbols",
        "relation_symbols",
        "callable_symbols",
        "diagnostics",
    ):
        assert not hasattr(catalog, deferred_field)


def test_empty_project_semantic_result_preserves_successful_parse_inputs(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
    _write(root, "models/tmp/skip.pietto", "shape Skip:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.root == parse_result.root
    assert semantic_result.config_path == parse_result.config_path
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert semantic_result.model.root == parse_result.root
    assert semantic_result.model.config_path == parse_result.config_path
    assert semantic_result.model.inputs is parse_result.parsed_inputs
    assert tuple(item.path for item in semantic_result.model.inputs) == (
        "models/a.pietto",
        "models/z.pietto",
        "root.pietto",
    )
    for parsed_input in semantic_result.model.inputs:
        assert isinstance(parsed_input, ProjectParsedInput)
        assert not Path(parsed_input.path).is_absolute()
        assert isinstance(parsed_input.script, Script)
        assert parsed_input.script.span.path == parsed_input.path


def test_empty_project_semantic_model_has_empty_catalog() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert model.catalog == ProjectSemanticCatalog()
    assert fields(model.catalog) == ()
    assert not hasattr(model.catalog, "type_symbols")
    assert not hasattr(model.catalog, "relation_symbols")


def test_project_semantic_result_defaults_and_ok_behavior() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )
    error_diagnostic = Diagnostic(
        code="PIE-S9999",
        severity=Severity.ERROR,
        message="Synthetic project semantic error.",
        location=SourceLocation(path="models/a.pietto", line=1, column=1),
    )
    warning_diagnostic = Diagnostic(
        code="PIE-S9998",
        severity=Severity.WARNING,
        message="Synthetic project semantic warning.",
        location=SourceLocation(path="models/a.pietto", line=1, column=1),
    )

    assert (
        ProjectSemanticResult(root=None, config_path=None, model=None).diagnostics == ()
    )
    assert not ProjectSemanticResult(root=None, config_path=None, model=None).ok
    assert ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
    ).ok
    assert ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
        diagnostics=(warning_diagnostic,),
    ).ok
    assert not ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
        diagnostics=(error_diagnostic,),
    ).ok


def test_parse_failures_return_no_model_and_no_semantic_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert not parse_result.ok
    assert semantic_result.root == parse_result.root
    assert semantic_result.config_path == parse_result.config_path
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert not semantic_result.ok


def test_missing_root_or_config_returns_no_model() -> None:
    parse_result = ProjectParseCheckResult(
        root=None,
        config_path=None,
        inputs=(),
        errors=(),
        diagnostics=(),
    )

    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.root is None
    assert semantic_result.config_path is None
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert not semantic_result.ok


def test_project_semantic_scaffold_does_not_call_single_file_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_analyze(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project semantic scaffold must not analyze scripts")

    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    parse_result = check_project_parse_only(root)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_analyze)

    assert build_empty_project_semantic_result(parse_result).ok


def test_project_semantic_scaffold_does_not_enter_output_pipelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    parse_result = check_project_parse_only(root)

    assert build_empty_project_semantic_result(parse_result).ok


def test_project_json_v2_does_not_expose_project_semantic_scaffold(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert document["ok"] is True
    assert "ProjectSemantic" not in serialized
    assert "catalog" not in serialized
    assert "parsed_inputs" not in serialized
    assert "script" not in serialized


def test_project_text_output_remains_parse_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_slice3_docs_lock_private_scaffold_only_scope() -> None:
    docs = " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))

    for required in (
        "Slice 3 adds a private project semantic model scaffold",
        "`ProjectSemanticCatalog`",
        "`ProjectSemanticModel`",
        "`ProjectSemanticResult`",
        "`build_empty_project_semantic_result(...)`",
        "`ProjectParseCheckResult.parsed_inputs`",
        "empty catalog placeholder only",
        "no semantic analysis yet",
        "no symbol collection",
        "no duplicate diagnostics",
        "no cross-file type namespace resolution",
        "no cross-file relation namespace resolution",
        "no CLI/JSON/text behavior change",
        "no IR, SQL, project `emit-sql`, or project `explain` path",
        "no import from `pietto.semantic`",
    ):
        assert required in docs, required


def _forbid_project_compiler_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project scaffold must not enter output pipelines")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)
    monkeypatch.setattr(cli, "build_semantic_metadata_artifact", unexpected_call)
    monkeypatch.setattr(cli, "semantic_metadata_artifact_to_json_dict", unexpected_call)
    monkeypatch.setattr(cli, "render_semantic_metadata_text", unexpected_call)


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path
