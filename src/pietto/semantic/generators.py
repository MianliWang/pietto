"""Generators: the conditional count and sum of a group, and its test.

A generator ``BODY for o in SOURCE [if TEST]`` is the only argument of a call.
Its meaning is fixed by SOURCE alone: a relation name is the whole relation
(today's ``any(...)``), ``group`` is the member rows of the current group when
no relation or ``let`` that the body sees is named ``group``, and
``binding.field`` is a row's collected list. The pre-admission gate admits
only ``sum(1 for o in group if TEST)``, ``sum(o.f for o in group if TEST)``,
``any(TEST for o in group)`` and ``all(TEST for o in group)`` as a whole
aliased SELECT item of a relation body without JOIN inputs in a single file or
a `schema_version = 2` project, and in such a project also the `sum` and
`any` of a row's collected list, whose project checks type and place them; any
other use is one diagnostic, the first rule it breaks in a fixed order. An
``any(... for o in group)`` in a SELECT item is read as a generator call
(`group_any_calls`) before the gate, as only there can it be the test of a
group. After the gate, `normalize_group_generators` reads each member field
``o.f`` as the input row's field ``f``: inside an aggregate the member row is
the input row, so later readers see a plain row expression in the generator.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import cast

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    GROUP_TEST_AGGREGATE_NAMES,
    SEMANTIC_AGGREGATE_NAMES,
    aggregate_alias_required_diagnostic,
    callee_name,
    deferred_composition_diagnostic,
    invalid_context_diagnostic,
    nested_aggregate_diagnostic,
    semantic_aggregate_call_name,
)

__all__ = (
    "BEFORE_GROUPS_HINT",
    "GROUP_SOURCE",
    "generator_of",
    "group_any_calls",
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


# Before GROUP BY there is one row, not a group.
BEFORE_GROUPS_HINT = (
    "a group's rows exist only after `group by`; test a row's own fields directly"
)


def group_test_hint(binder: str, name: str = "any") -> str:
    """The suggestion of a test of the group, `any` or `all` over `group`,
    outside a SELECT item where a later clause would read it."""

    output = "has_paid" if name == "any" else "all_paid"
    return (
        f"select `{output} = {name}({binder}.paid for {binder} in group)` and read "
        f"`{output}` in `having` or `order by`"
    )


def group_any_calls(script: ast.Script) -> ast.Script:
    """``script`` with each ``any(TEST for o in group)`` written in a SELECT
    item read as the generator call ``any`` of ``TEST for o in group``, at the
    same spans: there it is the test of a group, which the gate admits or
    refuses as any other generator call (a relation or ``let`` named `group`
    included). Elsewhere it keeps its relation meaning."""

    from pietto.semantic.inline_functions import _rebuild, _tree_nodes

    selected: set[int] = set()
    pending: list[object] = [
        item
        for body in _tree_nodes(script)
        if isinstance(body, _BODIES)
        for item in cast(
            ast.TableDef | ast.QueryDef | ast.SelectBody, body
        ).select_items
    ]
    while pending:
        node = pending.pop()
        if type(node) is ast.AnyExpr:
            # Inside another `any(...)` a row is tested, never a group.
            if cast(ast.AnyExpr, node).relation_name == GROUP_SOURCE:
                selected.add(id(node))
            continue
        pending.extend(_children(node))
    if not selected:
        return script

    def visit(before: object, after: object) -> object:
        if id(before) not in selected:
            return after
        test = cast(ast.AnyExpr, after)
        span, body = test.span, test.predicate
        return ast.CallExpr(
            span=span,
            callee=ast.NameExpr(
                span=ast.Span(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.line,
                    end_column=span.column + 3,
                ),
                name="any",
            ),
            arguments=(
                ast.GeneratorExpr(
                    span=ast.Span(
                        path=span.path,
                        line=body.span.line,
                        column=body.span.column,
                        end_line=test.relation_span.end_line,
                        end_column=test.relation_span.end_column,
                    ),
                    body=body,
                    binding_name=test.binding_name,
                    binding_span=test.binding_span,
                    source=(GROUP_SOURCE,),
                    source_span=test.relation_span,
                    condition=None,
                ),
            ),
        )

    return cast(ast.Script, _rebuild(script, visit))


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


def generator_diagnostics(
    script: ast.Script, *, single_file: bool, explicit_modules: bool = False
) -> list[Diagnostic]:
    """One diagnostic for each generator call that is not admitted: a single
    file and a `schema_version = 2` project admit the conditional count and
    sum of a group, a `schema_version = 2` project also the `sum` and `any` of
    a row's collected list (whose project checks type it), a `schema_version =
    1` project none. A generator inside another generator is reported by the
    outer one."""

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
            legacy_flat=not single_file and not explicit_modules,
            lists=explicit_modules,
        )
        if diagnostic is not None:
            found.append(diagnostic)
    return found


def normalize_group_generators(script: ast.Script) -> ast.Script:
    """``script`` with each member field read ``o.f`` of an admitted group
    generator read as the input row's field ``f``, at the same span. A list
    generator over a row's field ``c.xs`` keeps its element reads ``o.f``."""

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
        if (
            type(after) is not ast.GeneratorExpr
            or cast(ast.GeneratorExpr, after).source_read is not None
        ):
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
            source_read=generator.source_read,
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
    legacy_flat: bool,
    lists: bool = False,
) -> Diagnostic | None:
    from pietto.semantic.expressions import (
        _unknown_function_diagnostic,
        is_unknown_function_call,
    )

    name = callee_name(call)
    binder = generator.binding_name
    if lists and generator.source_read is not None:
        return _list_diagnostic(call, generator, known)
    if name in {"first", "last"}:
        return _error(
            call.span,
            f"{name} takes no generator",
            f"write `{name}(x, order by k, id)`",
        )
    only = generator.source[0]
    if (
        lists
        and only != GROUP_SOURCE
        and only not in relations
        and (position is None or only not in position.inputs | position.lets)
        and not _grouped(position)
    ):
        # No relation of that name outside a group: most likely a collected
        # field read without its row, which a single name after `in` never
        # is. In a group it is the single file's group hint below. The row
        # is named only in a body without JOIN inputs, where it is the FROM
        # row; with them the list may be any input's.
        found = (
            None
            if position is None or position.body.join_clauses
            else position.body.from_clause
        )
        row = (
            found.binding_name or found.source_name
            if type(found) is ast.FromClause
            else "c"
        )
        return _diagnostic(
            "PIE-S2301",
            generator.source_span,
            f"Unknown or unavailable generator source: {only}",
            f"a row's collected list is read through its row: "
            f"`for {binder} in {row}.{only}`",
        )
    if legacy_flat:
        return _error(
            call.span,
            f"{name}(... for ...): a schema_version = 1 project has no generator "
            "in the current syntax",
            "set schema_version = 2 to check it",
        )
    if name not in {"sum", *GROUP_TEST_AGGREGATE_NAMES}:
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
                f"only `sum(... for {binder} in group if ...)`, `any(...)` and "
                "`all(...)` take a generator",
            )
        if is_unknown_function_call(call) and name not in known:
            return _unknown_function_diagnostic(call, name)
        return _error(call.span, "A generator is only the argument of sum, any or all")
    source = ".".join(generator.source)
    if name == "any" and generator.condition is not None:
        return _error(
            call.span,
            "any takes its test in the body",
            f"write `any(q for o in {source})`"
            if type(generator.body) is ast.LiteralExpr and generator.body.value is True
            else f"write `any(p and q for o in {source})`",
        )
    if name == "all" and generator.condition is not None:
        return _error(
            call.span,
            "all takes its test in the body",
            f"count the exceptions: `n = sum(1 for {binder} in group if q and not "
            "p)`, then `having n == 0`",
        )
    if len(generator.source) > 1:
        return _error(
            generator.source_span,
            f"A generator over {source} reads a row's collected list, which "
            "only a project collects",
            "`sum` and `any` read a collected list in a project whose "
            "pietto.toml sets `schema_version = 2`",
        )
    lets = frozenset() if position is None else position.lets
    if position is not None:
        relations = relations | position.inputs
    if source == GROUP_SOURCE and source in lets:
        return _error(
            generator.source_span,
            f"Generator over group in {name}: group is the let group, not this group",
            "rename the let group to read this group's rows",
        )
    if source == GROUP_SOURCE and source in relations:
        return _error(
            generator.source_span,
            f"Generator over group in {name}: group is the relation group, not this "
            "group",
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
        return _error(
            generator.source_span,
            f"Generator over {source} in {name}: {source} is the whole relation, "
            "not this group",
            f"for this group's rows write `for {binder} in group`; all over a whole "
            "relation is not available"
            if name == "all"
            else f"for this group's rows write `for {binder} in group`"
            if position is None or _grouped(position)
            else "count per key in a grouped query and join it on the key",
        )
    if position is None or position.context not in {"select", "nested"}:
        context = "this position" if position is None else position.context
        refused = invalid_context_diagnostic(call, context=context)
        if (
            context in {"having clause", "order by"}
            and name in GROUP_TEST_AGGREGATE_NAMES
        ):
            hint = group_test_hint(binder, name)
        elif context in {"having clause", "order by"}:
            return refused
        else:
            hint = BEFORE_GROUPS_HINT
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
            f"{name}(... for {binder} in group ...) over JOIN rows is not available "
            "yet",
            "join in one query, then group it in another that reads it with `from`",
        )
    # The body of a test of the group is its test.
    return (
        None
        if name in GROUP_TEST_AGGREGATE_NAMES
        else _body_diagnostic(call, generator)
    ) or _read_diagnostic(generator, _keys(position.body), position.lets)


