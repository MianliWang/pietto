from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
import struct
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.capability_availability as availability
from pietto._project.capability_availability import (
    CapabilityProfileAvailabilityOccurrence,
    CompilerCapabilityProfileAvailabilityAuthority,
    CompilerCapabilityProfileAvailabilityLedger,
    DeclaredCapabilityProfileAvailabilityBlocked,
    DeclaredCapabilityProfileAvailabilityBlockerKind,
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
    ProjectCapabilityProfileAvailabilityLedger,
    build_declared_capability_profile_availability,
)
from pietto._project.model import ProjectRoot, ProjectRootPackageActivation
from pietto._project.package_load_plan import (
    LoadedDependencyPackage,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
import pietto._project.package_manifest as package_manifest
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
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


def _profile(
    name: str = "base",
    *,
    declared_base: CapabilityProfileReference | None = None,
) -> StaticCapabilityProfile:
    reference = CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", name),
        "profile release",
    )
    is_overlay = declared_base is not None
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        reference,
        CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION
            if is_overlay
            else CapabilityProfileTargetKind.DATABASE,
            "PostgreSQL",
            "16",
            name if is_overlay else None,
            "extension release" if is_overlay else None,
        ),
        CapabilityProfileKind.OVERLAY if is_overlay else CapabilityProfileKind.BASE,
        ()
        if declared_base is None
        else (CapabilityProfileBaseOccurrence(reference, 0, declared_base),),
        (),
    )


def _requirements(
    name: str = "requirements",
    *,
    empty: bool = False,
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", name)
    occurrences = (
        ()
        if empty
        else (
            CapabilityRequirementOccurrence(
                identity,
                0,
                CapabilityKey(
                    CapabilityDomain.SCALAR_FUNCTION,
                    subject="feature",
                    operation="signature",
                ),
            ),
        )
    )
    return CapabilityRequirementCollection(identity, occurrences)


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


def test_compiler_declares_one_exact_profile_available() -> None:
    profile = _profile()
    occurrence = CapabilityProfileAvailabilityOccurrence(
        CompilerCapabilityProfileAvailabilityAuthority.COMPILER,
        0,
        profile,
    )
    ledger = CompilerCapabilityProfileAvailabilityLedger((occurrence,))
    result = build_declared_capability_profile_availability(ledger)

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.compiler is ledger
    assert result.project is None
    assert result.occurrences == (occurrence,)
    assert result.reference_buckets[0].profile is profile


def test_project_declarations_retain_exact_root_and_owner_local_order() -> None:
    project = ProjectRoot("logical/project")
    first = _profile("first")
    second = _profile("second")
    compiler = _compiler_ledger()
    project_ledger = _project_ledger(project, second, first)
    result = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.project is project_ledger
    assert result.project is not None
    assert result.project.project is project
    assert tuple(item.owner for item in result.occurrences) == (project, project)
    assert tuple(item.position for item in result.occurrences) == (0, 1)
    assert result.profiles == (second, first)


@pytest.mark.parametrize("owner", ("compiler", "project"))
def test_exact_duplicate_within_one_owner_is_structurally_blocked(
    owner: str,
) -> None:
    profile = _profile()
    compiler = (
        _compiler_ledger(profile, profile)
        if owner == "compiler"
        else _compiler_ledger()
    )
    project = ProjectRoot("logical")
    project_ledger = (
        _project_ledger(project, profile, profile) if owner == "project" else None
    )
    result = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityBlocked)
    assert tuple(blocker.kind for blocker in result.blockers) == (
        DeclaredCapabilityProfileAvailabilityBlockerKind.EXACT_DUPLICATE_AVAILABILITY_DECLARATION,
    )
    blocker = result.blockers[0]
    assert tuple(item.position for item in blocker.occurrences) == (0, 1)
    assert all(item.profile is profile for item in blocker.occurrences)


def test_same_exact_profile_from_compiler_and_project_retains_both_provenances() -> (
    None
):
    profile = _profile()
    project = ProjectRoot("logical")
    compiler = _compiler_ledger(profile)
    project_ledger = _project_ledger(project, profile)
    result = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.occurrences == (
        compiler.occurrences[0],
        project_ledger.occurrences[0],
    )
    assert result.reference_buckets[0].profile is profile
    assert result.reference_buckets[0].occurrences == result.occurrences
    assert result.profiles == (profile,)


def test_same_reference_with_distinct_profile_authorities_is_ambiguous() -> None:
    compiler_profile = _profile("same")
    project_profile = _profile("same")
    assert compiler_profile == project_profile
    assert compiler_profile is not project_profile
    project = ProjectRoot("logical")
    compiler = _compiler_ledger(compiler_profile)
    project_ledger = _project_ledger(project, project_profile)
    result = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityBlocked)
    assert not hasattr(result, "reference_buckets")
    assert tuple(blocker.kind for blocker in result.blockers) == (
        DeclaredCapabilityProfileAvailabilityBlockerKind.AMBIGUOUS_PROFILE_REFERENCE,
    )
    blocker = result.blockers[0]
    assert blocker.reference == compiler_profile.profile
    assert tuple(item.profile for item in blocker.occurrences) == (
        compiler_profile,
        project_profile,
    )


