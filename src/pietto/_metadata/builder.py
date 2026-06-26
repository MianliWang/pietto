"""Private builder for Semantic Metadata Artifact v1 success data."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    TypeDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir.model import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    DefinitionIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    OrderItemIR,
    ProjectionIR,
    RelationIR,
    RelationKindIR,
    RowSchemaIR,
    ScriptIR,
    SourceIR,
    SourceSpan,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
)
from pietto.semantic import SemanticResult

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

_DEFERRED_BUILTINS = frozenset({"Bytes", "Json"})
_LIMITED_FROZEN_BUILTINS = frozenset({"UUID"})
_UNKNOWN_TYPE_NAME = "<unknown>"
_AGGREGATE_FUNCTIONS = frozenset(
    {
        "count",
        "count_distinct",
        "sum",
        "avg",
        "min",
        "max",
    }
)


def build_semantic_metadata_artifact(
    *,
    path: str | Path | None,
    script: Script,
    semantic_result: SemanticResult,
    ir: ScriptIR,
    diagnostics: Sequence[Diagnostic] = (),
) -> SemanticMetadataArtifact:
    """Build private success metadata from an already-successful pipeline."""

    all_diagnostics = tuple(diagnostics)
    _require_success(all_diagnostics)
    _require_success(semantic_result.diagnostics)

    source_path = str(path) if path is not None else None
    sources = tuple(
        _source_metadata(definition)
        for definition in ir.definitions
        if isinstance(definition, SourceIR)
    )
    relations = tuple(
        _relation_metadata(definition, ir.definitions)
        for definition in ir.definitions
        if isinstance(definition, RelationIR)
    )
    payload = SemanticMetadataPayload(
        source=SemanticMetadataSourceIdentity(path=source_path),
        definitions=tuple(
            _definition_metadata(definition) for definition in script.definitions
        ),
        sources=sources,
        relations=relations,
        types=_collect_types(sources, relations),
    )
    return SemanticMetadataArtifact(
        artifact=SEMANTIC_METADATA_ARTIFACT_NAME,
        schema_version=SEMANTIC_METADATA_SCHEMA_VERSION,
        command=SEMANTIC_METADATA_COMMAND,
        ok=True,
        path=source_path,
        diagnostics=all_diagnostics,
        metadata=payload,
    )


def _require_success(diagnostics: Sequence[Diagnostic]) -> None:
    if any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics):
        raise ValueError(
            "Semantic Metadata Artifact v1 metadata requires successful diagnostics."
        )


def _definition_metadata(definition: Definition) -> SemanticMetadataDefinition:
    return SemanticMetadataDefinition(
        name=definition.name,
        kind=_definition_kind(definition),
        location=_location_from_span(definition.span),
    )


def _definition_kind(definition: Definition) -> str:
    if isinstance(definition, TypeDef):
        return "type"
    if isinstance(definition, EnumDef):
        return "enum"
    if isinstance(definition, ShapeDef):
        return "shape"
    if isinstance(definition, SourceDef):
        return "source"
    if isinstance(definition, TableDef):
        return "table"
    if isinstance(definition, QueryDef):
        return "query"
    if isinstance(definition, ConstraintDef):
        return "constraint"
    if isinstance(definition, DeriveDef):
        return "derive"
    return "unknown"


def _source_metadata(source: SourceIR) -> SemanticMetadataSource:
    return SemanticMetadataSource(
        name=source.name,
        schema=_schema_metadata(source.row_schema),
        location=_location_from_span(source.span),
    )


def _relation_metadata(
    relation: RelationIR,
    definitions: Sequence[DefinitionIR],
) -> SemanticMetadataRelation:
    source_definition = _find_definition(definitions, relation.source.name)
    return SemanticMetadataRelation(
        name=relation.name,
        kind=relation.kind.value,
        input=SemanticMetadataRelationInput(
            name=relation.source.name,
            kind=_input_kind(source_definition),
        ),
        input_schema=_input_schema(source_definition),
        output_schema=_schema_metadata(relation.row_schema),
        projections=tuple(
            _projection_metadata(projection) for projection in relation.projections
        ),
        query=_query_metadata(relation),
        aggregates=tuple(
            aggregate
            for projection in relation.projections
            for aggregate in _aggregate_metadata(projection)
        ),
        lineage=tuple(
            SemanticMetadataLineage(
                output=projection.name,
                field_leaves=_field_leaves(projection.expression),
            )
            for projection in relation.projections
        ),
        location=_location_from_span(relation.span),
    )


def _find_definition(
    definitions: Sequence[DefinitionIR],
    name: str,
) -> DefinitionIR | None:
    return next(
        (
            definition
            for definition in definitions
            if isinstance(definition, (SourceIR, RelationIR))
            and definition.name == name
        ),
        None,
    )


def _input_kind(definition: DefinitionIR | None) -> str:
    if isinstance(definition, SourceIR):
        return "source"
    if isinstance(definition, RelationIR):
        if definition.kind is RelationKindIR.TABLE:
            return "table"
        if definition.kind is RelationKindIR.QUERY:
            return "query"
    return "unknown"


def _input_schema(definition: DefinitionIR | None) -> SemanticMetadataSchema:
    if isinstance(definition, SourceIR):
        return _schema_metadata(definition.row_schema)
    if isinstance(definition, RelationIR):
        return _schema_metadata(definition.row_schema)
    return SemanticMetadataSchema(fields=())


def _schema_metadata(schema: RowSchemaIR) -> SemanticMetadataSchema:
    if schema.is_unknown:
        return SemanticMetadataSchema(fields=())
    return SemanticMetadataSchema(
        fields=tuple(
            SemanticMetadataField(
                name=field.name,
                type=_type_metadata(field.type_ref),
                nullability=field.nullability.value,
                location=_location_from_span(field.span),
            )
            for field in schema.fields
        )
    )


def _type_metadata(type_ref: TypeRefIR) -> SemanticMetadataType:
    status = "unknown" if _type_is_unknown(type_ref) else "known"
    name = (
        None if type_ref.declared_name == _UNKNOWN_TYPE_NAME else type_ref.declared_name
    )
    canonical_name = (
        None
        if type_ref.canonical_name == _UNKNOWN_TYPE_NAME
        else type_ref.canonical_name
    )
    return SemanticMetadataType(
        status=status,
        name=name if status == "known" else None,
        kind=type_ref.kind.value,
        canonical_name=canonical_name if status == "known" else None,
        canonical_kind=type_ref.canonical_kind.value,
        nullability=type_ref.nullability.value,
        support_posture=_support_posture(type_ref),
    )


def _type_is_unknown(type_ref: TypeRefIR) -> bool:
    return (
        type_ref.kind is TypeKindIR.UNKNOWN
        or type_ref.canonical_kind is TypeKindIR.UNKNOWN
        or type_ref.declared_name == _UNKNOWN_TYPE_NAME
        or type_ref.canonical_name == _UNKNOWN_TYPE_NAME
    )


def _support_posture(type_ref: TypeRefIR) -> str:
    if _type_is_unknown(type_ref):
        return "unknown"
    if type_ref.kind is TypeKindIR.ENUM or type_ref.canonical_kind is TypeKindIR.ENUM:
        return "metadata_only"
    if (
        type_ref.kind is TypeKindIR.BUILTIN
        or type_ref.canonical_kind is TypeKindIR.BUILTIN
    ):
        if type_ref.canonical_name in _DEFERRED_BUILTINS:
            return "deferred_builtin"
        if type_ref.canonical_name in _LIMITED_FROZEN_BUILTINS:
            return "limited_frozen"
    return "current"


def _query_metadata(relation: RelationIR) -> SemanticMetadataQuery:
    return SemanticMetadataQuery(
        where=SemanticMetadataClausePresence(present=relation.filter is not None),
        group_keys=tuple(
            leaf
            for key in relation.group_keys
            for leaf in (_field_leaf(key, fallback_relation=relation.source.name),)
            if leaf is not None
        ),
        satisfying=SemanticMetadataClausePresence(
            present=relation.result_predicate is not None
        ),
        order_by=tuple(
            _order_by_metadata(relation, item) for item in relation.order_by
        ),
        limit=(
            None
            if relation.limit is None
            else SemanticMetadataLimit(
                value=relation.limit.value,
                location=_location_from_span(relation.limit.span),
            )
        ),
    )


def _order_by_metadata(
    relation: RelationIR,
    item: OrderItemIR,
) -> SemanticMetadataOrderBy:
    return SemanticMetadataOrderBy(
        scope="grouped_result" if relation.group_keys else "input",
        direction=item.direction.value.upper(),
        expression_kind=_expression_kind(item.expression),
        field_leaves=_field_leaves(item.expression),
        location=_location_from_span(item.span),
    )


def _projection_metadata(projection: ProjectionIR) -> SemanticMetadataProjection:
    return SemanticMetadataProjection(
        name=projection.name,
        expression_kind=_expression_kind(projection.expression),
        type=_type_metadata(projection.type_ref or projection.expression.value_type),
        field_leaves=_field_leaves(projection.expression),
        location=_location_from_span(projection.span),
    )


def _aggregate_metadata(
    projection: ProjectionIR,
) -> tuple[SemanticMetadataAggregate, ...]:
    return tuple(
        SemanticMetadataAggregate(
            function=expression.function,
            arguments=tuple(
                _expression_summary(argument) for argument in expression.arguments
            ),
            result_type=_type_metadata(expression.value_type),
            projection_name=projection.name,
            location=_location_from_span(expression.span),
        )
        for expression in _walk_expressions(projection.expression)
        if isinstance(expression, AggregateCallIR)
        and expression.function in _AGGREGATE_FUNCTIONS
    )


def _expression_summary(
    expression: ExpressionIR,
) -> SemanticMetadataExpressionSummary:
    return SemanticMetadataExpressionSummary(
        expression_kind=_expression_kind(expression),
        type=_type_metadata(expression.value_type),
        field_leaves=_field_leaves(expression),
        location=_location_from_span(expression.span),
    )


def _expression_kind(expression: ExpressionIR) -> str:
    if isinstance(expression, FieldRefIR):
        return "field_ref"
    if isinstance(expression, AggregateCallIR):
        return "aggregate_call"
    if isinstance(expression, (BinaryIR, UnaryIR)):
        return "bounded_expression"
    if isinstance(expression, LiteralIR):
        return "literal"
    if isinstance(expression, CallIR):
        return "call"
    if isinstance(expression, (ComparisonIR, BetweenIR, IsNullIR)):
        return "predicate"
    return "unknown"


def _field_leaves(
    expression: ExpressionIR,
) -> tuple[SemanticMetadataFieldLeaf, ...]:
    return tuple(
        leaf
        for item in _walk_expressions(expression)
        if isinstance(item, FieldRefIR)
        for leaf in (_field_leaf(item),)
        if leaf is not None
    )


def _field_leaf(
    expression: FieldRefIR,
    *,
    fallback_relation: str | None = None,
) -> SemanticMetadataFieldLeaf | None:
    if expression.field is None:
        if fallback_relation is None:
            return None
        return SemanticMetadataFieldLeaf(
            relation=fallback_relation,
            field=expression.name,
            qualifier=expression.qualifier,
            location=_location_from_span(expression.span),
        )
    if expression.field.owner is None:
        if fallback_relation is None:
            return None
        relation = fallback_relation
    else:
        relation = expression.field.owner.name
    return SemanticMetadataFieldLeaf(
        relation=relation,
        field=expression.field.name,
        qualifier=expression.qualifier,
        location=_location_from_span(expression.span),
    )


def _walk_expressions(expression: ExpressionIR) -> Iterable[ExpressionIR]:
    yield expression
    if isinstance(expression, AggregateCallIR):
        yield from _walk_many(expression.arguments)
    elif isinstance(expression, CallIR):
        yield from _walk_many(expression.arguments)
    elif isinstance(expression, UnaryIR):
        yield from _walk_expressions(expression.operand)
    elif isinstance(expression, BinaryIR):
        yield from _walk_expressions(expression.left)
        yield from _walk_expressions(expression.right)
    elif isinstance(expression, ComparisonIR):
        yield from _walk_expressions(expression.left)
        yield from _walk_expressions(expression.right)
    elif isinstance(expression, BetweenIR):
        yield from _walk_expressions(expression.value)
        yield from _walk_expressions(expression.lower)
        yield from _walk_expressions(expression.upper)
    elif isinstance(expression, IsNullIR):
        yield from _walk_expressions(expression.value)


def _walk_many(expressions: Iterable[ExpressionIR]) -> Iterable[ExpressionIR]:
    for expression in expressions:
        yield from _walk_expressions(expression)


def _collect_types(
    sources: Sequence[SemanticMetadataSource],
    relations: Sequence[SemanticMetadataRelation],
) -> tuple[SemanticMetadataType, ...]:
    seen: set[SemanticMetadataType] = set()
    ordered: list[SemanticMetadataType] = []
    for type_ref in _iter_types(sources, relations):
        if type_ref not in seen:
            seen.add(type_ref)
            ordered.append(type_ref)
    return tuple(ordered)


def _iter_types(
    sources: Sequence[SemanticMetadataSource],
    relations: Sequence[SemanticMetadataRelation],
) -> Iterable[SemanticMetadataType]:
    for source in sources:
        yield from _schema_types(source.schema)
    for relation in relations:
        yield from _schema_types(relation.input_schema)
        yield from _schema_types(relation.output_schema)
        for projection in relation.projections:
            if projection.type is not None:
                yield projection.type
        for aggregate in relation.aggregates:
            yield aggregate.result_type
            for argument in aggregate.arguments:
                if argument.type is not None:
                    yield argument.type


def _schema_types(schema: SemanticMetadataSchema) -> Iterable[SemanticMetadataType]:
    for field in schema.fields:
        yield field.type


def _location_from_span(
    span: Span | SourceSpan | None,
) -> SemanticMetadataLocation | None:
    if span is None:
        return None
    return SemanticMetadataLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
