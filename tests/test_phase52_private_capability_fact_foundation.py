from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any, cast

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
import pietto.semantic.capability_facts as capability_facts
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


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
PROFILE_REL = "src/pietto/semantic/capability_profiles.py"
SELECTOR_REL = "src/pietto/semantic/extension_signature_requirements.py"
EXTENSION_PROVIDER_REL = "src/pietto/_project/extension_signature_provider.py"
EXTENSION_INSPECTION_REL = "src/pietto/_project/extension_catalog_inspection.py"
PROVIDER_REL = "src/pietto/semantic/capability_providers.py"
COMPOSITION_REL = "src/pietto/semantic/capability_composition.py"
CHECKING_REL = "src/pietto/_project/capability_checking.py"
INSPECTION_REL = "src/pietto/_project/capability_inspection.py"
SPEC_REL = (
    "docs/spec/"
    "phase52-private-capability-key-disposition-evidence-fact-foundation-v1.md"
)
SELF_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
LOOKUP_PATH = REPO_ROOT / LOOKUP_REL
INVENTORY_PATH = REPO_ROOT / INVENTORY_REL
SIGNATURE_PATH = REPO_ROOT / SIGNATURE_REL


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _runtime_source() -> str:
    return _read(SOURCE_PATH)


def _key() -> CapabilityKey:
    return CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")


def _evidence() -> CapabilityEvidence:
    return CapabilityEvidence(
        CapabilityEvidenceSource.SPEC,
        SPEC_REL,
        "Capability Key Contract",
    )


def _fact(
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        _key(),
        support,
        disposition
        if disposition is not None
        else CapabilityDisposition(CapabilityDispositionKind.NONE),
        evidence if evidence is not None else (_evidence(),),
    )


def test_private_module_owns_exact_frozen_slots_carrier_shapes() -> None:
    assert capability_facts.__all__ == ()
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert tuple(field.name for field in fields(CapabilityDisposition)) == (
        "kind",
        "owner",
        "reason",
    )
    assert tuple(field.name for field in fields(CapabilityEvidence)) == (
        "source",
        "source_path",
        "source_reference",
        "reason",
        "dialect",
        "backend",
        "extension",
    )
    assert tuple(field.name for field in fields(CapabilityFact)) == (
        "key",
        "support",
        "disposition",
        "evidence",
    )
    for carrier in (
        CapabilityKey,
        CapabilityDisposition,
        CapabilityEvidence,
        CapabilityFact,
    ):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__


def test_exact_enum_member_inventories_are_locked() -> None:
    assert [(item.name, item.value) for item in CapabilityDomain] == [
        ("LOGICAL_TYPE", "logical_type"),
        ("LITERAL", "literal"),
        ("PARAMETER", "parameter"),
        ("SCALAR_FUNCTION", "scalar_function"),
        ("UNARY_OPERATOR", "unary_operator"),
        ("BINARY_OPERATOR", "binary_operator"),
        ("COMPARISON", "comparison"),
        ("NULL_TEST", "null_test"),
        ("CLAUSE", "clause"),
        ("AGGREGATE", "aggregate"),
        ("WINDOW_FUNCTION", "window_function"),
        ("EXPRESSION_STAGE", "expression_stage"),
        ("CONVERSION", "conversion"),
        ("DIALECT_LOWERING", "dialect_lowering"),
        ("EXTENSION_SIGNATURE", "extension_signature"),
    ]
    assert [(item.name, item.value) for item in CapabilitySupport] == [
        ("SUPPORTED", "supported"),
        ("EXPLICITLY_UNSUPPORTED", "explicitly_unsupported"),
    ]
    assert [(item.name, item.value) for item in CapabilityDispositionKind] == [
        ("NONE", "none"),
        ("DEFERRED", "deferred"),
        ("OUT_OF_SCOPE", "out_of_scope"),
    ]
    assert [item.value for item in CapabilityEvidenceSource] == [
        "grammar_ast",
        "semantic_catalog",
        "semantic_procedure",
        "semantic_model",
        "ir",
        "backend",
        "project",
        "public",
        "roadmap",
        "test",
        "spec",
    ]


def test_capability_key_equality_hash_and_exact_text_identity_are_stable() -> None:
    first = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject=" Int ",
        operation=" + ",
        operands=cast(Any, (item for item in (" Float ", "Float"))),
        context=" select ",
    )
    second = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject=" Int ",
        operation=" + ",
        operands=(" Float ", "Float"),
        context=" select ",
    )
    assert first == second
    assert hash(first) == hash(second)
    assert first.subject == " Int "
    assert first.operation == " + "
    assert first.operands == (" Float ", "Float")
    assert first.context == " select "


