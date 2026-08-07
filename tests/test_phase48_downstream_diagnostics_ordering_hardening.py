from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import cast

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase48-downstream-diagnostics-deterministic-ordering-hardening-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-downstream-diagnostics-deterministic-ordering-hardening-v1.md",
    "tests/test_phase48_downstream_diagnostics_ordering_hardening.py",
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


def test_slice8_contract_document_exists_and_is_linked_from_plan() -> None:
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
        "Phase 48 Slice 8",
        "Downstream diagnostics and deterministic ordering hardening",
        "`docs/spec/phase48-downstream-diagnostics-deterministic-ordering-hardening-v1.md`",
        "docs/spec/tests-only",
        "existing `PIE-S2102`",
        "existing `PIE-S2301`",
        "existing `PIE-S2302`",
        "Project JSON v2 top-level shape remains unchanged",
        "No other file is approved in Slice 8 Gate 2",
    ):
        assert required in docs, required


def test_multiple_invalid_direct_fields_keep_select_item_order(
    tmp_path: Path,
) -> None:
    _, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        first_missing\n"
            "        users.second_missing\n"
            "        db.users.third_missing\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: first_missing"),
        ("PIE-S2102", "Unknown field: users.second_missing"),
        ("PIE-S2102", "Unknown field: db.users.third_missing"),
    ]


def test_downstream_invalid_fields_follow_dependency_and_project_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query bad_first:\n"
            "    from seed\n"
            "    select:\n"
            "        missing_first\n"
            "query bad_second:\n"
            "    from seed\n"
            "    select:\n"
            "        seed.missing_second\n"
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    bad_first = _derived_definition(parse_result, "bad_first")
    bad_second = _derived_definition(parse_result, "bad_second")
    assert tuple(semantic_result.model.relation_row_schemas) == (
        seed,
        bad_first,
        bad_second,
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        bad_first,
        bad_second,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing_first"),
        ("PIE-S2102", "Unknown field: seed.missing_second"),
    ]


def test_out_of_order_definitions_keep_dependency_first_private_order(
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
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        mid,
        final,
    )


def test_independent_relations_tie_break_by_canonical_definition_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query second:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query first:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    second = _derived_definition(parse_result, "second")
    first = _derived_definition(parse_result, "first")

    assert tuple(semantic_result.model.relation_row_schemas) == (second, first)
    assert tuple(semantic_result.model.relation_row_schema_states) == (second, first)


def test_unknown_propagation_does_not_emit_downstream_pie_s2102(
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


def test_deferred_propagation_remains_diagnostic_free(tmp_path: Path) -> None:
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
    assert seed in semantic_result.model.relation_row_schemas
    assert downstream in semantic_result.model.relation_row_schemas
    assert tuple(semantic_result.model.relation_row_schemas[seed].fields) == ("total",)
    assert tuple(semantic_result.model.relation_row_schemas[downstream].fields) == (
        "total",
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


def test_blocked_propagation_uses_unresolved_relation_diagnostic_only(
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


def test_cycle_members_are_blocked_without_pie_s2102(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        also_missing\n",
            include_source=False,
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (first, second)
    _assert_state(
        semantic_result,
        first,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
    )
    _assert_state(
        semantic_result,
        second,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_duplicate_output_remains_unknown_and_diagnostic_free(tmp_path: Path) -> None:
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


def test_multi_file_source_selection_keeps_dependency_first_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a_source.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n',
    )
    _write(
        root,
        "models/b_final.pietto",
        "query final:\n    from mid\n    select:\n        id\n",
    )
    _write(
        root,
        "models/c_seed.pietto",
        "query seed:\n    from users\n    select:\n        id\n",
    )
    _write(
        root,
        "models/d_mid.pietto",
        "query mid:\n    from seed\n    select:\n        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert tuple(parsed_input.path for parsed_input in parse_result.parsed_inputs) == (
        "models/a_source.pietto",
        "models/b_final.pietto",
        "models/c_seed.pietto",
        "models/d_mid.pietto",
    )
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")
    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        mid,
        final,
    )


def test_project_json_v2_keeps_slice8_private_ordering_facts_private(
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
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2102", "Unknown field: missing")
    ]
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "ProjectRowSchema",
        "ProjectRowField",
        "provenance",
        "relation_dependency_graph",
        "ProjectRelationDependencyGraph",
        "cycle_blocked",
        "unknown_schema",
        "upstream_unknown",
        "deferred_phase48_behavior",
        "unresolved_relation_blocked",
        "dependency-first",
        "private ordering",
    ):
        assert private_fact not in serialized


def test_phase48_slice8_package_version_dirty_paths_and_src_lock() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    dirty_paths = _git_status_paths()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (
        dirty_paths
        in (
            set(),
            ALLOWED_SLICE8_GATE2_PATHS,
            ALLOWED_SLICE4_GATE2_PATHS,
        )
    ) or _phase54_active_gate2_is_active()
    if dirty_paths != ALLOWED_SLICE4_GATE2_PATHS:
        assert (_git_diff("src/") == "") or _phase54_active_gate2_is_active()
    if dirty_paths != ALLOWED_SLICE4_GATE2_PATHS:
        assert (
            _git_diff("src/pietto/_project/model.py") == ""
        ) or _phase54_active_gate2_is_active()
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
