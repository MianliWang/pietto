from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.compatibility_matrix_projection as projection_module
import pietto.semantic as semantic_package
import test_phase55_slice10_package_inspection_canonical_serialization as package_slice
import test_phase56_slice6_exact_capability_requirement_checking as checking_slice
import test_phase56_slice8_capability_inspection_representation as inspection_slice
import test_phase58_slice3_project_explain_package_requirement_provenance as slice3
from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    build_package_capability_checking_matrix,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_inspection import PackageInspectionFactSet
from pietto._project.package_load_plan import LoadedPackage
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainAvailabilityOccurrence,
    ProjectExplainAvailabilityOwnerKind,
    ProjectExplainCapabilityProfile,
    ProjectExplainCapabilitySupport,
    ProjectExplainCheckedEvidence,
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluatedTarget,
    ProjectExplainEvaluationState,
    ProjectExplainLookupSummary,
    ProjectExplainLookupVariant,
    ProjectExplainMatrixBlocker,
    ProjectExplainMatrixBlockerKind,
    ProjectExplainMatrixCell,
    ProjectExplainMatrixRow,
    ProjectExplainPackageTargetEvaluation,
    ProjectExplainProfileKind,
    ProjectExplainProfileTargetKind,
    ProjectExplainRequirementTargetMatrix,
    _project_empty_requirement_target_matrix,
    _project_requirement_target_matrix,
)
from pietto._project_explain.model import (
    ProjectExplainEvidencePosture,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.capability_profiles import CapabilityRequirementCollection


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice4-project-explain-requirement-target-matrix-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project_explain/compatibility_matrix_projection.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _capability_facts(
    package_facts: PackageInspectionFactSet,
    collections: tuple[CapabilityRequirementCollection | None, ...],
    contexts: tuple[CapabilityCheckingTargetContext, ...],
) -> tuple[CapabilityInspectionFactSet, ...]:
    assert len(collections) == len(package_facts.inspection.packages)
    result: list[CapabilityInspectionFactSet] = []
    for package, collection in zip(
        package_facts.inspection.packages,
        collections,
        strict=True,
    ):
        loaded = cast(LoadedPackage, package.entry.package)
        binding = (
            None
            if collection is None
            else PackageCapabilityRequirementBinding(loaded, collection)
        )
        result.append(
            build_capability_inspection(
                build_package_capability_checking_matrix(
                    loaded,
                    binding,
                    contexts,
                )
            )
        )
    return tuple(result)


def _authority(
    root: Path,
    collections: tuple[CapabilityRequirementCollection | None, ...],
    contexts: tuple[CapabilityCheckingTargetContext, ...],
) -> tuple[
    ProjectExplainPackageRequirementProjection,
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
]:
    package_facts = package_slice._simple_inspection(
        root,
        root_path=".",
        dependency_path="dep",
        authored_path="dep",
    )
    capability_facts = _capability_facts(package_facts, collections, contexts)
    return (
        _project_package_requirement_provenance(package_facts, capability_facts),
        package_facts,
        capability_facts,
    )


def _simple_profile(
    *,
    name: str = "base",
    kind: ProjectExplainProfileKind = ProjectExplainProfileKind.BASE,
) -> ProjectExplainCapabilityProfile:
    return ProjectExplainCapabilityProfile(
        namespace="pietto",
        name=name,
        profile_release="profile release",
        kind=kind,
        target_kind=(
            ProjectExplainProfileTargetKind.DATABASE
            if kind is ProjectExplainProfileKind.BASE
            else ProjectExplainProfileTargetKind.EXTENSION
        ),
        database_family="PostgreSQL",
        target_release="16",
        extension_identity=None if kind is ProjectExplainProfileKind.BASE else name,
        extension_release=(
            None if kind is ProjectExplainProfileKind.BASE else "extension release"
        ),
    )


def _lookup(
    variant: ProjectExplainLookupVariant,
    *,
    unsupported: bool = False,
) -> ProjectExplainLookupSummary:
    support = (
        ProjectExplainCapabilitySupport.EXPLICITLY_UNSUPPORTED
        if unsupported
        else ProjectExplainCapabilitySupport.SUPPORTED
    )
    if variant is ProjectExplainLookupVariant.FOUND:
        return ProjectExplainLookupSummary(
            variant=variant,
            reason=None,
            supports=(support,),
        )
    if variant is ProjectExplainLookupVariant.ABSENT:
        return ProjectExplainLookupSummary(
            variant=variant,
            reason="no_catalog_entry",
            supports=(),
        )
    if variant is ProjectExplainLookupVariant.UNKNOWN:
        return ProjectExplainLookupSummary(
            variant=variant,
            reason="not_evidenced",
            supports=(),
        )
    return ProjectExplainLookupSummary(
        variant=variant,
        reason="conflicting_evidence",
        supports=(
            ProjectExplainCapabilitySupport.SUPPORTED,
            ProjectExplainCapabilitySupport.EXPLICITLY_UNSUPPORTED,
        ),
    )


def _evidence_for(status: ProjectExplainCheckedStatus) -> ProjectExplainCheckedEvidence:
    target = _lookup(ProjectExplainLookupVariant.FOUND)
    provider = _lookup(ProjectExplainLookupVariant.FOUND)
    if status is ProjectExplainCheckedStatus.UNSUPPORTED:
        target = _lookup(ProjectExplainLookupVariant.FOUND, unsupported=True)
    elif status is ProjectExplainCheckedStatus.ABSENT:
        provider = _lookup(ProjectExplainLookupVariant.ABSENT)
    elif status is ProjectExplainCheckedStatus.UNKNOWN:
        provider = _lookup(ProjectExplainLookupVariant.UNKNOWN)
    elif status is ProjectExplainCheckedStatus.CONFLICT:
        target = _lookup(ProjectExplainLookupVariant.CONFLICT)
    return ProjectExplainCheckedEvidence(
        target_lookup=target,
        provider_domain_complete=(
            provider.variant is not ProjectExplainLookupVariant.UNKNOWN
        ),
        provider_unknown_reason=None,
        provider_lookup=provider,
    )


def _five_status_authority(
    root: Path,
) -> tuple[
    ProjectExplainPackageRequirementProjection,
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
]:
    first, second, third = inspection_slice._unique_supported_provider_facts()[:3]
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    unknown_key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="signature",
        dialect="postgresql",
        extension="PostGIS",
    )
    satisfied = inspection_slice._fact(first.key)
    unsupported = inspection_slice._fact(
        second.key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    absent = inspection_slice._fact(absent_key)
    unknown = inspection_slice._fact(unknown_key)
    conflict_supported = inspection_slice._fact(
        third.key,
        reference="conflict supported",
    )
    conflict_unsupported = inspection_slice._fact(
        third.key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="conflict unsupported",
    )
    base = checking_slice.slice4._base(
        facts=(satisfied, unsupported, absent, unknown, conflict_supported)
    )
    overlay = checking_slice.slice4._overlay(
        "overlay",
        base.profile,
        facts=(conflict_unsupported,),
    )
    composition = inspection_slice._success(base, (overlay,))
    requirements = slice3._requirements(
        "dependency",
        "requirements",
        first.key,
        second.key,
        absent_key,
        unknown_key,
        third.key,
    )
    return _authority(
        root,
        (requirements, None),
        (inspection_slice._context(0, composition),),
    )


def test_exact_vocabularies_fields_immutability_and_private_surface() -> None:
    expected_enums = {
        ProjectExplainEvaluationState: (
            ("UNDECLARED", "undeclared"),
            ("BLOCKED", "blocked"),
            ("CHECKED", "checked"),
        ),
        ProjectExplainCheckedStatus: (
            ("SATISFIED", "satisfied"),
            ("UNSUPPORTED", "unsupported"),
            ("ABSENT", "absent"),
            ("UNKNOWN", "unknown"),
            ("CONFLICT", "conflict"),
        ),
        ProjectExplainProfileKind: (("BASE", "base"), ("OVERLAY", "overlay")),
        ProjectExplainProfileTargetKind: (
            ("DATABASE", "database"),
            ("EXTENSION", "extension"),
        ),
        ProjectExplainAvailabilityOwnerKind: (
            ("COMPILER", "compiler"),
            ("PROJECT", "project"),
        ),
        ProjectExplainMatrixBlockerKind: (
            (
                "PROFILE_NOT_DECLARED_AVAILABLE",
                "profile_not_declared_available",
            ),
            ("PROFILE_AUTHORITY_MISMATCH", "profile_authority_mismatch"),
        ),
        ProjectExplainLookupVariant: (
            ("FOUND", "found"),
            ("ABSENT", "absent"),
            ("UNKNOWN", "unknown"),
            ("CONFLICT", "conflict"),
        ),
        ProjectExplainCapabilitySupport: (
            ("SUPPORTED", "supported"),
            ("EXPLICITLY_UNSUPPORTED", "explicitly_unsupported"),
        ),
    }
    for enumeration, expected in expected_enums.items():
        assert tuple((member.name, member.value) for member in enumeration) == expected

    expected_fields: dict[type[Any], tuple[str, ...]] = {
        ProjectExplainCapabilityProfile: (
            "namespace",
            "name",
            "profile_release",
            "kind",
            "target_kind",
            "database_family",
            "target_release",
            "extension_identity",
            "extension_release",
        ),
        ProjectExplainEvaluatedTarget: (
            "position",
            "database_family",
            "database_release",
            "base_profile",
            "supplied_overlays",
            "dependency_order",
        ),
        ProjectExplainAvailabilityOccurrence: (
            "owner_kind",
            "owner_position",
            "project_path",
            "profile",
        ),
        ProjectExplainMatrixBlocker: (
            "kind",
            "selected_profile",
            "bucket_profile",
            "bucket_occurrences",
        ),
        ProjectExplainPackageTargetEvaluation: (
            "package_position",
            "target_position",
            "state",
            "evidence_posture",
            "availability",
            "blockers",
        ),
        ProjectExplainLookupSummary: ("variant", "reason", "supports"),
        ProjectExplainCheckedEvidence: (
            "target_lookup",
            "provider_domain_complete",
            "provider_unknown_reason",
            "provider_lookup",
        ),
        ProjectExplainMatrixCell: (
            "target_position",
            "state",
            "checked_status",
            "evidence_posture",
            "checked_evidence",
        ),
        ProjectExplainMatrixRow: ("requirement_position", "cells"),
        ProjectExplainRequirementTargetMatrix: (
            "targets",
            "package_target_evaluations",
            "rows",
        ),
    }
    for carrier, expected in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(field.name for field in fields(carrier)) == expected
        assert "__dict__" not in cast(Any, carrier).__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )

    profile = _simple_profile()
    with pytest.raises(FrozenInstanceError):
        profile.name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(profile, profile_release=cast(Any, 1))
    with pytest.raises(TypeError):
        ProjectExplainMatrixRow(requirement_position=cast(Any, True), cells=())
    with pytest.raises(TypeError):
        ProjectExplainMatrixRow(requirement_position=0, cells=cast(Any, []))

    assert project_explain_package.__all__ == projection_module.__all__ == ()
    for public_module in (pietto, project_package, metadata_package, semantic_package):
        for name in expected_fields:
            assert not hasattr(public_module, name.__name__)


