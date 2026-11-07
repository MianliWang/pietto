"""Frozen accepted and rejected vectors for the capability pure boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType

from pietto._project.capability_pure_boundary import (
    CAPABILITY_PURE_ABSENT,
    CAPABILITY_PURE_FORMAT_MARKER,
    CAPABILITY_PURE_MAX_INTEGER,
    CapabilityPureDocument,
    CapabilityPureField,
    CapabilityPureRecord,
    CapabilityPureStatus,
    CapabilityPureTag,
    CapabilityPureValue,
    capability_pure_boolean,
    capability_pure_enumeration,
    capability_pure_integer,
    capability_pure_text,
)

CAPABILITY_DIFFERENTIAL_VECTOR_FORMAT = "pietto.capability-differential-vectors.v1"


class CapabilityDifferentialClassification(StrEnum):
    PORTABLE_EVALUATION = "portable_evaluation"
    PORTABLE_REJECTION = "portable_rejection"


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityDifferentialVector:
    vector_format: str
    vector_id: str
    purposes: tuple[str, ...]
    classification: CapabilityDifferentialClassification
    document: CapabilityPureDocument
    expected_status: CapabilityPureStatus
    expected_bytes: bytes | None = None
    expected_record_position: int | None = None
    expected_field_position: int | None = None


@dataclass(frozen=True, slots=True)
class _ProfileSpec:
    schema: str
    namespace: str
    name: str
    profile_release: str
    kind: str
    target_kind: str
    database_family: str
    target_release: str
    extension_identity: str | None = None
    extension_release: str | None = None


@dataclass(frozen=True, slots=True)
class _AvailabilitySpec:
    owner_kind: str
    owner_position: int
    project_path: str | None
    profile: _ProfileSpec


@dataclass(frozen=True, slots=True)
class _BlockerSpec:
    kind: str
    selected_profile: _ProfileSpec
    bucket_profile: _ProfileSpec | None = None
    bucket_occurrences: tuple[_AvailabilitySpec, ...] = ()


@dataclass(frozen=True, slots=True)
class _TargetSpec:
    variant: str
    base: _ProfileSpec
    supplied_overlays: tuple[_ProfileSpec, ...]
    dependency_order: tuple[_ProfileSpec, ...]
    availability: tuple[_AvailabilitySpec, ...]
    blockers: tuple[_BlockerSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class _KeySpec:
    domain: str
    subject: str | None
    operation: str | None = None
    operands: tuple[str, ...] = ()
    context: str | None = None
    dialect: str | None = None
    extension: str | None = None


@dataclass(frozen=True, slots=True)
class _EvidenceSpec:
    source: str
    source_path: str
    source_reference: str
    reason: str | None = None
    dialect: str | None = None
    backend: str | None = None
    extension: str | None = None


@dataclass(frozen=True, slots=True)
class _FactSpec:
    key: _KeySpec
    support: str = "supported"
    disposition: str = "none"
    disposition_owner: str | None = None
    disposition_reason: str | None = None
    evidence: tuple[_EvidenceSpec, ...] = (
        _EvidenceSpec("test", "tests/vector.py", "vector"),
    )


@dataclass(frozen=True, slots=True)
class _TargetOccurrenceSpec:
    profile_position: int
    profile_fact_position: int
    fact: _FactSpec


@dataclass(frozen=True, slots=True)
class _CheckSpec:
    status: str
    target_occurrences: tuple[_TargetOccurrenceSpec, ...]
    target_lookup: str
    target_reason: str | None
    provider_domain_complete: bool
    provider_unknown_reason: str | None
    provider_lookup: str
    provider_reason: str | None
    provider_facts: tuple[_FactSpec, ...]


@dataclass(frozen=True, slots=True)
class _RequirementSpec:
    key: _KeySpec
    cells: tuple[_CheckSpec | None, ...]


_BASE = _ProfileSpec(
    "pietto.capability-profile.v1",
    "pietto.targets",
    "base",
    "profile release",
    "base",
    "database",
    "PostgreSQL",
    "16",
)
_OVERLAY_ONE = _ProfileSpec(
    "pietto.capability-profile.v1",
    "pietto.targets",
    "overlay-one",
    "overlay release one",
    "overlay",
    "extension",
    "PostgreSQL",
    "16",
    "PostGIS",
    "3.4.1",
)
_OVERLAY_TWO = _ProfileSpec(
    "pietto.capability-profile.v1",
    "pietto.targets",
    "overlay-two",
    "overlay release two",
    "overlay",
    "extension",
    "PostgreSQL",
    "16",
    "TimescaleDB",
    "2.14",
)
_OVERLAY_CHILD = _ProfileSpec(
    "pietto.capability-profile.v1",
    "pietto.targets",
    "overlay-child",
    "overlay child release",
    "overlay",
    "extension",
    "PostgreSQL",
    "16",
    "PostGIS-child",
    "1",
)


def _s(value: str) -> CapabilityPureValue:
    return capability_pure_text(value)


def _e(value: str) -> CapabilityPureValue:
    return capability_pure_enumeration(value)


def _i(value: int) -> CapabilityPureValue:
    return capability_pure_integer(value)


def _b(value: bool) -> CapabilityPureValue:
    return capability_pure_boolean(value)


def _optional_text(value: str | None) -> CapabilityPureValue:
    return CAPABILITY_PURE_ABSENT if value is None else _s(value)


def _optional_enum(value: str | None) -> CapabilityPureValue:
    return CAPABILITY_PURE_ABSENT if value is None else _e(value)


def _record(
    kind: str,
    *pairs: tuple[str, CapabilityPureValue],
) -> CapabilityPureRecord:
    return CapabilityPureRecord(
        kind=kind,
        fields=tuple(CapabilityPureField(key=key, value=value) for key, value in pairs),
    )


def _profile_pairs(
    profile: _ProfileSpec,
) -> tuple[tuple[str, CapabilityPureValue], ...]:
    return (
        ("schema", _e(profile.schema)),
        ("namespace", _s(profile.namespace)),
        ("name", _s(profile.name)),
        ("profile_release", _s(profile.profile_release)),
        ("kind", _e(profile.kind)),
        ("target_kind", _e(profile.target_kind)),
        ("database_family", _s(profile.database_family)),
        ("target_release", _s(profile.target_release)),
        ("extension_identity", _optional_text(profile.extension_identity)),
        ("extension_release", _optional_text(profile.extension_release)),
    )


def _key_pairs(key: _KeySpec) -> tuple[tuple[str, CapabilityPureValue], ...]:
    return (
        ("domain", _e(key.domain)),
        ("subject", _optional_text(key.subject)),
        ("operation", _optional_text(key.operation)),
        ("operands", _i(len(key.operands))),
        ("context", _optional_text(key.context)),
        ("dialect", _optional_text(key.dialect)),
        ("extension", _optional_text(key.extension)),
    )


def _availability_pairs(
    availability: _AvailabilitySpec,
) -> tuple[tuple[str, CapabilityPureValue], ...]:
    return (
        ("owner_kind", _e(availability.owner_kind)),
        ("owner_position", _i(availability.owner_position)),
        ("project_path", _optional_text(availability.project_path)),
        *_profile_pairs(availability.profile),
    )


def _emit_fact(
    records: list[CapabilityPureRecord],
    axis: str,
    scope: tuple[tuple[str, CapabilityPureValue], ...],
    fact: _FactSpec,
) -> None:
    records.append(
        _record(
            f"{axis}_fact",
            *scope,
            *_key_pairs(fact.key),
            ("support", _e(fact.support)),
            ("disposition", _e(fact.disposition)),
            ("disposition_owner", _optional_text(fact.disposition_owner)),
            ("disposition_reason", _optional_text(fact.disposition_reason)),
            ("evidence", _i(len(fact.evidence))),
        )
    )
    for position, operand in enumerate(fact.key.operands):
        records.append(
            _record(
                f"{axis}_fact_operand",
                *scope,
                ("operand", _i(position)),
                ("value", _s(operand)),
            )
        )
    for position, evidence in enumerate(fact.evidence):
        records.append(
            _record(
                f"{axis}_fact_evidence",
                *scope,
                ("evidence", _i(position)),
                ("source", _e(evidence.source)),
                ("source_path", _s(evidence.source_path)),
                ("source_reference", _s(evidence.source_reference)),
                ("reason", _optional_enum(evidence.reason)),
                ("dialect", _optional_text(evidence.dialect)),
                ("backend", _optional_text(evidence.backend)),
                ("extension", _optional_text(evidence.extension)),
            )
        )


def _emit_target(
    records: list[CapabilityPureRecord],
    target_position: int,
    target: _TargetSpec,
) -> None:
    records.append(
        _record(
            "target",
            ("target", _i(target_position)),
            ("variant", _e(target.variant)),
            ("supplied_overlays", _i(len(target.supplied_overlays))),
            ("dependency_profiles", _i(len(target.dependency_order))),
            ("availability", _i(len(target.availability))),
            ("blockers", _i(len(target.blockers))),
        )
    )
    records.append(
        _record(
            "target_profile",
            ("target", _i(target_position)),
            ("order", _e("base")),
            ("profile", _i(0)),
            *_profile_pairs(target.base),
        )
    )
    for position, profile in enumerate(target.supplied_overlays):
        records.append(
            _record(
                "target_profile",
                ("target", _i(target_position)),
                ("order", _e("supplied_overlay")),
                ("profile", _i(position)),
                *_profile_pairs(profile),
            )
        )
    for position, profile in enumerate(target.dependency_order):
        records.append(
            _record(
                "target_profile",
                ("target", _i(target_position)),
                ("order", _e("dependency")),
                ("profile", _i(position)),
                *_profile_pairs(profile),
            )
        )
    for position, availability in enumerate(target.availability):
        records.append(
            _record(
                "availability",
                ("target", _i(target_position)),
                ("occurrence", _i(position)),
                *_availability_pairs(availability),
            )
        )
    for position, blocker in enumerate(target.blockers):
        records.append(
            _record(
                "blocker",
                ("target", _i(target_position)),
                ("blocker", _i(position)),
                ("kind", _e(blocker.kind)),
                ("has_bucket", _b(blocker.bucket_profile is not None)),
                ("bucket_occurrences", _i(len(blocker.bucket_occurrences))),
            )
        )
        records.append(
            _record(
                "blocker_profile",
                ("target", _i(target_position)),
                ("blocker", _i(position)),
                ("role", _s("selected")),
                *_profile_pairs(blocker.selected_profile),
            )
        )
        if blocker.bucket_profile is not None:
            records.append(
                _record(
                    "blocker_profile",
                    ("target", _i(target_position)),
                    ("blocker", _i(position)),
                    ("role", _s("bucket")),
                    *_profile_pairs(blocker.bucket_profile),
                )
            )
        for occurrence_position, availability in enumerate(blocker.bucket_occurrences):
            records.append(
                _record(
                    "blocker_availability",
                    ("target", _i(target_position)),
                    ("blocker", _i(position)),
                    ("occurrence", _i(occurrence_position)),
                    *_availability_pairs(availability),
                )
            )


def _emit_requirement(
    records: list[CapabilityPureRecord],
    requirement_position: int,
    requirement: _RequirementSpec,
    targets: tuple[_TargetSpec, ...],
) -> None:
    records.append(
        _record(
            "requirement",
            ("requirement", _i(requirement_position)),
            *_key_pairs(requirement.key),
        )
    )
    for position, operand in enumerate(requirement.key.operands):
        records.append(
            _record(
                "requirement_operand",
                ("requirement", _i(requirement_position)),
                ("operand", _i(position)),
                ("value", _s(operand)),
            )
        )
    for target_position, (target, check) in enumerate(
        zip(targets, requirement.cells, strict=True)
    ):
        records.append(
            _record(
                "cell",
                ("requirement", _i(requirement_position)),
                ("target", _i(target_position)),
                ("has_check", _b(check is not None)),
                ("status", _optional_enum(None if check is None else check.status)),
                (
                    "target_occurrences",
                    _i(0 if check is None else len(check.target_occurrences)),
                ),
                (
                    "target_lookup",
                    _optional_enum(None if check is None else check.target_lookup),
                ),
                (
                    "target_reason",
                    _optional_enum(None if check is None else check.target_reason),
                ),
                (
                    "target_lookup_facts",
                    _i(0 if check is None else len(check.target_occurrences)),
                ),
                (
                    "provider_domain_complete",
                    CAPABILITY_PURE_ABSENT
                    if check is None
                    else _b(check.provider_domain_complete),
                ),
                (
                    "provider_unknown_reason",
                    _optional_enum(
                        None if check is None else check.provider_unknown_reason
                    ),
                ),
                (
                    "provider_lookup",
                    _optional_enum(None if check is None else check.provider_lookup),
                ),
                (
                    "provider_reason",
                    _optional_enum(None if check is None else check.provider_reason),
                ),
                (
                    "provider_lookup_facts",
                    _i(0 if check is None else len(check.provider_facts)),
                ),
            )
        )
        if check is None:
            continue
        for occurrence_position, occurrence in enumerate(check.target_occurrences):
            profile = target.dependency_order[occurrence.profile_position]
            scope = (
                ("requirement", _i(requirement_position)),
                ("target", _i(target_position)),
                ("occurrence", _i(occurrence_position)),
            )
            records.append(
                _record(
                    "target_occurrence",
                    *scope,
                    ("profile", _i(occurrence.profile_position)),
                    ("profile_namespace", _s(profile.namespace)),
                    ("profile_name", _s(profile.name)),
                    ("profile_release", _s(profile.profile_release)),
                    ("profile_fact", _i(occurrence.profile_fact_position)),
                )
            )
            _emit_fact(records, "target", scope, occurrence.fact)
        for fact_position, fact in enumerate(check.provider_facts):
            _emit_fact(
                records,
                "provider",
                (
                    ("requirement", _i(requirement_position)),
                    ("target", _i(target_position)),
                    ("fact", _i(fact_position)),
                ),
                fact,
            )


def _document(
    *,
    declaration: str,
    targets: tuple[_TargetSpec, ...],
    requirements: tuple[_RequirementSpec, ...],
    role: str = "root",
    namespace: str = "example",
    name: str = "root",
    release: str = "1.0.0",
    digest: str = "1" * 64,
) -> CapabilityPureDocument:
    records = [
        _record(
            "inspection",
            ("format", _e(CAPABILITY_PURE_FORMAT_MARKER)),
            ("declaration", _e(declaration)),
            ("targets", _i(len(targets))),
            ("requirements", _i(len(requirements))),
        ),
        _record(
            "package",
            ("role", _e(role)),
            ("namespace", _s(namespace)),
            ("name", _s(name)),
            ("release", _s(release)),
            ("content_digest", _s(digest)),
        ),
    ]
    if declaration == "declared":
        records.append(
            _record(
                "requirements",
                ("namespace", _s("consumer")),
                ("name", _s("requirements")),
                ("count", _i(len(requirements))),
            )
        )
    for target_position, target in enumerate(targets):
        _emit_target(records, target_position, target)
    for requirement_position, requirement in enumerate(requirements):
        _emit_requirement(records, requirement_position, requirement, targets)
    return CapabilityPureDocument(records=tuple(records))


def _availability(
    profile: _ProfileSpec = _BASE,
    *,
    owner: str = "compiler",
    position: int = 0,
    project_path: str | None = None,
) -> _AvailabilitySpec:
    return _AvailabilitySpec(owner, position, project_path, profile)


def _target(
    variant: str,
    *,
    base: _ProfileSpec = _BASE,
    supplied: tuple[_ProfileSpec, ...] = (),
    dependency: tuple[_ProfileSpec, ...] | None = None,
    availability: tuple[_AvailabilitySpec, ...] | None = None,
    blockers: tuple[_BlockerSpec, ...] = (),
) -> _TargetSpec:
    dependency_order = (base, *supplied) if dependency is None else dependency
    declared = (
        tuple(
            _availability(profile, position=position)
            for position, profile in enumerate(dependency_order)
        )
        if availability is None
        else availability
    )
    return _TargetSpec(
        variant,
        base,
        supplied,
        dependency_order,
        declared,
        blockers,
    )


def _found_check(
    key: _KeySpec,
    status: str = "satisfied",
    *,
    support: str = "supported",
    target_facts: int = 1,
) -> _CheckSpec:
    occurrences = tuple(
        _TargetOccurrenceSpec(
            0,
            position,
            _FactSpec(
                key, support=support if position == 0 else "explicitly_unsupported"
            ),
        )
        for position in range(target_facts)
    )
    return _CheckSpec(
        status,
        occurrences,
        "found" if target_facts == 1 else "conflict",
        None if target_facts == 1 else "conflicting_evidence",
        True,
        None,
        "found",
        None,
        (_FactSpec(key),),
    )


def _accepted_documents() -> tuple[
    tuple[str, tuple[str, ...], CapabilityPureDocument], ...
]:
    key = _KeySpec("conversion", "feature", "convert", ("B", "A"))
    target = _target("checked")
    satisfied = _found_check(key)
    unsupported = _found_check(key, "unsupported", support="explicitly_unsupported")
    absent = replace(
        satisfied,
        status="absent",
        provider_lookup="absent",
        provider_reason="no_catalog_entry",
        provider_facts=(),
    )
    unknown = replace(
        satisfied,
        status="unknown",
        provider_domain_complete=False,
        provider_lookup="unknown",
        provider_reason="not_evidenced",
        provider_facts=(),
    )
    conflict = replace(
        _found_check(key, "conflict", target_facts=2),
        provider_lookup="conflict",
        provider_reason="conflicting_evidence",
        provider_facts=(
            _FactSpec(key),
            _FactSpec(key, support="explicitly_unsupported"),
        ),
    )
    blocked_target = _target(
        "blocked",
        availability=(),
        blockers=(_BlockerSpec("profile_not_declared_available", _BASE),),
    )
    bucket_availability = _availability(_BASE)
    bucket_target = _target(
        "blocked",
        blockers=(
            _BlockerSpec(
                "profile_authority_mismatch",
                _BASE,
                _BASE,
                (bucket_availability,),
            ),
        ),
    )
    second_key = _KeySpec("extension_signature", "extension", "lookup")
    second_check = replace(
        _found_check(second_key),
        status="unknown",
        provider_domain_complete=False,
        provider_unknown_reason="no_current_result_rule",
        provider_lookup="unknown",
        provider_reason="no_current_result_rule",
        provider_facts=(),
    )
    two_targets = (
        target,
        _target("checked", base=replace(_BASE, profile_release="p2")),
    )
    two_target_requirement = _RequirementSpec(key, (satisfied, unknown))
    two_requirements = (
        _RequirementSpec(key, (satisfied,)),
        _RequirementSpec(second_key, (second_check,)),
    )
    sibling_target = _target(
        "checked",
        supplied=(_OVERLAY_ONE, _OVERLAY_TWO),
    )
    chain_target = _target(
        "checked",
        supplied=(_OVERLAY_CHILD, _OVERLAY_ONE),
        dependency=(_BASE, _OVERLAY_ONE, _OVERLAY_CHILD),
    )
    project_target = _target(
        "checked",
        availability=(
            _availability(_BASE, owner="project", project_path="logical/project"),
        ),
    )
    unicode_key = _KeySpec(
        "conversion",
        "雪\\\t\n\r\x01",
        "café",
        ("é", "e\u0301"),
    )
    unicode_evidence = _EvidenceSpec(
        "test",
        "path\\\tline\n雪",
        "reference\r\x7f",
    )
    unicode_fact = _FactSpec(unicode_key, evidence=(unicode_evidence,))
    unicode_check = replace(
        _found_check(unicode_key),
        status="unknown",
        target_occurrences=(_TargetOccurrenceSpec(0, 0, unicode_fact),),
        provider_domain_complete=False,
        provider_lookup="unknown",
        provider_reason="not_evidenced",
        provider_facts=(),
    )
    extension_target = _target(
        "checked",
        supplied=(_OVERLAY_ONE,),
    )
    disposition_fact = _FactSpec(
        key,
        disposition="deferred",
        disposition_owner="Phase 60",
        disposition_reason="later",
        evidence=(
            _EvidenceSpec("test", "one", "first"),
            _EvidenceSpec(
                "spec",
                "two",
                "second",
                "dialect_lowering_gap",
                "postgresql",
                "backend",
                "extension",
            ),
        ),
    )
    disposition_check = replace(
        satisfied,
        target_occurrences=(_TargetOccurrenceSpec(0, 0, disposition_fact),),
    )
    return (
        (
            "undeclared_root",
            ("undeclared", "root_package", "optional_absence"),
            _document(
                declaration="undeclared",
                targets=(_target("undeclared"),),
                requirements=(),
            ),
        ),
        (
            "declared_empty_root",
            ("declared_empty", "root_package"),
            _document(declaration="declared", targets=(target,), requirements=()),
        ),
        (
            "declared_empty_dependency",
            ("declared_empty", "dependency_package"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(),
                role="dependency",
                name="dependency",
            ),
        ),
        (
            "checked_satisfied",
            ("checked", "satisfied", "compiler_availability"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (satisfied,)),),
            ),
        ),
        (
            "checked_unsupported",
            ("checked", "unsupported"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (unsupported,)),),
            ),
        ),
        (
            "checked_absent",
            ("checked", "absent"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (absent,)),),
            ),
        ),
        (
            "checked_unknown",
            ("checked", "unknown"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (unknown,)),),
            ),
        ),
        (
            "checked_conflict",
            (
                "checked",
                "conflict",
                "ordered_target_conflict",
                "ordered_provider_conflict",
            ),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (conflict,)),),
            ),
        ),
        (
            "blocked_without_bucket",
            ("blocked", "blocker_without_bucket"),
            _document(
                declaration="declared", targets=(blocked_target,), requirements=()
            ),
        ),
        (
            "blocked_with_bucket",
            ("blocked", "blocker_with_bucket"),
            _document(
                declaration="declared", targets=(bucket_target,), requirements=()
            ),
        ),
        (
            "one_requirement_two_targets",
            ("multiple_targets", "rectangular_cells"),
            _document(
                declaration="declared",
                targets=two_targets,
                requirements=(two_target_requirement,),
            ),
        ),
        (
            "two_requirements_one_target",
            ("multiple_requirements", "requirement_order"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=two_requirements,
            ),
        ),
        (
            "two_by_two_matrix",
            ("multiple_requirements", "multiple_targets", "rectangular_matrix"),
            _document(
                declaration="declared",
                targets=two_targets,
                requirements=(
                    two_target_requirement,
                    _RequirementSpec(second_key, (second_check, second_check)),
                ),
            ),
        ),
        (
            "sibling_overlays",
            ("sibling_overlays", "supplied_order", "dependency_order"),
            _document(
                declaration="declared", targets=(sibling_target,), requirements=()
            ),
        ),
        (
            "overlay_dependency_chain",
            ("overlay_dependency_chain", "dependency_order"),
            _document(declaration="declared", targets=(chain_target,), requirements=()),
        ),
        (
            "compiler_availability",
            ("compiler_availability", "availability_order"),
            _document(declaration="declared", targets=(target,), requirements=()),
        ),
        (
            "project_availability",
            ("project_availability", "logical_project_path"),
            _document(
                declaration="declared", targets=(project_target,), requirements=()
            ),
        ),
        (
            "unicode_control_escaping",
            ("unicode", "control_characters", "escaping", "no_normalization"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(unicode_key, (unicode_check,)),),
                namespace="例",
                name="雪",
            ),
        ),
        (
            "extension_signature_overlay",
            ("extension_signature", "extension_profile", "bounded_unknown_reason"),
            _document(
                declaration="declared",
                targets=(extension_target,),
                requirements=(_RequirementSpec(second_key, (second_check,)),),
            ),
        ),
        (
            "disposition_ordered_evidence",
            ("disposition", "ordered_evidence", "optional_scopes"),
            _document(
                declaration="declared",
                targets=(target,),
                requirements=(_RequirementSpec(key, (disposition_check,)),),
            ),
        ),
    )


# Reviewed bytes literals. Tests never regenerate these expectations.
_EXPECTED_CANONICAL_BYTES_LITERAL: dict[str, bytes] = {
    "undeclared_root": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:undeclared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\ntarget\ttarget=i:0\tvariant=e:undeclared\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n",
    "declared_empty_root": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n",
    "declared_empty_dependency": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:dependency\tnamespace=s:example\tname=s:dependency\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n",
    "checked_satisfied": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:satisfied\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:found\tprovider_reason=n:\tprovider_lookup_facts=i:1\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "checked_unsupported": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:unsupported\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:found\tprovider_reason=n:\tprovider_lookup_facts=i:1\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:explicitly_unsupported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "checked_absent": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:absent\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:absent\tprovider_reason=e:no_catalog_entry\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "checked_unknown": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=n:\tprovider_lookup=e:unknown\tprovider_reason=e:not_evidenced\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "checked_conflict": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:conflict\ttarget_occurrences=i:2\ttarget_lookup=e:conflict\ttarget_reason=e:conflicting_evidence\ttarget_lookup_facts=i:2\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:conflict\tprovider_reason=e:conflicting_evidence\tprovider_lookup_facts=i:2\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:1\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:1\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:1\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:explicitly_unsupported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:1\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:1\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:1\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:1\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:explicitly_unsupported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:1\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:1\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:1\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "blocked_with_bucket": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:blocked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:1\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nblocker\ttarget=i:0\tblocker=i:0\tkind=e:profile_authority_mismatch\thas_bucket=b:true\tbucket_occurrences=i:1\nblocker_profile\ttarget=i:0\tblocker=i:0\trole=s:selected\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nblocker_profile\ttarget=i:0\tblocker=i:0\trole=s:bucket\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nblocker_availability\ttarget=i:0\tblocker=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n",
    "two_by_two_matrix": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:2\trequirements=i:2\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:2\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget\ttarget=i:1\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:1\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:p2\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:1\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:p2\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:1\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:p2\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:satisfied\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:found\tprovider_reason=n:\tprovider_lookup_facts=i:1\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\ncell\trequirement=i:0\ttarget=i:1\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=n:\tprovider_lookup=e:unknown\tprovider_reason=e:not_evidenced\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:0\ttarget=i:1\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:p2\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:1\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:1\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:1\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:1\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\nrequirement\trequirement=i:1\tdomain=e:extension_signature\tsubject=s:extension\toperation=s:lookup\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\ncell\trequirement=i:1\ttarget=i:0\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=e:no_current_result_rule\tprovider_lookup=e:unknown\tprovider_reason=e:no_current_result_rule\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:1\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:1\ttarget=i:0\toccurrence=i:0\tdomain=e:extension_signature\tsubject=s:extension\toperation=s:lookup\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_evidence\trequirement=i:1\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\ncell\trequirement=i:1\ttarget=i:1\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=e:no_current_result_rule\tprovider_lookup=e:unknown\tprovider_reason=e:no_current_result_rule\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:1\ttarget=i:1\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:p2\tprofile_fact=i:0\ntarget_fact\trequirement=i:1\ttarget=i:1\toccurrence=i:0\tdomain=e:extension_signature\tsubject=s:extension\toperation=s:lookup\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_evidence\trequirement=i:1\ttarget=i:1\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "sibling_overlays": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:2\tdependency_profiles=i:3\tavailability=i:3\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:supplied_overlay\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\ntarget_profile\ttarget=i:0\torder=e:supplied_overlay\tprofile=i:1\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-two\tprofile_release=s:overlay release two\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:TimescaleDB\textension_release=s:2.14\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:1\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:2\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-two\tprofile_release=s:overlay release two\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:TimescaleDB\textension_release=s:2.14\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:1\towner_kind=e:compiler\towner_position=i:1\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\navailability\ttarget=i:0\toccurrence=i:2\towner_kind=e:compiler\towner_position=i:2\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-two\tprofile_release=s:overlay release two\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:TimescaleDB\textension_release=s:2.14\n",
    "overlay_dependency_chain": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:2\tdependency_profiles=i:3\tavailability=i:3\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:supplied_overlay\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-child\tprofile_release=s:overlay child release\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS-child\textension_release=s:1\ntarget_profile\ttarget=i:0\torder=e:supplied_overlay\tprofile=i:1\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:1\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:2\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-child\tprofile_release=s:overlay child release\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS-child\textension_release=s:1\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:1\towner_kind=e:compiler\towner_position=i:1\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\navailability\ttarget=i:0\toccurrence=i:2\towner_kind=e:compiler\towner_position=i:2\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-child\tprofile_release=s:overlay child release\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS-child\textension_release=s:1\n",
    "project_availability": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:0\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:0\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:project\towner_position=i:0\tproject_path=s:logical/project\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\n",
    "unicode_control_escaping": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:\xe4\xbe\x8b\tname=s:\xe9\x9b\xaa\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:\xe9\x9b\xaa\\\\\\t\\n\\r\\x01\toperation=s:caf\xc3\xa9\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:\xc3\xa9\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:e\xcc\x81\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=n:\tprovider_lookup=e:unknown\tprovider_reason=e:not_evidenced\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:\xe9\x9b\xaa\\\\\\t\\n\\r\\x01\toperation=s:caf\xc3\xa9\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:\xc3\xa9\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:e\xcc\x81\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:path\\\\\\tline\\n\xe9\x9b\xaa\tsource_reference=s:reference\\r\\x7f\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "extension_signature_overlay": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:1\tdependency_profiles=i:2\tavailability=i:2\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:supplied_overlay\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:1\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:1\towner_kind=e:compiler\towner_position=i:1\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:overlay-one\tprofile_release=s:overlay release one\tkind=e:overlay\ttarget_kind=e:extension\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=s:PostGIS\textension_release=s:3.4.1\nrequirement\trequirement=i:0\tdomain=e:extension_signature\tsubject=s:extension\toperation=s:lookup\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:unknown\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:false\tprovider_unknown_reason=e:no_current_result_rule\tprovider_lookup=e:unknown\tprovider_reason=e:no_current_result_rule\tprovider_lookup_facts=i:0\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:extension_signature\tsubject=s:extension\toperation=s:lookup\toperands=i:0\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
    "disposition_ordered_evidence": b"inspection\tformat=e:pietto.capability-inspection.v1\tdeclaration=e:declared\ttargets=i:1\trequirements=i:1\npackage\trole=e:root\tnamespace=s:example\tname=s:root\trelease=s:1.0.0\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\nrequirements\tnamespace=s:consumer\tname=s:requirements\tcount=i:1\ntarget\ttarget=i:0\tvariant=e:checked\tsupplied_overlays=i:0\tdependency_profiles=i:1\tavailability=i:1\tblockers=i:0\ntarget_profile\ttarget=i:0\torder=e:base\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\ntarget_profile\ttarget=i:0\torder=e:dependency\tprofile=i:0\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\navailability\ttarget=i:0\toccurrence=i:0\towner_kind=e:compiler\towner_position=i:0\tproject_path=n:\tschema=e:pietto.capability-profile.v1\tnamespace=s:pietto.targets\tname=s:base\tprofile_release=s:profile release\tkind=e:base\ttarget_kind=e:database\tdatabase_family=s:PostgreSQL\ttarget_release=s:16\textension_identity=n:\textension_release=n:\nrequirement\trequirement=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\nrequirement_operand\trequirement=i:0\toperand=i:0\tvalue=s:B\nrequirement_operand\trequirement=i:0\toperand=i:1\tvalue=s:A\ncell\trequirement=i:0\ttarget=i:0\thas_check=b:true\tstatus=e:satisfied\ttarget_occurrences=i:1\ttarget_lookup=e:found\ttarget_reason=n:\ttarget_lookup_facts=i:1\tprovider_domain_complete=b:true\tprovider_unknown_reason=n:\tprovider_lookup=e:found\tprovider_reason=n:\tprovider_lookup_facts=i:1\ntarget_occurrence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tprofile=i:0\tprofile_namespace=s:pietto.targets\tprofile_name=s:base\tprofile_release=s:profile release\tprofile_fact=i:0\ntarget_fact\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:deferred\tdisposition_owner=s:Phase 60\tdisposition_reason=s:later\tevidence=i:2\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:0\tvalue=s:B\ntarget_fact_operand\trequirement=i:0\ttarget=i:0\toccurrence=i:0\toperand=i:1\tvalue=s:A\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:one\tsource_reference=s:first\treason=n:\tdialect=n:\tbackend=n:\textension=n:\ntarget_fact_evidence\trequirement=i:0\ttarget=i:0\toccurrence=i:0\tevidence=i:1\tsource=e:spec\tsource_path=s:two\tsource_reference=s:second\treason=e:dialect_lowering_gap\tdialect=s:postgresql\tbackend=s:backend\textension=s:extension\nprovider_fact\trequirement=i:0\ttarget=i:0\tfact=i:0\tdomain=e:conversion\tsubject=s:feature\toperation=s:convert\toperands=i:2\tcontext=n:\tdialect=n:\textension=n:\tsupport=e:supported\tdisposition=e:none\tdisposition_owner=n:\tdisposition_reason=n:\tevidence=i:1\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:0\tvalue=s:B\nprovider_fact_operand\trequirement=i:0\ttarget=i:0\tfact=i:0\toperand=i:1\tvalue=s:A\nprovider_fact_evidence\trequirement=i:0\ttarget=i:0\tfact=i:0\tevidence=i:0\tsource=e:test\tsource_path=s:tests/vector.py\tsource_reference=s:vector\treason=n:\tdialect=n:\tbackend=n:\textension=n:\n",
}
EXPECTED_CANONICAL_BYTES: Mapping[str, bytes] = MappingProxyType(
    _EXPECTED_CANONICAL_BYTES_LITERAL
)


def _replace_field(
    record: CapabilityPureRecord,
    key: str,
    value: CapabilityPureValue,
) -> CapabilityPureRecord:
    return replace(
        record,
        fields=tuple(
            replace(field, value=value) if field.key == key else field
            for field in record.fields
        ),
    )


def _replace_record(
    document: CapabilityPureDocument,
    position: int,
    record: CapabilityPureRecord,
) -> CapabilityPureDocument:
    records = list(document.records)
    records[position] = record
    return replace(document, records=tuple(records))


def _record_position(
    document: CapabilityPureDocument,
    kind: str,
    occurrence: int = 0,
) -> int:
    matches = tuple(
        position
        for position, record in enumerate(document.records)
        if record.kind == kind
    )
    return matches[occurrence]


def _mutate_field(
    document: CapabilityPureDocument,
    kind: str,
    key: str,
    value: CapabilityPureValue,
    occurrence: int = 0,
) -> CapabilityPureDocument:
    position = _record_position(document, kind, occurrence)
    return _replace_record(
        document,
        position,
        _replace_field(document.records[position], key, value),
    )


def _remove_record(
    document: CapabilityPureDocument,
    position: int,
) -> CapabilityPureDocument:
    return replace(
        document,
        records=(*document.records[:position], *document.records[position + 1 :]),
    )


def _insert_record(
    document: CapabilityPureDocument,
    position: int,
    record: CapabilityPureRecord,
) -> CapabilityPureDocument:
    return replace(
        document,
        records=(
            *document.records[:position],
            record,
            *document.records[position:],
        ),
    )


def _remove_field(
    document: CapabilityPureDocument,
    kind: str,
    key: str,
    occurrence: int = 0,
) -> CapabilityPureDocument:
    position = _record_position(document, kind, occurrence)
    record = document.records[position]
    return _replace_record(
        document,
        position,
        replace(
            record, fields=tuple(field for field in record.fields if field.key != key)
        ),
    )


def _extra_field(
    document: CapabilityPureDocument,
    kind: str,
    occurrence: int = 0,
) -> CapabilityPureDocument:
    position = _record_position(document, kind, occurrence)
    record = document.records[position]
    return _replace_record(
        document,
        position,
        replace(
            record,
            fields=(*record.fields, CapabilityPureField(key="extra", value=_s("x"))),
        ),
    )


def _swap_fields(
    document: CapabilityPureDocument,
    kind: str,
    left: int,
    right: int,
    occurrence: int = 0,
) -> CapabilityPureDocument:
    position = _record_position(document, kind, occurrence)
    record = document.records[position]
    fields = list(record.fields)
    fields[left], fields[right] = fields[right], fields[left]
    return _replace_record(document, position, replace(record, fields=tuple(fields)))


def _rejected_documents() -> tuple[
    tuple[str, tuple[str, ...], CapabilityPureDocument], ...
]:
    accepted = {vector_id: document for vector_id, _, document in _accepted_documents()}
    undeclared = accepted["undeclared_root"]
    empty = accepted["declared_empty_root"]
    checked = accepted["checked_satisfied"]
    absent = accepted["checked_absent"]
    unknown = accepted["checked_unknown"]
    conflict = accepted["checked_conflict"]
    blocked = accepted["blocked_without_bucket"]
    bucket = accepted["blocked_with_bucket"]
    matrix = accepted["two_by_two_matrix"]
    sibling = accepted["sibling_overlays"]
    project = accepted["project_availability"]
    disposition = accepted["disposition_ordered_evidence"]
    cases: list[tuple[str, tuple[str, ...], CapabilityPureDocument]] = []

    def add(vector_id: str, purpose: str, document: CapabilityPureDocument) -> None:
        cases.append((vector_id, (purpose,), document))

    add("empty_document", "empty_document", CapabilityPureDocument())
    add("missing_header", "missing_inspection_header", _remove_record(undeclared, 0))
    add(
        "unknown_package_kind",
        "unknown_record_kind",
        _replace_record(
            undeclared,
            1,
            replace(undeclared.records[1], kind="unknown"),
        ),
    )
    add(
        "wrong_format_marker",
        "wrong_format_marker",
        _mutate_field(undeclared, "inspection", "format", _e("wrong")),
    )
    add(
        "duplicate_header",
        "duplicate_singleton_header",
        _insert_record(undeclared, 1, undeclared.records[0]),
    )
    add(
        "duplicate_package",
        "duplicate_singleton_package",
        _insert_record(undeclared, 2, undeclared.records[1]),
    )
    add(
        "missing_header_field",
        "missing_field",
        _remove_field(undeclared, "inspection", "targets"),
    )
    add("extra_header_field", "extra_field", _extra_field(undeclared, "inspection"))
    add(
        "wrong_header_field_order",
        "wrong_field_order",
        _swap_fields(undeclared, "inspection", 0, 1),
    )
    add(
        "wrong_header_scalar_tag",
        "wrong_scalar_tag",
        _mutate_field(
            undeclared, "inspection", "format", _s(CAPABILITY_PURE_FORMAT_MARKER)
        ),
    )
    add(
        "required_header_absent",
        "absent_not_allowed",
        _mutate_field(undeclared, "inspection", "format", CAPABILITY_PURE_ABSENT),
    )
    malformed_absent = CapabilityPureValue(tag=CapabilityPureTag.ABSENT, text="x")
    add(
        "absent_with_payload",
        "malformed_absent_payload",
        _mutate_field(empty, "target_profile", "extension_identity", malformed_absent),
    )
    missing_enum = CapabilityPureValue(tag=CapabilityPureTag.ENUMERATION)
    add(
        "missing_enum_payload",
        "missing_scalar_payload",
        _mutate_field(undeclared, "inspection", "format", missing_enum),
    )
    extra_enum = CapabilityPureValue(
        tag=CapabilityPureTag.ENUMERATION,
        text=CAPABILITY_PURE_FORMAT_MARKER,
        integer=1,
    )
    add(
        "extra_enum_payload",
        "extra_scalar_payload",
        _mutate_field(undeclared, "inspection", "format", extra_enum),
    )
    add(
        "negative_target_count",
        "negative_integer",
        _mutate_field(undeclared, "inspection", "targets", _i(-1)),
    )
    add(
        "overflow_target_count",
        "integer_out_of_range",
        _mutate_field(
            undeclared,
            "inspection",
            "targets",
            _i(CAPABILITY_PURE_MAX_INTEGER + 1),
        ),
    )
    add(
        "unknown_declaration_enum",
        "unknown_enumeration",
        _mutate_field(undeclared, "inspection", "declaration", _e("other")),
    )
    missing_boolean = CapabilityPureValue(tag=CapabilityPureTag.BOOLEAN)
    add(
        "missing_boolean_payload",
        "malformed_boolean_payload",
        _mutate_field(checked, "cell", "has_check", missing_boolean),
    )
    add("missing_package", "missing_required_package", _remove_record(undeclared, 1))
    add(
        "missing_requirements_header",
        "declared_requirements_header",
        _remove_record(empty, 2),
    )
    add(
        "requirements_on_undeclared",
        "undeclared_requirements_header",
        _insert_record(undeclared, 2, empty.records[2]),
    )
    add(
        "requirements_count_mismatch",
        "requirement_count_mismatch",
        _mutate_field(empty, "requirements", "count", _i(1)),
    )
    add(
        "trailing_target_record",
        "trailing_record",
        _insert_record(undeclared, len(undeclared.records), undeclared.records[2]),
    )
    add(
        "target_count_high",
        "target_count_mismatch",
        _mutate_field(undeclared, "inspection", "targets", _i(2)),
    )
    add(
        "sparse_target_ordinal",
        "sparse_target_ordinal",
        _mutate_field(undeclared, "target", "target", _i(1)),
    )
    add(
        "duplicate_target_ordinal",
        "duplicate_target_ordinal",
        _mutate_field(matrix, "target", "target", _i(0), occurrence=1),
    )
    add(
        "requirement_count_high",
        "requirement_count_mismatch",
        _mutate_field(checked, "inspection", "requirements", _i(2)),
    )
    add(
        "sparse_requirement_ordinal",
        "sparse_requirement_ordinal",
        _mutate_field(checked, "requirement", "requirement", _i(1)),
    )
    add(
        "duplicate_requirement_ordinal",
        "duplicate_requirement_ordinal",
        _mutate_field(matrix, "requirement", "requirement", _i(0), occurrence=1),
    )
    add(
        "requirement_operand_count_high",
        "operand_count_mismatch",
        _mutate_field(checked, "requirement", "operands", _i(3)),
    )
    add(
        "sparse_requirement_operand",
        "sparse_operand_ordinal",
        _mutate_field(checked, "requirement_operand", "operand", _i(1)),
    )
    cell_position = _record_position(checked, "cell")
    add("missing_cell", "cell_count_mismatch", _remove_record(checked, cell_position))
    add(
        "cell_wrong_target",
        "cell_target_order",
        _mutate_field(checked, "cell", "target", _i(1)),
    )
    add(
        "cell_wrong_requirement",
        "cell_requirement_scope",
        _mutate_field(checked, "cell", "requirement", _i(1)),
    )

    base_position = _record_position(empty, "target_profile")
    add(
        "missing_base_profile",
        "missing_base_projection",
        _remove_record(empty, base_position),
    )
    add(
        "base_profile_wrong_order",
        "wrong_profile_order",
        _mutate_field(empty, "target_profile", "order", _e("dependency")),
    )
    add(
        "base_profile_sparse_ordinal",
        "sparse_profile_ordinal",
        _mutate_field(empty, "target_profile", "profile", _i(1)),
    )
    add(
        "base_profile_wrong_kind",
        "profile_kind_relation",
        _mutate_field(empty, "target_profile", "kind", _e("overlay")),
    )
    add(
        "base_profile_wrong_target_kind",
        "profile_target_relation",
        _mutate_field(empty, "target_profile", "target_kind", _e("extension")),
    )
    add(
        "supplied_overlay_count_high",
        "supplied_overlay_count_mismatch",
        _mutate_field(sibling, "target", "supplied_overlays", _i(3)),
    )
    add(
        "supplied_overlay_wrong_order",
        "supplied_profile_order",
        _mutate_field(
            sibling,
            "target_profile",
            "order",
            _e("dependency"),
            occurrence=1,
        ),
    )
    add(
        "supplied_overlay_sparse_ordinal",
        "sparse_profile_ordinal",
        _mutate_field(sibling, "target_profile", "profile", _i(1), occurrence=1),
    )
    add(
        "dependency_profile_count_high",
        "dependency_profile_count_mismatch",
        _mutate_field(sibling, "target", "dependency_profiles", _i(4)),
    )
    add(
        "dependency_profile_wrong_order",
        "dependency_profile_order",
        _mutate_field(
            sibling,
            "target_profile",
            "order",
            _e("supplied_overlay"),
            occurrence=3,
        ),
    )
    add(
        "dependency_profile_sparse_ordinal",
        "sparse_profile_ordinal",
        _mutate_field(sibling, "target_profile", "profile", _i(2), occurrence=3),
    )
    add(
        "dependency_base_mismatch",
        "dependency_base_relation",
        _mutate_field(
            sibling, "target_profile", "profile_release", _s("other"), occurrence=3
        ),
    )
    add(
        "dependency_selected_set_mismatch",
        "dependency_selected_set",
        _mutate_field(sibling, "target_profile", "name", _s("other"), occurrence=4),
    )
    add(
        "availability_count_high",
        "availability_count_mismatch",
        _mutate_field(empty, "target", "availability", _i(2)),
    )
    add(
        "sparse_availability_ordinal",
        "sparse_availability_ordinal",
        _mutate_field(empty, "availability", "occurrence", _i(1)),
    )
    add(
        "duplicate_availability_owner_position",
        "duplicate_availability_owner_position",
        _mutate_field(
            sibling,
            "availability",
            "owner_position",
            _i(0),
            occurrence=1,
        ),
    )
    add(
        "sparse_availability_owner_position",
        "sparse_availability_owner_position",
        _mutate_field(
            sibling,
            "availability",
            "owner_position",
            _i(7),
            occurrence=1,
        ),
    )
    project_first = _mutate_field(
        sibling,
        "availability",
        "owner_kind",
        _e("project"),
    )
    project_first = _mutate_field(
        project_first,
        "availability",
        "project_path",
        _s("logical/project"),
    )
    add(
        "compiler_after_project_availability",
        "availability_owner_partition_order",
        project_first,
    )
    add(
        "compiler_with_project_path",
        "availability_owner_path_relation",
        _mutate_field(empty, "availability", "project_path", _s("logical")),
    )
    add(
        "project_without_path",
        "availability_owner_path_relation",
        _mutate_field(project, "availability", "project_path", CAPABILITY_PURE_ABSENT),
    )
    add(
        "checked_missing_selected_availability",
        "checked_availability_relation",
        _remove_record(
            _mutate_field(empty, "target", "availability", _i(0)),
            _record_position(empty, "availability"),
        ),
    )
    add(
        "blocker_count_high",
        "blocker_count_mismatch",
        _mutate_field(blocked, "target", "blockers", _i(2)),
    )
    add(
        "sparse_blocker_ordinal",
        "sparse_blocker_ordinal",
        _mutate_field(blocked, "blocker", "blocker", _i(1)),
    )
    add(
        "missing_selected_blocker_profile",
        "missing_blocker_profile",
        _remove_record(blocked, _record_position(blocked, "blocker_profile")),
    )
    add(
        "selected_blocker_role_wrong",
        "blocker_profile_role",
        _mutate_field(blocked, "blocker_profile", "role", _s("bucket")),
    )
    add(
        "selected_blocker_profile_foreign",
        "blocker_selected_profile_relation",
        _mutate_field(blocked, "blocker_profile", "name", _s("foreign")),
    )
    add(
        "bucket_flag_without_profile",
        "blocker_bucket_presence",
        _mutate_field(blocked, "blocker", "has_bucket", _b(True)),
    )
    add(
        "mismatch_bucket_zero_occurrences",
        "blocker_bucket_state",
        _mutate_field(bucket, "blocker", "bucket_occurrences", _i(0)),
    )
    add(
        "sparse_blocker_availability",
        "sparse_blocker_availability",
        _mutate_field(bucket, "blocker_availability", "occurrence", _i(1)),
    )
    add(
        "blocker_availability_owner_position_mismatch",
        "blocker_availability_owner_position",
        _mutate_field(bucket, "blocker_availability", "owner_position", _i(1)),
    )
    add(
        "blocker_bucket_profile_mismatch",
        "blocker_bucket_profile_relation",
        _mutate_field(bucket, "blocker_profile", "name", _s("foreign"), occurrence=1),
    )
    add(
        "blocker_availability_profile_mismatch",
        "blocker_availability_profile_relation",
        _mutate_field(bucket, "blocker_availability", "name", _s("foreign")),
    )

    blocked_key = _KeySpec("conversion", "blocked")
    blocked_row = _document(
        declaration="declared",
        targets=(
            _target(
                "blocked",
                availability=(),
                blockers=(_BlockerSpec("profile_not_declared_available", _BASE),),
            ),
        ),
        requirements=(_RequirementSpec(blocked_key, (None,)),),
    )
    add(
        "blocked_cell_fake_check",
        "blocked_cell_fake_check",
        _mutate_field(blocked_row, "cell", "has_check", _b(True)),
    )
    add(
        "checked_cell_without_check",
        "checked_cell_requires_check",
        _mutate_field(checked, "cell", "has_check", _b(False)),
    )
    add(
        "checked_cell_missing_status",
        "checked_cell_complete",
        _mutate_field(checked, "cell", "status", CAPABILITY_PURE_ABSENT),
    )
    add(
        "unchecked_cell_fake_status",
        "unchecked_cell_forbids_status",
        _mutate_field(blocked_row, "cell", "status", _e("unknown")),
    )
    add(
        "target_occurrence_count_high",
        "target_occurrence_count_mismatch",
        _mutate_field(checked, "cell", "target_occurrences", _i(2)),
    )
    add(
        "sparse_target_occurrence",
        "sparse_target_occurrence",
        _mutate_field(checked, "target_occurrence", "occurrence", _i(1)),
    )
    add(
        "target_occurrence_profile_outside",
        "target_profile_coordinate",
        _mutate_field(checked, "target_occurrence", "profile", _i(1)),
    )
    add(
        "target_occurrence_profile_reference_mismatch",
        "target_profile_reference",
        _mutate_field(checked, "target_occurrence", "profile_name", _s("other")),
    )
    add(
        "target_lookup_count_mismatch",
        "target_lookup_fact_count",
        _mutate_field(checked, "cell", "target_lookup_facts", _i(0)),
    )
    add(
        "found_without_fact",
        "found_lookup_posture",
        _mutate_field(checked, "cell", "provider_lookup_facts", _i(0)),
    )
    add(
        "absent_with_fact",
        "absent_lookup_posture",
        _mutate_field(absent, "cell", "provider_lookup_facts", _i(1)),
    )
    add(
        "absent_wrong_reason",
        "absent_lookup_reason",
        _mutate_field(absent, "cell", "provider_reason", _e("not_evidenced")),
    )
    add(
        "unknown_with_fact",
        "unknown_lookup_posture",
        _mutate_field(unknown, "cell", "provider_lookup_facts", _i(1)),
    )
    add(
        "unknown_absence_reason",
        "unknown_lookup_reason",
        _mutate_field(unknown, "cell", "provider_reason", _e("no_catalog_entry")),
    )
    add(
        "conflict_with_one_fact",
        "conflict_lookup_posture",
        _mutate_field(conflict, "cell", "target_lookup_facts", _i(1)),
    )
    add(
        "conflict_wrong_reason",
        "conflict_lookup_reason",
        _mutate_field(conflict, "cell", "target_reason", _e("not_evidenced")),
    )
    add(
        "provider_complete_with_unknown_reason",
        "provider_completeness_posture",
        _mutate_field(checked, "cell", "provider_unknown_reason", _e("not_evidenced")),
    )
    add(
        "provider_complete_unknown_lookup",
        "provider_completeness_posture",
        _mutate_field(unknown, "cell", "provider_domain_complete", _b(True)),
    )
    add(
        "provider_incomplete_absent_lookup",
        "provider_completeness_posture",
        _mutate_field(absent, "cell", "provider_domain_complete", _b(False)),
    )
    add(
        "bounded_unknown_reason_mismatch",
        "provider_unknown_reason_posture",
        _mutate_field(
            unknown, "cell", "provider_unknown_reason", _e("no_current_result_rule")
        ),
    )
    add(
        "undeclared_with_requirement_count",
        "undeclared_forbids_requirements",
        _mutate_field(undeclared, "inspection", "requirements", _i(1)),
    )
    add(
        "target_fact_wrong_scope",
        "target_fact_scope",
        _mutate_field(checked, "target_fact", "target", _i(1)),
    )
    add(
        "provider_fact_wrong_scope",
        "provider_fact_scope",
        _mutate_field(checked, "provider_fact", "target", _i(1)),
    )

    add(
        "target_fact_key_mismatch",
        "fact_key_relation",
        _mutate_field(checked, "target_fact", "subject", _s("other")),
    )
    add(
        "target_fact_operand_count_high",
        "fact_operand_count_mismatch",
        _mutate_field(checked, "target_fact", "operands", _i(3)),
    )
    add(
        "sparse_target_fact_operand",
        "sparse_fact_operand",
        _mutate_field(checked, "target_fact_operand", "operand", _i(1)),
    )
    add(
        "target_fact_operand_value_mismatch",
        "fact_key_relation",
        _mutate_field(checked, "target_fact_operand", "value", _s("other")),
    )
    add(
        "target_fact_evidence_count_high",
        "evidence_count_mismatch",
        _mutate_field(checked, "target_fact", "evidence", _i(2)),
    )
    add(
        "sparse_target_fact_evidence",
        "sparse_evidence_ordinal",
        _mutate_field(checked, "target_fact_evidence", "evidence", _i(1)),
    )
    add(
        "zero_fact_evidence",
        "fact_requires_evidence",
        _mutate_field(checked, "target_fact", "evidence", _i(0)),
    )
    add(
        "invalid_fact_support",
        "invalid_support",
        _mutate_field(checked, "target_fact", "support", _e("maybe")),
    )
    add(
        "invalid_fact_disposition",
        "invalid_disposition",
        _mutate_field(checked, "target_fact", "disposition", _e("later")),
    )
    add(
        "none_disposition_with_owner",
        "disposition_posture",
        _mutate_field(checked, "target_fact", "disposition_owner", _s("owner")),
    )
    add(
        "deferred_disposition_missing_owner",
        "disposition_posture",
        _mutate_field(
            disposition, "target_fact", "disposition_owner", CAPABILITY_PURE_ABSENT
        ),
    )
    add(
        "invalid_evidence_source",
        "invalid_evidence_source",
        _mutate_field(checked, "target_fact_evidence", "source", _e("external")),
    )
    add(
        "invalid_evidence_reason",
        "invalid_evidence_reason",
        _mutate_field(checked, "target_fact_evidence", "reason", _e("other")),
    )
    add(
        "evidence_extension_without_dialect",
        "evidence_scope_posture",
        _mutate_field(checked, "target_fact_evidence", "extension", _s("ext")),
    )
    add(
        "evidence_optional_wrong_tag",
        "malformed_optional_scope",
        _mutate_field(checked, "target_fact_evidence", "dialect", _e("postgresql")),
    )
    add(
        "sparse_provider_fact_ordinal",
        "sparse_provider_fact",
        _mutate_field(checked, "provider_fact", "fact", _i(1)),
    )
    add(
        "sparse_provider_fact_operand",
        "sparse_provider_fact_operand",
        _mutate_field(checked, "provider_fact_operand", "operand", _i(1)),
    )
    add(
        "sparse_provider_evidence",
        "sparse_provider_evidence",
        _mutate_field(checked, "provider_fact_evidence", "evidence", _i(1)),
    )
    add(
        "provider_evidence_wrong_scope",
        "provider_evidence_scope",
        _mutate_field(checked, "provider_fact_evidence", "target", _i(1)),
    )
    add(
        "target_evidence_wrong_scope",
        "target_evidence_scope",
        _mutate_field(checked, "target_fact_evidence", "target", _i(1)),
    )
    return tuple(cases)


_REJECTION_EXPECTATIONS: Mapping[
    str,
    tuple[CapabilityPureStatus, int | None, int | None],
] = MappingProxyType(
    {
        "empty_document": (CapabilityPureStatus.EMPTY_DOCUMENT, None, None),
        "missing_header": (CapabilityPureStatus.MISSING_HEADER_RECORD, 0, None),
        "unknown_package_kind": (CapabilityPureStatus.UNKNOWN_RECORD_KIND, 1, None),
        "wrong_format_marker": (CapabilityPureStatus.UNKNOWN_FORMAT_MARKER, 0, 0),
        "duplicate_header": (
            CapabilityPureStatus.DUPLICATE_SINGLETON_RECORD,
            1,
            None,
        ),
        "duplicate_package": (
            CapabilityPureStatus.DUPLICATE_SINGLETON_RECORD,
            2,
            None,
        ),
        "missing_header_field": (
            CapabilityPureStatus.FIELD_ARITY_MISMATCH,
            0,
            None,
        ),
        "extra_header_field": (
            CapabilityPureStatus.FIELD_ARITY_MISMATCH,
            0,
            None,
        ),
        "wrong_header_field_order": (
            CapabilityPureStatus.FIELD_KEY_MISMATCH,
            0,
            0,
        ),
        "wrong_header_scalar_tag": (
            CapabilityPureStatus.VALUE_TAG_MISMATCH,
            0,
            0,
        ),
        "required_header_absent": (
            CapabilityPureStatus.ABSENT_VALUE_NOT_ALLOWED,
            0,
            0,
        ),
        "absent_with_payload": (CapabilityPureStatus.EXTRA_VALUE_PAYLOAD, 4, 11),
        "missing_enum_payload": (CapabilityPureStatus.MISSING_VALUE_PAYLOAD, 0, 0),
        "extra_enum_payload": (CapabilityPureStatus.EXTRA_VALUE_PAYLOAD, 0, 0),
        "negative_target_count": (CapabilityPureStatus.NEGATIVE_INTEGER, 0, 2),
        "overflow_target_count": (
            CapabilityPureStatus.INTEGER_OUT_OF_RANGE,
            0,
            2,
        ),
        "unknown_declaration_enum": (
            CapabilityPureStatus.UNKNOWN_ENUMERATION,
            0,
            1,
        ),
        "missing_boolean_payload": (
            CapabilityPureStatus.MISSING_VALUE_PAYLOAD,
            10,
            2,
        ),
        "missing_package": (CapabilityPureStatus.SECTION_ORDER_VIOLATION, 1, None),
        "missing_requirements_header": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            2,
            None,
        ),
        "requirements_on_undeclared": (
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            2,
            None,
        ),
        "requirements_count_mismatch": (
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            2,
            2,
        ),
        "trailing_target_record": (
            CapabilityPureStatus.TRAILING_RECORD_AFTER_DOCUMENT,
            6,
            None,
        ),
        "target_count_high": (CapabilityPureStatus.MISSING_REQUIRED_RECORD, 0, None),
        "sparse_target_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            2,
            0,
        ),
        "duplicate_target_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            7,
            0,
        ),
        "requirement_count_high": (
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            2,
            2,
        ),
        "sparse_requirement_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            7,
            0,
        ),
        "duplicate_requirement_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            30,
            0,
        ),
        "requirement_operand_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            7,
            None,
        ),
        "sparse_requirement_operand": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            8,
            1,
        ),
        "missing_cell": (CapabilityPureStatus.CHILD_COUNT_MISMATCH, 7, None),
        "cell_wrong_target": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            10,
            None,
        ),
        "cell_wrong_requirement": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            10,
            None,
        ),
        "missing_base_profile": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            4,
            1,
        ),
        "base_profile_wrong_order": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            4,
            1,
        ),
        "base_profile_sparse_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            4,
            2,
        ),
        "base_profile_wrong_kind": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            4,
            7,
        ),
        "base_profile_wrong_target_kind": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            4,
            7,
        ),
        "supplied_overlay_count_high": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            7,
            1,
        ),
        "supplied_overlay_wrong_order": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            5,
            1,
        ),
        "supplied_overlay_sparse_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            5,
            2,
        ),
        "dependency_profile_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            3,
            None,
        ),
        "dependency_profile_wrong_order": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            7,
            1,
        ),
        "dependency_profile_sparse_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            7,
            2,
        ),
        "dependency_base_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            3,
            None,
        ),
        "dependency_selected_set_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            3,
            None,
        ),
        "availability_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            3,
            None,
        ),
        "sparse_availability_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            6,
            1,
        ),
        "duplicate_availability_owner_position": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            11,
            3,
        ),
        "sparse_availability_owner_position": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            11,
            3,
        ),
        "compiler_after_project_availability": (
            CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            11,
            2,
        ),
        "compiler_with_project_path": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            6,
            4,
        ),
        "project_without_path": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            6,
            4,
        ),
        "checked_missing_selected_availability": (
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            3,
            None,
        ),
        "blocker_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            3,
            None,
        ),
        "sparse_blocker_ordinal": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            6,
            1,
        ),
        "missing_selected_blocker_profile": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            6,
            None,
        ),
        "selected_blocker_role_wrong": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            7,
            2,
        ),
        "selected_blocker_profile_foreign": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
            None,
        ),
        "bucket_flag_without_profile": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            6,
            None,
        ),
        "mismatch_bucket_zero_occurrences": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
            None,
        ),
        "sparse_blocker_availability": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            10,
            2,
        ),
        "blocker_availability_owner_position_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            7,
            None,
        ),
        "blocker_bucket_profile_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            9,
            None,
        ),
        "blocker_availability_profile_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            10,
            None,
        ),
        "blocked_cell_fake_check": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            9,
            2,
        ),
        "checked_cell_without_check": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            2,
        ),
        "checked_cell_missing_status": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "unchecked_cell_fake_status": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            9,
            None,
        ),
        "target_occurrence_count_high": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "sparse_target_occurrence": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            11,
            2,
        ),
        "target_occurrence_profile_outside": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            11,
            3,
        ),
        "target_occurrence_profile_reference_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            11,
            None,
        ),
        "target_lookup_count_mismatch": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "found_without_fact": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "absent_with_fact": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "absent_wrong_reason": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "unknown_with_fact": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "unknown_absence_reason": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "conflict_with_one_fact": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "conflict_wrong_reason": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "provider_complete_with_unknown_reason": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "provider_complete_unknown_lookup": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "provider_incomplete_absent_lookup": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "bounded_unknown_reason_mismatch": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            10,
            None,
        ),
        "undeclared_with_requirement_count": (
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            0,
            None,
        ),
        "target_fact_wrong_scope": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            12,
            None,
        ),
        "provider_fact_wrong_scope": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            16,
            None,
        ),
        "target_fact_key_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            12,
            None,
        ),
        "target_fact_operand_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            12,
            None,
        ),
        "sparse_target_fact_operand": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            13,
            3,
        ),
        "target_fact_operand_value_mismatch": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            12,
            None,
        ),
        "target_fact_evidence_count_high": (
            CapabilityPureStatus.CHILD_COUNT_MISMATCH,
            12,
            None,
        ),
        "sparse_target_fact_evidence": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            15,
            3,
        ),
        "zero_fact_evidence": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            12,
            None,
        ),
        "invalid_fact_support": (
            CapabilityPureStatus.UNKNOWN_ENUMERATION,
            12,
            10,
        ),
        "invalid_fact_disposition": (
            CapabilityPureStatus.UNKNOWN_ENUMERATION,
            12,
            11,
        ),
        "none_disposition_with_owner": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            12,
            None,
        ),
        "deferred_disposition_missing_owner": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            12,
            None,
        ),
        "invalid_evidence_source": (
            CapabilityPureStatus.UNKNOWN_ENUMERATION,
            15,
            4,
        ),
        "invalid_evidence_reason": (
            CapabilityPureStatus.UNKNOWN_ENUMERATION,
            15,
            7,
        ),
        "evidence_extension_without_dialect": (
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            15,
            None,
        ),
        "evidence_optional_wrong_tag": (
            CapabilityPureStatus.VALUE_TAG_MISMATCH,
            15,
            8,
        ),
        "sparse_provider_fact_ordinal": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            16,
            None,
        ),
        "sparse_provider_fact_operand": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            17,
            3,
        ),
        "sparse_provider_evidence": (
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            19,
            3,
        ),
        "provider_evidence_wrong_scope": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            19,
            None,
        ),
        "target_evidence_wrong_scope": (
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            15,
            None,
        ),
    }
)


def _rejected_vectors() -> tuple[CapabilityDifferentialVector, ...]:
    return tuple(
        CapabilityDifferentialVector(
            vector_format=CAPABILITY_DIFFERENTIAL_VECTOR_FORMAT,
            vector_id=vector_id,
            purposes=purposes,
            classification=CapabilityDifferentialClassification.PORTABLE_REJECTION,
            document=document,
            expected_status=_REJECTION_EXPECTATIONS[vector_id][0],
            expected_record_position=_REJECTION_EXPECTATIONS[vector_id][1],
            expected_field_position=_REJECTION_EXPECTATIONS[vector_id][2],
        )
        for vector_id, purposes, document in _rejected_documents()
    )


def differential_vectors() -> tuple[CapabilityDifferentialVector, ...]:
    accepted_ids = {
        "undeclared_root",
        "declared_empty_root",
        "declared_empty_dependency",
        "checked_satisfied",
        "checked_unsupported",
        "checked_absent",
        "checked_unknown",
        "checked_conflict",
        "blocked_with_bucket",
        "two_by_two_matrix",
        "sibling_overlays",
        "overlay_dependency_chain",
        "project_availability",
        "unicode_control_escaping",
        "extension_signature_overlay",
        "disposition_ordered_evidence",
    }
    accepted = tuple(
        CapabilityDifferentialVector(
            vector_format=CAPABILITY_DIFFERENTIAL_VECTOR_FORMAT,
            vector_id=vector_id,
            purposes=purposes,
            classification=CapabilityDifferentialClassification.PORTABLE_EVALUATION,
            document=document,
            expected_status=CapabilityPureStatus.OK,
            expected_bytes=EXPECTED_CANONICAL_BYTES.get(vector_id),
        )
        for vector_id, purposes, document in _accepted_documents()
        if vector_id in accepted_ids
    )
    return (*accepted, *_rejected_vectors())
