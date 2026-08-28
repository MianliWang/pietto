from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_signatures as capability_signatures
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
from pietto.semantic.catalog import BUILTIN_FUNCTIONS


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_signatures.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_signatures, name))


def _all_facts() -> tuple[CapabilityFact, ...]:
    return _facts("_CAPABILITY_SIGNATURE_FACTS")


def _inputs(
    key: CapabilityKey,
) -> tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None]:
    helper = cast(Any, getattr(capability_signatures, "signature_lookup_inputs"))
    return cast(
        tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None],
        helper(key),
    )


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = _inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _assert_fact(
    fact: CapabilityFact,
    domain: CapabilityDomain,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    assert fact.key == CapabilityKey(
        domain,
        subject=subject,
        operation=operation,
        operands=operands,
        context="expression",
    )
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert fact.disposition.owner is None
    assert fact.disposition.reason is None


def test_private_module_api_and_dependency_shape_is_exact() -> None:
    source = _read(SOURCE_PATH)
    tree = ast.parse(source, filename=SOURCE_REL)
    assert capability_signatures.__all__ == ()
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    }
    assert imports == {"collections.abc", "pietto.semantic.capability_facts"}
    assert "capability_lookup" not in source
    assert "lookup_capability" not in source
    assert "CapabilityDomain.NULLABILITY" not in source
    for forbidden in ("rglob(", "getenv(", "environ", "open(", "registry", "cache"):
        assert forbidden not in source.lower()
    with pytest.raises(ValueError, match="exact capability key"):
        cast(Any, capability_signatures.signature_lookup_inputs)("comparison")


def test_signature_family_counts_order_and_combined_tuple_are_exact() -> None:
    scalar = _facts("_SCALAR_FUNCTION_FACTS")
    unary = _facts("_UNARY_OPERATOR_FACTS")
    binary = _facts("_BINARY_OPERATOR_FACTS")
    comparison = _facts("_COMPARISON_FACTS")
    null_test = _facts("_NULL_TEST_FACTS")
    combined = _all_facts()
    assert tuple(map(len, (scalar, unary, binary, comparison, null_test))) == (
        4,
        4,
        21,
        8,
        2,
    )
    assert combined == (*scalar, *unary, *binary, *comparison, *null_test)
    assert len(combined) == len(set(combined)) == 39
    assert tuple(fact.key.domain for fact in combined) == (
        *(CapabilityDomain.SCALAR_FUNCTION for _ in range(4)),
        *(CapabilityDomain.UNARY_OPERATOR for _ in range(4)),
        *(CapabilityDomain.BINARY_OPERATOR for _ in range(21)),
        *(CapabilityDomain.COMPARISON for _ in range(8)),
        *(CapabilityDomain.NULL_TEST for _ in range(2)),
    )


def test_freeze_rejects_exact_duplicates_and_preserves_same_key_distinct_facts() -> (
    None
):
    freeze = cast(Any, getattr(capability_signatures, "_freeze_signatures"))
    fact = _all_facts()[0]
    with pytest.raises(ValueError, match="duplicate"):
        freeze((fact, fact))
    conflicting = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freeze((fact, conflicting)) == (fact, conflicting)


def test_fixed_tail_key_encoding_preserves_identity_arity_result_and_nullability() -> (
    None
):
    for fact in _all_facts():
        key = fact.key
        assert key.subject is not None
        assert len(key.operands) >= 2
        remaining_inputs = key.operands[:-2]
        result_type = key.operands[-2]
        result_nullability = key.operands[-1]
        inputs = (key.subject, *remaining_inputs)
        assert all(inputs)
        assert result_type in {"Int", "Float", "Decimal", "Text", "Bool"}
        assert result_nullability in {"unknown", "non_null", "preserve_operand"}
        assert key.context == "expression"
        assert key.dialect is None
        assert key.extension is None


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Text", "lower", ("Text", "unknown")),
        (1, "Text", "trim", ("Text", "unknown")),
        (2, "Text", "len", ("Int", "unknown")),
        (3, "Text", "matches", ("Text", "Bool", "unknown")),
    ),
    ids=("lower", "trim", "len", "matches"),
)
def test_scalar_function_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_SCALAR_FUNCTION_FACTS")[index],
        CapabilityDomain.SCALAR_FUNCTION,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Int", "+", ("Int", "preserve_operand")),
        (1, "Float", "+", ("Float", "preserve_operand")),
        (2, "Int", "-", ("Int", "preserve_operand")),
        (3, "Float", "-", ("Float", "preserve_operand")),
    ),
    ids=("int-plus", "float-plus", "int-minus", "float-minus"),
)
def test_unary_operator_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_UNARY_OPERATOR_FACTS")[index],
        CapabilityDomain.UNARY_OPERATOR,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Int", "+", ("Int", "Int", "unknown")),
        (1, "Int", "+", ("Float", "Float", "unknown")),
        (2, "Float", "+", ("Int", "Float", "unknown")),
        (3, "Float", "+", ("Float", "Float", "unknown")),
        (4, "Decimal", "+", ("Decimal", "Decimal", "unknown")),
        (5, "Decimal", "+", ("Int", "Decimal", "unknown")),
        (6, "Int", "+", ("Decimal", "Decimal", "unknown")),
        (7, "Int", "-", ("Int", "Int", "unknown")),
        (8, "Int", "-", ("Float", "Float", "unknown")),
        (9, "Float", "-", ("Int", "Float", "unknown")),
        (10, "Float", "-", ("Float", "Float", "unknown")),
        (11, "Decimal", "-", ("Decimal", "Decimal", "unknown")),
        (12, "Decimal", "-", ("Int", "Decimal", "unknown")),
        (13, "Int", "-", ("Decimal", "Decimal", "unknown")),
        (14, "Int", "*", ("Int", "Int", "unknown")),
        (15, "Int", "*", ("Float", "Float", "unknown")),
        (16, "Float", "*", ("Int", "Float", "unknown")),
        (17, "Float", "*", ("Float", "Float", "unknown")),
        (18, "Int", "%", ("Int", "Int", "unknown")),
        (19, "Bool", "and", ("Bool", "Bool", "unknown")),
        (20, "Bool", "or", ("Bool", "Bool", "unknown")),
    ),
    ids=(
        "int-add-int",
        "int-add-float",
        "float-add-int",
        "float-add-float",
        "decimal-add-decimal",
        "decimal-add-int",
        "int-add-decimal",
        "int-sub-int",
        "int-sub-float",
        "float-sub-int",
        "float-sub-float",
        "decimal-sub-decimal",
        "decimal-sub-int",
        "int-sub-decimal",
        "int-mul-int",
        "int-mul-float",
        "float-mul-int",
        "float-mul-float",
        "int-mod-int",
        "bool-and-bool",
        "bool-or-bool",
    ),
)
def test_binary_operator_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_BINARY_OPERATOR_FACTS")[index],
        CapabilityDomain.BINARY_OPERATOR,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Expression", "==", ("Expression", "Bool", "unknown")),
        (1, "Expression", "!=", ("Expression", "Bool", "unknown")),
        (2, "Expression", "<", ("Expression", "Bool", "unknown")),
        (3, "Expression", "<=", ("Expression", "Bool", "unknown")),
        (4, "Expression", ">", ("Expression", "Bool", "unknown")),
        (5, "Expression", ">=", ("Expression", "Bool", "unknown")),
        (6, "Expression", "like", ("Expression", "Bool", "unknown")),
        (
            7,
            "ValueTypeKind.KNOWN",
            "between",
            (
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Bool",
                "unknown",
            ),
        ),
    ),
    ids=("eq", "ne", "lt", "le", "gt", "ge", "like", "between"),
)
def test_comparison_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_COMPARISON_FACTS")[index],
        CapabilityDomain.COMPARISON,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "operation"),
    ((0, "is null"), (1, "is not null")),
    ids=("is-null", "is-not-null"),
)
def test_null_test_fact_is_exact(index: int, operation: str) -> None:
    _assert_fact(
        _facts("_NULL_TEST_FACTS")[index],
        CapabilityDomain.NULL_TEST,
        "Expression",
        operation,
        ("Bool", "non_null"),
    )


