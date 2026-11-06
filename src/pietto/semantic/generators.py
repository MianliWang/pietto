"""Generators: the conditional count and sum of a group.

A generator ``BODY for o in SOURCE [if TEST]`` is the only argument of a call.
Its meaning is fixed by SOURCE alone: a relation name is the whole relation
(today's ``any(...)``), ``group`` is the member rows of the current group when
no relation or ``let`` that the body sees is named ``group``, and
``binding.field`` is a row's collected list (not available yet). The
pre-admission gate admits only ``sum(1 for o in group if TEST)`` and
``sum(o.f for o in group if TEST)`` as a whole aliased SELECT item of a
relation body without JOIN inputs; any other use is one diagnostic, the first
rule it breaks in a fixed order. After the gate, `normalize_group_generators`
reads each member field ``o.f`` as the input row's field ``f``: inside an
aggregate the member row is the input row, so later readers see a plain row
expression in the generator.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import cast

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    SEMANTIC_AGGREGATE_NAMES,
    aggregate_alias_required_diagnostic,
    callee_name,
    deferred_composition_diagnostic,
    invalid_context_diagnostic,
    nested_aggregate_diagnostic,
    semantic_aggregate_call_name,
)

__all__ = (
    "GROUP_SOURCE",
    "generator_of",
    "group_test_hint",
    "names_group",
    "normalize_group_generators",
)

GROUP_SOURCE = "group"
_CODE = "PIE-S2334"
# The clause of a relation body that reads an aggregate, as PIE-S2308 names it.
_CONTEXTS = {
    "where_clause": "where clause",
    "join_filters": "where clause",
    "let_clause": "let binding",
    "naming_declarations": "let binding",
    "join_clauses": "JOIN ON",
    "satisfying_clause": "having clause",
    "order_by_clause": "order by",
}
_BODIES = (ast.TableDef, ast.QueryDef, ast.SelectBody)
_RELATIONS = (
    ast.SourceDef,
    ast.TableDef,
    ast.QueryDef,
    ast.SetRelationDef,
    ast.BlockRelationDef,
)
# A test reads one member row: none of these is a value of that row.
_NOT_ROW_VALUES = (
    ast.WindowExpr,
    ast.AnyExpr,
    ast.GeneratorExpr,
    ast.RelationExistsExpr,
    ast.RelationScalarExpr,
    ast.RelationMembershipExpr,
    ast.CollectRelationExpr,
    ast.CapturedFieldExpr,
)


def generator_of(expression: object) -> ast.GeneratorExpr | None:
    """The generator of a call written with one, else None."""

    if type(expression) is not ast.CallExpr:
        return None
    arguments = cast(ast.CallExpr, expression).arguments
    if len(arguments) == 1 and type(arguments[0]) is ast.GeneratorExpr:
        return cast(ast.GeneratorExpr, arguments[0])
    return None


def group_test_hint(binder: str) -> str:
    """The suggestion of an `any(... for o in group)` that names no relation:
    a test of the group is a conditional count compared later."""

    return (
        "a group test is not available yet: select "
        f"`n = sum(1 for {binder} in group if ...)` and test `n > 0` "
        "in `having` or a later query"
    )


def names_group(script: ast.Script) -> bool:
    """Whether a relation, import or `let` of ``script`` is named `group`."""

    from pietto.semantic.inline_functions import _tree_nodes

    return GROUP_SOURCE in _relations(script) or any(
        type(node) in {ast.LetRelationDef, ast.QueryLetDeclaration, ast.LetBinding}
        and cast(ast.LetBinding, node).name == GROUP_SOURCE
        for node in _tree_nodes(script)
    )


def _relations(script: ast.Script) -> set[str]:
    return {
        *(item.name for item in script.definitions if isinstance(item, _RELATIONS)),
        *(
            item.local_name or item.exported_name
            for statement in script.module_statements
            if type(statement) is ast.ImportStatement
            for item in statement.items
        ),
    }


def generator_diagnostics(script: ast.Script, *, single_file: bool) -> list[Diagnostic]:
    """One diagnostic for each generator call that is not admitted: a single
    file admits the conditional count and sum of a group, a project none yet.
    A generator inside another generator is reported by the outer one."""

    from pietto.semantic.inline_functions import _tree_nodes

    calls = [node for node in _tree_nodes(script) if generator_of(node) is not None]
    if not calls:
        return []
    known = {
        *(item.name for item in script.definitions if hasattr(item, "name")),
        *(item.name for item in script.relationship_templates),
    }
    relations = _relations(script)
    positions = dict(_positions(script))
    found = []
    skipped: set[int] = set()
    for node in calls:
        generator = generator_of(node)
        if generator is None or id(node) in skipped:
            continue
        skipped.update(
            id(inner) for inner in _tree_nodes(generator) if generator_of(inner)
        )
        call = cast(ast.CallExpr, node)
        diagnostic = _check(
            call,
            generator,
            positions.get(id(call)),
            known=known,
            relations=relations,
            project=not single_file,
        )
        if diagnostic is not None:
            found.append(diagnostic)
    return found


def normalize_group_generators(script: ast.Script) -> ast.Script:
    """``script`` with each member field read ``o.f`` of an admitted generator
    read as the input row's field ``f``, at the same span."""

    from pietto.semantic.inline_functions import _rebuild

    def member(binder: str):
        def visit(_before: object, after: object) -> object:
            if (
                type(after) is ast.DottedNameExpr
                and len(cast(ast.DottedNameExpr, after).parts) == 2
                and cast(ast.DottedNameExpr, after).parts[0] == binder
            ):
                read = cast(ast.DottedNameExpr, after)
                return ast.NameExpr(span=read.span, name=read.parts[1])
            return after

        return visit

    def visit(_before: object, after: object) -> object:
        if type(after) is not ast.GeneratorExpr:
            return after
        generator = cast(ast.GeneratorExpr, after)
        reads = member(generator.binding_name)
        return ast.GeneratorExpr(
            span=generator.span,
            body=cast(ast.Expression, _rebuild(generator.body, reads)),
            binding_name=generator.binding_name,
            binding_span=generator.binding_span,
            source=generator.source,
            source_span=generator.source_span,
            condition=None
            if generator.condition is None
            else cast(ast.Expression, _rebuild(generator.condition, reads)),
        )

    return cast(ast.Script, _rebuild(script, visit))