def test_compiler_and_project_ledgers_are_additive_evidence_without_precedence() -> (
    None
):
    compiler_profile = _profile("compiler-profile")
    project_profile = _profile("project-profile")
    project = ProjectRoot("logical")
    compiler = _compiler_ledger(compiler_profile)
    project_ledger = _project_ledger(project, project_profile)
    result = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.occurrences == (
        compiler.occurrences[0],
        project_ledger.occurrences[0],
    )
    assert result.profiles == (compiler_profile, project_profile)
    assert not hasattr(result, "winner")
    assert not hasattr(result, "precedence")


def test_unresolved_overlay_can_be_declared_available_without_composition() -> None:
    missing = CapabilityProfileReference(
        CapabilityProfileIdentity("pietto.targets", "missing"),
        "unavailable release",
    )
    overlay = _profile("overlay", declared_base=missing)
    result = build_declared_capability_profile_availability(_compiler_ledger(overlay))

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.profiles == (overlay,)
    assert overlay.base_occurrences[0].base is missing


def test_empty_availability_and_omission_are_not_capability_lookup_results() -> None:
    result = build_declared_capability_profile_availability(_compiler_ledger())

    assert isinstance(result, DeclaredCapabilityProfileAvailabilityReady)
    assert result.occurrences == result.reference_buckets == result.profiles == ()
    assert not hasattr(result, "support")
    assert not hasattr(result, "domain_complete")
    assert not hasattr(result, "installed")


def test_owner_authority_dense_positions_and_exact_types_fail_closed() -> None:
    profile = _profile()
    project = ProjectRoot("logical")
    with pytest.raises(ValueError, match="non-negative position"):
        CapabilityProfileAvailabilityOccurrence(project, True, profile)
    with pytest.raises(ValueError, match="dense and declaration ordered"):
        ProjectCapabilityProfileAvailabilityLedger(
            project,
            (CapabilityProfileAvailabilityOccurrence(project, 1, profile),),
        )
    equal_but_foreign = ProjectRoot("logical")
    assert equal_but_foreign == project and equal_but_foreign is not project
    with pytest.raises(ValueError, match="exact project authority"):
        ProjectCapabilityProfileAvailabilityLedger(
            project,
            (
                CapabilityProfileAvailabilityOccurrence(
                    equal_but_foreign,
                    0,
                    profile,
                ),
            ),
        )
    with pytest.raises(ValueError, match="exact owner"):
        CapabilityProfileAvailabilityOccurrence(cast(Any, object()), 0, profile)


def test_availability_results_reject_grafted_ledgers_and_buckets() -> None:
    profile = _profile()
    compiler = _compiler_ledger(profile)
    ready = build_declared_capability_profile_availability(compiler)
    assert isinstance(ready, DeclaredCapabilityProfileAvailabilityReady)
    foreign = _compiler_ledger(profile)

    with pytest.raises(ValueError, match="exact declaration ledgers"):
        DeclaredCapabilityProfileAvailabilityReady(
            foreign,
            None,
            ready.occurrences,
            ready.reference_buckets,
        )

    first = _profile("first")
    second = _profile("second")
    two = build_declared_capability_profile_availability(
        _compiler_ledger(first, second)
    )
    assert isinstance(two, DeclaredCapabilityProfileAvailabilityReady)
    with pytest.raises(ValueError, match="exact declaration authority"):
        DeclaredCapabilityProfileAvailabilityReady(
            two.compiler,
            None,
            two.occurrences,
            tuple(reversed(two.reference_buckets)),
        )

    duplicate = build_declared_capability_profile_availability(
        _compiler_ledger(profile, profile)
    )
    assert isinstance(duplicate, DeclaredCapabilityProfileAvailabilityBlocked)
    foreign_profile = _profile("foreign")
    foreign = _compiler_ledger(foreign_profile, foreign_profile)
    foreign_blocker = availability.DeclaredCapabilityProfileAvailabilityBlocker(
        DeclaredCapabilityProfileAvailabilityBlockerKind.EXACT_DUPLICATE_AVAILABILITY_DECLARATION,
        foreign.occurrences,
    )
    with pytest.raises(ValueError, match="declared blocker authority"):
        DeclaredCapabilityProfileAvailabilityBlocked(
            duplicate.compiler,
            None,
            duplicate.occurrences,
            (foreign_blocker,),
        )


