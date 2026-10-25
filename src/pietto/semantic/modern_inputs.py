"""Resolve modern local names and bind row predicates to existing inputs."""

from __future__ import annotations

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import replace

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.existence_generators import AnyUseInfo
from pietto.semantic.model import (
    RelationshipCallInfo,
    RelationshipTemplateInfo,
)
from pietto.semantic.relation_schemas import _projection_output_name
from pietto.semantic.relationship_predicates import (
    RelationshipCallFailure,
    RowCandidate,
    _diagnostic,
    bind_relationship_expression,
)

__all__ = ()

_RELATIONS = (ast.SourceDef, ast.TableDef, ast.QueryDef)


def normalize_query_names(
    script: ast.Script,
    *,
    existence_generators: Sequence[AnyUseInfo] = (),
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> tuple[ast.Script, tuple[Diagnostic, ...]]:
    """Resolve each ``let name = value`` in its authored input scope.

    A bare value with both a relation candidate and scalar candidate is refused;
    position never decides its role. FROM and JOIN remain explicit row inputs.
    """

    generated_ids = {id(use.clause) for use in existence_generators}
    # A lowered WHERE ANY still binds its row name over its hidden ON condition.
    lowered = {id(use.clause.on_clause): use.expression for use in existence_generators}
    relations: dict[str, list[ast.SourceDef | ast.TableDef | ast.QueryDef]] = {}
    shapes: dict[str, list[ast.ShapeDef]] = {}
    for item in script.definitions:
        if isinstance(item, _RELATIONS):
            relations.setdefault(item.name, []).append(item)
        elif isinstance(item, ast.ShapeDef):
            shapes.setdefault(item.name, []).append(item)
    diagnostics: list[Diagnostic] = []
    definitions: list[ast.Definition] = []
    for definition in script.definitions:
        if (
            not isinstance(definition, (ast.TableDef, ast.QueryDef))
            or not definition.naming_declarations
            and not definition.named_windows
        ):
            definitions.append(definition)
            continue
        aliases: dict[str, list[ast.SourceDef | ast.TableDef | ast.QueryDef]] = {}
        alias_positions: dict[str, tuple[int, int]] = {}
        visible: list[ast.SourceDef | ast.TableDef | ast.QueryDef] = []
        scalar_names = {parameter.name for parameter in _owner_parameters(definition)}
        declared: set[str] = set()
        scalar_bindings: list[ast.LetBinding] = []
        from_clause = definition.from_clause
        joins: list[ast.JoinClause] = []
        # The input names a let cannot take, as PIE-S2329 refuses them.
        input_names: set[str] = set()

        def relation_candidates(
            name: str,
        ) -> list[ast.SourceDef | ast.TableDef | ast.QueryDef]:
            return [*aliases.get(name, ()), *relations.get(name, ())]

        def input_fields() -> set[str | None]:
            return {
                name
                for source in visible
                for name in (
                    (
                        field.name
                        for shape in shapes.get(source.shape_name or "", ())
                        for field in shape.fields
                    )
                    if isinstance(source, ast.SourceDef)
                    else map(_projection_output_name, source.select_items)
                )
            }

        def scalar_candidate(name: str) -> bool:
            return name in scalar_names or name in input_fields()

        window_names: set[str] = set()
        windows: list[tuple[ast.NamedWindowDeclaration, frozenset[str]]] = []
        authored = sorted(
            (
                *definition.naming_declarations,
                *definition.named_windows,
                from_clause,
                *definition.join_clauses,
            ),
            key=lambda node: (node.span.line, node.span.column),
        )
        for node in authored:
            if isinstance(node, ast.NamedWindowDeclaration):
                # Windows share the let namespace; two windows of one name
                # keep their own named-window diagnostic.
                if node.name in declared:
                    diagnostics.append(
                        _diagnostic(node, f"Duplicate query local name: {node.name}")
                    )
                elif shadow := shadowed_input(node, input_fields(), input_names):
                    diagnostics.append(shadow)
                window_names.add(node.name)
                windows.append((node, frozenset(declared)))
            elif isinstance(node, ast.QueryLetDeclaration):
                if node.name in declared or node.name in window_names:
                    diagnostics.append(
                        _diagnostic(node, f"Duplicate query local name: {node.name}")
                    )
                declared.add(node.name)
                value = node.expression
                candidates = (
                    relation_candidates(value.name)
                    if isinstance(value, ast.NameExpr)
                    else []
                )
                if (
                    candidates
                    and isinstance(value, ast.NameExpr)
                    and scalar_candidate(value.name)
                ):
                    diagnostics.append(
                        _diagnostic(
                            value, f"Ambiguous relation or scalar name: {value.name}"
                        )
                    )
                elif len(candidates) > 1:
                    assert isinstance(value, ast.NameExpr)
                    diagnostics.append(
                        _diagnostic(value, f"Ambiguous relation name: {value.name}")
                    )
                elif candidates:
                    aliases.setdefault(node.name, []).extend(candidates)
                    alias_positions.setdefault(
                        node.name, (node.span.line, node.span.column)
                    )
                else:
                    position = (node.span.line, node.span.column)
                    last_input = max(
                        (item.span.line, item.span.column)
                        for item in (definition.from_clause, *definition.join_clauses)
                        if id(item) not in generated_ids
                    )
                    where = definition.where_clause
                    if position <= last_input or (
                        where is not None
                        and position >= (where.span.line, where.span.column)
                    ):
                        diagnostics.append(
                            _diagnostic(
                                node,
                                "A row-value let must follow FROM and every JOIN and precede WHERE",
                            )
                        )
                        continue
                    diagnostics.extend(later_let_reads(windows, node.name))
                    scalar_names.add(node.name)
                    binding = ast.LetBinding(
                        span=node.span, name=node.name, expression=value
                    )
                    if occurrence_observer is not None:
                        occurrence_observer(node, binding)
                    scalar_bindings.append(binding)
            elif isinstance(node, ast.FromClause):
                candidates = relation_candidates(node.source_name)
                if len(candidates) > 1:
                    if definition.naming_declarations:
                        diagnostics.append(
                            _diagnostic(
                                node, f"Ambiguous FROM input: {node.source_name}"
                            )
                        )
                elif candidates:
                    target = candidates[0]
                    if node.source_name in aliases:
                        from_clause = replace(
                            node, source_name=target.name, binding_name=node.source_name
                        )
                    visible.append(target)
                input_names.add(from_clause.binding_name or from_clause.source_name)
                if definition.join_clauses:
                    input_names.add(from_clause.source_name)
            else:
                assert isinstance(node, ast.JoinClause)
                candidates = relation_candidates(node.target_relation_name)
                if len(candidates) > 1:
                    if definition.naming_declarations:
                        diagnostics.append(
                            _diagnostic(
                                node,
                                f"Ambiguous JOIN input: {node.target_relation_name}",
                            )
                        )
                    joins.append(node)
                elif candidates:
                    target = candidates[0]
                    joins.append(replace(node, target_relation_name=target.name))
                    if node.kind not in (
                        ast.AuthoredJoinKind.SEMI,
                        ast.AuthoredJoinKind.ANTI,
                    ):
                        visible.append(target)
                else:
                    joins.append(node)
                if id(node) not in generated_ids:
                    input_names.update(
                        (node.target_binding_name, joins[-1].target_relation_name)
                    )
        if not definition.naming_declarations:
            # Only windows: the check above leaves the definition as written.
            definitions.append(definition)
            continue
        let_clause = definition.let_clause
        if scalar_bindings:
            if let_clause is None:
                let_clause = ast.LetClause(
                    span=scalar_bindings[0].span, bindings=tuple(scalar_bindings)
                )
            else:
                previous_let_clause = let_clause
                let_clause = replace(
                    let_clause, bindings=(*let_clause.bindings, *scalar_bindings)
                )
                if occurrence_observer is not None:
                    occurrence_observer(previous_let_clause, let_clause)
        normalized = replace(
            definition,
            from_clause=from_clause,
            join_clauses=tuple(joins),
            let_clause=let_clause,
            naming_declarations=(),
        )
        if occurrence_observer is not None:
            occurrence_observer(definition, normalized)
        from pietto.semantic.inline_functions import _rebuild

        scopes = _lexical_any_scopes(normalized, lowered)

        def any_target(before: object, after: object) -> object:
            if not isinstance(before, ast.AnyExpr) or not isinstance(
                after, ast.AnyExpr
            ):
                return after
            if any(
                scope.binding_name == before.relation_name
                for scope in scopes.get(id(before), ())
            ):
                return after
            position = (before.span.line, before.span.column)
            candidates = [
                *relations.get(before.relation_name, ()),
                *(
                    aliases.get(before.relation_name, ())
                    if alias_positions.get(before.relation_name, position) <= position
                    else ()
                ),
            ]
            if len(candidates) > 1:
                diagnostics.append(
                    _diagnostic(before, f"Ambiguous ANY input: {before.relation_name}")
                )
            elif candidates and before.relation_name in aliases:
                return replace(after, relation_name=candidates[0].name)
            return after

        rebuilt = _rebuild(
            normalized, any_target, occurrence_observer=occurrence_observer
        )
        assert isinstance(rebuilt, (ast.TableDef, ast.QueryDef))
        definitions.append(rebuilt)
    return replace(script, definitions=tuple(definitions)), tuple(diagnostics)


def shadowed_input(
    window: ast.NamedWindowDeclaration,
    fields: Container[str | None],
    relations: Container[str],
) -> Diagnostic | None:
    """PIE-S2329 when a window takes the name of an input field or relation,
    which a value let cannot take either."""

    if window.name in fields:
        reason = "Let binding cannot shadow input field"
    elif window.name in relations:
        reason = "Let binding cannot shadow input relation"
    else:
        return None
    span = window.span
    return Diagnostic(
        code="PIE-S2329",
        severity=Severity.ERROR,
        message=f"{reason}: {window.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def later_let_reads(
    windows: Sequence[tuple[ast.NamedWindowDeclaration, frozenset[str]]], name: str
) -> list[Diagnostic]:
    """PIE-S2330 at each read of the value let ``name`` by a window declared
    before it, unless a let of that name precedes the window: like a let, a
    window reads only earlier lets, while windows still read each other in
    either direction."""

    from pietto.semantic.inline_functions import _tree_nodes

    return [
        Diagnostic(
            code="PIE-S2330",
            severity=Severity.ERROR,
            message=f"Let binding cannot reference a later binding: {name}",
            location=SourceLocation(
                path=read.span.path,
                line=read.span.line,
                column=read.span.column,
                end_line=read.span.end_line,
                end_column=read.span.end_column,
            ),
        )
        for window, before in windows
        if name not in before and window.spec is not None
        for read in _tree_nodes(window.spec)
        if type(read) is ast.NameExpr and read.name == name
    ]


def _lexical_any_scopes(
    root: ast.Node, lowered: Mapping[int, ast.AnyExpr] | None = None
) -> dict[int, tuple[ast.AnyExpr, ...]]:
    from pietto.semantic.inline_functions import _children

    scopes: dict[int, tuple[ast.AnyExpr, ...]] = {}
    pending: list[tuple[object, tuple[ast.AnyExpr, ...]]] = [(root, ())]
    while pending:
        node, ancestors = pending.pop()
        if lowered and id(node) in lowered:
            ancestors = (*ancestors, lowered[id(node)])
        if isinstance(node, ast.Expression):
            scopes[id(node)] = ancestors
        if isinstance(node, ast.AnyExpr):
            pending.append((node.predicate, (*ancestors, node)))
        else:
            pending.extend(
                (child, ancestors) for child in reversed(_children(node) or ())
            )
    return scopes


def bind_script_relationship_predicates(
    script: ast.Script,
    *,
    templates: Sequence[RelationshipTemplateInfo],
    shape_candidates: Mapping[str, Sequence[ast.Node]],
    scalar_names: frozenset[str] = frozenset(),
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> tuple[
    ast.Script,
    tuple[RelationshipCallInfo, ...],
    tuple[Diagnostic, ...],
    tuple[RelationshipCallFailure, ...],
]:
    """Single-file adapter; module binding supplies a separate project adapter."""

    if not script.relationship_templates:
        return script, (), (), ()
    declared_names = frozenset(
        template.name for template in script.relationship_templates
    )
    relations: dict[str, list[ast.SourceDef | ast.TableDef | ast.QueryDef]] = {}
    for item in script.definitions:
        if isinstance(item, _RELATIONS):
            relations.setdefault(item.name, []).append(item)
    calls: list[RelationshipCallInfo] = []
    failures: list[RelationshipCallFailure] = []
    diagnostics: list[Diagnostic] = []
    definitions: list[ast.Definition] = []
    for definition in script.definitions:
        if not isinstance(definition, (ast.TableDef, ast.QueryDef)):
            definitions.append(definition)
            continue
        owner: ast.TableDef | ast.QueryDef = definition
        inputs: list[tuple[str, ast.Node, str, bool]] = [
            (
                owner.from_clause.binding_name or owner.from_clause.source_name,
                owner.from_clause,
                owner.from_clause.source_name,
                True,
            ),
            *(
                (
                    join.target_binding_name,
                    join,
                    join.target_relation_name,
                    join.kind
                    not in (ast.AuthoredJoinKind.SEMI, ast.AuthoredJoinKind.ANTI),
                )
                for join in owner.join_clauses
            ),
        ]
        owner_calls: list[RelationshipCallInfo] = []
        replacements: dict[int, ast.Node] = {}

        def rewrite(
            expression: ast.Expression,
            context: ast.Node,
            limit: int | None = None,
        ) -> ast.Expression:
            lexical_scopes = _lexical_any_scopes(expression)

            def resolve(argument: ast.NameExpr) -> tuple[RowCandidate, ...]:
                candidates: list[RowCandidate] = []
                for scope in reversed(lexical_scopes.get(id(argument), ())):
                    if scope.binding_name != argument.name:
                        continue
                    for source in relations.get(scope.relation_name, ()):
                        if not isinstance(source, ast.SourceDef):
                            continue
                        for shape in shape_candidates.get(source.shape_name or "", ()):
                            if isinstance(shape, ast.ShapeDef):
                                candidates.append((scope, source, shape))
                    return tuple(candidates)
                for position, (name, occurrence, relation_name, visible) in enumerate(
                    inputs
                ):
                    if name != argument.name or (
                        limit is not None and position > limit
                    ):
                        continue
                    if not visible and position != limit:
                        continue
                    for source in relations.get(relation_name, ()):
                        if not isinstance(source, ast.SourceDef):
                            continue
                        for shape in shape_candidates.get(source.shape_name or "", ()):
                            if isinstance(shape, ast.ShapeDef):
                                candidates.append((occurrence, source, shape))
                return tuple(candidates)

            scalar_argument_names = {
                binding.name
                for binding in (owner.let_clause.bindings if owner.let_clause else ())
            }
            scalar_argument_names.update(
                parameter.name for parameter in _owner_parameters(owner)
            )
            for position, (_, _, relation_name, visible) in enumerate(inputs):
                if (limit is not None and position > limit) or (
                    not visible and position != limit
                ):
                    continue
                for source in relations.get(relation_name, ()):
                    if isinstance(source, ast.SourceDef):
                        for shape in shape_candidates.get(source.shape_name or "", ()):
                            if isinstance(shape, ast.ShapeDef):
                                scalar_argument_names.update(
                                    field.name for field in shape.fields
                                )

            def available_scalar(argument: ast.NameExpr) -> bool:
                return (
                    not any(
                        scope.binding_name == argument.name
                        for scope in lexical_scopes.get(id(argument), ())
                    )
                    and argument.name in scalar_argument_names
                )

            def observed(before: object, after: object) -> None:
                if isinstance(before, ast.AnyExpr) and isinstance(after, ast.AnyExpr):
                    replacements[id(before)] = after
                if occurrence_observer is not None:
                    occurrence_observer(before, after)

            expanded, uses, found, failed = bind_relationship_expression(
                expression,
                templates=templates,
                declared_names=declared_names,
                resolve_row=resolve,
                owner=owner,
                context=context,
                scalar_names=scalar_names,
                scalar_argument_names=frozenset(scalar_argument_names),
                scalar_argument_available=available_scalar,
                occurrence_observer=observed,
                first_ordinal=len(calls) + len(owner_calls),
            )
            owner_calls.extend(uses)
            failures.extend(failed)
            diagnostics.extend(found)
            return expanded

        joins: list[ast.JoinClause] = []
        for position, join in enumerate(owner.join_clauses, 1):
            on = join.on_clause
            if on is not None:
                new_on = replace(on, expression=rewrite(on.expression, on, position))
                replacements[id(on)] = new_on
                if occurrence_observer is not None:
                    occurrence_observer(on, new_on)
                new_join = replace(join, on_clause=new_on)
            else:
                new_join = join
            replacements[id(join)] = new_join
            if occurrence_observer is not None:
                occurrence_observer(join, new_join)
            joins.append(new_join)
        values: dict[str, object] = {"join_clauses": tuple(joins)}
        for name in ("where_clause", "qualify_clause", "satisfying_clause"):
            clause = getattr(owner, name)
            if clause is not None:
                changed = replace(clause, expression=rewrite(clause.expression, clause))
                replacements[id(clause)] = changed
                if occurrence_observer is not None:
                    occurrence_observer(clause, changed)
                values[name] = changed
        select_items = []
        for item in owner.select_items:
            changed = replace(item, expression=rewrite(item.expression, item))
            replacements[id(item)] = changed
            if occurrence_observer is not None:
                occurrence_observer(item, changed)
            select_items.append(changed)
        values["select_items"] = tuple(select_items)
        if owner.let_clause is not None:
            bindings = []
            for item in owner.let_clause.bindings:
                limit = max(
                    (
                        position
                        for position, (_, occurrence, _, _) in enumerate(inputs)
                        if (occurrence.span.line, occurrence.span.column)
                        <= (item.span.line, item.span.column)
                    ),
                    default=-1,
                )
                changed = replace(
                    item, expression=rewrite(item.expression, item, limit)
                )
                replacements[id(item)] = changed
                if occurrence_observer is not None:
                    occurrence_observer(item, changed)
                bindings.append(changed)
            let_clause = replace(owner.let_clause, bindings=tuple(bindings))
            if occurrence_observer is not None:
                occurrence_observer(owner.let_clause, let_clause)
            values["let_clause"] = let_clause
        result = replace(owner, **values)
        if occurrence_observer is not None:
            occurrence_observer(owner, result)
        definitions.append(result)
        calls.extend(
            replace(
                call,
                owner=result,
                context=replacements.get(id(call.context), call.context),
                arguments=tuple(
                    replace(
                        argument,
                        occurrence=replacements.get(
                            id(argument.occurrence), argument.occurrence
                        ),
                    )
                    for argument in call.arguments
                ),
            )
            for call in owner_calls
        )
    # Clause traversal order is an implementation detail; facts keep source use order.
    calls.sort(
        key=lambda call: (
            call.call.span.path or "",
            call.call.span.line,
            call.call.span.column,
            call.call.span.occurrence,
        )
    )
    ordered = tuple(replace(call, ordinal=index) for index, call in enumerate(calls))
    return (
        replace(script, definitions=tuple(definitions)),
        ordered,
        tuple(diagnostics),
        tuple(failures),
    )


def _owner_parameters(
    owner: ast.TableDef | ast.QueryDef,
) -> tuple[ast.QueryParameter, ...]:
    return owner.parameters if isinstance(owner, ast.QueryDef) else ()
