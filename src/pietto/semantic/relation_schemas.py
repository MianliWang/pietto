"""Minimal row schema propagation for table and query definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    NameExpr,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    aggregate_alias_required_diagnostic,
    contains_semantic_aggregate,
    deferred_composition_diagnostic,
    deferred_argument_expression_diagnostic,
    has_unknown_field_reference,
    is_semantic_aggregate_call,
    is_supported_semantic_aggregate_arity,
    is_supported_semantic_aggregate_argument,
    is_supported_semantic_aggregate_argument_expression,
    mixed_projection_diagnostic,
    nested_aggregate_diagnostic,
    nested_semantic_aggregate,
    semantic_aggregate_call_name,
    wrong_arity_diagnostic,
    wrong_argument_type_diagnostic,
)
from pietto.semantic.group_by import project_grouped_schema
from pietto.semantic.model import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

_UNKNOWN_RESOLVED_TYPE = ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN)


def propagate_relation_schemas(
    script: Script,
    *,
    mode: CheckMode,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    cyclic_relations: set[DerivedRelation],
    expression_value_types: Mapping[Expression, ValueType] | None = None,
) -> tuple[dict[DerivedRelation, RowSchema], list[Diagnostic]]:
    """Propagate stable projection names through table and query relations."""

    schemas: dict[DerivedRelation, RowSchema] = {}
    diagnostics: list[Diagnostic] = []
    visiting: set[DerivedRelation] = set()

    def infer(definition: DerivedRelation) -> RowSchema:
        if definition in schemas:
            return schemas[definition]
        if definition in cyclic_relations:
            schema, relation_diagnostics = _project_schema(
                definition,
                _unknown_schema(),
                mode=mode,
                expression_value_types=expression_value_types,
            )
            schemas[definition] = schema
            diagnostics.extend(relation_diagnostics)
            return schema
        if definition in visiting:
            return _unknown_schema()

        visiting.add(definition)
        target = from_resolutions.get(definition.from_clause)
        if isinstance(target, SourceDef):
            input_schema = source_row_schemas[target]
        elif isinstance(target, (TableDef, QueryDef)):
            input_schema = infer(target)
        else:
            input_schema = _unknown_schema()

        schema, relation_diagnostics = _project_schema(
            definition,
            input_schema,
            mode=mode,
            expression_value_types=expression_value_types,
        )
        visiting.remove(definition)
        schemas[definition] = schema
        diagnostics.extend(relation_diagnostics)
        return schema

    for definition in script.definitions:
        if isinstance(definition, (TableDef, QueryDef)):
            infer(definition)

    return schemas, diagnostics


def _project_schema(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    mode: CheckMode,
    expression_value_types: Mapping[Expression, ValueType] | None,
) -> tuple[RowSchema, list[Diagnostic]]:
    """Build ordered output fields from stable projection names."""

    if definition.group_by_clause is not None:
        return project_grouped_schema(
            definition,
            input_schema,
            expression_value_types=expression_value_types,
        )

    fields: dict[str, RowField] = {}
    seen_names: set[str] = set()
    diagnostics: list[Diagnostic] = []
    named_items: list[tuple[SelectItem, str]] = []
    aggregate_diagnostics, invalid_aggregate_items = _aggregate_projection_diagnostics(
        definition,
        expression_value_types=expression_value_types,
    )
    diagnostics.extend(aggregate_diagnostics)

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            diagnostic = (
                None
                if contains_semantic_aggregate(item.expression)
                else _unnamed_projection_diagnostic(item, mode)
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
            continue

        if output_name in seen_names:
            diagnostics.append(_duplicate_projection_diagnostic(item, output_name))
            continue
        seen_names.add(output_name)
        named_items.append((item, output_name))

    has_unknown_field = False
    for item, output_name in named_items:
        expression = item.expression
        if input_schema.is_unknown:
            fields[output_name] = _unknown_row_field(output_name)
            continue

        input_field = _projection_input_field(
            definition,
            item,
            input_schema,
        )
        if item in invalid_aggregate_items:
            fields[output_name] = _unknown_row_field(output_name)
            continue
        if input_field is None:
            if item.alias is None and isinstance(expression, NameExpr):
                diagnostics.append(_unknown_field_diagnostic(expression))
                has_unknown_field = True
            elif isinstance(expression, DottedNameExpr):
                has_unknown_field = True
            fields[output_name] = _computed_row_field(
                output_name,
                expression,
                expression_value_types=expression_value_types,
            )
            continue
        fields[output_name] = _projected_row_field(output_name, input_field)

    return RowSchema(
        fields=fields,
        is_unknown=input_schema.is_unknown or has_unknown_field,
    ), diagnostics


def _aggregate_projection_diagnostics(
    definition: DerivedRelation,
    *,
    expression_value_types: Mapping[Expression, ValueType] | None,
) -> tuple[list[Diagnostic], set[SelectItem]]:
    """Validate the direct aliased no-GROUP aggregate projection shape."""

    diagnostics: list[Diagnostic] = []
    invalid_items: set[SelectItem] = set()
    valid_aggregate_items: list[SelectItem] = []

    for item in definition.select_items:
        expression = item.expression
        if not contains_semantic_aggregate(expression):
            continue

        nested = nested_semantic_aggregate(expression)
        if nested is not None:
            diagnostics.append(nested_aggregate_diagnostic(nested))
            invalid_items.add(item)
            continue

        if not is_semantic_aggregate_call(expression):
            diagnostics.append(deferred_composition_diagnostic(expression))
            invalid_items.add(item)
            continue

        assert isinstance(expression, CallExpr)
        function_name = semantic_aggregate_call_name(expression)
        assert function_name is not None
        if item.alias is None:
            diagnostics.append(aggregate_alias_required_diagnostic(expression))
            invalid_items.add(item)
            continue

        if not is_supported_semantic_aggregate_arity(
            function_name,
            len(expression.arguments),
        ):
            if not _has_unknown_argument(
                expression,
                expression_value_types=expression_value_types,
            ):
                diagnostics.append(wrong_arity_diagnostic(expression))
            invalid_items.add(item)
            continue

        if expression.arguments:
            argument = expression.arguments[0]
            has_unknown_reference = has_unknown_field_reference(
                argument,
                expression_value_types,
            )
            argument_type = (
                None
                if expression_value_types is None
                else expression_value_types.get(argument)
            )
            if argument_type is None or argument_type.kind is ValueTypeKind.UNKNOWN:
                if not has_unknown_reference:
                    diagnostics.append(
                        deferred_argument_expression_diagnostic(expression)
                    )
                invalid_items.add(item)
                continue
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
                invalid_items.add(item)
                continue
            if not is_supported_semantic_aggregate_argument_expression(
                function_name,
                argument,
                argument_type,
            ):
                diagnostics.append(deferred_argument_expression_diagnostic(expression))
                invalid_items.add(item)
                continue

        valid_aggregate_items.append(item)

    has_non_aggregate_projection = any(
        not contains_semantic_aggregate(item.expression)
        for item in definition.select_items
    )
    if valid_aggregate_items and has_non_aggregate_projection:
        diagnostics.append(
            mixed_projection_diagnostic(valid_aggregate_items[0].expression)
        )
        invalid_items.update(valid_aggregate_items)

    return diagnostics, invalid_items


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


def _projection_input_field(
    definition: DerivedRelation,
    item: SelectItem,
    input_schema: RowSchema,
) -> RowField | None:
    """Return the input field referenced by a simple projection, if any."""

    expression = item.expression
    if item.alias is None and isinstance(expression, NameExpr):
        return input_schema.fields.get(expression.name)
    if isinstance(expression, DottedNameExpr):
        return _qualified_projection_input_field(
            definition,
            expression,
            input_schema,
        )
    return None


def _qualified_projection_input_field(
    definition: DerivedRelation,
    expression: DottedNameExpr,
    input_schema: RowSchema,
) -> RowField | None:
    """Resolve a two-part projection against the sole relation input."""

    if (
        len(expression.parts) != 2
        or expression.parts[0] != definition.from_clause.source_name
    ):
        return None
    return input_schema.fields.get(expression.parts[1])


def _projected_row_field(output_name: str, input_field: RowField) -> RowField:
    """Preserve input field facts while honoring the projection output name."""

    if output_name == input_field.name:
        return input_field
    return RowField(
        name=output_name,
        resolved_type=input_field.resolved_type,
        nullability=input_field.nullability,
        definition=input_field.definition,
    )


def _projection_output_name(item: SelectItem) -> str | None:
    """Return a projection's stable public output name, when one exists."""

    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _unknown_row_field(name: str) -> RowField:
    """Create a named output field whose expression type is not inferred yet."""

    return RowField(
        name=name,
        resolved_type=_UNKNOWN_RESOLVED_TYPE,
        nullability=EffectiveNullability.UNKNOWN,
    )


