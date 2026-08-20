from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType

import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRoot,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbol,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import (
    ConstraintDef,
    DeriveDef,
    SourceDef,
)
from pietto.errors import Severity

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"


def test_project_type_resolution_facts_are_frozen_private_scaffold() -> None:
    assert is_dataclass(ProjectResolvedType)
    assert hasattr(ProjectResolvedType, "__slots__")

    resolved_type = ProjectResolvedType(
        name="Missing",
        kind=ProjectResolvedTypeKind.UNKNOWN,
    )
    assert not hasattr(resolved_type, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(resolved_type, "name", "Other")


def test_project_semantic_model_type_resolution_maps_default_readonly() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert isinstance(model.type_resolutions, MappingProxyType)
    assert isinstance(model.source_shape_resolutions, MappingProxyType)
    assert model.type_resolutions == {}
    assert model.source_shape_resolutions == {}


def test_builtin_type_expr_names_resolve_without_diagnostics(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    builtin_names = (
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    )
    fields = "".join(
        f"    value_{index}: {name}\n"
        for index, name in enumerate(builtin_names, start=1)
    )
    _write(root, "builtins.pietto", f"shape Builtins:\n{fields}")

    _, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    by_name = _resolved_types_by_name(semantic_result.model)
    for name in builtin_names:
        assert len(by_name[name]) == 1
        assert by_name[name][0].kind is ProjectResolvedTypeKind.BUILTIN
        assert by_name[name][0].symbol is None


def test_cross_file_type_namespace_references_resolve(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/types.pietto",
        "type Email = Text not null\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "shape User:\n"
        "    id: Int\n",
    )
    _write(
        root,
        "models/usage.pietto",
        "shape Account:\n"
        "    owner: User\n"
        "    status: Status\n"
        "    email: Email\n"
        "constraint accepts_status(value: Status) -> Bool not null:\n"
        "    value is not null\n"
        "derive normalize_email(value: Email) -> Email:\n"
        "    value\n"
        'source accounts: Account is postgres.table("accounts")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    by_name = _resolved_types_by_name(semantic_result.model)
    assert ProjectResolvedTypeKind.SHAPE in {item.kind for item in by_name["User"]}
    assert ProjectResolvedTypeKind.ENUM in {item.kind for item in by_name["Status"]}
    assert ProjectResolvedTypeKind.TYPE_ALIAS in {
        item.kind for item in by_name["Email"]
    }

    account_source = _source_definition(parse_result, "accounts")
    account_symbol = semantic_result.model.source_shape_resolutions[account_source]
    assert isinstance(account_symbol, ProjectSymbol)
    assert account_symbol.kind is ProjectSymbolKind.SHAPE
    assert account_symbol.name == "Account"
    assert account_symbol.path == "models/usage.pietto"

    status_constraint = _definition(parse_result, ConstraintDef, "accepts_status")
    normalize_derive = _definition(parse_result, DeriveDef, "normalize_email")
    assert (
        semantic_result.model.type_resolutions[
            status_constraint.parameters[0].type
        ].kind
        is ProjectResolvedTypeKind.ENUM
    )
    assert (
        semantic_result.model.type_resolutions[normalize_derive.return_type].kind
        is ProjectResolvedTypeKind.TYPE_ALIAS
    )


def test_missing_type_expr_names_emit_project_relative_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "missing_types.pietto",
        "type Alias = MissingAlias\n"
        "shape Bad:\n"
        "    field: MissingField\n"
        "constraint bad(value: MissingParam) -> MissingReturn:\n"
        "    value is not null\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.message, diagnostic.location.path)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2002", "Unknown type: MissingAlias", "missing_types.pietto"),
        ("PIE-S2002", "Unknown type: MissingField", "missing_types.pietto"),
        ("PIE-S2002", "Unknown type: MissingParam", "missing_types.pietto"),
        ("PIE-S2002", "Unknown type: MissingReturn", "missing_types.pietto"),
    ]
    assert all(
        diagnostic.severity is Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    unknown_resolutions = [
        item
        for item in semantic_result.model.type_resolutions.values()
        if item.kind is ProjectResolvedTypeKind.UNKNOWN
    ]
    assert len(unknown_resolutions) == 4
    assert {item.symbol for item in unknown_resolutions} == {None}


def test_missing_source_shape_names_emit_project_relative_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "missing_shape.pietto",
        'source rows: MissingShape is postgres.table("rows")\n',
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.source_shape_resolutions == {}
    assert [
        (diagnostic.code, diagnostic.message, diagnostic.location.path)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2303", "Unknown source shape: MissingShape", "missing_shape.pietto"),
    ]


def test_source_shape_names_must_resolve_to_shape_symbols(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "non_shape_sources.pietto",
        "type Alias = Text not null\n"
        "enum Status:\n"
        "    ACTIVE\n"
        'source alias_rows: Alias is postgres.table("alias_rows")\n'
        'source status_rows: Status is postgres.table("status_rows")\n',
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.source_shape_resolutions == {}
    assert [
        (diagnostic.code, diagnostic.message, diagnostic.location.path)
        for diagnostic in semantic_result.diagnostics
    ] == [
        (
            "PIE-S2303",
            "Source shape must refer to a shape: Alias",
            "non_shape_sources.pietto",
        ),
        (
            "PIE-S2303",
            "Source shape must refer to a shape: Status",
            "non_shape_sources.pietto",
        ),
    ]


def test_duplicate_type_namespace_short_circuits_type_resolution(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(root, "models/a.pietto", "shape Shared:\n    id: Int\n")
    _write(
        root,
        "models/b.pietto",
        "enum Shared:\n"
        "    ACTIVE\n"
        "shape UsesMissing:\n"
        "    field: MissingType\n"
        'source rows: Shared is postgres.table("rows")\n',
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2001", "Duplicate symbol name in type namespace: Shared"),
    ]
    assert semantic_result.model.type_resolutions == {}
    assert semantic_result.model.source_shape_resolutions == {}


def test_type_namespace_behavior_remains_stable_with_valid_relation(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "type_namespace_with_relation.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.catalog.relation_symbols) == (
        "rows",
        "projected",
    )
    assert semantic_result.model.source_shape_resolutions


def test_parse_check_failures_do_not_create_type_namespace_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "bad.pietto", "shape Broken\n    id: MissingType\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert not parse_result.ok
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert not semantic_result.ok


def test_project_json_v2_does_not_expose_type_resolution_facts(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "good.pietto",
        'shape Row:\n    id: Int\nsource rows: Row is postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.type_resolutions
    assert semantic_result.model.source_shape_resolutions
    assert document["ok"] is True
    assert "ProjectResolvedType" not in serialized
    assert "type_resolutions" not in serialized
    assert "source_shape_resolutions" not in serialized
    assert "catalog" not in serialized


def test_project_text_check_output_remains_parse_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "good.pietto",
        'shape Row:\n    id: Int\nsource rows: Row is postgres.table("rows")\n',
    )

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_slice5_does_not_import_semantic_or_enter_output_paths() -> None:
    source = MODEL_PATH.read_text(encoding="utf-8")

    assert "pietto.semantic" not in source
    assert "semantic.analyze" not in source
    assert "build_ir" not in source
    assert "emit_postgres_sql" not in source
    assert "emit_mysql_sql" not in source


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _resolved_types_by_name(
    model: ProjectSemanticModel,
) -> dict[str, list[ProjectResolvedType]]:
    by_name: dict[str, list[ProjectResolvedType]] = {}
    for resolved_type in model.type_resolutions.values():
        by_name.setdefault(resolved_type.name, []).append(resolved_type)
    return by_name


def _definition(
    parse_result: ProjectParseCheckResult,
    definition_type: type[ConstraintDef] | type[DeriveDef],
    name: str,
) -> ConstraintDef | DeriveDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, definition_type) and definition.name == name:
                return definition
    raise AssertionError(f"Definition not found: {name}")


def _source_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> SourceDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, SourceDef) and definition.name == name:
                return definition
    raise AssertionError(f"Source not found: {name}")


def _forbid_project_compiler_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter compiler output pipelines")

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
