from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.semantic.capability_lookup as capability_lookup
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
SOURCE_REL = "src/pietto/semantic/capability_lookup.py"
FACTS_REL = "src/pietto/semantic/capability_facts.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
WINDOW_REL = "src/pietto/semantic/capability_windows.py"
PROFILE_REL = "src/pietto/semantic/capability_profiles.py"
SELECTOR_REL = "src/pietto/semantic/extension_signature_requirements.py"
EXTENSION_PROVIDER_REL = "src/pietto/_project/extension_signature_provider.py"
EXTENSION_INSPECTION_REL = "src/pietto/_project/extension_catalog_inspection.py"
PROVIDER_REL = "src/pietto/semantic/capability_providers.py"
COMPOSITION_REL = "src/pietto/semantic/capability_composition.py"
CHECKING_REL = "src/pietto/_project/capability_checking.py"
INSPECTION_REL = "src/pietto/_project/capability_inspection.py"
SELF_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _key(
    *,
    subject: str = "Int",
    dialect: str | None = None,
    extension: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        dialect=dialect,
        extension=extension,
    )


def _evidence(
    *,
    reference: str = "exact-current fact",
    reason: CapabilityReasonCode | None = None,
    dialect: str | None = None,
    backend: str | None = None,
    extension: str | None = None,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        CapabilityEvidenceSource.TEST,
        SELF_REL,
        reference,
        reason,
        dialect=dialect,
        backend=backend,
        extension=extension,
    )


def _fact(
    *,
    key: CapabilityKey | None = None,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        _key() if key is None else key,
        support,
        CapabilityDisposition(CapabilityDispositionKind.NONE)
        if disposition is None
        else disposition,
        (_evidence(),) if evidence is None else evidence,
    )


def test_lookup_result_carriers_are_exact_frozen_slotted_shapes() -> None:
    fact = _fact()
    assert capability_lookup.__all__ == ()
    assert tuple(field.name for field in fields(Found)) == ("fact",)
    assert tuple(field.name for field in fields(Absent)) == ("key", "reason")
    assert tuple(field.name for field in fields(Unknown)) == ("reason",)
    assert tuple(field.name for field in fields(Conflict)) == ("reason", "evidence")
    for carrier in (Found, Absent, Unknown, Conflict):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__
    with pytest.raises(FrozenInstanceError):
        setattr(Found(fact), "fact", fact)


def test_private_alias_and_import_surfaces_remain_unexported() -> None:
    source_tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    aliases = [node for node in source_tree.body if isinstance(node, ast.TypeAlias)]
    assert [node.name.id for node in aliases if isinstance(node.name, ast.Name)] == [
        "CapabilityLookupResult"
    ]
    assert "capability_lookup" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_lookup" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_lookup_uses_only_exact_key_equality_without_fallback() -> None:
    target = _key(subject=" Int ")
    exact = _fact(key=target)
    normalized_only = _fact(key=_key(subject="Int"))
    unrelated_dialect = _fact(key=_key(subject=" Int ", dialect="postgresql"))
    result = lookup_capability(
        target,
        (normalized_only, unrelated_dialect, exact),
        domain_complete=True,
    )
    assert result == Found(exact)


def test_identical_duplicate_facts_are_idempotently_folded_in_first_position() -> None:
    fact = _fact()
    result = lookup_capability(
        fact.key,
        (fact, fact, _fact(key=_key(subject="Float")), fact),
        domain_complete=True,
    )
    assert result == Found(fact)


def test_equal_posture_but_different_evidence_is_a_stable_conflict() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    result = lookup_capability(first.key, (second, first), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (second, first),
    )


def test_complete_zero_match_is_absent_and_forbids_explicit_unknown_reason() -> None:
    key = _key()
    assert lookup_capability(key, (), domain_complete=True) == Absent(key)
    with pytest.raises(ValueError):
        lookup_capability(
            key,
            (),
            domain_complete=True,
            unknown_reason=CapabilityReasonCode.NOT_EVIDENCED,
        )


def test_incomplete_zero_match_defaults_to_not_evidenced_unknown() -> None:
    assert lookup_capability(_key(), (), domain_complete=False) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


def test_incomplete_domains_preserve_actual_found_and_conflict_evidence() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    assert lookup_capability(first.key, (first,), domain_complete=False) == Found(first)
    assert lookup_capability(
        first.key, (first, second), domain_complete=False
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, second))


def test_all_facts_are_frozen_and_validated_before_any_match_is_returned() -> None:
    fact = _fact()
    yielded: list[object] = []

    def facts() -> Any:
        yielded.append(fact)
        yield fact
        malformed = object()
        yielded.append(malformed)
        yield malformed

    with pytest.raises(ValueError):
        lookup_capability(fact.key, facts(), domain_complete=True)
    assert len(yielded) == 2


def test_lookup_and_carrier_structural_errors_are_value_errors() -> None:
    fact = _fact()
    invalid_calls = (
        lambda: Found(cast(Any, object())),
        lambda: Absent(cast(Any, object())),
        lambda: Absent(fact.key, cast(Any, CapabilityReasonCode.NOT_EVIDENCED)),
        lambda: lookup_capability(cast(Any, object()), (), domain_complete=True),
        lambda: lookup_capability(fact.key, cast(Any, "facts"), domain_complete=True),
        lambda: lookup_capability(fact.key, cast(Any, None), domain_complete=True),
        lambda: lookup_capability(fact.key, (), domain_complete=cast(Any, 1)),
        lambda: lookup_capability(
            fact.key,
            (),
            domain_complete=False,
            unknown_reason=cast(Any, "not_evidenced"),
        ),
        lambda: lookup_capability(
            fact.key,
            (),
            domain_complete=False,
            unknown_reason=CapabilityReasonCode.NO_CATALOG_ENTRY,
        ),
    )
    for call in invalid_calls:
        with pytest.raises(ValueError):
            call()
    with pytest.raises(TypeError):
        cast(Any, lookup_capability)()


def test_conflict_requires_ordered_distinct_same_key_exact_facts() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    other_key = _fact(key=_key(subject="Float"))
    conflict = Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        cast(Any, [second, first]),
    )
    assert conflict.evidence == (second, first)
    invalid = (
        (CapabilityReasonCode.NOT_EVIDENCED, (first, second)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first,)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, first)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, other_key)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, cast(Any, "facts")),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, cast(Any, (first, object()))),
    )
    for reason, evidence in invalid:
        with pytest.raises(ValueError):
            Conflict(reason, cast(Any, evidence))


def test_lookup_is_pure_deterministic_and_does_not_mutate_input() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    facts = [first, second, first]
    before = list(facts)
    one = lookup_capability(first.key, facts, domain_complete=False)
    two = lookup_capability(first.key, tuple(facts), domain_complete=False)
    assert one == two
    assert facts == before


def test_lookup_and_inventory_are_only_private_fact_consumers_without_registry() -> (
    None
):
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert classes == {"Found", "Absent", "Unknown", "Conflict"}
    assert functions == {"lookup_capability"}
    assert not any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith("Capability")
        for node in tree.body
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if (
            path
            in {
                SOURCE_PATH,
                REPO_ROOT / FACTS_REL,
                REPO_ROOT / INVENTORY_REL,
                REPO_ROOT / SIGNATURE_REL,
                REPO_ROOT / CONTEXT_REL,
                REPO_ROOT / AGGREGATE_REL,
                REPO_ROOT / WINDOW_REL,
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
        source = _read(path)
        assert "semantic.capability_facts" not in source
        assert "CapabilityFact" not in source
        source_tree = ast.parse(source, filename=str(path))
        capability_key_identifiers = (
            {node.id for node in ast.walk(source_tree) if isinstance(node, ast.Name)}
            | {
                node.attr
                for node in ast.walk(source_tree)
                if isinstance(node, ast.Attribute)
            }
            | {
                node.name.rsplit(".", 1)[-1]
                for node in ast.walk(source_tree)
                if isinstance(node, ast.alias)
            }
        )
        assert "CapabilityKey" not in capability_key_identifiers
    signature_source = _read(REPO_ROOT / SIGNATURE_REL)
    assert "semantic.capability_facts" in signature_source
    assert "CapabilityFact" in signature_source
    assert "CapabilityKey" in signature_source
    selector_source = _read(REPO_ROOT / SELECTOR_REL)
    assert "semantic.capability_facts" in selector_source
    assert "CapabilityDomain" in selector_source
    assert "CapabilityFact" not in selector_source
    inspection_source = _read(REPO_ROOT / INSPECTION_REL)
    assert "semantic.capability_facts" in inspection_source
    assert "CapabilityFact" in inspection_source
    assert "CapabilityKey" in inspection_source
    extension_inspection_source = _read(REPO_ROOT / EXTENSION_INSPECTION_REL)
    assert "semantic.capability_lookup" in extension_inspection_source
    assert "lookup_capability" in extension_inspection_source
    assert "CapabilityFact" in extension_inspection_source
    preservation_source = _read(
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    assert "semantic.capability_facts" in preservation_source
    assert "__all__: tuple[str, ...] = ()" in preservation_source


def test_zero_match_uses_only_the_explicit_incomplete_domain_reason() -> None:
    reason = CapabilityReasonCode.UNKNOWN_NULLABILITY
    assert lookup_capability(
        _key(), (), domain_complete=False, unknown_reason=reason
    ) == Unknown(reason)


@pytest.mark.parametrize(
    "reason",
    (
        CapabilityReasonCode.NOT_EVIDENCED,
        CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        CapabilityReasonCode.UNRESOLVED_EXPRESSION,
        CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
        CapabilityReasonCode.UNKNOWN_NULLABILITY,
        CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
        CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED,
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_AMBIGUOUS,
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_CONFLICT,
        CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH,
        CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE,
        CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED,
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE,
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_CONFLICT,
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE,
    ),
    ids=(
        "not-evidenced",
        "no-current-result-rule",
        "unresolved-expression",
        "null-literal-no-concrete-type",
        "unknown-nullability",
        "sql-three-valued-truth",
        "dialect-lowering-gap",
        "extension-catalog-undeclared",
        "extension-catalog-selection-ambiguous",
        "extension-catalog-selection-conflict",
        "extension-catalog-target-mismatch",
        "extension-catalog-not-provider-eligible",
        "extension-cataloged-unmodeled",
        "extension-catalog-completeness-incomplete",
        "extension-catalog-completeness-conflict",
        "extension-catalog-completeness-unavailable",
    ),
)
def test_unknown_accepts_each_non_absent_non_conflict_reason(
    reason: CapabilityReasonCode,
) -> None:
    assert Unknown(reason).reason is reason


@pytest.mark.parametrize(
    "reason",
    (
        CapabilityReasonCode.NO_CATALOG_ENTRY,
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
    ),
    ids=("absence-only", "conflict-only"),
)
def test_unknown_rejects_absence_and_conflict_only_reasons(
    reason: CapabilityReasonCode,
) -> None:
    with pytest.raises(ValueError):
        Unknown(reason)


@pytest.mark.parametrize(
    ("support", "disposition"),
    (
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED,
                "Phase 53",
                "owned later",
            ),
        ),
    ),
    ids=("support", "disposition"),
)
def test_support_or_disposition_differences_are_conflicts(
    support: CapabilitySupport,
    disposition: CapabilityDisposition,
) -> None:
    first = _fact()
    second = _fact(support=support, disposition=disposition)
    result = lookup_capability(first.key, (first, second), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (first, second),
    )


@pytest.mark.parametrize(
    ("first_evidence", "second_evidence"),
    (
        (
            _evidence(dialect="postgresql"),
            _evidence(dialect="mysql"),
        ),
        (
            _evidence(dialect="postgresql", backend="postgresql"),
            _evidence(dialect="postgresql", backend="private-mysql"),
        ),
        (
            _evidence(dialect="postgresql", extension="jsonb"),
            _evidence(dialect="postgresql", extension="pgvector"),
        ),
    ),
    ids=("dialect", "backend", "extension"),
)
def test_dialect_backend_or_extension_scope_differences_are_conflicts(
    first_evidence: CapabilityEvidence,
    second_evidence: CapabilityEvidence,
) -> None:
    first = _fact(evidence=(first_evidence,))
    second = _fact(evidence=(second_evidence,))
    result = lookup_capability(first.key, (first, second), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (first, second),
    )


# Phase 53 Slice 13 reader migration.
