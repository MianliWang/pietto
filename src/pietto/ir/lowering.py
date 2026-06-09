"""Internal lowering helpers for foundational Semantic IR metadata."""

from __future__ import annotations

from pietto.ast_nodes import Span, TypeExpr
from pietto.ir.model import (
    NullabilityIR,
    RowFieldIR,
    RowSchemaIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
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
