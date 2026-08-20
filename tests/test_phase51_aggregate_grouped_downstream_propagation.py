from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast


import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_persistence as persistence_module
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadinessReason,
    ProjectAggregateGroupedClauseReadinessStatus,
    ProjectRelationClauseDependencyKind,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_dependency_lineage import (
    ProjectAggregateGroupedDependencyLineageReadiness,
    build_project_aggregate_grouped_dependency_lineage_readiness,
)
from pietto._project.aggregate_grouped_persistence import (
    ProjectAggregateGroupedPersistenceBundle,
    build_project_aggregate_grouped_persistence,
)
from pietto._project.aggregate_grouped_schema import (
    build_project_aggregate_grouped_schema_finalization,
    build_project_group_key_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
)
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNodeKind,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_persistence.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
EXPECTED_PROJECT_JSON_V2_KEYS = (
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

type _CandidateInputs = tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectRelationRowLineage | None,
]


def test_persistence_bundle_is_frozen_atomic_and_retains_one_slice9_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        field.name for field in fields(ProjectAggregateGroupedPersistenceBundle)
    ) == (
        "definition",
        "let_scope_facts",
        "dependency_lineage_readiness",
        "state",
        "aggregate_result_facts",
    )
    assert is_dataclass(ProjectAggregateGroupedPersistenceBundle)
    assert hasattr(ProjectAggregateGroupedPersistenceBundle, "__slots__")
    signature = inspect.signature(build_project_aggregate_grouped_persistence)
    assert tuple(signature.parameters) == (
        "definition",
        "input_schema",
        "upstream_symbol",
        "upstream_lineage",
        "fallback_path",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    for helper, parameter_names in (
        (
            build_project_aggregate_grouped_schema_finalization,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
        (
            build_project_aggregate_grouped_clause_readiness,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
        (
            build_project_aggregate_grouped_dependency_lineage_readiness,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "upstream_lineage",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
    ):
        helper_signature = inspect.signature(helper)
        assert tuple(helper_signature.parameters) == parameter_names
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in helper_signature.parameters.values()
        )
        assert helper_signature.parameters["let_scope_facts"].default is None
    assert tuple(
        inspect.signature(build_project_group_key_schema_facts).parameters
    ) == (
        "definition",
        "input_schema",
        "upstream_symbol",
        "fallback_path",
    )

    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        _aggregate_body("total = count()"),
    )
    original = (
        persistence_module.build_project_aggregate_grouped_dependency_lineage_readiness
    )
    calls: list[dict[str, Any]] = []

    def spy(**kwargs: Any) -> ProjectAggregateGroupedDependencyLineageReadiness:
        calls.append(dict(kwargs))
        return original(**kwargs)

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_dependency_lineage_readiness",
        spy,
    )
    bundle = build_project_aggregate_grouped_persistence(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=symbol,
        upstream_lineage=upstream_lineage,
        fallback_path="models.pietto",
    )

    assert len(calls) == 1
    assert calls[0]["definition"] is definition
    assert calls[0]["let_scope_facts"] is bundle.let_scope_facts
    readiness = bundle.dependency_lineage_readiness
    finalization = readiness.clause_readiness.finalization
    assert readiness.definition is definition
    assert bundle.state is finalization.state
    assert isinstance(bundle.aggregate_result_facts, MappingProxyType)
    assert tuple(bundle.aggregate_result_facts) == ("total",)
    assert (
        bundle.aggregate_result_facts["total"]
        is finalization.aggregate_result_facts["total"]
    )
    assert not hasattr(bundle, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(bundle, "state", bundle.state)
    with pytest.raises(ValueError, match="retain aggregate facts"):
        replace(bundle, aggregate_result_facts={})


def test_production_calls_slice9_readiness_once_per_eligible_definition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(
        tmp_path,
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n"
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount)\n"
        "query ordinary:\n"
        "    from users\n"
        "    select:\n"
        "        amount\n"
        "query relation_aggregate:\n"
        "    from ordinary\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "query pure_grouping:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n",
    )
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    helper_name = "_is_project_aggregate_grouped_definition"
    helper = persistence_module._is_project_aggregate_grouped_definition
    helper_signature = inspect.signature(helper)
    assert helper.__name__ == helper_name
    assert tuple(helper_signature.parameters) == ("definition",)
    helper_parameter = helper_signature.parameters["definition"]
    assert helper_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert helper_parameter.default is inspect.Parameter.empty
    assert tuple(
        helper(_derived_definition(parse_result, name))
        for name in ("aggregate", "grouped", "pure_grouping", "ordinary")
    ) == (True, True, True, False)

    model_source = MODEL_PATH.read_text(encoding="utf-8")
    persistence_source = HELPER_PATH.read_text(encoding="utf-8")
    assert "from pietto.semantic" not in model_source
    assert "import pietto.semantic" not in model_source
    assert "contains_semantic_aggregate" not in model_source
    assert f"if {helper_name}(definition):" in model_source
    assert (
        "from pietto.semantic.aggregates import contains_semantic_aggregate"
        in persistence_source
    )
    assert f"def {helper_name}(" in persistence_source
    assert helper_name not in persistence_module.__all__
    assert not hasattr(pietto, helper_name)
    assert not hasattr(project_package, helper_name)

    original_let = persistence_module.build_project_relation_let_scope_facts
    original_readiness = (
        persistence_module.build_project_aggregate_grouped_dependency_lineage_readiness
    )
    let_calls: dict[str, list[ProjectRelationLetScopeFacts]] = {}
    readiness_calls: dict[str, list[ProjectRelationLetScopeFacts | None]] = {}

    def let_spy(**kwargs: Any) -> ProjectRelationLetScopeFacts:
        definition = cast(TableDef | QueryDef, kwargs["definition"])
        result = original_let(**kwargs)
        let_calls.setdefault(definition.name, []).append(result)
        return result

    def readiness_spy(
        **kwargs: Any,
    ) -> ProjectAggregateGroupedDependencyLineageReadiness:
        definition = cast(TableDef | QueryDef, kwargs["definition"])
        let_scope_facts = cast(
            ProjectRelationLetScopeFacts | None,
            kwargs.get("let_scope_facts"),
        )
        readiness_calls.setdefault(definition.name, []).append(let_scope_facts)
        return original_readiness(**kwargs)

    monkeypatch.setattr(
        persistence_module,
        "build_project_relation_let_scope_facts",
        let_spy,
    )
    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_dependency_lineage_readiness",
        readiness_spy,
    )
    semantic_result = build_empty_project_semantic_result(parse_result)
    model = _semantic_model(semantic_result)
    eligible = ("aggregate", "grouped", "relation_aggregate", "pure_grouping")

    assert set(let_calls) == set(eligible)
    assert set(readiness_calls) == set(eligible)
    for name in eligible:
        definition = _derived_definition(parse_result, name)
        assert len(let_calls[name]) == 1
        assert len(readiness_calls[name]) == 1
        assert readiness_calls[name][0] is let_calls[name][0]
        assert model.relation_let_scope_facts[definition] is let_calls[name][0]
    assert "ordinary" not in readiness_calls