class _Position:
    """Where a generator call is written in one relation body."""

    def __init__(
        self,
        body: ast.TableDef | ast.QueryDef | ast.SelectBody,
        context: str,
        item: ast.SelectItem | None,
        lets: frozenset[str],
    ) -> None:
        self.body = body
        self.context = context
        self.item = item
        self.lets = lets
        # The FROM and JOIN binding names of the body.
        self.inputs = frozenset(
            (
                *(
                    ()
                    if type(body.from_clause) is not ast.FromClause
                    or body.from_clause.binding_name is None
                    else (body.from_clause.binding_name,)
                ),
                *(join.target_binding_name for join in body.join_clauses),
            )
        )


def _positions(script: ast.Script) -> Iterator[tuple[int, _Position]]:
    from pietto.semantic.inline_functions import _tree_nodes

    pending: list[tuple[object, frozenset[str]]] = [(script, frozenset())]
    while pending:
        value, block_lets = pending.pop()
        if type(value) is ast.BlockRelationDef:
            block = cast(ast.BlockRelationDef, value)
            block_lets = frozenset(let.name for let in block.let_relations)
        if isinstance(value, _BODIES):
            body = cast(ast.TableDef | ast.QueryDef | ast.SelectBody, value)
            lets = block_lets | {
                *(item.name for item in body.naming_declarations),
                *(
                    ()
                    if body.let_clause is None
                    else (item.name for item in body.let_clause.bindings)
                ),
            }
            for name in (
                "select_items",
                "where_clause",
                "join_filters",
                "let_clause",
                "naming_declarations",
                "join_clauses",
                "satisfying_clause",
                "order_by_clause",
                "qualify_clause",
                "limit_clause",
                "named_windows",
            ):
                slot = getattr(body, name)
                items = slot if name == "select_items" else (slot,)
                for item in items:
                    for node in _tree_nodes(item):
                        if generator_of(node) is None:
                            continue
                        if name == "select_items":
                            select = cast(ast.SelectItem, item)
                            context = (
                                "select" if node is select.expression else "nested"
                            )
                            position = _Position(body, context, select, lets)
                        else:
                            position = _Position(
                                body,
                                _CONTEXTS.get(name, "this position"),
                                None,
                                lets,
                            )
                        yield id(node), position
            continue
        children = _children(value)
        pending.extend((child, block_lets) for child in reversed(children))