def _computed_row_field(
    output_name: str,
    expression: Expression,
    *,
    expression_value_types: Mapping[Expression, ValueType] | None,
) -> RowField:
    """Create an alias field from a known computed expression when available."""

    value_type = (
        None
        if expression_value_types is None
        else expression_value_types.get(expression)
    )
    if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
        return _unknown_row_field(output_name)
    return RowField(
        name=output_name,
        resolved_type=value_type.resolved_type,
        nullability=value_type.nullability,
    )


def _unknown_schema() -> RowSchema:
    """Create an immutable Unknown row schema."""

    return RowSchema(is_unknown=True)


def _unknown_field_diagnostic(expression: NameExpr) -> Diagnostic:
    """Report an unknown bare projection field at its expression span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {expression.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unnamed_projection_diagnostic(
    item: SelectItem,
    mode: CheckMode,
) -> Diagnostic | None:
    """Apply the mode-sensitive policy for unnamed computed projections."""

    if mode is CheckMode.LOOSE:
        return None
    severity = Severity.WARNING if mode is CheckMode.CHECKED else Severity.ERROR
    span = item.span
    return Diagnostic(
        code="PIE-S2304",
        severity=severity,
        message="Computed projection requires an explicit alias",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _duplicate_projection_diagnostic(
    item: SelectItem,
    output_name: str,
) -> Diagnostic:
    """Report a repeated projection output name at the later select item."""

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