def test_aggregate_only_schema_facts_graph_and_lineage_are_persisted_atomically(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            _aggregate_body(
                "total = count()\n"
                "        maximum = max(amount)\n"
                "        summed = sum(amount + tax)"
            ),
        )
    )
    model = _semantic_model(semantic_result)
    definition = _derived_definition(parse_result, "candidate")
    state = model.relation_row_schema_states[definition]
    schema = model.relation_row_schemas[definition]
    facts = model.relation_aggregate_result_facts[definition]
    graph = model.relation_row_dependency_graphs[definition]
    lineage = model.relation_row_lineages[definition]

    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    assert state.schema is schema
    assert tuple(schema.fields) == ("total", "maximum", "summed")
    assert all(
        field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
        for field in schema.fields.values()
    )
    assert tuple(facts) == ("total", "maximum", "summed")
    assert tuple(fact.function for fact in facts.values()) == (
        "count",
        "max",
        "sum",
    )
    assert tuple(fact.argument_count for fact in facts.values()) == (0, 1, 1)
    assert model.relation_let_scope_facts[definition].status is (
        ProjectLetScopeFactsStatus.ABSENT
    )
    assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    assert graph.reason is ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
    assert lineage.status is ProjectRowLineageStatus.CONCRETE
    assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert tuple(edge.kind for edge in graph.edges) == (
        ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT,
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
    )
    assert tuple(fact.kind for fact in lineage.facts) == tuple(
        ProjectRowLineageFactKind(edge.kind.value) for edge in graph.edges
    )


