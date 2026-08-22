"""Private capability inspection and deterministic canonical representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar, cast

from pietto._project.capability_availability import (
    CapabilityProfileAvailabilityOccurrence,
    CompilerCapabilityProfileAvailabilityAuthority,
    DeclaredCapabilityProfileReferenceBucket,
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
    PackageCapabilityRequirementsUndeclared,
    SelectedProfileAvailabilityBlocker,
    SelectedProfileAvailabilityBlockerKind,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingMatrixCell,
    CapabilityCheckingMatrixRow,
    CapabilityCheckingTargetColumn,
    CapabilityCheckingTargetContext,
    PackageCapabilityCheckingMatrix,
)
from pietto._project.capability_pure_boundary import (
    CAPABILITY_PURE_ABSENT,
    CapabilityPureDocument,
    CapabilityPureField,
    CapabilityPureRecord,
    CapabilityPureStatus,
    CapabilityPureValue,
    capability_pure_boolean,
    capability_pure_enumeration,
    capability_pure_integer,
    capability_pure_text,
    evaluate_capability_document,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_load_plan import (
    LoadedDependencyPackage,
    LoadedPackage,
    _package_content_digest,
    _package_coordinate,
)
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    EffectiveCapabilityProfileFactOccurrence,
)
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import Absent, Conflict, Found, Unknown
from pietto.semantic.capability_profiles import (
    CapabilityProfileKind,
    CapabilityProfileSchemaVersion,
    CapabilityProfileTargetKind,
    StaticCapabilityProfile,
)

__all__: tuple[str, ...] = ()


class CapabilityInspectionFormat(StrEnum):
    CAPABILITY_INSPECTION_V1 = "pietto.capability-inspection.v1"


class CapabilityInspectionPackageRole(StrEnum):
    ROOT = "root"
    DEPENDENCY = "dependency"


class CapabilityInspectionRequirementDeclaration(StrEnum):
    UNDECLARED = "undeclared"
    DECLARED = "declared"


class CapabilityInspectionColumnVariant(StrEnum):
    UNDECLARED = "undeclared"
    BLOCKED = "blocked"
    CHECKED = "checked"


class CapabilityInspectionAvailabilityOwnerKind(StrEnum):
    COMPILER = "compiler"
    PROJECT = "project"


class CapabilityInspectionProfileOrder(StrEnum):
    BASE = "base"
    SUPPLIED_OVERLAY = "supplied_overlay"
    DEPENDENCY = "dependency"


class CapabilityInspectionLookupVariant(StrEnum):
    FOUND = "found"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionPackage:
    role: CapabilityInspectionPackageRole
    namespace: str
    name: str
    release: str
    content_digest: str
    package: LoadedPackage = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionPackage:
        raise TypeError("Inspected capability packages require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionKey:
    domain: CapabilityDomain
    subject: str | None
    operation: str | None
    operands: tuple[str, ...]
    context: str | None
    dialect: str | None
    extension: str | None
    key: CapabilityKey = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionKey:
        raise TypeError("Inspected capability keys require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionEvidence:
    source: CapabilityEvidenceSource
    source_path: str
    source_reference: str
    reason: CapabilityReasonCode | None
    dialect: str | None
    backend: str | None
    extension: str | None
    evidence: CapabilityEvidence = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionEvidence:
        raise TypeError("Inspected capability evidence requires canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionFact:
    key: CapabilityInspectionKey
    support: CapabilitySupport
    disposition_kind: CapabilityDispositionKind
    disposition_owner: str | None
    disposition_reason: str | None
    evidence: tuple[CapabilityInspectionEvidence, ...]
    fact: CapabilityFact = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionFact:
        raise TypeError("Inspected capability facts require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionProfile:
    schema_version: CapabilityProfileSchemaVersion
    namespace: str
    name: str
    profile_release: str
    kind: CapabilityProfileKind
    target_kind: CapabilityProfileTargetKind
    database_family: str
    target_release: str
    extension_identity: str | None
    extension_release: str | None
    profile: StaticCapabilityProfile = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionProfile:
        raise TypeError("Inspected capability profiles require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionAvailabilityOccurrence:
    owner_kind: CapabilityInspectionAvailabilityOwnerKind
    owner_position: int
    project_path: str | None
    profile: CapabilityInspectionProfile
    occurrence: CapabilityProfileAvailabilityOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionAvailabilityOccurrence:
        raise TypeError(
            "Inspected capability availability requires canonical construction"
        )


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionLookup:
    variant: CapabilityInspectionLookupVariant
    reason: CapabilityReasonCode | None
    facts: tuple[CapabilityInspectionFact, ...]
    result: Found | Absent | Unknown | Conflict = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionLookup:
        raise TypeError("Inspected capability lookups require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionTargetOccurrence:
    position: int
    profile_position: int
    profile: CapabilityInspectionProfile
    profile_fact_position: int
    fact: CapabilityInspectionFact
    occurrence: EffectiveCapabilityProfileFactOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionTargetOccurrence:
        raise TypeError("Inspected target occurrences require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionCheck:
    target_occurrences: tuple[CapabilityInspectionTargetOccurrence, ...]
    target_lookup: CapabilityInspectionLookup
    provider_domain_complete: bool
    provider_unknown_reason: CapabilityReasonCode | None
    provider_lookup: CapabilityInspectionLookup
    status: CapabilityRequirementStatus
    check: CapabilityRequirementCheck = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionCheck:
        raise TypeError("Inspected capability checks require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionBlocker:
    kind: SelectedProfileAvailabilityBlockerKind
    selected_profile: CapabilityInspectionProfile
    bucket_profile: CapabilityInspectionProfile | None
    bucket_occurrences: tuple[CapabilityInspectionAvailabilityOccurrence, ...]
    blocker: SelectedProfileAvailabilityBlocker = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionBlocker:
        raise TypeError("Inspected capability blockers require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionColumn:
    position: int
    variant: CapabilityInspectionColumnVariant
    base_profile: CapabilityInspectionProfile
    supplied_overlays: tuple[CapabilityInspectionProfile, ...]
    dependency_order: tuple[CapabilityInspectionProfile, ...]
    availability: tuple[CapabilityInspectionAvailabilityOccurrence, ...]
    blockers: tuple[CapabilityInspectionBlocker, ...]
    column: CapabilityCheckingTargetColumn = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionColumn:
        raise TypeError("Inspected capability columns require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionCell:
    column_position: int
    check: CapabilityInspectionCheck | None
    cell: CapabilityCheckingMatrixCell = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspectionCell:
        raise TypeError("Inspected capability cells require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspectionRequirement:
    position: int
    key: CapabilityInspectionKey
    cells: tuple[CapabilityInspectionCell, ...]
    row: CapabilityCheckingMatrixRow = field(repr=False, compare=False, hash=False)

    def __new__(cls) -> CapabilityInspectionRequirement:
        raise TypeError(
            "Inspected capability requirements require canonical construction"
        )


@dataclass(frozen=True, slots=True, init=False)
class CapabilityInspection:
    format: CapabilityInspectionFormat
    package: CapabilityInspectionPackage
    requirement_declaration: CapabilityInspectionRequirementDeclaration
    requirement_namespace: str | None
    requirement_name: str | None
    target_count: int
    requirement_count: int
    targets: tuple[CapabilityInspectionColumn, ...]
    requirements: tuple[CapabilityInspectionRequirement, ...]
    matrix: PackageCapabilityCheckingMatrix = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __new__(cls) -> CapabilityInspection:
        raise TypeError("Capability inspections require canonical construction")


_Derived = TypeVar("_Derived")


def _derived(carrier: type[_Derived], /, **attributes: object) -> _Derived:
    derived = object.__new__(carrier)
    for name, value in attributes.items():
        object.__setattr__(derived, name, value)
    return cast(_Derived, derived)


def _project_package(package: LoadedPackage) -> CapabilityInspectionPackage:
    coordinate = _package_coordinate(package)
    return _derived(
        CapabilityInspectionPackage,
        role=(
            CapabilityInspectionPackageRole.ROOT
            if type(package) is LoadedRootPackage
            else CapabilityInspectionPackageRole.DEPENDENCY
        ),
        namespace=coordinate.identity.namespace,
        name=coordinate.identity.name,
        release=coordinate.exact_version,
        content_digest=_package_content_digest(package),
        package=package,
    )


def _project_key(key: CapabilityKey) -> CapabilityInspectionKey:
    return _derived(
        CapabilityInspectionKey,
        domain=key.domain,
        subject=key.subject,
        operation=key.operation,
        operands=key.operands,
        context=key.context,
        dialect=key.dialect,
        extension=key.extension,
        key=key,
    )


def _project_evidence(evidence: CapabilityEvidence) -> CapabilityInspectionEvidence:
    return _derived(
        CapabilityInspectionEvidence,
        source=evidence.source,
        source_path=evidence.source_path,
        source_reference=evidence.source_reference,
        reason=evidence.reason,
        dialect=evidence.dialect,
        backend=evidence.backend,
        extension=evidence.extension,
        evidence=evidence,
    )


def _project_fact(fact: CapabilityFact) -> CapabilityInspectionFact:
    return _derived(
        CapabilityInspectionFact,
        key=_project_key(fact.key),
        support=fact.support,
        disposition_kind=fact.disposition.kind,
        disposition_owner=fact.disposition.owner,
        disposition_reason=fact.disposition.reason,
        evidence=tuple(_project_evidence(item) for item in fact.evidence),
        fact=fact,
    )


def _project_profile(profile: StaticCapabilityProfile) -> CapabilityInspectionProfile:
    target = profile.target
    return _derived(
        CapabilityInspectionProfile,
        schema_version=profile.schema_version,
        namespace=profile.profile.identity.namespace,
        name=profile.profile.identity.name,
        profile_release=profile.profile.release,
        kind=profile.kind,
        target_kind=target.kind,
        database_family=target.family,
        target_release=target.release,
        extension_identity=target.extension_identity,
        extension_release=target.extension_release,
        profile=profile,
    )


def _project_availability_occurrence(
    occurrence: CapabilityProfileAvailabilityOccurrence,
) -> CapabilityInspectionAvailabilityOccurrence:
    owner = occurrence.owner
    if owner is CompilerCapabilityProfileAvailabilityAuthority.COMPILER:
        owner_kind = CapabilityInspectionAvailabilityOwnerKind.COMPILER
        project_path = None
    else:
        if type(owner) is not ProjectRoot:
            raise ValueError("Capability inspection requires exact availability owner")
        owner_kind = CapabilityInspectionAvailabilityOwnerKind.PROJECT
        project_path = owner.path
    return _derived(
        CapabilityInspectionAvailabilityOccurrence,
        owner_kind=owner_kind,
        owner_position=occurrence.position,
        project_path=project_path,
        profile=_project_profile(occurrence.profile),
        occurrence=occurrence,
    )


def _project_lookup(
    result: Found | Absent | Unknown | Conflict,
) -> CapabilityInspectionLookup:
    if type(result) is Found:
        variant = CapabilityInspectionLookupVariant.FOUND
        reason = None
        facts = (_project_fact(result.fact),)
    elif type(result) is Absent:
        variant = CapabilityInspectionLookupVariant.ABSENT
        reason = result.reason
        facts = ()
    elif type(result) is Unknown:
        variant = CapabilityInspectionLookupVariant.UNKNOWN
        reason = result.reason
        facts = ()
    elif type(result) is Conflict:
        variant = CapabilityInspectionLookupVariant.CONFLICT
        reason = result.reason
        facts = tuple(_project_fact(fact) for fact in result.evidence)
    else:
        raise ValueError("Capability inspection requires an exact lookup result")
    return _derived(
        CapabilityInspectionLookup,
        variant=variant,
        reason=reason,
        facts=facts,
        result=result,
    )


def _project_target_occurrence(
    position: int,
    occurrence: EffectiveCapabilityProfileFactOccurrence,
    composition: CapabilityProfileCompositionSuccess,
) -> CapabilityInspectionTargetOccurrence:
    profile_position = next(
        candidate_position
        for candidate_position, profile in enumerate(composition.dependency_order)
        if profile is occurrence.profile
    )
    return _derived(
        CapabilityInspectionTargetOccurrence,
        position=position,
        profile_position=profile_position,
        profile=_project_profile(occurrence.profile),
        profile_fact_position=occurrence.occurrence.position,
        fact=_project_fact(occurrence.fact),
        occurrence=occurrence,
    )


def _project_check(
    check: CapabilityRequirementCheck,
    composition: CapabilityProfileCompositionSuccess,
) -> CapabilityInspectionCheck:
    target_occurrences = tuple(
        _project_target_occurrence(position, occurrence, composition)
        for position, occurrence in enumerate(check.target_occurrences)
    )
    return _derived(
        CapabilityInspectionCheck,
        target_occurrences=target_occurrences,
        target_lookup=_project_lookup(check.target_result),
        provider_domain_complete=check.provider_inputs.domain_complete,
        provider_unknown_reason=check.provider_inputs.unknown_reason,
        provider_lookup=_project_lookup(check.provider_result),
        status=check.status,
        check=check,
    )


def _project_blocker(
    blocker: SelectedProfileAvailabilityBlocker,
) -> CapabilityInspectionBlocker:
    bucket: DeclaredCapabilityProfileReferenceBucket | None = blocker.bucket
    return _derived(
        CapabilityInspectionBlocker,
        kind=blocker.kind,
        selected_profile=_project_profile(blocker.profile),
        bucket_profile=None if bucket is None else _project_profile(bucket.profile),
        bucket_occurrences=(
            ()
            if bucket is None
            else tuple(
                _project_availability_occurrence(occurrence)
                for occurrence in bucket.occurrences
            )
        ),
        blocker=blocker,
    )


def _project_column(
    column: CapabilityCheckingTargetColumn,
) -> CapabilityInspectionColumn:
    result = column.result
    if type(result) is PackageCapabilityRequirementsUndeclared:
        variant = CapabilityInspectionColumnVariant.UNDECLARED
        blockers: tuple[CapabilityInspectionBlocker, ...] = ()
    elif type(result) is PackageCapabilityRequirementsBlocked:
        variant = CapabilityInspectionColumnVariant.BLOCKED
        blockers = tuple(_project_blocker(blocker) for blocker in result.blockers)
    elif type(result) is PackageCapabilityRequirementsChecked:
        variant = CapabilityInspectionColumnVariant.CHECKED
        blockers = ()
    else:
        raise ValueError("Capability inspection requires an exact column result")
    composition = column.context.composition
    return _derived(
        CapabilityInspectionColumn,
        position=column.position,
        variant=variant,
        base_profile=_project_profile(composition.base),
        supplied_overlays=tuple(
            _project_profile(profile) for profile in composition.overlays
        ),
        dependency_order=tuple(
            _project_profile(profile) for profile in composition.dependency_order
        ),
        availability=tuple(
            _project_availability_occurrence(occurrence)
            for occurrence in column.context.availability.occurrences
        ),
        blockers=blockers,
        column=column,
    )


def _project_requirement(
    position: int,
    row: CapabilityCheckingMatrixRow,
) -> CapabilityInspectionRequirement:
    return _derived(
        CapabilityInspectionRequirement,
        position=position,
        key=_project_key(row.occurrence.key),
        cells=tuple(
            _derived(
                CapabilityInspectionCell,
                column_position=cell.column.position,
                check=(
                    None
                    if cell.check is None
                    else _project_check(cell.check, cell.column.context.composition)
                ),
                cell=cell,
            )
            for cell in row.cells
        ),
        row=row,
    )


def _derive_inspection(
    matrix: PackageCapabilityCheckingMatrix,
) -> CapabilityInspection:
    binding = matrix.binding
    requirement_declaration = (
        CapabilityInspectionRequirementDeclaration.UNDECLARED
        if binding is None
        else CapabilityInspectionRequirementDeclaration.DECLARED
    )
    identity = None if binding is None else binding.requirements.identity
    return _derived(
        CapabilityInspection,
        format=CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1,
        package=_project_package(matrix.package),
        requirement_declaration=requirement_declaration,
        requirement_namespace=None if identity is None else identity.namespace,
        requirement_name=None if identity is None else identity.name,
        target_count=len(matrix.columns),
        requirement_count=len(matrix.rows),
        targets=tuple(_project_column(column) for column in matrix.columns),
        requirements=tuple(
            _project_requirement(position, row)
            for position, row in enumerate(matrix.rows)
        ),
        matrix=matrix,
    )


def _validate_matrix(matrix: PackageCapabilityCheckingMatrix) -> None:
    if type(matrix) is not PackageCapabilityCheckingMatrix:
        raise TypeError("Capability inspection requires an exact canonical matrix")
    if type(matrix.package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise ValueError("Capability inspection requires an exact loaded package")
    binding = matrix.binding
    if binding is not None:
        if type(binding) is not PackageCapabilityRequirementBinding:
            raise ValueError("Capability inspection requires an exact binding")
        if binding.package is not matrix.package:
            raise ValueError("Capability inspection rejects foreign binding authority")
    if (
        type(matrix.contexts) is not tuple
        or not matrix.contexts
        or any(
            type(item) is not CapabilityCheckingTargetContext
            for item in matrix.contexts
        )
        or type(matrix.columns) is not tuple
        or len(matrix.columns) != len(matrix.contexts)
        or any(
            type(item) is not CapabilityCheckingTargetColumn for item in matrix.columns
        )
        or type(matrix.rows) is not tuple
        or any(type(item) is not CapabilityCheckingMatrixRow for item in matrix.rows)
    ):
        raise ValueError("Capability inspection requires exact matrix shape")
    for position, (context, column) in enumerate(
        zip(matrix.contexts, matrix.columns, strict=True)
    ):
        if (
            context.position != position
            or column.position != position
            or column.context is not context
            or column.result.package is not matrix.package
            or column.result.composition is not context.composition
            or column.result.availability is not context.availability
        ):
            raise ValueError("Capability inspection requires exact column authority")
        result = column.result
        if binding is None:
            if type(result) is not PackageCapabilityRequirementsUndeclared:
                raise ValueError("Undeclared inspection requires undeclared columns")
        elif (
            not isinstance(
                result,
                (
                    PackageCapabilityRequirementsBlocked,
                    PackageCapabilityRequirementsChecked,
                ),
            )
            or result.binding is not binding
        ):
            raise ValueError("Declared inspection requires exact binding authority")
    if binding is None:
        if matrix.rows:
            raise ValueError("Undeclared inspection forbids requirement rows")
        return
    occurrences = binding.requirements.occurrences
    if len(matrix.rows) != len(occurrences):
        raise ValueError("Declared inspection requires every requirement row")
    for requirement_position, (row, occurrence) in enumerate(
        zip(matrix.rows, occurrences, strict=True)
    ):
        if row.occurrence is not occurrence or len(row.cells) != len(matrix.columns):
            raise ValueError("Capability inspection requires exact row authority")
        for column_position, (cell, column) in enumerate(
            zip(row.cells, matrix.columns, strict=True)
        ):
            if (
                type(cell) is not CapabilityCheckingMatrixCell
                or cell.column is not column
                or cell.column.position != column_position
            ):
                raise ValueError("Capability inspection requires exact cell authority")
            result = column.result
            if type(result) is PackageCapabilityRequirementsChecked:
                if cell.check is not result.checks[requirement_position]:
                    raise ValueError("Checked inspection cells require exact checks")
            elif type(result) is PackageCapabilityRequirementsBlocked:
                if cell.check is not None:
                    raise ValueError("Blocked inspection cells forbid checks")
            else:
                raise ValueError("Declared inspection forbids undeclared columns")


@dataclass(frozen=True, slots=True, kw_only=True)
class _CapabilityInspectionAuthority:
    matrix: PackageCapabilityCheckingMatrix = field(
        repr=False,
        compare=False,
        hash=False,
    )
    inspection: CapabilityInspection = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    canonical_bytes: bytes = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        _validate_matrix(self.matrix)
        inspection = _derive_inspection(self.matrix)
        object.__setattr__(self, "inspection", inspection)
        object.__setattr__(
            self,
            "canonical_bytes",
            _serialize_capability_inspection(inspection),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityInspectionFactSet:
    inspection: CapabilityInspection
    canonical_bytes: bytes
    authority: _CapabilityInspectionAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.authority) is not _CapabilityInspectionAuthority:
            raise TypeError("Capability inspection facts require exact authority")
        if self.inspection is not self.authority.inspection:
            raise ValueError("Capability inspection facts reject a grafted inspection")
        if self.canonical_bytes is not self.authority.canonical_bytes:
            raise ValueError(
                "Capability inspection facts reject grafted canonical bytes"
            )


def build_capability_inspection(
    matrix: PackageCapabilityCheckingMatrix,
) -> CapabilityInspectionFactSet:
    """Derive one inspection and its bytes without recomputing matrix truth."""

    authority = _CapabilityInspectionAuthority(matrix=matrix)
    return CapabilityInspectionFactSet(
        inspection=authority.inspection,
        canonical_bytes=authority.canonical_bytes,
        authority=authority,
    )


type _EncodedField = tuple[str, CapabilityPureValue]
type _EncodedScope = tuple[_EncodedField, ...]


def _text(value: str) -> CapabilityPureValue:
    if type(value) is not str:
        raise TypeError("Canonical capability text must be exact text")
    return capability_pure_text(value)


def _enumeration(value: StrEnum) -> CapabilityPureValue:
    if not isinstance(value, StrEnum):
        raise TypeError("Canonical capability enumerations require exact enums")
    return capability_pure_enumeration(value.value)


def _integer(value: int) -> CapabilityPureValue:
    if type(value) is not int or value < 0:
        raise ValueError("Canonical capability integers must be non-negative")
    return capability_pure_integer(value)


def _boolean(value: bool) -> CapabilityPureValue:
    if type(value) is not bool:
        raise TypeError("Canonical capability booleans must be exact")
    return capability_pure_boolean(value)


def _optional_text(value: str | None) -> CapabilityPureValue:
    return CAPABILITY_PURE_ABSENT if value is None else _text(value)


def _optional_enumeration(value: StrEnum | None) -> CapabilityPureValue:
    return CAPABILITY_PURE_ABSENT if value is None else _enumeration(value)


def _record(
    records: list[CapabilityPureRecord],
    kind: str,
    *fields: _EncodedField,
) -> None:
    records.append(
        CapabilityPureRecord(
            kind=kind,
            fields=tuple(
                CapabilityPureField(key=key, value=value) for key, value in fields
            ),
        )
    )


def _profile_fields(profile: CapabilityInspectionProfile) -> _EncodedScope:
    return (
        ("schema", _enumeration(profile.schema_version)),
        ("namespace", _text(profile.namespace)),
        ("name", _text(profile.name)),
        ("profile_release", _text(profile.profile_release)),
        ("kind", _enumeration(profile.kind)),
        ("target_kind", _enumeration(profile.target_kind)),
        ("database_family", _text(profile.database_family)),
        ("target_release", _text(profile.target_release)),
        ("extension_identity", _optional_text(profile.extension_identity)),
        ("extension_release", _optional_text(profile.extension_release)),
    )


def _key_fields(key: CapabilityInspectionKey) -> _EncodedScope:
    return (
        ("domain", _enumeration(key.domain)),
        ("subject", _optional_text(key.subject)),
        ("operation", _optional_text(key.operation)),
        ("operands", _integer(len(key.operands))),
        ("context", _optional_text(key.context)),
        ("dialect", _optional_text(key.dialect)),
        ("extension", _optional_text(key.extension)),
    )


def _emit_key_operands(
    lines: list[CapabilityPureRecord],
    kind: str,
    scope: _EncodedScope,
    key: CapabilityInspectionKey,
) -> None:
    for position, operand in enumerate(key.operands):
        _record(
            lines,
            kind,
            *scope,
            ("operand", _integer(position)),
            ("value", _text(operand)),
        )


def _availability_fields(
    occurrence: CapabilityInspectionAvailabilityOccurrence,
) -> _EncodedScope:
    return (
        ("owner_kind", _enumeration(occurrence.owner_kind)),
        ("owner_position", _integer(occurrence.owner_position)),
        ("project_path", _optional_text(occurrence.project_path)),
        *_profile_fields(occurrence.profile),
    )


def _emit_fact(
    lines: list[CapabilityPureRecord],
    axis: str,
    scope: _EncodedScope,
    fact: CapabilityInspectionFact,
) -> None:
    _record(
        lines,
        f"{axis}_fact",
        *scope,
        *_key_fields(fact.key),
        ("support", _enumeration(fact.support)),
        ("disposition", _enumeration(fact.disposition_kind)),
        ("disposition_owner", _optional_text(fact.disposition_owner)),
        ("disposition_reason", _optional_text(fact.disposition_reason)),
        ("evidence", _integer(len(fact.evidence))),
    )
    _emit_key_operands(lines, f"{axis}_fact_operand", scope, fact.key)
    for position, evidence in enumerate(fact.evidence):
        _record(
            lines,
            f"{axis}_fact_evidence",
            *scope,
            ("evidence", _integer(position)),
            ("source", _enumeration(evidence.source)),
            ("source_path", _text(evidence.source_path)),
            ("source_reference", _text(evidence.source_reference)),
            ("reason", _optional_enumeration(evidence.reason)),
            ("dialect", _optional_text(evidence.dialect)),
            ("backend", _optional_text(evidence.backend)),
            ("extension", _optional_text(evidence.extension)),
        )


def _emit_profile(
    lines: list[CapabilityPureRecord],
    kind: str,
    scope: _EncodedScope,
    profile: CapabilityInspectionProfile,
) -> None:
    _record(lines, kind, *scope, *_profile_fields(profile))


def _serialize_capability_inspection(inspection: CapabilityInspection) -> bytes:
    document = _capability_pure_document(inspection)
    outcome = evaluate_capability_document(document)
    if outcome.status is not CapabilityPureStatus.OK or outcome.canonical_bytes is None:
        raise ValueError(
            "Canonical capability payload must evaluate exactly: "
            f"{outcome.status.value} at record {outcome.record_position} "
            f"field {outcome.field_position}"
        )
    return outcome.canonical_bytes


def _capability_pure_document(
    inspection: CapabilityInspection,
) -> CapabilityPureDocument:
    if type(inspection) is not CapabilityInspection:
        raise TypeError("Capability pure projection requires an inspection")
    lines: list[CapabilityPureRecord] = []
    _record(
        lines,
        "inspection",
        ("format", _enumeration(inspection.format)),
        ("declaration", _enumeration(inspection.requirement_declaration)),
        ("targets", _integer(inspection.target_count)),
        ("requirements", _integer(inspection.requirement_count)),
    )
    package = inspection.package
    _record(
        lines,
        "package",
        ("role", _enumeration(package.role)),
        ("namespace", _text(package.namespace)),
        ("name", _text(package.name)),
        ("release", _text(package.release)),
        ("content_digest", _text(package.content_digest)),
    )
    if inspection.requirement_declaration is (
        CapabilityInspectionRequirementDeclaration.DECLARED
    ):
        assert inspection.requirement_namespace is not None
        assert inspection.requirement_name is not None
        _record(
            lines,
            "requirements",
            ("namespace", _text(inspection.requirement_namespace)),
            ("name", _text(inspection.requirement_name)),
            ("count", _integer(inspection.requirement_count)),
        )
    for column in inspection.targets:
        target_scope = (("target", _integer(column.position)),)
        _record(
            lines,
            "target",
            *target_scope,
            ("variant", _enumeration(column.variant)),
            ("supplied_overlays", _integer(len(column.supplied_overlays))),
            ("dependency_profiles", _integer(len(column.dependency_order))),
            ("availability", _integer(len(column.availability))),
            ("blockers", _integer(len(column.blockers))),
        )
        _emit_profile(
            lines,
            "target_profile",
            (
                *target_scope,
                ("order", _enumeration(CapabilityInspectionProfileOrder.BASE)),
                ("profile", _integer(0)),
            ),
            column.base_profile,
        )
        for position, profile in enumerate(column.supplied_overlays):
            _emit_profile(
                lines,
                "target_profile",
                (
                    *target_scope,
                    (
                        "order",
                        _enumeration(CapabilityInspectionProfileOrder.SUPPLIED_OVERLAY),
                    ),
                    ("profile", _integer(position)),
                ),
                profile,
            )
        for position, profile in enumerate(column.dependency_order):
            _emit_profile(
                lines,
                "target_profile",
                (
                    *target_scope,
                    (
                        "order",
                        _enumeration(CapabilityInspectionProfileOrder.DEPENDENCY),
                    ),
                    ("profile", _integer(position)),
                ),
                profile,
            )
        for position, occurrence in enumerate(column.availability):
            _record(
                lines,
                "availability",
                *target_scope,
                ("occurrence", _integer(position)),
                *_availability_fields(occurrence),
            )
        for position, blocker in enumerate(column.blockers):
            blocker_scope = (*target_scope, ("blocker", _integer(position)))
            _record(
                lines,
                "blocker",
                *blocker_scope,
                ("kind", _enumeration(blocker.kind)),
                ("has_bucket", _boolean(blocker.bucket_profile is not None)),
                ("bucket_occurrences", _integer(len(blocker.bucket_occurrences))),
            )
            _emit_profile(
                lines,
                "blocker_profile",
                (*blocker_scope, ("role", _text("selected"))),
                blocker.selected_profile,
            )
            if blocker.bucket_profile is not None:
                _emit_profile(
                    lines,
                    "blocker_profile",
                    (*blocker_scope, ("role", _text("bucket"))),
                    blocker.bucket_profile,
                )
            for occurrence_position, occurrence in enumerate(
                blocker.bucket_occurrences
            ):
                _record(
                    lines,
                    "blocker_availability",
                    *blocker_scope,
                    ("occurrence", _integer(occurrence_position)),
                    *_availability_fields(occurrence),
                )
    for requirement in inspection.requirements:
        requirement_scope = (("requirement", _integer(requirement.position)),)
        _record(
            lines,
            "requirement",
            *requirement_scope,
            *_key_fields(requirement.key),
        )
        _emit_key_operands(
            lines,
            "requirement_operand",
            requirement_scope,
            requirement.key,
        )
        for cell in requirement.cells:
            cell_scope = (
                *requirement_scope,
                ("target", _integer(cell.column_position)),
            )
            check = cell.check
            _record(
                lines,
                "cell",
                *cell_scope,
                ("has_check", _boolean(check is not None)),
                (
                    "status",
                    _optional_enumeration(None if check is None else check.status),
                ),
                (
                    "target_occurrences",
                    _integer(0 if check is None else len(check.target_occurrences)),
                ),
                (
                    "target_lookup",
                    _optional_enumeration(
                        None if check is None else check.target_lookup.variant
                    ),
                ),
                (
                    "target_reason",
                    _optional_enumeration(
                        None if check is None else check.target_lookup.reason
                    ),
                ),
                (
                    "target_lookup_facts",
                    _integer(0 if check is None else len(check.target_lookup.facts)),
                ),
                (
                    "provider_domain_complete",
                    CAPABILITY_PURE_ABSENT
                    if check is None
                    else _boolean(check.provider_domain_complete),
                ),
                (
                    "provider_unknown_reason",
                    _optional_enumeration(
                        None if check is None else check.provider_unknown_reason
                    ),
                ),
                (
                    "provider_lookup",
                    _optional_enumeration(
                        None if check is None else check.provider_lookup.variant
                    ),
                ),
                (
                    "provider_reason",
                    _optional_enumeration(
                        None if check is None else check.provider_lookup.reason
                    ),
                ),
                (
                    "provider_lookup_facts",
                    _integer(0 if check is None else len(check.provider_lookup.facts)),
                ),
            )
            if check is None:
                continue
            for occurrence in check.target_occurrences:
                occurrence_scope = (
                    *cell_scope,
                    ("occurrence", _integer(occurrence.position)),
                )
                _record(
                    lines,
                    "target_occurrence",
                    *occurrence_scope,
                    ("profile", _integer(occurrence.profile_position)),
                    ("profile_namespace", _text(occurrence.profile.namespace)),
                    ("profile_name", _text(occurrence.profile.name)),
                    ("profile_release", _text(occurrence.profile.profile_release)),
                    ("profile_fact", _integer(occurrence.profile_fact_position)),
                )
                _emit_fact(lines, "target", occurrence_scope, occurrence.fact)
            for fact_position, fact in enumerate(check.provider_lookup.facts):
                _emit_fact(
                    lines,
                    "provider",
                    (*cell_scope, ("fact", _integer(fact_position))),
                    fact,
                )
    return CapabilityPureDocument(records=tuple(lines))
