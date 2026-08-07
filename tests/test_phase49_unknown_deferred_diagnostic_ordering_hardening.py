from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tomllib

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
)
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
)
from pietto._project.row_lineage import (
    ProjectRowLineageReason,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, TableDef
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-49-row-level-computed-let-schema-lineage.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase49-unknown-deferred-diagnostic-ordering-hardening-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE12_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-unknown-deferred-diagnostic-ordering-hardening-v1.md",
    "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
}

FORBIDDEN_SOURCE_DIFF_PATHS = (
    "src/pietto/_project/model.py",
    "src/pietto/_project/json_v2.py",
    "src/pietto/_project/check.py",
    "src/pietto/_project/row_dependency_graph.py",
    "src/pietto/_project/row_lineage.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/semantic/let_bindings.py",
)

PRIVATE_JSON_FACTS = (
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
    "ProjectRelationRowSchemaState",
    "ProjectRelationLetScopeFacts",
    "ProjectRelationRowDependencyGraph",
    "ProjectRelationRowLineage",
    "UNKNOWN_SCHEMA",
    "DEFERRED_PHASE48_BEHAVIOR",
    "UNRESOLVED_RELATION_BLOCKED",
    "CYCLE_BLOCKED",
    "DUPLICATE_OUTPUT_NAME",
    "LET_DIAGNOSTICS_SUPPRESSED",
    "unknown_schema",
    "deferred_phase48_behavior",
    "unresolved_relation_blocked",
    "cycle_blocked",
    "duplicate_output_name",
    "let_diagnostics_suppressed",
    "dependency",
    "lineage",
    "provenance",
    "origin",
)


def test_slice12_spec_exists_and_is_linked_from_plan() -> None:
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
        "Phase 49 Slice 12",
        "Unknown/deferred/diagnostic ordering hardening",
        "`docs/spec/phase49-unknown-deferred-diagnostic-ordering-hardening-v1.md`",
        "docs/spec/tests-only hardening",
        "`relation_row_schema_states`",
        "`relation_let_scope_facts`",
        "`relation_row_dependency_graphs`",
        "`relation_row_lineages`",
        "Project JSON v2 remains unchanged",
        "No production source file",
    ):
        assert required in docs, required


def test_missing_field_unknown_schema_keeps_single_public_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]
    broken = _derived_definition(parse_result, "broken")
    _assert_row_schema_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
    )
    _assert_dependency_graph_state(
        semantic_result,
        broken,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA,
    )
    _assert_lineage_state(
        semantic_result,
        broken,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.UNKNOWN_SCHEMA,
    )


def test_unresolved_relation_blocks_private_carriers_without_extra_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n"
            "    from missing_relation\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]
    broken = _derived_definition(parse_result, "broken")
    _assert_row_schema_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_let_state(
        semantic_result,
        broken,
        ProjectLetScopeFactsStatus.BLOCKED,
        ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
    )
    _assert_dependency_graph_state(
        semantic_result,
        broken,
        ProjectRowDependencyGraphStatus.BLOCKED,
        ProjectRowDependencyGraphReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_lineage_state(
        semantic_result,
        broken,
        ProjectRowLineageStatus.BLOCKED,
        ProjectRowLineageReason.UNRESOLVED_RELATION_BLOCKED,
    )


def test_relation_cycle_blocks_private_carriers_without_missing_field_noise(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query first:\n"
            "    from second\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    let:\n"
            "        other = id + 1\n"
            "    select:\n"
            "        also_missing\n",
            include_source=False,
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    for relation_name in ("first", "second"):
        definition = _derived_definition(parse_result, relation_name)
        _assert_row_schema_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        )
        _assert_let_state(
            semantic_result,
            definition,
            ProjectLetScopeFactsStatus.BLOCKED,
            ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
        )
        _assert_dependency_graph_state(
            semantic_result,
            definition,
            ProjectRowDependencyGraphStatus.BLOCKED,
            ProjectRowDependencyGraphReason.CYCLE_BLOCKED,
        )
        _assert_lineage_state(
            semantic_result,
            definition,
            ProjectRowLineageStatus.BLOCKED,
            ProjectRowLineageReason.CYCLE_BLOCKED,
        )


def test_duplicate_output_names_stay_private_unknown_and_diagnostic_free(
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
    projected = _derived_definition(parse_result, "projected")
    _assert_row_schema_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
    )
    _assert_dependency_graph_state(
        semantic_result,
        projected,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.DUPLICATE_OUTPUT_NAME,
    )
    _assert_lineage_state(
        semantic_result,
        projected,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.DUPLICATE_OUTPUT_NAME,
    )


def test_grouped_aggregate_schema_graph_and_lineage_are_concrete_without_public_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    grouped = _derived_definition(parse_result, "grouped")
    _assert_row_schema_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )
    _assert_dependency_graph_state(
        semantic_result,
        grouped,
        ProjectRowDependencyGraphStatus.CONCRETE,
        ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE,
    )
    _assert_lineage_state(
        semantic_result,
        grouped,
        ProjectRowLineageStatus.CONCRETE,
        ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
    )
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.relation_row_schemas[grouped].fields) == (
        "status",
        "total",
    )
    assert tuple(semantic_result.model.relation_aggregate_result_facts[grouped]) == (
        "total",
    )