def test_grouped_schema_group_key_and_aggregate_facts_preserve_select_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "        region\n"
            "    select:\n"
            "        region_name = region\n"
            "        total = count()\n"
            "        status\n"
            "        summed = sum(amount)\n",
        )
    )
    model = _semantic_model(semantic_result)
    definition = _derived_definition(parse_result, "grouped")
    schema = model.relation_row_schemas[definition]
    facts = model.relation_aggregate_result_facts[definition]
    graph = model.relation_row_dependency_graphs[definition]

    assert tuple(schema.fields) == ("region_name", "total", "status", "summed")
    assert tuple(field.result_role for field in schema.fields.values()) == (
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
    )
    assert tuple(facts) == ("total", "summed")
    assert tuple(fact.function for fact in facts.values()) == ("count", "sum")
    assert all(fact.grouped for fact in facts.values())
    projection_edges = tuple(
        (edge.kind, edge.from_node.name, edge.to_node.field_name)
        for edge in graph.edges
        if edge.kind
        in {
            ProjectRowDependencyEdgeKind.DIRECT_PROJECTION,
            ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
        }
    )
    assert projection_edges == (
        (
            ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
            "region_name",
            "region",
        ),
        (ProjectRowDependencyEdgeKind.DIRECT_PROJECTION, "status", "status"),
    )


def test_selected_let_and_field_bearing_expression_aggregates_use_one_canonical_fact_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        base = amount + tax\n"
        "        selected = base + amount\n"
        "    select:\n"
        "        total = sum(selected)\n"
        "        weighted = avg(score * weight)\n"
        "        distinct_status = count_distinct(lower(trim(status)))\n",
    )
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    original = (
        persistence_module.build_project_aggregate_grouped_dependency_lineage_readiness
    )
    captured: list[
        tuple[
            ProjectRelationLetScopeFacts,
            ProjectAggregateGroupedDependencyLineageReadiness,
        ]
    ] = []

    def spy(**kwargs: Any) -> ProjectAggregateGroupedDependencyLineageReadiness:
        let_facts = cast(ProjectRelationLetScopeFacts, kwargs["let_scope_facts"])
        readiness = original(**kwargs)
        captured.append((let_facts, readiness))
        return readiness

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_dependency_lineage_readiness",
        spy,
    )
    semantic_result = build_empty_project_semantic_result(parse_result)
    model = _semantic_model(semantic_result)
    definition = _derived_definition(parse_result, "candidate")

    assert len(captured) == 1
    let_facts, readiness = captured[0]
    finalization = readiness.clause_readiness.finalization
    assert model.relation_let_scope_facts[definition] is let_facts
    assert model.relation_row_schema_states[definition] is finalization.state
    assert model.relation_row_schemas[definition] is finalization.state.schema
    assert (
        model.relation_row_dependency_graphs[definition] is readiness.dependency_graph
    )
    assert model.relation_row_lineages[definition] is readiness.lineage
    persisted_facts = model.relation_aggregate_result_facts[definition]
    assert tuple(persisted_facts) == ("total", "weighted", "distinct_status")
    assert tuple(fact.function for fact in persisted_facts.values()) == (
        "sum",
        "avg",
        "count_distinct",
    )
    for name, fact in persisted_facts.items():
        assert fact is finalization.aggregate_result_facts[name]

    graph = model.relation_row_dependency_graphs[definition]
    argument_targets = {
        (
            edge.from_node.name,
            edge.to_node.kind,
            edge.to_node.binding_name or edge.to_node.field_name,
        )
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT
    }
    assert argument_targets == {
        ("total", ProjectRowDependencyNodeKind.LET_BINDING, "selected"),
        ("weighted", ProjectRowDependencyNodeKind.UPSTREAM_FIELD, "score"),
        ("weighted", ProjectRowDependencyNodeKind.UPSTREAM_FIELD, "weight"),
        (
            "distinct_status",
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            "status",
        ),
    }
    assert any(
        edge.kind is ProjectRowDependencyEdgeKind.LET_EXPRESSION for edge in graph.edges
    )


