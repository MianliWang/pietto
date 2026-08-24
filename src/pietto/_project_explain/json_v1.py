"""Explicit deterministic JSON v1 serialization for Project Explain."""

from __future__ import annotations

import json
from typing import cast

from .compatibility_matrix_projection import (
    ProjectExplainAvailabilityOccurrence,
    ProjectExplainCapabilityProfile,
    ProjectExplainCheckedEvidence,
    ProjectExplainEvaluatedTarget,
    ProjectExplainLookupSummary,
    ProjectExplainMatrixBlocker,
    ProjectExplainMatrixCell,
    ProjectExplainMatrixRow,
    ProjectExplainPackageTargetEvaluation,
    ProjectExplainRequirementTargetMatrix,
)
from .composition import (
    ProjectExplainArtifactReference,
    ProjectExplainPayload,
    ProjectExplainRequirementExplanation,
    ProjectExplainRequirementTargetExplanation,
    _compose_project_explain_payload,
)
from .extension_catalog_evidence_projection import (
    ProjectExplainCatalogEntryFamily,
    ProjectExplainExtensionCatalogAvailabilityDeclaration,
    ProjectExplainExtensionCatalogCallableIdentity,
    ProjectExplainExtensionCatalogCastIdentity,
    ProjectExplainExtensionCatalogCompletenessClaim,
    ProjectExplainExtensionCatalogCompletenessEvidence,
    ProjectExplainExtensionCatalogContextEvidence,
    ProjectExplainExtensionCatalogEntryEvidence,
    ProjectExplainExtensionCatalogEvidenceProjection,
    ProjectExplainExtensionCatalogExactGroupEvidence,
    ProjectExplainExtensionCatalogOperatorIdentity,
    ProjectExplainExtensionCatalogReference,
    ProjectExplainExtensionCatalogSelection,
    ProjectExplainExtensionCatalogSelectionCandidate,
    ProjectExplainExtensionCatalogSelector,
    ProjectExplainExtensionCatalogSourceOccurrence,
    ProjectExplainExtensionCatalogSummary,
    ProjectExplainExtensionCatalogTarget,
    ProjectExplainExtensionCatalogTypeReference,
    ProjectExplainExtensionRequirementEvidence,
)
from .model import (
    ProjectExplainDiagnostic,
    ProjectExplainEnvelope,
    ProjectExplainLocation,
    ProjectExplainLogicalPath,
)
from .package_requirement_projection import (
    ProjectExplainCapabilityKey,
    ProjectExplainDirectDependency,
    ProjectExplainPackage,
    ProjectExplainPackageAsset,
    ProjectExplainPackageCoordinate,
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementCollection,
    ProjectExplainRequirementCollectionIdentity,
    ProjectExplainRequirementRequest,
)
from .portability_projection import (
    ProjectExplainDefiniteGap,
    ProjectExplainProjectPortability,
    ProjectExplainRequirementPortability,
)

__all__: tuple[str, ...] = ()


def project_explain_envelope_to_json_value(
    envelope: ProjectExplainEnvelope[ProjectExplainPayload],
) -> dict[str, object]:
    """Build the exact four-field Project Explain JSON v1 envelope."""

    if type(envelope) is not ProjectExplainEnvelope:
        raise TypeError("Project Explain JSON requires an exact envelope.")
    envelope.__post_init__()

    payload_value: dict[str, object] | None = None
    if envelope.ok:
        payload = envelope.payload
        if type(payload) is not ProjectExplainPayload:
            raise TypeError(
                "Successful Project Explain JSON requires an exact payload."
            )
        canonical = _compose_project_explain_payload(
            payload.package_requirements,
            payload.compatibility,
            payload.extension_catalog_evidence,
            payload.portability,
        )
        if payload != canonical:
            raise ValueError(
                "Project Explain JSON requires the canonical Slice 7 payload."
            )
        payload_value = _payload_to_json_value(payload)

    return {
        "format": envelope.format.value,
        "ok": envelope.ok,
        "diagnostics": [
            _diagnostic_to_json_value(diagnostic) for diagnostic in envelope.diagnostics
        ],
        "payload": payload_value,
    }