def _grouped(position: _Position | None) -> bool:
    """Whether the body reads its input as groups: GROUP BY, or every SELECT
    item an aggregate."""

    return position is not None and (
        position.body.group_by_clause is not None
        or all(
            semantic_aggregate_call_name(item.expression) is not None
            for item in position.body.select_items
        )
    )


def _list_diagnostic(
    call: ast.CallExpr, generator: ast.GeneratorExpr, known: set[str]
) -> Diagnostic | None:
    """The first rule a generator over a row's collected list ``c.xs``
    breaks: only `sum` and `any` take one, `any` takes its test in the body,
    a `sum` adds 1 under an `if` or one field ``o.f``, and the body and test
    read only the element ``o``. Where it is written, its types and the
    source field are the project checks' (a read of the field outside a
    SELECT item stays PIE-S2805)."""

    from pietto.semantic.expressions import (
        _unknown_function_diagnostic,
        is_unknown_function_call,
    )

    name = callee_name(call)
    binder = generator.binding_name
    source = ".".join(generator.source)
    if name not in {"sum", "any"}:
        if is_unknown_function_call(call) and name not in known:
            return _unknown_function_diagnostic(call, name)
        hint = (
            f"count the matching elements with `sum(1 for {binder} in {source} if ...)`"
            if name == "count" and generator.condition is not None
            else f"count the list with `len({source})`"
            if name in {"count", "len"}
            else "`sum` and `any` take a list generator"
        )
        if name in {"count", "len"}:
            return _error(call.span, f"{name} takes no generator", hint)
        if name in GROUP_TEST_AGGREGATE_NAMES:
            # `all` tests the rows of a group, never a list.
            return _error(call.span, f"{name} takes no list generator", hint)
        if name in SEMANTIC_AGGREGATE_NAMES:
            return _error(
                call.span,
                f"{name} takes no generator; a list {name} is not available",
                hint,
            )
        return _error(call.span, "A generator is only the argument of sum or any", hint)
    if name == "any" and generator.condition is not None:
        return _error(
            call.span,
            "any takes its test in the body",
            f"write `any(q for {binder} in {source})`"
            if type(generator.body) is ast.LiteralExpr and generator.body.value is True
            else f"write `any(p and q for {binder} in {source})`",
        )
    body = generator.body
    if name == "sum":
        if (
            type(body) is ast.LiteralExpr
            and type(body.value) is int
            and body.value == 1
        ):
            if generator.condition is None:
                return _error(
                    call.span,
                    f"sum(1 for {binder} in {source}) counts every element",
                    f"write `len({source})`",
                )
        elif not (type(body) is ast.DottedNameExpr and body.parts[0] == binder):
            hint = None
            if type(body) is ast.ConditionalExpr:
                hint = (
                    f"filter with `if` after the source: "
                    f"`sum({binder}.f for {binder} in {source} if ...)`"
                )
            elif type(body) is ast.NameExpr:
                hint = f"read the element as `{binder}.{body.name}`"
            return _diagnostic(
                "PIE-S2315",
                call.span,
                f"sum of a list adds 1 or one field of {binder}; expression "
                "bodies are not supported yet",
                hint,
            )
    return _read_diagnostic(generator, frozenset(), frozenset())


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
    key field or a parameter. A group's member is the input row, so such a
    read names its member field; a list's element is another row, whose
    fields are not known here."""

    from pietto.semantic.inline_functions import _tree_nodes

    binder = generator.binding_name
    outside = (
        None
        if generator.source_read is None
        else f"read the element's fields as `{binder}.f` and the row's values "
        "outside the generator"
    )
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
            if read in lets:
                # A computed GROUP BY key too: an aggregate argument reads a
                # let only as the whole argument, and `o.<let>` is no member
                # field (PIE-S2102 below).
                return _error(
                    node.span,
                    f"Generator reads the let {read} outside its member",
                    f"write the let's expression over fields of {binder}, "
                    f"such as `{binder}.f`",
                )
            if read not in keys:
                return _error(
                    node.span,
                    f"Generator reads {read} outside its member",
                    outside or f"write `{binder}.{read}`",
                )
        if type(node) is ast.DottedNameExpr:
            parts = cast(ast.DottedNameExpr, node).parts
            if parts[0] != binder:
                return _error(
                    node.span,
                    f"Generator reads {'.'.join(parts)} outside its member",
                    outside or f"write `{binder}.{parts[-1]}`",
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