def test_count_relation_input_persists_without_fabricated_field_leaf(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(tmp_path, _aggregate_body("total = count()"))
    )
    model = _semantic_model(semantic_result)
    definition = _derived_definition(parse_result, "candidate")
    graph = model.relation_row_dependency_graphs[definition]
    lineage = model.relation_row_lineages[definition]

    assert tuple(edge.kind for edge in graph.edges) == (
        ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT,
    )
    assert graph.edges[0].from_node.name == "total"
    assert graph.edges[0].to_node.kind is ProjectRowDependencyNodeKind.RELATION_INPUT
    assert graph.edges[0].to_node.name == "users"
    assert all(
        node.kind is not ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        for node in graph.nodes
    )
    assert tuple(fact.kind for fact in lineage.facts) == (
        ProjectRowLineageFactKind.AGGREGATE_RELATION_INPUT,
    )
    assert lineage.facts[0].upstream_segment.kind is (
        ProjectRowLineageSegmentKind.RELATION_INPUT
    )
    assert all(fact.upstream_segment.field_name is None for fact in lineage.facts)


def test_source_table_query_and_relation_upstream_reasons_are_parity_locked(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table direct_table:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(amount)\n"
            "query direct_query:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(amount)\n"
            "table table_seed:\n"
            "    from users\n"
            "    select:\n"
            "        amount\n"
            "query from_table:\n"
            "    from table_seed\n"
            "    select:\n"
            "        total = sum(amount)\n"
            "query query_seed:\n"
            "    from users\n"
            "    select:\n"
            "        amount\n"
            "table from_query:\n"
            "    from query_seed\n"
            "    select:\n"
            "        total = sum(amount)\n"
            "query counted:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "query count_rollup:\n"
            "    from counted\n"
            "    select:\n"
            "        summed = sum(total)\n",
        )
    )
    model = _semantic_model(semantic_result)
    expected = {
        "direct_table": ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        "direct_query": ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        "from_table": ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        "from_query": ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        "count_rollup": ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
    }
    for name, reason in expected.items():
        definition = _derived_definition(parse_result, name)
        state = model.relation_row_schema_states[definition]
        graph = model.relation_row_dependency_graphs[definition]
        lineage = model.relation_row_lineages[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is reason
        assert graph.reason.value == reason.value
        assert lineage.reason.value == reason.value
    assert isinstance(_derived_definition(parse_result, "direct_table"), TableDef)
    assert isinstance(_derived_definition(parse_result, "direct_query"), QueryDef)
    assert isinstance(_derived_definition(parse_result, "from_table"), QueryDef)
    assert isinstance(_derived_definition(parse_result, "from_query"), TableDef)
    count_rollup = _derived_definition(parse_result, "count_rollup")
    count_rollup_lineage = model.relation_row_lineages[count_rollup]
    assert any(
        fact.kind is ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY
        and fact.upstream_segment.kind is ProjectRowLineageSegmentKind.RELATION_INPUT
        and fact.upstream_segment.name == "users"
        for fact in count_rollup_lineage.facts
    )


def test_one_hop_downstream_uses_bare_and_immediate_qualified_outputs_only(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = status\n"
            "        total = sum(amount)\n"
            "query bare:\n"
            "    from aggregate\n"
            "    select:\n"
            "        label\n"
            "        total\n"
            "table qualified:\n"
            "    from aggregate\n"
            "    select:\n"
            "        label_copy = aggregate.label\n"
            "        total_copy = aggregate.total\n"
            "query wrong_source:\n"
            "    from aggregate\n"
            "    select:\n"
            "        bad = users.total\n"
            "query hidden_argument:\n"
            "    from aggregate\n"
            "    select:\n"
            "        amount\n"
            "query hidden_group_key:\n"
            "    from aggregate\n"
            "    select:\n"
            "        status\n"
            "query wrong_earlier:\n"
            "    from bare\n"
            "    select:\n"
            "        bad = aggregate.total\n"
            "query multi_part:\n"
            "    from aggregate\n"
            "    select:\n"
            "        bad = db.aggregate.total\n"
            "query selected_let:\n"
            "    from users\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        total = sum(gross)\n"
            "query let_downstream:\n"
            "    from selected_let\n"
            "    select:\n"
            "        total\n"
            "query hidden_let:\n"
            "    from selected_let\n"
            "    select:\n"
            "        gross\n",
        )
    )
    model = _semantic_model(semantic_result)
    bare = _derived_definition(parse_result, "bare")
    qualified = _derived_definition(parse_result, "qualified")

    assert tuple(model.relation_row_schemas[bare].fields) == ("label", "total")
    assert tuple(model.relation_row_schemas[qualified].fields) == (
        "label_copy",
        "total_copy",
    )
    for definition in (bare, qualified):
        assert model.relation_row_schema_states[definition].status is (
            ProjectRelationRowSchemaStatus.CONCRETE
        )
    selected_let = _derived_definition(parse_result, "selected_let")
    let_downstream = _derived_definition(parse_result, "let_downstream")
    assert model.relation_row_schema_states[selected_let].status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert model.relation_row_schema_states[let_downstream].status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert tuple(model.relation_row_schemas[let_downstream].fields) == ("total",)
    for name in (
        "wrong_source",
        "hidden_argument",
        "hidden_group_key",
        "wrong_earlier",
        "multi_part",
        "hidden_let",
    ):
        _assert_non_concrete_bundle(
            model,
            _derived_definition(parse_result, name),
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            reason=ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )
    diagnostic_pairs = {
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    }
    assert {
        ("PIE-S2102", "Unknown field: users.total"),
        ("PIE-S2102", "Unknown field: amount"),
        ("PIE-S2102", "Unknown field: status"),
        ("PIE-S2102", "Unknown field: aggregate.total"),
        ("PIE-S2102", "Unknown field: db.aggregate.total"),
        ("PIE-S2102", "Unknown field: gross"),
    } <= diagnostic_pairs


