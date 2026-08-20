from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.semantic.capability_aggregates as capability_aggregates
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_aggregates.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_aggregates, name))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    helper = cast(Any, capability_aggregates.aggregate_lookup_inputs)
    facts, complete, reason = helper(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _signature_key(
    subject: str,
    shape: str,
    argument_type: str,
    result_type: str,
    nullability: str,
    *,
    arity: str = "1",
    context: str = "aggregate_signature",
    dialect: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject=subject,
        operation="signature",
        operands=(
            arity,
            shape,
            argument_type,
            result_type,
            nullability,
            "GROUP",
            "aggregate_result",
        ),
        context=context,
        dialect=dialect,
    )


def _algebra_key(
    subject: str,
    operation: str,
    scope: str,
    value: str,
    *,
    context: str = "aggregate_algebra",
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject=subject,
        operation=operation,
        operands=(scope, value),
        context=context,
    )


def _expected_signature_rows() -> tuple[
    tuple[str, tuple[str, ...], CapabilitySupport], ...
]:
    supported = CapabilitySupport.SUPPORTED
    direct_count_types = (
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    )
    expression_count_types = ("Bool", "Int", "Float", "Decimal", "Text")
    distinct_types = (
        "Bool",
        "Int",
        "Float",
        "Decimal",
        "Text",
        "Date",
        "Timestamp",
        "UUID",
    )
    rows: list[tuple[str, tuple[str, ...], CapabilitySupport]] = []

    def add(
        subject: str,
        arity: str,
        shape: str,
        argument: str,
        result: str,
        nullability: str,
        support: CapabilitySupport = supported,
    ) -> None:
        rows.append(
            (
                subject,
                (
                    arity,
                    shape,
                    argument,
                    result,
                    nullability,
                    "GROUP",
                    "aggregate_result",
                ),
                support,
            )
        )

    add("count", "0", "no_argument", "NO_ARGUMENT", "Int", "non_null")
    for argument in direct_count_types:
        add("count", "1", "direct_field", argument, "Int", "non_null")
    for argument in expression_count_types:
        add(
            "count",
            "1",
            "field_bearing_expression",
            argument,
            "Int",
            "non_null",
        )
    add("count", "1", "direct_field", "Shape", "Int", "non_null")
    add(
        "count",
        "1",
        "direct_field",
        "Shape",
        "Int",
        "non_null",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    for argument in distinct_types:
        add(
            "count_distinct",
            "1",
            "direct_field",
            argument,
            "Int",
            "non_null",
        )
    add(
        "count_distinct",
        "1",
        "lower_trim_text_transform_chain",
        "Text",
        "Int",
        "non_null",
    )
    for argument, result in (
        ("Int", "Int"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add("sum", "1", "direct_field", argument, result, "nullable")
    for argument, result in (
        ("Int", "Int"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add(
            "sum",
            "1",
            "field_only_numeric_expression",
            argument,
            result,
            "nullable",
        )
    for argument in ("Int", "Float"):
        add(
            "sum",
            "1",
            "field_and_literal_numeric_expression",
            argument,
            argument,
            "nullable",
        )
    for argument, result in (
        ("Int", "Float"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add("avg", "1", "direct_field", argument, result, "nullable")
    for argument, result in (
        ("Int", "Float"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add(
            "avg",
            "1",
            "field_only_numeric_expression",
            argument,
            result,
            "nullable",
        )
    for argument in ("Int", "Float"):
        add(
            "avg",
            "1",
            "field_and_literal_numeric_expression",
            argument,
            "Float",
            "nullable",
        )
    for subject in ("min", "max"):
        for argument in ("Int", "Float", "Decimal", "Date", "Timestamp"):
            add(subject, "1", "direct_field", argument, argument, "nullable")
    return tuple(rows)


def _expected_algebra_rows() -> tuple[
    tuple[
        str,
        str,
        tuple[str, str],
        CapabilitySupport,
        CapabilityDispositionKind,
    ],
    ...,
]:
    supported = CapabilitySupport.SUPPORTED
    unsupported = CapabilitySupport.EXPLICITLY_UNSUPPORTED
    none = CapabilityDispositionKind.NONE
    deferred = CapabilityDispositionKind.DEFERRED
    return (
        ("count", "empty_input_result", ("arity_0", "zero"), supported, none),
        ("count", "empty_input_result", ("arity_1", "zero"), supported, none),
        (
            "count_distinct",
            "empty_input_result",
            ("arity_1", "zero"),
            supported,
            none,
        ),
        (
            "sum",
            "empty_input_result",
            ("all_supported_signatures", "sql_null"),
            supported,
            none,
        ),
        (
            "min",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            supported,
            none,
        ),
        (
            "max",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            supported,
            none,
        ),
        (
            "count",
            "argument_inspection",
            ("arity_0", "does_not_inspect_values"),
            supported,
            none,
        ),
        (
            "count",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            supported,
            none,
        ),
        (
            "count_distinct",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            supported,
            none,
        ),
        (
            "count_distinct",
            "duplicate_treatment",
            ("arity_1", "eliminates_duplicates"),
            supported,
            none,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_filter",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "inline_distinct_modifier",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_internal_ordering",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "generic_aggregate_modifier",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "nested_aggregate",
            ("aggregate_argument", "not_supported"),
            unsupported,
            none,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "scalar_wrapping",
            ("direct_aggregate_projection", "not_supported"),
            unsupported,
            none,
        ),
    )


def test_private_module_api_and_dependency_shape_is_exact() -> None:
    assert capability_aggregates.__all__ == ()
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assert not any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Import))
        for node in tree.body
    )
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports <= {
        "__future__",
        "collections.abc",
        "pietto.semantic.capability_facts",
    }
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"_freeze_aggregates", "aggregate_lookup_inputs"} <= functions
    source = _read(SOURCE_PATH)
    for forbidden in (
        "capability_lookup",
        "open(",
        "getenv",
        "os.environ",
        "database",
        "callback",
    ):
        assert forbidden not in source


def test_freezer_and_combined_fact_order_are_exact() -> None:
    signature = _facts("_AGGREGATE_SIGNATURE_FACTS")
    algebra = _facts("_AGGREGATE_ALGEBRA_FACTS")
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert combined == signature + algebra
    freezer = cast(Any, getattr(capability_aggregates, "_freeze_aggregates"))
    with pytest.raises(ValueError, match="duplicate"):
        freezer((signature[0], signature[0]))
    distinct = replace(signature[0], support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freezer((signature[0], distinct)) == (signature[0], distinct)


@pytest.mark.parametrize(
    ("subject", "fact_count", "key_count"),
    (
        ("count", 18, 17),
        ("count_distinct", 9, 9),
        ("sum", 8, 8),
        ("avg", 8, 8),
        ("min", 5, 5),
        ("max", 5, 5),
    ),
)
def test_signature_family_counts_are_exact(
    subject: str,
    fact_count: int,
    key_count: int,
) -> None:
    facts = tuple(
        fact
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == subject
    )
    assert (len(facts), len({fact.key for fact in facts})) == (fact_count, key_count)


def test_signature_inventory_order_keys_support_and_disposition_are_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    expected = _expected_signature_rows()
    assert len(facts) == len(expected) == 53
    assert len({fact.key for fact in facts}) == 52
    assert (
        tuple((fact.key.subject, fact.key.operands, fact.support) for fact in facts)
        == expected
    )
    for fact in facts:
        assert fact.key.domain is CapabilityDomain.AGGREGATE
        assert fact.key.operation == "signature"
        assert fact.key.context == "aggregate_signature"
        assert fact.key.dialect is None
        assert fact.key.extension is None
        assert fact.disposition.kind is CapabilityDispositionKind.NONE
        assert fact.disposition.owner is None
        assert fact.disposition.reason is None


def test_signature_key_schema_and_completeness_are_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    assert all(len(fact.key.operands) == 7 for fact in facts)
    assert facts[0].key.operands == (
        "0",
        "no_argument",
        "NO_ARGUMENT",
        "Int",
        "non_null",
        "GROUP",
        "aggregate_result",
    )
    assert {fact.key.operands[1] for fact in facts} == {
        "no_argument",
        "direct_field",
        "field_bearing_expression",
        "lower_trim_text_transform_chain",
        "field_only_numeric_expression",
        "field_and_literal_numeric_expression",
    }
    for fact in facts:
        inputs, complete, reason = capability_aggregates.aggregate_lookup_inputs(
            fact.key
        )
        assert inputs == facts
        assert complete is True
        assert reason is None


@pytest.mark.parametrize(
    ("subject", "shape", "argument", "result", "nullability"),
    (
        ("count", "no_argument", "NO_ARGUMENT", "Int", "non_null"),
        ("count", "direct_field", "Bytes", "Int", "non_null"),
        ("count", "field_bearing_expression", "Text", "Int", "non_null"),
        ("count", "direct_field", "Shape", "Int", "non_null"),
        ("count_distinct", "direct_field", "UUID", "Int", "non_null"),
        (
            "count_distinct",
            "lower_trim_text_transform_chain",
            "Text",
            "Int",
            "non_null",
        ),
        ("sum", "direct_field", "Int", "Int", "nullable"),
        (
            "sum",
            "field_only_numeric_expression",
            "Decimal",
            "Decimal",
            "nullable",
        ),
        (
            "sum",
            "field_and_literal_numeric_expression",
            "Float",
            "Float",
            "nullable",
        ),
        ("avg", "direct_field", "Int", "Float", "nullable"),
        (
            "avg",
            "field_only_numeric_expression",
            "Decimal",
            "Decimal",
            "nullable",
        ),
        ("min", "direct_field", "Date", "Date", "nullable"),
        ("max", "direct_field", "Timestamp", "Timestamp", "nullable"),
    ),
)
def test_signature_result_type_nullability_stage_and_role_are_exact(
    subject: str,
    shape: str,
    argument: str,
    result: str,
    nullability: str,
) -> None:
    matches = tuple(
        fact
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == subject
        and fact.key.operands[1:5] == (shape, argument, result, nullability)
    )
    assert matches
    assert all(
        fact.key.operands[5:] == ("GROUP", "aggregate_result") for fact in matches
    )


@pytest.mark.parametrize(
    "index",
    (0, 1, 11, 16, 17, 26, 33, 43),
)
def test_signature_evidence_order_and_authority_are_exact(index: int) -> None:
    fact = _facts("_AGGREGATE_SIGNATURE_FACTS")[index]
    assert len(fact.evidence) == len(set(fact.evidence))
    assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
    order = {
        source: position for position, source in enumerate(CapabilityEvidenceSource)
    }
    positions = [order[entry.source] for entry in fact.evidence]
    assert positions == sorted(positions)
    assert fact.evidence[0].source is CapabilityEvidenceSource.GRAMMAR_AST
    assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in {
        entry.source for entry in fact.evidence
    }
    backends = [
        entry
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    ]
    assert [(entry.dialect, entry.backend) for entry in backends] in (
        [],
        [("postgresql", "postgresql"), ("mysql", "private-mysql")],
    )


def test_shape_signature_real_conflict_is_adjacent_ordered_and_winner_free() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    supported, unsupported = facts[16:18]
    assert (
        supported.key
        == unsupported.key
        == _signature_key("count", "direct_field", "Shape", "Int", "non_null")
    )
    assert supported.support is CapabilitySupport.SUPPORTED
    assert unsupported.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert any(
        entry.reason is CapabilityReasonCode.DIALECT_LOWERING_GAP
        for entry in unsupported.evidence
    )
    result = _lookup(supported.key)
    assert isinstance(result, Conflict)
    assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert result.evidence == (supported, unsupported)


def test_count_alias_shape_let_and_expression_policy_is_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    keys = {fact.key for fact in facts}
    assert not any("row_let" in key.operands for key in keys)
    assert not any("aggregate_let" in key.operands for key in keys)
    assert not any("projection_alias" in key.operands for key in keys)
    assert not any("literal_only" in key.operands for key in keys)
    assert not any("null_literal" in key.operands for key in keys)
    count_expression_types = tuple(
        fact.key.operands[2]
        for fact in facts
        if fact.key.subject == "count"
        and fact.key.operands[1] == "field_bearing_expression"
    )
    assert count_expression_types == ("Bool", "Int", "Float", "Decimal", "Text")
    distinct_shapes = {
        fact.key.operands[1] for fact in facts if fact.key.subject == "count_distinct"
    }
    assert distinct_shapes == {
        "direct_field",
        "lower_trim_text_transform_chain",
    }


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "0",
                "no_argument",
                "NO_ARGUMENT",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "field_bearing_expression",
                "Text",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count_distinct",
            operation="signature",
            operands=(
                "1",
                "lower_trim_text_transform_chain",
                "Text",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="signature",
            operands=(
                "1",
                "field_and_literal_numeric_expression",
                "Int",
                "Int",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
    ),
)
def test_signature_lookup_found_is_exact(key: CapabilityKey) -> None:
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.key == key


def test_signature_complete_wrong_tail_is_absent() -> None:
    key = _signature_key("count", "direct_field", "Int", "Float", "non_null")
    result = _lookup(key)
    assert isinstance(result, Absent)
    assert result.key == key
    assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY


def test_signature_incomplete_questions_are_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "TYPE_ALIAS",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="future_aggregate",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="alternate_context",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
            dialect="postgresql",
            extension="future",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=("1", "direct_field", "Int", "Int", "non_null", "GROUP"),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Decimal(12,2)",
                "Decimal(12,2)",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="window_signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "nullable",
                "WINDOW",
                "window_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "project_only",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="avg",
            operation="signature",
            operands=(
                "1",
                "literal_only_numeric_expression",
                "Int",
                "Float",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="count",
            operation="signature",
            operands=("Int",),
            context="expression",
        ),
    )
    for key in keys:
        result = _lookup(key)
        assert isinstance(result, Unknown)
        assert result.reason is CapabilityReasonCode.NOT_EVIDENCED


def test_injected_conflict_and_duplicate_freeze_preserve_lookup_contract() -> None:
    original = _facts("_AGGREGATE_SIGNATURE_FACTS")[0]
    conflicting = replace(original, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    result = lookup_capability(
        original.key,
        (original, conflicting),
        domain_complete=True,
    )
    assert isinstance(result, Conflict)
    assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert result.evidence == (original, conflicting)
    freezer = cast(Any, getattr(capability_aggregates, "_freeze_aggregates"))
    assert freezer((original, conflicting)) == (original, conflicting)
    with pytest.raises(ValueError, match="duplicate"):
        freezer((original, original))


def test_algebra_inventory_order_keys_support_and_disposition_are_exact() -> None:
    facts = _facts("_AGGREGATE_ALGEBRA_FACTS")
    expected = _expected_algebra_rows()
    property_values = frozenset(
        (
            "zero",
            "sql_null",
            "nullable_on_empty_input",
            "does_not_inspect_values",
            "eliminates_sql_null_results",
            "eliminates_duplicates",
            "not_supported",
        )
    )
    assert len(facts) == len({fact.key for fact in facts}) == len(expected) == 16
    assert (
        cast(
            frozenset[str],
            getattr(capability_aggregates, "_ALGEBRA_PROPERTY_VALUES"),
        )
        == property_values
    )
    assert (
        tuple(
            (
                fact.key.subject,
                fact.key.operation,
                cast(tuple[str, str], fact.key.operands),
                fact.support,
                fact.disposition.kind,
            )
            for fact in facts
        )
        == expected
    )
    assert tuple(dict.fromkeys(fact.key.operands[1] for fact in facts)) == (
        "zero",
        "sql_null",
        "nullable_on_empty_input",
        "does_not_inspect_values",
        "eliminates_sql_null_results",
        "eliminates_duplicates",
        "not_supported",
    )
    for index, fact in enumerate(facts):
        _, complete, reason = cast(
            Any,
            capability_aggregates.aggregate_lookup_inputs,
        )(fact.key)
        assert complete is True
        assert reason is None
        assert fact.key.domain is CapabilityDomain.AGGREGATE
        assert fact.key.context == "aggregate_algebra"
        assert fact.key.dialect is None
        assert fact.key.extension is None
        if 10 <= index <= 13:
            assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
            assert fact.disposition.reason
        else:
            assert fact.disposition.owner is None
            assert fact.disposition.reason is None


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
)
def test_supported_algebra_fact_is_exact(index: int) -> None:
    fact = _facts("_AGGREGATE_ALGEBRA_FACTS")[index]
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    result = _lookup(fact.key)
    assert isinstance(result, Found)
    assert result.fact == fact


@pytest.mark.parametrize(
    "indexes",
    ((10,), (11,), (12,), (13,), (14, 15)),
)
def test_rejected_algebra_fact_group_is_exact(indexes: tuple[int, ...]) -> None:
    facts = _facts("_AGGREGATE_ALGEBRA_FACTS")
    for index in indexes:
        fact = facts[index]
        assert fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        if index < 14:
            assert fact.disposition.kind is CapabilityDispositionKind.DEFERRED
            assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
        else:
            assert fact.disposition.kind is CapabilityDispositionKind.NONE
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact == fact


def test_algebra_completeness_absence_and_omission_are_exact() -> None:
    complete_absences = (
        _algebra_key(
            "count",
            "argument_inspection",
            "arity_0",
            "eliminates_duplicates",
        ),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_filter",
            "all_current_aggregates",
            "zero",
        ),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "nested_aggregate",
            "aggregate_argument",
            "sql_null",
        ),
    )
    for key in complete_absences:
        result = _lookup(key)
        assert isinstance(result, Absent)
        assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY

    canonical = _algebra_key(
        "count", "argument_inspection", "arity_0", "does_not_inspect_values"
    )
    malformed = (
        replace(canonical, operands=("arity_0",)),
        replace(
            canonical,
            operands=("arity_0", "does_not_inspect_values", "extra"),
        ),
        replace(canonical, operands=("arity_0", "Bogus")),
        replace(canonical, operands=("arity_0", "Zero")),
        replace(canonical, operands=("Bogus", "zero")),
        replace(canonical, subject="future_aggregate"),
        replace(canonical, operation="future_property"),
        replace(canonical, context="expression"),
        replace(canonical, dialect="postgresql"),
        replace(canonical, dialect="postgresql", extension="future"),
        _algebra_key("avg", "empty_input_result", "arity_1", "sql_null"),
        _algebra_key("sum", "associativity", "all_supported_signatures", "true"),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "window_over",
            "all_current_aggregates",
            "supported",
        ),
    )
    for key in malformed:
        unknown = _lookup(key)
        assert isinstance(unknown, Unknown)
        assert unknown.reason is CapabilityReasonCode.NOT_EVIDENCED


def test_modifier_window_nested_global_grouped_and_clause_boundaries_are_exact() -> (
    None
):
    algebra = _facts("_AGGREGATE_ALGEBRA_FACTS")
    assert tuple(fact.key.operation for fact in algebra[10:]) == (
        "aggregate_filter",
        "inline_distinct_modifier",
        "aggregate_internal_ordering",
        "generic_aggregate_modifier",
        "nested_aggregate",
        "scalar_wrapping",
    )
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert not any("window" in (fact.key.operation or "").lower() for fact in combined)
    assert not any(fact.key.domain is CapabilityDomain.CLAUSE for fact in combined)
    assert all(
        fact.key.operands[-2:] == ("GROUP", "aggregate_result")
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
    )
    assert not any("global" in fact.key.operands for fact in combined)
    assert not any("grouped" in fact.key.operands for fact in combined)


def test_no_existing_consumer_public_export_registry_io_or_callback_exists() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_aggregates" not in source
        assert "aggregate_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_aggregates" in preservation_source
    assert "aggregate_lookup_inputs" in preservation_source
    assert "capability_aggregates" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_aggregates" not in _read(REPO_ROOT / "src/pietto/__init__.py")
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assigned_names = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Name)
    }
    assert not any(
        token in name.lower()
        for name in assigned_names
        for token in ("registry", "cache", "callback", "consumer")
    )


def test_backend_evidence_is_separate_ordered_and_non_authoritative() -> None:
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert len(combined) == 69
    assert len({fact.key for fact in combined}) == 68
    for fact in combined:
        sources = tuple(entry.source for entry in fact.evidence)
        backends = tuple(
            entry
            for entry in fact.evidence
            if entry.source is CapabilityEvidenceSource.BACKEND
        )
        if backends:
            assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in sources
            assert sources.index(CapabilityEvidenceSource.SEMANTIC_PROCEDURE) < (
                sources.index(CapabilityEvidenceSource.BACKEND)
            )
            assert tuple((entry.dialect, entry.backend) for entry in backends) == (
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            )
        assert all(entry.extension is None for entry in fact.evidence)


# Phase 53 Slice 13 reader migration.
