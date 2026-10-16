"""Pure inline ``def`` functions: checked at the definition, inlined at calls.

A call ``f(a, b)`` is replaced by ``f``'s body with each parameter replaced by
its argument, before any call site is typed, so every later reader sees only
ordinary expressions and the SQL equals that of the call written out by hand.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable
from dataclasses import fields, is_dataclass, replace
from typing import cast

from pietto._syntax_admission import source_order
from pietto.ast_nodes import (
    CallExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    Expression,
    FunctionDef,
    ImportStatement,
    ModuleDeclarationKind,
    NameExpr,
    Node,
    Nullability,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    RelationshipMetadata,
    Script,
    ShapeDef,
    Span,
    TypeExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    SEMANTIC_AGGREGATE_NAMES,
    child_expressions,
    semantic_aggregate_call_name,
)
from pietto.semantic.capability_windows import _WINDOW_IDENTITIES
from pietto.semantic.catalog import BUILTIN_FUNCTIONS, SPECIAL_BUILTIN_FUNCTION_NAMES
from pietto.semantic.expressions import (
    InlinedArgument,
    infer_row_expression,
    register_inlined_argument,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

__all__: tuple[str, ...] = ()

# A def parameter or result is exactly one of these builtin scalars.
_SCALAR_TYPES = ("Bool", "Int", "Float", "Decimal", "Text", "Date", "Timestamp", "UUID")
# Every name a call may already denote; a def never shadows one.
_RESERVED_NAMES = frozenset(
    {
        *BUILTIN_FUNCTIONS,
        *SPECIAL_BUILTIN_FUNCTION_NAMES,
        *SEMANTIC_AGGREGATE_NAMES,
        *_WINDOW_IDENTITIES,
        "generate_series",
    }
)
# One expansion, with its arguments, has at most this many expression nodes
# and this nesting depth.
_MAX_EXPANSION_NODES = 1000
_MAX_EXPANSION_DEPTH = 64
_NULLABILITY = {
    Nullability.NOT_NULL: EffectiveNullability.NON_NULL,
    Nullability.NULLABLE: EffectiveNullability.NULLABLE,
}


def inline_functions(script: Script) -> tuple[Script, tuple[Diagnostic, ...]]:
    """Check every ``def`` and replace every call to one by its expansion.

    The result drops the ``def`` declarations. A script without one is
    returned as is; any error leaves the script unusable for later readers.
    """

    if not any(type(item) is FunctionDef for item in script.definitions):
        return script, ()
    found: list[Diagnostic] = []
    callable_names: set[str] = set()
    defined: dict[str, FunctionDef] = {}
    for definition in script.definitions:
        if type(definition) not in (FunctionDef, ConstraintDef, DeriveDef):
            continue
        name = cast(FunctionDef | ConstraintDef | DeriveDef, definition).name
        if name in callable_names:
            found.append(
                _diagnostic(
                    "PIE-S2001",
                    f"Duplicate symbol name in callable namespace: {name}",
                    definition.span,
                )
            )
            continue
        callable_names.add(name)
        if type(definition) is FunctionDef:
            defined[name] = cast(FunctionDef, definition)
    shapes = _shape_names(script)
    for function in defined.values():
        found.extend(_signature_diagnostics(function, shapes))
        found.extend(_body_form_diagnostics(function))
    found.extend(_recursion_diagnostics(defined))
    if found:
        return script, _ordered(found)

    templates: dict[str, Expression] = {}
    for function in _callee_order(defined):
        expansion = _Expansion(defined, templates, found)
        body = expansion.expand(function.body)
        if expansion.failed:
            continue
        nodes, depth = _measure(body)
        if nodes > _MAX_EXPANSION_NODES or depth > _MAX_EXPANSION_DEPTH:
            found.append(_size_diagnostic(function, nodes, depth, body.span))
            continue
        before = len(found)
        _check_body(function, body, found)
        if len(found) == before:
            templates[function.name] = body
    if found:
        return script, _ordered(found)

    expansion = _Expansion(defined, templates, found)
    definitions = tuple(
        cast(Definition, expansion.expand_tree(item))
        for item in script.definitions
        if type(item) is not FunctionDef
    )
    relationships = cast(
        tuple[RelationshipMetadata, ...], expansion.expand_tree(script.relationships)
    )
    if found:
        return script, _ordered(found)
    return replace(script, definitions=definitions, relationships=relationships), ()


class _Expansion:
    """Replace each call to a checked ``def`` by its body, bottom up."""

    def __init__(
        self,
        defined: dict[str, FunctionDef],
        templates: dict[str, Expression],
        found: list[Diagnostic],
    ) -> None:
        self.defined = defined
        self.templates = templates
        self.found = found
        self.failed = False

    def expand(self, expression: Expression) -> Expression:
        return cast(Expression, self.expand_tree(expression))

    def expand_tree(self, value: object) -> object:
        return _rebuild(value, self._expand_call)

    def _expand_call(self, original: object, rebuilt: object) -> object:
        if (
            type(rebuilt) is not CallExpr
            or type(cast(CallExpr, rebuilt).callee) is not NameExpr
        ):
            return rebuilt
        call = cast(CallExpr, rebuilt)
        function = self.defined.get(cast(NameExpr, call.callee).name)
        if function is None:
            return rebuilt
        template = self.templates.get(function.name)
        if template is None:
            # The callee failed its own checks, which reported it.
            self.failed = True
            return rebuilt
        if any(self._unexpanded(argument) for argument in call.arguments):
            # An inner call failed and reported why.
            self.failed = True
            return rebuilt
        if len(call.arguments) != len(function.parameters):
            self.failed = True
            self.found.append(
                _diagnostic(
                    "PIE-S2395",
                    f"Invalid arguments for def {function.name}: expected "
                    f"{len(function.parameters)}, got {len(call.arguments)}",
                    call.span,
                )
            )
            return rebuilt
        arguments = dict(
            zip((parameter.name for parameter in function.parameters), call.arguments)
        )
        for position, parameter in enumerate(function.parameters, start=1):
            register_inlined_argument(
                arguments[parameter.name],
                InlinedArgument(
                    call=call.span,
                    function=function.name,
                    position=position,
                    parameter=parameter.name,
                    expected=_value_type(parameter.type),
                ),
            )
        nodes, depth = _measure(template)
        for name, argument in arguments.items():
            uses, deepest = _parameter_uses(template, name)
            argument_nodes, argument_depth = _measure(argument)
            nodes += uses * (argument_nodes - 1)
            depth = max(depth, deepest + argument_depth - 1)
        if nodes > _MAX_EXPANSION_NODES or depth > _MAX_EXPANSION_DEPTH:
            self.failed = True
            self.found.append(_size_diagnostic(function, nodes, depth, call.span))
            return rebuilt
        return cast(
            Expression,
            _rebuild(template, _substitution(arguments, template, call.span)),
        )

    def _unexpanded(self, expression: Expression) -> bool:
        return any(
            type(node) is CallExpr
            and type(cast(CallExpr, node).callee) is NameExpr
            and cast(NameExpr, cast(CallExpr, node).callee).name in self.defined
            for node in _nodes(expression)
        )


def _size_diagnostic(
    function: FunctionDef, nodes: int, depth: int, span: Span
) -> Diagnostic:
    return _diagnostic(
        "PIE-S2399",
        f"The expansion of def {function.name} has {nodes} expression nodes "
        f"nested {depth} deep; an expansion, with its arguments, has at most "
        f"{_MAX_EXPANSION_NODES} nodes nested at most {_MAX_EXPANSION_DEPTH} deep",
        span,
    )


def _substitution(
    arguments: dict[str, Expression], template: Expression, call: Span
) -> Callable[[object, object], object]:
    """Put each argument in place of its parameter.

    The expansion takes the call's span, so a finding in it is reported at the
    call. Every other body node, and every repeated use of an argument, is a
    copy that starts at the call and is as many columns long as its post-order
    ordinal: like the same text written out by hand, each inlined occurrence
    keeps a distinct identity.
    """

    used: set[str] = set()
    ordinal = itertools.count(1)

    def located(node: object) -> object:
        if not isinstance(node, Node):
            return node
        return replace(
            node,
            span=replace(
                call, end_line=call.line, end_column=call.column + next(ordinal)
            ),
        )

    def substitute(original: object, rebuilt: object) -> object:
        if type(original) is NameExpr:
            name = cast(NameExpr, original).name
            argument = arguments.get(name)
            if argument is not None:
                if name in used:
                    return _rebuild(argument, lambda _, copy: located(copy))
                used.add(name)
                return argument
        if original is template and isinstance(rebuilt, Node):
            return replace(rebuilt, span=call)
        return located(rebuilt)

    return substitute


def _rebuild(root: object, visit: Callable[[object, object], object]) -> object:
    """Rebuild an AST bottom up without recursion; ``visit(original, rebuilt)``
    may replace each AST value. Unchanged subtrees keep their identity."""

    done: list[object] = []
    pending: list[tuple[object, tuple[object, ...] | None]] = [(root, None)]
    while pending:
        value, children = pending.pop()
        if children is None:
            children = _children(value)
            if children is None:
                done.append(value)
                continue
            pending.append((value, children))
            pending.extend((child, None) for child in reversed(children))
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
                cast(Node, value),
                **{
                    item.name: new
                    for item, new, old in zip(
                        fields(cast(Node, value)), rebuilt_children, children
                    )
                    if new is not old
                },
            )
        done.append(visit(value, rebuilt) if type(value) is not tuple else rebuilt)
    (result,) = done
    return result


def _children(value: object) -> tuple[object, ...] | None:
    kind = type(value)
    if kind is tuple:
        return cast(tuple[object, ...], value)
    if kind is Span or kind.__module__ != "pietto.ast_nodes" or not is_dataclass(value):
        return None
    return tuple(getattr(value, item.name) for item in fields(cast(Node, value)))


def _parameter_uses(template: Expression, name: str) -> tuple[int, int]:
    """How often ``name`` is read, and the deepest level (the root is 1)."""

    uses = deepest = 0
    pending = [(template, 1)]
    while pending:
        node, level = pending.pop()
        if type(node) is NameExpr and cast(NameExpr, node).name == name:
            uses += 1
            deepest = max(deepest, level)
        pending.extend((child, level + 1) for child in child_expressions(node))
    return uses, deepest


def _nodes(expression: Expression) -> list[Expression]:
    found: list[Expression] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        found.append(node)
        pending.extend(child_expressions(node))
    return found


def _measure(expression: Expression) -> tuple[int, int]:
    nodes = depth = 0
    pending = [(expression, 1)]
    while pending:
        node, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        pending.extend((child, level + 1) for child in child_expressions(node))
    return nodes, depth


def _shape_names(script: Script) -> frozenset[str]:
    """Local shapes and imported shapes, which name row types."""

    return frozenset(
        {
            *(
                definition.name
                for definition in script.definitions
                if type(definition) is ShapeDef
            ),
            *(
                item.local_name or item.exported_name
                for statement in script.module_statements
                if type(statement) is ImportStatement
                for item in statement.items
                if item.declaration_kind is ModuleDeclarationKind.SHAPE
            ),
        }
    )


def _signature_diagnostics(
    function: FunctionDef, shapes: frozenset[str]
) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    if function.name in _RESERVED_NAMES:
        found.append(
            _diagnostic(
                "PIE-S2398",
                f"Def {function.name} has the name of a built-in function; "
                "a def cannot shadow one",
                function.span,
            )
        )
    seen: set[str] = set()
    for parameter in function.parameters:
        if parameter.name in seen:
            found.append(
                _diagnostic(
                    "PIE-S2001",
                    f"Duplicate parameter name in def {function.name}: "
                    f"{parameter.name}",
                    parameter.span,
                )
            )
        seen.add(parameter.name)
        found.extend(
            _type_diagnostics(
                function, parameter.type, f"parameter {parameter.name}", shapes
            )
        )
    found.extend(_type_diagnostics(function, function.return_type, "result", shapes))
    return found


def _type_diagnostics(
    function: FunctionDef, type_expr: TypeExpr, role: str, shapes: frozenset[str]
) -> list[Diagnostic]:
    if type_expr.name in _SCALAR_TYPES and not type_expr.arguments:
        return []
    if type_expr.name in shapes:
        message = (
            f"Def {function.name} {role} has row type {type_expr.name}; "
            "row-typed def parameters and results are not available yet"
        )
    else:
        written = f"{type_expr.name}(...)" if type_expr.arguments else type_expr.name
        message = (
            f"Def {function.name} {role} has type {written}; a def parameter "
            f"or result type is exactly {', '.join(_SCALAR_TYPES[:-1])} or "
            f"{_SCALAR_TYPES[-1]}, without arguments"
        )
    return [_diagnostic("PIE-S2397", message, type_expr.span)]


def _body_form_diagnostics(function: FunctionDef) -> list[Diagnostic]:
    """A def body is one scalar expression over its parameters; every
    parameter appears in it, so every argument is checked at its call."""

    found: list[Diagnostic] = []
    used: set[str] = set()
    pending: list[Expression] = [function.body]
    while pending:
        node = pending.pop()
        form = None
        if type(node) is NameExpr:
            used.add(cast(NameExpr, node).name)
        elif type(node) is DottedNameExpr:
            form = f"the qualified name {'.'.join(cast(DottedNameExpr, node).parts)}"
        elif (name := semantic_aggregate_call_name(node)) is not None:
            form = f"the aggregate {name}"
        elif type(node) is WindowExpr:
            form = "a window function"
        elif type(node) in (
            RelationExistsExpr,
            RelationScalarExpr,
            RelationMembershipExpr,
        ):
            form = "a relation read"
        if form is not None:
            found.append(
                _diagnostic(
                    "PIE-S2397",
                    f"Def {function.name} body uses {form}; a def body reads "
                    "only its parameters and calls scalar functions",
                    node.span,
                )
            )
        pending.extend(child_expressions(node))
    found.extend(
        _diagnostic(
            "PIE-S2397",
            f"Def {function.name} parameter {parameter.name} is not used in its "
            "body; every parameter must be used",
            parameter.span,
        )
        for parameter in function.parameters
        if parameter.name not in used
    )
    return found


def _calls(function: FunctionDef, defined: dict[str, FunctionDef]) -> list[str]:
    """The defs ``function`` calls, in body source order, once each."""

    callees: dict[str, None] = {}
    pending: list[Expression] = [function.body]
    while pending:
        node = pending.pop()
        if (
            type(node) is CallExpr
            and type(cast(CallExpr, node).callee) is NameExpr
            and cast(NameExpr, cast(CallExpr, node).callee).name in defined
        ):
            callees[cast(NameExpr, cast(CallExpr, node).callee).name] = None
        pending.extend(reversed(child_expressions(node)))
    return list(callees)


def _recursion_diagnostics(defined: dict[str, FunctionDef]) -> list[Diagnostic]:
    """One error per recursive group of defs, at its first def in source
    order, naming a shortest call path from it back to itself."""

    edges = {name: _calls(function, defined) for name, function in defined.items()}
    reach = {name: _reachable(name, edges) for name in defined}
    found: list[Diagnostic] = []
    cyclic: set[str] = set()
    for name in defined:
        if name in cyclic or name not in reach[name]:
            continue
        group = {other for other in reach[name] if name in reach[other]}
        cyclic.update(group)
        path = _shortest_cycle(name, edges, group)
        found.append(
            _diagnostic(
                "PIE-S2396",
                f"Recursive def calls are not available: {' -> '.join(path)}",
                defined[name].span,
            )
        )
    return found


def _reachable(start: str, edges: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    pending = list(edges[start])
    while pending:
        name = pending.pop()
        if name not in seen:
            seen.add(name)
            pending.extend(edges[name])
    return seen


def _shortest_cycle(
    start: str, edges: dict[str, list[str]], group: set[str]
) -> list[str]:
    previous: dict[str, str] = {}
    frontier = [start]
    while frontier:
        following: list[str] = []
        for name in frontier:
            for callee in edges[name]:
                if callee == start:
                    path = [start]
                    while name != start:
                        path.append(name)
                        name = previous[name]
                    return [start, *reversed(path[1:]), start]
                if callee in group and callee not in previous:
                    previous[callee] = name
                    following.append(callee)
        frontier = following
    raise AssertionError("A recursive def reaches itself.")


def _callee_order(defined: dict[str, FunctionDef]) -> list[FunctionDef]:
    """Every def after the defs it calls; otherwise in source order."""

    edges = {name: _calls(function, defined) for name, function in defined.items()}
    ordered: dict[str, None] = {}
    for root in defined:
        pending: list[tuple[str, bool]] = [(root, False)]
        while pending:
            name, ready = pending.pop()
            if name in ordered:
                continue
            if ready:
                ordered[name] = None
                continue
            pending.append((name, True))
            pending.extend((callee, False) for callee in reversed(edges[name]))
    return [defined[name] for name in ordered]


def _check_body(
    function: FunctionDef, body: Expression, found: list[Diagnostic]
) -> None:
    """Type the expanded body over the declared parameters; its canonical type
    is the declared result type, and it is never null when that says so."""

    schema = RowSchema(
        fields={
            parameter.name: RowField(
                name=parameter.name,
                resolved_type=ResolvedType(
                    name=parameter.type.name, kind=TypeKind.BUILTIN
                ),
                nullability=_NULLABILITY[parameter.type.nullability],
            )
            for parameter in function.parameters
        }
    )
    before = len(found)
    actual = infer_row_expression(body, schema, {}, found, report_unknown_name=True)
    if len(found) != before or actual.kind is ValueTypeKind.UNKNOWN:
        return
    expected = _value_type(function.return_type)
    if (
        actual.resolved_type.kind is not TypeKind.BUILTIN
        or actual.resolved_type.name != expected.resolved_type.name
    ):
        message = (
            f"Def {function.name} body type {actual.resolved_type.name} does not "
            f"match declared return type {expected.resolved_type.name}"
        )
    elif (
        expected.nullability is EffectiveNullability.NON_NULL
        and actual.nullability is not EffectiveNullability.NON_NULL
    ):
        message = (
            f"Def {function.name} body may be null, but its declared return "
            "type is not null"
        )
    else:
        return
    found.append(_diagnostic("PIE-S2402", message, function.body.span))


def _value_type(type_expr: TypeExpr) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=type_expr.name, kind=TypeKind.BUILTIN),
        nullability=_NULLABILITY[type_expr.nullability],
    )


def _ordered(found: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    return tuple(sorted(found, key=source_order))


def _diagnostic(code: str, message: str, span: Span) -> Diagnostic:
    return Diagnostic(
        code=code,
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
