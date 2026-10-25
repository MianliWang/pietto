"""Check scalar ANY bodies against exact nested and outer input occurrences.

The inventory owns provenance; this module owns checked field/capture facts for
single-file expression lowering. It reuses the ordinary row typing kernel.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto.semantic.relationship_predicates import RelationshipCallFailure

from pietto import ast_nodes as ast
from pietto._flat_relational_admission import availability_diagnostic
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import child_expressions, contains_semantic_aggregate
from pietto.semantic.existence_generators import AnyUseInfo, AnyValueInfo
from pietto.semantic.expressions import _UNKNOWN_VALUE_TYPE, infer_row_expression
from pietto.semantic.joins import JoinStructure, _field_value_type, join_rows
from pietto.semantic.let_bindings import (
    _invalid_let_dependency_diagnostic,
    let_expansion_diagnostics,
)
from pietto.semantic.model import (
    AnyFieldReadInfo,
    AnyValueSemanticInfo,
    EffectiveNullability,
    LetScopeSemanticInfo,
    ResolvedType,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.predicate_checks import _check_bool_expression

Relation = ast.SourceDef | ast.TableDef | ast.QueryDef
Owner = ast.TableDef | ast.QueryDef
# A scope contains existing row schemas, each attached to its actual occurrence.
Input = tuple[ast.FromClause | ast.JoinClause | ast.AnyExpr, Relation, str, RowSchema]
_BOOL = ValueType(
    resolved_type=ResolvedType(name="Bool", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)


def resolve_any_inputs(
    uses: Sequence[AnyValueInfo],
    relation_symbols: Mapping[str, ast.Definition],
    existence_generators: Sequence[AnyUseInfo] = (),
) -> tuple[dict[ast.AnyExpr, Relation], list[Diagnostic]]:
    """Resolve all iterators before cycles, including those in unused LETs.

    A WHERE ANY lowered to a hidden SEMI/ANTI input still binds its row name
    over that input's ON condition, as it binds it over its body in place.
    """
    resolutions: dict[ast.AnyExpr, Relation] = {}
    diagnostics: list[Diagnostic] = []
    by_identity = {id(use.expression): use for use in uses}
    lowered = {id(use.clause.on_clause): use.expression for use in existence_generators}
    for use in uses:
        expression = use.expression
        # Binders shadow the name as written, before a let alias is replaced.
        name = use.authored_expression.relation_name
        parent = use.context
        shadowed = False
        while isinstance(parent, ast.AnyExpr):
            shadowed |= parent.binding_name == name
            parent_use = by_identity.get(id(parent))
            if parent_use is None:
                raise AssertionError("ANY parent has no occurrence inventory")
            parent = parent_use.context
        binder = lowered.get(id(parent))
        shadowed |= binder is not None and binder.binding_name == name
        target = None if shadowed else relation_symbols.get(expression.relation_name)
        if isinstance(target, (ast.SourceDef, ast.TableDef, ast.QueryDef)):
            resolutions[expression] = target
        else:
            diagnostics.append(
                _diagnostic(
                    expression.relation_span,
                    "PIE-S2301",
                    f"Unknown or unavailable ANY relation: {expression.relation_name}",
                )
            )
    return resolutions, diagnostics


def check_any_values(
    uses: Sequence[AnyValueInfo],
    *,
    resolutions: Mapping[ast.AnyExpr, Relation],
    from_resolutions: Mapping[ast.FromClause, Relation],
    structures: Mapping[Owner, JoinStructure],
    source_row_schemas: Mapping[ast.SourceDef, RowSchema],
    relation_row_schemas: Mapping[Owner, RowSchema],
    let_scopes: Mapping[Owner, LetScopeSemanticInfo],
    expression_value_types: dict[ast.Expression, ValueType],
    type_expansions: Mapping[ast.TypeExpr, ResolvedType],
    cyclic_relations: set[Owner] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> tuple[dict[ast.AnyExpr, AnyValueSemanticInfo], list[Diagnostic]]:
    """Validate every occurrence; only completely checked bodies acquire facts."""
    facts: dict[ast.AnyExpr, AnyValueSemanticInfo] = {}
    diagnostics: list[Diagnostic] = []
    by_identity = {id(use.expression): use for use in uses}
    environments: dict[int, tuple[Input, ...]] = {}
    processed: set[int] = set()
    processing: set[int] = set()
    cycles = cyclic_relations or set()
    failed_call_ids = {id(failure.expression) for failure in failed_relationship_calls}
    ignored_row_arguments = {
        id(argument)
        for failure in failed_relationship_calls
        for argument in failure.expression.arguments
        if isinstance(argument, ast.NameExpr)
    }

    def schema_of(relation: Relation) -> RowSchema:
        if isinstance(relation, ast.SourceDef):
            return source_row_schemas.get(relation, RowSchema(is_unknown=True))
        return relation_row_schemas.get(relation, RowSchema(is_unknown=True))

    def outer_inputs(use: AnyValueInfo) -> tuple[Input, ...]:
        if isinstance(use.context, ast.AnyExpr):
            parent = by_identity[id(use.context)]
            check(parent)
            return environments.get(id(parent.expression), ())
        owner = use.owner
        structure = structures.get(owner)
        if owner.join_clauses:
            if structure is None:
                return ()
            rows = join_rows(structure, schema_of)
            if rows is None:
                return ()
            on = isinstance(use.context, ast.JoinOnClause)
            prefix = use.join_prefix_count
            row = rows.on[prefix - 1] if on else rows.tail
            inputs = []
            for item in structure.inputs:
                if on:
                    visible = item.ordinal == prefix or (
                        item.visible and item.ordinal < prefix
                    )
                else:
                    visible = item.visible
                if not visible:
                    continue
                mark = item.binding + "."
                fields = {
                    key[len(mark) :]: value
                    for key, value in row.fields.items()
                    if key.startswith(mark)
                }
                inputs.append(
                    (
                        owner.from_clause if item.clause is None else item.clause,
                        item.relation,
                        item.binding,
                        RowSchema(fields=fields),
                    )
                )
            return tuple(inputs)
        source = from_resolutions.get(owner.from_clause)
        if source is None:
            return ()
        return (
            (
                owner.from_clause,
                source,
                owner.from_clause.binding_name or owner.from_clause.source_name,
                schema_of(source),
            ),
        )

    def root_context(use: AnyValueInfo) -> ast.Node:
        while isinstance(use.context, ast.AnyExpr):
            use = by_identity[id(use.context)]
        return use.context

    def check(use: AnyValueInfo) -> None:
        expression = use.expression
        key = id(expression)
        if key in processed:
            return
        if key in processing:
            # The parent constructs its environment before checking a nested body.
            return
        processing.add(key)
        target = resolutions.get(expression)
        outer = outer_inputs(use)
        local = RowSchema(is_unknown=True) if target is None else schema_of(target)
        visible = tuple(item for item in outer if item[2] != expression.binding_name)
        if target is not None:
            visible += ((expression, target, expression.binding_name, local),)
        environments[key] = visible
        start = len(diagnostics)
        failed = target is None or use.owner in cycles or target in cycles
        if target is not None and local.is_unknown and target not in cycles:
            diagnostics.append(
                availability_diagnostic(
                    expression.relation_span,
                    f"ANY over {expression.relation_name} requires known input fields.",
                )
            )
            failed = True
        if use.owner.join_clauses and use.owner not in structures:
            failed = True
        context = root_context(use)
        allow_lets = not isinstance(context, ast.JoinOnClause)
        scope = let_scopes.get(use.owner) if allow_lets else None
        allowed_bindings = () if scope is None else scope.bindings
        blocked_lets: set[str] = set()
        if scope is not None and isinstance(context, ast.LetBinding):
            positions = [
                index
                for index, binding in enumerate(scope.bindings)
                if binding is context
            ]
            if len(positions) != 1:
                raise AssertionError("ANY LET context has no exact binding occurrence")
            position = positions[0]
            blocked_lets = {binding.name for binding in scope.bindings[position:]}
            allowed_bindings = scope.bindings[:position]
        allowed_names = {binding.name for binding in allowed_bindings}
        let_types = (
            {}
            if scope is None
            else {
                name: value_type
                for name, value_type in scope.value_types.items()
                if name in allowed_names
            }
        )
        lets = (
            {}
            if scope is None
            else {
                binding.name: binding.expression
                for binding in allowed_bindings
                if binding.name in let_types
            }
        )
        reads: dict[ast.Expression, AnyFieldReadInfo] = {}
        captures: list[AnyFieldReadInfo] = []
        nested: list[ast.AnyExpr] = []
        types: dict[ast.Expression, ValueType] = {}
        # LET expressions retain their declaration's row environment, independent
        # of any same-spelled generator binder at a use site.
        tail_use = use
        while isinstance(tail_use.context, ast.AnyExpr):
            tail_use = by_identity[id(tail_use.context)]
        tail_environment = outer_inputs(tail_use)

        def read_tree(
            node: ast.Expression,
            environment: tuple[Input, ...],
            let_stack: frozenset[str] = frozenset(),
        ) -> None:
            nonlocal failed
            if id(node) in failed_call_ids:
                failed = True
            if isinstance(node, ast.AnyExpr):
                nested.append(node)
                child = by_identity.get(id(node))
                if child is None:
                    raise AssertionError("Nested ANY has no exact occurrence inventory")
                check(child)
                types[node] = _BOOL
                child_fact = facts.get(node)
                if child_fact is None:
                    failed = True
                else:
                    captures.extend(
                        item
                        for item in child_fact.captures
                        if item.occurrence is not expression
                    )
                return
            if isinstance(node, ast.WindowExpr):
                diagnostics.append(
                    availability_diagnostic(
                        node.span,
                        "Window expressions are unavailable in ANY predicates.",
                    )
                )
                failed = True
                return
            if isinstance(node, (ast.NameExpr, ast.DottedNameExpr)):
                if id(node) in ignored_row_arguments:
                    return
                if (
                    isinstance(node, ast.NameExpr)
                    and node.name in blocked_lets
                    and not any(
                        isinstance(item[0], ast.AnyExpr) and item[2] == node.name
                        for item in environment
                    )
                ):
                    assert isinstance(context, ast.LetBinding)
                    diagnostics.append(
                        _invalid_let_dependency_diagnostic(
                            node,
                            node.name,
                            reason="Let binding cannot reference itself"
                            if node.name == context.name
                            else "Let binding cannot reference a later binding",
                        )
                    )
                    types[node] = _UNKNOWN_VALUE_TYPE
                    failed = True
                    return
                if isinstance(node, ast.NameExpr) and node.name in lets:
                    # A local row binder shadows an outer scalar name.
                    if not any(
                        isinstance(item[0], ast.AnyExpr) and item[2] == node.name
                        for item in environment
                    ):
                        types[node] = let_types[node.name]
                        if node.name in let_stack:
                            failed = True
                            return
                        read_tree(
                            lets[node.name], tail_environment, let_stack | {node.name}
                        )
                        return
                if isinstance(node, ast.NameExpr):
                    name = node.name
                    candidates = [
                        item for item in environment if name in item[3].fields
                    ]
                    if any(
                        item[2] == name and isinstance(item[0], ast.AnyExpr)
                        for item in environment
                    ):
                        candidates = []
                else:
                    name = node.parts[-1]
                    candidates = [
                        item
                        for item in environment
                        if len(node.parts) == 2
                        and item[2] == node.parts[0]
                        and name in item[3].fields
                    ]
                if len(candidates) != 1:
                    types[node] = _UNKNOWN_VALUE_TYPE
                    failed = True
                    spelling = (
                        node.name
                        if isinstance(node, ast.NameExpr)
                        else ".".join(node.parts)
                    )
                    unavailable = (
                        isinstance(node, ast.DottedNameExpr)
                        and node.parts[0] == expression.binding_name
                        and local.is_unknown
                    ) or any(
                        item[3].is_unknown
                        and (isinstance(node, ast.NameExpr) or item[2] == node.parts[0])
                        for item in environment
                    )
                    if unavailable:
                        return
                    diagnostics.append(
                        _diagnostic(
                            node.span,
                            "PIE-S2102",
                            f"{'Ambiguous' if candidates else 'Unknown or unavailable'} field in ANY predicate: {spelling}",
                        )
                    )
                    return
                occurrence, relation, binding, row = candidates[0]
                value_type = _field_value_type(row.fields[name])
                read = reads.get(node)
                if read is None:
                    read = AnyFieldReadInfo(
                        occurrence, relation, binding, name, value_type
                    )
                    reads[node] = read
                types[node] = value_type
                if value_type.kind is ValueTypeKind.UNKNOWN:
                    failed = True
                if occurrence is not expression:
                    captures.append(read)
                return
            for child in child_expressions(node):
                read_tree(child, environment, let_stack)

        if contains_semantic_aggregate(expression.predicate):
            diagnostics.append(
                _diagnostic(
                    expression.predicate.span,
                    "PIE-S2335",
                    "Aggregate expressions are unavailable in ANY predicates.",
                )
            )
            failed = True
        expansion = let_expansion_diagnostics(
            use.owner, let_types, extra_expressions=(expression.predicate,)
        )
        # This call checks the new body; ordinary relation roots are checked by
        # the existing LET pass. Do not duplicate their already owned failures.
        expansion = [
            item
            for item in expansion
            if item.location == _location(expression.predicate.span)
        ]
        diagnostics.extend(expansion)
        if expansion:
            failed = True
        else:
            read_tree(expression.predicate, visible)
        joined = RowSchema(
            fields={
                f"{binding}.{name}": field
                for _, _, binding, row in visible
                for name, field in row.fields.items()
            },
            joined=True,
        )
        inferred = infer_row_expression(
            expression.predicate,
            joined,
            types,
            diagnostics,
            report_unknown_name=False,
            field_qualifier=expression.binding_name,
            bare_value_types=let_types,
            bare_value_expressions=lets,
            type_expansions=type_expansions,
            failed_relationship_calls=failed_relationship_calls,
        )
        not_bool = _check_bool_expression(
            expression.predicate,
            context="ANY predicate",
            expression_value_types=types,
            type_expansions=type_expansions,
            explained=failed or len(diagnostics) > start,
            row_schema=joined,
            lets=lets,
        )
        if not_bool is not None:
            diagnostics.append(not_bool)
        elif (
            inferred.kind is ValueTypeKind.UNKNOWN
            and not failed
            and len(diagnostics) == start
        ):
            # Literal None is the SQL UNKNOWN predicate and never matches.
            if not (
                isinstance(expression.predicate, ast.LiteralExpr)
                and expression.predicate.value is None
            ):
                diagnostics.append(
                    _diagnostic(
                        expression.predicate.span,
                        "PIE-S2202",
                        "ANY predicate requires a known Bool expression.",
                    )
                )
        # Each copied occurrence retains its inlined scalar parameter contract.
        infer_row_expression(
            expression,
            joined,
            types,
            diagnostics,
            report_unknown_name=False,
            type_expansions=type_expansions,
        )
        expression_value_types.update(types)
        if not failed and len(diagnostics) == start:
            assert target is not None
            facts[expression] = AnyValueSemanticInfo(
                use,
                target,
                local,
                expression.predicate,
                reads,
                tuple(captures),
                tuple(nested),
            )
        processing.remove(key)
        processed.add(key)

    for use in uses:
        check(use)
    return facts, diagnostics


def _location(span: ast.Span) -> SourceLocation:
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _diagnostic(span: ast.Span, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code, severity=Severity.ERROR, message=message, location=_location(span)
    )
