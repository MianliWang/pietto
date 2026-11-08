"""The order of `first` and `last`: a single file's static determinism proof.

`first(x, order by k, ..., id)` is the value of `x` at the first member row of
its group in the call's internal order, `last` at the last row. The order must
name one row, so Pietto never picks a winner: every key is a direct field of
the FROM input (a `let` name of one reads as that field), no key is None on a
member row (its type has no `| None`, or a top-level `and` conjunct of the
query's WHERE tests it with `is not None`), and the keys with the field GROUP
BY keys that are never None cover every field of one `unique(...)` of the FROM
source's shape, so the order ends in a unique key (D73.05's walk: since every
key is a direct field that is never None, a key after a complete unique key
never changes the order). Over JOIN rows the call is refused instead, and
over an input whose fields are not known (a source without a shape). These
checks run only for a call with no error reported inside it (an unknown
field, a value of the wrong type or form, a missing `order by`), in a single
file and in a project alike, so a call gets one diagnostic at most; the first
key that fails reports.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    NameExpr,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    ORDERED_VALUE_AGGREGATE_NAMES,
    aggregate_composition_leaves,
    semantic_aggregate_call_name,
)
from pietto.semantic.model import (
    EffectiveNullability,
    RowSchema,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.null_warnings import where_not_none_reads

__all__ = (
    "ordered_value_diagnostics",
    "ordered_value_join_diagnostic",
    "ordered_value_order_diagnostic",
    "ordered_value_reported",
)


def ordered_value_diagnostics(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, object],
    type_symbols: Mapping[str, object],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema],
    expression_value_types: Mapping[Expression, ValueType],
    let_expressions: Mapping[TableDef | QueryDef, Mapping[str, Expression]],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """PIE-S2334 at a `first` or `last` over JOIN rows and PIE-S2104 at the
    first key of its order that fails the proof, for each such call that is a
    direct SELECT aggregate leaf whose typing admitted it and has no error in
    ``reported``."""

    found: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        for item in definition.select_items:
            for call in aggregate_composition_leaves(item.expression) or ():
                name = semantic_aggregate_call_name(call)
                typed = expression_value_types.get(call)
                if name not in ORDERED_VALUE_AGGREGATE_NAMES or typed is None:
                    continue
                assert isinstance(call, CallExpr)
                if ordered_value_reported(call, reported):
                    continue
                if definition.join_clauses or definition.join_filters:
                    found.append(ordered_value_join_diagnostic(call))
                    continue
                source = from_resolutions.get(definition.from_clause)
                schema = (
                    source_row_schemas.get(source)
                    if isinstance(source, SourceDef)
                    else relation_row_schemas.get(source)
                    if isinstance(source, (TableDef, QueryDef))
                    else None
                )
                if schema is not None and schema.is_unknown:
                    # A source without a shape, or a relation over one: no key
                    # is known to be a field, never None or unique.
                    found.append(
                        _unknown_input_diagnostic(
                            call, source_keys=isinstance(source, SourceDef)
                        )
                    )
                    continue
                if typed.kind is not ValueTypeKind.KNOWN:
                    continue
                shape = (
                    type_symbols.get(source.shape_name)
                    if isinstance(source, SourceDef) and source.shape_name is not None
                    else None
                )
                problem = ordered_value_order_diagnostic(
                    call,
                    fields={}
                    if schema is None
                    else {
                        field_name: row_field.nullability
                        is not EffectiveNullability.NON_NULL
                        for field_name, row_field in schema.fields.items()
                    },
                    qualifier=definition.from_clause.binding_name
                    or definition.from_clause.source_name,
                    lets=let_expressions.get(definition, {}),
                    where=definition,
                    group_keys=()
                    if definition.group_by_clause is None
                    else tuple(group.key for group in definition.group_by_clause.items),
                    unique_keys=tuple(unique.field_names for unique in shape.uniques)
                    if isinstance(shape, ShapeDef)
                    else (),
                    source_keys=isinstance(source, SourceDef),
                )
                if problem is not None:
                    found.append(problem)
    return found


def ordered_value_reported(call: CallExpr, reported: Sequence[Diagnostic]) -> bool:
    """Whether an error of ``reported`` lies inside ``call``: its value or an
    order key failed to type, or the call itself was refused. The JOIN refusal
    and the order proof then do not run, so the call reports that error alone."""

    span = call.span
    return any(
        diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == span.path
        and (span.line, span.column)
        <= (diagnostic.location.line, diagnostic.location.column)
        < (span.end_line, span.end_column)
        for diagnostic in reported
    )


def ordered_value_join_diagnostic(call: CallExpr) -> Diagnostic:
    """PIE-S2334 at a `first` or `last` over JOIN rows: its proof reads the
    `unique(...)` keys of one source."""

    return _diagnostic(
        call,
        f"{semantic_aggregate_call_name(call)} over JOIN rows is not available yet",
        "join in one query, then group it in another that reads it with `from`",
        code="PIE-S2334",
    )


def ordered_value_order_diagnostic(
    call: CallExpr,
    *,
    fields: Mapping[str, bool],
    qualifier: str,
    lets: Mapping[str, Expression],
    where: TableDef | QueryDef,
    group_keys: tuple[Expression, ...],
    unique_keys: tuple[tuple[str, ...], ...],
    source_keys: bool,
) -> Diagnostic | None:
    """PIE-S2104 at the first failure of the order proof of ``call``, a
    `first` or `last` over one input whose fields ``fields`` maps to whether
    it may be None, or None when its order ends in a unique key; a source's
    ``unique_keys`` are its shape's, and ``source_keys`` says whether the
    input is a source."""

    name = semantic_aggregate_call_name(call)

    def field(expression: Expression) -> str | None:
        seen: set[str] = set()
        while type(expression) is NameExpr and expression.name in lets:
            if expression.name in seen:
                return None
            seen.add(expression.name)
            expression = lets[expression.name]
        if type(expression) is NameExpr:
            return expression.name if expression.name in fields else None
        if (
            type(expression) is DottedNameExpr
            and len(expression.parts) == 2
            and expression.parts[0] == qualifier
            and expression.parts[1] in fields
        ):
            return expression.parts[1]
        return None

    tested = where_not_none_reads(where, lets, field)

    def never_none(name: str) -> bool:
        return not fields[name] or name in tested

    covered: set[str] = set()
    for item in call.aggregate_order_by:
        key = field(item.expression)
        if key is None:
            return _diagnostic(
                item.expression, f"Order key of {name} must be a direct field", None
            )
        if not never_none(key):
            return _diagnostic(
                item.expression,
                f"Order key {key} of {name} may be None, and None has no promised "
                "place in the order",
                f"add `{key} is not None` to the query's `where` as a top-level "
                "`and` test, or order by a key that is never None",
            )
        covered.add(key)
    covered.update(
        key
        for group in group_keys
        if (key := field(group)) is not None and never_none(key)
    )
    if any(set(unique) <= covered for unique in unique_keys):
        return None
    if unique_keys:
        hint = (
            "end the `order by` with the fields of a `unique(...)` key of its "
            f"source, such as `{', '.join(unique_keys[0])}`"
        )
    elif source_keys:
        hint = (
            "declare a `unique(...)` key in the shape of its source and end the "
            "`order by` with its fields"
        )
    else:
        hint = (
            f"{name} reads the `unique(...)` keys of a source: read the source "
            "with `from`, not a table or query"
        )
    return _diagnostic(
        call,
        f"The order of {name} does not end in a unique key, so rows that tie have "
        "no promised order",
        hint,
    )


def _unknown_input_diagnostic(call: CallExpr, *, source_keys: bool) -> Diagnostic:
    """PIE-S2104 at a `first` or `last` over an input row whose fields are
    not known, which no order proves total."""

    name = semantic_aggregate_call_name(call)
    return _diagnostic(
        call,
        f"The order of {name} reads an input whose fields are not known, so rows "
        "that tie have no promised order",
        "give its source a shape with a `unique(...)` key and end the `order by` "
        "with its fields"
        if source_keys
        else f"{name} reads the `unique(...)` keys of a source: read the source "
        "with `from`, not a table or query",
    )


def _diagnostic(
    expression: Expression,
    message: str,
    hint: str | None,
    *,
    code: str = "PIE-S2104",
) -> Diagnostic:
    span = expression.span
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
