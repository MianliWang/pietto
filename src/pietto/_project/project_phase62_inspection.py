"""Verified-only private Phase-62 inspection, queries, and pure projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.project_grain import (
    ProjectBaseGrainFactorIdentity,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGroupedGrainFactorIdentity,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRSnapshotScope,
    ProjectIRUseRef,
)
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinIdentity,
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinMatchFieldPair,
    ProjectIRJoinOutputProperties,
    ProjectIRJoinUnavailableProperty,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
    ProjectIRJoinRowOutput,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIROutputCandidateKey,
    ProjectIROutputFDIndex,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputValueFD,
)
from pietto._project.project_ir_verification import ProjectIRVerificationResult
from pietto._project.project_multifact import (
    ProjectActualGrainCandidate,
    ProjectAggregateFactHomeLocality,
    ProjectAggregateFactIdentity,
    ProjectAggregateFactJoinLocality,
    ProjectAggregateFactLocality,
    ProjectAggregateFactOccurrence,
    ProjectCommonGrainResult,
    ProjectFactChasmCandidate,
    ProjectFactContextualGrain,
    ProjectFactMultiplicityExposure,
    ProjectMultiFactAlignment,
    ProjectMultiFactAnalysis,
    ProjectMultiFactConcreteRegion,
    ProjectMultiFactNonConcreteRegionSubject,
)
from pietto._project.project_phase62_pure_boundary import (
    PROJECT_PHASE62_INSPECTION_FORMAT,
    PROJECT_PHASE62_PURE_ABSENT,
    ProjectPhase62PortableRef,
    ProjectPhase62PortableRefDomain,
    ProjectPhase62PureDocument,
    ProjectPhase62PureField,
    ProjectPhase62PureRecord,
    ProjectPhase62PureStatus,
    ProjectPhase62PureValue,
    ProjectPhase62RecordKind,
    evaluate_project_phase62_document,
    project_phase62_pure_enumeration,
    project_phase62_pure_enumerations,
    project_phase62_pure_integer,
    project_phase62_pure_integers,
    project_phase62_pure_ref,
    project_phase62_pure_refs,
    project_phase62_pure_text,
    project_phase62_pure_texts,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62AnalysisBundle,
    ProjectPhase62CombinedReverseUseEntry,
    ProjectPhase62CombinedUse,
    ProjectPhase62FactLocalityEntry,
    ProjectPhase62MultiFactAlignmentIndex,
    ProjectPhase62NullingProvenanceEntry,
    ProjectPhase62VerificationResult,
    ProjectPhase62VerificationStatus,
)
from pietto._project.project_relationship_conditions import (
    ProjectConcreteRelationshipCondition,
    ProjectRelationshipEqualityCorrespondence,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
    ProjectRelationshipDirectionIdentity,
)
from pietto._project.project_relationship_paths import (
    ProjectRelationshipPath,
    ProjectRelationshipPathAnalysis,
    ProjectRelationshipPathStep,
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUse,
    ProjectJoinUseIdentity,
    ProjectNonConcreteJoinUse,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
    ProjectTraversalStepUse,
)
from pietto._project.project_relationships import (
    ProjectRelationshipDeclarationIdentity,
    ProjectRelationshipSubject,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62InspectionSummary:
    scope: ProjectIRSnapshotScope = field(repr=False, compare=False, hash=False)
    relationship_count: int
    direction_count: int
    condition_count: int
    correspondence_count: int
    guarantee_count: int
    ledger_count: int
    join_use_count: int
    path_step_count: int
    binary_join_count: int
    joined_output_count: int
    joined_field_count: int
    base_relational_output_count: int
    candidate_key_count: int
    value_fd_count: int
    grain_factor_count: int
    grain_dependency_count: int
    aggregate_fact_count: int
    fact_locality_count: int
    common_grain_count: int
    alignment_count: int
    chasm_count: int
    non_concrete_region_count: int
    combined_analysis_entry_count: int

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Phase-62 summary requires one exact snapshot scope.")
        for value in (
            self.relationship_count,
            self.direction_count,
            self.condition_count,
            self.correspondence_count,
            self.guarantee_count,
            self.ledger_count,
            self.join_use_count,
            self.path_step_count,
            self.binary_join_count,
            self.joined_output_count,
            self.joined_field_count,
            self.base_relational_output_count,
            self.candidate_key_count,
            self.value_fd_count,
            self.grain_factor_count,
            self.grain_dependency_count,
            self.aggregate_fact_count,
            self.fact_locality_count,
            self.common_grain_count,
            self.alignment_count,
            self.chasm_count,
            self.non_concrete_region_count,
            self.combined_analysis_entry_count,
        ):
            if type(value) is not int or value < 0:
                raise TypeError("Phase-62 summary counts must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62Inspection:
    """Complete observation of one exact verified Phase-62 bundle."""

    analysis_bundle: ProjectPhase62AnalysisBundle = field(
        repr=False, compare=False, hash=False
    )
    summary: ProjectPhase62InspectionSummary
    verification: ProjectPhase62VerificationResult
    root: ProjectMultiFactAnalysis = field(repr=False, compare=False, hash=False)
    base_verification: ProjectIRVerificationResult
    relationship_subjects: tuple[ProjectRelationshipSubject, ...]
    relationship_directions: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]
    relationship_conditions: tuple[ProjectConcreteRelationshipCondition, ...]
    correspondences: tuple[ProjectRelationshipEqualityCorrespondence, ...]
    match_guarantees: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]
    direct_candidate_buckets: tuple[
        tuple[ProjectDirectionalRelationshipMatchGuarantee, ...], ...
    ]
    declaration_direction_buckets: tuple[
        tuple[ProjectDirectionalRelationshipMatchGuarantee, ...], ...
    ]
    join_use_ledgers: tuple[ProjectRelationJoinUseLedger, ...]
    relation_bindings: tuple[ProjectRelationBindingOccurrence, ...]
    join_uses: tuple[ProjectJoinUse, ...]
    traversal_step_uses: tuple[ProjectTraversalStepUse, ...]
    paths: tuple[ProjectRelationshipPath, ...]
    path_steps: tuple[ProjectRelationshipPathStep, ...]
    path_analyses: tuple[ProjectRelationshipPathAnalysis, ...]
    concrete_join_regions: tuple[ProjectIRConcreteJoinRegion, ...]
    non_concrete_join_regions: tuple[ProjectIRNonConcreteJoinRegion, ...]
    binary_joins: tuple[ProjectIRBinaryJoinOccurrence, ...]
    join_input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    join_input_uses: tuple[ProjectPhase62CombinedUse, ...]
    joined_outputs: tuple[ProjectIRJoinRowOutput, ...]
    joined_fields: tuple[ProjectIRJoinedRowField, ...]
    match_field_pairs: tuple[ProjectIRJoinMatchFieldPair, ...]
    join_output_properties: tuple[ProjectIRJoinOutputProperties, ...]
    base_relational_outputs: tuple[ProjectIROutputRelationalProperties, ...]
    join_relational_outputs: tuple[ProjectIROutputRelationalProperties, ...]
    relational_fields: tuple[ProjectIROutputFieldOccurrence, ...]
    value_classes: tuple[ProjectIROutputValueClass, ...]
    candidate_keys: tuple[ProjectIROutputCandidateKey, ...]
    value_fds: tuple[ProjectIROutputValueFD, ...]
    fd_indexes: tuple[ProjectIROutputFDIndex, ...]
    grains: tuple[ProjectIRProvidedIntrinsicGrain, ...]
    grain_factors: tuple[ProjectGrainDomainFactor, ...]
    grain_dependencies: tuple[ProjectGrainDependencyFact, ...]
    aggregate_facts: tuple[ProjectAggregateFactOccurrence, ...]
    home_localities: tuple[ProjectAggregateFactHomeLocality, ...]
    join_localities: tuple[ProjectAggregateFactJoinLocality, ...]
    fact_localities: tuple[ProjectAggregateFactLocality, ...]
    contextual_grains: tuple[ProjectFactContextualGrain, ...]
    multiplicity_exposures: tuple[ProjectFactMultiplicityExposure, ...]
    concrete_multifact_regions: tuple[ProjectMultiFactConcreteRegion, ...]
    actual_grain_candidates: tuple[ProjectActualGrainCandidate, ...]
    common_grain_results: tuple[ProjectCommonGrainResult, ...]
    alignments: tuple[ProjectMultiFactAlignment, ...]
    chasms: tuple[ProjectFactChasmCandidate, ...]
    non_concrete_multifact_regions: tuple[ProjectMultiFactNonConcreteRegionSubject, ...]
    combined_reverse_uses: tuple[ProjectPhase62CombinedReverseUseEntry, ...]
    combined_topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    nulling_provenance: tuple[ProjectPhase62NullingProvenanceEntry, ...]
    fact_locality_index: tuple[ProjectPhase62FactLocalityEntry, ...]
    multifact_alignment_index: ProjectPhase62MultiFactAlignmentIndex

    def __post_init__(self) -> None:
        bundle = self.analysis_bundle
        if (
            type(bundle) is not ProjectPhase62AnalysisBundle
            or bundle.verification.status
            is not ProjectPhase62VerificationStatus.VERIFIED
            or bundle.verification.issues
            or self.verification is not bundle.verification
            or self.root is not bundle.verification.root
            or self.base_verification is not bundle.verification.base_verification
            or self.combined_reverse_uses is not bundle.combined_reverse_uses
            or self.combined_topological_order is not bundle.combined_topological_order
            or self.nulling_provenance is not bundle.nulling_provenance
            or self.fact_locality_index is not bundle.fact_localities
            or self.multifact_alignment_index is not bundle.multifact_alignments
        ):
            raise ValueError("Inspection requires one exact VERIFIED analysis bundle.")
        expected = _runtime_sections(self.root)
        for name, retained in expected.items():
            if not _same_objects(
                cast(tuple[object, ...], getattr(self, name)), retained
            ):
                raise ValueError(
                    "Phase-62 inspection sections must retain exact canonical objects."
                )
        summary = _inspection_summary(bundle, expected)
        if self.summary != summary or self.summary.scope is not summary.scope:
            raise ValueError("Phase-62 inspection summary must retain exact counts.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62InspectionProduct:
    inspection: ProjectPhase62Inspection
    document: ProjectPhase62PureDocument = field(init=False)
    canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.inspection) is not ProjectPhase62Inspection:
            raise TypeError("Phase-62 product requires an exact inspection.")
        document = _project_phase62_document(self.inspection)
        outcome = evaluate_project_phase62_document(document)
        if (
            outcome.status is not ProjectPhase62PureStatus.OK
            or outcome.canonical_bytes is None
        ):
            raise ValueError(
                "Authority-derived Phase-62 inspection must evaluate exactly: "
                f"{outcome.status.value} at {outcome.record_position}:"
                f"{outcome.field_position}."
            )
        object.__setattr__(self, "document", document)
        object.__setattr__(self, "canonical_bytes", outcome.canonical_bytes)


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _runtime_sections(root: ProjectMultiFactAnalysis) -> dict[str, tuple[object, ...]]:
    uses = root.join_regions.uses
    index = uses.index
    subjects = uses.relationships.subjects
    conditions = tuple(
        item
        for item in index.guarantees.conditions.conditions
        if type(item) is ProjectConcreteRelationshipCondition
    )
    join_uses = tuple(use for ledger in uses.ledgers for use in ledger.uses)
    paths = tuple(use.path for use in join_uses if use.path is not None)
    concrete_regions = tuple(
        region
        for region in root.join_regions.regions
        if type(region) is ProjectIRConcreteJoinRegion
    )
    non_concrete_regions = tuple(
        region
        for region in root.join_regions.regions
        if type(region) is ProjectIRNonConcreteJoinRegion
    )
    joins = tuple(join for region in concrete_regions for join in region.joins)
    base_relational = root.base_relational.outputs
    join_relational = tuple(
        item.relational for item in root.join_regions.properties.outputs
    )
    relational = (*base_relational, *join_relational)
    home = root.home_localities
    join_localities = root.join_localities
    alignments = root.alignments
    values: dict[str, tuple[object, ...]] = {
        "relationship_subjects": subjects,
        "relationship_directions": index.directions,
        "relationship_conditions": conditions,
        "correspondences": tuple(
            item for condition in conditions for item in condition.correspondences
        ),
        "match_guarantees": index.directions,
        "direct_candidate_buckets": tuple(index.by_pair.values()),
        "declaration_direction_buckets": tuple(index.by_declaration.values()),
        "join_use_ledgers": uses.ledgers,
        "relation_bindings": tuple(
            binding for ledger in uses.ledgers for binding in ledger.bindings
        ),
        "join_uses": join_uses,
        "traversal_step_uses": tuple(
            step for use in join_uses for step in use.step_uses
        ),
        "paths": paths,
        "path_steps": tuple(step for path in paths for step in path.steps),
        "path_analyses": tuple(
            use.analysis for use in join_uses if type(use) is ProjectConcreteJoinUse
        ),
        "concrete_join_regions": concrete_regions,
        "non_concrete_join_regions": non_concrete_regions,
        "binary_joins": joins,
        "join_input_slots": tuple(slot for join in joins for slot in join.input_slots),
        "join_input_uses": tuple(use for join in joins for use in join.input_uses),
        "joined_outputs": tuple(join.output for join in joins),
        "joined_fields": tuple(
            item for join in joins for item in join.output.row_shape.fields
        ),
        "match_field_pairs": tuple(item for join in joins for item in join.matches),
        "join_output_properties": root.join_regions.properties.outputs,
        "base_relational_outputs": base_relational,
        "join_relational_outputs": join_relational,
        "relational_fields": tuple(
            item for output in relational for item in output.fields
        ),
        "value_classes": tuple(
            item for output in relational for item in output.value_classes
        ),
        "candidate_keys": tuple(item for output in relational for item in output.keys),
        "value_fds": tuple(item for output in relational for item in output.fds),
        "fd_indexes": tuple(output.fd_index for output in relational),
        "grains": tuple(output.grain for output in relational),
        "grain_factors": tuple(
            factor for output in relational for factor in output.grain.factors
        ),
        "grain_dependencies": tuple(
            fact for output in relational for fact in output.grain.dependencies
        ),
        "aggregate_facts": root.facts,
        "home_localities": home,
        "join_localities": join_localities,
        "fact_localities": (*home, *join_localities),
        "contextual_grains": tuple(
            locality.contextual_grain for locality in (*home, *join_localities)
        ),
        "multiplicity_exposures": tuple(
            exposure
            for locality in join_localities
            for exposure in locality.multiplicity_exposures
        ),
        "concrete_multifact_regions": root.concrete_regions,
        "actual_grain_candidates": (
            *(
                candidate
                for alignment in root.home_alignments
                for candidate in alignment.common_grain.actual_candidates
            ),
            *(
                candidate
                for region in root.concrete_regions
                for candidate in region.actual_candidates
            ),
        ),
        "common_grain_results": tuple(
            alignment.common_grain for alignment in alignments
        ),
        "alignments": alignments,
        "chasms": tuple(
            chasm for region in root.concrete_regions for chasm in region.chasms
        ),
        "non_concrete_multifact_regions": root.non_concrete_regions,
    }
    return values


def _inspection_summary(
    bundle: ProjectPhase62AnalysisBundle,
    sections: dict[str, tuple[object, ...]],
) -> ProjectPhase62InspectionSummary:
    return ProjectPhase62InspectionSummary(
        scope=bundle.root.evaluation.project_plan.structural_stage.scope,
        relationship_count=len(sections["relationship_subjects"]),
        direction_count=len(sections["relationship_directions"]),
        condition_count=len(sections["relationship_conditions"]),
        correspondence_count=len(sections["correspondences"]),
        guarantee_count=len(sections["match_guarantees"]),
        ledger_count=len(sections["join_use_ledgers"]),
        join_use_count=len(sections["join_uses"]),
        path_step_count=len(sections["path_steps"]),
        binary_join_count=len(sections["binary_joins"]),
        joined_output_count=len(sections["joined_outputs"]),
        joined_field_count=len(sections["joined_fields"]),
        base_relational_output_count=len(sections["base_relational_outputs"]),
        candidate_key_count=len(sections["candidate_keys"]),
        value_fd_count=len(sections["value_fds"]),
        grain_factor_count=len(sections["grain_factors"]),
        grain_dependency_count=len(sections["grain_dependencies"]),
        aggregate_fact_count=len(sections["aggregate_facts"]),
        fact_locality_count=len(sections["fact_localities"]),
        common_grain_count=len(sections["common_grain_results"]),
        alignment_count=len(sections["alignments"]),
        chasm_count=len(sections["chasms"]),
        non_concrete_region_count=(
            len(sections["non_concrete_join_regions"])
            + len(sections["non_concrete_multifact_regions"])
        ),
        combined_analysis_entry_count=(
            len(bundle.combined_reverse_uses)
            + len(bundle.combined_topological_order)
            + len(bundle.nulling_provenance)
            + len(bundle.fact_localities)
            + 1
        ),
    )


def _derive_project_phase62_inspection(
    bundle: ProjectPhase62AnalysisBundle,
) -> ProjectPhase62Inspection:
    if type(bundle) is not ProjectPhase62AnalysisBundle:
        raise TypeError("Phase-62 inspection requires an exact analysis bundle.")
    if (
        bundle.verification.status is not ProjectPhase62VerificationStatus.VERIFIED
        or bundle.verification.issues
        or bundle.verification.root is not bundle.root
    ):
        raise ValueError("Phase-62 inspection requires one VERIFIED bundle.")
    sections = _runtime_sections(bundle.root)
    return ProjectPhase62Inspection(
        analysis_bundle=bundle,
        summary=_inspection_summary(bundle, sections),
        verification=bundle.verification,
        root=bundle.root,
        base_verification=bundle.verification.base_verification,
        combined_reverse_uses=bundle.combined_reverse_uses,
        combined_topological_order=bundle.combined_topological_order,
        nulling_provenance=bundle.nulling_provenance,
        fact_locality_index=bundle.fact_localities,
        multifact_alignment_index=bundle.multifact_alignments,
        **cast(dict[str, object], sections),  # pyright: ignore[reportArgumentType]
    )


def build_project_phase62_inspection(
    bundle: ProjectPhase62AnalysisBundle,
) -> ProjectPhase62InspectionProduct:
    """Observe one exact VERIFIED Phase-62 bundle without rerunning producers."""

    return ProjectPhase62InspectionProduct(
        inspection=_derive_project_phase62_inspection(bundle)
    )


def serialize_project_phase62_inspection(
    inspection: ProjectPhase62Inspection,
) -> bytes:
    if type(inspection) is not ProjectPhase62Inspection:
        raise TypeError("Canonical serialization requires an exact inspection.")
    document = _project_phase62_document(inspection)
    outcome = evaluate_project_phase62_document(document)
    if (
        outcome.status is not ProjectPhase62PureStatus.OK
        or outcome.canonical_bytes is None
    ):
        raise ValueError(
            "Phase-62 inspection did not pass pure evaluation: "
            f"{outcome.status.value} at {outcome.record_position}:"
            f"{outcome.field_position}."
        )
    return outcome.canonical_bytes


def _require_inspection(inspection: ProjectPhase62Inspection) -> None:
    if type(inspection) is not ProjectPhase62Inspection:
        raise TypeError("Phase-62 queries require an exact inspection.")


def _require_ref(
    inspection: ProjectPhase62Inspection, ref: object, expected: type[object]
) -> None:
    if type(ref) is not expected:
        raise TypeError("Phase-62 queries require one exact typed ref.")
    typed = cast(
        ProjectIRPlanNodeRef
        | ProjectIROutputValueRef
        | ProjectIRInputSlotRef
        | ProjectIRUseRef,
        ref,
    )
    if typed.scope is not inspection.summary.scope:
        raise ValueError("Phase-62 query refs require the inspected snapshot scope.")


# ponytail: canonical tuple scans preserve winner-free authority; add indexes only
# after measured need, without replacing the retained tuples.
def query_project_phase62_relationships(
    inspection: ProjectPhase62Inspection,
    identity: ProjectRelationshipDeclarationIdentity,
) -> tuple[ProjectRelationshipSubject, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectRelationshipDeclarationIdentity:
        raise TypeError("Relationship queries require an exact typed identity.")
    return tuple(
        item
        for item in inspection.relationship_subjects
        if item.occurrence.identity is identity
    )


def query_project_phase62_directions(
    inspection: ProjectPhase62Inspection,
    identity: ProjectRelationshipDirectionIdentity,
) -> tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectRelationshipDirectionIdentity:
        raise TypeError("Direction queries require an exact typed identity.")
    return tuple(
        item
        for item in inspection.relationship_directions
        if item.direction is identity
    )


def query_project_phase62_join_uses(
    inspection: ProjectPhase62Inspection,
    identity: ProjectJoinUseIdentity,
) -> tuple[ProjectJoinUse, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectJoinUseIdentity:
        raise TypeError("JOIN-use queries require an exact typed identity.")
    return tuple(item for item in inspection.join_uses if item.identity is identity)


def query_project_phase62_binary_joins(
    inspection: ProjectPhase62Inspection,
    identity: ProjectIRBinaryJoinIdentity,
) -> tuple[ProjectIRBinaryJoinOccurrence, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectIRBinaryJoinIdentity:
        raise TypeError("Binary JOIN queries require an exact typed identity.")
    return tuple(item for item in inspection.binary_joins if item.identity is identity)


def query_project_phase62_nodes(
    inspection: ProjectPhase62Inspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(
        item
        for item in (
            *inspection.root.evaluation.project_plan.structural_stage.nodes,
            *inspection.root.join_regions.structural.nodes,
        )
        if item.ref == ref
    )


def query_project_phase62_outputs(
    inspection: ProjectPhase62Inspection,
    ref: ProjectIROutputValueRef,
) -> tuple[ProjectIROutputValueOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIROutputValueRef)
    return tuple(
        item
        for item in (
            *inspection.root.evaluation.project_plan.structural_stage.outputs,
            *inspection.root.join_regions.structural.outputs,
        )
        if item.ref == ref
    )


def query_project_phase62_input_slots(
    inspection: ProjectPhase62Inspection,
    ref: ProjectIRInputSlotRef,
) -> tuple[ProjectIRInputSlotOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRInputSlotRef)
    return tuple(
        item
        for item in (
            *inspection.root.evaluation.project_plan.structural_stage.input_slots,
            *inspection.join_input_slots,
        )
        if item.ref == ref
    )


def query_project_phase62_uses(
    inspection: ProjectPhase62Inspection,
    ref: ProjectIRUseRef,
) -> tuple[ProjectPhase62CombinedUse, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRUseRef)
    return tuple(
        item
        for item in (
            *inspection.root.evaluation.project_plan.structural_stage.uses,
            *inspection.join_input_uses,
        )
        if item.ref == ref
    )


def query_project_phase62_nulling(
    inspection: ProjectPhase62Inspection,
    output: ProjectIROutputValueRef,
    field_position: int,
) -> tuple[ProjectPhase62NullingProvenanceEntry, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, output, ProjectIROutputValueRef)
    if type(field_position) is not int or field_position < 0:
        raise ValueError("Nulling queries require a non-negative field position.")
    return tuple(
        item
        for item in inspection.nulling_provenance
        if item.coordinate.output == output
        and item.coordinate.field_position == field_position
    )


def query_project_phase62_facts(
    inspection: ProjectPhase62Inspection,
    identity: ProjectAggregateFactIdentity,
) -> tuple[ProjectAggregateFactOccurrence, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectAggregateFactIdentity:
        raise TypeError("Fact queries require an exact typed identity.")
    if identity.aggregate_node.scope is not inspection.summary.scope:
        raise ValueError("Fact queries require the inspected snapshot scope.")
    return tuple(
        item for item in inspection.aggregate_facts if item.identity is identity
    )


def query_project_phase62_fact_localities(
    inspection: ProjectPhase62Inspection,
    identity: ProjectAggregateFactIdentity,
) -> tuple[ProjectAggregateFactLocality, ...]:
    facts = query_project_phase62_facts(inspection, identity)
    return tuple(
        locality
        for locality in inspection.fact_localities
        if any(locality.fact is fact for fact in facts)
    )


def query_project_phase62_alignments_involving(
    inspection: ProjectPhase62Inspection,
    locality: ProjectAggregateFactLocality,
) -> tuple[ProjectMultiFactAlignment, ...]:
    _require_inspection(inspection)
    if type(locality) not in {
        ProjectAggregateFactHomeLocality,
        ProjectAggregateFactJoinLocality,
    } or not any(locality is retained for retained in inspection.fact_localities):
        raise ValueError("Alignment queries require one exact retained locality.")
    return tuple(
        item
        for item in inspection.alignments
        if item.left is locality or item.right is locality
    )


def query_project_phase62_alignment_bucket(
    inspection: ProjectPhase62Inspection,
    left: ProjectAggregateFactLocality,
    right: ProjectAggregateFactLocality,
) -> tuple[ProjectMultiFactAlignment, ...]:
    _require_inspection(inspection)
    if left is right or any(
        type(item)
        not in {ProjectAggregateFactHomeLocality, ProjectAggregateFactJoinLocality}
        or not any(item is retained for retained in inspection.fact_localities)
        for item in (left, right)
    ):
        raise ValueError("Pair queries require two exact retained localities.")
    return tuple(
        item
        for item in inspection.alignments
        if (item.left is left and item.right is right)
        or (item.left is right and item.right is left)
    )


def query_project_phase62_common_grains(
    inspection: ProjectPhase62Inspection,
    alignment: ProjectMultiFactAlignment,
) -> tuple[ProjectCommonGrainResult, ...]:
    _require_inspection(inspection)
    if type(alignment) is not ProjectMultiFactAlignment or not any(
        alignment is retained for retained in inspection.alignments
    ):
        raise ValueError("Common-grain queries require one exact alignment.")
    return (alignment.common_grain,)


def query_project_phase62_chasms_containing(
    inspection: ProjectPhase62Inspection,
    locality: ProjectAggregateFactLocality,
) -> tuple[ProjectFactChasmCandidate, ...]:
    _require_inspection(inspection)
    if type(locality) not in {
        ProjectAggregateFactHomeLocality,
        ProjectAggregateFactJoinLocality,
    } or not any(locality is retained for retained in inspection.fact_localities):
        raise ValueError("Chasm queries require one exact retained locality.")
    return tuple(
        item
        for item in inspection.chasms
        if any(locality is participant for participant in item.localities)
    )


def query_project_phase62_non_concrete_join_uses(
    inspection: ProjectPhase62Inspection,
) -> tuple[ProjectNonConcreteJoinUse, ...]:
    _require_inspection(inspection)
    return tuple(
        item for item in inspection.join_uses if type(item) is ProjectNonConcreteJoinUse
    )


def query_project_phase62_non_concrete_join_regions(
    inspection: ProjectPhase62Inspection,
) -> tuple[ProjectIRNonConcreteJoinRegion, ...]:
    _require_inspection(inspection)
    return inspection.non_concrete_join_regions


def query_project_phase62_non_concrete_multifact_regions(
    inspection: ProjectPhase62Inspection,
) -> tuple[ProjectMultiFactNonConcreteRegionSubject, ...]:
    _require_inspection(inspection)
    return inspection.non_concrete_multifact_regions


def _position(values: tuple[object, ...], subject: object, label: str) -> int:
    matches = tuple(position for position, item in enumerate(values) if item is subject)
    if len(matches) != 1:
        raise ValueError(f"Portable projection requires one exact {label}.")
    return matches[0]


def _ref(
    domain: ProjectPhase62PortableRefDomain, position: int
) -> ProjectPhase62PortableRef:
    return ProjectPhase62PortableRef(domain=domain, position=position)


def _section_ref(
    domain: ProjectPhase62PortableRefDomain,
    values: tuple[object, ...],
    subject: object,
    label: str,
) -> ProjectPhase62PortableRef:
    return _ref(domain, _position(values, subject, label))


def _runtime_ref(value: object) -> ProjectPhase62PortableRef:
    if type(value) is ProjectIRPlanNodeRef:
        domain = ProjectPhase62PortableRefDomain.PLAN_NODE
    elif type(value) is ProjectIROutputValueRef:
        domain = ProjectPhase62PortableRefDomain.OUTPUT_VALUE
    elif type(value) is ProjectIRInputSlotRef:
        domain = ProjectPhase62PortableRefDomain.INPUT_SLOT
    elif type(value) is ProjectIRUseRef:
        domain = ProjectPhase62PortableRefDomain.USE
    else:
        raise TypeError("Portable projection requires one typed Project IR ref.")
    return _ref(domain, value.position)


def _optional_ref(value: ProjectPhase62PortableRef | None) -> ProjectPhase62PureValue:
    return (
        PROJECT_PHASE62_PURE_ABSENT
        if value is None
        else project_phase62_pure_ref(value)
    )


def _optional_enumeration(value: str | None) -> ProjectPhase62PureValue:
    return (
        PROJECT_PHASE62_PURE_ABSENT
        if value is None
        else project_phase62_pure_enumeration(value)
    )


def _record(
    records: list[ProjectPhase62PureRecord],
    kind: ProjectPhase62RecordKind,
    *fields: tuple[str, ProjectPhase62PureValue],
) -> None:
    records.append(
        ProjectPhase62PureRecord(
            kind=kind,
            fields=tuple(
                ProjectPhase62PureField(key=key, value=value) for key, value in fields
            ),
        )
    )


def _owner_fields(
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[tuple[str, ProjectPhase62PureValue], ...]:
    nominal = identity.identity
    return (
        ("owner_module", project_phase62_pure_text(nominal.module_path)),
        (
            "owner_module_position",
            project_phase62_pure_integer(identity.module_position),
        ),
        (
            "owner_namespace",
            project_phase62_pure_enumeration(nominal.namespace.value),
        ),
        (
            "owner_kind",
            project_phase62_pure_enumeration(nominal.declaration_kind.value),
        ),
        ("owner_name", project_phase62_pure_text(nominal.declared_name)),
        (
            "owner_declaration_position",
            project_phase62_pure_integer(identity.declaration_position),
        ),
    )


def _traversal_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    bindings = cast(tuple[object, ...], inspection.relation_bindings)
    join_uses = cast(tuple[object, ...], inspection.join_uses)
    path_steps = cast(tuple[object, ...], inspection.path_steps)
    relational = cast(
        tuple[object, ...],
        (*inspection.base_relational_outputs, *inspection.join_relational_outputs),
    )
    for binding in inspection.relation_bindings:
        output_ref = (
            None
            if binding.output is None
            else _section_ref(
                ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                relational,
                binding.output,
                "relational output",
            )
        )
        _record(
            records,
            ProjectPhase62RecordKind.BINDING,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.BINDING,
                        bindings,
                        binding,
                        "relation binding",
                    )
                ),
            ),
            *_owner_fields(binding.identity.owner),
            (
                "binding_position",
                project_phase62_pure_integer(binding.identity.binding_position),
            ),
            ("name", project_phase62_pure_text(binding.name)),
            ("relation_name", project_phase62_pure_text(binding.relation_name)),
            ("state", project_phase62_pure_enumeration(binding.state.value)),
            ("output", _optional_ref(output_ref)),
        )
    for use in inspection.join_uses:
        source_ref = (
            None
            if use.source_binding is None
            else _section_ref(
                ProjectPhase62PortableRefDomain.BINDING,
                bindings,
                use.source_binding,
                "source binding",
            )
        )
        state = (
            "concrete"
            if type(use) is ProjectConcreteJoinUse
            else cast(ProjectNonConcreteJoinUse, use).state.value
        )
        _record(
            records,
            ProjectPhase62RecordKind.JOIN_USE,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.JOIN_USE,
                        join_uses,
                        use,
                        "JOIN use",
                    )
                ),
            ),
            *_owner_fields(use.identity.owner),
            (
                "join_position",
                project_phase62_pure_integer(use.identity.join_position),
            ),
            ("kind", project_phase62_pure_enumeration(use.kind.value)),
            ("state", project_phase62_pure_enumeration(state)),
            (
                "reasons",
                project_phase62_pure_enumerations(
                    ()
                    if type(use) is ProjectConcreteJoinUse
                    else tuple(
                        item.kind.value
                        for item in cast(ProjectNonConcreteJoinUse, use).issues
                    )
                ),
            ),
            ("source_binding", _optional_ref(source_ref)),
            (
                "target_binding",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.BINDING,
                        bindings,
                        use.target_binding,
                        "target binding",
                    )
                ),
            ),
            (
                "steps",
                project_phase62_pure_refs(
                    ()
                    if use.path is None
                    else tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.TRAVERSAL_STEP,
                            path_steps,
                            step,
                            "path step",
                        )
                        for step in use.path.steps
                    )
                ),
            ),
        )
    directions = cast(tuple[object, ...], inspection.relationship_directions)
    for use in inspection.join_uses:
        if use.path is None:
            continue
        analysis = use.analysis if type(use) is ProjectConcreteJoinUse else None
        for step in use.path.steps:
            hop = None if analysis is None else analysis.hops[step.position]
            _record(
                records,
                ProjectPhase62RecordKind.TRAVERSAL_STEP,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.TRAVERSAL_STEP,
                            path_steps,
                            step,
                            "path step",
                        )
                    ),
                ),
                (
                    "join_use",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_USE,
                            join_uses,
                            use,
                            "JOIN use",
                        )
                    ),
                ),
                ("position", project_phase62_pure_integer(step.position)),
                (
                    "direction",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION,
                            directions,
                            step.guarantee,
                            "relationship direction",
                        )
                    ),
                ),
                (
                    "fanout",
                    _optional_enumeration(None if hop is None else hop.fanout.value),
                ),
                (
                    "inner_survival",
                    _optional_enumeration(
                        None if hop is None else hop.inner_survival.value
                    ),
                ),
                (
                    "left_nulling",
                    _optional_enumeration(
                        None if hop is None else hop.left_nulling.value
                    ),
                ),
            )


def _grain_factor_ref(
    inspection: ProjectPhase62Inspection,
    grain: ProjectIRProvidedIntrinsicGrain,
    identity: object,
) -> ProjectPhase62PortableRef:
    matches = tuple(
        position
        for position, factor in enumerate(grain.factors)
        if factor.identity is identity
    )
    if len(matches) != 1 or not any(grain is item for item in inspection.grains):
        raise ValueError("Contextual grain factor is outside retained authority.")
    grain_position = _position(
        cast(tuple[object, ...], inspection.grains), grain, "grain"
    )
    return _ref(
        ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
        sum(len(item.factors) for item in inspection.grains[:grain_position])
        + matches[0],
    )


def _project_topology(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    base = inspection.root.evaluation.project_plan.structural_stage
    nodes = (*base.nodes, *inspection.root.join_regions.structural.nodes)
    outputs = (*base.outputs, *inspection.root.join_regions.structural.outputs)
    slots = (*base.input_slots, *inspection.join_input_slots)
    uses = (*base.uses, *inspection.join_input_uses)
    for node in nodes:
        _record(
            records,
            ProjectPhase62RecordKind.PROJECT_NODE,
            ("ref", project_phase62_pure_ref(_runtime_ref(node.ref))),
        )
    for output in outputs:
        _record(
            records,
            ProjectPhase62RecordKind.PROJECT_OUTPUT,
            ("ref", project_phase62_pure_ref(_runtime_ref(output.ref))),
            ("producer", project_phase62_pure_ref(_runtime_ref(output.producer.ref))),
        )
    for slot in slots:
        _record(
            records,
            ProjectPhase62RecordKind.PROJECT_SLOT,
            ("ref", project_phase62_pure_ref(_runtime_ref(slot.ref))),
            ("consumer", project_phase62_pure_ref(_runtime_ref(slot.consumer.ref))),
            ("ordinal", project_phase62_pure_integer(slot.input_ordinal)),
        )
    for use in uses:
        _record(
            records,
            ProjectPhase62RecordKind.PROJECT_USE,
            ("ref", project_phase62_pure_ref(_runtime_ref(use.ref))),
            ("output", project_phase62_pure_ref(_runtime_ref(use.output.ref))),
            ("slot", project_phase62_pure_ref(_runtime_ref(use.slot.ref))),
        )


def _relationship_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    subjects = cast(tuple[object, ...], inspection.relationship_subjects)
    directions = cast(tuple[object, ...], inspection.relationship_directions)
    conditions = cast(tuple[object, ...], inspection.relationship_conditions)
    correspondences = cast(tuple[object, ...], inspection.correspondences)
    relational = cast(
        tuple[object, ...],
        (*inspection.base_relational_outputs, *inspection.join_relational_outputs),
    )
    for subject in inspection.relationship_subjects:
        occurrence = subject.occurrence
        identity = occurrence.identity
        _record(
            records,
            ProjectPhase62RecordKind.RELATIONSHIP,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONSHIP,
                        subjects,
                        subject,
                        "relationship subject",
                    )
                ),
            ),
            ("module_path", project_phase62_pure_text(identity.module.path)),
            ("module_position", project_phase62_pure_integer(identity.module_position)),
            (
                "declaration_position",
                project_phase62_pure_integer(identity.relationship_position),
            ),
            (
                "source_position",
                project_phase62_pure_integer(occurrence.relationship.span.line),
            ),
            ("name", project_phase62_pure_text(occurrence.name)),
        )
    for guarantee in inspection.relationship_directions:
        direction = guarantee.direction
        relationship = next(
            item
            for item in inspection.relationship_subjects
            if item.occurrence.identity is direction.declaration
        )
        _record(
            records,
            ProjectPhase62RecordKind.RELATIONSHIP_DIRECTION,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION,
                        directions,
                        guarantee,
                        "relationship direction",
                    )
                ),
            ),
            (
                "relationship",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONSHIP,
                        subjects,
                        relationship,
                        "relationship subject",
                    )
                ),
            ),
            (
                "source_endpoint",
                project_phase62_pure_integer(
                    direction.source.identity.endpoint_position
                ),
            ),
            (
                "target_endpoint",
                project_phase62_pure_integer(
                    direction.target.identity.endpoint_position
                ),
            ),
            (
                "source_role",
                project_phase62_pure_text(direction.source.authored_role),
            ),
            (
                "target_role",
                project_phase62_pure_text(direction.target.authored_role),
            ),
            (
                "source_relation",
                project_phase62_pure_text(direction.source.authored_relation_spelling),
            ),
            (
                "target_relation",
                project_phase62_pure_text(direction.target.authored_relation_spelling),
            ),
        )
    for condition in inspection.relationship_conditions:
        _record(
            records,
            ProjectPhase62RecordKind.CONDITION,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CONDITION,
                        conditions,
                        condition,
                        "relationship condition",
                    )
                ),
            ),
            (
                "relationship",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONSHIP,
                        subjects,
                        condition.relationship,
                        "relationship subject",
                    )
                ),
            ),
            (
                "correspondences",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.CORRESPONDENCE,
                            correspondences,
                            item,
                            "relationship correspondence",
                        )
                        for item in condition.correspondences
                    )
                ),
            ),
        )
    for correspondence in inspection.correspondences:
        condition = next(
            item
            for item in inspection.relationship_conditions
            if any(correspondence is retained for retained in item.correspondences)
        )
        _record(
            records,
            ProjectPhase62RecordKind.CORRESPONDENCE,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CORRESPONDENCE,
                        correspondences,
                        correspondence,
                        "relationship correspondence",
                    )
                ),
            ),
            (
                "condition",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CONDITION,
                        conditions,
                        condition,
                        "relationship condition",
                    )
                ),
            ),
            (
                "position",
                project_phase62_pure_integer(correspondence.identity.conjunct_position),
            ),
            (
                "left_endpoint",
                project_phase62_pure_integer(
                    correspondence.endpoint_zero.endpoint.identity.endpoint_position
                ),
            ),
            (
                "right_endpoint",
                project_phase62_pure_integer(
                    correspondence.endpoint_one.endpoint.identity.endpoint_position
                ),
            ),
            (
                "left_field",
                project_phase62_pure_text(
                    correspondence.endpoint_zero.authored_field_spelling
                ),
            ),
            (
                "right_field",
                project_phase62_pure_text(
                    correspondence.endpoint_one.authored_field_spelling
                ),
            ),
        )
    guarantees = cast(tuple[object, ...], inspection.match_guarantees)
    for guarantee in inspection.match_guarantees:
        _record(
            records,
            ProjectPhase62RecordKind.MATCH_GUARANTEE,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.MATCH_GUARANTEE,
                        guarantees,
                        guarantee,
                        "match guarantee",
                    )
                ),
            ),
            (
                "direction",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION,
                        directions,
                        guarantee,
                        "relationship direction",
                    )
                ),
            ),
            (
                "source_output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational,
                        guarantee.source_output,
                        "relational output",
                    )
                ),
            ),
            (
                "target_output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational,
                        guarantee.target_output,
                        "relational output",
                    )
                ),
            ),
            ("minimum", project_phase62_pure_enumeration(guarantee.minimum.value)),
            ("maximum", project_phase62_pure_enumeration(guarantee.maximum.value)),
        )


def _relational_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    relational = (
        *inspection.base_relational_outputs,
        *inspection.join_relational_outputs,
    )
    relational_objects = cast(tuple[object, ...], relational)
    fields = cast(tuple[object, ...], inspection.relational_fields)
    classes = cast(tuple[object, ...], inspection.value_classes)
    keys = cast(tuple[object, ...], inspection.candidate_keys)
    fds = cast(tuple[object, ...], inspection.value_fds)
    grains = cast(tuple[object, ...], inspection.grains)
    for output in relational:
        _record(
            records,
            ProjectPhase62RecordKind.RELATIONAL_OUTPUT,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        output,
                        "relational output",
                    )
                ),
            ),
            (
                "runtime_output",
                project_phase62_pure_ref(_runtime_ref(output.output.occurrence.ref)),
            ),
            (
                "kind",
                project_phase62_pure_enumeration(
                    "base"
                    if any(
                        output is retained
                        for retained in inspection.base_relational_outputs
                    )
                    else "join"
                ),
            ),
            (
                "fields",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.RELATIONAL_FIELD,
                            fields,
                            item,
                            "relational field",
                        )
                        for item in output.fields
                    )
                ),
            ),
            (
                "classes",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.VALUE_CLASS,
                            classes,
                            item,
                            "value class",
                        )
                        for item in output.value_classes
                    )
                ),
            ),
            (
                "keys",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.CANDIDATE_KEY,
                            keys,
                            item,
                            "candidate key",
                        )
                        for item in output.keys
                    )
                ),
            ),
            (
                "fds",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.VALUE_FD,
                            fds,
                            item,
                            "value FD",
                        )
                        for item in output.fd_index.facts
                    )
                ),
            ),
            (
                "grain",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.GRAIN,
                        grains,
                        output.grain,
                        "grain",
                    )
                ),
            ),
        )
    for item in inspection.relational_fields:
        _record(
            records,
            ProjectPhase62RecordKind.RELATIONAL_FIELD,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_FIELD,
                        fields,
                        item,
                        "relational field",
                    )
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        next(
                            output
                            for output in relational
                            if output.output is item.output
                        ),
                        "relational output",
                    )
                ),
            ),
            ("position", project_phase62_pure_integer(item.field_position)),
            ("name", project_phase62_pure_text(item.evidence.name)),
            (
                "nullability",
                project_phase62_pure_enumeration(item.effective_nullability.value),
            ),
        )
    for item in inspection.value_classes:
        owner = next(output for output in relational if output.output is item.output)
        _record(
            records,
            ProjectPhase62RecordKind.VALUE_CLASS,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.VALUE_CLASS,
                        classes,
                        item,
                        "value class",
                    )
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        owner,
                        "relational output",
                    )
                ),
            ),
            (
                "members",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.RELATIONAL_FIELD,
                            fields,
                            member,
                            "relational field",
                        )
                        for member in item.members
                    )
                ),
            ),
        )
    for item in inspection.candidate_keys:
        owner = next(output for output in relational if output.output is item.output)
        _record(
            records,
            ProjectPhase62RecordKind.CANDIDATE_KEY,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CANDIDATE_KEY,
                        keys,
                        item,
                        "candidate key",
                    )
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        owner,
                        "relational output",
                    )
                ),
            ),
            (
                "determinants",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.VALUE_CLASS,
                            classes,
                            value_class,
                            "value class",
                        )
                        for value_class in item.determinants
                    )
                ),
            ),
            ("strength", project_phase62_pure_enumeration(item.strength.value)),
        )
    for item in inspection.value_fds:
        owner = next(output for output in relational if output.output is item.output)
        _record(
            records,
            ProjectPhase62RecordKind.VALUE_FD,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.VALUE_FD,
                        fds,
                        item,
                        "value FD",
                    )
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        owner,
                        "relational output",
                    )
                ),
            ),
            (
                "determinants",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.VALUE_CLASS,
                            classes,
                            value_class,
                            "value class",
                        )
                        for value_class in item.determinants
                    )
                ),
            ),
            (
                "dependents",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.VALUE_CLASS,
                            classes,
                            value_class,
                            "value class",
                        )
                        for value_class in item.dependents
                    )
                ),
            ),
            ("strength", project_phase62_pure_enumeration(item.strength.value)),
        )
    factor_position = 0
    dependency_position = 0
    for grain in inspection.grains:
        grain_ref = _section_ref(
            ProjectPhase62PortableRefDomain.GRAIN,
            grains,
            grain,
            "grain",
        )
        factor_refs = tuple(
            _ref(
                ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
                factor_position + position,
            )
            for position in range(len(grain.factors))
        )
        dependency_refs = tuple(
            _ref(
                ProjectPhase62PortableRefDomain.GRAIN_DEPENDENCY,
                dependency_position + position,
            )
            for position in range(len(grain.dependencies))
        )
        owner = next(output for output in relational if output.grain is grain)
        _record(
            records,
            ProjectPhase62RecordKind.GRAIN,
            ("ref", project_phase62_pure_ref(grain_ref)),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational_objects,
                        owner,
                        "relational output",
                    )
                ),
            ),
            ("state", project_phase62_pure_enumeration(grain.state.value)),
            ("factors", project_phase62_pure_refs(factor_refs)),
            (
                "active",
                project_phase62_pure_refs(
                    tuple(
                        _grain_factor_ref(inspection, grain, identity)
                        for identity in grain.active
                    )
                ),
            ),
            ("dependencies", project_phase62_pure_refs(dependency_refs)),
        )
        factor_position += len(grain.factors)
        dependency_position += len(grain.dependencies)
    factor_position = 0
    for grain in inspection.grains:
        grain_ref = _section_ref(
            ProjectPhase62PortableRefDomain.GRAIN,
            grains,
            grain,
            "grain",
        )
        for factor in grain.factors:
            identity = factor.identity
            if type(identity) is ProjectJoinGrainFactorIdentity:
                base = identity.base
            else:
                base = cast(ProjectBaseGrainFactorIdentity, identity)
            owner = base.owner
            nominal = owner.identity
            operator = (
                base.operator
                if type(base) is ProjectGroupedGrainFactorIdentity
                else None
            )
            _record(
                records,
                ProjectPhase62RecordKind.GRAIN_FACTOR,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _ref(
                            ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
                            factor_position,
                        )
                    ),
                ),
                ("grain", project_phase62_pure_ref(grain_ref)),
                ("kind", project_phase62_pure_enumeration(identity.kind.value)),
                ("owner_module", project_phase62_pure_text(nominal.module_path)),
                (
                    "owner_module_position",
                    project_phase62_pure_integer(owner.module_position),
                ),
                (
                    "owner_declaration_position",
                    project_phase62_pure_integer(owner.declaration_position),
                ),
                ("owner_name", project_phase62_pure_text(nominal.declared_name)),
                (
                    "operator",
                    _optional_ref(None if operator is None else _runtime_ref(operator)),
                ),
                (
                    "introduction_use",
                    _optional_ref(
                        None
                        if type(identity) is not ProjectJoinGrainFactorIdentity
                        else _runtime_ref(identity.introduction_use)
                    ),
                ),
                (
                    "nulling",
                    project_phase62_pure_refs(
                        ()
                        if type(identity) is not ProjectJoinGrainFactorIdentity
                        else tuple(
                            _runtime_ref(item) for item in identity.nulling_joins
                        )
                    ),
                ),
            )
            factor_position += 1
    dependency_position = 0
    for grain in inspection.grains:
        grain_ref = _section_ref(
            ProjectPhase62PortableRefDomain.GRAIN,
            grains,
            grain,
            "grain",
        )
        for dependency in grain.dependencies:
            _record(
                records,
                ProjectPhase62RecordKind.GRAIN_DEPENDENCY,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _ref(
                            ProjectPhase62PortableRefDomain.GRAIN_DEPENDENCY,
                            dependency_position,
                        )
                    ),
                ),
                ("grain", project_phase62_pure_ref(grain_ref)),
                (
                    "determinants",
                    project_phase62_pure_refs(
                        tuple(
                            _grain_factor_ref(inspection, grain, identity)
                            for identity in dependency.determinants
                        )
                    ),
                ),
                (
                    "dependents",
                    project_phase62_pure_refs(
                        tuple(
                            _grain_factor_ref(inspection, grain, identity)
                            for identity in dependency.dependents
                        )
                    ),
                ),
            )
            dependency_position += 1


def _join_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    regions = inspection.root.join_regions.regions
    region_objects = cast(tuple[object, ...], regions)
    joins = cast(tuple[object, ...], inspection.binary_joins)
    join_uses = cast(tuple[object, ...], inspection.join_uses)
    relational = cast(
        tuple[object, ...],
        (*inspection.base_relational_outputs, *inspection.join_relational_outputs),
    )
    matches = cast(tuple[object, ...], inspection.match_field_pairs)
    joined_fields = cast(tuple[object, ...], inspection.joined_fields)
    for region in regions:
        if type(region) is ProjectIRConcreteJoinRegion:
            region_state = "concrete"
            region_joins = region.joins
            blockers: tuple[ProjectNonConcreteJoinUse, ...] = ()
        else:
            non_concrete = cast(ProjectIRNonConcreteJoinRegion, region)
            region_state = non_concrete.state.value
            region_joins = ()
            blockers = non_concrete.blockers
        _record(
            records,
            ProjectPhase62RecordKind.JOIN_REGION,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.JOIN_REGION,
                        region_objects,
                        region,
                        "JOIN region",
                    )
                ),
            ),
            (
                "state",
                project_phase62_pure_enumeration(region_state),
            ),
            (
                "joins",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.BINARY_JOIN,
                            joins,
                            join,
                            "binary JOIN",
                        )
                        for join in region_joins
                    )
                ),
            ),
            (
                "blockers",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_USE,
                            join_uses,
                            blocker,
                            "JOIN-use blocker",
                        )
                        for blocker in blockers
                    )
                ),
            ),
        )
    for join in inspection.binary_joins:
        region = next(
            item
            for item in inspection.concrete_join_regions
            if any(join is retained for retained in item.joins)
        )
        output = next(
            item
            for item in inspection.join_relational_outputs
            if item.output is join.output
        )
        left = next(
            item
            for item in (
                *inspection.base_relational_outputs,
                *inspection.join_relational_outputs,
            )
            if item is join.left_input
        )
        right = next(
            item
            for item in (
                *inspection.base_relational_outputs,
                *inspection.join_relational_outputs,
            )
            if item is join.right_input
        )
        properties = next(
            item for item in inspection.join_output_properties if item.join is join
        )
        if type(properties.null_extension) is ProjectIRProvidedNullExtension:
            null_property = "provided"
        elif type(properties.null_extension) is ProjectIRJoinUnavailableProperty:
            null_property = properties.null_extension.availability.value
        else:
            raise TypeError("JOIN nulling property must be one closed runtime type.")
        _record(
            records,
            ProjectPhase62RecordKind.BINARY_JOIN,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.BINARY_JOIN,
                        joins,
                        join,
                        "binary JOIN",
                    )
                ),
            ),
            (
                "region",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.JOIN_REGION,
                        region_objects,
                        region,
                        "JOIN region",
                    )
                ),
            ),
            (
                "join_use",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.JOIN_USE,
                        join_uses,
                        join.use,
                        "JOIN use",
                    )
                ),
            ),
            (
                "path_position",
                project_phase62_pure_integer(join.identity.path_step_position),
            ),
            ("node", project_phase62_pure_ref(_runtime_ref(join.node.ref))),
            (
                "left_output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational,
                        left,
                        "left relational output",
                    )
                ),
            ),
            (
                "right_output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational,
                        right,
                        "right relational output",
                    )
                ),
            ),
            (
                "slots",
                project_phase62_pure_refs(
                    tuple(_runtime_ref(item.ref) for item in join.input_slots)
                ),
            ),
            (
                "uses",
                project_phase62_pure_refs(
                    tuple(_runtime_ref(item.ref) for item in join.input_uses)
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                        relational,
                        output,
                        "JOIN relational output",
                    )
                ),
            ),
            (
                "matches",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_MATCH,
                            matches,
                            item,
                            "JOIN match",
                        )
                        for item in join.matches
                    )
                ),
            ),
            ("kind", project_phase62_pure_enumeration(join.kind.value)),
            ("fanout", project_phase62_pure_enumeration(join.fanout.value)),
            ("survival", project_phase62_pure_enumeration(join.survival.value)),
            (
                "null_extension",
                project_phase62_pure_enumeration(join.null_extension.value),
            ),
            (
                "barrier",
                project_phase62_pure_enumeration(join.outer_join_barrier.value),
            ),
            ("null_property", project_phase62_pure_enumeration(null_property)),
        )
    correspondence_objects = cast(tuple[object, ...], inspection.correspondences)
    for join in inspection.binary_joins:
        for position, item in enumerate(join.matches):
            _record(
                records,
                ProjectPhase62RecordKind.JOIN_MATCH,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_MATCH,
                            matches,
                            item,
                            "JOIN match",
                        )
                    ),
                ),
                (
                    "binary_join",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.BINARY_JOIN,
                            joins,
                            join,
                            "binary JOIN",
                        )
                    ),
                ),
                ("position", project_phase62_pure_integer(position)),
                (
                    "correspondence",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.CORRESPONDENCE,
                            correspondence_objects,
                            item.correspondence,
                            "relationship correspondence",
                        )
                    ),
                ),
                (
                    "left",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOINED_FIELD,
                            joined_fields,
                            item.left,
                            "joined field",
                        )
                    ),
                ),
                (
                    "right",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOINED_FIELD,
                            joined_fields,
                            item.right,
                            "joined field",
                        )
                    ),
                ),
            )
    for join in inspection.binary_joins:
        output = next(
            item
            for item in inspection.join_relational_outputs
            if item.output is join.output
        )
        for item in join.output.row_shape.fields:
            _record(
                records,
                ProjectPhase62RecordKind.JOINED_FIELD,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOINED_FIELD,
                            joined_fields,
                            item,
                            "joined field",
                        )
                    ),
                ),
                (
                    "binary_join",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.BINARY_JOIN,
                            joins,
                            join,
                            "binary JOIN",
                        )
                    ),
                ),
                (
                    "output",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
                            relational,
                            output,
                            "JOIN relational output",
                        )
                    ),
                ),
                ("position", project_phase62_pure_integer(item.field_position)),
                (
                    "introduction_use",
                    project_phase62_pure_ref(_runtime_ref(item.introduction_use.ref)),
                ),
                (
                    "nulling",
                    project_phase62_pure_refs(
                        tuple(_runtime_ref(ref) for ref in item.nulling_joins)
                    ),
                ),
                (
                    "nullability",
                    project_phase62_pure_enumeration(item.effective_nullability.value),
                ),
                ("name", project_phase62_pure_text(item.evidence.name)),
            )
    nulling = cast(tuple[object, ...], inspection.nulling_provenance)
    for entry in inspection.nulling_provenance:
        _record(
            records,
            ProjectPhase62RecordKind.NULLING,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.NULLING,
                        nulling,
                        entry,
                        "nulling entry",
                    )
                ),
            ),
            (
                "output",
                project_phase62_pure_ref(_runtime_ref(entry.coordinate.output)),
            ),
            (
                "field_position",
                project_phase62_pure_integer(entry.coordinate.field_position),
            ),
            (
                "joins",
                project_phase62_pure_refs(
                    tuple(_runtime_ref(ref) for ref in entry.nulling_joins)
                ),
            ),
        )


def _candidate_entries(
    inspection: ProjectPhase62Inspection,
) -> tuple[
    tuple[
        ProjectActualGrainCandidate,
        ProjectIRConcreteJoinRegion | None,
        ProjectMultiFactAlignment | None,
        ProjectIRProvidedIntrinsicGrain,
    ],
    ...,
]:
    entries = (
        *(
            (
                candidate,
                None,
                alignment,
                cast(
                    ProjectIRProvidedIntrinsicGrain,
                    alignment.left.contextual_grain.authority,
                ),
            )
            for alignment in inspection.root.home_alignments
            for candidate in alignment.common_grain.actual_candidates
        ),
        *(
            (
                candidate,
                region.region,
                None,
                region.final_properties.relational.grain,
            )
            for region in inspection.concrete_multifact_regions
            for candidate in region.actual_candidates
        ),
    )
    if not _same_objects(
        tuple(item[0] for item in entries),
        cast(tuple[object, ...], inspection.actual_grain_candidates),
    ):
        raise ValueError("Actual candidates must retain exact owner order.")
    return entries


def _candidate_ref(
    entries: tuple[
        tuple[
            ProjectActualGrainCandidate,
            ProjectIRConcreteJoinRegion | None,
            ProjectMultiFactAlignment | None,
            ProjectIRProvidedIntrinsicGrain,
        ],
        ...,
    ],
    candidate: ProjectActualGrainCandidate,
) -> ProjectPhase62PortableRef:
    matches = tuple(
        position
        for position, (item, _region, _alignment, _grain) in enumerate(entries)
        if item is candidate
    )
    if len(matches) != 1:
        raise ValueError("Common-grain candidate requires one exact owner.")
    return _ref(ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE, matches[0])


def _multifact_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    facts = cast(tuple[object, ...], inspection.aggregate_facts)
    localities = cast(tuple[object, ...], inspection.fact_localities)
    regions = cast(tuple[object, ...], inspection.root.join_regions.regions)
    joins = cast(tuple[object, ...], inspection.binary_joins)
    exposures = cast(tuple[object, ...], inspection.multiplicity_exposures)
    alignments = cast(tuple[object, ...], inspection.alignments)
    common_results = cast(tuple[object, ...], inspection.common_grain_results)
    chasms = cast(tuple[object, ...], inspection.chasms)
    for fact in inspection.aggregate_facts:
        _record(
            records,
            ProjectPhase62RecordKind.AGGREGATE_FACT,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.AGGREGATE_FACT,
                        facts,
                        fact,
                        "aggregate fact",
                    )
                ),
            ),
            (
                "aggregate_node",
                project_phase62_pure_ref(_runtime_ref(fact.identity.aggregate_node)),
            ),
            (
                "result_position",
                project_phase62_pure_integer(fact.identity.aggregate_result_position),
            ),
            (
                "selected_ordinal",
                project_phase62_pure_integer(fact.selected_output_ordinal),
            ),
            ("function", project_phase62_pure_text(fact.aggregate_result.function)),
            (
                "output_name",
                project_phase62_pure_text(fact.aggregate_result.output_name),
            ),
        )
    for locality in inspection.fact_localities:
        is_home = type(locality) is ProjectAggregateFactHomeLocality
        grain = cast(
            ProjectIRProvidedIntrinsicGrain, locality.contextual_grain.authority
        )
        if is_home:
            region_ref = None
            introduction_ref = None
            locality_exposures: tuple[ProjectFactMultiplicityExposure, ...] = ()
        else:
            join_locality = cast(ProjectAggregateFactJoinLocality, locality)
            region_ref = _section_ref(
                ProjectPhase62PortableRefDomain.JOIN_REGION,
                regions,
                join_locality.region,
                "JOIN region",
            )
            introduction_ref = _runtime_ref(join_locality.introduction_use.ref)
            locality_exposures = join_locality.multiplicity_exposures
        _record(
            records,
            ProjectPhase62RecordKind.FACT_LOCALITY,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.FACT_LOCALITY,
                        localities,
                        locality,
                        "fact locality",
                    )
                ),
            ),
            (
                "fact",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.AGGREGATE_FACT,
                        facts,
                        locality.fact,
                        "aggregate fact",
                    )
                ),
            ),
            (
                "kind",
                project_phase62_pure_enumeration("home" if is_home else "join"),
            ),
            ("introduction_use", _optional_ref(introduction_ref)),
            ("region", _optional_ref(region_ref)),
            (
                "factors",
                project_phase62_pure_refs(
                    tuple(
                        _grain_factor_ref(inspection, grain, identity)
                        for identity in locality.contextual_grain.factors
                    )
                ),
            ),
            (
                "exposures",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.MULTIPLICITY_EXPOSURE,
                            exposures,
                            exposure,
                            "multiplicity exposure",
                        )
                        for exposure in locality_exposures
                    )
                ),
            ),
        )
    for locality in inspection.join_localities:
        grain = locality.final_region_properties.relational.grain
        locality_ref = _section_ref(
            ProjectPhase62PortableRefDomain.FACT_LOCALITY,
            localities,
            locality,
            "fact locality",
        )
        for exposure in locality.multiplicity_exposures:
            _record(
                records,
                ProjectPhase62RecordKind.MULTIPLICITY_EXPOSURE,
                (
                    "ref",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.MULTIPLICITY_EXPOSURE,
                            exposures,
                            exposure,
                            "multiplicity exposure",
                        )
                    ),
                ),
                ("locality", project_phase62_pure_ref(locality_ref)),
                (
                    "join",
                    project_phase62_pure_ref(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.BINARY_JOIN,
                            joins,
                            exposure.join,
                            "binary JOIN",
                        )
                    ),
                ),
                (
                    "factors",
                    project_phase62_pure_refs(
                        tuple(
                            _grain_factor_ref(inspection, grain, identity)
                            for identity in exposure.factor_additions
                        )
                    ),
                ),
            )
    entries = _candidate_entries(inspection)
    for position, (candidate, region, home_alignment, grain) in enumerate(entries):
        _record(
            records,
            ProjectPhase62RecordKind.ACTUAL_GRAIN_CANDIDATE,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(
                        ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE,
                        position,
                    )
                ),
            ),
            (
                "region",
                _optional_ref(
                    None
                    if region is None
                    else _section_ref(
                        ProjectPhase62PortableRefDomain.JOIN_REGION,
                        regions,
                        region,
                        "JOIN region",
                    )
                ),
            ),
            (
                "home_alignment",
                _optional_ref(
                    None
                    if home_alignment is None
                    else _section_ref(
                        ProjectPhase62PortableRefDomain.ALIGNMENT,
                        alignments,
                        home_alignment,
                        "home alignment",
                    )
                ),
            ),
            (
                "factors",
                project_phase62_pure_refs(
                    tuple(
                        _grain_factor_ref(inspection, grain, identity)
                        for identity in candidate.factors.factors
                    )
                ),
            ),
            (
                "authority_kinds",
                project_phase62_pure_enumerations(
                    tuple(item.kind.value for item in candidate.authorities)
                ),
            ),
        )
    for alignment in inspection.alignments:
        result = alignment.common_grain
        _record(
            records,
            ProjectPhase62RecordKind.COMMON_GRAIN,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.COMMON_GRAIN,
                        common_results,
                        result,
                        "common-grain result",
                    )
                ),
            ),
            ("status", project_phase62_pure_enumeration(result.status.value)),
            (
                "actual",
                project_phase62_pure_refs(
                    tuple(
                        _candidate_ref(entries, item)
                        for item in result.actual_candidates
                    )
                ),
            ),
            (
                "common",
                project_phase62_pure_refs(
                    tuple(
                        _candidate_ref(entries, item.candidate)
                        for item in result.common_candidates
                    )
                ),
            ),
            (
                "retained",
                project_phase62_pure_refs(
                    tuple(
                        _candidate_ref(entries, item.candidate)
                        for item in result.candidates
                    )
                ),
            ),
        )
    for alignment in inspection.alignments:
        _record(
            records,
            ProjectPhase62RecordKind.ALIGNMENT,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.ALIGNMENT,
                        alignments,
                        alignment,
                        "alignment",
                    )
                ),
            ),
            (
                "left",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.FACT_LOCALITY,
                        localities,
                        alignment.left,
                        "left locality",
                    )
                ),
            ),
            (
                "right",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.FACT_LOCALITY,
                        localities,
                        alignment.right,
                        "right locality",
                    )
                ),
            ),
            (
                "structural",
                project_phase62_pure_enumeration(alignment.structural.value),
            ),
            (
                "risks",
                project_phase62_pure_enumerations(
                    tuple(item.value for item in alignment.multiplicity_risks)
                ),
            ),
            (
                "requirements",
                project_phase62_pure_enumerations(
                    tuple(item.value for item in alignment.requirements)
                ),
            ),
            (
                "common",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.COMMON_GRAIN,
                        common_results,
                        alignment.common_grain,
                        "common-grain result",
                    )
                ),
            ),
            (
                "chasms",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.CHASM,
                            chasms,
                            item,
                            "chasm",
                        )
                        for item in alignment.chasms
                    )
                ),
            ),
        )
    for chasm in inspection.chasms:
        _record(
            records,
            ProjectPhase62RecordKind.CHASM,
            (
                "ref",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CHASM,
                        chasms,
                        chasm,
                        "chasm",
                    )
                ),
            ),
            (
                "common",
                project_phase62_pure_ref(_candidate_ref(entries, chasm.common_grain)),
            ),
            (
                "participants",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.FACT_LOCALITY,
                            localities,
                            item,
                            "chasm locality",
                        )
                        for item in chasm.localities
                    )
                ),
            ),
            (
                "joins",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.BINARY_JOIN,
                            joins,
                            item,
                            "chasm introduction JOIN",
                        )
                        for item in chasm.introduction_joins
                    )
                ),
            ),
        )
    non_concrete_uses = tuple(
        item for item in inspection.join_uses if type(item) is ProjectNonConcreteJoinUse
    )
    position = 0
    join_uses = cast(tuple[object, ...], inspection.join_uses)
    for use in non_concrete_uses:
        _record(
            records,
            ProjectPhase62RecordKind.NON_CONCRETE,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.NON_CONCRETE, position)
                ),
            ),
            ("kind", project_phase62_pure_enumeration("join_use")),
            ("state", project_phase62_pure_enumeration(use.state.value)),
            (
                "reasons",
                project_phase62_pure_enumerations(
                    tuple(item.kind.value for item in use.issues)
                ),
            ),
            (
                "join_uses",
                project_phase62_pure_refs(
                    (
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_USE,
                            join_uses,
                            use,
                            "non-concrete JOIN use",
                        ),
                    )
                ),
            ),
            ("facts", PROJECT_PHASE62_PURE_ABSENT),
        )
        position += 1
    for region in inspection.non_concrete_join_regions:
        _record(
            records,
            ProjectPhase62RecordKind.NON_CONCRETE,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.NON_CONCRETE, position)
                ),
            ),
            ("kind", project_phase62_pure_enumeration("join_region")),
            ("state", project_phase62_pure_enumeration(region.state.value)),
            (
                "reasons",
                project_phase62_pure_enumerations(
                    tuple(
                        issue.kind.value
                        for blocker in region.blockers
                        for issue in blocker.issues
                    )
                ),
            ),
            (
                "join_uses",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_USE,
                            join_uses,
                            item,
                            "JOIN-region blocker",
                        )
                        for item in region.blockers
                    )
                ),
            ),
            ("facts", PROJECT_PHASE62_PURE_ABSENT),
        )
        position += 1
    for subject in inspection.non_concrete_multifact_regions:
        _record(
            records,
            ProjectPhase62RecordKind.NON_CONCRETE,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.NON_CONCRETE, position)
                ),
            ),
            ("kind", project_phase62_pure_enumeration("multifact_region")),
            ("state", project_phase62_pure_enumeration(subject.structural.value)),
            (
                "reasons",
                project_phase62_pure_enumerations(
                    tuple(
                        issue.kind.value
                        for blocker in subject.blockers
                        for issue in blocker.issues
                    )
                ),
            ),
            (
                "join_uses",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.JOIN_USE,
                            join_uses,
                            item,
                            "multi-fact blocker",
                        )
                        for item in subject.blockers
                    )
                ),
            ),
            (
                "facts",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.AGGREGATE_FACT,
                            facts,
                            item,
                            "identifiable aggregate fact",
                        )
                        for item in subject.identifiable_facts
                    )
                ),
            ),
        )
        position += 1


def _analysis_records(
    inspection: ProjectPhase62Inspection,
    records: list[ProjectPhase62PureRecord],
) -> None:
    position = 0
    for entry in inspection.combined_reverse_uses:
        _record(
            records,
            ProjectPhase62RecordKind.ANALYSIS_REVERSE_USE,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY, position)
                ),
            ),
            ("output", project_phase62_pure_ref(_runtime_ref(entry.output.ref))),
            (
                "uses",
                project_phase62_pure_refs(
                    tuple(_runtime_ref(use.ref) for use in entry.uses)
                ),
            ),
        )
        position += 1
    for topological_position, node in enumerate(inspection.combined_topological_order):
        _record(
            records,
            ProjectPhase62RecordKind.ANALYSIS_TOPOLOGICAL,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY, position)
                ),
            ),
            (
                "position",
                project_phase62_pure_integer(topological_position),
            ),
            ("node", project_phase62_pure_ref(_runtime_ref(node.ref))),
        )
        position += 1
    nulling = cast(tuple[object, ...], inspection.nulling_provenance)
    for entry in inspection.nulling_provenance:
        _record(
            records,
            ProjectPhase62RecordKind.ANALYSIS_NULLING,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY, position)
                ),
            ),
            (
                "nulling",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.NULLING,
                        nulling,
                        entry,
                        "nulling analysis entry",
                    )
                ),
            ),
        )
        position += 1
    facts = cast(tuple[object, ...], inspection.aggregate_facts)
    localities = cast(tuple[object, ...], inspection.fact_localities)
    for entry in inspection.fact_locality_index:
        _record(
            records,
            ProjectPhase62RecordKind.ANALYSIS_FACT_LOCALITY,
            (
                "ref",
                project_phase62_pure_ref(
                    _ref(ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY, position)
                ),
            ),
            (
                "fact",
                project_phase62_pure_ref(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.AGGREGATE_FACT,
                        facts,
                        entry.fact,
                        "aggregate fact",
                    )
                ),
            ),
            (
                "localities",
                project_phase62_pure_refs(
                    tuple(
                        _section_ref(
                            ProjectPhase62PortableRefDomain.FACT_LOCALITY,
                            localities,
                            locality,
                            "fact locality",
                        )
                        for locality in entry.localities
                    )
                ),
            ),
        )
        position += 1
    alignments = cast(tuple[object, ...], inspection.alignments)
    chasms = cast(tuple[object, ...], inspection.chasms)
    _record(
        records,
        ProjectPhase62RecordKind.ANALYSIS_ALIGNMENT,
        (
            "ref",
            project_phase62_pure_ref(
                _ref(ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY, position)
            ),
        ),
        (
            "alignments",
            project_phase62_pure_refs(
                tuple(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.ALIGNMENT,
                        alignments,
                        item,
                        "alignment",
                    )
                    for item in inspection.multifact_alignment_index.alignments
                )
            ),
        ),
        (
            "chasms",
            project_phase62_pure_refs(
                tuple(
                    _section_ref(
                        ProjectPhase62PortableRefDomain.CHASM,
                        chasms,
                        item,
                        "chasm",
                    )
                    for item in inspection.multifact_alignment_index.chasms
                )
            ),
        ),
    )


def _project_phase62_document(
    inspection: ProjectPhase62Inspection,
) -> ProjectPhase62PureDocument:
    if type(inspection) is not ProjectPhase62Inspection:
        raise TypeError("Portable projection requires an exact inspection.")
    records: list[ProjectPhase62PureRecord] = []
    _record(
        records,
        ProjectPhase62RecordKind.HEADER,
        ("format", project_phase62_pure_text(PROJECT_PHASE62_INSPECTION_FORMAT)),
        (
            "verification",
            project_phase62_pure_enumeration(inspection.verification.status.value),
        ),
        (
            "base_verification",
            project_phase62_pure_enumeration(inspection.base_verification.status.value),
        ),
    )
    _project_topology(inspection, records)
    _relationship_records(inspection, records)
    _traversal_records(inspection, records)
    _relational_records(inspection, records)
    _join_records(inspection, records)
    _multifact_records(inspection, records)
    _analysis_records(inspection, records)
    _record(records, ProjectPhase62RecordKind.END)
    names = tuple(kind.value for kind in ProjectPhase62RecordKind)
    counts = tuple(
        sum(record.kind is kind for record in records)
        + (1 if kind is ProjectPhase62RecordKind.SUMMARY else 0)
        for kind in ProjectPhase62RecordKind
    )
    records.insert(
        1,
        ProjectPhase62PureRecord(
            kind=ProjectPhase62RecordKind.SUMMARY,
            fields=(
                ProjectPhase62PureField(
                    key="names", value=project_phase62_pure_texts(names)
                ),
                ProjectPhase62PureField(
                    key="counts", value=project_phase62_pure_integers(counts)
                ),
            ),
        ),
    )
    return ProjectPhase62PureDocument(
        format_marker=PROJECT_PHASE62_INSPECTION_FORMAT,
        records=tuple(records),
    )
