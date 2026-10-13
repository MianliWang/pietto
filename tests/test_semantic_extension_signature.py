from __future__ import annotations

from dataclasses import fields
import hashlib

import _pietto_capability_differential_vectors as vectors
import pietto._project.capability_pure_boundary as pure_boundary
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import Unknown, lookup_capability
from pietto.semantic.capability_profiles import CapabilityProfileTarget

EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _provider_families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        inventory._CAPABILITY_FACTS,
        signatures._CAPABILITY_SIGNATURE_FACTS,
        contexts._CAPABILITY_CONTEXT_FACTS,
        aggregates._AGGREGATE_CAPABILITY_FACTS,
        windows._WINDOW_CAPABILITY_FACTS,
    )


def _corpus_digest() -> str:
    rows: list[str] = []
    for vector in vectors.differential_vectors():
        outcome = pure_boundary.evaluate_capability_document(vector.document)
        matched = (
            outcome.status is vector.expected_status
            and outcome.record_position == vector.expected_record_position
            and outcome.field_position == vector.expected_field_position
            and outcome.canonical_bytes == vector.expected_bytes
        )
        record = outcome.record_position if outcome.record_position is not None else "-"
        field = outcome.field_position if outcome.field_position is not None else "-"
        rows.append(
            f"{vector.vector_id}:{outcome.status.value}:{record}:{field}:{matched}"
        )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def test_phase56_predecessor_and_extension_signature_posture_are_exact() -> None:
    families = _provider_families()
    facts = tuple(fact for family in families for fact in family)
    assert all(families)
    assert len(set(facts)) == len(facts)
    window_identities = (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
    )
    expected_window_inventory = tuple(
        (CapabilityDomain.WINDOW_FUNCTION, identity, operation, dialect)
        for operation, dialect in (
            ("signature", None),
            ("lowering", "postgresql"),
            ("lowering", "mysql"),
        )
        for identity in window_identities
    )
    assert (
        tuple(
            (fact.key.domain, fact.key.subject, fact.key.operation, fact.key.dialect)
            for fact in families[-1]
        )
        == expected_window_inventory
    )
    assert CapabilityDomain.EXTENSION_SIGNATURE.value == "extension_signature"
    assert not any(
        fact.key.domain is CapabilityDomain.EXTENSION_SIGNATURE for fact in facts
    )

    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="vector",
        operation="signature",
        dialect="postgresql",
        extension="pgvector",
    )
    provider = providers.canonical_capability_provider_inputs(key)
    assert provider.key is key
    assert provider.facts == ()
    assert provider.domain_complete is False
    assert provider.unknown_reason is None
    assert lookup_capability(
        key,
        provider.facts,
        domain_complete=provider.domain_complete,
        unknown_reason=provider.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)

    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert {"release", "backend"}.isdisjoint(
        field.name for field in fields(CapabilityKey)
    )
    assert tuple(field.name for field in fields(CapabilityProfileTarget)) == (
        "kind",
        "family",
        "release",
        "extension_identity",
        "extension_release",
    )
    assert "extension_signature" in pure_boundary._CAPABILITY_DOMAINS
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )

    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.CapabilityPureStatus.OK
    )
    assert corpus and accepted
    assert any(vector not in accepted for vector in corpus)
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST
