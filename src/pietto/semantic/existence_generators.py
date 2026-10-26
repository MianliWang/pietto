"""Normalize inter-JOIN ANY filters into existing hidden SEMI/ANTI inputs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__ = ()


@dataclass(frozen=True, slots=True)
class AnyUseInfo:
    """One authored generator and its exact current hidden input occurrence."""

    expression: ast.AnyExpr
    authored_owner: ast.TableDef | ast.QueryDef
    context: ast.JoinFilterClause | ast.WhereClause
    owner: ast.TableDef | ast.QueryDef
    clause: ast.JoinClause
    input_ordinal: int
    preceding_join_count: int


@dataclass(frozen=True, slots=True)
class AnyValueInfo:
    authored_expression: ast.AnyExpr
    authored_owner: ast.TableDef | ast.QueryDef
    authored_context: ast.Node
    authored_join_count: int
    expression: ast.AnyExpr
    owner: ast.TableDef | ast.QueryDef
    context: ast.Node
    join_prefix_count: int


def _any_inventory(
    script: ast.Script,
) -> tuple[tuple[ast.AnyExpr, ast.TableDef | ast.QueryDef, ast.Node, int], ...]:
    from pietto.semantic.inline_functions import _children

    found = []
    for owner in script.definitions:
        if not isinstance(owner, (ast.TableDef, ast.QueryDef)):
            continue
        contexts: list[
            tuple[
                ast.JoinOnClause
                | ast.JoinFilterClause
                | ast.WhereClause
                | ast.SelectItem
                | ast.LetBinding
                | ast.QueryLetDeclaration,
                int,
            ]
        ] = []
        for index, join in enumerate(owner.join_clauses, 1):
            if join.on_clause is not None:
                contexts.append((join.on_clause, index))
        contexts.extend(
            (item, item.preceding_join_count) for item in owner.join_filters
        )
        if owner.where_clause is not None:
            contexts.append((owner.where_clause, len(owner.join_clauses)))
        contexts.extend((item, len(owner.join_clauses)) for item in owner.select_items)
        if owner.let_clause is not None:
            contexts.extend(
                (item, len(owner.join_clauses)) for item in owner.let_clause.bindings
            )
        contexts.extend(
            (item, len(owner.join_clauses)) for item in owner.naming_declarations
        )
        for context, prefix in contexts:
            pending: list[tuple[object, ast.Node]] = [(context.expression, context)]
            while pending:
                node, scope = pending.pop()
                if isinstance(node, ast.AnyExpr):
                    found.append((node, owner, scope, prefix))
                    pending.append((node.predicate, node))
                else:
                    pending.extend(
                        (child, scope) for child in reversed(_children(node) or ())
                    )
    return tuple(found)


class AnyValueTrace:
    def __init__(
        self, raw_script: ast.Script, *, uses: Sequence[AnyValueInfo] = ()
    ) -> None:
        self._origins: dict[
            int,
            tuple[ast.AnyExpr, ast.AnyExpr, ast.TableDef | ast.QueryDef, ast.Node, int],
        ] = {}
        inventory = _any_inventory(raw_script)
        current: dict[
            int, tuple[ast.AnyExpr, ast.TableDef | ast.QueryDef, ast.Node, int]
        ] = {}
        for expression, owner, context, prefix in inventory:
            if id(expression) in current:
                raise AssertionError("Duplicate ANY occurrence in current inventory")
            current[id(expression)] = (expression, owner, context, prefix)
        if uses:
            for use in uses:
                key = id(use.expression)
                item = current.get(key)
                if (
                    key in self._origins
                    or item is None
                    or item[0] is not use.expression
                    or item[1] is not use.owner
                    or item[2] is not use.context
                    or item[3] != use.join_prefix_count
                ):
                    raise AssertionError("ANY current inventory does not match uses")
                self._origins[key] = (
                    use.expression,
                    use.authored_expression,
                    use.authored_owner,
                    use.authored_context,
                    use.authored_join_count,
                )
            if len(self._origins) != len(current):
                raise AssertionError("ANY current inventory does not match uses")
        else:
            for expression, owner, context, prefix in inventory:
                self._origins[id(expression)] = (
                    expression,
                    expression,
                    owner,
                    context,
                    prefix,
                )

    def record(self, before: object, after: object) -> None:
        if not isinstance(before, ast.AnyExpr) or not isinstance(after, ast.AnyExpr):
            return
        origin = self._origins.get(id(before))
        if origin is not None:
            self._origins[id(after)] = (after, *origin[1:])


def collect_any_values(
    script: ast.Script, *, trace: AnyValueTrace
) -> tuple[AnyValueInfo, ...]:
    found = []
    for expression, owner, context, prefix in _any_inventory(script):
        origin = trace._origins.get(id(expression))
        if origin is None or origin[0] is not expression:
            raise AssertionError("ANY occurrence has no authored identity trace")
        _, authored, authored_owner, authored_context, authored_prefix = origin
        found.append(
            AnyValueInfo(
                authored,
                authored_owner,
                authored_context,
                authored_prefix,
                expression,
                owner,
                context,
                prefix,
            )
        )
    return tuple(found)


def rebind_any_values(
    before: ast.Script,
    after: ast.Script,
    uses: Sequence[AnyValueInfo],
    *,
    trace: AnyValueTrace,
) -> tuple[AnyValueInfo, ...]:
    inventory = _any_inventory(before)
    if len(inventory) != len(uses) or any(
        expression is not use.expression
        or owner is not use.owner
        or context is not use.context
        or prefix != use.join_prefix_count
        for (expression, owner, context, prefix), use in zip(
            inventory, uses, strict=True
        )
    ):
        raise AssertionError("ANY current inventory does not match uses")
    return collect_any_values(after, trace=trace)


def any_binders(uses: Sequence[AnyUseInfo]) -> dict[str, str]:
    """The binder as written of each hidden JOIN binding, by its generated name."""

    return {use.clause.target_binding_name: use.expression.binding_name for use in uses}


def written_read(
    node: ast.NameExpr | ast.DottedNameExpr, binders: Mapping[str, str]
) -> str:
    """``node`` as written: a read of a hidden JOIN's generated binding names
    the binder of its `any` (``binders``, from `any_binders`)."""

    head, *rest = node.parts if isinstance(node, ast.DottedNameExpr) else (node.name,)
    return ".".join((binders.get(head, head), *rest))


def without_any(script: ast.Script) -> ast.Script:
    """``script`` for a check that refuses each any(...): a WHERE before a
    later JOIN, which the parser admits only as `[not] any(...)` conjuncts, is
    dropped, and every other any(...) is the Bool literal True at its span."""

    from pietto.semantic.inline_functions import _rebuild

    def visit(before: object, after: object) -> object:
        if isinstance(before, ast.AnyExpr):
            return ast.LiteralExpr(span=before.span, value=True)
        if (
            isinstance(after, (ast.TableDef, ast.QueryDef, ast.SelectBody))
            and after.join_filters
        ):
            return replace(after, join_filters=())
        return after

    rebuilt = _rebuild(script, visit)
    assert isinstance(rebuilt, ast.Script)
    return rebuilt


def normalize_existence_generators(
    script: ast.Script,
    *,
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> tuple[ast.Script, tuple[AnyUseInfo, ...], tuple[Diagnostic, ...]]:
    """Lower inter-JOIN existential filters while preserving scalar values."""

    from pietto.semantic.inline_functions import _tree_nodes

    nodes = _tree_nodes(script)
    generators = tuple(node for node in nodes if isinstance(node, ast.AnyExpr))
    if not generators and not any(
        isinstance(node, (ast.TableDef, ast.QueryDef, ast.SelectBody))
        and node.join_filters
        for node in nodes
    ):
        return script, (), ()
    used: set[str] = set()
    for node in nodes:
        for attribute in ("name", "binding_name", "source_name", "target_binding_name"):
            name = getattr(node, attribute, None)
            if isinstance(name, str):
                used.add(name)
        if isinstance(node, ast.DottedNameExpr):
            used.add(node.parts[0])
    counter = 0
    consumed: set[int] = set()
    uses: list[AnyUseInfo] = []
    diagnostics: list[Diagnostic] = []
    definitions: list[ast.Definition] = []
    for item in script.definitions:
        if not isinstance(item, (ast.TableDef, ast.QueryDef)):
            definitions.append(item)
            continue
        definition: ast.TableDef | ast.QueryDef = item
        joins: list[ast.JoinClause] = []
        own: list[AnyUseInfo] = []

        def append_filter(
            condition: ast.Expression,
            context: ast.JoinFilterClause,
            prefix: int,
        ) -> bool:
            nonlocal counter
            if isinstance(condition, ast.UnaryExpr) and condition.operator == "not":
                negative = True
                expression = condition.operand
            else:
                negative = False
                expression = condition
            if not isinstance(expression, ast.AnyExpr):
                return False
            consumed.add(id(expression))
            while True:
                counter += 1
                binding = f"_pietto_any_{counter}"
                if binding not in used:
                    used.add(binding)
                    break

            def rename(before: object, after: object) -> object:
                if (
                    isinstance(after, ast.NameExpr)
                    and after.name == expression.binding_name
                ):
                    return replace(after, name=binding)
                if (
                    isinstance(after, ast.DottedNameExpr)
                    and after.parts[0] == expression.binding_name
                ):
                    return replace(after, parts=(binding, *after.parts[1:]))
                return after

            predicate = _rebuild_unshadowed(
                expression.predicate,
                expression.binding_name,
                rename,
                occurrence_observer,
            )
            assert isinstance(predicate, ast.Expression)
            clause = ast.JoinClause(
                span=condition.span,
                kind=ast.AuthoredJoinKind.ANTI
                if negative
                else ast.AuthoredJoinKind.SEMI,
                target_relation_name=expression.relation_name,
                target_binding_name=binding,
                target_binding_span=expression.binding_span,
                source_binding_name=None,
                on_clause=ast.JoinOnClause(
                    span=expression.predicate.span, expression=predicate
                ),
                uses_named_input=True,
            )
            joins.append(clause)
            own.append(
                AnyUseInfo(
                    expression,
                    definition,
                    context,
                    definition,
                    clause,
                    len(joins),
                    prefix,
                )
            )
            return True

        for prefix in range(len(definition.join_clauses) + 1):
            if prefix:
                joins.append(definition.join_clauses[prefix - 1])
            for clause in definition.join_filters:
                if clause.preceding_join_count != prefix:
                    continue
                for condition in _conjuncts(clause.expression):
                    if not append_filter(condition, clause, prefix):
                        diagnostics.append(_unsupported(condition))
        if not own:
            definitions.append(definition)
            continue
        normalized = replace(definition, join_clauses=tuple(joins), join_filters=())
        if occurrence_observer is not None:
            occurrence_observer(definition, normalized)
        definitions.append(normalized)
        uses.extend(replace(use, owner=normalized) for use in own)
    supported = {id(expression) for expression, _, _, _ in _any_inventory(script)}
    diagnostics.extend(
        _unsupported(expression)
        for expression in generators
        if id(expression) not in consumed and id(expression) not in supported
    )
    diagnostics.sort(
        key=lambda item: (
            item.location.path or "",
            item.location.line,
            item.location.column,
            item.code,
        )
    )
    return (
        replace(script, definitions=tuple(definitions)),
        tuple(uses),
        tuple(diagnostics),
    )


def rebind_existence_generators(
    before: ast.Script,
    after: ast.Script,
    uses: Sequence[AnyUseInfo],
) -> tuple[AnyUseInfo, ...]:
    """Rebind across transforms preserving derived-owner and JOIN order.

    Scalar def declarations may disappear; no name or AST equality chooses an
    owner or occurrence. Authored nodes remain the original provenance.
    """

    if not uses:
        return ()
    old = tuple(
        item
        for item in before.definitions
        if isinstance(item, (ast.TableDef, ast.QueryDef))
    )
    new = tuple(
        item
        for item in after.definitions
        if isinstance(item, (ast.TableDef, ast.QueryDef))
    )
    mapping = {id(left): right for left, right in zip(old, new, strict=True)}
    rebound: list[AnyUseInfo] = []
    for use in uses:
        owner = mapping[id(use.owner)]
        assert len(owner.join_clauses) == len(use.owner.join_clauses)
        assert use.owner.join_clauses[use.input_ordinal - 1] is use.clause
        rebound.append(
            replace(use, owner=owner, clause=owner.join_clauses[use.input_ordinal - 1])
        )
    return tuple(rebound)


def _rebuild_unshadowed(
    root: object,
    binding: str,
    visit: Callable[[object, object], object],
    observer: Callable[[object, object], None] | None,
) -> object:
    from pietto.semantic.inline_functions import _child_names, _children

    done: list[object] = []
    pending: list[tuple[object, tuple[object, ...] | None, bool]] = [(root, None, True)]
    while pending:
        value, children, active = pending.pop()
        if children is None:
            children = _children(value)
            if children is None:
                done.append(value)
                continue
            pending.append((value, children, active))
            child_active = active and not (
                isinstance(value, ast.AnyExpr) and value.binding_name == binding
            )
            pending.extend((child, None, child_active) for child in reversed(children))
            continue
        start = len(done) - len(children)
        rebuilt_children = tuple(done[start:])
        del done[start:]
        if all(new is old for new, old in zip(rebuilt_children, children)):
            rebuilt = value
        elif type(value) is tuple:
            rebuilt = rebuilt_children
        else:
            rebuilt = replace(
                cast(ast.Node, value),
                **{
                    name: new
                    for name, new, old in zip(
                        _child_names(value), rebuilt_children, children
                    )
                    if new is not old
                },
            )
        result = (
            visit(value, rebuilt) if active and type(value) is not tuple else rebuilt
        )
        if observer is not None:
            observer(value, result)
        done.append(result)
    (result,) = done
    return result


def _conjuncts(expression: ast.Expression) -> tuple[ast.Expression, ...]:
    found: list[ast.Expression] = []
    pending = [expression]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.BinaryExpr) and current.operator == "and":
            pending.extend((current.right, current.left))
        else:
            found.append(current)
    return tuple(found)


def _unsupported(expression: ast.Expression) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code="PIE-S2334",
        severity=Severity.ERROR,
        message="ANY is not supported in this context",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
