"""Closed JOIN images, matching scopes and retained obligation transport."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockSnapshot,
    ProjectIRQueryBlockEntry,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRSingleMatchRetention,
    ProjectIRSingleMatchProofImage,
)
from pietto._project.project_query_block_ir_algebra import (
    ProjectIRComposedJoin,
    ProjectIRJoinInputCorrespondence,
)
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRJoinMatchFieldPair,
)
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir import ProjectIRPlanNodeRef
from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
from pietto._project.project_join_conditions import ProjectJoinConditionField
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_joined_row_filter import ProjectConcreteJoinedRowFilter
from pietto._project.project_scalar_references import ProjectScalarEnvironmentField
from pietto._project.project_relationship_conditions import (
    ProjectRelationshipEqualityCorrespondence,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchAssessment,
    ProjectSingleMatchRequest,
)
from pietto.errors import Diagnostic

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLSymbol
    from pietto._project.project_sql_plan_expressions import ProjectSQLMatchSite

__all__: tuple[str, ...] = ()


def joined_tail(
    entry: ProjectIRQueryBlockEntry,
) -> ProjectConcreteJoinedRowFilter | None:
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput) and isinstance(
        entry.semantic_entry.root, ProjectConcreteJoinedQualify
    ):
        return entry.semantic_entry.root.window_stage.input_aggregation.input_filter
    return None


def join_images(
    root: ProjectIRQueryBlockSnapshot, entry: ProjectIRQueryBlockEntry
) -> tuple[ProjectIRComposedJoin, ...]:
    """Read complete current images from the already VERIFIED snapshot."""
    tail = joined_tail(entry)
    if tail is None:
        return ()
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    region = tail.joined_semantics.row_source.region
    if entry.join_prefix is not None:
        if entry.join_prefix.region is not region:
            raise ValueError("JOIN image root does not match its semantic region.")
        images = entry.join_prefix.joins
    else:
        images = tuple(
            image
            for image in root.retained_joins
            if any(image.source is source for source in region.joins)
        )
    if len(images) != len(region.joins) or any(
        image.source is not source
        for image, source in zip(images, region.joins, strict=True)
    ):
        raise ValueError("JOIN images must cover the exact ordered semantic region.")
    return images


def input_predecessor(
    image: ProjectIRJoinInputCorrespondence, earlier: tuple[ProjectIRComposedJoin, ...]
) -> ProjectIRComposedJoin | None:
    matches = tuple(
        join
        for join in earlier
        if image.use.output is join.output.occurrence
        and image.source_properties.output is join.source.output
    )
    if image.producer is not None:
        if matches:
            raise ValueError(
                "An external JOIN input cannot also be an internal predecessor."
            )
        return None
    if len(matches) != 1:
        raise ValueError("Internal JOIN input requires one exact earlier output.")
    return matches[0]


def condition_field_keys(
    join: ProjectIRComposedJoin,
) -> tuple[tuple[ProjectJoinConditionField | None, ...], ...]:
    """Match existing pre-match fields to original input occurrences, never names."""
    source = join.source
    if not isinstance(source, ProjectCurrentBinaryJoin):
        return tuple(
            tuple(None for _ in image.source_properties.fields) for image in join.inputs
        )
    right = (
        source.right_input.fields
        if source.input_scope is None
        else source.input_scope.bindings[source.use.identity.join_position + 1].fields
    )
    origins = (
        source.left_fields,
        tuple((source.use.target_binding, member) for member in right),
    )
    result = []
    for image, fields in zip(join.inputs, origins, strict=True):
        if len(fields) != len(image.source_properties.fields):
            raise ValueError("Pre-match origins must cover the complete input.")
        local = []
        for binding, original in fields:
            matches = tuple(
                f
                for f in join.condition.environment.fields
                if f.binding is binding and f.input_field is original
            )
            if len(matches) > 1:
                raise ValueError("Pre-match field occurrence has multiple images.")
            local.append(matches[0] if matches else None)
        result.append(tuple(local))
    return tuple(result)


def base_matches(
    join: ProjectIRComposedJoin,
) -> tuple[
    tuple[
        ProjectIRJoinMatchFieldPair | ProjectRelationshipEqualityCorrespondence,
        ProjectDirectionalRelationshipMatchGuarantee,
        int,
        int,
    ],
    ...,
]:
    source = join.source
    if isinstance(source, ProjectIRBinaryJoinOccurrence):
        width = len(source.left_input.fields)
        return tuple(
            (
                pair,
                source.guarantee,
                pair.left.field_position,
                pair.right.field_position - width,
            )
            for pair in source.matches
        )
    condition = join.condition
    if not condition.base_conditions:
        return ()
    guarantee = condition.base_guarantee
    if (
        guarantee is None
        or len(condition.base_conditions) != 1
        or len(condition.environment.source_candidates) != 1
    ):
        raise ValueError(
            "Direct relationship matching requires exact directional authority."
        )
    source_binding = condition.environment.source_candidates[0]
    right = (
        source.right_input.fields
        if source.input_scope is None
        else source.input_scope.bindings[source.use.identity.join_position + 1].fields
    )
    result = []
    for correspondence in condition.base_conditions[0].correspondences:
        endpoints = (correspondence.endpoint_zero, correspondence.endpoint_one)
        sources = tuple(
            e for e in endpoints if e.endpoint is guarantee.direction.source
        )
        targets = tuple(
            e for e in endpoints if e.endpoint is guarantee.direction.target
        )
        if len(sources) != 1 or len(targets) != 1:
            raise ValueError("Relationship equality lost its directional endpoints.")
        left_positions = tuple(
            i
            for i, (binding, original) in enumerate(source.left_fields)
            if binding is source_binding
            and original.evidence is sources[0].semantic_field
            and original.field_position == sources[0].field_identity.field_position
        )
        right_positions = tuple(
            i
            for i, original in enumerate(right)
            if original.evidence is targets[0].semantic_field
            and original.field_position == targets[0].field_identity.field_position
        )
        if len(left_positions) != 1 or len(right_positions) != 1:
            raise ValueError(
                "Relationship equality requires exact pre-match field images."
            )
        result.append(
            (correspondence, guarantee, left_positions[0], right_positions[0])
        )
    return tuple(result)


class ProjectSQLJoinPortKind(StrEnum):
    MATCH = "match"
    OUTPUT = "output"


class ProjectSQLJoinRows(StrEnum):
    MATCHED_PAIRS = "matched_pairs"
    LEFT_PRESERVED = "left_preserved"
    CARTESIAN_PAIRS = "cartesian_pairs"
    RIGHT_PRESERVED = "right_preserved"
    BOTH_PRESERVED = "both_preserved"
    LEFT_EXISTS = "left_exists"
    LEFT_NOT_EXISTS = "left_not_exists"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinInput:
    ref: ProjectSQLPlanRef
    join: ProjectSQLPlanRef
    ordinal: int
    source: ProjectIRJoinInputCorrespondence
    producer: ProjectSQLPlanRef | None
    predecessor: ProjectSQLPlanRef | None
    binding_use: ProjectSQLPlanRef | None
    ports: tuple[ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinPort:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    kind: ProjectSQLJoinPortKind
    position: int
    input: ProjectSQLPlanRef | None
    source: ProjectSQLPlanRef
    original: ProjectIROutputFieldOccurrence | ProjectIRJoinedRowField
    field: ProjectIROutputFieldOccurrence | ProjectIRJoinedRowField
    key: (
        ProjectJoinConditionField
        | ProjectIROutputFieldOccurrence
        | ProjectIRJoinedRowField
    )
    nulling: tuple[ProjectIRPlanNodeRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRelationshipMatch:
    ref: ProjectSQLPlanRef
    join: ProjectSQLPlanRef
    source: ProjectIRJoinMatchFieldPair | ProjectRelationshipEqualityCorrespondence
    guarantee: ProjectDirectionalRelationshipMatchGuarantee
    left: ProjectSQLPlanRef
    right: ProjectSQLPlanRef
    authored_operands: tuple[ProjectSQLPlanRef, ProjectSQLPlanRef]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoin:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    position: int
    source: ProjectIRComposedJoin
    kind: AuthoredJoinKind
    rows: ProjectSQLJoinRows
    inputs: tuple[ProjectSQLPlanRef, ProjectSQLPlanRef]
    outputs: tuple[ProjectSQLPlanRef, ...]
    equalities: tuple[ProjectSQLPlanRef, ...]
    on: ProjectSQLPlanRef | None
    site: ProjectSQLMatchSite | None
    properties: ProjectIROutputRelationalProperties


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinTail:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    join: ProjectSQLPlanRef
    source: ProjectConcreteJoinedRowFilter
    fields: tuple[ProjectScalarEnvironmentField, ...]
    ports: tuple[ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLMatchContext:
    join: ProjectSQLPlanRef
    ports: tuple[ProjectSQLJoinPort, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    _ports: Mapping[ProjectSQLPlanRef, ProjectSQLJoinPort] = field(
        init=False, repr=False
    )
    _symbols: Mapping[ProjectSQLPlanRef, ProjectSQLSymbol] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        ports = {p.ref: p for p in self.ports}
        symbols = {s.ref: s for s in self.symbols}
        if (
            len(ports) != len(self.ports)
            or len(symbols) != len(self.symbols)
            or len(symbols) != len(ports)
            or len({s.subject for s in self.symbols}) != len(ports)
            or any(
                p.block is not self.join or p.kind is not ProjectSQLJoinPortKind.MATCH
                for p in self.ports
            )
            or any(
                s.scope is not self.join or s.subject not in ports for s in self.symbols
            )
        ):
            raise ValueError("Matching context requires exact pre-match members.")
        object.__setattr__(self, "_ports", MappingProxyType(ports))
        object.__setattr__(self, "_symbols", MappingProxyType(symbols))

    def lookup(self, ref: ProjectSQLPlanRef) -> ProjectSQLJoinPort:
        symbol = self._symbols.get(ref)
        port = self._ports.get(ref if symbol is None else symbol.subject)
        if (
            port is None
            or port.block is not self.join
            or port.kind is not ProjectSQLJoinPortKind.MATCH
        ):
            raise ValueError("Reference is outside this pre-match scope.")
        return port


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSingleMatch:
    ref: ProjectSQLPlanRef
    source: ProjectIRSingleMatchRetention
    request: ProjectSingleMatchRequest
    assessment: ProjectSingleMatchAssessment
    joins: tuple[ProjectSQLPlanRef, ...]
    input_pairs: tuple[tuple[ProjectSQLPlanRef, ProjectSQLPlanRef], ...]
    proofs: tuple[ProjectSQLPlanRef, ...]
    diagnostic: Diagnostic | None
    downstream_enforcement_required: bool


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSingleMatchProof:
    ref: ProjectSQLPlanRef
    obligation: ProjectSQLPlanRef
    parent: ProjectSQLPlanRef | None
    source: ProjectIRSingleMatchProofImage
    joins: tuple[ProjectSQLPlanRef, ...]
    producers: tuple[ProjectSQLPlanRef, ...]
    children: tuple[ProjectSQLPlanRef, ...]


class ProjectSQLJoinDemandKind(StrEnum):
    JOIN_ROWS = "join_rows"
    MATCH_INPUT = "match_input"
    MATCH_FIELD = "match_field"
    OUTPUT_FIELD = "output_field"
    RELATIONSHIP_EQUALITY = "relationship_equality"
    POST_MATCH_SCOPE = "post_match_scope"
    SINGLE_MATCH = "single_match"
    PROOF_CONTEXT = "proof_context"


type ProjectSQLJoinWitness = (
    ProjectSQLJoin
    | ProjectSQLJoinInput
    | ProjectSQLJoinPort
    | ProjectSQLRelationshipMatch
    | ProjectSQLJoinTail
    | ProjectSQLSingleMatch
    | ProjectSQLSingleMatchProof
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLJoinDemandKind
    witness: ProjectSQLJoinWitness
    origin: ProjectSQLPlanRef
