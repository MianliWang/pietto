"""Semantic validation for relationship metadata."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    Node,
    QueryDef,
    RelationshipMetadata,
    Script,
    SourceDef,
    TableDef,
    TableFunctionRelationDef,
    TypeDef,
    TypeExpr,
    ValuesRelationDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    RelationshipSemanticEndpointInfo,
    RelationshipSemanticInfo,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
)

# Equality over these builtins has no exact type identity yet.
_DEFERRED_EQUALITY_BUILTINS = frozenset({"Any", "Bytes", "Decimal", "Json"})


def check_relationship_metadata(
    script: Script,
    relation_symbols: Mapping[
        str, Definition | ValuesRelationDef | TableFunctionRelationDef
    ],
) -> tuple[tuple[RelationshipSemanticInfo, ...], tuple[Diagnostic, ...]]:
    """Validate relationship metadata and build readonly semantic facts."""

    relationships: list[RelationshipSemanticInfo] = []
    diagnostics: list[Diagnostic] = []
    relationship_names: set[str] = set()

    for relationship in script.relationships:
        is_valid = True
        if relationship.name in relationship_names:
            is_valid = False
            diagnostics.append(
                _diagnostic(
                    relationship,
                    code="PIE-S2602",
                    message=(
                        f"Duplicate relationship metadata name: {relationship.name}"
                    ),
                )
            )
        else:
            relationship_names.add(relationship.name)

        endpoint_names: set[str] = set()
        endpoints: list[RelationshipSemanticEndpointInfo] = []
        for endpoint in relationship.endpoints:
            # Diagnostics at one endpoint follow the public code order.
            relation = relation_symbols.get(endpoint.relation_name)
            if not isinstance(relation, (SourceDef, TableDef, QueryDef)):
                relation = None
                is_valid = False
                diagnostics.append(
                    _diagnostic(
                        endpoint,
                        code="PIE-S2601",
                        message=(
                            "Unknown relationship endpoint relation: "
                            f"{endpoint.relation_name}"
                        ),
                    )
                )
            if endpoint.local_name in endpoint_names:
                is_valid = False
                diagnostics.append(
                    _diagnostic(
                        endpoint,
                        code="PIE-S2603",
                        message=(
                            "Duplicate endpoint local name in relationship "
                            f"{relationship.name}: {endpoint.local_name}"
                        ),
                    )
                )
            else:
                endpoint_names.add(endpoint.local_name)
            if relation is None:
                continue
            endpoints.append(
                RelationshipSemanticEndpointInfo(
                    local_name=endpoint.local_name,
                    relation_name=endpoint.relation_name,
                    relation=relation,
                )
            )

        if is_valid:
            assert len(endpoints) == 2
            relationships.append(
                RelationshipSemanticInfo(
                    name=relationship.name,
                    endpoints=(endpoints[0], endpoints[1]),
                )
            )

    return tuple(relationships), tuple(diagnostics)


def check_relationship_conditions(
    script: Script,
    relationships: tuple[RelationshipSemanticInfo, ...],
    *,
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema],
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> tuple[Diagnostic, ...]:
    """Check the field equalities of each admitted relationship `on` condition."""

    diagnostics: list[Diagnostic] = []
    position = 0
    for relationship in script.relationships:
        # Admitted facts follow source order and skip invalid declarations.
        if position == len(relationships) or not _admits(
            relationships[position], relationship
        ):
            continue
        roles = {
            endpoint.local_name: endpoint
            for endpoint in relationships[position].endpoints
        }
        position += 1
        if relationship.base_match is None:
            continue
        for comparison in _field_equalities(relationship.base_match.expression):
            resolved: list[tuple[RelationshipSemanticEndpointInfo, ResolvedType]] = []
            for operand in (comparison.left, comparison.right):
                assert type(operand) is DottedNameExpr
                role, name = operand.parts
                endpoint = roles.get(role)
                if endpoint is None:
                    diagnostics.append(unknown_condition_operand(operand, role=True))
                    continue
                relation = endpoint.relation
                schema = (
                    source_row_schemas.get(relation)
                    if isinstance(relation, SourceDef)
                    else relation_row_schemas.get(relation)
                )
                if schema is None or schema.is_unknown:
                    continue
                field = schema.fields.get(name)
                if field is None:
                    diagnostics.append(unknown_condition_operand(operand, role=False))
                    continue
                resolved.append((endpoint, _expanded_type(field, type_expansions)))
            if len(resolved) != 2 or resolved[0][0] is resolved[1][0]:
                continue
            left_type, right_type = resolved[0][1], resolved[1][1]
            left_identity = _type_identity(left_type)
            right_identity = _type_identity(right_type)
            if None not in (left_identity, right_identity) and (
                left_identity != right_identity
            ):
                diagnostics.append(
                    incompatible_condition_operands(
                        comparison, left_type.name, right_type.name
                    )
                )
    return tuple(diagnostics)


def unknown_condition_operand(operand: DottedNameExpr, *, role: bool) -> Diagnostic:
    """Report an unknown endpoint role or endpoint field at one operand."""

    endpoint_role, field = operand.parts
    return _diagnostic(
        operand,
        code="PIE-S2604",
        message=(
            f"Unknown relationship condition endpoint role: {endpoint_role}"
            if role
            else f"Unknown relationship condition field: {endpoint_role}.{field}"
        ),
    )


def incompatible_condition_operands(
    comparison: ComparisonExpr, left_type: str, right_type: str
) -> Diagnostic:
    """Report one field equality whose operand types differ."""

    left, right = comparison.left, comparison.right
    assert type(left) is DottedNameExpr and type(right) is DottedNameExpr
    return _diagnostic(
        comparison,
        code="PIE-S2604",
        message=(
            "Incompatible relationship condition operands: "
            f"{'.'.join(left.parts)} ({left_type}) == "
            f"{'.'.join(right.parts)} ({right_type})"
        ),
    )


def _admits(info: RelationshipSemanticInfo, relationship: RelationshipMetadata) -> bool:
    return info.name == relationship.name and all(
        (admitted.local_name, admitted.relation_name)
        == (endpoint.local_name, endpoint.relation_name)
        for admitted, endpoint in zip(
            info.endpoints, relationship.endpoints, strict=True
        )
    )


def _field_equalities(expression: Expression) -> tuple[ComparisonExpr, ...]:
    """Return the `a.x == b.y` conjuncts of an `and` chain in source order."""

    if type(expression) is BinaryExpr and expression.operator == "and":
        return (
            *_field_equalities(expression.left),
            *_field_equalities(expression.right),
        )
    if (
        type(expression) is ComparisonExpr
        and expression.operator == "=="
        and all(
            type(operand) is DottedNameExpr and len(operand.parts) == 2
            for operand in (expression.left, expression.right)
        )
    ):
        return (expression,)
    return ()


def _expanded_type(
    field: RowField, type_expansions: Mapping[TypeExpr, ResolvedType]
) -> ResolvedType:
    """Expand a field's alias type, also for an output that lost its FieldDef."""

    resolved_type = field.resolved_type
    if field.definition is not None:
        return type_expansions.get(field.definition.type_expr, resolved_type)
    if isinstance(resolved_type.definition, TypeDef):
        return type_expansions.get(resolved_type.definition.base, resolved_type)
    return resolved_type


def _type_identity(resolved_type: ResolvedType) -> tuple[str, str] | None:
    if resolved_type.kind is TypeKind.ENUM or (
        resolved_type.kind is TypeKind.BUILTIN
        and resolved_type.name not in _DEFERRED_EQUALITY_BUILTINS
    ):
        return (resolved_type.kind.value, resolved_type.name)
    return None


def _diagnostic(node: Node, *, code: str, message: str) -> Diagnostic:
    """Create an error diagnostic at a complete metadata node span."""

    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
