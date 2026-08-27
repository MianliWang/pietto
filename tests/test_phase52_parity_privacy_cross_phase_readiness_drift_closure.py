from __future__ import annotations

import ast
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.semantic.capability_aggregates as capability_aggregates
import pietto.semantic.capability_composition as capability_composition
import pietto.semantic.capability_contexts as capability_contexts
import pietto.semantic.capability_facts as capability_facts
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_lookup as capability_lookup
import pietto.semantic.capability_profiles as capability_profiles
import pietto.semantic.capability_providers as capability_providers
import pietto.semantic.capability_signatures as capability_signatures
import pietto.semantic.capability_windows as capability_windows
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
FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
WINDOW_REL = "src/pietto/semantic/capability_windows.py"
PROFILE_REL = "src/pietto/semantic/capability_profiles.py"
SELECTOR_REL = "src/pietto/semantic/extension_signature_requirements.py"
EXTENSION_PROVIDER_REL = "src/pietto/_project/extension_signature_provider.py"
EXTENSION_INSPECTION_REL = "src/pietto/_project/extension_catalog_inspection.py"
EXTENSION_INSPECTION_PURE_REL = (
    "src/pietto/_project/extension_catalog_inspection_pure_boundary.py"
)
PROVIDER_REL = "src/pietto/semantic/capability_providers.py"
COMPOSITION_REL = "src/pietto/semantic/capability_composition.py"
MODULE_RELS = (
    FACTS_REL,
    LOOKUP_REL,
    INVENTORY_REL,
    SIGNATURE_REL,
    CONTEXT_REL,
    AGGREGATE_REL,
    WINDOW_REL,
    PROFILE_REL,
    PROVIDER_REL,
    COMPOSITION_REL,
)
EVIDENCE_SOURCE_COUNTS = {
    CapabilityEvidenceSource.GRAMMAR_AST: 267,
    CapabilityEvidenceSource.SEMANTIC_CATALOG: 87,
    CapabilityEvidenceSource.SEMANTIC_PROCEDURE: 397,
    CapabilityEvidenceSource.SEMANTIC_MODEL: 130,
    CapabilityEvidenceSource.IR: 247,
    CapabilityEvidenceSource.BACKEND: 236,
    CapabilityEvidenceSource.PROJECT: 129,
    CapabilityEvidenceSource.PUBLIC: 18,
    CapabilityEvidenceSource.ROADMAP: 90,
    CapabilityEvidenceSource.TEST: 465,
    CapabilityEvidenceSource.SPEC: 307,
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _facts(module: object, name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(module, name))


def _families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        _facts(capability_inventory, "_CAPABILITY_FACTS"),
        _facts(capability_signatures, "_CAPABILITY_SIGNATURE_FACTS"),
        _facts(capability_contexts, "_CAPABILITY_CONTEXT_FACTS"),
        _facts(capability_aggregates, "_AGGREGATE_CAPABILITY_FACTS"),
        _facts(capability_windows, "_WINDOW_CAPABILITY_FACTS"),
    )


def _all_facts() -> tuple[CapabilityFact, ...]:
    return tuple(fact for family in _families() for fact in family)


def _helper_inputs(
    key: CapabilityKey,
) -> tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None]:
    inputs = capability_providers.canonical_capability_provider_inputs(key)
    return inputs.facts, inputs.domain_complete, inputs.unknown_reason


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = _helper_inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _backend_records(fact: CapabilityFact) -> tuple[Any, ...]:
    return tuple(
        evidence
        for evidence in fact.evidence
        if evidence.source is CapabilityEvidenceSource.BACKEND
    )


def _dual_backend_facts(
    facts: tuple[CapabilityFact, ...],
) -> tuple[CapabilityFact, ...]:
    expected = {("postgresql", "postgresql"), ("mysql", "private-mysql")}
    return tuple(
        fact
        for fact in facts
        if {(item.dialect, item.backend) for item in _backend_records(fact)} == expected
    )