def test_blocker_kinds_enforce_exact_reference_and_authority_semantics() -> None:
    first = _profile("first")
    second = _profile("second")
    compiler = _compiler_ledger(first, second)
    with pytest.raises(ValueError, match="one exact reference"):
        availability.DeclaredCapabilityProfileAvailabilityBlocker(
            DeclaredCapabilityProfileAvailabilityBlockerKind.AMBIGUOUS_PROFILE_REFERENCE,
            compiler.occurrences,
        )

    one = _profile("same")
    another = _profile("same")
    same_reference = _compiler_ledger(one, another)
    with pytest.raises(ValueError, match="one exact authority"):
        availability.DeclaredCapabilityProfileAvailabilityBlocker(
            DeclaredCapabilityProfileAvailabilityBlockerKind.EXACT_DUPLICATE_AVAILABILITY_DECLARATION,
            same_reference.occurrences,
        )

    project = ProjectRoot("logical")
    compiler_occurrence = _compiler_ledger(one).occurrences[0]
    project_occurrence = _project_ledger(project, one).occurrences[0]
    with pytest.raises(ValueError, match="distinct profile authorities"):
        availability.DeclaredCapabilityProfileAvailabilityBlocker(
            DeclaredCapabilityProfileAvailabilityBlockerKind.AMBIGUOUS_PROFILE_REFERENCE,
            (compiler_occurrence, project_occurrence),
        )


def test_availability_carriers_are_private_frozen_slotted_and_closed() -> None:
    carriers = (
        CapabilityProfileAvailabilityOccurrence,
        CompilerCapabilityProfileAvailabilityLedger,
        ProjectCapabilityProfileAvailabilityLedger,
        availability.DeclaredCapabilityProfileAvailabilityBlocker,
        availability.DeclaredCapabilityProfileReferenceBucket,
        DeclaredCapabilityProfileAvailabilityReady,
        DeclaredCapabilityProfileAvailabilityBlocked,
        PackageCapabilityRequirementBinding,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    assert tuple(CompilerCapabilityProfileAvailabilityAuthority) == (
        CompilerCapabilityProfileAvailabilityAuthority.COMPILER,
    )
    assert tuple(
        field.name for field in fields(CapabilityProfileAvailabilityOccurrence)
    ) == ("owner", "position", "profile")
    ready = build_declared_capability_profile_availability(_compiler_ledger(_profile()))
    assert isinstance(ready, DeclaredCapabilityProfileAvailabilityReady)
    with pytest.raises(FrozenInstanceError):
        ready.occurrences = ()  # pyright: ignore[reportAttributeAccessIssue]
    assert availability.__all__ == ()
    for name in (
        "CapabilityProfileAvailabilityOccurrence",
        "DeclaredCapabilityProfileAvailabilityReady",
        "PackageCapabilityRequirementBinding",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_root_and_dependency_packages_retain_exact_requirement_authority(
    tmp_path: Path,
) -> None:
    root, dependency = _loaded_packages(tmp_path)
    root_requirements = _requirements("root")
    dependency_requirements = _requirements("dependency")
    root_binding = PackageCapabilityRequirementBinding(root, root_requirements)
    dependency_binding = PackageCapabilityRequirementBinding(
        dependency,
        dependency_requirements,
    )

    assert root_binding.package is root
    assert root_binding.requirements is root_requirements
    assert dependency_binding.package is dependency
    assert dependency_binding.requirements is dependency_requirements
    assert type(root_binding.package) is LoadedRootPackage
    assert type(dependency_binding.package) is LoadedDependencyPackage


def test_explicit_empty_requirements_remain_distinct_from_no_binding(
    tmp_path: Path,
) -> None:
    root, _dependency = _loaded_packages(tmp_path)
    explicit_empty = _requirements("empty", empty=True)
    binding = PackageCapabilityRequirementBinding(root, explicit_empty)
    undeclared: PackageCapabilityRequirementBinding | None = None

    assert binding.requirements is explicit_empty
    assert binding.requirements.occurrences == ()
    assert undeclared is None
    assert binding is not undeclared


def test_package_binding_rejects_grafts_and_adds_no_unused_binding_set(
    tmp_path: Path,
) -> None:
    root, _dependency = _loaded_packages(tmp_path)
    requirements = _requirements()
    with pytest.raises(ValueError, match="exact loaded package"):
        PackageCapabilityRequirementBinding(cast(Any, object()), requirements)
    with pytest.raises(ValueError, match="exact requirement collection"):
        PackageCapabilityRequirementBinding(root, cast(Any, object()))
    assert not hasattr(availability, "PackageCapabilityRequirementBindingSet")
    assert not hasattr(availability, "ProjectCapabilityRequirementBinding")
    assert not hasattr(availability, "CompilerCapabilityRequirementBinding")


def test_availability_and_package_requirements_remain_three_separate_axes() -> None:
    source = inspect.getsource(availability).lower()
    for forbidden in (
        "capability_composition",
        "compose_capability_profiles",
        "capability_providers",
        "canonical_capability_provider_inputs",
        "lookup_capability",
        "capabilitylookupresult",
        "projectpinnedroot",
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
    binding_fields = tuple(
        field.name for field in fields(PackageCapabilityRequirementBinding)
    )
    assert binding_fields == ("package", "requirements")
    assert {
        "profile",
        "availability",
        "provides",
        "installed",
        "project",
        "compiler",
    }.isdisjoint(binding_fields)


def test_package_manifest_and_asset_contracts_have_no_profile_provision() -> None:
    source = inspect.getsource(package_manifest)
    assert "must be module_source" in source
    assert "capability_profile" not in source
    assert "profile_asset" not in source


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
