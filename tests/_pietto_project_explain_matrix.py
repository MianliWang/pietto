from __future__ import annotations

from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCapabilityProfile,
    ProjectExplainCapabilitySupport,
    ProjectExplainCheckedEvidence,
    ProjectExplainCheckedStatus,
    ProjectExplainLookupSummary,
    ProjectExplainLookupVariant,
    ProjectExplainProfileKind,
    ProjectExplainProfileTargetKind,
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
