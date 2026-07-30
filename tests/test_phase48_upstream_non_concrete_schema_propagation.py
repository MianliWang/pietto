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
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase48-upstream-non-concrete-schema-propagation-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE7_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-upstream-non-concrete-schema-propagation-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
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

ALLOWED_SLICE4_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-computed-alias-project-row-schema-mvp-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_project_json_private_fact_privacy_readiness.py",
    "tests/test_phase48_downstream_diagnostics_ordering_hardening.py",
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


def test_slice7_contract_document_exists_and_is_linked_from_plan() -> None:
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
        "Phase 48 Slice 7",
        "Upstream unknown / absent / deferred / blocked schema propagation",
        "private schema availability state propagation",
        "`UNKNOWN`",
        "`DEFERRED`",
        "`BLOCKED`",
        "Project JSON v2 top-level shape remains unchanged",
        "existing `PIE-S2102`",
        "existing `PIE-S2301`",
        "existing `PIE-S2302`",
        "No other file is approved in Slice 7 Gate 2",
    ):
        assert required in docs, required


def test_direct_missing_field_gets_unknown_state_with_existing_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n    from users\n    select:\n        missing\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    assert schema.is_unknown is True
    assert schema.fields == {}
    _assert_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        schema_is_relation_schema=True,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]


def test_duplicate_output_gets_unknown_state_without_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        id = users.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    assert schema.is_unknown is True
    assert schema.fields == {}
    _assert_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        schema_is_relation_schema=True,
    )


def test_downstream_from_unknown_gets_unknown_state_without_extra_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    assert semantic_result.model.relation_row_schemas[seed].is_unknown is True
    assert semantic_result.model.relation_row_schemas[exported].is_unknown is True
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        exported,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        schema_is_relation_schema=True,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]


def test_computed_alias_and_aggregate_are_concrete_while_pure_grouping_stays_deferred(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query computed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query with_let:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + 1\n"
            "    select:\n"
            "        id\n"
            "query aggregate:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        email\n"
            "    select:\n"
            "        email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    computed = _derived_definition(parse_result, "computed")
    with_let = _derived_definition(parse_result, "with_let")
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")

    computed_schema = semantic_result.model.relation_row_schemas[computed]
    assert tuple(computed_schema.fields) == ("total",)
    assert computed_schema.fields["total"].resolved_type.name == "Int"
    assert computed_schema.fields["total"].field_def is None
    aggregate_schema = semantic_result.model.relation_row_schemas[aggregate]
    assert tuple(aggregate_schema.fields) == ("total",)
    assert tuple(semantic_result.model.relation_aggregate_result_facts[aggregate]) == (
        "total",
    )
    assert grouped not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        computed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        aggregate,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.DEFERRED,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )

    with_let_schema = semantic_result.model.relation_row_schemas[with_let]
    assert tuple(with_let_schema.fields) == ("id",)
    assert "total" not in with_let_schema.fields
    _assert_state(
        semantic_result,
        with_let,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )


def test_unresolved_relation_gets_private_blocked_state_with_existing_pie_s2301(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n    from missing_relation\n    select:\n        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    broken = _derived_definition(parse_result, "broken")
    assert broken not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_cycle_members_get_private_blocked_states_with_existing_pie_s2302(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
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
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (first, second)
    for definition in (first, second):
        _assert_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_downstream_from_blocked_gets_blocked_state_without_extra_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n"
            "    from missing_relation\n"
            "    select:\n"
            "        id\n"
            "query downstream:\n"
            "    from broken\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    broken = _derived_definition(parse_result, "broken")
    downstream = _derived_definition(parse_result, "downstream")
    assert broken not in semantic_result.model.relation_row_schemas
    assert downstream not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_state(
        semantic_result,
        downstream,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_downstream_from_computed_alias_gets_concrete_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query downstream:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    downstream = _derived_definition(parse_result, "downstream")
    seed_schema = semantic_result.model.relation_row_schemas[seed]
    downstream_schema = semantic_result.model.relation_row_schemas[downstream]
    assert tuple(seed_schema.fields) == ("total",)
    assert tuple(downstream_schema.fields) == ("total",)
    assert downstream_schema.fields["total"].field_def is None
    assert (
        downstream_schema.fields["total"].nullability
        is ProjectRowFieldNullability.UNKNOWN
    )
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        downstream,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        schema_is_relation_schema=True,
    )


def test_existing_concrete_query_to_query_propagation_remains_concrete(
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
    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        exported,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        schema_is_relation_schema=True,
    )


def test_project_json_v2_does_not_expose_slice7_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query computed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

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
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "ProjectRowSchema",
        "unknown_schema",
        "duplicate_output_name",
        "deferred_phase48_behavior",
        "unresolved_relation_blocked",
        "cycle_blocked",
        "upstream_unknown",
        "upstream_deferred",
        "upstream_blocked",
    ):
        assert private_fact not in serialized


def test_phase48_slice7_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    dirty_paths = _git_status_paths()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (
        dirty_paths
        in (
            set(),
            ALLOWED_SLICE7_GATE2_PATHS,
            ALLOWED_SLICE4_GATE2_PATHS,
        )
    ) or _slice5_gate2()
    assert _git_diff("src/pietto/_project/check.py") == ""
    assert _git_diff("src/pietto/_project/json_v2.py") == ""


def _assert_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
    *,
    schema_is_relation_schema: bool = False,
) -> None:
    assert semantic_result.model is not None
    state = semantic_result.model.relation_row_schema_states[definition]
    assert state.status is status
    assert state.reason is reason
    if schema_is_relation_schema:
        assert state.schema is semantic_result.model.relation_row_schemas[definition]
    else:
        assert state.schema is None


def _diagnostic_pairs(semantic_result: ProjectSemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ]


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    assert semantic_result.model is not None
    return parse_result, semantic_result


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
