"""Private JSON-compatible serializers for Semantic Metadata Artifact v1."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pietto.cli_json import diagnostic_to_json_dict
from pietto.errors import Diagnostic

from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SEMANTIC_METADATA_COMMAND,
    SEMANTIC_METADATA_SCHEMA_VERSION,
    SemanticMetadataAggregate,
    SemanticMetadataArtifact,
    SemanticMetadataClausePresence,
    SemanticMetadataDefinition,
    SemanticMetadataExpressionSummary,
    SemanticMetadataField,
    SemanticMetadataFieldLeaf,
    SemanticMetadataLimit,
    SemanticMetadataLineage,
    SemanticMetadataLocation,
    SemanticMetadataOrderBy,
    SemanticMetadataPayload,
    SemanticMetadataProjection,
    SemanticMetadataQuery,
    SemanticMetadataRelation,
    SemanticMetadataRelationInput,
    SemanticMetadataSchema,
    SemanticMetadataSource,
    SemanticMetadataSourceIdentity,
    SemanticMetadataType,
)

SemanticMetadataFailureStage = Literal["parse", "semantic", "ir"]

_FAILURE_STAGES = frozenset({"parse", "semantic", "ir"})


def semantic_metadata_artifact_to_json_dict(
    artifact: SemanticMetadataArtifact,
) -> dict[str, object]:
    """Serialize one successful private metadata artifact to JSON-compatible data."""

    return {
        "artifact": artifact.artifact,
        "schema_version": artifact.schema_version,
        "command": artifact.command,
        "ok": artifact.ok,
        "path": artifact.path,
        "diagnostics": [
            diagnostic_to_json_dict(diagnostic, fallback_path=artifact.path)
            for diagnostic in artifact.diagnostics
        ],
        "metadata": _payload_to_json_dict(artifact.metadata),
    }


def build_semantic_metadata_error_envelope(
    *,
    path: str | Path | None,
    stage: SemanticMetadataFailureStage,
    diagnostics: Sequence[Diagnostic] = (),
    message: str,
) -> dict[str, object]:
    """Build one fail-closed Artifact v1 failure envelope."""

    if stage not in _FAILURE_STAGES:
        raise ValueError(f"Unsupported Semantic Metadata Artifact v1 stage: {stage}")

    output_path = str(path) if path is not None else None
    return {
        "artifact": SEMANTIC_METADATA_ARTIFACT_NAME,
        "schema_version": SEMANTIC_METADATA_SCHEMA_VERSION,
        "command": SEMANTIC_METADATA_COMMAND,
        "ok": False,
        "path": output_path,
        "diagnostics": [
            diagnostic_to_json_dict(diagnostic, fallback_path=output_path)
            for diagnostic in diagnostics
        ],
        "error": {
            "stage": stage,
            "message": message,
        },
    }


def _payload_to_json_dict(payload: SemanticMetadataPayload) -> dict[str, object]:
    return {
        "source": _source_identity_to_json_dict(payload.source),
        "definitions": [
            _definition_to_json_dict(definition) for definition in payload.definitions
        ],
        "sources": [_source_to_json_dict(source) for source in payload.sources],
        "relations": [
            _relation_to_json_dict(relation) for relation in payload.relations
        ],
        "types": [_type_to_json_dict(type_ref) for type_ref in payload.types],
    }


def _source_identity_to_json_dict(
    source: SemanticMetadataSourceIdentity,
) -> dict[str, object]:
    return {"path": source.path}


def _definition_to_json_dict(
    definition: SemanticMetadataDefinition,
) -> dict[str, object]:
    return {
        "name": definition.name,
        "kind": definition.kind,
        "location": _location_to_json_dict(definition.location),
    }


def _source_to_json_dict(source: SemanticMetadataSource) -> dict[str, object]:
    return {
        "name": source.name,
        "schema": _schema_to_json_dict(source.schema),
        "location": _location_to_json_dict(source.location),
    }


def _relation_to_json_dict(relation: SemanticMetadataRelation) -> dict[str, object]:
    return {
        "name": relation.name,
        "kind": relation.kind,
        "input": _relation_input_to_json_dict(relation.input),
        "input_schema": _schema_to_json_dict(relation.input_schema),
        "output_schema": _schema_to_json_dict(relation.output_schema),
        "projections": [
            _projection_to_json_dict(projection) for projection in relation.projections
        ],
        "query": _query_to_json_dict(relation.query),
        "aggregates": [
            _aggregate_to_json_dict(aggregate) for aggregate in relation.aggregates
        ],
        "lineage": [_lineage_to_json_dict(lineage) for lineage in relation.lineage],
        "location": _location_to_json_dict(relation.location),
    }


def _relation_input_to_json_dict(
    relation_input: SemanticMetadataRelationInput,
) -> dict[str, object]:
    return {
        "name": relation_input.name,
        "kind": relation_input.kind,
    }


def _schema_to_json_dict(schema: SemanticMetadataSchema) -> dict[str, object]:
    return {"fields": [_field_to_json_dict(field) for field in schema.fields]}


def _field_to_json_dict(field: SemanticMetadataField) -> dict[str, object]:
    return {
        "name": field.name,
        "type": _type_to_json_dict(field.type),
        "nullability": field.nullability,
        "location": _location_to_json_dict(field.location),
    }


def _type_to_json_dict(
    type_ref: SemanticMetadataType | None,
) -> dict[str, object] | None:
    if type_ref is None:
        return None
    return {
        "status": type_ref.status,
        "name": type_ref.name,
        "kind": type_ref.kind,
        "canonical_name": type_ref.canonical_name,
        "canonical_kind": type_ref.canonical_kind,
        "nullability": type_ref.nullability,
        "support_posture": type_ref.support_posture,
    }


def _query_to_json_dict(query: SemanticMetadataQuery) -> dict[str, object]:
    return {
        "where": _clause_presence_to_json_dict(query.where),
        "group_keys": [_field_leaf_to_json_dict(leaf) for leaf in query.group_keys],
        "satisfying": _clause_presence_to_json_dict(query.satisfying),
        "order_by": [_order_by_to_json_dict(item) for item in query.order_by],
        "limit": _limit_to_json_dict(query.limit),
    }


def _clause_presence_to_json_dict(
    presence: SemanticMetadataClausePresence,
) -> dict[str, object]:
    return {"present": presence.present}


def _order_by_to_json_dict(item: SemanticMetadataOrderBy) -> dict[str, object]:
    return {
        "scope": item.scope,
        "direction": item.direction,
        "expression_kind": item.expression_kind,
        "field_leaves": [_field_leaf_to_json_dict(leaf) for leaf in item.field_leaves],
    }


def _limit_to_json_dict(
    limit: SemanticMetadataLimit | None,
) -> dict[str, object] | None:
    if limit is None:
        return None
    return {"value": limit.value}


def _projection_to_json_dict(
    projection: SemanticMetadataProjection,
) -> dict[str, object]:
    return {
        "name": projection.name,
        "expression_kind": projection.expression_kind,
        "type": _type_to_json_dict(projection.type),
        "field_leaves": [
            _field_leaf_to_json_dict(leaf) for leaf in projection.field_leaves
        ],
        "location": _location_to_json_dict(projection.location),
    }


def _aggregate_to_json_dict(
    aggregate: SemanticMetadataAggregate,
) -> dict[str, object]:
    return {
        "function": aggregate.function,
        "arguments": [
            _expression_summary_to_json_dict(argument)
            for argument in aggregate.arguments
        ],
        "result_type": _type_to_json_dict(aggregate.result_type),
        "projection_name": aggregate.projection_name,
        "location": _location_to_json_dict(aggregate.location),
    }


def _expression_summary_to_json_dict(
    expression: SemanticMetadataExpressionSummary,
) -> dict[str, object]:
    return {
        "expression_kind": expression.expression_kind,
        "type": _type_to_json_dict(expression.type),
        "field_leaves": [
            _field_leaf_to_json_dict(leaf) for leaf in expression.field_leaves
        ],
    }


def _lineage_to_json_dict(lineage: SemanticMetadataLineage) -> dict[str, object]:
    return {
        "output": lineage.output,
        "field_leaves": [
            _field_leaf_to_json_dict(leaf) for leaf in lineage.field_leaves
        ],
    }


def _field_leaf_to_json_dict(leaf: SemanticMetadataFieldLeaf) -> dict[str, object]:
    return {
        "relation": leaf.relation,
        "field": leaf.field,
        "qualifier": list(leaf.qualifier),
        "location": _location_to_json_dict(leaf.location),
    }


def _location_to_json_dict(
    location: SemanticMetadataLocation | None,
) -> dict[str, object] | None:
    if location is None:
        return None
    return {
        "path": location.path,
        "line": location.line,
        "column": location.column,
        "end_line": location.end_line,
        "end_column": location.end_column,
    }
