"""Single-file top-level constants: declaration checks, `--set` values and
the substitution of every read by its value.

A constant ``cutoff: Date = "2024-01-31"`` is one literal of a closed type,
read by its bare name anywhere a value is read except in a source's
connector. Analysis replaces each read
by the literal, as if it were written there, so a constant changes only SQL
bytes and never a semantic fact. A `Date` or `Timestamp` constant is written
as a Text literal and read as a ``date`` or ``datetime`` literal of its type.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from typing import cast

from pietto.ast_nodes import (
    CallExpr,
    Expression,
    FunctionDef,
    GroupByItem,
    LiteralExpr,
    NameExpr,
    Node,
    Nullability,
    OrderItem,
    Script,
    SelectItem,
    SourceDef,
    Span,
    TypeExpr,
    UnaryExpr,
)
from pietto._builtin_shadows import _SHADOWABLE
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.inline_functions import _RESERVED_NAMES, _rebuild, _tree_nodes

__all__ = (
    "CONSTANT_CODE",
    "constant_diagnostics",
    "override_constants",
    "substitute_constants",
)

CONSTANT_CODE = "PIE-S2391"
_TYPES = ("Bool", "Int", "Float", "Text", "Date", "Timestamp")
_TYPE_MESSAGE = (
    "A constant is `Bool`, `Int`, `Float`, `Text`, `Date` or `Timestamp`, "
    "without `| None`."
)
# How each type's one literal is written: in source, and as a `--set` value.
_SOURCE_FORMS = {
    "Bool": "`True` or `False`",
    "Int": "an integer such as `10` or `-10`",
    "Float": "a number with a decimal point such as `1.5` or `-1.5`",
    "Text": 'a Text literal such as `"EU"`',
    "Date": 'a Text literal `"YYYY-MM-DD"` from 1000-01-01 to 9999-12-31',
    "Timestamp": 'a Text literal `"YYYY-MM-DD HH:MM:SS"`, with up to six '
    "fractional digits, from 1000-01-01 00:00:00 to 9999-12-31 23:59:59.499999",
}
_VALUE_FORMS = {
    "Bool": "True or False",
    "Int": "an integer such as 10 or -10",
    "Float": "a number with a decimal point such as 1.5 or -1.5",
    "Text": "UTF-8 text",
    "Date": "YYYY-MM-DD from 1000-01-01 to 9999-12-31",
    "Timestamp": "YYYY-MM-DD HH:MM:SS, with up to six fractional digits, "
    "from 1000-01-01 00:00:00 to 9999-12-31 23:59:59.499999",
}
_INT = re.compile(r"-?[0-9](?:_?[0-9])*")
_FLOAT = re.compile(r"-?[0-9](?:_?[0-9])*\.[0-9](?:_?[0-9])*")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
)
_MAX_NUMBER_LENGTH = 4096  # as a numeric source literal
_LAST_TIMESTAMP = datetime(9999, 12, 31, 23, 59, 59, 499999)
# Every builtin call name: a constant named so would read as the constant
# alone and as the builtin when called.
_BUILTIN_CALL_NAMES = _RESERVED_NAMES | _SHADOWABLE
# The fields that declare a name another read could mean, on any node but
# the reads and type references themselves.
_DECLARING_FIELDS = (
    "name",
    "alias",
    "binding_name",
    "target_binding_name",
    "local_name",
)
_NAME_READS = frozenset(
    {
        "NameExpr",
        "ParameterRefExpr",
        "TypeExpr",
        "TypeArgument",
        "Annotation",
        "NamedWindowReference",
    }
)

type _Value = bool | int | float | str | date


def _admitted_type(declared: TypeExpr) -> str | None:
    if (
        declared.name in _TYPES
        and not declared.arguments
        and declared.nullability is not Nullability.NULLABLE
    ):
        return declared.name
    return None


def _number(
    text: str, pattern: re.Pattern[str], kind: type[int] | type[float]
) -> int | float | None:
    if len(text) > _MAX_NUMBER_LENGTH or pattern.fullmatch(text) is None:
        return None
    value = kind(text.replace("_", ""))
    return value if math.isfinite(value) else None


def _temporal(type_name: str, text: str) -> date | None:
    """The `Date` or `Timestamp` a Text literal or `--set` value spells."""

    try:
        if type_name == "Date" and _DATE.fullmatch(text):
            value: date = date.fromisoformat(text)
        elif type_name == "Timestamp" and _TIMESTAMP.fullmatch(text):
            value = datetime.fromisoformat(text)
            if value > _LAST_TIMESTAMP:
                return None
        else:
            return None
    except ValueError:
        return None
    return value if value.year >= 1000 else None


def _source_value(type_name: str, expression: Expression) -> _Value | None:
    """The value of a constant's initializer when it is one literal of its
    type: a negative number is a minus sign before the literal."""

    sign = 1
    if (
        type_name in {"Int", "Float"}
        and type(expression) is UnaryExpr
        and cast(UnaryExpr, expression).operator == "-"
    ):
        sign, expression = -1, cast(UnaryExpr, expression).operand
    if type(expression) is not LiteralExpr:
        return None
    value = cast(LiteralExpr, expression).value
    if type_name == "Bool":
        return value if type(value) is bool else None
    if type_name == "Int":
        return sign * value if type(value) is int else None
    if type_name == "Float":
        return sign * value if type(value) is float else None
    if type(value) is not str:
        return None
    return value if type_name == "Text" else _temporal(type_name, value)


def _set_value(type_name: str, text: str) -> _Value | None:
    """The value a `--set` text spells, read as a literal of the type."""

    if type_name == "Bool":
        return {"True": True, "true": True, "False": False, "false": False}.get(text)
    if type_name == "Int":
        return _number(text, _INT, int)
    if type_name == "Float":
        return _number(text, _FLOAT, float)
    if type_name == "Text":
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return None
        return text
    return _temporal(type_name, text)


def _expression(type_name: str, value: _Value, span: Span) -> Expression:
    """The expression a read of a constant of ``value`` stands for, as it
    would be written there: a negative number keeps its minus sign."""

    if type_name in {"Int", "Float"} and cast(int | float, value) < 0:
        return UnaryExpr(
            span=span,
            operator="-",
            operand=LiteralExpr(span=span, value=-cast(int | float, value)),
        )
    return LiteralExpr(span=span, value=value)


def override_constants(script: Script, settings: Sequence[tuple[str, str]]) -> Script:
    """``script`` with each `--set NAME=VALUE` written as the value of every
    constant ``NAME``; raises ValueError with the usage message for a name
    that no constant declares or a value that is no literal of its type. A
    constant of a type that has no constants, or whose source value is no
    literal of its type, keeps its source value, whose error analysis
    reports: `--set` changes a value, never whether the file is valid."""

    constants = list(script.constants)
    for name, text in settings:
        found = [index for index, item in enumerate(constants) if item.name == name]
        if not found:
            raise ValueError(f"--set {name}: no top-level constant {name} is declared")
        for index in found:
            constant = constants[index]
            type_name = _admitted_type(constant.type)
            if type_name is None:
                continue
            value = _set_value(type_name, text)
            if value is None:
                raise ValueError(
                    f"--set {name}: constant {name} has type {type_name}; "
                    f"write {_VALUE_FORMS[type_name]}"
                )
            if _source_value(type_name, constant.value) is None:
                continue
            span = constant.value.span
            # As written in source: a Date or Timestamp is a Text literal.
            constants[index] = replace(
                constant,
                value=LiteralExpr(span=span, value=text)
                if type_name in {"Date", "Timestamp"}
                else _expression(type_name, value, span),
            )
    return replace(script, constants=tuple(constants))


def constant_diagnostics(script: Script) -> tuple[Diagnostic, ...]:
    """Every error of the constants of a single file, in source order: a
    type or value that is not one literal of a constant type, a repeated
    name (PIE-S2001), a name the file also declares otherwise or a builtin
    call name, and a read that is a source connector argument, a GROUP BY or
    ORDER BY key or an unnamed SELECT item."""

    if not script.constants:
        return ()
    found: list[Diagnostic] = []
    seen: set[str] = set()
    declared = _declared_names(script)
    for constant in script.constants:
        type_name = _admitted_type(constant.type)
        if type_name is None:
            found.append(_error(CONSTANT_CODE, _TYPE_MESSAGE, constant.type.span))
        elif _source_value(type_name, constant.value) is None:
            found.append(
                _error(
                    CONSTANT_CODE,
                    f"Constant `{constant.name}` takes one `{type_name}` literal: "
                    f"{_SOURCE_FORMS[type_name]}.",
                    constant.value.span,
                )
            )
        if constant.name in seen:
            found.append(
                _error(
                    "PIE-S2001",
                    f"Duplicate symbol name in constant namespace: {constant.name}",
                    constant.span,
                )
            )
        elif constant.name in declared:
            found.append(
                _error(
                    CONSTANT_CODE,
                    f"Constant `{constant.name}` is also declared as another name "
                    "in this file; give the constant a name of its own.",
                    constant.span,
                )
            )
        elif constant.name in _BUILTIN_CALL_NAMES:
            found.append(
                _error(
                    CONSTANT_CODE,
                    f"Constant `{constant.name}` has the name of a built-in "
                    "function; give the constant a name of its own.",
                    constant.span,
                )
            )
        seen.add(constant.name)
    names = frozenset(seen)
    # What a source reads is part of its identity, never a constant's value.
    for definition in script.definitions:
        if type(definition) is SourceDef:
            for node in _tree_nodes(cast(SourceDef, definition).connector):
                if _reads(node, names):
                    found.append(
                        _error(
                            CONSTANT_CODE,
                            f"Constant `{cast(NameExpr, node).name}` is no source "
                            "connector argument; a source names what it reads "
                            "with a literal written there.",
                            cast(NameExpr, node).span,
                        )
                    )
    for node in _tree_nodes(_without_constants(script)):
        read = _key_read(node, names)
        if read is not None:
            found.append(
                _error(
                    CONSTANT_CODE,
                    f"Constant `{read.name}` is no GROUP BY or ORDER BY key; "
                    "a key reads a field or an output.",
                    read.span,
                )
            )
        elif (
            type(node) is SelectItem
            and cast(SelectItem, node).alias is None
            and _reads(cast(SelectItem, node).expression, names)
        ):
            name = cast(NameExpr, cast(SelectItem, node).expression).name
            found.append(
                _error(
                    CONSTANT_CODE,
                    f"A SELECT item that reads only constant `{name}` needs its "
                    f"own name, such as `value = {name}`.",
                    cast(Node, node).span,
                )
            )
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


def substitute_constants(
    script: Script,
    *,
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> Script:
    """``script`` without its constants, each read replaced by its value at
    the read's span; ``constant_diagnostics`` found no error."""

    if not script.constants:
        return script
    values: dict[str, tuple[str, _Value]] = {}
    for constant in script.constants:
        type_name = cast(str, _admitted_type(constant.type))
        values[constant.name] = (
            type_name,
            cast(_Value, _source_value(type_name, constant.value)),
        )

    def visit(original: object, rebuilt: object) -> object:
        del original
        if type(rebuilt) is NameExpr and cast(NameExpr, rebuilt).name in values:
            type_name, value = values[cast(NameExpr, rebuilt).name]
            return _expression(type_name, value, cast(NameExpr, rebuilt).span)
        return rebuilt

    rebuilt = _rebuild(
        _without_constants(script), visit, occurrence_observer=occurrence_observer
    )
    return cast(Script, rebuilt)


