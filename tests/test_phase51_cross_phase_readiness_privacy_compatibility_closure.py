from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_clause_facts as clause_module
import pietto._project.aggregate_grouped_dependency_lineage as dependency_lineage_module
import pietto._project.aggregate_grouped_persistence as persistence_module
import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowResultRole,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphStatus,
)
from pietto._project.row_lineage import (
    ProjectRowLineageFactKind,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md"
)
ACTIVE_ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
PHASE50_PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
PHASE50_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase50-completion-audit-and-status-lock-v1.md"
)

EXPECTED_GATE2_PATHS = {
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
    "tests/test_phase49_selected_let_derived_output_schema.py",
    "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase51_group_key_project_row_schema.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
}
EXPECTED_UNTRACKED_PATHS = {
    "docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
}
PHASE52_GATE2_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}
PHASE52_UNTRACKED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
}
SLICE2_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
SLICE4_PATH_COUNTS = (138, 2, 140)
SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
SLICE5_PATH_COUNTS = (164, 3, 167)
SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
SLICE6_PATH_COUNTS = (57, 4, 61)
SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
SLICE7_PATH_COUNTS = (59, 3, 62)
SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
SLICE8_PATH_COUNTS = (66, 3, 69)
SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
SLICE9_PATH_COUNTS = (68, 3, 71)
CI_REPAIR_BASE_HEAD_SHA = "321ec6f80737015648bc1f81b0561fdd34610e92"
CI_REPAIR_MODIFIED_PATHS = {
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
}
BOUNDARY_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)
PROTECTED_HASHES = {
    ".github/workflows/ci.yml": (
        "56339c3e565471c3a95a0f79a05eaf9596d734a173d1936d5df167526508ddac"
    ),
    ".python-version": (
        "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d"
    ),
    "pyproject.toml": (
        "851e706f2cbafb24c48068cdd6fd8a6ada1f93317618000be71db3681c40a1a8"
    ),
    "uv.lock": "12795f072df20fb688b37e484dd4561cd33e34bf601be3cb0fa1f9075eee38a2",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": (
        "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169"
    ),
}
PROJECT_JSON_V2_KEYS = (
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
CONTRACT_H2_HEADINGS = (
    "## Purpose And Slice Identity",
    "## Authority And Trusted Slice 10 Handoff",
    "## Phase 51 Slice 1-10 State",
    "## Production-state Compatibility Closure",
    "## Qualification Compatibility Closure",
    "## Diagnostic-transition Closure",
    "## Privacy And Serialization Closure",
    "## Public Python Export Closure",
    "## Parse-only And Parser-error Bypass",
    "## Ordering Determinism And Compatibility Closure",
    "## Static-lock Migration Ledger",
    "## Compiler Project-private And Protected-surface Closure",
    "## Phase 52 Readiness Boundary",
    "## Explicit Deferred-owner Boundary",
    "## Production Public Diagnostic And Release Non-goals",
    "## Exact Gate 2 Allowlist",
    "## Environment Strategy",
    "## Formatting And Hash Policy",
    "## Exact Validation Matrix",
    "## Clean-tree And Natural-CI Matrix",
    "## Same-task Repair And Evidence Policy",
    "## Future Gate 3 Condition",
    "## Slice 12 Handoff Boundary",
    "## Stop Conditions",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "shape User:\n"
        "    email: Text not null\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        "    score: Int not null\n"
        "    bonus: Int nullable\n"
        "    status: Text not null\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
        encoding="utf-8",
    )
    return root


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    assert semantic_result.model is not None
    return parse_result, semantic_result


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived definition not found: {name}")


def _diagnostic_pairs(result: ProjectSemanticResult) -> list[tuple[str, str]]:
    return [(diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics]


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _compiler_digest() -> str:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return _digest(
        tuple(sorted(paths, key=lambda path: path.relative_to(REPO_ROOT).as_posix()))
    )


def test_mixed_aggregate_grouped_diagnostic_order_and_non_concrete_suppression_are_exact(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query unresolved:\n"
            "    from missing_relation\n"
            "    select:\n"
            "        total = count()\n"
            "query aggregate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = status\n"
            "        total = sum(amount)\n"
            "query invalid_concrete:\n"
            "    from aggregate\n"
            "    select:\n"
            "        bad = users.total\n"
            "query cycle_a:\n"
            "    from cycle_b\n"
            "    select:\n"
            "        total = count()\n"
            "query cycle_b:\n"
            "    from cycle_a\n"
            "    select:\n"
            "        total = count()\n"
            "query pure_grouping:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "query pure_downstream:\n"
            "    from pure_grouping\n"
            "    select:\n"
            "        status\n"
            "query duplicate_output:\n"
            "    from users\n"
            "    select:\n"
            "        duplicate = sum(amount)\n"
            "        duplicate = avg(score)\n"
            "query duplicate_downstream:\n"
            "    from duplicate_output\n"
            "    select:\n"
            "        duplicate\n"
            "query invalid_grouped_let:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    group by:\n"
            "        email\n"
            "    select:\n"
            "        total\n"
            "query invalid_let_downstream:\n"
            "    from invalid_grouped_let\n"
            "    select:\n"
            "        total\n"
            "query blocked_downstream:\n"
            "    from unresolved\n"
            "    select:\n"
            "        total\n",
        )
    )
    model = semantic_result.model
    assert model is not None

    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation"),
        ("PIE-S2102", "Unknown field: users.total"),
        ("PIE-S2302", "Relation cycle detected: cycle_a -> cycle_b -> cycle_a"),
    ]

    aggregate = _derived_definition(parse_result, "aggregate")
    aggregate_state = model.relation_row_schema_states[aggregate]
    aggregate_schema = model.relation_row_schemas[aggregate]
    assert aggregate_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        aggregate_state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    )
    assert aggregate_state.schema is aggregate_schema
    assert tuple(aggregate_schema.fields) == ("label", "total")
    assert tuple(model.relation_aggregate_result_facts[aggregate]) == ("total",)

    expected_non_concrete = {
        "unresolved": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
        ),
        "invalid_concrete": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        ),
        "cycle_a": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ),
        "cycle_b": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ),
        "pure_grouping": (
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ),
        "pure_downstream": (
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        ),
        "duplicate_output": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ),
        "duplicate_downstream": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        ),
        "invalid_grouped_let": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ),
        "invalid_let_downstream": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        ),
        "blocked_downstream": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        ),
    }
    for name, (status, reason) in expected_non_concrete.items():
        definition = _derived_definition(parse_result, name)
        state = model.relation_row_schema_states[definition]
        graph = model.relation_row_dependency_graphs[definition]
        lineage = model.relation_row_lineages[definition]

        assert state.status is status
        assert state.reason is reason
        assert graph.status.value == status.value
        assert graph.reason.value == reason.value
        assert graph.nodes == ()
        assert graph.edges == ()
        assert lineage.status.value == status.value
        assert lineage.reason.value == reason.value
        assert lineage.facts == ()
        assert definition not in model.relation_aggregate_result_facts
        if status is ProjectRelationRowSchemaStatus.UNKNOWN:
            assert state.schema is model.relation_row_schemas[definition]
            assert state.schema is not None
            assert state.schema.is_unknown
            assert state.schema.fields == {}
        else:
            assert state.schema is None
            assert definition not in model.relation_row_schemas


