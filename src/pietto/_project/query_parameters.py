"""Entry-query header parameters: declarations, positions and dependence.

A query header parameter is a named value bound at execution. A read, or a
let or output whose value depends on one, is admitted beneath scalar operators
and the value arguments of a closed set of scalar builtins in the row roles
(``let:``, ``where``, JOIN ``on``, an ungrouped SELECT list) and in the result
roles (SATISFYING, QUALIFY and ORDER BY keys). A grouped SELECT list admits a
dependent value only as a computed LET group key or as the one LET argument of
count, avg, min or max; a GROUP BY key only as a computed LET binding without
JOIN. Inside a window call of an ungrouped SELECT list a bare read is also
admitted as a value argument, a lag/lead default, or a structural count
(lag/lead offset, ntile bucket count, nth_value position); a count must be
declared ``Int``, not ``Int | None``. Every other position (LIMIT, other
window positions and frames, structural call arguments) is refused here before
semantic analysis. Each relation let of the entry query reads the header under
the same rules (Phase70 S11); no other declaration reads it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import TYPE_CHECKING, Any, cast

from pietto.ast_nodes import (
    AuthoredWindowFrame,
    BetweenExpr,
    BlockRelationDef,
    BinaryExpr,
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    FromClause,
    IsNullExpr,
    MembershipExpr,
    NameExpr,
    Node,
    Nullability,
    ParameterRefExpr,
    QueryDef,
    Script,
    SelectBody,
    SetRelationDef,
    Span,
    TableDef,
    UnaryExpr,
    WindowExpr,
    WindowFrameBound,
)
from pietto._syntax_admission import admitted_header
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import SEMANTIC_AGGREGATE_NAMES
from pietto.semantic.expressions import QUERY_PARAMETER_TYPES

if TYPE_CHECKING:
    from pietto._project.module_catalog import (
        ProjectDeclarationOccurrence,
        ProjectModuleCatalogSet,
    )
    from pietto._project.module_relation_resolution import (
        ProjectModuleRelationResolutionEnvironment,
        ProjectModuleRelationResolutionSet,
    )

__all__: tuple[str, ...] = ()

MAX_QUERY_PARAMETERS = 64
DECLARATION_CODE = "PIE-S2353"
COLLISION_CODE = "PIE-S2354"
POSITION_CODE = "PIE-S2355"
INPUT_CODE = "PIE-S2356"
COUNT_CODE = "PIE-S2358"
COUNT_MESSAGE = "A window count parameter must be declared Int, not Int | None."
COLLISION_MESSAGE = (
    "Query parameter name is also a field, let, relation, output or window name."
)
INPUT_MESSAGE = "A query with parameters cannot be the input of another relation."
_POSITION_MESSAGE = "Query parameters are not available in this position."
# Aggregates whose one LET argument may depend on a parameter: the LET site
# carries every binding obligation and the result law reads only its port.
_LET_AGGREGATES = frozenset({"count", "avg", "min", "max"})
# Scalar builtins and the argument positions that carry a value (None: all).
# Absent builtins and positions are structural or fixed-value (substr bounds,
# len, replace, matches, a starts_with/ends_with needle rendered twice).
_VALUE_ARGUMENTS: dict[str, tuple[int, ...] | None] = {
    "lower": (0,),
    "upper": (0,),
    "trim": (0,),
    "contains": (0, 1),
    "starts_with": (0,),
    "ends_with": (0,),
    "nullif": (0, 1),
    "coalesce": None,
    "sign": (0,),
}
# Operators a parameter value may pass through on its way to a row result.
_SCALAR_OPERATORS = (
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    IsNullExpr,
    BetweenExpr,
    ConditionalExpr,
    MembershipExpr,
    CastExpr,
)
# Window call argument positions a bare read may fill, by function identity:
# value arguments and lag/lead defaults, then the structural counts.
_WINDOW_VALUE_POSITIONS = {
    "lag": (0, 2),
    "lead": (0, 2),
    "first_value": (0,),
    "last_value": (0,),
    "nth_value": (0,),
}
_WINDOW_COUNT_POSITIONS = {"lag": 1, "lead": 1, "ntile": 0, "nth_value": 1}


def _window_parameter_arguments(
    window: WindowExpr,
) -> tuple[tuple[ParameterRefExpr, ...], tuple[ParameterRefExpr, ...]]:
    """The admitted bare reads of one window call: (value or default, counts)."""

    name = window.identity.name
    arguments = window.call.arguments

    def reads(positions: tuple[int, ...]) -> tuple[ParameterRefExpr, ...]:
        return tuple(
            cast(ParameterRefExpr, arguments[position])
            for position in positions
            if position < len(arguments)
            and type(arguments[position]) is ParameterRefExpr
        )

    count = _WINDOW_COUNT_POSITIONS.get(name)
    return (
        reads(_WINDOW_VALUE_POSITIONS.get(name, ())),
        reads(() if count is None else (count,)),
    )


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


def reads_header(owner: object, entry: object) -> bool:
    """Whether a relation-body owner reads the header of ``entry``: the entry
    query itself and each of its own relation lets (Phase70 S11)."""

    owner_ = cast("ProjectDeclarationOccurrence", owner)
    entry_ = cast("ProjectDeclarationOccurrence", entry)
    return owner_ is entry_ or (
        entry_.let_position is None
        and owner_.let_position is not None
        and owner_.identity.module_path == entry_.identity.module_path
        and owner_.module_position == entry_.module_position
        and owner_.declaration_position == entry_.declaration_position
    )


def _header_bodies(definition: object) -> tuple[QueryDef, ...]:
    """The entry query and each FROM-based relation let of it, every one as a
    query carrying the header, so a let reads it under the entry's rules."""

    if type(definition) is QueryDef and definition.parameters:
        return (definition,)
    if (
        type(definition) is not BlockRelationDef
        or not definition.parameters
        or not admitted_header(definition)
    ):
        # An unadmitted header reports only PIE-S2346.
        return ()
    from pietto._project.module_catalog import _SELECT_FIELDS

    block = cast(BlockRelationDef, definition)
    return tuple(
        QueryDef(
            span=span,
            name=name,
            parameters=block.parameters,
            **{item: getattr(body, item) for item in _SELECT_FIELDS},
        )
        for span, name, body in (
            (block.span, block.name, block.body),
            *((let.span, let.name, let.body) for let in block.let_relations),
        )
        if type(body) is SelectBody and type(body.from_clause) is FromClause
    )


