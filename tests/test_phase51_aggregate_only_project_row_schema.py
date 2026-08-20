from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateSchemaFacts,
    ProjectAggregateSelectedResult,
    build_project_aggregate_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import (
    CallExpr,
    Expression,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_schema.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md"
)

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

SUPPORTED_AGGREGATE_CASES = (
    ("count()", "count", 0, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(active)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(amount)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(score)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(price)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(status)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(order_date)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(created_at)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(raw)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    ("count(payload)", "count", 1, "Int", ProjectRowFieldNullability.NON_NULL),
    (
        "count(customer_id)",
        "count",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(active)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(amount)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(score)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(price)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(status)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(order_date)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(created_at)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    (
        "count_distinct(customer_id)",
        "count_distinct",
        1,
        "Int",
        ProjectRowFieldNullability.NON_NULL,
    ),
    ("sum(amount)", "sum", 1, "Int", ProjectRowFieldNullability.NULLABLE),
    ("sum(score)", "sum", 1, "Float", ProjectRowFieldNullability.NULLABLE),
    ("sum(price)", "sum", 1, "Decimal", ProjectRowFieldNullability.NULLABLE),
    ("avg(amount)", "avg", 1, "Float", ProjectRowFieldNullability.NULLABLE),
    ("avg(score)", "avg", 1, "Float", ProjectRowFieldNullability.NULLABLE),
    ("avg(price)", "avg", 1, "Decimal", ProjectRowFieldNullability.NULLABLE),
    ("min(amount)", "min", 1, "Int", ProjectRowFieldNullability.NULLABLE),
    ("min(score)", "min", 1, "Float", ProjectRowFieldNullability.NULLABLE),
    ("min(price)", "min", 1, "Decimal", ProjectRowFieldNullability.NULLABLE),
    ("min(order_date)", "min", 1, "Date", ProjectRowFieldNullability.NULLABLE),
    (
        "min(created_at)",
        "min",
        1,
        "Timestamp",
        ProjectRowFieldNullability.NULLABLE,
    ),
    ("max(amount)", "max", 1, "Int", ProjectRowFieldNullability.NULLABLE),
    ("max(score)", "max", 1, "Float", ProjectRowFieldNullability.NULLABLE),
    ("max(price)", "max", 1, "Decimal", ProjectRowFieldNullability.NULLABLE),
    ("max(order_date)", "max", 1, "Date", ProjectRowFieldNullability.NULLABLE),
    (
        "max(created_at)",
        "max",
        1,
        "Timestamp",
        ProjectRowFieldNullability.NULLABLE,
    ),
)


def test_aggregate_carriers_are_exact_frozen_slots_defensive_and_fail_closed(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        "query aggregate:\n    from users\n    select:\n        total = sum(amount)\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    item, selected = next(iter(facts.selected_results.items()))
    call = item.expression
    assert isinstance(call, CallExpr)

    assert tuple(field.name for field in fields(ProjectAggregateSelectedResult)) == (
        "field",
        "fact",
    )
    assert tuple(field.name for field in fields(ProjectAggregateSchemaFacts)) == (
        "selected_results",
    )
    assert is_dataclass(ProjectAggregateSelectedResult)
    assert is_dataclass(ProjectAggregateSchemaFacts)
    assert hasattr(ProjectAggregateSelectedResult, "__slots__")
    assert hasattr(ProjectAggregateSchemaFacts, "__slots__")
    assert not hasattr(selected, "__dict__")
    assert not hasattr(facts, "__dict__")
    assert not isinstance(facts, ProjectRowSchema)

    with pytest.raises(FrozenInstanceError):
        setattr(selected, "fact", selected.fact)
    with pytest.raises(FrozenInstanceError):
        setattr(facts, "selected_results", {})

    caller_results = dict(facts.selected_results)
    copied = ProjectAggregateSchemaFacts(selected_results=caller_results)
    caller_results.clear()
    assert isinstance(copied.selected_results, MappingProxyType)
    assert tuple(copied.selected_results) == (item,)
    with pytest.raises(TypeError):
        cast(
            MutableMapping[SelectItem, ProjectAggregateSelectedResult],
            copied.selected_results,
        )[item] = selected

    provenance = selected.field.provenance
    assert provenance is not None
    malformed_fields = (
        replace(
            selected.field,
            result_role=ProjectRowResultRole.ORDINARY_ROW_VALUE,
        ),
        replace(
            selected.field,
            field_def=input_schema.fields["amount"].field_def,
        ),
        replace(selected.field, provenance=None),
        replace(
            selected.field,
            provenance=replace(
                provenance,
                kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
            ),
        ),
        replace(selected.field, name="other"),
        replace(
            selected.field,
            resolved_type=ProjectResolvedType(
                name="<unknown>",
                kind=ProjectResolvedTypeKind.UNKNOWN,
            ),
        ),
        replace(
            selected.field,
            nullability=ProjectRowFieldNullability.UNKNOWN,
        ),
    )
    for malformed_field in malformed_fields:
        with pytest.raises(ValueError):
            ProjectAggregateSelectedResult(
                field=malformed_field,
                fact=selected.fact,
            )
    with pytest.raises(ValueError):
        ProjectAggregateSelectedResult(
            field=cast(Any, object()),
            fact=selected.fact,
        )
    with pytest.raises(ValueError):
        ProjectAggregateSelectedResult(
            field=selected.field,
            fact=cast(Any, object()),
        )

    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(selected_results={})
    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(selected_results=cast(Any, []))
    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(selected_results=cast(Any, {"total": selected}))
    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(selected_results=cast(Any, {item: object()}))
    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(
            selected_results={replace(item, alias="other"): selected}
        )
    with pytest.raises(ValueError):
        ProjectAggregateSchemaFacts(
            selected_results={replace(item, expression=call.arguments[0]): selected}
        )

    incoherent_results = (
        replace(selected, fact=replace(selected.fact, function="count")),
        replace(selected, fact=replace(selected.fact, grouped=True)),
        replace(selected, fact=replace(selected.fact, argument_count=0)),
        replace(
            selected,
            fact=replace(
                selected.fact,
                location=replace(
                    selected.fact.location,
                    column=selected.fact.location.column + 1,
                ),
            ),
        ),
    )
    for incoherent in incoherent_results:
        with pytest.raises(ValueError):
            ProjectAggregateSchemaFacts(selected_results={item: incoherent})


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_table_and_query_one_output_candidates_are_identical(
    tmp_path: Path,
    relation_kind: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        f"{relation_kind} aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n",
    )
    item, selected = next(
        iter(
            _build_facts(
                definition, input_schema, upstream_symbol
            ).selected_results.items()
        )
    )

    assert item.alias == "total"
    assert selected.field.name == "total"
    assert selected.field.resolved_type == ProjectResolvedType(
        name="Int",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert selected.field.nullability is ProjectRowFieldNullability.NON_NULL
    assert selected.fact.function == "count"
    assert selected.fact.argument_count == 0


@pytest.mark.parametrize(
    ("expression", "function", "argument_count", "type_name", "nullability"),
    SUPPORTED_AGGREGATE_CASES,
)
def test_exact_current_direct_aggregate_type_and_nullability_matrix(
    tmp_path: Path,
    expression: str,
    function: str,
    argument_count: int,
    type_name: str,
    nullability: ProjectRowFieldNullability,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        f"        result = {expression}\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    item, selected = next(iter(facts.selected_results.items()))
    location = _location(item.expression, fallback_path="models.pietto")

    assert tuple(facts.selected_results) == (item,)
    assert selected.field.name == item.alias == "result"
    assert selected.field.resolved_type.name == type_name
    assert selected.field.resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
    assert selected.field.resolved_type.symbol is None
    assert selected.field.nullability is nullability
    assert selected.field.field_def is None
    assert selected.field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
    assert selected.field.provenance == ProjectRowFieldProvenance(
        kind=ProjectRowFieldProvenanceKind.AGGREGATE,
        symbol=upstream_symbol,
        location=location,
    )
    assert selected.fact == ProjectAggregateResultFact(
        function=function,
        output_name="result",
        grouped=False,
        argument_count=argument_count,
        location=location,
    )
    if type_name == "Decimal":
        assert selected.field.resolved_type == ProjectResolvedType(
            name="Decimal",
            kind=ProjectResolvedTypeKind.BUILTIN,
        )


def test_qualified_multiple_repeated_and_duplicate_aliases_preserve_select_order(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count(users.amount)\n"
        "        unique_count = count_distinct(users.customer_id)\n"
        "        repeated = sum(users.amount)\n"
        "        repeated = sum(users.amount)\n"
        "        latest = max(users.created_at)\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    items = tuple(facts.selected_results)
    selected = tuple(facts.selected_results.values())

    assert len(items) == 5
    assert tuple(item.alias for item in items) == (
        "total",
        "unique_count",
        "repeated",
        "repeated",
        "latest",
    )
    assert tuple(result.field.name for result in selected) == (
        "total",
        "unique_count",
        "repeated",
        "repeated",
        "latest",
    )
    assert tuple(result.fact.function for result in selected) == (
        "count",
        "count_distinct",
        "sum",
        "sum",
        "max",
    )
    assert items[2] != items[3]
    assert selected[2] is not selected[3]
    for item, result in facts.selected_results.items():
        assert result.fact.location == _location(
            item.expression,
            fallback_path="models.pietto",
        )


@pytest.mark.parametrize(
    "relation_body",
    (
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = sum(wrong.amount)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = sum(catalog.users.amount)\n",
        "query aggregate:\n    from users\n    select:\n        sum(amount)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = count(amount, score)\n",
        "query aggregate:\n    from users\n    select:\n        result = sum()\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = median(amount)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = COUNT(amount)\n",
        "query aggregate:\n    from users\n    select:\n        result = sum(status)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = count(anything)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = count(enum_status)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = count_distinct(raw)\n",
        "query aggregate:\n    from users\n    select:\n        result = sum(1)\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = sum(count(amount))\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = sum(amount) + 1\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        result = count()\n"
        "        status\n",
        "query aggregate:\n"
        "    from users\n"
        "    select:\n"
        "        valid = count()\n"
        "        invalid = sum(status)\n",
    ),
)
def test_invalid_shape_type_function_composition_and_mixed_output_have_no_candidate(
    tmp_path: Path,
    relation_body: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        relation_body,
    )

    assert (
        build_project_aggregate_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_unknown_missing_and_empty_inputs_have_no_partial_candidate(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        "query aggregate:\n    from users\n    select:\n        result = sum(amount)\n",
    )
    missing_fields = dict(input_schema.fields)
    missing_fields.pop("amount")
    unknown_fields = dict(input_schema.fields)
    unknown_fields["amount"] = replace(
        input_schema.fields["amount"],
        resolved_type=ProjectResolvedType(
            name="<unknown>",
            kind=ProjectResolvedTypeKind.UNKNOWN,
        ),
        nullability=ProjectRowFieldNullability.UNKNOWN,
    )

    for unavailable_schema in (
        ProjectRowSchema(is_unknown=True),
        ProjectRowSchema(fields={}),
        ProjectRowSchema(fields=missing_fields),
        ProjectRowSchema(fields=unknown_fields),
    ):
        assert (
            build_project_aggregate_schema_facts(
                definition=definition,
                input_schema=unavailable_schema,
                upstream_symbol=upstream_symbol,
                fallback_path="models.pietto",
            )
            is None
        )

    no_select = replace(definition, select_items=())
    assert (
        build_project_aggregate_schema_facts(
            definition=no_select,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )

    count_definition = replace(
        definition,
        select_items=(
            _derived_definition(
                check_project_parse_only(
                    _project(
                        tmp_path / "count",
                        "query count_only:\n"
                        "    from users\n"
                        "    select:\n"
                        "        result = count()\n",
                    )
                ),
                "count_only",
            ).select_items[0],
        ),
    )
    assert (
        build_project_aggregate_schema_facts(
            definition=count_definition,
            input_schema=ProjectRowSchema(is_unknown=True),
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_grouped_definition_remains_outside_no_group_wrapper(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _aggregate_inputs(
        tmp_path,
        "query aggregate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        result = count()\n",
    )

    assert (
        build_project_aggregate_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_aggregate_and_grouped_outputs_are_persisted_private_and_unserialized(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "table grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
        )
    )
    assert semantic_result.model is not None
    model = semantic_result.model
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")
    assert tuple(model.relation_aggregate_result_facts) == (aggregate, grouped)
    assert tuple(model.relation_aggregate_result_facts[aggregate]) == ("total",)
    assert tuple(model.relation_aggregate_result_facts[grouped]) == ("total",)

    for definition, expected_fields in (
        (aggregate, ("total",)),
        (grouped, ("status", "total")),
    ):
        state = model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        schema = state.schema
        assert schema is not None
        assert schema is model.relation_row_schemas[definition]
        assert tuple(schema.fields) == expected_fields
        assert schema.fields["total"].result_role is (
            ProjectRowResultRole.AGGREGATE_RESULT
        )

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    assert tuple(document) == EXPECTED_PROJECT_JSON_V2_KEYS
    assert project_package.__all__ == ()
    assert "aggregate_grouped_schema" not in model_source
    for name in (
        "ProjectAggregateSelectedResult",
        "ProjectAggregateSchemaFacts",
        "build_project_aggregate_schema_facts",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized


def test_helper_plan_and_contract_keep_the_bounded_slice4_boundary() -> None:
    helper_source = inspect.getsource(build_project_aggregate_schema_facts)
    module_source = HELPER_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan_lines = plan.splitlines()

    assert "### Slice 4 Gate 2 Bounded Implementation Status" in plan_lines
    assert "## Slice 4 Gate 2 Bounded Implementation Status" not in plan_lines
    assert spec.splitlines()[0] == (
        "# Phase 51 Aggregate-only Result Candidate Foundation v1"
    )
    for required in (
        "candidate-only",
        "unpersisted",
        "ProjectAggregateSelectedResult",
        "ProjectAggregateSchemaFacts",
        "build_project_aggregate_schema_facts",
        "build_project_row_expression_value_types",
        "semantic_aggregate_call_name",
        "is_supported_semantic_aggregate_arity",
        "is_direct_field_argument",
        "is_supported_semantic_aggregate_argument_expression",
        "semantic_projection_aggregate_result_value_type",
        "ProjectRowResultRole.AGGREGATE_RESULT",
        "ProjectRowFieldProvenanceKind.AGGREGATE",
        "SelectItem",
        "MappingProxyType",
        "DEFERRED_PHASE48_BEHAVIOR",
        "exactly these 14 paths",
        "ruff check --fix",
        "/tmp/pietto-phase51-slice4-gate2-evidence-and-diff.txt",
    ):
        assert required in spec, required
    for slice_number in range(5, 11):
        assert f"Slice {slice_number}" in spec

    assert "ProjectRowSchema(" not in helper_source
    assert "ProjectSemanticModel" not in module_source
    assert "SEMANTIC_AGGREGATE_NAMES" not in module_source
    assert "semantic.analyze" not in module_source
    assert "analyze(" not in helper_source


def _aggregate_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "aggregate",
) -> tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
]:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    assert semantic_result.model is not None
    definition = _derived_definition(parse_result, definition_name)
    source = _source_definition(parse_result, "users")
    input_schema = semantic_result.model.source_row_schemas[source]
    upstream_symbol = semantic_result.model.relation_resolutions[definition.from_clause]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
    )


def _build_facts(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> ProjectAggregateSchemaFacts:
    facts = build_project_aggregate_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert facts is not None
    return facts


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "enum Status:\n"
        "    active\n"
        "    paused\n"
        "shape User:\n"
        "    active: Bool not null\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        "    score: Float not null\n"
        "    weight: Float nullable\n"
        "    price: Decimal(12, 2) not null\n"
        "    status: Text not null\n"
        "    order_date: Date nullable\n"
        "    created_at: Timestamp not null\n"
        "    raw: Bytes not null\n"
        "    payload: Json not null\n"
        "    customer_id: UUID not null\n"
        "    anything: Any nullable\n"
        "    enum_status: Status not null\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
        encoding="utf-8",
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


def _location(expression: Expression, *, fallback_path: str) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