@pytest.mark.parametrize(
    ("status", "posture"),
    (
        (
            ProjectExplainCheckedStatus.SATISFIED,
            ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION,
        ),
        (
            ProjectExplainCheckedStatus.UNSUPPORTED,
            ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION,
        ),
        (
            ProjectExplainCheckedStatus.ABSENT,
            ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION,
        ),
        (
            ProjectExplainCheckedStatus.UNKNOWN,
            ProjectExplainEvidencePosture.UNAVAILABLE,
        ),
        (
            ProjectExplainCheckedStatus.CONFLICT,
            ProjectExplainEvidencePosture.CONFLICTING,
        ),
    ),
)
def test_checked_status_algebra_and_posture_are_exact(
    status: ProjectExplainCheckedStatus,
    posture: ProjectExplainEvidencePosture,
) -> None:
    cell = ProjectExplainMatrixCell(
        target_position=0,
        state=ProjectExplainEvaluationState.CHECKED,
        checked_status=status,
        evidence_posture=posture,
        checked_evidence=_evidence_for(status),
    )
    assert cell.checked_status is status
    with pytest.raises(ValueError, match="posture"):
        replace(
            cell,
            evidence_posture=ProjectExplainEvidencePosture.SOURCE_FACT,
        )
    with pytest.raises(ValueError, match="disagrees"):
        replace(
            cell,
            checked_status=(
                ProjectExplainCheckedStatus.UNKNOWN
                if status is not ProjectExplainCheckedStatus.UNKNOWN
                else ProjectExplainCheckedStatus.SATISFIED
            ),
            evidence_posture=(
                ProjectExplainEvidencePosture.UNAVAILABLE
                if status is not ProjectExplainCheckedStatus.UNKNOWN
                else ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
            ),
        )


