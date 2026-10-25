"""Semantic helpers for parsed GROUP BY clauses."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    LiteralExpr,
    NameExpr,
    Node,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
    inlined_arguments,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    accepts_argument_form,
    aggregate_alias_required_diagnostic,
    aggregate_argument_can_use_let_scope,
    child_expressions,
    contains_semantic_aggregate,
    deferred_argument_expression_diagnostic,
    deferred_composition_diagnostic,
    effective_semantic_aggregate_argument_expression,
    extremum_reads_let,
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
from pietto.semantic.catalog import BUILTIN_FUNCTIONS, BUILTIN_TYPE_NAMES
from pietto.semantic.expressions import (
    _canonical_value_type,
    condition_value_type,
    let_value,
    null_arithmetic_argument_diagnostics,
    resolved_binary_value_type,
    resolved_unary_value_type,
    unfit_argument,
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

from pietto.semantic.row_lookup import bare_field, qualified_field

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
    rejected_lets: frozenset[str] = frozenset(),
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    let_extrema: bool = True,
    reported_errors: frozenset[Diagnostic] | None = None,
) -> tuple[RowSchema, list[Diagnostic]]:
    """Build grouped row schema facts while keeping lowering fail-closed.

    A bare read of a name in `rejected_lets` (a let binding PIE-S2329 already
    refused) is not also reported as an unknown field. Without `let_extrema`,
    as in a single file, `min` and `max` read no `let:` name (PIE-S2315).

    Over a row of unknown type, such as a source without a shape, the relation
    is checked by the names of the fields it reads (`open_input_schema`), its
    ORDER BY is refused as a whole (PIE-S2321), and its row has no field, as
    before Pietto checked one.
    """

    diagnostics: list[Diagnostic] = []
    if definition.group_by_clause is None:
        raise AssertionError("grouped schema requires a GROUP BY clause")

    unknown = input_schema.is_unknown
    if unknown:
        # A row of unknown type hides the types of its fields, not their names.
        input_schema = open_input_schema(definition)

    group_keys, unknown_key_texts, key_diagnostics = _resolve_group_keys(
        definition,
        input_schema,
        let_expansions=let_expansions,
        rejected_lets=rejected_lets,
    )
    diagnostics.extend(key_diagnostics)

    key_fields = {key.identity: key.field for key in group_keys}
    fields: dict[str, RowField] = {}
    grouped_order_outputs: dict[str, _GroupedOrderOutput] = {}
    seen_names: set[str] = set()
    duplicate_output_names: set[str] = set()
    saw_valid_aggregate = False
    saw_invalid_projection = False

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is not None:
            if output_name in seen_names:
                diagnostics.append(_duplicate_projection_diagnostic(item, output_name))
                saw_invalid_projection = True
                duplicate_output_names.add(output_name)
                grouped_order_outputs.pop(output_name, None)
                continue
            seen_names.add(output_name)

        # Window outputs belong to the later WINDOW stage. Keep duplicate-name
        # ownership above while publishing only a concrete analyzed result into
        # the final grouped schema and final-order output scope.
        if type(item.expression) is WindowExpr:
            value_type = (
                None
                if expression_value_types is None
                else expression_value_types.get(item.expression)
            )
            valid = (
                output_name is not None
                and value_type is not None
                and value_type.kind is ValueTypeKind.KNOWN
                and value_type.resolved_type.kind is not TypeKind.UNKNOWN
                and value_type.nullability
                in {
                    EffectiveNullability.NON_NULL,
                    EffectiveNullability.NULLABLE,
                }
            )
            if output_name is not None:
                grouped_order_outputs[output_name] = _GroupedOrderOutput(
                    supported=valid,
                )
                if valid:
                    assert value_type is not None
                    fields[output_name] = RowField(
                        name=output_name,
                        resolved_type=value_type.resolved_type,
                        nullability=value_type.nullability,
                    )
            continue

        if contains_semantic_aggregate(item.expression):
            aggregate_field, aggregate_diagnostics, valid = _aggregate_output_field(
                item,
                definition=definition,
                input_schema=input_schema,
                output_name=output_name,
                expression_value_types=expression_value_types,
                let_expansions=let_expansions,
                type_expansions=type_expansions,
                reported_errors=reported_errors,
                let_extrema=let_extrema,
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
                key_field = key_fields[key_identity]
                fields[output_name] = (
                    _unknown_row_field(output_name)
                    if passes_unfit_field(
                        item.expression, key_field, expression_value_types
                    )
                    else _projected_row_field(output_name, key_field)
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
                if (
                    isinstance(item.expression, NameExpr)
                    and item.expression.name not in rejected_lets
                ):
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
            None if unknown else grouped_order_outputs,
            input_schema=input_schema,
            let_expansions=let_expansions,
            suppressed_output_names=duplicate_output_names,
        )
    )

    if not saw_valid_aggregate and not saw_invalid_projection:
        diagnostics.append(_pure_grouped_output_deferred_diagnostic(definition))

    if unknown:
        return RowSchema(is_unknown=True), diagnostics
    return RowSchema(fields=fields), diagnostics


def _resolve_group_keys(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    let_expansions: Mapping[str, Expression] | None,
    rejected_lets: frozenset[str] = frozenset(),
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
            if not (isinstance(item.key, NameExpr) and item.key.name in rejected_lets):
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
        return bare_field(input_schema, expression.name)
    if isinstance(expression, DottedNameExpr):
        return qualified_field(
            input_schema,
            expression.parts,
            (definition.from_clause.binding_name or definition.from_clause.source_name),
        )
    return None


def _aggregate_output_field(
    item: SelectItem,
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    output_name: str | None,
    expression_value_types: Mapping[Expression, ValueType] | None,
    let_expansions: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    let_extrema: bool,
    reported_errors: frozenset[Diagnostic] | None = None,
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
        ) or (
            input_schema.is_unknown
            and unknown_row_arguments(
                function_name,
                expression,
                definition=definition,
                input_schema=input_schema,
                let_expansions=let_expansions,
                value_types=expression_value_types,
                type_expansions=type_expansions,
            )
        ):
            diagnostics.append(wrong_arity_diagnostic(expression))
        return _unknown_row_field(item.alias), diagnostics, False

    argument_type = None
    if expression.arguments:
        argument = expression.arguments[0]
        unread = (
            unread_let_diagnostics(function_name, argument, let_expansions)
            if input_schema.is_unknown
            else []
        )
        authored_type = (
            None
            if expression_value_types is None
            else expression_value_types.get(argument)
        )
        if unread:
            diagnostics.extend(unread)
            if (
                authored_type is not None
                and authored_type.kind is ValueTypeKind.KNOWN
                and not is_supported_semantic_aggregate_argument(
                    function_name,
                    _canonical_value_type(authored_type, type_expansions, enum=True),
                )
            ):
                diagnostics.append(
                    wrong_argument_type_diagnostic(
                        expression,
                        actual_name=authored_type.resolved_type.name,
                    )
                )
            return _unknown_row_field(item.alias), diagnostics, False
        checked = (
            unknown_row_aggregate(
                function_name,
                expression,
                definition=definition,
                input_schema=input_schema,
                let_expansions=let_expansions,
                value_types=expression_value_types,
                type_expansions=type_expansions,
                reported_errors=reported_errors,
            )
            if input_schema.is_unknown
            else None
        )
        if authored_type is None or authored_type.kind is ValueTypeKind.UNKNOWN:
            if checked is not None:
                valid, errors = checked
                diagnostics.extend(errors)
                return _unknown_row_field(item.alias), diagnostics, valid
            if not unknown_to_aggregate(
                function_name,
                argument,
                definition=definition,
                input_schema=input_schema,
                let_expansions=let_expansions,
                value_types=expression_value_types,
                type_expansions=type_expansions,
                reported_errors=reported_errors,
            ):
                diagnostics.append(deferred_argument_expression_diagnostic(expression))
            return _unknown_row_field(item.alias), diagnostics, False
        # An aggregate reads a type alias argument as the type it expands to.
        argument_type = _canonical_value_type(authored_type, type_expansions, enum=True)
        if not is_supported_semantic_aggregate_argument(
            function_name,
            argument_type,
        ):
            diagnostics.append(
                wrong_argument_type_diagnostic(
                    expression,
                    actual_name=authored_type.resolved_type.name,
                )
            )
            return _unknown_row_field(item.alias), diagnostics, False
        if (
            not let_extrema
            and extremum_reads_let(
                function_name, argument, let_expansions, input_schema
            )
        ) or not is_supported_semantic_aggregate_argument_expression(
            function_name,
            argument,
            argument_type,
            let_expansions=let_expansions,
        ):
            diagnostics.append(deferred_argument_expression_diagnostic(expression))
            return _unknown_row_field(item.alias), diagnostics, False
        if checked is not None and not checked[0]:
            # A call typed by its signature beside a field of the row has a
            # type that no field type may give it.
            diagnostics.extend(checked[1])
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
    suppressed_output_names: set[str] | None = None,
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
        if item.expression.name in (suppressed_output_names or set()):
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


def passes_unfit_field(
    expression: Expression,
    input_field: RowField,
    value_types: Mapping[Expression, ValueType] | None,
) -> bool:
    """Whether ``expression`` selects ``input_field`` passed to a ``def`` it
    does not fit (PIE-S2395), which typing records as Unknown although the
    field has a type: its output then has no type, as a computed output with
    an error has."""

    if (
        not inlined_arguments(expression)
        or value_types is None
        or input_field.resolved_type.kind is TypeKind.UNKNOWN
    ):
        return False
    value_type = value_types.get(expression)
    return value_type is not None and value_type.kind is ValueTypeKind.UNKNOWN


def unknown_to_aggregate(
    function_name: str,
    argument: Expression,
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    reported_errors: frozenset[Diagnostic] | None = None,
    reading_field: bool = False,
) -> bool:
    """Whether the aggregate ``function_name`` adds no PIE-S2315 for its
    ``argument`` of unknown type: a scalar error from typed NULL arithmetic
    is already specific, or the argument reads a field of unknown type,
    or a ``def`` argument in it that does not fit its parameter, at any depth
    or in the value of a `let:` name it reads, is unknown because of its own
    PIE-S2395 and the aggregate accepts the argument's form for some argument
    type. A part that is unknown only because of such a ``def`` argument is no
    field of unknown type. The aggregate reads a `let:` name only as its whole
    argument, and then the names that name's value reads; over an input row of
    known shape a `min` or `max` argument reads any `let:` name in it as its
    value, its form is accepted for no argument type, and a field of unknown
    type there does not make it unknown (`extremum_reads_let`).

    With ``reading_field``, whether only fields of unknown type leave the
    argument unknown: it reads one and holds no such ``def`` argument."""

    if value_types is None:
        return False
    if reported_errors:
        error_argument = (
            let_value(argument, input_schema, let_expansions)
            if aggregate_argument_can_use_let_scope(
                function_name, argument, let_expansions
            )
            else argument
        )
        if null_arithmetic_argument_diagnostics(
            error_argument,
            input_schema,
            value_types,
            let_expansions,
            type_expansions,
            reported_errors=reported_errors,
        ):
            return True
    extremum = extremum_reads_let(function_name, argument, let_expansions, input_schema)
    lets = (
        let_expansions
        if let_expansions is not None
        and (
            extremum
            or aggregate_argument_can_use_let_scope(
                function_name, argument, let_expansions
            )
        )
        else {}
    )

    def unfit(node: Expression) -> bool:
        if not inlined_arguments(node):
            return False
        if isinstance(node, DottedNameExpr) or (
            isinstance(node, NameExpr) and node.name not in lets
        ):
            field = _resolve_input_field(definition, node, input_schema)
            return field is not None and passes_unfit_field(node, field, value_types)
        return unfit_argument(
            function_name, node, let_expansions, value_types, type_expansions
        )

    def holds_unfit(root: Expression) -> bool:
        reached: set[str] = set()
        pending = [root]
        while pending:
            node = pending.pop()
            if unfit(node):
                return True
            if isinstance(node, NameExpr) and node.name in lets:
                if node.name not in reached:
                    reached.add(node.name)
                    pending.append(lets[node.name])
            else:
                pending.extend(child_expressions(node))
        return False

    pending = [
        effective_semantic_aggregate_argument_expression(
            function_name, argument, let_expansions=let_expansions
        )
    ]
    followed: set[str] = set()
    reads_field = False
    while pending and not reads_field:
        node = pending.pop()
        if not isinstance(node, (NameExpr, DottedNameExpr)):
            pending.extend(child_expressions(node))
            continue
        # A name met again (`w = w`) is checked as the read it is.
        if (
            extremum
            and isinstance(node, NameExpr)
            and node.name in lets
            and node.name not in followed
        ):
            followed.add(node.name)
            pending.append(lets[node.name])
            continue
        value_type = value_types.get(node)
        reads_field = (
            (value_type is None or value_type.kind is ValueTypeKind.UNKNOWN)
            and not unfit(node)
            and not (
                isinstance(node, NameExpr)
                and node.name in lets
                and holds_unfit(lets[node.name])
            )
            # There a field of unknown type is still read through a name that
            # is no direct field; only an error elsewhere explains the name.
            and not (
                extremum
                and _resolve_input_field(definition, node, input_schema) is not None
            )
        )
    if reading_field:
        return reads_field and not holds_unfit(argument)
    if reads_field:
        return True
    # In a form the aggregate accepts for no argument type, it is also
    # PIE-S2315, which no argument type would avoid.
    return (
        not extremum
        and holds_unfit(argument)
        and accepts_argument_form(
            function_name, argument, let_expansions=let_expansions
        )
    )


def unknown_row_aggregate(
    function_name: str,
    expression: CallExpr,
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    reported_errors: frozenset[Diagnostic] | None = None,
) -> tuple[bool, list[Diagnostic]] | None:
    """Check the aggregate ``expression`` of a relation over a row of unknown
    type, such as a source without a shape, read as ``input_schema`` from
    `open_input_schema`, whose one argument reads fields of that row, which
    alone leave it unknown when it is, as over a known row of field types
    the argument allows: whether it is valid, and its errors. It is valid
    when the aggregate accepts the argument's form for a type the argument
    has for one type of each of those fields (`_argument_types`), so a part
    of known type, such as a literal, is checked as over a known row:
    `count(x + 1)` is valid and `count(x + "a")` and `count(len(x) + x)` are
    PIE-S2315, as over a row of any field types, and so is any other form. A
    read of a name that is no field of the row has an error of its own, and
    so has an argument of an accepted form in which typing reported one.
    An already-reported typed-NULL scalar error also stands alone when the
    argument form is refused.
    None when the argument reads no field of the row or is unknown for
    another reason."""

    argument = expression.arguments[0]
    reads = _reads_unknown_row(
        function_name,
        argument,
        definition=definition,
        input_schema=input_schema,
        let_expansions=let_expansions,
        value_types=value_types,
        type_expansions=type_expansions,
    )
    if reads is None:
        return None
    if not reads:
        return False, []
    form = effective_semantic_aggregate_argument_expression(
        function_name, argument, let_expansions=let_expansions
    )
    if accepts_argument_form(function_name, form):
        types = _argument_types(
            argument,
            lambda name: is_supported_semantic_aggregate_argument_expression(
                function_name, form, _builtin_type(name), form_only=True
            ),
            definition=definition,
            input_schema=input_schema,
            let_expansions=let_expansions,
            value_types=value_types or {},
            type_expansions=type_expansions,
        )
        if types is None:
            return False, []
        if types:
            return True, []
    if reported_errors and value_types is not None:
        error_argument = (
            let_value(argument, input_schema, let_expansions)
            if aggregate_argument_can_use_let_scope(
                function_name, argument, let_expansions
            )
            else argument
        )
        if null_arithmetic_argument_diagnostics(
            error_argument,
            input_schema,
            value_types,
            let_expansions,
            type_expansions,
            reported_errors=reported_errors,
        ):
            return False, []
    return False, [deferred_argument_expression_diagnostic(expression)]


_ArgumentPart = tuple[ValueType | None, frozenset[str]]

# A field of a row of unknown type that an aggregate argument reads takes the
# first of these types that all its reads may have. When some field types
# give the argument a type the aggregate accepts, so do those that make each
# field of a number type an `Int`: only fields give a `Decimal` in such an
# argument, so each part of a number type is then an `Int`, or a `Float`
# where it reads a `Float` literal, and each rule that takes a number takes
# either beside either, but `%`, which takes only an `Int`, as its operands
# then still are.
_FIELD_TYPE_ORDER = ("Int", *sorted(BUILTIN_TYPE_NAMES - {"Int"}))


def _argument_types(
    argument: Expression,
    accepts: Callable[[str], bool],
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> frozenset[str] | None:
    """The built-in types that ``argument``, an aggregate argument in a form
    the aggregate accepts over the row of unknown type ``input_schema``, has
    of those ``accepts`` takes, for one type of each field of that row it
    reads, also through the values of the `let:` names it reads, if some
    field types give it one, and else none: a literal or other leaf that
    typing typed has that type, a field read the type of its field, a null
    any type, as each `null` is typed by its operator, and an operator or a
    function each type its rule gives over the types its operands may have,
    none when an operand may have none, as a call typed by its signature
    beside a field may not (`lower(x + 1)`). None when typing reported an
    error in it, which explains its unknown type: typing gave no type to a
    part all of whose operands it typed, read an `and` or `or` operand of a
    known type that is not `Bool` as a condition (`condition_value_type`), or
    found a null arithmetic operand beside one of a type that the operator
    does not take twice.

    The types each part may have, each read of a field taking any type, give
    from the types the aggregate accepts down the types each read may have
    there; a field then takes the first type of `_FIELD_TYPE_ORDER` that all
    its reads may have, which gives the argument a type the aggregate accepts
    when any field types do. Each part is visited three times, so the cost
    grows linearly with the argument and the `let:` values it reads."""

    lets = let_expansions or {}
    row = RowSchema(is_unknown=True)

    def typed(node: Expression) -> ValueType | None:
        value_type = value_types.get(node)
        if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
            return None
        return _canonical_value_type(value_type, type_expansions)

    def refused(node: BinaryExpr) -> bool:
        if node.operator in {"and", "or"}:
            return any(
                (
                    condition := _canonical_value_type(
                        condition_value_type(
                            operand, value_types.get(operand, _UNKNOWN_TYPE), row, lets
                        ),
                        type_expansions,
                    )
                ).kind
                is ValueTypeKind.KNOWN
                and _type_names(condition) != {"Bool"}
                for operand in (node.left, node.right)
            )
        for null, other in ((node.left, node.right), (node.right, node.left)):
            other_type = typed(other)
            value = let_value(null, row, lets)
            if (
                other_type is not None
                and type(value) is LiteralExpr
                and value.value is None
            ):
                return (
                    resolved_binary_value_type(node.operator, other_type, other_type)[1]
                    is not None
                )
        return False

    def reads(node: Expression) -> tuple[Expression, ...]:
        if isinstance(node, NameExpr) and node.name in lets:
            return (lets[node.name],)
        return child_expressions(node)

    def field(node: Expression) -> str | None:
        if (
            not isinstance(node, (NameExpr, DottedNameExpr))
            or (isinstance(node, NameExpr) and node.name in lets)
            or typed(node) is not None
        ):
            return None
        return _field_identity(definition, node, input_schema)

    def evaluate(
        node: Expression,
        parts: Mapping[int, _ArgumentPart | None],
        field_types: Mapping[str, frozenset[str]],
    ) -> _ArgumentPart | None:
        known = typed(node)
        operands: list[frozenset[str]] = []
        operands_typed = True
        for child in reads(node):
            operand = parts[id(child)]
            if operand is None:
                return None
            operands.append(operand[1])
            operands_typed = operands_typed and operand[0] is not None
        if isinstance(node, NameExpr) and node.name in lets:
            return known, operands[0]
        if not operands:
            if known is not None:
                return known, _type_names(known)
            name = field(node)
            return known, (
                BUILTIN_TYPE_NAMES
                if name is None
                else field_types.get(name, BUILTIN_TYPE_NAMES)
            )
        if operands_typed:
            if known is None:
                # Typing checked the part with the type of each operand.
                return None
        elif isinstance(node, BinaryExpr) and refused(node):
            return None
        return known, _part_types(node, operands)

    # A loop, not recursion, as `let:` values may nest deeper than the
    # interpreter's recursion limit (PIE-S2328); a part on its own path is a
    # `let:` cycle, which has an error of its own. Each part follows the
    # parts it reads in `order`.
    parts: dict[int, _ArgumentPart | None] = {}
    order: list[Expression] = []
    on_path: set[int] = set()
    pending: list[tuple[Expression, bool]] = [(argument, False)]
    while pending:
        node, read = pending.pop()
        key = id(node)
        if read:
            on_path.discard(key)
            parts[key] = evaluate(node, parts, {})
            order.append(node)
        elif key in on_path:
            parts[key] = None
        elif key not in parts:
            on_path.add(key)
            pending.append((node, True))
            pending.extend((child, False) for child in reads(node))
    if parts[id(argument)] is None:
        return None
    may = {key: part[1] for key, part in parts.items() if part is not None}

    # The types each part may have where the argument has one the aggregate
    # accepts: those that give each part reading it such a type beside some
    # types of its other operands.
    accepted = frozenset(filter(accepts, may[id(argument)]))
    needs = {id(argument): accepted}
    reads_need: dict[str, frozenset[str]] = {}
    for node in reversed(order):
        need = needs[id(node)]
        name = field(node)
        if name is not None:
            reads_need[name] = reads_need.get(name, need) & need
            continue
        children = reads(node)
        for child, child_need in zip(
            children,
            [need]
            if isinstance(node, NameExpr) and node.name in lets
            else _operand_needs(node, [may[id(child)] for child in children], need),
            strict=True,
        ):
            key = id(child)
            needs[key] = needs[key] & child_need if key in needs else child_need

    field_types: dict[str, frozenset[str]] = {}
    for name, types in reads_need.items():
        first = next((each for each in _FIELD_TYPE_ORDER if each in types), None)
        if first is None:
            return frozenset()
        field_types[name] = frozenset({first})
    typed_parts: dict[int, _ArgumentPart | None] = {}
    for node in order:
        typed_parts[id(node)] = evaluate(node, typed_parts, field_types)
    typed_argument = typed_parts[id(argument)]
    assert typed_argument is not None
    return typed_argument[1] & accepted


_UNKNOWN_TYPE = ValueType(
    resolved_type=_UNKNOWN_RESOLVED_TYPE,
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


def _type_names(value_type: ValueType) -> frozenset[str]:
    resolved = value_type.resolved_type
    if resolved.kind is TypeKind.BUILTIN:
        return frozenset({resolved.name})
    return frozenset()


def _part_types(node: Expression, operands: list[frozenset[str]]) -> frozenset[str]:
    """The types an operator or a built-in function gives ``node`` over
    operands of the types ``operands``; any type for another part, which no
    aggregate accepts in its argument."""

    if isinstance(node, UnaryExpr):
        return _unary_types(node.operator, operands[0])
    if isinstance(node, BinaryExpr):
        return _binary_types(node.operator, operands[0], operands[1])
    if isinstance(node, CallExpr) and isinstance(node.callee, NameExpr):
        signature = BUILTIN_FUNCTIONS.get(node.callee.name)
        if signature is not None and len(signature.parameter_types) == len(operands):
            if all(
                parameter in types
                for parameter, types in zip(
                    signature.parameter_types, operands, strict=True
                )
            ):
                return frozenset({signature.return_type})
            return frozenset()
    return BUILTIN_TYPE_NAMES


def _operand_needs(
    node: Expression, operands: list[frozenset[str]], need: frozenset[str]
) -> list[frozenset[str]]:
    """The types of each operand of ``node``, of the types ``operands`` its
    operands may have, that give ``node`` a type of ``need`` beside some
    types of its other operands (`_part_types`)."""

    return [
        frozenset(
            name
            for name in types
            if _part_types(
                node, [*operands[:index], frozenset({name}), *operands[index + 1 :]]
            )
            & need
        )
        for index, types in enumerate(operands)
    ]


@cache
def _builtin_type(name: str) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=EffectiveNullability.UNKNOWN,
    )


@cache
def _unary_types(operator: str, operand: frozenset[str]) -> frozenset[str]:
    return frozenset(
        result.resolved_type.name
        for name in operand
        for result, expected in (
            resolved_unary_value_type(operator, _builtin_type(name)),
        )
        if expected is None and result.kind is ValueTypeKind.KNOWN
    )


@cache
def _binary_types(
    operator: str, left: frozenset[str], right: frozenset[str]
) -> frozenset[str]:
    return frozenset(
        result.resolved_type.name
        for left_name in left
        for right_name in right
        for result, expected in (
            resolved_binary_value_type(
                operator, _builtin_type(left_name), _builtin_type(right_name)
            ),
        )
        if expected is None and result.kind is ValueTypeKind.KNOWN
    )


def unknown_row_arguments(
    function_name: str,
    expression: CallExpr,
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether each argument of the aggregate ``expression`` of a relation over
    a row of unknown type, read as ``input_schema`` from `open_input_schema`,
    that has no type has none only because it reads fields of that row, so a
    wrong number of arguments is PIE-S2309 as over a known row."""

    return value_types is not None and all(
        (
            (value_type := value_types.get(argument)) is not None
            and value_type.kind is not ValueTypeKind.UNKNOWN
        )
        or _reads_unknown_row(
            function_name,
            argument,
            definition=definition,
            input_schema=input_schema,
            let_expansions=let_expansions,
            value_types=value_types,
            type_expansions=type_expansions,
        )
        is True
        for argument in expression.arguments
    )


