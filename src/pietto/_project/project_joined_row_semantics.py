"""Private Phase-63 bridge to exact joined-row lineage and properties."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldNullability,
)
from pietto._project.module_attribution import (
    ProjectModuleAttributionFactSet,
    ProjectModuleRelationLineage,
    ProjectModuleRelationOutputFieldAttribution,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
    ProjectModuleRowFieldLineage,
    ProjectModuleSourceFieldOrigin,
)
from pietto._project.project_ir_joins import (
    ProjectIRJoinOutputProperties,
    ProjectIRJoinUnavailableProperty,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRJoinedRowField,
    ProjectIRProvidedNullExtension,
    ProjectIRRowField,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputFDIndex,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueFD,
    ProjectIRProvidedIntrinsicGrain,
)
from pietto._project.project_multifact import (
    ProjectMultiFactConcreteRegion,
)
from pietto._project.project_query_block import ProjectVerifiedJoinedRowSource
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedLetNamespaces,
    ProjectJoinedLetNamespaceResult,
    ProjectJoinedLetValue,
    ProjectJoinedScalarNamespace,
    ProjectNonConcreteJoinedLetNamespaces,
)
from pietto._project.project_scalar_references import (
    ProjectScalarEnvironmentField,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedRowPropertyBridge:
    """Exact final Phase-62 properties without derivation or interpretation."""

    row_source: ProjectVerifiedJoinedRowSource = field(
        repr=False,
        compare=False,
        hash=False,
    )
    multifact_region: ProjectMultiFactConcreteRegion = field(
        repr=False,
        compare=False,
        hash=False,
    )
    properties: ProjectIRJoinOutputProperties = field(init=False)

    def __post_init__(self) -> None:
        if type(self.row_source) is not ProjectVerifiedJoinedRowSource or (
            type(self.multifact_region) is not ProjectMultiFactConcreteRegion
            or self.multifact_region.region is not self.row_source.region
        ):
            raise ValueError("Joined properties require exact shared Phase-62 roots.")
        properties = self.multifact_region.final_properties
        if (
            type(properties) is not ProjectIRJoinOutputProperties
            or properties.join is not self.row_source.region.joins[-1]
            or properties.relational.output is not self.row_source.final_output
        ):
            raise ValueError("Joined properties require the exact final JOIN output.")
        object.__setattr__(self, "properties", properties)

    @property
    def relational(self) -> ProjectIROutputRelationalProperties:
        return self.properties.relational

    @property
    def null_extension(
        self,
    ) -> ProjectIRProvidedNullExtension | ProjectIRJoinUnavailableProperty:
        return self.properties.null_extension

    @property
    def ordering(self) -> ProjectIRJoinUnavailableProperty:
        return self.properties.ordering

    @property
    def keys(self) -> tuple[ProjectIROutputCandidateKey, ...]:
        return self.relational.keys

    @property
    def fds(self) -> tuple[ProjectIROutputValueFD, ...]:
        return self.relational.fds

    @property
    def fd_index(self) -> ProjectIROutputFDIndex:
        return self.relational.fd_index

    @property
    def grain(self) -> ProjectIRProvidedIntrinsicGrain:
        return self.relational.grain


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedRowFieldSemantics:
    """One final joined occurrence bridged to existing upstream lineage."""

    scalar_field: ProjectScalarEnvironmentField = field(
        repr=False,
        compare=False,
        hash=False,
    )
    joined_field: ProjectIRJoinedRowField = field(
        repr=False,
        compare=False,
        hash=False,
    )
    property_field: ProjectIROutputFieldOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_properties: ProjectIROutputRelationalProperties = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_field: ProjectIROutputFieldOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    canonical_field: ProjectModuleRowFieldIdentity
    lineage: ProjectModuleRowFieldLineage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_origin: ProjectModuleSourceFieldOrigin | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    output_attribution: ProjectModuleRelationOutputFieldAttribution | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    source_roots: tuple[ProjectModuleRowFieldIdentity, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.scalar_field) is not ProjectScalarEnvironmentField or (
            type(self.joined_field) is not ProjectIRJoinedRowField
            or self.scalar_field.source_field is not self.joined_field
            or self.scalar_field.position != self.joined_field.field_position
        ):
            raise ValueError("Joined field semantics require the exact scalar field.")
        if (
            type(self.property_field) is not ProjectIROutputFieldOccurrence
            or self.property_field.field_position != self.joined_field.field_position
            or self.property_field.evidence is not self.joined_field.evidence
            or self.property_field.effective_nullability
            is not self.joined_field.effective_nullability
        ):
            raise ValueError("Joined field semantics require exact final properties.")
        if (
            type(self.input_properties) is not ProjectIROutputRelationalProperties
            or type(self.input_field) is not ProjectIROutputFieldOccurrence
            or self.input_field.output is not self.input_properties.output
            or self.input_properties.output.occurrence
            is not self.joined_field.introduction_use.output
            or self.input_field.evidence is not self.joined_field.evidence
        ):
            raise ValueError("Joined field semantics require its exact input output.")
        if type(self.canonical_field) is not ProjectModuleRowFieldIdentity or (
            type(self.lineage) is not ProjectModuleRowFieldLineage
            or self.lineage.field is not self.canonical_field
        ):
            raise ValueError("Joined field semantics require exact canonical lineage.")
        if (
            self.scalar_field.value_type.nullability.value
            != self.joined_field.effective_nullability.value
        ):
            raise ValueError("Joined field scalar nullability must remain coherent.")
        if self.canonical_field.kind is ProjectModuleRowFieldKind.SOURCE_FIELD:
            if (
                type(self.source_origin) is not ProjectModuleSourceFieldOrigin
                or self.source_origin.source_field is not self.canonical_field
                or self.output_attribution is not None
            ):
                raise ValueError("Source fields require exact source-origin evidence.")
        elif self.canonical_field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT:
            if (
                self.source_origin is not None
                or type(self.output_attribution)
                is not ProjectModuleRelationOutputFieldAttribution
                or self.output_attribution.identity is not self.canonical_field
                or self.output_attribution.semantic_field
                is not self.joined_field.evidence
            ):
                raise ValueError(
                    "Relation fields require exact output-attribution evidence."
                )
        else:
            raise ValueError("Joined inputs cannot use shape-field identity.")
        object.__setattr__(
            self,
            "source_roots",
            tuple(path.root_field for path in self.lineage.paths),
        )

    @property
    def effective_nullability(self) -> ProjectRowFieldNullability:
        return self.joined_field.effective_nullability

    @property
    def nulling_joins(self):
        return self.joined_field.nulling_joins

    @property
    def introduction_use(self):
        return self.joined_field.introduction_use


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedRowLineageIssue:
    """One final occurrence whose exact upstream lineage is non-concrete."""

    scalar_field: ProjectScalarEnvironmentField = field(
        repr=False,
        compare=False,
        hash=False,
    )
    joined_field: ProjectIRJoinedRowField = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_field: ProjectIROutputFieldOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    canonical_field: ProjectModuleRowFieldIdentity
    lineage: ProjectModuleRelationLineage = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if (
            self.scalar_field.source_field is not self.joined_field
            or self.input_field.evidence is not self.joined_field.evidence
            or self.lineage.owner != self.canonical_field.owner
            or self.lineage.status is ProjectRelationRowSchemaStatus.CONCRETE
        ):
            raise ValueError("Lineage issue requires exact non-concrete authority.")


class ProjectJoinedRowSemanticsNonConcreteReason(StrEnum):
    LET_NAMESPACE_NON_CONCRETE = "let_namespace_non_concrete"
    UPSTREAM_LINEAGE_NON_CONCRETE = "upstream_lineage_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedRowSemantics:
    """One closed post-JOIN row-semantic and property authority."""

    namespaces: ProjectConcreteJoinedLetNamespaces = field(
        repr=False,
        compare=False,
        hash=False,
    )
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    property_bridge: ProjectJoinedRowPropertyBridge
    fields: tuple[ProjectJoinedRowFieldSemantics, ...]
    post_let: ProjectJoinedScalarNamespace = field(init=False)

    def __post_init__(self) -> None:
        if type(self.namespaces) is not ProjectConcreteJoinedLetNamespaces or (
            type(self.attribution) is not ProjectModuleAttributionFactSet
            or type(self.property_bridge) is not ProjectJoinedRowPropertyBridge
            or self.property_bridge.row_source
            is not self.namespaces.binding_environment.row_source
        ):
            raise ValueError("Concrete joined semantics require exact shared roots.")
        scalar_fields = self.namespaces.binding_environment.scalar_environment.fields
        if (
            type(self.fields) is not tuple
            or len(self.fields) != len(scalar_fields)
            or any(
                type(item) is not ProjectJoinedRowFieldSemantics
                or item.scalar_field is not scalar_field
                or item.property_field
                is not self.property_bridge.relational.fields[position]
                for position, (item, scalar_field) in enumerate(
                    zip(self.fields, scalar_fields, strict=True)
                )
            )
        ):
            raise ValueError("Concrete joined semantics must cover final row order.")
        historical = self.property_bridge.row_source.historical_semantic_facts.state
        if (
            historical.status is not ProjectRelationRowSchemaStatus.DEFERRED
            or historical.reason
            is not ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
        ):
            raise ValueError("Joined semantics must preserve historical deferral.")
        object.__setattr__(self, "post_let", self.namespaces.post_let)

    @property
    def row_source(self) -> ProjectVerifiedJoinedRowSource:
        return self.property_bridge.row_source

    @property
    def final_output(self) -> ProjectIRJoinRowOutput:
        return self.row_source.final_output

    @property
    def multifact_region(self) -> ProjectMultiFactConcreteRegion:
        return self.property_bridge.multifact_region

    @property
    def let_values(self) -> tuple[ProjectJoinedLetValue, ...]:
        return self.namespaces.values


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedRowSemantics:
    """One closed upstream blocker with no concrete row-semantic stage."""

    namespaces: ProjectJoinedLetNamespaceResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectJoinedRowSemanticsNonConcreteReason
    upstream_blocker: ProjectNonConcreteJoinedLetNamespaces | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    lineage_issues: tuple[ProjectJoinedRowLineageIssue, ...] = ()
    post_let: None = field(init=False, default=None)
    property_bridge: None = field(init=False, default=None)
    fields: tuple[ProjectJoinedRowFieldSemantics, ...] = field(
        init=False,
        default=(),
    )

    def __post_init__(self) -> None:
        if type(self.attribution) is not ProjectModuleAttributionFactSet or (
            type(self.reason) is not ProjectJoinedRowSemanticsNonConcreteReason
        ):
            raise TypeError("Joined semantic terminal requires exact roots and reason.")
        if (
            self.reason
            is ProjectJoinedRowSemanticsNonConcreteReason.LET_NAMESPACE_NON_CONCRETE
        ):
            if (
                type(self.namespaces) is not ProjectNonConcreteJoinedLetNamespaces
                or self.upstream_blocker is not self.namespaces
                or self.lineage_issues
            ):
                raise ValueError("LET terminal must retain only its exact blocker.")
        elif (
            type(self.namespaces) is not ProjectConcreteJoinedLetNamespaces
            or self.upstream_blocker is not None
            or not self.lineage_issues
            or any(
                type(issue) is not ProjectJoinedRowLineageIssue
                for issue in self.lineage_issues
            )
        ):
            raise ValueError("Lineage terminal requires complete exact issues.")


type ProjectJoinedRowSemanticsResult = (
    ProjectConcreteJoinedRowSemantics | ProjectNonConcreteJoinedRowSemantics
)


def _require_attribution_root(
    namespaces: ProjectJoinedLetNamespaceResult,
    attribution: ProjectModuleAttributionFactSet,
) -> None:
    if (
        type(namespaces)
        not in {
            ProjectConcreteJoinedLetNamespaces,
            ProjectNonConcreteJoinedLetNamespaces,
        }
        or type(attribution) is not ProjectModuleAttributionFactSet
    ):
        raise TypeError("Joined semantics require exact Slice-5 and attribution roots.")
    analysis = namespaces.binding_environment.row_source.verification.root
    if attribution._authority.semantic_facts is not (
        analysis.evaluation.project_plan.semantic_facts
    ):
        raise ValueError("Joined semantics require the same project semantic root.")


def _property_bridge(
    namespaces: ProjectConcreteJoinedLetNamespaces,
) -> ProjectJoinedRowPropertyBridge:
    row_source = namespaces.binding_environment.row_source
    matches = tuple(
        item
        for item in row_source.verification.root.concrete_regions
        if item.region is row_source.region
    )
    if len(matches) != 1:
        raise ValueError("Joined semantics require one exact multi-fact region.")
    return ProjectJoinedRowPropertyBridge(
        row_source=row_source,
        multifact_region=matches[0],
    )


def _input_field(
    bridge: ProjectJoinedRowPropertyBridge,
    joined_field: ProjectIRJoinedRowField,
) -> tuple[ProjectIROutputRelationalProperties, ProjectIROutputFieldOccurrence]:
    matches = tuple(
        item
        for item in bridge.row_source.verification.root.base_relational.outputs
        if item.output.occurrence is joined_field.introduction_use.output
    )
    if len(matches) != 1:
        raise ValueError("Joined field requires one exact standalone input output.")
    input_properties = matches[0]
    fields = tuple(
        item
        for item in input_properties.fields
        if item.evidence is joined_field.evidence
    )
    if len(fields) != 1:
        raise ValueError("Joined field requires one exact input semantic occurrence.")
    return input_properties, fields[0]


def _canonical_field(
    attribution: ProjectModuleAttributionFactSet,
    input_properties: ProjectIROutputRelationalProperties,
    input_field: ProjectIROutputFieldOccurrence,
) -> ProjectModuleRowFieldIdentity:
    shape_field = input_properties.output.row_shape.fields[input_field.field_position]
    if shape_field.evidence is not input_field.evidence:
        raise ValueError("Input shape and relational field evidence must agree.")
    if type(shape_field) is ProjectIRRowField:
        return shape_field.anchor.identity
    owner = input_properties.output.row_shape.relation.identity
    output_matches = tuple(
        item.identity
        for item in attribution.find_relation_output_fields(owner)
        if item.semantic_field is input_field.evidence
        and item.identity.field_position == input_field.field_position
    )
    source_matches = tuple(
        item.source_field
        for item in attribution.source_field_origins
        if item.source_field.owner == owner
        and item.source_field.field_position == input_field.field_position
    )
    matches = (*output_matches, *source_matches)
    if len(matches) != 1:
        raise ValueError("Input field requires one existing canonical identity.")
    return matches[0]


def _field_semantics(
    *,
    attribution: ProjectModuleAttributionFactSet,
    bridge: ProjectJoinedRowPropertyBridge,
    scalar_field: ProjectScalarEnvironmentField,
) -> ProjectJoinedRowFieldSemantics | ProjectJoinedRowLineageIssue:
    joined_field = scalar_field.source_field
    if type(joined_field) is not ProjectIRJoinedRowField:
        raise TypeError("Joined semantics require exact joined field occurrences.")
    property_field = bridge.relational.fields[joined_field.field_position]
    input_properties, input_field = _input_field(bridge, joined_field)
    canonical = _canonical_field(attribution, input_properties, input_field)
    lineages = attribution.find_row_lineage(canonical.owner)
    if len(lineages) != 1:
        raise ValueError("Canonical field requires one retained relation lineage.")
    relation_lineage = lineages[0]
    if relation_lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return ProjectJoinedRowLineageIssue(
            scalar_field=scalar_field,
            joined_field=joined_field,
            input_field=input_field,
            canonical_field=canonical,
            lineage=relation_lineage,
        )
    field_lineages = tuple(
        item for item in relation_lineage.fields if item.field is canonical
    )
    if len(field_lineages) != 1:
        raise ValueError("Canonical field requires one exact existing field lineage.")
    lineage = field_lineages[0]
    source_origin: ProjectModuleSourceFieldOrigin | None = None
    output_attribution: ProjectModuleRelationOutputFieldAttribution | None = None
    if canonical.kind is ProjectModuleRowFieldKind.SOURCE_FIELD:
        origins = attribution.find_source_field_origin(canonical)
        if len(origins) != 1:
            raise ValueError("Source field requires one exact origin.")
        source_origin = origins[0]
    elif canonical.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT:
        outputs = attribution.find_relation_output_field(canonical)
        if len(outputs) != 1 or outputs[0].semantic_field is not joined_field.evidence:
            raise ValueError("Relation field requires exact output attribution.")
        output_attribution = outputs[0]
    else:
        raise ValueError("Joined inputs cannot originate from shape-field identity.")
    return ProjectJoinedRowFieldSemantics(
        scalar_field=scalar_field,
        joined_field=joined_field,
        property_field=property_field,
        input_properties=input_properties,
        input_field=input_field,
        canonical_field=canonical,
        lineage=lineage,
        source_origin=source_origin,
        output_attribution=output_attribution,
    )


def build_project_joined_row_semantics(
    *,
    namespaces: ProjectJoinedLetNamespaceResult,
    attribution: ProjectModuleAttributionFactSet,
) -> ProjectJoinedRowSemanticsResult:
    """Attach exact Phase-62 row authority only to a successful POST_LET root."""

    _require_attribution_root(namespaces, attribution)
    if type(namespaces) is ProjectNonConcreteJoinedLetNamespaces:
        return ProjectNonConcreteJoinedRowSemantics(
            namespaces=namespaces,
            attribution=attribution,
            reason=ProjectJoinedRowSemanticsNonConcreteReason.LET_NAMESPACE_NON_CONCRETE,
            upstream_blocker=namespaces,
        )
    if type(namespaces) is not ProjectConcreteJoinedLetNamespaces:
        raise AssertionError("joined semantic root lost its exact Slice-5 variant")
    bridge = _property_bridge(namespaces)
    built = tuple(
        _field_semantics(
            attribution=attribution,
            bridge=bridge,
            scalar_field=scalar_field,
        )
        for scalar_field in namespaces.binding_environment.scalar_environment.fields
    )
    issues = tuple(item for item in built if type(item) is ProjectJoinedRowLineageIssue)
    if issues:
        return ProjectNonConcreteJoinedRowSemantics(
            namespaces=namespaces,
            attribution=attribution,
            reason=(
                ProjectJoinedRowSemanticsNonConcreteReason.UPSTREAM_LINEAGE_NON_CONCRETE
            ),
            lineage_issues=issues,
        )
    fields = tuple(
        item for item in built if type(item) is ProjectJoinedRowFieldSemantics
    )
    if len(fields) != len(built):
        raise AssertionError("joined field semantics lost a closed result variant")
    return ProjectConcreteJoinedRowSemantics(
        namespaces=namespaces,
        attribution=attribution,
        property_bridge=bridge,
        fields=fields,
    )
