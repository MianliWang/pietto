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
    ProjectGroupedSchemaFacts,
    ProjectGroupedSelectedResult,
    build_project_aggregate_schema_facts,
    build_project_grouped_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
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
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_schema.py"
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


def test_grouped_carriers_are_exact_frozen_slots_defensive_and_fail_closed(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    key_item, aggregate_item = tuple(facts.selected_results)
    key_result = facts.selected_results[key_item]
    aggregate_result = facts.selected_results[aggregate_item]
    aggregate_fact = aggregate_result.aggregate_fact
    assert aggregate_fact is not None
    assert isinstance(key_item.expression, NameExpr)
    assert isinstance(aggregate_item.expression, CallExpr)
    assert isinstance(key_result.field, ProjectRowField)

    assert tuple(field.name for field in fields(ProjectGroupedSelectedResult)) == (
        "field",
        "aggregate_fact",
    )
    assert tuple(field.name for field in fields(ProjectGroupedSchemaFacts)) == (
        "group_keys",
        "selected_results",
    )
    assert is_dataclass(ProjectGroupedSelectedResult)
    assert is_dataclass(ProjectGroupedSchemaFacts)
    assert hasattr(ProjectGroupedSelectedResult, "__slots__")
    assert hasattr(ProjectGroupedSchemaFacts, "__slots__")
    assert not hasattr(key_result, "__dict__")
    assert not hasattr(facts, "__dict__")
    assert not isinstance(facts, ProjectRowSchema)

    with pytest.raises(FrozenInstanceError):
        setattr(key_result, "aggregate_fact", aggregate_fact)
    with pytest.raises(FrozenInstanceError):
        setattr(facts, "selected_results", {})

    caller_results = dict(facts.selected_results)
    copied = ProjectGroupedSchemaFacts(
        group_keys=facts.group_keys,
        selected_results=caller_results,
    )
    caller_results.clear()
    assert isinstance(copied.selected_results, MappingProxyType)
    assert tuple(copied.selected_results) == (key_item, aggregate_item)
    with pytest.raises(TypeError):
        cast(
            MutableMapping[SelectItem, ProjectGroupedSelectedResult],
            copied.selected_results,
        )[key_item] = key_result

    key_provenance = key_result.field.provenance
    aggregate_provenance = aggregate_result.field.provenance
    assert key_provenance is not None
    assert aggregate_provenance is not None

    malformed_selected_results = (
        (cast(Any, object()), None),
        (
            replace(
                key_result.field,
                result_role=ProjectRowResultRole.ORDINARY_ROW_VALUE,
            ),
            None,
        ),
        (key_result.field, aggregate_fact),
        (replace(key_result.field, provenance=None), None),
        (
            replace(
                key_result.field,
                provenance=replace(
                    key_provenance,
                    kind=ProjectRowFieldProvenanceKind.AGGREGATE,
                ),
            ),
            None,
        ),
        (
            replace(
                key_result.field,
                resolved_type=ProjectResolvedType(
                    name="<unknown>",
                    kind=ProjectResolvedTypeKind.UNKNOWN,
                ),
            ),
            None,
        ),
        (aggregate_result.field, None),
        (
            replace(
                aggregate_result.field,
                field_def=input_schema.fields["status"].field_def,
            ),
            aggregate_fact,
        ),
        (replace(aggregate_result.field, provenance=None), aggregate_fact),
        (
            replace(
                aggregate_result.field,
                provenance=replace(
                    aggregate_provenance,
                    kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
                ),
            ),
            aggregate_fact,
        ),
        (replace(aggregate_result.field, name="other"), aggregate_fact),
        (
            replace(
                aggregate_result.field,
                resolved_type=ProjectResolvedType(
                    name="<unknown>",
                    kind=ProjectResolvedTypeKind.UNKNOWN,
                ),
            ),
            aggregate_fact,
        ),
        (
            replace(
                aggregate_result.field,
                nullability=ProjectRowFieldNullability.UNKNOWN,
            ),
            aggregate_fact,
        ),
        (aggregate_result.field, replace(aggregate_fact, grouped=False)),
        (aggregate_result.field, cast(Any, object())),
    )
    for malformed_field, malformed_fact in malformed_selected_results:
        with pytest.raises(ValueError):
            ProjectGroupedSelectedResult(
                field=malformed_field,
                aggregate_fact=malformed_fact,
            )

    with pytest.raises(ValueError, match="non-empty tuple"):
        ProjectGroupedSchemaFacts(
            group_keys=(),
            selected_results=facts.selected_results,
        )
    with pytest.raises(ValueError, match="non-empty tuple"):
        ProjectGroupedSchemaFacts(
            group_keys=cast(Any, list(facts.group_keys)),
            selected_results=facts.selected_results,
        )
    with pytest.raises(ValueError, match="unique"):
        ProjectGroupedSchemaFacts(
            group_keys=(facts.group_keys[0], facts.group_keys[0]),
            selected_results=facts.selected_results,
        )
    with pytest.raises(ValueError, match="group-key facts"):
        ProjectGroupedSchemaFacts(
            group_keys=(cast(Any, object()),),
            selected_results=facts.selected_results,
        )
    with pytest.raises(ValueError, match="mapping"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results=cast(Any, []),
        )
    with pytest.raises(ValueError, match="non-empty selected"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={},
        )
    with pytest.raises(ValueError, match="select-item"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results=cast(Any, {"status": key_result}),
        )
    with pytest.raises(ValueError, match="grouped selected-result"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results=cast(Any, {key_item: object()}),
        )
    with pytest.raises(ValueError, match="aggregate result"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={key_item: key_result},
        )
    with pytest.raises(ValueError, match="output identity"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={
                replace(key_item, alias="other"): key_result,
                aggregate_item: aggregate_result,
            },
        )
    with pytest.raises(ValueError, match="input field mismatch"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={
                key_item: replace(
                    key_result,
                    field=replace(
                        key_result.field,
                        resolved_type=ProjectResolvedType(
                            name="Int",
                            kind=ProjectResolvedTypeKind.BUILTIN,
                        ),
                    ),
                ),
                aggregate_item: aggregate_result,
            },
        )
    with pytest.raises(ValueError, match="resolved group-key identity"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={
                replace(
                    key_item,
                    expression=replace(key_item.expression, name="region"),
                ): key_result,
                aggregate_item: aggregate_result,
            },
        )
    with pytest.raises(ValueError, match="direct aggregate call"):
        ProjectGroupedSchemaFacts(
            group_keys=facts.group_keys,
            selected_results={
                key_item: key_result,
                replace(
                    aggregate_item,
                    expression=key_item.expression,
                ): aggregate_result,
            },
        )

    incoherent_aggregate_results = (
        replace(
            aggregate_result,
            aggregate_fact=replace(aggregate_fact, function="sum"),
        ),
        replace(
            aggregate_result,
            aggregate_fact=replace(aggregate_fact, argument_count=1),
        ),
        replace(
            aggregate_result,
            aggregate_fact=replace(
                aggregate_fact,
                location=replace(
                    aggregate_fact.location,
                    column=aggregate_fact.location.column + 1,
                ),
            ),
        ),
    )
    for incoherent in incoherent_aggregate_results:
        with pytest.raises(ValueError):
            ProjectGroupedSchemaFacts(
                group_keys=facts.group_keys,
                selected_results={key_item: key_result, aggregate_item: incoherent},
            )


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_table_and_query_share_one_key_one_aggregate_candidate_shape(
    tmp_path: Path,
    relation_kind: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        f"{relation_kind} grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = users.status\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    key_item, aggregate_item = tuple(facts.selected_results)
    key_result = facts.selected_results[key_item]
    aggregate_result = facts.selected_results[aggregate_item]
    aggregate_fact = aggregate_result.aggregate_fact

    assert tuple(facts.selected_results) == definition.select_items
    assert tuple(fact.field_identity for fact in facts.group_keys) == ("status",)
    input_key_field = input_schema.fields["status"]
    assert key_result.field.name == "label"
    assert key_result.field.resolved_type == input_key_field.resolved_type
    assert key_result.field.nullability is input_key_field.nullability
    assert key_result.field.field_def is input_key_field.field_def
    assert key_result.field.result_role is ProjectRowResultRole.GROUP_KEY
    assert key_result.aggregate_fact is None
    assert key_result.field.provenance == ProjectRowFieldProvenance(
        kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
        symbol=upstream_symbol,
        location=_location(key_item.expression, fallback_path="models.pietto"),
    )
    assert aggregate_fact is not None
    assert aggregate_result.field.name == "total"
    assert aggregate_result.field.resolved_type == ProjectResolvedType(
        name="Int",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert aggregate_result.field.nullability is ProjectRowFieldNullability.NON_NULL
    assert aggregate_result.field.field_def is None
    assert aggregate_result.field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
    assert aggregate_result.field.provenance == ProjectRowFieldProvenance(
        kind=ProjectRowFieldProvenanceKind.AGGREGATE,
        symbol=upstream_symbol,
        location=_location(
            aggregate_item.expression,
            fallback_path="models.pietto",
        ),
    )
    assert aggregate_fact.function == "count"
    assert aggregate_fact.grouped is True
    assert aggregate_fact.argument_count == 0
    assert aggregate_fact.location == _location(
        aggregate_item.expression,
        fallback_path="models.pietto",
    )


def test_group_key_unknown_nullability_is_retained_for_slice7_availability(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    fields_with_unknown_key = dict(input_schema.fields)
    fields_with_unknown_key["status"] = replace(
        fields_with_unknown_key["status"],
        nullability=ProjectRowFieldNullability.UNKNOWN,
    )

    facts = _build_facts(
        definition,
        ProjectRowSchema(fields=fields_with_unknown_key),
        upstream_symbol,
    )
    key_result = next(iter(facts.selected_results.values()))

    assert key_result.field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert key_result.aggregate_fact is None


def test_multiple_keys_and_direct_aggregates_preserve_exact_select_order(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.region\n"
        "    select:\n"
        "        first_key = status\n"
        "        total = count()\n"
        "        counted = count(users.amount)\n"
        "        distinct_status = count_distinct(status)\n"
        "        summed = sum(amount)\n"
        "        averaged = avg(amount)\n"
        "        earliest = min(created_at)\n"
        "        latest = max(users.created_at)\n"
        "        users.region\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    items = tuple(facts.selected_results)
    selected = tuple(facts.selected_results.values())

    assert items == definition.select_items
    assert tuple(item.alias for item in items) == (
        "first_key",
        "total",
        "counted",
        "distinct_status",
        "summed",
        "averaged",
        "earliest",
        "latest",
        None,
    )
    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert tuple(result.field.name for result in selected) == (
        "first_key",
        "total",
        "counted",
        "distinct_status",
        "summed",
        "averaged",
        "earliest",
        "latest",
        "region",
    )
    assert tuple(result.field.result_role for result in selected) == (
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.GROUP_KEY,
    )
    assert tuple(
        result.aggregate_fact.function
        for result in selected
        if result.aggregate_fact is not None
    ) == ("count", "count", "count_distinct", "sum", "avg", "min", "max")
    assert tuple(
        result.field.resolved_type.name
        for result in selected
        if result.aggregate_fact is not None
    ) == ("Int", "Int", "Int", "Int", "Float", "Timestamp", "Timestamp")
    assert tuple(
        result.field.nullability
        for result in selected
        if result.aggregate_fact is not None
    ) == (
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.NULLABLE,
    )
    for item, result in facts.selected_results.items():
        if result.aggregate_fact is None:
            assert result.field.field_def is not None
            assert result.field.provenance is not None
            assert (
                result.field.provenance.kind
                is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
            )
        else:
            assert result.aggregate_fact.grouped is True
            assert result.aggregate_fact.location == _location(
                item.expression,
                fallback_path="models.pietto",
            )
            assert result.field.field_def is None
            assert result.field.provenance is not None
            assert (
                result.field.provenance.kind is ProjectRowFieldProvenanceKind.AGGREGATE
            )
            assert result.field.provenance.symbol is upstream_symbol


def test_unselected_group_keys_are_retained_with_zero_selected_key_outputs(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "table grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        region\n"
        "    select:\n"
        "        total = count()\n"
        "        summed = sum(amount)\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert tuple(facts.selected_results) == definition.select_items
    assert tuple(result.field.name for result in facts.selected_results.values()) == (
        "total",
        "summed",
    )
    assert all(
        result.aggregate_fact is not None for result in facts.selected_results.values()
    )


def test_direct_and_chained_group_key_lets_compose_with_direct_aggregates(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "        region_key = users.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        key\n"
        "        bucket\n"
        "    select:\n"
        "        status\n"
        "        renamed = users.region\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert isinstance(facts.group_keys[0].effective_expression, NameExpr)
    assert facts.group_keys[0].effective_expression.name == "status"
    assert isinstance(facts.group_keys[1].effective_expression, DottedNameExpr)
    assert facts.group_keys[1].effective_expression.parts == ("users", "region")
    assert tuple(result.field.name for result in facts.selected_results.values()) == (
        "status",
        "renamed",
        "total",
    )

    _, _, selecting_let, let_schema, let_symbol = _grouped_inputs(
        tmp_path / "select-let",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        key\n"
        "        total = count()\n",
    )
    assert (
        build_project_grouped_schema_facts(
            definition=selecting_let,
            input_schema=let_schema,
            upstream_symbol=let_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_repeated_occurrences_and_all_duplicate_alias_families_are_preserved(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        region\n"
        "    select:\n"
        "        duplicate = status\n"
        "        duplicate = users.status\n"
        "        repeated = sum(amount)\n"
        "        repeated = sum(amount)\n"
        "        shared = region\n"
        "        shared = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    items = tuple(facts.selected_results)
    results = tuple(facts.selected_results.values())

    assert items == definition.select_items
    assert len(items) == 6
    assert tuple(item.alias for item in items) == (
        "duplicate",
        "duplicate",
        "repeated",
        "repeated",
        "shared",
        "shared",
    )
    assert tuple(result.field.name for result in results) == (
        "duplicate",
        "duplicate",
        "repeated",
        "repeated",
        "shared",
        "shared",
    )
    assert items[0] != items[1]
    assert items[2] != items[3]
    assert items[0].span.line != items[1].span.line
    assert items[2].span.line != items[3].span.line
    assert results[2].aggregate_fact is not None
    assert results[3].aggregate_fact is not None
    assert results[2].aggregate_fact is not results[3].aggregate_fact
    assert results[2].aggregate_fact.location != results[3].aggregate_fact.location
    assert results[4].aggregate_fact is None
    assert results[5].aggregate_fact is not None


@pytest.mark.parametrize(
    "relation_body",
    (
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        missing\n"
        "    select:\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        invalid = sum(status)\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        invalid = count(amount, tax)\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        invalid = median(amount)\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        region\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n",
    ),
)
def test_invalid_key_aggregate_ordinary_expression_and_pure_grouping_return_none(
    tmp_path: Path,
    relation_body: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        relation_body,
    )

    assert (
        build_project_grouped_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_unknown_missing_and_malformed_inputs_fail_closed(tmp_path: Path) -> None:
    _, _, definition, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount)\n",
    )
    missing_key_fields = dict(input_schema.fields)
    missing_key_fields.pop("status")
    missing_aggregate_fields = dict(input_schema.fields)
    missing_aggregate_fields.pop("amount")

    for unavailable_schema in (
        ProjectRowSchema(is_unknown=True),
        ProjectRowSchema(fields={}),
        ProjectRowSchema(fields=missing_key_fields),
        ProjectRowSchema(fields=missing_aggregate_fields),
    ):
        assert (
            build_project_grouped_schema_facts(
                definition=definition,
                input_schema=unavailable_schema,
                upstream_symbol=upstream_symbol,
                fallback_path="models.pietto",
            )
            is None
        )

    assert (
        build_project_grouped_schema_facts(
            definition=replace(definition, select_items=()),
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    group_by_clause = definition.group_by_clause
    assert group_by_clause is not None
    assert (
        build_project_grouped_schema_facts(
            definition=replace(
                definition,
                group_by_clause=replace(group_by_clause, items=()),
            ),
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )

    aggregate_item = definition.select_items[1]
    assert (
        build_project_grouped_schema_facts(
            definition=replace(
                definition,
                select_items=(aggregate_item, aggregate_item),
            ),
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_slice4_wrapper_and_grouped_api_misuse_boundary(tmp_path: Path) -> None:
    _, _, grouped, input_schema, upstream_symbol = _grouped_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    assert (
        build_project_aggregate_schema_facts(
            definition=grouped,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )

    no_group = replace(
        grouped,
        group_by_clause=None,
        select_items=(grouped.select_items[1],),
    )
    aggregate_facts = build_project_aggregate_schema_facts(
        definition=no_group,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert aggregate_facts is not None
    selected = next(iter(aggregate_facts.selected_results.values()))
    assert selected.fact.grouped is False

    with pytest.raises(ValueError, match="GROUP BY"):
        build_project_grouped_schema_facts(
            definition=no_group,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )


def test_aggregate_grouped_outputs_are_concrete_private_persisted_and_unserialized(
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
            "        total = count()\n"
            "query pure:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n",
        )
    )
    assert semantic_result.model is not None
    model = semantic_result.model
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")
    pure = _derived_definition(parse_result, "pure")
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

    assert pure not in model.relation_row_schemas
    assert pure not in model.relation_aggregate_result_facts
    pure_state = model.relation_row_schema_states[pure]
    assert pure_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert pure_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_state.schema is None

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    module_source = HELPER_PATH.read_text(encoding="utf-8")
    grouped_builder_source = inspect.getsource(build_project_grouped_schema_facts)

    assert tuple(document) == EXPECTED_PROJECT_JSON_V2_KEYS
    assert project_package.__all__ == ()
    assert "aggregate_grouped_schema" not in model_source
    assert "ProjectSemanticModel" not in module_source
    assert "ProjectRowSchema(" not in grouped_builder_source
    assert "semantic.analyze" not in module_source
    assert "analyze(" not in grouped_builder_source
    for name in (
        "ProjectGroupedSelectedResult",
        "ProjectGroupedSchemaFacts",
        "build_project_grouped_schema_facts",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized


def _grouped_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "grouped",
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
) -> ProjectGroupedSchemaFacts:
    facts = build_project_grouped_schema_facts(
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
        "    customer_id: UUID not null\n"
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
