from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.semantic.capability_contexts as capability_contexts
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


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_contexts.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
STAGE_EXPECTED = (
    ("literal_expression", "CONSTANT"),
    ("constant_scalar_expression", "CONSTANT"),
    ("resolved_row_reference", "ROW"),
    ("row_scalar_expression", "ROW"),
    ("aggregate_dependent_expression", "GROUP"),
    ("group_output_reference", "GROUP"),
    ("unresolved_reference_expression", "UNKNOWN"),
)

CLAUSE_EXPECTED = (
    (
        "where",
        (
            "ROW",
            "Bool_when_known",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "pre_group_filter",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "group_by",
        (
            "ROW",
            "no_result_type_constraint",
            "direct_input_field_or_direct_field_row_let",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "group_key",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "bounded_result_predicate",
            "selected_group_key_and_aggregate_outputs",
            "selected_output_names_with_matching_aggregate_let_exception",
        ),
        "grouped_result_filter",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "ROW",
            "no_result_type_constraint",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "input_order",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "GROUP",
            "no_result_type_constraint",
            "bare_selected_output_or_matching_group_key_row_let",
            "selected_group_key_and_aggregate_outputs",
            "selected_output_names_with_matching_group_key_let_exception",
        ),
        "grouped_result_order",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "where",
        (
            "ROW",
            "Bool_when_known",
            "aggregate_dependent_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "pre_group_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "group_by",
        (
            "ROW",
            "no_result_type_constraint",
            "non_field_group_key",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "group_key",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "broad expression group keys require separate authorization",
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "global_aggregate_postfilter",
            "no_group_aggregate_outputs",
            "selected_output_aliases_do_not_create_satisfying_scope",
        ),
        "no_group_result_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "global aggregate post-filtering requires separate authorization",
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "bounded_result_predicate",
            "unselected_raw_input_fields",
            "selected_output_names_required",
        ),
        "grouped_result_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "ROW",
            "no_result_type_constraint",
            "aggregate_dependent_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "input_order",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "GROUP",
            "no_result_type_constraint",
            "non_bare_or_unselected_grouped_order_expression",
            "grouped_input_or_unselected_outputs",
            "selected_output_names_required",
        ),
        "grouped_result_order",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "broad grouped result ordering requires separate authorization",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_contexts, name))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    helper = cast(Any, capability_contexts.stage_clause_lookup_inputs)
    facts, complete, reason = helper(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _assert_evidence_shape(fact: CapabilityFact) -> None:
    assert len(fact.evidence) == len(set(fact.evidence))
    assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
    order = {source: index for index, source in enumerate(CapabilityEvidenceSource)}
    positions = [order[entry.source] for entry in fact.evidence]
    assert positions == sorted(positions)
    backends = [
        entry
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    ]
    assert [entry.dialect for entry in backends] in (
        [],
        ["postgresql", "mysql"],
    )
    assert all(entry.extension is None for entry in fact.evidence)


def test_private_module_api_and_dependency_shape_is_exact() -> None:
    assert capability_contexts.__all__ == ()
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assert not any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)) for node in tree.body
    )
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports == {
        "__future__",
        "collections.abc",
        "pietto.semantic.capability_facts",
    }
    source = _read(SOURCE_PATH)
    assert "capability_lookup" not in source
    assert "open(" not in source
    assert "getenv" not in source