def serialize_project_explain_json_document(
    envelope: ProjectExplainEnvelope[ProjectExplainPayload],
) -> bytes:
    """Serialize one compact UTF-8 Project Explain JSON v1 document."""

    document = json.dumps(
        project_explain_envelope_to_json_value(envelope),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    )
    return f"{document}\n".encode("utf-8")


def _logical_path_to_json_value(value: ProjectExplainLogicalPath) -> dict[str, object]:
    if type(value) is not ProjectExplainLogicalPath:
        raise TypeError("Project Explain JSON requires an exact logical path.")
    value.__post_init__()
    return {
        "kind": value.kind.value,
        "value": value.value,
    }


def _location_to_json_value(
    value: ProjectExplainLocation | None,
) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is not ProjectExplainLocation:
        raise TypeError("Project Explain JSON requires an exact location.")
    value.__post_init__()
    return {
        "path": None if value.path is None else _logical_path_to_json_value(value.path),
        "line": value.line,
        "column": value.column,
        "end_line": value.end_line,
        "end_column": value.end_column,
    }


def _diagnostic_to_json_value(
    value: ProjectExplainDiagnostic,
) -> dict[str, object]:
    if type(value) is not ProjectExplainDiagnostic:
        raise TypeError("Project Explain JSON requires an exact diagnostic.")
    value.__post_init__()
    return {
        "code": value.code,
        "severity": value.severity.value,
        "message": value.message,
        "location": _location_to_json_value(value.location),
        "suggestion": value.suggestion,
    }


def _package_coordinate_to_json_value(
    value: ProjectExplainPackageCoordinate,
) -> dict[str, object]:
    if type(value) is not ProjectExplainPackageCoordinate:
        raise TypeError("Project Explain JSON requires an exact package coordinate.")
    value.__post_init__()
    return {
        "namespace": value.namespace,
        "name": value.name,
        "release": value.release,
    }


def _package_asset_to_json_value(
    value: ProjectExplainPackageAsset,
) -> dict[str, object]:
    if type(value) is not ProjectExplainPackageAsset:
        raise TypeError("Project Explain JSON requires an exact package asset.")
    value.__post_init__()
    return {
        "position": value.position,
        "kind": value.kind.value,
        "path": _logical_path_to_json_value(value.path),
    }


def _direct_dependency_to_json_value(
    value: ProjectExplainDirectDependency,
) -> dict[str, object]:
    if type(value) is not ProjectExplainDirectDependency:
        raise TypeError("Project Explain JSON requires an exact direct dependency.")
    value.__post_init__()
    return {
        "position": value.position,
        "target_package_position": value.target_package_position,
        "coordinate": _package_coordinate_to_json_value(value.coordinate),
        "content_digest_pin": value.content_digest_pin,
        "locator_kind": value.locator_kind.value,
        "project_path": _logical_path_to_json_value(value.project_path),
    }


def _package_to_json_value(value: ProjectExplainPackage) -> dict[str, object]:
    if type(value) is not ProjectExplainPackage:
        raise TypeError("Project Explain JSON requires an exact package.")
    value.__post_init__()
    return {
        "position": value.position,
        "role": value.role.value,
        "coordinate": _package_coordinate_to_json_value(value.coordinate),
        "project_path": _logical_path_to_json_value(value.project_path),
        "content_digest": value.content_digest,
        "assets": [_package_asset_to_json_value(item) for item in value.assets],
        "dependencies": [
            _direct_dependency_to_json_value(item) for item in value.dependencies
        ],
    }


