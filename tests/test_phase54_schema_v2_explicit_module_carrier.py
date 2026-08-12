from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import json
from pathlib import Path
import re

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto._project.check as project_check
import pietto._project.model as project_model
import pietto._project.module_carrier as module_carrier
import pietto.cli as cli
import pietto.parser_api as parser_api
from pietto._project.config import load_project_config
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigLoadResult,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
)
from pietto._project.source_selection import select_project_sources

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md"
)
SELF_PATH = REPO_ROOT / "tests/test_phase54_schema_v2_explicit_module_carrier.py"


def test_schema_versions_map_to_exact_project_compilation_modes(
    tmp_path: Path,
) -> None:
    expected = (
        (1, ProjectCompilationMode.LEGACY_FLAT),
        (2, ProjectCompilationMode.EXPLICIT_MODULES),
    )

    for schema_version, compilation_mode in expected:
        root = _configured_project(
            tmp_path / f"v{schema_version}",
            schema_version=schema_version,
        )
        result = load_project_config(root)

        assert result.ok
        assert result.config is not None
        assert result.config.schema_version == schema_version
        assert result.config.compilation_mode is compilation_mode
        assert result.config.sources.include_patterns == ("**/*.pietto",)
        assert result.config.sources.exclude_patterns == ()


def test_schema_version_validation_and_unknown_keys_remain_fail_closed(
    tmp_path: Path,
) -> None:
    invalid_types = (
        "",
        "schema_version = true\n",
        'schema_version = "2"\n',
        "schema_version = 2.0\n",
    )
    for index, prefix in enumerate(invalid_types):
        root = _root_with_config(
            tmp_path / f"type-{index}",
            prefix + '\n[sources]\ninclude = ["*.pietto"]\n',
        )
        result = load_project_config(root)
        assert not result.ok
        assert result.config is None
        assert _single_config_schema_message(result) == (
            "Project configuration schema_version must be integer 1 or 2."
        )

    for schema_version in (-1, 0, 3):
        root = _root_with_config(
            tmp_path / f"value-{schema_version}",
            f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        )
        result = load_project_config(root)
        assert not result.ok
        assert result.config is None
        assert _single_config_schema_message(result) == (
            "Project configuration schema_version must be 1 or 2."
        )

    unknown_cases = (
        (
            'schema_version = 1\nname = "x"\n\n[sources]\ninclude = ["*.pietto"]\n',
            "Project configuration contains unsupported top-level key: name.",
        ),
        (
            'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\ndefault = []\n',
            "Project [sources] contains unsupported key: default.",
        ),
    )
    for index, (config_text, message) in enumerate(unknown_cases):
        result = load_project_config(
            _root_with_config(tmp_path / f"unknown-{index}", config_text)
        )
        assert not result.ok
        assert result.config is None
        assert _single_config_schema_message(result) == message


def test_schema_versions_select_identical_normalized_ordered_inputs(
    tmp_path: Path,
) -> None:
    results: list[ProjectDiscoveryResult] = []
    for schema_version in (1, 2):
        root = _configured_project(
            tmp_path / f"v{schema_version}",
            schema_version=schema_version,
            include=("models/**/*.pietto", "*.pietto"),
            exclude=("models/tmp/*.pietto",),
        )
        _write(root, "root.pietto", "shape Root:\n    id: Int\n")
        _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
        _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
        _write(root, "models/tmp/skip.pietto", "shape Skip:\n    id: Int\n")
        results.append(select_project_sources(root, load_project_config(root)))

    legacy, explicit = results
    assert legacy.ok and explicit.ok
    assert legacy.inputs == explicit.inputs
    assert tuple(item.path for item in legacy.inputs) == (
        "models/a.pietto",
        "models/z.pietto",
        "root.pietto",
    )
    assert legacy.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert explicit.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert tuple(module.path for module in legacy.modules) == tuple(
        module.path for module in explicit.modules
    )