def test_multi_hop_table_query_chain_activates_after_complete_upstream_persistence(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = status\n"
            "        total = sum(amount)\n"
            "table middle:\n"
            "    from aggregate\n"
            "    select:\n"
            "        key = aggregate.label\n"
            "        copied_total = aggregate.total\n"
            "query next_hop:\n"
            "    from middle\n"
            "    select:\n"
            "        label = middle.key\n"
            "        total = middle.copied_total\n"
            "table final:\n"
            "    from next_hop\n"
            "    select:\n"
            "        label\n"
            "        total\n",
        )
    )
    model = _semantic_model(semantic_result)
    definitions = tuple(
        _derived_definition(parse_result, name)
        for name in ("aggregate", "middle", "next_hop", "final")
    )

    assert tuple(model.relation_row_schema_states) == definitions
    assert tuple(model.relation_row_schemas) == definitions
    assert tuple(model.relation_row_dependency_graphs) == definitions
    assert tuple(model.relation_row_lineages) == definitions
    assert tuple(model.relation_aggregate_result_facts) == (definitions[0],)
    assert all(
        model.relation_row_schema_states[definition].status
        is ProjectRelationRowSchemaStatus.CONCRETE
        for definition in definitions
    )
    final_graph = model.relation_row_dependency_graphs[definitions[-1]]
    assert {edge.to_node.relation_name for edge in final_graph.edges} == {"next_hop"}
    final_lineage_names = {
        fact.upstream_segment.name
        for fact in model.relation_row_lineages[definitions[-1]].facts
    }
    assert {
        "next_hop.label",
        "next_hop.total",
        "middle.key",
        "middle.copied_total",
        "aggregate.label",
        "aggregate.total",
        "users.status",
        "users.amount",
    } <= final_lineage_names


