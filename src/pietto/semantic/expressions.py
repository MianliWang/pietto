"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

import bisect
import dataclasses
import functools
import itertools
from collections import ChainMap, Counter
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, ParamSpec, cast

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
    aggregate_argument_can_use_let_scope,
    contains_semantic_aggregate,
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

if TYPE_CHECKING:
    from pietto._inline_argument import InlinedArgument
    from pietto.semantic.window_semantics import (
        ResolvedNamedWindowNamespace,
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
        ast.UnaryExpr,
        ast.ConditionalExpr,
        ast.MembershipExpr,
        ast.RelationExistsExpr,
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
) -> bool:
    """Check an argument of ``value_type`` against each ``def`` parameter it
    is inlined for.

    A known type must be the parameter type after alias expansion, and a
    ``not null`` parameter takes only a value proven non-null. An argument
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
            and canonical.name == slot.type_name
        )
        if type_fits and (
            slot.nullable
            or (
                value_type.nullability is EffectiveNullability.NON_NULL
                and not is_null()
            )
        ):
            continue
        if type_fits and is_null():
            actual = "null"
        else:
            actual = (
                f"{(canonical or value_type.resolved_type).name} "
                f"{_NULLABILITY_TEXT[value_type.nullability]}"
            )
        expected = "nullable" if slot.nullable else "not null"
        diagnostics.append(
            Diagnostic(
                code="PIE-S2395",
                severity=Severity.ERROR,
                message=(
                    f"Invalid argument for def {slot.function} at position "
                    f"{slot.position} ({slot.parameter}): expected "
                    f"{slot.type_name} {expected}, got {actual}"
                ),
                location=_span_location(slot.call),
            )
        )
        # An inner call's parameter comes first; once it does not fit, the
        # value is unknown to every call around it.
        return False
    return True


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
    """

    __slots__ = ("checked", "differs", "erroneous", "field_types", "typed", "written")

    def __init__(
        self,
        values: Mapping[str, Expression] | None = None,
        erroneous: set[str] | None = None,
        field_types: dict[Expression, ValueType] | None = None,
    ) -> None:
        super().__init__(values or {})
        self.erroneous: set[str] = set() if erroneous is None else erroneous
        self.field_types = field_types
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