@pytest.mark.parametrize(
    ("domain", "expected_count", "owner"),
    (
        (CapabilityDomain.LOGICAL_TYPE, 25, "slice4"),
        (CapabilityDomain.LITERAL, 13, "slice4"),
        (CapabilityDomain.PARAMETER, 3, "slice4"),
        (CapabilityDomain.SCALAR_FUNCTION, 4, "slice5"),
        (CapabilityDomain.UNARY_OPERATOR, 4, "slice5"),
        (CapabilityDomain.BINARY_OPERATOR, 21, "slice5"),
        (CapabilityDomain.COMPARISON, 8, "slice5"),
        (CapabilityDomain.NULL_TEST, 2, "slice5"),
        (CapabilityDomain.EXPRESSION_STAGE, 7, "slice6"),
        (CapabilityDomain.CLAUSE, 11, "slice6"),
        (CapabilityDomain.AGGREGATE, 69, "slice7"),
        (CapabilityDomain.WINDOW_FUNCTION, 24, "phase53_slice15"),
        (CapabilityDomain.CONVERSION, 0, "post60_reserved"),
        (CapabilityDomain.EXTENSION_SIGNATURE, 0, "phase57_reserved"),
    ),
)
def test_capability_domain_population_and_reservation_matrix_is_exact(
    domain: CapabilityDomain,
    expected_count: int,
    owner: str,
) -> None:
    facts = tuple(fact for fact in _all_facts() if fact.key.domain is domain)
    assert len(facts) == expected_count
    expected_owners = {
        CapabilityDomain.LOGICAL_TYPE: "slice4",
        CapabilityDomain.LITERAL: "slice4",
        CapabilityDomain.PARAMETER: "slice4",
        CapabilityDomain.SCALAR_FUNCTION: "slice5",
        CapabilityDomain.UNARY_OPERATOR: "slice5",
        CapabilityDomain.BINARY_OPERATOR: "slice5",
        CapabilityDomain.COMPARISON: "slice5",
        CapabilityDomain.NULL_TEST: "slice5",
        CapabilityDomain.EXPRESSION_STAGE: "slice6",
        CapabilityDomain.CLAUSE: "slice6",
        CapabilityDomain.AGGREGATE: "slice7",
        CapabilityDomain.WINDOW_FUNCTION: "phase53_slice15",
        CapabilityDomain.CONVERSION: "post60_reserved",
        CapabilityDomain.EXTENSION_SIGNATURE: "phase57_reserved",
    }
    assert expected_owners[domain] == owner
    assert all(fact.key.domain is domain for fact in facts)
    assert not any(
        fact.key.domain is CapabilityDomain.DIALECT_LOWERING for fact in _all_facts()
    )


def test_slice4_7_fact_key_totals_duplicates_and_collisions_are_exact() -> None:
    families = _families()
    assert tuple(
        (len(family), len({fact.key for fact in family})) for family in families
    ) == (
        (41, 41),
        (39, 39),
        (18, 18),
        (69, 68),
        (24, 24),
    )
    facts = _all_facts()
    assert (len(facts), len({fact.key for fact in facts})) == (191, 190)
    assert len(set(facts)) == 191
    repeated = tuple(
        key for key, count in Counter(fact.key for fact in facts).items() if count > 1
    )
    assert len(repeated) == 1
    assert repeated[0] == CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="count",
        operation="signature",
        operands=(
            "1",
            "direct_field",
            "Shape",
            "Int",
            "non_null",
            "GROUP",
            "aggregate_result",
        ),
        context="aggregate_signature",
    )
    family_keys = tuple({fact.key for fact in family} for family in families)
    assert all(
        family_keys[left].isdisjoint(family_keys[right])
        for left in range(len(family_keys))
        for right in range(left + 1, len(family_keys))
    )


