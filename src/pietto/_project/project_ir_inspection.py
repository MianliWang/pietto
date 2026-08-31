"""Verified-only private Project IR inspection, queries, and pure projection."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRSnapshotScope,
    ProjectIRStructuralUseOccurrence,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
)
from pietto._project.project_ir_composition import ProjectIRCrossRelationEdge
from pietto._project.project_ir_construction import (
    ProjectIRNonConcreteSingleRelationFragment,
    ProjectIRSingleRelationFragment,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
    ProjectIRWindowOperatorEvaluationContext,
    ProjectIRWindowResultEvaluationContext,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorOccurrence,
    ProjectIRRowShapeCompatibility,
)
from pietto._project.project_ir_properties import (
    ProjectIRCurrentOutput,
    ProjectIREffectEvidence,
    ProjectIRProvidedBagMultiplicity,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRProvidedLocalGrainEvidence,
    ProjectIRProvidedOutputShape,
    ProjectIRProvidedProperty,
    ProjectIRProvidedRelationOrdering,
    ProjectIRRelationRowOutput,
    ProjectIRRequiredRowShape,
    ProjectIRScalarFieldOutput,
    ProjectIRStageRowShape,
    ProjectIRStageScalarFieldOutput,
    ProjectIRUnavailableProvidedProperty,
)
from pietto._project.project_ir_pure_boundary import (
    PROJECT_IR_INSPECTION_FORMAT,
    PROJECT_IR_PURE_ABSENT,
    ProjectIRPortableRef,
    ProjectIRPortableRefDomain,
    ProjectIRPureDocument,
    ProjectIRPureField,
    ProjectIRPureRecord,
    ProjectIRPureStatus,
    ProjectIRPureValue,
    evaluate_project_ir_document,
    project_ir_pure_enumeration,
    project_ir_pure_enumerations,
    project_ir_pure_integer,
    project_ir_pure_ref,
    project_ir_pure_refs,
    project_ir_pure_text,
    project_ir_pure_texts,
)
from pietto._project.project_ir_verification import (
    ProjectIRAnalysisBundle,
    ProjectIRReachabilityEntry,
    ProjectIRReverseUseEntry,
    ProjectIRRewriteReadiness,
    ProjectIRSemanticEquivalenceAssessment,
    ProjectIRVerificationResult,
    ProjectIRVerificationStatus,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRInspectionSummary:
    """Exact runtime snapshot and complete section counts."""

    scope: ProjectIRSnapshotScope = field(repr=False, compare=False, hash=False)
    fragment_count: int
    node_count: int
    output_count: int
    input_slot_count: int
    use_count: int
    cross_edge_count: int
    property_count: int
    compatibility_count: int
    effect_count: int
    evaluation_context_count: int

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Inspection summary requires an exact snapshot scope.")
        for value in (
            self.fragment_count,
            self.node_count,
            self.output_count,
            self.input_slot_count,
            self.use_count,
            self.cross_edge_count,
            self.property_count,
            self.compatibility_count,
            self.effect_count,
            self.evaluation_context_count,
        ):
            if type(value) is not int or value < 0:
                raise TypeError("Inspection summary counts must be non-negative.")


type ProjectIRInspectionEvaluationContext = (
    ProjectIRAggregateEvaluationContext
    | ProjectIRWindowOperatorEvaluationContext
    | ProjectIRWindowResultEvaluationContext
)
type ProjectIRRuntimeRef = (
    ProjectIRPlanNodeRef
    | ProjectIROutputValueRef
    | ProjectIRInputSlotRef
    | ProjectIRUseRef
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRInspection:
    """Complete read-only observation retaining exact runtime authorities."""

    analysis_bundle: ProjectIRAnalysisBundle = field(
        repr=False,
        compare=False,
        hash=False,
    )
    summary: ProjectIRInspectionSummary
    fragments: tuple[ProjectIRSingleRelationFragment, ...]
    nodes: tuple[ProjectIRPlanNodeOccurrence, ...]
    operators: tuple[ProjectIRLogicalOperatorOccurrence, ...]
    outputs: tuple[ProjectIRCurrentOutput, ...]
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    uses: tuple[ProjectIRStructuralUseOccurrence, ...]
    cross_relation_edges: tuple[ProjectIRCrossRelationEdge, ...]
    provided_properties: tuple[ProjectIRProvidedProperty, ...]
    required_properties: tuple[ProjectIRRequiredRowShape, ...]
    compatibilities: tuple[ProjectIRRowShapeCompatibility, ...]
    effects: tuple[ProjectIREffectEvidence, ...]
    aggregate_contexts: tuple[ProjectIRAggregateEvaluationContext, ...]
    window_operator_contexts: tuple[ProjectIRWindowOperatorEvaluationContext, ...]
    window_result_contexts: tuple[ProjectIRWindowResultEvaluationContext, ...]
    verification: ProjectIRVerificationResult
    reverse_uses: tuple[ProjectIRReverseUseEntry, ...]
    topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    reachability: tuple[ProjectIRReachabilityEntry, ...]
    equivalence_assessments: tuple[ProjectIRSemanticEquivalenceAssessment, ...]
    rewrite_readiness: tuple[ProjectIRRewriteReadiness, ...]

    def __post_init__(self) -> None:
        if type(self.analysis_bundle) is not ProjectIRAnalysisBundle:
            raise TypeError("Inspection requires an exact analysis bundle.")
        if (
            self.analysis_bundle.verification.status
            is not ProjectIRVerificationStatus.VERIFIED
            or self.analysis_bundle.verification.issues
            or self.verification is not self.analysis_bundle.verification
        ):
            raise ValueError("Inspection requires exact VERIFIED admission.")
        stage = self.analysis_bundle.stage
        plan = stage.project_plan
        expected_operators = tuple(
            operator
            for fragment in plan.fragments
            for operator in fragment.logical_stage.operators
        )
        expected_outputs = tuple(
            output
            for fragment in plan.fragments
            for output in fragment.property_stage.outputs
        )
        expected_provided = tuple(
            property_
            for fragment in plan.fragments
            for property_ in fragment.property_stage.provided
        )
        expected_required = tuple(
            edge.required_row_shape for edge in plan.cross_relation_edges
        )
        expected_compatibilities = tuple(
            edge.compatibility for edge in plan.cross_relation_edges
        )
        expected_effects = tuple(
            effect
            for fragment in plan.fragments
            for effect in fragment.property_stage.effects
        )
        exact = (
            (self.fragments, plan.fragments),
            (self.nodes, plan.structural_stage.nodes),
            (self.operators, expected_operators),
            (self.outputs, expected_outputs),
            (self.input_slots, plan.structural_stage.input_slots),
            (self.uses, plan.structural_stage.uses),
            (self.cross_relation_edges, plan.cross_relation_edges),
            (self.provided_properties, expected_provided),
            (self.required_properties, expected_required),
            (self.compatibilities, expected_compatibilities),
            (self.effects, expected_effects),
            (self.aggregate_contexts, stage.aggregate_contexts),
            (self.window_operator_contexts, stage.window_operator_contexts),
            (self.window_result_contexts, stage.window_result_contexts),
            (self.reverse_uses, self.analysis_bundle.reverse_uses),
            (self.topological_order, self.analysis_bundle.topological_order),
            (self.reachability, self.analysis_bundle.reachability),
            (
                self.equivalence_assessments,
                self.analysis_bundle.equivalence_assessments,
            ),
            (self.rewrite_readiness, self.analysis_bundle.rewrite_readiness),
        )
        if any(not _same_objects(actual, expected) for actual, expected in exact):
            raise ValueError("Inspection sections must retain exact canonical objects.")
        expected_summary = _inspection_summary(self.analysis_bundle)
        if (
            self.summary != expected_summary
            or self.summary.scope is not plan.structural_stage.scope
        ):
            raise ValueError("Inspection summary must retain exact Project counts.")

    @property
    def stage(self):
        return self.analysis_bundle.stage


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRInspectionProduct:
    """Inspection projected once through the single pure encoding authority."""

    inspection: ProjectIRInspection
    document: ProjectIRPureDocument = field(init=False)
    canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.inspection) is not ProjectIRInspection:
            raise TypeError("Inspection products require an exact inspection.")
        document = _project_ir_pure_document(self.inspection)
        object.__setattr__(self, "document", document)
        object.__setattr__(self, "canonical_bytes", _canonical_document_bytes(document))


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is expected_item
        for item, expected_item in zip(actual, expected, strict=True)
    )


def _inspection_summary(bundle: ProjectIRAnalysisBundle) -> ProjectIRInspectionSummary:
    stage = bundle.stage
    plan = stage.project_plan
    property_count = sum(
        len(fragment.property_stage.provided) for fragment in plan.fragments
    ) + len(plan.cross_relation_edges)
    return ProjectIRInspectionSummary(
        scope=plan.structural_stage.scope,
        fragment_count=len(plan.fragments),
        node_count=len(plan.structural_stage.nodes),
        output_count=len(plan.structural_stage.outputs),
        input_slot_count=len(plan.structural_stage.input_slots),
        use_count=len(plan.structural_stage.uses),
        cross_edge_count=len(plan.cross_relation_edges),
        property_count=property_count,
        compatibility_count=len(plan.cross_relation_edges),
        effect_count=sum(
            len(fragment.property_stage.effects) for fragment in plan.fragments
        ),
        evaluation_context_count=(
            len(stage.aggregate_contexts)
            + len(stage.window_operator_contexts)
            + len(stage.window_result_contexts)
        ),
    )


def _derive_project_ir_inspection(
    bundle: ProjectIRAnalysisBundle,
) -> ProjectIRInspection:
    if type(bundle) is not ProjectIRAnalysisBundle:
        raise TypeError("Project IR inspection requires an exact analysis bundle.")
    if (
        bundle.verification.status is not ProjectIRVerificationStatus.VERIFIED
        or bundle.verification.issues
    ):
        raise ValueError("Project IR inspection requires a VERIFIED analysis bundle.")
    stage = bundle.stage
    plan = stage.project_plan
    return ProjectIRInspection(
        analysis_bundle=bundle,
        summary=_inspection_summary(bundle),
        fragments=plan.fragments,
        nodes=plan.structural_stage.nodes,
        operators=tuple(
            operator
            for fragment in plan.fragments
            for operator in fragment.logical_stage.operators
        ),
        outputs=tuple(
            output
            for fragment in plan.fragments
            for output in fragment.property_stage.outputs
        ),
        input_slots=plan.structural_stage.input_slots,
        uses=plan.structural_stage.uses,
        cross_relation_edges=plan.cross_relation_edges,
        provided_properties=tuple(
            property_
            for fragment in plan.fragments
            for property_ in fragment.property_stage.provided
        ),
        required_properties=tuple(
            edge.required_row_shape for edge in plan.cross_relation_edges
        ),
        compatibilities=tuple(edge.compatibility for edge in plan.cross_relation_edges),
        effects=tuple(
            effect
            for fragment in plan.fragments
            for effect in fragment.property_stage.effects
        ),
        aggregate_contexts=stage.aggregate_contexts,
        window_operator_contexts=stage.window_operator_contexts,
        window_result_contexts=stage.window_result_contexts,
        verification=bundle.verification,
        reverse_uses=bundle.reverse_uses,
        topological_order=bundle.topological_order,
        reachability=bundle.reachability,
        equivalence_assessments=bundle.equivalence_assessments,
        rewrite_readiness=bundle.rewrite_readiness,
    )


def build_project_ir_inspection(
    bundle: ProjectIRAnalysisBundle,
) -> ProjectIRInspectionProduct:
    """Observe one fresh VERIFIED analysis bundle without mutation or allocation."""

    return ProjectIRInspectionProduct(inspection=_derive_project_ir_inspection(bundle))


def _canonical_document_bytes(document: ProjectIRPureDocument) -> bytes:
    outcome = evaluate_project_ir_document(document)
    if outcome.status is not ProjectIRPureStatus.OK or outcome.canonical_bytes is None:
        raise ValueError(
            "Authority-derived Project IR inspection must evaluate exactly: "
            f"{outcome.status.value} at {outcome.record_position}:"
            f"{outcome.field_position}."
        )
    return outcome.canonical_bytes


def serialize_project_ir_inspection(inspection: ProjectIRInspection) -> bytes:
    """Delegate the exact inspection through the one portable pure evaluator."""

    if type(inspection) is not ProjectIRInspection:
        raise TypeError("Canonical serialization requires an exact inspection.")
    return _canonical_document_bytes(_project_ir_pure_document(inspection))


def _require_inspection(inspection: ProjectIRInspection) -> None:
    if type(inspection) is not ProjectIRInspection:
        raise TypeError("Project IR queries require an exact inspection.")


def _require_ref(
    inspection: ProjectIRInspection,
    ref: ProjectIRRuntimeRef,
    ref_type: type[object],
) -> None:
    if type(ref) is not ref_type:
        raise TypeError("Project IR queries require an exact typed ref.")
    if ref.scope is not inspection.summary.scope:
        raise ValueError("Project IR query refs require the inspected snapshot scope.")


# ponytail: private inspection queries scan canonical tuples; add immutable indexes
# only after measurement, and keep their tuple sources as authority.
def query_project_ir_relations(
    inspection: ProjectIRInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRSingleRelationFragment, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectDeclarationOccurrenceIdentity:
        raise TypeError("Relation queries require an occurrence identity.")
    return tuple(
        fragment
        for fragment in inspection.fragments
        if fragment.subject.anchor.identity == identity
    )


def query_project_ir_nodes(
    inspection: ProjectIRInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(node for node in inspection.nodes if node.ref == ref)


def query_project_ir_outputs(
    inspection: ProjectIRInspection,
    ref: ProjectIROutputValueRef,
) -> tuple[ProjectIRCurrentOutput, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIROutputValueRef)
    return tuple(
        output for output in inspection.outputs if output.occurrence.ref == ref
    )


def query_project_ir_input_slots(
    inspection: ProjectIRInspection,
    ref: ProjectIRInputSlotRef,
) -> tuple[ProjectIRInputSlotOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRInputSlotRef)
    return tuple(slot for slot in inspection.input_slots if slot.ref == ref)


def query_project_ir_uses(
    inspection: ProjectIRInspection,
    ref: ProjectIRUseRef,
) -> tuple[ProjectIRStructuralUseOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRUseRef)
    return tuple(use for use in inspection.uses if use.ref == ref)


def query_project_ir_incoming_uses(
    inspection: ProjectIRInspection,
    node_ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRStructuralUseOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, node_ref, ProjectIRPlanNodeRef)
    return tuple(use for use in inspection.uses if use.slot.consumer.ref == node_ref)


def query_project_ir_outgoing_uses(
    inspection: ProjectIRInspection,
    node_ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRStructuralUseOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, node_ref, ProjectIRPlanNodeRef)
    return tuple(use for use in inspection.uses if use.output.producer.ref == node_ref)


def query_project_ir_cross_edges(
    inspection: ProjectIRInspection,
    use_ref: ProjectIRUseRef,
) -> tuple[ProjectIRCrossRelationEdge, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, use_ref, ProjectIRUseRef)
    return tuple(
        edge for edge in inspection.cross_relation_edges if edge.use.ref == use_ref
    )


def query_project_ir_properties(
    inspection: ProjectIRInspection,
    output_ref: ProjectIROutputValueRef,
) -> tuple[ProjectIRProvidedProperty, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, output_ref, ProjectIROutputValueRef)
    return tuple(
        property_
        for property_ in inspection.provided_properties
        if property_.output.occurrence.ref == output_ref
    )


def query_project_ir_effects(
    inspection: ProjectIRInspection,
    output_ref: ProjectIROutputValueRef,
) -> tuple[ProjectIREffectEvidence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, output_ref, ProjectIROutputValueRef)
    return tuple(
        effect
        for effect in inspection.effects
        if effect.output.occurrence.ref == output_ref
    )


def query_project_ir_evaluation_contexts(
    inspection: ProjectIRInspection,
    node_ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRInspectionEvaluationContext, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, node_ref, ProjectIRPlanNodeRef)
    return (
        *(
            context
            for context in inspection.aggregate_contexts
            if context.operator.node.ref == node_ref
        ),
        *(
            context
            for context in inspection.window_operator_contexts
            if context.operator.node.ref == node_ref
        ),
        *(
            context
            for context in inspection.window_result_contexts
            if context.operator_context.operator.node.ref == node_ref
        ),
    )


def query_project_ir_non_concrete(
    inspection: ProjectIRInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRNonConcreteSingleRelationFragment, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectDeclarationOccurrenceIdentity:
        raise TypeError("Why-not queries require a relation occurrence identity.")
    return tuple(
        fragment
        for fragment in inspection.fragments
        if type(fragment) is ProjectIRNonConcreteSingleRelationFragment
        and fragment.subject.anchor.identity == identity
    )


def query_project_ir_reachability(
    inspection: ProjectIRInspection,
    node_ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRReachabilityEntry, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, node_ref, ProjectIRPlanNodeRef)
    return tuple(
        entry for entry in inspection.reachability if entry.source.ref == node_ref
    )


def query_project_ir_equivalence(
    inspection: ProjectIRInspection,
    left: ProjectDeclarationOccurrenceIdentity,
    right: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRSemanticEquivalenceAssessment, ...]:
    _require_inspection(inspection)
    if (
        type(left) is not ProjectDeclarationOccurrenceIdentity
        or type(right) is not ProjectDeclarationOccurrenceIdentity
    ):
        raise TypeError("Equivalence queries require exact relation occurrences.")
    return tuple(
        assessment
        for assessment in inspection.equivalence_assessments
        if (
            assessment.left.subject.anchor.identity,
            assessment.right.subject.anchor.identity,
        )
        in {(left, right), (right, left)}
    )


def query_project_ir_rewrite_readiness(
    inspection: ProjectIRInspection,
    left: ProjectDeclarationOccurrenceIdentity,
    right: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRRewriteReadiness, ...]:
    assessments = query_project_ir_equivalence(inspection, left, right)
    return tuple(
        readiness
        for readiness in inspection.rewrite_readiness
        if any(readiness.assessment is assessment for assessment in assessments)
    )


def _portable_ref(ref: object) -> ProjectIRPortableRef:
    if type(ref) is ProjectIRPlanNodeRef:
        domain = ProjectIRPortableRefDomain.PLAN_NODE
    elif type(ref) is ProjectIROutputValueRef:
        domain = ProjectIRPortableRefDomain.OUTPUT_VALUE
    elif type(ref) is ProjectIRInputSlotRef:
        domain = ProjectIRPortableRefDomain.INPUT_SLOT
    elif type(ref) is ProjectIRUseRef:
        domain = ProjectIRPortableRefDomain.USE
    else:
        raise TypeError("Portable inspection requires a typed Project IR ref.")
    return ProjectIRPortableRef(domain=domain, position=ref.position)


def _optional_ref(ref: object | None) -> ProjectIRPureValue:
    return (
        PROJECT_IR_PURE_ABSENT
        if ref is None
        else project_ir_pure_ref(_portable_ref(ref))
    )


def _optional_text(value: str | None) -> ProjectIRPureValue:
    return PROJECT_IR_PURE_ABSENT if value is None else project_ir_pure_text(value)


def _optional_enumeration(value: str | None) -> ProjectIRPureValue:
    return (
        PROJECT_IR_PURE_ABSENT if value is None else project_ir_pure_enumeration(value)
    )


def _optional_integer(value: int | None) -> ProjectIRPureValue:
    return PROJECT_IR_PURE_ABSENT if value is None else project_ir_pure_integer(value)


def _pure_record(
    records: list[ProjectIRPureRecord],
    kind: str,
    *fields: tuple[str, ProjectIRPureValue],
) -> None:
    records.append(
        ProjectIRPureRecord(
            kind=kind,
            fields=tuple(
                ProjectIRPureField(key=key, value=value) for key, value in fields
            ),
        )
    )


def _fragment_position(
    inspection: ProjectIRInspection,
    fragment: ProjectIRSingleRelationFragment,
) -> int:
    matches = tuple(
        position
        for position, retained in enumerate(inspection.fragments)
        if retained is fragment
    )
    if len(matches) != 1:
        raise ValueError("Inspection fragments require one exact position.")
    return matches[0]


def _fragment_for_node(
    inspection: ProjectIRInspection,
    node: ProjectIRPlanNodeOccurrence,
) -> ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in inspection.fragments
        if any(node is retained for retained in fragment.structural_stage.nodes)
    )
    if len(matches) != 1:
        raise ValueError("Inspection nodes require one exact fragment.")
    return matches[0]


def _operator_for_node(
    inspection: ProjectIRInspection,
    node: ProjectIRPlanNodeOccurrence,
) -> ProjectIRLogicalOperatorOccurrence:
    matches = tuple(
        operator for operator in inspection.operators if operator.node is node
    )
    if len(matches) != 1:
        raise ValueError("Inspection nodes require one exact operator.")
    return matches[0]


def _output_kind(output: ProjectIRCurrentOutput) -> str:
    if type(output) is ProjectIRRelationRowOutput:
        return "relation_row"
    if type(output) is ProjectIRScalarFieldOutput:
        return "scalar_field"
    return "stage_scalar_field"


def _output_field(
    output: ProjectIRCurrentOutput,
) -> tuple[str, int | None, str | None]:
    if type(output) is ProjectIRRelationRowOutput:
        return "none", None, None
    if type(output) is ProjectIRScalarFieldOutput:
        return (
            "semantic",
            output.field.anchor.identity.field_position,
            output.field.anchor.identity.name,
        )
    if type(output) is ProjectIRStageScalarFieldOutput:
        return "stage", output.field.field_position, output.field.evidence.name
    raise TypeError("Inspection encountered an unsupported output carrier.")


def _output_fields(
    output: ProjectIRCurrentOutput,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    fields = output.row_shape.fields
    return (
        tuple(field.evidence.name for field in fields),
        tuple(field.evidence.resolved_type.name for field in fields),
        tuple(field.evidence.resolved_type.kind.value for field in fields),
        tuple(field.evidence.nullability.value for field in fields),
        tuple(field.evidence.result_role.value for field in fields),
    )


def _property_values(
    property_: ProjectIRProvidedProperty,
) -> tuple[str, str | None, int | None]:
    if type(property_) is ProjectIRUnavailableProvidedProperty:
        return property_.availability.value, None, None
    if type(property_) is ProjectIRProvidedOutputShape:
        return "exact", _output_kind(property_.output), None
    if type(property_) is ProjectIRProvidedBagMultiplicity:
        return "exact", "bag", None
    if type(property_) is ProjectIRProvidedClosedBindings:
        return "exact", "closed", None
    if type(property_) is ProjectIRProvidedRelationOrdering:
        return "exact", None, len(property_.items)
    if type(property_) is ProjectIRProvidedLocalGrainEvidence:
        return "exact", None, len(property_.occurrences)
    if type(property_) is ProjectIRProvidedCardinalityUpperBound:
        return "exact", None, property_.upper_bound
    if type(property_) is ProjectIRProvidedEvaluationPolicy:
        return "exact", property_.policy.kind.value, None
    raise TypeError("Inspection encountered an unsupported property carrier.")


def _project_ir_pure_document(
    inspection: ProjectIRInspection,
) -> ProjectIRPureDocument:
    """Project exact runtime authority into explicit portable records."""

    if type(inspection) is not ProjectIRInspection:
        raise TypeError("Portable projection requires an exact inspection.")
    stage = inspection.stage
    plan = stage.project_plan
    start = plan.starting_allocation
    end = plan.ending_allocation
    records: list[ProjectIRPureRecord] = []
    _pure_record(
        records,
        "header",
        ("format", project_ir_pure_enumeration(PROJECT_IR_INSPECTION_FORMAT)),
        (
            "verification",
            project_ir_pure_enumeration(inspection.verification.status.value),
        ),
        ("node_start", project_ir_pure_integer(start.next_plan_node_position)),
        (
            "node_count",
            project_ir_pure_integer(
                end.next_plan_node_position - start.next_plan_node_position
            ),
        ),
        ("output_start", project_ir_pure_integer(start.next_output_value_position)),
        (
            "output_count",
            project_ir_pure_integer(
                end.next_output_value_position - start.next_output_value_position
            ),
        ),
        ("slot_start", project_ir_pure_integer(start.next_input_slot_position)),
        (
            "slot_count",
            project_ir_pure_integer(
                end.next_input_slot_position - start.next_input_slot_position
            ),
        ),
        ("use_start", project_ir_pure_integer(start.next_use_position)),
        (
            "use_count",
            project_ir_pure_integer(end.next_use_position - start.next_use_position),
        ),
        ("fragment_count", project_ir_pure_integer(len(inspection.fragments))),
        (
            "cross_edge_count",
            project_ir_pure_integer(len(inspection.cross_relation_edges)),
        ),
        (
            "property_count",
            project_ir_pure_integer(
                len(inspection.provided_properties)
                + len(inspection.required_properties)
            ),
        ),
        (
            "compatibility_count",
            project_ir_pure_integer(len(inspection.compatibilities)),
        ),
        ("effect_count", project_ir_pure_integer(len(inspection.effects))),
        (
            "evaluation_context_count",
            project_ir_pure_integer(inspection.summary.evaluation_context_count),
        ),
        ("reverse_use_count", project_ir_pure_integer(len(inspection.reverse_uses))),
        (
            "topological_count",
            project_ir_pure_integer(len(inspection.topological_order)),
        ),
        ("reachability_count", project_ir_pure_integer(len(inspection.reachability))),
        (
            "equivalence_count",
            project_ir_pure_integer(len(inspection.equivalence_assessments)),
        ),
        ("rewrite_count", project_ir_pure_integer(len(inspection.rewrite_readiness))),
    )
    for position, fragment in enumerate(inspection.fragments):
        identity = fragment.subject.anchor.identity
        _pure_record(
            records,
            "fragment",
            ("fragment", project_ir_pure_integer(position)),
            ("module_path", project_ir_pure_text(identity.identity.module_path)),
            ("module_position", project_ir_pure_integer(identity.module_position)),
            (
                "declaration_position",
                project_ir_pure_integer(identity.declaration_position),
            ),
            (
                "declaration_kind",
                project_ir_pure_enumeration(identity.identity.declaration_kind.value),
            ),
            ("declared_name", project_ir_pure_text(identity.identity.declared_name)),
            ("state", project_ir_pure_enumeration(fragment.subject.state.value)),
            (
                "reason",
                _optional_text(
                    None
                    if fragment.subject.state.value == "concrete"
                    else fragment.semantic_facts.state.reason.value
                ),
            ),
            (
                "root",
                _optional_ref(fragment.root.ref if fragment.root is not None else None),
            ),
            ("nodes", project_ir_pure_integer(len(fragment.structural_stage.nodes))),
            (
                "outputs",
                project_ir_pure_integer(len(fragment.structural_stage.outputs)),
            ),
        )
    for node in inspection.nodes:
        fragment = _fragment_for_node(inspection, node)
        _pure_record(
            records,
            "node",
            ("node", project_ir_pure_ref(_portable_ref(node.ref))),
            (
                "fragment",
                project_ir_pure_integer(_fragment_position(inspection, fragment)),
            ),
            (
                "operator",
                project_ir_pure_enumeration(
                    _operator_for_node(inspection, node).kind.value
                ),
            ),
        )
    for output in inspection.outputs:
        fragment = _fragment_for_node(inspection, output.occurrence.producer)
        checkpoint = (
            output.row_shape.checkpoint.kind.value
            if type(output.row_shape) is ProjectIRStageRowShape
            else None
        )
        field_domain, field_position, field_name = _output_field(output)
        names, type_names, type_kinds, nullabilities, roles = _output_fields(output)
        _pure_record(
            records,
            "output",
            ("output", project_ir_pure_ref(_portable_ref(output.occurrence.ref))),
            (
                "fragment",
                project_ir_pure_integer(_fragment_position(inspection, fragment)),
            ),
            (
                "producer",
                project_ir_pure_ref(_portable_ref(output.occurrence.producer.ref)),
            ),
            ("kind", project_ir_pure_enumeration(_output_kind(output))),
            ("checkpoint", _optional_enumeration(checkpoint)),
            ("field_domain", project_ir_pure_enumeration(field_domain)),
            ("field_position", _optional_integer(field_position)),
            ("field_name", _optional_text(field_name)),
            ("field_count", project_ir_pure_integer(len(names))),
            ("field_names", project_ir_pure_texts(names)),
            ("type_names", project_ir_pure_texts(type_names)),
            ("type_kinds", project_ir_pure_enumerations(type_kinds)),
            ("nullabilities", project_ir_pure_enumerations(nullabilities)),
            ("result_roles", project_ir_pure_enumerations(roles)),
        )
    for slot in inspection.input_slots:
        _pure_record(
            records,
            "input_slot",
            ("slot", project_ir_pure_ref(_portable_ref(slot.ref))),
            ("consumer", project_ir_pure_ref(_portable_ref(slot.consumer.ref))),
            ("input_ordinal", project_ir_pure_integer(slot.input_ordinal)),
        )
    for use in inspection.uses:
        semantic = type(use) is ProjectIRUseOccurrence
        _pure_record(
            records,
            "use",
            ("use", project_ir_pure_ref(_portable_ref(use.ref))),
            (
                "kind",
                project_ir_pure_enumeration(
                    "semantic" if semantic else "operator_flow"
                ),
            ),
            ("output", project_ir_pure_ref(_portable_ref(use.output.ref))),
            ("slot", project_ir_pure_ref(_portable_ref(use.slot.ref))),
            (
                "role",
                _optional_enumeration(use.role.value if semantic else None),
            ),
            (
                "source_order",
                _optional_integer(use.source_order if semantic else None),
            ),
        )
    for position, edge in enumerate(inspection.cross_relation_edges):
        origin = edge.authority.dependency.origin_path
        if origin is None:
            raise ValueError("Verified cross edges require exact origin paths.")
        _pure_record(
            records,
            "cross_edge",
            ("edge", project_ir_pure_integer(position)),
            ("use", project_ir_pure_ref(_portable_ref(edge.use.ref))),
            (
                "producer_fragment",
                project_ir_pure_integer(_fragment_position(inspection, edge.producer)),
            ),
            (
                "consumer_fragment",
                project_ir_pure_integer(_fragment_position(inspection, edge.consumer)),
            ),
            (
                "compatibility",
                project_ir_pure_enumeration(edge.compatibility.status.value),
            ),
            (
                "origin_kind",
                project_ir_pure_enumeration(
                    "local" if origin.local_occurrence is not None else "imported"
                ),
            ),
            ("origin_hops", project_ir_pure_integer(len(origin.hops))),
        )
    property_position = 0
    for property_ in inspection.provided_properties:
        evidence, value_enum, value_integer = _property_values(property_)
        _pure_record(
            records,
            "property",
            ("property", project_ir_pure_integer(property_position)),
            ("direction", project_ir_pure_enumeration("provided")),
            (
                "output",
                project_ir_pure_ref(_portable_ref(property_.output.occurrence.ref)),
            ),
            ("input_slot", PROJECT_IR_PURE_ABSENT),
            ("slot", project_ir_pure_enumeration(property_.property_slot.value)),
            ("evidence", project_ir_pure_enumeration(evidence)),
            ("value_enum", _optional_enumeration(value_enum)),
            ("value_integer", _optional_integer(value_integer)),
        )
        property_position += 1
    for property_ in inspection.required_properties:
        _pure_record(
            records,
            "property",
            ("property", project_ir_pure_integer(property_position)),
            ("direction", project_ir_pure_enumeration("required")),
            ("output", PROJECT_IR_PURE_ABSENT),
            (
                "input_slot",
                project_ir_pure_ref(_portable_ref(property_.input_slot.ref)),
            ),
            ("slot", project_ir_pure_enumeration(property_.property_slot.value)),
            ("evidence", project_ir_pure_enumeration("exact")),
            ("value_enum", project_ir_pure_enumeration("exact")),
            ("value_integer", PROJECT_IR_PURE_ABSENT),
        )
        property_position += 1
    for position, edge in enumerate(inspection.cross_relation_edges):
        _pure_record(
            records,
            "compatibility",
            ("compatibility", project_ir_pure_integer(position)),
            (
                "provided_output",
                project_ir_pure_ref(
                    _portable_ref(edge.provided_row_shape.output.occurrence.ref)
                ),
            ),
            (
                "required_slot",
                project_ir_pure_ref(
                    _portable_ref(edge.required_row_shape.input_slot.ref)
                ),
            ),
            ("status", project_ir_pure_enumeration(edge.compatibility.status.value)),
        )
    for position, effect in enumerate(inspection.effects):
        _pure_record(
            records,
            "effect",
            ("effect", project_ir_pure_integer(position)),
            (
                "output",
                project_ir_pure_ref(_portable_ref(effect.output.occurrence.ref)),
            ),
            ("determinism", project_ir_pure_enumeration(effect.determinism.value)),
            (
                "error_behavior",
                project_ir_pure_enumeration(effect.error_behavior.value),
            ),
            ("side_effects", project_ir_pure_enumeration(effect.side_effects.value)),
            (
                "evaluation_count",
                project_ir_pure_enumeration(effect.evaluation_count.value),
            ),
        )
    context_position = 0
    for context in inspection.aggregate_contexts:
        _pure_record(
            records,
            "evaluation_context",
            ("context", project_ir_pure_integer(context_position)),
            ("kind", project_ir_pure_enumeration("aggregate")),
            ("operator", project_ir_pure_ref(_portable_ref(context.operator.node.ref))),
            (
                "input",
                project_ir_pure_ref(
                    _portable_ref(context.input_row_output.occurrence.ref)
                ),
            ),
            (
                "result",
                project_ir_pure_ref(
                    _portable_ref(context.result_row_output.occurrence.ref)
                ),
            ),
            ("checkpoint", project_ir_pure_enumeration("base_result")),
            ("window_ordinal", PROJECT_IR_PURE_ABSENT),
            ("group_keys", project_ir_pure_integer(len(context.group_keys))),
            (
                "aggregate_results",
                project_ir_pure_integer(len(context.aggregate_results)),
            ),
            ("policy", PROJECT_IR_PURE_ABSENT),
        )
        context_position += 1
    for context in inspection.window_operator_contexts:
        _pure_record(
            records,
            "evaluation_context",
            ("context", project_ir_pure_integer(context_position)),
            ("kind", project_ir_pure_enumeration("window_operator")),
            ("operator", project_ir_pure_ref(_portable_ref(context.operator.node.ref))),
            (
                "input",
                project_ir_pure_ref(
                    _portable_ref(context.stream_input_row_output.occurrence.ref)
                ),
            ),
            (
                "result",
                project_ir_pure_ref(
                    _portable_ref(context.result_row_output.occurrence.ref)
                ),
            ),
            ("checkpoint", project_ir_pure_enumeration("base_result")),
            ("window_ordinal", PROJECT_IR_PURE_ABSENT),
            ("group_keys", PROJECT_IR_PURE_ABSENT),
            ("aggregate_results", PROJECT_IR_PURE_ABSENT),
            ("policy", PROJECT_IR_PURE_ABSENT),
        )
        context_position += 1
    for context in inspection.window_result_contexts:
        _pure_record(
            records,
            "evaluation_context",
            ("context", project_ir_pure_integer(context_position)),
            ("kind", project_ir_pure_enumeration("window_result")),
            (
                "operator",
                project_ir_pure_ref(
                    _portable_ref(context.operator_context.operator.node.ref)
                ),
            ),
            ("input", PROJECT_IR_PURE_ABSENT),
            (
                "result",
                project_ir_pure_ref(
                    _portable_ref(context.stage_scalar_output.occurrence.ref)
                ),
            ),
            ("checkpoint", PROJECT_IR_PURE_ABSENT),
            (
                "window_ordinal",
                project_ir_pure_integer(context.window_fact.selected_output_ordinal),
            ),
            ("group_keys", PROJECT_IR_PURE_ABSENT),
            ("aggregate_results", PROJECT_IR_PURE_ABSENT),
            ("policy", project_ir_pure_enumeration(context.policy.policy.kind.value)),
        )
        context_position += 1
    for position, entry in enumerate(inspection.reverse_uses):
        _pure_record(
            records,
            "reverse_use",
            ("reverse_use", project_ir_pure_integer(position)),
            ("output", project_ir_pure_ref(_portable_ref(entry.output.ref))),
            (
                "uses",
                project_ir_pure_refs(
                    tuple(_portable_ref(use.ref) for use in entry.uses)
                ),
            ),
        )
    for position, node in enumerate(inspection.topological_order):
        _pure_record(
            records,
            "topological",
            ("topological", project_ir_pure_integer(position)),
            ("node", project_ir_pure_ref(_portable_ref(node.ref))),
        )
    for position, entry in enumerate(inspection.reachability):
        _pure_record(
            records,
            "reachability",
            ("reachability", project_ir_pure_integer(position)),
            ("node", project_ir_pure_ref(_portable_ref(entry.source.ref))),
            (
                "reachable",
                project_ir_pure_refs(
                    tuple(_portable_ref(node.ref) for node in entry.reachable)
                ),
            ),
        )
    for position, assessment in enumerate(inspection.equivalence_assessments):
        dimension_values = tuple(
            (item.dimension.value, project_ir_pure_enumeration(item.status.value))
            for item in assessment.dimensions
        )
        _pure_record(
            records,
            "equivalence",
            ("equivalence", project_ir_pure_integer(position)),
            (
                "left_fragment",
                project_ir_pure_integer(
                    _fragment_position(inspection, assessment.left)
                ),
            ),
            (
                "right_fragment",
                project_ir_pure_integer(
                    _fragment_position(inspection, assessment.right)
                ),
            ),
            ("status", project_ir_pure_enumeration(assessment.status.value)),
            *dimension_values,
        )
    for position, readiness in enumerate(inspection.rewrite_readiness):
        assessment_position = next(
            index
            for index, assessment in enumerate(inspection.equivalence_assessments)
            if assessment is readiness.assessment
        )
        _pure_record(
            records,
            "rewrite_readiness",
            ("rewrite", project_ir_pure_integer(position)),
            ("equivalence", project_ir_pure_integer(assessment_position)),
            ("status", project_ir_pure_enumeration(readiness.status.value)),
            (
                "blockers",
                project_ir_pure_enumerations(
                    tuple(blocker.value for blocker in readiness.blockers)
                ),
            ),
        )
    _pure_record(records, "end")
    return ProjectIRPureDocument(records=tuple(records))
