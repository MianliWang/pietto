from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
import inspect
import re
from typing import Any, cast
import unicodedata

import pytest

import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking_module
import pietto._project.capability_inspection as inspection_module
import pietto._project.capability_matrix as matrix_module
import test_phase56_slice6_exact_capability_requirement_checking as slice6
import test_phase56_slice7_multi_target_capability_matrix as slice7

from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_checking import CapabilityRequirementStatus
from pietto._project.capability_inspection import (
    CapabilityInspection,
    CapabilityInspectionAvailabilityOccurrence,
    CapabilityInspectionAvailabilityOwnerKind,
    CapabilityInspectionBlocker,
    CapabilityInspectionCell,
    CapabilityInspectionCheck,
    CapabilityInspectionColumn,
    CapabilityInspectionColumnVariant,
    CapabilityInspectionEvidence,
    CapabilityInspectionFact,
    CapabilityInspectionFactSet,
    CapabilityInspectionFormat,
    CapabilityInspectionKey,
    CapabilityInspectionLookup,
    CapabilityInspectionLookupVariant,
    CapabilityInspectionPackage,
    CapabilityInspectionPackageRole,
    CapabilityInspectionProfile,
    CapabilityInspectionRequirement,
    CapabilityInspectionRequirementDeclaration,
    CapabilityInspectionTargetOccurrence,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    PackageCapabilityCheckingMatrix,
    build_package_capability_checking_matrix,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_load_plan import LoadedDependencyPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
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
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    StaticCapabilityProfile,
)


