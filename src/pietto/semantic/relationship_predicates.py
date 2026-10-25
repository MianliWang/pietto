"""Shape-typed row predicates, bound before ordinary scalar typing/lowering.

Inputs are occurrences supplied by the relation owner. Shape names are lookup
material only: a parameter and an actual row must share the same declaration.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import (
    EffectiveNullability,
    RelationshipArgumentInfo,
    RelationshipCallInfo,
    RelationshipTemplateInfo,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

__all__ = ()

# The adapter returns existing occurrence, relation and declared shape identities.
RowCandidate = tuple[
    ast.Node, ast.SourceDef | ast.TableDef | ast.QueryDef, ast.ShapeDef
]
RowResolver = Callable[[ast.NameExpr], Sequence[RowCandidate]]


def check_relationship_templates(
    script: ast.Script,
    *,
    shape_candidates: Mapping[str, Sequence[ast.Node]],
    type_resolutions: Mapping[ast.TypeExpr, ResolvedType],
    type_expansions: Mapping[ast.TypeExpr, ResolvedType],
    type_nullability: Mapping[ast.TypeExpr, EffectiveNullability],
) -> tuple[tuple[RelationshipTemplateInfo, ...], tuple[Diagnostic, ...]]:
    """Check each declaration against its resolved shapes, without query rows."""

    from pietto.semantic.inline_functions import _tree_nodes

    checked: list[RelationshipTemplateInfo] = []
    diagnostics: list[Diagnostic] = []
    buckets: dict[str, list[ast.RelationshipTemplate]] = {}
    for declaration in script.relationship_templates:
        buckets.setdefault(declaration.name, []).append(declaration)
    for declaration in script.relationship_templates:
        start = len(diagnostics)
        if len(buckets[declaration.name]) > 1:
            diagnostics.append(
                _diagnostic(
                    declaration,
                    f"Ambiguous relationship predicate name: {declaration.name}",
                )
            )
        shapes: list[ast.ShapeDef] = []
        names: set[str] = set()
        parameters: dict[str, tuple[ast.ShapeDef, RowSchema]] = {}
        if not declaration.parameters:
            diagnostics.append(
                _diagnostic(
                    declaration, "A relationship predicate needs row parameters"
                )
            )
        for parameter in declaration.parameters:
            if parameter.name in names:
                diagnostics.append(
                    _diagnostic(
                        parameter, f"Duplicate relationship parameter: {parameter.name}"
                    )
                )
            names.add(parameter.name)
            candidates = shape_candidates.get(parameter.shape_name, ())
            if len(candidates) != 1 or not isinstance(candidates[0], ast.ShapeDef):
                diagnostics.append(
                    _diagnostic(
                        parameter,
                        f"{'Ambiguous' if candidates else 'Unknown'} relationship parameter shape: "
                        f"{parameter.shape_name}",
                    )
                )
                continue
            shape = cast(ast.ShapeDef, candidates[0])
            shapes.append(shape)
            row = RowSchema(
                fields={
                    field.name: RowField(
                        name=field.name,
                        resolved_type=type_expansions.get(
                            field.type_expr,
                            type_resolutions.get(
                                field.type_expr,
                                ResolvedType(
                                    name=field.type_expr.name, kind=TypeKind.UNKNOWN
                                ),
                            ),
                        ),
                        nullability=type_nullability.get(
                            field.type_expr, EffectiveNullability.UNKNOWN
                        ),
                        definition=field,
                    )
                    for field in shape.fields
                }
            )
            parameters[parameter.name] = (shape, row)
        if len(diagnostics) != start:
            continue
        value_types: dict[ast.Expression, ValueType] = {}
        if contains_semantic_aggregate(declaration.body):
            diagnostics.append(
                _diagnostic(
                    declaration.body, "A relationship predicate cannot aggregate rows"
                )
            )
        for node in _tree_nodes(declaration.body):
            if type(node) is ast.DottedNameExpr:
                role = parameters.get(node.parts[0])
                field = (
                    role[1].fields.get(node.parts[1])
                    if role is not None and len(node.parts) == 2
                    else None
                )
                if field is None:
                    diagnostics.append(
                        _diagnostic(
                            node,
                            f"Unknown relationship parameter field: {'.'.join(node.parts)}",
                        )
                    )
                else:
                    value_types[node] = ValueType(
                        resolved_type=field.resolved_type, nullability=field.nullability
                    )
            elif type(node) is ast.NameExpr:
                diagnostics.append(
                    _diagnostic(
                        node,
                        f"A relationship body requires a parameter field: {node.name}",
                    )
                )
            elif type(node) in (
                ast.RelationExistsExpr,
                ast.RelationScalarExpr,
                ast.RelationMembershipExpr,
                ast.CapturedFieldExpr,
                ast.ParameterRefExpr,
                ast.WindowExpr,
                ast.AnyExpr,
            ):
                assert isinstance(node, ast.Expression)
                diagnostics.append(
                    _diagnostic(
                        node, "A relationship predicate reads only its supplied rows"
                    )
                )
        if len(diagnostics) != start:
            continue
        result = infer_row_expression(
            declaration.body,
            RowSchema(),
            value_types,
            diagnostics,
            report_unknown_name=True,
            type_expansions=type_expansions,
        )
        if len(diagnostics) == start and (
            result.kind is not ValueTypeKind.KNOWN
            or result.resolved_type.kind is not TypeKind.BUILTIN
            or result.resolved_type.name != "Bool"
        ):
            diagnostics.append(
                _diagnostic(
                    declaration.body,
                    "A relationship predicate body must have type Bool",
                )
            )
        if len(diagnostics) == start:
            checked.append(
                RelationshipTemplateInfo(
                    declaration=declaration, parameter_shapes=tuple(shapes)
                )
            )
    return tuple(checked), tuple(diagnostics)


@dataclass(frozen=True, slots=True, eq=False)
class RelationshipCallFailure:
    call: ast.CallExpr
    expression: ast.CallExpr
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        if (
            type(self.call) is not ast.CallExpr
            or type(self.expression) is not ast.CallExpr
            or type(self.diagnostics) is not tuple
            or any(type(item) is not Diagnostic for item in self.diagnostics)
            or not any(item.severity is Severity.ERROR for item in self.diagnostics)
        ):
            raise ValueError(
                "Failed relationship calls require exact calls and errors."
            )


def bind_relationship_expression(
    expression: ast.Expression,
    *,
    templates: Sequence[RelationshipTemplateInfo],
    declared_names: frozenset[str],
    resolve_row: RowResolver,
    owner: ast.TableDef | ast.QueryDef,
    context: ast.Node,
    scalar_names: frozenset[str] = frozenset(),
    scalar_argument_names: frozenset[str] = frozenset(),
    scalar_argument_available: Callable[[ast.NameExpr], bool] | None = None,
    occurrence_observer: Callable[[object, object], None] | None = None,
    first_ordinal: int = 0,
) -> tuple[
    ast.Expression,
    tuple[RelationshipCallInfo, ...],
    tuple[Diagnostic, ...],
    tuple[RelationshipCallFailure, ...],
]:
    """Bind every predicate call; preserve the whole expression's value syntax.

    The caller supplies only inputs readable at this exact use. No relation is
    introduced by a predicate argument and no shape supplies row nullability.
    """

    from pietto.semantic.inline_functions import _rebuild

    buckets: dict[str, list[RelationshipTemplateInfo]] = {}
    for template in templates:
        buckets.setdefault(template.declaration.name, []).append(template)
    diagnostics: list[Diagnostic] = []
    uses: list[RelationshipCallInfo] = []
    failures: list[RelationshipCallFailure] = []
    occurrences = itertools.count(1)
    mandatory_calls: set[int] = set()
    pending = (
        [expression] if type(context) in (ast.JoinOnClause, ast.WhereClause) else []
    )
    while pending:
        node = pending.pop()
        if type(node) is ast.BinaryExpr and node.operator == "and":
            pending.extend((node.right, node.left))
        elif type(node) is ast.CallExpr:
            mandatory_calls.add(id(node))

    def bind(original: object, rebuilt: object) -> object:
        rebuilt = _scalar_contracts(original, rebuilt)
        if (
            type(rebuilt) is not ast.CallExpr
            or type(rebuilt.callee) is not ast.NameExpr
        ):
            return rebuilt
        name = rebuilt.callee.name

        def failed(start: int) -> ast.CallExpr:
            failures.append(
                RelationshipCallFailure(
                    cast(ast.CallExpr, original), rebuilt, tuple(diagnostics[start:])
                )
            )
            return rebuilt

        if name not in declared_names:
            return rebuilt
        candidates = buckets.get(name, ())
        rows = [
            tuple(resolve_row(argument)) if type(argument) is ast.NameExpr else ()
            for argument in rebuilt.arguments
        ]
        if name in scalar_names:
            if not any(rows):
                return rebuilt
            if all(
                type(argument) is not ast.NameExpr
                or (
                    scalar_argument_available(argument)
                    if scalar_argument_available is not None
                    else argument.name in scalar_argument_names
                )
                for argument in rebuilt.arguments
            ):
                start = len(diagnostics)
                diagnostics.append(
                    _diagnostic(
                        rebuilt, f"Ambiguous scalar or relationship call: {name}"
                    )
                )
                return failed(start)
        if len(candidates) != 1:
            start = len(diagnostics)
            diagnostics.append(
                _diagnostic(
                    rebuilt,
                    f"Relationship predicate {name} has no unambiguous checked declaration",
                )
            )
            return failed(start)
        template = candidates[0]
        parameters = template.declaration.parameters
        if len(parameters) != len(rebuilt.arguments):
            start = len(diagnostics)
            diagnostics.append(
                _diagnostic(
                    rebuilt,
                    f"Invalid arguments for relationship {name}: expected {len(parameters)}, "
                    f"got {len(rebuilt.arguments)}",
                )
            )
            return failed(start)
        arguments: list[RelationshipArgumentInfo] = []
        start = len(diagnostics)
        for parameter, shape, argument, actuals in zip(
            parameters, template.parameter_shapes, rebuilt.arguments, rows, strict=True
        ):
            if len(actuals) != 1:
                diagnostics.append(
                    _diagnostic(
                        argument,
                        f"{'Ambiguous' if actuals else 'Unavailable'} row argument for "
                        f"relationship {name} parameter {parameter.name}",
                    )
                )
                continue
            occurrence, relation, actual_shape = actuals[0]
            if actual_shape is not shape:
                diagnostics.append(
                    _diagnostic(
                        argument,
                        f"Relationship {name} parameter {parameter.name} requires declared "
                        f"shape {shape.name}; the actual row has a different shape identity",
                    )
                )
                continue
            arguments.append(
                RelationshipArgumentInfo(
                    parameter, argument, occurrence, relation, actual_shape
                )
            )
        if len(diagnostics) != start:
            return failed(start)
        aliases = {
            binding.parameter.name: cast(ast.NameExpr, binding.argument).name
            for binding in arguments
        }

        def substitute(before: object, after: object) -> object:
            if not isinstance(after, ast.Node):
                return after
            # Every copied body node is an explicit located occurrence.
            span = replace(rebuilt.span, occurrence=next(occurrences))
            if type(after) is ast.DottedNameExpr and after.parts[0] in aliases:
                result = replace(
                    after, parts=(aliases[after.parts[0]], *after.parts[1:]), span=span
                )
            else:
                result = replace(after, span=span)
            return _scalar_contracts(before, result)

        expanded = cast(
            ast.Expression,
            _rebuild(
                template.declaration.body,
                substitute,
                occurrence_observer=occurrence_observer,
            ),
        )
        expanded = cast(
            ast.Expression,
            _scalar_contracts(expanded, replace(expanded, span=rebuilt.span)),
        )
        for slot in ast.inlined_arguments(cast(ast.Expression, original)):
            expanded = ast.with_inlined_argument(expanded, slot)
        uses.append(
            RelationshipCallInfo(
                template=template,
                call=cast(ast.CallExpr, original),
                owner=owner,
                context=context,
                ordinal=first_ordinal + len(uses),
                arguments=tuple(arguments),
                expanded=expanded,
                mandatory_equalities=(
                    mandatory_field_equalities(expanded)
                    if id(original) in mandatory_calls
                    else ()
                ),
            )
        )
        return expanded

    rewritten = cast(
        ast.Expression,
        _rebuild(expression, bind, occurrence_observer=occurrence_observer),
    )
    return rewritten, tuple(uses), tuple(diagnostics), tuple(failures)


def _scalar_contracts(before: object, after: object) -> object:
    """AST replacement must retain existing scalar def argument obligations."""

    if (
        before is not after
        and isinstance(before, ast.Expression)
        and isinstance(after, ast.Expression)
    ):
        for slot in ast.inlined_arguments(before):
            after = ast.with_inlined_argument(after, slot)
    return after


def mandatory_field_equalities(
    expression: ast.Expression,
) -> tuple[ast.ComparisonExpr, ...]:
    """Positive top-level equality conjuncts only; OR/NOT add no key proof."""

    found: list[ast.ComparisonExpr] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        if type(node) is ast.BinaryExpr and node.operator == "and":
            pending.extend((node.right, node.left))
        elif (
            type(node) is ast.ComparisonExpr
            and node.operator == "=="
            and type(node.left) is ast.DottedNameExpr
            and type(node.right) is ast.DottedNameExpr
            and len(node.left.parts) == len(node.right.parts) == 2
        ):
            found.append(node)
    return tuple(found)


def deferred_row_calls(script: ast.Script) -> frozenset[int]:
    """Calls a scalar def must leave for exact row binding, including bad rows.

    A shared spelling is not a declaration collision: scalar arguments still
    call the scalar def. Bare input names require the row owner's decision.
    """

    if not script.relationship_templates:
        return frozenset()
    names = {template.name for template in script.relationship_templates}
    deferred: set[int] = set()
    for definition in script.definitions:
        if not isinstance(definition, (ast.TableDef, ast.QueryDef)):
            continue
        inputs = (
            (
                definition.from_clause.binding_name
                or definition.from_clause.source_name,
                definition.from_clause,
                True,
            ),
            *(
                (
                    join.target_binding_name,
                    join,
                    join.kind
                    not in (ast.AuthoredJoinKind.SEMI, ast.AuthoredJoinKind.ANTI),
                )
                for join in definition.join_clauses
            ),
        )
        scoped: dict[int, tuple[ast.CallExpr, frozenset[str]]] = {}

        def collect(root: ast.Node, visible: frozenset[str]) -> None:
            from pietto.semantic.inline_functions import _children

            pending: list[tuple[object, frozenset[str]]] = [(root, visible)]
            while pending:
                node, readable = pending.pop()
                if isinstance(node, ast.AnyExpr):
                    pending.append((node.predicate, readable | {node.binding_name}))
                    continue
                if (
                    type(node) is ast.CallExpr
                    and type(node.callee) is ast.NameExpr
                    and node.callee.name in names
                ):
                    scoped[id(node)] = (node, readable)
                pending.extend(
                    (child, readable) for child in reversed(_children(node) or ())
                )

        # Non-row contexts, including ORDER BY scalar calls, remain scalar.
        collect(definition, frozenset())
        tail = frozenset(name for name, _, visible in inputs if visible)
        for context in (
            definition.where_clause,
            definition.qualify_clause,
            definition.satisfying_clause,
            *definition.select_items,
        ):
            if context is not None:
                collect(context, tail)
        for position, join in enumerate(definition.join_clauses, 1):
            if join.on_clause is not None:
                collect(
                    join.on_clause,
                    frozenset(
                        name
                        for ordinal, (name, _, visible) in enumerate(inputs)
                        if ordinal <= position and (visible or ordinal == position)
                    ),
                )
        if definition.let_clause is not None:
            for binding in definition.let_clause.bindings:
                collect(
                    binding,
                    frozenset(
                        name
                        for name, occurrence, visible in inputs
                        if visible
                        and (occurrence.span.line, occurrence.span.column)
                        <= (binding.span.line, binding.span.column)
                    ),
                )
        deferred.update(
            identity
            for identity, (call, visible) in scoped.items()
            if any(
                type(argument) is ast.NameExpr and argument.name in visible
                for argument in call.arguments
            )
        )
    return frozenset(deferred)


def _diagnostic(node: ast.Node, message: str) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code="PIE-S2604",
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