def test_logical_module_carrier_is_frozen_slots_hashable_and_enforces_invariants() -> (
    None
):
    parse_result = parser_api.parse_source(
        "shape Row:\n    id: Int\n",
        path="models/row.pietto",
    )
    assert parse_result.ast is not None
    project_input = ProjectInput(path="models/row.pietto", status="parsed")
    parsed_input = ProjectParsedInput(
        path="models/row.pietto",
        script=parse_result.ast,
    )
    module = ProjectLogicalModule(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        path="models/row.pietto",
        position=0,
        project_input=project_input,
        parsed_input=parsed_input,
    )

    assert is_dataclass(ProjectLogicalModule)
    assert hasattr(ProjectLogicalModule, "__slots__")
    assert not hasattr(module, "__dict__")
    assert tuple(field.name for field in fields(ProjectLogicalModule)) == (
        "compilation_mode",
        "path",
        "position",
        "project_input",
        "parsed_input",
    )
    assert isinstance(hash(module), int)
    with pytest.raises(FrozenInstanceError):
        setattr(module, "position", 1)

    invalid_arguments = (
        {"compilation_mode": "explicit_modules"},
        {"path": "../row.pietto"},
        {"position": True},
        {"position": -1},
        {"project_input": ProjectInput(path="other.pietto", status="parsed")},
        {
            "parsed_input": ProjectParsedInput(
                path="other.pietto",
                script=parse_result.ast,
            )
        },
    )
    base: dict[str, object] = {
        "compilation_mode": ProjectCompilationMode.EXPLICIT_MODULES,
        "path": "models/row.pietto",
        "position": 0,
        "project_input": project_input,
        "parsed_input": parsed_input,
    }
    for replacement in invalid_arguments:
        with pytest.raises((TypeError, ValueError)):
            ProjectLogicalModule(**(base | replacement))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="input paths must be unique"):
        module_carrier._build_project_logical_modules(
            ProjectCompilationMode.EXPLICIT_MODULES,
            (project_input, project_input),
        )
    with pytest.raises(ValueError, match="parsed paths must be unique"):
        module_carrier._build_project_logical_modules(
            ProjectCompilationMode.EXPLICIT_MODULES,
            (project_input,),
            (parsed_input, parsed_input),
        )
    with pytest.raises(ValueError, match="unmatched parsed inputs"):
        module_carrier._build_project_logical_modules(
            ProjectCompilationMode.EXPLICIT_MODULES,
            (project_input,),
            (
                ProjectParsedInput(
                    path="other.pietto",
                    script=parse_result.ast,
                ),
            ),
        )

    for forbidden in (
        "physical_path",
        "device",
        "inode",
        "digest",
        "trust",
        "imports",
        "exports",
        "graph_edges",
    ):
        assert not hasattr(module, forbidden)


