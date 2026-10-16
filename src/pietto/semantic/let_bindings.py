"""Private semantic helpers for relation-local ``let:`` bindings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    ConditionalExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    FromClause,
    IsNullExpr,
    LetBinding,
    LiteralExpr,
    MembershipExpr,
    Node,
    RelationExistsExpr,
    RelationScalarExpr,
    RelationMembershipExpr,
    NameExpr,
    ParameterRefExpr,
    QueryDef,
    SelectItem,
    SetRelationDef,
    SourceDef,
    TableDef,
    TypeExpr,
    UnaryExpr,
    TableFunctionRelationDef,
    ValuesRelationDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import (
    LetScopeSemanticInfo,
    ResolvedType,
    RowSchema,
    ValueType,
)

DerivedRelation = TableDef | QueryDef
RelationDefinition = (
    SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | ValuesRelationDef
    | TableFunctionRelationDef
)
RelationInputSchemas = (
    Mapping[DerivedRelation, RowSchema]
    | Mapping[DerivedRelation | SetRelationDef, RowSchema]
    | Mapping[DerivedRelation | SetRelationDef | ValuesRelationDef, RowSchema]
    | Mapping[
        DerivedRelation | SetRelationDef | ValuesRelationDef | TableFunctionRelationDef,
        RowSchema,
    ]
)


def analyze_relation_let_bindings(
    definitions: tuple[Definition, ...],
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: RelationInputSchemas,
    allow_unaliased_selected_let_outputs: bool = False,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
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
            allow_unaliased_selected_let_outputs=(allow_unaliased_selected_let_outputs),
            type_expansions=type_expansions,
        )
        scopes[definition] = scope
        value_types.update(relation_values)
        diagnostics.extend(relation_diagnostics)

    return scopes, value_types, diagnostics


def admitted_relation_let_expressions(
    definition: DerivedRelation,
    input_schema: RowSchema,
) -> dict[str, Expression]:
    """Return relation-local let expressions admitted into the private scope."""

    if definition.let_clause is None:
        return {}
    invalid_names = _invalid_binding_names(definition, input_schema, [])
    expressions: dict[str, Expression] = {}
    seen_names: set[str] = set()
    for binding in definition.let_clause.bindings:
        if binding.name not in invalid_names and binding.name not in seen_names:
            expressions[binding.name] = binding.expression
        seen_names.add(binding.name)
    return expressions


# Single-file IR inlines every `let:` binding at each read, so the size and
# depth of an expression after inlining bound the IR and SQL it produces.
_MAX_INLINE_NODES = 100_000
_MAX_INLINE_DEPTH = 256


def let_expansion_diagnostics(
    definition: DerivedRelation,
    admitted: Mapping[str, object],
) -> list[Diagnostic]:
    """Refuse expressions whose single-file let inline expansion is too big.

    Each binding and each relation expression that reads an admitted earlier
    binding is measured after inlining it. Only the first expression past a
    bound on a read path is reported (PIE-S2328).
    """

    if definition.let_clause is None:
        return []
    diagnostics: list[Diagnostic] = []
    # Per inlined binding: (node count, depth, it or a binding it reads exceeds).
    measured: dict[str, tuple[int, int, bool]] = {}

    def measure(expression: Expression) -> tuple[int, int, bool, bool]:
        """Return node count, depth, an exceeding read, and any let read."""

        if type(expression) is NameExpr and expression.name in measured:
            return (*measured[expression.name], True)
        size, depth, exceeded, inlined = 1, 0, False, False
        for operand in _operands(expression):
            operand_size, operand_depth, operand_exceeded, operand_inlined = measure(
                operand
            )
            size += operand_size
            depth = max(depth, operand_depth)
            exceeded = exceeded or operand_exceeded
            inlined = inlined or operand_inlined
        return size, depth + 1, exceeded, inlined

    def check(
        node: Node, expression: Expression, binding: str | None
    ) -> tuple[int, int, bool]:
        size, depth, exceeded, inlined = measure(expression)
        exceeds = inlined and (size > _MAX_INLINE_NODES or depth > _MAX_INLINE_DEPTH)
        if exceeds and not exceeded:
            diagnostics.append(_inline_expansion_diagnostic(node, binding, depth=depth))
        return size, depth, exceeds or exceeded

    for binding in definition.let_clause.bindings:
        if binding.name in admitted and binding.name not in measured:
            measured[binding.name] = check(binding, binding.expression, binding.name)
    for expression in _relation_expressions(definition):
        check(expression, expression, None)
    return diagnostics


def _relation_expressions(definition: DerivedRelation) -> tuple[Expression, ...]:
    """Return the relation expressions that single-file IR lowers with lets."""

    return (
        *(
            ()
            if definition.where_clause is None
            else (definition.where_clause.expression,)
        ),
        *(
            ()
            if definition.group_by_clause is None
            else tuple(item.key for item in definition.group_by_clause.items)
        ),
        *(item.expression for item in definition.select_items),
        *(
            ()
            if definition.satisfying_clause is None
            else (definition.satisfying_clause.expression,)
        ),
        *(
            ()
            if definition.order_by_clause is None
            else tuple(item.expression for item in definition.order_by_clause.items)
        ),
    )


def _operands(expression: Expression) -> tuple[Expression, ...]:
    """Return the operands that let inline expansion descends into."""

    if isinstance(expression, CallExpr):
        return expression.arguments
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, (CastExpr, IsNullExpr, RelationMembershipExpr)):
        return (expression.value,)
    if isinstance(expression, (BinaryExpr, ComparisonExpr)):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    return ()


def _inline_expansion_diagnostic(
    node: Node,
    binding: str | None,
    *,
    depth: int,
) -> Diagnostic:
    limit = (
        f"{_MAX_INLINE_DEPTH} nested levels"
        if depth > _MAX_INLINE_DEPTH
        else f"{_MAX_INLINE_NODES} expression nodes"
    )
    message = (
        "Expression exceeds the single-file let inline expansion limit of "
        f"{limit} after inlining the let bindings it reads"
        if binding is None
        else "Let binding exceeds the single-file let inline expansion limit of "
        f"{limit} after inlining the let bindings it reads: {binding}"
    )
    span = node.span
    return Diagnostic(
        code="PIE-S2328",
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
    *,
    allow_unaliased_selected_let_outputs: bool = False,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
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
        allow_unaliased_selected_let_outputs=allow_unaliased_selected_let_outputs,
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
            type_expansions=type_expansions,
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
    *,
    allow_unaliased_selected_let_outputs: bool = False,
) -> set[str]:
    assert definition.let_clause is not None

    invalid_names: set[str] = set()
    seen_names: set[str] = set()

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
        if _binding_conflicts_with_projection_output(
            definition,
            binding.name,
            allow_unaliased_selected_let_outputs=allow_unaliased_selected_let_outputs,
        ):
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding conflicts with projection output name",
                )
            )
            invalid_names.add(binding.name)

    return invalid_names


def _binding_conflicts_with_projection_output(
    definition: DerivedRelation,
    binding_name: str,
    *,
    allow_unaliased_selected_let_outputs: bool,
) -> bool:
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name != binding_name:
            continue
        if (
            allow_unaliased_selected_let_outputs
            and item.alias is None
            and isinstance(item.expression, NameExpr)
            and item.expression.name == binding_name
        ):
            continue
        return True
    return False


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
    relation_row_schemas: RelationInputSchemas,
) -> RowSchema:
    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(
        target,
        (
            TableDef,
            QueryDef,
            SetRelationDef,
            ValuesRelationDef,
            TableFunctionRelationDef,
        ),
    ):
        return cast(
            Mapping[
                DerivedRelation
                | SetRelationDef
                | ValuesRelationDef
                | TableFunctionRelationDef,
                RowSchema,
            ],
            relation_row_schemas,
        ).get(target, RowSchema(is_unknown=True))
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
    elif isinstance(expression, ConditionalExpr):
        children.extend(
            (expression.when_true, expression.condition, expression.when_false)
        )
    elif isinstance(expression, MembershipExpr):
        children.append(expression.value)
        children.extend(expression.options)
    elif isinstance(expression, RelationMembershipExpr):
        children.append(expression.value)
    elif isinstance(expression, CastExpr):
        children.append(expression.value)
    elif isinstance(expression, BinaryExpr):
        children.extend((expression.left, expression.right))
    elif isinstance(expression, ComparisonExpr):
        children.extend((expression.left, expression.right))
    elif isinstance(expression, BetweenExpr):
        children.extend((expression.value, expression.lower, expression.upper))
    elif isinstance(expression, IsNullExpr):
        children.append(expression.value)
    elif not isinstance(
        expression,
        (
            LiteralExpr,
            NameExpr,
            DottedNameExpr,
            ParameterRefExpr,
            RelationExistsExpr,
            RelationScalarExpr,
        ),
    ):
        raise AssertionError(f"Unsupported expression: {type(expression).__name__}")

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
