from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, fields, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRoot,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.errors import SourceLocation
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowOrderBindingFact,
    WindowOrderFieldBinding,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PERSISTENCE_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_persistence.py"

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


def test_result_role_and_fact_carriers_are_exact_frozen_and_slots() -> None:
    assert tuple((role.name, role.value) for role in ProjectRowResultRole) == (
        ("ORDINARY_ROW_VALUE", "ordinary_row_value"),
        ("GROUP_KEY", "group_key"),
        ("AGGREGATE_RESULT", "aggregate_result"),
        ("WINDOW_RESULT", "window_result"),
    )
    assert tuple(field.name for field in fields(ProjectRowField)) == (
        "name",
        "resolved_type",
        "nullability",
        "field_def",
        "provenance",
        "result_role",
    )
    assert tuple(field.name for field in fields(ProjectAggregateResultFact)) == (
        "function",
        "output_name",
        "grouped",
        "argument_count",
        "location",
    )
    assert is_dataclass(ProjectAggregateResultFact)
    assert hasattr(ProjectAggregateResultFact, "__slots__")
    assert tuple((item.name, item.value) for item in RankingAdvancePolicy) == (
        ("PER_ROW", "per_row"),
        ("GAPPED_PEER_RANK", "preceding_row_count_plus_one"),
        (
            "DENSE_PEER_RANK",
            "preceding_distinct_peer_group_count_plus_one",
        ),
    )
    assert tuple(field.name for field in fields(RankingWindowSemanticFact)) == (
        "semantic_fact",
        "advance_policy",
    )
    assert is_dataclass(RankingWindowSemanticFact)
    assert hasattr(RankingWindowSemanticFact, "__slots__")
    assert tuple((item.name, item.value) for item in DistributionWindowPolicy) == (
        ("PERCENT_RANK", "percent_rank"),
        ("CUMULATIVE_DISTRIBUTION", "cumulative_distribution"),
        ("BALANCED_BUCKETS", "balanced_buckets"),
    )
    assert tuple(field.name for field in fields(DistributionWindowSemanticFact)) == (
        "semantic_fact",
        "distribution_policy",
        "ranking_fact",
        "bucket_count",
    )
    assert is_dataclass(DistributionWindowSemanticFact)
    assert hasattr(DistributionWindowSemanticFact, "__slots__")
    assert tuple(field.name for field in fields(WindowOrderFieldBinding)) == (
        "order_item",
        "value_type",
        "effective_direction",
    )
    assert tuple(field.name for field in fields(WindowOrderBindingFact)) == (
        "semantic_fact",
        "bindings",
    )
    assert tuple(field.name for field in fields(WindowExpressionAnalysis)) == (
        "semantic_fact",
        "ranking_fact",
        "distribution_fact",
        "partition_binding_fact",
        "order_binding_fact",
        "navigation_fact",
    )

    row_field = _row_field("id")
    fact = _fact(function="Future_AGG", output_name="total")

    assert row_field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    assert fact.function == "Future_AGG"
    assert not hasattr(fact, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(fact, "function", "count")
    window_source = (REPO_ROOT / "src/pietto/_project/window_semantics.py").read_text(
        encoding="utf-8"
    )
    assert "def build_row_number_window_result_project_fact(" in window_source
    assert "WindowResultProjectFact(" in window_source


def test_existing_constructor_shapes_keep_the_ordinary_default() -> None:
    resolved_type = _resolved_int()
    positional = ProjectRowField(
        "id",
        resolved_type,
        ProjectRowFieldNullability.NON_NULL,
    )
    keyword = ProjectRowField(
        name="id",
        resolved_type=resolved_type,
        nullability=ProjectRowFieldNullability.NON_NULL,
        field_def=None,
        provenance=None,
    )

    assert positional.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    assert keyword.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE


@pytest.mark.parametrize(
    "overrides",
    (
        {"function": ""},
        {"function": 1},
        {"output_name": ""},
        {"output_name": 1},
        {"grouped": 0},
        {"grouped": "false"},
        {"argument_count": True},
        {"argument_count": -1},
        {"argument_count": 1.5},
        {"location": None},
    ),
)
def test_aggregate_result_fact_validation_is_structural_only(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "function": "Future_AGG",
        "output_name": "total",
        "grouped": False,
        "argument_count": 0,
        "location": _location(),
    }
    values.update(overrides)

    with pytest.raises(ValueError):
        ProjectAggregateResultFact(**cast(Any, values))


def test_function_identity_is_not_normalized_or_semantically_catalogued() -> None:
    fact = _fact(function="Future_AGG", output_name="total", argument_count=17)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    persistence_source = PERSISTENCE_PATH.read_text(encoding="utf-8")

    assert fact.function == "Future_AGG"
    assert fact.argument_count == 17
    assert "count_distinct" not in model_source
    assert "SEMANTIC_AGGREGATE_NAMES" not in model_source
    assert "expected_semantic_aggregate_arity" not in model_source
    assert "contains_semantic_aggregate" not in model_source
    assert "from pietto.semantic" not in model_source
    assert "import pietto.semantic" not in model_source
    assert "semantic_api" not in model_source
    assert "_is_project_aggregate_grouped_definition" in model_source
    assert "build_project_aggregate_grouped_persistence" in model_source
    assert (
        "from pietto.semantic.aggregates import contains_semantic_aggregate"
        in persistence_source
    )
    assert "def _is_project_aggregate_grouped_definition(" in persistence_source
    assert "semantic_api.analyze" not in persistence_source
    assert "from pietto.semantic import analyze" not in persistence_source
    assert "semantic.analyze" not in model_source


def test_nested_fact_maps_are_defensive_readonly_and_source_ordered(
    tmp_path: Path,
) -> None:
    parse_result = check_project_parse_only(_aggregate_project(tmp_path))
    assert parse_result.ok
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")
    aggregate_schema = ProjectRowSchema(
        fields={
            "total": _row_field(
                "total",
                result_role=ProjectRowResultRole.AGGREGATE_RESULT,
            ),
            "maximum": _row_field(
                "maximum",
                result_role=ProjectRowResultRole.AGGREGATE_RESULT,
            ),
        }
    )
    grouped_schema = ProjectRowSchema(
        fields={
            "email": _row_field(
                "email",
                result_role=ProjectRowResultRole.GROUP_KEY,
            ),
            "total": _row_field(
                "total",
                result_role=ProjectRowResultRole.AGGREGATE_RESULT,
            ),
        }
    )
    aggregate_facts = {
        "total": _fact(function="count", output_name="total"),
        "maximum": _fact(function="max", output_name="maximum", argument_count=1),
    }
    grouped_facts = {
        "total": _fact(function="count", output_name="total", grouped=True),
    }
    caller_facts = {
        aggregate: aggregate_facts,
        grouped: grouped_facts,
    }
    model = _model(
        parse_result,
        relation_row_schemas={
            aggregate: aggregate_schema,
            grouped: grouped_schema,
        },
        relation_aggregate_result_facts=caller_facts,
    )

    aggregate_facts["late"] = _fact(function="sum", output_name="late")
    caller_facts.clear()

    assert isinstance(model.relation_aggregate_result_facts, MappingProxyType)
    assert tuple(model.relation_aggregate_result_facts) == (aggregate, grouped)
    assert tuple(model.relation_aggregate_result_facts[aggregate]) == (
        "total",
        "maximum",
    )
    assert tuple(model.relation_aggregate_result_facts[grouped]) == ("total",)
    assert isinstance(
        model.relation_aggregate_result_facts[aggregate], MappingProxyType
    )
    with pytest.raises(TypeError):
        cast(
            MutableMapping[str, ProjectAggregateResultFact],
            model.relation_aggregate_result_facts[aggregate],
        )["other"] = _fact(function="count", output_name="other")
    with pytest.raises(TypeError):
        cast(
            MutableMapping[
                TableDef | QueryDef,
                MutableMapping[str, ProjectAggregateResultFact],
            ],
            model.relation_aggregate_result_facts,
        )[aggregate] = {}


def test_model_rejects_inconsistent_aggregate_result_facts(tmp_path: Path) -> None:
    parse_result = check_project_parse_only(_aggregate_project(tmp_path))
    assert parse_result.ok
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")
    aggregate_field = _row_field(
        "total",
        result_role=ProjectRowResultRole.AGGREGATE_RESULT,
    )
    aggregate_schema = ProjectRowSchema(fields={"total": aggregate_field})
    ordinary_schema = ProjectRowSchema(fields={"total": _row_field("total")})
    group_key_schema = ProjectRowSchema(
        fields={
            "total": _row_field(
                "total",
                result_role=ProjectRowResultRole.GROUP_KEY,
            )
        }
    )
    fact = _fact(function="Future_AGG", output_name="total")

    with pytest.raises(ValueError, match="relation keys"):
        _model(
            parse_result,
            relation_row_schemas={aggregate: aggregate_schema},
            relation_aggregate_result_facts=cast(Any, {"aggregate": {"total": fact}}),
        )
    with pytest.raises(ValueError, match="output key mismatch"):
        _model(
            parse_result,
            relation_row_schemas={aggregate: aggregate_schema},
            relation_aggregate_result_facts={aggregate: {"other": fact}},
        )
    with pytest.raises(ValueError, match="relation schema"):
        _model(
            parse_result,
            relation_row_schemas={},
            relation_aggregate_result_facts={aggregate: {"total": fact}},
        )
    with pytest.raises(ValueError, match="schema field"):
        _model(
            parse_result,
            relation_row_schemas={
                aggregate: ProjectRowSchema(fields={"other": _row_field("other")})
            },
            relation_aggregate_result_facts={aggregate: {"total": fact}},
        )
    for schema in (ordinary_schema, group_key_schema):
        with pytest.raises(ValueError, match="aggregate result role"):
            _model(
                parse_result,
                relation_row_schemas={aggregate: schema},
                relation_aggregate_result_facts={aggregate: {"total": fact}},
            )
    with pytest.raises(ValueError, match="matching fact"):
        _model(
            parse_result,
            relation_row_schemas={aggregate: aggregate_schema},
            relation_aggregate_result_facts={},
        )
    with pytest.raises(ValueError, match="grouped mismatch"):
        _model(
            parse_result,
            relation_row_schemas={grouped: aggregate_schema},
            relation_aggregate_result_facts={grouped: {"total": fact}},
        )


def test_existing_project_row_field_paths_remain_ordinary(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _ordinary_project(tmp_path)
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    projected = _derived_definition(parse_result, "projected")
    downstream = _derived_definition(parse_result, "downstream")

    for field in semantic_result.model.source_row_schemas[source].fields.values():
        assert field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    for definition in (projected, downstream):
        for field in semantic_result.model.relation_row_schemas[
            definition
        ].fields.values():
            assert field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    assert semantic_result.model.relation_aggregate_result_facts == {}


def test_both_production_model_paths_keep_empty_facts_default(tmp_path: Path) -> None:
    normal_parse, normal_result = _project_semantic_result(
        _ordinary_project(tmp_path / "normal")
    )
    duplicate_parse = check_project_parse_only(_duplicate_project(tmp_path / "dup"))
    duplicate_result = build_empty_project_semantic_result(duplicate_parse)

    assert normal_parse.ok
    assert normal_result.model is not None
    assert normal_result.model.relation_aggregate_result_facts == {}
    assert duplicate_parse.ok
    assert duplicate_result.diagnostics
    assert duplicate_result.model is not None
    assert duplicate_result.model.relation_aggregate_result_facts == {}


def test_aggregate_and_grouped_relations_are_concrete_with_persisted_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _aggregate_project(tmp_path)
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    model = semantic_result.model
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")
    assert tuple(model.relation_aggregate_result_facts) == (aggregate, grouped)
    assert tuple(model.relation_aggregate_result_facts[aggregate]) == (
        "total",
        "maximum",
    )
    assert tuple(model.relation_aggregate_result_facts[grouped]) == ("total",)
    assert tuple(model.relation_row_schemas[aggregate].fields) == (
        "total",
        "maximum",
    )
    assert tuple(model.relation_row_schemas[grouped].fields) == ("email", "total")
    for name in ("aggregate", "grouped"):
        definition = _derived_definition(parse_result, name)
        state = model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        schema = state.schema
        assert schema is not None
        assert schema is model.relation_row_schemas[definition]
        assert all(
            field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
            for output_name, field in schema.fields.items()
            if output_name in model.relation_aggregate_result_facts[definition]
        )


def test_new_private_facts_are_not_exported_or_serialized(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _ordinary_project(tmp_path)
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert tuple(document) == EXPECTED_PROJECT_JSON_V2_KEYS
    assert project_package.__all__ == ()
    for name in (
        "ProjectRowResultRole",
        "ProjectAggregateResultFact",
        "relation_aggregate_result_facts",
        "ordinary_row_value",
        "group_key",
        "aggregate_result",
        "WindowResultIdentity",
        "WindowDependencyOccurrence",
        "WindowDependencyEdge",
        "WindowResultProjectFact",
        "RankingAdvancePolicy",
        "RankingWindowSemanticFact",
        "DistributionWindowPolicy",
        "DistributionWindowSemanticFact",
        "WindowOrderFieldBinding",
        "WindowOrderBindingFact",
        "WindowExpressionAnalysis",
        "NavigationDirection",
        "NavigationOffsetFact",
        "NavigationDefaultFact",
        "NavigationWindowSemanticFact",
        "window_result",
        "analyze_window_expression",
        "analyze_distribution_window_expression",
        "analyze_ranking_window_expression",
        "analyze_navigation_window_expression",
        "build_window_result_project_fact",
        "build_ranking_window_result_project_fact",
        "build_navigation_window_result_project_fact",
        "build_row_number_window_result_project_fact",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized

    for relative_path in (
        "src/pietto/_project/json_v2.py",
        "src/pietto/cli_json.py",
        "src/pietto/_metadata/serializer.py",
    ):
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "ProjectAggregateResultFact" not in source
        assert "relation_aggregate_result_facts" not in source


def _model(
    parse_result: ProjectParseCheckResult,
    *,
    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema],
    relation_aggregate_result_facts: object,
) -> ProjectSemanticModel:
    return ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=parse_result.parsed_inputs,
        catalog=ProjectSemanticCatalog(),
        relation_row_schemas=relation_row_schemas,
        relation_aggregate_result_facts=cast(Any, relation_aggregate_result_facts),
    )


def _row_field(
    name: str,
    *,
    result_role: ProjectRowResultRole = ProjectRowResultRole.ORDINARY_ROW_VALUE,
) -> ProjectRowField:
    return ProjectRowField(
        name=name,
        resolved_type=_resolved_int(),
        nullability=ProjectRowFieldNullability.NON_NULL,
        result_role=result_role,
    )


def _resolved_int() -> ProjectResolvedType:
    return ProjectResolvedType(name="Int", kind=ProjectResolvedTypeKind.BUILTIN)


def _fact(
    *,
    function: str,
    output_name: str,
    grouped: bool = False,
    argument_count: int = 0,
) -> ProjectAggregateResultFact:
    return ProjectAggregateResultFact(
        function=function,
        output_name=output_name,
        grouped=grouped,
        argument_count=argument_count,
        location=_location(),
    )


def _location() -> SourceLocation:
    return SourceLocation(path="models.pietto", line=1, column=1)


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _ordinary_project(path: Path) -> Path:
    return _project(
        path,
        "query projected:\n"
        "    from users\n"
        "    let:\n"
        "        adjusted = score + bonus\n"
        "    select:\n"
        "        id\n"
        "        renamed = id\n"
        "        computed = score + bonus\n"
        "        adjusted\n"
        "query downstream:\n"
        "    from projected\n"
        "    select:\n"
        "        computed\n",
    )


def _aggregate_project(path: Path) -> Path:
    return _project(
        path,
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n"
        "        maximum = max(score)\n"
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        email\n"
        "    select:\n"
        "        email\n"
        "        total = count()\n",
    )


def _duplicate_project(path: Path) -> Path:
    return _project(
        path,
        "query duplicate:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query duplicate:\n"
        "    from users\n"
        "    select:\n"
        "        id\n",
    )


def _project(path: Path, relations: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (path / "models.pietto").write_text(
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text not null\n"
        "    score: Int not null\n"
        "    bonus: Int nullable\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
        encoding="utf-8",
    )
    return path


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


_SLICE11_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "src/pietto/semantic/window_order_analysis.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
)

_SLICE12_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-lag-lead-navigation-offset-default-nullability-contract-v1.md",
    "src/pietto/semantic/window_navigation_analysis.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
)
# Phase 53 Slice 13 reader migration.