def test_state_status_separation_and_malformed_evidence_fail_closed() -> None:
    with pytest.raises(ValueError, match="UNDECLARED"):
        ProjectExplainMatrixCell(
            target_position=0,
            state=ProjectExplainEvaluationState.UNDECLARED,
            checked_status=None,
            evidence_posture=ProjectExplainEvidencePosture.UNAVAILABLE,
            checked_evidence=None,
        )
    blocked = ProjectExplainMatrixCell(
        target_position=0,
        state=ProjectExplainEvaluationState.BLOCKED,
        checked_status=None,
        evidence_posture=ProjectExplainEvidencePosture.UNAVAILABLE,
        checked_evidence=None,
    )
    with pytest.raises(ValueError, match="forbid"):
        replace(
            blocked,
            checked_status=ProjectExplainCheckedStatus.UNKNOWN,
            checked_evidence=_evidence_for(ProjectExplainCheckedStatus.UNKNOWN),
        )
    with pytest.raises(ValueError, match="FOUND"):
        ProjectExplainLookupSummary(
            variant=ProjectExplainLookupVariant.FOUND,
            reason="not_evidenced",
            supports=(ProjectExplainCapabilitySupport.SUPPORTED,),
        )
    with pytest.raises(ValueError, match="ABSENT"):
        ProjectExplainLookupSummary(
            variant=ProjectExplainLookupVariant.ABSENT,
            reason="not_evidenced",
            supports=(),
        )
    with pytest.raises(ValueError, match="CONFLICT"):
        ProjectExplainLookupSummary(
            variant=ProjectExplainLookupVariant.CONFLICT,
            reason="conflicting_evidence",
            supports=(ProjectExplainCapabilitySupport.SUPPORTED,),
        )
    with pytest.raises(TypeError, match="exact bool"):
        replace(
            _evidence_for(ProjectExplainCheckedStatus.SATISFIED),
            provider_domain_complete=cast(Any, 1),
        )
    profile = _simple_profile()
    occurrence = ProjectExplainAvailabilityOccurrence(
        owner_kind=ProjectExplainAvailabilityOwnerKind.COMPILER,
        owner_position=0,
        project_path=None,
        profile=profile,
    )
    with pytest.raises(ValueError, match="forbid bucket"):
        ProjectExplainMatrixBlocker(
            kind=ProjectExplainMatrixBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
            selected_profile=profile,
            bucket_profile=profile,
            bucket_occurrences=(occurrence,),
        )
    with pytest.raises(ValueError, match="require bucket"):
        ProjectExplainMatrixBlocker(
            kind=ProjectExplainMatrixBlockerKind.PROFILE_AUTHORITY_MISMATCH,
            selected_profile=profile,
            bucket_profile=None,
            bucket_occurrences=(),
        )