def test_fact_order_domain_ownership_and_combined_inventory_are_deterministic() -> None:
    inventory, signatures, contexts, aggregates, windows = _families()
    assert _all_facts() == (*inventory, *signatures, *contexts, *aggregates, *windows)
    assert inventory == (
        *_facts(capability_inventory, "_LOGICAL_TYPE_FACTS"),
        *_facts(capability_inventory, "_LITERAL_FACTS"),
        *_facts(capability_inventory, "_PARAMETER_FACTS"),
        *_facts(capability_inventory, "_NULLABILITY_FACTS"),
    )
    assert signatures == (
        *_facts(capability_signatures, "_SCALAR_FUNCTION_FACTS"),
        *_facts(capability_signatures, "_UNARY_OPERATOR_FACTS"),
        *_facts(capability_signatures, "_BINARY_OPERATOR_FACTS"),
        *_facts(capability_signatures, "_COMPARISON_FACTS"),
        *_facts(capability_signatures, "_NULL_TEST_FACTS"),
    )
    assert contexts == (
        *_facts(capability_contexts, "_EXPRESSION_STAGE_FACTS"),
        *_facts(capability_contexts, "_CLAUSE_CAPABILITY_FACTS"),
    )
    assert aggregates == (
        *_facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS"),
        *_facts(capability_aggregates, "_AGGREGATE_ALGEBRA_FACTS"),
    )
    assert windows == (
        *_facts(capability_windows, "_WINDOW_SIGNATURE_FACTS"),
        *_facts(capability_windows, "_WINDOW_LOWERING_FACTS"),
    )


@pytest.mark.parametrize(
    "schema_group",
    (
        "inventory_logical_type",
        "inventory_literal",
        "inventory_parameter",
        "signature_scalar",
        "signature_operators",
        "context_stage",
        "context_clause",
        "aggregate_signature_and_algebra",
    ),
)
def test_all_populated_completeness_schemas_are_exact(schema_group: str) -> None:
    inventory, signatures, contexts, aggregates, _windows = _families()
    if schema_group == "inventory_logical_type":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LOGICAL_TYPE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[-1], operands=("future",))
    elif schema_group == "inventory_literal":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LITERAL
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("Int",))
    elif schema_group == "inventory_parameter":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.PARAMETER
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], context="future_context")
    elif schema_group == "signature_scalar":
        keys = tuple(
            fact.key
            for fact in signatures
            if fact.key.domain is CapabilityDomain.SCALAR_FUNCTION
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        assert _helper_inputs(replace(keys[0], operation="future_builtin"))[1]
        malformed = replace(keys[0], operands=("Text", "future_tail"))
    elif schema_group == "signature_operators":
        keys = tuple(
            fact.key
            for fact in signatures
            if fact.key.domain is not CapabilityDomain.SCALAR_FUNCTION
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("Int", "unknown"))
    elif schema_group == "context_stage":
        keys = tuple(
            fact.key
            for fact in contexts
            if fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("WINDOW",))
    elif schema_group == "context_clause":
        keys = tuple(
            fact.key for fact in contexts if fact.key.domain is CapabilityDomain.CLAUSE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("ROW",))
    else:
        assert schema_group == "aggregate_signature_and_algebra"
        keys = tuple(fact.key for fact in aggregates)
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=keys[0].operands[:-1])
    assert _helper_inputs(malformed)[1] is False


def test_canonical_complete_zero_match_and_open_position_absence_are_exact() -> None:
    shape_key = CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="count",
        operation="signature",
        operands=(
            "1",
            "direct_field",
            "Shape",
            "Int",
            "non_null",
            "GROUP",
            "aggregate_result",
        ),
        context="aggregate_signature",
    )
    for fact in _all_facts():
        result = _lookup(fact.key)
        if fact.key == shape_key:
            assert isinstance(result, Conflict)
        else:
            assert result == Found(fact)

    absent_keys = (
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Float", "non_null"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureBuiltin",
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="future_declaration",
            operation="declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="future_builtin",
            operands=("Text", "unknown"),
            context="expression",
        ),
    )
    for key in absent_keys:
        assert _helper_inputs(key)[1] is True
        assert _lookup(key) == Absent(key, CapabilityReasonCode.NO_CATALOG_ENTRY)


