from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
import pietto.semantic.capability_inventory as capability_inventory
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
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
SOURCE_REL = "src/pietto/semantic/capability_inventory.py"
SELF_REL = "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_inventory, name))


def _all_facts() -> tuple[CapabilityFact, ...]:
    return _facts("_CAPABILITY_FACTS")


def _inputs(key: CapabilityKey) -> tuple[tuple[CapabilityFact, ...], bool]:
    function = cast(
        Any,
        getattr(capability_inventory, "inventory_lookup_inputs"),
    )
    return cast(tuple[tuple[CapabilityFact, ...], bool], function(key))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete = _inputs(key)
    return lookup_capability(key, facts, domain_complete=complete)


def test_private_module_api_and_privacy_shape_are_exact() -> None:
    source = _read(SOURCE_PATH)
    tree = ast.parse(source, filename=SOURCE_REL)
    assert capability_inventory.__all__ == ()
    assert "capability_lookup" not in source
    assert "lookup_capability" not in source
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    assert "CapabilityDomain.NULLABILITY" not in source
    with pytest.raises(ValueError):
        cast(Any, capability_inventory.inventory_lookup_inputs)("logical_type")


def test_four_fact_tuples_counts_order_and_combined_identity_are_exact() -> None:
    logical = _facts("_LOGICAL_TYPE_FACTS")
    literals = _facts("_LITERAL_FACTS")
    parameters = _facts("_PARAMETER_FACTS")
    nullability = _facts("_NULLABILITY_FACTS")
    combined = _all_facts()
    assert tuple(map(len, (logical, literals, parameters, nullability))) == (
        22,
        13,
        3,
        3,
    )
    assert combined == (*logical, *literals, *parameters, *nullability)
    assert len(combined) == len(set(combined)) == 41
    assert tuple(fact.key.subject for fact in combined[:11]) == (
        "Any",
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


def test_inventory_construction_rejects_exact_duplicates_but_preserves_conflicts() -> (
    None
):
    freeze = cast(Any, getattr(capability_inventory, "_freeze_inventory"))
    fact = _all_facts()[0]
    with pytest.raises(ValueError, match="duplicate"):
        freeze((fact, fact))
    conflicting = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freeze((fact, conflicting)) == (fact, conflicting)


@pytest.mark.parametrize(
    "subject",
    (
        "Any",
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
    ),
    ids=(
        "any",
        "bool",
        "bytes",
        "date",
        "decimal",
        "float",
        "int",
        "json",
        "text",
        "timestamp",
        "uuid",
    ),
)
def test_builtin_catalog_membership_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="catalog_membership",
        context="builtin_registry",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    assert result.fact.disposition.kind is CapabilityDispositionKind.NONE


@pytest.mark.parametrize(
    "subject",
    ("type_alias", "enum", "shape"),
    ids=("type-alias", "enum", "shape"),
)
def test_declaration_kind_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="declaration_kind",
        context="semantic_model",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


@pytest.mark.parametrize(
    ("subject", "reason", "disposition"),
    (
        (
            "<unknown>",
            CapabilityReasonCode.UNRESOLVED_EXPRESSION,
            CapabilityDispositionKind.NONE,
        ),
        (
            "Null",
            CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
            CapabilityDispositionKind.NONE,
        ),
        (
            "DateTime",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Time",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Interval",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Money",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Currency",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
    ),
    ids=("unknown", "null", "datetime", "time", "interval", "money", "currency"),
)
def test_internal_and_deferred_logical_type_facts_fail_closed(
    subject: str,
    reason: CapabilityReasonCode,
    disposition: CapabilityDispositionKind,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="catalog_membership",
        context="builtin_registry",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition.kind is disposition
    assert reason in {entry.reason for entry in result.fact.evidence}


def test_decimal_precision_scale_is_one_bounded_supported_side_fact() -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="Decimal",
        operation="precision_scale",
        operands=("Int", "Int"),
        context="type_expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    non_decimal = replace(key, subject="Text")
    facts, complete = _inputs(non_decimal)
    assert facts
    assert complete is False
    assert lookup_capability(non_decimal, facts, domain_complete=complete) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


@pytest.mark.parametrize(
    ("subject", "operands"),
    (
        ("integer", ("Int", "non_null")),
        ("float", ("Float", "non_null")),
        ("text", ("Text", "non_null")),
        ("boolean", ("Bool", "non_null")),
        ("null", ("no_concrete_type", "unknown")),
    ),
    ids=("integer", "float", "text", "boolean", "null"),
)
def test_supported_literal_results_are_exact(
    subject: str,
    operands: tuple[str, ...],
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LITERAL,
        subject=subject,
        operation="result",
        operands=operands,
        context="expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


@pytest.mark.parametrize(
    ("subject", "disposition"),
    (
        ("Any", CapabilityDispositionKind.NONE),
        ("Bytes", CapabilityDispositionKind.NONE),
        ("Date", CapabilityDispositionKind.DEFERRED),
        ("Decimal", CapabilityDispositionKind.NONE),
        ("Json", CapabilityDispositionKind.NONE),
        ("Timestamp", CapabilityDispositionKind.DEFERRED),
        ("UUID", CapabilityDispositionKind.NONE),
        ("Enum", CapabilityDispositionKind.NONE),
    ),
    ids=("any", "bytes", "date", "decimal", "json", "timestamp", "uuid", "enum"),
)
def test_unsupported_literal_categories_are_explicit(
    subject: str,
    disposition: CapabilityDispositionKind,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LITERAL,
        subject=subject,
        operation="result",
        context="expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition.kind is disposition
    assert CapabilityReasonCode.NOT_EVIDENCED in {
        entry.reason for entry in result.fact.evidence
    }


@pytest.mark.parametrize(
    "subject",
    ("constraint", "derive"),
    ids=("constraint", "derive"),
)
def test_callable_declaration_parameter_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject=subject,
        operation="declare",
        operands=("name", "TypeExpr"),
        context="callable_declaration",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


def test_runtime_sql_parameter_substitution_is_explicitly_out_of_scope() -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="runtime_sql_parameter",
        operation="substitute",
        context="runtime_execution",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition == CapabilityDisposition(
        CapabilityDispositionKind.OUT_OF_SCOPE,
        "Pietto charter",
        "runtime substitution and prepared-statement execution are host/database responsibilities",
    )


@pytest.mark.parametrize(
    ("subject", "result_name", "reason"),
    (
        ("implicit", "unknown", CapabilityReasonCode.UNKNOWN_NULLABILITY),
        ("nullable", "nullable", None),
        ("not_null", "non_null", None),
    ),
    ids=("implicit", "nullable", "not-null"),
)
def test_declared_nullability_mappings_are_exact(
    subject: str,
    result_name: str,
    reason: CapabilityReasonCode | None,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="effective_nullability",
        operands=(result_name,),
        context="type_expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    assert reason in {entry.reason for entry in result.fact.evidence}


def test_null_literal_is_distinct_from_null_and_unknown_logical_spellings() -> None:
    null_literal = next(
        fact for fact in _facts("_LITERAL_FACTS") if fact.key.subject == "null"
    )
    assert null_literal.key.operands == ("no_concrete_type", "unknown")
    assert null_literal.support is CapabilitySupport.SUPPORTED
    logical_subjects = {
        fact.key.subject
        for fact in _facts("_LOGICAL_TYPE_FACTS")
        if fact.key.operation == "catalog_membership"
    }
    assert {"Null", "<unknown>"} <= logical_subjects
    assert "null" not in logical_subjects


def test_each_fact_has_unique_evidence_in_locked_layer_order() -> None:
    rank = {
        source: index
        for index, source in enumerate(
            (
                CapabilityEvidenceSource.GRAMMAR_AST,
                CapabilityEvidenceSource.SEMANTIC_CATALOG,
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                CapabilityEvidenceSource.SEMANTIC_MODEL,
                CapabilityEvidenceSource.IR,
                CapabilityEvidenceSource.BACKEND,
                CapabilityEvidenceSource.PROJECT,
                CapabilityEvidenceSource.PUBLIC,
                CapabilityEvidenceSource.ROADMAP,
                CapabilityEvidenceSource.TEST,
                CapabilityEvidenceSource.SPEC,
            )
        )
    }
    for fact in _all_facts():
        assert fact.evidence
        assert len(fact.evidence) == len(set(fact.evidence))
        assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
        evidence_rank = [rank[entry.source] for entry in fact.evidence]
        assert evidence_rank == sorted(evidence_rank)


@pytest.mark.parametrize(
    "subject",
    ("integer", "float", "text", "boolean", "null"),
    ids=("integer", "float", "text", "boolean", "null"),
)
def test_supported_literals_have_ordered_postgresql_and_private_mysql_scope(
    subject: str,
) -> None:
    fact = next(
        fact for fact in _facts("_LITERAL_FACTS") if fact.key.subject == subject
    )
    backend = tuple(
        (entry.dialect, entry.backend)
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert backend == (("postgresql", "postgresql"), ("mysql", "private-mysql"))


def test_seven_exact_completeness_schemas_and_unowned_domains_are_locked() -> None:
    complete = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "Future",
            "catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "future_kind",
            "declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "Decimal",
            "precision_scale",
            ("Int", "Int"),
            "type_expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "integer",
            "result",
            ("Int", "non_null"),
            "expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "Any",
            "result",
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            "constraint",
            "declare",
            ("name", "TypeExpr"),
            context="callable_declaration",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            "runtime_sql_parameter",
            "substitute",
            context="runtime_execution",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "implicit",
            "effective_nullability",
            ("unknown",),
            context="type_expression",
        ),
    )
    assert all(_inputs(key)[1] for key in complete)
    incomplete = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            operation="declaration_kind",
            context="semantic_model",
        ),
        replace(complete[2], operands=("Int",)),
        replace(complete[2], operands=("Int", "Int", "Int")),
        replace(complete[3], operands=()),
        replace(complete[3], operands=("Int", "non_null", "extra")),
        replace(complete[3], operands=("Bogus", "non_null")),
        replace(complete[3], operands=("Int", "Bogus")),
        replace(complete[3], subject="Integer"),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "future",
            "result",
            ("Future",),
            "expression",
        ),
        replace(complete[4], operands=("unexpected",)),
        replace(complete[5], operands=()),
        replace(complete[5], operands=("name", "TypeExpr", "extra")),
        replace(complete[5], operands=("name", "Bogus")),
        replace(complete[5], subject="Constraint"),
        replace(complete[6], operands=("unexpected",)),
        replace(complete[7], operands=()),
        replace(complete[7], operands=("unknown", "extra")),
        replace(complete[7], operands=("Bogus",)),
        replace(complete[7], subject="Implicit"),
        replace(complete[7], context="expression"),
    )
    for key in incomplete:
        facts, schema_complete = _inputs(key)
        assert facts
        assert schema_complete is False
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    unowned = CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="sum",
        operation="result",
    )
    assert _inputs(unowned) == ((), False)


def test_every_inventory_fact_resolves_to_found_with_exact_identity() -> None:
    for fact in _all_facts():
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact is fact


def test_unlisted_complete_builtin_catalog_spelling_resolves_absent() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureScalar",
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="future_kind",
            operation="declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Float", "non_null"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("nullable",),
            context="type_expression",
        ),
    )
    assert all(_lookup(key) == Absent(key) for key in keys)


