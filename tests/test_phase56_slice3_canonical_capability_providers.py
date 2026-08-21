from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from typing import Any, cast

import pytest

import pietto
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as capability_aggregates
import pietto.semantic.capability_contexts as capability_contexts
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as capability_signatures
import pietto.semantic.capability_windows as capability_windows
from pietto._project import module_semantic_fact_preservation as preservation
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)
from pietto.semantic.capability_providers import (
    CanonicalCapabilityProviderInputs,
    canonical_capability_provider_inputs,
)


type _ProviderTuple = tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]
type _ProviderHelper = Callable[[CapabilityKey], _ProviderTuple]


def _inventory_inputs(key: CapabilityKey) -> _ProviderTuple:
    facts, complete = capability_inventory.inventory_lookup_inputs(key)
    return facts, complete, None


_FAMILIES: tuple[tuple[tuple[CapabilityFact, ...], _ProviderHelper], ...] = (
    (capability_inventory._CAPABILITY_FACTS, _inventory_inputs),
    (
        capability_signatures._CAPABILITY_SIGNATURE_FACTS,
        capability_signatures.signature_lookup_inputs,
    ),
    (
        capability_contexts._CAPABILITY_CONTEXT_FACTS,
        capability_contexts.stage_clause_lookup_inputs,
    ),
    (
        capability_aggregates._AGGREGATE_CAPABILITY_FACTS,
        capability_aggregates.aggregate_lookup_inputs,
    ),
    (
        capability_windows._WINDOW_CAPABILITY_FACTS,
        capability_windows.window_lookup_inputs,
    ),
)


def _all_facts() -> tuple[CapabilityFact, ...]:
    return tuple(fact for family, _helper in _FAMILIES for fact in family)


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    inputs = canonical_capability_provider_inputs(key)
    return lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    )


@pytest.mark.parametrize(("family", "helper"), _FAMILIES)
def test_every_current_fact_key_matches_its_existing_family_provider(
    family: tuple[CapabilityFact, ...],
    helper: _ProviderHelper,
) -> None:
    before = tuple(family)
    for fact in family:
        expected_facts, expected_complete, expected_reason = helper(fact.key)
        actual = canonical_capability_provider_inputs(fact.key)
        assert actual.key is fact.key
        assert actual.facts == expected_facts
        assert actual.domain_complete is expected_complete
        assert actual.unknown_reason is expected_reason
    assert family == before


def test_fact_counts_order_found_and_conflict_results_are_unchanged() -> None:
    facts = _all_facts()
    counts = Counter(fact.key for fact in facts)

    assert (len(facts), len(counts), len(set(facts))) == (191, 190, 191)
    for key in counts:
        expected = tuple(fact for fact in facts if fact.key == key)
        result = _lookup(key)
        if len(expected) == 1:
            assert isinstance(result, Found)
            assert result.fact is expected[0]
        else:
            assert len(expected) == 2
            assert isinstance(result, Conflict)
            assert result.evidence == expected


def test_complete_zero_match_and_malformed_scope_remain_absent_and_unknown() -> None:
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    malformed_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="future_operation",
        context="builtin_registry",
    )

    assert _lookup(absent_key) == Absent(absent_key)
    assert _lookup(malformed_key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


@pytest.mark.parametrize(
    ("key", "reason"),
    (
        (
            CapabilityKey(
                CapabilityDomain.BINARY_OPERATOR,
                subject="Int",
                operation="/",
                operands=("Int", "Int", "unknown"),
                context="expression",
            ),
            CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        ),
        (
            CapabilityKey(
                CapabilityDomain.SCALAR_FUNCTION,
                subject="Text",
                operation="matches",
                operands=("Text", "Bool", "unknown"),
                context="expression",
                dialect="mysql",
            ),
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        ),
        *(
            (
                CapabilityKey(
                    CapabilityDomain.COMPARISON,
                    subject="Expression",
                    operation="like",
                    operands=("Expression", "Bool", "unknown"),
                    context="expression",
                    dialect=dialect,
                ),
                CapabilityReasonCode.DIALECT_LOWERING_GAP,
            )
            for dialect in ("postgresql", "mysql")
        ),
    ),
)
def test_bounded_unknown_reasons_remain_exact(
    key: CapabilityKey,
    reason: CapabilityReasonCode,
) -> None:
    inputs = canonical_capability_provider_inputs(key)
    assert inputs.domain_complete is False
    assert inputs.unknown_reason is reason
    assert _lookup(key) == Unknown(reason)


@pytest.mark.parametrize(
    "domain",
    (
        CapabilityDomain.CONVERSION,
        CapabilityDomain.DIALECT_LOWERING,
        CapabilityDomain.EXTENSION_SIGNATURE,
    ),
)
def test_unowned_domains_remain_incomplete_unknown_and_never_absent(
    domain: CapabilityDomain,
) -> None:
    key = CapabilityKey(domain, subject="future", operation="lookup")
    inputs = canonical_capability_provider_inputs(key)

    assert inputs.key is key
    assert inputs.facts == ()
    assert inputs.domain_complete is False
    assert inputs.unknown_reason is None
    assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert not isinstance(_lookup(key), Absent)


def test_incomplete_selected_provider_stops_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[CapabilityKey] = []

    def selected(key: CapabilityKey) -> tuple[tuple[CapabilityFact, ...], bool]:
        calls.append(key)
        return (), False

    def forbidden(_key: CapabilityKey) -> Any:
        raise AssertionError("canonical provider attempted fallback")

    monkeypatch.setattr(providers, "inventory_lookup_inputs", selected)
    for name in (
        "signature_lookup_inputs",
        "stage_clause_lookup_inputs",
        "aggregate_lookup_inputs",
        "window_lookup_inputs",
    ):
        monkeypatch.setattr(providers, name, forbidden)
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="future_operation",
    )

    inputs = canonical_capability_provider_inputs(key)
    assert calls == [key]
    assert inputs.facts == ()
    assert inputs.domain_complete is False


def test_provider_inputs_validate_exact_immutable_lookup_state() -> None:
    first, second = _all_facts()[:2]
    valid = CanonicalCapabilityProviderInputs(
        first.key,
        (second,),
        False,
        CapabilityReasonCode.NOT_EVIDENCED,
    )

    assert tuple(field.name for field in fields(CanonicalCapabilityProviderInputs)) == (
        "key",
        "facts",
        "domain_complete",
        "unknown_reason",
    )
    assert is_dataclass(CanonicalCapabilityProviderInputs)
    assert hasattr(CanonicalCapabilityProviderInputs, "__slots__")
    assert valid.facts == (second,)
    with pytest.raises(FrozenInstanceError):
        valid.domain_complete = True  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(ValueError, match="exact capability key"):
        CanonicalCapabilityProviderInputs(cast(Any, object()), (), False, None)
    with pytest.raises(ValueError, match="exact fact tuple"):
        CanonicalCapabilityProviderInputs(
            first.key,
            cast(tuple[CapabilityFact, ...], [first]),
            False,
            None,
        )
    with pytest.raises(ValueError, match="exact capability facts"):
        CanonicalCapabilityProviderInputs(
            first.key,
            cast(tuple[CapabilityFact, ...], (object(),)),
            False,
            None,
        )
    with pytest.raises(ValueError, match="exact completeness"):
        CanonicalCapabilityProviderInputs(first.key, (), cast(bool, 1), None)
    with pytest.raises(ValueError, match="complete.*unknown reason"):
        CanonicalCapabilityProviderInputs(
            first.key,
            (),
            True,
            CapabilityReasonCode.NOT_EVIDENCED,
        )
    for reason in (
        CapabilityReasonCode.NO_CATALOG_ENTRY,
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
    ):
        with pytest.raises(ValueError, match="inadmissible unknown reason"):
            CanonicalCapabilityProviderInputs(first.key, (), False, reason)


def test_exact_duplicates_fold_and_distinct_conflict_order_is_preserved() -> None:
    fact = capability_inventory._CAPABILITY_FACTS[0]
    inputs = canonical_capability_provider_inputs(fact.key)
    assert lookup_capability(
        fact.key,
        (*inputs.facts, fact),
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    ) == Found(fact)

    conflict_key = next(
        key
        for key, count in Counter(fact.key for fact in _all_facts()).items()
        if count > 1
    )
    expected = tuple(fact for fact in _all_facts() if fact.key == conflict_key)
    assert _lookup(conflict_key) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        expected,
    )


def test_semantic_preservation_consumer_uses_canonical_result_equivalently() -> None:
    capabilities = preservation._capability_inventory()
    assert preservation.canonical_capability_provider_inputs is (
        canonical_capability_provider_inputs
    )
    keys = tuple(dict.fromkeys(fact.key for fact in _all_facts())) + (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureScalar",
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(CapabilityDomain.CONVERSION, subject="Int", operation="to"),
    )

    for key in keys:
        actual = capabilities.lookup(key)
        expected = _lookup(key)
        assert actual == expected
        if isinstance(expected, Found):
            assert isinstance(actual, Found)
            assert actual.fact is expected.fact
        if isinstance(expected, Conflict):
            assert isinstance(actual, Conflict)
            assert actual.evidence == expected.evidence


def test_provider_is_key_only_private_and_has_no_ambient_or_profile_state() -> None:
    source = inspect.getsource(providers).lower()
    assert tuple(
        inspect.signature(canonical_capability_provider_inputs).parameters
    ) == ("key",)
    for forbidden in (
        "capability_profiles",
        "registry",
        "entry_points",
        "import_module",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "database connection",
    ):
        assert forbidden not in source
    assert providers.__all__ == ()
    assert not hasattr(pietto, "CanonicalCapabilityProviderInputs")
    assert not hasattr(semantic_package, "CanonicalCapabilityProviderInputs")