def test_malformed_closed_future_dialect_extension_keys_are_unknown() -> None:
    clause = _facts(capability_contexts, "_CLAUSE_CAPABILITY_FACTS")[0].key
    keys = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("future",),
            context="type_expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Int",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            subject="future_parameter",
            operation="declare",
            operands=("name", "TypeExpr"),
            context="callable_declaration",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="FutureType",
            operation="lower",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.UNARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Int", "PRESERVE_OPERAND"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("WINDOW",),
            context="expression",
        ),
        replace(
            clause,
            operands=(*clause.operands[:2], "future_shape", *clause.operands[3:]),
        ),
        replace(clause, dialect="postgresql"),
        replace(clause, dialect="postgresql", extension="future_extension"),
    )
    assert all(
        _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED) for key in keys
    )


def test_division_and_backend_gap_unknown_reasons_are_exact() -> None:
    division = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject="Int",
        operation="/",
        operands=("Int", "Int", "unknown"),
        context="expression",
    )
    matches_mysql = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="Text",
        operation="matches",
        operands=("Text", "Bool", "unknown"),
        context="expression",
        dialect="mysql",
    )
    like = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Expression",
        operation="like",
        operands=("Expression", "Bool", "unknown"),
        context="expression",
    )
    assert _lookup(division) == Unknown(CapabilityReasonCode.NO_CURRENT_RESULT_RULE)
    assert _lookup(matches_mysql) == Unknown(CapabilityReasonCode.DIALECT_LOWERING_GAP)
    assert _lookup(replace(like, dialect="postgresql")) == Unknown(
        CapabilityReasonCode.DIALECT_LOWERING_GAP
    )
    assert _lookup(replace(like, dialect="mysql")) == Unknown(
        CapabilityReasonCode.DIALECT_LOWERING_GAP
    )


