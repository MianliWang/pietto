from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase48-table-to-table-table-to-query-propagation-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE4_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md",
    "docs/spec/phase48-table-to-table-table-to-query-propagation-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
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


def test_slice4_contract_document_exists_and_locks_table_upstream_scope() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    docs = " ".join(
        (
            PLAN_PATH.read_text(encoding="utf-8")
            + "\n"
            + SPEC_PATH.read_text(encoding="utf-8")
        ).split()
    )

    for required in (
        "Phase 48 Slice 4",
        "Table-to-table / table-to-query propagation",
        "one-hop table-upstream propagation only",
        "direct-source concrete table schema seed",
        "Do not use a schema newly propagated in Slice 4 as an upstream seed",
        "No query-to-query propagation",
        "No table-from-query propagation",
        "No multi-hop propagation",
        "Project JSON v2 top-level shape remains unchanged",
        "No other file is approved in Slice 4 Gate 2",
    ):
        assert required in docs, required


def test_table_from_direct_source_table_propagates_bare_and_qualified_fields(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
            "table curated:\n"
            "    from staged\n"
            "    select:\n"
            "        staged.email\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    curated = _derived_definition(parse_result, "curated")
    source_schema = semantic_result.model.source_row_schemas[source]
    staged_schema = semantic_result.model.relation_row_schemas[staged]
    curated_schema = semantic_result.model.relation_row_schemas[curated]

    assert tuple(semantic_result.model.relation_row_schemas) == (staged, curated)
    assert tuple(staged_schema.fields) == ("id", "email")
    assert tuple(curated_schema.fields) == ("email", "id")
    _assert_projection_field(
        relation_field=curated_schema.fields["email"],
        source_field=source_schema.fields["email"],
        source_symbol=semantic_result.model.relation_resolutions[curated.from_clause],
        expected_name="email",
    )
    _assert_projection_field(
        relation_field=curated_schema.fields["id"],
        source_field=source_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[curated.from_clause],
        expected_name="id",
    )


def test_query_from_direct_source_table_propagates_renamed_fields(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        user_id = id\n"
            "        contact = staged.email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    source_schema = semantic_result.model.source_row_schemas[source]
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (staged, exported)
    assert tuple(exported_schema.fields) == ("user_id", "contact")
    _assert_projection_field(
        relation_field=exported_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="user_id",
    )
    _assert_projection_field(
        relation_field=exported_schema.fields["contact"],
        source_field=source_schema.fields["email"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="contact",
    )


def test_concrete_states_cover_direct_source_and_relation_upstream_schemas(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query source_query:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    source_query = _derived_definition(parse_result, "source_query")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    states = semantic_result.model.relation_row_schema_states

    assert tuple(semantic_result.model.relation_row_schemas) == (
        source_query,
        staged,
        exported,
    )
    assert tuple(states) == (source_query, staged, exported)
    assert states[source_query].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[source_query].reason
        is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    )
    assert (
        states[source_query].schema
        is semantic_result.model.relation_row_schemas[source_query]
    )
    assert states[staged].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[staged].reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    )
    assert states[staged].schema is semantic_result.model.relation_row_schemas[staged]
    assert states[exported].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[exported].reason
        is ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    assert (
        states[exported].schema is semantic_result.model.relation_row_schemas[exported]
    )


def test_wrong_original_source_qualifier_over_table_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    assert exported_schema.is_unknown is True
    assert exported not in semantic_result.model.relation_row_schema_states
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_multi_part_lineage_selector_over_table_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        staged.users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    assert exported_schema.is_unknown is True
    assert exported_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: staged.users.id")]


def test_query_to_query_and_table_from_query_propagate_concrete_schemas(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query query_seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from query_seed\n"
            "    select:\n"
            "        id\n"
            "table table_from_query:\n"
            "    from query_seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    query_seed = _derived_definition(parse_result, "query_seed")
    exported = _derived_definition(parse_result, "exported")
    table_from_query = _derived_definition(parse_result, "table_from_query")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        query_seed,
        exported,
        table_from_query,
    )
    assert tuple(semantic_result.model.relation_row_schemas[exported].fields) == ("id",)
    assert tuple(
        semantic_result.model.relation_row_schemas[table_from_query].fields
    ) == ("id",)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        query_seed,
        exported,
        table_from_query,
    )


def test_propagated_table_schema_is_used_as_multi_hop_seed(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table curated:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n"
            "query published:\n"
            "    from curated\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    curated = _derived_definition(parse_result, "curated")
    published = _derived_definition(parse_result, "published")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        staged,
        curated,
        published,
    )
    assert tuple(semantic_result.model.relation_row_schemas[published].fields) == (
        "id",
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        staged,
        curated,
        published,
    )


def test_table_upstream_computed_alias_remains_deferred_without_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        total = id + 1\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (staged,)
    assert exported not in semantic_result.model.relation_row_schemas


def test_project_json_v2_does_not_expose_table_upstream_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schema_states
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
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "source_row_schemas",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "direct_source_concrete",
        "table_upstream_concrete",
        "relation_upstream_concrete",
        "ProjectRowSchema",
        "ProjectRowField",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def test_phase48_slice4_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE4_GATE2_PATHS)
    assert _git_diff("src/pietto/_project/check.py") == ""
    assert _git_diff("src/pietto/_project/json_v2.py") == ""


def _assert_projection_field(
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


def _project(tmp_path: Path, relation_body: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_body}",
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


def _git_diff(path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--", path],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout
