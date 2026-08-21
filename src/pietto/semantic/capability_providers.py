"""Private canonical capability-provider inputs."""

from __future__ import annotations

from dataclasses import dataclass

from pietto.semantic.capability_aggregates import aggregate_lookup_inputs
from pietto.semantic.capability_contexts import stage_clause_lookup_inputs
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_inventory import inventory_lookup_inputs
from pietto.semantic.capability_signatures import signature_lookup_inputs
from pietto.semantic.capability_windows import window_lookup_inputs

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CanonicalCapabilityProviderInputs:
    """Exact ordered inputs for the existing capability lookup."""

    key: CapabilityKey
    facts: tuple[CapabilityFact, ...]
    domain_complete: bool
    unknown_reason: CapabilityReasonCode | None = None

    def __post_init__(self) -> None:
        if type(self.key) is not CapabilityKey:
            raise ValueError("canonical provider requires an exact capability key")
        if type(self.facts) is not tuple:
            raise ValueError("canonical provider requires an exact fact tuple")
        if any(type(fact) is not CapabilityFact for fact in self.facts):
            raise ValueError("canonical provider requires exact capability facts")
        if type(self.domain_complete) is not bool:
            raise ValueError("canonical provider requires exact completeness")
        if self.unknown_reason is not None:
            if type(self.unknown_reason) is not CapabilityReasonCode:
                raise ValueError("canonical provider requires an exact unknown reason")
            if self.unknown_reason in {
                CapabilityReasonCode.NO_CATALOG_ENTRY,
                CapabilityReasonCode.CONFLICTING_EVIDENCE,
            }:
                raise ValueError(
                    "canonical provider forbids an inadmissible unknown reason"
                )
        if self.domain_complete and self.unknown_reason is not None:
            raise ValueError(
                "complete canonical provider inputs forbid an unknown reason"
            )


def canonical_capability_provider_inputs(
    key: CapabilityKey,
) -> CanonicalCapabilityProviderInputs:
    """Select one existing provider by exact domain without fallback."""

    if type(key) is not CapabilityKey:
        raise ValueError("canonical provider requires an exact capability key")
    if key.domain in {
        CapabilityDomain.LOGICAL_TYPE,
        CapabilityDomain.LITERAL,
        CapabilityDomain.PARAMETER,
    }:
        facts, complete = inventory_lookup_inputs(key)
        reason = None
    elif key.domain in {
        CapabilityDomain.SCALAR_FUNCTION,
        CapabilityDomain.UNARY_OPERATOR,
        CapabilityDomain.BINARY_OPERATOR,
        CapabilityDomain.COMPARISON,
        CapabilityDomain.NULL_TEST,
    }:
        facts, complete, reason = signature_lookup_inputs(key)
    elif key.domain in {
        CapabilityDomain.EXPRESSION_STAGE,
        CapabilityDomain.CLAUSE,
    }:
        facts, complete, reason = stage_clause_lookup_inputs(key)
    elif key.domain is CapabilityDomain.AGGREGATE:
        facts, complete, reason = aggregate_lookup_inputs(key)
    elif key.domain is CapabilityDomain.WINDOW_FUNCTION:
        facts, complete, reason = window_lookup_inputs(key)
    else:
        facts, complete, reason = (), False, None
    return CanonicalCapabilityProviderInputs(key, facts, complete, reason)