def test_scalar_catalog_excludes_aggregates_connectors_and_user_callables() -> None:
    facts = _facts("_SCALAR_FUNCTION_FACTS")
    assert tuple(BUILTIN_FUNCTIONS) == ("lower", "trim", "len", "matches")
    assert tuple(fact.key.operation for fact in facts) == tuple(BUILTIN_FUNCTIONS)
    excluded = {
        "count",
        "count_distinct",
        "sum",
        "avg",
        "min",
        "max",
        "connector",
        "user_callable",
    }
    assert excluded.isdisjoint({fact.key.operation for fact in facts})


def test_like_and_matches_backend_ledgers_are_scoped_without_precedence() -> None:
    matches = _facts("_SCALAR_FUNCTION_FACTS")[-1]
    like = _facts("_COMPARISON_FACTS")[-2]
    for fact in (matches, like):
        assert fact.key.dialect is None
        assert fact.key.extension is None
        backends = tuple(
            entry
            for entry in fact.evidence
            if entry.source is CapabilityEvidenceSource.BACKEND
        )
        assert tuple((entry.dialect, entry.backend) for entry in backends) == (
            ("postgresql", "postgresql"),
            ("mysql", "private-mysql"),
        )
    match_backends = tuple(
        entry
        for entry in matches.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert tuple(entry.reason for entry in match_backends) == (
        None,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
    )
    like_backends = tuple(
        entry
        for entry in like.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert all(
        entry.reason is CapabilityReasonCode.DIALECT_LOWERING_GAP
        for entry in like_backends
    )


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Int",
            operation="/",
            operands=("Int", "Int", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Decimal",
            operation="*",
            operands=("Decimal", "Decimal", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Text",
            operation="+",
            operands=("Text", "Text", "unknown"),
            context="expression",
        ),
    ),
    ids=("division", "decimal-multiply", "text-concatenation"),
)
def test_omitted_operator_family_remains_incomplete(key: CapabilityKey) -> None:
    facts, complete, _ = _inputs(key)
    assert facts is _facts("_BINARY_OPERATOR_FACTS")
    assert complete is False
    assert isinstance(_lookup(key), Unknown)


def test_generic_comparison_and_between_do_not_claim_concrete_pair_compatibility() -> (
    None
):
    concrete = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Int",
        operation="==",
        operands=("Int", "Bool", "unknown"),
        context="expression",
    )
    unknown_child = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="ValueTypeKind.KNOWN",
        operation="between",
        operands=(
            "ValueTypeKind.UNKNOWN",
            "ValueTypeKind.KNOWN",
            "Bool",
            "unknown",
        ),
        context="expression",
    )
    for key in (concrete, unknown_child):
        facts, complete, reason = _inputs(key)
        assert facts is _facts("_COMPARISON_FACTS")
        assert complete is False
        assert reason is None
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_null_tests_preserve_non_null_bool_and_distinct_three_valued_truth() -> None:
    for fact in _facts("_NULL_TEST_FACTS"):
        assert fact.key.operands == ("Bool", "non_null")
        reasons = {entry.reason for entry in fact.evidence}
        assert CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE in reasons
        assert CapabilityReasonCode.SQL_THREE_VALUED_TRUTH in reasons
        assert CapabilityReasonCode.UNKNOWN_NULLABILITY not in reasons
    assert "Null" not in {
        fact.key.subject for fact in _all_facts() if fact.key.subject is not None
    }


