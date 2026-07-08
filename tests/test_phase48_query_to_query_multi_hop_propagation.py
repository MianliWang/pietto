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
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE5_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
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


def test_slice5_contract_document_exists_and_locks_concrete_only_scope() -> None:
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
        "Phase 48 Slice 5",
        "Query-to-query and multi-hop propagation",
        "concrete-only relation-to-relation propagation",
        "`TableDef | QueryDef` downstream",
        "`TableDef | QueryDef` immediate upstream",
        "table-from-query",
        "multi-hop",
        "dependency-first deterministic ordering",
        "dependent relation -> dependency relation",
        "No non-concrete upstream propagation until Slice 7",
        "Project JSON v2 top-level shape remains unchanged",
        "No other file is approved in Slice 5 Gate 2",
    ):
        assert required in docs, required


def test_query_from_direct_source_query_propagates_concrete_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    seed_schema = semantic_result.model.relation_row_schemas[seed]
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    assert tuple(seed_schema.fields) == ("id",)
    assert tuple(exported_schema.fields) == ("id",)
    _assert_projection_field(
        relation_field=exported_schema.fields["id"],
        source_field=seed_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="id",
    )
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (exported, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_query_from_propagated_query_supports_multi_hop(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query mid:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query final:\n"
            "    from mid\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schemas[final].fields) == ("id",)
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (mid, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
            (final, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_table_from_query_propagates_concrete_schema(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table materialized:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    materialized = _derived_definition(parse_result, "materialized")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, materialized)
    assert tuple(semantic_result.model.relation_row_schemas[materialized].fields) == (
        "id",
    )
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (materialized, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_mixed_table_query_multi_hop_chain_propagates_in_dependency_order(
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
            "        contact = staged.email\n"
            "table materialized:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.user_id\n"
            "query final:\n"
            "    from materialized\n"
            "    select:\n"
            "        user_id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    materialized = _derived_definition(parse_result, "materialized")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        staged,
        exported,
        materialized,
        final,
    )
    assert tuple(semantic_result.model.relation_row_schemas[exported].fields) == (
        "user_id",
        "contact",
    )
    assert tuple(semantic_result.model.relation_row_schemas[final].fields) == (
        "user_id",
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        staged,
        exported,
        materialized,
        final,
    )


def test_qualified_and_renamed_projection_through_query_upstream(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query exported:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.id\n"
            "        user_id = id\n"
            "        contact = exported.email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    published_schema = semantic_result.model.relation_row_schemas[published]

    assert tuple(published_schema.fields) == ("id", "user_id", "contact")


def test_original_source_qualifier_over_query_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query exported:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_lineage_path_selector_over_query_upstream_uses_pie_s2102(
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
            "        id\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.staged.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: exported.staged.id")]


def test_dependency_first_order_does_not_depend_on_definition_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query final:\n"
            "    from mid\n"
            "    select:\n"
            "        id\n"
            "query mid:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (seed, mid, final)


def test_duplicate_output_names_through_query_upstream_remain_unknown_without_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "        id = seed.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    assert exported_schema.is_unknown is True
    assert exported_schema.fields == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (seed,)


def test_non_concrete_upstreams_do_not_propagate_in_slice5(
    tmp_path: Path,
) -> None:
    unknown_root = _project(
        tmp_path / "unknown",
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        missing\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        id\n",
    )
    unknown_parse, unknown_semantic = _project_semantic_result(unknown_root)
    unknown_seed = _derived_definition(unknown_parse, "seed")
    unknown_exported = _derived_definition(unknown_parse, "exported")
    assert not unknown_semantic.ok
    assert unknown_semantic.model is not None
    assert unknown_semantic.model.relation_row_schemas[unknown_seed].is_unknown is True
    assert unknown_exported not in unknown_semantic.model.relation_row_schemas
    assert [(item.code, item.message) for item in unknown_semantic.diagnostics] == [
        ("PIE-S2102", "Unknown field: missing")
    ]

    deferred_root = _project(
        tmp_path / "deferred",
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        total = score + 1\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        total\n",
    )
    deferred_parse, deferred_semantic = _project_semantic_result(deferred_root)
    deferred_seed = _derived_definition(deferred_parse, "seed")
    deferred_exported = _derived_definition(deferred_parse, "exported")
    assert deferred_semantic.ok
    assert deferred_semantic.model is not None
    assert deferred_seed not in deferred_semantic.model.relation_row_schemas
    assert deferred_exported not in deferred_semantic.model.relation_row_schemas

    cycle_root = _project(
        tmp_path / "cycle",
        "query first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "query second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
        include_source=False,
    )
    _, cycle_semantic = _project_semantic_result(cycle_root)
    assert not cycle_semantic.ok
    assert cycle_semantic.model is not None
    assert cycle_semantic.model.relation_row_schemas == {}
    assert [(item.code, item.message) for item in cycle_semantic.diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_deferred_expression_surfaces_remain_outside_slice5(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query computed:\n"
            "    from seed\n"
            "    select:\n"
            "        total = id + 1\n"
            "query with_let:\n"
            "    from seed\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        id\n"
            "query aggregate:\n"
            "    from seed\n"
            "    select:\n"
            "        total = count()\n"
            "query grouped:\n"
            "    from seed\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    computed = _derived_definition(parse_result, "computed")
    with_let = _derived_definition(parse_result, "with_let")
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, with_let)
    assert computed not in semantic_result.model.relation_row_schemas
    assert tuple(semantic_result.model.relation_row_schemas[with_let].fields) == ("id",)
    assert aggregate not in semantic_result.model.relation_row_schemas
    assert grouped not in semantic_result.model.relation_row_schemas


def test_project_json_v2_does_not_expose_slice5_private_facts(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from seed\n"
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
    assert semantic_result.model.relation_row_schemas
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
        "relation_upstream_concrete",
        "provenance",
        "ProjectRowSchema",
        "ProjectRowField",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def test_phase48_slice5_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE5_GATE2_PATHS)
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


def _assert_concrete_states(
    semantic_result: ProjectSemanticResult,
    expected: tuple[tuple[TableDef | QueryDef, ProjectRelationRowSchemaReason], ...],
) -> None:
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.relation_row_schema_states) == tuple(
        definition for definition, _reason in expected
    )
    for definition, reason in expected:
        state = semantic_result.model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is reason
        assert state.schema is semantic_result.model.relation_row_schemas[definition]


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(
    tmp_path: Path,
    relation_body: str,
    *,
    include_source: bool = True,
) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    source_text = ""
    if include_source:
        source_text = (
            "shape User:\n"
            "    id: Int not null\n"
            "    email: Text nullable\n"
            "    score: Int\n"
            'source users: User is postgres.table("users")\n'
        )
    _write(root, "models.pietto", f"{source_text}{relation_body}")
    return root


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
