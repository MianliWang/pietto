"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

import bisect
import contextlib
import contextvars
import dataclasses
import functools
import itertools
from collections import ChainMap, Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, ParamSpec, cast

if TYPE_CHECKING:
    from pietto.semantic.relationship_predicates import RelationshipCallFailure

from pietto import ast_nodes as ast
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CastExpr,
    CheckDef,
    ComparisonExpr,
    ConditionalExpr,
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    Expression,
    FromClause,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Nullability,
    ParameterRefExpr,
    QueryDef,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
    WindowFrameUnit,
    inlined_arguments,
    with_inlined_argument,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    SEMANTIC_AGGREGATE_NAMES,
    accepts_argument_form,
    aggregate_argument_can_use_let_scope,
    contains_semantic_aggregate,
    extremum_reads_let,
    has_unknown_field_reference,
    invalid_context_diagnostic,
    is_semantic_aggregate_call,
    is_supported_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS, BuiltinFunction
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.row_lookup import bare_field, has_bare_field, qualified_field

if TYPE_CHECKING:
    from pietto._inline_argument import InlinedArgument
    from pietto.semantic.window_semantics import (
        AggregateWindowAnalysis,
        ResolvedNamedWindowNamespace,
        WindowComputationAnalysis,
        WindowExpressionAnalysis,
    )

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)
_NULLIF_SIGNATURE = BuiltinFunction("nullif", ("T", "T"), "T")
_SIGN_SIGNATURE = BuiltinFunction("sign", ("Int|Decimal",), "Int")


_KNOWN_EXPRESSIONS = frozenset(
    {
        ast.LiteralExpr,
        ast.NameExpr,
        ast.DottedNameExpr,
        ast.CallExpr,
        ast.CollectRelationExpr,
        ast.UnaryExpr,
        ast.ConditionalExpr,
        ast.MembershipExpr,
        ast.RelationExistsExpr,
        ast.AnyExpr,
        ast.RelationScalarExpr,
        ast.RelationMembershipExpr,
        ast.CastExpr,
        ast.BinaryExpr,
        ast.ComparisonExpr,
        ast.BetweenExpr,
        ast.IsNullExpr,
        ast.WindowExpr,
        ast.ParameterRefExpr,
        ast.CapturedFieldExpr,
    }
)
QUERY_PARAMETER_TYPES = ("Bool", "Int", "Float", "Text")
_QUERY_PARAMETER_NULLABILITY = {
    Nullability.NOT_NULL: EffectiveNullability.NON_NULL,
    Nullability.NULLABLE: EffectiveNullability.NULLABLE,
}


_P = ParamSpec("_P")


def checks_inlined_arguments(
    infer: Callable[_P, ValueType],
) -> Callable[_P, ValueType]:
    """Check each inlined argument a clause-specific typer types itself; it
    takes the expression first and ``diagnostics`` and ``value_types`` by
    keyword. The type it records for the expression is the checked one."""

    @functools.wraps(infer)
    def checked(*args: _P.args, **kwargs: _P.kwargs) -> ValueType:
        expression = cast(Expression, args[0])
        diagnostics = cast(list[Diagnostic], kwargs["diagnostics"])
        reported = len(diagnostics)
        value_type = _check_inlined_argument(
            expression,
            infer(*args, **kwargs),
            diagnostics,
            cast(
                Mapping[TypeExpr, ResolvedType] | None,
                kwargs.get("type_expansions"),
            ),
            reported=reported,
        )
        cast(dict[Expression, ValueType], kwargs["value_types"])[expression] = (
            value_type
        )
        return value_type

    return checked


def _check_inlined_argument(
    expression: Expression,
    value_type: ValueType,
    diagnostics: list[Diagnostic],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    reported: int | None = None,
) -> ValueType:
    """``value_type``, or Unknown when ``expression`` does not fit each ``def``
    parameter it is inlined for (`_fits_parameters`); ``diagnostics`` past
    ``reported`` are those typing it reported."""

    if _fits_parameters(
        expression,
        value_type,
        diagnostics,
        type_expansions,
        erroneous=reported is not None and _has_error(diagnostics[reported:]),
    ):
        return value_type
    return _UNKNOWN_VALUE_TYPE


def _has_error(diagnostics: Sequence[Diagnostic]) -> bool:
    return any(item.severity is Severity.ERROR for item in diagnostics)


def _fits_parameters(
    expression: Expression,
    value_type: ValueType,
    diagnostics: list[Diagnostic],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    erroneous: bool = False,
    null: bool | None = None,
    unchecked: Callable[[], bool] | None = None,
) -> bool:
    """Check an argument of ``value_type`` against each ``def`` parameter it
    is inlined for.

    A known type must be the parameter type after alias expansion, or for a
    nullable numeric parameter a number of another type that is always null
    (`_fits_null_number`), and a ``not null`` parameter takes only a value
    proven non-null, unless
    ``unchecked`` finds that its unknown nullability is not checked
    (`_typed_beside_unknown`). An argument
    that is always null (``null``, by default `always_null` of
    ``expression``) fits only a nullable parameter, and only one of its own
    type when it has one: a comparison with an always-null operand is still
    Bool. Any other argument whose type is unknown is not checked: either it
    is ``erroneous``, an error was reported for it (as for a comparison with
    the null literal), or nothing is known about it, as for a field of a
    source without a shape. A mismatch is one error at the innermost call
    that does not fit, and every use then stays Unknown so that the expansion
    reports nothing else; a use that the body repeats reports it again, and
    the result reports each error once.
    """

    slots = inlined_arguments(expression)
    if not slots:
        return True

    def is_null() -> bool:
        nonlocal null
        if null is None:
            null = always_null(expression)
        return null

    known = value_type.kind is not ValueTypeKind.UNKNOWN
    if not known and (erroneous or not is_null()):
        return True
    canonical = _canonical_resolved_type(value_type, type_expansions) if known else None
    for slot in slots:
        type_fits = not known or (
            canonical is not None
            and canonical.kind is TypeKind.BUILTIN
            and (
                canonical.name == slot.type_name
                or (slot.nullable and _fits_null_number(canonical, slot, is_null))
            )
        )
        if type_fits and (
            slot.nullable
            or (
                value_type.nullability is EffectiveNullability.NON_NULL
                and not is_null()
            )
            or (
                value_type.nullability is EffectiveNullability.UNKNOWN
                and unchecked is not None
                and not is_null()
                and unchecked()
            )
        ):
            continue
        if type_fits and is_null():
            actual = "null"
        else:
            actual = (
                f"{(canonical or value_type.resolved_type).name}"
                f"{_NULLABILITY_TEXT[value_type.nullability]}"
            )
        expected = " | None" if slot.nullable else ""
        diagnostics.append(
            Diagnostic(
                code="PIE-S2395",
                severity=Severity.ERROR,
                message=(
                    f"Invalid argument for def {slot.function} at position "
                    f"{slot.position} ({slot.parameter}): expected "
                    f"{slot.type_name}{expected}, got {actual}"
                ),
                location=_span_location(slot.call),
            )
        )
        # An inner call's parameter comes first; once it does not fit, the
        # value is unknown to every call around it.
        return False
    return True


# Expressions of unknown type beside an operand of unknown type (`_infer`); a
# comparison other than LIKE is a Bool of unknown nullability beside one.
_UNKNOWN_SPREADING = (
    CallExpr,
    BinaryExpr,
    UnaryExpr,
    ConditionalExpr,
    CastExpr,
    BetweenExpr,
    MembershipExpr,
)


def _typed_beside_unknown(
    expression: Expression,
    value_types: Mapping[Expression, ValueType],
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
) -> bool:
    """Whether ``expression`` has a type only as a call has the type its
    signature gives it beside an argument of unknown type (`_call_value_type`):
    it reaches such a call through `let:` names and through operands whose
    unknown type would leave the type around them unknown. The call's
    nullability then follows from that argument's, which is not known, so a
    ``def`` parameter does not check it, as it does not check an argument of
    unknown type. The parts of a `let:` value have the types they have where
    it is bound (`LetValues.part_types`)."""

    part_types = cast(LetValues, lets).part_types if type(lets) is LetValues else {}
    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr:
            name = cast(NameExpr, node).name
            if (
                lets
                and name in lets
                and not has_bare_field(row_schema, name)
                and name not in expanded
            ):
                expanded.add(name)
                pending.append(lets[name])
            continue
        if not isinstance(node, _UNKNOWN_SPREADING) and not (
            type(node) is ComparisonExpr
            and cast(ComparisonExpr, node).operator in {"like", "not like"}
        ):
            continue
        children = _captured_field_children(node)
        if type(node) is CallExpr and any(
            (child_type := value_types.get(child, part_types.get(child))) is not None
            and child_type.kind is ValueTypeKind.UNKNOWN
            for child in children
        ):
            return True
        pending.extend(children)
    return False


# Expressions whose type follows from their operands' types alone.
_RETYPED_FROM_OPERANDS = (
    LiteralExpr,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    BetweenExpr,
    IsNullExpr,
    ConditionalExpr,
    MembershipExpr,
    CastExpr,
    CallExpr,
)