def test_downstream_ordinary_projection_resets_result_role_and_preserves_ancestry(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = status\n"
            "        total = sum(amount)\n"
            "query downstream:\n"
            "    from aggregate\n"
            "    select:\n"
            "        status_copy = label\n"
            "        total_copy = total\n",
        )
    )
    model = _semantic_model(semantic_result)
    aggregate = _derived_definition(parse_result, "aggregate")
    downstream = _derived_definition(parse_result, "downstream")
    upstream_schema = model.relation_row_schemas[aggregate]
    downstream_schema = model.relation_row_schemas[downstream]

    assert upstream_schema.fields["label"].result_role is (
        ProjectRowResultRole.GROUP_KEY
    )
    assert upstream_schema.fields["total"].result_role is (
        ProjectRowResultRole.AGGREGATE_RESULT
    )
    for upstream_name, downstream_name in (
        ("label", "status_copy"),
        ("total", "total_copy"),
    ):
        upstream_field = upstream_schema.fields[upstream_name]
        downstream_field = downstream_schema.fields[downstream_name]
        assert downstream_field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
        assert downstream_field.resolved_type is upstream_field.resolved_type
        assert downstream_field.nullability is upstream_field.nullability
    assert downstream not in model.relation_aggregate_result_facts

    graph = model.relation_row_dependency_graphs[downstream]
    assert tuple(edge.kind for edge in graph.edges) == (
        ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
        ProjectRowDependencyEdgeKind.RENAMED_PROJECTION,
    )
    lineage = model.relation_row_lineages[downstream]
    for output_name, source_name in (
        ("status_copy", "users.status"),
        ("total_copy", "users.amount"),
    ):
        output_facts = tuple(
            fact
            for fact in lineage.facts
            if fact.output_segment.output_name == output_name
        )
        assert output_facts[0].kind is ProjectRowLineageFactKind.RENAMED_PROJECTION
        assert output_facts[0].upstream_segment.kind is (
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD
        )
        assert any(
            fact.kind is ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY
            and fact.upstream_segment.name == source_name
            for fact in output_facts[1:]
        )


def test_non_concrete_results_persist_atomically_and_do_not_activate_downstream(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query invalid_literal:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(1)\n"
            "query unknown_downstream:\n"
            "    from invalid_literal\n"
            "    select:\n"
            "        total\n"
            "query unsupported_order:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "    order by:\n"
            "        amount desc\n"
            "query deferred_downstream:\n"
            "    from unsupported_order\n"
            "    select:\n"
            "        total\n",
        )
    )
    model = _semantic_model(semantic_result)
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "invalid_literal"),
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        reason=ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "unknown_downstream"),
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    )
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "unsupported_order"),
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "deferred_downstream"),
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
    )


def test_duplicate_unknown_invalid_unresolved_and_cycle_outcomes_remain_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(
        tmp_path,
        "query duplicate_output:\n"
        "    from users\n"
        "    select:\n"
        "        duplicate = sum(amount)\n"
        "        duplicate = avg(score)\n"
        "query duplicate_key:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "query unavailable:\n"
        "    from users\n"
        "    select:\n"
        "        total = sum(missing)\n"
        "query invalid:\n"
        "    from users\n"
        "    select:\n"
        "        total = sum(1)\n"
        "query unresolved:\n"
        "    from absent\n"
        "    select:\n"
        "        total = count()\n"
        "query cycle_a:\n"
        "    from cycle_b\n"
        "    select:\n"
        "        total = count()\n"
        "query cycle_b:\n"
        "    from cycle_a\n"
        "    select:\n"
        "        total = count()\n",
    )
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    original = persistence_module.build_project_aggregate_grouped_persistence
    calls: list[str] = []
    bundles: dict[str, ProjectAggregateGroupedPersistenceBundle] = {}

    def spy(**kwargs: Any) -> ProjectAggregateGroupedPersistenceBundle:
        definition = cast(TableDef | QueryDef, kwargs["definition"])
        calls.append(definition.name)
        bundle = original(**kwargs)
        bundles[definition.name] = bundle
        return bundle

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_persistence",
        spy,
    )
    semantic_result = build_empty_project_semantic_result(parse_result)
    model = _semantic_model(semantic_result)

    expected = {
        "duplicate_output": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ),
        "duplicate_key": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
        ),
        "unavailable": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        ),
        "invalid": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ),
        "unresolved": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
        ),
        "cycle_a": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ),
        "cycle_b": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ),
    }
    for name, (status, reason) in expected.items():
        _assert_non_concrete_bundle(
            model,
            _derived_definition(parse_result, name),
            status=status,
            reason=reason,
        )
    assert calls == ["duplicate_output", "duplicate_key", "unavailable", "invalid"]
    for name in calls:
        finalization = bundles[
            name
        ].dependency_lineage_readiness.clause_readiness.finalization
        definition = _derived_definition(parse_result, name)
        assert (
            model.relation_let_scope_facts[definition] is bundles[name].let_scope_facts
        )
        assert finalization.state.status is not (
            ProjectRelationRowSchemaStatus.CONCRETE
        )
        assert bundles[name].state is finalization.state
    diagnostic_codes = {diagnostic.code for diagnostic in semantic_result.diagnostics}
    assert {"PIE-S2301", "PIE-S2302"} <= diagnostic_codes


