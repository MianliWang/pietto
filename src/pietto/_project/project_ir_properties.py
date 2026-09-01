"""Private exact semantic properties over one structural Project IR stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Never, cast

from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectRelationRowSchemaState,
    ProjectRowField,
    ProjectRowFieldNullability,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleClauseDependencyFact,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleWindowOutputFact,
)
from pietto._project.project_ir import (
    ProjectIRConcreteRelationSubject,
    ProjectIRFieldAnchor,
    ProjectIRInputSlotOccurrence,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRResolvedRelationAnchor,
    ProjectIRSnapshotScope,
    ProjectIRStageFieldAnchor,
    ProjectIRStructuralStage,
    ProjectIRUseOccurrence,
    _declaration_identity,
    _require_exact_tuple,
)
from pietto.ast_nodes import GroupByItem, LiteralExpr, OrderItem, QueryDef, TableDef
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT
from pietto.semantic.window_semantics import WindowFunctionFramePolicy

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRowField:
    """One exact Project field occurrence together with its typed evidence."""

    anchor: ProjectIRFieldAnchor
    evidence: ProjectRowField = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.anchor) is not ProjectIRFieldAnchor:
            raise TypeError("Project IR row field requires an exact field anchor.")
        if type(self.evidence) is not ProjectRowField:
            raise TypeError("Project IR row field requires exact field evidence.")
        if self.anchor.identity.name != self.evidence.name:
            raise ValueError("Project IR row field identity and evidence must match.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRowShape:
    """Exact ordered current row shape, separate from plan occurrence identity."""

    relation: ProjectIRRelationAnchor
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    fields: tuple[ProjectIRRowField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.relation) is not ProjectIRRelationAnchor:
            raise TypeError("Project IR row shape requires a relation anchor.")
        if type(self.evidence) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Project IR row shape requires exact semantic evidence.")
        schema = self.evidence.state.schema
        if (
            _declaration_identity(self.evidence.owner) != self.relation.identity
            or self.evidence.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
        ):
            raise ValueError(
                "Project IR row shape requires matching concrete evidence."
            )
        _require_exact_tuple(self.fields, ProjectIRRowField, label="Row fields")
        if any(
            item.anchor.identity.owner != self.relation.identity for item in self.fields
        ):
            raise ValueError("Project IR row fields must belong to their relation.")
        if tuple(item.anchor.identity.field_position for item in self.fields) != tuple(
            range(len(self.fields))
        ):
            raise ValueError("Project IR row fields must retain exact source order.")
        schema_fields = tuple(schema.fields.values())
        if len(self.fields) != len(schema_fields) or any(
            item.evidence is not expected
            for item, expected in zip(self.fields, schema_fields, strict=True)
        ):
            raise ValueError(
                "Project IR row shape must retain complete field evidence."
            )


class ProjectIRStageRowCheckpointKind(StrEnum):
    """Exact semantic checkpoints used by current intermediate row stages."""

    INPUT = "input"
    BASE_RESULT = "base_result"
    FINAL = "final"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRStageRowCheckpoint:
    """One exact semantic row checkpoint for a plan-local stage row."""

    relation: ProjectIRRelationAnchor
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectIRStageRowCheckpointKind
    state: ProjectRelationRowSchemaState = field(init=False)

    def __post_init__(self) -> None:
        if type(self.relation) is not ProjectIRRelationAnchor:
            raise TypeError("Stage row checkpoint requires a relation anchor.")
        if type(self.evidence) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Stage row checkpoint requires exact semantic evidence.")
        if type(self.kind) is not ProjectIRStageRowCheckpointKind:
            raise TypeError("Stage row checkpoint requires an exact kind.")
        if _declaration_identity(self.evidence.owner) != self.relation.identity:
            raise ValueError("Stage row checkpoint must match its relation owner.")
        state = {
            ProjectIRStageRowCheckpointKind.INPUT: self.evidence.input_state,
            ProjectIRStageRowCheckpointKind.BASE_RESULT: (
                self.evidence.base_result_state
            ),
            ProjectIRStageRowCheckpointKind.FINAL: self.evidence.state,
        }[self.kind]
        if state is None:
            raise ValueError("Stage row checkpoint is unavailable for this relation.")
        object.__setattr__(self, "state", state)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRStageRowField:
    """One positional stage field with exact checkpoint/type evidence."""

    checkpoint: ProjectIRStageRowCheckpoint
    field_position: int
    evidence: ProjectRowField = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.checkpoint) is not ProjectIRStageRowCheckpoint:
            raise TypeError("Stage row field requires an exact checkpoint.")
        if type(self.field_position) is not int or self.field_position < 0:
            raise TypeError("Stage row field position must be non-negative.")
        if type(self.evidence) is not ProjectRowField:
            raise TypeError("Stage row field requires exact field evidence.")
        schema = self.checkpoint.state.schema
        if (
            self.checkpoint.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
        ):
            raise ValueError("Stage row field requires a concrete checkpoint.")
        fields = tuple(schema.fields.values())
        if (
            self.field_position >= len(fields)
            or fields[self.field_position] is not self.evidence
        ):
            raise ValueError("Stage row field must retain exact checkpoint order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRStageRowShape:
    """Complete plan-local row shape at one exact semantic checkpoint."""

    checkpoint: ProjectIRStageRowCheckpoint
    fields: tuple[ProjectIRStageRowField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.checkpoint) is not ProjectIRStageRowCheckpoint:
            raise TypeError("Stage row shape requires an exact checkpoint.")
        _require_exact_tuple(self.fields, ProjectIRStageRowField, label="Stage fields")
        if any(item.checkpoint is not self.checkpoint for item in self.fields):
            raise ValueError("Stage row fields must retain the exact checkpoint.")
        if tuple(item.field_position for item in self.fields) != tuple(
            range(len(self.fields))
        ):
            raise ValueError("Stage row fields must retain exact position order.")
        schema = self.checkpoint.state.schema
        if (
            self.checkpoint.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
        ):
            raise ValueError("Stage row shape requires a concrete checkpoint.")
        schema_fields = tuple(schema.fields.values())
        if len(self.fields) != len(schema_fields) or any(
            item.evidence is not expected
            for item, expected in zip(self.fields, schema_fields, strict=True)
        ):
            raise ValueError("Stage row shape must retain complete field evidence.")

    @property
    def relation(self) -> ProjectIRRelationAnchor:
        return self.checkpoint.relation

    @property
    def evidence(self) -> ProjectModuleRelationSemanticFacts:
        return self.checkpoint.evidence


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinedRowField:
    """One plan-local joined field instance with exact nulling provenance."""

    field_position: int
    evidence: ProjectRowField = field(repr=False)
    introduction_use: ProjectIRJoinInputUseOccurrence = field(
        repr=False, compare=False, hash=False
    )
    nulling_joins: tuple[ProjectIRPlanNodeRef, ...]
    effective_nullability: ProjectRowFieldNullability

    def __post_init__(self) -> None:
        if type(self.field_position) is not int or self.field_position < 0:
            raise ValueError("Joined field position must be non-negative.")
        if type(self.evidence) is not ProjectRowField:
            raise TypeError("Joined field requires exact semantic field evidence.")
        if type(self.introduction_use) is not ProjectIRJoinInputUseOccurrence:
            raise TypeError("Joined field requires an exact introduction use.")
        if type(self.nulling_joins) is not tuple or any(
            type(item) is not ProjectIRPlanNodeRef for item in self.nulling_joins
        ):
            raise TypeError("Joined field nulling provenance must be an exact tuple.")
        positions = tuple(item.position for item in self.nulling_joins)
        if len(set(self.nulling_joins)) != len(self.nulling_joins) or any(
            left >= right for left, right in zip(positions, positions[1:], strict=False)
        ):
            raise ValueError("Joined field nulling refs must be unique and ordered.")
        if any(
            item.scope is not self.introduction_use.ref.scope
            for item in self.nulling_joins
        ):
            raise ValueError("Joined field provenance requires one snapshot scope.")
        if type(self.effective_nullability) is not ProjectRowFieldNullability:
            raise TypeError("Joined field requires exact effective nullability.")
        if self.nulling_joins and (
            self.effective_nullability is not ProjectRowFieldNullability.NULLABLE
        ):
            raise ValueError("Null-generated joined fields must be nullable.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinedRowShape:
    """One plan-local binary JOIN row without fabricated semantic-row facts."""

    relation: ProjectIRRelationAnchor
    producer: ProjectIRPlanNodeOccurrence
    fields: tuple[ProjectIRJoinedRowField, ...]

    def __post_init__(self) -> None:
        if type(self.relation) is not ProjectIRRelationAnchor:
            raise TypeError("Joined row shape requires a relation anchor.")
        if (
            type(self.producer) is not ProjectIRPlanNodeOccurrence
            or self.producer.anchor != self.relation
        ):
            raise ValueError("Joined row shape requires its exact producer node.")
        _require_exact_tuple(
            self.fields, ProjectIRJoinedRowField, label="Joined fields"
        )
        if tuple(item.field_position for item in self.fields) != tuple(
            range(len(self.fields))
        ):
            raise ValueError("Joined row fields must retain exact output order.")
        if any(
            item.introduction_use.ref.scope is not self.producer.ref.scope
            for item in self.fields
        ):
            raise ValueError("Joined row fields require one snapshot scope.")
        if any(
            item.introduction_use.slot.consumer.ref.position
            > self.producer.ref.position
            or any(
                ref.position > self.producer.ref.position for ref in item.nulling_joins
            )
            for item in self.fields
        ):
            raise ValueError("Joined row provenance cannot refer to a later JOIN.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinRowOutput:
    """One binary JOIN row output outside the base unary property stage."""

    occurrence: ProjectIROutputValueOccurrence
    row_shape: ProjectIRJoinedRowShape

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectIROutputValueOccurrence:
            raise TypeError("JOIN row output requires an output occurrence.")
        if type(self.row_shape) is not ProjectIRJoinedRowShape:
            raise TypeError("JOIN row output requires an exact joined row shape.")
        if (
            type(self.occurrence.anchor) is not ProjectIRRelationAnchor
            or self.occurrence.anchor != self.row_shape.relation
            or self.occurrence.producer is not self.row_shape.producer
        ):
            raise ValueError("JOIN row output must retain its exact producer and row.")


type ProjectIRCurrentRowShape = ProjectIRRowShape | ProjectIRStageRowShape


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRScalarFieldOutput:
    """Current scalar field output without a permanent ExpressionIR equation."""

    occurrence: ProjectIROutputValueOccurrence
    row_shape: ProjectIRRowShape
    field: ProjectIRRowField

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectIROutputValueOccurrence:
            raise TypeError("Scalar output requires an output-value occurrence.")
        if type(self.row_shape) is not ProjectIRRowShape:
            raise TypeError("Scalar output requires an exact row shape.")
        if type(self.field) is not ProjectIRRowField:
            raise TypeError("Scalar output requires an exact row field.")
        if (
            type(self.occurrence.anchor) is not ProjectIRFieldAnchor
            or self.occurrence.anchor != self.field.anchor
            or self.occurrence.producer.anchor != self.row_shape.relation
            or not any(item is self.field for item in self.row_shape.fields)
        ):
            raise ValueError("Scalar output must retain its exact row and field.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRStageScalarFieldOutput:
    """Plan-local scalar value distinct from a final semantic field export."""

    occurrence: ProjectIROutputValueOccurrence
    row_shape: ProjectIRStageRowShape
    field: ProjectIRStageRowField

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectIROutputValueOccurrence:
            raise TypeError("Stage scalar output requires an output occurrence.")
        if type(self.row_shape) is not ProjectIRStageRowShape:
            raise TypeError("Stage scalar output requires a stage row shape.")
        if type(self.field) is not ProjectIRStageRowField:
            raise TypeError("Stage scalar output requires a stage row field.")
        anchor = self.occurrence.anchor
        if (
            type(anchor) is not ProjectIRStageFieldAnchor
            or anchor.producer is not self.occurrence.producer
            or anchor.field_position != self.field.field_position
            or self.field.checkpoint is not self.row_shape.checkpoint
            or self.occurrence.producer.anchor != self.row_shape.relation
        ):
            raise ValueError("Stage scalar output must retain its exact stage field.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRelationRowOutput:
    """Current BAG relation output with one exact ordered row shape."""

    occurrence: ProjectIROutputValueOccurrence
    row_shape: ProjectIRCurrentRowShape

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectIROutputValueOccurrence:
            raise TypeError("Relation output requires an output-value occurrence.")
        if type(self.row_shape) not in {ProjectIRRowShape, ProjectIRStageRowShape}:
            raise TypeError("Relation output requires a typed current row shape.")
        if (
            type(self.occurrence.anchor) is not ProjectIRRelationAnchor
            or self.occurrence.anchor != self.row_shape.relation
        ):
            raise ValueError("Relation output must retain its exact relation anchor.")


type ProjectIRCurrentOutput = (
    ProjectIRScalarFieldOutput
    | ProjectIRStageScalarFieldOutput
    | ProjectIRRelationRowOutput
)


class ProjectIRProvidedPropertySlot(StrEnum):
    """Closed Slice-3 exact-property slots, not estimate or requirement kinds."""

    OUTPUT_SHAPE = "output_shape"
    CARDINALITY_BOUNDS = "cardinality_bounds"
    MULTIPLICITY = "multiplicity"
    RELATION_RESULT_ORDERING = "relation_result_ordering"
    LOCAL_GRAIN_EVIDENCE = "local_grain_evidence"
    FACT_DOMAINS = "fact_domains"
    FREE_BINDINGS = "free_bindings"
    NULL_EXTENSION = "null_extension"
    POLICY_EVALUATION = "policy_evaluation"


class ProjectIRPropertyAvailability(StrEnum):
    """Explicit lack-of-fact states; neither one means false or empty."""

    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedOutputShape:
    """Exact provided output shape owned by one output occurrence."""

    output: ProjectIRCurrentOutput

    def __post_init__(self) -> None:
        _validate_current_output(self.output, label="Provided output shape")

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.OUTPUT_SHAPE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedBagMultiplicity:
    """Exact current duplicate-preserving relation multiplicity."""

    output: ProjectIRRelationRowOutput

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRRelationRowOutput:
            raise TypeError("BAG multiplicity requires a relation-row output.")

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.MULTIPLICITY


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedClosedBindings:
    """Exact empty free-binding fact for current closed Project IR."""

    output: ProjectIRRelationRowOutput

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRRelationRowOutput:
            raise TypeError("Closed bindings require a relation-row output.")

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.FREE_BINDINGS

    @property
    def bindings(self) -> tuple[object, ...]:
        return ()


def _validate_clause_evidence(
    output: ProjectIRRelationRowOutput,
    evidence: ProjectModuleRelationSemanticFacts,
    *,
    role: ProjectModuleFactOccurrenceRole,
    label: str,
) -> tuple[ProjectModuleClauseDependencyFact, ...]:
    _validate_relation_evidence(output, evidence, label=label)
    facts = tuple(item for item in evidence.clause_dependencies if item.role is role)
    if not facts:
        raise ValueError(f"{label} requires non-empty exact evidence.")
    if any(
        item.status is not ProjectModuleCandidateBucketStatus.CONCRETE for item in facts
    ):
        raise ValueError(f"{label} requires matching concrete semantic evidence.")
    if tuple(item.source_ordinal for item in facts) != tuple(range(len(facts))):
        raise ValueError(f"{label} must retain exact source order.")
    return facts


def _validate_relation_evidence(
    output: ProjectIRRelationRowOutput,
    evidence: object,
    *,
    label: str,
) -> None:
    if type(evidence) is not ProjectModuleRelationSemanticFacts:
        raise TypeError(f"{label} requires exact relation semantic evidence.")
    if evidence is not output.row_shape.evidence:
        raise ValueError(f"{label} must reuse the output's exact semantic authority.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedRelationOrdering:
    """Exact relation-result ordering, never window-local ordering."""

    output: ProjectIRRelationRowOutput
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    items: tuple[OrderItem, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRRelationRowOutput:
            raise TypeError("Relation ordering requires a relation-row output.")
        _validate_relation_evidence(
            self.output,
            self.evidence,
            label="Relation-result ordering",
        )
        definition = self.evidence.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Relation-result ordering requires a derived relation.")
        definition = cast(TableDef | QueryDef, definition)
        clause = definition.order_by_clause
        if clause is None:
            raise ValueError("Relation-result ordering requires an exact order clause.")
        _require_exact_tuple(clause.items, OrderItem, label="Relation-result ordering")
        items = clause.items
        if definition.group_by_clause is not None:
            facts = _validate_clause_evidence(
                self.output,
                self.evidence,
                role=ProjectModuleFactOccurrenceRole.GROUPED_ORDER,
                label="Relation-result ordering",
            )
            if len(facts) != len(items) or any(
                fact.source_occurrence is not item
                for fact, item in zip(facts, items, strict=True)
            ):
                raise ValueError(
                    "Relation-result ordering requires complete grouped evidence."
                )
        object.__setattr__(self, "items", items)

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedLocalGrainEvidence:
    """Exact local group-key evidence without a grain descriptor or comparison."""

    output: ProjectIRRelationRowOutput
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    occurrences: tuple[GroupByItem, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRRelationRowOutput:
            raise TypeError("Local grain evidence requires a relation-row output.")
        facts = _validate_clause_evidence(
            self.output,
            self.evidence,
            role=ProjectModuleFactOccurrenceRole.GROUP_KEY,
            label="Local grain evidence",
        )
        occurrences = tuple(item.source_occurrence for item in facts)
        if any(type(item) is not GroupByItem for item in occurrences):
            raise TypeError("Local grain evidence requires exact group-key items.")
        object.__setattr__(self, "occurrences", occurrences)

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedCardinalityUpperBound:
    """Exact static LIMIT upper bound with retained semantic-fact authority."""

    output: ProjectIRRelationRowOutput
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    upper_bound: int = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRRelationRowOutput:
            raise TypeError("Cardinality bound requires a relation-row output.")
        _validate_relation_evidence(
            self.output,
            self.evidence,
            label="Cardinality bound",
        )
        definition = self.evidence.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Cardinality bound requires a derived relation.")
        definition = cast(TableDef | QueryDef, definition)
        clause = definition.limit_clause
        expression = None if clause is None else clause.expression
        if type(expression) is not LiteralExpr:
            raise ValueError(
                "Cardinality bound requires an exact static integer LIMIT."
            )
        value = expression.value
        if type(value) is not int or not 0 <= value <= MAX_RELATION_LIMIT:
            raise ValueError("Cardinality bound requires a valid static LIMIT.")
        object.__setattr__(self, "upper_bound", value)

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedEvaluationPolicy:
    """Exact existing window policy evidence, separate from effect evidence."""

    output: ProjectIRScalarFieldOutput | ProjectIRStageScalarFieldOutput
    evidence: ProjectModuleWindowOutputFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    policy: WindowFunctionFramePolicy = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) not in {
            ProjectIRScalarFieldOutput,
            ProjectIRStageScalarFieldOutput,
        }:
            raise TypeError("Evaluation policy requires a scalar field output.")
        if type(self.evidence) is not ProjectModuleWindowOutputFact:
            raise TypeError("Evaluation policy requires exact window evidence.")
        project_fact = self.evidence.project_fact
        if type(self.output) is ProjectIRScalarFieldOutput:
            field_owner = self.output.field.anchor.identity.owner
            field_position = self.output.field.anchor.identity.field_position
            field_name = self.output.field.anchor.identity.name
        else:
            stage_output = cast(ProjectIRStageScalarFieldOutput, self.output)
            field_owner = stage_output.row_shape.relation.identity
            field_position = stage_output.field.field_position
            field_name = stage_output.field.evidence.name
        if (
            self.evidence.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or project_fact is None
            or not any(
                item is self.evidence
                for item in self.output.row_shape.evidence.window_outputs
            )
            or _declaration_identity(self.evidence.owner) != field_owner
            or self.evidence.selected_output_ordinal != field_position
            or self.evidence.output_name != field_name
        ):
            raise ValueError(
                "Evaluation policy must match exact concrete output evidence."
            )
        object.__setattr__(
            self,
            "policy",
            project_fact.analysis.validated_specification.function_policy,
        )

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.POLICY_EVALUATION


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRUnavailableProvidedProperty:
    """Explicit unknown or not-applicable state for one provided-property slot."""

    output: ProjectIRCurrentOutput
    property_slot: ProjectIRProvidedPropertySlot
    availability: ProjectIRPropertyAvailability

    def __post_init__(self) -> None:
        _validate_current_output(self.output, label="Unavailable property")
        if type(self.property_slot) is not ProjectIRProvidedPropertySlot:
            raise TypeError("Unavailable property requires an exact property slot.")
        if self.property_slot is ProjectIRProvidedPropertySlot.OUTPUT_SHAPE:
            raise ValueError("Current typed outputs always establish output shape.")
        if type(self.availability) is not ProjectIRPropertyAvailability:
            raise TypeError("Unavailable property requires an exact availability.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedNullExtension:
    """Positive complete field-local null-extension provenance."""

    output: ProjectIRJoinRowOutput
    fields: tuple[ProjectIRJoinedRowField, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRJoinRowOutput:
            raise TypeError("NULL_EXTENSION requires one joined row output.")
        fields = self.output.row_shape.fields
        if not any(item.nulling_joins for item in fields):
            raise ValueError("Positive NULL_EXTENSION requires exact nulling evidence.")
        object.__setattr__(self, "fields", fields)

    @property
    def property_slot(self) -> ProjectIRProvidedPropertySlot:
        return ProjectIRProvidedPropertySlot.NULL_EXTENSION


type ProjectIRProvidedProperty = (
    ProjectIRProvidedOutputShape
    | ProjectIRProvidedBagMultiplicity
    | ProjectIRProvidedClosedBindings
    | ProjectIRProvidedRelationOrdering
    | ProjectIRProvidedLocalGrainEvidence
    | ProjectIRProvidedCardinalityUpperBound
    | ProjectIRProvidedEvaluationPolicy
    | ProjectIRUnavailableProvidedProperty
)


class ProjectIRRequiredPropertySlot(StrEnum):
    """Consumer input requirement slots; only row shape has current authority."""

    ROW_SHAPE = "row_shape"
    ORDERING = "ordering"
    LOCAL_GRAIN_EVIDENCE = "local_grain_evidence"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRequiredRowShape:
    """Exact consumer-side relation row-shape requirement."""

    input_slot: ProjectIRInputSlotOccurrence
    row_shape: ProjectIRRowShape
    authority: ProjectIRResolvedRelationAnchor

    def __post_init__(self) -> None:
        if type(self.input_slot) is not ProjectIRInputSlotOccurrence:
            raise TypeError("Required row shape requires an input-slot occurrence.")
        if type(self.row_shape) is not ProjectIRRowShape:
            raise TypeError("Required row shape requires an exact row shape.")
        if type(self.authority) is not ProjectIRResolvedRelationAnchor:
            raise TypeError("Required row shape requires exact resolution authority.")
        if (
            self.authority.reference.owner != self.input_slot.consumer.anchor.identity
            or self.authority.target != self.row_shape.relation.identity
        ):
            raise ValueError("Required row shape must retain consumer-side authority.")

    @property
    def property_slot(self) -> ProjectIRRequiredPropertySlot:
        return ProjectIRRequiredPropertySlot.ROW_SHAPE


type ProjectIRRequiredInputProperty = ProjectIRRequiredRowShape


class ProjectIRDeterminismEvidence(StrEnum):
    """Determinism/volatility evidence states reserved by the route lock."""

    UNKNOWN = "unknown"
    DETERMINISTIC = "deterministic"
    VOLATILE = "volatile"


class ProjectIRErrorBehaviorEvidence(StrEnum):
    """May-error evidence states reserved by the route lock."""

    UNKNOWN = "unknown"
    MAY_ERROR = "may_error"
    CANNOT_ERROR = "cannot_error"


class ProjectIRSideEffectEvidence(StrEnum):
    """Side-effect evidence states reserved by the route lock."""

    UNKNOWN = "unknown"
    HAS_SIDE_EFFECTS = "has_side_effects"
    SIDE_EFFECT_FREE = "side_effect_free"


class ProjectIREvaluationCountEvidence(StrEnum):
    """Evaluation-count sensitivity evidence states reserved by the route lock."""

    UNKNOWN = "unknown"
    SENSITIVE = "sensitive"
    INSENSITIVE = "insensitive"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIREffectEvidence:
    """Current conservative effect evidence outside occurrence identity."""

    output: ProjectIRCurrentOutput
    determinism: ProjectIRDeterminismEvidence
    error_behavior: ProjectIRErrorBehaviorEvidence
    side_effects: ProjectIRSideEffectEvidence
    evaluation_count: ProjectIREvaluationCountEvidence

    def __post_init__(self) -> None:
        _validate_current_output(self.output, label="Effect evidence")
        expected_types = (
            (self.determinism, ProjectIRDeterminismEvidence),
            (self.error_behavior, ProjectIRErrorBehaviorEvidence),
            (self.side_effects, ProjectIRSideEffectEvidence),
            (self.evaluation_count, ProjectIREvaluationCountEvidence),
        )
        if any(type(value) is not expected for value, expected in expected_types):
            raise TypeError("Effect evidence requires exact typed axis values.")
        if (
            self.determinism is not ProjectIRDeterminismEvidence.UNKNOWN
            or self.error_behavior is not ProjectIRErrorBehaviorEvidence.UNKNOWN
            or self.side_effects is not ProjectIRSideEffectEvidence.UNKNOWN
            or self.evaluation_count is not ProjectIREvaluationCountEvidence.UNKNOWN
        ):
            raise ValueError(
                "Current Project authority supports only unknown effect evidence."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIREstimateBoundary:
    """Distinct empty statistics seam until a legitimate estimator exists."""

    scope: ProjectIRSnapshotScope
    statistics: tuple[Never, ...] = ()

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Estimate boundary requires an exact snapshot scope.")
        if type(self.statistics) is not tuple:
            raise TypeError("Estimate statistics must be an exact tuple.")
        if self.statistics:
            raise ValueError("Current Project IR has no legitimate estimate producer.")


_CURRENT_OUTPUT_TYPES = (
    ProjectIRScalarFieldOutput,
    ProjectIRStageScalarFieldOutput,
    ProjectIRRelationRowOutput,
)
_PROVIDED_PROPERTY_TYPES = (
    ProjectIRProvidedOutputShape,
    ProjectIRProvidedBagMultiplicity,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedRelationOrdering,
    ProjectIRProvidedLocalGrainEvidence,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRUnavailableProvidedProperty,
)


def _validate_current_output(output: object, *, label: str) -> None:
    if type(output) not in _CURRENT_OUTPUT_TYPES:
        raise TypeError(f"{label} requires a typed current output.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPropertyStage:
    """Typed semantic-property layer over exactly one unchanged structural stage."""

    structural: ProjectIRStructuralStage
    estimates: ProjectIREstimateBoundary = field(compare=False, hash=False)
    outputs: tuple[ProjectIRCurrentOutput, ...] = ()
    provided: tuple[ProjectIRProvidedProperty, ...] = ()
    required: tuple[ProjectIRRequiredInputProperty, ...] = ()
    effects: tuple[ProjectIREffectEvidence, ...] = ()

    def __post_init__(self) -> None:
        if type(self.structural) is not ProjectIRStructuralStage:
            raise TypeError("Property stage requires an exact structural stage.")
        if type(self.estimates) is not ProjectIREstimateBoundary:
            raise TypeError("Property stage requires an exact estimate boundary.")
        if self.estimates.scope is not self.structural.scope:
            raise ValueError("Property and estimate stages require one snapshot scope.")
        _require_exact_tuple(
            self.outputs, _CURRENT_OUTPUT_TYPES, label="Current outputs"
        )
        _require_exact_tuple(
            self.provided,
            _PROVIDED_PROPERTY_TYPES,
            label="Provided properties",
        )
        _require_exact_tuple(
            self.required,
            ProjectIRRequiredRowShape,
            label="Required input properties",
        )
        _require_exact_tuple(
            self.effects,
            ProjectIREffectEvidence,
            label="Effect evidence",
        )
        if len(self.outputs) != len(self.structural.outputs) or any(
            model.occurrence is not occurrence
            for model, occurrence in zip(
                self.outputs,
                self.structural.outputs,
                strict=True,
            )
        ):
            raise ValueError(
                "Property outputs must retain exact structural output coordinates."
            )
        concrete_subjects = tuple(
            item
            for item in self.structural.subjects
            if type(item) is ProjectIRConcreteRelationSubject
        )
        for output in self.outputs:
            matches = tuple(
                subject
                for subject in concrete_subjects
                if subject.anchor == output.row_shape.relation
            )
            if (
                len(matches) != 1
                or matches[0].evidence is not output.row_shape.evidence
            ):
                raise ValueError(
                    "Property outputs require exact retained concrete subject authority."
                )
        if any(
            not any(item.output is output for output in self.outputs)
            for item in self.provided
        ):
            raise ValueError("Provided properties require retained output occurrences.")
        provided_slots = tuple(ProjectIRProvidedPropertySlot)
        provided_keys = tuple(
            (
                item.output.occurrence.ref.position,
                provided_slots.index(item.property_slot),
            )
            for item in self.provided
        )
        if len(set(provided_keys)) != len(provided_keys):
            raise ValueError("Provided property slots require unique authority.")
        if provided_keys != tuple(sorted(provided_keys)):
            raise ValueError("Provided properties must retain structural order.")
        if any(
            not any(item.input_slot is slot for slot in self.structural.input_slots)
            for item in self.required
        ):
            raise ValueError("Required properties require retained consumer slots.")
        if any(
            not any(
                use.slot is item.input_slot
                and type(use) is ProjectIRUseOccurrence
                and type(use.anchor) is ProjectIRResolvedRelationAnchor
                and use.anchor is item.authority
                for use in self.structural.uses
            )
            for item in self.required
        ):
            raise ValueError(
                "Required properties require exact structural use authority."
            )
        required_slots = tuple(ProjectIRRequiredPropertySlot)
        required_keys = tuple(
            (
                item.input_slot.ref.position,
                required_slots.index(item.property_slot),
            )
            for item in self.required
        )
        if len(set(required_keys)) != len(required_keys):
            raise ValueError("Required property slots require unique authority.")
        if required_keys != tuple(sorted(required_keys)):
            raise ValueError("Required properties must retain structural order.")
        if any(
            not any(item.output is output for output in self.outputs)
            for item in self.effects
        ):
            raise ValueError("Effect evidence requires retained output occurrences.")
        effect_positions = tuple(
            item.output.occurrence.ref.position for item in self.effects
        )
        if len(set(effect_positions)) != len(effect_positions):
            raise ValueError("One output cannot select an effect-evidence winner.")
        if effect_positions != tuple(sorted(effect_positions)):
            raise ValueError("Effect evidence must retain structural order.")

    @property
    def scope(self) -> ProjectIRSnapshotScope:
        return self.structural.scope

    @property
    def free_outer_bindings(self) -> tuple[object, ...]:
        return self.structural.free_outer_bindings