def query_parameter_diagnostics(
    script: Script, *, position_diagnostics_out: list[Diagnostic] | None = None
) -> tuple[Diagnostic, ...]:
    """Declaration and position errors of every entry-query header, sorted;
    the relation lets of an entry query follow the same position rules.

    The optional output retains the actual position occurrences for the caller
    that must recheck them after canonical query naming. Other header errors
    still stop that caller before normalization.
    """

    found: list[Diagnostic] = []
    for definition in script.definitions:
        bodies = _header_bodies(definition)
        if bodies:
            found.extend(_declaration_diagnostics(bodies[0]))
        for body in bodies:
            found.extend(
                _position_diagnostics(
                    body, position_diagnostics_out=position_diagnostics_out
                )
            )
            # An unaliased read would name its output after the parameter.
            found.extend(
                _diagnostic(COLLISION_CODE, COLLISION_MESSAGE, item.expression.span)
                for item in body.select_items
                if item.alias is None and type(item.expression) is ParameterRefExpr
            )
    return tuple(
        sorted(
            found,
            key=lambda item: (
                item.location.line,
                item.location.column,
                item.code,
                item.location.end_line or 0,
                item.location.end_column or 0,
            ),
        )
    )


def _declaration_diagnostics(definition: QueryDef) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    seen: set[str] = set()
    for ordinal, parameter in enumerate(definition.parameters):
        declared = parameter.type
        if ordinal >= MAX_QUERY_PARAMETERS:
            found.append(
                _diagnostic(
                    DECLARATION_CODE,
                    f"A query declares at most {MAX_QUERY_PARAMETERS} parameters.",
                    parameter.span,
                )
            )
        if declared.name not in QUERY_PARAMETER_TYPES or declared.arguments:
            found.append(
                _diagnostic(
                    DECLARATION_CODE,
                    "Query parameter type must be Bool, Int, Float or Text.",
                    parameter.span,
                )
            )
        if parameter.name in seen:
            found.append(
                _diagnostic(
                    "PIE-S2001",
                    f"Duplicate parameter name in query {definition.name}: "
                    f"{parameter.name}",
                    parameter.span,
                )
            )
        seen.add(parameter.name)
    return found


