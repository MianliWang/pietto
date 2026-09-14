"""Explicit, non-executable assessment of a complete verified requirement report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Never

from pietto.ast_nodes import NameExpr, DottedNameExpr
from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_target_mapping as mapping
from pietto._project.project_sql_plan_verification import ProjectSQLPlanVerification
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
)
from pietto.semantic import capability_providers as providers
from pietto.semantic import capability_inventory as inventory
from pietto.semantic import capability_signatures as signatures
from pietto.semantic import capability_aggregates as aggregates
from pietto.semantic import capability_windows as windows
from pietto.semantic.capability_facts import (
    CapabilityDomain as D,
    CapabilityKey,
    CapabilitySupport,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import (
    Found,
    Absent,
    Unknown,
    Conflict,
    CapabilityLookupResult,
    lookup_capability,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    StaticCapabilityProfile,
    CapabilityProfileKind,
)
from pietto.semantic.capability_composition import (
    compose_capability_profiles,
    CapabilityProfileCompositionResult,
    CapabilityProfileCompositionSuccess,
    CapabilityProfileCompositionBlocked,
    EffectiveCapabilityProfileFactOccurrence,
)
from pietto.semantic.extension_signature_requirements import (
    extension_signature_dialect_family_bridge,
)

__all__: tuple[str, ...] = ()


class TargetInputIssue(StrEnum):
    PROFILE_MISSING = "explicit_target_profile_missing"
    TARGET_MISMATCH = "profile_target_family_or_release_mismatch"
    COMPOSITION_BLOCKED = "profile_composition_blocked"
    CATALOG_UNMAPPED = "no_plan_extension_selector_mapping"
    CATALOG_TARGET_MISMATCH = "catalog_database_family_or_release_mismatch"


@dataclass(frozen=True, slots=True, eq=False)
class TargetCatalogResidual:
    position: int
    context: ExtensionSignatureProviderContext
    selector: object
    selection: object
    issues: tuple[TargetInputIssue, ...]


@dataclass(frozen=True, slots=True, eq=False, init=False)
class ProjectSQLTargetRequest:
    target: CapabilityProfileTarget | None
    base: StaticCapabilityProfile | None
    overlays: tuple[StaticCapabilityProfile, ...]
    composition: CapabilityProfileCompositionResult | None
    catalog_context: ExtensionSignatureProviderContext | None
    catalog_residuals: tuple[TargetCatalogResidual, ...]
    issues: tuple[TargetInputIssue, ...]
    _roots: tuple[object, ...]

    def __init__(self) -> Never:
        raise TypeError("Target requests require explicit preparation.")


def _same(actual, expected) -> bool:
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def prepare_project_sql_target_request(
    target: CapabilityProfileTarget | None = None,
    *,
    base: StaticCapabilityProfile | None = None,
    overlays: tuple[StaticCapabilityProfile, ...] = (),
    catalog_context: ExtensionSignatureProviderContext | None = None,
) -> ProjectSQLTargetRequest:
    if target is not None and (
        type(target) is not CapabilityProfileTarget
        or target.kind is not CapabilityProfileTargetKind.DATABASE
    ):
        raise ValueError("Target assessment requires an exact DATABASE target.")
    if base is not None and type(base) is not StaticCapabilityProfile:
        raise ValueError("Target assessment requires an exact static profile.")
    if type(overlays) is not tuple or any(
        type(p) is not StaticCapabilityProfile for p in overlays
    ):
        raise ValueError("Target assessment requires ordered exact overlays.")
    if (
        catalog_context is not None
        and type(catalog_context) is not ExtensionSignatureProviderContext
    ):
        raise ValueError("Target assessment requires an exact catalog context.")
    if target is None and (base is not None or overlays or catalog_context is not None):
        raise ValueError("Omitted target forbids selected target evidence.")
    if base is None and overlays:
        raise ValueError("Target overlays require an explicit base profile.")
    composition = None if base is None else compose_capability_profiles(base, overlays)
    issues = []
    if target is not None:
        if base is None:
            issues.append(TargetInputIssue.PROFILE_MISSING)
        if any(
            p.target.family != target.family or p.target.release != target.release
            for p in (() if base is None else (base, *overlays))
        ):
            issues.append(TargetInputIssue.TARGET_MISMATCH)
        if type(composition) is CapabilityProfileCompositionBlocked:
            issues.append(TargetInputIssue.COMPOSITION_BLOCKED)
    catalog_residuals = []
    if catalog_context is not None:
        for position, (selector, selection) in enumerate(
            zip(
                catalog_context.selectors.occurrences,
                catalog_context.selections,
                strict=True,
            )
        ):
            requested = selection.selection.requested_target
            reasons = [TargetInputIssue.CATALOG_UNMAPPED]
            bridge = (
                None
                if target is None
                else extension_signature_dialect_family_bridge(target.family)
            )
            if (
                target is None
                or bridge is None
                or requested.database_family != bridge.database_family
                or requested.database_release != target.release
            ):
                reasons.append(TargetInputIssue.CATALOG_TARGET_MISMATCH)
            catalog_residuals.append(
                TargetCatalogResidual(
                    position, catalog_context, selector, selection, tuple(reasons)
                )
            )
        if catalog_residuals:
            issues.append(TargetInputIssue.CATALOG_UNMAPPED)
        if any(
            TargetInputIssue.CATALOG_TARGET_MISMATCH in r.issues
            for r in catalog_residuals
        ):
            issues.append(TargetInputIssue.CATALOG_TARGET_MISMATCH)
    value = object.__new__(ProjectSQLTargetRequest)
    for name, item in {
        "target": target,
        "base": base,
        "overlays": overlays,
        "composition": composition,
        "catalog_context": catalog_context,
        "catalog_residuals": tuple(catalog_residuals),
        "issues": tuple(issues),
        "_roots": (target, base, overlays, composition, catalog_context),
    }.items():
        object.__setattr__(value, name, item)
    if not _check_request(value):
        raise ValueError("Target request evidence is inconsistent.")
    return value


def _check_request(request: ProjectSQLTargetRequest) -> bool:
    if type(request) is not ProjectSQLTargetRequest or not _same(
        request._roots,
        (
            request.target,
            request.base,
            request.overlays,
            request.composition,
            request.catalog_context,
        ),
    ):
        return False
    target, base, composition = request.target, request.base, request.composition
    if target is None:
        return (
            base is None
            and request.overlays == ()
            and composition is None
            and request.catalog_context is None
            and request.catalog_residuals == ()
            and request.issues == ()
        )
    if (
        type(target) is not CapabilityProfileTarget
        or target.kind is not CapabilityProfileTargetKind.DATABASE
    ):
        return False
    target.__post_init__()
    if type(request.overlays) is not tuple:
        return False
    profiles = () if base is None else (base, *request.overlays)
    for profile in profiles:
        if type(profile) is not StaticCapabilityProfile:
            return False
        # Profile validation freezes supplied tuples only, and acquires no evidence.
        profile.__post_init__()
        for position, occurrence in enumerate(profile.capability_occurrences):
            if (
                type(occurrence.position) is not int
                or occurrence.position != position
                or occurrence.owner is not profile.profile
            ):
                return False
            occurrence.__post_init__()
        for position, occurrence in enumerate(profile.base_occurrences):
            if type(occurrence.position) is not int or occurrence.position != position:
                return False
            occurrence.__post_init__()
    if base is None:
        if composition is not None or request.overlays:
            return False
    else:
        if not isinstance(
            composition,
            (CapabilityProfileCompositionSuccess, CapabilityProfileCompositionBlocked),
        ):
            return False
        if (
            type(composition)
            not in (
                CapabilityProfileCompositionSuccess,
                CapabilityProfileCompositionBlocked,
            )
            or composition.base is not base
            or not _same(composition.overlays, request.overlays)
        ):
            return False
        composition.__post_init__()
        if isinstance(composition, CapabilityProfileCompositionSuccess):
            if base.kind is not CapabilityProfileKind.BASE or len(
                {p.profile for p in profiles}
            ) != len(profiles):
                return False
            ordered = composition.dependency_order
            remaining = list(request.overlays)
            seen = {base.profile}
            for profile in ordered[1:]:
                eligible = [p for p in remaining if p.base_occurrences[0].base in seen]
                if not eligible or profile is not eligible[0]:
                    return False
                remaining.remove(profile)
                seen.add(profile.profile)
            if remaining:
                return False
            facts = tuple(o.fact for p in ordered for o in p.capability_occurrences)
            if len(set(facts)) != len(facts):
                return False
        else:
            for blocker in composition.blockers:
                blocker.__post_init__()
                if any(
                    not any(p is selected for selected in profiles)
                    for p in blocker.profiles
                ):
                    return False
    mismatch = any(
        p.target.family != target.family or p.target.release != target.release
        for p in profiles
    )
    context = request.catalog_context
    if context is None:
        if request.catalog_residuals:
            return False
    else:
        if type(context) is not ExtensionSignatureProviderContext:
            return False
        context.__post_init__()
        if type(request.catalog_residuals) is not tuple or len(
            request.catalog_residuals
        ) != len(context.selections):
            return False
        for i, residual in enumerate(request.catalog_residuals):
            selection, selector = (
                context.selections[i],
                context.selectors.occurrences[i],
            )
            selection.__post_init__()
            selector.__post_init__()
            requested = selection.selection.requested_target
            bridge = extension_signature_dialect_family_bridge(target.family)
            mismatch_catalog = (
                bridge is None
                or requested.database_family != bridge.database_family
                or requested.database_release != target.release
            )
            expected = (
                (
                    TargetInputIssue.CATALOG_UNMAPPED,
                    TargetInputIssue.CATALOG_TARGET_MISMATCH,
                )
                if mismatch_catalog
                else (TargetInputIssue.CATALOG_UNMAPPED,)
            )
            if (
                type(residual) is not TargetCatalogResidual
                or type(residual.position) is not int
                or residual.position != i
                or residual.context is not context
                or residual.selector is not selector
                or residual.selection is not selection
                or residual.issues != expected
            ):
                return False
    expected_issues = []
    if base is None:
        expected_issues.append(TargetInputIssue.PROFILE_MISSING)
    if mismatch:
        expected_issues.append(TargetInputIssue.TARGET_MISMATCH)
    if type(composition) is CapabilityProfileCompositionBlocked:
        expected_issues.append(TargetInputIssue.COMPOSITION_BLOCKED)
    if request.catalog_residuals:
        expected_issues.append(TargetInputIssue.CATALOG_UNMAPPED)
    if any(
        TargetInputIssue.CATALOG_TARGET_MISMATCH in r.issues
        for r in request.catalog_residuals
    ):
        expected_issues.append(TargetInputIssue.CATALOG_TARGET_MISMATCH)
    return _same(request.issues, tuple(expected_issues))


class AspectOutcome(StrEnum):
    SATISFIED = "satisfied_exact_subproposition"
    NEGATIVE = "exact_negative"
    ABSENT = "complete_provider_domain_absent"
    UNKNOWN = "incomplete_lookup_unknown"
    CONFLICT = "conflicting_facts"
    UNMAPPED = "unmapped_proposition"
    INAPPLICABLE = "inapplicable_declared_evidence"
    INPUT_UNRESOLVED = "explicit_input_unresolved"
    NOT_ASSESSED = "not_assessed"


class AssessmentPosture(StrEnum):
    NOT_ASSESSED = "not_assessed"
    INCOMPLETE = "incomplete_requirement_assessment"
    SATISFIED = "complete_requirements_satisfied"


S = AspectOutcome


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLTargetLookup:
    position: int
    request: ProjectSQLTargetRequest
    kind: mapping.PropositionKind
    key: CapabilityKey
    inputs: providers.CanonicalCapabilityProviderInputs
    profile_occurrences: tuple[EffectiveCapabilityProfileFactOccurrence, ...]
    provider_result: CapabilityLookupResult
    profile_result: CapabilityLookupResult
    # Declared compiler-proposition scope only; not database conformance.
    profile_applicable: bool


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLTargetAspect:
    position: int
    ordinal: int
    entry: reports.ProjectSQLDemandEntry
    proposition: mapping.ProjectSQLTargetProposition
    lookup: ProjectSQLTargetLookup | None
    outcomes: tuple[AspectOutcome, ...]


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLTargetDemand:
    position: int
    entry: reports.ProjectSQLDemandEntry
    aspects: tuple[ProjectSQLTargetAspect, ...]
    posture: AssessmentPosture


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLTargetSummary:
    demand_count: int
    aspect_count: int
    query_count: int
    posture: AssessmentPosture
    categories: Mapping[AspectOutcome, tuple[ProjectSQLTargetAspect, ...]]
    pending_realizations: tuple[ProjectSQLTargetAspect, ...]
    original_obligations: reports.ProjectSQLRequirementSummary
    input_issues: tuple[TargetInputIssue, ...]
    catalog_residuals: tuple[TargetCatalogResidual, ...]


@dataclass(frozen=True, slots=True, eq=False, init=False)
class ProjectSQLTargetAssessment:
    source_verification: ProjectSQLPlanVerification
    request: ProjectSQLTargetRequest
    request_roots: tuple[object, ...]
    report_verification: reports.ProjectSQLRequirementVerification
    report: reports.ProjectSQLRequirementReport
    demands: tuple[ProjectSQLTargetDemand, ...]
    aspects: tuple[ProjectSQLTargetAspect, ...]
    lookups: tuple[ProjectSQLTargetLookup, ...]
    by_demand: Mapping[sql.ProjectSQLPlanRef, ProjectSQLTargetDemand]
    uses: Mapping[ProjectSQLTargetLookup, tuple[ProjectSQLTargetAspect, ...]]
    summary: ProjectSQLTargetSummary

    def __init__(self) -> Never:
        raise TypeError("Target assessments require canonical construction.")


def _profile_occurrences(request):
    composition = request.composition
    if type(composition) is CapabilityProfileCompositionSuccess:
        return composition.effective_occurrences
    return ()


def _family(demand):
    callee = demand.source.connector.callee
    if type(callee) is NameExpr:
        return {"postgres.table": "postgresql", "mysql.table": "mysql"}.get(callee.name)
    if type(callee) is DottedNameExpr:
        bridge: Mapping[tuple[str, ...], str] = {
            ("postgres", "table"): "postgresql",
            ("mysql", "table"): "mysql",
        }
        return bridge.get(callee.parts)
    return None


def _applicable(request, result) -> bool:
    """Only explicit declaration scope, never measured database conformance."""
    if any(
        i in request.issues
        for i in (
            TargetInputIssue.TARGET_MISMATCH,
            TargetInputIssue.PROFILE_MISSING,
            TargetInputIssue.COMPOSITION_BLOCKED,
        )
    ):
        return False
    if not isinstance(result, (Found, Conflict)):
        return True
    facts = (result.fact,) if isinstance(result, Found) else result.evidence
    target = request.target
    # Compiler facts can cite several backends. These atoms are provenance;
    # the language proposition remains unscoped. Wholly scoped declarations
    # still require the selected target, and extension evidence cannot leak in.
    return target is not None and all(
        all(e.extension in (None, fact.key.extension) for e in fact.evidence)
        and (
            any(e.dialect is None for e in fact.evidence)
            or all(e.dialect == target.family for e in fact.evidence)
        )
        for fact in facts
    )


def _outcomes(proposition, lookup, request):
    if request.target is None:
        return (S.NOT_ASSESSED,)
    if proposition.kind is mapping.K.SOURCE_FAMILY:
        return (
            (S.SATISFIED,)
            if _family(proposition.witness) == request.target.family
            else (S.NEGATIVE,)
        )
    if proposition.key is None:
        return (S.UNMAPPED,)
    results = (lookup.provider_result, lookup.profile_result)
    states = set()
    if any(type(r) is Conflict for r in results):
        states.add(S.CONFLICT)
    if any(
        type(r) is Found and r.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        for r in results
    ):
        states.add(S.NEGATIVE)
    if any(type(r) is Absent for r in results):
        states.add(S.ABSENT)
    if any(type(r) is Unknown for r in results):
        states.add(S.UNKNOWN)
    if any(
        i in request.issues
        for i in (
            TargetInputIssue.PROFILE_MISSING,
            TargetInputIssue.TARGET_MISMATCH,
            TargetInputIssue.COMPOSITION_BLOCKED,
        )
    ):
        states.add(S.INPUT_UNRESOLVED)
    if not lookup.profile_applicable:
        states.add(S.INAPPLICABLE)
    if not states and all(
        type(r) is Found and r.fact.support is CapabilitySupport.SUPPORTED
        for r in results
    ):
        states.add(S.SATISFIED)
    return tuple(o for o in S if o in states)


def _posture(target, aspects):
    if target is None:
        return AssessmentPosture.NOT_ASSESSED
    return (
        AssessmentPosture.SATISFIED
        if aspects and all(a.outcomes == (S.SATISFIED,) for a in aspects)
        else AssessmentPosture.INCOMPLETE
    )


def _build_assessment(
    source_verification: ProjectSQLPlanVerification,
    request: ProjectSQLTargetRequest,
    *,
    report_verification: reports.ProjectSQLRequirementVerification | None = None,
) -> ProjectSQLTargetAssessment:
    if not _check_request(request):
        raise ValueError("Target request evidence is inconsistent.")
    if report_verification is None:
        report = reports.build_project_sql_requirement_report(source_verification)
        report_verification = reports.verify_project_sql_requirement_report(
            report, source_verification
        )
    else:
        if type(report_verification) is not reports.ProjectSQLRequirementVerification:
            raise ValueError("Target assessment requires an exact report verification.")
        report = report_verification.report
    if (
        type(report_verification) is not reports.ProjectSQLRequirementVerification
        or report_verification.source_verification is not source_verification
        or not report_verification.verified
        or not reports.verify_project_sql_requirement_report(
            report, source_verification
        ).verified
    ):
        raise ValueError("Target assessment requires an exact current VERIFIED report.")
    expressions = {e.ref: e for e in report.plan.expressions}
    occurrences = _profile_occurrences(request)
    profile_facts = tuple(o.fact for o in occurrences)
    demands, aspects, lookups = [], [], []
    shared = {}
    for entry in report.entries:
        local = []
        for ordinal, proposition in enumerate(
            mapping.build_propositions(entry, expressions)
        ):
            lookup = None
            key = proposition.key
            if key is not None and request.target is not None:
                share_key = (proposition.kind, key)
                if share_key not in shared:
                    inputs = providers.canonical_capability_provider_inputs(key)
                    profile_result = lookup_capability(
                        key, profile_facts, domain_complete=False
                    )
                    lookup = ProjectSQLTargetLookup(
                        len(lookups),
                        request,
                        proposition.kind,
                        key,
                        inputs,
                        occurrences,
                        lookup_capability(
                            key,
                            inputs.facts,
                            domain_complete=inputs.domain_complete,
                            unknown_reason=inputs.unknown_reason,
                        ),
                        profile_result,
                        _applicable(request, profile_result),
                    )
                    shared[share_key] = lookup
                    lookups.append(lookup)
                lookup = shared[share_key]
            aspect = ProjectSQLTargetAspect(
                len(aspects),
                ordinal,
                entry,
                proposition,
                lookup,
                _outcomes(proposition, lookup, request),
            )
            aspects.append(aspect)
            local.append(aspect)
        demands.append(
            ProjectSQLTargetDemand(
                len(demands), entry, tuple(local), _posture(request.target, local)
            )
        )
    summary = ProjectSQLTargetSummary(
        len(demands),
        len(aspects),
        len(lookups),
        _posture(request.target, aspects),
        MappingProxyType({o: tuple(a for a in aspects if o in a.outcomes) for o in S}),
        tuple(a for a in aspects if a.proposition.kind is mapping.K.RESIDUAL),
        report.summary,
        request.issues,
        request.catalog_residuals,
    )
    product = object.__new__(ProjectSQLTargetAssessment)
    for name, value in {
        "source_verification": source_verification,
        "request": request,
        "request_roots": request._roots,
        "report_verification": report_verification,
        "report": report,
        "demands": tuple(demands),
        "aspects": tuple(aspects),
        "lookups": tuple(lookups),
        "by_demand": MappingProxyType({d.entry.ref: d for d in demands}),
        "uses": MappingProxyType(
            {q: tuple(a for a in aspects if a.lookup is q) for q in lookups}
        ),
        "summary": summary,
    }.items():
        object.__setattr__(product, name, value)
    return product


def build_project_sql_target_assessment(
    source_verification: ProjectSQLPlanVerification,
    request: ProjectSQLTargetRequest,
    *,
    report_verification: reports.ProjectSQLRequirementVerification | None = None,
) -> ProjectSQLTargetAssessment:
    try:
        return _build_assessment(
            source_verification, request, report_verification=report_verification
        )
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        raise ValueError(
            "Target assessment requires consistent verified inputs and retained evidence."
        ) from None


class TargetAssessmentIssue(StrEnum):
    ROOTS = "target_assessment_roots"
    STRUCTURE = "target_assessment_structure"
    MAPPING = "target_assessment_mapping"
    EVIDENCE = "target_assessment_evidence"
    OUTCOMES = "target_assessment_outcomes"
    INDEXES = "target_assessment_indexes"
    SUMMARY = "target_assessment_summary"


def _lookup_matches(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is Found:
        return actual.fact is expected.fact
    if type(expected) is Conflict:
        return actual.reason is expected.reason and _same(
            actual.evidence, expected.evidence
        )
    if type(expected) is Absent:
        return actual.key is expected.key and actual.reason is expected.reason
    return actual.reason is expected.reason


def _check_provider(query):
    """Validate canonical membership against original inventories, without dispatch."""
    key, inputs = query.key, query.inputs
    if (
        type(inputs) is not providers.CanonicalCapabilityProviderInputs
        or inputs.key is not key
    ):
        return False
    reason = None
    if key.domain is D.LOGICAL_TYPE:
        facts = (*inventory._LOGICAL_TYPE_FACTS, *inventory._NULLABILITY_FACTS)
        complete = inventory._schema_is_complete(key)
    elif key.domain is D.LITERAL:
        facts, complete = inventory._LITERAL_FACTS, inventory._schema_is_complete(key)
    elif key.domain in (
        D.SCALAR_FUNCTION,
        D.UNARY_OPERATOR,
        D.BINARY_OPERATOR,
        D.COMPARISON,
        D.NULL_TEST,
    ):
        facts = {
            D.SCALAR_FUNCTION: signatures._SCALAR_FUNCTION_FACTS,
            D.UNARY_OPERATOR: signatures._UNARY_OPERATOR_FACTS,
            D.BINARY_OPERATOR: signatures._BINARY_OPERATOR_FACTS,
            D.COMPARISON: signatures._COMPARISON_FACTS,
            D.NULL_TEST: signatures._NULL_TEST_FACTS,
        }[key.domain]
        complete = signatures._schema_is_complete(key)
        reason = None if complete else signatures._unknown_reason(key)
    elif key.domain is D.AGGREGATE and key.context == "aggregate_signature":
        facts, complete = (
            aggregates._AGGREGATE_SIGNATURE_FACTS,
            aggregates._signature_schema_is_complete(key),
        )
        reason = None if complete else CapabilityReasonCode.NOT_EVIDENCED
    elif key.domain is D.WINDOW_FUNCTION and key.context == "window_signature":
        facts, complete = (
            windows._WINDOW_SIGNATURE_FACTS,
            windows._signature_schema_is_complete(key),
        )
        reason = None if complete else CapabilityReasonCode.NOT_EVIDENCED
    else:
        return False
    return (
        _same(inputs.facts, facts)
        and type(inputs.domain_complete) is bool
        and inputs.domain_complete is complete
        and inputs.unknown_reason is reason
    )


def _check_outcomes(aspect, request):
    states, proposition, query = aspect.outcomes, aspect.proposition, aspect.lookup
    if (
        type(states) is not tuple
        or any(type(o) is not S for o in states)
        or len(set(states)) != len(states)
        or tuple(o for o in S if o in states) != states
    ):
        return False
    if request.target is None:
        return states == (S.NOT_ASSESSED,)
    if proposition.kind is mapping.K.SOURCE_FAMILY:
        callee = proposition.witness.source.connector.callee
        parts = (
            callee.parts
            if type(callee) is DottedNameExpr
            else {
                "postgres.table": ("postgres", "table"),
                "mysql.table": ("mysql", "table"),
            }.get(callee.name)
        )
        matches = (
            parts == ("postgres", "table") and request.target.family == "postgresql"
        ) or (parts == ("mysql", "table") and request.target.family == "mysql")
        return states == ((S.SATISFIED,) if matches else (S.NEGATIVE,))
    if proposition.key is None:
        return states == (S.UNMAPPED,)
    if query is None:
        return False
    raw = (query.provider_result, query.profile_result)
    negative = any(
        type(r) is Found and r.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        for r in raw
    )
    absent = any(type(r) is Absent for r in raw)
    unknown = any(type(r) is Unknown for r in raw)
    conflict = any(type(r) is Conflict for r in raw)
    declared = query.profile_result
    facts = (
        (declared.fact,)
        if isinstance(declared, Found)
        else declared.evidence
        if isinstance(declared, Conflict)
        else ()
    )
    applicable = all(
        all(e.extension is None for e in fact.evidence)
        and (
            any(e.dialect is None for e in fact.evidence)
            or all(e.dialect == request.target.family for e in fact.evidence)
        )
        for fact in facts
    )
    unresolved = any(
        i in request.issues
        for i in (
            TargetInputIssue.PROFILE_MISSING,
            TargetInputIssue.TARGET_MISMATCH,
            TargetInputIssue.COMPOSITION_BLOCKED,
        )
    )
    applicable = applicable and not unresolved
    if (
        type(query.profile_applicable) is not bool
        or query.profile_applicable is not applicable
    ):
        return False
    satisfied = (
        not unresolved
        and applicable
        and all(
            type(r) is Found and r.fact.support is CapabilitySupport.SUPPORTED
            for r in raw
        )
    )
    tests = {
        S.SATISFIED: satisfied,
        S.NEGATIVE: negative,
        S.ABSENT: absent,
        S.UNKNOWN: unknown,
        S.CONFLICT: conflict,
        S.INAPPLICABLE: not applicable,
        S.INPUT_UNRESOLVED: unresolved,
        S.UNMAPPED: False,
        S.NOT_ASSESSED: False,
    }
    return bool(states) and all(
        (outcome in states) is condition for outcome, condition in tests.items()
    )


def _verify(product, source_verification, request):
    Issue = TargetAssessmentIssue
    if (
        type(product) is not ProjectSQLTargetAssessment
        or product.source_verification is not source_verification
        or product.request is not request
        or product.request_roots is not request._roots
        or not _check_request(request)
    ):
        return (Issue.ROOTS,)
    checked, report = product.report_verification, product.report
    if (
        type(checked) is not reports.ProjectSQLRequirementVerification
        or checked.report is not report
        or checked.source_verification is not source_verification
        or not checked.verified
        or not reports.verify_project_sql_requirement_report(
            report, source_verification
        ).verified
    ):
        return (Issue.ROOTS,)
    if any(
        type(v) is not tuple
        for v in (product.demands, product.aspects, product.lookups)
    ) or len(product.demands) != len(report.entries):
        return (Issue.STRUCTURE,)
    expressions = {e.ref: e for e in report.plan.expressions}
    seen_aspects = []
    for i, (demand, original) in enumerate(
        zip(product.demands, report.entries, strict=True)
    ):
        if (
            type(demand) is not ProjectSQLTargetDemand
            or type(demand.position) is not int
            or demand.position != i
            or demand.entry is not original
            or type(demand.aspects) is not tuple
        ):
            return (Issue.STRUCTURE,)
        if not mapping.check_propositions(
            original, tuple(a.proposition for a in demand.aspects), expressions
        ):
            return (Issue.MAPPING,)
        for ordinal, aspect in enumerate(demand.aspects):
            if (
                type(aspect) is not ProjectSQLTargetAspect
                or type(aspect.position) is not int
                or aspect.position != len(seen_aspects)
                or type(aspect.ordinal) is not int
                or aspect.ordinal != ordinal
                or aspect.entry is not original
            ):
                return (Issue.STRUCTURE,)
            seen_aspects.append(aspect)
        expected_posture = (
            AssessmentPosture.NOT_ASSESSED
            if request.target is None
            else AssessmentPosture.SATISFIED
            if demand.aspects
            and all(a.outcomes == (S.SATISFIED,) for a in demand.aspects)
            else AssessmentPosture.INCOMPLETE
        )
        if demand.posture is not expected_posture:
            return (Issue.OUTCOMES,)
    if not _same(product.aspects, tuple(seen_aspects)):
        return (Issue.STRUCTURE,)
    composition = request.composition
    original_occurrences = (
        composition.effective_occurrences
        if type(composition) is CapabilityProfileCompositionSuccess
        else ()
    )
    profile_facts = tuple(o.fact for o in original_occurrences)
    sharing = {}
    expected_queries = []
    for aspect in product.aspects:
        proposition, query = aspect.proposition, aspect.lookup
        if proposition.key is None or request.target is None:
            if query is not None:
                return (Issue.MAPPING,)
        else:
            if (
                type(query) is not ProjectSQLTargetLookup
                or query.request is not request
                or query.kind is not proposition.kind
                or type(query.key) is not CapabilityKey
                or query.key != proposition.key
            ):
                return (Issue.MAPPING,)
            share_key = (query.kind, query.key)
            if share_key in sharing:
                if query is not sharing[share_key]:
                    return (Issue.MAPPING,)
            else:
                sharing[share_key] = query
                if (
                    type(query.position) is not int
                    or query.position != len(expected_queries)
                    or query.key is not proposition.key
                ):
                    return (Issue.MAPPING,)
                expected_queries.append(query)
                if not _check_provider(query) or not _same(
                    query.profile_occurrences, original_occurrences
                ):
                    return (Issue.EVIDENCE,)
                if not _lookup_matches(
                    query.provider_result,
                    lookup_capability(
                        query.key,
                        query.inputs.facts,
                        domain_complete=query.inputs.domain_complete,
                        unknown_reason=query.inputs.unknown_reason,
                    ),
                ) or not _lookup_matches(
                    query.profile_result,
                    lookup_capability(query.key, profile_facts, domain_complete=False),
                ):
                    return (Issue.EVIDENCE,)
        if not _check_outcomes(aspect, request):
            return (Issue.OUTCOMES,)
    if not _same(product.lookups, tuple(expected_queries)):
        return (Issue.MAPPING,)
    if (
        type(product.by_demand) is not MappingProxyType
        or tuple(product.by_demand) != tuple(e.ref for e in report.entries)
        or any(product.by_demand.get(d.entry.ref) is not d for d in product.demands)
    ):
        return (Issue.INDEXES,)
    if (
        type(product.uses) is not MappingProxyType
        or not _same(tuple(product.uses), product.lookups)
        or any(
            not _same(
                product.uses[q], tuple(a for a in product.aspects if a.lookup is q)
            )
            for q in product.lookups
        )
    ):
        return (Issue.INDEXES,)
    summary = product.summary
    if (
        type(summary) is not ProjectSQLTargetSummary
        or any(
            type(count) is not int
            for count in (
                summary.demand_count,
                summary.aspect_count,
                summary.query_count,
            )
        )
        or (summary.demand_count, summary.aspect_count, summary.query_count)
        != (len(report.entries), len(product.aspects), len(product.lookups))
    ):
        return (Issue.SUMMARY,)
    complete = (
        bool(product.demands)
        and bool(product.aspects)
        and not request.issues
        and all(a.outcomes == (S.SATISFIED,) for a in product.aspects)
    )
    posture = (
        AssessmentPosture.NOT_ASSESSED
        if request.target is None
        else AssessmentPosture.SATISFIED
        if complete
        else AssessmentPosture.INCOMPLETE
    )
    if (
        summary.posture is not posture
        or summary.original_obligations is not report.summary
        or summary.input_issues is not request.issues
        or summary.catalog_residuals is not request.catalog_residuals
        or not _same(
            summary.pending_realizations,
            tuple(
                a for a in product.aspects if a.proposition.kind is mapping.K.RESIDUAL
            ),
        )
    ):
        return (Issue.SUMMARY,)
    if (
        type(summary.categories) is not MappingProxyType
        or tuple(summary.categories) != tuple(S)
        or any(
            not _same(
                summary.categories[o],
                tuple(a for a in product.aspects if o in a.outcomes),
            )
            for o in S
        )
    ):
        return (Issue.SUMMARY,)
    return ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLTargetAssessmentVerification:
    assessment: ProjectSQLTargetAssessment
    source_verification: ProjectSQLPlanVerification
    request: ProjectSQLTargetRequest
    issues: tuple[TargetAssessmentIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        try:
            issues = _verify(self.assessment, self.source_verification, self.request)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            issues = (TargetAssessmentIssue.STRUCTURE,)
        object.__setattr__(self, "issues", issues)

    @property
    def verified(self) -> bool:
        return not self.issues


def verify_project_sql_target_assessment(
    assessment, source_verification, request
) -> ProjectSQLTargetAssessmentVerification:
    return ProjectSQLTargetAssessmentVerification(
        assessment=assessment, source_verification=source_verification, request=request
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLTargetAssessmentInspection:
    verification: ProjectSQLTargetAssessmentVerification
    assessment: ProjectSQLTargetAssessment = field(init=False)

    def portable(self):
        from pietto._project.project_sql_plan_portable import (
            build_project_sql_plan_portable,
        )

        return build_project_sql_plan_portable(
            self.verification.source_verification, assessment=self.verification
        )

    def __post_init__(self) -> None:
        checked = self.verification
        try:
            valid = (
                type(checked) is ProjectSQLTargetAssessmentVerification
                and checked.verified
                and verify_project_sql_target_assessment(
                    checked.assessment, checked.source_verification, checked.request
                ).verified
            )
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                "Target inspection requires an exact current VERIFIED assessment."
            )
        object.__setattr__(self, "assessment", checked.assessment)

    @property
    def summary(self):
        return self.assessment.summary

    @property
    def target(self):
        return self.assessment.request.target

    @property
    def demands(self):
        return self.assessment.demands

    @property
    def lookups(self):
        return self.assessment.lookups

    def demand(self, ref: sql.ProjectSQLPlanRef) -> ProjectSQLTargetDemand:
        if (
            type(ref) is not sql.ProjectSQLPlanRef
            or ref not in self.assessment.by_demand
        ):
            raise ValueError("Target query requires an owned demand reference.")
        return self.assessment.by_demand[ref]

    def aspect(
        self, ref: sql.ProjectSQLPlanRef, ordinal: int
    ) -> ProjectSQLTargetAspect:
        demand = self.demand(ref)
        if type(ordinal) is not int or ordinal < 0 or ordinal >= len(demand.aspects):
            raise ValueError("Target query requires an owned aspect ordinal.")
        return demand.aspects[ordinal]

    def lookup(self, aspect: ProjectSQLTargetAspect) -> ProjectSQLTargetLookup | None:
        if (
            type(aspect) is not ProjectSQLTargetAspect
            or type(aspect.position) is not int
            or aspect.position < 0
            or aspect.position >= len(self.assessment.aspects)
            or self.assessment.aspects[aspect.position] is not aspect
        ):
            raise ValueError("Target query requires an owned aspect.")
        return aspect.lookup

    def uses(
        self, lookup: ProjectSQLTargetLookup
    ) -> tuple[ProjectSQLTargetAspect, ...]:
        if (
            type(lookup) is not ProjectSQLTargetLookup
            or lookup not in self.assessment.uses
        ):
            raise ValueError("Target query requires an owned lookup.")
        return self.assessment.uses[lookup]

    def for_outcome(self, outcome: AspectOutcome) -> tuple[ProjectSQLTargetAspect, ...]:
        if type(outcome) is not AspectOutcome:
            raise ValueError("Target query requires an exact outcome.")
        return self.summary.categories[outcome]


def inspect_project_sql_target_assessment(
    checked: ProjectSQLTargetAssessmentVerification,
) -> ProjectSQLTargetAssessmentInspection:
    return ProjectSQLTargetAssessmentInspection(verification=checked)
