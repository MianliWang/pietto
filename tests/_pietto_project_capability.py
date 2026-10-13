from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import struct
from typing import Any, cast

import _pietto_capability_differential_vectors as vectors
from pietto._project.capability_availability import (
    CapabilityProfileAvailabilityOccurrence,
    CompilerCapabilityProfileAvailabilityAuthority,
    CompilerCapabilityProfileAvailabilityLedger,
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
    ProjectCapabilityProfileAvailabilityLedger,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_matrix import CapabilityCheckingTargetContext
from pietto._project.capability_matrix import (
    PackageCapabilityCheckingMatrix,
    build_package_capability_checking_matrix,
)
import pietto._project.capability_pure_boundary as pure_boundary
from pietto._project.capability_checking import check_package_capability_requirements  # noqa: F401
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.model import ProjectRoot, ProjectRootPackageActivation
from pietto._project.package_load_plan import (
    LoadedDependencyPackage,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto.semantic import (
    capability_aggregates,
    capability_contexts,
    capability_inventory,
    capability_signatures,
    capability_windows,
)
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityDomain,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
    CapabilityProfileFactOccurrence,
    CapabilityProfileIdentity,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileSchemaVersion,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
    StaticCapabilityProfile,
)


_SOURCE = b"shape Row:\n    id: Int\n"
_FAMILIES = (
    capability_inventory._CAPABILITY_FACTS,
    capability_signatures._CAPABILITY_SIGNATURE_FACTS,
    capability_contexts._CAPABILITY_CONTEXT_FACTS,
    capability_aggregates._AGGREGATE_CAPABILITY_FACTS,
    capability_windows._WINDOW_CAPABILITY_FACTS,
)
_PROVIDER_FACTS = tuple(fact for family in _FAMILIES for fact in family)
_SUPPORTED_PROVIDER_FACT = next(
    fact for fact in _PROVIDER_FACTS if fact.support is CapabilitySupport.SUPPORTED
)
_UNSUPPORTED_PROVIDER_FACT = next(
    fact
    for fact in _PROVIDER_FACTS
    if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
)
_COUNT_CONFLICT_KEY = next(
    key
    for key, count in Counter(fact.key for fact in _PROVIDER_FACTS).items()
    if count > 1
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


def _reference(
    name: str,
    release: str = "profile release",
) -> CapabilityProfileReference:
    return CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", name),
        release,
    )


def _base(
    name: str = "base",
    *,
    profile_release: str = "profile release",
    family: str = "PostgreSQL",
    target_release: str = "16",
    facts: tuple[CapabilityFact, ...] = (),
) -> StaticCapabilityProfile:
    owner = _reference(name, profile_release)
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.DATABASE,
            family,
            target_release,
        ),
        CapabilityProfileKind.BASE,
        (),
        tuple(
            CapabilityProfileFactOccurrence(owner, position, fact)
            for position, fact in enumerate(facts)
        ),
    )


def _overlay(
    name: str,
    declared_base: CapabilityProfileReference,
    *,
    profile_release: str = "profile release",
    family: str = "PostgreSQL",
    target_release: str = "16",
    extension: str | None = None,
    facts: tuple[CapabilityFact, ...] = (),
) -> StaticCapabilityProfile:
    owner = _reference(name, profile_release)
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        owner,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            family,
            target_release,
            name if extension is None else extension,
            "extension release",
        ),
        CapabilityProfileKind.OVERLAY,
        (CapabilityProfileBaseOccurrence(owner, 0, declared_base),),
        tuple(
            CapabilityProfileFactOccurrence(owner, position, fact)
            for position, fact in enumerate(facts)
        ),
    )


def _target_fact(
    key: CapabilityKey,
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    reference: str = "target declaration",
) -> CapabilityFact:
    return CapabilityFact(
        key,
        support,
        CapabilityDisposition(CapabilityDispositionKind.NONE)
        if disposition is None
        else disposition,
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_project_capability_checking.py",
                reference,
            ),
        ),
    )


def _requirements(*keys: CapabilityKey) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", "slice6")
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _composition(
    *facts: CapabilityFact,
) -> CapabilityProfileCompositionSuccess:
    base = _base(facts=tuple(facts))
    result = compose_capability_profiles(base, ())
    assert isinstance(result, CapabilityProfileCompositionSuccess)
    return result


def _compiler_ledger(
    *profiles: StaticCapabilityProfile,
) -> CompilerCapabilityProfileAvailabilityLedger:
    return CompilerCapabilityProfileAvailabilityLedger(
        tuple(
            CapabilityProfileAvailabilityOccurrence(
                CompilerCapabilityProfileAvailabilityAuthority.COMPILER,
                position,
                profile,
            )
            for position, profile in enumerate(profiles)
        )
    )


def _project_ledger(
    project: ProjectRoot,
    *profiles: StaticCapabilityProfile,
) -> ProjectCapabilityProfileAvailabilityLedger:
    return ProjectCapabilityProfileAvailabilityLedger(
        project,
        tuple(
            CapabilityProfileAvailabilityOccurrence(project, position, profile)
            for position, profile in enumerate(profiles)
        ),
    )


def _availability(
    composition: CapabilityProfileCompositionSuccess,
    *profiles: object,
) -> DeclaredCapabilityProfileAvailabilityReady:
    selected = (
        composition.dependency_order
        if not profiles
        else cast(tuple[Any, ...], profiles)
    )
    result = build_declared_capability_profile_availability(_compiler_ledger(*selected))
    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    return result