def _dependent_names(
    definition: QueryDef,
) -> tuple[frozenset[str], frozenset[str]]:
    """Let and output names whose value reads a parameter, directly or not.

    A row expression sees input fields and lets, never a SELECT output, so an
    output only taints the clauses that resolve output names.
    """

    lets: set[str] = set()
    if definition.let_clause is not None:
        for binding in definition.let_clause.bindings:
            if _reads(binding.expression, lets):
                lets.add(binding.name)
    outputs: set[str] = set()
    for item in definition.select_items:
        name = item.alias
        if name is None and type(item.expression) is NameExpr:
            name = cast(NameExpr, item.expression).name
        if name is not None and _reads(item.expression, lets):
            outputs.add(name)
    return frozenset(lets), frozenset(outputs)


def parameter_ordinals(definition: QueryDef, root: Node) -> frozenset[int]:
    """Ordinals of the parameters ``root`` reads, directly or through lets."""

    bindings = () if definition.let_clause is None else definition.let_clause.bindings
    found: set[int] = set()
    expanded: set[str] = set()
    pending: list[Node] = [root]
    while pending:
        for node in _value_nodes(pending.pop()):
            if type(node) is ParameterRefExpr:
                found.add(cast(ParameterRefExpr, node).ordinal)
            elif type(node) is NameExpr and cast(NameExpr, node).name not in expanded:
                name = cast(NameExpr, node).name
                expanded.add(name)
                pending.extend(b.expression for b in bindings if b.name == name)
    return frozenset(found)


def _reads(root: Node, dependent: set[str] | frozenset[str]) -> bool:
    return any(
        type(node) is ParameterRefExpr
        or (type(node) is NameExpr and cast(NameExpr, node).name in dependent)
        for node in _value_nodes(root)
    )