def test_five_checked_statuses_project_without_rechecking(tmp_path: Path) -> None:
    package_projection, package_facts, capability_facts = _five_status_authority(
        tmp_path
    )
    matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )

    assert len(matrix.targets) == 1
    assert tuple(
        (evaluation.package_position, evaluation.target_position, evaluation.state)
        for evaluation in matrix.package_target_evaluations
    ) == (
        (0, 0, ProjectExplainEvaluationState.CHECKED),
        (1, 0, ProjectExplainEvaluationState.UNDECLARED),
    )
    assert tuple(
        cast(ProjectExplainCheckedStatus, row.cells[0].checked_status)
        for row in matrix.rows
    ) == tuple(ProjectExplainCheckedStatus)
    assert tuple(row.requirement_position for row in matrix.rows) == tuple(range(5))
    assert all(row.cells[0].target_position == 0 for row in matrix.rows)

    satisfied, unsupported, absent, unknown, conflict = tuple(
        cast(ProjectExplainCheckedEvidence, row.cells[0].checked_evidence)
        for row in matrix.rows
    )
    assert satisfied.provider_lookup.variant is ProjectExplainLookupVariant.FOUND
    assert unsupported.target_lookup.supports == (
        ProjectExplainCapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert absent.provider_lookup.reason == "no_catalog_entry"
    assert unknown.provider_lookup.reason == "not_evidenced"
    assert conflict.target_lookup.supports == (
        ProjectExplainCapabilitySupport.SUPPORTED,
        ProjectExplainCapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert matrix.rows[3].cells[0].evidence_posture is (
        ProjectExplainEvidencePosture.UNAVAILABLE
    )
    assert matrix.rows[4].cells[0].evidence_posture is (
        ProjectExplainEvidencePosture.CONFLICTING
    )


def test_target_order_profile_order_availability_and_multiplicity_are_exact(
    tmp_path: Path,
) -> None:
    base = checking_slice.slice4._base(
        "z-base",
        profile_release="base release",
        target_release="17",
    )
    parent = checking_slice.slice4._overlay(
        "parent",
        base.profile,
        target_release="17",
    )
    child = checking_slice.slice4._overlay(
        "child",
        parent.profile,
        target_release="17",
    )
    composition = inspection_slice._success(base, (child, parent))
    availability = build_declared_capability_profile_availability(
        checking_slice.slice5._compiler_ledger(base),
        checking_slice.slice5._project_ledger(
            ProjectRoot("logical/project"),
            parent,
            child,
        ),
    )
    assert isinstance(availability, DeclaredCapabilityProfileAvailabilityReady)
    first = inspection_slice._context(0, composition, availability)

    duplicate_base = checking_slice.slice4._base(
        "z-base",
        profile_release="base release",
        target_release="17",
    )
    duplicate_parent = checking_slice.slice4._overlay(
        "parent",
        duplicate_base.profile,
        target_release="17",
    )
    duplicate_child = checking_slice.slice4._overlay(
        "child",
        duplicate_parent.profile,
        target_release="17",
    )
    duplicate_composition = inspection_slice._success(
        duplicate_base,
        (duplicate_child, duplicate_parent),
    )
    duplicate_availability = build_declared_capability_profile_availability(
        checking_slice.slice5._compiler_ledger(duplicate_base),
        checking_slice.slice5._project_ledger(
            ProjectRoot("logical/project"),
            duplicate_parent,
            duplicate_child,
        ),
    )
    assert isinstance(
        duplicate_availability,
        DeclaredCapabilityProfileAvailabilityReady,
    )
    second = inspection_slice._context(
        1,
        duplicate_composition,
        duplicate_availability,
    )
    package_projection, package_facts, capability_facts = _authority(
        tmp_path,
        (None, slice3._requirements("root", "empty")),
        (first, second),
    )
    matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )

    assert tuple(target.position for target in matrix.targets) == (0, 1)
    assert matrix.targets[0].base_profile == matrix.targets[1].base_profile
    assert tuple(profile.name for profile in matrix.targets[0].supplied_overlays) == (
        "child",
        "parent",
    )
    assert tuple(profile.name for profile in matrix.targets[0].dependency_order) == (
        "z-base",
        "parent",
        "child",
    )
    assert tuple(
        (occurrence.owner_kind, occurrence.owner_position)
        for occurrence in matrix.package_target_evaluations[0].availability
    ) == (
        (ProjectExplainAvailabilityOwnerKind.COMPILER, 0),
        (ProjectExplainAvailabilityOwnerKind.PROJECT, 0),
        (ProjectExplainAvailabilityOwnerKind.PROJECT, 1),
    )
    assert tuple(
        occurrence.project_path
        for occurrence in matrix.package_target_evaluations[0].availability
    ) == (
        None,
        ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value="logical/project",
        ),
        ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value="logical/project",
        ),
    )
    assert tuple(
        evaluation.state for evaluation in matrix.package_target_evaluations
    ) == (
        ProjectExplainEvaluationState.UNDECLARED,
        ProjectExplainEvaluationState.UNDECLARED,
        ProjectExplainEvaluationState.CHECKED,
        ProjectExplainEvaluationState.CHECKED,
    )
    assert matrix.rows == ()