def test_selection_builds_one_zero_based_logical_module_per_input(
    tmp_path: Path,
) -> None:
    root = _configured_project(
        tmp_path / "project",
        schema_version=2,
        include=("*.pietto",),
    )
    _write(root, "z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "a.pietto", "shape Alpha:\n    id: Int\n")

    result = select_project_sources(root, load_project_config(root))

    assert result.ok
    assert len(result.modules) == len(result.inputs) == 2
    assert tuple(module.path for module in result.modules) == (
        "a.pietto",
        "z.pietto",
    )
    assert tuple(module.position for module in result.modules) == (0, 1)
    for position, module in enumerate(result.modules):
        assert module.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
        assert module.project_input is result.inputs[position]
        assert module.parsed_input is None


def test_parse_check_rebuilds_modules_with_parsed_input_references(
    tmp_path: Path,
) -> None:
    root = _configured_project(
        tmp_path / "project",
        schema_version=2,
        include=("*.pietto",),
    )
    _write(root, "z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "a.pietto", "shape Alpha:\n    id: Int\n")

    result = project_check.check_project_parse_only(root)

    assert result.ok
    assert result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert tuple(module.position for module in result.modules) == (0, 1)
    assert tuple(module.path for module in result.modules) == (
        "a.pietto",
        "z.pietto",
    )
    for position, module in enumerate(result.modules):
        assert module.project_input is result.inputs[position]
        assert module.project_input.status == "parsed"
        assert module.parsed_input is result.parsed_inputs[position]
    assert result.modules == project_check.check_project_parse_only(root).modules


def test_parse_and_read_failures_retain_ordered_logical_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(
        tmp_path / "project",
        schema_version=2,
        include=("*.pietto",),
    )
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    _write(root, "unreadable.pietto", "shape Hidden:\n    id: Int\n")
    original_load = project_check._load_trusted_source

    def load_with_one_failure(*args: object, **kwargs: object) -> object:
        selected_input = args[1]
        if getattr(selected_input, "identity").path == "unreadable.pietto":
            raise OSError("synthetic unreadable input")
        return original_load(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(project_check, "_load_trusted_source", load_with_one_failure)

    result = project_check.check_project_parse_only(root)

    assert not result.ok
    assert result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert tuple(module.path for module in result.modules) == (
        "bad.pietto",
        "good.pietto",
        "unreadable.pietto",
    )
    assert all(
        module.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
        for module in result.modules
    )
    assert tuple(module.position for module in result.modules) == (0, 1, 2)
    assert tuple(module.project_input.status for module in result.modules) == (
        "error",
        "parsed",
        "error",
    )
    assert result.modules[0].parsed_input is None
    assert result.modules[1].parsed_input is result.parsed_inputs[0]
    assert result.modules[2].parsed_input is None


def test_explicit_mode_returns_before_legacy_flat_catalog_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    parse_result = project_check.check_project_parse_only(root)

    def unexpected_flat_catalog(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("explicit modules must not enter the flat catalog")

    monkeypatch.setattr(
        project_model,
        "_build_project_semantic_catalog",
        unexpected_flat_catalog,
    )

    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert not semantic_result.ok
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert semantic_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert semantic_result.modules is parse_result.modules


def test_legacy_mode_still_enters_flat_catalog_and_reports_duplicate_pie_s2001(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=1)
    _write(root, "a.pietto", "shape Shared:\n    id: Int\n")
    _write(root, "b.pietto", "shape Shared:\n    value: Text\n")
    parse_result = project_check.check_project_parse_only(root)
    original_builder = project_model._build_project_semantic_catalog
    calls = 0

    def observed_flat_catalog(
        parsed_inputs: tuple[ProjectParsedInput, ...],
    ) -> object:
        nonlocal calls
        calls += 1
        return original_builder(parsed_inputs)

    monkeypatch.setattr(
        project_model,
        "_build_project_semantic_catalog",
        observed_flat_catalog,
    )

    semantic_result = build_empty_project_semantic_result(parse_result)

    assert calls == 1
    assert semantic_result.model is not None
    assert [diagnostic.code for diagnostic in semantic_result.diagnostics] == [
        "PIE-S2001"
    ]
    assert semantic_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert semantic_result.modules is parse_result.modules


def test_schema_v2_project_text_cli_fails_closed_without_success_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_schema_v2_project_json_keeps_exact_envelope_and_fails_exit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    expected = {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {"root": ".", "config_path": "pietto.toml"},
        "inputs": [{"path": "row.pietto", "kind": "source", "status": "parsed"}],
        "diagnostics": [],
        "cli_errors": [],
        "result": {"check": {"files_total": 1, "files_ok": 1, "files_with_errors": 0}},
    }

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == f"{json.dumps(expected, ensure_ascii=True)}\n"
    assert captured.err == ""


def test_schema_v1_project_cli_output_remains_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=1)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 0
    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_project_json_and_public_exports_do_not_expose_module_carriers(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    parse_result = project_check.check_project_parse_only(root)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document, sort_keys=True)

    assert tuple(document) == (
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
    for forbidden in (
        "compilation_mode",
        "legacy_flat",
        "explicit_modules",
        "modules",
        "position",
        "digest",
        "physical",
        "trust",
    ):
        assert forbidden not in serialized
    assert module_carrier.__all__ == ()
    assert not hasattr(pietto, "ProjectCompilationMode")
    assert not hasattr(pietto, "ProjectLogicalModule")
    assert tuple(field.name for field in fields(ProjectConfigLoadResult)) == (
        "root",
        "config_path",
        "config",
        "errors",
        "pinned_root",
    )
    assert "compilation_mode" not in {
        field.name for field in fields(ProjectSemanticModel)
    }
    assert "modules" not in {field.name for field in fields(ProjectSemanticModel)}
    assert (
        ProjectDiscoveryResult(
            root=None,
            config_path=None,
            inputs=(),
            errors=(),
        ).compilation_mode
        is ProjectCompilationMode.LEGACY_FLAT
    )
    assert (
        ProjectParseCheckResult(
            root=None,
            config_path=None,
            inputs=(),
            errors=(),
            diagnostics=(),
        ).modules
        == ()
    )
    assert (
        ProjectSemanticResult(
            root=None,
            config_path=None,
            model=None,
        ).modules
        == ()
    )


def test_single_file_check_behavior_remains_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "single.pietto"
    source_path.write_text("shape Row:\n    id: Int not null\n", encoding="utf-8")

    assert cli.main(["check", str(source_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {source_path}\n"
    assert captured.err == ""


def test_import_export_grammar_ast_and_module_diagnostic_codes_remain_absent() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")
    ast_source = (REPO_ROOT / "src/pietto/ast_nodes.py").read_text(encoding="utf-8")
    graph_path = REPO_ROOT / "src/pietto/_project/module_graph.py"
    resolution_path = REPO_ROOT / "src/pietto/_project/module_resolution.py"
    relation_resolution_path = (
        REPO_ROOT / "src/pietto/_project/module_relation_resolution.py"
    )
    graph_source = graph_path.read_text(encoding="utf-8")
    non_graph_production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if path not in {graph_path, resolution_path, relation_resolution_path}
    )

    assert re.search(r"(?m)^IMPORT: 'import';$", grammar)
    assert re.search(r"(?m)^EXPORT: 'export';$", grammar)
    assert re.search(r"(?m)^AS: 'as';$", grammar)
    for value in (
        "class ModuleDeclarationKind",
        "class ImportItem",
        "class ImportStatement",
        "class ExportItem",
        "class ExportStatement",
        "module_statements: tuple[ModuleStatement, ...] = ()",
    ):
        assert value in ast_source
    for number in range(2701, 2708):
        code = f"PIE-S{number}"
        assert code in graph_source
        assert code not in non_graph_production


def test_slice2_contract_allowlist_and_retained_later_boundaries_are_exact() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    source = SELF_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=SELF_PATH.as_posix())
    test_nodes = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )

    assert len(test_nodes) == 16
    assert all(not node.decorator_list for node in test_nodes)
    assert "## Status And Slice 15 Lifecycle" in plan
    assert "## Slice 3 Exact Production Boundary And Gate Contract" in plan
    assert "## Slice 4 Exact Production Boundary And Gate Contract" in plan
    for phrase in (
        "Authority is `A3_M54_D0`.",
        "Mechanical reader modified M48",
        "exactly 55 literal Python paths",
        "Projected clean collection is\n10,830",
        "Slice 3 retains pinned-root loading",
        "Slice 4 retains contextual import/export grammar",
        "Slice 8 retains module graph, cycles",
        "No `PIE-S2701` through `PIE-S2707` code is added or emitted.",
        "next=PHASE54_SLICE3_GATE0_GATE1",
        "Do not begin Slice 3.",
    ):
        assert phrase in spec
    for relative in (
        "docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md",
        "src/pietto/_project/module_carrier.py",
        "tests/test_phase54_schema_v2_explicit_module_carrier.py",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "src/pietto/_project/config.py",
        "src/pietto/_project/model.py",
        "src/pietto/_project/source_selection.py",
        "src/pietto/_project/check.py",
        "tests/test_phase44_project_config_loader.py",
    ):
        assert relative in spec


def _configured_project(
    root: Path,
    *,
    schema_version: int,
    include: tuple[str, ...] = ("**/*.pietto",),
    exclude: tuple[str, ...] = (),
) -> Path:
    include_text = ", ".join(json.dumps(pattern) for pattern in include)
    exclude_text = ", ".join(json.dumps(pattern) for pattern in exclude)
    return _root_with_config(
        root,
        f"schema_version = {schema_version}\n\n"
        "[sources]\n"
        f"include = [{include_text}]\n"
        f"exclude = [{exclude_text}]\n",
    )


def _root_with_config(root: Path, config_text: str) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _single_config_schema_message(result: ProjectConfigLoadResult) -> str:
    assert len(result.errors) == 1
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    return result.errors[0].message