def test_freezer_and_combined_fact_order_are_exact() -> None:
    stage = _facts("_EXPRESSION_STAGE_FACTS")
    clause = _facts("_CLAUSE_CAPABILITY_FACTS")
    combined = _facts("_CAPABILITY_CONTEXT_FACTS")
    assert combined == stage + clause
    freezer = cast(Any, getattr(capability_contexts, "_freeze_contexts"))
    with pytest.raises(ValueError, match="duplicate"):
        freezer((stage[0], stage[0]))
    distinct = replace(stage[0], support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freezer((stage[0], distinct)) == (stage[0], distinct)


def test_fact_family_ownership_and_aggregate_window_separation_are_exact() -> None:
    combined = _facts("_CAPABILITY_CONTEXT_FACTS")
    assert len(combined) == len(set(combined)) == 18
    assert {fact.key.domain for fact in combined} == {
        CapabilityDomain.EXPRESSION_STAGE,
        CapabilityDomain.CLAUSE,
    }
    assert not any("WINDOW" in fact.key.operands for fact in combined)
    assert not any(fact.key.domain is CapabilityDomain.AGGREGATE for fact in combined)


def test_backend_and_project_evidence_remain_non_authoritative() -> None:
    for fact in _facts("_CAPABILITY_CONTEXT_FACTS"):
        sources = tuple(entry.source for entry in fact.evidence)
        if CapabilityEvidenceSource.BACKEND in sources:
            assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in sources
            assert sources.index(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE
            ) < sources.index(CapabilityEvidenceSource.BACKEND)
        if CapabilityEvidenceSource.PROJECT in sources:
            assert sources[0] is CapabilityEvidenceSource.GRAMMAR_AST
            assert sources.index(CapabilityEvidenceSource.PROJECT) > sources.index(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE
            )


def test_no_existing_consumer_or_public_export_is_added() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_contexts" not in source
        assert "stage_clause_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_contexts" in preservation_source
    assert "stage_clause_lookup_inputs" in preservation_source
    assert "capability_contexts" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_contexts" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_prior_slice4_and_slice5_fact_counts_are_unchanged() -> None:
    inventory = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_inventory, "_CAPABILITY_FACTS"),
    )
    signatures = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_signatures, "_CAPABILITY_SIGNATURE_FACTS"),
    )
    assert len(inventory) == len(set(inventory)) == 41
    assert len(signatures) == len(set(signatures)) == 39


def test_expression_stage_fact_inventory_is_exact() -> None:
    facts = _facts("_EXPRESSION_STAGE_FACTS")
    assert (
        tuple((fact.key.subject, fact.key.operands[0]) for fact in facts)
        == STAGE_EXPECTED
    )
    for fact in facts:
        assert fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        assert fact.key.operation == "observed_stage"
        assert fact.key.context == "expression"
        assert fact.key.dialect is fact.key.extension is None
        assert fact.support is CapabilitySupport.SUPPORTED
        assert fact.disposition.kind is CapabilityDispositionKind.NONE


@pytest.mark.parametrize(
    "index", range(7), ids=("ES01", "ES02", "ES03", "ES04", "ES05", "ES06", "ES07")
)
def test_expression_stage_evidence_order_and_paths_are_exact(index: int) -> None:
    _assert_evidence_shape(_facts("_EXPRESSION_STAGE_FACTS")[index])


def test_expression_ast_and_context_coverage_map_is_exact() -> None:
    facts = _facts("_EXPRESSION_STAGE_FACTS")
    assert {fact.key.subject for fact in facts} == {
        subject for subject, _ in STAGE_EXPECTED
    }
    assert {fact.key.operands[0] for fact in facts} == {
        "CONSTANT",
        "ROW",
        "GROUP",
        "UNKNOWN",
    }
    assert not any("WINDOW" in fact.key.operands for fact in facts)
    assert all(fact.key.context == "expression" for fact in facts)


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4, 5, 6),
    ids=("ES01", "ES02", "ES03", "ES04", "ES05", "ES06", "ES07"),
)
def test_expression_stage_lookup_found_is_exact(index: int) -> None:
    fact = _facts("_EXPRESSION_STAGE_FACTS")[index]
    result = _lookup(fact.key)
    assert result == Found(fact)


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="resolved_row_reference",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="aggregate_dependent_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="unresolved_reference_expression",
            operation="observed_stage",
            operands=("GROUP",),
            context="expression",
        ),
    ),
    ids=("literal-row", "resolved-constant", "aggregate-row", "unresolved-group"),
)
def test_expression_stage_complete_wrong_claim_is_absent(key: CapabilityKey) -> None:
    assert isinstance(_lookup(key), Absent)


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("WINDOW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="future_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="select",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
            dialect="mysql",
            extension="vendor",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT", "ROW"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="classify",
            operands=("CONSTANT",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.CONVERSION,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
        ),
    ),
    ids=(
        "window",
        "future-subject",
        "wrong-context",
        "dialect",
        "extension",
        "malformed-operands",
        "wrong-operation",
        "other-domain",
    ),
)
def test_expression_stage_incomplete_question_is_unknown(key: CapabilityKey) -> None:
    result = _lookup(key)
    assert result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_stage_type_nullability_and_three_valued_truth_are_orthogonal() -> None:
    literal = _facts("_EXPRESSION_STAGE_FACTS")[0]
    unresolved = _facts("_EXPRESSION_STAGE_FACTS")[-1]
    assert literal.key.operands == ("CONSTANT",)
    assert any(
        entry.reason is CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE
        for entry in literal.evidence
    )
    assert unresolved.key.operands == ("UNKNOWN",)
    assert isinstance(_lookup(unresolved.key), Found)
    assert any(
        entry.reason is CapabilityReasonCode.UNRESOLVED_EXPRESSION
        for entry in unresolved.evidence
    )