def test_capability_key_field_types_operand_order_and_scope_invariants_fail_closed() -> (
    None
):
    invalid = (
        {"domain": cast(Any, "logical_type"), "subject": "Int"},
        {"domain": CapabilityDomain.LOGICAL_TYPE},
        {"domain": CapabilityDomain.LOGICAL_TYPE, "subject": ""},
        {"domain": CapabilityDomain.LOGICAL_TYPE, "subject": "  "},
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, "Float"),
        },
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, None),
        },
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, ("Float", "")),
        },
        {
            "domain": CapabilityDomain.EXTENSION_SIGNATURE,
            "operation": "vector",
            "extension": "pgvector",
        },
    )
    for arguments in invalid:
        with pytest.raises(ValueError):
            CapabilityKey(**cast(Any, arguments))

    ordered = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        operation="pair",
        operands=("Text", "Text"),
    )
    reversed_key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        operation="pair",
        operands=("Text", "Int"),
    )
    assert ordered.operands == ("Text", "Text")
    assert ordered != reversed_key


def test_none_disposition_requires_absent_owner_and_reason() -> None:
    disposition = CapabilityDisposition(CapabilityDispositionKind.NONE)
    assert disposition.owner is None
    assert disposition.reason is None
    for owner, reason in (("Phase 53", None), (None, "later"), ("Phase 53", "later")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.NONE, owner, reason)


def test_deferred_disposition_requires_exact_owner_and_reason() -> None:
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        " Phase 53 ",
        " explicit owner ",
    )
    assert disposition.owner == " Phase 53 "
    assert disposition.reason == " explicit owner "
    for owner, reason in ((None, None), ("Phase 53", None), (None, "later")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.DEFERRED, owner, reason)


def test_out_of_scope_disposition_requires_exact_owner_and_reason() -> None:
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.OUT_OF_SCOPE,
        " runtime ",
        " database-owned ",
    )
    assert disposition.owner == " runtime "
    assert disposition.reason == " database-owned "
    for owner, reason in ((None, None), ("runtime", None), (None, "owned")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.OUT_OF_SCOPE, owner, reason)


def test_disposition_rejects_blank_text_without_normalizing_valid_text() -> None:
    for owner, reason in (
        ("", "reason"),
        (" ", "reason"),
        ("owner", ""),
        ("owner", " "),
    ):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.DEFERRED, owner, reason)
    with pytest.raises(ValueError):
        CapabilityDisposition(cast(Any, "deferred"), "owner", "reason")


def test_evidence_carrier_fields_provenance_and_scope_invariants_are_exact() -> None:
    evidence = CapabilityEvidence(
        CapabilityEvidenceSource.BACKEND,
        " src/pietto/sql/mysql/emitter.py ",
        " render_expression ",
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
        dialect=" mysql ",
        backend=" private-mysql ",
        extension=" json ",
    )
    assert evidence.source_path == " src/pietto/sql/mysql/emitter.py "
    assert evidence.source_reference == " render_expression "
    assert evidence.dialect == " mysql "
    assert evidence.backend == " private-mysql "
    assert evidence.extension == " json "
    invalid = (
        (cast(Any, "backend"), "path", "ref", None, None),
        (CapabilityEvidenceSource.BACKEND, "", "ref", None, None),
        (CapabilityEvidenceSource.BACKEND, "path", " ", None, None),
        (CapabilityEvidenceSource.BACKEND, "path", "ref", cast(Any, "gap"), None),
        (CapabilityEvidenceSource.BACKEND, "path", "ref", None, "pgvector"),
    )
    for source, path, reference, reason, extension in invalid:
        with pytest.raises(ValueError):
            CapabilityEvidence(
                source,
                path,
                reference,
                reason,
                extension=extension,
            )


def test_capability_fact_evidence_is_nonempty_ordered_immutable_and_unique() -> None:
    first = _evidence()
    second = CapabilityEvidence(
        CapabilityEvidenceSource.TEST,
        SELF_REL,
        "test_capability_fact_evidence_is_nonempty_ordered_immutable_and_unique",
    )
    fact = _fact(evidence=cast(Any, [first, second]))
    assert fact.evidence == (first, second)
    with pytest.raises(ValueError):
        _fact(evidence=())
    with pytest.raises(ValueError):
        _fact(evidence=cast(Any, (first, first)))
    with pytest.raises(ValueError):
        _fact(evidence=cast(Any, "not evidence"))