def _position_diagnostics(
    definition: QueryDef, *, position_diagnostics_out: list[Diagnostic] | None = None
) -> list[Diagnostic]:
    lets, outputs = _dependent_names(definition)
    grouped = (
        definition.group_by_clause is not None
        or definition.satisfying_clause is not None
        or any(
            type(item.expression) is not WindowExpr
            and any(
                type(node) is CallExpr
                and type(cast(CallExpr, node).callee) is NameExpr
                and cast(NameExpr, cast(CallExpr, node).callee).name
                in SEMANTIC_AGGREGATE_NAMES
                for node in _value_nodes(item.expression)
            )
            for item in definition.select_items
        )
    )
    bindings = () if definition.let_clause is None else definition.let_clause.bindings
    binding_by_name: dict[str, Node] = {}
    for binding in bindings:
        binding_by_name.setdefault(binding.name, binding.expression)
    admitted: list[Node] = [binding.expression for binding in bindings]
    refused: list[Node] = []
    # A computed LET group key reads only its LET port (JOIN keys: later).
    keys: set[str] = set()
    if definition.group_by_clause is not None:
        for item in definition.group_by_clause.items:
            key = item.key
            if (
                not definition.join_clauses
                and type(key) is NameExpr
                and key.name in binding_by_name
                and type(binding_by_name[key.name]) not in {NameExpr, DottedNameExpr}
            ):
                keys.add(key.name)
            else:
                refused.append(item)
    if definition.where_clause is not None:
        admitted.append(definition.where_clause.expression)
    admitted.extend(
        clause.on_clause.expression
        for clause in definition.join_clauses
        if clause.on_clause is not None
    )
    found: list[Diagnostic] = []
    windowed: set[int] = set()
    for item in definition.select_items:
        expression = item.expression
        if type(expression) is WindowExpr and not grouped:
            values, counts = _window_parameter_arguments(cast(WindowExpr, expression))
            windowed.update(id(read) for read in (*values, *counts))
            found.extend(
                _diagnostic(COUNT_CODE, COUNT_MESSAGE, read.span)
                for read in counts
                if read.type_name != "Int"
                or read.nullability is not Nullability.NOT_NULL
            )
        if type(expression) is WindowExpr:
            refused.append(expression)
        elif not grouped:
            admitted.append(expression)
        elif not (
            (type(expression) is NameExpr and cast(NameExpr, expression).name in keys)
            or _let_aggregate(expression)
        ):
            refused.append(expression)
    refused.extend(definition.named_windows)
    # SATISFYING, QUALIFY, ORDER BY and LIMIT also resolve SELECT output names,
    # so what they admit or refuse is checked against dependent outputs too.
    admitted_late: list[Node] = []
    late: list[Node] = []
    for clause in (definition.satisfying_clause, definition.qualify_clause):
        if clause is not None:
            admitted_late.append(clause.expression)
    if definition.order_by_clause is not None:
        for order in definition.order_by_clause.items:
            # A grouped ORDER key is a bare output name; an ungrouped one must
            # read a field, let or output (a constant key orders nothing).
            if (
                type(order.expression) is not NameExpr
                if grouped
                else not any(
                    type(node) in {NameExpr, DottedNameExpr}
                    for node in _value_nodes(order.expression)
                )
            ):
                late.append(order.expression)
            else:
                admitted_late.append(order.expression)
    if definition.limit_clause is not None:
        late.append(definition.limit_clause)

    # Beneath scalar operators and builtin value arguments a read stays
    # admitted; below any other expression (a window, a structural argument or
    # a relation read) it is refused.
    for roots, out in ((admitted, refused), (admitted_late, late)):
        for root in roots:
            pending: list[Node] = [root]
            while pending:
                node = pending.pop()
                if isinstance(node, _SCALAR_OPERATORS):
                    pending.extend(_children(node))
                elif type(node) is CallExpr:
                    call = cast(CallExpr, node)
                    if _let_aggregate(call):
                        continue
                    values = (
                        _VALUE_ARGUMENTS.get(cast(NameExpr, call.callee).name, ())
                        if type(call.callee) is NameExpr
                        else ()
                    )
                    for index, argument in enumerate(call.arguments):
                        if values is None or index in values:
                            pending.append(argument)
                        else:
                            out.append(argument)
                elif type(node) not in {ParameterRefExpr, NameExpr}:
                    out.extend(_children(node))
    # A GROUP BY key is a bare name, never rewritten to a read.
    names = lets | {parameter.name for parameter in definition.parameters}
    positions = [
        _diagnostic(POSITION_CODE, _POSITION_MESSAGE, node.span)
        for roots, visible in ((refused, names), (late, names | outputs))
        for root in roots
        for node in _value_nodes(root)
        if (type(node) is ParameterRefExpr and id(node) not in windowed)
        or (type(node) is NameExpr and cast(NameExpr, node).name in visible)
    ]
    if position_diagnostics_out is not None:
        position_diagnostics_out.extend(positions)
    return found + positions


def _let_aggregate(node: Node) -> bool:
    """count/avg/min/max over one bare name (the LET it reads is checked)."""

    if type(node) is not CallExpr:
        return False
    call = cast(CallExpr, node)
    return (
        type(call.callee) is NameExpr
        and cast(NameExpr, call.callee).name in _LET_AGGREGATES
        and len(call.arguments) == 1
        and type(call.arguments[0]) is NameExpr
    )


def _children(node: object) -> tuple[Node, ...]:
    """Direct AST children, never a call's callee name; a window frame's
    offsets are children of its window."""

    if type(node) is CallExpr:
        return cast(CallExpr, node).arguments
    result: list[Node] = []
    for item in fields(cast(Any, node)):
        value = getattr(node, item.name)
        for child in cast(
            tuple[object, ...], value if type(value) is tuple else (value,)
        ):
            if isinstance(child, Node):
                result.append(child)
            elif type(child) in {AuthoredWindowFrame, WindowFrameBound}:
                result.extend(_children(child))
    return tuple(result)


def _value_nodes(root: Node) -> tuple[Node, ...]:
    """Every node below ``root`` in authored order, without recursion."""

    result: list[Node] = []
    pending: list[Node] = [root]
    while pending:
        node = pending.pop()
        result.append(node)
        pending.extend(reversed(_children(node)))
    return tuple(result)


