"""Pure inline ``def`` functions: checked at the definition, inlined at calls.

A call ``f(a, b)`` is replaced by ``f``'s body with each parameter replaced by
its argument, before any call site is typed, so every later reader sees only
ordinary expressions and the SQL equals that of the call written out by hand.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import fields, is_dataclass, replace
from types import MappingProxyType
from typing import NamedTuple, cast

from pietto._inline_argument import InlinedArgument
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
    LimitClause,
    ModuleDeclarationKind,
    NamedWindowDeclaration,
    NameExpr,
    Node,
    Nullability,
    QueryDef,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    RelationshipMetadata,
    Script,
    SelectBody,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    TableFunctionFromClause,
    TypeArgument,
    TypeDef,
    TypeExpr,
    ValuesBody,
    WindowExpr,
    inlined_arguments,
    with_inlined_argument,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    SEMANTIC_AGGREGATE_NAMES,
    semantic_aggregate_call_name,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS, SPECIAL_BUILTIN_FUNCTION_NAMES
from pietto.semantic.expressions import always_null, infer_row_expression
from pietto.semantic.window_semantics import WINDOW_FUNCTION_NAMES
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
        *WINDOW_FUNCTION_NAMES,
        "generate_series",
    }
)
# One expansion, with its arguments, has at most this many expression nodes
# and this nesting depth.
_MAX_EXPANSION_NODES = 1000
_MAX_EXPANSION_DEPTH = 64
# Positions whose hand-written form is a literal, a field or a window call
# that Pietto checks by its own rule; a def call there is refused.
_REFUSED_POSITIONS: MappingProxyType[type[Node], str] = MappingProxyType(
    {
        WindowExpr: "in a window computation",
        NamedWindowDeclaration: "in a window computation",
        TableFunctionFromClause: "in a table-function input",
        LimitClause: "in LIMIT",
        ValuesBody: "in a VALUES row",
        RelationshipMetadata: "in a relationship condition",
        SourceDef: "in a source connector",
        TypeArgument: "in a type argument",
    }
)
_AS_TABLE_FUNCTION = "as a table function"
_RELATION_READS = (RelationExistsExpr, RelationScalarExpr, RelationMembershipExpr)
_NULLABILITY = MappingProxyType(
    {
        Nullability.NOT_NULL: EffectiveNullability.NON_NULL,
        Nullability.NULLABLE: EffectiveNullability.NULLABLE,
    }
)


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
    aliases = _scalar_aliases(script)
    for function in defined.values():
        found.extend(_signature_diagnostics(function, shapes, aliases))
        found.extend(_body_form_diagnostics(function))
    found.extend(_recursion_diagnostics(defined))
    # A def body is walked as its expansion is, so a call in a type argument
    # is refused there too.
    found.extend(
        _position_diagnostics(
            tuple(function.body for function in defined.values()), defined
        )
    )
    if found:
        return script, _ordered(found)
    # A def reads each alias in its signature as the type it expands to.
    defined = {
        name: _with_alias_bases(function, aliases) for name, function in defined.items()
    }

    templates: dict[str, tuple[Expression, _Size]] = {}
    occurrences = itertools.count(1)
    for function in _callee_order(defined):
        expansion = _Expansion(defined, templates, found, occurrences)
        body = expansion.expand(function.body)
        if expansion.failed:
            continue
        size = _measure(body)
        if size.nodes > _MAX_EXPANSION_NODES or size.depth > _MAX_EXPANSION_DEPTH:
            found.append(_size_diagnostic(function, size.nodes, size.depth, body.span))
            continue
        before = len(found)
        _check_body(function, body, found)
        if len(found) == before:
            # Measured once here, not at every call.
            templates[function.name] = (body, size)
    if found:
        return script, _ordered(found)
    if len(templates) != len(defined):
        # A def without a template reported why above; none is dropped
        # unchecked.
        raise AssertionError("Every def is checked before it is inlined.")
    others = tuple(item for item in script.definitions if type(item) is not FunctionDef)
    found.extend(_position_diagnostics((*others, *script.relationships), defined))
    if found:
        return script, _ordered(found)

    expansion = _Expansion(defined, templates, found, occurrences)
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


def drop_repeated_call_diagnostics(
    script: Script, diagnostics: Sequence[Diagnostic]
) -> tuple[Diagnostic, ...]:
    """Keep only the first of equal diagnostics located in a def call.

    ``script`` is the parsed script. Its expansion types the body at the call
    and each use of an argument at the argument's own text, so one written
    call can report one error more than once: in an argument the body uses n
    times, or in body nodes that its arguments make fail alike. That text is
    written once, so each such error is reported once. Dropping repeats after
    typing, not during it, keeps every copy's error in view of the rule that
    does not check an argument with an error of its own against its parameter.
    A repeat outside a call stays.

    ``diagnostics`` are in source order within each file, as analysis returns
    them, so one pass over each file's calls in source order places them all.
    """

    if len(set(diagnostics)) == len(diagnostics):
        return tuple(diagnostics)
    defined = {
        item.name: item for item in script.definitions if type(item) is FunctionDef
    }
    # The text of each outermost call, in source order; calls do not overlap.
    ranges: dict[str | None, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
    pending: list[object] = [script]
    while pending:
        value = pending.pop()
        if _def_call_name(value, defined) is None:
            pending.extend(reversed(_in_text_order(value)))
            continue
        span = cast(CallExpr, value).span
        ranges.setdefault(span.path, []).append(
            ((span.line, span.column), (span.end_line, span.end_column))
        )
    # Per file, the first call that does not end before the last diagnostic.
    passed: dict[str | None, int] = {}
    seen: set[Diagnostic] = set()
    kept: list[Diagnostic] = []
    for diagnostic in diagnostics:
        location = diagnostic.location
        spans = ranges.get(location.path, [])
        at = (location.line, location.column)
        index = passed.get(location.path, 0)
        while index < len(spans) and spans[index][1] <= at:
            index += 1
        passed[location.path] = index
        if diagnostic in seen and index < len(spans) and spans[index][0] <= at:
            continue
        seen.add(diagnostic)
        kept.append(diagnostic)
    return tuple(kept)


def _in_text_order(value: object) -> tuple[object, ...]:
    """The AST values below ``value`` in the order of their text: a tuple's
    items as written, and a node's fields by where their text starts. A field
    without text holds no call and is left out. Only a script's fields
    interleave, and of them only its definitions hold calls once analysis
    runs: a call in a relationship is PIE-S2397 before it."""

    children = _children(value) or ()
    if type(value) is tuple:
        return children
    starts = [
        (start, child)
        for child in children
        if (start := _text_start(child)) is not None
    ]
    # A node has a fixed number of fields, so sorting them is constant work.
    return tuple(child for _, child in sorted(starts, key=lambda item: item[0]))


def _text_start(value: object) -> tuple[int, int] | None:
    """Where the first node in ``value`` starts, if it holds one."""

    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, Node):
            return (item.span.line, item.span.column)
        pending.extend(reversed(_children(item) or ()))
    return None


class _Expansion:
    """Replace each call to a checked ``def`` by its body, bottom up."""

    def __init__(
        self,
        defined: dict[str, FunctionDef],
        templates: dict[str, tuple[Expression, _Size]],
        found: list[Diagnostic],
        occurrences: Iterator[int],
    ) -> None:
        self.defined = defined
        self.templates = templates
        self.found = found
        self.occurrences = occurrences
        self.failed = False
        # Each node that is or holds a call left unexpanded, kept alive so
        # its id stays its own; a parent is marked from its children alone.
        self.unexpanded: dict[int, object] = {}

    def expand(self, expression: Expression) -> Expression:
        return cast(Expression, self.expand_tree(expression))

    def expand_tree(self, value: object) -> object:
        return _rebuild(value, self._visit)

    def _visit(self, original: object, rebuilt: object) -> object:
        result = self._expand_call(original, rebuilt)
        if result is rebuilt and self._holds_unexpanded(rebuilt):
            self.unexpanded[id(rebuilt)] = rebuilt
        return result

    def _holds_unexpanded(self, node: object) -> bool:
        pending = list(_children(node) or ())
        while pending:
            value = pending.pop()
            if type(value) is tuple:
                pending.extend(cast(tuple[object, ...], value))
            elif id(value) in self.unexpanded:
                return True
        return False

    def _refuse(self, call: CallExpr) -> CallExpr:
        self.failed = True
        self.unexpanded[id(call)] = call
        return call

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
        checked = self.templates.get(function.name)
        if checked is None:
            # The callee failed its own checks, which reported it.
            return self._refuse(call)
        template, size = checked
        if any(id(argument) in self.unexpanded for argument in call.arguments):
            # An inner call failed and reported why.
            return self._refuse(call)
        if len(call.arguments) != len(function.parameters):
            self._refuse(call)
            self.found.append(
                _diagnostic(
                    "PIE-S2395",
                    f"Invalid arguments for def {function.name}: expected "
                    f"{len(function.parameters)}, got {len(call.arguments)}",
                    call.span,
                )
            )
            return call
        reads = [
            (position, parameter)
            for position, (parameter, argument) in enumerate(
                zip(function.parameters, call.arguments), start=1
            )
            if any(type(node) in _RELATION_READS for node in _tree_nodes(argument))
        ]
        if reads:
            # A relation read's SQL alias follows its source position, which
            # a body that repeats or reorders its parameters would change.
            self._refuse(call)
            self.found.extend(
                _diagnostic(
                    "PIE-S2395",
                    f"Invalid argument for def {function.name} at position "
                    f"{position} ({parameter.name}): an argument cannot read a "
                    "relation (exists, scalar or in) yet",
                    call.span,
                )
                for position, parameter in reads
            )
            return call
        # Each argument carries the parameter it must fit, so wherever its
        # expansion is typed, the argument is checked against it.
        arguments = {
            parameter.name: with_inlined_argument(
                argument,
                InlinedArgument(
                    call=call.span,
                    function=function.name,
                    position=position,
                    parameter=parameter.name,
                    type_name=parameter.type.name,
                    nullable=parameter.type.nullability is Nullability.NULLABLE,
                ),
            )
            for position, (parameter, argument) in enumerate(
                zip(function.parameters, call.arguments), start=1
            )
        }
        nodes, depth = size.nodes, size.depth
        for name, argument in arguments.items():
            uses, deepest = size.names.get(name, (0, 0))
            argument_size = _measure(argument)
            nodes += uses * (argument_size.nodes - 1)
            depth = max(depth, deepest + argument_size.depth - 1)
        if nodes > _MAX_EXPANSION_NODES or depth > _MAX_EXPANSION_DEPTH:
            self._refuse(call)
            self.found.append(_size_diagnostic(function, nodes, depth, call.span))
            return call
        return cast(
            Expression,
            _rebuild(
                template,
                _substitution(arguments, template, call.span, self.occurrences),
            ),
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
    arguments: dict[str, Expression],
    template: Expression,
    call: Span,
    occurrences: Iterator[int],
) -> Callable[[object, object], object]:
    """Put each argument in place of its parameter.

    Every node keeps a real location: the expansion and every other body node
    are at the call, and an argument, also when the body uses it again, is at
    its own text. A copy differs from the original only in an internal span
    ``occurrence``, as the same text written out twice by hand would differ in
    position. Every use of an argument, and every node inside it, carries the
    parameters it must fit, so a mismatch leaves each use Unknown and the
    expansion reports nothing else.
    """

    used: set[str] = set()

    def occurrence(node: object, span: Span) -> object:
        return replace(
            cast(Node, node), span=replace(span, occurrence=next(occurrences))
        )

    def copied(original: object, copy: object) -> object:
        # Window frames and their bounds are AST values without a span.
        if not isinstance(copy, Node):
            return copy
        new = occurrence(copy, copy.span)
        if isinstance(new, Expression):
            # An inner call's argument keeps the parameter it must fit.
            for slot in inlined_arguments(cast(Expression, original)):
                new = with_inlined_argument(new, slot)
        return new

    def substitute(original: object, rebuilt: object) -> object:
        if type(original) is NameExpr:
            name = cast(NameExpr, original).name
            argument = arguments.get(name)
            if argument is not None:
                if name not in used:
                    used.add(name)
                    return argument
                return _rebuild(argument, copied)
        if original is template and isinstance(rebuilt, Expression):
            return replace(rebuilt, span=call)
        return occurrence(rebuilt, call) if isinstance(rebuilt, Node) else rebuilt

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
                    name: new
                    for name, new, old in zip(
                        _child_names(value), rebuilt_children, children
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
    return tuple(getattr(value, name) for name in _child_names(value))


def _child_names(value: object) -> tuple[str, ...]:
    """A node's fields, except a call's callee: a name that is called is
    never a value, so a parameter of the same name does not replace it."""

    return tuple(
        item.name
        for item in fields(cast(Node, value))
        if type(value) is not CallExpr or item.name != "callee"
    )


def _tree_nodes(root: object) -> list[object]:
    """``root`` and every AST node below it that ``_rebuild`` visits, in
    source order: a cast's type arguments and a window's specification too."""

    found: list[object] = []
    pending = [root]
    while pending:
        value = pending.pop()
        children = _children(value)
        if children is None:
            continue
        if type(value) is not tuple:
            found.append(value)
        pending.extend(reversed(children))
    return found


def _def_call_name(node: object, defined: dict[str, FunctionDef]) -> str | None:
    if type(node) is not CallExpr or type(cast(CallExpr, node).callee) is not NameExpr:
        return None
    name = cast(NameExpr, cast(CallExpr, node).callee).name
    return name if name in defined else None


class _Size(NamedTuple):
    """An expression's node count and nesting depth (the root is 1), and for
    each name it reads, how often and at the deepest level."""

    nodes: int
    depth: int
    names: dict[str, tuple[int, int]]


def _measure(expression: Expression) -> _Size:
    nodes = depth = 0
    names: dict[str, tuple[int, int]] = {}
    pending = [(expression, 1)]
    while pending:
        node, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        if type(node) is NameExpr:
            uses, deepest = names.get(cast(NameExpr, node).name, (0, 0))
            names[cast(NameExpr, node).name] = (uses + 1, max(deepest, level))
        pending.extend((child, level + 1) for child in _expression_children(node))
    return _Size(nodes, depth, names)


def _expression_children(node: Expression) -> list[Expression]:
    """The nearest expressions below ``node`` that ``_rebuild`` visits: its
    operands, and also a cast's type arguments and a window call's arguments
    and specification, so a window counts at its full size."""

    found: list[Expression] = []
    pending = list(reversed(_children(node) or ()))
    while pending:
        value = pending.pop()
        if isinstance(value, Expression):
            found.append(value)
        elif (children := _children(value)) is not None:
            pending.extend(reversed(children))
    return found


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


def _scalar_aliases(script: Script) -> dict[str, str]:
    """Each type alias declared once in the file, and not named by an import,
    whose chain of such aliases ends at a def scalar type, with that type. No
    alias in the chain has type arguments or an ``ensure``."""

    counts: dict[str, int] = {}
    for definition in script.definitions:
        if type(definition) is TypeDef:
            name = cast(TypeDef, definition).name
            counts[name] = counts.get(name, 0) + 1
    imported = {
        item.local_name or item.exported_name
        for statement in script.module_statements
        if type(statement) is ImportStatement
        for item in statement.items
    }
    aliases = {
        definition.name: definition
        for definition in script.definitions
        if type(definition) is TypeDef
        and counts[definition.name] == 1
        and definition.name not in imported
    }
    # Each alias is walked once: a chain stops at an alias already decided.
    decided: dict[str, str | None] = {}
    for name in aliases:
        chain: dict[str, None] = {}
        current: str | None = name
        while current in aliases and current not in decided and current not in chain:
            chain[current] = None
            alias = aliases[current]
            current = None if alias.ensures or alias.base.arguments else alias.base.name
        if current is None or current in chain:
            base = None
        elif current in decided:
            base = decided[current]
        else:
            base = current if current in _SCALAR_TYPES else None
        decided.update(dict.fromkeys(chain, base))
    return {name: base for name, base in decided.items() if base is not None}


def _with_alias_bases(function: FunctionDef, aliases: dict[str, str]) -> FunctionDef:
    def base(type_expr: TypeExpr) -> TypeExpr:
        name = aliases.get(type_expr.name)
        return type_expr if name is None else replace(type_expr, name=name)

    return replace(
        function,
        parameters=tuple(
            replace(parameter, type=base(parameter.type))
            for parameter in function.parameters
        ),
        return_type=base(function.return_type),
    )


def _signature_diagnostics(
    function: FunctionDef, shapes: frozenset[str], aliases: dict[str, str]
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
                function,
                parameter.type,
                f"parameter {parameter.name}",
                shapes,
                aliases,
            )
        )
    found.extend(
        _type_diagnostics(function, function.return_type, "result", shapes, aliases)
    )
    return found


def _type_diagnostics(
    function: FunctionDef,
    type_expr: TypeExpr,
    role: str,
    shapes: frozenset[str],
    aliases: dict[str, str],
) -> list[Diagnostic]:
    if (
        type_expr.name in _SCALAR_TYPES or type_expr.name in aliases
    ) and not type_expr.arguments:
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
            f"{_SCALAR_TYPES[-1]}, without arguments, or an alias of one declared "
            "in this file without arguments or `ensure`"
        )
    return [_diagnostic("PIE-S2397", message, type_expr.span)]


def _body_form_diagnostics(function: FunctionDef) -> list[Diagnostic]:
    """A def body is one scalar expression over its parameters; every
    parameter appears in it, so every argument is checked at its call."""

    found: list[Diagnostic] = []
    used: set[str] = set()
    # Every node the expansion visits, a cast's type arguments among them.
    for node in _tree_nodes(function.body):
        if not isinstance(node, Expression):
            continue
        form = None
        if type(node) is NameExpr:
            used.add(cast(NameExpr, node).name)
        elif type(node) is DottedNameExpr:
            form = f"the qualified name {'.'.join(cast(DottedNameExpr, node).parts)}"
        elif (name := semantic_aggregate_call_name(node)) is not None:
            form = f"the aggregate {name}"
        # A window call cannot be written in a body (PIE-P1000), and the
        # admission gate refuses a relation read there (PIE-S2348 to PIE-S2350).
        if form is not None:
            found.append(
                _diagnostic(
                    "PIE-S2397",
                    f"Def {function.name} body uses {form}; a def body reads "
                    "only its parameters and calls scalar functions",
                    node.span,
                )
            )
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


def _position_diagnostics(
    roots: tuple[object, ...], defined: dict[str, FunctionDef]
) -> list[Diagnostic]:
    """Refuse a def call where the hand-written form must be a literal, a
    field or a window call, which Pietto checks by a rule of its own: inside
    a window computation, as a table function or in its input, LIMIT, a VALUES
    row, a relationship condition, a source connector, a type argument, and
    the ORDER BY of a grouped relation. The innermost such position names the
    refusal."""

    found: list[Diagnostic] = []
    pending: list[tuple[object, str | None]] = [(root, None) for root in roots]
    while pending:
        value, position = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend((item, position) for item in cast(tuple[object, ...], value))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        position = _REFUSED_POSITIONS.get(cast(type[Node], kind)) or position
        if position is not None and (name := _def_call_name(value, defined)):
            found.append(
                _diagnostic(
                    "PIE-S2397",
                    f"A def call is not available {position}: {name}",
                    cast(CallExpr, value).span,
                )
            )
            continue
        if position == _AS_TABLE_FUNCTION:
            # The table function's own arguments are its input.
            position = _REFUSED_POSITIONS[TableFunctionFromClause]
        for name in _child_names(value):
            child = getattr(value, name)
            if kind is TableFunctionFromClause and name == "call":
                label = _AS_TABLE_FUNCTION
            elif (
                name == "order_by_clause"
                and kind in (TableDef, QueryDef, SelectBody)
                and cast(TableDef, value).group_by_clause is not None
            ):
                label = "in the ORDER BY of a grouped relation"
            else:
                label = position
            pending.append((child, label))
    return found


def _calls(function: FunctionDef, defined: dict[str, FunctionDef]) -> list[str]:
    """The defs ``function`` calls, in body source order, once each."""

    callees: dict[str, None] = {}
    for node in _tree_nodes(function.body):
        if (name := _def_call_name(node, defined)) is not None:
            callees[name] = None
    return list(callees)


def _recursion_diagnostics(defined: dict[str, FunctionDef]) -> list[Diagnostic]:
    """One error per recursive group of defs, at its first def in source
    order, naming a shortest call path from it back to itself."""

    edges = {name: _calls(function, defined) for name, function in defined.items()}
    source_order = {name: position for position, name in enumerate(defined)}
    found: list[Diagnostic] = []
    for group in _call_groups(edges):
        name = min(group, key=source_order.__getitem__)
        if len(group) == 1 and name not in edges[name]:
            continue
        path = _shortest_cycle(name, edges, group)
        found.append(
            _diagnostic(
                "PIE-S2396",
                f"Recursive def calls are not available: {' -> '.join(path)}",
                defined[name].span,
            )
        )
    return found


def _call_groups(edges: dict[str, list[str]]) -> list[set[str]]:
    """The strongly connected groups of the call graph, by one iterative
    Tarjan pass: each def and each call is visited once, so a long chain of
    defs costs no more than its length."""

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    groups: list[set[str]] = []
    for root in edges:
        if root in index:
            continue
        work = [(root, 0)]
        while work:
            name, position = work[-1]
            if position == 0:
                index[name] = low[name] = len(index)
                stack.append(name)
                on_stack.add(name)
            callees = edges[name]
            if position < len(callees):
                work[-1] = (name, position + 1)
                callee = callees[position]
                if callee not in index:
                    work.append((callee, 0))
                elif callee in on_stack:
                    low[name] = min(low[name], index[callee])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[name])
            if low[name] == index[name]:
                group: set[str] = set()
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    group.add(member)
                    if member == name:
                        break
                groups.append(group)
    return groups


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
    """Type the expanded body over the declared parameters. Its canonical type
    is the declared result type, and it is never null when that says so. A
    body that is always null fits only a nullable result; a body whose type
    stays unknown without an error fits none."""

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
    if len(found) != before:
        return
    expected = _value_type(function.return_type)
    if actual.kind is ValueTypeKind.UNKNOWN:
        if not always_null(body):
            message = (
                f"Def {function.name} body type is not known, so it cannot "
                f"match declared return type {expected.resolved_type.name}"
            )
        elif expected.nullability is EffectiveNullability.NON_NULL:
            message = (
                f"Def {function.name} body is always null, but its declared "
                "return type is not null"
            )
        else:
            return
    elif (
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