def test_blockers_and_declared_empty_remain_distinct_from_undeclared(
    tmp_path: Path,
) -> None:
    base = checking_slice.slice4._base()
    overlay = checking_slice.slice4._overlay("overlay", base.profile)
    composition = inspection_slice._success(base, (overlay,))
    foreign_base = checking_slice.slice4._base()
    blocked = inspection_slice._context(
        1,
        composition,
        checking_slice._availability(composition, foreign_base),
    )
    checked_composition = checking_slice._composition()
    checked = inspection_slice._context(0, checked_composition)
    package_projection, package_facts, capability_facts = _authority(
        tmp_path,
        (None, slice3._requirements("root", "empty")),
        (checked, blocked),
    )
    matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )

    assert tuple(
        evaluation.state for evaluation in matrix.package_target_evaluations
    ) == (
        ProjectExplainEvaluationState.UNDECLARED,
        ProjectExplainEvaluationState.UNDECLARED,
        ProjectExplainEvaluationState.CHECKED,
        ProjectExplainEvaluationState.BLOCKED,
    )
    blocked_evaluation = matrix.package_target_evaluations[-1]
    assert blocked_evaluation.evidence_posture is (
        ProjectExplainEvidencePosture.CONFLICTING
    )
    assert tuple(blocker.kind for blocker in blocked_evaluation.blockers) == (
        ProjectExplainMatrixBlockerKind.PROFILE_AUTHORITY_MISMATCH,
        ProjectExplainMatrixBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE,
    )
    assert blocked_evaluation.blockers[0].bucket_profile is not None
    assert len(blocked_evaluation.blockers[0].bucket_occurrences) == 1
    assert blocked_evaluation.blockers[1].bucket_profile is None
    assert blocked_evaluation.blockers[1].bucket_occurrences == ()
    assert matrix.rows == ()


