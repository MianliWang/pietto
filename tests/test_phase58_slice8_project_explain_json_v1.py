from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass, replace
import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.compatibility_matrix_projection as compatibility
import pietto._project_explain.composition as composition
import pietto._project_explain.extension_catalog_evidence_projection as catalog
import pietto._project_explain.json_v1 as json_v1
import pietto._project_explain.model as model
import pietto._project_explain.package_requirement_projection as package
import pietto._project_explain.portability_projection as portability
import pietto.semantic as semantic_package
import test_phase58_slice4_project_explain_requirement_target_matrix as slice4
import test_phase58_slice6_project_explain_portability_derivation as slice6
import test_phase58_slice7_project_explain_composition_references as slice7
from pietto.errors import Severity
from pietto.semantic.capability_facts import CapabilityDomain
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase58-slice8-project-explain-json-v1.md"
SOURCE = REPO_ROOT / "src/pietto/_project_explain/json_v1.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
SUCCESS_GOLDEN = REPO_ROOT / "tests/fixtures/golden/project_explain_v1_success.json"
FAILURE_GOLDEN = REPO_ROOT / "tests/fixtures/golden/project_explain_v1_failure.json"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


goldens = cast(
    Any,
    _load_module("pietto_slice8_check_goldens", REPO_ROOT / "scripts/check_goldens.py"),
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _EnvelopeSubclass(
    model.ProjectExplainEnvelope[composition.ProjectExplainPayload]
):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class _PayloadSubclass(composition.ProjectExplainPayload):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class _CallableIdentitySubclass(catalog.ProjectExplainExtensionCatalogCallableIdentity):
    pass


_CARRIER_FIELDS: dict[type[Any], tuple[str, ...]] = {
    model.ProjectExplainLogicalPath: ("kind", "value"),
    model.ProjectExplainLocation: (
        "path",
        "line",
        "column",
        "end_line",
        "end_column",
    ),
    model.ProjectExplainDiagnostic: (
        "code",
        "severity",
        "message",
        "location",
        "suggestion",
    ),
    model.ProjectExplainEnvelope: ("format", "ok", "diagnostics", "payload"),
    package.ProjectExplainPackageCoordinate: ("namespace", "name", "release"),
    package.ProjectExplainPackageAsset: ("position", "kind", "path"),
    package.ProjectExplainDirectDependency: (
        "position",
        "target_package_position",
        "coordinate",
        "content_digest_pin",
        "locator_kind",
        "project_path",
    ),
    package.ProjectExplainPackage: (
        "position",
        "role",
        "coordinate",
        "project_path",
        "content_digest",
        "assets",
        "dependencies",
    ),
    package.ProjectExplainRequirementCollectionIdentity: ("namespace", "name"),
    package.ProjectExplainCapabilityKey: (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    ),
    package.ProjectExplainRequirementCollection: (
        "declared_by",
        "requested_by",
        "package_role",
        "identity",
        "requirement_positions",
    ),
    package.ProjectExplainRequirementRequest: (
        "position",
        "stage",
        "declared_by",
        "requested_by",
        "package_role",
        "collection",
        "occurrence_position",
        "key",
    ),
    package.ProjectExplainPackageRequirementProjection: (
        "root_package_position",
        "packages",
        "requirement_collections",
        "requirements",
    ),
    compatibility.ProjectExplainCapabilityProfile: (
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
    compatibility.ProjectExplainEvaluatedTarget: (
        "position",
        "database_family",
        "database_release",
        "base_profile",
        "supplied_overlays",
        "dependency_order",
    ),
    compatibility.ProjectExplainAvailabilityOccurrence: (
        "owner_kind",
        "owner_position",
        "project_path",
        "profile",
    ),
    compatibility.ProjectExplainMatrixBlocker: (
        "kind",
        "selected_profile",
        "bucket_profile",
        "bucket_occurrences",
    ),
    compatibility.ProjectExplainPackageTargetEvaluation: (
        "package_position",
        "target_position",
        "state",
        "evidence_posture",
        "availability",
        "blockers",
    ),
    compatibility.ProjectExplainLookupSummary: ("variant", "reason", "supports"),
    compatibility.ProjectExplainCheckedEvidence: (
        "target_lookup",
        "provider_domain_complete",
        "provider_unknown_reason",
        "provider_lookup",
    ),
    compatibility.ProjectExplainMatrixCell: (
        "target_position",
        "state",
        "checked_status",
        "evidence_posture",
        "checked_evidence",
    ),
    compatibility.ProjectExplainMatrixRow: ("requirement_position", "cells"),
    compatibility.ProjectExplainRequirementTargetMatrix: (
        "targets",
        "package_target_evaluations",
        "rows",
    ),
    catalog.ProjectExplainExtensionCatalogReference: (
        "namespace",
        "name",
        "release",
    ),
    catalog.ProjectExplainExtensionCatalogTarget: (
        "database_family",
        "database_release",
        "extension_identity",
        "extension_release",
    ),
    catalog.ProjectExplainExtensionCatalogSourceOccurrence: (
        "position",
        "source_authority",
        "source_revision",
        "source_locator",
        "curation",
    ),
    catalog.ProjectExplainExtensionCatalogSummary: (
        "position",
        "reference",
        "target",
        "content_sha256",
        "canonical_byte_length",
        "source_occurrences",
    ),
    catalog.ProjectExplainExtensionCatalogTypeReference: (
        "kind",
        "logical_name",
        "logical_kind",
        "physical_name",
        "extension_identity",
    ),
    catalog.ProjectExplainExtensionCatalogCallableIdentity: (
        "sql_name",
        "input_types",
    ),
    catalog.ProjectExplainExtensionCatalogOperatorIdentity: (
        "operator_name",
        "arity",
        "operand_types",
    ),
    catalog.ProjectExplainExtensionCatalogCastIdentity: (
        "source_type",
        "target_type",
    ),
    catalog.ProjectExplainExtensionCatalogSelector: ("family", "identity"),
    catalog.ProjectExplainExtensionCatalogAvailabilityDeclaration: (
        "position",
        "owner_kind",
        "project_path",
        "catalog_position",
        "reference",
        "target",
        "content_sha256",
    ),
    catalog.ProjectExplainExtensionCatalogSelectionCandidate: (
        "catalog_position",
        "reference",
        "target",
        "content_sha256",
        "declaration_positions",
    ),
    catalog.ProjectExplainExtensionCatalogSelection: (
        "requested_target",
        "active_project_path",
        "outcome",
        "evidence_posture",
        "availability",
        "applicable_declaration_positions",
        "excluded_project_declaration_positions",
        "target_declaration_positions",
        "candidates",
        "selected_catalog_position",
    ),
    catalog.ProjectExplainExtensionCatalogEntryEvidence: (
        "entry_position",
        "entry_family",
        "matchability",
        "exposure",
        "unmodeled_reasons",
        "source_positions",
    ),
    catalog.ProjectExplainExtensionCatalogExactGroupEvidence: (
        "position",
        "state",
        "entries",
    ),
    catalog.ProjectExplainExtensionCatalogCompletenessClaim: (
        "position",
        "kind",
        "source_positions",
    ),
    catalog.ProjectExplainExtensionCatalogCompletenessEvidence: (
        "position",
        "state",
        "claims",
    ),
    catalog.ProjectExplainExtensionRequirementEvidence: (
        "requirement_position",
        "selector",
        "bridged_database_family",
        "selection",
        "selected_catalog_position",
        "exact_group",
        "unmodeled_blockers",
        "completeness",
    ),
    catalog.ProjectExplainExtensionCatalogContextEvidence: (
        "package_position",
        "target_position",
        "collection",
        "catalogs",
        "requirements",
    ),
    catalog.ProjectExplainExtensionCatalogEvidenceProjection: ("contexts",),
    portability.ProjectExplainDefiniteGap: ("target_position", "status"),
    portability.ProjectExplainRequirementPortability: (
        "requirement_position",
        "classification",
        "reason",
        "definite_gaps",
    ),
    portability.ProjectExplainProjectPortability: (
        "classification",
        "reason",
        "requirements_evaluated",
        "requirements",
    ),
    composition.ProjectExplainArtifactReference: ("kind", "positions"),
    composition.ProjectExplainRequirementTargetExplanation: (
        "target",
        "evaluation",
        "matrix_cell",
        "extension_evidence",
        "source_evidence",
    ),
    composition.ProjectExplainRequirementExplanation: (
        "request",
        "declared_by",
        "requested_by",
        "targets",
        "portability",
    ),
    composition.ProjectExplainPayload: (
        "package_requirements",
        "compatibility",
        "extension_catalog_evidence",
        "portability",
        "requirement_explanations",
    ),
}

_CARRIER_SERIALIZERS: dict[
    type[Any],
    Callable[[Any], dict[str, object] | None],
] = {
    model.ProjectExplainLogicalPath: json_v1._logical_path_to_json_value,
    model.ProjectExplainLocation: json_v1._location_to_json_value,
    model.ProjectExplainDiagnostic: json_v1._diagnostic_to_json_value,
    model.ProjectExplainEnvelope: json_v1.project_explain_envelope_to_json_value,
    package.ProjectExplainPackageCoordinate: json_v1._package_coordinate_to_json_value,
    package.ProjectExplainPackageAsset: json_v1._package_asset_to_json_value,
    package.ProjectExplainDirectDependency: json_v1._direct_dependency_to_json_value,
    package.ProjectExplainPackage: json_v1._package_to_json_value,
    package.ProjectExplainRequirementCollectionIdentity: (
        json_v1._requirement_collection_identity_to_json_value
    ),
    package.ProjectExplainCapabilityKey: json_v1._capability_key_to_json_value,
    package.ProjectExplainRequirementCollection: (
        json_v1._requirement_collection_to_json_value
    ),
    package.ProjectExplainRequirementRequest: json_v1._requirement_request_to_json_value,
    package.ProjectExplainPackageRequirementProjection: (
        json_v1._package_requirement_projection_to_json_value
    ),
    compatibility.ProjectExplainCapabilityProfile: (
        json_v1._capability_profile_to_json_value
    ),
    compatibility.ProjectExplainEvaluatedTarget: (
        json_v1._evaluated_target_to_json_value
    ),
    compatibility.ProjectExplainAvailabilityOccurrence: (
        json_v1._availability_occurrence_to_json_value
    ),
    compatibility.ProjectExplainMatrixBlocker: json_v1._matrix_blocker_to_json_value,
    compatibility.ProjectExplainPackageTargetEvaluation: (
        json_v1._package_target_evaluation_to_json_value
    ),
    compatibility.ProjectExplainLookupSummary: json_v1._lookup_summary_to_json_value,
    compatibility.ProjectExplainCheckedEvidence: (
        json_v1._checked_evidence_to_json_value
    ),
    compatibility.ProjectExplainMatrixCell: json_v1._matrix_cell_to_json_value,
    compatibility.ProjectExplainMatrixRow: json_v1._matrix_row_to_json_value,
    compatibility.ProjectExplainRequirementTargetMatrix: (
        json_v1._requirement_target_matrix_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogReference: (
        json_v1._catalog_reference_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogTarget: json_v1._catalog_target_to_json_value,
    catalog.ProjectExplainExtensionCatalogSourceOccurrence: (
        json_v1._catalog_source_occurrence_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogSummary: json_v1._catalog_summary_to_json_value,
    catalog.ProjectExplainExtensionCatalogTypeReference: (
        json_v1._catalog_type_reference_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogCallableIdentity: (
        json_v1._catalog_callable_identity_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogOperatorIdentity: (
        json_v1._catalog_operator_identity_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogCastIdentity: (
        json_v1._catalog_cast_identity_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogSelector: (
        json_v1._catalog_selector_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogAvailabilityDeclaration: (
        json_v1._catalog_availability_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogSelectionCandidate: (
        json_v1._catalog_selection_candidate_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogSelection: (
        json_v1._catalog_selection_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogEntryEvidence: (
        json_v1._catalog_entry_evidence_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogExactGroupEvidence: (
        json_v1._catalog_exact_group_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogCompletenessClaim: (
        json_v1._catalog_completeness_claim_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogCompletenessEvidence: (
        json_v1._catalog_completeness_to_json_value
    ),
    catalog.ProjectExplainExtensionRequirementEvidence: (
        json_v1._extension_requirement_evidence_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogContextEvidence: (
        json_v1._catalog_context_to_json_value
    ),
    catalog.ProjectExplainExtensionCatalogEvidenceProjection: (
        json_v1._catalog_evidence_projection_to_json_value
    ),
    portability.ProjectExplainDefiniteGap: json_v1._definite_gap_to_json_value,
    portability.ProjectExplainRequirementPortability: (
        json_v1._requirement_portability_to_json_value
    ),
    portability.ProjectExplainProjectPortability: (
        json_v1._project_portability_to_json_value
    ),
    composition.ProjectExplainArtifactReference: (
        json_v1._artifact_reference_to_json_value
    ),
    composition.ProjectExplainRequirementTargetExplanation: (
        json_v1._requirement_target_explanation_to_json_value
    ),
    composition.ProjectExplainRequirementExplanation: (
        json_v1._requirement_explanation_to_json_value
    ),
    composition.ProjectExplainPayload: json_v1._payload_to_json_value,
}

_CARRIER_MODULES = (
    model,
    package,
    compatibility,
    catalog,
    portability,
    composition,
)


def _success_envelope(
    root: Path,
) -> model.ProjectExplainEnvelope[composition.ProjectExplainPayload]:
    payload = composition._compose_project_explain_payload(
        *slice7._source_rich_sections(root)
    )
    return model.ProjectExplainEnvelope(
        format=model.ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=True,
        diagnostics=(
            model.ProjectExplainDiagnostic(
                code="PIE-T5808-W",
                severity=Severity.WARNING,
                message="Unicode witness: 雪 / é / e\u0301",
                location=model.ProjectExplainLocation(
                    path=model.ProjectExplainLogicalPath(
                        kind=model.ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                        value="models/雪-é-e\u0301.pietto",
                    ),
                    line=1,
                    column=2,
                    end_line=1,
                    end_column=3,
                ),
                suggestion="Review exact source spelling.",
            ),
        ),
        payload=payload,
    )


def _failure_envelope() -> model.ProjectExplainEnvelope[
    composition.ProjectExplainPayload
]:
    return model.ProjectExplainEnvelope(
        format=model.ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=False,
        diagnostics=(
            model.ProjectExplainDiagnostic(
                code="PIE-T5808-E",
                severity=Severity.ERROR,
                message="Test-owned Project Explain failure witness.",
                location=model.ProjectExplainLocation(
                    path=model.ProjectExplainLogicalPath(
                        kind=model.ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
                        value="models/failure.pietto",
                    ),
                    line=None,
                    column=None,
                    end_line=None,
                    end_column=None,
                ),
                suggestion=None,
            ),
        ),
        payload=None,
    )


def _type_references() -> tuple[
    catalog.ProjectExplainExtensionCatalogTypeReference,
    catalog.ProjectExplainExtensionCatalogTypeReference,
    catalog.ProjectExplainExtensionCatalogTypeReference,
]:
    return (
        catalog.ProjectExplainExtensionCatalogTypeReference(
            kind=catalog.ProjectExplainCatalogTypeReferenceKind.PIETTO_LOGICAL,
            logical_name="Int",
            logical_kind=TypeKind.BUILTIN,
            physical_name=None,
            extension_identity=None,
        ),
        catalog.ProjectExplainExtensionCatalogTypeReference(
            kind=catalog.ProjectExplainCatalogTypeReferenceKind.POSTGRES_BUILTIN,
            logical_name=None,
            logical_kind=None,
            physical_name="int4",
            extension_identity=None,
        ),
        catalog.ProjectExplainExtensionCatalogTypeReference(
            kind=catalog.ProjectExplainCatalogTypeReferenceKind.EXTENSION_NATIVE,
            logical_name=None,
            logical_kind=None,
            physical_name="vector",
            extension_identity="pgvector",
        ),
    )


def _walk_carriers(value: object, witnesses: dict[type[Any], object]) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        value_type = type(value)
        if value_type in _CARRIER_FIELDS:
            witnesses.setdefault(value_type, value)
        for field in fields(value):
            _walk_carriers(getattr(value, field.name), witnesses)
    elif type(value) is tuple:
        for item in cast(tuple[object, ...], value):
            _walk_carriers(item, witnesses)


def test_exact_four_field_success_and_failure_envelopes(tmp_path: Path) -> None:
    success = _success_envelope(tmp_path)
    success_value = json_v1.project_explain_envelope_to_json_value(success)
    assert tuple(success_value) == ("format", "ok", "diagnostics", "payload")
    assert success_value["format"] == "pietto.project-explain.v1"
    assert success_value["ok"] is True
    assert success_value["payload"] is not None
    assert len(cast(list[object], success_value["diagnostics"])) == 1

    empty_diagnostics = replace(success, diagnostics=())
    assert (
        json_v1.project_explain_envelope_to_json_value(empty_diagnostics)["diagnostics"]
        == []
    )

    failure_value = json_v1.project_explain_envelope_to_json_value(_failure_envelope())
    assert tuple(failure_value) == ("format", "ok", "diagnostics", "payload")
    assert failure_value["ok"] is False
    assert failure_value["payload"] is None
    assert set(failure_value) == {"format", "ok", "diagnostics", "payload"}


def test_all_49_reachable_carriers_have_exact_explicit_field_serializers(
    tmp_path: Path,
) -> None:
    envelope = _success_envelope(tmp_path)
    witnesses: dict[type[Any], object] = {}
    _walk_carriers(envelope, witnesses)

    logical, builtin, _native = _type_references()
    witnesses[compatibility.ProjectExplainMatrixBlocker] = slice6._evaluation(
        0,
        slice6._target(0),
        compatibility.ProjectExplainEvaluationState.BLOCKED,
    ).blockers[0]
    witnesses[catalog.ProjectExplainExtensionCatalogOperatorIdentity] = (
        catalog.ProjectExplainExtensionCatalogOperatorIdentity(
            operator_name="-",
            arity=catalog.ProjectExplainPostgreSQLOperatorArity.UNARY,
            operand_types=(builtin,),
        )
    )
    witnesses[catalog.ProjectExplainExtensionCatalogCastIdentity] = (
        catalog.ProjectExplainExtensionCatalogCastIdentity(
            source_type=logical,
            target_type=builtin,
        )
    )
    witnesses[portability.ProjectExplainDefiniteGap] = (
        portability.ProjectExplainDefiniteGap(
            target_position=0,
            status=compatibility.ProjectExplainCheckedStatus.ABSENT,
        )
    )

    assert len(_CARRIER_FIELDS) == 49
    declared_carriers = {
        carrier
        for carrier_module in _CARRIER_MODULES
        for _name, carrier in inspect.getmembers(carrier_module, inspect.isclass)
        if carrier.__module__ == carrier_module.__name__ and is_dataclass(carrier)
    }
    assert declared_carriers == _CARRIER_FIELDS.keys()
    assert _CARRIER_SERIALIZERS.keys() == _CARRIER_FIELDS.keys()
    assert witnesses.keys() == _CARRIER_FIELDS.keys()
    for carrier_type, expected_fields in _CARRIER_FIELDS.items():
        assert tuple(field.name for field in fields(carrier_type)) == expected_fields
        serialized = _CARRIER_SERIALIZERS[carrier_type](witnesses[carrier_type])
        assert serialized is not None
        assert tuple(serialized) == expected_fields

    spec_inventory = {
        cells[0].strip("`"): tuple(
            field.strip().strip("`") for field in cells[1].split(",")
        )
        for line in SPEC.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `ProjectExplain")
        for cells in (tuple(cell.strip() for cell in line.strip("|").split("|")),)
    }
    assert spec_inventory == {
        carrier.__name__: field_names
        for carrier, field_names in _CARRIER_FIELDS.items()
    }


def test_typed_selector_families_and_identity_shapes_are_structured() -> None:
    logical, builtin, native = _type_references()
    callable_identity = catalog.ProjectExplainExtensionCatalogCallableIdentity(
        sql_name="example",
        input_types=(logical, native),
    )
    operator_identity = catalog.ProjectExplainExtensionCatalogOperatorIdentity(
        operator_name="<->",
        arity=catalog.ProjectExplainPostgreSQLOperatorArity.BINARY,
        operand_types=(native, native),
    )
    cast_identity = catalog.ProjectExplainExtensionCatalogCastIdentity(
        source_type=logical,
        target_type=builtin,
    )
    selectors = (
        catalog.ProjectExplainExtensionCatalogSelector(
            family=catalog.ProjectExplainCatalogEntryFamily.NATIVE_TYPE,
            identity=native,
        ),
        catalog.ProjectExplainExtensionCatalogSelector(
            family=catalog.ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION,
            identity=callable_identity,
        ),
        catalog.ProjectExplainExtensionCatalogSelector(
            family=catalog.ProjectExplainCatalogEntryFamily.AGGREGATE,
            identity=callable_identity,
        ),
        catalog.ProjectExplainExtensionCatalogSelector(
            family=catalog.ProjectExplainCatalogEntryFamily.OPERATOR,
            identity=operator_identity,
        ),
        catalog.ProjectExplainExtensionCatalogSelector(
            family=catalog.ProjectExplainCatalogEntryFamily.CAST,
            identity=cast_identity,
        ),
    )

    values = tuple(json_v1._catalog_selector_to_json_value(item) for item in selectors)
    assert tuple(value["family"] for value in values) == tuple(
        item.family.value for item in selectors
    )
    assert tuple(
        tuple(cast(dict[str, object], value["identity"])) for value in values
    ) == (
        _CARRIER_FIELDS[catalog.ProjectExplainExtensionCatalogTypeReference],
        _CARRIER_FIELDS[catalog.ProjectExplainExtensionCatalogCallableIdentity],
        _CARRIER_FIELDS[catalog.ProjectExplainExtensionCatalogCallableIdentity],
        _CARRIER_FIELDS[catalog.ProjectExplainExtensionCatalogOperatorIdentity],
        _CARRIER_FIELDS[catalog.ProjectExplainExtensionCatalogCastIdentity],
    )
    assert all(
        "type" not in value and "type" not in cast(dict[str, object], value["identity"])
        for value in values
    )


def test_reference_kinds_arities_and_enum_values_are_exact() -> None:
    for kind in composition.ProjectExplainArtifactReferenceKind:
        arity = composition._REFERENCE_ARITIES[kind]
        value = json_v1._artifact_reference_to_json_value(
            composition.ProjectExplainArtifactReference(
                kind=kind,
                positions=tuple(range(arity)),
            )
        )
        assert value == {"kind": kind.value, "positions": list(range(arity))}

    for variant in compatibility.ProjectExplainLookupVariant:
        lookup = slice4._lookup(variant)
        value = json_v1._lookup_summary_to_json_value(lookup)
        assert value["variant"] == variant.value
        assert value["supports"] == [item.value for item in lookup.supports]

    for status in compatibility.ProjectExplainCheckedStatus:
        cell = slice6._cell(0, status)
        value = json_v1._matrix_cell_to_json_value(cell)
        assert value["checked_status"] == status.value
        assert (
            value["state"] == compatibility.ProjectExplainEvaluationState.CHECKED.value
        )

    target = slice6._target(0)
    for state in compatibility.ProjectExplainEvaluationState:
        evaluation = slice6._evaluation(0, target, state)
        value = json_v1._package_target_evaluation_to_json_value(evaluation)
        assert value["state"] == state.value
        assert value["evidence_posture"] == evaluation.evidence_posture.value

    for domain in CapabilityDomain:
        key = package.ProjectExplainCapabilityKey(
            domain=domain,
            subject="subject",
            operation=None,
            operands=(),
            context=None,
            dialect=None,
            extension=None,
        )
        assert json_v1._capability_key_to_json_value(key)["domain"] == domain.value

    for profile_kind in compatibility.ProjectExplainProfileKind:
        profile = slice4._simple_profile(kind=profile_kind)
        profile_value = json_v1._capability_profile_to_json_value(profile)
        assert profile_value["kind"] == profile_kind.value
        assert profile_value["target_kind"] == profile.target_kind.value

    profile = slice4._simple_profile()
    occurrences = (
        compatibility.ProjectExplainAvailabilityOccurrence(
            owner_kind=compatibility.ProjectExplainAvailabilityOwnerKind.COMPILER,
            owner_position=0,
            project_path=None,
            profile=profile,
        ),
        compatibility.ProjectExplainAvailabilityOccurrence(
            owner_kind=compatibility.ProjectExplainAvailabilityOwnerKind.PROJECT,
            owner_position=0,
            project_path=model.ProjectExplainLogicalPath(
                kind=model.ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                value="pietto.toml",
            ),
            profile=profile,
        ),
    )
    assert tuple(
        json_v1._availability_occurrence_to_json_value(item)["owner_kind"]
        for item in occurrences
    ) == tuple(item.owner_kind.value for item in occurrences)

    blockers = (
        slice6._evaluation(
            0,
            target,
            compatibility.ProjectExplainEvaluationState.BLOCKED,
        ).blockers[0],
        compatibility.ProjectExplainMatrixBlocker(
            kind=compatibility.ProjectExplainMatrixBlockerKind.PROFILE_AUTHORITY_MISMATCH,
            selected_profile=profile,
            bucket_profile=profile,
            bucket_occurrences=(occurrences[0],),
        ),
    )
    assert tuple(
        json_v1._matrix_blocker_to_json_value(item)["kind"] for item in blockers
    ) == tuple(item.kind.value for item in blockers)


def test_catalog_and_portability_enum_variants_emit_values(tmp_path: Path) -> None:
    payload = cast(
        composition.ProjectExplainPayload,
        _success_envelope(tmp_path).payload,
    )
    selected = payload.extension_catalog_evidence.contexts[0].requirements[0].selection
    candidate = selected.candidates[0]
    second_candidate = replace(
        candidate, catalog_position=candidate.catalog_position + 1
    )
    selections = (
        selected,
        replace(
            selected,
            outcome=catalog.ProjectExplainCatalogSelectionOutcome.UNDECLARED,
            evidence_posture=model.ProjectExplainEvidencePosture.UNAVAILABLE,
            candidates=(),
            selected_catalog_position=None,
        ),
        replace(
            selected,
            outcome=catalog.ProjectExplainCatalogSelectionOutcome.AMBIGUOUS,
            evidence_posture=model.ProjectExplainEvidencePosture.CONFLICTING,
            candidates=(candidate, second_candidate),
            selected_catalog_position=None,
        ),
        replace(
            selected,
            outcome=catalog.ProjectExplainCatalogSelectionOutcome.CONFLICT,
            evidence_posture=model.ProjectExplainEvidencePosture.CONFLICTING,
            candidates=(candidate, second_candidate),
            selected_catalog_position=None,
        ),
    )
    assert tuple(
        json_v1._catalog_selection_to_json_value(item)["outcome"] for item in selections
    ) == tuple(item.outcome.value for item in selections)

    logical, builtin, native = _type_references()
    assert tuple(
        json_v1._catalog_type_reference_to_json_value(item)["kind"]
        for item in (logical, builtin, native)
    ) == tuple(item.kind.value for item in (logical, builtin, native))
    for logical_kind in TypeKind:
        logical_value = replace(logical, logical_kind=logical_kind)
        assert (
            json_v1._catalog_type_reference_to_json_value(logical_value)["logical_kind"]
            == logical_kind.value
        )

    for arity, operands in (
        (catalog.ProjectExplainPostgreSQLOperatorArity.UNARY, (native,)),
        (catalog.ProjectExplainPostgreSQLOperatorArity.BINARY, (native, native)),
    ):
        operator = catalog.ProjectExplainExtensionCatalogOperatorIdentity(
            operator_name="<->",
            arity=arity,
            operand_types=operands,
        )
        assert (
            json_v1._catalog_operator_identity_to_json_value(operator)["arity"]
            == arity.value
        )

    available = selected.availability[0]
    project_available = replace(
        available,
        owner_kind=catalog.ProjectExplainCatalogAvailabilityOwnerKind.PROJECT,
        project_path=model.ProjectExplainLogicalPath(
            kind=model.ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value="pietto.toml",
        ),
    )
    assert tuple(
        json_v1._catalog_availability_to_json_value(item)["owner_kind"]
        for item in (available, project_available)
    ) == tuple(item.owner_kind.value for item in (available, project_available))

    exact_entry = catalog.ProjectExplainExtensionCatalogEntryEvidence(
        entry_position=0,
        entry_family=catalog.ProjectExplainCatalogEntryFamily.NATIVE_TYPE,
        matchability=catalog.ProjectExplainCatalogMatchability.EXACT_MATCHABLE,
        exposure=catalog.ProjectExplainCatalogExposure.IMPLEMENTATION_SUPPORT,
        unmodeled_reasons=(),
        source_positions=(0,),
    )
    for exposure in catalog.ProjectExplainCatalogExposure:
        entry = replace(exact_entry, exposure=exposure)
        assert (
            json_v1._catalog_entry_evidence_to_json_value(entry)["exposure"]
            == exposure.value
        )
    for reason in catalog.ProjectExplainCatalogUnmodeledReason:
        entry = replace(
            exact_entry,
            matchability=catalog.ProjectExplainCatalogMatchability.CATALOGED_UNMODELED,
            unmodeled_reasons=(reason,),
        )
        value = json_v1._catalog_entry_evidence_to_json_value(entry)
        assert value["matchability"] == "cataloged_unmodeled"
        assert value["unmodeled_reasons"] == [reason.value]
    for family in catalog.ProjectExplainCatalogEntryFamily:
        entry = replace(exact_entry, entry_family=family)
        assert (
            json_v1._catalog_entry_evidence_to_json_value(entry)["entry_family"]
            == family.value
        )

    second_entry = replace(exact_entry, entry_position=1)
    groups = (
        catalog.ProjectExplainExtensionCatalogExactGroupEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogExactGroupState.UNIQUE,
            entries=(exact_entry,),
        ),
        catalog.ProjectExplainExtensionCatalogExactGroupEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogExactGroupState.CONSISTENT_DUPLICATE,
            entries=(exact_entry, second_entry),
        ),
        catalog.ProjectExplainExtensionCatalogExactGroupEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogExactGroupState.EVIDENCE_CONFLICT,
            entries=(exact_entry, second_entry),
        ),
    )
    assert tuple(
        json_v1._catalog_exact_group_to_json_value(item)["state"] for item in groups
    ) == tuple(item.state.value for item in groups)

    complete_claim = catalog.ProjectExplainExtensionCatalogCompletenessClaim(
        position=0,
        kind=catalog.ProjectExplainCatalogCompletenessClaimKind.COMPLETE,
        source_positions=(0,),
    )
    incomplete_claim = catalog.ProjectExplainExtensionCatalogCompletenessClaim(
        position=1,
        kind=catalog.ProjectExplainCatalogCompletenessClaimKind.INCOMPLETE,
        source_positions=(0,),
    )
    completeness_values = (
        catalog.ProjectExplainExtensionCatalogCompletenessEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogCompletenessState.COMPLETE,
            claims=(complete_claim,),
        ),
        catalog.ProjectExplainExtensionCatalogCompletenessEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogCompletenessState.INCOMPLETE,
            claims=(replace(incomplete_claim, position=0),),
        ),
        catalog.ProjectExplainExtensionCatalogCompletenessEvidence(
            position=0,
            state=catalog.ProjectExplainCatalogCompletenessState.CONFLICT,
            claims=(complete_claim, incomplete_claim),
        ),
    )
    assert tuple(
        json_v1._catalog_completeness_to_json_value(item)["state"]
        for item in completeness_values
    ) == tuple(item.state.value for item in completeness_values)
    assert {
        claim["kind"]
        for item in completeness_values
        for claim in cast(
            list[dict[str, object]],
            json_v1._catalog_completeness_to_json_value(item)["claims"],
        )
    } == {item.value for item in catalog.ProjectExplainCatalogCompletenessClaimKind}

    gap = portability.ProjectExplainDefiniteGap(
        target_position=0,
        status=compatibility.ProjectExplainCheckedStatus.UNSUPPORTED,
    )
    requirement_values = (
        portability.ProjectExplainRequirementPortability(
            requirement_position=0,
            classification=portability.ProjectExplainPortabilityClassification.PORTABLE,
            reason=None,
            definite_gaps=(),
        ),
        portability.ProjectExplainRequirementPortability(
            requirement_position=0,
            classification=(
                portability.ProjectExplainPortabilityClassification.NOT_PORTABLE
            ),
            reason=None,
            definite_gaps=(gap,),
        ),
        portability.ProjectExplainRequirementPortability(
            requirement_position=0,
            classification=(
                portability.ProjectExplainPortabilityClassification.INDETERMINATE
            ),
            reason=portability.ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS,
            definite_gaps=(),
        ),
    )
    assert tuple(
        json_v1._requirement_portability_to_json_value(item)["classification"]
        for item in requirement_values
    ) == tuple(item.classification.value for item in requirement_values)


def test_arrays_preserve_composed_semantic_order_without_new_dedup(
    tmp_path: Path,
) -> None:
    envelope = _success_envelope(tmp_path / "source-rich")
    payload = cast(composition.ProjectExplainPayload, envelope.payload)
    value = cast(
        dict[str, Any],
        json_v1.project_explain_envelope_to_json_value(envelope)["payload"],
    )
    packages = value["package_requirements"]["packages"]
    requirements = value["package_requirements"]["requirements"]
    assert [item["position"] for item in packages] == [
        item.position for item in payload.package_requirements.packages
    ]
    assert [item["position"] for item in requirements] == [
        item.position for item in payload.package_requirements.requirements
    ]

    compatibility_value = value["compatibility"]
    assert [item["position"] for item in compatibility_value["targets"]] == [
        item.position for item in payload.compatibility.targets
    ]
    assert [
        (item["package_position"], item["target_position"])
        for item in compatibility_value["package_target_evaluations"]
    ] == [
        (item.package_position, item.target_position)
        for item in payload.compatibility.package_target_evaluations
    ]
    assert [item["requirement_position"] for item in compatibility_value["rows"]] == [
        item.requirement_position for item in payload.compatibility.rows
    ]
    assert [
        [cell["target_position"] for cell in row["cells"]]
        for row in compatibility_value["rows"]
    ] == [
        [cell.target_position for cell in row.cells]
        for row in payload.compatibility.rows
    ]

    context_value = value["extension_catalog_evidence"]["contexts"][0]
    context = payload.extension_catalog_evidence.contexts[0]
    assert [item["position"] for item in context_value["catalogs"]] == [
        item.position for item in context.catalogs
    ]
    assert [
        item["position"] for item in context_value["catalogs"][0]["source_occurrences"]
    ] == [item.position for item in context.catalogs[0].source_occurrences]
    assert [
        item["request"]["positions"] for item in value["requirement_explanations"]
    ] == [list(item.request.positions) for item in payload.requirement_explanations]
    assert value["requirement_explanations"][0]["targets"][0]["source_evidence"] == [
        {"kind": item.kind.value, "positions": list(item.positions)}
        for item in payload.requirement_explanations[0].targets[0].source_evidence
    ]

    two_target_payload = composition._compose_project_explain_payload(
        *slice7._selected_sections(tmp_path / "two-targets", target_count=2)
    )
    two_target_envelope = replace(envelope, payload=two_target_payload)
    two_target_value = cast(
        dict[str, Any],
        json_v1.project_explain_envelope_to_json_value(two_target_envelope)["payload"],
    )
    assert [
        item["position"] for item in two_target_value["compatibility"]["targets"]
    ] == [
        0,
        1,
    ]


@pytest.mark.parametrize(
    ("kind", "path_value"),
    [
        (model.ProjectExplainLogicalPathKind.PROJECT_RELATIVE, "models/雪.pietto"),
        (model.ProjectExplainLogicalPathKind.PACKAGE_RELATIVE, "src/types.pietto"),
        (
            model.ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR,
            "https://example.test/source#é",
        ),
    ],
)
def test_logical_path_kinds_locations_and_host_privacy(
    kind: model.ProjectExplainLogicalPathKind,
    path_value: str,
) -> None:
    path = model.ProjectExplainLogicalPath(kind=kind, value=path_value)
    assert json_v1._logical_path_to_json_value(path) == {
        "kind": kind.value,
        "value": path_value,
    }
    path_only = model.ProjectExplainLocation(
        path=path,
        line=None,
        column=None,
        end_line=None,
        end_column=None,
    )
    assert json_v1._location_to_json_value(path_only) == {
        "path": {"kind": kind.value, "value": path_value},
        "line": None,
        "column": None,
        "end_line": None,
        "end_column": None,
    }
    assert json_v1._location_to_json_value(None) is None

    with pytest.raises(ValueError):
        model.ProjectExplainLogicalPath(
            kind=model.ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value="/home/user/private.pietto",
        )


def test_compact_utf8_bytes_are_deterministic_and_not_normalized(
    tmp_path: Path,
) -> None:
    envelope = _success_envelope(tmp_path)
    first = json_v1.serialize_project_explain_json_document(envelope)
    second = json_v1.serialize_project_explain_json_document(envelope)
    assert first == second
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert first.count(b"\n") == 1
    assert not first.startswith(b"\xef\xbb\xbf")
    assert b'": ' not in first and b', "' not in first
    assert (
        "雪".encode() in first and "é".encode() in first and "e\u0301".encode() in first
    )
    assert b"\\u96ea" not in first
    assert json.loads(first)["format"] == "pietto.project-explain.v1"
    assert "é".encode() != "e\u0301".encode()
    assert str(tmp_path).encode() not in first
    assert b"/home/" not in first and b"/tmp/" not in first

    diagnostic = envelope.diagnostics[0]
    surrogate = replace(diagnostic, message="bad surrogate: \ud800")
    invalid = replace(envelope, diagnostics=(surrogate,))
    with pytest.raises(UnicodeEncodeError):
        json_v1.serialize_project_explain_json_document(invalid)


def test_canonical_payload_subclasses_private_grafts_and_partial_failures_reject(
    tmp_path: Path,
) -> None:
    success = _success_envelope(tmp_path / "canonical")
    payload = cast(composition.ProjectExplainPayload, success.payload)
    grafted = replace(payload, requirement_explanations=())
    with pytest.raises(ValueError, match="canonical Slice 7"):
        json_v1.project_explain_envelope_to_json_value(
            replace(success, payload=grafted)
        )

    subclass_payload = _PayloadSubclass(
        package_requirements=payload.package_requirements,
        compatibility=payload.compatibility,
        extension_catalog_evidence=payload.extension_catalog_evidence,
        portability=payload.portability,
        requirement_explanations=payload.requirement_explanations,
    )
    with pytest.raises(TypeError, match="exact payload"):
        json_v1.project_explain_envelope_to_json_value(
            replace(success, payload=subclass_payload)
        )

    subclass_envelope = _EnvelopeSubclass(
        format=success.format,
        ok=success.ok,
        diagnostics=success.diagnostics,
        payload=payload,
    )
    with pytest.raises(TypeError, match="exact envelope"):
        json_v1.project_explain_envelope_to_json_value(subclass_envelope)

    wrong_marker = replace(success)
    object.__setattr__(wrong_marker, "format", "pietto.project-explain.invalid")
    with pytest.raises(TypeError, match="v1 format marker"):
        json_v1.project_explain_envelope_to_json_value(wrong_marker)

    missing_payload = replace(success)
    object.__setattr__(missing_payload, "payload", None)
    with pytest.raises(ValueError, match="need a payload"):
        json_v1.project_explain_envelope_to_json_value(missing_payload)

    error_success = replace(success)
    object.__setattr__(error_success, "diagnostics", _failure_envelope().diagnostics)
    with pytest.raises(ValueError, match="forbid error diagnostics"):
        json_v1.project_explain_envelope_to_json_value(error_success)

    error_free_failure = _failure_envelope()
    object.__setattr__(error_free_failure, "diagnostics", success.diagnostics)
    with pytest.raises(ValueError, match="require an error diagnostic"):
        json_v1.project_explain_envelope_to_json_value(error_free_failure)

    callable_identity = (
        payload.extension_catalog_evidence.contexts[0].requirements[0].selector.identity
    )
    assert (
        type(callable_identity)
        is catalog.ProjectExplainExtensionCatalogCallableIdentity
    )
    callable_subclass = _CallableIdentitySubclass(
        sql_name=callable_identity.sql_name,
        input_types=callable_identity.input_types,
    )
    with pytest.raises(TypeError, match="exact callable identity"):
        json_v1._catalog_callable_identity_to_json_value(callable_subclass)

    mismatched_selector = replace(
        payload.extension_catalog_evidence.contexts[0].requirements[0].selector
    )
    object.__setattr__(
        mismatched_selector,
        "family",
        catalog.ProjectExplainCatalogEntryFamily.OPERATOR,
    )
    with pytest.raises(TypeError, match="family and typed identity disagree"):
        json_v1._catalog_selector_to_json_value(mismatched_selector)

    altered_evidence = catalog.ProjectExplainExtensionCatalogEvidenceProjection(
        contexts=()
    )
    with pytest.raises(ValueError):
        json_v1.project_explain_envelope_to_json_value(
            replace(
                success,
                payload=replace(
                    payload,
                    extension_catalog_evidence=altered_evidence,
                ),
            )
        )

    failure = _failure_envelope()
    object.__setattr__(failure, "payload", payload)
    with pytest.raises(ValueError, match="forbid a payload"):
        json_v1.project_explain_envelope_to_json_value(failure)


def test_success_and_failure_goldens_are_byte_exact_and_strictly_registered(
    tmp_path: Path,
) -> None:
    success = json_v1.serialize_project_explain_json_document(
        _success_envelope(tmp_path)
    )
    failure = json_v1.serialize_project_explain_json_document(_failure_envelope())
    assert success == SUCCESS_GOLDEN.read_bytes()
    assert failure == FAILURE_GOLDEN.read_bytes()
    assert json.loads(success)["ok"] is True
    assert json.loads(failure) == {
        "format": "pietto.project-explain.v1",
        "ok": False,
        "diagnostics": [
            {
                "code": "PIE-T5808-E",
                "severity": "error",
                "message": "Test-owned Project Explain failure witness.",
                "location": {
                    "path": {
                        "kind": "package_relative",
                        "value": "models/failure.pietto",
                    },
                    "line": None,
                    "column": None,
                    "end_line": None,
                    "end_column": None,
                },
                "suggestion": None,
            }
        ],
        "payload": None,
    }

    assert goldens.MODEL_JSON_FIXTURES == frozenset(
        {SUCCESS_GOLDEN.name, FAILURE_GOLDEN.name}
    )
    assert goldens.MODEL_JSON_FIXTURES < goldens.JSON_FIXTURES
    assert set(goldens.FIXTURE_INPUTS) == (
        goldens.CLASSIFIED_FIXTURES - goldens.MODEL_JSON_FIXTURES
    )
    assert Path("tests/test_phase58_slice8_project_explain_json_v1.py") in (
        goldens.REFERENCE_TESTS
    )
    assert goldens.audit(REPO_ROOT) == ()


def test_source_is_explicit_private_and_cli_reuses_serializer_exactly() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported_modules == {"json"}
    for forbidden in (
        "asdict",
        "dataclasses.fields",
        "vars(",
        "__dict__",
        "inspect",
        "repr(",
        "pickle",
        "jsonpickle",
        "default=str",
        "sort_keys=True",
        "Path(",
        "open(",
        "read_text(",
        "read_bytes(",
        "requests",
        "socket",
        "subprocess",
        "cli_json",
        "render_json_document",
    ):
        assert forbidden not in source
    assert "ensure_ascii=False" in source
    assert "allow_nan=False" in source
    assert "sort_keys=False" in source
    assert 'separators=(",", ":")' in source
    assert json_v1.__all__ == ()

    for module in (
        pietto,
        project_package,
        metadata_package,
        project_explain_package,
        semantic_package,
    ):
        assert not hasattr(module, "serialize_project_explain_json_document")
        assert not hasattr(module, "project_explain_envelope_to_json_value")
    cli_source = (REPO_ROOT / "src/pietto/cli.py").read_text(encoding="utf-8")
    assert "serialize_project_explain_json_document" in cli_source
    assert "json.dumps" not in cli_source
    assert not tuple((REPO_ROOT / "docs/spec").glob("*project-explain*.schema.json"))


def test_spec_golden_policy_and_installed_module_contract_are_exact() -> None:
    spec = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "pietto.project-explain.v1",
        "format ok diagnostics payload",
        "49 serialized dataclass carriers",
        "ensure_ascii=False",
        "allow_nan=False",
        "sort_keys=False",
        'separators=(",", ":")',
        "one final LF",
        "UTF-8",
        "null",
        "MODEL_JSON_FIXTURES",
        "PHASE58_SLICE8_SELF_OWNED_OPEN = 0",
        "Slice 9 remains unstarted and retains CLI integration",
    ):
        assert required in spec

    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    for required in (
        'f"{prefix}/_project_explain/json_v1.py"',
        '"installed private project explain JSON v1 import"',
        "import pietto._project_explain.json_v1",
    ):
        assert required in package_smoke
