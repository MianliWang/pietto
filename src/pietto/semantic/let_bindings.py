"""Private semantic helpers for relation-local ``let:`` bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto.semantic.relationship_predicates import RelationshipCallFailure

from collections.abc import Mapping, Sequence
from typing import cast

from pietto.ast_nodes import (
    AnyExpr,
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
    JoinClause,
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
    WindowExpr,
    TableFunctionRelationDef,
    ValuesRelationDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto.semantic.expressions import (
    LetValues,
    _FailedRelationshipTypes,
    infer_row_expression,
)
from pietto.semantic.model import (
    LetScopeSemanticInfo,
    ResolvedType,
    RowSchema,
    ValueType,
)
from pietto.semantic.row_lookup import has_bare_field

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
    joined_inputs: Mapping[DerivedRelation, RowSchema] | None = None,
    reserved_let_names: Mapping[DerivedRelation, frozenset[str]] | None = None,
    normalized_bindings: Mapping[LetBinding, Expression] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> tuple[
    dict[DerivedRelation, LetScopeSemanticInfo],
    dict[Expression, ValueType],
    list[Diagnostic],
]:
    """Validate relation-local let clauses and return private value scopes.

    A relation in ``joined_inputs`` reads that row instead of its FROM input,
    and a let binding cannot take a name ``reserved_let_names`` gives it.
    """

    scopes: dict[DerivedRelation, LetScopeSemanticInfo] = {}
    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        if definition.let_clause is None:
            continue
        input_schema = (joined_inputs or {}).get(definition)
        if input_schema is None:
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
            reserved_names=(reserved_let_names or {}).get(definition, frozenset()),
            normalized_bindings=normalized_bindings,
            failed_relationship_calls=failed_relationship_calls,
        )
        scopes[definition] = scope
        value_types.update(relation_values)
        diagnostics.extend(relation_diagnostics)

    return scopes, value_types, diagnostics


def admitted_relation_let_expressions(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    reserved_names: frozenset[str] = frozenset(),
) -> dict[str, Expression]:
    """Return relation-local let expressions admitted into the private scope."""

    if definition.let_clause is None:
        return {}
    invalid_names = _invalid_binding_names(
        definition, input_schema, [], reserved_names=reserved_names
    )
    expressions: dict[str, Expression] = {}
    seen_names: set[str] = set()
    for binding in definition.let_clause.bindings:
        if binding.name not in invalid_names and binding.name not in seen_names:
            expressions[binding.name] = binding.expression
        seen_names.add(binding.name)
    return expressions


def join_reserved_let_names(
    definition: DerivedRelation, *, generated_joins: tuple[JoinClause, ...] = ()
) -> frozenset[str]:
    """The names a single-file JOIN relation's let bindings cannot take.

    Every binding, SEMI and ANTI ones included, and every binding's relation.
    """

    names = {
        definition.from_clause.source_name,
        (definition.from_clause.binding_name or definition.from_clause.source_name),
    }
    generated = {id(clause) for clause in generated_joins}
    for clause in definition.join_clauses:
        if id(clause) not in generated:
            names.update((clause.target_binding_name, clause.target_relation_name))
    return frozenset(names)


# Single-file IR inlines every `let:` binding at each read, so the size and
# nesting of an expression after inlining bound the IR and SQL it produces.
# Levels are weighted by the recursion that lowering and SQL rendering spend
# per level; an expression written inline is bounded by PIE-S2006 instead.
_MAX_INLINE_NODES = 100_000
_MAX_INLINE_LEVELS = 768


def let_expansion_diagnostics(
    definition: DerivedRelation,
    admitted: Mapping[str, object],
    *,
    extra_expressions: tuple[Expression, ...] = (),
) -> list[Diagnostic]:
    """Refuse relation expressions whose single-file let inlining is too big.

    Emission inlines a binding only where a relation expression reads it, so
    only those reads are measured (PIE-S2328, at the reading expression); a
    binding that nothing reads is never inlined and never refused. Each let
    substitution, a plain alias included, adds one nested level.
    """

    if definition.let_clause is None:
        return []
    # Per binding read: (inlined node count, inlined levels including the
    # substitution, the first binding on its read path past a limit, if any).
    measured: dict[str, tuple[int, int, str | None]] = {}

    def measure(expression: Expression) -> tuple[int, int, str | None, bool]:
        """Return inlined node count, levels, first culprit, and any let read."""

        if type(expression) is NameExpr and expression.name in measured:
            return (*measured[expression.name], True)
        size, levels, culprit, inlined = 1, 0, None, False
        for operand in _operands(expression):
            operand_size, operand_levels, operand_culprit, operand_inlined = measure(
                operand
            )
            size += operand_size
            levels = max(levels, operand_levels)
            culprit = culprit or operand_culprit
            inlined = inlined or operand_inlined
        return size, levels + _level_weight(expression), culprit, inlined

    for binding in definition.let_clause.bindings:
        if binding.name in admitted and binding.name not in measured:
            size, levels, culprit, _inlined = measure(binding.expression)
            levels += 1
            if culprit is None and _exceeds(size, levels):
                culprit = binding.name
            measured[binding.name] = (size, levels, culprit)
    diagnostics: list[Diagnostic] = []
    for expression in (*_relation_expressions(definition), *extra_expressions):
        size, levels, culprit, inlined = measure(expression)
        if inlined and _exceeds(size, levels):
            diagnostics.append(
                _inline_expansion_diagnostic(expression, culprit, levels=levels)
            )
    return diagnostics


def _level_weight(expression: Expression) -> int:
    """Return the nested levels one expression node counts for."""

    if isinstance(expression, CallExpr):
        return 3
    if isinstance(expression, (ConditionalExpr, MembershipExpr)):
        return 2
    return 1


def _exceeds(size: int, levels: int) -> bool:
    return size > _MAX_INLINE_NODES or levels > _MAX_INLINE_LEVELS


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
            if definition.qualify_clause is None
            else (definition.qualify_clause.expression,)
        ),
        *(
            ()
            if definition.order_by_clause is None
            else tuple(item.expression for item in definition.order_by_clause.items)
        ),
    )


def _operands(expression: Expression) -> tuple[Expression, ...]:
    """Return the operands that let inline expansion descends into."""

    if isinstance(expression, AnyExpr):
        return ()
    if isinstance(expression, CallExpr):
        return (
            *expression.arguments,
            *(item.expression for item in expression.aggregate_order_by),
        )
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
    if isinstance(expression, WindowExpr):
        frame = expression.spec.frame
        offsets = (
            ()
            if frame is None
            else tuple(
                bound.offset
                for bound in (frame.start, frame.end)
                if bound is not None and bound.offset is not None
            )
        )
        return (
            *expression.call.arguments,
            *expression.spec.partition_by,
            *(item.expression for item in expression.spec.order_by),
            *offsets,
        )
    return ()


def _inline_expansion_diagnostic(
    node: Node,
    binding: str | None,
    *,
    levels: int,
) -> Diagnostic:
    limit = (
        f"{_MAX_INLINE_LEVELS} nested levels"
        if levels > _MAX_INLINE_LEVELS
        else f"{_MAX_INLINE_NODES} expression nodes"
    )
    message = (
        "Expression exceeds the single-file let inline expansion limit of "
        f"{limit} after inlining the let bindings it reads"
        + ("" if binding is None else f" (first at let binding {binding})")
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
    reserved_names: frozenset[str] = frozenset(),
    normalized_bindings: Mapping[LetBinding, Expression] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> tuple[LetScopeSemanticInfo, dict[Expression, ValueType], list[Diagnostic]]:
    assert definition.let_clause is not None

    diagnostics: list[Diagnostic] = []
    value_types: dict[Expression, ValueType] = (
        _FailedRelationshipTypes(failed_relationship_calls)
        if failed_relationship_calls
        else {}
    )
    scope_values: dict[str, ValueType] = {}
    # Earlier admitted bindings, which `let_value` follows as emission inlines.
    scope_expressions = LetValues()
    seen_names: set[str] = set()
    all_names = tuple(binding.name for binding in definition.let_clause.bindings)
    all_name_set = set(all_names)
    invalid_binding_names = _invalid_binding_names(
        definition,
        input_schema,
        diagnostics,
        allow_unaliased_selected_let_outputs=allow_unaliased_selected_let_outputs,
        reserved_names=reserved_names,
    )

    ignored_dependency_ids = frozenset(
        id(argument)
        for failure in failed_relationship_calls
        for argument in failure.expression.arguments
        if isinstance(argument, NameExpr)
    )
    for binding in definition.let_clause.bindings:
        reported = len(diagnostics)
        if contains_semantic_aggregate(binding.expression):
            diagnostics.append(
                invalid_context_diagnostic(binding.expression, context="let binding")
            )
        suppressed_unknown_names = _dependency_diagnostics(
            binding,
            all_name_set=all_name_set,
            prior_names=set(scope_values),
            diagnostics=diagnostics,
            ignored_expression_ids=ignored_dependency_ids,
        )
        expression = (normalized_bindings or {}).get(binding, binding.expression)
        value_type = infer_row_expression(
            expression,
            input_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=(
                definition.from_clause.binding_name
                or definition.from_clause.source_name
            ),
            bare_value_types=scope_values,
            bare_value_expressions=scope_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
        )
        value_types[binding.expression] = value_type
        if binding.name not in invalid_binding_names and binding.name not in seen_names:
            scope_values[binding.name] = value_type
            scope_expressions[binding.name] = expression
            if any(item.severity is Severity.ERROR for item in diagnostics[reported:]):
                scope_expressions.erroneous.add(binding.name)
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
    reserved_names: frozenset[str] = frozenset(),
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

        if has_bare_field(input_schema, binding.name):
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding cannot shadow input field",
                )
            )
            invalid_names.add(binding.name)
            continue
        if (
            binding.name
            == (
                definition.from_clause.binding_name
                or definition.from_clause.source_name
            )
            or binding.name in reserved_names
        ):
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
            # A single file cannot select a binding by its own name in a
            # relation with GROUP BY yet; the message says what to write.
            from pietto.semantic.group_by import grouped_let_select_hint

            hint = (
                grouped_let_select_hint(
                    definition,
                    binding.name,
                    input_schema,
                    {
                        item.name: item.expression
                        for item in reversed(definition.let_clause.bindings)
                    },
                )
                if all(
                    _selects_binding(item, binding.name)
                    for item in definition.select_items
                    if _projection_output_name(item) == binding.name
                )
                else ""
            )
            diagnostics.append(
                _invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding conflicts with projection output name",
                    hint=hint,
                )
            )
            invalid_names.add(binding.name)

    return invalid_names


def _selects_binding(item: SelectItem, binding_name: str) -> bool:
    """Whether ``item`` selects the binding by its own name, which outputs
    its value."""

    return (
        item.alias is None
        and isinstance(item.expression, NameExpr)
        and item.expression.name == binding_name
    )


def _binding_conflicts_with_projection_output(
    definition: DerivedRelation,
    binding_name: str,
    *,
    allow_unaliased_selected_let_outputs: bool,
) -> bool:
    """Whether an output of another value takes the binding's name.

    Selecting the binding by its own name outputs its value; a single file
    selects a binding so only in a relation without GROUP BY.
    """

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name != binding_name:
            continue
        if (
            allow_unaliased_selected_let_outputs or definition.group_by_clause is None
        ) and _selects_binding(item, binding_name):
            continue
        return True
    return False


def _dependency_diagnostics(
    binding: LetBinding,
    *,
    all_name_set: set[str],
    prior_names: set[str],
    diagnostics: list[Diagnostic],
    ignored_expression_ids: frozenset[int] = frozenset(),
) -> set[str]:
    suppressed_unknown_names: set[str] = set()
    reported_names: set[str] = set()
    for expression in _walk_expressions(binding.expression):
        if id(expression) in ignored_expression_ids or not isinstance(
            expression, NameExpr
        ):
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
        children.extend(item.expression for item in expression.aggregate_order_by)
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
            AnyExpr,
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
    hint: str = "",
) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code="PIE-S2329",
        severity=Severity.ERROR,
        message=f"{reason}: {name}" + (f"; {hint}" if hint else ""),
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