def _reads_unknown_row(
    function_name: str,
    argument: Expression,
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool | None:
    """Whether ``argument`` of the aggregate ``function_name``, over the row
    of unknown type ``input_schema`` from `open_input_schema`, reads only
    fields of that row, also through the values of the `let:` names it reads:
    None when it is unknown for another reason (`unknown_to_aggregate`), and
    False when it reads a name that is no field of the row."""

    if not unknown_to_aggregate(
        function_name,
        argument,
        definition=definition,
        input_schema=input_schema,
        let_expansions=let_expansions,
        value_types=value_types,
        type_expansions=type_expansions,
        reading_field=True,
    ):
        return None
    lets = let_expansions or {}
    pending: list[tuple[Expression, frozenset[str]]] = [(argument, frozenset())]
    while pending:
        node, reached = pending.pop()
        if isinstance(node, NameExpr) and node.name in lets:
            if node.name in reached:
                return False
            pending.append((lets[node.name], reached | {node.name}))
        elif isinstance(node, (NameExpr, DottedNameExpr)):
            if _resolve_input_field(definition, node, input_schema) is None:
                return False
        else:
            pending.extend((child, reached) for child in child_expressions(node))
    return True


def unread_let_diagnostics(
    function_name: str,
    argument: Expression,
    let_expansions: Mapping[str, Expression] | None,
) -> list[Diagnostic]:
    """PIE-S2102 for each `let:` name that the aggregate ``function_name``
    reads in ``argument`` of a relation over a row of unknown type where it
    reads no `let:` name: inside a call or an operator, or as the argument of
    `min` or `max`. Such a name is no field of the row, as over a known row."""

    lets = let_expansions or {}
    if aggregate_argument_can_use_let_scope(function_name, argument, lets):
        return []
    diagnostics: list[Diagnostic] = []
    pending = [argument]
    while pending:
        node = pending.pop()
        if isinstance(node, NameExpr):
            if node.name in lets:
                diagnostics.append(_unknown_field_diagnostic(node))
        else:
            pending.extend(reversed(child_expressions(node)))
    return diagnostics


def open_input_schema(definition: DerivedRelation) -> RowSchema:
    """Return the row of unknown type ``definition`` reads, such as a source
    without a shape, as its grouping and aggregates read it: each name its
    `let:` values, GROUP BY keys and SELECT items read, bare or after its
    `from` binding, that no `let:` binds is a field of unknown type there, and
    the row stays unknown to any other read."""

    lets = () if definition.let_clause is None else definition.let_clause.bindings
    keys = (
        () if definition.group_by_clause is None else definition.group_by_clause.items
    )
    let_names = {binding.name for binding in lets}
    pending: list[Expression] = [
        *(binding.expression for binding in lets),
        *(item.key for item in keys),
        *(item.expression for item in definition.select_items),
    ]
    pending.reverse()
    fields: dict[str, RowField] = {}
    while pending:
        node = pending.pop()
        if isinstance(node, NameExpr):
            name = None if node.name in let_names else node.name
        elif isinstance(node, DottedNameExpr):
            name = (
                node.parts[1]
                if len(node.parts) == 2
                and node.parts[0]
                == (
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                )
                else None
            )
        else:
            pending.extend(reversed(child_expressions(node)))
            continue
        if name is not None and name not in fields:
            fields[name] = _unknown_row_field(name)
    return RowSchema(fields=fields, is_unknown=True)


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
        message="Grouped scalar projection expressions are not supported yet",
    )


def _pure_grouped_output_deferred_diagnostic(definition: DerivedRelation) -> Diagnostic:
    assert definition.group_by_clause is not None
    return _diagnostic(
        definition.group_by_clause,
        code="PIE-S2320",
        message="Grouped output without an aggregate is not supported yet",
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
