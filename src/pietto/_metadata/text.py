"""Private deterministic text renderer for Semantic Metadata Artifact v1."""

from __future__ import annotations

from pietto._metadata.model import (
    SemanticMetadataAggregate,
    SemanticMetadataArtifact,
    SemanticMetadataField,
    SemanticMetadataFieldLeaf,
    SemanticMetadataLineage,
    SemanticMetadataOrderBy,
    SemanticMetadataProjection,
    SemanticMetadataRelation,
    SemanticMetadataSource,
    SemanticMetadataType,
)


def render_semantic_metadata_text(artifact: SemanticMetadataArtifact) -> str:
    """Render one successful metadata artifact as stable human-readable text."""

    lines = [
        artifact.artifact,
        f"schema_version: {artifact.schema_version}",
        f"command: {artifact.command}",
        f"path: {_optional(artifact.path)}",
        (
            "summary: "
            f"definitions={len(artifact.metadata.definitions)} "
            f"sources={len(artifact.metadata.sources)} "
            f"relations={len(artifact.metadata.relations)} "
            f"types={len(artifact.metadata.types)}"
        ),
        "definitions:",
    ]
    if artifact.metadata.definitions:
        lines.extend(
            f"  - {definition.name} ({definition.kind})"
            for definition in artifact.metadata.definitions
        )
    else:
        lines.append("  - none")

    lines.append("sources:")
    if artifact.metadata.sources:
        for source in artifact.metadata.sources:
            lines.extend(_source_lines(source))
    else:
        lines.append("  - none")

    lines.append("relations:")
    if artifact.metadata.relations:
        for relation in artifact.metadata.relations:
            lines.extend(_relation_lines(relation))
    else:
        lines.append("  - none")

    lines.append("types:")
    if artifact.metadata.types:
        lines.extend(
            f"  - {_type_label(type_ref)}" for type_ref in artifact.metadata.types
        )
    else:
        lines.append("  - none")
    return "\n".join(lines)


def _source_lines(source: SemanticMetadataSource) -> list[str]:
    lines = [f"  - {source.name}", "    fields:"]
    if source.schema.fields:
        lines.extend(f"      - {_field_label(field)}" for field in source.schema.fields)
    else:
        lines.append("      - none")
    return lines


def _relation_lines(relation: SemanticMetadataRelation) -> list[str]:
    lines = [
        f"  - {relation.name} ({relation.kind})",
        f"    input: {relation.input.name} ({relation.input.kind})",
        "    output fields:",
    ]
    if relation.output_schema.fields:
        lines.extend(
            f"      - {_field_label(field)}" for field in relation.output_schema.fields
        )
    else:
        lines.append("      - none")

    query = relation.query
    lines.append(
        "    query: "
        f"where={_present(query.where.present)} "
        f"group_keys={_leaf_list(query.group_keys)} "
        f"satisfying={_present(query.satisfying.present)} "
        f"order_by={len(query.order_by)} "
        f"limit={query.limit.value if query.limit is not None else 'none'}"
    )
    lines.extend(_projection_lines(relation.projections))
    lines.extend(_order_by_lines(relation.query.order_by))
    lines.extend(_aggregate_lines(relation.aggregates))
    lines.extend(_lineage_lines(relation.lineage))
    return lines


def _projection_lines(projections: tuple[SemanticMetadataProjection, ...]) -> list[str]:
    lines = ["    projections:"]
    if not projections:
        lines.append("      - none")
        return lines
    for projection in projections:
        lines.append(
            "      - "
            f"{_optional(projection.name)} "
            f"kind={projection.expression_kind} "
            f"type={_type_label(projection.type)} "
            f"leaves={_leaf_list(projection.field_leaves)}"
        )
    return lines


def _order_by_lines(order_by: tuple[SemanticMetadataOrderBy, ...]) -> list[str]:
    lines = ["    order_by:"]
    if not order_by:
        lines.append("      - none")
        return lines
    for item in order_by:
        lines.append(
            "      - "
            f"{item.scope} {item.direction} "
            f"kind={item.expression_kind} "
            f"leaves={_leaf_list(item.field_leaves)}"
        )
    return lines


def _aggregate_lines(aggregates: tuple[SemanticMetadataAggregate, ...]) -> list[str]:
    lines = ["    aggregates:"]
    if not aggregates:
        lines.append("      - none")
        return lines
    for aggregate in aggregates:
        arguments = ", ".join(
            f"{argument.expression_kind}:{_leaf_list(argument.field_leaves)}"
            for argument in aggregate.arguments
        )
        if not arguments:
            arguments = "none"
        lines.append(
            "      - "
            f"{_optional(aggregate.projection_name)} = "
            f"{aggregate.function}({arguments}) -> "
            f"{_type_label(aggregate.result_type)}"
        )
    return lines


def _lineage_lines(lineage: tuple[SemanticMetadataLineage, ...]) -> list[str]:
    lines = ["    lineage:"]
    if not lineage:
        lines.append("      - none")
        return lines
    for item in lineage:
        lines.append(f"      - {_lineage_label(item)}")
    return lines


def _lineage_label(lineage: SemanticMetadataLineage) -> str:
    return f"{_optional(lineage.output)} <- {_leaf_list(lineage.field_leaves)}"


def _field_label(field: SemanticMetadataField) -> str:
    return (
        f"{field.name}: {_type_label(field.type)} field_nullability={field.nullability}"
    )


def _type_label(type_ref: SemanticMetadataType | None) -> str:
    if type_ref is None:
        return "unknown"
    name = type_ref.name if type_ref.name is not None else "unknown"
    canonical = (
        type_ref.canonical_name if type_ref.canonical_name is not None else "unknown"
    )
    return (
        f"{name} kind={type_ref.kind} canonical={canonical} "
        f"canonical_kind={type_ref.canonical_kind} "
        f"nullability={type_ref.nullability} "
        f"support={type_ref.support_posture} status={type_ref.status}"
    )


def _leaf_list(leaves: tuple[SemanticMetadataFieldLeaf, ...]) -> str:
    if not leaves:
        return "none"
    return ", ".join(_leaf_label(leaf) for leaf in leaves)


def _leaf_label(leaf: SemanticMetadataFieldLeaf) -> str:
    qualifier = ".".join(leaf.qualifier)
    prefix = f"{qualifier}:" if qualifier else ""
    return f"{prefix}{leaf.relation}.{leaf.field}"


def _present(value: bool) -> str:
    return "yes" if value else "no"


def _optional(value: str | None) -> str:
    return value if value is not None else "null"
