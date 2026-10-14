"""Entry-query header parameters: declarations, positions and dependence.

A query header parameter is a named value bound at execution. Phase70 S04
admits a read only in the row roles (``let:``, ``where``, the SELECT list of
an ungrouped query and JOIN ``on``) and only beneath scalar operators; every
other position (window frames included), including any read through a let or
output that depends on a parameter, is refused here before semantic analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import TYPE_CHECKING, Any, cast

from pietto.ast_nodes import (
    AuthoredWindowFrame,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    IsNullExpr,
    MembershipExpr,
    NameExpr,
    Node,
    Nullability,
    ParameterRefExpr,
    QueryDef,
    Script,
    SetRelationDef,
    Span,
    TableDef,
    UnaryExpr,
    WindowExpr,
    WindowFrameBound,
)
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
COLLISION_MESSAGE = (
    "Query parameter name is also a field, let, relation, output or window name."
)
INPUT_MESSAGE = "A query with parameters cannot be the input of another relation."
_POSITION_MESSAGE = "Query parameters are not available in this position."
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


def query_parameter_diagnostics(script: Script) -> tuple[Diagnostic, ...]:
    """Declaration and position errors of every entry-query header, sorted."""

    found: list[Diagnostic] = []
    for definition in script.definitions:
        if type(definition) is QueryDef and definition.parameters:
            found.extend(_declaration_diagnostics(definition))
            found.extend(_position_diagnostics(definition))
            # An unaliased read would name its output after the parameter.
            found.extend(
                _diagnostic(COLLISION_CODE, COLLISION_MESSAGE, item.expression.span)
                for item in definition.select_items
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
        if declared.nullability is Nullability.IMPLICIT:
            found.append(
                _diagnostic(
                    DECLARATION_CODE,
                    "Query parameter must declare not null or nullable.",
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


def _position_diagnostics(definition: QueryDef) -> list[Diagnostic]:
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
    admitted: list[Node] = []
    if definition.let_clause is not None:
        admitted.extend(item.expression for item in definition.let_clause.bindings)
    if definition.where_clause is not None:
        admitted.append(definition.where_clause.expression)
    admitted.extend(
        clause.on_clause.expression
        for clause in definition.join_clauses
        if clause.on_clause is not None
    )
    refused: list[Node] = []
    for item in definition.select_items:
        if grouped or type(item.expression) is WindowExpr:
            refused.append(item.expression)
        else:
            admitted.append(item.expression)
    if definition.group_by_clause is not None:
        refused.append(definition.group_by_clause)
    refused.extend(definition.named_windows)
    # These clauses also resolve SELECT output names.
    late = [
        clause
        for clause in (
            definition.satisfying_clause,
            definition.qualify_clause,
            definition.order_by_clause,
            definition.limit_clause,
        )
        if clause is not None
    ]

    # Beneath scalar operators of a row role a read stays admitted; below any
    # other expression (a call, a window or a relation read) it is refused.
    for root in admitted:
        pending: list[Node] = [root]
        while pending:
            node = pending.pop()
            if isinstance(node, _SCALAR_OPERATORS):
                pending.extend(_children(node))
            elif type(node) is CallExpr:
                refused.extend(cast(CallExpr, node).arguments)
            elif type(node) not in {ParameterRefExpr, NameExpr}:
                refused.extend(_children(node))
    # A GROUP BY key is a bare name, never rewritten to a read.
    names = lets | {parameter.name for parameter in definition.parameters}
    return [
        _diagnostic(POSITION_CODE, _POSITION_MESSAGE, node.span)
        for roots, visible in ((refused, names), (late, names | outputs))
        for root in roots
        for node in _value_nodes(root)
        if type(node) is ParameterRefExpr
        or (type(node) is NameExpr and cast(NameExpr, node).name in visible)
    ]


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
    """Header names colliding with any other visible name, and inputs reading a
    parameterized query; both need resolved relation names and the completed
    field names of each input, keyed by its owner occurrence.

    Every relation body is read, relation lets and the body of a declaration
    with lets included, each through its own scoped relation names.
    """

    if resolutions is None or catalogs is None:
        return ()
    found: list[Diagnostic] = []
    for environment in resolutions.environments:
        for catalog in catalogs.find_module_path(environment.module.path):
            for owner in catalog.relation_owners:
                definition = owner.definition
                for name, span in _relation_inputs(definition):
                    if any(
                        type(symbol.target_occurrence.definition) is QueryDef
                        and cast(
                            QueryDef, symbol.target_occurrence.definition
                        ).parameters
                        for symbol in environment.find_scoped_relation_name(owner, name)
                    ):
                        found.append(_diagnostic(INPUT_CODE, INPUT_MESSAGE, span))
                if type(definition) is QueryDef and definition.parameters:
                    names = _visible_names(owner, definition, environment, input_fields)
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
        names.update((clause.target_binding_name, clause.source_binding_name))
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