def test_expression_stage_injected_conflict_preserves_order() -> None:
    fact = _facts("_EXPRESSION_STAGE_FACTS")[0]
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    facts, complete, reason = cast(Any, capability_contexts.stage_clause_lookup_inputs)(
        fact.key
    )
    result = lookup_capability(
        fact.key,
        (*facts, distinct),
        domain_complete=complete,
        unknown_reason=reason,
    )
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, distinct),
    )


def test_clause_fact_inventory_order_and_combined_tuple_are_exact() -> None:
    facts = _facts("_CLAUSE_CAPABILITY_FACTS")
    observed = tuple(
        (
            fact.key.subject,
            fact.key.operands,
            fact.key.context,
            fact.support,
            fact.disposition.kind,
            fact.disposition.owner,
            fact.disposition.reason,
        )
        for fact in facts
    )
    assert observed == CLAUSE_EXPECTED
    assert (
        _facts("_CAPABILITY_CONTEXT_FACTS") == _facts("_EXPRESSION_STAGE_FACTS") + facts
    )


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4),
    ids=("C01", "C02", "C03", "C04", "C05"),
)
def test_supported_clause_fact_is_exact(index: int) -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[index]
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert _lookup(fact.key) == Found(fact)


@pytest.mark.parametrize(
    "index",
    (5, 6, 7, 8, 9, 10),
    ids=("C06", "C07", "C08", "C09", "C10", "C11"),
)
def test_unsupported_clause_fact_is_exact(index: int) -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[index]
    assert fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    if index in {6, 7, 10}:
        assert fact.disposition.kind is CapabilityDispositionKind.DEFERRED
        assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
    else:
        assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert _lookup(fact.key) == Found(fact)


@pytest.mark.parametrize(
    "index",
    range(11),
    ids=("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11"),
)
def test_clause_evidence_order_and_paths_are_exact(index: int) -> None:
    _assert_evidence_shape(_facts("_CLAUSE_CAPABILITY_FACTS")[index])


def test_clause_completeness_and_absence_are_exact() -> None:
    absent_key = CapabilityKey(
        CapabilityDomain.CLAUSE,
        subject="where",
        operation="admit",
        operands=(
            "ROW",
            "Bool",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        context="pre_group_filter",
    )
    assert isinstance(_lookup(absent_key), Absent)
    malformed = replace(absent_key, operands=("ROW",))
    assert _lookup(malformed) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_clause_lookup_four_results_are_exact() -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[0]
    assert _lookup(fact.key) == Found(fact)
    absent_key = replace(
        fact.key,
        operands=(
            "ROW",
            "Bool",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
    )
    assert isinstance(_lookup(absent_key), Absent)
    unknown_key = replace(
        fact.key,
        operands=(
            "WINDOW",
            "Bool_when_known",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
    )
    assert _lookup(unknown_key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    facts, complete, reason = cast(Any, capability_contexts.stage_clause_lookup_inputs)(
        fact.key
    )
    conflict = lookup_capability(
        fact.key,
        (*facts, distinct),
        domain_complete=complete,
        unknown_reason=reason,
    )
    assert conflict == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, distinct),
    )


def test_clause_omissions_and_tensions_remain_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="select",
            operation="admit",
            context="output",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE, subject="let", operation="admit", context="binding"
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="limit",
            operation="admit",
            context="static",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "WINDOW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=("ROW",),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "future_shape",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="project_pre_group_filter",
        ),
    )
    assert all(
        _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED) for key in keys
    )


# Phase 53 Slice 13 reader migration.