def test_evidence_order_uniqueness_and_paths_are_exact() -> None:
    source_order = {
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
    allowed_reasons = {
        None,
        CapabilityReasonCode.UNKNOWN_NULLABILITY,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
        CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
    }
    for fact in _all_facts():
        evidence = fact.evidence
        assert len(evidence) == len(set(evidence))
        assert tuple(source_order[item.source] for item in evidence) == tuple(
            sorted(source_order[item.source] for item in evidence)
        )
        assert all((REPO_ROOT / item.source_path).is_file() for item in evidence)
        assert all(item.extension is None for item in evidence)
        assert all(item.reason in allowed_reasons for item in evidence)
        assert not any(
            item.source
            in {CapabilityEvidenceSource.PROJECT, CapabilityEvidenceSource.PUBLIC}
            for item in evidence
        )
        backends = tuple(
            item for item in evidence if item.source is CapabilityEvidenceSource.BACKEND
        )
        assert tuple((item.dialect, item.backend) for item in backends) == (
            ("postgresql", "postgresql"),
            ("mysql", "private-mysql"),
        )


def test_signature_completeness_schemas_are_exact() -> None:
    complete_absences = (
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="upper",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.UNARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Float", "preserve_operand"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Int", "Float", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.COMPARISON,
            subject="Expression",
            operation="==",
            operands=("Expression", "Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.COMPARISON,
            subject="ValueTypeKind.KNOWN",
            operation="between",
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Text",
                "unknown",
            ),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.NULL_TEST,
            subject="Expression",
            operation="is null",
            operands=("Text", "non_null"),
            context="expression",
        ),
    )
    assert all(_inputs(key)[1:] == (True, None) for key in complete_absences)
    incomplete = (
        replace(complete_absences[0], dialect="postgresql"),
        replace(
            complete_absences[0],
            dialect="postgresql",
            extension="future",
        ),
        replace(complete_absences[0], subject="text"),
        replace(complete_absences[0], operands=("Bogus", "unknown")),
        replace(
            complete_absences[0],
            operands=("Text", "Bogus", "unknown"),
        ),
        replace(complete_absences[0], operands=("Text",)),
        replace(
            complete_absences[0],
            operands=("Text", "unknown", "Bogus"),
        ),
        replace(complete_absences[1], operands=("Int", "unknown")),
        replace(complete_absences[1], operands=("Bogus", "preserve_operand")),
        replace(complete_absences[1], operands=("int", "preserve_operand")),
        replace(
            complete_absences[1],
            operands=("Int", "preserve_operand", "extra"),
        ),
        replace(complete_absences[2], context="where"),
        replace(complete_absences[2], operands=("Int", "Bogus", "unknown")),
        replace(
            complete_absences[3],
            operands=("Expression", "Bogus", "unknown"),
        ),
        replace(
            complete_absences[4],
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Bogus",
                "unknown",
            ),
        ),
        replace(complete_absences[5], operands=("Bogus", "non_null")),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="Int",
            operation="sum",
            operands=("Int", "unknown"),
            context="expression",
        ),
    )
    assert all(_inputs(key)[1:] == (False, None) for key in incomplete)


def test_all_inventory_keys_lookup_as_found() -> None:
    for fact in _all_facts():
        result = _lookup(fact.key)
        assert result == Found(fact)
        assert isinstance(result, Found)
        assert result.fact is fact


def test_complete_schema_zero_match_lookup_is_absent() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="upper",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="lower",
            operands=("Text", "Text", "unknown"),
            context="expression",
        ),
        replace(
            _facts("_UNARY_OPERATOR_FACTS")[0].key,
            operands=("Float", "preserve_operand"),
        ),
        replace(
            _facts("_BINARY_OPERATOR_FACTS")[0].key,
            operands=("Int", "Float", "unknown"),
        ),
        replace(
            _facts("_COMPARISON_FACTS")[0].key,
            operands=("Expression", "Text", "unknown"),
        ),
        replace(
            _facts("_COMPARISON_FACTS")[-1].key,
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Text",
                "unknown",
            ),
        ),
        replace(_facts("_NULL_TEST_FACTS")[0].key, operands=("Text", "non_null")),
    )
    assert all(_lookup(key) == Absent(key) for key in keys)


