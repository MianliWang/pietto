from __future__ import annotations

import ast
from collections import Counter
from dataclasses import fields
import inspect
from pathlib import Path
import unicodedata

from _pietto_repository_facts import REPOSITORY_FACTS
import pietto._project.capability_availability as availability
import pietto._project.package_manifest as package_manifest
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_composition as composition
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionBlockerKind,
)
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import Conflict, Unknown, lookup_capability
from pietto.semantic.capability_profiles import (
    CapabilityProfileKind,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _provider_families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        inventory._CAPABILITY_FACTS,
        signatures._CAPABILITY_SIGNATURE_FACTS,
        contexts._CAPABILITY_CONTEXT_FACTS,
        aggregates._AGGREGATE_CAPABILITY_FACTS,
        windows._WINDOW_CAPABILITY_FACTS,
    )


def _top_level_test_names(source_path: str) -> frozenset[str]:
    source = REPOSITORY_FACTS.python(REPO_ROOT / source_path)
    tree = ast.parse(source.text, filename=str(source.path))
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def test_foundation_provider_counts_and_no_winner_semantics_are_exact() -> None:
    families = _provider_families()
    facts = tuple(fact for family in families for fact in family)
    counts = Counter(fact.key for fact in facts)

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
    assert tuple(CapabilitySupport) == (
        CapabilitySupport.SUPPORTED,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert tuple(CapabilityDispositionKind) == (
        CapabilityDispositionKind.NONE,
        CapabilityDispositionKind.DEFERRED,
        CapabilityDispositionKind.OUT_OF_SCOPE,
    )
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert "release" not in {field.name for field in fields(CapabilityKey)}
    assert "backend" not in {field.name for field in fields(CapabilityKey)}

    composed = CapabilityKey(CapabilityDomain.CONVERSION, subject="Café")
    decomposed = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject=unicodedata.normalize("NFD", "Café"),
    )
    assert composed != decomposed
    conflict_keys = tuple(key for key, count in counts.items() if count > 1)
    assert conflict_keys
    for conflict_key in conflict_keys:
        conflict_facts = tuple(fact for fact in facts if fact.key == conflict_key)
        result = lookup_capability(conflict_key, facts, domain_complete=True)
        assert isinstance(result, Conflict)
        assert result.evidence == conflict_facts
        assert not hasattr(result, "winner")

    for domain in (
        CapabilityDomain.CONVERSION,
        CapabilityDomain.DIALECT_LOWERING,
        CapabilityDomain.EXTENSION_SIGNATURE,
    ):
        key = CapabilityKey(domain, subject="future", operation="lookup")
        provider = providers.canonical_capability_provider_inputs(key)
        assert provider.key is key
        assert all(fact.key != key for fact in provider.facts)
        assert provider.domain_complete is False
        assert provider.unknown_reason is None
        assert lookup_capability(
            key,
            provider.facts,
            domain_complete=provider.domain_complete,
            unknown_reason=provider.unknown_reason,
        ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_named_test_evidence_resolves_in_its_exact_current_test_file() -> None:
    test_names_by_path: dict[str, frozenset[str]] = {}
    for family in _provider_families():
        for fact in family:
            for evidence in fact.evidence:
                if (
                    evidence.source is CapabilityEvidenceSource.TEST
                    and evidence.source_reference.startswith("test_")
                ):
                    test_names = test_names_by_path.get(evidence.source_path)
                    if test_names is None:
                        test_names = _top_level_test_names(evidence.source_path)
                        test_names_by_path[evidence.source_path] = test_names
                    assert evidence.source_reference in test_names, evidence


def test_profiles_composition_availability_and_package_ownership_are_closed() -> None:
    assert tuple(CapabilityProfileKind) == (
        CapabilityProfileKind.BASE,
        CapabilityProfileKind.OVERLAY,
    )
    assert tuple(CapabilityProfileTargetKind) == (
        CapabilityProfileTargetKind.DATABASE,
        CapabilityProfileTargetKind.EXTENSION,
    )
    assert tuple(field.name for field in fields(CapabilityProfileTarget)) == (
        "kind",
        "family",
        "release",
        "extension_identity",
        "extension_release",
    )
    assert tuple(
        field.name for field in fields(PackageCapabilityRequirementBinding)
    ) == (
        "package",
        "requirements",
    )
    identity = CapabilityRequirementCollectionIdentity("consumer", "empty")
    explicit_empty = CapabilityRequirementCollection(identity, ())
    assert explicit_empty.occurrences == ()
    assert explicit_empty is not None

    blocker_values = tuple(
        item.value for item in CapabilityProfileCompositionBlockerKind
    )
    assert {
        "unresolved_base",
        "ambiguous_base_reference",
        "cycle",
        "target_family_mismatch",
        "target_release_mismatch",
        "exact_duplicate_capability_fact",
    } <= set(blocker_values)
    composition_source = inspect.getsource(composition).lower()
    for forbidden in ("override", "winner", "precedence"):
        assert forbidden not in composition_source
    availability_source = inspect.getsource(availability).lower()
    assert "installed" not in availability_source
    manifest_source = inspect.getsource(package_manifest)
    manifest_tree = ast.parse(manifest_source)
    profile_imports = tuple(
        (node.level, alias.name, alias.asname)
        for node in manifest_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "pietto.semantic.capability_profiles"
        for alias in node.names
    )
    assert profile_imports == (
        (0, "CapabilityRequirementCollection", None),
        (0, "CapabilityRequirementCollectionIdentity", None),
        (0, "CapabilityRequirementOccurrence", None),
    )
    assert not any(
        alias.name.startswith("pietto.semantic.capability_profiles")
        for node in manifest_tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    profile_owned_symbols = {
        "CapabilityProfileSchemaVersion",
        "CapabilityProfileKind",
        "CapabilityProfileTargetKind",
        "CapabilityProfileIdentity",
        "CapabilityProfileReference",
        "CapabilityProfileTarget",
        "CapabilityProfileBaseOccurrence",
        "CapabilityProfileFactOccurrence",
        "StaticCapabilityProfile",
    }
    manifest_symbols = (
        {node.id for node in ast.walk(manifest_tree) if isinstance(node, ast.Name)}
        | {
            node.attr
            for node in ast.walk(manifest_tree)
            if isinstance(node, ast.Attribute)
        }
        | {
            node.asname or node.name.rsplit(".", 1)[-1]
            for node in ast.walk(manifest_tree)
            if isinstance(node, ast.alias)
        }
        | {
            node.name
            for node in ast.walk(manifest_tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
    )
    assert profile_owned_symbols.isdisjoint(manifest_symbols)

    manifest_fields = tuple(
        field.name for field in fields(package_manifest.PackageManifest)
    )
    assert manifest_fields == (
        "schema_version",
        "namespace",
        "name",
        "version",
        "assets",
        "dependencies",
        "capability_requirements",
    )
    assert package_manifest._SCHEMA_V1_TOP_LEVEL_KEYS == manifest_fields[:-1]
    assert package_manifest._SCHEMA_V2_TOP_LEVEL_KEYS == manifest_fields
    assert package_manifest._TOP_LEVEL_KEYS == (
        *manifest_fields,
        "extension_signature_selectors",
    )
    forbidden_manifest_authority = {
        "profiles",
        "capability_profiles",
        "evaluated_targets",
        "target_profiles",
        "profile_availability",
        "profile_asset",
        "profile_assets",
        "catalog_availability",
        "catalog_selection",
    }
    assert forbidden_manifest_authority.isdisjoint(manifest_fields)
    assert forbidden_manifest_authority.isdisjoint(package_manifest._TOP_LEVEL_KEYS)
