"""Internal lowering helpers for foundational Semantic IR metadata."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Span,
    TypeDef,
    TypeExpr,
    UnaryExpr,
)
from pietto.ir.diagnostics import missing_semantic_fact_diagnostic
from pietto.ir.model import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    ExpressionLoweringResult,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    RowFieldIR,
    RowSchemaIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS
from pietto.semantic.aggregates import (
    aggregate_call_name,
    aggregate_result_value_type,
    is_direct_field_argument,
)
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


def lower_type_ref(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower one parsed type reference from readonly semantic facts."""

    resolved = semantic_model.type_resolutions.get(type_expr)
    canonical = semantic_model.type_expansions.get(type_expr)
    nullability = semantic_model.type_nullability.get(
        type_expr,
        EffectiveNullability.UNKNOWN,
    )
    return _type_ref_from_semantics(
        declared_name=type_expr.name,
        resolved=resolved,
        canonical=canonical,
        nullability=nullability,
    )


def lower_canonical_type_ref(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower the canonical target of one parsed type reference."""

    type_ref = lower_type_ref(type_expr, semantic_model)
    return TypeRefIR(
        symbol=type_ref.canonical_symbol,
        canonical_symbol=type_ref.canonical_symbol,
        declared_name=type_ref.canonical_name,
        canonical_name=type_ref.canonical_name,
        kind=type_ref.canonical_kind,
        canonical_kind=type_ref.canonical_kind,
        nullability=type_ref.nullability,
    )


def lower_value_type(
    value_type: ValueType,
    semantic_model: SemanticModel,
) -> TypeRefIR:
    """Lower an expression value type with canonical alias information."""

    resolved = value_type.resolved_type
    canonical = resolved
    if isinstance(resolved.definition, TypeDef):
        canonical = semantic_model.type_expansions.get(
            resolved.definition.base,
            resolved,
        )
    return _type_ref_from_semantics(
        declared_name=resolved.name,
        resolved=resolved,
        canonical=canonical,
        nullability=value_type.nullability,
    )


def lower_expr(
    expression: Expression,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField] | None = None,
    field_owner: SymbolId | None = None,
    field_qualifier: str | None = None,
) -> ExpressionLoweringResult:
    """Lower one typed expression without re-running semantic analysis."""

    if (
        expression not in semantic_model.expression_value_types
        and not _is_static_connector_call(expression)
    ):
        return ExpressionLoweringResult(
            expression=None,
            diagnostics=(
                missing_semantic_fact_diagnostic(
                    expression,
                    "expression value type",
                ),
            ),
        )

    return ExpressionLoweringResult(
        expression=_lower_expr_node(
            expression,
            semantic_model,
            fields=fields or {},
            field_owner=field_owner,
            field_qualifier=field_qualifier,
        ),
        diagnostics=(),
    )


def _lower_expr_node(
    expression: Expression,
    semantic_model: SemanticModel,
    *,
    fields: Mapping[str, RowField],
    field_owner: SymbolId | None,
    field_qualifier: str | None,
) -> ExpressionIR:
    """Recursively copy one expression into parser-independent IR."""

    value_type = lower_value_type(
        semantic_model.expression_value_types.get(
            expression,
            _UNKNOWN_VALUE_TYPE,
        ),
        semantic_model,
    )
    common = {
        "span": lower_span(expression.span),
        "value_type": value_type,
    }

    if isinstance(expression, LiteralExpr):
        return LiteralIR(value=expression.value, **common)
    if isinstance(expression, NameExpr):
        field = None
        if expression.name in fields:
            field = FieldId(owner=field_owner, name=expression.name)
        return FieldRefIR(
            name=expression.name,
            qualifier=(),
            field=field,
            **common,
        )
    if isinstance(expression, DottedNameExpr):
        field = None
        if (
            len(expression.parts) == 2
            and expression.parts[0] == field_qualifier
            and expression.parts[1] in fields
        ):
            field = FieldId(owner=field_owner, name=expression.parts[1])
        return FieldRefIR(
            name=expression.parts[-1],
            qualifier=expression.parts[:-1],
            field=field,
            **common,
        )
    if isinstance(expression, CallExpr):
        callee = _callee_name(expression)
        if _is_valid_aggregate_projection(expression, semantic_model, value_type):
            return AggregateCallIR(
                function=callee,
                arguments=tuple(
                    _lower_expr_node(
                        argument,
                        semantic_model,
                        fields=fields,
                        field_owner=field_owner,
                        field_qualifier=field_qualifier,
                    )
                    for argument in expression.arguments
                ),
                **common,
            )
        callee_symbol = None
        if callee in BUILTIN_FUNCTIONS:
            callee_symbol = SymbolId(SymbolNamespace.CALLABLE, callee)
        return CallIR(
            callee=callee,
            callee_symbol=callee_symbol,
            arguments=tuple(
                _lower_expr_node(
                    argument,
                    semantic_model,
                    fields=fields,
                    field_owner=field_owner,
                    field_qualifier=field_qualifier,
                )
                for argument in expression.arguments
            ),
            **common,
        )
    if isinstance(expression, UnaryExpr):
        return UnaryIR(
            operator=expression.operator,
            operand=_lower_expr_node(
                expression.operand,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            **common,
        )
    if isinstance(expression, BinaryExpr):
        return BinaryIR(
            left=_lower_expr_node(
                expression.left,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            operator=expression.operator,
            right=_lower_expr_node(
                expression.right,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            **common,
        )
    if isinstance(expression, ComparisonExpr):
        return ComparisonIR(
            left=_lower_expr_node(
                expression.left,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            operator=expression.operator,
            right=_lower_expr_node(
                expression.right,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            **common,
        )
    if isinstance(expression, BetweenExpr):
        return BetweenIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            lower=_lower_expr_node(
                expression.lower,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            upper=_lower_expr_node(
                expression.upper,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            **common,
        )
    if isinstance(expression, IsNullExpr):
        return IsNullIR(
            value=_lower_expr_node(
                expression.value,
                semantic_model,
                fields=fields,
                field_owner=field_owner,
                field_qualifier=field_qualifier,
            ),
            negated=expression.negated,
            **common,
        )
    raise TypeError(f"Unsupported expression AST node: {type(expression).__name__}")


def _callee_name(expression: CallExpr) -> str:
    """Return the static source-level name of a call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    return ".".join(expression.callee.parts)


def _is_valid_aggregate_projection(
    expression: CallExpr,
    semantic_model: SemanticModel,
    value_type: TypeRefIR,
) -> bool:
    """Return whether this call is a precise output projection aggregate."""

    function_name = aggregate_call_name(expression)
    if function_name is None:
        return False
    semantic_value_type = semantic_model.expression_value_types.get(expression)
    if semantic_value_type is None:
        return False
    if not _aggregate_type_matches_ir(
        function_name,
        expression,
        semantic_model,
        semantic_value_type,
        value_type,
    ):
        return False

    for relation, schema in semantic_model.relation_row_schemas.items():
        for item in relation.select_items:
            if item.expression is not expression or item.alias is None:
                continue
            field = schema.fields.get(item.alias)
            return (
                field is not None
                and field.resolved_type.kind is semantic_value_type.resolved_type.kind
                and field.resolved_type.name == semantic_value_type.resolved_type.name
                and field.nullability is semantic_value_type.nullability
            )
    return False


def _aggregate_type_matches_ir(
    function_name: str,
    expression: CallExpr,
    semantic_model: SemanticModel,
    semantic_value_type: ValueType,
    value_type: TypeRefIR,
) -> bool:
    if not expression.arguments:
        expected = aggregate_result_value_type(function_name)
    elif len(expression.arguments) == 1 and is_direct_field_argument(
        expression.arguments[0]
    ):
        argument_type = semantic_model.expression_value_types.get(
            expression.arguments[0]
        )
        expected = (
            None
            if argument_type is None
            else aggregate_result_value_type(function_name, argument_type)
        )
    else:
        expected = None
    return (
        expected is not None
        and semantic_value_type == expected
        and value_type.canonical_kind is TypeKindIR.BUILTIN
        and value_type.canonical_name == expected.resolved_type.name
        and value_type.nullability.value == expected.nullability.value
    )


def _is_static_connector_call(expression: Expression) -> bool:
    """Allow the validated connector call omitted from expression typing."""

    return isinstance(expression, CallExpr) and _callee_name(expression) in (
        "postgres.table",
        "mysql.table",
    )


def lower_row_schema(
    schema: RowSchema,
    semantic_model: SemanticModel,
) -> RowSchemaIR:
    """Lower an ordered semantic row schema without retaining AST nodes."""

    return RowSchemaIR(
        fields=tuple(
            _lower_row_field(field, semantic_model) for field in schema.fields.values()
        ),
        is_unknown=schema.is_unknown,
    )


def _lower_row_field(
    field: RowField,
    semantic_model: SemanticModel,
) -> RowFieldIR:
    """Lower a row field, using its declaration when semantic facts have one."""

    if field.definition is not None:
        type_ref = lower_type_ref(field.definition.type_expr, semantic_model)
        span = lower_span(field.definition.span)
    else:
        type_ref = _type_ref_from_semantics(
            declared_name=field.resolved_type.name,
            resolved=field.resolved_type,
            canonical=field.resolved_type,
            nullability=field.nullability,
        )
        span = None

    nullability = _lower_nullability(field.nullability)
    return RowFieldIR(
        name=field.name,
        type_ref=type_ref,
        nullability=nullability,
        span=span,
    )


def _type_ref_from_semantics(
    *,
    declared_name: str,
    resolved: ResolvedType | None,
    canonical: ResolvedType | None,
    nullability: EffectiveNullability,
) -> TypeRefIR:
    """Copy resolved type facts into parser-independent IR metadata."""

    resolved = resolved or _unknown_type(declared_name)
    canonical = canonical or _unknown_type()

    return TypeRefIR(
        symbol=_type_symbol(resolved),
        canonical_symbol=_type_symbol(canonical),
        declared_name=declared_name,
        canonical_name=canonical.name,
        kind=TypeKindIR(resolved.kind.value),
        canonical_kind=TypeKindIR(canonical.kind.value),
        nullability=_lower_nullability(nullability),
    )


def _type_symbol(resolved: ResolvedType) -> SymbolId | None:
    """Build a stable type symbol unless semantic resolution is Unknown."""

    if resolved.kind is TypeKind.UNKNOWN:
        return None
    return SymbolId(
        namespace=SymbolNamespace.TYPE,
        name=resolved.name,
    )


def _unknown_type(name: str = "<unknown>") -> ResolvedType:
    """Create an internal Unknown type for incomplete semantic metadata."""

    return ResolvedType(name=name, kind=TypeKind.UNKNOWN)


def _lower_nullability(value: EffectiveNullability) -> NullabilityIR:
    """Copy effective semantic nullability into the IR enum."""

    return NullabilityIR(value.value)


def lower_span(span: Span) -> SourceSpan:
    """Copy a parser AST span without retaining the AST object."""

    return SourceSpan(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