def query_parameter_semantic_diagnostics(
    resolutions: ProjectModuleRelationResolutionSet | None,
    catalogs: ProjectModuleCatalogSet | None,
    input_fields: Mapping[ProjectDeclarationOccurrence, frozenset[str]],
) -> tuple[Diagnostic, ...]:
    """Header names colliding with any other visible name, and inputs or
    relation reads naming a parameterized query; both need resolved relation
    names and the completed field names of each input, keyed by its owner
    occurrence.

    Every relation body is read, relation lets and the body of a declaration
    with lets included, each through its own scoped relation names; the names
    of an entry query include those of each of its relation lets.
    """

    if resolutions is None or catalogs is None:
        return ()
    found: list[Diagnostic] = []
    for environment in resolutions.environments:
        # An expression read binds its whole block like an input does.
        found.extend(
            _diagnostic(INPUT_CODE, INPUT_MESSAGE, item.read.expression.span)
            for item in environment.expression_reads
            if item.target_symbol is not None
            and _parameterized(item.target_symbol.target_occurrence.definition)
        )
        for catalog in catalogs.find_module_path(environment.module.path):
            for owner in catalog.relation_owners:
                definition = owner.definition
                for name, span in _relation_inputs(definition):
                    if any(
                        _parameterized(symbol.target_occurrence.definition)
                        for symbol in environment.find_scoped_relation_name(owner, name)
                    ):
                        found.append(_diagnostic(INPUT_CODE, INPUT_MESSAGE, span))
                if type(definition) is QueryDef and definition.parameters:
                    names = set(
                        _visible_names(owner, definition, environment, input_fields)
                    )
                    # Each relation let reads the header too: its name and every
                    # name visible in its own body are collisions as well.
                    for let in catalog.find_lets(owner.declaration_position):
                        names.add(let.identity.declared_name)
                        if type(let.definition) is QueryDef:
                            names.update(
                                _visible_names(
                                    let, let.definition, environment, input_fields
                                )
                            )
                    seen: set[str] = set()
                    for parameter in definition.parameters:
                        if parameter.name in names and parameter.name not in seen:
                            found.append(
                                _diagnostic(
                                    COLLISION_CODE, COLLISION_MESSAGE, parameter.span
                                )
                            )
                        seen.add(parameter.name)
    return tuple(
        sorted(
            found,
            key=lambda item: (
                item.location.path or "",
                item.location.line,
                item.location.column,
                item.code,
            ),
        )
    )


def _parameterized(definition: object) -> bool:
    return type(definition) is QueryDef and bool(cast(QueryDef, definition).parameters)


def _relation_inputs(definition: object) -> tuple[tuple[str, Span], ...]:
    if type(definition) in {TableDef, QueryDef}:
        relation = cast(TableDef | QueryDef, definition)
        return (
            (relation.from_clause.source_name, relation.from_clause.span),
            *(
                (clause.target_relation_name, clause.span)
                for clause in relation.join_clauses
            ),
        )
    if type(definition) is SetRelationDef:
        return tuple(
            (operand.relation_name, operand.span)
            for operand in cast(SetRelationDef, definition).body.operands
        )
    return ()


def _visible_names(
    owner: ProjectDeclarationOccurrence,
    definition: QueryDef,
    environment: ProjectModuleRelationResolutionEnvironment,
    input_fields: Mapping[ProjectDeclarationOccurrence, frozenset[str]],
) -> frozenset[str]:
    names = {symbol.local_name for symbol in environment.symbols}
    if definition.let_clause is not None:
        names.update(binding.name for binding in definition.let_clause.bindings)
    for item in definition.select_items:
        if item.alias is not None:
            names.add(item.alias)
        elif type(item.expression) is NameExpr:
            names.add(cast(NameExpr, item.expression).name)
        elif type(item.expression) is DottedNameExpr:
            names.add(cast(DottedNameExpr, item.expression).parts[-1])
    names.update(window.name for window in definition.named_windows)
    for clause in definition.join_clauses:
        # An omitted JOIN source is the FROM input or an earlier JOIN target,
        # each visible without it.
        names.add(clause.target_binding_name)
        if clause.source_binding_name is not None:
            names.add(clause.source_binding_name)
    for relation in (
        definition.from_clause.source_name,
        *(clause.target_relation_name for clause in definition.join_clauses),
    ):
        for symbol in environment.find_scoped_relation_name(owner, relation):
            # An input without a concrete completed output has no field names
            # here; it also leaves the completed result unsuccessful, so no
            # header name ever binds a read in its place.
            names.update(input_fields.get(symbol.target_occurrence, ()))
    return frozenset(names)