def test_out_of_order_aggregate_grouped_chain_preserves_all_six_map_orders(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query final_aggregate:\n"
            "    from middle\n"
            "    select:\n"
            "        grand_total = sum(copied_total)\n"
            "        rows = count()\n"
            "table middle:\n"
            "    from grouped\n"
            "    select:\n"
            "        copied_label = grouped.label\n"
            "        copied_total = grouped.total\n"
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = status\n"
            "        total = sum(amount)\n",
        )
    )
    assert semantic_result.diagnostics == ()
    model = semantic_result.model
    assert model is not None
    final_aggregate = _derived_definition(parse_result, "final_aggregate")
    middle = _derived_definition(parse_result, "middle")
    grouped = _derived_definition(parse_result, "grouped")
    source_order = (final_aggregate, middle, grouped)
    completion_order = (grouped, middle, final_aggregate)

    assert tuple(model.relation_row_schemas) == completion_order
    assert tuple(model.relation_row_schema_states) == completion_order
    assert tuple(model.relation_let_scope_facts) == source_order
    assert tuple(model.relation_aggregate_result_facts) == (
        final_aggregate,
        grouped,
    )
    assert tuple(model.relation_row_dependency_graphs) == source_order
    assert tuple(model.relation_row_lineages) == source_order

    for definition in source_order:
        state = model.relation_row_schema_states[definition]
        schema = model.relation_row_schemas[definition]
        graph = model.relation_row_dependency_graphs[definition]
        lineage = model.relation_row_lineages[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.schema is schema
        assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
        assert lineage.status is ProjectRowLineageStatus.CONCRETE
        assert graph.reason.value == state.reason.value
        assert lineage.reason.value == state.reason.value

    assert tuple(model.relation_row_schemas[grouped].fields) == ("label", "total")
    assert tuple(model.relation_row_schemas[middle].fields) == (
        "copied_label",
        "copied_total",
    )
    assert tuple(model.relation_row_schemas[final_aggregate].fields) == (
        "grand_total",
        "rows",
    )
    assert tuple(model.relation_aggregate_result_facts[final_aggregate]) == (
        "grand_total",
        "rows",
    )
    assert tuple(model.relation_aggregate_result_facts[grouped]) == ("total",)
    assert tuple(
        fact.function
        for fact in model.relation_aggregate_result_facts[final_aggregate].values()
    ) == ("sum", "count")
    assert all(
        field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
        for field in model.relation_row_schemas[final_aggregate].fields.values()
    )

    final_graph = model.relation_row_dependency_graphs[final_aggregate]
    assert tuple(edge.kind for edge in final_graph.edges) == (
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
        ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT,
    )
    assert tuple(
        (edge.from_node.name, edge.to_node.name) for edge in final_graph.edges
    ) == (
        ("grand_total", "middle.copied_total"),
        ("rows", "middle"),
    )
    grand_total_lineage = tuple(
        fact
        for fact in model.relation_row_lineages[final_aggregate].facts
        if fact.output_segment.output_name == "grand_total"
    )
    assert tuple(fact.kind for fact in grand_total_lineage) == (
        ProjectRowLineageFactKind.AGGREGATE_ARGUMENT,
        ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
        ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
    )
    assert tuple(fact.upstream_segment.name for fact in grand_total_lineage) == (
        "middle.copied_total",
        "grouped.total",
        "users.amount",
    )
    assert grand_total_lineage[0].upstream_segment.kind is (
        ProjectRowLineageSegmentKind.UPSTREAM_FIELD
    )


def test_current_aggregate_grouped_private_facts_remain_unserialized_and_unexported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "project",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = status\n"
        "        total = sum(gross)\n"
        "    satisfying:\n"
        '        (total > 0) and (label == "open")\n'
        "    order by:\n"
        "        total desc\n"
        "        label asc\n"
        "    limit 5\n"
        "query downstream:\n"
        "    from grouped\n"
        "    select:\n"
        "        label\n"
        "        total\n",
    )
    parse_result, semantic_result = _project_semantic_result(root)
    assert semantic_result.ok
    model = semantic_result.model
    assert model is not None
    grouped = _derived_definition(parse_result, "grouped")
    downstream = _derived_definition(parse_result, "downstream")
    assert tuple(model.relation_row_schemas[grouped].fields) == ("label", "total")
    assert tuple(model.relation_aggregate_result_facts[grouped]) == ("total",)
    assert model.relation_let_scope_facts[grouped].value_types
    assert model.relation_row_dependency_graphs[grouped].edges
    assert model.relation_row_lineages[grouped].facts
    assert tuple(model.relation_row_schemas[downstream].fields) == ("label", "total")

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    assert tuple(document) == PROJECT_JSON_V2_KEYS
    serialized = json.dumps(document)
    private_tokens = (
        "relation_row_schemas",
        "relation_row_schema_states",
        "relation_let_scope_facts",
        "relation_aggregate_result_facts",
        "relation_row_dependency_graphs",
        "relation_row_lineages",
        "relation_dependency_graph",
        "ProjectRowSchema",
        "ProjectRelationRowSchemaState",
        "ProjectRelationLetScopeFacts",
        "ProjectAggregateResultFact",
        "ProjectRelationRowDependencyGraph",
        "ProjectRelationRowLineage",
        "ProjectAggregateGroupedSchemaFinalization",
        "ProjectAggregateGroupedClauseReadiness",
        "ProjectAggregateGroupedDependencyLineageReadiness",
        "ProjectAggregateGroupedPersistenceBundle",
        "group_key_input",
        "satisfying_output",
        "grouped_order_output",
        "aggregate_argument",
        "aggregate_relation_input",
        "transitive_dependency",
        "relation_clause_readiness",
        "dependency_lineage_readiness",
        "limit_present",
    )
    assert all(token not in serialized for token in private_tokens)

    assert project_package.__all__ == ()
    assert clause_module.__all__ == ()
    assert dependency_lineage_module.__all__ == ()
    assert persistence_module.__all__ == ()
    private_exports = (
        "ProjectSemanticModel",
        "ProjectRowSchema",
        "ProjectRelationRowSchemaState",
        "ProjectRelationLetScopeFacts",
        "ProjectRelationRowDependencyGraph",
        "ProjectRelationRowLineage",
        "ProjectAggregateGroupedSchemaFinalization",
        "ProjectAggregateGroupedClauseReadiness",
        "ProjectAggregateGroupedDependencyLineageReadiness",
        "ProjectAggregateGroupedPersistenceBundle",
        "build_project_aggregate_grouped_schema_finalization",
        "build_project_aggregate_grouped_clause_readiness",
        "build_project_aggregate_grouped_dependency_lineage_readiness",
        "build_project_aggregate_grouped_persistence",
    )
    for public_module in (pietto, project_package):
        assert all(not hasattr(public_module, name) for name in private_exports)

    single_file = tmp_path / "single.pietto"
    single_file.write_text(
        "shape Single:\n"
        "    id: Int not null\n"
        'source singles: Single is postgres.table("singles")\n'
        "query projected:\n"
        "    from singles\n"
        "    select:\n"
        "        id\n",
        encoding="utf-8",
    )
    assert cli.main(["check", str(single_file), "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    check_document = cast(dict[str, object], json.loads(captured.out))
    assert tuple(check_document) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert check_document["schema_version"] == 1
    assert {"artifact", "metadata", "mode", "project"}.isdisjoint(check_document)

    assert cli.main(["explain", str(single_file), "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    explain_document = cast(dict[str, object], json.loads(captured.out))
    assert tuple(explain_document) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert {"mode", "project", "inputs", "result"}.isdisjoint(explain_document)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("parse-only and parser-error paths must bypass semantics")

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_persistence",
        forbidden,
    )
    assert check_project_parse_only(root).ok

    parser_error_root = _project(tmp_path / "parser-error", "")
    (parser_error_root / "models.pietto").write_text(
        "shape Broken\n    id: Int\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "build_empty_project_semantic_result", forbidden)
    assert (
        cli.main(["check", "--project", str(parser_error_root), "--format", "json"])
        == 1
    )
    captured = capsys.readouterr()
    assert captured.err == ""
    parser_error_document = cast(dict[str, object], json.loads(captured.out))
    parser_diagnostics = cast(
        list[dict[str, object]], parser_error_document["diagnostics"]
    )
    assert [diagnostic["code"] for diagnostic in parser_diagnostics] == ["PIE-P1000"]
    assert tuple(parser_error_document) == PROJECT_JSON_V2_KEYS


def test_package_version_remains_current() -> None:
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_phase52_and_deferred_owner_boundaries_are_locked() -> None:
    roadmap = _normalized(ACTIVE_ROADMAP_PATH)
    plan = _normalized(PLAN_PATH)
    contract = _normalized(SPEC_PATH)
    phase50_handoff = (
        f"{_normalized(PHASE50_PLAN_PATH)} {_normalized(PHASE50_SPEC_PATH)}"
    )

    phase_titles = (
        (52, "Core Type-System Capability Foundation"),
        (53, "Window Function Syntax And Capability Contract"),
        (54, "Import / Module / Export Readiness"),
        (55, "Semantic Package Asset Schema"),
        (56, "Capability Profile Static Schema And Declared Checking"),
        (57, "PostgreSQL Extension Signature-Catalog Readiness"),
        (58, "Project Explain / Portability / Public Metadata Readiness"),
        (59, "Package Graph And Lineage / Provenance Integration"),
        (60, "Multi-dialect Capability Ecosystem Completion Checkpoint"),
    )
    assert all(
        f"Phase {phase}: {title}" in phase50_handoff for phase, title in phase_titles
    )
    assert all(f"| {phase} | {title} |" in roadmap for phase, title in phase_titles)

    for required in (
        "Phase 52",
        "Phase 53",
        "Phase 54",
        "Phase 55",
        "Phase 56",
        "Phase 57",
        "Phase 58",
        "Phase 59",
        "Phase 60",
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT",
        "POST60_PROJECT_IR",
        "POST60_MULTI_RELATION_SQL",
    ):
        assert required in roadmap
        assert required in plan
        assert required in contract
    for required in (
        "exact-current type-system capability carrier and fail-closed lookup",
        "independently versioned",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "Project JSON v2",
        "JOIN",
        "grain",
        "fanout",
        "project IR/SQL",
        "runtime/database execution",
    ):
        assert required in contract
    assert contract.count("Slice 11 implements no compiler or runtime behavior.") == 1
