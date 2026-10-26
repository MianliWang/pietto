"""Closed JOIN images, matching scopes and retained obligation transport."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockEntry,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRSingleMatchRetention,
    ProjectIRSingleMatchProofImage,
)
from pietto._project.project_query_block_ir_algebra import (
    ProjectIRComposedJoin,
    ProjectIRJoinInputCorrespondence,
)
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir import ProjectIRPlanNodeRef
from pietto._project.project_join_conditions import ProjectJoinConditionField
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_joined_row_filter import ProjectConcreteJoinedRowFilter
from pietto._project.project_scalar_references import ProjectScalarEnvironmentField
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


def join_images(entry: ProjectIRQueryBlockEntry) -> tuple[ProjectIRComposedJoin, ...]:
    """Read complete current images from the already VERIFIED snapshot."""
    tail = joined_tail(entry)
    if tail is None:
        return ()
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    region = tail.joined_semantics.row_source.region
    # A joined tail always reads its composed JOIN prefix.
    if entry.join_prefix is None:
        raise ValueError("JOIN images must cover the exact ordered semantic region.")
    if entry.join_prefix.region is not region:
        raise ValueError("JOIN image root does not match its semantic region.")
    images = entry.join_prefix.joins
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


def compiled_join_rejections(records, join):
    """Project the resolved graph into the original per-use ON proof."""
    from pietto._project.project_sql_emission_joins import resolved_null_rejected_ports

    nodes = {}
    for address, record in records.items():
        if address.kind == "read":
            nodes[address] = ("read", None, (), (record.get("use"), record.get("port")))
        elif address.kind == "operation":
            role, token = record.get("operator")
            kind = "logical" if role == "binary" and token in ("and", "or") else role
            nodes[address] = (kind, token, record.get("operands"), None)
        elif address.kind in ("literal", "parameter_read"):
            nodes[address] = ("opaque", None, (), None)
    equalities = tuple(
        (nodes[records[a].get("left")][3], nodes[records[a].get("right")][3])
        for a in join.get("equalities")
    )
    return resolved_null_rejected_ports(
        AuthoredJoinKind(join.get("kind")), equalities, join.get("predicate"), nodes
    )