def test_empty_denominator_has_rows_without_synthetic_results(tmp_path: Path) -> None:
    requirements = slice3._requirements(
        "dependency",
        "requirements",
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int"),
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Text"),
    )
    context = inspection_slice._context(0, checking_slice._composition())
    package_projection, _package_facts, _capability_facts = _authority(
        tmp_path,
        (requirements, None),
        (context,),
    )
    matrix = _project_empty_requirement_target_matrix(package_projection)

    assert matrix.targets == ()
    assert matrix.package_target_evaluations == ()
    assert tuple(row.requirement_position for row in matrix.rows) == (0, 1)
    assert tuple(row.cells for row in matrix.rows) == ((), ())


def test_common_context_identity_count_and_package_authority_fail_closed(
    tmp_path: Path,
) -> None:
    package_facts = package_slice._simple_inspection(
        tmp_path,
        root_path=".",
        dependency_path="dep",
        authored_path="dep",
    )
    collections = (None, None)
    first_context = inspection_slice._context(0, checking_slice._composition())
    foreign_equal_context = inspection_slice._context(
        0,
        checking_slice._composition(),
    )
    inspections: list[CapabilityInspectionFactSet] = []
    for package, context in zip(
        package_facts.inspection.packages,
        (first_context, foreign_equal_context),
        strict=True,
    ):
        inspections.append(
            build_capability_inspection(
                build_package_capability_checking_matrix(
                    cast(LoadedPackage, package.entry.package),
                    None,
                    (context,),
                )
            )
        )
    capability_facts = tuple(inspections)
    package_projection = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    with pytest.raises(ValueError, match="same exact target authority"):
        _project_requirement_target_matrix(
            package_projection,
            package_facts,
            capability_facts,
        )

    shared = inspection_slice._context(0, checking_slice._composition())
    extra = inspection_slice._context(1, checking_slice._composition())
    mismatched: list[CapabilityInspectionFactSet] = []
    for position, package in enumerate(package_facts.inspection.packages):
        mismatched.append(
            build_capability_inspection(
                build_package_capability_checking_matrix(
                    cast(LoadedPackage, package.entry.package),
                    None,
                    (shared, extra) if position == 0 else (shared,),
                )
            )
        )
    mismatched_facts = tuple(mismatched)
    mismatched_projection = _project_package_requirement_provenance(
        package_facts,
        mismatched_facts,
    )
    with pytest.raises(ValueError, match="same target count"):
        _project_requirement_target_matrix(
            mismatched_projection,
            package_facts,
            mismatched_facts,
        )

    valid_facts = _capability_facts(package_facts, collections, (shared,))
    valid_projection = _project_package_requirement_provenance(
        package_facts,
        valid_facts,
    )
    foreign_facts = _capability_facts(
        package_facts,
        (None, slice3._requirements("root", "empty")),
        (shared,),
    )
    foreign_projection = _project_package_requirement_provenance(
        package_facts,
        foreign_facts,
    )
    with pytest.raises(ValueError, match="same exact Slice 3 projection"):
        _project_requirement_target_matrix(
            foreign_projection,
            package_facts,
            valid_facts,
        )
    with pytest.raises(ValueError, match="package authority order"):
        _project_requirement_target_matrix(
            valid_projection,
            package_facts,
            tuple(reversed(valid_facts)),
        )