def unfit_argument(
    function_name: str,
    argument: Expression,
    let_expansions: Mapping[str, Expression] | None,
    value_types: Mapping[Expression, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether ``argument`` of the aggregate ``function_name``, passed to a
    ``def``, does not fit its parameter as the type it has where it stands:
    its PIE-S2395 is then its error, as for a field passed in its place,
    which is unknown to the aggregate. ``value_types`` records such an
    argument as Unknown, so a `let:` name that the aggregate reads as its
    value has the type its binding is recorded with where it is bound, and
    is null where its value written in is (`_written_null`), and an
    operator, literal or call is typed again from its operands' recorded
    types; a field passed in its place is itself unknown. An always-null
    argument does not fit a ``not null`` parameter whatever its type, unless
    it has an error of its own (`_has_own_error`), as where it is typed."""

    if value_types is None or not inlined_arguments(argument):
        return False
    if aggregate_argument_can_use_let_scope(function_name, argument, let_expansions):
        bindings = cast(Mapping[str, Expression], let_expansions)
        name = cast(NameExpr, argument).name
        value_type = value_types.get(bindings[name])
        # A read of a binding has no error of its own; a binding with one is
        # not written in, so it is not null (`_written_null`).
        null = _written_null(name, bindings, value_types, type_expansions)
        erroneous = False
    elif type(argument) in _RETYPED_FROM_OPERANDS:
        operands = {
            child: value_types[child]
            for child in _captured_field_children(argument)
            if child in value_types
        }
        value_type = _infer(
            dataclasses.replace(argument),
            RowSchema(),
            operands,
            [],
            report_unknown_name=False,
            type_expansions=type_expansions,
        )
        null = always_null(argument)
        erroneous = (
            null
            and value_type.kind is ValueTypeKind.UNKNOWN
            and _has_own_error(argument, value_types, type_expansions)
        )
    else:
        return False
    return value_type is not None and not _fits_parameters(
        argument, value_type, [], type_expansions, erroneous=erroneous, null=null
    )


def _written_null(
    name: str,
    bindings: Mapping[str, Expression],
    value_types: Mapping[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether the `let:` name ``name`` of ``bindings`` is always null as
    emission writes it in (`_write_lets`): its value, with each earlier name
    it reads through a null operand written in, is always null
    (`always_null`), and its binding has no error of its own
    (`_has_own_error`), as a binding with one is not written in. A binding
    reads only earlier ones, so they are decided first, without recursion."""

    reached = {name}
    pending = [name]
    while pending:
        nodes = [bindings[pending.pop()]]
        while nodes:
            node = nodes.pop()
            if type(node) is not NameExpr:
                nodes.extend(_null_operands(node))
                continue
            read = cast(NameExpr, node).name
            if read in bindings and read not in reached:
                reached.add(read)
                pending.append(read)
    order = {binding: index for index, binding in enumerate(bindings)}
    nulls: dict[str, bool] = {}
    for current in sorted(reached, key=order.__getitem__):
        value = bindings[current]
        nulls[current] = always_null(value, nulls) and not _has_own_error(
            value, value_types, type_expansions
        )
    return nulls[name]


def _has_own_error(
    expression: Expression,
    value_types: Mapping[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether typing ``expression`` again, each part without operands (a
    field, `let:` name or literal) with the type ``value_types`` records for
    it, finds an error: a part built on them, an inner ``def`` argument
    included, has an error of its own, as typing it where it stands found.
    The ``def`` parameters of ``expression`` itself are not checked."""

    seeds: dict[Expression, ValueType] = {}
    pending = [expression]
    while pending:
        node = pending.pop()
        children = _captured_field_children(node)
        if children:
            pending.extend(children)
        elif node in value_types:
            seeds[node] = value_types[node]
        elif type(node) is ast.CapturedFieldExpr:
            # Typed only by its let's capture environment.
            return True
    found: list[Diagnostic] = []
    _infer(
        dataclasses.replace(expression),
        RowSchema(),
        seeds,
        found,
        report_unknown_name=False,
        type_expansions=type_expansions,
    )
    return _has_error(found)


class LetValues(dict[str, Expression]):
    """The `let:` values of one relation that typing follows by name, as
    emission inlines them, in binding order, and what checks a ``def``
    argument as emission writes it, each `let:` name replaced by its value
    (`_written_argument`).

    A name in ``erroneous`` has an error of its own and is not written in, so
    that its error stands alone. ``written`` holds each binding as written
    (`_Written`), or None for one that is not, and ``differs`` whether a read
    of one is not typed as it is written; until one is, every argument is its
    own written form. Then ``typed`` holds, for each expression typed here by
    identity, the diagnostics list it was typed into and where in it its
    diagnostics are, and ``checked`` each ``def`` argument as the argument
    around it reads it (`_Written`), or None for one checked as it stands
    that reads a binding. Where typing has no row to read fields from (a
    relation with JOIN inputs), ``field_types`` holds the type of each field
    the values read, which a binding is written with (`_write_lets`).
    ``part_types`` holds the type of each part of the values where they are
    bound, where typing knows them (`_typed_beside_unknown`).
    """

    __slots__ = (
        "checked",
        "differs",
        "erroneous",
        "field_types",
        "part_types",
        "typed",
        "written",
    )

    def __init__(
        self,
        values: Mapping[str, Expression] | None = None,
        erroneous: set[str] | None = None,
        field_types: dict[Expression, ValueType] | None = None,
        part_types: Mapping[Expression, ValueType] | None = None,
    ) -> None:
        super().__init__(values or {})
        self.erroneous: set[str] = set() if erroneous is None else erroneous
        self.field_types = field_types
        self.part_types: Mapping[Expression, ValueType] = part_types or {}
        self.written: dict[str, _Written | None] = {}
        self.differs = False
        self.typed: dict[int, tuple[list[Diagnostic], int, int]] = {}
        self.checked: dict[int, _Written | None] = {}


@dataclasses.dataclass(frozen=True, slots=True)
class _Written:
    """A binding or ``def`` argument as emission writes it: ``form``, of
    ``value_type`` (None for an argument that is its own written form),
    ``always_null`` or not, ``size`` nodes nested ``levels`` deep once
    inlined, as PIE-S2328 counts them, and, for a binding, the ``errors``
    writing it finds, which move to each read of it."""

    form: Expression
    value_type: ValueType | None
    always_null: bool
    size: int
    levels: int
    errors: tuple[Diagnostic, ...] = ()


class _FailedRelationshipTypes(dict[Expression, ValueType]):
    def __init__(self, failures: Sequence[RelationshipCallFailure]) -> None:
        super().__init__()
        self.failures = {id(failure.expression): failure for failure in failures}


class _WrittenTypes(dict[Expression, ValueType]):
    """The types a written form (`_written_form`) is typed with, by part,
    and the diagnostics of each part it keeps whole, by identity, which
    typing reports where it reaches that part, as it would the part itself
    written there."""

    __slots__ = ("diagnostics", "failures")

    def __init__(self) -> None:
        super().__init__()
        self.diagnostics: dict[int, list[Diagnostic]] = {}
        self.failures: dict[int, RelationshipCallFailure] = {}


def _written_form(
    expression: Expression,
    lets: LetValues,
    row_schema: RowSchema,
    value_types: Mapping[Expression, ValueType],
    diagnostics: list[Diagnostic] | None,
    *,
    root: bool,
    root_type: ValueType | None = None,
    reads_let: Callable[[str], bool] = lambda name: True,
) -> tuple[Expression, _WrittenTypes, bool, bool, int, int] | None:
    """``expression`` as emission writes it, the types and diagnostics to
    type it with (`_WrittenTypes`), whether it differs from ``expression``,
    whether it is always null (`always_null`), and its size and levels once
    inlined (PIE-S2328).

    A read of a written binding, where typing reads the name as its `let:`
    value (``reads_let``), is its value: the null literal itself, which
    takes its type from where it stands, or the read with the binding's type
    and errors, which move to the start of the read; a read whose type where
    it stands (``root_type`` at the ``root``) is the written one stays as it
    is. A ``def`` argument inside, already checked (`LetValues.checked`), is
    its form of the type it has around it, still the argument of its own
    calls; an aggregate call is kept whole, as its arguments read a binding
    as its name. Each part kept whole keeps its type in ``value_types`` and
    the diagnostics typing it into ``diagnostics`` reported
    (`LetValues.typed`), and only the parts rebuilt around them are typed
    again. At the ``root`` the expression's own ``def`` parameters are left
    out, for its caller to check them. None when it reads a captured field
    whose type is not known here, or an argument whose form was not used.
    """

    from pietto.semantic.let_bindings import _level_weight

    seeds = _WrittenTypes()
    sources = value_types.maps if isinstance(value_types, ChainMap) else (value_types,)
    for source in sources:
        if isinstance(source, (_FailedRelationshipTypes, _WrittenTypes)):
            seeds.failures.update(source.failures)

    def keep(part: Expression, value_type: ValueType, node: Expression) -> None:
        seeds[part] = value_type
        typed = lets.typed.get(id(node))
        if typed is not None and typed[0] is diagnostics:
            seeds.diagnostics[id(part)] = typed[0][typed[1] : typed[2]]

    def walk(
        node: Expression, root: bool
    ) -> tuple[Expression, bool, bool, int, int] | None:
        if not root and id(node) in lets.checked:
            argument = lets.checked[id(node)]
            if argument is None:
                return None
            if argument.value_type is None:
                return node, False, argument.always_null, argument.size, argument.levels
            # Still the argument of its calls: one that does not fit stays
            # unknown, and is no null literal, around it.
            form = (
                _null_fitting(
                    argument.form.span,
                    (*inlined_arguments(argument.form), *inlined_arguments(node)),
                )
                if _is_null_literal(argument.form)
                else functools.reduce(
                    with_inlined_argument, inlined_arguments(node), argument.form
                )
            )
            keep(form, argument.value_type, node)
            return form, True, argument.always_null, argument.size, argument.levels
        if (
            type(node) is NameExpr
            and not has_bare_field(row_schema, node.name)
            and reads_let(node.name)
        ):
            written = lets.written.get(node.name)
            if written is not None:
                if _is_null_literal(written.form):
                    own = () if root else inlined_arguments(node)
                    return (
                        _null_fitting(
                            node.span, (*inlined_arguments(written.form), *own)
                        ),
                        True,
                        True,
                        written.size,
                        written.levels,
                    )
                if not (
                    written.errors
                    or written.always_null
                    or (root_type if root else value_types.get(node))
                    != written.value_type
                ):
                    # Typed where it stands as it is written.
                    return node, False, False, written.size, written.levels
                result = dataclasses.replace(node) if root else node
                seeds[result] = cast(ValueType, written.value_type)
                at = _span_location(node.span)
                seeds.diagnostics[id(result)] = [
                    dataclasses.replace(error, location=at) for error in written.errors
                ]
                return result, True, written.always_null, written.size, written.levels
        if type(node) is ast.CapturedFieldExpr and node not in value_types:
            return None
        size, levels = 1, 0
        walked: list[tuple[Expression, Expression, bool]] = []
        nulls: dict[int, bool] = {}
        for child in _captured_field_children(node):
            item = walk(child, False)
            if item is None:
                return None
            form, changed, nulls[id(child)], child_size, child_levels = item
            size += child_size
            levels = max(levels, child_levels)
            walked.append((child, form, changed))
        levels += _level_weight(node)
        operands = [nulls[id(child)] for child in _null_operands(node)]
        if type(node) is LiteralExpr:
            null = cast(LiteralExpr, node).value is None
        elif type(node) in (CallExpr, ConditionalExpr):
            null = bool(operands) and all(operands)
        else:
            null = any(operands)
        if not any(changed for _, _, changed in walked) or (
            type(node) is CallExpr and is_semantic_aggregate_call(node)
        ):
            return node, False, null, size, levels
        for child, _, changed in walked:
            if not changed and child in value_types:
                keep(child, value_types[child], child)
        result = _with_children(node, {id(child): form for child, form, _ in walked})
        if not root:
            for slot in inlined_arguments(node):
                result = with_inlined_argument(result, slot)
        failure = seeds.failures.get(id(node))
        if failure is not None:
            assert isinstance(result, CallExpr)
            seeds.failures[id(result)] = dataclasses.replace(failure, expression=result)
        return result, True, null, size, levels

    item = walk(expression, root)
    if item is None:
        return None
    form, changed, null, size, levels = item
    return form, seeds, changed, null, size, levels


def _null_fitting(span: ast.Span, slots: tuple[InlinedArgument, ...]) -> LiteralExpr:
    """The null literal at ``span`` that must fit ``slots``, innermost call
    first. Null fits each nullable parameter, so only the first ``not null``
    one counts and the literal carries that one alone, however long the chain
    of `let:` names and calls it passes through."""

    literal = LiteralExpr(value=None, span=span)
    for slot in slots:
        if not slot.nullable:
            return with_inlined_argument(literal, slot)
    return literal


def _span_location(span: ast.Span) -> SourceLocation:
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _with_children(node: Expression, forms: Mapping[int, Expression]) -> Expression:
    """``node`` without its ``def`` parameters, each child in ``forms`` (by
    identity) replaced by its form."""

    changes: dict[str, object] = {}
    for item in dataclasses.fields(node):
        value = getattr(node, item.name)
        if isinstance(value, Expression) and id(value) in forms:
            changes[item.name] = forms[id(value)]
        elif type(value) is tuple:
            changes[item.name] = tuple(
                forms.get(id(child), child) for child in cast(tuple[object, ...], value)
            )
    return dataclasses.replace(node, **changes)


def _write_lets(
    lets: LetValues,
    row_schema: RowSchema,
    value_types: Mapping[Expression, ValueType],
    *,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> None:
    """Write each binding of ``lets`` not yet written, in binding order, once:
    a binding reads only earlier ones, so each is written with those written
    in, and one that reads a later one has an error of its own. A binding
    with an error of its own is not written, and a read of one is typed as
    itself. A binding that reads no written one has the type it has where it
    is bound; any other is typed as written, and keeps that type and the
    errors writing it in finds, once each. A binding is typed where it is
    bound as it is written (`_null_reads`), so writing it in is expected to
    find no error the binding did not report itself; one it finds is still
    kept, and reported at each read (`_written_form`).

    It runs where typing starts, once a ``def`` argument reads a binding
    (`_reads_let_in_argument`), as writing a value where the argument stands
    would nest it that much deeper. A binding is typed as it is where it is
    bound, without the relation reads of the expression typed (a row `let:`
    reads no relation), so the same values serve every expression; a name
    in it is never an unknown field, as it is not where it is bound.
    """

    pending = list(
        itertools.takewhile(lambda name: name not in lets.written, reversed(lets))
    )
    # The parts of a value are typed as where it is bound: by the row, or by
    # the field types the values read where there is no row.
    part_types = (
        value_types
        if lets.field_types is None
        else ChainMap(cast(dict[Expression, ValueType], value_types), lets.field_types)
    )
    for name in reversed(pending):
        lets.written[name] = None
        if name in lets.erroneous:
            continue
        item = _written_form(lets[name], lets, row_schema, part_types, None, root=False)
        if item is None:
            continue
        form, seeds, changed, null, size, levels = item
        found: list[Diagnostic] = []
        if _is_null_literal(form):
            # A read writes the literal itself (`_written_form`).
            value_type = _UNKNOWN_VALUE_TYPE
        elif not changed and bare_value_types is not None and name in bare_value_types:
            value_type = bare_value_types[name]
        else:
            # Without a row, a field below a part that is not kept whole, as
            # in `not o.flag`, takes the type it has where it is bound.
            field_types = lets.field_types or {}
            nodes = [form] if field_types else []
            while nodes:
                node = nodes.pop()
                if type(node) not in (NameExpr, DottedNameExpr):
                    nodes.extend(_captured_field_children(node))
                elif (field_type := field_types.get(node)) is not None:
                    seeds.setdefault(node, field_type)
            value_type = _infer(
                form,
                row_schema,
                seeds,
                found,
                report_unknown_name=False,
                field_qualifier=field_qualifier,
                bare_value_types=bare_value_types,
                bare_value_expressions=MappingProxyType(lets),
                type_expansions=type_expansions,
            )
        # Each error moves to the read that writes the value in, so the
        # binding keeps one of each.
        at = _span_location(lets[name].span)
        written = lets.written[name] = _Written(
            form,
            value_type,
            null,
            size,
            levels + 1,
            tuple(
                dict.fromkeys(
                    dataclasses.replace(error, location=at)
                    for error in found
                    if error.severity is Severity.ERROR
                )
            ),
        )
        # A read is typed as its binding is where that is known, else unknown.
        read_type = None if bare_value_types is None else bare_value_types.get(name)
        lets.differs = lets.differs or bool(
            null or written.errors or value_type != (read_type or _UNKNOWN_VALUE_TYPE)
        )


def _reads_let_in_argument(
    expressions: Sequence[Expression],
    lets: LetValues,
    row_schema: RowSchema,
) -> bool:
    """Whether a ``def`` argument in ``expressions`` reads a binding of
    ``lets``."""

    pending = [(expression, False) for expression in expressions]
    while pending:
        node, argument = pending.pop()
        argument = argument or bool(inlined_arguments(node))
        if (
            argument
            and type(node) is NameExpr
            and node.name in lets
            and not has_bare_field(row_schema, node.name)
        ):
            return True
        pending.extend((child, argument) for child in _captured_field_children(node))
    return False


def _written_argument(
    expression: Expression,
    value_type: ValueType,
    lets: LetValues,
    row_schema: RowSchema,
    value_types: Mapping[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    allow_aggregate_projection: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> tuple[ValueType, bool, list[Diagnostic]] | None:
    """A ``def`` argument, typed where it stands as ``value_type`` into
    ``diagnostics``, as emission writes it, with the `let:` values ``lets``
    has written in: its type and whether it is always null there, and the
    diagnostics the literal spelling reports, a value's errors at the start
    of its read (`_written_form`). None when it is its own written form, or
    when writing the values in passes the PIE-S2328 limit or reads a captured
    field whose type is not known here; it is then checked as it stands. It
    is recorded as the argument around it reads it (`LetValues.checked`).
    """

    from pietto.semantic.let_bindings import _exceeds

    item = _written_form(
        expression,
        lets,
        row_schema,
        value_types,
        diagnostics,
        root=True,
        root_type=value_type,
        # As `_name_value_type` reads a name that is no field: where it reads
        # no `let:` value, as in a grouped select, the name is unknown.
        reads_let=lambda name: (
            row_schema.is_unknown
            or (bare_value_types is not None and name in bare_value_types)
            or name in (suppressed_unknown_names or ())
        ),
    )
    if item is None:
        lets.checked[id(expression)] = None
        return None
    form, seeds, changed, null, size, levels = item
    if not changed:
        lets.checked[id(expression)] = _Written(expression, None, null, size, levels)
        return None
    if _exceeds(size, levels):
        lets.checked[id(expression)] = None
        return None
    found: list[Diagnostic] = []
    form_type = _infer(
        form,
        row_schema,
        seeds,
        found,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        allow_aggregate_projection=allow_aggregate_projection,
        bare_value_types=bare_value_types,
        bare_value_expressions=MappingProxyType(lets),
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    lets.checked[id(expression)] = _Written(form, form_type, null, size, levels)
    return form_type, null, found


def always_null(
    expression: Expression, names: Mapping[str, bool] | None = None
) -> bool:
    """Whether ``expression`` is NULL on every row: a null literal; a sign or
    ``not`` of such a value; an arithmetic operator or comparison with such an
    operand; or a ``coalesce`` or conditional whose every value is. A cast of
    null is not a supported cast (PIE-S2105), so it is not one of them. A
    name is null where ``names`` says it is."""

    results: dict[int, bool] = {}
    pending: list[tuple[Expression, bool]] = [(expression, False)]
    while pending:
        node, ready = pending.pop()
        children = _null_operands(node)
        if children and not ready:
            pending.append((node, True))
            pending.extend((child, False) for child in children)
            continue
        operands = [results[id(child)] for child in children]
        if type(node) is LiteralExpr:
            results[id(node)] = cast(LiteralExpr, node).value is None
        elif type(node) is NameExpr:
            results[id(node)] = names is not None and names.get(
                cast(NameExpr, node).name, False
            )
        elif type(node) in (CallExpr, ConditionalExpr):
            results[id(node)] = bool(operands) and all(operands)
        else:
            results[id(node)] = any(operands)
    return results[id(expression)]


def _null_operands(node: Expression) -> tuple[Expression, ...]:
    """The operands whose NULL decides whether ``node`` is always null."""

    kind = type(node)
    if kind is UnaryExpr:
        return (cast(UnaryExpr, node).operand,)
    if kind is ComparisonExpr or (
        kind is BinaryExpr and cast(BinaryExpr, node).operator not in ("and", "or")
    ):
        binary = cast(BinaryExpr | ComparisonExpr, node)
        return (binary.left, binary.right)
    if (
        kind is CallExpr
        and type(cast(CallExpr, node).callee) is NameExpr
        and cast(NameExpr, cast(CallExpr, node).callee).name == "coalesce"
    ):
        return cast(CallExpr, node).arguments
    if kind is ConditionalExpr:
        conditional = cast(ConditionalExpr, node)
        return (conditional.when_true, conditional.when_false)
    return ()


_NULLABILITY_TEXT = MappingProxyType(
    {
        EffectiveNullability.NON_NULL: "",
        EffectiveNullability.NULLABLE: " | None",
        EffectiveNullability.UNKNOWN: " of unknown nullability",
    }
)


def query_parameter_value_type(type_name: str, nullability: Nullability) -> ValueType:
    """The value type of a validated header parameter or of one of its reads."""

    effective = _QUERY_PARAMETER_NULLABILITY.get(nullability)
    if type_name not in QUERY_PARAMETER_TYPES or effective is None:
        raise ValueError("Query parameter lacks a validated declaration.")
    return _builtin_value_type(type_name, effective)


def type_callable_bodies(
    script: Script,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type top-level callable bodies against their parameter environments."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, (ConstraintDef, DeriveDef)):
            continue
        row_schema = _callable_row_schema(
            definition,
            type_expansions=type_expansions,
            type_nullability=type_nullability,
        )
        _append_invalid_count_context_diagnostic(
            definition.body,
            diagnostics,
            context=(
                "constraint body"
                if isinstance(definition, ConstraintDef)
                else "derive body"
            ),
        )
        _infer(
            definition.body,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
        )

    return value_types, diagnostics


def type_shape_predicates(
    script: Script,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type shape check bodies and index predicates against shape fields."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, ShapeDef):
            continue
        row_schema = _shape_row_schema(
            definition,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
        )
        for item in definition.items:
            if isinstance(item, CheckDef):
                expression = item.expression
                context = "shape check"
            elif isinstance(item, IndexDef) and item.predicate is not None:
                expression = item.predicate
                context = "index predicate"
            else:
                continue
            start = len(diagnostics)
            _append_invalid_count_context_diagnostic(
                expression,
                diagnostics,
                context=context,
            )
            _infer(
                expression,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
                type_expansions=type_expansions,
            )
            _append_condition_diagnostic(
                expression,
                context,
                value_types,
                diagnostics,
                type_expansions,
                explained=_has_error(diagnostics[start:]),
            )

    return value_types, diagnostics


def _append_condition_diagnostic(
    expression: Expression,
    context: str,
    value_types: Mapping[Expression, ValueType],
    diagnostics: list[Diagnostic],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    explained: bool,
    row_schema: RowSchema | None = None,
    lets: Mapping[str, Expression] | None = None,
) -> None:
    """Report a condition, typed into ``value_types``, that is not a Bool
    (PIE-S2202): one of a known type, or, where no error explains its unknown
    type (``explained``), a built-in call whose signature fixes another type,
    also as a `let:` value (`condition_value_type`). A type alias reads as
    the type it expands to."""

    from pietto.semantic.predicate_checks import _check_bool_expression

    diagnostic = _check_bool_expression(
        expression,
        context=context,
        expression_value_types=value_types,
        type_expansions=type_expansions,
        explained=explained,
        row_schema=row_schema,
        lets=lets,
    )
    if diagnostic is not None:
        diagnostics.append(diagnostic)


def type_shape_field_derives(
    script: Script,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type field derive expressions against all fields in their shape."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, ShapeDef):
            continue
        row_schema = _shape_row_schema(
            definition,
            type_resolutions=type_expansions,
            type_nullability=type_nullability,
        )
        for field in definition.fields:
            if field.derive_expression is None:
                continue
            _append_invalid_count_context_diagnostic(
                field.derive_expression,
                diagnostics,
                context="field derive body",
            )
            _infer(
                field.derive_expression,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )

    return value_types, diagnostics


def type_source_connector_arguments(
    script: Script,
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type source connector arguments without typing the connector call."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    empty_environment = RowSchema()

    for definition in script.definitions:
        if not isinstance(definition, SourceDef):
            continue
        connector = definition.connector
        if not isinstance(connector, CallExpr):
            continue
        for argument in connector.arguments:
            _append_invalid_count_context_diagnostic(
                argument,
                diagnostics,
                context="source connector argument",
            )
            _infer(
                argument,
                empty_environment,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )

    return value_types, diagnostics


def type_relation_expressions(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
    relation_let_value_types: Mapping[DerivedRelation, Mapping[str, ValueType]]
    | None = None,
    relation_let_expressions: Mapping[DerivedRelation, Mapping[str, Expression]]
    | None = None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    let_diagnostics: Sequence[Diagnostic] = (),
    single_file: bool = True,
    let_part_types: Mapping[Expression, ValueType] | None = None,
    joined_inputs: Mapping[DerivedRelation, RowSchema] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> tuple[
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[WindowExpr, WindowExpressionAnalysis | AggregateWindowAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Type supported table/query expressions without validating consumers.

    ``let_diagnostics`` are the relation `let:` diagnostics; a window frame
    offset that reads a binding with one of them reports no PIE-S2104.
    Without ``single_file`` the checks that only single-file SQL needs are
    skipped: the ROWS and GROUPS frame offset and window count literal ranges
    and a bare constant ungrouped ORDER BY key.
    ``let_part_types`` are the types of the parts of the `let:` values where
    they are bound (`LetValues.part_types`).
    """

    value_types: dict[Expression, ValueType] = (
        _FailedRelationshipTypes(failed_relationship_calls)
        if failed_relationship_calls
        else {}
    )
    diagnostics: list[Diagnostic] = []
    window_analyses: dict[
        WindowExpr, WindowExpressionAnalysis | AggregateWindowAnalysis
    ] = {}
    named_window_namespaces: dict[
        DerivedRelation,
        ResolvedNamedWindowNamespace,
    ] = {}
    relation_let_value_types = relation_let_value_types or {}
    relation_let_expressions = (
        relation_let_expressions
        if relation_let_expressions is not None
        else _relation_let_expressions(script, relation_let_value_types)
    )

    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        input_schema = (joined_inputs or {}).get(definition)
        if input_schema is None:
            input_schema = _input_schema(
                definition,
                from_resolutions=from_resolutions,
                source_row_schemas=source_row_schemas,
                relation_row_schemas=relation_row_schemas,
            )
        let_value_types = relation_let_value_types.get(definition)
        let_expressions = relation_let_expressions.get(definition)
        rejected_lets = set(rejected_let_names(definition, let_value_types))
        erroneous_lets = rejected_lets | _let_names_with_diagnostics(
            definition, let_diagnostics
        )
        if let_expressions is not None:
            let_expressions = LetValues(
                let_expressions, erroneous_lets, part_types=let_part_types
            )
            from pietto.semantic.let_bindings import _relation_expressions

            if _reads_let_in_argument(
                _relation_expressions(definition), let_expressions, input_schema
            ):
                _write_lets(
                    let_expressions,
                    input_schema,
                    value_types,
                    field_qualifier=(
                        definition.from_clause.binding_name
                        or definition.from_clause.source_name
                    ),
                    bare_value_types=let_value_types,
                    type_expansions=type_expansions,
                )
        join_windows_refused = False
        named_window_namespace_failed = False
        named_window_namespace = None
        if definition.named_windows and not join_windows_refused:
            from pietto.semantic.window_analysis import (
                named_window_resolution_diagnostics,
            )
            from pietto.semantic.window_semantics import (
                NamedWindowResolutionFailure,
                ResolvedNamedWindowNamespace,
                resolve_named_window_namespace,
            )

            named_window_namespace = resolve_named_window_namespace(definition)
            if type(named_window_namespace) is NamedWindowResolutionFailure:
                diagnostics.extend(
                    named_window_resolution_diagnostics(named_window_namespace)
                )
                named_window_namespace_failed = True
                named_window_namespace = None
            else:
                assert type(named_window_namespace) is ResolvedNamedWindowNamespace
                named_window_namespaces[definition] = named_window_namespace
        selected_output_names = tuple(
            _relation_projection_output_name(item) for item in definition.select_items
        )
        selected_output_name_counts = Counter(
            name for name in selected_output_names if name is not None
        )
        duplicate_window_output_names = {
            item.alias
            for item in definition.select_items
            if type(item.expression) is WindowExpr
            and item.alias is not None
            and selected_output_name_counts[item.alias] != 1
        }
        window_alias_value_types: dict[str, ValueType] = {}
        if definition.where_clause is not None:
            where = definition.where_clause.expression
            start = len(diagnostics)
            _append_invalid_count_context_diagnostic(
                where,
                diagnostics,
                context="where clause",
            )
            where_type = _infer(
                where,
                input_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
                field_qualifier=(
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                ),
                bare_value_types=let_value_types,
                bare_value_expressions=let_expressions,
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
            _append_condition_diagnostic(
                where,
                "where clause",
                value_types,
                diagnostics,
                type_expansions,
                explained=where_type.kind is ValueTypeKind.KNOWN
                or unknown_explained(
                    where, diagnostics[start:], input_schema, let_expressions
                ),
                row_schema=input_schema,
                lets=let_expressions,
            )
        for selected_output_ordinal, item in enumerate(definition.select_items):
            if type(item.expression) is WindowExpr:
                if join_windows_refused or named_window_namespace_failed:
                    continue
                from pietto.semantic.window_analysis import (
                    analyze_window_expression,
                )

                window_diagnostic_count = len(diagnostics)
                analysis = analyze_window_expression(
                    definition=definition,
                    item=item,
                    selected_output_ordinal=selected_output_ordinal,
                    source_id=item.expression.span.path or definition.name,
                    input_schema=input_schema,
                    field_qualifier=(
                        definition.from_clause.binding_name
                        or definition.from_clause.source_name
                    ),
                    value_types=value_types,
                    diagnostics=diagnostics,
                    let_value_types=let_value_types or {},
                    let_expressions=let_expressions or {},
                    named_window_namespace=named_window_namespace,
                    type_expansions=type_expansions,
                    let_extrema=False,
                    allow_aggregate_windows=single_file,
                )
                # A window read of a let name PIE-S2329 refused reports nothing
                # more. Dropping its unknown-field report afterwards keeps the
                # analysis stopping there without a fallback in its place.
                refused_reads = {f"Unknown field: {name}" for name in rejected_lets}
                diagnostics[window_diagnostic_count:] = [
                    diagnostic
                    for diagnostic in diagnostics[window_diagnostic_count:]
                    if diagnostic.code != "PIE-S2102"
                    or diagnostic.message not in refused_reads
                ]
                from pietto.semantic.window_semantics import (
                    AggregateWindowAnalysis,
                    WindowExpressionAnalysis,
                    WindowResultAvailabilityKind,
                )

                if isinstance(
                    analysis, (WindowExpressionAnalysis, AggregateWindowAnalysis)
                ):
                    window_analyses[item.expression] = analysis
                    # A project checks only RANGE offsets, as explicit modules do.
                    diagnostics.extend(
                        _window_literal_range_diagnostics(
                            item.expression,
                            analysis,
                            input_schema,
                            let_expressions or {},
                            erroneous_lets,
                            units=frozenset(WindowFrameUnit)
                            if single_file
                            else frozenset({WindowFrameUnit.RANGE}),
                            counts=single_file,
                        )
                    )
                    result = analysis.semantic_fact.result
                    if (
                        result.kind is WindowResultAvailabilityKind.CONCRETE
                        and result.value_type is not None
                    ):
                        value_types[item.expression] = result.value_type
                        if (
                            item.alias is not None
                            and selected_output_name_counts[item.alias] == 1
                        ):
                            window_alias_value_types[item.alias] = result.value_type
                continue
            select_let_value_types = (
                let_value_types
                if (
                    definition.group_by_clause is None
                    and not contains_semantic_aggregate(item.expression)
                )
                or _is_direct_aggregate_projection(item)
                else None
            )
            _infer(
                item.expression,
                input_schema,
                value_types,
                diagnostics,
                # Bare projection diagnostics are owned by schema propagation.
                report_unknown_name=not isinstance(item.expression, NameExpr),
                field_qualifier=(
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                ),
                allow_aggregate_projection=_is_direct_aggregate_projection(item),
                bare_value_types=select_let_value_types,
                bare_value_expressions=let_expressions,
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
        if definition.qualify_clause is not None:
            qualify = definition.qualify_clause.expression
            for hidden_ordinal, window in enumerate(
                _window_expressions(qualify), len(definition.select_items)
            ):
                if join_windows_refused or named_window_namespace_failed:
                    continue
                from pietto.semantic.window_analysis import analyze_window_expression
                from pietto.semantic.window_semantics import (
                    AggregateWindowAnalysis,
                    WindowExpressionAnalysis,
                    WindowResultAvailabilityKind,
                )

                analysis = analyze_window_expression(
                    definition=definition,
                    item=SelectItem(alias=None, expression=window, span=window.span),
                    selected_output_ordinal=hidden_ordinal,
                    source_id=window.span.path or definition.name,
                    input_schema=input_schema,
                    field_qualifier=(
                        definition.from_clause.binding_name
                        or definition.from_clause.source_name
                    ),
                    value_types=value_types,
                    diagnostics=diagnostics,
                    let_value_types=let_value_types or {},
                    let_expressions=let_expressions or {},
                    named_window_namespace=named_window_namespace,
                    type_expansions=type_expansions,
                    let_extrema=False,
                    allow_hidden=True,
                    allow_aggregate_windows=single_file,
                )
                if isinstance(
                    analysis, (WindowExpressionAnalysis, AggregateWindowAnalysis)
                ):
                    window_analyses[window] = analysis
                    if single_file:
                        diagnostics.extend(
                            _window_literal_range_diagnostics(
                                window,
                                analysis,
                                input_schema,
                                let_expressions or {},
                                erroneous_lets,
                                units=frozenset(WindowFrameUnit),
                                counts=True,
                            )
                        )
                    result = analysis.semantic_fact.result
                    if (
                        result.kind is WindowResultAvailabilityKind.CONCRETE
                        and result.value_type is not None
                    ):
                        value_types[window] = result.value_type
                else:
                    value_types[window] = _UNKNOWN_VALUE_TYPE
            output_types = {
                name: value_types.get(item.expression, _UNKNOWN_VALUE_TYPE)
                for name, item in zip(
                    selected_output_names, definition.select_items, strict=True
                )
                if name is not None and selected_output_name_counts[name] == 1
            }
            for name in _bare_names(qualify):
                ambiguity = qualify_output_ambiguity(
                    name,
                    definition,
                    input_schema,
                    let_names={*(let_value_types or {}), *rejected_lets},
                )
                if ambiguity is not None:
                    diagnostics.append(ambiguity)
            start = len(diagnostics)
            qualify_type = _infer(
                qualify,
                input_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
                field_qualifier=(
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                ),
                bare_value_types={**(let_value_types or {}), **output_types},
                bare_value_expressions=let_expressions,
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
            _append_condition_diagnostic(
                qualify,
                "qualify clause",
                value_types,
                diagnostics,
                type_expansions,
                explained=qualify_type.kind is ValueTypeKind.KNOWN
                or unknown_explained(
                    qualify,
                    diagnostics[start:],
                    input_schema,
                    let_expressions,
                ),
                row_schema=input_schema,
                lets=let_expressions,
            )
        if (
            definition.order_by_clause is not None
            and definition.group_by_clause is None
        ):
            aggregated = any(
                contains_semantic_aggregate(selected.expression)
                for selected in definition.select_items
            )
            # A key that names a SELECT output alone reads that output, which
            # emission restates as it inlines a `let:` value; a name two
            # outputs share is a duplicate output already.
            outputs = {
                name: selected.expression
                for name, selected in zip(
                    selected_output_names, definition.select_items, strict=True
                )
                if name is not None
                and type(selected.expression) is not WindowExpr
                and selected_output_name_counts[name] == 1
            }
            for item in definition.order_by_clause.items:
                key_diagnostic_count = len(diagnostics)
                _append_invalid_count_context_diagnostic(
                    item.expression,
                    diagnostics,
                    context="order by",
                )
                order_bare_value_types = let_value_types
                if (
                    type(item.expression) is NameExpr
                    and item.expression.name in window_alias_value_types
                ):
                    order_bare_value_types = dict(window_alias_value_types)
                    order_bare_value_types.update(let_value_types or {})
                elif (
                    type(item.expression) is NameExpr
                    and item.expression.name in duplicate_window_output_names
                ):
                    order_bare_value_types = {
                        item.expression.name: _UNKNOWN_VALUE_TYPE,
                        **(let_value_types or {}),
                    }
                ambiguity = (
                    order_output_ambiguity(
                        item.expression,
                        definition,
                        input_schema,
                        let_expressions,
                        let_names={*(let_value_types or {}), *rejected_lets},
                    )
                    if type(item.expression) is NameExpr
                    else None
                )
                order_lets: Mapping[str, Expression] = let_expressions or {}
                if ambiguity is not None:
                    diagnostics.append(ambiguity)
                elif (
                    type(item.expression) is NameExpr
                    and item.expression.name in selected_output_name_counts
                    and not _names_window_output(definition, item.expression.name)
                    and item.expression.name not in rejected_lets
                    and item.expression.name not in (order_bare_value_types or {})
                    and not input_schema.is_unknown
                    and not has_bare_field(input_schema, item.expression.name)
                ):
                    output = outputs.get(item.expression.name)
                    order_bare_value_types = {
                        **(let_value_types or {}),
                        item.expression.name: _UNKNOWN_VALUE_TYPE
                        if output is None
                        else value_types.get(output, _UNKNOWN_VALUE_TYPE),
                    }
                    if output is not None:
                        order_lets = {**order_lets, item.expression.name: output}
                _infer(
                    item.expression,
                    input_schema,
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    field_qualifier=(
                        definition.from_clause.binding_name
                        or definition.from_clause.source_name
                    ),
                    bare_value_types=order_bare_value_types,
                    bare_value_expressions=let_expressions,
                    suppressed_unknown_names=rejected_lets,
                    type_expansions=type_expansions,
                )
                # A key that already reported its own error gets no PIE-S2380.
                # A bare constant key needs no field knowledge: with an unknown
                # input row a `let:` name is inlined, as emission inlines it.
                problem = (
                    None
                    if len(diagnostics) > key_diagnostic_count
                    else _order_key_problem(
                        item.expression,
                        input_schema,
                        order_lets,
                        aggregated=aggregated,
                        bare_constants=single_file,
                        rejected_lets=rejected_lets,
                    )
                )
                if problem is not None:
                    diagnostics.append(_order_key_diagnostic(item.expression, problem))

    return (
        value_types,
        diagnostics,
        window_analyses,
        named_window_namespaces,
    )


def _window_expressions(expression: Expression) -> Iterator[WindowExpr]:
    """Yield every authored window predicate leaf in source traversal order."""

    if type(expression) is WindowExpr:
        yield expression
        return
    for child in _captured_field_children(expression):
        yield from _window_expressions(child)


def _bare_names(expression: Expression) -> Iterator[NameExpr]:
    """Yield each bare candidate so QUALIFY never chooses an input or output."""

    if type(expression) is NameExpr:
        yield expression
        return
    if type(expression) is WindowExpr:
        return
    for child in _captured_field_children(expression):
        yield from _bare_names(child)


_SIGNED64_MAX = (1 << 63) - 1
# The literal count argument of each window function that takes one.
_WINDOW_COUNT_POSITIONS = {"ntile": 0, "lag": 1, "lead": 1, "nth_value": 1}


def _window_literal_range_diagnostics(
    expression: WindowExpr,
    analysis: (
        WindowExpressionAnalysis | AggregateWindowAnalysis | WindowComputationAnalysis
    ),
    input_schema: RowSchema | None,
    let_expressions: Mapping[str, Expression],
    erroneous_lets: set[str],
    *,
    units: frozenset[WindowFrameUnit] = frozenset(WindowFrameUnit),
    counts: bool = True,
) -> list[Diagnostic]:
    """Refuse window literals that no SQL target accepts, before emission.

    A ROWS, GROUPS or RANGE offset of one of ``units``, after the `let:`
    inlining emission performs, must be a nonnegative signed 64-bit Int
    literal (no target emits another RANGE offset), and with ``counts`` a
    count argument may not exceed that range; the narrower PostgreSQL int4
    count range is checked when PostgreSQL SQL is emitted. An offset that
    reads a `let:` name in `erroneous_lets` already has its error. Without
    ``input_schema`` (a JOIN input) no bare name is an input field.
    """

    input_schema = input_schema or RowSchema()
    name = expression.identity.name
    messages: list[str] = []
    frame = analysis.validated_specification.resolved.frame
    unit = frame.unit
    offsets = tuple(
        (bound.offset, let_value(bound.offset, input_schema, let_expressions))
        for bound in (frame.start, frame.end)
        if bound is not None and bound.offset is not None
    )
    if (
        unit is not None
        and unit in units
        and any(
            not (
                type(value) is LiteralExpr
                and type(value.value) is int
                and 0 <= value.value <= _SIGNED64_MAX
            )
            and not _reads_erroneous_let(
                offset, input_schema, let_expressions, erroneous_lets
            )
            for offset, value in offsets
        )
    ):
        messages.append(
            f"Invalid window frame for function {name}: "
            f"{unit.value.upper()} offsets must be nonnegative integer "
            f"literals up to {_SIGNED64_MAX}"
        )
    position = _WINDOW_COUNT_POSITIONS.get(name) if counts else None
    arguments = expression.call.arguments
    if position is not None and position < len(arguments):
        count = arguments[position]
        if (
            type(count) is LiteralExpr
            and type(count.value) is int
            and count.value > _SIGNED64_MAX
        ):
            messages.append(
                f"Invalid arguments for function {name}: integer literal must not "
                f"exceed {_SIGNED64_MAX}"
            )
    span = expression.call.span
    return [
        Diagnostic(
            code="PIE-S2104",
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
        for message in messages
    ]


def _reads_erroneous_let(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    erroneous_lets: set[str],
) -> bool:
    """Whether the expression reads, through `let:` names, an erroneous let."""

    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr and not has_bare_field(input_schema, node.name):
            if node.name in erroneous_lets:
                return True
            if node.name in let_expressions and node.name not in expanded:
                expanded.add(node.name)
                pending.append(let_expressions[node.name])
            continue
        pending.extend(_captured_field_children(node))
    return False


def _let_names_with_diagnostics(
    definition: TableDef | QueryDef,
    diagnostics: Sequence[Diagnostic],
) -> set[str]:
    """Return the relation's let names whose binding has a diagnostic.

    Bindings are written one after another, so a diagnostic can only be in
    the last binding that starts at or before it.
    """

    if definition.let_clause is None:
        return set()
    bindings = definition.let_clause.bindings
    starts = [(binding.span.line, binding.span.column) for binding in bindings]
    names: set[str] = set()
    for diagnostic in diagnostics:
        if (location := diagnostic.location) is None:
            continue
        at = (location.line, location.column)
        index = bisect.bisect_right(starts, at) - 1
        if index < 0:
            continue
        span = bindings[index].span
        if location.path == span.path and at < (span.end_line, span.end_column):
            names.add(bindings[index].name)
    return names


def let_value(
    expression: Expression,
    row_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> Expression:
    """Follow bare `let:` names, never input fields, to the inlined expression."""

    return _let_chain(expression, row_schema, let_expressions)[-1]


def _let_chain(
    expression: Expression,
    row_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> list[Expression]:
    """``expression`` and each `let:` value its bare name, never an input
    field, leads to in turn."""

    chain = [expression]
    expanded: set[str] = set()
    while (
        type(expression) is NameExpr
        and let_expressions
        and expression.name in let_expressions
        and not has_bare_field(row_schema, expression.name)
        and expression.name not in expanded
    ):
        expanded.add(expression.name)
        expression = let_expressions[expression.name]
        chain.append(expression)
    return chain


def _order_key_problem(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    *,
    aggregated: bool,
    bare_constants: bool,
    rejected_lets: set[str],
) -> str | None:
    """Return why a target would misread or reject an ungrouped ORDER BY key.

    After `let:` inlining and unary signs a bare constant remains: PostgreSQL
    and MySQL read an integer as a column position, and PostgreSQL rejects any
    other bare constant (a computed constant such as `1 + 1` sorts nothing and
    stays accepted); only ``bare_constants`` reports it. In a query with
    aggregates and no GROUP BY, a key that reads an input field outside an
    aggregate is rejected by the targets; over a row of unknown type a name
    that no `let:` binds is such a field.
    """

    if bare_constants and _is_bare_constant(expression, input_schema, let_expressions):
        return (
            "Constant ORDER BY key: a target reads a bare constant key as a "
            "column position or rejects it"
        )
    if aggregated and _reads_input_field_outside_aggregate(
        expression, input_schema, let_expressions, rejected_lets
    ):
        return (
            "ORDER BY key reads an input field outside an aggregate in a query "
            "with aggregates and no GROUP BY, which SQL targets reject"
        )
    return None


def _is_bare_constant(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> bool:
    """Return whether a literal remains after `let:` inlining and unary signs."""

    value = let_value(expression, input_schema, let_expressions)
    while type(value) is UnaryExpr and value.operator in {"+", "-"}:
        value = let_value(value.operand, input_schema, let_expressions)
    return type(value) is LiteralExpr


def _reads_input_field_outside_aggregate(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    rejected_lets: set[str],
) -> bool:
    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr:
            if has_bare_field(input_schema, node.name):
                return True
            if node.name in let_expressions:
                if node.name not in expanded:
                    expanded.add(node.name)
                    pending.append(let_expressions[node.name])
            elif input_schema.is_unknown and node.name not in rejected_lets:
                return True
            continue
        if type(node) is DottedNameExpr:
            return True
        if type(node) is WindowExpr or (
            type(node) is CallExpr and is_semantic_aggregate_call(node)
        ):
            continue
        pending.extend(_captured_field_children(node))
    return False


def _order_key_diagnostic(expression: Expression, message: str) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code="PIE-S2380",
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


def rejected_let_names(
    definition: TableDef | QueryDef,
    admitted: Mapping[str, object] | None,
) -> frozenset[str]:
    """Return the relation's let names that its scope did not admit.

    PIE-S2329 already reports each such binding, so a read of its name does
    not also report an unknown field.
    """

    if definition.let_clause is None or admitted is None:
        return frozenset()
    return frozenset(
        binding.name
        for binding in definition.let_clause.bindings
        if binding.name not in admitted
    )


def infer_row_expression(
    expression: Expression,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None = None,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    suppressed_unknown_names: set[str] | None = None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    relation_columns: Mapping[Expression, ValueType] | None = None,
    captured_value_types: (
        Mapping[ast.CapturedFieldExpr, ValueType | Diagnostic] | None
    ) = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> ValueType:
    """Infer one row-level expression with optional bare-only local bindings.

    ``relation_columns`` holds the known column type of each ``in`` relation
    read, keyed by its expression; its left value must pair with it.

    Each captured outer field below ``expression`` takes its type from
    ``captured_value_types``, the capture environment of its let; a field its
    outer input lacks maps to that environment's own diagnostic instead.
    """

    original_types = value_types
    if failed_relationship_calls and not isinstance(
        value_types, _FailedRelationshipTypes
    ):
        value_types = _FailedRelationshipTypes(failed_relationship_calls)
        value_types.update(original_types)
    seed = value_types.get(expression)
    refused: list[Diagnostic] = []
    if captured_value_types:
        pending: list[Expression] = [expression]
        while pending:
            node = pending.pop()
            if type(node) is not ast.CapturedFieldExpr:
                pending.extend(reversed(_captured_field_children(node)))
                continue
            if node in value_types:
                continue
            captured = captured_value_types[node]
            if type(captured) is Diagnostic:
                if report_unknown_name:
                    refused.append(captured)
                captured = _UNKNOWN_VALUE_TYPE
            value_types[node] = cast(ValueType, captured)
    if (
        type(bare_value_expressions) is LetValues
        and len(bare_value_expressions.written) < len(bare_value_expressions)
        and _reads_let_in_argument((expression,), bare_value_expressions, row_schema)
    ):
        _write_lets(
            bare_value_expressions,
            row_schema,
            value_types,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            type_expansions=type_expansions,
        )
    start = len(diagnostics)
    value_type = _infer(
        expression,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    if refused:
        # A refused captured field reports in source order with the
        # expression's other diagnostics, which keep their own order.
        inferred = diagnostics[start:]
        del diagnostics[start:]
        for diagnostic in inferred:
            while refused and _source_before(refused[0], diagnostic):
                diagnostics.append(refused.pop(0))
            diagnostics.append(diagnostic)
        diagnostics.extend(refused)
    if value_types is not original_types:
        original_types.update(value_types)
    if isinstance(value_types, _FailedRelationshipTypes):
        owned = {
            id(diagnostic)
            for failure in value_types.failures.values()
            for diagnostic in failure.diagnostics
        }
        seen: set[int] = set()
        unique: list[Diagnostic] = []
        for diagnostic in diagnostics:
            identity = id(diagnostic)
            if identity in owned:
                if identity in seen:
                    continue
                seen.add(identity)
            unique.append(diagnostic)
        diagnostics[:] = unique
    if seed is not None:
        # A read the caller seeded that is the whole expression is the
        # caller's own result.
        return seed
    if type(expression) is ast.CapturedFieldExpr:
        # A whole captured field is typed here, so one that does not fit a
        # def parameter is recorded as Unknown, as a computed expression is.
        value_types[expression] = value_type
    return value_type


def _source_before(first: Diagnostic, second: Diagnostic) -> bool:
    if first.location is None or second.location is None:
        return False
    return (first.location.line, first.location.column) < (
        second.location.line,
        second.location.column,
    )


def _captured_field_children(expression: Expression) -> tuple[Expression, ...]:
    """Direct value children where a captured field read may be written."""

    if isinstance(expression, CallExpr):
        return (
            *expression.arguments,
            *(item.expression for item in expression.aggregate_order_by),
        )
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, (CastExpr, ast.RelationMembershipExpr)):
        return (expression.value,)
    if isinstance(expression, (BinaryExpr, ComparisonExpr)):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if type(expression) in _KNOWN_EXPRESSIONS:
        return ()
    raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


def _callable_row_schema(
    definition: ConstraintDef | DeriveDef,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> RowSchema:
    """Build a local value environment from the first parameter binding."""

    fields: dict[str, RowField] = {}
    for parameter in definition.parameters:
        if parameter.name in fields:
            continue
        fields[parameter.name] = RowField(
            name=parameter.name,
            resolved_type=type_expansions[parameter.type],
            nullability=type_nullability[parameter.type],
        )
    return RowSchema(fields=fields)


def _shape_row_schema(
    shape: ShapeDef,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> RowSchema:
    """Build the local field environment used by shape predicates."""

    fields: dict[str, RowField] = {}
    for field in shape.fields:
        if field.name in fields:
            continue
        fields[field.name] = RowField(
            name=field.name,
            resolved_type=type_resolutions[field.type_expr],
            nullability=type_nullability[field.type_expr],
            definition=field,
        )
    return RowSchema(fields=fields)


def _input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> RowSchema:
    """Return a relation's resolved input schema or an Unknown schema."""

    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _is_direct_aggregate_projection(item: SelectItem) -> bool:
    expression = item.expression
    return (
        item.alias is not None
        and isinstance(expression, CallExpr)
        and is_semantic_aggregate_call(expression)
    )


def _relation_projection_output_name(item: SelectItem) -> str | None:
    """Return one selected output name for duplicate-scope accounting."""

    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _relation_let_expressions(
    script: Script,
    relation_let_value_types: Mapping[DerivedRelation, Mapping[str, ValueType]],
) -> dict[DerivedRelation, dict[str, Expression]]:
    expressions: dict[DerivedRelation, dict[str, Expression]] = {}
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        if definition.let_clause is None:
            continue
        admitted_names = relation_let_value_types.get(definition)
        if not admitted_names:
            continue
        expressions[definition] = {
            binding.name: binding.expression
            for binding in definition.let_clause.bindings
            if binding.name in admitted_names
        }
    return expressions


def _infer(
    expression: Expression,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None = None,
    allow_aggregate_projection: bool = False,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    suppressed_unknown_names: set[str] | None = None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    relation_columns: Mapping[Expression, ValueType] | None = None,
    argument_null: bool | None = None,
) -> ValueType:
    """Infer only the expression forms supported by this scaffold.

    ``argument_null`` says whether ``expression``, a ``def`` argument checked
    as it stands, is always null, where its caller knows; by default
    `always_null` of it decides (`_fits_parameters`).
    """

    if isinstance(value_types, (_FailedRelationshipTypes, _WrittenTypes)):
        failure = value_types.failures.get(id(expression))
        if failure is not None and not (
            type(value_types) is _WrittenTypes and expression in value_types
        ):
            reported = len(diagnostics)
            assert isinstance(expression, CallExpr)
            for argument in expression.arguments:
                if isinstance(argument, NameExpr):
                    value_types[argument] = _UNKNOWN_VALUE_TYPE
                else:
                    _infer(
                        argument,
                        row_schema,
                        value_types,
                        diagnostics,
                        report_unknown_name=report_unknown_name,
                        field_qualifier=field_qualifier,
                        bare_value_types=bare_value_types,
                        bare_value_expressions=bare_value_expressions,
                        suppressed_unknown_names=suppressed_unknown_names,
                        type_expansions=type_expansions,
                        relation_columns=relation_columns,
                    )
            value_types[expression] = _UNKNOWN_VALUE_TYPE
            diagnostics.extend(failure.diagnostics)
            if (
                type(bare_value_expressions) is LetValues
                and bare_value_expressions.differs
            ):
                bare_value_expressions.typed[id(expression)] = (
                    diagnostics,
                    reported,
                    len(diagnostics),
                )
            return _UNKNOWN_VALUE_TYPE
    if type(expression) not in _KNOWN_EXPRESSIONS:
        raise AssertionError(f"Unsupported expression: {type(expression).__name__}")
    reported = len(diagnostics)
    existing = value_types.get(expression)
    if existing is not None:
        if type(value_types) is _WrittenTypes:
            # A part of a written form kept whole reports what typing it
            # reported, as the part itself written here would.
            diagnostics.extend(value_types.diagnostics.pop(id(expression), ()))
        if inlined_arguments(expression):
            # A caller may seed the type of a read it owns (a captured field,
            # a joined field, a scalar read, a QUALIFY output). The seed stays
            # the caller's evidence; a use that does not fit is Unknown to the
            # expression around it, as a computed one is.
            existing = _check_inlined_argument(
                expression, existing, diagnostics, type_expansions, reported=reported
            )
        lets = bare_value_expressions
        if type(lets) is LetValues and lets.differs:
            lets.typed[id(expression)] = (diagnostics, reported, len(diagnostics))
        return existing

    if isinstance(expression, WindowExpr):
        diagnostics.append(
            _unknown_function_diagnostic(
                expression.call,
                _callee_name(expression.call),
            )
        )
        return _UNKNOWN_VALUE_TYPE

    if isinstance(expression, LiteralExpr):
        value_type = _literal_value_type(expression)
    elif isinstance(expression, ParameterRefExpr):
        value_type = query_parameter_value_type(
            expression.type_name, expression.nullability
        )
    elif isinstance(expression, NameExpr):
        value_type = _name_value_type(
            expression,
            row_schema,
            diagnostics,
            report_unknown=report_unknown_name,
            bare_value_types=bare_value_types,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    elif isinstance(expression, DottedNameExpr) and field_qualifier is not None:
        value_type = _qualified_name_value_type(
            expression,
            row_schema,
            diagnostics,
            field_qualifier=field_qualifier,
            report_unknown=report_unknown_name,
        )
    elif isinstance(expression, CallExpr):
        value_type = _call_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            allow_aggregate_projection=allow_aggregate_projection,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        if len(diagnostics) == reported:
            value_type = _number_call_type(
                expression,
                value_type,
                value_types,
                diagnostics,
                type_expansions,
                nulls=lambda: _null_reads(
                    expression.arguments,
                    row_schema,
                    bare_value_types,
                    bare_value_expressions,
                    values=True,
                ),
            )
    elif isinstance(expression, ast.CapturedFieldExpr):
        # A captured field is typed only by its let's capture environment.
        raise AssertionError("Captured field read lacks its capture environment.")
    elif isinstance(expression, (ast.RelationExistsExpr, ast.AnyExpr)):
        # An existence test is never NULL; its relation is resolved, scheduled
        # and checked by the owner of the relation name, not by this kernel.
        value_type = _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    elif isinstance(expression, ast.RelationScalarExpr):
        # A scalar read's type is its read block column's, which only the
        # relation-name owner knows; a caller supplies it in ``value_types``.
        value_type = _UNKNOWN_VALUE_TYPE
    elif isinstance(expression, ast.CollectRelationExpr):
        # A collected relation is a nested value, never a scalar one; its
        # project facts report it (PIE-S2802), so it has no scalar type.
        value_type = _UNKNOWN_VALUE_TYPE
    elif isinstance(expression, ast.RelationMembershipExpr):
        # The left value is checked here; the read relation is resolved,
        # scheduled and checked by the relation-name owner, which supplies the
        # type of its one column in ``relation_columns`` when it is known, and
        # the pair then follows the literal-list rule. Three-valued IN is NULL
        # for a NULL left value over a non-empty relation and for a NULL
        # candidate without a match, so the result is conservatively nullable.
        left_type = _infer(
            expression.value,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        column = None if relation_columns is None else relation_columns.get(expression)
        null = _null_reads(
            (expression.value,), row_schema, bare_value_types, bare_value_expressions
        )
        if column is not None and null[0]:
            # A bare NULL takes the known column's type, as in the literal list.
            contextual = _contextual_null_literal_types(
                (expression.value, expression),
                (left_type, column),
                value_types,
                type_expansions,
                (*null, False),
            )
            if contextual is not None:
                left_type = contextual[0]
        if column is not None:
            left_type = _membership_text_literal_types(
                (
                    _comparison_literal(
                        expression.value, row_schema, bare_value_expressions
                    ),
                    None,
                ),
                (left_type, column),
                type_expansions,
            )[0]
        if left_type.kind is ValueTypeKind.UNKNOWN:
            value_type = _UNKNOWN_VALUE_TYPE
        elif (
            column is not None
            and _membership_canonical_type((left_type, column), type_expansions) is None
        ):
            diagnostics.append(
                _invalid_operator_operands_diagnostic(
                    expression, expected="same canonical membership operands"
                )
            )
            value_type = _UNKNOWN_VALUE_TYPE
        else:
            value_type = _builtin_value_type("Bool", EffectiveNullability.NULLABLE)
    elif isinstance(expression, IsNullExpr):
        _infer(
            expression.value,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        value_type = _builtin_value_type(
            "Bool",
            EffectiveNullability.NON_NULL,
        )
    elif isinstance(expression, UnaryExpr):
        value_type = _unary_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    elif isinstance(expression, ConditionalExpr):
        value_type = _conditional_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    elif isinstance(expression, MembershipExpr):
        value_type = _membership_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    elif isinstance(expression, CastExpr):
        value_type = _cast_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    elif isinstance(expression, BinaryExpr):
        value_type = _binary_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    elif isinstance(expression, ComparisonExpr):
        left_type = _infer(
            expression.left,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        right_type = _infer(
            expression.right,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        if expression.operator in {"like", "not like"}:
            # LIKE reads a type alias operand as the type it expands to.
            value_type, expected = resolved_like_value_type(
                _canonical_value_type(left_type, type_expansions),
                _canonical_value_type(right_type, type_expansions),
            )
            if expected is None and _ends_in_unpaired_like_escape(
                let_value(expression.right, row_schema, bare_value_expressions)
            ):
                expected = (
                    "a pattern that does not end in the escape character ! "
                    "(write !! for a literal !)"
                )
        elif _reads_null_literal(
            (expression.left, expression.right), row_schema, bare_value_expressions
        ):
            # `null is null` is TRUE, so a test of null against null has no remedy.
            remedy = (
                None
                if _reads_null_literal(
                    (expression.left, expression.right),
                    row_schema,
                    bare_value_expressions,
                    every=True,
                )
                else {"==": "is None", "!=": "is not None"}.get(expression.operator)
            )
            diagnostics.append(_null_comparison_diagnostic(expression, remedy=remedy))
            value_type, expected = _UNKNOWN_VALUE_TYPE, None
        else:
            value_type, expected = resolved_comparison_value_type(
                left_type,
                right_type,
                type_expansions,
                comparison_literals(
                    expression.left,
                    expression.right,
                    row_schema,
                    bare_value_expressions,
                ),
            )
        if expected is not None:
            diagnostics.append(
                _invalid_operator_operands_diagnostic(expression, expected=expected)
            )
    elif isinstance(expression, BetweenExpr):
        value_type = _between_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    else:
        # Unsupported forms remain opaque so calls and arithmetic are not
        # accidentally checked through their child expressions.
        value_type = _UNKNOWN_VALUE_TYPE
    if len(diagnostics) == reported and isinstance(
        expression, (ComparisonExpr, BetweenExpr, MembershipExpr)
    ):
        expected = _number_test_expected(
            expression, value_types, row_schema, bare_value_expressions, type_expansions
        )
        if expected is not None:
            value_type = _UNKNOWN_VALUE_TYPE
            diagnostics.append(
                _invalid_operator_operands_diagnostic(expression, expected=expected)
            )

    lets = bare_value_expressions
    if inlined_arguments(expression):

        def unchecked() -> bool:
            return _typed_beside_unknown(expression, value_types, row_schema, lets)

        written = None
        if type(lets) is LetValues and lets.differs:
            # Checked as emission writes it, with each `let:` value in place.
            written = _written_argument(
                expression,
                value_type,
                lets,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=report_unknown_name,
                field_qualifier=field_qualifier,
                allow_aggregate_projection=allow_aggregate_projection,
                bare_value_types=bare_value_types,
                suppressed_unknown_names=suppressed_unknown_names,
                type_expansions=type_expansions,
                relation_columns=relation_columns,
            )
        if written is None:
            fits = _fits_parameters(
                expression,
                value_type,
                diagnostics,
                type_expansions,
                erroneous=_has_error(diagnostics[reported:]),
                null=argument_null,
                unchecked=unchecked,
            )
        else:
            # The literal spelling's diagnostics, in place of those typing it
            # as it stands reported, decide whether it fits.
            form_type, null, found = written
            del diagnostics[reported:]
            diagnostics.extend(found)
            fits = _fits_parameters(
                expression,
                form_type,
                diagnostics,
                type_expansions,
                erroneous=_has_error(found),
                null=null,
                unchecked=unchecked,
            )
            if fits:
                # Typed as written, also for the expression around it.
                value_type = form_type
            else:
                checked = cast(LetValues, lets).checked
                checked[id(expression)] = dataclasses.replace(
                    cast(_Written, checked[id(expression)]),
                    value_type=_UNKNOWN_VALUE_TYPE,
                )
        if not fits:
            value_type = _UNKNOWN_VALUE_TYPE
    if (
        type(value_types) is DefBodyTypes
        and value_type.kind is ValueTypeKind.KNOWN
        and _non_null_operands(expression, value_types)
    ):
        value_type = dataclasses.replace(
            value_type, nullability=EffectiveNullability.NON_NULL
        )
    value_types[expression] = value_type
    if type(lets) is LetValues and lets.differs:
        lets.typed[id(expression)] = (diagnostics, reported, len(diagnostics))
    return value_type


class DefBodyTypes(dict[Expression, ValueType]):
    """The types of the parts of a ``def`` body that the body check types
    again to prove its ``not null`` result further than elsewhere
    (`_non_null_operands`), once each argument in it has fit its parameter as
    it does elsewhere."""

    __slots__ = ()


def _non_null_operands(
    expression: Expression, value_types: Mapping[Expression, ValueType]
) -> bool:
    """Whether ``expression`` is a comparison, `between` or `+`, `-` or `*`
    whose operands are all non-null, which SQL never makes NULL. MySQL `/`
    and `%` are NULL for a zero divisor, and `and` and `or` are not proven."""

    if type(expression) is ComparisonExpr:
        operands = (expression.left, expression.right)
    elif type(expression) is BetweenExpr:
        operands = (expression.value, expression.lower, expression.upper)
    elif type(expression) is BinaryExpr and expression.operator in {"+", "-", "*"}:
        operands = (expression.left, expression.right)
    else:
        return False
    return all(
        operand in value_types
        and value_types[operand].nullability is EffectiveNullability.NON_NULL
        for operand in operands
    )


def _unary_value_type(
    expression: UnaryExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type one prefix arithmetic expression."""

    start = len(diagnostics)
    operand_type = _infer(
        expression.operand,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    result, expected = resolved_unary_value_type(
        expression.operator, _canonical_value_type(operand_type, type_expansions)
    )
    if (
        expression.operator == "not"
        and operand_type.kind is ValueTypeKind.UNKNOWN
        and _not_bool_condition(
            expression.operand,
            operand_type,
            row_schema,
            bare_value_expressions,
            type_expansions,
        )
        and not unknown_explained(
            expression.operand,
            diagnostics[start:],
            row_schema,
            bare_value_expressions,
        )
    ):
        # `not` reads its operand as a condition.
        expected = "Bool operand"
    if expected is not None and expression.operator in {"+", "-"}:
        null_number = _null_number_type(
            (expression.operand,),
            (operand_type,),
            row_schema,
            bare_value_expressions,
            type_expansions,
        )
        if null_number is not None:
            result, expected = null_number, None
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
    elif operand_type is _UNKNOWN_NUMBER and expression.operator in {"+", "-"}:
        result = _UNKNOWN_NUMBER
    return result


def resolved_unary_value_type(
    operator: str | ValueType,
    operand_type: ValueType | None = None,
) -> tuple[ValueType, str | None]:
    """Return the closed unary result without source lookup or elaboration.

    The one-argument form remains the historic numeric rule for internal
    callers that have not yet selected an authored operator.
    """

    if operand_type is None:
        assert isinstance(operator, ValueType)
        operand_type = operator
        operator = "+"
    assert isinstance(operator, str)
    assert isinstance(operand_type, ValueType)
    if operand_type.kind is ValueTypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE, None
    if operator == "not":
        if _is_builtin(operand_type, "Bool"):
            return ValueType(
                resolved_type=operand_type.resolved_type,
                nullability=operand_type.nullability,
            ), None
        return _UNKNOWN_VALUE_TYPE, "Bool operand"
    if not _is_numeric(operand_type):
        return _UNKNOWN_VALUE_TYPE, "numeric operand"
    return ValueType(
        resolved_type=operand_type.resolved_type,
        nullability=operand_type.nullability,
    ), None


def _conditional_value_type(
    expression: ConditionalExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type source-ordered conditional operands with no branch promotion."""

    start = len(diagnostics)
    when_true_type = _infer(
        expression.when_true,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    true_end = len(diagnostics)
    condition_type = _infer(
        expression.condition,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    condition_end = len(diagnostics)
    when_false_type = _infer(
        expression.when_false,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    erroneous = {
        id(child)
        for child, value_type, errors in (
            (expression.when_true, when_true_type, diagnostics[start:true_end]),
            (expression.condition, condition_type, diagnostics[true_end:condition_end]),
            (expression.when_false, when_false_type, diagnostics[condition_end:]),
        )
        if value_type.kind is ValueTypeKind.UNKNOWN and _has_error(errors)
    }
    when_true_null, when_false_null = _null_reads(
        (expression.when_true, expression.when_false),
        row_schema,
        bare_value_types,
        bare_value_expressions,
        values=True,
        erroneous=erroneous,
    )
    (condition_null,) = _null_reads(
        (expression.condition,),
        row_schema,
        bare_value_types,
        bare_value_expressions,
        erroneous=erroneous,
    )
    branch_types = _contextual_null_literal_types(
        (expression.when_true, expression.when_false),
        (when_true_type, when_false_type),
        value_types,
        type_expansions,
        (when_true_null, when_false_null),
    )
    if branch_types is not None:
        when_true_type, when_false_type = branch_types
    if condition_null and condition_type.kind is ValueTypeKind.UNKNOWN:
        condition_type = _contextual_null_literal_type("Bool")
        value_types[expression.condition] = condition_type
    if any(
        value_type.kind is ValueTypeKind.UNKNOWN
        for value_type in (when_true_type, condition_type, when_false_type)
    ):
        # A branch of unknown type without an error of its own leaves the
        # condition to be checked.
        if _not_bool_condition(
            expression.condition,
            condition_type,
            row_schema,
            bare_value_expressions,
            type_expansions,
        ) and not unknown_explained(
            expression, diagnostics[start:], row_schema, bare_value_expressions
        ):
            diagnostics.append(
                _invalid_operator_operands_diagnostic(
                    expression,
                    expected="Bool condition",
                )
            )
        elif _is_canonical_builtin(
            condition_type, "Bool", type_expansions
        ) or not unknown_explained(
            expression, diagnostics[start:], row_schema, bare_value_expressions
        ):
            # A branch mismatch does not depend on an unchecked condition's type.
            branch_types = _nulls_as_numbers(
                (when_true_type, when_false_type),
                lambda: (when_true_null, when_false_null),
            )
            expected = _number_misfit(
                lambda types: (
                    None
                    if _shared_canonical_type(types, type_expansions) is not None
                    else "same canonical branch types"
                ),
                branch_types,
                type_expansions,
            )
            if expected is not None:
                diagnostics.append(
                    _invalid_operator_operands_diagnostic(expression, expected=expected)
                )
            elif _of_numbers(branch_types, type_expansions) and _is_canonical_builtin(
                condition_type, "Bool", type_expansions
            ):
                return _UNKNOWN_NUMBER
        return _UNKNOWN_VALUE_TYPE
    if not _is_canonical_builtin(condition_type, "Bool", type_expansions):
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="Bool condition",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(
        (when_true_type, when_false_type),
        type_expansions,
    )
    if canonical is None:
        null_number = _null_number_type(
            (expression.when_true, expression.when_false),
            (when_true_type, when_false_type),
            row_schema,
            bare_value_expressions,
            type_expansions,
        )
        canonical = None if null_number is None else null_number.resolved_type
    if canonical is None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="same canonical branch types",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=canonical,
        nullability=_join_nullability(
            (when_true_type.nullability, when_false_type.nullability)
        ),
    )


def _membership_value_type(
    expression: MembershipExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type fixed scalar-list membership while retaining every occurrence."""

    erroneous: set[int] = set()
    inferred: list[ValueType] = []
    for child in (expression.value, *expression.options):
        start = len(diagnostics)
        child_type = _infer(
            child,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        inferred.append(child_type)
        if child_type.kind is ValueTypeKind.UNKNOWN and _has_error(diagnostics[start:]):
            erroneous.add(id(child))
    child_types = tuple(inferred)
    # A non-empty list tests `value == option` for each option: always NULL
    # when every test reads the null literal; another option may still match.
    if expression.options:
        null_value = _reads_null_literal(
            (expression.value,), row_schema, bare_value_expressions
        )
        if null_value or _reads_null_literal(
            expression.options, row_schema, bare_value_expressions, every=True
        ):
            remedy = (
                None
                if null_value
                else "is not None"
                if expression.negated
                else "is None"
            )
            diagnostics.append(_null_comparison_diagnostic(expression, remedy=remedy))
            return _UNKNOWN_VALUE_TYPE
    child_types = _membership_text_literal_types(
        tuple(
            _comparison_literal(operand, row_schema, bare_value_expressions)
            for operand in (expression.value, *expression.options)
        ),
        child_types,
        type_expansions,
    )
    nulls = _null_reads(
        (expression.value, *expression.options),
        row_schema,
        bare_value_types,
        bare_value_expressions,
        values=True,
        erroneous=erroneous,
    )
    contextual = _contextual_null_literal_types(
        (expression.value, *expression.options),
        child_types,
        value_types,
        type_expansions,
        nulls,
        membership=True,
    )
    if contextual is not None:
        child_types = contextual
    # A null option that operands of two types leave untyped is checked as if
    # it were not there.
    operands = (expression.value, *expression.options)
    kept = tuple(
        (operand, value_type)
        for position, (operand, value_type, null) in enumerate(
            zip(operands, child_types, nulls, strict=True)
        )
        if position == 0 or not (null and value_type.kind is ValueTypeKind.UNKNOWN)
    )
    checked = tuple(value_type for _, value_type in kept)
    if any(value_type.kind is ValueTypeKind.UNKNOWN for value_type in checked):
        return _UNKNOWN_VALUE_TYPE
    if _membership_canonical_type(
        checked, type_expansions
    ) is None and not _null_number_type(
        tuple(operand for operand, _ in kept),
        checked,
        row_schema,
        bare_value_expressions,
        type_expansions,
        shared=_membership_canonical_type,
    ):
        if len(kept) < len(operands) and all(
            resolved_comparison_value_type(
                checked[0],
                option_type,
                type_expansions,
                comparison_literals(
                    expression.value, option, row_schema, bare_value_expressions
                ),
            )[1]
            is None
            for option, option_type in kept[1:]
        ):
            # Comparable operands keep their gradual pairing, but the
            # membership result is Bool and its NULL option can make it NULL.
            return _builtin_value_type("Bool", EffectiveNullability.NULLABLE)
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="same canonical membership operands",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    if not expression.options:
        return _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    return _builtin_value_type(
        "Bool",
        _join_nullability(tuple(value_type.nullability for value_type in child_types)),
    )


def _cast_value_type(
    expression: CastExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Admit only the explicit portable Int-to-Float or Int-to-Text conversion."""

    diagnostic_count = len(diagnostics)
    value_type = _infer(
        expression.value,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    target_name = expression.target.name
    supported_target = target_name in {"Float", "Text"} and (
        not expression.target.arguments
        and expression.target.nullability is Nullability.IMPLICIT
    )
    if value_type.kind is ValueTypeKind.UNKNOWN:
        # A null operand and the target are known without the operand's type;
        # a silent unknown operand is refused unless the cast is to Float or Text. Only
        # the operand's own error explains it, also one in a `let:` value it
        # reads, as written there it would be its own: an unknown input row
        # does not, since both admitted casts read the operand's type.
        explained = len(diagnostics) > diagnostic_count or (
            type(bare_value_expressions) is LetValues
            and _reads_erroneous_let(
                expression.value,
                row_schema,
                bare_value_expressions,
                bare_value_expressions.erroneous,
            )
        )
        # A `let:` name bound to null is the null literal emission inlines; a
        # null def argument that does not fit its parameter is PIE-S2395 alone.
        null_operand = _reads_null_literal(
            (expression.value,), row_schema, bare_value_expressions
        )
        if null_operand or not (explained or supported_target):
            diagnostics.append(
                _invalid_cast_diagnostic(
                    expression,
                    value_type,
                    type_expansions,
                    null_operand=null_operand,
                )
            )
        return _UNKNOWN_VALUE_TYPE
    if not supported_target or not _is_canonical_builtin(
        value_type, "Int", type_expansions
    ):
        diagnostics.append(
            _invalid_cast_diagnostic(expression, value_type, type_expansions)
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type(target_name, value_type.nullability)


def _binary_value_type(
    expression: BinaryExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type one arithmetic or Boolean binary expression."""

    start = len(diagnostics)
    left_type = _infer(
        expression.left,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    right_type = _infer(
        expression.right,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    # An operator reads a type alias as the type it expands to.
    result, expected = resolved_binary_value_type(
        expression.operator,
        _canonical_value_type(left_type, type_expansions),
        _canonical_value_type(right_type, type_expansions),
    )
    if (
        expression.operator in {"and", "or"}
        and result.kind is ValueTypeKind.UNKNOWN
        and expected is None
        and any(
            _not_bool_condition(
                operand,
                operand_type,
                row_schema,
                bare_value_expressions,
                type_expansions,
            )
            for operand, operand_type in (
                (expression.left, left_type),
                (expression.right, right_type),
            )
        )
        and not unknown_explained(
            expression, diagnostics[start:], row_schema, bare_value_expressions
        )
    ):
        # Each operand is a condition, which an operand of unknown type
        # without an error of its own leaves to be checked.
        expected = "Bool operands"
    elif (
        expression.operator in {"+", "-", "*", "/", "%"}
        and result.kind is ValueTypeKind.UNKNOWN
        and expected is None
    ):
        # A null operand takes the other's type, which the operator must take;
        # the result, always null, is then of the operator's result type over
        # two operands of that type, unless an operand's own error, such as a
        # `let:` name that is an unknown field where it is read, explains it.
        for null, other_type in (
            (expression.left, right_type),
            (expression.right, left_type),
        ):
            if other_type.kind is ValueTypeKind.KNOWN and _reads_null_literal(
                (null,), row_schema, bare_value_expressions
            ):
                canonical = _canonical_value_type(other_type, type_expansions)
                typed, expected = resolved_binary_value_type(
                    expression.operator, canonical, canonical
                )
                if expected is None and not _has_error(diagnostics[start:]):
                    if typed.kind is ValueTypeKind.KNOWN:
                        result = dataclasses.replace(
                            typed, nullability=EffectiveNullability.NULLABLE
                        )
                    elif _of_numbers(
                        (canonical, canonical),
                        type_expansions,
                        division=expression.operator == "/",
                    ):
                        result = _UNKNOWN_NUMBER
                break
        else:
            # An operand that is a number of unknown type (`_UNKNOWN_NUMBER`).
            expected = _number_misfit(
                lambda types: resolved_binary_value_type(
                    expression.operator, types[0], types[1]
                )[1],
                (left_type, right_type),
                type_expansions,
            )
            if expected is None and _of_numbers(
                (left_type, right_type),
                type_expansions,
                division=expression.operator == "/",
            ):
                result = _UNKNOWN_NUMBER
    if expected is not None and expression.operator in {"+", "-", "*", "/", "%"}:
        # A NULL number takes another number's type, as the database does.
        null_number = _null_number_type(
            (expression.left, expression.right),
            (left_type, right_type),
            row_schema,
            bare_value_expressions,
            type_expansions,
            remainder=expression.operator == "%",
        )
        if null_number is not None:
            result, expected = null_number, None
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
    return result


def _canonical_value_type(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    enum: bool = False,
) -> ValueType:
    """Return a type alias value as the builtin type it expands to.

    With ``enum``, as for an aggregate argument, an alias of an enum also reads
    as that enum.
    """

    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.TYPE_ALIAS
    ):
        return value_type
    canonical = _canonical_resolved_type(value_type, type_expansions)
    if canonical is None or not (
        canonical.kind is TypeKind.BUILTIN or (enum and canonical.kind is TypeKind.ENUM)
    ):
        return value_type
    return ValueType(resolved_type=canonical, nullability=value_type.nullability)


def resolved_binary_value_type(
    operator: str, left_type: ValueType, right_type: ValueType
) -> tuple[ValueType, str | None]:
    """Original binary rule; no expression, name lookup or source elaboration."""
    if (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE, None
    if operator == "/":
        # SQL division: Int / Int is Int, truncated toward zero, and a Float
        # operand gives Float. A Decimal operand has no decided rule and stays
        # deferred; every other known operand type is not numeric.
        if _is_numeric(left_type) and _is_numeric(right_type):
            name = (
                "Float"
                if _is_builtin(left_type, "Float") or _is_builtin(right_type, "Float")
                else "Int"
            )
            return _builtin_value_type(name, EffectiveNullability.UNKNOWN), None
        if not all(
            _is_numeric(value_type) or _is_builtin(value_type, "Decimal")
            for value_type in (left_type, right_type)
        ):
            return _UNKNOWN_VALUE_TYPE, "numeric operands"
        return _UNKNOWN_VALUE_TYPE, None
    if operator in {"and", "or"}:
        if _is_builtin(left_type, "Bool") and _is_builtin(right_type, "Bool"):
            return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN), None
        return _UNKNOWN_VALUE_TYPE, "Bool operands"
    if operator == "%":
        if _is_builtin(left_type, "Int") and _is_builtin(right_type, "Int"):
            return _builtin_value_type("Int", EffectiveNullability.UNKNOWN), None
        return _UNKNOWN_VALUE_TYPE, "Int operands"
    if operator in {"+", "-", "*"}:
        name = _binary_arithmetic_result_type(operator, left_type, right_type)
        if name is not None:
            return _builtin_value_type(name, EffectiveNullability.UNKNOWN), None
        if operator == "+" and (
            _is_builtin(left_type, "Text") or _is_builtin(right_type, "Text")
        ):
            return (
                _UNKNOWN_VALUE_TYPE,
                "numeric operands; string concatenation is not supported yet",
            )
        return _UNKNOWN_VALUE_TYPE, "numeric operands"
    return _UNKNOWN_VALUE_TYPE, None


# Builtin families from the canonical scalar type registry trait vocabulary;
# an enum or a shape is a family of its own declaration. `Any` has none and
# stays unchecked (deferred).
_COMPARISON_FAMILIES = {
    "Int": "numeric",
    "Float": "numeric",
    "Decimal": "numeric",
    "Text": "text",
    "Bool": "boolean",
    "Date": "temporal",
    "Timestamp": "temporal",
    "UUID": "identifier",
    "Bytes": "binary",
    "Json": "json",
}
# A Text literal is the only constant form of these families; which literals
# are valid constants of them awaits a typed-constant decision.
_TEXT_CONSTANT_FAMILIES = frozenset({"temporal", "identifier", "binary", "json"})


def resolved_comparison_value_type(
    left_type: ValueType,
    right_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    literals: tuple[object, object] | None = None,
) -> tuple[ValueType, str | None]:
    """Comparison rule over resolved operands; no implicit cross-family
    conversion. A `Text` operand compares with a type of
    `_TEXT_CONSTANT_FAMILIES` only as a Text literal, and with an enum only
    as one of its labels: ``literals`` holds each operand's literal value,
    None for an operand that is not a literal (`comparison_literals`);
    without it such a pair is not refused."""

    resolved = tuple(
        _comparison_resolved_type(value_type, type_expansions)
        for value_type in (left_type, right_type)
    )
    families = tuple(_comparison_family(canonical) for canonical in resolved)
    if (
        None in families
        or families[0] == families[1]
        or any(
            family == "text"
            and _text_compares_with(
                cast(ResolvedType, resolved[1 - position]),
                None if literals is None else literals[position],
                checked=literals is not None,
            )
            for position, family in enumerate(families)
        )
    ):
        return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN), None
    return _UNKNOWN_VALUE_TYPE, "comparable operands"


def comparison_literals(
    left: Expression,
    right: Expression,
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
) -> tuple[object, object]:
    """Each operand's value where it is, after `let:` inlining, a literal, as
    emission writes it; None for any other operand."""

    return (
        _comparison_literal(left, row_schema, lets),
        _comparison_literal(right, row_schema, lets),
    )


def _comparison_literal(
    operand: Expression,
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
) -> object:
    node = let_value(operand, row_schema, lets)
    return cast(LiteralExpr, node).value if type(node) is LiteralExpr else None


def _operands_do_not_compare(
    operands: Sequence[tuple[Expression, ValueType]],
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether two of ``operands`` do not compare
    (`resolved_comparison_value_type`). An operand of no family compares with
    any, two of one family always compare, and whether two of different
    families do follows from the families and, for a `Text` operand, its
    literal value, so an operand is compared only with the first earlier
    operand of each such key of another family. Two families other than
    `Text` do not compare, so only the first operands of at most two such
    families meet every `Text` key."""

    seen: dict[object, dict[object, tuple[ValueType, object]]] = {}
    for operand, operand_type in operands:
        family = _comparison_family(
            _comparison_resolved_type(operand_type, type_expansions)
        )
        if family is None:
            continue
        literal = _comparison_literal(operand, row_schema, lets)
        key = literal if family == "text" and type(literal) is str else None
        keys = seen.setdefault(family, {})
        if key in keys:
            continue
        if any(
            resolved_comparison_value_type(
                operand_type, other_type, type_expansions, (literal, other_literal)
            )[1]
            is not None
            for other_family, other_keys in seen.items()
            if other_family != family
            for other_type, other_literal in other_keys.values()
        ):
            return True
        keys[key] = (operand_type, literal)
    return False


def _text_compares_with(other: ResolvedType, literal: object, *, checked: bool) -> bool:
    """Whether a `Text` operand, of literal value ``literal`` where ``checked``,
    compares with an operand of the type ``other`` of another family: a Text
    literal with a type that has no literal of its own, and a label of an
    enum with that enum."""

    if _comparison_family(other) in _TEXT_CONSTANT_FAMILIES:
        return not checked or type(literal) is str
    return other.kind is TypeKind.ENUM and (
        not checked
        or (
            type(literal) is str and literal in getattr(other.definition, "members", ())
        )
    )


def _ends_in_unpaired_like_escape(pattern: Expression) -> bool:
    """Whether a literal LIKE pattern ends in an unpaired `ESCAPE '!'` character.

    PostgreSQL rejects such a pattern and MySQL matches its final `!` literally.
    """

    if type(pattern) is not LiteralExpr or type(pattern.value) is not str:
        return False
    return (len(pattern.value) - len(pattern.value.rstrip("!"))) % 2 == 1


def resolved_like_value_type(
    left_type: ValueType,
    right_type: ValueType,
) -> tuple[ValueType, str | None]:
    """Return the closed Text/Text LIKE result without collation claims."""

    if (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE, None
    if not (_is_builtin(left_type, "Text") and _is_builtin(right_type, "Text")):
        return _UNKNOWN_VALUE_TYPE, "Text operands"
    return _builtin_value_type(
        "Bool",
        _join_nullability((left_type.nullability, right_type.nullability)),
    ), None


def _canonical_resolved_type(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    if value_type.kind is ValueTypeKind.UNKNOWN:
        return None
    resolved = value_type.resolved_type
    if resolved.kind is not TypeKind.TYPE_ALIAS:
        return resolved
    if type_expansions is None or not isinstance(resolved.definition, TypeDef):
        return None
    return type_expansions.get(resolved.definition.base)


def _shared_canonical_type(
    value_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    canonical_types = tuple(
        _canonical_resolved_type(value_type, type_expansions)
        for value_type in value_types
    )
    if not canonical_types or any(value_type is None for value_type in canonical_types):
        return None
    canonical = canonical_types[0]
    assert canonical is not None
    if any(
        value_type is None
        or value_type.kind is not canonical.kind
        or value_type.name != canonical.name
        or value_type.definition is not canonical.definition
        for value_type in canonical_types[1:]
    ):
        return None
    return canonical


def _membership_canonical_type(
    value_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    """Return the type an `in` test compares its value and options as.

    `v in (a, b)` tests `v == a` and `v == b`, so besides one shared canonical
    type it accepts `Decimal` mixed with `Int`, as those comparisons do, and
    compares them as `Decimal`; every other mix, `Float` included, is refused.
    """

    shared = _shared_canonical_type(value_types, type_expansions)
    if shared is not None:
        return shared
    names = {
        None
        if canonical is None or canonical.kind is not TypeKind.BUILTIN
        else canonical.name
        for canonical in (
            _canonical_resolved_type(value_type, type_expansions)
            for value_type in value_types
        )
    }
    if names == {"Decimal", "Int"}:
        return ResolvedType(name="Decimal", kind=TypeKind.BUILTIN)
    return None


def _membership_text_literal_types(
    literals: tuple[object, ...],
    value_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> tuple[ValueType, ...]:
    """Type a `Text` literal operand of an `in` test as the first operand of an
    enum or of a type whose only constant form is a Text literal, where a
    comparison with that operand admits the literal (a label of the enum):
    `status in ("paid", "shipped")` compares as `status == "paid"` does.
    ``literals`` holds each operand's literal value (`_comparison_literal`)."""

    target = next(
        (
            value_type
            for value_type in value_types
            if (resolved := _comparison_resolved_type(value_type, type_expansions))
            is not None
            and (
                resolved.kind is TypeKind.ENUM
                or _comparison_family(resolved) in _TEXT_CONSTANT_FAMILIES
            )
        ),
        None,
    )
    if target is None:
        return value_types
    resolved = cast(ResolvedType, _comparison_resolved_type(target, type_expansions))
    return tuple(
        ValueType(
            resolved_type=target.resolved_type, nullability=value_type.nullability
        )
        if _is_canonical_builtin(value_type, "Text", type_expansions)
        and _text_compares_with(resolved, literal, checked=True)
        else value_type
        for literal, value_type in zip(literals, value_types, strict=True)
    )


def _join_nullability(
    nullabilities: tuple[EffectiveNullability, ...],
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in nullabilities:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in nullabilities:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


def _comparison_resolved_type(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    if value_type.kind is not ValueTypeKind.KNOWN:
        return None
    resolved_type = value_type.resolved_type
    if type_expansions is not None and resolved_type.kind is TypeKind.TYPE_ALIAS:
        # Single-file row fields keep alias names; compare the canonical expansion.
        definition = resolved_type.definition
        assert isinstance(definition, TypeDef)
        resolved_type = type_expansions[definition.base]
    return resolved_type


def _comparison_family(resolved_type: ResolvedType | None) -> object:
    if resolved_type is None:
        return None
    if resolved_type.kind in {TypeKind.ENUM, TypeKind.SHAPE}:
        return (resolved_type.kind, id(resolved_type.definition))
    if resolved_type.kind is not TypeKind.BUILTIN:
        return None
    return _COMPARISON_FAMILIES.get(resolved_type.name)


def _between_value_type(
    expression: BetweenExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type an inclusive between predicate as two bound comparisons."""

    child_types = tuple(
        _infer(
            child,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        for child in (expression.value, expression.lower, expression.upper)
    )
    # `value >= lower and value <= upper` is always NULL when both comparisons
    # read the null literal; one null bound is never TRUE but may be FALSE.
    if _reads_null_literal(
        (expression.value,), row_schema, bare_value_expressions
    ) or _reads_null_literal(
        (expression.lower, expression.upper),
        row_schema,
        bare_value_expressions,
        every=True,
    ):
        diagnostics.append(_null_comparison_diagnostic(expression, remedy=None))
        return _UNKNOWN_VALUE_TYPE
    # A null bound leaves the test a Bool that the other bound decides.
    known = ((expression.value, child_types[0]),) + tuple(
        (bound, bound_type)
        for bound, bound_type in zip(
            (expression.lower, expression.upper), child_types[1:], strict=True
        )
        if not _reads_null_literal((bound,), row_schema, bare_value_expressions)
    )
    if any(child_type.kind is ValueTypeKind.UNKNOWN for _, child_type in known):
        return _UNKNOWN_VALUE_TYPE
    for bound, bound_type in known[1:]:
        _, expected = resolved_comparison_value_type(
            child_types[0],
            bound_type,
            type_expansions,
            comparison_literals(
                expression.value, bound, row_schema, bare_value_expressions
            ),
        )
        if expected is not None:
            diagnostics.append(
                _invalid_operator_operands_diagnostic(expression, expected=expected)
            )
            return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)


def _call_value_type(
    expression: CallExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    allow_aggregate_projection: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type one exact built-in call while suppressing Unknown cascades.

    An Unknown argument suppresses only the checks that need its type. An
    argument's own error also suppresses the name and window checks, the
    `sign`/`year`/`month`/`day` arity check and the `substr` bounds check; an
    unknown input row suppresses none of them. A call whose signature fixes
    its result type, `count` and `count_distinct` included, has that type
    beside an Unknown argument that no error explains, such as a field of a
    source without a shape, and its other arguments are checked, as the
    call has that type or fails wherever it runs.
    """

    function_name = _callee_name(expression)
    if expression.aggregate_order_by and function_name != "string_agg":
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message="Internal ORDER BY is only supported by string_agg",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    diagnostic_count = len(diagnostics)
    argument_types, erroneous = _call_argument_types(
        expression,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        allow_aggregate_projection=allow_aggregate_projection,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
        relation_columns=relation_columns,
    )
    for item in expression.aggregate_order_by:
        _infer(
            item.expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
    # An argument's own error explains an Unknown argument; the call then adds
    # nothing. An unknown input row explains no name, arity or window check,
    # since none of them reads an argument's type.
    unknown = any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    )
    cascade = len(diagnostics) > diagnostic_count and unknown
    # So is a read of a `let:` binding with an error of its own, or of a name
    # whose error is reported where it is bound or referenced (a forward or
    # self reference, a refused binding).
    explained = cascade or (
        unknown
        and _reads_erroneous_let(
            expression,
            row_schema,
            bare_value_expressions or {},
            (
                bare_value_expressions.erroneous
                if type(bare_value_expressions) is LetValues
                else set()
            )
            | (suppressed_unknown_names or set()),
        )
    )
    values = function_name in {"coalesce", "nullif"}
    nulls = _null_reads(
        expression.arguments,
        row_schema,
        bare_value_types,
        bare_value_expressions,
        values=values,
        erroneous=erroneous,
    )
    if values:
        contextual = _contextual_null_literal_types(
            expression.arguments,
            argument_types,
            value_types,
            type_expansions,
            nulls,
        )
        if contextual is None:
            # Beside an argument of unknown type the arguments of known type
            # must still have one type where two of them are of families that
            # do not compare, as the database then has no common type for
            # them; others keep the type of the argument of unknown type to
            # decide.
            known = tuple(
                (argument, argument_type)
                for argument, argument_type in zip(
                    expression.arguments, argument_types, strict=True
                )
                if argument_type.kind is ValueTypeKind.KNOWN
            )
            if (
                function_name == "coalesce"
                and not explained
                and _operands_do_not_compare(
                    known, row_schema, bare_value_expressions, type_expansions
                )
            ):
                _coalesce_value_type(
                    expression,
                    tuple(argument_type for _, argument_type in known),
                    type_expansions,
                    diagnostics,
                )
            return _UNKNOWN_VALUE_TYPE
        argument_types = contextual
        null_number = (
            None
            if len(argument_types) < 2
            or _shared_canonical_type(argument_types, type_expansions) is not None
            else _null_number_type(
                expression.arguments,
                argument_types,
                row_schema,
                bare_value_expressions,
                type_expansions,
                shared=_shared_canonical_type,
            )
        )
        if null_number is not None:
            # The NULL number takes the other numbers' type, as the database does.
            argument_types = tuple(
                dataclasses.replace(null_number, nullability=argument_type.nullability)
                for argument_type in argument_types
            )
        if function_name == "coalesce":
            return _coalesce_value_type(
                expression, argument_types, type_expansions, diagnostics
            )
        return _nullif_value_type(
            expression, argument_types, type_expansions, diagnostics
        )

    if is_semantic_aggregate_call(expression):
        if function_name == "string_agg" and not expression.aggregate_order_by:
            diagnostics.append(
                _call_diagnostic(
                    expression,
                    code="PIE-S2104",
                    message="Invalid arguments for aggregate string_agg: expected ORDER BY key",
                )
            )
            return _UNKNOWN_VALUE_TYPE
        if function_name != "string_agg" and expression.aggregate_order_by:
            diagnostics.append(
                _call_diagnostic(
                    expression,
                    code="PIE-S2104",
                    message=f"Invalid arguments for aggregate {function_name}: ORDER BY is only supported by string_agg",
                )
            )
            return _UNKNOWN_VALUE_TYPE
        if function_name == "string_agg":
            for argument_type in argument_types:
                if (
                    argument_type.kind is ValueTypeKind.KNOWN
                    and not _is_canonical_builtin(
                        argument_type, "Text", type_expansions
                    )
                ):
                    diagnostics.append(
                        _call_diagnostic(
                            expression,
                            code="PIE-S2104",
                            message=(
                                "Invalid arguments for aggregate string_agg: "
                                "expected two Text arguments"
                            ),
                        )
                    )
                    return _UNKNOWN_VALUE_TYPE
        if any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        ):
            # `count` and `count_distinct` count whatever they read: of a
            # field of unknown type, such as of a source without a shape, in
            # a form they accept, they are an `Int`.
            if (
                allow_aggregate_projection
                and not explained
                and function_name in {"count", "count_distinct"}
                and len(expression.arguments) == 1
                and has_unknown_field_reference(expression.arguments[0], value_types)
                and accepts_argument_form(
                    function_name,
                    expression.arguments[0],
                    let_expansions=bare_value_expressions,
                )
            ):
                return _builtin_value_type("Int", EffectiveNullability.NON_NULL)
            return _UNKNOWN_VALUE_TYPE
        if allow_aggregate_projection:
            result_type = _aggregate_value_type(
                expression,
                argument_types,
                let_expansions=bare_value_expressions,
                row_schema=row_schema,
                type_expansions=type_expansions,
            )
            if result_type is not None:
                return result_type
            if function_name == "string_agg":
                diagnostics.append(
                    _call_diagnostic(
                        expression,
                        code="PIE-S2104",
                        message="Invalid arguments for aggregate string_agg: expected two Text arguments",
                    )
                )
        return _UNKNOWN_VALUE_TYPE

    if (
        function_name in {"sign", "year", "month", "day"}
        and any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        )
        and (cascade or len(argument_types) == 1)
    ):
        return (
            _UNKNOWN_VALUE_TYPE
            if explained
            else _builtin_value_type("Int", EffectiveNullability.UNKNOWN)
        )
    if function_name == "sign":
        if (
            len(argument_types) == 1
            and _is_canonical_builtin(argument_types[0], "Float", type_expansions)
            and _null_number_type(
                expression.arguments,
                argument_types,
                row_schema,
                bare_value_expressions,
                type_expansions,
            )
        ):
            # PostgreSQL and MySQL take the sign of a NULL number of any type.
            return _builtin_value_type("Int", EffectiveNullability.NULLABLE)
        return _sign_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
        )
    if function_name in {"year", "month", "day"}:
        return _civil_date_part_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
        )
    if function_name == "round":
        return _round_value_type(
            expression,
            argument_types,
            diagnostics,
            type_expansions=type_expansions,
            lets=bare_value_expressions,
        )
    if function_name == "date_trunc":
        return _date_trunc_value_type(
            expression,
            argument_types,
            diagnostics,
            type_expansions=type_expansions,
            lets=bare_value_expressions,
        )

    signature = BUILTIN_FUNCTIONS.get(function_name)
    if signature is None:
        if cascade:
            return _UNKNOWN_VALUE_TYPE
        from pietto.semantic.window_semantics import WINDOW_FUNCTION_NAMES

        if function_name in WINDOW_FUNCTION_NAMES:
            diagnostics.append(
                _window_without_spec_diagnostic(expression, function_name)
            )
            return _UNKNOWN_VALUE_TYPE
        diagnostics.append(_unknown_function_diagnostic(expression, function_name))
        return _UNKNOWN_VALUE_TYPE

    if len(argument_types) != len(signature.parameter_types):
        diagnostics.append(_wrong_arity_diagnostic(expression, signature))
        return _UNKNOWN_VALUE_TYPE

    argument_types = _contextual_fixed_null_literal_types(
        expression.arguments,
        argument_types,
        signature.parameter_types,
        value_types,
        nulls,
    )
    if function_name == "abs":
        # `abs` keeps an Int, Float or Decimal argument's type, so over an
        # argument of unknown type that no error explains it is a number of
        # unknown type; its signature, which also types a null argument, is
        # the Decimal one.
        if argument_types[0].kind is ValueTypeKind.UNKNOWN:
            return _UNKNOWN_VALUE_TYPE if explained else _UNKNOWN_NUMBER
        for name in ("Int", "Float"):
            if _is_canonical_builtin(argument_types[0], name, type_expansions):
                return _builtin_value_type(name, argument_types[0].nullability)
    if explained and any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ):
        # The `substr` bounds check reads only literals, so a silent Unknown
        # argument, such as a read of a `let:` binding with an error, does not
        # hide it.
        if (
            function_name == "substr"
            and not cascade
            and not _valid_static_substr_bounds(expression)
        ):
            diagnostics.append(_invalid_substr_bounds_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    mismatch = _builtin_argument_mismatch(
        expression, signature, argument_types, type_expansions
    )
    if mismatch is not None:
        diagnostics.append(mismatch[1])
        return _UNKNOWN_VALUE_TYPE

    if function_name == "substr" and not _valid_static_substr_bounds(expression):
        diagnostics.append(_invalid_substr_bounds_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    if function_name == "matches":
        return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)

    return _builtin_value_type(
        signature.return_type,
        _join_nullability(
            tuple(argument_type.nullability for argument_type in argument_types)
        ),
    )


def _builtin_argument_mismatch(
    expression: CallExpr,
    signature: BuiltinFunction,
    argument_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> tuple[int, Diagnostic] | None:
    """The first known argument that the closed builtin signature refuses."""

    for position, (argument_type, expected_name) in enumerate(
        zip(argument_types, signature.parameter_types, strict=True), start=1
    ):
        if argument_type.kind is ValueTypeKind.UNKNOWN:
            continue
        if _is_canonical_builtin(argument_type, expected_name, type_expansions) or (
            signature.name == "abs"
            and any(
                _is_canonical_builtin(argument_type, name, type_expansions)
                for name in ("Int", "Float")
            )
        ):
            continue
        return position, _wrong_argument_type_diagnostic(
            expression,
            signature,
            position=position,
            expected_name=(
                "Int, Float or Decimal" if signature.name == "abs" else expected_name
            ),
            actual_name=argument_type.resolved_type.name,
        )
    return None


def null_arithmetic_argument_diagnostics(
    expression: Expression,
    row_schema: RowSchema,
    value_types: Mapping[Expression, ValueType],
    let_expressions: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    reported_errors: frozenset[Diagnostic],
) -> tuple[Diagnostic, ...]:
    """Closed-call type errors whose failing value reads typed NULL arithmetic.

    These concrete errors survive an aggregate's shape refusal; unrelated
    argument errors and shapes keep their existing diagnostics. A mismatch
    must already be in ``reported_errors`` before its value is followed;
    typing is never replayed to manufacture an error for this check.
    """

    def reads_typed_null_arithmetic(value: Expression) -> bool:
        pending = [value]
        seen: set[int] = set()
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            typed = value_types.get(node)
            if typed is None or not _is_number(typed, type_expansions):
                continue
            if type(node) is BinaryExpr:
                binary = cast(BinaryExpr, node)
                if binary.operator in {"+", "-", "*", "/", "%"} and _reads_null_literal(
                    (binary.left, binary.right), row_schema, let_expressions
                ):
                    return True
            if type(node) is NameExpr:
                bound = let_value(node, row_schema, let_expressions)
                if bound is not node:
                    pending.append(bound)
            elif type(node) is CallExpr and _callee_name(cast(CallExpr, node)) in {
                "abs",
                "nullif",
            }:
                pending.extend(cast(CallExpr, node).arguments)
            else:
                pending.extend(_null_operands(node))
        return False

    found: list[Diagnostic] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        pending.extend(reversed(_captured_field_children(node)))
        if type(node) is not CallExpr:
            continue
        call = cast(CallExpr, node)
        if value_types.get(call, _UNKNOWN_VALUE_TYPE).kind is not ValueTypeKind.UNKNOWN:
            continue
        signature = BUILTIN_FUNCTIONS.get(_callee_name(call))
        if signature is None or len(call.arguments) != len(signature.parameter_types):
            continue
        argument_types = tuple(
            value_types.get(argument, _UNKNOWN_VALUE_TYPE)
            for argument in call.arguments
        )
        if any(
            value_type.kind is ValueTypeKind.UNKNOWN
            and value_type is not _UNKNOWN_NUMBER
            for value_type in argument_types
        ):
            continue
        mismatch = _builtin_argument_mismatch(
            call, signature, argument_types, type_expansions
        )
        if mismatch is None:
            mismatch = _number_argument_mismatch(
                call, argument_types, signature.parameter_types
            )
        if (
            mismatch is not None
            and mismatch[1] in reported_errors
            and reads_typed_null_arithmetic(call.arguments[mismatch[0] - 1])
        ):
            found.append(mismatch[1])
    return tuple(found)


def condition_value_type(
    expression: Expression,
    value_type: ValueType,
    row_schema: RowSchema | None = None,
    lets: Mapping[str, Expression] | None = None,
) -> ValueType:
    """The type a condition reads ``expression`` of ``value_type`` as, where
    no error explains an unknown type (`unknown_explained`): a call of a
    built-in function whose signature fixes its result type (each of them
    but `coalesce` and `nullif`), of unknown type because the type of an
    argument is unknown, as over a source without a shape, has that type, of
    unknown nullability, as the call has that type or fails wherever it
    runs, also as the value of a `let:` name of ``lets`` (`let_value`, with
    the fields of ``row_schema``); anything else has ``value_type``."""

    if value_type.kind is not ValueTypeKind.UNKNOWN:
        return value_type
    if lets is not None:
        expression = let_value(expression, row_schema or RowSchema(), lets)
    if type(expression) is not CallExpr:
        return value_type
    call = cast(CallExpr, expression)
    name = _callee_name(call)
    if name in {"sign", "year", "month", "day"}:
        result = "Int" if len(call.arguments) == 1 else None
    else:
        signature = BUILTIN_FUNCTIONS.get(name)
        result = (
            None
            if signature is None
            or len(call.arguments) != len(signature.parameter_types)
            else signature.return_type
        )
    if result is None:
        return value_type
    return _builtin_value_type(result, EffectiveNullability.UNKNOWN)


def unknown_explained(
    expression: Expression,
    diagnostics: Sequence[Diagnostic],
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
) -> bool:
    """Whether an error explains an unknown type in ``expression``: one of
    ``diagnostics``, those typing it reported, or one of a `let:` binding of
    ``lets`` it reads (`_reads_erroneous_let`), as a read of such a binding
    is unknown. A condition then refuses no unknown type, as an operator
    with such an operand adds nothing."""

    return _has_error(diagnostics) or (
        type(lets) is LetValues
        and _reads_erroneous_let(expression, row_schema, lets, lets.erroneous)
    )


def _not_bool_condition(
    expression: Expression,
    value_type: ValueType,
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether a condition that reads ``expression`` of ``value_type``, with
    no error explaining an unknown type, is not a Bool
    (`condition_value_type`), a number of unknown type (`_UNKNOWN_NUMBER`)
    included."""

    condition = condition_value_type(expression, value_type, row_schema, lets)
    return value_type is _UNKNOWN_NUMBER or (
        condition.kind is ValueTypeKind.KNOWN
        and not _is_canonical_builtin(condition, "Bool", type_expansions)
    )


# A number of unknown type: a quotient with a `Decimal` operand, which has no
# type while `Decimal` division is not specified, arithmetic (`+`, `-`, `*`,
# `/`, `%` or a sign) over such a number and numbers, and a `coalesce`,
# `nullif` or conditional of such numbers, where a null takes their type
# (`_nulls_as_numbers`, `_of_numbers`). It equals
# `_UNKNOWN_VALUE_TYPE`, so whatever reads the type sees an unknown type, but
# typing returns this object for it, as it does for a `let:` name bound to
# it, so each use tells in O(1) that it reads a number and refuses one that
# no number fits (`_number_misfit`).
_UNKNOWN_NUMBER = ValueType(
    resolved_type=_UNKNOWN_VALUE_TYPE.resolved_type,
    nullability=_UNKNOWN_VALUE_TYPE.nullability,
    kind=ValueTypeKind.UNKNOWN,
)
# The types a number can have.
_NUMBER_TYPES = tuple(
    ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=EffectiveNullability.UNKNOWN,
    )
    for name in ("Int", "Float", "Decimal")
)


def is_unknown_number(value_type: ValueType | None) -> bool:
    """Whether typing typed an expression as a number of unknown type
    (`_UNKNOWN_NUMBER`), such as `amount / 2` of a `Decimal` field."""

    return value_type is _UNKNOWN_NUMBER


def _is_number(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    """Whether ``value_type``, an alias read as the type it expands to, is
    `Int`, `Float` or `Decimal`, or is a number of unknown type."""

    canonical = _canonical_value_type(value_type, type_expansions)
    return (
        value_type is _UNKNOWN_NUMBER
        or _is_numeric(canonical)
        or _is_builtin(canonical, "Decimal")
    )


def _of_numbers(
    operand_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    division: bool = False,
) -> bool:
    """Whether a value of unknown type that is one of, or is computed from,
    operands of ``operand_types`` alone is a number of unknown type: each is
    a number (`_is_number`), and one of them is of unknown type or, in a
    ``division``, a `Decimal`."""

    return all(
        _is_number(operand_type, type_expansions) for operand_type in operand_types
    ) and any(
        operand_type is _UNKNOWN_NUMBER
        or (
            division
            and _is_builtin(
                _canonical_value_type(operand_type, type_expansions), "Decimal"
            )
        )
        for operand_type in operand_types
    )


def _nulls_as_numbers(
    operand_types: tuple[ValueType, ...],
    nulls: Callable[[], tuple[bool, ...]],
) -> tuple[ValueType, ...]:
    """``operand_types`` of the arguments of a `coalesce` or `nullif` or the
    branches of a conditional, where a null among them (``nulls``,
    `_null_reads`) beside a number of unknown type is one, as a null there
    takes the type of the values beside it."""

    if not any(operand_type is _UNKNOWN_NUMBER for operand_type in operand_types):
        return operand_types
    return tuple(
        _UNKNOWN_NUMBER if null else operand_type
        for operand_type, null in zip(operand_types, nulls(), strict=True)
    )


def _number_misfit[T](
    rule: Callable[[tuple[ValueType, ...]], T | None],
    operand_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> T | None:
    """What ``rule``, which checks operands of ``operand_types`` and returns
    what it refuses, reports where one of them is a number of unknown type
    (`_UNKNOWN_NUMBER`) that no number fits: with every number among them
    read as one numeric type, each numeric type is refused. A number thus
    fits beside numbers, of whatever types, and any other operand of unknown
    type leaves the rule unread, as it does without a number."""

    if not any(
        operand_type is _UNKNOWN_NUMBER for operand_type in operand_types
    ) or any(
        operand_type.kind is ValueTypeKind.UNKNOWN
        and operand_type is not _UNKNOWN_NUMBER
        for operand_type in operand_types
    ):
        return None
    found = [
        rule(
            tuple(
                number_type
                if _is_number(operand_type, type_expansions)
                else _canonical_value_type(operand_type, type_expansions)
                for operand_type in operand_types
            )
        )
        for number_type in _NUMBER_TYPES
    ]
    return None if any(problem is None for problem in found) else found[0]


def _number_test_expected(
    expression: ComparisonExpr | BetweenExpr | MembershipExpr,
    value_types: Mapping[Expression, ValueType],
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> str | None:
    """What a comparison, `like`, `between` or `in` test whose operands are
    typed in ``value_types`` expects where one of them is a number of
    unknown type that no number fits (`_number_misfit`), as in
    `amount / 2 == "x"` or `amount / 2 in ("x", "y")`, or None."""

    if isinstance(expression, ComparisonExpr):
        operands = (expression.left, expression.right)
    elif isinstance(expression, BetweenExpr):
        # A null bound leaves the test to the other bound.
        operands = (expression.value,) + tuple(
            bound
            for bound in (expression.lower, expression.upper)
            if not _reads_null_literal((bound,), row_schema, lets)
        )
    else:
        operands = (expression.value, *expression.options)
    operand_types = tuple(
        value_types.get(operand, _UNKNOWN_VALUE_TYPE) for operand in operands
    )
    if isinstance(expression, MembershipExpr):
        return _number_misfit(
            lambda types: (
                None
                if _membership_canonical_type(types, type_expansions) is not None
                else "same canonical membership operands"
            ),
            operand_types,
            type_expansions,
        )
    if isinstance(expression, ComparisonExpr) and expression.operator in {
        "like",
        "not like",
    }:
        return _number_misfit(
            lambda types: resolved_like_value_type(types[0], types[1])[1],
            operand_types,
            type_expansions,
        )
    # A comparison, and a `between` of its value with each bound.
    return _number_misfit(
        lambda types: next(
            (
                expected
                for bound_type in types[1:]
                if (
                    expected := resolved_comparison_value_type(
                        types[0], bound_type, type_expansions
                    )[1]
                )
                is not None
            ),
            None,
        ),
        operand_types,
        type_expansions,
    )


def _number_call_type(
    expression: CallExpr,
    value_type: ValueType,
    value_types: Mapping[Expression, ValueType],
    diagnostics: list[Diagnostic],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    nulls: Callable[[], tuple[bool, ...]],
) -> ValueType:
    """The type of a built-in call, typed as ``value_type`` with no
    diagnostic, over a number of unknown type (`_UNKNOWN_NUMBER`): a
    `coalesce` or `nullif` of numbers, where a null argument (``nulls``,
    `_null_reads`) takes their type, is one, and an argument that no number
    fits is PIE-S2104 (`_number_misfit`), as in `coalesce(label, amount / 2)`
    or, for a parameter of a type that is no number, `lower(amount / 2)`
    (`got numeric`)."""

    name = _callee_name(expression)
    arguments = expression.arguments
    if name in {"coalesce", "nullif"}:
        if len(arguments) < 2 or (name == "nullif" and len(arguments) > 2):
            # A wrong argument count is left to emission, as beside any other
            # argument of unknown type.
            return value_type
        check = _coalesce_value_type if name == "coalesce" else _nullif_value_type

        def refused(types: tuple[ValueType, ...]) -> Diagnostic | None:
            found: list[Diagnostic] = []
            check(expression, types, type_expansions, found)
            return found[0] if found else None

        argument_types = _nulls_as_numbers(
            tuple(
                value_types.get(argument, _UNKNOWN_VALUE_TYPE) for argument in arguments
            ),
            nulls,
        )
        diagnostic = _number_misfit(refused, argument_types, type_expansions)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
            return _UNKNOWN_VALUE_TYPE
        if _of_numbers(argument_types, type_expansions):
            return _UNKNOWN_NUMBER
        return value_type
    signature = BUILTIN_FUNCTIONS.get(name)
    parameters = (
        ("Date or Timestamp",)
        if name in {"year", "month", "day"}
        else None
        if signature is None
        else signature.parameter_types
    )
    if parameters is None or len(parameters) != len(arguments):
        return value_type
    mismatch = _number_argument_mismatch(
        expression,
        tuple(value_types.get(argument, _UNKNOWN_VALUE_TYPE) for argument in arguments),
        parameters,
    )
    if mismatch is not None:
        diagnostics.append(mismatch[1])
        return _UNKNOWN_VALUE_TYPE
    return value_type


# The numeric types, each implicitly converted to the next where the database
# needs one type for two numbers.
_NUMBER_NAMES = ("Int", "Decimal", "Float")
# Whether a NULL number fits beside numbers of other types (`_null_number_type`)
# and a `def` parameter of another numeric type (`_fits_null_number`): in a
# single file (`null_numbers`). A project relation does not complete with one,
# so it keeps the typed twin's diagnostic there.
_NULL_NUMBERS: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_NULL_NUMBERS", default=False
)


@contextlib.contextmanager
def null_numbers() -> Iterator[None]:
    """Type NULL numbers beside numbers of other types inside the block."""

    token = _NULL_NUMBERS.set(True)
    try:
        yield
    finally:
        _NULL_NUMBERS.reset(token)


def _fits_null_number(
    canonical: ResolvedType, slot: InlinedArgument, is_null: Callable[[], bool]
) -> bool:
    """Whether an argument of the number type ``canonical`` that is always
    null (``is_null``) fits the numeric parameter of ``slot``. The call is
    typed with the argument written in its body, where the NULL number takes
    the type of the numbers beside it (`_null_number_type`) as the database
    does, so no value depends on the parameter's own number type."""

    return (
        _NULL_NUMBERS.get()
        and canonical.name in _NUMBER_NAMES
        and slot.type_name in _NUMBER_NAMES
        and is_null()
    )


def _written_nulls(
    row_schema: RowSchema, lets: Mapping[str, Expression] | None
) -> dict[str, bool]:
    """Whether each `let:` name of ``lets`` is always null (`always_null`)
    with the names before it written in, in binding order, so a chain needs
    no recursion. A name with an error of its own is not written in."""

    erroneous = lets.erroneous if type(lets) is LetValues else set()
    names: dict[str, bool] = {}
    for name, value in (lets or {}).items():
        if not has_bare_field(row_schema, name) and name not in erroneous:
            names[name] = always_null(value, names)
    return names


def _null_number_type(
    expressions: Sequence[Expression],
    value_types: Sequence[ValueType],
    row_schema: RowSchema,
    lets: Mapping[str, Expression] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    remainder: bool = False,
    shared: Callable[
        [tuple[ValueType, ...], Mapping[TypeExpr, ResolvedType] | None],
        ResolvedType | None,
    ]
    | None = None,
) -> ValueType | None:
    """The type that numbers of ``value_types`` have together when one of
    them is a NULL number: always null (`always_null`, such as `None + d`)
    and of a known `Int`, `Decimal` or `Float` type. Its type has no value to
    keep exact, and PostgreSQL and MySQL convert an `Int` to a `Decimal` and
    either to a `Float` where they need one type, so a NULL number fits beside
    numbers of other types; the widest decides the type, nullable. A
    ``remainder`` takes no `Float`, which PostgreSQL has no `%` for. The
    operands that are not always null keep the operator's own rule
    (``shared``), so a NULL number lets no other numbers of different types
    mix. None outside `null_numbers`."""

    if not _NULL_NUMBERS.get():
        return None
    names = []
    for value_type in value_types:
        canonical = _canonical_value_type(value_type, type_expansions)
        name = next(
            (
                name
                for name in _NUMBER_NAMES
                if value_type.kind is ValueTypeKind.KNOWN
                and _is_builtin(canonical, name)
            ),
            None,
        )
        if name is None or (remainder and name == "Float"):
            return None
        names.append((name, canonical))
    written = _written_nulls(row_schema, lets)
    nulls = [always_null(expression, written) for expression in expressions]
    if not any(nulls):
        return None
    others = tuple(
        value_type
        for value_type, null in zip(value_types, nulls, strict=True)
        if not null
    )
    if (
        shared is not None
        and len(others) > 1
        and shared(others, type_expansions) is None
    ):
        return None
    widest = max(names, key=lambda item: _NUMBER_NAMES.index(item[0]))[1]
    return ValueType(
        resolved_type=widest.resolved_type, nullability=EffectiveNullability.NULLABLE
    )


def _number_argument_mismatch(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    parameters: tuple[str, ...],
) -> tuple[int, Diagnostic] | None:
    """The original numeric fallback's first parameter that no number fits."""

    for position, (argument_type, parameter) in enumerate(
        zip(argument_types, parameters, strict=True), start=1
    ):
        if (
            parameter not in {"Int", "Float", "Decimal"}
            and argument_type is _UNKNOWN_NUMBER
        ):
            return position, _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    f"Invalid argument type for function {_callee_name(expression)} at position "
                    f"{position}: expected {parameter}, got numeric"
                ),
            )
    return None


def _coalesce_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    diagnostics: list[Diagnostic],
) -> ValueType:
    if len(argument_types) < 2:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid arguments for function coalesce: expected at least 2, got "
                    f"{len(argument_types)}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(argument_types, type_expansions)
    if canonical is None:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument types for function coalesce: expected same "
                    "canonical type"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    if EffectiveNullability.NON_NULL in {
        argument_type.nullability for argument_type in argument_types
    }:
        nullability = EffectiveNullability.NON_NULL
    elif EffectiveNullability.UNKNOWN in {
        argument_type.nullability for argument_type in argument_types
    }:
        nullability = EffectiveNullability.UNKNOWN
    else:
        nullability = EffectiveNullability.NULLABLE
    return ValueType(resolved_type=canonical, nullability=nullability)


def _nullif_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    diagnostics: list[Diagnostic],
) -> ValueType:
    if len(argument_types) != 2:
        diagnostics.append(_wrong_arity_diagnostic(expression, _NULLIF_SIGNATURE))
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(argument_types, type_expansions)
    if canonical is None:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument types for function nullif: expected same "
                    "canonical comparable type"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    left_nullability = argument_types[0].nullability
    return ValueType(
        resolved_type=canonical,
        nullability=(
            EffectiveNullability.NULLABLE
            if left_nullability is EffectiveNullability.NON_NULL
            else left_nullability
        ),
    )


def _is_null_literal(expression: Expression) -> bool:
    return isinstance(expression, LiteralExpr) and expression.value is None


def _null_reads(
    expressions: Sequence[Expression],
    row_schema: RowSchema,
    bare_value_types: Mapping[str, ValueType] | None,
    let_expressions: Mapping[str, Expression] | None,
    *,
    values: bool = False,
    erroneous: set[int] | None = None,
) -> tuple[bool, ...]:
    """Whether each of ``expressions`` is a null that takes its type from where
    it stands: the null literal, or a `let:` name read as its binding (in
    ``bare_value_types``) whose value, inlined as emission inlines it, is the
    null literal; never a ``def`` argument that does not fit its parameter,
    which stays Unknown to the expression around it. With ``values``, where
    the expressions are values that must have one type (conditional
    branches, `coalesce` and `nullif` arguments, `in` operands), so is a
    conditional, `coalesce` or `nullif` whose every value is such a null:
    beside a value of another type it is that null, so the type of the
    values beside it is the type of all of them. An Unknown expression
    whose own typing reported an error (its identity in ``erroneous``) never
    takes a contextual type; errors in a known sibling do not prevent it."""

    def lets(expression: Expression) -> Mapping[str, Expression] | None:
        return (
            let_expressions
            if type(expression) is NameExpr
            and bare_value_types is not None
            and expression.name in bare_value_types
            else None
        )

    def reads(expression: Expression) -> bool:
        return _reads_null_literal((expression,), row_schema, lets(expression))

    # This call has one row and binding scope; None marks an active node.
    null_values: dict[tuple[int, bool], bool | None] = {}

    def reads_value(expression: Expression) -> bool:
        pending: list[
            tuple[Expression, bool, tuple[tuple[Expression, bool], ...] | None]
        ] = [(expression, False, None)]
        while pending:
            node, alias, children = pending.pop()
            key = (id(node), alias)
            if children is not None:
                null_values[key] = all(
                    null_values[(id(child), chained)] for child, chained in children
                )
                continue
            if key in null_values:
                if null_values[key] is None:
                    null_values[key] = False
                continue
            null_values[key] = False
            if not all(slot.nullable for slot in inlined_arguments(node)):
                continue
            if _is_null_literal(node):
                null_values[key] = True
                continue
            if type(node) is NameExpr:
                bindings = let_expressions if alias else lets(node)
                name = cast(NameExpr, node).name
                if (
                    bindings is None
                    or name not in bindings
                    or has_bare_field(row_schema, name)
                    or (type(bindings) is LetValues and name in bindings.erroneous)
                ):
                    continue
                value = bindings[name]
                children = ((value, type(value) is NameExpr),)
            elif type(node) is ConditionalExpr:
                conditional = cast(ConditionalExpr, node)
                children = (
                    (conditional.when_true, False),
                    (conditional.when_false, False),
                )
            elif (
                type(node) is CallExpr
                and _callee_name(cast(CallExpr, node)) in {"coalesce", "nullif"}
                and cast(CallExpr, node).arguments
            ):
                children = tuple(
                    (child, False) for child in cast(CallExpr, node).arguments
                )
            else:
                continue
            null_values[key] = None
            pending.append((node, alias, children))
            pending.extend(
                (child, chained, None) for child, chained in reversed(children)
            )
        return null_values[(id(expression), False)] is True

    return tuple(
        False
        if erroneous is not None and id(expression) in erroneous
        else (reads_value if values else reads)(expression)
        for expression in expressions
    )


def _reads_null_literal(
    expressions: Sequence[Expression],
    row_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
    *,
    every: bool = False,
) -> bool:
    """Whether any (or every) operand is, after `let:` inlining, the null literal.

    A null ``def`` argument that does not fit its parameter is not, also when
    it is a `let:` name bound to null: that is PIE-S2395, and its use is
    Unknown to the expression around it.
    """

    reads = (
        _is_null_literal(chain[-1])
        and all(slot.nullable for value in chain for slot in inlined_arguments(value))
        for chain in (
            _let_chain(expression, row_schema, let_expressions)
            for expression in expressions
        )
    )
    return all(reads) if every else any(reads)


def _contextual_null_literal_type(resolved: ResolvedType | str) -> ValueType:
    return ValueType(
        resolved_type=(
            _builtin_value_type(resolved, EffectiveNullability.NULLABLE).resolved_type
            if isinstance(resolved, str)
            else resolved
        ),
        nullability=EffectiveNullability.NULLABLE,
    )


def _contextual_null_literal_types(
    expressions: tuple[Expression, ...],
    value_types: tuple[ValueType, ...],
    recorded: dict[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    nulls: tuple[bool, ...],
    *,
    membership: bool = False,
) -> tuple[ValueType, ...] | None:
    """Type only NULLs (``nulls``, `_null_reads`) from one local approved
    common-type context.

    With ``membership``, as for an `in` list, the context is the type the test
    compares as.
    """

    if any(
        value_type.kind is ValueTypeKind.UNKNOWN and not null
        for value_type, null in zip(value_types, nulls, strict=True)
    ):
        return None
    known = tuple(
        value_type
        for value_type in value_types
        if value_type.kind is ValueTypeKind.KNOWN
    )
    if not known:
        return None
    canonical = (_membership_canonical_type if membership else _shared_canonical_type)(
        known, type_expansions
    )
    if canonical is None:
        return value_types
    result = []
    for expression, value_type, null in zip(
        expressions, value_types, nulls, strict=True
    ):
        if value_type.kind is ValueTypeKind.UNKNOWN and null:
            value_type = _contextual_null_literal_type(canonical)
            recorded[expression] = value_type
        result.append(value_type)
    return tuple(result)


def _contextual_fixed_null_literal_types(
    expressions: tuple[Expression, ...],
    value_types: tuple[ValueType, ...],
    parameter_types: tuple[str, ...],
    recorded: dict[Expression, ValueType],
    nulls: tuple[bool, ...],
) -> tuple[ValueType, ...]:
    """Type NULLs (``nulls``, `_null_reads`) only where one closed built-in
    parameter type selects it."""

    result = []
    for expression, value_type, parameter_type, null in zip(
        expressions, value_types, parameter_types, nulls, strict=True
    ):
        if value_type.kind is ValueTypeKind.UNKNOWN and null:
            value_type = _contextual_null_literal_type(parameter_type)
            recorded[expression] = value_type
        result.append(value_type)
    return tuple(result)


def _sign_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    if len(argument_types) != 1:
        diagnostics.append(_wrong_arity_diagnostic(expression, _SIGN_SIGNATURE))
        return _UNKNOWN_VALUE_TYPE
    argument_type = argument_types[0]
    if not (
        _is_canonical_builtin(argument_type, "Int", type_expansions)
        or _is_canonical_builtin(argument_type, "Decimal", type_expansions)
    ):
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument type for function sign at position 1: "
                    f"expected Int or Decimal, got {argument_type.resolved_type.name}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Int", argument_type.nullability)


def _civil_date_part_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    if len(argument_types) != 1:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    f"Invalid arguments for function {_callee_name(expression)}: "
                    f"expected 1, got {len(argument_types)}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    argument_type = argument_types[0]
    if not (
        _is_canonical_builtin(argument_type, "Date", type_expansions)
        or _is_canonical_builtin(argument_type, "Timestamp", type_expansions)
    ):
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    f"Invalid argument type for function {_callee_name(expression)} at "
                    "position 1: expected Date or Timestamp, got "
                    f"{argument_type.resolved_type.name}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Int", argument_type.nullability)


def _static_literal(
    expression: Expression,
    lets: Mapping[str, Expression] | None,
) -> str | int | None:
    """Resolve an admitted `let` chain only when it ends at one literal."""

    seen: set[str] = set()
    while isinstance(expression, NameExpr) and lets is not None:
        if expression.name in seen or expression.name not in lets:
            return None
        seen.add(expression.name)
        expression = lets[expression.name]
    if isinstance(expression, LiteralExpr):
        if type(expression.value) is str:
            return expression.value
        if type(expression.value) is int:
            return expression.value
    if (
        isinstance(expression, UnaryExpr)
        and expression.operator == "-"
        and isinstance(expression.operand, LiteralExpr)
        and type(expression.operand.value) is int
    ):
        return -expression.operand.value
    return None


def _round_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    lets: Mapping[str, Expression] | None,
) -> ValueType:
    if len(argument_types) not in {1, 2}:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=f"Invalid arguments for function round: expected 1 or 2, got {len(argument_types)}",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    value = argument_types[0]
    if _is_canonical_builtin(value, "Float", type_expansions):
        if len(argument_types) == 1:
            return _builtin_value_type("Float", value.nullability)
    elif _is_canonical_builtin(value, "Decimal", type_expansions):
        if len(argument_types) == 1:
            return _builtin_value_type("Decimal", value.nullability)
        scale = _static_literal(expression.arguments[1], lets)
        if type(scale) is int and -30 <= scale <= 30:
            return _builtin_value_type("Decimal", value.nullability)
    diagnostics.append(
        _call_diagnostic(
            expression,
            code="PIE-S2104",
            message="Invalid arguments for function round",
        )
    )
    return _UNKNOWN_VALUE_TYPE


def _date_trunc_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    lets: Mapping[str, Expression] | None,
) -> ValueType:
    if len(argument_types) != 2:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=f"Invalid arguments for function date_trunc: expected 2, got {len(argument_types)}",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    unit = _static_literal(expression.arguments[0], lets)
    value = argument_types[1]
    if type(unit) is str:
        if _is_canonical_builtin(value, "Date", type_expansions) and unit in {
            "year",
            "month",
            "day",
        }:
            return _builtin_value_type("Date", value.nullability)
        if _is_canonical_builtin(value, "Timestamp", type_expansions) and unit in {
            "year",
            "month",
            "day",
            "hour",
            "minute",
        }:
            return _builtin_value_type("Timestamp", value.nullability)
    diagnostics.append(
        _call_diagnostic(
            expression,
            code="PIE-S2104",
            message="Invalid arguments for function date_trunc",
        )
    )
    return _UNKNOWN_VALUE_TYPE


def _invalid_substr_bounds_diagnostic(expression: CallExpr) -> Diagnostic:
    return _call_diagnostic(
        expression,
        code="PIE-S2104",
        message=(
            "Invalid arguments for function substr: start must be a positive "
            "Int literal and count must be a non-negative Int literal"
        ),
    )


def _valid_static_substr_bounds(expression: CallExpr) -> bool:
    start, count = expression.arguments[1:]
    return (
        isinstance(start, LiteralExpr)
        and type(start.value) is int
        and start.value > 0
        and isinstance(count, LiteralExpr)
        and type(count.value) is int
        and count.value >= 0
    )


def _call_argument_types(
    expression: CallExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    allow_aggregate_projection: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    relation_columns: Mapping[Expression, ValueType] | None,
) -> tuple[tuple[ValueType, ...], set[int]]:
    if (
        allow_aggregate_projection
        and is_semantic_aggregate_call(expression)
        and len(expression.arguments) == 1
        and not contains_semantic_aggregate(expression.arguments[0])
    ):
        argument = expression.arguments[0]
        temporary_diagnostics: list[Diagnostic] = []
        function_name = _callee_name(expression)
        # A `min` or `max` argument that reads a `let:` name is refused
        # (PIE-S2315, `extremum_reads_let`) after the checks that its names
        # with their binding types make, as for the value written in place.
        argument_bare_value_types = (
            bare_value_types
            if aggregate_argument_can_use_let_scope(
                function_name,
                argument,
                bare_value_expressions,
            )
            or extremum_reads_let(
                function_name, argument, bare_value_expressions, row_schema
            )
            else None
        )
        # A `let:` name that an aggregate reads is checked with its binding's
        # type, not written in (`LetValues`), and is null where its binding
        # written in is, as a read of it written in place is.
        binding = (
            cast(LetValues, bare_value_expressions).written.get(
                cast(NameExpr, argument).name
            )
            if argument_bare_value_types is not None
            and type(bare_value_expressions) is LetValues
            and type(argument) is NameExpr
            else None
        )
        # An aggregate reads a type alias argument as the type it expands to.
        argument_type = _canonical_value_type(
            _infer(
                argument,
                row_schema,
                value_types,
                temporary_diagnostics,
                report_unknown_name=report_unknown_name,
                field_qualifier=field_qualifier,
                bare_value_types=argument_bare_value_types,
                bare_value_expressions=(
                    None
                    if bare_value_expressions is None
                    else MappingProxyType(bare_value_expressions)
                ),
                suppressed_unknown_names=suppressed_unknown_names,
                type_expansions=type_expansions,
                relation_columns=relation_columns,
                argument_null=None if binding is None else binding.always_null,
            ),
            type_expansions,
            enum=True,
        )
        if (
            is_supported_semantic_aggregate_argument_expression(
                function_name,
                argument,
                argument_type,
                let_expansions=bare_value_expressions,
            )
            or has_unknown_field_reference(argument, value_types)
            # A def argument in it that does not fit is unknown to the
            # aggregate, as such a field is, and its PIE-S2395 is its error.
            or any(
                diagnostic.code == "PIE-S2395" for diagnostic in temporary_diagnostics
            )
            or (
                isinstance(value_types, (_FailedRelationshipTypes, _WrittenTypes))
                and any(
                    diagnostic is owned
                    for diagnostic in temporary_diagnostics
                    for failure in value_types.failures.values()
                    for owned in failure.diagnostics
                )
            )
        ):
            diagnostics.extend(temporary_diagnostics)
        elif temporary_diagnostics:
            null_errors = frozenset(
                null_arithmetic_argument_diagnostics(
                    argument,
                    row_schema,
                    value_types,
                    bare_value_expressions,
                    type_expansions,
                    reported_errors=frozenset(temporary_diagnostics),
                )
            )
            diagnostics.extend(
                diagnostic
                for diagnostic in temporary_diagnostics
                if diagnostic in null_errors
            )
        return (argument_type,), set()

    inferred: list[ValueType] = []
    erroneous: set[int] = set()
    for argument in expression.arguments:
        start = len(diagnostics)
        argument_type = _infer(
            argument,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
            relation_columns=relation_columns,
        )
        inferred.append(argument_type)
        if argument_type.kind is ValueTypeKind.UNKNOWN and _has_error(
            diagnostics[start:]
        ):
            erroneous.add(id(argument))
    return tuple(inferred), erroneous


def _callee_name(expression: CallExpr) -> str:
    """Return a source-level name for a simple or dotted call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    assert isinstance(expression.callee, DottedNameExpr)
    return ".".join(expression.callee.parts)


def _aggregate_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    *,
    let_expansions: Mapping[str, Expression] | None,
    row_schema: RowSchema,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType | None:
    """Return a precise aggregate type only for approved direct projections."""

    function_name = semantic_aggregate_call_name(expression)
    if function_name is None:
        return None
    if function_name == "string_agg":
        if (
            len(expression.arguments) != 2
            or not expression.aggregate_order_by
            or len(argument_types) != 2
            or any(
                not _is_canonical_builtin(argument, "Text", type_expansions)
                for argument in argument_types
            )
        ):
            return None
        return _builtin_value_type("Text", EffectiveNullability.NULLABLE)
    if not expression.arguments:
        return semantic_projection_aggregate_result_value_type(function_name)
    if len(expression.arguments) != 1:
        return None
    argument = expression.arguments[0]
    if extremum_reads_let(
        function_name, argument, let_expansions, row_schema
    ) or not is_supported_semantic_aggregate_argument_expression(
        function_name,
        argument,
        argument_types[0],
        let_expansions=let_expansions,
    ):
        return None
    return semantic_projection_aggregate_result_value_type(
        function_name,
        argument_types[0],
    )


def _append_invalid_count_context_diagnostic(
    expression: Expression,
    diagnostics: list[Diagnostic],
    *,
    context: str,
) -> None:
    """Report aggregate use where aggregate semantics are not admitted."""

    if contains_semantic_aggregate(expression):
        diagnostics.append(invalid_context_diagnostic(expression, context=context))


def _literal_value_type(expression: LiteralExpr) -> ValueType:
    """Map supported scalar literals to portable built-in types."""

    return resolved_literal_value_type(expression.value)


def resolved_literal_value_type(value: object) -> ValueType:
    """Original scalar literal law, independent of a source expression owner."""
    if isinstance(value, bool):
        name = "Bool"
    elif isinstance(value, str):
        name = "Text"
    elif isinstance(value, int):
        name = "Int"
    elif isinstance(value, float):
        name = "Float"
    else:
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type(name, EffectiveNullability.NON_NULL)


def _name_value_type(
    expression: NameExpr,
    row_schema: RowSchema,
    diagnostics: list[Diagnostic],
    *,
    report_unknown: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Resolve a bare field name against a known row schema; a name in
    ``bare_value_types`` that is no field, such as a `let:` name, has its
    type there, also over a row whose fields are unknown, as emission inlines
    a `let:` name wherever it is read."""

    if row_schema.is_unknown:
        value_type = (
            None if bare_value_types is None else bare_value_types.get(expression.name)
        )
        return _UNKNOWN_VALUE_TYPE if value_type is None else value_type
    field = bare_field(row_schema, expression.name)
    if field is not None:
        if field.resolved_type.kind is TypeKind.UNKNOWN:
            return _UNKNOWN_VALUE_TYPE
        return ValueType(
            resolved_type=field.resolved_type,
            nullability=field.nullability,
        )

    if bare_value_types is not None:
        value_type = bare_value_types.get(expression.name)
        if value_type is not None:
            return value_type

    if report_unknown and expression.name not in (suppressed_unknown_names or set()):
        diagnostics.append(_unknown_field_diagnostic(expression))
    return _UNKNOWN_VALUE_TYPE


def _qualified_name_value_type(
    expression: DottedNameExpr,
    row_schema: RowSchema,
    diagnostics: list[Diagnostic],
    *,
    field_qualifier: str,
    report_unknown: bool,
) -> ValueType:
    """Resolve one two-part field reference against the visible input bindings.

    A row of unknown type hides its fields, not the name of its input: a read
    such as `other.a` or `items.a.b` is unknown there as over a known row.
    """

    if (
        len(expression.parts) != 2
        or (not row_schema.joined and expression.parts[0] != field_qualifier)
        or (row_schema.joined and field_qualifier == "")
    ):
        if report_unknown:
            diagnostics.append(_unknown_field_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE
    if row_schema.is_unknown:
        return _UNKNOWN_VALUE_TYPE

    field = qualified_field(row_schema, expression.parts, field_qualifier)
    if field is None:
        if report_unknown:
            diagnostics.append(_unknown_field_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE
    if field.resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=field.resolved_type,
        nullability=field.nullability,
    )


def _is_numeric(value_type: ValueType) -> bool:
    """Return whether a known value type is one of Pietto's numeric scalars."""

    return _is_builtin(value_type, "Int") or _is_builtin(value_type, "Float")


def _binary_arithmetic_result_type(
    operator: str,
    left_type: ValueType,
    right_type: ValueType,
) -> str | None:
    """Return the approved result type for one binary arithmetic expression."""

    if _is_numeric(left_type) and _is_numeric(right_type):
        return (
            "Float"
            if _is_builtin(left_type, "Float") or _is_builtin(right_type, "Float")
            else "Int"
        )
    if (
        operator in {"+", "-", "*"}
        and _is_builtin(left_type, "Decimal")
        and _is_builtin(right_type, "Decimal")
    ):
        return "Decimal"
    if operator in {"+", "-"} and _is_decimal_int_pair(left_type, right_type):
        return "Decimal"
    return None


def _is_decimal_int_pair(left_type: ValueType, right_type: ValueType) -> bool:
    return (_is_builtin(left_type, "Decimal") and _is_builtin(right_type, "Int")) or (
        _is_builtin(left_type, "Int") and _is_builtin(right_type, "Decimal")
    )


def _is_builtin(value_type: ValueType, name: str) -> bool:
    """Return whether a known value type names one exact built-in type."""

    return (
        value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.resolved_type.name == name
    )


def _is_canonical_builtin(
    value_type: ValueType,
    name: str,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    resolved = _canonical_resolved_type(value_type, type_expansions)
    return (
        resolved is not None
        and resolved.kind is TypeKind.BUILTIN
        and resolved.name == name
    )


def _builtin_value_type(
    name: str,
    nullability: EffectiveNullability,
) -> ValueType:
    """Create a known value type for one portable built-in."""

    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
    )


def _invalid_operator_operands_diagnostic(
    expression: (
        UnaryExpr
        | BinaryExpr
        | ComparisonExpr
        | BetweenExpr
        | ConditionalExpr
        | MembershipExpr
        | ast.RelationMembershipExpr
    ),
    *,
    expected: str,
) -> Diagnostic:
    """Report incompatible known operands at the full operator expression span."""

    return _operator_operands_diagnostic(expression, f"expected {expected}")


def _null_comparison_diagnostic(
    expression: ComparisonExpr | BetweenExpr | MembershipExpr,
    *,
    remedy: str | None,
) -> Diagnostic:
    """Report a comparison with the null literal, which is never TRUE."""

    detail = "comparison with null is never true"
    if remedy is not None:
        detail += f"; write `{remedy}` instead"
    return _operator_operands_diagnostic(expression, detail)


def _operator_operands_diagnostic(
    expression: (
        UnaryExpr
        | BinaryExpr
        | ComparisonExpr
        | BetweenExpr
        | ConditionalExpr
        | MembershipExpr
        | ast.RelationMembershipExpr
    ),
    detail: str,
) -> Diagnostic:
    span = expression.span
    if isinstance(expression, BetweenExpr):
        operator = "between"
    elif isinstance(expression, ConditionalExpr):
        operator = "conditional"
    elif isinstance(expression, (MembershipExpr, ast.RelationMembershipExpr)):
        operator = "in" if not expression.negated else "not in"
    else:
        operator = expression.operator
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=f"Invalid operands for operator {operator}: {detail}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _invalid_cast_diagnostic(
    expression: CastExpr,
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    null_operand: bool = False,
) -> Diagnostic:
    """Report a rejected explicit conversion, echoing the attempted pair."""

    if value_type.kind is ValueTypeKind.UNKNOWN:
        source = "null" if null_operand else "unknown"
    else:
        canonical = _canonical_resolved_type(value_type, type_expansions)
        source = (value_type.resolved_type if canonical is None else canonical).name
    target = _type_expression_text(expression.target)
    hint = (
        "only Int-to-Text conversion is supported; write Text(expression)"
        if (
            expression.target.name == "Text"
            and not expression.target.arguments
            and expression.target.nullability is Nullability.IMPLICIT
        )
        else "only Int-to-Float conversion is supported; write Float(expression)"
    )
    span = expression.span
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=f"Invalid cast from {source} to {target}: {hint}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _type_expression_text(type_expr: TypeExpr) -> str:
    """Render an authored type with its arguments and nullability marker."""

    text = type_expr.name
    if type_expr.arguments:
        text += f"({', '.join(map(_type_argument_text, type_expr.arguments))})"
    if type_expr.nullability is Nullability.NULLABLE:
        return f"{text} | None"
    return text


def _type_argument_text(argument: ast.TypeArgument) -> str:
    """Render numeric literal arguments; elide any other argument value."""

    value = argument.value
    text = (
        str(value.value)
        if type(value) is LiteralExpr and type(value.value) in (int, float)
        else "..."
    )
    return text if argument.name is None else f"{argument.name} = {text}"


def _unknown_field_diagnostic(expression: NameExpr | DottedNameExpr) -> Diagnostic:
    """Report an unknown field reference at its expression span."""

    span = expression.span
    name = (
        expression.name
        if isinstance(expression, NameExpr)
        else ".".join(expression.parts)
    )
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _names_window_output(definition: TableDef | QueryDef, name: str) -> bool:
    return any(
        type(item.expression) is WindowExpr and item.alias == name
        for item in definition.select_items
    )


def order_output_ambiguity(
    key: NameExpr,
    definition: TableDef | QueryDef,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
    *,
    let_names: set[str],
) -> Diagnostic | None:
    """Refuse an ungrouped ORDER BY key, named alone, that is both a known
    input field and a SELECT output of another value: neither reading wins.

    An output of that same field (`x`, `x = x`, `x = q.x`, or a `let:` name
    bound to one) reads the same value. A `let:` name never names an output
    of another value (PIE-S2329), and over a joined row a name that several
    inputs have is PIE-S2335 already.
    """

    name = key.name
    if input_schema.is_unknown or name in let_names:
        return None
    if input_schema.joined:
        keys = [
            field for field in input_schema.fields if field.partition(".")[2] == name
        ]
        if len(keys) != 1:
            return None
        qualified = keys[0]
    elif name in input_schema.fields:
        qualifier = (
            definition.from_clause.binding_name or definition.from_clause.source_name
        )
        qualified = f"{qualifier}.{name}"
    else:
        return None

    def same_field(selected: SelectItem) -> bool:
        if type(selected.expression) is WindowExpr:
            return False
        value = let_value(selected.expression, input_schema, let_expressions)
        if type(value) is NameExpr:
            return value.name == name
        return type(value) is DottedNameExpr and ".".join(value.parts) == qualified

    if all(
        same_field(selected)
        for selected in definition.select_items
        if _relation_projection_output_name(selected) == name
    ):
        return None
    return order_output_ambiguity_diagnostic(key, qualified)


def qualify_output_ambiguity(
    key: NameExpr,
    definition: TableDef | QueryDef,
    input_schema: RowSchema,
    *,
    let_names: set[str],
) -> Diagnostic | None:
    """Refuse any QUALIFY name with both input and selected-output candidates.

    Unlike ORDER BY, identical values remain distinct candidates here: QUALIFY
    binds after SELECT/window evaluation and must never select a winner.
    """

    name = key.name
    if input_schema.is_unknown or name in let_names:
        return None
    if input_schema.joined:
        keys = [
            field for field in input_schema.fields if field.partition(".")[2] == name
        ]
        if len(keys) != 1:
            return None
        qualified = keys[0]
    elif name in input_schema.fields:
        qualifier = (
            definition.from_clause.binding_name or definition.from_clause.source_name
        )
        qualified = f"{qualifier}.{name}"
    else:
        return None
    if not any(
        _relation_projection_output_name(item) == name
        for item in definition.select_items
    ):
        return None
    return order_output_ambiguity_diagnostic(key, qualified)


def order_output_ambiguity_diagnostic(key: NameExpr, qualified: str) -> Diagnostic:
    """PIE-S2102 for an ORDER BY key that names an input field and an output."""

    span = key.span
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=(
            f"Ambiguous field: {key.name} is both the input field {qualified} and "
            f"a SELECT output; write {qualified}, or give the output another name"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


# The aggregate names in one fixed order, as a message lists them.
_AGGREGATE_NAMES = sorted(SEMANTIC_AGGREGATE_NAMES)
# What to write instead of a function that a SQL or Python habit calls, by its
# lowercase name.
_UNKNOWN_FUNCTION_HINTS = {
    "length": "use `len(Text)` instead",
    "char_length": "use `len(Text)` instead",
    "concat": "string concatenation is not supported yet",
    "generate_series": "it is a table function, read with "
    "`from generate_series(start, stop, step) as n` in an EXPLICIT_MODULES project",
    # D71.01/D71.02: the nested-relation spellings no call writes.
    **dict.fromkeys(
        ("collect", "list"),
        "a Collect read is the select item `name = collect relation` in an "
        "EXPLICIT_MODULES project",
    ),
    "unnest": "an Unnest is `let o = unnest(binding.field)` that a later JOIN of "
    "the same body reads, in an EXPLICIT_MODULES project",
    **dict.fromkeys(
        (
            "array_agg",
            "group_concat",
            "mean",
            "median",
            "std",
            "stddev",
            "stddev_pop",
            "stddev_samp",
            "string_agg",
            "var",
            "var_pop",
            "var_samp",
            "variance",
        ),
        f"the available aggregates are {', '.join(_AGGREGATE_NAMES[:-1])} and "
        f"{_AGGREGATE_NAMES[-1]}",
    ),
}


def is_unknown_function_call(expression: CallExpr) -> bool:
    """Whether typing reports ``expression`` as an unknown function (PIE-S2103):
    its callee names no built-in, aggregate or window function."""

    from pietto.semantic.window_semantics import WINDOW_FUNCTION_NAMES

    name = _callee_name(expression)
    return not (
        name
        in {"coalesce", "nullif", "sign", "year", "month", "day", "round", "date_trunc"}
        or is_semantic_aggregate_call(expression)
        or name in BUILTIN_FUNCTIONS
        or name in WINDOW_FUNCTION_NAMES
    )


def _unknown_function_diagnostic(
    expression: CallExpr,
    function_name: str,
) -> Diagnostic:
    """Report a call target absent from the explicit built-in catalog."""

    hint = _UNKNOWN_FUNCTION_HINTS.get(function_name.lower())
    return _call_diagnostic(
        expression,
        code="PIE-S2103",
        message=f"Unknown function: {function_name}"
        + ("" if hint is None else f"; {hint}"),
    )


def _window_without_spec_diagnostic(
    expression: CallExpr,
    function_name: str,
) -> Diagnostic:
    """Report a window function called without a window specification."""

    call = f"{function_name}({'...' if expression.arguments else ''})"
    return _call_diagnostic(
        expression,
        code="PIE-S2103",
        message=(
            f"Window function needs a `window` specification: {function_name} "
            f"(write `{call} window(order by ...)` in a SELECT item)"
        ),
    )


def _wrong_arity_diagnostic(
    expression: CallExpr,
    signature: BuiltinFunction,
) -> Diagnostic:
    """Report a built-in call with the wrong argument count."""

    return _call_diagnostic(
        expression,
        code="PIE-S2104",
        message=(
            f"Invalid arguments for function {signature.name}: expected "
            f"{len(signature.parameter_types)}, got {len(expression.arguments)}"
        ),
    )


def _wrong_argument_type_diagnostic(
    expression: CallExpr,
    signature: BuiltinFunction,
    *,
    position: int,
    expected_name: str,
    actual_name: str,
) -> Diagnostic:
    """Report the first incompatible known argument in a built-in call."""

    return _call_diagnostic(
        expression,
        code="PIE-S2104",
        message=(
            f"Invalid argument type for function {signature.name} at position "
            f"{position}: expected {expected_name}, got {actual_name}"
        ),
    )


def _call_diagnostic(
    expression: CallExpr,
    *,
    code: str,
    message: str,
) -> Diagnostic:
    """Create a call diagnostic at the complete call-expression span."""

    span = expression.span
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