def test_incomplete_query_parameter_binding_resolves_unknown() -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="query_placeholder",
        operation="bind",
        context="query_expression",
    )
    facts, complete = _inputs(key)
    assert facts == _facts("_PARAMETER_FACTS")
    assert complete is False
    assert lookup_capability(key, facts, domain_complete=complete) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


def test_dialect_and_extension_keyed_zero_matches_resolve_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Int", "non_null"),
            context="expression",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="Int",
            operation="catalog_membership",
            context="builtin_registry",
            dialect="postgresql",
            extension="future",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            subject="constraint",
            operation="declare",
            operands=("name", "TypeExpr"),
            context="callable_declaration",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("unknown",),
            context="type_expression",
            dialect="postgresql",
            extension="future",
        ),
    )
    for key in keys:
        facts, complete = _inputs(key)
        assert facts
        assert complete is False
        assert lookup_capability(key, facts, domain_complete=complete) == Unknown(
            CapabilityReasonCode.NOT_EVIDENCED
        )


def test_lookup_folds_duplicates_and_preserves_distinct_same_key_conflicts() -> None:
    fact = _all_facts()[0]
    assert lookup_capability(
        fact.key,
        (fact, fact),
        domain_complete=True,
    ) == Found(fact)
    conflict = CapabilityFact(
        fact.key,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        fact.disposition,
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                SELF_REL,
                "injected distinct same-key conflict",
                CapabilityReasonCode.CONFLICTING_EVIDENCE,
            ),
        ),
    )
    assert lookup_capability(
        fact.key,
        (fact, conflict),
        domain_complete=True,
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (fact, conflict))


def test_private_inventory_has_no_compiler_public_or_serializer_consumer() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    provider_path = REPO_ROOT / "src/pietto/semantic/capability_providers.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if (
            path in {SOURCE_PATH, preservation_path, provider_path}
            or "generated" in path.parts
        ):
            continue
        source = REPOSITORY_FACTS.python(path).text
        assert "semantic.capability_inventory" not in source
        assert "inventory_lookup_inputs" not in source
    preservation_source = REPOSITORY_FACTS.python(preservation_path).text
    assert "semantic.capability_inventory" in preservation_source
    assert "inventory_lookup_inputs" not in preservation_source
    provider_source = REPOSITORY_FACTS.python(provider_path).text
    assert "semantic.capability_inventory" in provider_source
    assert "inventory_lookup_inputs" in provider_source
    assert (
        "capability_inventory"
        not in REPOSITORY_FACTS.python(
            REPO_ROOT / "src/pietto/semantic/__init__.py"
        ).text
    )
    assert (
        "capability_inventory"
        not in REPOSITORY_FACTS.python(REPO_ROOT / "src/pietto/__init__.py").text
    )