def test_found_absent_unknown_conflict_precedence_and_duplicate_folding_are_exact() -> (
    None
):
    fact = _all_facts()[0]
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert lookup_capability(fact.key, (fact,), domain_complete=True) == Found(fact)
    assert lookup_capability(fact.key, (fact, fact), domain_complete=True) == Found(
        fact
    )
    assert lookup_capability(
        fact.key, (fact, distinct), domain_complete=True
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (fact, distinct))
    assert lookup_capability(
        fact.key, (distinct, fact), domain_complete=True
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (distinct, fact))
    missing = replace(fact.key, subject="NoCatalogEntry")
    assert lookup_capability(missing, (fact,), domain_complete=True) == Absent(missing)
    assert lookup_capability(
        missing,
        (fact,),
        domain_complete=False,
        unknown_reason=CapabilityReasonCode.NOT_EVIDENCED,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    with pytest.raises(ValueError, match="exact capability facts"):
        lookup_capability(
            fact.key,
            cast(Any, (fact, object())),
            domain_complete=True,
        )


def test_each_family_lookup_input_filtering_completeness_and_reason_are_exact() -> None:
    inventory, signatures, contexts, aggregates, windows = _families()
    expected_by_domain = {
        CapabilityDomain.LOGICAL_TYPE: tuple(
            fact
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LOGICAL_TYPE
        ),
        CapabilityDomain.LITERAL: tuple(
            fact for fact in inventory if fact.key.domain is CapabilityDomain.LITERAL
        ),
        CapabilityDomain.PARAMETER: tuple(
            fact for fact in inventory if fact.key.domain is CapabilityDomain.PARAMETER
        ),
        CapabilityDomain.SCALAR_FUNCTION: _facts(
            capability_signatures, "_SCALAR_FUNCTION_FACTS"
        ),
        CapabilityDomain.UNARY_OPERATOR: _facts(
            capability_signatures, "_UNARY_OPERATOR_FACTS"
        ),
        CapabilityDomain.BINARY_OPERATOR: _facts(
            capability_signatures, "_BINARY_OPERATOR_FACTS"
        ),
        CapabilityDomain.COMPARISON: _facts(capability_signatures, "_COMPARISON_FACTS"),
        CapabilityDomain.NULL_TEST: _facts(capability_signatures, "_NULL_TEST_FACTS"),
        CapabilityDomain.EXPRESSION_STAGE: _facts(
            capability_contexts, "_EXPRESSION_STAGE_FACTS"
        ),
        CapabilityDomain.CLAUSE: _facts(
            capability_contexts, "_CLAUSE_CAPABILITY_FACTS"
        ),
        CapabilityDomain.AGGREGATE: aggregates,
        CapabilityDomain.WINDOW_FUNCTION: windows,
    }
    for domain, expected in expected_by_domain.items():
        key = next(fact.key for fact in _all_facts() if fact.key.domain is domain)
        facts, complete, reason = _helper_inputs(key)
        if domain is CapabilityDomain.AGGREGATE:
            expected = (
                _facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS")
                if key.context == "aggregate_signature"
                else _facts(capability_aggregates, "_AGGREGATE_ALGEBRA_FACTS")
            )
        elif domain is CapabilityDomain.WINDOW_FUNCTION:
            expected = (
                _facts(capability_windows, "_WINDOW_SIGNATURE_FACTS")
                if key.context == "window_signature"
                else _facts(capability_windows, "_WINDOW_LOWERING_FACTS")
            )
        assert facts == expected
        assert complete is True
        assert reason is None

    foreign = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject="Int",
        operation="convert",
        operands=("Text",),
        context="expression",
    )
    assert _helper_inputs(foreign) == ((), False, None)
    assert cast(Any, capability_inventory.inventory_lookup_inputs)(foreign) == (
        (),
        False,
    )
    assert cast(Any, capability_signatures.signature_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_contexts.stage_clause_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_aggregates.aggregate_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_windows.window_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )


@pytest.mark.parametrize(
    ("index", "support", "backend_count"),
    (
        (0, CapabilitySupport.SUPPORTED, 0),
        (1, CapabilitySupport.EXPLICITLY_UNSUPPORTED, 2),
    ),
)
def test_conflict_evidence_order_and_count_shape_real_conflict_are_exact(
    index: int,
    support: CapabilitySupport,
    backend_count: int,
) -> None:
    shape_facts = tuple(
        fact
        for fact in _facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == "count" and "Shape" in fact.key.operands
    )
    assert len(shape_facts) == 2
    fact = shape_facts[index]
    assert fact.support is support
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert len(_backend_records(fact)) == backend_count
    if backend_count:
        assert tuple(item.reason for item in _backend_records(fact)) == (
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    assert _lookup(fact.key) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        shape_facts,
    )


def test_canonical_evidence_source_order_paths_references_and_scope_are_exact() -> None:
    evidence = tuple(item for fact in _all_facts() for item in fact.evidence)
    assert len(evidence) == 2373
    assert Counter(item.source for item in evidence) == EVIDENCE_SOURCE_COUNTS
    source_order = {
        source: index for index, source in enumerate(CapabilityEvidenceSource)
    }
    for fact in _all_facts():
        indexes = tuple(source_order[item.source] for item in fact.evidence)
        assert indexes == tuple(sorted(indexes))
        backend = _backend_records(fact)
        if len(backend) == 2:
            assert tuple((item.dialect, item.backend) for item in backend) == (
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            )
    for item in evidence:
        assert (REPO_ROOT / item.source_path).is_file()
        assert item.source_reference.strip() == item.source_reference
        assert item.source_reference
        assert item.extension is None
        if item.source is CapabilityEvidenceSource.BACKEND:
            assert (item.dialect, item.backend) in {
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            }
        else:
            assert item.dialect is None
            assert item.backend is None


