from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

import pietto.cli as cli
from _static_audit_helpers import normalized_text as _normalized
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import FromClause, QueryDef, TableDef
from pietto.errors import Severity

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PLAN_PATH = REPO_ROOT / "docs/plan/phase-45-project-wide-semantic-model-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md"


def test_project_relation_resolution_map_defaults_readonly() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert isinstance(model.relation_resolutions, MappingProxyType)
    assert model.relation_resolutions == {}


def test_cross_file_relation_namespace_references_resolve(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a_source.pietto",
        'shape Row:\n    id: Int\nsource raw: Row is postgres.table("raw")\n',
    )
    _write(
        root,
        "models/b_table.pietto",
        "table staged:\n    from raw\n    select:\n        id\n",
    )
    _write(
        root,
        "models/c_query.pietto",
        "query exported:\n    from staged\n    select:\n        id\n",
    )
    _write(
        root,
        "models/d_from_query.pietto",
        "table table_from_query:\n"
        "    from exported\n"
        "    select:\n"
        "        id\n"
        "query query_from_query:\n"
        "    from exported\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    resolutions = semantic_result.model.relation_resolutions
    assert all(isinstance(from_clause, FromClause) for from_clause in resolutions)

    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    table_from_query = _derived_definition(parse_result, "table_from_query")
    query_from_query = _derived_definition(parse_result, "query_from_query")

    assert resolutions[staged.from_clause].kind is ProjectSymbolKind.SOURCE
    assert resolutions[staged.from_clause].name == "raw"
    assert resolutions[exported.from_clause].kind is ProjectSymbolKind.TABLE
    assert resolutions[exported.from_clause].name == "staged"
    assert resolutions[table_from_query.from_clause].kind is ProjectSymbolKind.QUERY
    assert resolutions[table_from_query.from_clause].name == "exported"
    assert resolutions[query_from_query.from_clause].kind is ProjectSymbolKind.QUERY
    assert resolutions[query_from_query.from_clause].name == "exported"


def test_missing_relation_targets_emit_project_relative_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "missing_relations.pietto",
        "table missing_table_input:\n"
        "    from missing_source\n"
        "    select:\n"
        "        id\n"
        "query missing_query_input:\n"
        "    from missing_table\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_resolutions == {}
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2301", Severity.ERROR, "Unknown relation: missing_source"),
        ("PIE-S2301", Severity.ERROR, "Unknown relation: missing_table"),
    ]
    assert [diagnostic.location.path for diagnostic in semantic_result.diagnostics] == [
        "missing_relations.pietto",
        "missing_relations.pietto",
    ]


def test_duplicate_relation_symbols_short_circuit_relation_resolution(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "duplicate_relation.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table rows:\n"
        "    from missing_relation\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2001", "Duplicate symbol name in relation namespace: rows"),
    ]
    assert semantic_result.model.type_resolutions == {}
    assert semantic_result.model.source_shape_resolutions == {}
    assert semantic_result.model.relation_resolutions == {}


def test_type_and_relation_diagnostics_coexist_in_deterministic_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "mixed_diagnostics.pietto",
        "type Alias = MissingType\n"
        'source rows: MissingShape is postgres.table("rows")\n'
        "table projected:\n"
        "    from missing_relation\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2002", "Unknown type: MissingType"),
        ("PIE-S2303", "Unknown source shape: MissingShape"),
        ("PIE-S2301", "Unknown relation: missing_relation"),
    ]


def test_relation_cycles_remain_deferred(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_deferred.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    assert (
        semantic_result.model.relation_resolutions[first.from_clause].name == "second"
    )
    assert (
        semantic_result.model.relation_resolutions[second.from_clause].name == "first"
    )
    assert "PIE-S2302" not in {
        diagnostic.code for diagnostic in semantic_result.diagnostics
    }


def test_sources_and_relationship_metadata_endpoints_are_out_of_scope(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "relationship_deferred.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "relationship external:\n"
        "    endpoint known: rows\n"
        "    endpoint missing: missing_endpoint\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert parse_result.parsed_inputs[0].script.relationships
    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert semantic_result.model.relation_resolutions == {}


def test_project_json_v2_does_not_expose_relation_resolution_facts(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "good.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_resolutions
    assert document["ok"] is True
    assert "ProjectSymbol" not in serialized
    assert "relation_resolutions" not in serialized
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
        "private_relation_error.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


def test_slice6_does_not_import_semantic_or_enter_output_paths() -> None:
    source = MODEL_PATH.read_text(encoding="utf-8")

    assert "pietto.semantic" not in source
    assert "semantic.analyze" not in source
    assert "build_ir" not in source
    assert "emit_postgres_sql" not in source
    assert "emit_mysql_sql" not in source
    assert "check_relation_cycles" not in source
    assert "PIE-S2302" not in source


def test_slice6_docs_lock_private_relation_namespace_semantics() -> None:
    docs = " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))

    for required in (
        "Slice 6 adds private cross-file relation namespace semantics",
        "private relation-resolution facts",
        "`ProjectSemanticModel.relation_resolutions`",
        "table and query `from` targets are checked",
        "`ProjectSemanticCatalog.relation_symbols`",
        "relation targets may be source, table, or query",
        "`PIE-S2301`",
        "duplicate catalog diagnostics short-circuit relation resolution",
        "type/source-shape diagnostics do not short-circuit relation checks",
        "relation cycle detection is deferred",
        "`PIE-S2302` is not emitted in Slice 6",
        "row schema propagation is deferred",
        "projection/body semantic validation is deferred",
        "relationship metadata endpoints are out of scope",
        "no CLI/JSON/text behavior change",
        "no IR, SQL, project `emit-sql`, or project `explain` path",
        "no import from `pietto.semantic`",
    ):
        assert required in docs, required


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived relation not found: {name}")


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