def test_private_cell_graft_and_public_internal_references_fail_closed(
    tmp_path: Path,
) -> None:
    package_projection, package_facts, capability_facts = _five_status_authority(
        tmp_path
    )
    foreign_context = inspection_slice._context(0, checking_slice._composition())
    foreign_facts = _capability_facts(
        package_facts,
        (None, None),
        (foreign_context,),
    )
    root_target = capability_facts[1].inspection.targets[0]
    original_profile = root_target.base_profile
    object.__setattr__(
        root_target,
        "base_profile",
        foreign_facts[1].inspection.targets[0].base_profile,
    )
    try:
        with pytest.raises(ValueError, match="foreign inspected base profile"):
            _project_requirement_target_matrix(
                package_projection,
                package_facts,
                capability_facts,
            )
    finally:
        object.__setattr__(root_target, "base_profile", original_profile)

    inspected_check = cast(
        Any,
        capability_facts[0].inspection.requirements[0].cells[0].check,
    )
    original_completeness = inspected_check.provider_domain_complete
    object.__setattr__(inspected_check, "provider_domain_complete", False)
    try:
        with pytest.raises(ValueError, match="checked authority"):
            _project_requirement_target_matrix(
                package_projection,
                package_facts,
                capability_facts,
            )
    finally:
        object.__setattr__(
            inspected_check,
            "provider_domain_complete",
            original_completeness,
        )

    private_cell = capability_facts[0].inspection.requirements[0].cells[0]
    original_check = private_cell.check
    object.__setattr__(private_cell, "check", None)
    try:
        with pytest.raises(ValueError, match="foreign inspected check"):
            _project_requirement_target_matrix(
                package_projection,
                package_facts,
                capability_facts,
            )
    finally:
        object.__setattr__(private_cell, "check", original_check)

    matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )
    with pytest.raises(ValueError, match="one cell per target"):
        replace(matrix, rows=(replace(matrix.rows[0], cells=()), *matrix.rows[1:]))
    with pytest.raises(ValueError, match="package by target order"):
        replace(
            matrix,
            package_target_evaluations=tuple(
                reversed(matrix.package_target_evaluations)
            ),
        )
    with pytest.raises(ValueError, match="dense and ordered"):
        replace(
            matrix,
            rows=(replace(matrix.rows[0], requirement_position=1), *matrix.rows[1:]),
        )