def test_invalid_selected_let_helper_diagnostics_stay_private_and_ordered(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = subtotal + bonus\n"
            "        subtotal = score\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [("PIE-S2102", "Unknown field: total")]
    projected = _derived_definition(parse_result, "projected")
    _assert_let_state(
        semantic_result,
        projected,
        ProjectLetScopeFactsStatus.UNKNOWN,
        ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED,
    )
    _assert_row_schema_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
    )
    _assert_dependency_graph_state(
        semantic_result,
        projected,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA,
    )
    _assert_lineage_state(
        semantic_result,
        projected,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.UNKNOWN_SCHEMA,
    )


def test_project_json_v2_keeps_slice12_private_carrier_facts_private(
    tmp_path: Path,
) -> None:
    valid_parse, valid_semantic = _project_semantic_result(
        _project(
            tmp_path / "valid",
            "query projected:\n    from users\n    select:\n        id\n",
        )
    )
    invalid_parse, invalid_semantic = _project_semantic_result(
        _project(
            tmp_path / "invalid",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )

    for parse_result, semantic_result in (
        (valid_parse, valid_semantic),
        (invalid_parse, invalid_semantic),
    ):
        document = project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
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
        _assert_private_json_facts_absent(document)


def test_slice12_forbidden_files_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
    assert (
        _git_status_paths() in (set(), ALLOWED_SLICE12_GATE2_PATHS)
    ) or _phase54_active_gate2_is_active()

    for path in FORBIDDEN_SOURCE_DIFF_PATHS:
        assert (
            _git_output(["diff", "--", path]) == ""
        ) or _phase54_active_gate2_is_active(), path
    assert _git_output(["diff", "--", "grammar"]) == ""
    assert _git_output(["diff", "--", "generated"]) == ""
    assert _git_output(["diff", "--", ".github/workflows"]) == ""
    assert _git_output(["diff", "--", "pyproject.toml"]) == ""
    assert _git_output(["diff", "--", "uv.lock"]) == ""


def _assert_row_schema_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    assert semantic_result.model is not None
    state = semantic_result.model.relation_row_schema_states[definition]
    assert state.status is status
    assert state.reason is reason
    if status is ProjectRelationRowSchemaStatus.CONCRETE:
        assert state.schema is not None
    elif status is ProjectRelationRowSchemaStatus.UNKNOWN:
        assert state.schema is not None
        assert state.schema.is_unknown is True
    else:
        assert state.schema is None


def _assert_let_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectLetScopeFactsStatus,
    reason: ProjectLetScopeFactsReason,
) -> None:
    assert semantic_result.model is not None
    facts = semantic_result.model.relation_let_scope_facts[definition]
    assert facts.status is status
    assert facts.reason is reason
    assert tuple(facts.value_types) == ()


def _assert_dependency_graph_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRowDependencyGraphStatus,
    reason: ProjectRowDependencyGraphReason,
) -> None:
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_row_dependency_graphs[definition]
    assert graph.status is status
    assert graph.reason is reason
    if status is not ProjectRowDependencyGraphStatus.CONCRETE:
        assert graph.nodes == ()
        assert graph.edges == ()


def _assert_lineage_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRowLineageStatus,
    reason: ProjectRowLineageReason,
) -> None:
    assert semantic_result.model is not None
    lineage = semantic_result.model.relation_row_lineages[definition]
    assert lineage.status is status
    assert lineage.reason is reason
    if status is not ProjectRowLineageStatus.CONCRETE:
        assert lineage.facts == ()


def _assert_private_json_facts_absent(document: dict[str, object]) -> None:
    serialized = json.dumps(document)
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized
    assert _json_paths_for_key(document, "reason") == ()
    assert _json_paths_for_key(document, "status") == ("inputs[].status",)


def _json_paths_for_key(value: object, key: str, path: str = "") -> tuple[str, ...]:
    if isinstance(value, dict):
        paths: list[str] = []
        for child_key, child_value in value.items():
            child_path = child_key if not path else f"{path}.{child_key}"
            if child_key == key:
                paths.append(child_path)
            paths.extend(_json_paths_for_key(child_value, key, child_path))
        return tuple(paths)
    if isinstance(value, list):
        normalized_path = f"{path}[]" if path else "[]"
        paths = []
        for item in value:
            paths.extend(_json_paths_for_key(item, key, normalized_path))
        return tuple(dict.fromkeys(paths))
    return ()


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
    root: Path,
    relation_source: str,
    *,
    include_source: bool = True,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    source_prefix = (
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text not null\n"
        "    score: Int not null\n"
        "    bonus: Int not null\n"
        "    status: Text not null\n"
    )
    if include_source:
        source_prefix += 'source users: User is postgres.table("users")\n'
    (root / "models.pietto").write_text(
        source_prefix + relation_source,
        encoding="utf-8",
    )
    return root


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Missing derived definition: {name}")


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--short", "--untracked-files=all"])
    return {line[3:] for line in output.splitlines() if line}


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()