def test_capability_fact_composition_is_frozen_hashable_and_has_no_lookup_state() -> (
    None
):
    fact = _fact()
    assert hash(fact) == hash(_fact())
    assert tuple(field.name for field in fields(fact)) == (
        "key",
        "support",
        "disposition",
        "evidence",
    )
    with pytest.raises(FrozenInstanceError):
        setattr(fact, "support", CapabilitySupport.EXPLICITLY_UNSUPPORTED)


@pytest.mark.parametrize(
    ("support", "disposition"),
    (
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED, "Phase 53", "later"
            ),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.OUT_OF_SCOPE, "runtime", "owned"
            ),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED, "Phase 53", "later"
            ),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.OUT_OF_SCOPE, "runtime", "owned"
            ),
        ),
    ),
    ids=(
        "supported-none",
        "supported-deferred",
        "supported-out-of-scope",
        "explicitly-unsupported-none",
        "explicitly-unsupported-deferred",
        "explicitly-unsupported-out-of-scope",
    ),
)
def test_support_and_disposition_are_orthogonal(
    support: CapabilitySupport,
    disposition: CapabilityDisposition,
) -> None:
    fact = _fact(support=support, disposition=disposition)
    assert fact.support is support
    assert fact.disposition is disposition


def test_reason_codes_are_exact_private_non_diagnostic_vocabulary() -> None:
    assert [(item.name, item.value) for item in CapabilityReasonCode] == [
        ("NO_CATALOG_ENTRY", "no_catalog_entry"),
        ("NOT_EVIDENCED", "not_evidenced"),
        ("NO_CURRENT_RESULT_RULE", "no_current_result_rule"),
        ("UNRESOLVED_EXPRESSION", "unresolved_expression"),
        ("NULL_LITERAL_NO_CONCRETE_TYPE", "null_literal_no_concrete_type"),
        ("UNKNOWN_NULLABILITY", "unknown_nullability"),
        ("SQL_THREE_VALUED_TRUTH", "sql_three_valued_truth"),
        ("DIALECT_LOWERING_GAP", "dialect_lowering_gap"),
        ("CONFLICTING_EVIDENCE", "conflicting_evidence"),
        ("EXTENSION_CATALOG_UNDECLARED", "extension_catalog_undeclared"),
        (
            "EXTENSION_CATALOG_SELECTION_AMBIGUOUS",
            "extension_catalog_selection_ambiguous",
        ),
        (
            "EXTENSION_CATALOG_SELECTION_CONFLICT",
            "extension_catalog_selection_conflict",
        ),
        (
            "EXTENSION_CATALOG_TARGET_MISMATCH",
            "extension_catalog_target_mismatch",
        ),
        (
            "EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE",
            "extension_catalog_not_provider_eligible",
        ),
        ("EXTENSION_CATALOGED_UNMODELED", "extension_cataloged_unmodeled"),
        (
            "EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE",
            "extension_catalog_completeness_incomplete",
        ),
        (
            "EXTENSION_CATALOG_COMPLETENESS_CONFLICT",
            "extension_catalog_completeness_conflict",
        ),
        (
            "EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE",
            "extension_catalog_completeness_unavailable",
        ),
    ]
    assert all(not item.value.startswith("PIE-") for item in CapabilityReasonCode)


def test_slice2_has_no_lookup_result_carriers_registry_or_populated_facts() -> None:
    tree = ast.parse(_runtime_source(), filename=SOURCE_REL)
    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert class_names == {
        "CapabilityDomain",
        "CapabilitySupport",
        "CapabilityDispositionKind",
        "CapabilityEvidenceSource",
        "CapabilityReasonCode",
        "CapabilityKey",
        "CapabilityDisposition",
        "CapabilityEvidence",
        "CapabilityFact",
    }
    assert class_names.isdisjoint(
        {"Found", "Absent", "Unknown", "Conflict", "CapabilityLookupResult"}
    )
    function_names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert function_names == {
        "_require_nonblank_text",
        "_require_optional_nonblank_text",
    }
    assert not any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith("Capability")
        for node in tree.body
    )


