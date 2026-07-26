"""Semantic helpers for parsed GROUP BY clauses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    NameExpr,
    Node,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    aggregate_alias_required_diagnostic,
    contains_semantic_aggregate,
    deferred_argument_expression_diagnostic,
    deferred_composition_diagnostic,
    effective_semantic_aggregate_argument_expression,
    has_unknown_field_reference,
    is_semantic_aggregate_call,
    is_supported_semantic_aggregate_arity,
    is_supported_semantic_aggregate_argument,
    is_supported_semantic_aggregate_argument_expression,
    nested_semantic_aggregate,
    nested_aggregate_diagnostic,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
    wrong_arity_diagnostic,
    wrong_argument_type_diagnostic,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

GROUP_BY_DEFERRED_CODE = "PIE-S2316"
GROUP_BY_DEFERRED_MESSAGE = (
    "GROUP BY lowering gate is retired; valid GROUP BY lowers to SQL"
)

_UNKNOWN_RESOLVED_TYPE = ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN)

DerivedRelation = TableDef | QueryDef
RelationDefinition = SourceDef | TableDef | QueryDef


@dataclass(frozen=True, slots=True)
class _GroupKey:
    identity: str
    field: RowField
    item: GroupByItem


@dataclass(frozen=True, slots=True)
class _GroupedOrderOutput:
    supported: bool
    field_identity: str | None = None


def check_group_by_deferred(script: Script) -> list[Diagnostic]:
    """Preserve the retired Slice 4-6 GROUP BY gate as a no-op helper."""

    del script
    return []


def project_grouped_schema(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    expression_value_types: Mapping[Expression, ValueType] | None,
    let_expansions: Mapping[str, Expression] | None = None,
) -> tuple[RowSchema, list[Diagnostic]]:
    """Build grouped row schema facts while keeping lowering fail-closed."""

    diagnostics: list[Diagnostic] = []
    if definition.group_by_clause is None:
        raise AssertionError("grouped schema requires a GROUP BY clause")

    if input_schema.is_unknown:
        diagnostics.extend(_grouped_order_by_diagnostics(definition))
        return _unknown_schema(), diagnostics

    group_keys, unknown_key_texts, key_diagnostics = _resolve_group_keys(
        definition,
        input_schema,
        let_expansions=let_expansions,
    )
    diagnostics.extend(key_diagnostics)

    key_fields = {key.identity: key.field for key in group_keys}
    fields: dict[str, RowField] = {}
    grouped_order_outputs: dict[str, _GroupedOrderOutput] = {}
    seen_names: set[str] = set()
    saw_valid_aggregate = False
    saw_invalid_projection = False

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is not None:
            if output_name in seen_names:
                diagnostics.append(_duplicate_projection_diagnostic(item, output_name))
                saw_invalid_projection = True
                continue
            seen_names.add(output_name)

        # Window outputs belong to the later WINDOW stage.  Keep duplicate-name
        # ownership above, but do not publish the result into the GROUP schema.
        if type(item.expression) is WindowExpr:
            continue

        if contains_semantic_aggregate(item.expression):
            aggregate_field, aggregate_diagnostics, valid = _aggregate_output_field(
                item,
                output_name=output_name,
                expression_value_types=expression_value_types,
                let_expansions=let_expansions,
            )
            diagnostics.extend(aggregate_diagnostics)
            if aggregate_field is not None:
                fields[aggregate_field.name] = aggregate_field
            if output_name is not None:
                grouped_order_outputs[output_name] = _GroupedOrderOutput(
                    supported=valid,
                )
            if valid:
                saw_valid_aggregate = True
            else:
                saw_invalid_projection = True
            continue

        key_identity = _field_identity(
            definition,
            item.expression,
            input_schema,
        )
        if key_identity is not None and key_identity in key_fields:
            if output_name is not None:
                fields[output_name] = _projected_row_field(
                    output_name,
                    key_fields[key_identity],
                )
                grouped_order_outputs[output_name] = _GroupedOrderOutput(
                    supported=True,
                    field_identity=key_identity,
                )
            continue

        if _matches_unknown_group_key(item.expression, unknown_key_texts):
            if output_name is not None:
                fields[output_name] = _unknown_row_field(output_name)
                grouped_order_outputs[output_name] = _GroupedOrderOutput(
                    supported=False,
                )
            saw_invalid_projection = True
            continue

        if isinstance(item.expression, (NameExpr, DottedNameExpr)):
            field = _resolve_input_field(
                definition,
                item.expression,
                input_schema,
            )
            if field is None:
                if isinstance(item.expression, NameExpr):
                    diagnostics.append(_unknown_field_diagnostic(item.expression))
                if output_name is not None:
                    fields[output_name] = _unknown_row_field(output_name)
                    grouped_order_outputs[output_name] = _GroupedOrderOutput(
                        supported=False,
                    )
            else:
                diagnostics.append(_non_grouped_projection_diagnostic(item.expression))
                if output_name is not None:
                    fields[output_name] = _unknown_row_field(output_name)
                    grouped_order_outputs[output_name] = _GroupedOrderOutput(
                        supported=False,
                    )
            saw_invalid_projection = True
            continue

        diagnostics.append(_scalar_grouped_projection_diagnostic(item.expression))
        if output_name is not None:
            fields[output_name] = _unknown_row_field(output_name)
            grouped_order_outputs[output_name] = _GroupedOrderOutput(supported=False)
        saw_invalid_projection = True

    diagnostics.extend(
        _grouped_order_by_diagnostics(
            definition,
            grouped_order_outputs,
            input_schema=input_schema,
            let_expansions=let_expansions,
        )
    )

    if not saw_valid_aggregate and not saw_invalid_projection:
        diagnostics.append(_pure_grouped_output_deferred_diagnostic(definition))

    return RowSchema(fields=fields), diagnostics


def _resolve_group_keys(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    let_expansions: Mapping[str, Expression] | None,
) -> tuple[list[_GroupKey], set[str], list[Diagnostic]]:
    keys: list[_GroupKey] = []
    unknown_key_texts: set[str] = set()
    diagnostics: list[Diagnostic] = []
    seen_identities: set[str] = set()

    assert definition.group_by_clause is not None
    for item in definition.group_by_clause.items:
        effective_key = _effective_group_key_expression(
            item.key,
            let_expansions=let_expansions,
            let_stack=frozenset(),
        )
        identity = _field_identity(definition, effective_key, input_schema)
        if identity is None:
            unknown_key_texts.add(_field_text(item.key))
            diagnostics.append(_unknown_field_diagnostic(item.key))
            continue
        field = input_schema.fields[identity]
        if identity in seen_identities:
            diagnostics.append(_duplicate_group_key_diagnostic(item.key))
            continue
        seen_identities.add(identity)
        keys.append(_GroupKey(identity=identity, field=field, item=item))

    return keys, unknown_key_texts, diagnostics


def _effective_group_key_expression(
    expression: NameExpr | DottedNameExpr,
    *,
    let_expansions: Mapping[str, Expression] | None,
    let_stack: frozenset[str],
) -> NameExpr | DottedNameExpr:
    if not isinstance(expression, NameExpr):
        return expression
    if let_expansions is None or expression.name not in let_expansions:
        return expression
    if expression.name in let_stack:
        return expression

    expanded = let_expansions[expression.name]
    if isinstance(expanded, DottedNameExpr):
        return expanded
    if isinstance(expanded, NameExpr):
        return _effective_group_key_expression(
            expanded,
            let_expansions=let_expansions,
            let_stack=let_stack | frozenset((expression.name,)),
        )
    return expression


def _field_identity(
    definition: DerivedRelation,
    expression: Expression,
    input_schema: RowSchema,
) -> str | None:
    field = _resolve_input_field(definition, expression, input_schema)
    if field is None:
        return None
    return field.name


def _resolve_input_field(
    definition: DerivedRelation,
    expression: Expression,
    input_schema: RowSchema,
) -> RowField | None:
    if isinstance(expression, NameExpr):
        return input_schema.fields.get(expression.name)
    if isinstance(expression, DottedNameExpr):
        if (
            len(expression.parts) != 2
            or expression.parts[0] != definition.from_clause.source_name
        ):
            return None
        return input_schema.fields.get(expression.parts[1])
    return None


def _aggregate_output_field(
    item: SelectItem,
    *,
    output_name: str | None,
    expression_value_types: Mapping[Expression, ValueType] | None,
    let_expansions: Mapping[str, Expression] | None,
) -> tuple[RowField | None, list[Diagnostic], bool]:
    expression = item.expression
    diagnostics: list[Diagnostic] = []

    nested = nested_semantic_aggregate(expression)
    if nested is not None:
        diagnostics.append(nested_aggregate_diagnostic(nested))
        return _unknown_named_field(output_name), diagnostics, False

    if not is_semantic_aggregate_call(expression):
        diagnostics.append(deferred_composition_diagnostic(expression))
        return _unknown_named_field(output_name), diagnostics, False

    assert isinstance(expression, CallExpr)
    function_name = semantic_aggregate_call_name(expression)
    assert function_name is not None
    if item.alias is None:
        diagnostics.append(aggregate_alias_required_diagnostic(expression))
        return None, diagnostics, False

    if not is_supported_semantic_aggregate_arity(
        function_name,
        len(expression.arguments),
    ):
        if not _has_unknown_argument(
            expression,
            expression_value_types=expression_value_types,
        ):
            diagnostics.append(wrong_arity_diagnostic(expression))
        return _unknown_row_field(item.alias), diagnostics, False

    argument_type = None
    if expression.arguments:
        argument = expression.arguments[0]
        effective_argument = effective_semantic_aggregate_argument_expression(
            function_name,
            argument,
            let_expansions=let_expansions,
        )
        has_unknown_reference = has_unknown_field_reference(
            effective_argument,
            expression_value_types,
        )

        argument_type = (
            None
            if expression_value_types is None
            else expression_value_types.get(argument)
        )
        if argument_type is None or argument_type.kind is ValueTypeKind.UNKNOWN:
            if not has_unknown_reference:
                diagnostics.append(deferred_argument_expression_diagnostic(expression))
            return _unknown_row_field(item.alias), diagnostics, False
        if not is_supported_semantic_aggregate_argument(
            function_name,
            argument_type,
        ):
            diagnostics.append(
                wrong_argument_type_diagnostic(
                    expression,
                    actual_name=argument_type.resolved_type.name,
                )
            )
            return _unknown_row_field(item.alias), diagnostics, False
        if not is_supported_semantic_aggregate_argument_expression(
            function_name,
            argument,
            argument_type,
            let_expansions=let_expansions,
        ):
            diagnostics.append(deferred_argument_expression_diagnostic(expression))
            return _unknown_row_field(item.alias), diagnostics, False

    value_type = (
        None
        if expression_value_types is None
        else expression_value_types.get(expression)
    )
    if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
        value_type = semantic_projection_aggregate_result_value_type(
            function_name,
            argument_type,
        )
    if value_type is None:
        return _unknown_row_field(item.alias), diagnostics, False

    return (
        RowField(
            name=item.alias,
            resolved_type=value_type.resolved_type,
            nullability=value_type.nullability,
        ),
        diagnostics,
        True,
    )


def _has_unknown_argument(
    expression: CallExpr,
    *,
    expression_value_types: Mapping[Expression, ValueType] | None,
) -> bool:
    if expression_value_types is None:
        return False
    return any(
        (value_type := expression_value_types.get(argument)) is None
        or value_type.kind is ValueTypeKind.UNKNOWN
        for argument in expression.arguments
    )


def _grouped_order_by_diagnostics(
    definition: DerivedRelation,
    output_scope: Mapping[str, _GroupedOrderOutput] | None = None,
    *,
    input_schema: RowSchema | None = None,
    let_expansions: Mapping[str, Expression] | None = None,
) -> list[Diagnostic]:
    if definition.order_by_clause is None:
        return []
    if output_scope is None:
        return [
            _grouped_order_by_unsupported_diagnostic(
                definition.order_by_clause,
            )
        ]

    diagnostics: list[Diagnostic] = []
    for item in definition.order_by_clause.items:
        if not isinstance(item.expression, NameExpr):
            diagnostics.append(
                _grouped_order_by_unsupported_diagnostic(item.expression)
            )
            continue
        scoped = output_scope.get(item.expression.name)
        if scoped is not None:
            if not scoped.supported:
                diagnostics.append(
                    _grouped_order_by_unsupported_diagnostic(item.expression)
                )
            continue
        field_identity = _grouped_order_let_field_identity(
            definition,
            item.expression,
            input_schema=input_schema,
            let_expansions=let_expansions,
        )
        if field_identity is None or not any(
            output.supported and output.field_identity == field_identity
            for output in output_scope.values()
        ):
            diagnostics.append(
                _grouped_order_by_unsupported_diagnostic(item.expression)
            )
    return diagnostics


def _grouped_order_let_field_identity(
    definition: DerivedRelation,
    expression: NameExpr,
    *,
    input_schema: RowSchema | None,
    let_expansions: Mapping[str, Expression] | None,
) -> str | None:
    if input_schema is None or let_expansions is None:
        return None
    if expression.name not in let_expansions:
        return None
    effective_expression = _effective_field_let_expression(
        expression,
        let_expansions=let_expansions,
        let_stack=frozenset(),
    )
    if effective_expression is None:
        return None
    return _field_identity(definition, effective_expression, input_schema)


def _effective_field_let_expression(
    expression: NameExpr,
    *,
    let_expansions: Mapping[str, Expression],
    let_stack: frozenset[str],
) -> NameExpr | DottedNameExpr | None:
    if expression.name not in let_expansions:
        return expression
    if expression.name in let_stack:
        return None

    expanded = let_expansions[expression.name]
    if isinstance(expanded, DottedNameExpr):
        return expanded
    if isinstance(expanded, NameExpr):
        return _effective_field_let_expression(
            expanded,
            let_expansions=let_expansions,
            let_stack=let_stack | frozenset((expression.name,)),
        )
    return None


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _matches_unknown_group_key(
    expression: Expression,
    unknown_key_texts: set[str],
) -> bool:
    return isinstance(expression, (NameExpr, DottedNameExpr)) and (
        _field_text(expression) in unknown_key_texts
    )


def _field_text(expression: NameExpr | DottedNameExpr) -> str:
    if isinstance(expression, NameExpr):
        return expression.name
    return ".".join(expression.parts)


def _projected_row_field(output_name: str, input_field: RowField) -> RowField:
    if output_name == input_field.name:
        return input_field
    return RowField(
        name=output_name,
        resolved_type=input_field.resolved_type,
        nullability=input_field.nullability,
        definition=input_field.definition,
    )


def _unknown_named_field(output_name: str | None) -> RowField | None:
    if output_name is None:
        return None
    return _unknown_row_field(output_name)


def _unknown_row_field(name: str) -> RowField:
    return RowField(
        name=name,
        resolved_type=_UNKNOWN_RESOLVED_TYPE,
        nullability=EffectiveNullability.UNKNOWN,
    )


def _unknown_schema() -> RowSchema:
    return RowSchema(is_unknown=True)


def _unknown_field_diagnostic(expression: NameExpr | DottedNameExpr) -> Diagnostic:
    name = _field_text(expression)
    return _diagnostic(
        expression,
        code="PIE-S2102",
        message=f"Unknown field: {name}",
    )


def _duplicate_group_key_diagnostic(
    expression: NameExpr | DottedNameExpr,
) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2317",
        message=f"Duplicate GROUP BY key: {_field_text(expression)}",
    )


def _non_grouped_projection_diagnostic(
    expression: NameExpr | DottedNameExpr,
) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2318",
        message=f"Grouped projection is not a GROUP BY key: {_field_text(expression)}",
    )


def _scalar_grouped_projection_diagnostic(expression: Expression) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2319",
        message="Grouped scalar projection expressions are deferred",
    )


def _pure_grouped_output_deferred_diagnostic(definition: DerivedRelation) -> Diagnostic:
    assert definition.group_by_clause is not None
    return _diagnostic(
        definition.group_by_clause,
        code="PIE-S2320",
        message="Pure grouped output without an aggregate is deferred",
    )


def _grouped_order_by_unsupported_diagnostic(node: Node) -> Diagnostic:
    return _diagnostic(
        node,
        code="PIE-S2321",
        message="Unsupported grouped ORDER BY item; expected a supported select output name",
    )


def _duplicate_projection_diagnostic(
    item: SelectItem,
    output_name: str,
) -> Diagnostic:
    span = item.span
    return Diagnostic(
        code="PIE-S2305",
        severity=Severity.ERROR,
        message=f"Duplicate projection field: {output_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _diagnostic(
    expression: Node,
    *,
    code: str,
    message: str,
) -> Diagnostic:
    span = expression.span
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