def _walk(value: object) -> tuple[object, ...]:
    values = [value]
    if is_dataclass(value) and not isinstance(value, type):
        for declared in fields(value):
            values.extend(_walk(getattr(value, declared.name)))
    elif isinstance(value, tuple):
        for item in value:
            values.extend(_walk(item))
    return tuple(values)


def test_output_is_detached_private_and_has_no_retained_later_surface(
    tmp_path: Path,
) -> None:
    package_projection, package_facts, capability_facts = _five_status_authority(
        tmp_path
    )
    matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )
    values = _walk(matrix)
    forbidden_names = {
        "CapabilityInspectionFactSet",
        "CapabilityInspection",
        "PackageCapabilityCheckingMatrix",
        "CapabilityCheckingTargetContext",
        "CapabilityCheckingTargetColumn",
        "CapabilityCheckingMatrixRow",
        "CapabilityCheckingMatrixCell",
        "CapabilityRequirementCheck",
        "StaticCapabilityProfile",
        "CapabilityFact",
        "CapabilityEvidence",
        "Found",
        "Absent",
        "Unknown",
        "Conflict",
        "Path",
    }
    assert not {type(value).__name__ for value in values} & forbidden_names
    source = _read(SOURCE)
    for forbidden in (
        "lookup_capability(",
        "check_package_capability_requirements(",
        "build_package_capability_checking_matrix(",
        "compose_capability_profiles(",
        "extension_catalog",
        "catalog_coordinate",
        "content_digest",
        "ProjectExplainPortability",
        "ProjectExplainPayload",
        "CrossSectionReference",
        "import json",
        "serialize",
        "render_",
        "argparse",
        "pathlib",
        "import os",
        "open(",
        "import requests",
        "socket",
    ):
        assert forbidden not in source
    for name in (
        "ProjectExplainCatalogCoordinate",
        "ProjectExplainPortability",
        "ProjectExplainPayload",
        "ProjectExplainCrossSectionReference",
        "project_explain_to_json",
        "render_project_explain",
    ):
        assert not hasattr(projection_module, name)


def test_spec_and_slice5_handoff_are_exact() -> None:
    document = _read(SPEC)
    assert "PHASE58_SLICE4_SELF_OWNED_OPEN = 0" in document
    normalized = " ".join(document.split())
    for required in (
        "PackageCapabilityCheckingMatrix",
        "no second checker",
        "explicitly empty evaluated target denominator",
        "UNDECLARED",
        "BLOCKED",
        "CHECKED",
        "SATISFIED",
        "UNSUPPORTED",
        "ABSENT",
        "UNKNOWN",
        "CONFLICT",
        "Slice 5 remains `UNSTARTED / NOT AUTHORIZED`",
    ):
        assert required in normalized

    package_smoke = _read(PACKAGE_SMOKE)
    for required in (
        'f"{prefix}/_project_explain/compatibility_matrix_projection.py"',
        '"installed private project explain compatibility matrix projection import"',
        "import pietto._project_explain.compatibility_matrix_projection",
    ):
        assert required in package_smoke
