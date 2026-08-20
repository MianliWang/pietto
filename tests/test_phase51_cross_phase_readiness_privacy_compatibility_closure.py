from __future__ import annotations

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