def test_clause_readiness_gates_activation_without_new_persisted_model_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(
        tmp_path,
        "query ready:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = status\n"
        "        total = count()\n"
        "    satisfying:\n"
        '        (total > 0) and (label == "open")\n'
        "    order by:\n"
        "        total desc\n"
        "        label asc\n"
        "    limit 5\n"
        "query ready_downstream:\n"
        "    from ready\n"
        "    select:\n"
        "        total\n"
        "query invalid_clause:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    satisfying:\n"
        "        amount > 0\n"
        "query blocked_downstream:\n"
        "    from invalid_clause\n"
        "    select:\n"
        "        total\n",
    )
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    original = (
        persistence_module.build_project_aggregate_grouped_dependency_lineage_readiness
    )
    captured: dict[str, ProjectAggregateGroupedDependencyLineageReadiness] = {}

    def spy(**kwargs: Any) -> ProjectAggregateGroupedDependencyLineageReadiness:
        definition = cast(TableDef | QueryDef, kwargs["definition"])
        result = original(**kwargs)
        captured[definition.name] = result
        return result

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_dependency_lineage_readiness",
        spy,
    )
    semantic_result = build_empty_project_semantic_result(parse_result)
    model = _semantic_model(semantic_result)
    ready = _derived_definition(parse_result, "ready")
    ready_downstream = _derived_definition(parse_result, "ready_downstream")
    invalid = _derived_definition(parse_result, "invalid_clause")
    blocked_downstream = _derived_definition(parse_result, "blocked_downstream")

    ready_readiness = captured["ready"].clause_readiness
    assert ready_readiness.status is (
        ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    )
    assert ready_readiness.reason is (
        ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY
    )
    assert ready_readiness.limit_present
    assert {fact.kind for fact in ready_readiness.dependency_facts} == {
        ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT,
        ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT,
        ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT,
    }
    assert model.relation_row_schema_states[ready].status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert model.relation_row_schema_states[ready_downstream].status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )

    invalid_readiness = captured["invalid_clause"]
    assert invalid_readiness.clause_readiness.finalization.state.status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert invalid_readiness.dependency_graph.status is (
        ProjectRowDependencyGraphStatus.UNKNOWN
    )
    _assert_non_concrete_bundle(
        model,
        invalid,
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        reason=ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )
    _assert_non_concrete_bundle(
        model,
        blocked_downstream,
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    )
    assert tuple(field.name for field in fields(ProjectSemanticModel)) == (
        "root",
        "config_path",
        "inputs",
        "catalog",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
        "source_row_schemas",
        "relation_row_schemas",
        "relation_row_schema_states",
        "relation_let_scope_facts",
        "relation_row_dependency_graphs",
        "relation_row_lineages",
        "relation_dependency_graph",
        "relation_aggregate_result_facts",
        "relation_window_result_facts",
    )
    for name in (
        "relation_clause_readiness",
        "relation_clause_dependency_facts",
        "relation_aggregate_grouped_readiness",
    ):
        assert not hasattr(model, name)
    graph_values = {
        edge.kind.value for edge in model.relation_row_dependency_graphs[ready].edges
    }
    assert graph_values.isdisjoint(
        {"group_key_input", "satisfying_output", "grouped_order_output"}
    )
    serialized_text = json.dumps(
        project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
    )
    for private_value in (
        "ProjectAggregateGroupedClauseReadiness",
        "WindowResultProjectFact",
        "relation_clause_readiness",
        "relation_window_result_facts",
        "group_key_input",
        "satisfying_output",
        "grouped_order_output",
        "limit_present",
    ):
        assert private_value not in serialized_text


def test_pure_grouping_persists_helper_deferred_reason_with_empty_payloads(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query pure_grouping:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "query downstream:\n"
            "    from pure_grouping\n"
            "    select:\n"
            "        status\n",
        )
    )
    model = _semantic_model(semantic_result)
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "pure_grouping"),
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    _assert_non_concrete_bundle(
        model,
        _derived_definition(parse_result, "downstream"),
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
    )
    assert not semantic_result.diagnostics