def test_incomplete_and_division_lookups_are_unknown_with_exact_reasons() -> None:
    division = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject="Int",
        operation="/",
        operands=("Int", "Int", "unknown"),
        context="expression",
    )
    matches_mysql = replace(
        _facts("_SCALAR_FUNCTION_FACTS")[-1].key,
        dialect="mysql",
    )
    like_postgres = replace(_facts("_COMPARISON_FACTS")[-2].key, dialect="postgresql")
    like_mysql = replace(_facts("_COMPARISON_FACTS")[-2].key, dialect="mysql")
    expected = (
        (division, CapabilityReasonCode.NO_CURRENT_RESULT_RULE),
        (matches_mysql, CapabilityReasonCode.DIALECT_LOWERING_GAP),
        (like_postgres, CapabilityReasonCode.DIALECT_LOWERING_GAP),
        (like_mysql, CapabilityReasonCode.DIALECT_LOWERING_GAP),
    )
    for key, reason in expected:
        _, complete, actual_reason = _inputs(key)
        assert complete is False
        assert actual_reason is reason
        assert _lookup(key) == Unknown(reason)
    malformed = (
        replace(division, subject="Bogus"),
        replace(division, operands=("Bogus", "Int", "unknown")),
        replace(division, operands=("Int", "Bogus", "unknown")),
        replace(division, operands=("Int", "int", "unknown")),
        replace(division, operands=("Int", "Int")),
        replace(division, operands=("Int", "Int", "unknown", "extra")),
        replace(division, context="where"),
        replace(division, dialect="postgresql"),
        replace(division, dialect="postgresql", extension="future"),
        replace(matches_mysql, extension="future"),
        replace(like_postgres, extension="future"),
    )
    for key in malformed:
        _, complete, reason = _inputs(key)
        assert complete is False
        assert reason is None
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    concrete = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Date",
        operation="==",
        operands=("Date", "Bool", "unknown"),
        context="expression",
    )
    assert _inputs(concrete)[1:] == (False, None)
    assert _lookup(concrete) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_distinct_same_key_facts_lookup_as_conflict_without_precedence() -> None:
    fact = _all_facts()[0]
    conflict = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    result = lookup_capability(
        fact.key,
        (fact, conflict),
        domain_complete=True,
    )
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, conflict),
    )


def test_no_aggregate_stage_clause_or_window_fact_is_present() -> None:
    forbidden_domains = {
        CapabilityDomain.AGGREGATE,
        CapabilityDomain.CLAUSE,
        CapabilityDomain.EXPRESSION_STAGE,
        CapabilityDomain.WINDOW_FUNCTION,
    }
    assert forbidden_domains.isdisjoint({fact.key.domain for fact in _all_facts()})
    assert not any(
        "window" in value for fact in _all_facts() for value in fact.key.operands
    )
    for domain in forbidden_domains:
        key = CapabilityKey(domain, subject="Expression", context="expression")
        assert _inputs(key) == ((), False, None)


def test_no_compiler_project_public_or_runtime_consumer_exists() -> None:
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
        assert "semantic.capability_signatures" not in source
        assert "signature_lookup_inputs" not in source
    preservation_source = REPOSITORY_FACTS.python(preservation_path).text
    assert "semantic.capability_signatures" in preservation_source
    assert "signature_lookup_inputs" not in preservation_source
    provider_source = REPOSITORY_FACTS.python(provider_path).text
    assert "semantic.capability_signatures" in provider_source
    assert "signature_lookup_inputs" in provider_source
    assert (
        "capability_signatures"
        not in REPOSITORY_FACTS.python(
            REPO_ROOT / "src/pietto/semantic/__init__.py"
        ).text
    )
    assert (
        "capability_signatures"
        not in REPOSITORY_FACTS.python(REPO_ROOT / "src/pietto/__init__.py").text
    )


def test_slice4_inventory_fact_count_and_completeness_are_unchanged() -> None:
    combined = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_inventory, "_CAPABILITY_FACTS"),
    )
    assert len(combined) == len(set(combined)) == 41
    helper = cast(Any, capability_inventory.inventory_lookup_inputs)
    found_key = combined[0].key
    found_inputs = helper(found_key)
    assert len(found_inputs) == 2
    assert found_inputs[1] is True
    incomplete = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="query",
        operation="binding",
        context="runtime",
    )
    assert helper(incomplete)[1] is False