def _children(value: object) -> tuple[object, ...]:
    from pietto.semantic.inline_functions import _children as children

    return children(value) or ()


def _check(
    call: ast.CallExpr,
    generator: ast.GeneratorExpr,
    position: _Position | None,
    *,
    known: set[str],
    relations: set[str],
    project: bool,
) -> Diagnostic | None:
    from pietto.semantic.expressions import (
        _unknown_function_diagnostic,
        is_unknown_function_call,
    )

    name = callee_name(call)
    binder = generator.binding_name
    if project:
        return _error(
            call.span,
            f"{name}(... for ...) is not available in a project yet",
            "a single file checks and emits the conditional count and sum of a group",
        )
    if name not in {"sum", "any"}:
        if name == "count":
            return _error(
                call.span,
                "count takes no generator",
                f"count matching rows with `sum(1 for {binder} in group if ...)`",
            )
        if name == "len":
            return _error(
                call.span,
                "len takes no generator",
                f"count matching rows with `sum(1 for {binder} in group if ...)`",
            )
        if name in SEMANTIC_AGGREGATE_NAMES:
            return _error(
                call.span,
                f"{name} takes no generator; a conditional {name} is not available",
                f"only `sum(... for {binder} in group if ...)` takes a generator",
            )
        if is_unknown_function_call(call) and name not in known:
            return _unknown_function_diagnostic(call, name)
        return _error(call.span, "A generator is only the argument of sum or any")
    source = ".".join(generator.source)
    if name == "any" and generator.condition is not None:
        return _error(
            call.span,
            "any takes its test in the body",
            "write `any(q for o in r)`"
            if type(generator.body) is ast.LiteralExpr and generator.body.value is True
            else "write `any(p and q for o in r)`",
        )
    if len(generator.source) > 1:
        return _error(
            generator.source_span,
            f"A generator over {source} is not available yet",
            "`len`, `sum` and `any` over a row's collected list are a coming feature",
        )
    lets = frozenset() if position is None else position.lets
    if position is not None:
        relations = relations | position.inputs
    if source == GROUP_SOURCE and source in lets:
        return _error(
            generator.source_span,
            "Generator over group in sum: group is the let group, not this group",
            "rename the let group to read this group's rows",
        )
    if source == GROUP_SOURCE and source in relations:
        return _error(
            generator.source_span,
            "Generator over group in sum: group is the relation group, not this group",
            "rename the relation group to read this group's rows",
        )
    if source != GROUP_SOURCE:
        if source not in relations and source not in lets:
            return _diagnostic(
                "PIE-S2301",
                generator.source_span,
                f"Unknown or unavailable generator source: {source}",
                f"for this group's rows write `for {binder} in group`",
            )
        grouped = (
            position is None
            or position.body.group_by_clause is not None
            or all(
                semantic_aggregate_call_name(item.expression) is not None
                for item in position.body.select_items
            )
        )
        return _error(
            generator.source_span,
            f"Generator over {source} in sum: {source} is the whole relation, "
            "not this group",
            f"for this group's rows write `for {binder} in group`"
            if grouped
            else "count per key in a grouped query and join it on the key",
        )
    if position is None or position.context not in {"select", "nested"}:
        context = "this position" if position is None else position.context
        refused = invalid_context_diagnostic(call, context=context)
        if context in {"having clause", "order by"}:
            return refused
        # Before GROUP BY there is one row, not a group.
        hint = (
            "a group's rows exist only after `group by`; "
            "test a row's own fields directly"
        )
        return replace(refused, message=f"{refused.message}; {hint}", suggestion=hint)
    if position.context == "nested":
        assert position.item is not None
        return deferred_composition_diagnostic(position.item.expression)
    assert position.item is not None
    if position.item.alias is None:
        return aggregate_alias_required_diagnostic(call)
    if position.body.join_clauses or position.body.join_filters:
        return _error(
            call.span,
            f"sum(... for {binder} in group ...) over JOIN rows is not available yet",
            "join in one query, then group it in another that reads it with `from`",
        )
    return _body_diagnostic(call, generator) or _read_diagnostic(
        generator, _keys(position.body), position.lets
    )


