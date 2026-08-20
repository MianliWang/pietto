from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType

import pytest

import pietto.cli as cli
import pietto.semantic as semantic_api
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
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import DeriveDef, ShapeDef, SourceDef, TableDef, TypeDef, Script
from pietto.errors import Diagnostic, Severity, SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def test_project_semantic_catalog_has_readonly_namespace_maps() -> None:
    catalog = ProjectSemanticCatalog()

    assert tuple(field.name for field in fields(ProjectSemanticCatalog)) == (
        "type_symbols",
        "relation_symbols",
        "callable_symbols",
    )
    assert not hasattr(catalog, "__dict__")
    assert isinstance(catalog.type_symbols, MappingProxyType)
    assert isinstance(catalog.relation_symbols, MappingProxyType)
    assert isinstance(catalog.callable_symbols, MappingProxyType)
    assert catalog.type_symbols == {}
    assert catalog.relation_symbols == {}
    assert catalog.callable_symbols == {}


def test_project_semantic_result_preserves_successful_parse_inputs(
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


def test_project_semantic_catalog_populates_symbols_in_deterministic_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a.pietto",
        "type Age = Int not null\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "    PAUSED\n"
        "shape User:\n"
        "    id: Int\n"
        "constraint usable(value: Text not null) -> Bool not null:\n"
        "    value is not null\n",
    )
    _write(
        root,
        "models/b.pietto",
        "derive normalize(value: Text not null) -> Text not null:\n"
        "    lower(value)\n"
        'source users: User is postgres.table("users")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query user_ids:\n"
        "    from active_users\n"
        "    select:\n"
        "        id\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.model is not None
    catalog = semantic_result.model.catalog
    assert tuple(catalog.type_symbols) == ("Age", "Status", "User")
    assert tuple(catalog.callable_symbols) == ("usable", "normalize")
    assert tuple(catalog.relation_symbols) == ("users", "active_users", "user_ids")

    age = catalog.type_symbols["Age"]
    assert age.namespace is ProjectSymbolNamespace.TYPE
    assert age.kind is ProjectSymbolKind.TYPE_ALIAS
    assert age.name == "Age"
    assert age.path == "models/a.pietto"
    assert age.location == SourceLocation(
        path="models/a.pietto",
        line=1,
        column=1,
        end_line=1,
        end_column=24,
    )
    assert isinstance(age.definition, TypeDef)
    assert age.definition.name == "Age"

    assert catalog.type_symbols["Status"].kind is ProjectSymbolKind.ENUM
    assert catalog.type_symbols["User"].kind is ProjectSymbolKind.SHAPE
    assert catalog.callable_symbols["usable"].kind is ProjectSymbolKind.CONSTRAINT
    assert catalog.callable_symbols["normalize"].kind is ProjectSymbolKind.DERIVE
    assert catalog.relation_symbols["users"].kind is ProjectSymbolKind.SOURCE
    assert catalog.relation_symbols["active_users"].kind is ProjectSymbolKind.TABLE
    assert catalog.relation_symbols["user_ids"].kind is ProjectSymbolKind.QUERY
    assert isinstance(catalog.type_symbols["User"].definition, ShapeDef)
    assert isinstance(catalog.relation_symbols["users"].definition, SourceDef)
    assert isinstance(catalog.relation_symbols["active_users"].definition, TableDef)
    assert isinstance(catalog.callable_symbols["normalize"].definition, DeriveDef)


def test_project_semantic_catalog_can_still_be_empty() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert model.catalog == ProjectSemanticCatalog()
    assert model.catalog.type_symbols == {}
    assert model.catalog.relation_symbols == {}
    assert model.catalog.callable_symbols == {}


def test_same_name_across_project_namespaces_is_allowed(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "shared.pietto",
        "shape Shared:\n"
        "    id: Int\n"
        "derive Shared(value: Text not null) -> Text not null:\n"
        "    value\n"
        'source Shared: Shared is postgres.table("shared")\n',
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    catalog = semantic_result.model.catalog
    assert set(catalog.type_symbols) == {"Shared"}
    assert set(catalog.callable_symbols) == {"Shared"}
    assert set(catalog.relation_symbols) == {"Shared"}


def test_project_duplicate_symbols_fail_closed_and_keep_first_symbol(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a.pietto",
        "shape Shared:\n"
        "    id: Int\n"
        "derive normalize(value: Text not null) -> Text not null:\n"
        "    value\n",
    )
    _write(
        root,
        "models/b.pietto",
        "enum Shared:\n"
        "    ACTIVE\n"
        "constraint normalize(value: Text not null) -> Bool not null:\n"
        "    value is not null\n"
        'source rows: Shared is postgres.table("rows")\n',
    )
    _write(
        root,
        "models/c.pietto",
        "table rows:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "query rows:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in type namespace: Shared",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in callable namespace: normalize",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in relation namespace: rows",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in relation namespace: rows",
        ),
    ]
    assert [
        (diagnostic.location.path, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("models/b.pietto", 1, 1),
        ("models/b.pietto", 3, 1),
        ("models/c.pietto", 1, 1),
        ("models/c.pietto", 5, 1),
    ]

    catalog = semantic_result.model.catalog
    assert catalog.type_symbols["Shared"].path == "models/a.pietto"
    assert catalog.type_symbols["Shared"].kind is ProjectSymbolKind.SHAPE
    assert catalog.callable_symbols["normalize"].path == "models/a.pietto"
    assert catalog.callable_symbols["normalize"].kind is ProjectSymbolKind.DERIVE
    assert catalog.relation_symbols["rows"].path == "models/b.pietto"
    assert catalog.relation_symbols["rows"].kind is ProjectSymbolKind.SOURCE


def test_relation_body_semantics_remain_deferred_after_resolution(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "body_deferred.pietto",
        "shape Raw:\n"
        "    id: Int\n"
        'source raw: Raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        total = missing_field + 1\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.catalog.relation_symbols) == ("raw", "projected")
    projected = semantic_result.model.catalog.relation_symbols["projected"].definition
    assert isinstance(projected, TableDef)
    assert (
        semantic_result.model.relation_resolutions[projected.from_clause].name == "raw"
    )


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