@pytest.mark.parametrize(
    "matrix_case",
    (
        "slice4",
        "slice5",
        "slice6",
        "slice7",
        "combined",
        "positive_supported",
        "matches",
        "like",
        "conflict_and_grouped_unsupported",
    ),
)
def test_postgresql_private_mysql_support_lowering_matrix_is_exact(
    matrix_case: str,
) -> None:
    families = _families()
    dual_by_family = tuple(_dual_backend_facts(family) for family in families)
    if matrix_case in {"slice4", "slice5", "slice6", "slice7"}:
        index = ("slice4", "slice5", "slice6", "slice7").index(matrix_case)
        assert (
            len(dual_by_family[index]),
            sum(len(_backend_records(fact)) for fact in dual_by_family[index]),
        ) == (
            (5, 10),
            (39, 78),
            (6, 12),
            (60, 120),
        )[index]
    elif matrix_case == "combined":
        dual = _dual_backend_facts(_all_facts())
        assert (len(dual), sum(len(_backend_records(fact)) for fact in dual)) == (
            110,
            220,
        )
    elif matrix_case == "positive_supported":
        dual = _dual_backend_facts(_all_facts())
        positive = tuple(
            fact
            for fact in dual
            if fact.support is CapabilitySupport.SUPPORTED
            and all(item.reason is None for item in _backend_records(fact))
        )
        assert len(positive) == 106
    elif matrix_case == "matches":
        fact = next(
            fact
            for fact in _all_facts()
            if fact.key.domain is CapabilityDomain.SCALAR_FUNCTION
            and fact.key.operation == "matches"
        )
        assert fact.support is CapabilitySupport.SUPPORTED
        assert tuple(item.reason for item in _backend_records(fact)) == (
            None,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    elif matrix_case == "like":
        fact = next(
            fact
            for fact in _all_facts()
            if fact.key.domain is CapabilityDomain.COMPARISON
            and fact.key.operation == "like"
        )
        assert fact.support is CapabilitySupport.SUPPORTED
        assert tuple(item.reason for item in _backend_records(fact)) == (
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    else:
        assert matrix_case == "conflict_and_grouped_unsupported"
        unsupported = tuple(
            fact
            for fact in _dual_backend_facts(_all_facts())
            if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        )
        assert tuple((fact.key.domain, fact.key.subject) for fact in unsupported) == (
            (CapabilityDomain.CLAUSE, "order_by"),
            (CapabilityDomain.AGGREGATE, "count"),
        )
        assert all(len(_backend_records(fact)) == 2 for fact in unsupported)


def test_support_disposition_owner_reason_and_affirmative_evidence_are_exact() -> None:
    facts = _all_facts()
    assert Counter(fact.support for fact in facts) == {
        CapabilitySupport.SUPPORTED: 162,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED: 29,
    }
    assert Counter(fact.disposition.kind for fact in facts) == {
        CapabilityDispositionKind.NONE: 176,
        CapabilityDispositionKind.DEFERRED: 14,
        CapabilityDispositionKind.OUT_OF_SCOPE: 1,
    }
    assert Counter(fact.disposition.owner for fact in facts) == {
        None: 176,
        "POST60_ADVANCED_TYPE_NATIVE_MAPPING": 7,
        "POST60_ADVANCED_AGGREGATION_GROUPING": 7,
        "Pietto charter": 1,
    }
    affirmative_sources = {
        CapabilityEvidenceSource.GRAMMAR_AST,
        CapabilityEvidenceSource.SEMANTIC_CATALOG,
        CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
        CapabilityEvidenceSource.SEMANTIC_MODEL,
        CapabilityEvidenceSource.IR,
        CapabilityEvidenceSource.BACKEND,
        CapabilityEvidenceSource.PROJECT,
        CapabilityEvidenceSource.TEST,
    }
    for fact in facts:
        if fact.disposition.kind is CapabilityDispositionKind.NONE:
            assert fact.disposition.owner is None
            assert fact.disposition.reason is None
        else:
            assert fact.disposition.owner
            assert fact.disposition.reason
        if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED:
            assert any(item.source in affirmative_sources for item in fact.evidence)


@pytest.mark.parametrize(
    ("relative", "module"),
    (
        (FACTS_REL, capability_facts),
        (LOOKUP_REL, capability_lookup),
        (INVENTORY_REL, capability_inventory),
        (SIGNATURE_REL, capability_signatures),
        (CONTEXT_REL, capability_contexts),
        (AGGREGATE_REL, capability_aggregates),
        (PROFILE_REL, capability_profiles),
        (PROVIDER_REL, capability_providers),
        (COMPOSITION_REL, capability_composition),
    ),
)
def test_private_import_ast_dynamic_export_and_package_boundary_is_exact(
    relative: str,
    module: object,
) -> None:
    source = _read(REPO_ROOT / relative)
    tree = ast.parse(source, filename=relative)
    assert getattr(module, "__all__") == ()
    assert not any(isinstance(node, ast.Import) for node in tree.body)
    assert not any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr in {"import_module", "entry_points"}
        )
        for node in ast.walk(tree)
    )
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
        for token in ("registry", "callback", "consumer", "dispatcher")
    )
    assert "capability_" not in _read(REPO_ROOT / "src/pietto/semantic/__init__.py")
    assert "capability_" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_no_forbidden_compiler_project_public_serializer_runtime_consumer_exists() -> (
    None
):
    forbidden_names = {
        "inventory_lookup_inputs",
        "signature_lookup_inputs",
        "stage_clause_lookup_inputs",
        "aggregate_lookup_inputs",
        "window_lookup_inputs",
    }
    module_stems = {Path(path).stem for path in MODULE_RELS}
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    availability_rel = "src/pietto/_project/capability_availability.py"
    checking_rel = "src/pietto/_project/capability_checking.py"
    matrix_rel = "src/pietto/_project/capability_matrix.py"
    inspection_rel = "src/pietto/_project/capability_inspection.py"
    pure_boundary_rel = "src/pietto/_project/capability_pure_boundary.py"
    config_rel = "src/pietto/_project/config.py"
    model_rel = "src/pietto/_project/model.py"
    package_manifest_rel = "src/pietto/_project/package_manifest.py"
    package_graph_rel = "src/pietto/_project/package_graph.py"
    package_graph_inspection_rel = "src/pietto/_project/package_graph_inspection.py"
    package_requirements_rel = "src/pietto/_project/package_capability_requirements.py"
    package_selectors_rel = (
        "src/pietto/_project/package_extension_signature_selectors.py"
    )
    project_environment_rel = "src/pietto/_project/project_capability_environment.py"
    runtime_builder_rel = "src/pietto/_project_explain/runtime_builder.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if (
            relative
            in {
                *MODULE_RELS,
                preservation_rel,
                availability_rel,
                checking_rel,
                matrix_rel,
                inspection_rel,
                pure_boundary_rel,
                config_rel,
                model_rel,
                package_manifest_rel,
                package_graph_rel,
                package_requirements_rel,
                project_environment_rel,
                SELECTOR_REL,
                EXTENSION_PROVIDER_REL,
                EXTENSION_INSPECTION_REL,
                EXTENSION_INSPECTION_PURE_REL,
                "src/pietto/_project_explain/package_requirement_projection.py",
                "src/pietto/_project_explain/compatibility_matrix_projection.py",
                runtime_builder_rel,
            }
            or "generated" in path.parts
        ):
            continue
        source = _read(path)
        assert all(name not in source for name in forbidden_names)
        assert all(f"semantic.{stem}" not in source for stem in module_stems)
    for directory in ("_project", "sql", "metadata"):
        root = REPO_ROOT / "src/pietto" / directory
        if root.exists():
            assert all(
                "capability_" not in _read(path)
                for path in root.rglob("*.py")
                if "generated" not in path.parts
                and path.relative_to(REPO_ROOT).as_posix()
                not in {
                    preservation_rel,
                    availability_rel,
                    checking_rel,
                    matrix_rel,
                    inspection_rel,
                    pure_boundary_rel,
                    config_rel,
                    model_rel,
                    package_manifest_rel,
                    package_graph_rel,
                    package_graph_inspection_rel,
                    package_requirements_rel,
                    package_selectors_rel,
                    project_environment_rel,
                    EXTENSION_PROVIDER_REL,
                    EXTENSION_INSPECTION_REL,
                    EXTENSION_INSPECTION_PURE_REL,
                }
            )
    provider_source = _read(REPO_ROOT / PROVIDER_REL)
    assert all(name in provider_source for name in forbidden_names)
    availability_source = _read(REPO_ROOT / availability_rel)
    assert "semantic.capability_profiles" in availability_source
    assert all(name not in availability_source for name in forbidden_names)
    assert all(
        f"semantic.{stem}" not in availability_source
        for stem in module_stems - {"capability_profiles"}
    )
    package_graph_source = _read(REPO_ROOT / package_graph_rel)
    package_graph_stems = {"capability_profiles"}
    assert all(name not in package_graph_source for name in forbidden_names)
    assert all(
        (f"semantic.{stem}" in package_graph_source) is (stem in package_graph_stems)
        for stem in module_stems
    )
    package_graph_inspection_source = _read(REPO_ROOT / package_graph_inspection_rel)
    assert "snapshot.capability_evaluations" in package_graph_inspection_source
    assert all(name not in package_graph_inspection_source for name in forbidden_names)
    assert all(
        f"semantic.{stem}" not in package_graph_inspection_source
        for stem in module_stems
    )
    selector_source = _read(REPO_ROOT / SELECTOR_REL)
    assert all(name not in selector_source for name in forbidden_names)
    selector_stems = {"capability_facts", "capability_profiles"}
    assert all(
        (f"semantic.{stem}" in selector_source) is (stem in selector_stems)
        for stem in module_stems
    )
    checking_source = _read(REPO_ROOT / checking_rel)
    checking_stems = {
        "capability_composition",
        "capability_facts",
        "capability_lookup",
        "capability_profiles",
        "capability_providers",
    }
    assert all(name not in checking_source for name in forbidden_names)
    assert all(
        (f"semantic.{stem}" in checking_source) is (stem in checking_stems)
        for stem in module_stems
    )
    matrix_source = _read(REPO_ROOT / matrix_rel)
    matrix_stems = {"capability_composition", "capability_profiles"}
    assert all(name not in matrix_source for name in forbidden_names)
    assert all(
        (f"semantic.{stem}" in matrix_source) is (stem in matrix_stems)
        for stem in module_stems
    )
    inspection_source = _read(REPO_ROOT / inspection_rel)
    inspection_stems = {
        "capability_composition",
        "capability_facts",
        "capability_lookup",
        "capability_profiles",
    }
    assert all(name not in inspection_source for name in forbidden_names)
    assert all(
        (f"semantic.{stem}" in inspection_source) is (stem in inspection_stems)
        for stem in module_stems
    )
    pure_boundary_source = _read(REPO_ROOT / pure_boundary_rel)
    assert all(name not in pure_boundary_source for name in forbidden_names)
    assert all(f"semantic.{stem}" not in pure_boundary_source for stem in module_stems)
    preservation_source = _read(REPO_ROOT / preservation_rel)
    assert "canonical_capability_provider_inputs" in preservation_source
    assert all(name not in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source