def test_persistence_helper_is_private_no_full_analyze_and_unserialized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert persistence_module.__all__ == ()
    for name in (
        "ProjectAggregateGroupedPersistenceBundle",
        "build_project_aggregate_grouped_persistence",
        "WindowResultProjectFact",
        "relation_window_result_facts",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    assert "ProjectSemanticModel" not in helper_source
    assert "semantic_api.analyze" not in helper_source
    assert "from pietto.semantic import analyze" not in helper_source
    assert "Diagnostic(" not in helper_source

    root = _project(tmp_path, _aggregate_body("total = count()"))
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)

    def forbidden(**_kwargs: Any) -> ProjectAggregateGroupedPersistenceBundle:
        raise AssertionError("parse-only unexpectedly invoked persistence")

    monkeypatch.setattr(
        persistence_module,
        "build_project_aggregate_grouped_persistence",
        forbidden,
    )
    assert check_project_parse_only(root).ok

    serialized = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    assert tuple(serialized) == EXPECTED_PROJECT_JSON_V2_KEYS
    serialized_text = json.dumps(serialized)
    for value in (
        "ProjectAggregateGroupedPersistenceBundle",
        "ProjectAggregateGroupedDependencyLineageReadiness",
        "WindowResultProjectFact",
        "relation_aggregate_result_facts",
        "relation_window_result_facts",
        "aggregate_relation_input",
        "satisfying_output",
        "grouped_order_output",
    ):
        assert value not in serialized_text


def _candidate_inputs(root: Path, relations: str) -> _CandidateInputs:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    model = _semantic_model(semantic_result)
    definition = _derived_definition(parse_result, "candidate")
    upstream_symbol = model.relation_resolutions[definition.from_clause]
    upstream_definition = upstream_symbol.definition
    if isinstance(upstream_definition, SourceDef):
        input_schema = model.source_row_schemas[upstream_definition]
        upstream_lineage = None
    else:
        assert isinstance(upstream_definition, (TableDef, QueryDef))
        input_schema = model.relation_row_schemas[upstream_definition]
        upstream_lineage = model.relation_row_lineages[upstream_definition]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
        upstream_lineage,
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _semantic_model(result: ProjectSemanticResult) -> ProjectSemanticModel:
    assert result.model is not None
    return result.model


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "shape User:\n"
        "    active: Bool not null\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        "    score: Float not null\n"
        "    weight: Float nullable\n"
        "    price: Decimal(12, 2) not null\n"
        "    status: Text not null\n"
        "    region: Text nullable\n"
        "    created_at: Timestamp not null\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
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
    raise AssertionError(f"Derived definition not found: {name}")


def _aggregate_body(select_items: str) -> str:
    return f"query candidate:\n    from users\n    select:\n        {select_items}\n"


def _assert_non_concrete_bundle(
    model: ProjectSemanticModel,
    definition: TableDef | QueryDef,
    *,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    assert status is not ProjectRelationRowSchemaStatus.CONCRETE
    state = model.relation_row_schema_states[definition]
    graph = model.relation_row_dependency_graphs[definition]
    lineage = model.relation_row_lineages[definition]
    let_scope_facts = model.relation_let_scope_facts[definition]
    assert state.status is status
    assert state.reason is reason
    if status is ProjectRelationRowSchemaStatus.UNKNOWN:
        assert state.schema is not None
        assert state.schema.is_unknown
        assert state.schema.fields == {}
        assert model.relation_row_schemas[definition] is state.schema
    else:
        assert state.schema is None
        assert definition not in model.relation_row_schemas
    assert definition not in model.relation_aggregate_result_facts
    assert definition not in model.relation_window_result_facts
    assert isinstance(let_scope_facts, ProjectRelationLetScopeFacts)
    if definition.let_clause is None:
        assert let_scope_facts.status is ProjectLetScopeFactsStatus.ABSENT
        assert let_scope_facts.clause is None
    else:
        assert let_scope_facts.clause is definition.let_clause
    assert graph.status.value == status.value
    assert graph.reason.value == reason.value
    assert graph.nodes == ()
    assert graph.edges == ()
    assert lineage.status.value == status.value
    assert lineage.reason.value == reason.value
    assert lineage.facts == ()