def constant_read_spans(
    script: Script,
) -> frozenset[tuple[str | None, int, int, int, int]]:
    """The source range of each read of a top-level constant, and of each call
    of a `def` or relationship that reads one (an inlined body takes its
    call's range), so a target that does not emit constants yet can tell them
    from written literals."""

    names = frozenset(constant.name for constant in script.constants)
    if not names:
        return frozenset()
    script = _without_constants(script)
    bodies = {
        definition.name: tuple(_tree_nodes(definition.body))
        for definition in (
            *(item for item in script.definitions if type(item) is FunctionDef),
            *script.relationship_templates,
        )
    }
    reading: set[str] = set()
    grown = True
    while grown:
        grown = False
        for name, nodes in bodies.items():
            if name not in reading and any(
                (type(node) is NameExpr and node.name in names)
                or (
                    type(node) is CallExpr
                    and type(node.callee) is NameExpr
                    and node.callee.name in reading
                )
                for node in nodes
            ):
                reading.add(name)
                grown = True
    return frozenset(
        (
            node.span.path,
            node.span.line,
            node.span.column,
            node.span.end_line,
            node.span.end_column,
        )
        for node in _tree_nodes(script)
        if (type(node) is NameExpr and node.name in names)
        or (
            type(node) is CallExpr
            and type(node.callee) is NameExpr
            and node.callee.name in reading
        )
    )


def _without_constants(script: Script) -> Script:
    return replace(script, constants=())


def _reads(expression: object, names: frozenset[str]) -> bool:
    return type(expression) is NameExpr and cast(NameExpr, expression).name in names


def _key_read(node: object, names: frozenset[str]) -> NameExpr | None:
    if type(node) is GroupByItem:
        key: object = cast(GroupByItem, node).key
    elif type(node) is OrderItem:
        key = cast(OrderItem, node).expression
    else:
        return None
    return cast(NameExpr, key) if _reads(key, names) else None


def _declared_names(script: Script) -> frozenset[str]:
    """Every name the file declares other than its constants: definitions,
    fields, parameters, lets, outputs, windows, bindings and imports."""

    found: set[str] = set()
    pending: list[object] = [_without_constants(script)]
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(cast(tuple[object, ...], value))
            continue
        kind = type(value)
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        for item in fields(value):
            child = getattr(value, item.name)
            if (
                item.name in _DECLARING_FIELDS
                and type(child) is str
                and kind.__name__ not in _NAME_READS
            ):
                found.add(child)
            pending.append(child)
    return frozenset(found)


def _error(code: str, message: str, span: Span) -> Diagnostic:
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
