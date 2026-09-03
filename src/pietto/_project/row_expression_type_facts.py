"""Private project row expression type fact helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto.ast_nodes import Expression, NameExpr
from pietto.errors import Diagnostic
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

_PROJECT_BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)
_UNKNOWN_PROJECT_FIELD_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


def project_row_field_to_semantic_value_type(
    field: ProjectRowField,
    effective_nullability: ProjectRowFieldNullability,
) -> ValueType:
    """Adapt one exact Project field occurrence for the semantic type kernel."""

    if type(field) is not ProjectRowField:
        raise TypeError("Project field adaptation requires an exact row field.")
    if type(effective_nullability) is not ProjectRowFieldNullability:
        raise TypeError("Project field adaptation requires exact nullability.")
    resolved_type = _semantic_resolved_type(field.resolved_type)
    if resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_PROJECT_FIELD_VALUE_TYPE
    return ValueType(
        resolved_type=resolved_type,
        nullability=_semantic_nullability(effective_nullability),
    )


def build_project_row_expression_value_types(
    *,
    expressions: Iterable[Expression],
    input_schema: ProjectRowSchema,
    relation_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None = None,
) -> Mapping[Expression, ValueType]:
    """Infer known row expression value types from a concrete project schema."""

    if input_schema.is_unknown:
        return MappingProxyType({})

    row_schema = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    for expression in tuple(expressions):
        if contains_semantic_aggregate(expression):
            continue
        scratch_value_types: dict[Expression, ValueType] = {}
        diagnostics: list[Diagnostic] = []
        root_value_type = infer_row_expression(
            expression,
            row_schema,
            scratch_value_types,
            diagnostics,
            report_unknown_name=not isinstance(expression, NameExpr),
            field_qualifier=relation_qualifier,
            bare_value_types=bare_value_types,
        )
        if (
            diagnostics
            or root_value_type.kind is not ValueTypeKind.KNOWN
            or expression not in scratch_value_types
            or any(
                value_type.kind is not ValueTypeKind.KNOWN
                for value_type in scratch_value_types.values()
            )
        ):
            continue
        value_types.update(scratch_value_types)

    return MappingProxyType(value_types)


def project_row_schema_to_semantic_row_schema(
    input_schema: ProjectRowSchema,
) -> RowSchema:
    """Convert a private project row schema into semantic row-schema facts."""

    fields: dict[str, RowField] = {}
    for name, field in input_schema.fields.items():
        fields[name] = RowField(
            name=name,
            resolved_type=_semantic_resolved_type(field.resolved_type),
            nullability=_semantic_nullability(field.nullability),
            definition=field.field_def,
        )
    return RowSchema(fields=fields)


def _semantic_resolved_type(resolved_type: ProjectResolvedType) -> ResolvedType:
    if (
        resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
        and resolved_type.name in _PROJECT_BUILTIN_TYPE_NAMES
    ):
        return ResolvedType(name=resolved_type.name, kind=TypeKind.BUILTIN)
    return ResolvedType(name=resolved_type.name, kind=TypeKind.UNKNOWN)


def _semantic_nullability(
    nullability: ProjectRowFieldNullability,
) -> EffectiveNullability:
    if nullability is ProjectRowFieldNullability.NON_NULL:
        return EffectiveNullability.NON_NULL
    if nullability is ProjectRowFieldNullability.NULLABLE:
        return EffectiveNullability.NULLABLE
    return EffectiveNullability.UNKNOWN
