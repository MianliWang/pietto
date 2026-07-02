"""Private semantic helpers for relation-local ``let:`` bindings."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    FromClause,
    IsNullExpr,
    LetBinding,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import (
    LetScopeSemanticInfo,
    RowSchema,
    ValueType,
)

DerivedRelation = TableDef | QueryDef
RelationDefinition = SourceDef | TableDef | QueryDef


def analyze_relation_let_bindings(
    definitions: tuple[Definition, ...],
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> tuple[
    dict[DerivedRelation, LetScopeSemanticInfo],
    dict[Expression, ValueType],
    list[Diagnostic],
]:
    """Validate relation-local let clauses and return private value scopes."""

    scopes: dict[DerivedRelation, LetScopeSemanticInfo] = {}
    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        if definition.let_clause is None:
            continue
        input_schema = _input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        scope, relation_values, relation_diagnostics = _analyze_relation_let_clause(
            definition,
            input_schema,
        )
        scopes[definition] = scope
        value_types.update(relation_values)
        diagnostics.extend(relation_diagnostics)

    return scopes, value_types, diagnostics


def let_projection_conflict_diagnostics(
    definition: DerivedRelation,
    let_scope: LetScopeSemanticInfo | None,
) -> list[Diagnostic]:
    """Report projection output names that collide with relation let names."""

    if let_scope is None:
        return []
    let_names = set(let_scope.value_types)
    diagnostics: list[Diagnostic] = []
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is not None and output_name in let_names:
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    item,
                    output_name,
                    reason="Projection output name conflicts with let binding",
                )
            )
    return diagnostics


def _analyze_relation_let_clause(
    definition: DerivedRelation,
    input_schema: RowSchema,
) -> tuple[LetScopeSemanticInfo, dict[Expression, ValueType], list[Diagnostic]]:
    assert definition.let_clause is not None

    diagnostics: list[Diagnostic] = []
    value_types: dict[Expression, ValueType] = {}
    scope_values: dict[str, ValueType] = {}
    seen_names: set[str] = set()
    all_names = tuple(binding.name for binding in definition.let_clause.bindings)
    all_name_set = set(all_names)
    invalid_binding_names = _invalid_binding_names(
        definition,
        input_schema,
        diagnostics,
    )

    for binding in definition.let_clause.bindings:
        if contains_semantic_aggregate(binding.expression):
            diagnostics.append(
                invalid_context_diagnostic(binding.expression, context="let binding")
            )
        suppressed_unknown_names = _dependency_diagnostics(
            binding,
            all_name_set=all_name_set,
            prior_names=set(scope_values),
            diagnostics=diagnostics,
        )
        value_type = infer_row_expression(
            binding.expression,
            input_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=definition.from_clause.source_name,
            bare_value_types=scope_values,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        if binding.name not in invalid_binding_names and binding.name not in seen_names:
            scope_values[binding.name] = value_type
        seen_names.add(binding.name)

    return (
        LetScopeSemanticInfo(
            clause=definition.let_clause,
            bindings=tuple(definition.let_clause.bindings),
            value_types=dict(scope_values),
        ),
        value_types,
        diagnostics,
    )


def _invalid_binding_names(
    definition: DerivedRelation,
    input_schema: RowSchema,
    diagnostics: list[Diagnostic],
) -> set[str]:
    assert definition.let_clause is not None

    invalid_names: set[str] = set()
    seen_names: set[str] = set()
    projection_outputs = {
        output_name
        for item in definition.select_items
        if (output_name := _projection_output_name(item)) is not None
    }

    for binding in definition.let_clause.bindings:
        if binding.name in seen_names:
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Duplicate let binding name",
                )
            )
            invalid_names.add(binding.name)
            continue
        seen_names.add(binding.name)

        if binding.name in input_schema.fields:
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding cannot shadow input field",
                )
            )
            invalid_names.add(binding.name)
            continue
        if binding.name == definition.from_clause.source_name:
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding cannot shadow input relation",
                )
            )
            invalid_names.add(binding.name)
            continue
        if binding.name in projection_outputs:
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding conflicts with projection output name",
                )
            )
            invalid_names.add(binding.name)

    return invalid_names


def _dependency_diagnostics(
    binding: LetBinding,
    *,
    all_name_set: set[str],
    prior_names: set[str],
    diagnostics: list[Diagnostic],
) -> set[str]:
    suppressed_unknown_names: set[str] = set()
    reported_names: set[str] = set()
    for expression in _walk_expressions(binding.expression):
        if not isinstance(expression, NameExpr):
            continue
        if expression.name == binding.name:
            diagnostics.append(
                _invalid_let_dependency_diagnostic(
                    expression,
                    expression.name,
                    reason="Let binding cannot reference itself",
                )
            )
            suppressed_unknown_names.add(expression.name)
            reported_names.add(expression.name)
            continue
        if (
            expression.name in all_name_set
            and expression.name not in prior_names
            and expression.name not in reported_names
        ):
            diagnostics.append(
                _invalid_let_dependency_diagnostic(
                    expression,
                    expression.name,
                    reason="Let binding cannot reference a later binding",
                )
            )
            suppressed_unknown_names.add(expression.name)
            reported_names.add(expression.name)
    return suppressed_unknown_names


def _input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> RowSchema:
    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _walk_expressions(expression: Expression) -> tuple[Expression, ...]:
    children: list[Expression] = []
    if isinstance(expression, CallExpr):
        children.append(expression.callee)
        children.extend(expression.arguments)
    elif isinstance(expression, UnaryExpr):
        children.append(expression.operand)
    elif isinstance(expression, BinaryExpr):
        children.extend((expression.left, expression.right))
    elif isinstance(expression, ComparisonExpr):
        children.extend((expression.left, expression.right))
    elif isinstance(expression, BetweenExpr):
        children.extend((expression.value, expression.lower, expression.upper))
    elif isinstance(expression, IsNullExpr):
        children.append(expression.value)

    walked: list[Expression] = [expression]
    for child in children:
        walked.extend(_walk_expressions(child))
    return tuple(walked)


def _invalid_let_name_diagnostic(
    node: LetBinding | SelectItem,
    name: str,
    *,
    reason: str,
) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code="PIE-S2329",
        severity=Severity.ERROR,
        message=f"{reason}: {name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _invalid_let_dependency_diagnostic(
    expression: NameExpr,
    name: str,
    *,
    reason: str,
) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code="PIE-S2330",
        severity=Severity.ERROR,
        message=f"{reason}: {name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