def _requirement_collection_identity_to_json_value(
    value: ProjectExplainRequirementCollectionIdentity,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementCollectionIdentity:
        raise TypeError(
            "Project Explain JSON requires an exact requirement collection identity."
        )
    value.__post_init__()
    return {
        "namespace": value.namespace,
        "name": value.name,
    }


def _capability_key_to_json_value(
    value: ProjectExplainCapabilityKey,
) -> dict[str, object]:
    if type(value) is not ProjectExplainCapabilityKey:
        raise TypeError("Project Explain JSON requires an exact capability key.")
    value.__post_init__()
    return {
        "domain": value.domain.value,
        "subject": value.subject,
        "operation": value.operation,
        "operands": list(value.operands),
        "context": value.context,
        "dialect": value.dialect,
        "extension": value.extension,
    }


def _requirement_collection_to_json_value(
    value: ProjectExplainRequirementCollection,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementCollection:
        raise TypeError(
            "Project Explain JSON requires an exact requirement collection."
        )
    value.__post_init__()
    return {
        "declared_by": value.declared_by,
        "requested_by": value.requested_by,
        "package_role": value.package_role.value,
        "identity": _requirement_collection_identity_to_json_value(value.identity),
        "requirement_positions": list(value.requirement_positions),
    }


def _requirement_request_to_json_value(
    value: ProjectExplainRequirementRequest,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementRequest:
        raise TypeError("Project Explain JSON requires an exact requirement request.")
    value.__post_init__()
    return {
        "position": value.position,
        "stage": value.stage.value,
        "declared_by": value.declared_by,
        "requested_by": value.requested_by,
        "package_role": value.package_role.value,
        "collection": _requirement_collection_identity_to_json_value(value.collection),
        "occurrence_position": value.occurrence_position,
        "key": _capability_key_to_json_value(value.key),
    }


def _package_requirement_projection_to_json_value(
    value: ProjectExplainPackageRequirementProjection,
) -> dict[str, object]:
    if type(value) is not ProjectExplainPackageRequirementProjection:
        raise TypeError(
            "Project Explain JSON requires an exact package requirement projection."
        )
    value.__post_init__()
    return {
        "root_package_position": value.root_package_position,
        "packages": [_package_to_json_value(item) for item in value.packages],
        "requirement_collections": [
            _requirement_collection_to_json_value(item)
            for item in value.requirement_collections
        ],
        "requirements": [
            _requirement_request_to_json_value(item) for item in value.requirements
        ],
    }


def _capability_profile_to_json_value(
    value: ProjectExplainCapabilityProfile,
) -> dict[str, object]:
    if type(value) is not ProjectExplainCapabilityProfile:
        raise TypeError("Project Explain JSON requires an exact capability profile.")
    value.__post_init__()
    return {
        "namespace": value.namespace,
        "name": value.name,
        "profile_release": value.profile_release,
        "kind": value.kind.value,
        "target_kind": value.target_kind.value,
        "database_family": value.database_family,
        "target_release": value.target_release,
        "extension_identity": value.extension_identity,
        "extension_release": value.extension_release,
    }


def _evaluated_target_to_json_value(
    value: ProjectExplainEvaluatedTarget,
) -> dict[str, object]:
    if type(value) is not ProjectExplainEvaluatedTarget:
        raise TypeError("Project Explain JSON requires an exact evaluated target.")
    value.__post_init__()
    return {
        "position": value.position,
        "database_family": value.database_family,
        "database_release": value.database_release,
        "base_profile": _capability_profile_to_json_value(value.base_profile),
        "supplied_overlays": [
            _capability_profile_to_json_value(item) for item in value.supplied_overlays
        ],
        "dependency_order": [
            _capability_profile_to_json_value(item) for item in value.dependency_order
        ],
    }


def _availability_occurrence_to_json_value(
    value: ProjectExplainAvailabilityOccurrence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainAvailabilityOccurrence:
        raise TypeError(
            "Project Explain JSON requires an exact availability occurrence."
        )
    value.__post_init__()
    return {
        "owner_kind": value.owner_kind.value,
        "owner_position": value.owner_position,
        "project_path": (
            None
            if value.project_path is None
            else _logical_path_to_json_value(value.project_path)
        ),
        "profile": _capability_profile_to_json_value(value.profile),
    }


def _matrix_blocker_to_json_value(
    value: ProjectExplainMatrixBlocker,
) -> dict[str, object]:
    if type(value) is not ProjectExplainMatrixBlocker:
        raise TypeError("Project Explain JSON requires an exact matrix blocker.")
    value.__post_init__()
    return {
        "kind": value.kind.value,
        "selected_profile": _capability_profile_to_json_value(value.selected_profile),
        "bucket_profile": (
            None
            if value.bucket_profile is None
            else _capability_profile_to_json_value(value.bucket_profile)
        ),
        "bucket_occurrences": [
            _availability_occurrence_to_json_value(item)
            for item in value.bucket_occurrences
        ],
    }


def _package_target_evaluation_to_json_value(
    value: ProjectExplainPackageTargetEvaluation,
) -> dict[str, object]:
    if type(value) is not ProjectExplainPackageTargetEvaluation:
        raise TypeError(
            "Project Explain JSON requires an exact package-target evaluation."
        )
    value.__post_init__()
    return {
        "package_position": value.package_position,
        "target_position": value.target_position,
        "state": value.state.value,
        "evidence_posture": value.evidence_posture.value,
        "availability": [
            _availability_occurrence_to_json_value(item) for item in value.availability
        ],
        "blockers": [_matrix_blocker_to_json_value(item) for item in value.blockers],
    }


def _lookup_summary_to_json_value(
    value: ProjectExplainLookupSummary,
) -> dict[str, object]:
    if type(value) is not ProjectExplainLookupSummary:
        raise TypeError("Project Explain JSON requires an exact lookup summary.")
    value.__post_init__()
    return {
        "variant": value.variant.value,
        "reason": value.reason,
        "supports": [item.value for item in value.supports],
    }


def _checked_evidence_to_json_value(
    value: ProjectExplainCheckedEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainCheckedEvidence:
        raise TypeError("Project Explain JSON requires exact checked evidence.")
    value.__post_init__()
    return {
        "target_lookup": _lookup_summary_to_json_value(value.target_lookup),
        "provider_domain_complete": value.provider_domain_complete,
        "provider_unknown_reason": value.provider_unknown_reason,
        "provider_lookup": _lookup_summary_to_json_value(value.provider_lookup),
    }


def _matrix_cell_to_json_value(
    value: ProjectExplainMatrixCell,
) -> dict[str, object]:
    if type(value) is not ProjectExplainMatrixCell:
        raise TypeError("Project Explain JSON requires an exact matrix cell.")
    value.__post_init__()
    return {
        "target_position": value.target_position,
        "state": value.state.value,
        "checked_status": (
            None if value.checked_status is None else value.checked_status.value
        ),
        "evidence_posture": value.evidence_posture.value,
        "checked_evidence": (
            None
            if value.checked_evidence is None
            else _checked_evidence_to_json_value(value.checked_evidence)
        ),
    }


def _matrix_row_to_json_value(value: ProjectExplainMatrixRow) -> dict[str, object]:
    if type(value) is not ProjectExplainMatrixRow:
        raise TypeError("Project Explain JSON requires an exact matrix row.")
    value.__post_init__()
    return {
        "requirement_position": value.requirement_position,
        "cells": [_matrix_cell_to_json_value(item) for item in value.cells],
    }


def _requirement_target_matrix_to_json_value(
    value: ProjectExplainRequirementTargetMatrix,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementTargetMatrix:
        raise TypeError("Project Explain JSON requires an exact requirement matrix.")
    value.__post_init__()
    return {
        "targets": [_evaluated_target_to_json_value(item) for item in value.targets],
        "package_target_evaluations": [
            _package_target_evaluation_to_json_value(item)
            for item in value.package_target_evaluations
        ],
        "rows": [_matrix_row_to_json_value(item) for item in value.rows],
    }


def _catalog_reference_to_json_value(
    value: ProjectExplainExtensionCatalogReference,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogReference:
        raise TypeError("Project Explain JSON requires an exact catalog reference.")
    value.__post_init__()
    return {
        "namespace": value.namespace,
        "name": value.name,
        "release": value.release,
    }


def _catalog_target_to_json_value(
    value: ProjectExplainExtensionCatalogTarget,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogTarget:
        raise TypeError("Project Explain JSON requires an exact catalog target.")
    value.__post_init__()
    return {
        "database_family": value.database_family,
        "database_release": value.database_release,
        "extension_identity": value.extension_identity,
        "extension_release": value.extension_release,
    }


def _catalog_source_occurrence_to_json_value(
    value: ProjectExplainExtensionCatalogSourceOccurrence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogSourceOccurrence:
        raise TypeError("Project Explain JSON requires an exact catalog source.")
    value.__post_init__()
    return {
        "position": value.position,
        "source_authority": value.source_authority,
        "source_revision": value.source_revision,
        "source_locator": _logical_path_to_json_value(value.source_locator),
        "curation": value.curation,
    }


def _catalog_summary_to_json_value(
    value: ProjectExplainExtensionCatalogSummary,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogSummary:
        raise TypeError("Project Explain JSON requires an exact catalog summary.")
    value.__post_init__()
    return {
        "position": value.position,
        "reference": _catalog_reference_to_json_value(value.reference),
        "target": _catalog_target_to_json_value(value.target),
        "content_sha256": value.content_sha256,
        "canonical_byte_length": value.canonical_byte_length,
        "source_occurrences": [
            _catalog_source_occurrence_to_json_value(item)
            for item in value.source_occurrences
        ],
    }


def _catalog_type_reference_to_json_value(
    value: ProjectExplainExtensionCatalogTypeReference,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogTypeReference:
        raise TypeError(
            "Project Explain JSON requires an exact catalog type reference."
        )
    value.__post_init__()
    return {
        "kind": value.kind.value,
        "logical_name": value.logical_name,
        "logical_kind": (
            None if value.logical_kind is None else value.logical_kind.value
        ),
        "physical_name": value.physical_name,
        "extension_identity": value.extension_identity,
    }


def _catalog_callable_identity_to_json_value(
    value: ProjectExplainExtensionCatalogCallableIdentity,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogCallableIdentity:
        raise TypeError("Project Explain JSON requires an exact callable identity.")
    value.__post_init__()
    return {
        "sql_name": value.sql_name,
        "input_types": [
            _catalog_type_reference_to_json_value(item) for item in value.input_types
        ],
    }


def _catalog_operator_identity_to_json_value(
    value: ProjectExplainExtensionCatalogOperatorIdentity,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogOperatorIdentity:
        raise TypeError("Project Explain JSON requires an exact operator identity.")
    value.__post_init__()
    return {
        "operator_name": value.operator_name,
        "arity": value.arity.value,
        "operand_types": [
            _catalog_type_reference_to_json_value(item) for item in value.operand_types
        ],
    }


def _catalog_cast_identity_to_json_value(
    value: ProjectExplainExtensionCatalogCastIdentity,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogCastIdentity:
        raise TypeError("Project Explain JSON requires an exact cast identity.")
    value.__post_init__()
    return {
        "source_type": _catalog_type_reference_to_json_value(value.source_type),
        "target_type": _catalog_type_reference_to_json_value(value.target_type),
    }


def _catalog_selector_to_json_value(
    value: ProjectExplainExtensionCatalogSelector,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogSelector:
        raise TypeError("Project Explain JSON requires an exact catalog selector.")
    value.__post_init__()
    if value.family is ProjectExplainCatalogEntryFamily.NATIVE_TYPE:
        identity = _catalog_type_reference_to_json_value(
            cast(ProjectExplainExtensionCatalogTypeReference, value.identity)
        )
    elif value.family in {
        ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION,
        ProjectExplainCatalogEntryFamily.AGGREGATE,
    }:
        identity = _catalog_callable_identity_to_json_value(
            cast(ProjectExplainExtensionCatalogCallableIdentity, value.identity)
        )
    elif value.family is ProjectExplainCatalogEntryFamily.OPERATOR:
        identity = _catalog_operator_identity_to_json_value(
            cast(ProjectExplainExtensionCatalogOperatorIdentity, value.identity)
        )
    else:
        identity = _catalog_cast_identity_to_json_value(
            cast(ProjectExplainExtensionCatalogCastIdentity, value.identity)
        )
    return {
        "family": value.family.value,
        "identity": identity,
    }


def _catalog_availability_to_json_value(
    value: ProjectExplainExtensionCatalogAvailabilityDeclaration,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogAvailabilityDeclaration:
        raise TypeError("Project Explain JSON requires exact catalog availability.")
    value.__post_init__()
    return {
        "position": value.position,
        "owner_kind": value.owner_kind.value,
        "project_path": (
            None
            if value.project_path is None
            else _logical_path_to_json_value(value.project_path)
        ),
        "catalog_position": value.catalog_position,
        "reference": _catalog_reference_to_json_value(value.reference),
        "target": _catalog_target_to_json_value(value.target),
        "content_sha256": value.content_sha256,
    }


def _catalog_selection_candidate_to_json_value(
    value: ProjectExplainExtensionCatalogSelectionCandidate,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogSelectionCandidate:
        raise TypeError("Project Explain JSON requires an exact catalog candidate.")
    value.__post_init__()
    return {
        "catalog_position": value.catalog_position,
        "reference": _catalog_reference_to_json_value(value.reference),
        "target": _catalog_target_to_json_value(value.target),
        "content_sha256": value.content_sha256,
        "declaration_positions": list(value.declaration_positions),
    }


def _catalog_selection_to_json_value(
    value: ProjectExplainExtensionCatalogSelection,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogSelection:
        raise TypeError("Project Explain JSON requires an exact catalog selection.")
    value.__post_init__()
    return {
        "requested_target": _catalog_target_to_json_value(value.requested_target),
        "active_project_path": (
            None
            if value.active_project_path is None
            else _logical_path_to_json_value(value.active_project_path)
        ),
        "outcome": value.outcome.value,
        "evidence_posture": value.evidence_posture.value,
        "availability": [
            _catalog_availability_to_json_value(item) for item in value.availability
        ],
        "applicable_declaration_positions": list(
            value.applicable_declaration_positions
        ),
        "excluded_project_declaration_positions": list(
            value.excluded_project_declaration_positions
        ),
        "target_declaration_positions": list(value.target_declaration_positions),
        "candidates": [
            _catalog_selection_candidate_to_json_value(item)
            for item in value.candidates
        ],
        "selected_catalog_position": value.selected_catalog_position,
    }


def _catalog_entry_evidence_to_json_value(
    value: ProjectExplainExtensionCatalogEntryEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogEntryEvidence:
        raise TypeError("Project Explain JSON requires exact catalog entry evidence.")
    value.__post_init__()
    return {
        "entry_position": value.entry_position,
        "entry_family": value.entry_family.value,
        "matchability": value.matchability.value,
        "exposure": value.exposure.value,
        "unmodeled_reasons": [item.value for item in value.unmodeled_reasons],
        "source_positions": list(value.source_positions),
    }


def _catalog_exact_group_to_json_value(
    value: ProjectExplainExtensionCatalogExactGroupEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogExactGroupEvidence:
        raise TypeError("Project Explain JSON requires exact catalog group evidence.")
    value.__post_init__()
    return {
        "position": value.position,
        "state": value.state.value,
        "entries": [
            _catalog_entry_evidence_to_json_value(item) for item in value.entries
        ],
    }


def _catalog_completeness_claim_to_json_value(
    value: ProjectExplainExtensionCatalogCompletenessClaim,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogCompletenessClaim:
        raise TypeError("Project Explain JSON requires an exact completeness claim.")
    value.__post_init__()
    return {
        "position": value.position,
        "kind": value.kind.value,
        "source_positions": list(value.source_positions),
    }


def _catalog_completeness_to_json_value(
    value: ProjectExplainExtensionCatalogCompletenessEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogCompletenessEvidence:
        raise TypeError("Project Explain JSON requires exact completeness evidence.")
    value.__post_init__()
    return {
        "position": value.position,
        "state": value.state.value,
        "claims": [
            _catalog_completeness_claim_to_json_value(item) for item in value.claims
        ],
    }


def _extension_requirement_evidence_to_json_value(
    value: ProjectExplainExtensionRequirementEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionRequirementEvidence:
        raise TypeError("Project Explain JSON requires exact extension evidence.")
    value.__post_init__()
    return {
        "requirement_position": value.requirement_position,
        "selector": _catalog_selector_to_json_value(value.selector),
        "bridged_database_family": value.bridged_database_family,
        "selection": _catalog_selection_to_json_value(value.selection),
        "selected_catalog_position": value.selected_catalog_position,
        "exact_group": (
            None
            if value.exact_group is None
            else _catalog_exact_group_to_json_value(value.exact_group)
        ),
        "unmodeled_blockers": [
            _catalog_entry_evidence_to_json_value(item)
            for item in value.unmodeled_blockers
        ],
        "completeness": (
            None
            if value.completeness is None
            else _catalog_completeness_to_json_value(value.completeness)
        ),
    }


def _catalog_context_to_json_value(
    value: ProjectExplainExtensionCatalogContextEvidence,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogContextEvidence:
        raise TypeError("Project Explain JSON requires exact catalog context evidence.")
    value.__post_init__()
    return {
        "package_position": value.package_position,
        "target_position": value.target_position,
        "collection": _requirement_collection_identity_to_json_value(value.collection),
        "catalogs": [_catalog_summary_to_json_value(item) for item in value.catalogs],
        "requirements": [
            _extension_requirement_evidence_to_json_value(item)
            for item in value.requirements
        ],
    }


def _catalog_evidence_projection_to_json_value(
    value: ProjectExplainExtensionCatalogEvidenceProjection,
) -> dict[str, object]:
    if type(value) is not ProjectExplainExtensionCatalogEvidenceProjection:
        raise TypeError("Project Explain JSON requires exact catalog evidence.")
    value.__post_init__()
    return {
        "contexts": [_catalog_context_to_json_value(item) for item in value.contexts],
    }


def _definite_gap_to_json_value(
    value: ProjectExplainDefiniteGap,
) -> dict[str, object]:
    if type(value) is not ProjectExplainDefiniteGap:
        raise TypeError("Project Explain JSON requires an exact definite gap.")
    value.__post_init__()
    return {
        "target_position": value.target_position,
        "status": value.status.value,
    }


def _requirement_portability_to_json_value(
    value: ProjectExplainRequirementPortability,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementPortability:
        raise TypeError("Project Explain JSON requires exact requirement portability.")
    value.__post_init__()
    return {
        "requirement_position": value.requirement_position,
        "classification": value.classification.value,
        "reason": None if value.reason is None else value.reason.value,
        "definite_gaps": [
            _definite_gap_to_json_value(item) for item in value.definite_gaps
        ],
    }


def _project_portability_to_json_value(
    value: ProjectExplainProjectPortability,
) -> dict[str, object]:
    if type(value) is not ProjectExplainProjectPortability:
        raise TypeError("Project Explain JSON requires exact project portability.")
    value.__post_init__()
    return {
        "classification": value.classification.value,
        "reason": None if value.reason is None else value.reason.value,
        "requirements_evaluated": value.requirements_evaluated,
        "requirements": [
            _requirement_portability_to_json_value(item) for item in value.requirements
        ],
    }


def _artifact_reference_to_json_value(
    value: ProjectExplainArtifactReference,
) -> dict[str, object]:
    if type(value) is not ProjectExplainArtifactReference:
        raise TypeError("Project Explain JSON requires an exact artifact reference.")
    value.__post_init__()
    return {
        "kind": value.kind.value,
        "positions": list(value.positions),
    }


def _requirement_target_explanation_to_json_value(
    value: ProjectExplainRequirementTargetExplanation,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementTargetExplanation:
        raise TypeError("Project Explain JSON requires an exact target explanation.")
    value.__post_init__()
    return {
        "target": _artifact_reference_to_json_value(value.target),
        "evaluation": _artifact_reference_to_json_value(value.evaluation),
        "matrix_cell": _artifact_reference_to_json_value(value.matrix_cell),
        "extension_evidence": (
            None
            if value.extension_evidence is None
            else _artifact_reference_to_json_value(value.extension_evidence)
        ),
        "source_evidence": [
            _artifact_reference_to_json_value(item) for item in value.source_evidence
        ],
    }


def _requirement_explanation_to_json_value(
    value: ProjectExplainRequirementExplanation,
) -> dict[str, object]:
    if type(value) is not ProjectExplainRequirementExplanation:
        raise TypeError("Project Explain JSON requires an exact explanation.")
    value.__post_init__()
    return {
        "request": _artifact_reference_to_json_value(value.request),
        "declared_by": _artifact_reference_to_json_value(value.declared_by),
        "requested_by": _artifact_reference_to_json_value(value.requested_by),
        "targets": [
            _requirement_target_explanation_to_json_value(item)
            for item in value.targets
        ],
        "portability": _artifact_reference_to_json_value(value.portability),
    }


def _payload_to_json_value(value: ProjectExplainPayload) -> dict[str, object]:
    if type(value) is not ProjectExplainPayload:
        raise TypeError("Project Explain JSON requires an exact payload.")
    value.__post_init__()
    return {
        "package_requirements": _package_requirement_projection_to_json_value(
            value.package_requirements
        ),
        "compatibility": _requirement_target_matrix_to_json_value(value.compatibility),
        "extension_catalog_evidence": _catalog_evidence_projection_to_json_value(
            value.extension_catalog_evidence
        ),
        "portability": _project_portability_to_json_value(value.portability),
        "requirement_explanations": [
            _requirement_explanation_to_json_value(item)
            for item in value.requirement_explanations
        ],
    }