@pytest.fixture(scope="module")
def loaded_packages(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[LoadedRootPackage, LoadedDependencyPackage]:
    return slice6.slice5._loaded_packages(tmp_path_factory.mktemp("slice8-packages"))


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


def _context(
    position: int,
    composition: CapabilityProfileCompositionSuccess,
    availability: DeclaredCapabilityProfileAvailabilityReady | None = None,
) -> CapabilityCheckingTargetContext:
    return slice7._context(position, composition, availability)


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


def _unique_supported_provider_facts() -> tuple[CapabilityFact, ...]:
    counts = Counter(fact.key for fact in slice6._PROVIDER_FACTS)
    return tuple(
        fact
        for fact in slice6._PROVIDER_FACTS
        if fact.support is CapabilitySupport.SUPPORTED and counts[fact.key] == 1
    )


def test_exact_matrix_builds_identity_bound_private_inspection(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = slice6._composition()
    matrix = _matrix(package, None, _context(0, composition))
    facts = _inspection(matrix)

    assert facts.inspection.matrix is matrix
    assert facts.inspection.format is (
        CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1
    )
    assert facts.inspection.format.value == "pietto.capability-inspection.v1"
    assert facts.inspection.package.package is package
    assert facts.inspection.package.role is CapabilityInspectionPackageRole.ROOT
    assert facts.inspection.package.namespace == "example"
    assert facts.inspection.package.name == "root"
    assert facts.inspection.package.release == "1.0.0"
    assert facts.inspection.package.content_digest == package.content_digest
    assert facts.canonical_bytes is facts.authority.canonical_bytes

    with pytest.raises(TypeError, match="exact canonical matrix"):
        build_capability_inspection(cast(Any, object()))
    with pytest.raises(TypeError, match="canonical construction"):
        CapabilityInspection()
    copied_inspection = object.__new__(CapabilityInspection)
    for declared in fields(CapabilityInspection):
        object.__setattr__(
            copied_inspection,
            declared.name,
            getattr(facts.inspection, declared.name),
        )
    assert copied_inspection == facts.inspection
    assert copied_inspection is not facts.inspection
    with pytest.raises(ValueError, match="grafted inspection"):
        CapabilityInspectionFactSet(
            inspection=copied_inspection,
            canonical_bytes=facts.canonical_bytes,
            authority=facts.authority,
        )
    copied_bytes = memoryview(facts.canonical_bytes).tobytes()
    assert copied_bytes == facts.canonical_bytes
    assert copied_bytes is not facts.canonical_bytes
    with pytest.raises(ValueError, match="grafted canonical bytes"):
        CapabilityInspectionFactSet(
            inspection=facts.inspection,
            canonical_bytes=copied_bytes,
            authority=facts.authority,
        )


def test_package_projection_excludes_loaded_host_identity(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, dependency = loaded_packages
    root_facts = _inspection(_matrix(package, None, _context(0, slice6._composition())))
    dependency_facts = _inspection(
        _matrix(dependency, None, _context(0, slice6._composition()))
    )

    assert root_facts.inspection.package.role is CapabilityInspectionPackageRole.ROOT
    assert dependency_facts.inspection.package.role is (
        CapabilityInspectionPackageRole.DEPENDENCY
    )
    assert dependency_facts.inspection.package.namespace == "example"
    assert dependency_facts.inspection.package.name == "dependency"
    for facts, loaded in ((root_facts, package), (dependency_facts, dependency)):
        payload = facts.canonical_bytes
        assert loaded.content_digest.encode() in payload
        for forbidden in (
            str(loaded_packages[0].located_root.canonical_path).encode(),
            b"canonical_path",
            b"physical_identity",
            b"device",
            b"inode",
            b"cwd",
        ):
            assert forbidden not in payload


def test_undeclared_and_explicit_empty_declared_remain_distinct(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = slice6._composition()
    context = _context(0, composition)
    undeclared = _inspection(_matrix(package, None, context))
    declared = _inspection(_matrix(package, slice6._binding(package), context))

    assert undeclared.inspection.requirement_declaration is (
        CapabilityInspectionRequirementDeclaration.UNDECLARED
    )
    assert undeclared.inspection.requirement_namespace is None
    assert undeclared.inspection.requirement_name is None
    assert undeclared.inspection.requirements == ()
    assert undeclared.inspection.targets[0].variant is (
        CapabilityInspectionColumnVariant.UNDECLARED
    )
    assert declared.inspection.requirement_declaration is (
        CapabilityInspectionRequirementDeclaration.DECLARED
    )
    assert declared.inspection.requirement_namespace == "consumer"
    assert declared.inspection.requirement_name == "slice6"
    assert declared.inspection.requirements == ()
    assert declared.inspection.targets[0].variant is (
        CapabilityInspectionColumnVariant.CHECKED
    )
    assert undeclared.canonical_bytes != declared.canonical_bytes


def test_target_profile_orders_and_availability_provenance_are_lossless(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    base = slice6.slice4._base(
        "base",
        profile_release="base profile release",
        target_release="database release",
    )
    parent = slice6.slice4._overlay(
        "parent",
        base.profile,
        profile_release="parent profile release",
        target_release="database release",
    )
    child = slice6.slice4._overlay(
        "child",
        parent.profile,
        profile_release="child profile release",
        target_release="database release",
    )
    child = cast(
        StaticCapabilityProfile,
        child.__class__(
            child.schema_version,
            child.profile,
            CapabilityProfileTarget(
                CapabilityProfileTargetKind.EXTENSION,
                "PostgreSQL",
                "database release",
                "child extension",
                "child extension release",
            ),
            child.kind,
            child.base_occurrences,
            child.capability_occurrences,
        ),
    )
    composition = _success(base, (child, parent))
    project = ProjectRoot("logical/project")
    compiler = slice6.slice5._compiler_ledger(base)
    project_ledger = slice6.slice5._project_ledger(project, parent, child)
    availability = build_declared_capability_profile_availability(
        compiler,
        project_ledger,
    )
    assert isinstance(availability, DeclaredCapabilityProfileAvailabilityReady)
    target = _inspection(
        _matrix(package, None, _context(0, composition, availability))
    ).inspection.targets[0]

    assert tuple(profile.profile for profile in target.supplied_overlays) == (
        child,
        parent,
    )
    assert tuple(profile.profile for profile in target.dependency_order) == (
        base,
        parent,
        child,
    )
    assert target.base_profile.schema_version.value == "pietto.capability-profile.v1"
    assert target.base_profile.profile_release == "base profile release"
    assert target.base_profile.target_release == "database release"
    assert target.dependency_order[-1].extension_identity == "child extension"
    assert target.dependency_order[-1].extension_release == ("child extension release")
    assert tuple(item.owner_kind for item in target.availability) == (
        CapabilityInspectionAvailabilityOwnerKind.COMPILER,
        CapabilityInspectionAvailabilityOwnerKind.PROJECT,
        CapabilityInspectionAvailabilityOwnerKind.PROJECT,
    )
    assert tuple(item.owner_position for item in target.availability) == (0, 0, 1)
    assert tuple(item.project_path for item in target.availability) == (
        None,
        "logical/project",
        "logical/project",
    )


def test_blocked_columns_preserve_blockers_without_fake_status(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    base = slice6.slice4._base()
    overlay = slice6.slice4._overlay("overlay", base.profile)
    composition = _success(base, (overlay,))
    foreign_base = slice6.slice4._base()
    availability = slice6._availability(composition, foreign_base)
    inspection = _inspection(
        _matrix(
            package,
            slice6._binding(package, key),
            _context(0, composition, availability),
        )
    )
    column = inspection.inspection.targets[0]
    cell = inspection.inspection.requirements[0].cells[0]

    assert column.variant is CapabilityInspectionColumnVariant.BLOCKED
    assert tuple(blocker.kind.value for blocker in column.blockers) == (
        "profile_authority_mismatch",
        "profile_not_declared_available",
    )
    assert column.blockers[0].selected_profile.profile is base
    assert column.blockers[0].bucket_profile is not None
    assert column.blockers[0].bucket_profile.profile is foreign_base
    assert len(column.blockers[0].bucket_occurrences) == 1
    assert column.blockers[1].selected_profile.profile is overlay
    assert column.blockers[1].bucket_profile is None
    assert column.blockers[1].bucket_occurrences == ()
    assert cell.check is None
    assert b"has_check=b:false" in inspection.canonical_bytes
    assert b"status=n:" in inspection.canonical_bytes


def test_checked_rows_preserve_five_states_and_complete_decision_evidence(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first, second, third = _unique_supported_provider_facts()[:3]
    rich_evidence = (
        CapabilityEvidence(
            CapabilityEvidenceSource.TEST,
            "path\\with\ttab\nline",
            "reference one",
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            "postgresql",
            "backend-one",
            "extension-one",
        ),
        CapabilityEvidence(
            CapabilityEvidenceSource.SPEC,
            "spec/path",
            "reference two",
        ),
    )
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        "Phase 60",
        "later exact work",
    )
    satisfied = _fact(
        first.key,
        disposition=disposition,
        evidence=rich_evidence,
    )
    unsupported = _fact(
        second.key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    absent = _fact(absent_key)
    unknown_key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="Café",
        operation="signature",
        operands=("Second", "First"),
        dialect="postgresql",
        extension="PostGIS",
    )
    unknown = _fact(unknown_key)
    conflict_supported = _fact(third.key, reference="conflict supported")
    conflict_unsupported = _fact(
        third.key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="conflict unsupported",
    )
    base = slice6.slice4._base(
        facts=(satisfied, unsupported, absent, unknown, conflict_supported)
    )
    overlay = slice6.slice4._overlay(
        "overlay",
        base.profile,
        facts=(conflict_unsupported,),
    )
    composition = _success(base, (overlay,))
    matrix = _matrix(
        package,
        slice6._binding(
            package,
            first.key,
            second.key,
            absent_key,
            unknown_key,
            third.key,
        ),
        _context(0, composition),
    )
    inspection = _inspection(matrix).inspection
    checks = tuple(
        cast(CapabilityInspectionCheck, row.cells[0].check)
        for row in inspection.requirements
    )

    assert tuple(check.status for check in checks) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNSUPPORTED,
        CapabilityRequirementStatus.ABSENT,
        CapabilityRequirementStatus.UNKNOWN,
        CapabilityRequirementStatus.CONFLICT,
    )
    assert checks[0].provider_lookup.variant is CapabilityInspectionLookupVariant.FOUND
    assert checks[0].provider_domain_complete is True
    rich = checks[0].target_occurrences[0].fact
    assert rich.support is CapabilitySupport.SUPPORTED
    assert rich.disposition_kind is CapabilityDispositionKind.DEFERRED
    assert rich.disposition_owner == "Phase 60"
    assert rich.disposition_reason == "later exact work"
    assert tuple(item.evidence for item in rich.evidence) == rich_evidence
    assert rich.evidence[0].source_path == "path\\with\ttab\nline"
    assert rich.evidence[0].reason is CapabilityReasonCode.DIALECT_LOWERING_GAP
    assert rich.evidence[0].dialect == "postgresql"
    assert rich.evidence[0].backend == "backend-one"
    assert rich.evidence[0].extension == "extension-one"
    assert checks[2].provider_lookup.variant is CapabilityInspectionLookupVariant.ABSENT
    assert checks[2].provider_lookup.reason is CapabilityReasonCode.NO_CATALOG_ENTRY
    assert checks[2].provider_domain_complete is True
    assert (
        checks[3].provider_lookup.variant is CapabilityInspectionLookupVariant.UNKNOWN
    )
    assert checks[3].provider_lookup.reason is CapabilityReasonCode.NOT_EVIDENCED
    assert checks[3].provider_domain_complete is False
    assert checks[3].provider_unknown_reason is None
    assert inspection.requirements[3].key.operands == ("Second", "First")
    assert inspection.requirements[3].key.context is None
    assert inspection.requirements[3].key.dialect == "postgresql"
    assert inspection.requirements[3].key.extension == "PostGIS"
    assert checks[4].target_lookup.variant is CapabilityInspectionLookupVariant.CONFLICT
    assert checks[4].target_lookup.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert tuple(fact.fact for fact in checks[4].target_lookup.facts) == (
        conflict_supported,
        conflict_unsupported,
    )
    assert tuple(
        item.profile_fact_position for item in checks[4].target_occurrences
    ) == (4, 0)
    assert tuple(item.profile_position for item in checks[4].target_occurrences) == (
        0,
        1,
    )


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
    base = slice6.slice4._base(
        profile_release=profile_release,
        facts=(fact,),
    )
    composition = _success(base)
    if project:
        project_root = ProjectRoot("logical/project")
        availability_result = build_declared_capability_profile_availability(
            slice6.slice5._compiler_ledger(),
            slice6.slice5._project_ledger(project_root, base),
        )
        assert isinstance(
            availability_result,
            DeclaredCapabilityProfileAvailabilityReady,
        )
        availability = availability_result
    else:
        availability = (
            slice6._availability(
                composition,
                slice6.slice4._base("extra"),
                base,
            )
            if availability_position_one
            else slice6._availability(composition)
        )
    return _inspection(
        _matrix(
            package,
            slice6._binding(package, key),
            _context(0, composition, availability),
        )
    )


def test_canonical_bytes_are_value_deterministic_escaped_and_semantic_sensitive(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first = _unknown_inspection(package)
    equal_but_distinct = _unknown_inspection(package)

    assert first.inspection is not equal_but_distinct.inspection
    assert first.canonical_bytes == equal_but_distinct.canonical_bytes
    assert first.canonical_bytes.endswith(b"\n")
    assert not first.canonical_bytes.endswith(b"\n\n")
    assert re.search(rb"0x[0-9a-fA-F]+", first.canonical_bytes) is None
    assert b"\\t" not in first.canonical_bytes
    escaped = _unknown_inspection(package, source_path="a\tb\nc\rd\\e")
    assert b"source_path=s:a\\tb\\nc\\rd\\\\e" in escaped.canonical_bytes

    variants = (
        _unknown_inspection(package, subject="Value"),
        _unknown_inspection(
            package,
            support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        ),
        _unknown_inspection(package, source_path="other/path"),
        _unknown_inspection(package, source_reference="other reference"),
        _unknown_inspection(
            package,
            evidence_reason=CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        ),
        _unknown_inspection(
            package,
            disposition=CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED,
                "Phase 60",
                "later",
            ),
        ),
        _unknown_inspection(package, profile_release="other release"),
        _unknown_inspection(package, project=True),
        _unknown_inspection(package, availability_position_one=True),
    )
    assert all(item.canonical_bytes != first.canonical_bytes for item in variants)

    composed = _unknown_inspection(package, subject="Café")
    decomposed = _unknown_inspection(
        package,
        subject=unicodedata.normalize("NFD", "Café"),
    )
    assert composed.canonical_bytes != decomposed.canonical_bytes
    assert "Café".encode() in composed.canonical_bytes
    assert unicodedata.normalize("NFD", "Café").encode() in decomposed.canonical_bytes


def test_extension_release_and_bounded_provider_reason_are_canonical(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    base = slice6.slice4._base()

    def extension_bytes(extension_release: str) -> bytes:
        original = slice6.slice4._overlay("extension", base.profile)
        overlay = StaticCapabilityProfile(
            original.schema_version,
            original.profile,
            CapabilityProfileTarget(
                CapabilityProfileTargetKind.EXTENSION,
                original.target.family,
                original.target.release,
                original.target.extension_identity,
                extension_release,
            ),
            original.kind,
            original.base_occurrences,
            original.capability_occurrences,
        )
        composition = _success(base, (overlay,))
        return _inspection(
            _matrix(package, None, _context(0, composition))
        ).canonical_bytes

    assert extension_bytes("one") != extension_bytes("two")

    key = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject="Int",
        operation="/",
        operands=("Int", "Int", "unknown"),
        context="expression",
    )
    composition = slice6._composition(_fact(key))
    facts = _inspection(
        _matrix(
            package,
            slice6._binding(package, key),
            _context(0, composition),
        )
    )
    check = facts.inspection.requirements[0].cells[0].check
    assert check is not None
    assert check.provider_unknown_reason is (
        CapabilityReasonCode.NO_CURRENT_RESULT_RULE
    )
    assert check.provider_lookup.variant is CapabilityInspectionLookupVariant.UNKNOWN
    assert check.provider_lookup.reason is CapabilityReasonCode.NO_CURRENT_RESULT_RULE
    assert b"provider_unknown_reason=e:no_current_result_rule" in facts.canonical_bytes


def test_requirement_target_and_conflict_orders_change_canonical_bytes(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first_key = CapabilityKey(CapabilityDomain.CONVERSION, subject="first")
    second_key = CapabilityKey(CapabilityDomain.CONVERSION, subject="second")
    first_fact = _fact(first_key)
    second_fact = _fact(second_key)
    composition = slice6._composition(first_fact, second_fact)
    context = _context(0, composition)
    first_order = _inspection(
        _matrix(
            package,
            slice6._binding(package, first_key, second_key),
            context,
        )
    )
    second_order = _inspection(
        _matrix(
            package,
            slice6._binding(package, second_key, first_key),
            context,
        )
    )
    assert first_order.canonical_bytes != second_order.canonical_bytes

    a = slice6._composition()
    b = _success(slice6.slice4._base(profile_release="other"))
    targets_ab = _inspection(_matrix(package, None, _context(0, a), _context(1, b)))
    targets_ba = _inspection(_matrix(package, None, _context(0, b), _context(1, a)))
    assert targets_ab.canonical_bytes != targets_ba.canonical_bytes

    conflict_key = _unique_supported_provider_facts()[3].key
    supported = _fact(conflict_key, reference="supported")
    unsupported = _fact(
        conflict_key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="unsupported",
    )
    base_one = slice6.slice4._base(facts=(supported,))
    overlay_one = slice6.slice4._overlay(
        "overlay",
        base_one.profile,
        facts=(unsupported,),
    )
    base_two = slice6.slice4._base(facts=(unsupported,))
    overlay_two = slice6.slice4._overlay(
        "overlay",
        base_two.profile,
        facts=(supported,),
    )
    conflict_one = _success(base_one, (overlay_one,))
    conflict_two = _success(base_two, (overlay_two,))
    bytes_one = _inspection(
        _matrix(
            package,
            slice6._binding(package, conflict_key),
            _context(0, conflict_one),
        )
    ).canonical_bytes
    bytes_two = _inspection(
        _matrix(
            package,
            slice6._binding(package, conflict_key),
            _context(0, conflict_two),
        )
    ).canonical_bytes
    assert bytes_one != bytes_two


def _lock_payloads(package: LoadedRootPackage) -> dict[str, bytes]:
    base = slice6.slice4._base(
        "lock",
        profile_release="p",
        target_release="d",
    )
    composition = _success(base)
    context = _context(0, composition)
    undeclared = _inspection(_matrix(package, None, context)).canonical_bytes
    explicit_empty = _inspection(
        _matrix(package, slice6._binding(package), context)
    ).canonical_bytes

    provider = _unique_supported_provider_facts()[0]
    checked_fact = _fact(
        provider.key,
        evidence=(CapabilityEvidence(CapabilityEvidenceSource.TEST, "p", "r"),),
    )
    checked_composition = slice6._composition(checked_fact)
    checked = _inspection(
        _matrix(
            package,
            slice6._binding(package, provider.key),
            _context(0, checked_composition),
        )
    ).canonical_bytes

    empty_availability = build_declared_capability_profile_availability(
        slice6.slice5._compiler_ledger()
    )
    assert isinstance(empty_availability, DeclaredCapabilityProfileAvailabilityReady)
    blocked = _inspection(
        _matrix(
            package,
            slice6._binding(package),
            _context(0, composition, empty_availability),
        )
    ).canonical_bytes

    unknown_key = CapabilityKey(CapabilityDomain.CONVERSION, subject="u")
    unknown_fact = _fact(
        unknown_key,
        evidence=(CapabilityEvidence(CapabilityEvidenceSource.TEST, "p", "u"),),
    )
    unknown_composition = slice6._composition(unknown_fact)
    unknown = _inspection(
        _matrix(
            package,
            slice6._binding(package, unknown_key),
            _context(0, unknown_composition),
        )
    ).canonical_bytes
    return {
        "undeclared": undeclared,
        "explicit_empty": explicit_empty,
        "checked": checked,
        "blocked": blocked,
        "unknown": unknown,
    }


_EXACT_BYTE_LOCKS = {
    "undeclared": (
        b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:undeclared\ttargets=i:1\trequirements=i:0\n"
        b"package\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:e1bb3b80e834edf3bc89ebb9167b1dc416d69dc0adc1ef601b5ea347a7cac575\n"
        b"target\ttarget=i:0\tvariant=e:undeclared\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\n"
        b"target_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"target_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"availability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
    ),
    "explicit_empty": (
        b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\n"
        b"package\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:e1bb3b80e834edf3bc89ebb9167b1dc416d69dc0adc1ef601b5ea347a7cac575\n"
        b"requirements\tnamespace=s:consumer\tname=s:slice6\tcount=i:0\n"
        b"target\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\n"
        b"target_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"target_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"availability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
    ),
    "checked": (
        b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\n"
        b"package\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:e1bb3b80e834edf3bc89ebb9167b1dc416d69dc0adc1ef601b5ea347a7cac575\n"
        b"requirements\tnamespace=s:consumer\tname=s:slice6\tcount=i:1\n"
        b"target\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\n"
        b"target_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"target_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"availability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"requirement\trequirement=i:0\tdomain=e:logical_type\tsubject=s:Any\toperation=s:catalog_membership\toperands=i:0\tcontext=s:builtin_registry\tdialect=n:\textension=n:\n"
        b"cell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:satisfied\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:found\tprovider_reason=n:\tprovider_lookup_facts=i:1\n"
        b"target_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\n"
        b"target_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:logical_type\tsubject=s:Any\toperation=s:catalog_membership\toperands=i:0\tcontext=s:builtin_registry\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\n"
        b"target_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:p\tsource_reference=s:r\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:logical_type\tsubject=s:Any\toperation=s:catalog_membership\toperands=i:0\tcontext=s:builtin_registry\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:9\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:semantic_catalog\tsource_path=s:src/pietto/semantic/catalog.py\tsource_reference=s:BUILTIN_TYPE_NAMES\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:1\tsource=e:semantic_procedure\tsource_path=s:src/pietto/semantic/analyzer.py\tsource_reference=s:_resolve_type\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:2\tsource=e:semantic_model\tsource_path=s:src/pietto/semantic/model.py\tsource_reference=s:ResolvedType and TypeKind.BUILTIN\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:3\tsource=e:ir\tsource_path=s:src/pietto/ir/model.py\tsource_reference=s:TypeRefIR and TypeKindIR.BUILTIN\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:4\tsource=e:project\tsource_path=s:src/pietto/_project/model.py\tsource_reference=s:_resolve_project_type\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:5\tsource=e:public\tsource_path=s:src/pietto/_metadata/builder.py\tsource_reference=s:_type_metadata and _support_posture\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:6\tsource=e:test\tsource_path=s:tests/test_semantic_types.py\tsource_reference=s:test_builtin_type_catalog_resolves_supported_names\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:7\tsource=e:spec\tsource_path=s:docs/spec/canonical-scalar-type-registry-v1.md\tsource_reference=s:Current Repo Facts\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
        b"provider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:8\tsource=e:spec\tsource_path=s:docs/spec/any-bytes-json-support-posture-v1.md\tsource_reference=s:Any support boundary\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
    ),
    "blocked": (
        b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\n"
        b"package\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:e1bb3b80e834edf3bc89ebb9167b1dc416d69dc0adc1ef601b5ea347a7cac575\n"
        b"requirements\tnamespace=s:consumer\tname=s:slice6\tcount=i:0\n"
        b"target\ttarget=i:0\tvariant=e:blocked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:0\tblockers=i:1\n"
        b"target_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"target_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
        b"blocker\ttarget=i:0\tblocker=i:0\tkind=e:profile_not_declared_available\thas_bucket=b:false\tbucket_occurrences=i:0\n"
        b"blocker_profile\ttarget=i:0\tblocker=i:0\trole=s:selected\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:lock\tprofile_release=s:p\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:d\textension_identity=n:\textension_release=n:\n"
    ),
    "unknown": (
        b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\n"
        b"package\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:e1bb3b80e834edf3bc89ebb9167b1dc416d69dc0adc1ef601b5ea347a7cac575\n"
        b"requirements\tnamespace=s:consumer\tname=s:slice6\tcount=i:1\n"
        b"target\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\n"
        b"target_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"target_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"availability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n"
        b"requirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:u\toperation=n:\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\n"
        b"cell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=n:\tprovider_lookup=e:unknown\tprovider_reason=e:not_evidenced\tprovider_lookup_facts=i:0\n"
        b"target_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\n"
        b"target_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:u\toperation=n:\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\n"
        b"target_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:p\tsource_reference=s:u\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n"
    ),
}


def test_small_exact_byte_locks_cover_required_shapes(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    assert _lock_payloads(package) == _EXACT_BYTE_LOCKS


def test_inspection_never_recomputes_checking_or_matrix_truth(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, _dependency = loaded_packages
    matrix = _matrix(package, None, _context(0, slice6._composition()))

    def forbidden(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("inspection recomputed capability truth")

    monkeypatch.setattr(
        checking_module,
        "check_package_capability_requirements",
        forbidden,
    )
    monkeypatch.setattr(
        matrix_module,
        "build_package_capability_checking_matrix",
        forbidden,
    )
    facts = build_capability_inspection(matrix)

    assert facts.inspection.matrix is matrix
    source = inspect.getsource(inspection_module)
    assert "check_package_capability_requirements(" not in source
    assert "build_package_capability_checking_matrix(" not in source
    assert "compose_capability_profiles(" not in source
    assert "build_declared_capability_profile_availability(" not in source
    assert "canonical_capability_provider_inputs(" not in source


def test_inspection_is_private_closed_and_has_no_portability_or_runtime_surface() -> (
    None
):
    carriers = (
        CapabilityInspectionPackage,
        CapabilityInspectionKey,
        CapabilityInspectionEvidence,
        CapabilityInspectionFact,
        CapabilityInspectionProfile,
        CapabilityInspectionAvailabilityOccurrence,
        CapabilityInspectionLookup,
        CapabilityInspectionTargetOccurrence,
        CapabilityInspectionCheck,
        CapabilityInspectionBlocker,
        CapabilityInspectionColumn,
        CapabilityInspectionCell,
        CapabilityInspectionRequirement,
        CapabilityInspection,
        CapabilityInspectionFactSet,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    for carrier in carriers[:-1]:
        with pytest.raises(TypeError):
            carrier()  # type: ignore[call-arg]
    assert tuple(field.name for field in fields(CapabilityInspection)) == (
        "format",
        "package",
        "requirement_declaration",
        "requirement_namespace",
        "requirement_name",
        "target_count",
        "requirement_count",
        "targets",
        "requirements",
        "matrix",
    )
    assert inspection_module.__all__ == ()
    for name in (
        "CapabilityInspection",
        "CapabilityInspectionFactSet",
        "build_capability_inspection",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    source = inspect.getsource(inspection_module).lower()
    for forbidden in (
        "portabilityclassifier",
        "portable_status",
        "best_target",
        "worst_status",
        "json.dumps",
        "pickle",
        "marshal",
        "hashlib",
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
    assert "__repr__" not in source
    assert "hash(" not in source