def _body_diagnostic(
    call: ast.CallExpr, generator: ast.GeneratorExpr
) -> Diagnostic | None:
    body, binder = generator.body, generator.binding_name
    if type(body) is ast.LiteralExpr and type(body.value) is int and body.value == 1:
        if generator.condition is None:
            return _error(
                call.span,
                f"sum(1 for {binder} in group) counts every row of the group",
                "write `count()`",
            )
        return None
    if type(body) is ast.DottedNameExpr and body.parts[0] == binder:
        if len(body.parts) != 2:
            return _diagnostic(
                "PIE-S2102",
                body.span,
                f"Unknown or unavailable field in generator: {'.'.join(body.parts)}",
            )
        if generator.condition is None:
            return _error(
                call.span,
                f"sum({binder}.{body.parts[1]} for {binder} in group) adds every "
                "row of the group",
                f"write `sum({body.parts[1]})`",
            )
        return None
    hint = None
    if type(body) is ast.ConditionalExpr:
        hint = (
            f"filter with `if` after the source: "
            f"`sum({binder}.f for {binder} in group if ...)`"
        )
    elif type(body) is ast.NameExpr:
        hint = f"read the member as `{binder}.{body.name}`"
    return _diagnostic(
        "PIE-S2315",
        call.span,
        f"Aggregate function sum of a generator adds 1 or one field of {binder}; "
        "expression bodies are not supported yet",
        hint,
    )


def _keys(body: ast.TableDef | ast.QueryDef | ast.SelectBody) -> frozenset[str]:
    if body.group_by_clause is None:
        return frozenset()
    return frozenset(
        item.key.name
        for item in body.group_by_clause.items
        if type(item.key) is ast.NameExpr
    )


def _read_diagnostic(
    generator: ast.GeneratorExpr, keys: frozenset[str], lets: frozenset[str]
) -> Diagnostic | None:
    """The first read of the test that is not a member field, a GROUP BY
    key field or a parameter."""

    from pietto.semantic.inline_functions import _tree_nodes

    binder = generator.binding_name
    for node in _tree_nodes((generator.body, generator.condition)):
        if isinstance(node, _NOT_ROW_VALUES):
            return _error(
                cast(ast.Expression, node).span,
                "A generator test reads one member row: no window, any(...), "
                "generator, relation read or captured field",
            )
        if type(node) is ast.CallExpr and (
            callee_name(cast(ast.CallExpr, node)) in SEMANTIC_AGGREGATE_NAMES
        ):
            return nested_aggregate_diagnostic(cast(ast.CallExpr, node))
        if type(node) is ast.NameExpr:
            read = cast(ast.NameExpr, node).name
            if read == binder:
                return _error(
                    node.span,
                    f"Generator reads its member {binder} as a value",
                    f"read a field of it: `{binder}.f`",
                )
            if read not in keys or read in lets:
                return _error(
                    node.span,
                    f"Generator reads {read} outside its member",
                    f"write `{binder}.{read}`",
                )
        if type(node) is ast.DottedNameExpr:
            parts = cast(ast.DottedNameExpr, node).parts
            if parts[0] != binder:
                return _error(
                    node.span,
                    f"Generator reads {'.'.join(parts)} outside its member",
                    f"write `{binder}.{parts[-1]}`",
                )
            if len(parts) != 2 or parts[1] in lets:
                return _diagnostic(
                    "PIE-S2102",
                    node.span,
                    f"Unknown or unavailable field in generator: {'.'.join(parts)}",
                )
    return None


def _error(span: ast.Span, message: str, hint: str | None = None) -> Diagnostic:
    return _diagnostic(_CODE, span, message, hint)


def _diagnostic(
    code: str, span: ast.Span, message: str, hint: str | None = None
) -> Diagnostic:
    """A message states its hint too, as text output prints only the message."""

    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message if hint is None else f"{message}; {hint}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
        suggestion=hint,
    )
