from __future__ import annotations

from collections.abc import MutableMapping
import json
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowField,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE7_GATE2_PATHS = {
    "src/pietto/_project/model.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}


def test_table_from_direct_source_populates_relation_row_schema_for_renamed_bare_field(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _renamed_projection_project(
            tmp_path,
            relation_kind="table",
            relation_name="active_users",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    table = _derived_definition(parse_result, "active_users")
    source_schema = semantic_result.model.source_row_schemas[source]
    relation_schema = semantic_result.model.relation_row_schemas[table]
    source_symbol = semantic_result.model.relation_resolutions[table.from_clause]

    assert isinstance(semantic_result.model.relation_row_schemas, MappingProxyType)
    assert isinstance(relation_schema.fields, MappingProxyType)
    assert tuple(semantic_result.model.relation_row_schemas) == (table,)
    assert tuple(relation_schema.fields) == ("user_id", "contact")
    assert relation_schema.is_unknown is False
    with pytest.raises(TypeError):
        cast(MutableMapping[str, ProjectRowField], relation_schema.fields)["extra"] = (
            relation_schema.fields["user_id"]
        )
    _assert_direct_projection_field(
        relation_field=relation_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=source_symbol,
        expected_name="user_id",
    )
    _assert_direct_projection_field(
        relation_field=relation_schema.fields["contact"],
        source_field=source_schema.fields["email"],
        source_symbol=source_symbol,
        expected_name="contact",
    )


def test_query_from_direct_source_populates_relation_row_schema_for_renamed_bare_field(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _renamed_projection_project(
            tmp_path,
            relation_kind="query",
            relation_name="active_users",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    query = _derived_definition(parse_result, "active_users")
    source_schema = semantic_result.model.source_row_schemas[source]
    relation_schema = semantic_result.model.relation_row_schemas[query]
    source_symbol = semantic_result.model.relation_resolutions[query.from_clause]

    assert tuple(semantic_result.model.relation_row_schemas) == (query,)
    assert tuple(relation_schema.fields) == ("user_id", "contact")
    _assert_direct_projection_field(
        relation_field=relation_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=source_symbol,
        expected_name="user_id",
    )
    _assert_direct_projection_field(
        relation_field=relation_schema.fields["contact"],
        source_field=source_schema.fields["email"],
        source_symbol=source_symbol,
        expected_name="contact",
    )


def test_direct_qualified_rename_populates_relation_row_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        user_id = users.id\n")
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    table = _derived_definition(parse_result, "projected")
    source_schema = semantic_result.model.source_row_schemas[source]
    relation_schema = semantic_result.model.relation_row_schemas[table]
    source_symbol = semantic_result.model.relation_resolutions[table.from_clause]

    assert tuple(relation_schema.fields) == ("user_id",)
    _assert_direct_projection_field(
        relation_field=relation_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=source_symbol,
        expected_name="user_id",
    )


def test_mixed_bare_qualified_and_renamed_direct_fields_preserve_select_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(
            tmp_path,
            "        users.email\n        id\n        user_id = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert tuple(relation_schema.fields) == ("email", "id", "user_id")


def test_distinct_alias_for_same_input_field_is_valid(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        id\n        id_alias = id\n")
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert tuple(relation_schema.fields) == ("id", "id_alias")
    assert relation_schema.is_unknown is False


def test_duplicate_output_from_rename_marks_relation_row_schema_unknown(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        id\n        id = users.id\n")
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert "PIE-S2102" not in _diagnostic_codes(semantic_result)
    assert "PIE-S2305" not in _diagnostic_codes(semantic_result)


def test_wrong_qualifier_in_renamed_qualified_field_marks_unknown_with_slice8_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        user_id = orders.id\n")
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: orders.id")]


def test_unknown_renamed_bare_field_marks_unknown_with_slice8_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        user_id = missing_field\n")
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: missing_field")]


def test_unknown_renamed_qualified_field_marks_unknown_with_slice8_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        user_id = users.missing_field\n")
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.missing_field")]


def test_multi_part_renamed_dotted_projection_marks_unknown_with_slice8_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        user_id = db.users.id\n")
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: db.users.id")]


def test_computed_alias_remains_deferred_to_phase49(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        total = score + 1\n")
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    assert table not in semantic_result.model.relation_row_schemas


def test_query_to_query_rename_projection_remains_absent(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        'source users: User is postgres.table("users")\n'
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        user_id = id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (staged,)
    assert staged in semantic_result.model.relation_row_schemas
    assert exported not in semantic_result.model.relation_row_schemas


def test_project_json_v2_does_not_expose_rename_relation_row_schema_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _renamed_projection_project(
            tmp_path,
            relation_kind="table",
            relation_name="active_users",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas
    for private_fact in (
        "relation_row_schemas",
        "source_row_schemas",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldNullability",
        "ProjectRowFieldProvenance",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def test_phase47_slice7_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE7_GATE2_PATHS)


def _assert_direct_projection_field(
    *,
    relation_field: ProjectRowField,
    source_field: ProjectRowField,
    source_symbol: object,
    expected_name: str,
) -> None:
    assert relation_field.name == expected_name
    assert relation_field.resolved_type is source_field.resolved_type
    assert relation_field.nullability is source_field.nullability
    assert relation_field.field_def is source_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )
    assert relation_field.provenance.symbol is source_symbol
    assert relation_field.provenance.location is not None
    assert relation_field.provenance.location.path == "models.pietto"


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _renamed_projection_project(
    tmp_path: Path,
    *,
    relation_kind: str,
    relation_name: str,
) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int\n"
        "    email: Text nullable\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_kind} {relation_name}:\n"
        "    from users\n"
        "    select:\n"
        "        user_id = id\n"
        "        contact = email\n",
    )
    return root


def _project_with_select(tmp_path: Path, select_body: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        f"{select_body}",
    )
    return root


def _source_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> SourceDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, SourceDef) and definition.name == name:
                return definition
    raise AssertionError(f"Source definition not found: {name}")


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived relation not found: {name}")


def _diagnostic_codes(semantic_result: ProjectSemanticResult) -> set[str]:
    return {diagnostic.code for diagnostic in semantic_result.diagnostics}


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


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths
