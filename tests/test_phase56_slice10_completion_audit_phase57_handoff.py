from __future__ import annotations

import ast
from collections import Counter
from dataclasses import fields
import hashlib
import inspect
from pathlib import Path
import unicodedata

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_availability as availability
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as inspection
import pietto._project.capability_matrix as matrix
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_composition as composition
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_facts as capability_facts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_lookup as capability_lookup
import pietto.semantic.capability_profiles as profiles
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_checking import CapabilityRequirementStatus
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionBlockerKind,
)
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
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
PHASE57_SCOPE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase57-postgresql-extension-signature-catalog-scope-lock-v1.md"
)
VECTOR_REL = "tests/_pietto_capability_differential_vectors.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)

_PHASE56_MODULES = (
    capability_facts,
    capability_lookup,
    inventory,
    signatures,
    contexts,
    aggregates,
    windows,
    profiles,
    providers,
    composition,
    availability,
    checking,
    matrix,
    inspection,
    pure_boundary,
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
            and (
                vector.expected_status is pure_boundary.CapabilityPureStatus.OK
                and outcome.canonical_bytes == vector.expected_bytes
                or vector.expected_status is not pure_boundary.CapabilityPureStatus.OK
                and outcome.canonical_bytes is None
            )
        )
        record = outcome.record_position if outcome.record_position is not None else "-"
        field = outcome.field_position if outcome.field_position is not None else "-"
        rows.append(
            f"{vector.vector_id}:{outcome.status.value}:{record}:{field}:{matched}"
        )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def test_phase56_private_module_chain_and_public_boundaries_are_closed() -> None:
    expected_paths = (
        "src/pietto/semantic/capability_facts.py",
        "src/pietto/semantic/capability_lookup.py",
        "src/pietto/semantic/capability_inventory.py",
        "src/pietto/semantic/capability_signatures.py",
        "src/pietto/semantic/capability_contexts.py",
        "src/pietto/semantic/capability_aggregates.py",
        "src/pietto/semantic/capability_windows.py",
        "src/pietto/semantic/capability_profiles.py",
        "src/pietto/semantic/capability_providers.py",
        "src/pietto/semantic/capability_composition.py",
        "src/pietto/_project/capability_availability.py",
        "src/pietto/_project/capability_checking.py",
        "src/pietto/_project/capability_matrix.py",
        "src/pietto/_project/capability_inspection.py",
        "src/pietto/_project/capability_pure_boundary.py",
    )
    assert all((REPO_ROOT / path).is_file() for path in expected_paths)
    assert all(module.__all__ == () for module in _PHASE56_MODULES)
    for name in (
        "CapabilityKey",
        "CapabilityFact",
        "CapabilityProfileIdentity",
        "PackageCapabilityCheckingMatrix",
        "CapabilityInspection",
        "CapabilityPureDocument",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(semantic_package, name)
        assert not hasattr(project_package, name)
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        assert "capability_" not in path.read_text(encoding="utf-8")


def test_foundation_provider_counts_and_no_winner_semantics_are_exact() -> None:
    families = _provider_families()
    facts = tuple(fact for family in families for fact in family)
    counts = Counter(fact.key for fact in facts)

    assert tuple(map(len, families)) == (41, 39, 18, 69, 24)
    assert (len(facts), len(counts), len(set(facts))) == (191, 190, 191)
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
    conflict_key = next(key for key, count in counts.items() if count > 1)
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
        assert provider.facts == ()
        assert provider.domain_complete is False
        assert provider.unknown_reason is None
        assert lookup_capability(
            key,
            provider.facts,
            domain_complete=provider.domain_complete,
            unknown_reason=provider.unknown_reason,
        ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


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
    assert profile_imports == ((0, "CapabilityRequirementCollectionIdentity", None),)
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
    assert package_manifest._TOP_LEVEL_KEYS == manifest_fields
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


def test_checking_matrix_inspection_and_pure_boundaries_remain_exact() -> None:
    assert tuple(CapabilityRequirementStatus) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNSUPPORTED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
    )
    assert tuple(
        inspect.signature(checking.check_package_capability_requirements).parameters
    ) == (
        "package",
        "binding",
        "composition",
        "availability",
        "extension_signature_provider_context",
    )
    assert tuple(
        inspect.signature(matrix.build_package_capability_checking_matrix).parameters
    ) == ("package", "binding", "contexts")
    checking_source = inspect.getsource(checking).lower()
    matrix_source = inspect.getsource(matrix).lower()
    for forbidden in ("installed", "database connection"):
        assert forbidden not in checking_source
    for forbidden in (
        "worst_status",
        "best_target",
        "portabilityclassifier",
        "portability_classifier",
    ):
        assert forbidden not in matrix_source
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    inspection_source = inspect.getsource(inspection)
    assert "evaluate_capability_document" in inspect.getsource(
        inspection._serialize_capability_inspection
    )
    assert "_capability_pure_document" in inspection_source
    assert "def _escape_text" not in inspection_source
    pure_source = inspect.getsource(pure_boundary)
    assert pure_boundary.CAPABILITY_PURE_RECORD_KINDS == (
        "inspection",
        "package",
        "requirements",
        "target",
        "target_profile",
        "availability",
        "blocker",
        "blocker_profile",
        "blocker_availability",
        "requirement",
        "requirement_operand",
        "cell",
        "target_occurrence",
        "target_fact",
        "target_fact_operand",
        "target_fact_evidence",
        "provider_fact",
        "provider_fact_operand",
        "provider_fact_evidence",
    )
    for forbidden in (
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "repr(",
        "id(",
    ):
        assert forbidden not in pure_source


def test_differential_corpus_and_interpreter_locks_are_frozen() -> None:
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

    source = (REPO_ROOT / VECTOR_REL).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=VECTOR_REL)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_EXPECTED_CANONICAL_BYTES_LITERAL"
    )
    assert isinstance(assignment.value, ast.Dict)
    assert len(assignment.value.keys) == 16
    assert all(isinstance(value, ast.Constant) for value in assignment.value.values)
    slice9_source = (
        REPO_ROOT
        / "tests/test_phase56_slice9_capability_pure_boundary_differential_and_e2e.py"
    ).read_text(encoding="utf-8")
    assert all(seed in slice9_source for seed in ("0", "1", "4294967295"))
    assert "((3, 12), (3, 13))" in slice9_source


def test_phase57_extension_signature_provider_handoff_remains_unimplemented() -> None:
    facts = tuple(fact for family in _provider_families() for fact in family)
    assert CapabilityDomain.EXTENSION_SIGNATURE.value == "extension_signature"
    assert not any(
        fact.key.domain is CapabilityDomain.EXTENSION_SIGNATURE for fact in facts
    )
    assert "extension" in {field.name for field in fields(CapabilityKey)}
    assert "release" not in {field.name for field in fields(CapabilityKey)}
    assert {"extension_identity", "extension_release"} <= {
        field.name for field in fields(CapabilityProfileTarget)
    }
    assert "extension_signature" in pure_boundary._CAPABILITY_DOMAINS
    extension_vectors = tuple(
        vector
        for vector in vectors.differential_vectors()
        if "extension_signature" in vector.purposes
    )
    assert extension_vectors
    assert all(
        b"domain=e:extension_signature" in vector.expected_bytes
        for vector in extension_vectors
        if vector.expected_bytes is not None
    )
    assert not (
        REPO_ROOT / "src/pietto/semantic/capability_extension_signatures.py"
    ).exists()
    assert (REPO_ROOT / "src/pietto/semantic/extension_catalog.py").is_file()
    provider_source = inspect.getsource(providers)
    assert "extension_catalog" not in provider_source
    assert "PostGIS" not in provider_source
    assert "pgvector" not in provider_source
    for source in (
        inspect.getsource(checking),
        inspect.getsource(matrix),
        inspect.getsource(inspection),
    ):
        assert "database connection" not in source.lower()
        assert "installation" not in source.lower()


def test_phase56_completion_and_phase57_handoff_remain_exact() -> None:
    scope = " ".join(PHASE57_SCOPE_LOCK.read_text(encoding="utf-8").split())
    assert (
        "Phase 56 completion is owned by live `main` and its successful natural "
        "exact-head CI"
    ) in scope
    assert "Phase 57 owns the PostgreSQL Extension Signature Catalog" in scope
    assert "Completion audit and Phase 58 handoff" in scope
    assert "`pietto.capability-inspection.v1`" in scope


def test_version_and_public_compatibility_documents_remain_unchanged() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    public_contracts = (
        "docs/spec/cli-json-v1.md",
        "docs/spec/project-cli-json-v2.md",
        "docs/spec/semantic-metadata-artifact-v1.md",
        "docs/spec/diagnostics.md",
    )
    assert all((REPO_ROOT / path).is_file() for path in public_contracts)