def _context(
    position: int,
    composition: CapabilityProfileCompositionSuccess,
    availability: DeclaredCapabilityProfileAvailabilityReady | None = None,
) -> CapabilityCheckingTargetContext:
    return CapabilityCheckingTargetContext(
        position,
        composition,
        _availability(composition) if availability is None else availability,
    )


def _fact(
    key: CapabilityKey,
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
    reference: str = "target",
) -> CapabilityFact:
    return CapabilityFact(
        key,
        support,
        (
            CapabilityDisposition(CapabilityDispositionKind.NONE)
            if disposition is None
            else disposition
        ),
        (
            (
                CapabilityEvidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/slice8.py",
                    reference,
                ),
            )
            if evidence is None
            else evidence
        ),
    )


def _success(
    base: StaticCapabilityProfile,
    overlays: tuple[StaticCapabilityProfile, ...] = (),
) -> CapabilityProfileCompositionSuccess:
    result = compose_capability_profiles(base, overlays)
    assert isinstance(result, CapabilityProfileCompositionSuccess)
    return result


def _unique_supported_provider_facts() -> tuple[CapabilityFact, ...]:
    counts = Counter(fact.key for fact in _PROVIDER_FACTS)
    return tuple(
        fact
        for fact in _PROVIDER_FACTS
        if fact.support is CapabilitySupport.SUPPORTED and counts[fact.key] == 1
    )


def _matrix(
    package: LoadedRootPackage | LoadedDependencyPackage,
    binding: Any,
    *contexts: CapabilityCheckingTargetContext,
) -> PackageCapabilityCheckingMatrix:
    return build_package_capability_checking_matrix(package, binding, contexts)


def _inspection(
    matrix: PackageCapabilityCheckingMatrix,
) -> CapabilityInspectionFactSet:
    return build_capability_inspection(matrix)


def _unknown_inspection(
    package: LoadedRootPackage,
    *,
    subject: str = "value",
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    source_path: str = "source/path",
    source_reference: str = "source reference",
    evidence_reason: CapabilityReasonCode | None = None,
    disposition: CapabilityDisposition | None = None,
    profile_release: str = "profile release",
    project: bool = False,
    availability_position_one: bool = False,
) -> CapabilityInspectionFactSet:
    key = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject=subject,
        operation="convert",
        operands=("B", "A"),
    )
    fact = _fact(
        key,
        support=support,
        disposition=disposition,
        evidence=(
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                source_path,
                source_reference,
                evidence_reason,
            ),
        ),
    )
    base = _base(
        profile_release=profile_release,
        facts=(fact,),
    )
    composition = _success(base)
    if project:
        project_root = ProjectRoot("logical/project")
        availability_result = build_declared_capability_profile_availability(
            _compiler_ledger(),
            _project_ledger(project_root, base),
        )
        assert isinstance(
            availability_result,
            DeclaredCapabilityProfileAvailabilityReady,
        )
        availability = availability_result
    else:
        availability = (
            _availability(
                composition,
                _base("extra"),
                base,
            )
            if availability_position_one
            else _availability(composition)
        )
    return _inspection(
        _matrix(
            package,
            _binding(package, key),
            _context(0, composition, availability),
        )
    )


def _binding(
    package: LoadedRootPackage | LoadedDependencyPackage,
    *keys: CapabilityKey,
) -> PackageCapabilityRequirementBinding:
    return PackageCapabilityRequirementBinding(package, _requirements(*keys))


def _loaded_packages(
    tmp_path: Path,
) -> tuple[LoadedRootPackage, LoadedDependencyPackage]:
    project = tmp_path / "project"
    dependency_digest = _write_package(project, "deps/dependency", name="dependency")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            (
                "example",
                "dependency",
                "1.0.0",
                dependency_digest,
                "../deps/dependency",
            ),
        ),
    )
    root = _load_root(project, "root", root_digest)
    result = _build_package_load_plan(root)
    assert result.ok and result.plan is not None
    assert result.plan.root_package is root
    dependency = result.plan.entries[0].package
    assert type(dependency) is LoadedDependencyPackage
    assert result.plan.entries[-1].package is root
    return root, dependency


def _write_package(
    project: Path,
    package_path: str,
    *,
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
    module_path: str = "main.pietto",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        namespace=namespace,
        name=name,
        version=version,
        module_path=module_path,
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    module = package_root / module_path
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_bytes(_SOURCE)
    return _digest(manifest, ((module_path, _SOURCE),))


def _load_root(project: Path, package_path: str, digest: str) -> LoadedRootPackage:
    pinned_root = _pin_project_root(project)
    assert type(pinned_root) is ProjectPinnedRoot
    activation = ProjectRootPackageActivation(
        path=package_path,
        namespace="example",
        name="root",
        version="1.0.0",
        sha256=digest,
    )
    located = _locate_root_package(pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    assert loaded.loaded_package.content_digest == digest
    return loaded.loaded_package


def _manifest(
    *,
    namespace: str,
    name: str,
    version: str,
    module_path: str,
    dependencies: tuple[tuple[str, str, str, str, str], ...],
) -> bytes:
    lines = [
        "schema_version = 1",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        f'version = "{version}"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        f'path = "{module_path}"',
    ]
    for dep_namespace, dep_name, dep_version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{dep_name}"',
                f'version = "{dep_version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _digest(manifest: bytes, assets: tuple[tuple[str, bytes], ...]) -> str:
    stream = bytearray(b"pietto-package-content-v1\0")
    for path, content in (("pietto-package.toml", manifest), *assets):
        path_bytes = path.encode()
        stream.extend(struct.pack(">Q", len(path_bytes)))
        stream.extend(path_bytes)
        stream.extend(struct.pack(">Q", len(content)))
        stream.extend(content)
    return hashlib.sha256(stream).hexdigest()
