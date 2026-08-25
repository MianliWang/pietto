from __future__ import annotations

from dataclasses import fields
import hashlib
import inspect
from pathlib import Path

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as inspection
import pietto._project.capability_matrix as matrix
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
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


REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase57-postgresql-extension-signature-catalog-scope-lock-v1.md"
)
PHASE56_HANDOFF = (
    REPO_ROOT / "tests/test_phase56_slice10_completion_audit_phase57_handoff.py"
)
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
EXPECTED_ROUTE = (
    (
        "1",
        "Phase architecture, release-aware authority, readiness decisions, and route lock",
    ),
    (
        "2",
        "Catalog schema/version/identity/release, exact target coordinate, and source provenance",
    ),
    (
        "3",
        "PostgreSQL builtin and extension-native type references, physical SQL object identity, and Phase 64/69 readiness",
    ),
    (
        "4",
        "Five typed catalog entry families, complex-signature metadata, and exact-matchability contracts",
    ),
    (
        "5",
        "Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256",
    ),
    (
        "6",
        "Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection",
    ),
    (
        "7",
        "Structured EXTENSION_SIGNATURE requirement selector authority",
    ),
    (
        "8",
        "EXTENSION_SIGNATURE provider integration using typed selectors, target-scoped catalog lookup, exact checking propagation, and matrix compatibility",
    ),
    ("9", "First concrete production catalog: pgvector"),
    (
        "10",
        "Second concrete production catalog: pg_trgm, plus ltree lightweight representability probe and PostGIS representability/stress audit without full-support claims",
    ),
    (
        "11",
        "Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness",
    ),
    (
        "12",
        "Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening",
    ),
    ("13", "Completion audit and Phase 58 handoff"),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(section: str) -> tuple[tuple[str, ...], ...]:
    rows = []
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        rows.append(tuple(cell.strip() for cell in line.strip("|").split("|")))
    return tuple(rows)


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
    handoff = _read(PHASE56_HANDOFF)
    assert (
        "test_phase57_extension_signature_provider_handoff_remains_unimplemented"
        in handoff
    )
    assert EXPECTED_CORPUS_DIGEST in handoff

    families = _provider_families()
    facts = tuple(fact for family in families for fact in family)
    assert tuple(map(len, families)) == (41, 39, 18, 69, 24)
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
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (
        125,
        16,
        109,
    )
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST


def test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior() -> (
    None
):
    source_root = REPO_ROOT / "src/pietto"
    catalog_path = source_root / "semantic/extension_catalog.py"
    pg_trgm_catalog_path = source_root / "semantic/extension_catalog_pg_trgm.py"
    pgvector_catalog_path = source_root / "semantic/extension_catalog_pgvector.py"
    catalog_pure_path = source_root / "semantic/extension_catalog_pure_boundary.py"
    availability_path = source_root / "_project/extension_catalog_availability.py"
    inspection_path = source_root / "_project/extension_catalog_inspection.py"
    inspection_pure_path = (
        source_root / "_project/extension_catalog_inspection_pure_boundary.py"
    )
    project_explain_catalog_evidence_path = (
        source_root / "_project_explain/extension_catalog_evidence_projection.py"
    )
    project_explain_composition_path = source_root / "_project_explain/composition.py"
    project_explain_json_path = source_root / "_project_explain/json_v1.py"
    project_explain_runtime_path = source_root / "_project_explain/runtime_builder.py"
    capability_facts_path = source_root / "semantic/capability_facts.py"
    capability_pure_path = source_root / "_project/capability_pure_boundary.py"
    project_environment_path = (
        source_root / "_project/project_capability_environment.py"
    )
    package_manifest_path = source_root / "_project/package_manifest.py"
    package_selectors_path = (
        source_root / "_project/package_extension_signature_selectors.py"
    )
    provider_path = source_root / "_project/extension_signature_provider.py"
    selector_path = source_root / "semantic/extension_signature_requirements.py"
    catalog_paths = {
        catalog_path,
        pg_trgm_catalog_path,
        pgvector_catalog_path,
        catalog_pure_path,
        availability_path,
        inspection_path,
        inspection_pure_path,
        project_explain_catalog_evidence_path,
        project_explain_composition_path,
        project_explain_json_path,
        project_explain_runtime_path,
        capability_facts_path,
        capability_pure_path,
        project_environment_path,
        package_manifest_path,
        package_selectors_path,
        provider_path,
        selector_path,
    }
    extension_catalog_modules = tuple(
        sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in source_root.rglob("*.py")
            if "extension" in path.stem
            and ("catalog" in path.stem or "signature" in path.stem)
        )
    )
    assert extension_catalog_modules == (
        "src/pietto/_project/extension_catalog_availability.py",
        "src/pietto/_project/extension_catalog_inspection.py",
        "src/pietto/_project/extension_catalog_inspection_pure_boundary.py",
        "src/pietto/_project/extension_signature_provider.py",
        "src/pietto/_project/package_extension_signature_selectors.py",
        "src/pietto/_project_explain/extension_catalog_evidence_projection.py",
        "src/pietto/semantic/extension_catalog.py",
        "src/pietto/semantic/extension_catalog_pg_trgm.py",
        "src/pietto/semantic/extension_catalog_pgvector.py",
        "src/pietto/semantic/extension_catalog_pure_boundary.py",
        "src/pietto/semantic/extension_signature_requirements.py",
    )

    facts = tuple(fact for family in _provider_families() for fact in family)
    named_extensions = {"pgvector", "pg_trgm", "PostGIS", "TimescaleDB"}
    assert not any(fact.key.extension in named_extensions for fact in facts)
    assert not any(
        evidence.extension in named_extensions
        for fact in facts
        for evidence in fact.evidence
    )

    production_source = "\n".join(
        _read(path)
        for path in sorted(source_root.rglob("*.py"))
        if path not in catalog_paths
    )
    for forbidden in (
        "create extension",
        "pg_extension",
        "server_version",
        "psycopg",
        "asyncpg",
        "extension_catalog",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        assert forbidden not in production_source.lower()
    catalog_source = _read(catalog_path).lower()
    for forbidden in (
        "capabilityfact",
        "canonical_capability_provider_inputs",
        "database connection",
        "installation",
        "create extension",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        assert forbidden not in catalog_source
    manifest_source = inspect.getsource(package_manifest)
    assert "select_extension_catalog(" not in manifest_source
    assert "ExtensionCatalogSelectionResult" not in manifest_source

    for module in (pietto, semantic_package, project_package):
        assert not hasattr(module, "ExtensionCatalog")
        assert not hasattr(module, "PostgreSQLExtensionCatalog")
        assert not hasattr(module, "ExtensionCatalogMetadata")
        assert not hasattr(module, "ExtensionCatalogTarget")
        assert not hasattr(module, "ExtensionCatalogTypeReference")
        assert not hasattr(module, "PostgreSQLCallableIdentity")
        assert not hasattr(module, "ExtensionCatalogEntryEvidence")
        assert not hasattr(module, "ExtensionScalarFunctionCatalogEntry")
    assert "extension_catalog" not in inspect.getsource(providers)
    for source in (
        inspect.getsource(checking),
        inspect.getsource(matrix),
        inspect.getsource(inspection),
    ):
        assert "server installation" not in source.lower()
        assert "database connection" not in source.lower()
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_exact_target_release_dimensions_and_authority_boundaries_are_locked() -> None:
    scope = _read(SCOPE_LOCK)
    target = _section(scope, "Exact Catalog Target")
    assert tuple(
        line for line in target.splitlines() if line[:3] in {"1. ", "2. ", "3. ", "4. "}
    ) == (
        "1. `database_family`",
        "2. `database_release`",
        "3. `extension_identity`",
        "4. `extension_release`",
    )
    assert "For Phase 57, `database_family` is PostgreSQL and remains explicit." in (
        target
    )
    assert "Compatibility between two exact catalog targets is never\ninferred." in (
        target
    )

    dimensions = _section(scope, "Independent Identity And Release Dimensions")
    expected_dimensions = (
        "1. capability-profile schema version;",
        "2. profile identity;",
        "3. profile release;",
        "4. database family;",
        "5. database release;",
        "6. extension identity;",
        "7. extension release;",
        "8. extension-catalog schema version;",
        "9. extension-catalog identity;",
        "10. extension-catalog release.",
    )
    assert (
        tuple(
            line
            for line in dimensions.splitlines()
            if line and line[0].isdigit() and ". " in line
        )
        == expected_dimensions
    )
    assert "No release is assumed to use SemVer" in dimensions
    assert "exact opaque nonblank text" in dimensions

    key_boundary = _section(scope, "CapabilityKey Boundary")
    assert tuple(
        line
        for line in key_boundary.splitlines()
        if line and line[0].isdigit() and ". `" in line
    ) == (
        "1. `domain`",
        "2. `subject`",
        "3. `operation`",
        "4. `operands`",
        "5. `context`",
        "6. `dialect`",
        "7. `extension`",
    )
    assert "Extension release remains outside `CapabilityKey`." in key_boundary
    assert "It contains neither `release` nor `backend`." in key_boundary

    provider = _section(scope, "Release-aware Provider Readiness")
    assert "target-scoped `EXTENSION_SIGNATURE` provider\nevidence" in provider
    assert (
        "Existing non-extension provider\ndomains may remain context-free" in provider
    )
    assert "Slice 7 owns the typed requirement-selector authority." in provider
    assert "Slice 8 owns the\nsmallest explicit private authority" in provider
    for forbidden in (
        "global mutable registry",
        "latest lookup",
        "environment lookup",
        "server lookup",
        "filesystem discovery",
    ):
        assert forbidden in provider

    separation = _section(scope, "Catalog Profile And Installation Separation")
    assert "A catalog is not an `OVERLAY` profile." in separation
    assert "A profile does not prove catalog\npresence." in separation
    assert "A catalog does not prove extension installation." in separation


def test_type_entry_matching_completeness_conflict_and_artifact_locks_are_exact() -> (
    None
):
    scope = _read(SCOPE_LOCK)
    type_refs = _section(scope, "Structured Type-reference Readiness")
    assert all(
        f"{position}. `{name}`" in type_refs
        for position, name in enumerate(
            ("PIETTO_LOGICAL", "POSTGRES_BUILTIN", "EXTENSION_NATIVE"),
            start=1,
        )
    )
    assert "exact owning extension identity" in type_refs
    assert "Phase 57 creates no Pietto logical type" in type_refs
    assert "Phase 64 owns advanced type mapping and coercion semantics" in type_refs

    physical = _section(scope, "Physical SQL Identity And Lowering Separation")
    assert "function SQL name" in physical
    assert "operator token or\nname" in physical
    assert "cast source and target identity" in physical
    assert "native type name" in physical
    assert "stores no\nSQL-lowering template" in physical
    assert "Phase 69 owns" in physical

    families = _section(scope, "Five Entry Families")
    assert tuple(
        line
        for line in families.splitlines()
        if line and line[0].isdigit() and ". " in line
    ) == (
        "1. extension-native type declaration / native-type mapping;",
        "2. scalar function;",
        "3. aggregate;",
        "4. operator;",
        "5. cast.",
    )
    assert "There is no sixth matchable family in Slice 1." in families

    complex_signatures = _section(scope, "Complex Signatures And Matchability")
    assert "default arguments" in complex_signatures
    assert "variadic arguments" in complex_signatures
    assert "polymorphic or pseudo-type signatures" in complex_signatures
    assert "set-returning posture" in complex_signatures
    assert "exact-matchable now" in complex_signatures
    assert "declared or evidenced, but not representable" in complex_signatures
    assert "must not satisfy a requirement" in complex_signatures

    matching = _section(scope, "Exact Matching Policy")
    exclusions = tuple(
        line[2:].removesuffix(";").removesuffix(".")
        for line in matching.splitlines()
        if line.startswith("- ")
    )
    assert exclusions == (
        "aliases",
        "variadic expansion",
        "default-argument omission",
        "polymorphic inference",
        "generic substitution",
        "implicit coercion",
        "cast-assisted overload selection",
        "best-match ranking",
        "score-based ranking",
        "winner selection",
    )
    assert "Declaration order is provenance only." in matching

    completeness = _section(scope, "Scoped Completeness")
    assert "There is no global `catalog_complete = true`." in completeness
    assert (
        "exact catalog target, entry or signature family, and relevant lookup scope"
        in (completeness.replace("\n", " "))
    )
    assert "otherwise omission remains unknown and not evidenced" in (
        completeness.replace("\n", " ")
    )

    conflicts = _section(scope, "Conflict Boundaries")
    assert tuple(line for line in conflicts.splitlines() if line.startswith("- ")) == (
        "- structural catalog conflict;",
        "- same-signature evidence conflict;",
        "- catalog omission; and",
        "- an unmodeled signature form.",
    )
    assert "no\nwinner or precedence semantics" in conflicts

    artifact = _section(scope, "Canonical Artifact And Trust Readiness")
    assert "deterministic canonical catalog bytes" in artifact
    assert "one exact\nSHA-256 content digest" in artifact
    assert "not governance evidence hashing" in artifact

    compatibility = _section(scope, "Phase 56 Representation Compatibility")
    assert "`pietto.capability-inspection.v1`" in compatibility
    assert "exactly 125 vectors: 16 accepted and 109\nrejected" in compatibility
    assert EXPECTED_CORPUS_DIGEST in compatibility
    assert "separate private extension-catalog inspection" in compatibility
    assert "must not be forced into the Phase 56 v1\nformat" in compatibility


def test_concrete_direction_route_and_expansion_policy_are_exact() -> None:
    scope = _read(SCOPE_LOCK)
    direction = _section(scope, "First Concrete Catalog Direction")
    assert "1. `pgvector` — first concrete production catalog;" in direction
    assert "2. `pg_trgm` — second concrete production catalog;" in direction
    assert "3. `ltree` — lightweight representability probe;" in direction
    assert "4. `PostGIS` — representability and stress audit" in direction
    assert "without a full-support claim" in direction
    assert "`TimescaleDB` remains deferred." in direction
    assert "Slice 1 adds no concrete\nentry and invents no release range." in direction

    route = _section(scope, "Exact Revised Route")
    assert _table_rows(route)[1:] == EXPECTED_ROUTE

    policy = _section(scope, "Phase Length Policy")
    for line in (
        "- A normal phase has 8–12 slices.",
        "- Phase 57 began with exactly 12 route rows.",
        "- The independently proven typed requirement-selector authority expands the",
        "- Evidence may justify expansion up to 16 slices when genuinely independent",
        "- Expansion requires an explicit evidence-backed route update.",
        "- Already published slice ownership must not be silently reordered.",
    ):
        assert line in policy
    assert "Route rows assign ownership only. They do not authorize later slices." in (
        policy
    )
    assert "Implementation inconvenience alone is not evidence." in route


def test_future_readiness_package_and_public_release_locks_are_exact() -> None:
    scope = _read(SCOPE_LOCK)
    readiness = _section(scope, "Future-readiness Ownership")
    rows = _table_rows(readiness)[1:]
    assert tuple(row[0] for row in rows) == (
        "58",
        "59",
        "60",
        "64",
        "66",
        "67",
        "68",
        "69",
    )
    expected_terms = {
        "58": ("digest", "matchability", "completeness", "public projection"),
        "59": ("package requirement occurrences", "selected catalogs", "graph"),
        "60": ("uncataloged", "unmodeled", "binary ecosystem flag"),
        "64": ("structured native and logical types", "no coercion now"),
        "66": ("package asset", "not assets now"),
        "67": ("remote", "no remote I/O now"),
        "68": ("coordinates and digests", "no solver or lockfile now"),
        "69": ("physical PostgreSQL identities", "no templates or emitter"),
    }
    for phase, text in rows:
        assert all(term in text for term in expected_terms[phase])

    package = _section(scope, "Package Asset Boundary")
    assert "Extension catalogs are not current package assets." in package
    assert "does not modify\n`pietto-package.toml`" in package
    assert "add `extension_catalog` to the package asset schema" in package

    slice_boundary = _section(scope, "Slice 1 Change And Release Boundary")
    for forbidden_change in (
        "production\nsource",
        "parser",
        "AST",
        "semantic behavior",
        "IR",
        "SQL",
        "diagnostics",
        "CLI",
        "JSON",
        "public\nAPI",
        "package asset",
    ):
        assert forbidden_change in slice_boundary
    assert "version remains `0.1.0`" in slice_boundary
    assert "no tag, Release, package publication, signing,\nor attestation" in (
        slice_boundary
    )
    assert "Slice 2 remains unstarted" in slice_boundary