def test_private_module_has_no_public_compiler_project_or_serializer_consumers() -> (
    None
):
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if (
            path
            in {
                SOURCE_PATH,
                LOOKUP_PATH,
                INVENTORY_PATH,
                SIGNATURE_PATH,
                REPO_ROOT / CONTEXT_REL,
                REPO_ROOT / AGGREGATE_REL,
                REPO_ROOT / "src/pietto/semantic/capability_windows.py",
                REPO_ROOT / PROFILE_REL,
                REPO_ROOT / SELECTOR_REL,
                REPO_ROOT / EXTENSION_PROVIDER_REL,
                REPO_ROOT / EXTENSION_INSPECTION_REL,
                REPO_ROOT / PROVIDER_REL,
                REPO_ROOT / COMPOSITION_REL,
                REPO_ROOT / CHECKING_REL,
                REPO_ROOT / INSPECTION_REL,
                REPO_ROOT / "src/pietto/_project/config.py",
                REPO_ROOT / "src/pietto/_project/model.py",
                REPO_ROOT / "src/pietto/_project/package_manifest.py",
                REPO_ROOT / "src/pietto/_project/project_capability_environment.py",
                REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py",
                REPO_ROOT
                / "src/pietto/_project_explain/package_requirement_projection.py",
                REPO_ROOT
                / "src/pietto/_project_explain/compatibility_matrix_projection.py",
                REPO_ROOT / "src/pietto/_project_explain/json_v1.py",
                REPO_ROOT / "src/pietto/_project_explain/runtime_builder.py",
            }
            or "generated" in path.parts
        ):
            continue
        facts = REPOSITORY_FACTS.python(path)
        source = facts.text
        assert "semantic.capability_facts" not in source
        assert "CapabilityFact" not in source
        assert "CapabilityKey" not in facts.identifiers
    assert (
        "capability_facts"
        not in REPOSITORY_FACTS.python(
            REPO_ROOT / "src/pietto/semantic/__init__.py"
        ).text
    )
    assert (
        "capability_facts"
        not in REPOSITORY_FACTS.python(REPO_ROOT / "src/pietto/__init__.py").text
    )
    lookup_source = REPOSITORY_FACTS.python(LOOKUP_PATH).text
    assert "semantic.capability_facts" in lookup_source
    assert "CapabilityFact" in lookup_source
    assert "CapabilityKey" in lookup_source
    inventory_source = REPOSITORY_FACTS.python(INVENTORY_PATH).text
    assert "semantic.capability_facts" in inventory_source
    assert "CapabilityFact" in inventory_source
    assert "CapabilityKey" in inventory_source
    signature_source = REPOSITORY_FACTS.python(SIGNATURE_PATH).text
    assert "semantic.capability_facts" in signature_source
    assert "CapabilityFact" in signature_source
    selector_source = REPOSITORY_FACTS.python(REPO_ROOT / SELECTOR_REL).text
    assert "semantic.capability_facts" in selector_source
    assert "CapabilityDomain" in selector_source
    assert "CapabilityFact" not in selector_source
    provider_source = REPOSITORY_FACTS.python(REPO_ROOT / PROVIDER_REL).text
    assert "semantic.capability_facts" in provider_source
    assert "CapabilityFact" in provider_source
    assert "CapabilityKey" in provider_source
    composition_source = REPOSITORY_FACTS.python(REPO_ROOT / COMPOSITION_REL).text
    assert "semantic.capability_facts" in composition_source
    assert "CapabilityFact" in composition_source
    checking_source = REPOSITORY_FACTS.python(REPO_ROOT / CHECKING_REL).text
    assert "semantic.capability_facts" in checking_source
    assert "CapabilitySupport" in checking_source
    inspection_source = REPOSITORY_FACTS.python(REPO_ROOT / INSPECTION_REL).text
    assert "semantic.capability_facts" in inspection_source
    assert "CapabilityFact" in inspection_source
    assert "CapabilityKey" in inspection_source
    extension_inspection_source = REPOSITORY_FACTS.python(
        REPO_ROOT / EXTENSION_INSPECTION_REL
    ).text
    assert "semantic.capability_facts" in extension_inspection_source
    assert "CapabilityFact" in extension_inspection_source
    assert "CapabilityKey" in extension_inspection_source
    preservation_source = REPOSITORY_FACTS.python(
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    ).text
    assert "semantic.capability_facts" in preservation_source
    assert "__all__: tuple[str, ...] = ()" in preservation_source
    assert "CapabilityKey" in signature_source
