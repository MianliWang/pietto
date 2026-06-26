"""Private immutable models for Semantic Metadata Artifact v1 success data."""

from __future__ import annotations

from dataclasses import dataclass

from pietto.errors import Diagnostic

SEMANTIC_METADATA_ARTIFACT_NAME = "Semantic Metadata Artifact v1"
SEMANTIC_METADATA_SCHEMA_VERSION = 1
SEMANTIC_METADATA_COMMAND = "explain"


@dataclass(frozen=True, slots=True)
class SemanticMetadataLocation:
    """A normalized source location detached from AST and IR objects."""

    path: str | None
    line: int
    column: int
    end_line: int | None
    end_column: int | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataType:
    """A normalized type summary for private artifact construction."""

    status: str
    name: str | None
    kind: str
    canonical_name: str | None
    canonical_kind: str
    nullability: str
    support_posture: str


@dataclass(frozen=True, slots=True)
class SemanticMetadataField:
    """One ordered row-schema field summary."""

    name: str
    type: SemanticMetadataType
    nullability: str
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataSchema:
    """An ordered row-schema summary."""

    fields: tuple[SemanticMetadataField, ...]


@dataclass(frozen=True, slots=True)
class SemanticMetadataSourceIdentity:
    """Single-file source identity for the private artifact model."""

    path: str | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataDefinition:
    """One source-level definition summary."""

    name: str
    kind: str
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataSource:
    """One source declaration summary without connector internals."""

    name: str
    schema: SemanticMetadataSchema
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataRelationInput:
    """The immediate input relation summary for a table or query."""

    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class SemanticMetadataFieldLeaf:
    """A direct resolved field-reference leaf."""

    relation: str
    field: str
    qualifier: tuple[str, ...]
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataExpressionSummary:
    """A bounded expression summary without raw expression trees."""

    expression_kind: str
    type: SemanticMetadataType | None
    field_leaves: tuple[SemanticMetadataFieldLeaf, ...]
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataClausePresence:
    """Presence bit for a query clause without expression details."""

    present: bool


@dataclass(frozen=True, slots=True)
class SemanticMetadataOrderBy:
    """One order-by item summary."""

    scope: str
    direction: str
    expression_kind: str
    field_leaves: tuple[SemanticMetadataFieldLeaf, ...]
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataLimit:
    """One static LIMIT summary."""

    value: int
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataProjection:
    """One projection summary."""

    name: str | None
    expression_kind: str
    type: SemanticMetadataType | None
    field_leaves: tuple[SemanticMetadataFieldLeaf, ...]
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataAggregate:
    """One aggregate call summary."""

    function: str
    arguments: tuple[SemanticMetadataExpressionSummary, ...]
    result_type: SemanticMetadataType
    projection_name: str | None
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataLineage:
    """Basic projection lineage over direct field leaves only."""

    output: str | None
    field_leaves: tuple[SemanticMetadataFieldLeaf, ...]


@dataclass(frozen=True, slots=True)
class SemanticMetadataQuery:
    """A relation query-posture summary."""

    where: SemanticMetadataClausePresence
    group_keys: tuple[SemanticMetadataFieldLeaf, ...]
    satisfying: SemanticMetadataClausePresence
    order_by: tuple[SemanticMetadataOrderBy, ...]
    limit: SemanticMetadataLimit | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataRelation:
    """One table or query relation summary."""

    name: str
    kind: str
    input: SemanticMetadataRelationInput
    input_schema: SemanticMetadataSchema
    output_schema: SemanticMetadataSchema
    projections: tuple[SemanticMetadataProjection, ...]
    query: SemanticMetadataQuery
    aggregates: tuple[SemanticMetadataAggregate, ...]
    lineage: tuple[SemanticMetadataLineage, ...]
    location: SemanticMetadataLocation | None


@dataclass(frozen=True, slots=True)
class SemanticMetadataPayload:
    """The normalized private metadata payload for a successful artifact."""

    source: SemanticMetadataSourceIdentity
    definitions: tuple[SemanticMetadataDefinition, ...]
    sources: tuple[SemanticMetadataSource, ...]
    relations: tuple[SemanticMetadataRelation, ...]
    types: tuple[SemanticMetadataType, ...]


@dataclass(frozen=True, slots=True)
class SemanticMetadataArtifact:
    """The private success envelope for Semantic Metadata Artifact v1."""

    artifact: str
    schema_version: int
    command: str
    ok: bool
    path: str | None
    diagnostics: tuple[Diagnostic, ...]
    metadata: SemanticMetadataPayload