class _WrittenTypes(dict[Expression, ValueType]):
    """The types a written form (`_written_form`) is typed with, by part,
    and the diagnostics of each part it keeps whole, by identity, which
    typing reports where it reaches that part, as it would the part itself
    written there."""

    __slots__ = ("diagnostics",)

    def __init__(self) -> None:
        super().__init__()
        self.diagnostics: dict[int, list[Diagnostic]] = {}


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
            and node.name not in row_schema.fields
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
            and node.name not in row_schema.fields
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
        EffectiveNullability.NON_NULL: "not null",
        EffectiveNullability.NULLABLE: "nullable",
        EffectiveNullability.UNKNOWN: "of unknown nullability",
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
) -> tuple[
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[WindowExpr, WindowExpressionAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Type supported table/query expressions without validating consumers.

    ``let_diagnostics`` are the relation `let:` diagnostics; a window frame
    offset that reads a binding with one of them reports no PIE-S2104.
    """

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    window_analyses: dict[WindowExpr, WindowExpressionAnalysis] = {}
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
            let_expressions = LetValues(let_expressions, erroneous_lets)
            from pietto.semantic.let_bindings import _relation_expressions

            if _reads_let_in_argument(
                _relation_expressions(definition), let_expressions, input_schema
            ):
                _write_lets(
                    let_expressions,
                    input_schema,
                    value_types,
                    field_qualifier=definition.from_clause.source_name,
                    bare_value_types=let_value_types,
                    type_expansions=type_expansions,
                )
        named_window_namespace_failed = False
        named_window_namespace = None
        if definition.named_windows:
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
                field_qualifier=definition.from_clause.source_name,
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
                if named_window_namespace_failed:
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
                    field_qualifier=definition.from_clause.source_name,
                    value_types=value_types,
                    diagnostics=diagnostics,
                    let_value_types=let_value_types or {},
                    let_expressions=let_expressions or {},
                    named_window_namespace=named_window_namespace,
                    type_expansions=type_expansions,
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
                    WindowExpressionAnalysis,
                    WindowResultAvailabilityKind,
                )

                if type(analysis) is WindowExpressionAnalysis:
                    window_analyses[item.expression] = analysis
                    diagnostics.extend(
                        _window_literal_range_diagnostics(
                            item.expression,
                            analysis,
                            input_schema,
                            let_expressions or {},
                            erroneous_lets,
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
                field_qualifier=definition.from_clause.source_name,
                allow_aggregate_projection=_is_direct_aggregate_projection(item),
                bare_value_types=select_let_value_types,
                bare_value_expressions=let_expressions,
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
        if (
            definition.order_by_clause is not None
            and definition.group_by_clause is None
        ):
            aggregated = any(
                contains_semantic_aggregate(selected.expression)
                for selected in definition.select_items
            )
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
                order_suppressed_names = rejected_lets
                if (
                    type(item.expression) is NameExpr
                    and item.expression.name in selected_output_name_counts
                    and not _names_window_output(definition, item.expression.name)
                    and item.expression.name not in rejected_lets
                    and item.expression.name not in (order_bare_value_types or {})
                    and not input_schema.is_unknown
                    and item.expression.name not in input_schema.fields
                ):
                    diagnostics.append(
                        _order_by_output_name_diagnostic(
                            item.expression,
                            tuple(
                                selected.expression
                                for name, selected in zip(
                                    selected_output_names,
                                    definition.select_items,
                                    strict=True,
                                )
                                if name == item.expression.name
                            ),
                            input_schema,
                            let_expressions,
                        )
                    )
                    order_suppressed_names = {*rejected_lets, item.expression.name}
                _infer(
                    item.expression,
                    input_schema,
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    field_qualifier=definition.from_clause.source_name,
                    bare_value_types=order_bare_value_types,
                    bare_value_expressions=let_expressions,
                    suppressed_unknown_names=order_suppressed_names,
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
                        let_expressions or {},
                        aggregated=aggregated and not input_schema.is_unknown,
                    )
                )
                if problem is not None:
                    diagnostics.append(_order_key_diagnostic(item.expression, problem))

    return value_types, diagnostics, window_analyses, named_window_namespaces


_SIGNED64_MAX = (1 << 63) - 1
# The literal count argument of each window function that takes one.
_WINDOW_COUNT_POSITIONS = {"ntile": 0, "lag": 1, "lead": 1, "nth_value": 1}


def _window_literal_range_diagnostics(
    expression: WindowExpr,
    analysis: WindowExpressionAnalysis,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    erroneous_lets: set[str],
) -> list[Diagnostic]:
    """Refuse window literals that no SQL target accepts, before emission.

    A ROWS or GROUPS offset, after the `let:` inlining emission performs, must
    be a nonnegative signed 64-bit Int literal, and a count argument may not
    exceed that range; the narrower PostgreSQL int4 count range is checked
    when PostgreSQL SQL is emitted. An offset that reads a `let:` name in
    `erroneous_lets` already has its error.
    """

    name = expression.identity.name
    messages: list[str] = []
    frame = analysis.validated_specification.resolved.frame
    unit = frame.unit
    offsets = tuple(
        (bound.offset, let_value(bound.offset, input_schema, let_expressions))
        for bound in (frame.start, frame.end)
        if bound is not None and bound.offset is not None
    )
    if (unit is WindowFrameUnit.ROWS or unit is WindowFrameUnit.GROUPS) and any(
        not (
            type(value) is LiteralExpr
            and type(value.value) is int
            and 0 <= value.value <= _SIGNED64_MAX
        )
        and not _reads_erroneous_let(
            offset, input_schema, let_expressions, erroneous_lets
        )
        for offset, value in offsets
    ):
        messages.append(
            f"Invalid window frame for function {name}: "
            f"{unit.value.upper()} offsets must be nonnegative integer "
            f"literals up to {_SIGNED64_MAX}"
        )
    position = _WINDOW_COUNT_POSITIONS.get(name)
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
        if type(node) is NameExpr and node.name not in input_schema.fields:
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
        and expression.name not in row_schema.fields
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
) -> str | None:
    """Return why a target would misread or reject an ungrouped ORDER BY key.

    After `let:` inlining and unary signs a bare constant remains: PostgreSQL
    and MySQL read an integer as a column position, and PostgreSQL rejects any
    other bare constant (a computed constant such as `1 + 1` sorts nothing and
    stays accepted). In a query with aggregates and no GROUP BY, a key that
    reads an input field outside an aggregate is rejected by the targets.
    """

    if _is_bare_constant(expression, input_schema, let_expressions):
        return (
            "Constant ORDER BY key: a target reads a bare constant key as a "
            "column position or rejects it"
        )
    if aggregated and _reads_input_field_outside_aggregate(
        expression, input_schema, let_expressions
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
) -> bool:
    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr:
            if node.name in input_schema.fields:
                return True
            if node.name in let_expressions and node.name not in expanded:
                expanded.add(node.name)
                pending.append(let_expressions[node.name])
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
) -> ValueType:
    """Infer one row-level expression with optional bare-only local bindings.

    ``relation_columns`` holds the known column type of each ``in`` relation
    read, keyed by its expression; its left value must pair with it.

    Each captured outer field below ``expression`` takes its type from
    ``captured_value_types``, the capture environment of its let; a field its
    outer input lacks maps to that environment's own diagnostic instead.
    """

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
        return expression.arguments
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
    elif isinstance(expression, ast.CapturedFieldExpr):
        # A captured field is typed only by its let's capture environment.
        raise AssertionError("Captured field read lacks its capture environment.")
    elif isinstance(expression, ast.RelationExistsExpr):
        # An existence test is never NULL; its relation is resolved, scheduled
        # and checked by the owner of the relation name, not by this kernel.
        value_type = _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    elif isinstance(expression, ast.RelationScalarExpr):
        # A scalar read's type is its read block column's, which only the
        # relation-name owner knows; a caller supplies it in ``value_types``.
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
                else {"==": "is null", "!=": "is not null"}.get(expression.operator)
            )
            diagnostics.append(_null_comparison_diagnostic(expression, remedy=remedy))
            value_type, expected = _UNKNOWN_VALUE_TYPE, None
        else:
            value_type, expected = resolved_comparison_value_type(
                left_type, right_type, type_expansions
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

    lets = bare_value_expressions
    if inlined_arguments(expression):
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
    value_types[expression] = value_type
    if type(lets) is LetValues and lets.differs:
        lets.typed[id(expression)] = (diagnostics, reported, len(diagnostics))
    return value_type


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
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
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
    when_true_null, condition_null, when_false_null = _null_reads(
        (expression.when_true, expression.condition, expression.when_false),
        row_schema,
        bare_value_types,
        bare_value_expressions,
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
        for child in (expression.value, *expression.options)
    )
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
                else "is not null"
                if expression.negated
                else "is null"
            )
            diagnostics.append(_null_comparison_diagnostic(expression, remedy=remedy))
            return _UNKNOWN_VALUE_TYPE
    contextual = _contextual_null_literal_types(
        (expression.value, *expression.options),
        child_types,
        value_types,
        type_expansions,
        _null_reads(
            (expression.value, *expression.options),
            row_schema,
            bare_value_types,
            bare_value_expressions,
        ),
        membership=True,
    )
    if contextual is not None:
        child_types = contextual
    if any(value_type.kind is ValueTypeKind.UNKNOWN for value_type in child_types):
        return _UNKNOWN_VALUE_TYPE
    if _membership_canonical_type(child_types, type_expansions) is None:
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
    """Admit only the explicit portable Int-to-Float conversion."""

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
    float_target = (
        expression.target.name == "Float"
        and not expression.target.arguments
        and expression.target.nullability is Nullability.IMPLICIT
    )
    if value_type.kind is ValueTypeKind.UNKNOWN:
        # A null operand and the target are known without the operand's type;
        # a silent unknown operand is refused unless the cast is to Float. Only
        # the operand's own error explains it, also one in a `let:` value it
        # reads, as written there it would be its own: an unknown input row
        # does not, since no cast but the Float one reads the operand's type.
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
        if null_operand or not (explained or float_target):
            diagnostics.append(
                _invalid_cast_diagnostic(
                    expression,
                    value_type,
                    type_expansions,
                    null_operand=null_operand,
                )
            )
        return _UNKNOWN_VALUE_TYPE
    if not float_target or not _is_canonical_builtin(
        value_type, "Int", type_expansions
    ):
        diagnostics.append(
            _invalid_cast_diagnostic(expression, value_type, type_expansions)
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Float", value_type.nullability)


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
        return _UNKNOWN_VALUE_TYPE, "numeric operands"
    return _UNKNOWN_VALUE_TYPE, None


# Builtin families from the canonical scalar type registry trait vocabulary.
# Any, Bytes, Json, enums and shapes stay unchecked (deferred).
_COMPARISON_FAMILIES = {
    "Int": "numeric",
    "Float": "numeric",
    "Decimal": "numeric",
    "Text": "text",
    "Bool": "boolean",
    "Date": "temporal",
    "Timestamp": "temporal",
    "UUID": "identifier",
}
# Text against types without literal syntax awaits a typed-constant decision.
_DEFERRED_COMPARISON_FAMILY_PAIRS = ({"text", "temporal"}, {"text", "identifier"})


def resolved_comparison_value_type(
    left_type: ValueType,
    right_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
) -> tuple[ValueType, str | None]:
    """Comparison rule over resolved operands; no implicit cross-family conversion."""
    families = {
        _comparison_family(left_type, type_expansions),
        _comparison_family(right_type, type_expansions),
    }
    if (
        None in families
        or len(families) == 1
        or families in _DEFERRED_COMPARISON_FAMILY_PAIRS
    ):
        return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN), None
    return _UNKNOWN_VALUE_TYPE, "comparable operands"


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


def _join_nullability(
    nullabilities: tuple[EffectiveNullability, ...],
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in nullabilities:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in nullabilities:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


def _comparison_family(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> str | None:
    resolved_type = value_type.resolved_type
    if type_expansions is not None and resolved_type.kind is TypeKind.TYPE_ALIAS:
        # Single-file row fields keep alias names; compare the canonical expansion.
        definition = resolved_type.definition
        assert isinstance(definition, TypeDef)
        resolved_type = type_expansions[definition.base]
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or resolved_type.kind is not TypeKind.BUILTIN
    ):
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
    if any(child_type.kind is ValueTypeKind.UNKNOWN for child_type in child_types):
        return _UNKNOWN_VALUE_TYPE
    for bound_type in child_types[1:]:
        _, expected = resolved_comparison_value_type(
            child_types[0], bound_type, type_expansions
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
    unknown input row suppresses none of them.
    """

    function_name = _callee_name(expression)
    diagnostic_count = len(diagnostics)
    argument_types = _call_argument_types(
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
    # An argument's own error explains an Unknown argument; the call then adds
    # nothing. An unknown input row explains no name, arity or window check,
    # since none of them reads an argument's type.
    cascade = len(diagnostics) > diagnostic_count and any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    )
    nulls = _null_reads(
        expression.arguments, row_schema, bare_value_types, bare_value_expressions
    )
    if function_name in {"coalesce", "nullif"}:
        contextual = _contextual_null_literal_types(
            expression.arguments,
            argument_types,
            value_types,
            type_expansions,
            nulls,
        )
        if contextual is None:
            return _UNKNOWN_VALUE_TYPE
        argument_types = contextual
        if function_name == "coalesce":
            return _coalesce_value_type(
                expression, argument_types, type_expansions, diagnostics
            )
        return _nullif_value_type(
            expression, argument_types, type_expansions, diagnostics
        )

    if is_semantic_aggregate_call(expression):
        if any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        ):
            return _UNKNOWN_VALUE_TYPE
        if allow_aggregate_projection:
            result_type = _aggregate_value_type(
                expression,
                argument_types,
                let_expansions=bare_value_expressions,
            )
            if result_type is not None:
                return result_type
        return _UNKNOWN_VALUE_TYPE

    if (
        function_name in {"sign", "year", "month", "day"}
        and any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        )
        and (cascade or len(argument_types) == 1)
    ):
        return _UNKNOWN_VALUE_TYPE
    if function_name == "sign":
        return _sign_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
        )
    if function_name in {"year", "month", "day"}:
        return _civil_date_part_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
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
    if any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ):
        # The `substr` bounds check reads only literals, so a silent Unknown
        # argument, such as a field of an unknown input row, does not hide it.
        if (
            function_name == "substr"
            and not cascade
            and not _valid_static_substr_bounds(expression)
        ):
            diagnostics.append(_invalid_substr_bounds_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    for position, (argument_type, expected_name) in enumerate(
        zip(argument_types, signature.parameter_types, strict=True),
        start=1,
    ):
        # A function reads a type alias argument as the type it expands to.
        if not _is_canonical_builtin(argument_type, expected_name, type_expansions):
            diagnostics.append(
                _wrong_argument_type_diagnostic(
                    expression,
                    signature,
                    position=position,
                    expected_name=expected_name,
                    actual_name=argument_type.resolved_type.name,
                )
            )
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
    (`condition_value_type`)."""

    condition = condition_value_type(expression, value_type, row_schema, lets)
    return condition.kind is ValueTypeKind.KNOWN and not _is_canonical_builtin(
        condition, "Bool", type_expansions
    )


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
) -> tuple[bool, ...]:
    """Whether each of ``expressions`` is a null that takes its type from where
    it stands: the null literal, or a `let:` name read as its binding (in
    ``bare_value_types``) whose value, inlined as emission inlines it, is the
    null literal; never a ``def`` argument that does not fit its parameter,
    which stays Unknown to the expression around it."""

    return tuple(
        _reads_null_literal(
            (expression,),
            row_schema,
            let_expressions
            if type(expression) is NameExpr
            and bare_value_types is not None
            and expression.name in bare_value_types
            else None,
        )
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
) -> tuple[ValueType, ...]:
    if (
        allow_aggregate_projection
        and is_semantic_aggregate_call(expression)
        and len(expression.arguments) == 1
        and not contains_semantic_aggregate(expression.arguments[0])
    ):
        argument = expression.arguments[0]
        temporary_diagnostics: list[Diagnostic] = []
        function_name = _callee_name(expression)
        argument_bare_value_types = (
            bare_value_types
            if aggregate_argument_can_use_let_scope(
                function_name,
                argument,
                bare_value_expressions,
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
            # A def argument that does not fit is unknown to the aggregate,
            # as such a field is, and its PIE-S2395 is its error.
            or unfit_argument(
                function_name, argument, None, value_types, type_expansions
            )
        ):
            diagnostics.extend(temporary_diagnostics)
        return (argument_type,)

    return tuple(
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
        for argument in expression.arguments
    )


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
) -> ValueType | None:
    """Return a precise aggregate type only for approved direct projections."""

    function_name = semantic_aggregate_call_name(expression)
    if function_name is None:
        return None
    if not expression.arguments:
        return semantic_projection_aggregate_result_value_type(function_name)
    if len(expression.arguments) != 1:
        return None
    argument = expression.arguments[0]
    if not is_supported_semantic_aggregate_argument_expression(
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
    field = row_schema.fields.get(expression.name)
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
    """Resolve one two-part field reference against the sole relation input."""

    if row_schema.is_unknown:
        return _UNKNOWN_VALUE_TYPE
    if len(expression.parts) != 2 or expression.parts[0] != field_qualifier:
        if report_unknown:
            diagnostics.append(_unknown_field_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    field = row_schema.fields.get(expression.parts[1])
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
    span = expression.span
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=(
            f"Invalid cast: cast({source} as {target}) is not supported; "
            "expected cast(Int as Float), the only supported cast"
        ),
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
        return f"{text} nullable"
    if type_expr.nullability is Nullability.NOT_NULL:
        return f"{text} not null"
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


def _order_by_output_name_diagnostic(
    expression: NameExpr,
    outputs: tuple[Expression, ...],
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> Diagnostic:
    """Report an ungrouped ORDER BY key that names only a SELECT output.

    ``outputs`` are the expressions selected under that name. An aggregate is
    refused in an ungrouped ORDER BY key and in `let:` too, so for an
    aggregate output the remedy is the grouped form instead; a bare constant
    key is refused (PIE-S2380), so a constant output gets no remedy.
    """

    span = expression.span
    if any(contains_semantic_aggregate(output) for output in outputs):
        remedy = (
            ", and an aggregate output cannot be ordered there (a grouped "
            "query can order by its name)"
        )
    elif any(
        _is_bare_constant(output, input_schema, let_expressions) for output in outputs
    ):
        remedy = ", and a constant output sorts nothing and cannot be an ORDER BY key"
    else:
        remedy = " (restate its expression or bind it in `let:`)"
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=(
            f"Unknown field: {expression.name}; outside a grouped query an "
            f"ORDER BY key cannot name a SELECT output{remedy}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unknown_function_diagnostic(
    expression: CallExpr,
    function_name: str,
) -> Diagnostic:
    """Report a call target absent from the explicit built-in catalog."""

    return _call_diagnostic(
        expression,
        code="PIE-S2103",
        message=f"Unknown function: {function_name}",
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
            f"(write `{call} window:` in a SELECT item, with an indented "
            "`order by:`)"
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
