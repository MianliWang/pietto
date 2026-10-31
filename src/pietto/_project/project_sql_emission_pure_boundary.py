"""Bounded data-only decoding and consistency of private emission observations.

This boundary accepts bytes/text or an already-parsed builtin mapping, checks
the closed schema, the canonical record order and the documented relations
between the serialized AST, tokens, ranges, values and both requirement
inventories, and returns an immutable view or one closed rejection.

It proves internal consistency only. It cannot authenticate source history,
recreate live verification or certify a database, and a coherent alternative
document can pass here; runtime correspondence is a separate check. Nothing
here imports the compiler, and a decoded view is never emission input.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import json
import math
import re
from types import MappingProxyType
from typing import Any, cast

from pietto._project import project_sql_emission_portable_schema as schema

__all__: tuple[str, ...] = ()


class Status(StrEnum):
    OK = "ok"
    INVALID_INPUT = "invalid_input"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_JSON = "invalid_json"
    DUPLICATE_KEY = "duplicate_key"
    UNKNOWN_FORMAT = "unknown_format"
    INVALID_DOCUMENT = "invalid_document"
    INVALID_RECORD = "invalid_record"
    INVALID_FIELD = "invalid_field"
    INVALID_VALUE = "invalid_value"
    INVALID_REF = "invalid_ref"
    INVALID_RELATION = "invalid_relation"
    RESOURCE_LIMIT = "resource_limit"


@dataclass(frozen=True, slots=True, order=True)
class Ref:
    kind: str
    index: int


@dataclass(frozen=True, slots=True, order=True)
class PlanRef:
    kind: str
    position: int


@dataclass(frozen=True, slots=True)
class Fixed:
    tag: str
    wire: bool | str

    @property
    def value(self) -> bool | int | float | str:
        if self.tag == "Int":
            return int(self.wire)
        if self.tag == "Float":
            return float.fromhex(str(self.wire))
        return self.wire


@dataclass(frozen=True, slots=True)
class Record:
    ref: Ref
    fields: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Range:
    """One token event (in byte order) or expression overlay (retained order)."""

    position: int
    kind: str
    role: str
    subject: PlanRef
    start: int
    end: int
    origins: tuple[Ref, ...]


class _Reject(Exception):
    def __init__(self, status: Status, detail: str) -> None:
        self.status, self.detail = status, detail


def _require(condition: object, detail: str, status=Status.INVALID_RELATION) -> None:
    if not condition:
        raise _Reject(status, detail)


@dataclass(frozen=True, slots=True)
class Outcome:
    status: Status
    view: View | None = None
    canonical_bytes: bytes | None = None
    detail: str | None = None


# -- raw JSON boundary -------------------------------------------------------

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1
# The reviewed signed Int storages a window ORDER key may carry, by width.
_SIGNED_STORAGE_BITS = {
    "pg_int2": 16,
    "pg_int4": 32,
    "pg_int8": 64,
    "my_smallint": 16,
    "my_int": 32,
    "my_bigint": 64,
    "my_signed_int": 64,
}


def _frame_offsets(frame) -> tuple[tuple[str, int], ...]:
    """Each finite endpoint of one documented frame, in retained order."""

    return tuple(
        (kind, int(str(text).split(" ", 1)[0]))
        for kind, text in (frame["start"], frame["end"])
        if kind in schema.FRAME_OFFSETS
    )


def _thresholds_exact(realization, direction, offsets) -> bool:
    """Whether a documented RANGE key domain keeps every threshold in signed64."""

    storage, domain = realization["storage"], realization["domain"]
    kind = storage.get("kind") if isinstance(storage, Mapping) else None
    bits = _SIGNED_STORAGE_BITS.get(kind) if type(kind) is str else None
    if bits is None or not isinstance(domain, Mapping):
        return False
    if domain.get("kind") != "int_range":
        return False
    try:
        low, high = int(domain["min"]), int(domain["max"])
    except (KeyError, TypeError, ValueError):
        return False
    if not -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1:
        return False
    for kind, offset in offsets:
        below = (kind == "offset_preceding") == (direction == "asc")
        lower, upper = (
            (low - offset, high - offset) if below else (low + offset, high + offset)
        )
        if lower < _I64_MIN or upper > _I64_MAX:
            return False
    return True


_VALUE_WINDOWS = frozenset({"lag", "lead", "first_value", "last_value", "nth_value"})
_PG_INT_OF_BITS = {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"}
_MYSQL_FIELD_DISPLAY = {"my_smallint": 6, "my_int": 11, "my_bigint": 20}


def _window_value_representation(family, read, carrier, default, doc):
    """The (storage, domain) one documented window value result must publish.

    Data-only consistency over the serialized facts: the carrier's own class,
    width and interval and the default literal decide it; None marks a
    combination no Phase66 rule publishes (a MySQL Bool value or an Int carrier
    without an established field/materialization/anchored-expression origin).
    """

    storage, domain = carrier["storage"], carrier["domain"]
    if not isinstance(storage, Mapping) or not isinstance(domain, Mapping):
        return None
    if family == "mysql" and carrier["tag"] == "Bool":
        return None
    if carrier["tag"] != "Int":
        return dict(storage), dict(domain)
    kind = storage.get("kind")
    if domain.get("kind") != "int_range" or type(kind) is not str:
        return None
    low, high = int(domain["min"]), int(domain["max"])
    number = None
    if default is not None and default != "NULL":
        if re.fullmatch(r"-?(0|[1-9][0-9]*)", str(default)) is None:
            return None
        number = int(default)
        if not _I64_MIN <= number <= _I64_MAX:
            return None
        low, high = min(low, number), max(high, number)
    if family == "postgres":
        bits = _SIGNED_STORAGE_BITS.get(kind) if kind.startswith("pg_") else None
        if bits is None:
            return None
        if number is not None:
            bits = max(bits, 32 if -(1 << 31) <= number < 1 << 31 else 64)
        result = _PG_INT_OF_BITS[bits]
    else:
        if read["aggregate"] is not None:
            display = {**_MYSQL_FIELD_DISPLAY, "my_signed_int": 20}.get(kind)
        elif read["literal"] is not None:
            value = doc[read["literal"]]["value"]
            while value.kind == "sql_unary":
                value = doc[value]["operand"]
            display = (
                21
                if value.kind == "sql_anchor"
                and doc[value]["physical_type"] == "my_signed_int"
                and kind == "my_signed_int"
                else None
            )
        else:
            display = (
                _MYSQL_FIELD_DISPLAY.get(kind)
                if (read["field"] is None) is not (read["window"] is None)
                else None
            )
        if display is None or (number is not None and number < 0):
            return None
        if number is not None:
            display = max(display, len(str(number)) + 1)
        result = "my_int" if display < 10 else "my_bigint"
    bits = _SIGNED_STORAGE_BITS[result]
    if not -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1:
        return None
    return {"kind": result}, {"kind": "int_range", "min": str(low), "max": str(high)}


_STRING = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"', re.S)
_BRACKETS = re.compile(r"[\[\]{}]")
_NAT = re.compile(r"0|[1-9][0-9]*")
_INT = re.compile(r"-?(0|[1-9][0-9]*)")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Reject(Status.DUPLICATE_KEY, "duplicate object key")
        result[key] = value
    return result


def _raw_int(text: str) -> int:
    _require(
        len(text) <= schema.MAX_NAT_DIGITS, "integer lexeme", Status.RESOURCE_LIMIT
    )
    _require(_NAT.fullmatch(text), "integer lexeme", Status.INVALID_VALUE)
    return int(text)


def _raw_float(_text: str) -> float:
    raise _Reject(Status.INVALID_VALUE, "JSON numbers are natural integers")


def _prescan(text: str) -> None:
    """Bound nesting and JSON value count before any container is built."""
    stripped = _STRING.sub("", text)
    count = stripped.count(",") + stripped.count("[") + stripped.count("{") + 1
    _require(count <= schema.MAX_JSON_VALUES, "JSON values", Status.RESOURCE_LIMIT)
    depth = 0
    for match in _BRACKETS.finditer(stripped):
        depth += 1 if match.group() in "[{" else -1
        _require(depth <= schema.MAX_DEPTH, "JSON depth", Status.RESOURCE_LIMIT)


def parse_emission_observation(raw: bytes | str) -> Outcome:
    """Strict raw boundary: every object key occurrence and lexeme is inspected."""
    try:
        _require(type(raw) in (bytes, str), "input type", Status.INVALID_INPUT)
        _require(
            len(raw) <= schema.MAX_DOCUMENT_BYTES,
            "document size",
            Status.RESOURCE_LIMIT,
        )
        text = raw.decode("utf-8") if type(raw) is bytes else raw
        assert isinstance(text, str)
        _require(
            len(text.encode("utf-8")) <= schema.MAX_DOCUMENT_BYTES,
            "document size",
            Status.RESOURCE_LIMIT,
        )
        _prescan(text)
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_raw_int,
            parse_float=_raw_float,
            parse_constant=_raw_float,
        )
        return evaluate_emission_observation(value)
    except _Reject as error:
        return Outcome(error.status, detail=error.detail)
    except UnicodeError:
        return Outcome(Status.INVALID_UTF8, detail="UTF-8")
    except (RecursionError, MemoryError):
        return Outcome(Status.RESOURCE_LIMIT, detail="resources")
    except (TypeError, ValueError):
        return Outcome(Status.INVALID_JSON, detail="JSON")


def _input_tree(root: object) -> None:
    """Bound a parsed builtin tree; never call user-defined methods."""
    pending: list[tuple[Any, int]] = [(root, 0)]
    active: set[int] = set()
    exits: list[tuple[int, int]] = []
    nodes = 0
    while pending:
        value, depth = pending.pop()
        while exits and exits[-1][1] >= depth:
            active.discard(exits.pop()[0])
        nodes += 1
        _require(nodes <= schema.MAX_JSON_VALUES, "JSON values", Status.RESOURCE_LIMIT)
        _require(depth <= schema.MAX_DEPTH, "JSON depth", Status.RESOURCE_LIMIT)
        kind = type(value)
        if value is None or kind is bool:
            continue
        if kind is int:
            _require(
                0 <= value <= schema.MAX_NAT, "natural integer", Status.INVALID_VALUE
            )  # type: ignore[operator]
            continue
        if kind is str:
            _require(
                len(value) <= schema.MAX_SQL_BYTES,  # type: ignore[arg-type]
                "text size",
                Status.RESOURCE_LIMIT,
            )
            continue
        _require(kind in (dict, list), "builtin JSON value", Status.INVALID_INPUT)
        _require(id(value) not in active, "container cycle", Status.INVALID_INPUT)
        active.add(id(value))
        exits.append((id(value), depth))
        if kind is dict:
            items = dict.items(value)  # type: ignore[arg-type]
            _require(
                all(type(key) is str for key, _ in items),
                "object key",
                Status.INVALID_FIELD,
            )
            pending.extend((child, depth + 1) for _, child in items)
        else:
            pending.extend((child, depth + 1) for child in list.__iter__(value))  # type: ignore[arg-type]


# -- closed schema decoding -------------------------------------------------


def _local(data: Any, kinds) -> Ref:
    _require(
        type(data) is list
        and len(data) == 2
        and type(data[0]) is str
        and type(data[1]) is int,
        "local reference",
        Status.INVALID_REF,
    )
    _require(data[0] in kinds, "reference domain", Status.INVALID_REF)
    return Ref(cast(str, data[0]), cast(int, data[1]))


def _plan(data: Any) -> PlanRef:
    _require(
        type(data) is dict
        and list(data) == ["kind", "position"]
        and type(data["kind"]) is str
        and type(data["position"]) is int,
        "plan reference",
        Status.INVALID_REF,
    )
    kind, position = data["kind"], data["position"]
    _require(
        kind in schema.PLAN_KINDS or (kind == schema.SCOPE_KIND and position == 0),
        "plan reference kind",
        Status.INVALID_REF,
    )
    return PlanRef(cast(str, kind), cast(int, position))


def _freeze(data: Any) -> Any:
    if type(data) is dict:
        _require(list(data) == sorted(data), "data key order", Status.INVALID_VALUE)
        return MappingProxyType({key: _freeze(value) for key, value in data.items()})
    if type(data) is list:
        return tuple(_freeze(item) for item in data)
    return data


def _fixed(data: Any) -> Fixed:
    _require(
        type(data) is dict and list(data) == ["tag", "value"],
        "fixed",
        Status.INVALID_VALUE,
    )
    tag, wire = data["tag"], data["value"]
    _require(tag in schema.TAGS, "fixed tag", Status.INVALID_VALUE)
    if tag == "Bool":
        _require(type(wire) is bool, "Bool value", Status.INVALID_VALUE)
    elif tag == "Int":
        _require(
            type(wire) is str
            and len(wire) <= schema.MAX_INT_TEXT
            and _INT.fullmatch(wire)
            and wire != "-0"
            and -(1 << 63) <= int(wire) < 1 << 63,
            "Int value",
            Status.INVALID_VALUE,
        )
    elif tag == "Float":
        _require(
            type(wire) is str and len(wire) <= schema.MAX_FLOAT_TEXT,
            "Float value",
            Status.INVALID_VALUE,
        )
        try:
            value = float.fromhex(cast(str, wire))
        except (OverflowError, ValueError):
            raise _Reject(Status.INVALID_VALUE, "Float value") from None
        _require(
            math.isfinite(value) and value.hex() == wire,
            "Float value",
            Status.INVALID_VALUE,
        )
    else:
        _require(type(wire) is str, "Text value", Status.INVALID_VALUE)
    return Fixed(cast(str, tag), cast(bool | str, wire))


def _value(spec: str, data: Any, refs: list[Ref], plans: set[PlanRef]) -> Any:
    if spec[0] == "?":
        return None if data is None else _value(spec[1:], data, refs, plans)
    if spec[0] == "*":
        _require(type(data) is list, "list", Status.INVALID_VALUE)
        return tuple(_value(spec[1:], item, refs, plans) for item in data)
    if spec[0] == "@":
        ref = _local(data, spec[1:].split("|"))
        refs.append(ref)
        return ref
    if spec == "nat":
        _require(type(data) is int, "natural integer", Status.INVALID_VALUE)
        return data
    if spec in ("text", "sql"):
        limit = schema.MAX_SQL_BYTES if spec == "sql" else schema.MAX_TEXT_BYTES
        _require(type(data) is str, "text", Status.INVALID_VALUE)
        _require(len(data.encode("utf-8")) <= limit, "text size", Status.RESOURCE_LIMIT)
        return data
    if spec == "bool":
        _require(type(data) is bool, "boolean", Status.INVALID_VALUE)
        return data
    if spec == "none":
        _require(data is None, "empty field", Status.INVALID_VALUE)
        return None
    if spec == "nullable":
        _require(
            type(data) is bool or data == "unknown", "nullable", Status.INVALID_VALUE
        )
        return data
    if spec == "data":
        return _freeze(data)
    if spec == "fixed":
        return _fixed(data)
    if spec == "plan":
        ref = _plan(data)
        plans.add(ref)
        return ref
    if spec == "subject":
        if type(data) is dict:
            return _value("plan", data, refs, plans)
        ref = _local(data, schema.RECORDS)
        refs.append(ref)
        return ref
    assert spec == "scope"
    if data == "statement":
        return "statement"
    if type(data) is list and len(data) == 2 and type(data[0]) is list:
        owner = _local(data[0], ("owner",))
        refs.append(owner)
        site = _plan(data[1])
        plans.add(site)
        return (owner, site)
    ref = _local(data, ("owner",))
    refs.append(ref)
    return ref


def _decode(
    value: Any,
) -> tuple[dict[Ref, Record], list[Ref], dict[Ref, list[Ref]], set]:
    _require(
        type(value) is dict and list(value) == ["format", "root", "records"],
        "document keys",
        Status.INVALID_DOCUMENT,
    )
    _require(value["format"] == schema.FORMAT, "format", Status.UNKNOWN_FORMAT)
    _require(
        _local(value["root"], ("artifact",)) == Ref(*schema.ROOT),
        "root",
        Status.INVALID_DOCUMENT,
    )
    rows: Any = value["records"]
    _require(type(rows) is list and rows, "records", Status.INVALID_DOCUMENT)
    _require(len(rows) <= schema.MAX_RECORDS, "records", Status.RESOURCE_LIMIT)
    records: dict[Ref, Record] = {}
    order: list[Ref] = []
    children: dict[Ref, list[Ref]] = {}
    plans: set[PlanRef] = set()
    edges = 0
    row: Any
    for row in rows:
        _require(
            type(row) is dict and list(row) == ["ref", "fields"],
            "record shape",
            Status.INVALID_RECORD,
        )
        head: Any = row["ref"]
        _require(
            type(head) is list
            and len(head) == 2
            and type(head[0]) is str
            and head[0] in schema.RECORDS,
            "record kind",
            Status.INVALID_RECORD,
        )
        ref = _local(head, schema.RECORDS)
        _require(ref not in records, "duplicate record", Status.INVALID_REF)
        rule = schema.RECORDS[ref.kind]
        fields: Any = row["fields"]
        _require(
            type(fields) is dict and list(fields) == [name for name, _ in rule],
            "record fields",
            Status.INVALID_FIELD,
        )
        refs: list[Ref] = []
        decoded = {name: _value(spec, fields[name], refs, plans) for name, spec in rule}
        edges += len(refs)
        _require(edges <= schema.MAX_EDGES, "reference edges", Status.RESOURCE_LIMIT)
        records[ref] = Record(ref, MappingProxyType(decoded))
        order.append(ref)
        children[ref] = refs
    return records, order, children, plans


def _canonical_order(records, order, children) -> None:
    """Records must be exactly the first-visit preorder from the root."""
    expected: list[Ref] = []
    counters: dict[str, int] = {}
    seen: set[Ref] = set()
    stack = [Ref(*schema.ROOT)]
    while stack:
        ref = stack.pop()
        if ref in seen:
            continue
        _require(ref in records, "dangling reference", Status.INVALID_REF)
        _require(
            counters.get(ref.kind, 0) == ref.index,
            "reference index",
            Status.INVALID_REF,
        )
        counters[ref.kind] = ref.index + 1
        seen.add(ref)
        expected.append(ref)
        stack.extend(reversed(children[ref]))
    _require(expected == order, "canonical record order", Status.INVALID_REF)


# -- relations ---------------------------------------------------------------


class _Doc:
    def __init__(self, records: dict[Ref, Record]) -> None:
        self.records = records
        self.kinds: dict[str, list[Ref]] = {}
        for ref in records:
            self.kinds.setdefault(ref.kind, []).append(ref)

    def __getitem__(self, ref: Ref) -> Mapping[str, Any]:
        return self.records[ref].fields

    def all(self, kind: str) -> list[Ref]:
        return self.kinds.get(kind, [])


def _json(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_raw_float,
            parse_constant=_raw_float,
        )
    except (TypeError, ValueError, RecursionError):
        raise _Reject(Status.INVALID_RELATION, "embedded JSON text") from None


UNITS = ("row_body", "row_result_body", "join_body", "set_body")
SCOPE_ROLES = frozenset(
    {
        "value_scope",
        "carry_scope",
        "group_key_scope",
        "result_scope",
        "window_result_scope",
        "grouping_scope",
        "window_partition_scope",
        "window_order_scope",
        "window_argument_scope",
        "order_scope",
        "result_carry_scope",
        "column_scope",
        "relation_scope",
        "stage_scope",
        "join_scope",
        "set_input_scope",
        "set_scope",
        "equality_scope",
        "join_column_scope",
    }
)
COLUMN_ROLES = frozenset(
    {
        "value_column",
        "carry_column",
        "group_key_column",
        "result_column",
        "window_result_column",
        "grouping_column",
        "window_partition_column",
        "window_order_column",
        "window_argument_column",
        "order_column",
        "result_carry_column",
        "column",
        "join_column",
        "set_input_column",
        "equality_column",
        "in_column",
        "capture_column",
    }
)
RELATION_ROLES = {
    "namespace": "namespace",
    "set_namespace": "namespace",
    "join_namespace": "namespace",
    "relation": "name",
    "set_relation": "name",
    "join_relation": "name",
    "exists_namespace": "namespace",
    "exists_relation": "name",
    "scalar_namespace": "namespace",
    "scalar_relation": "name",
    "in_namespace": "namespace",
    "in_relation": "name",
}
UNIT_REFERENCE_ROLES = frozenset(
    {
        "cte_reference",
        "stage_reference",
        "join_reference",
        "set_reference",
        "exists_reference",
        "scalar_reference",
        "in_reference",
    }
)
# Roles that only the WITH preamble may carry, never a unit's own SELECT.
PREAMBLE_ROLES = frozenset(
    {
        "with",
        "cte_separator",
        "cte_name",
        "cte_columns_open",
        "terminal_separator",
        "terminal_column",
        "cte_body_open",
        "cte_body_close",
        "with_body",
    }
)


def _unit_plan(doc: _Doc, ref: Ref) -> PlanRef:
    fields = doc[ref]
    if ref.kind == "row_body":
        return fields["block"]
    if ref.kind == "row_result_body":
        return fields["boundaries"][0]
    if ref.kind == "join_body":
        return fields["join"]
    if ref.kind == "set_body":
        return fields["body"]
    return doc[fields["definition"]]["original"]


def _block_column_name(doc, target, column) -> str | None:
    """The rendered name of the one producer output a scalar read reads."""
    if type(column) is not int:
        return None
    producer = target["producer"]
    if producer.kind == "bound_source":
        names = [
            doc[field]["column"]
            for field in doc[producer]["fields"]
            if doc[field]["ordinal"] == column
        ]
        return names[0] if len(names) == 1 else None
    if _inline_producer(doc, producer):
        # A capturing let's inline body names its outputs by their labels.
        outputs = doc[producer]["columns"]
        return doc[outputs[column]]["label"] if 0 <= column < len(outputs) else None
    columns = doc[producer]["cte_columns"]
    return doc[columns[column]]["name"] if 0 <= column < len(columns) else None


def _value_tag(doc, value):
    while value.kind == "sql_unary":
        value = doc[value]["operand"]
    if value.kind in {
        "sql_stage_reference",
        "sql_any_reference",
        "sql_operation",
        "sql_block_read",
        "sql_any_read",
        "sql_captured_reference",
    }:
        return doc[doc[value]["realization"]]["tag"]
    return doc[value]["tag"]


def _value_realization(doc, value):
    """One retained or fixed-value realization without compiler imports."""

    if value.kind == "sql_unary":
        operand = _value_realization(doc, doc[value]["operand"])
        if operand is None or doc[value]["operator"] not in {"+", "-"}:
            return None
        if operand["tag"] == "Int":
            try:
                low, high = int(operand["domain"]["min"]), int(operand["domain"]["max"])
            except (KeyError, TypeError, ValueError):
                return None
            if doc[value]["operator"] == "-":
                low, high = -high, -low
            return {
                "tag": "Int",
                "storage": operand["storage"],
                "nullable": operand["nullable"],
                "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
            }
        if operand["tag"] == "Float":
            return operand
        return None
    if value.kind == "sql_anchor":
        anchor = doc[value]
        leaf = doc[anchor["operand"]]
        fixed = (
            leaf["value"]
            if anchor["operand"].kind == "sql_literal"
            else doc[leaf["fixed"]]["value"]
            if anchor["operand"].kind == "sql_parameter"
            else None
        )
        if fixed is None or fixed.tag != anchor["tag"]:
            return None
        tag, physical = fixed.tag, anchor["physical_type"]
        if tag == "Bool" and physical == "pg_bool":
            return {
                "tag": tag,
                "storage": {"kind": physical},
                "nullable": False,
                "domain": {"kind": "bool01"},
            }
        if tag == "Int" and physical in _SIGNED_STORAGE_BITS:
            number = fixed.value
            if type(number) is not int:
                return None
            bits = _SIGNED_STORAGE_BITS[physical]
            if not -(1 << (bits - 1)) <= number <= (1 << (bits - 1)) - 1:
                return None
            return {
                "tag": tag,
                "storage": {"kind": physical},
                "nullable": False,
                "domain": {
                    "kind": "int_range",
                    "min": str(number),
                    "max": str(number),
                },
            }
        if tag == "Float" and physical == "pg_float8" and type(fixed.value) is float:
            return {
                "tag": tag,
                "storage": {"kind": physical},
                "nullable": False,
                "domain": {"kind": "finite_float", "format": "binary64"},
            }
        if tag == "Text" and physical == "pg_text" and type(fixed.value) is str:
            return {
                "tag": tag,
                "storage": {"kind": physical},
                "nullable": False,
                "domain": {
                    "kind": "text",
                    "max_characters": len(fixed.value),
                    "encoding": "UTF8",
                    "collation": "C",
                    "padding": "NO PAD",
                },
            }
        return None
    if value.kind in {
        "sql_stage_reference",
        "sql_any_reference",
        "sql_operation",
        "sql_block_read",
        "sql_any_read",
        "sql_captured_reference",
    }:
        return doc[doc[value]["realization"]]
    return None


def _literal_provenance(doc, value):
    """A direct literal or the retained literal origin of a materialized let."""

    if value.kind != "sql_stage_reference":
        return value
    literal = doc[doc[value]["column"]]["literal"]
    return None if literal is None else doc[literal]["value"]


def _literal_int(doc, value):
    """One authored Int literal, including its normalized unary sign."""

    value = _literal_provenance(doc, value)
    if value is None:
        return None
    if value.kind == "sql_anchor":
        leaf = doc[value]["operand"]
        fixed = (
            doc[leaf]["value"]
            if leaf.kind == "sql_literal"
            else doc[doc[leaf]["fixed"]]["value"]
            if leaf.kind == "sql_parameter"
            else None
        )
        return fixed.value if fixed is not None and fixed.tag == "Int" else None
    if value.kind == "sql_unary":
        operand = _literal_int(doc, doc[value]["operand"])
        if operand is None:
            return None
        return operand if doc[value]["operator"] == "+" else -operand
    return None


def _literal_text(doc, value):
    """One authored Text literal; units do not admit parameters or fields."""

    value = _literal_provenance(doc, value)
    if value is None:
        return None
    if value.kind != "sql_anchor":
        return None
    leaf = doc[value]["operand"]
    fixed = (
        doc[leaf]["value"]
        if leaf.kind == "sql_literal"
        else doc[doc[leaf]["fixed"]]["value"]
        if leaf.kind == "sql_parameter"
        else None
    )
    return fixed.value if fixed is not None and fixed.tag == "Text" else None


def _is_realization(realization, tag, storage, domain) -> bool:
    return (
        realization is not None
        and realization["tag"] == tag
        and dict(realization["storage"]) == storage
        and dict(realization["domain"]) == domain
    )


def _is_pg_float(realization) -> bool:
    return _is_realization(
        realization,
        "Float",
        {"kind": "pg_float8"},
        {"kind": "finite_float", "format": "binary64"},
    )


def _is_pg_text(realization, *, nullable=None, maximum=None) -> bool:
    return _is_realization(
        realization,
        "Text",
        {"kind": "pg_text"},
        {
            "kind": "text",
            "max_characters": maximum,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    ) and (nullable is None or realization["nullable"] == nullable)


def _is_pg_text_input(realization) -> bool:
    """One ordered PostgreSQL Text value with its complete comparison profile."""

    if realization is None or realization["tag"] != "Text":
        return False
    domain = realization["domain"]
    return (
        dict(realization["storage"]) == {"kind": "pg_text"}
        and domain["kind"] == "text"
        and type(domain["max_characters"]) is int
        and domain["max_characters"] >= 0
        and domain["encoding"] == "UTF8"
        and domain["collation"] == "C"
        and domain["padding"] == "NO PAD"
    )


def _is_pg_text_value(doc, value) -> bool:
    """A row Text carrier or one anchored PostgreSQL Text literal."""

    realization = _value_realization(doc, value)
    if realization is not None:
        return _is_pg_text_input(realization)
    if value.kind != "sql_anchor":
        return False
    anchor = doc[value]
    leaf = doc[anchor["operand"]]
    fixed = (
        leaf["value"]
        if value.kind == "sql_anchor" and anchor["operand"].kind == "sql_literal"
        else doc[leaf["fixed"]]["value"]
        if anchor["operand"].kind == "sql_parameter"
        else None
    )
    return (
        anchor["tag"] == "Text"
        and anchor["physical_type"] == "pg_text"
        and fixed is not None
        and fixed.tag == "Text"
    )


def _pg_decimal_parameters(realization):
    if realization is None or realization["tag"] != "Decimal":
        return None
    storage, domain = realization["storage"], realization["domain"]
    precision, scale = storage.get("precision"), storage.get("scale")
    if not (
        dict(storage) == {"kind": "pg_numeric", "precision": precision, "scale": scale}
        and type(precision) is int
        and type(scale) is int
        and 0 <= scale <= precision <= 65
        and dict(domain) == {"kind": "decimal", "precision": precision, "scale": scale}
    ):
        return None
    return precision, scale


def _is_pg_int(realization) -> bool:
    if realization is None or realization["tag"] != "Int":
        return False
    storage, domain = realization["storage"], realization["domain"]
    kind = storage.get("kind")
    bits = _SIGNED_STORAGE_BITS.get(kind)
    if dict(storage) != {"kind": kind} or bits is None:
        return False
    try:
        low, high = int(domain["min"]), int(domain["max"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        dict(domain) == {"kind": "int_range", "min": str(low), "max": str(high)}
        and -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1
    )


# Q1/Q2 evidence: a bigint result bounded by the target's checked signed
# 64-bit operation or narrowing (SQLSTATE 22003), not by a static range.
_TARGET_CHECKED = "target_checked_signed64_narrowing"


def _aggregate_casts(family: str, function: str) -> tuple[str | None, str | None]:
    """The reviewed argument and result casts of one aggregate: AVG(Int)
    averages binary64 and PostgreSQL SUM(Int) is bigint before and after."""
    if function == "avg":
        return ("pg_catalog.float8" if family == "postgres" else "DOUBLE"), None
    if function == "sum":
        return "pg_catalog.int8", "pg_catalog.int8"
    return None, None


def _is_pg_order_value(realization) -> bool:
    """The closed PostgreSQL aggregate-order carrier domain."""

    if realization is None:
        return False
    if realization["tag"] == "Int":
        return _is_pg_int(realization)
    if realization["tag"] == "Bool":
        return dict(realization["storage"]) == {"kind": "pg_bool"} and dict(
            realization["domain"]
        ) == {"kind": "bool01"}
    if realization["tag"] == "Text":
        return _is_pg_text_input(realization)
    if realization["tag"] == "Decimal":
        return _pg_decimal_parameters(realization) is not None
    if realization["tag"] == "Timestamp":
        return _is_realization(
            realization,
            "Timestamp",
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "timestamp"},
        )
    if realization["tag"] == "Date":
        return _is_realization(
            realization, "Date", {"kind": "pg_date"}, {"kind": "date"}
        )
    if realization["tag"] == "UUID":
        return _is_realization(
            realization,
            "UUID",
            {"kind": "pg_uuid"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        )
    return False


def _is_key_value(realization, family: str, *, partition: bool = False) -> bool:
    if family == "postgres":
        return _is_pg_order_value(realization)
    if realization is None or family != "mysql":
        return False
    tag, storage, domain = (
        realization["tag"],
        realization["storage"],
        realization["domain"],
    )
    if tag == "Int":
        return storage.get("kind") in {
            "my_smallint",
            "my_int",
            "my_bigint",
            "my_signed_int",
        } and _is_pg_int(realization)
    if tag == "Bool":
        return dict(storage) in (
            {"kind": "my_bool01"},
            {"kind": "my_signed_bool"},
        ) and dict(domain) == {"kind": "bool01"}
    if tag == "Decimal":
        if storage.get("kind") != "my_decimal":
            return False
        return (
            _pg_decimal_parameters(
                {**realization, "storage": {**storage, "kind": "pg_numeric"}}
            )
            is not None
        )
    if tag == "Text":
        maximum = domain.get("max_characters")
        length = storage.get("length")
        return (
            type(maximum) is int
            and maximum >= 0
            and dict(domain)
            == {
                "kind": "text",
                "max_characters": maximum,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            }
            and (
                dict(storage) == {"kind": "my_utf8mb4_text"}
                or type(length) is int
                and maximum <= length <= 16383
                and dict(storage) == {"kind": "my_varchar", "length": length}
            )
        )
    if tag == "Date":
        return _is_realization(
            realization, "Date", {"kind": "my_date"}, {"kind": "date"}
        )
    if tag == "Timestamp":
        return _is_realization(
            realization,
            "Timestamp",
            {"kind": "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        )
    if tag == "UUID" and partition:
        return _is_realization(
            realization,
            "UUID",
            {"kind": "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        )
    return False


def _source_field_matches_stage(doc, stage) -> bool:
    """A source-derived stage keeps its source carrier, apart from null widening."""

    field = stage["field"]
    if field is None:
        return True
    bound, realization = doc[field], doc[stage["realization"]]
    try:
        representation = _json(bound["representation"])
    except _Reject:
        return False
    return (
        realization["tag"] == bound["logical"]["name"]
        and dict(realization["storage"]) == representation["storage"]
        and dict(realization["domain"]) == representation["domain"]
        and (
            realization["nullable"] is True
            or realization["nullable"] == representation["nullable"]
        )
    )


def _validate_any_scopes(doc):
    kinds = (
        "sql_anchor",
        "sql_unary",
        "sql_null",
        "sql_operation",
        "sql_stage_reference",
        "sql_block_read",
        "sql_captured_reference",
        "sql_any_read",
        "sql_any_reference",
    )
    nodes = tuple(ref for kind in kinds for ref in doc.all(kind))
    if not any(ref.kind in {"sql_any_read", "sql_any_reference"} for ref in nodes):
        return

    def children(ref):
        value = doc[ref]
        if ref.kind == "sql_any_read":
            return (*value["operands"], value["predicate"])
        if ref.kind in {"sql_operation", "sql_block_read"}:
            return value["operands"]
        if ref.kind == "sql_unary":
            return (value["operand"],)
        return ()

    child_nodes = {child for ref in nodes for child in children(ref)}
    external_roots = []
    for kind, fields in schema.RECORDS.items():
        if kind in kinds:
            continue
        for ref in doc.all(kind):
            for name, spec in fields:
                if spec.lstrip("?*") != schema._VALUE:
                    continue
                value = doc[ref][name]
                if value is not None:
                    external_roots.extend(value if spec.startswith("*") else (value,))
    roots = (*external_roots, *(ref for ref in nodes if ref not in child_nodes))
    pending: list[tuple[Ref, tuple[tuple[PlanRef, Ref], ...], frozenset[Ref]]] = [
        (ref, (), frozenset()) for ref in roots
    ]
    seen = set()
    while pending:
        ref, active, path = pending.pop()
        _require(ref not in path, "ANY expression cycle")
        seen.add(ref)
        value = doc[ref]
        path = path | {ref}
        if ref.kind == "sql_any_reference":
            targets = tuple(target for use, target in active if use == value["use"])
            _require(len(targets) == 1, "ANY reference lexical scope")
            target = doc[targets[0]]
            column = doc[value["column"]]
            position = value["position"]
            _require(
                value["scope"] == target["symbol"]
                and value["port"] == column["terminal"]
                and column["scope"] == target["symbol"]
                and column["position"] == position
                and column["name"] == _block_column_name(doc, target, position)
                and doc[value["realization"]] == doc[column["realization"]],
                "ANY reference target column",
            )
            producer = target["producer"]
            if producer.kind == "bound_source":
                fields = tuple(
                    field
                    for field in doc[producer]["fields"]
                    if doc[field]["ordinal"] == position
                )
                _require(
                    len(fields) == 1 and column["field"] == fields[0],
                    "ANY source field",
                )
            else:
                outputs = doc[producer]["columns"]
                _require(position < len(outputs), "ANY output field")
                actual = doc[doc[outputs[position]]["column"]]
                _require(
                    column["terminal"] == actual["terminal"]
                    and column["realization"] == actual["realization"],
                    "ANY output field",
                )
        elif ref.kind == "sql_any_read":
            target = value["target"]
            use = doc[target]["use"]
            _require(
                all(old_use != use for old_use, _ in active),
                "ANY duplicate lexical input",
            )
            pending.extend((item, active, path) for item in value["operands"])
            pending.append((value["predicate"], (*active, (use, target)), path))
        else:
            pending.extend((item, active, path) for item in children(ref))
    _require(all(ref in seen for ref in nodes), "ANY expression inventory")


def _inline_producer(doc, producer) -> bool:
    """A read target's producer that is a capturing let's inline body."""
    return (
        producer.kind == "row_body"
        and doc[producer]["symbol"] is None
        and doc[producer]["final"] is False
    )


class _Check:
    def __init__(self, doc: _Doc) -> None:
        self.doc = doc
        artifact = doc[Ref(*schema.ROOT)]
        self.artifact = artifact
        self.request_ref = artifact["request"]
        self.request = doc[self.request_ref]
        self.family = self.request["family"]
        self.rendered = doc[artifact["rendered"]]
        self.ast = artifact["ast"]
        self.sql = self.rendered["sql"].encode("utf-8")

    # request and roots
    def roots(self) -> None:
        doc, request, family = self.doc, self.request, self.family
        _require(family in schema.FAMILIES, "target family")
        _require(request["release"] == schema.FAMILIES[family], "target release")
        contract = _json(request["normalized_bytes"])
        _json(request["accepted_bytes"])
        _require(
            type(contract) is dict
            and contract.get("target")
            == {"family": family, "release": request["release"]},
            "contract target",
        )
        target = request["target_request"]
        _require(
            type(target) is MappingProxyType
            and tuple(target) == ("issues", "target")
            and type(target["target"]) is MappingProxyType
            and target["target"].get("family")
            == ("postgresql" if family == "postgres" else family)
            and target["target"].get("release") == request["release"],
            "target request",
        )
        _require(
            request["literal_policy"] in ("preserve_literals", "bind_safe_literals"),
            "literal policy",
        )
        _require(request["input_blockers"] == (), "input blockers")
        _require(
            type(request["modules"]) is tuple
            and all(
                type(m) is MappingProxyType
                and tuple(m) == ("byte_count", "module", "sha256")
                and type(m["module"]) is str
                and type(m["byte_count"]) is int
                and re.fullmatch(r"[0-9a-f]{64}", str(m["sha256"]))
                for m in request["modules"]
            ),
            "module snapshots",
        )
        for position, premise in enumerate(request["premises"]):
            _require(doc[premise]["position"] == position, "premise position")
            _json(doc[premise]["value"])
        previous = -1
        for source in request["sources"]:
            fields = doc[source]
            _require(fields["position"] > previous, "source order")
            previous = fields["position"]
            names = set()
            _json(fields["selector"])
            for ordinal, field in enumerate(fields["fields"]):
                bound = doc[field]
                _require(bound["ordinal"] == ordinal, "source field ordinal")
                column = (
                    bound["column"]
                    if family == "postgres"
                    else bound["column"].casefold()
                )
                _require(column not in names, "source column collision")
                names.add(column)
                representation = _json(bound["representation"])
                _require(
                    type(representation) is dict
                    and sorted(representation) == ["domain", "nullable", "storage"],
                    "field representation",
                )
                _require(
                    tuple(bound["logical"]) == ("kind", "name")
                    and bound["nullability"] in ("non_null", "nullable", "unknown")
                    and (
                        bound["decimal"] is None
                        or tuple(bound["decimal"]) == ("precision", "scale")
                    ),
                    "field evidence",
                )
        _require(doc[self.ast]["request"] == self.request_ref, "query request")
        _require(self.rendered["ast"] == self.ast, "rendered query")
        for select in doc.all("sql_select"):
            _require(doc[select]["request"] == self.request_ref, "select request")

    # units, scans and symbols
    def units(self) -> list[Ref]:
        doc, ast = self.doc, self.ast
        if ast.kind == "sql_select":
            return self.direct_units()
        fields = doc[ast]
        units = list(
            fields["bodies"] if ast.kind == "sql_row_query" else fields["units"]
        )
        _require(units, "query units")
        position = {ref: u for u, ref in enumerate(units)}
        _require(len(position) == len(units), "repeated unit")
        for u, ref in enumerate(units):
            unit = doc[ref]
            final = u == len(units) - 1
            _require(
                unit["final"] is final if ref.kind != "join_body" else not final,
                "final unit",
            )
            if ref.kind in ("join_body", "row_result_body", "set_body"):
                _require(unit["index"] == u, "unit index")
            if final:
                _require(
                    unit["symbol"] is None and unit["cte_columns"] == (), "final symbol"
                )
            else:
                symbol = doc[unit["symbol"]]
                _require(
                    symbol["position"] == u
                    and symbol["name"] == f"p{u}"
                    and symbol["binding"] == _unit_plan(doc, ref),
                    "unit symbol",
                )
                terminals = (
                    tuple(doc[c]["port"] for c in unit["columns"])
                    if ref.kind == "join_body"
                    else unit["terminals"]
                )
                _require(len(unit["cte_columns"]) == len(terminals), "unit terminals")
                for i, (column, terminal) in enumerate(
                    zip(unit["cte_columns"], terminals, strict=True)
                ):
                    symbol = doc[column]
                    _require(
                        symbol["position"] == i
                        and symbol["name"] == f"c{i}"
                        and symbol["binding"] == terminal,
                        "unit terminal column",
                    )
            for producer in self.producers(ref):
                _require(position.get(producer, len(units)) < u, "producer order")
            ordinal = "position" if ref.kind == "join_body" else "ordinal"
            for i, column in enumerate(unit["columns"]):
                _require(doc[column][ordinal] == i, "column ordinal")
                _require(
                    doc[doc[column]["symbol"]]["position"] == i + 1, "column symbol"
                )
        inline = self.inline_units()
        _require(
            all(
                ref in position or ref in inline
                for kind in UNITS
                for ref in doc.all(kind)
            ),
            "orphan unit",
        )
        return units

    def inline_units(self) -> dict[Ref, Ref]:
        """Each inline let body and the block read target that renders it.

        A capturing let is no unit: its bodies are nested derived tables of
        its single read, the target's body first, each inner one read by a
        stage use of the next.
        """
        doc = self.doc
        result: dict[Ref, Ref] = {}
        for target in doc.all("sql_block_target"):
            body = doc[target]["producer"]
            if body.kind != "row_body" or doc[body]["symbol"] is not None:
                continue
            while True:
                unit = doc[body]
                _require(
                    body not in result
                    and unit["final"] is False
                    and unit["cte_columns"] == ()
                    and unit["aggregation"] is None
                    and unit["window"] is None,
                    "inline unit",
                )
                result[body] = target
                for i, column in enumerate(unit["columns"]):
                    _require(doc[column]["ordinal"] == i, "column ordinal")
                    _require(
                        doc[doc[column]["symbol"]]["position"] == i + 1,
                        "column symbol",
                    )
                scan = unit["scan"]
                if scan.kind != "row_stage_use":
                    break
                body = doc[scan]["body"]
                _require(
                    body.kind == "row_body" and doc[body]["symbol"] is None,
                    "inline unit",
                )
        self.inline = result
        return result

    def producers(self, ref: Ref) -> list[Ref]:
        doc, unit = self.doc, self.doc[ref]
        if ref.kind == "row_body":
            scan = unit["scan"]
            return [] if scan.kind == "row_scan" else [doc[scan]["body"]]
        if ref.kind == "row_result_body":
            return [doc[unit["scan"]]["body"]]
        items = unit["inputs"] if ref.kind == "join_body" else unit["operands"]
        return [
            doc[item]["producer"]
            for item in items
            if doc[item]["producer"].kind != "bound_source"
        ]

    def direct_units(self) -> list[Ref]:
        doc, select = self.doc, self.doc[self.ast]
        self.inline = {}
        units = []
        for i, cte in enumerate(select["ctes"]):
            fields = doc[cte]
            symbol = doc[fields["symbol"]]
            definition = doc[fields["definition"]]
            _require(
                symbol["position"] == i
                and symbol["name"] == f"p{i}"
                and symbol["binding"] == definition["original"],
                "cte symbol",
            )
            _require(
                len(fields["columns"]) == len(definition["terminals"]), "cte columns"
            )
            for j, (column, terminal) in enumerate(
                zip(fields["columns"], definition["terminals"], strict=True)
            ):
                symbol = doc[column]
                _require(
                    symbol["position"] == j
                    and symbol["name"] == f"c{j}"
                    and symbol["binding"] == terminal,
                    "cte column",
                )
            body = doc[fields["body"]]
            _require(
                body["ctes"] == () and body["definition"] == fields["definition"],
                "cte body",
            )
            scan = body["scan"]
            if scan.kind == "sql_named_use":
                _require(doc[scan]["cte"] in select["ctes"][:i], "cte order")
            units.append(fields["body"])
        units.append(self.ast)
        for ref in units:
            for i, column in enumerate(doc[ref]["columns"]):
                _require(doc[column]["ordinal"] == i, "column ordinal")
                _require(
                    doc[doc[column]["symbol"]]["position"] == i + 1, "column symbol"
                )
        return units

    # values, fixed literals and parameters
    def values(self) -> None:
        doc, family = self.doc, self.family
        _validate_any_scopes(doc)
        for ref in (*doc.all("sql_block_read"), *doc.all("sql_any_read")):
            read = doc[ref]
            if ref.kind == "sql_any_read":
                _require(
                    read["kind"] == "exists"
                    and _value_tag(doc, read["predicate"]) == "Bool",
                    "ANY predicate",
                )
            target = doc[read["target"]]
            realization = doc[read["realization"]]
            producer = doc[target["producer"]]
            membership = read["kind"] in ("in", "not_in")
            _require(
                (target["source"] is None)
                is (target["producer"].kind != "bound_source")
                and len(read["operands"]) == (1 if membership else 0)
                and (
                    read["kind"] == "exists"
                    and read["column"] is None
                    and realization["tag"] == "Bool"
                    and realization["nullable"] is False
                    or read["kind"] == "scalar"
                    and _block_column_name(doc, target, read["column"]) is not None
                    and realization["nullable"] is True
                    # Membership compares with the producer's one output column.
                    or membership
                    and read["column"] == 0
                    and len(
                        producer["fields"]
                        if target["producer"].kind == "bound_source"
                        else producer["columns"]
                        if _inline_producer(doc, target["producer"])
                        else producer["cte_columns"]
                    )
                    == 1
                    and realization["tag"] == "Bool"
                    and realization["nullable"] is True
                ),
                "block read",
            )
        for ref in doc.all("sql_captured_reference"):
            fields = doc[ref]
            own = dict(doc[fields["realization"]])
            outer = dict(doc[doc[fields["column"]]["realization"]])
            # A captured field may only widen its outer column to nullable.
            _require(
                fields["capture"].kind == "capture"
                and own.pop("nullable") in (outer.pop("nullable"), True)
                and own == outer,
                "captured reference",
            )
        for ref in doc.all("sql_operation"):
            op = doc[ref]
            _require(op["kind"] in schema.OPERATORS, "operation kind")
            _require(
                op["operator"] in schema.OPERATORS[op["kind"]], "operation operator"
            )
            if op["kind"] == "scalar_call" and op["operator"] == "date_of":
                _require(
                    _is_realization(
                        doc[op["realization"]],
                        "Date",
                        {"kind": "pg_date" if family == "postgres" else "my_date"},
                        {"kind": "date"},
                    ),
                    "date_of result carrier",
                )
            arity = {
                "sign": 1,
                "null_test": 1,
                "not": 1,
                "cast": 1,
                "between": 3,
                "conditional": 3,
            }.get(op["kind"])
            if arity is not None:
                _require(len(op["operands"]) == arity, "operation arity")
            elif op["kind"] == "membership":
                _require(len(op["operands"]) >= 1, "operation arity")
            elif op["kind"] == "scalar_call":
                arities = {
                    "lower": {1},
                    "upper": {1},
                    "trim": {1},
                    "len": {1},
                    "abs": {1},
                    "sign": {1},
                    "date_of": {1},
                    "year": {1},
                    "month": {1},
                    "day": {1},
                    "hour": {1},
                    "minute": {1},
                    "substr": {3},
                    "replace": {3},
                    "contains": {2},
                    "starts_with": {2},
                    "ends_with": {2},
                    "nullif": {2},
                    "round": {1, 2},
                    "date_trunc": {2},
                }
                count = len(op["operands"])
                _require(
                    count >= 2
                    if op["operator"] == "coalesce"
                    else count in arities.get(op["operator"], set()),
                    "operation arity",
                )
            else:
                _require(len(op["operands"]) == 2, "operation arity")
            operands = op["operands"]
            result = doc[op["realization"]]
            if op["kind"] == "cast":
                _require(_value_tag(doc, operands[0]) == "Int", "cast input")
                if op["operator"] == "int_to_float":
                    _require(
                        result["tag"] == "Float"
                        and (
                            _is_pg_float(result)
                            if family == "postgres"
                            else _is_realization(
                                result,
                                "Float",
                                {"kind": "my_double"},
                                {"kind": "finite_float", "format": "binary64"},
                            )
                        ),
                        "int_to_float realization",
                    )
                else:
                    operand = _value_realization(doc, operands[0])
                    _require(
                        family == "postgres"
                        and _is_pg_int(operand)
                        and _is_pg_text(
                            result,
                            nullable=None if operand is None else operand["nullable"],
                            maximum=20,
                        ),
                        "int_to_text realization",
                    )
            elif op["kind"] == "scalar_call" and op["operator"] == "round":
                _require(family == "postgres", "round family")
                value = _value_realization(doc, operands[0])
                if _value_tag(doc, operands[0]) == "Decimal":
                    scale = 0 if len(operands) == 1 else _literal_int(doc, operands[1])
                    parameters = _pg_decimal_parameters(value)
                    _require(
                        parameters is not None
                        and scale is not None
                        and type(scale) is int
                        and -30 <= scale <= 30
                        and (
                            len(operands) == 1 or _value_tag(doc, operands[1]) == "Int"
                        ),
                        "round decimal scale",
                    )
                    assert (
                        parameters is not None
                        and type(scale) is int
                        and value is not None
                    )
                    precision, source_scale = parameters
                    result_scale = min(source_scale, max(scale, 0))
                    result_precision = (
                        precision
                        if scale >= source_scale
                        else precision - source_scale + 1 + result_scale
                    )
                    _require(
                        1 <= result_precision <= 65
                        and 0 <= result_scale <= min(result_precision, 30)
                        and _is_realization(
                            result,
                            "Decimal",
                            {
                                "kind": "pg_numeric",
                                "precision": result_precision,
                                "scale": result_scale,
                            },
                            {
                                "kind": "decimal",
                                "precision": result_precision,
                                "scale": result_scale,
                            },
                        )
                        and result["nullable"] == value["nullable"],
                        "round decimal result",
                    )
                else:
                    assert value is not None
                    _require(
                        len(operands) == 1
                        and _is_pg_float(value)
                        and _is_pg_float(result)
                        and result["nullable"] == value["nullable"],
                        "round float realization",
                    )
            elif op["kind"] == "scalar_call" and op["operator"] == "date_trunc":
                unit = _literal_text(doc, operands[0])
                temporal = _value_realization(doc, operands[1])
                _require(
                    family == "postgres" and unit is not None and temporal is not None,
                    "date_trunc inputs",
                )
                assert unit is not None and temporal is not None
                if _is_realization(
                    temporal, "Date", {"kind": "pg_date"}, {"kind": "date"}
                ):
                    _require(
                        unit in {"year", "month", "day"}
                        and _is_realization(
                            result,
                            "Date",
                            {"kind": "pg_date"},
                            {"kind": "date"},
                        ),
                        "date_trunc date",
                    )
                    _require(
                        result["nullable"] == temporal["nullable"],
                        "date_trunc date",
                    )
                else:
                    _require(
                        unit in {"year", "month", "day", "hour", "minute"}
                        and _is_realization(
                            temporal,
                            "Timestamp",
                            {"kind": "pg_timestamp", "fractional_seconds": 6},
                            {"kind": "timestamp"},
                        )
                        and _is_realization(
                            result,
                            "Timestamp",
                            {"kind": "pg_timestamp", "fractional_seconds": 6},
                            {"kind": "timestamp"},
                        ),
                        "date_trunc timestamp",
                    )
                    _require(
                        result["nullable"] == temporal["nullable"],
                        "date_trunc timestamp",
                    )
        for ref in doc.all("aggregate_value_column"):
            column = doc[ref]
            expected = {
                "count": "COUNT",
                "count_distinct": "COUNT",
                "sum": "SUM",
                "min": "MIN",
                "max": "MAX",
                "avg": "AVG",
                "string_agg": "string_agg",
            }.get(column["function"])
            _require(
                expected is not None and column["spelling"] == expected,
                "aggregate spelling",
            )
            argument_cast, result_cast = _aggregate_casts(family, column["function"])
            _require(
                column["argument_cast"] == argument_cast
                and column["result_cast"] == result_cast
                and (
                    argument_cast is None
                    or column["argument"] is not None
                    and not column["distinct"]
                ),
                "aggregate argument cast",
            )
            if column["function"] == "sum":
                # Q1: PostgreSQL only; the checked bigint narrowing bounds an
                # Int argument's exact sum, NULL for an empty input.
                _require(
                    family == "postgres"
                    and (_value_realization(doc, column["argument"]) or {}).get("tag")
                    == "Int"
                    and _is_realization(
                        doc[doc[column["column"]]["realization"]],
                        "Int",
                        {"kind": "pg_int8"},
                        {
                            "kind": "int_range",
                            "min": str(-(1 << 63)),
                            "max": str((1 << 63) - 1),
                        },
                    )
                    and doc[doc[column["column"]]["realization"]]["nullable"] is True,
                    "sum result",
                )
            if column["function"] == "string_agg":
                result = doc[doc[column["column"]]["realization"]]
                _require(
                    family == "postgres"
                    and column["argument"] is not None
                    and column["delimiter"] is not None
                    and bool(column["order_by"]),
                    "string_agg shape",
                )
                _require(
                    _is_pg_text_value(doc, column["argument"])
                    and _is_pg_text_value(doc, column["delimiter"])
                    and _is_pg_text(result, nullable=True, maximum=None)
                    and all(
                        _is_pg_order_value(_value_realization(doc, doc[item]["value"]))
                        for item in column["order_by"]
                    ),
                    "string_agg typed inputs",
                )
            else:
                _require(
                    column["delimiter"] is None and not column["order_by"],
                    "aggregate extra inputs",
                )
        for ref in doc.all("sql_unary"):
            _require(doc[ref]["operator"] in ("+", "-"), "unary operator")
        for ref in doc.all("sql_anchor"):
            anchor = doc[ref]
            _require(anchor["tag"] in schema.TAGS, "anchor tag")
            _require(
                anchor["physical_type"] == schema.PHYSICAL[family][anchor["tag"]],
                "anchor physical type",
            )
            leaf = doc[anchor["operand"]]
            if anchor["operand"].kind == "sql_literal":
                _require(leaf["value"].tag == anchor["tag"], "literal tag")
            else:
                _require(
                    doc[leaf["fixed"]]["value"].tag == anchor["tag"], "parameter tag"
                )
                _require(
                    doc[leaf["use"]]["physical_type"] == anchor["physical_type"],
                    "parameter physical type",
                )
        # value trees are acyclic
        edges = {
            "sql_operation": "operands",
            "sql_unary": "operand",
            "sql_anchor": "operand",
        }
        state: dict[Ref, int] = {}
        for kind in edges:
            for root in doc.all(kind):
                stack = [(root, False)]
                while stack:
                    ref, leaving = stack.pop()
                    if leaving:
                        state[ref] = 2
                        continue
                    _require(state.get(ref) != 1, "value cycle")
                    if state.get(ref) == 2 or ref.kind not in edges:
                        continue
                    state[ref] = 1
                    stack.append((ref, True))
                    targets = doc[ref][edges[ref.kind]]
                    for child in targets if type(targets) is tuple else (targets,):
                        stack.append((child, False))
        uses = self.artifact["parameter_uses"]
        fixed = set(self.artifact["fixed_values"])
        slots = [doc[value]["slot"] for value in fixed]
        _require(len(set(slots)) == len(slots), "fixed slots")
        if self.request["literal_policy"] == "preserve_literals":
            _require(not uses and not doc.all("sql_parameter"), "preserved literals")
        claimed: dict[Ref, int] = {}
        for ref in doc.all("sql_parameter"):
            leaf = doc[ref]
            claimed[leaf["use"]] = claimed.get(leaf["use"], 0) + 1
            use = doc[leaf["use"]]
            _require(leaf["fixed"] in fixed, "parameter fixed value")
            value = doc[leaf["fixed"]]
            _require(
                value["slot"] == use["slot"] and use["original"] == leaf["original"],
                "parameter slot",
            )
            _require(
                use["physical_type"] == schema.PHYSICAL[family][value["value"].tag],
                "parameter use type",
            )
        _require(claimed == {use: 1 for use in uses}, "parameter use claims")
        seen: dict[PlanRef, tuple[int, str]] = {}
        for ordinal, ref in enumerate(uses):
            use = doc[ref]
            _require(use["ordinal"] == ordinal, "parameter ordinal")
            if family == "mysql":
                _require(use["server_index"] == ordinal + 1, "mysql parameter index")
            else:
                expected = seen.get(use["slot"], (len(seen) + 1, use["physical_type"]))
                _require(
                    (use["server_index"], use["physical_type"]) == expected,
                    "postgres parameter index",
                )
                seen[use["slot"]] = expected

    # structural specifics
    def shapes(self) -> None:
        doc = self.doc
        for ref in doc.all("join_body"):
            join = doc[ref]
            _require(len(join["inputs"]) == 2, "join inputs")
            _require(
                tuple(doc[item]["ordinal"] for item in join["inputs"]) == (0, 1),
                "join input ordinals",
            )
            kind = join["join_kind"]
            membership = {"semi": "exists", "anti": "not_exists"}.get(kind)
            _require(
                kind in schema.JOIN_SPELLING or membership is not None, "join kind"
            )
            _require(join["membership"] == membership, "join membership")
            _require(
                (join["sentinel"] is None) == (membership is None), "join sentinel"
            )
            for column in join["columns"]:
                fields = doc[column]
                if fields["nulling"]:
                    realization = doc[doc[fields["column"]]["realization"]]
                    _require(realization["nullable"] is True, "outer null image")
        for ref in doc.all("set_body"):
            unit = doc[ref]
            _require(
                unit["kind"] in schema.SET_KINDS
                and unit["quantifier"] in schema.SET_QUANTIFIERS
                and unit["fold"] == "source_order_left_fold"
                and len(unit["operands"]) >= 2,
                "set operation",
            )
            for position, operand in enumerate(unit["operands"]):
                _require(doc[operand]["position"] == position, "set operand position")
            for column in unit["columns"]:
                fields = doc[column]
                inputs = fields["inputs"]
                _require(len(inputs) == len(unit["operands"]), "set column inputs")
                for operand, read in zip(unit["operands"], inputs, strict=True):
                    _require(
                        doc[operand]["columns"][fields["ordinal"]] == read,
                        "set positional alignment",
                    )
        for ref in doc.all("result_order"):
            order = doc[ref]
            _require(order["carrier"] in schema.CARRIERS, "order carrier")
            for position, item in enumerate(order["items"]):
                fields = doc[item]
                _require(
                    fields["position"] == position
                    and fields["carrier"] == order["carrier"]
                    and fields["direction"] in schema.DIRECTIONS,
                    "order item",
                )
                read = doc[fields["read"]]
                _require(
                    _source_field_matches_stage(doc, read)
                    and _is_key_value(doc[read["realization"]], self.family),
                    "result order carrier",
                )
        for ref in doc.all("window_frame"):
            frame = doc[ref]
            _require(frame["unit"] in schema.FRAME_UNITS, "frame unit")
            _require(
                frame["exclusion"] is None or frame["exclusion"] in schema.EXCLUSIONS,
                "frame exclusion",
            )
            for bound in (frame["start"], frame["end"]):
                _require(type(bound) is tuple and len(bound) == 2, "frame bound")
                kind, text = cast(tuple[str, str], bound)
                if kind in schema.FRAME_BOUNDS:
                    _require(text == schema.FRAME_BOUNDS[kind], "frame bound")
                else:
                    suffix = schema.FRAME_OFFSETS.get(kind)
                    _require(
                        suffix is not None
                        and re.fullmatch(r"(0|[1-9][0-9]*) " + suffix, str(text))
                        and int(str(text).split(" ", 1)[0]) <= _I64_MAX,
                        "frame offset",
                    )
        # R15-INT-OFFSET-V1 over the serialized facts alone: each finite RANGE
        # threshold of the documented key domain stays inside signed64. This is
        # data consistency, not proof that the source domain holds in a database.
        for ref in doc.all("window_specification"):
            spec = doc[ref]
            if spec["frame"] is None:
                continue
            frame = doc[spec["frame"]]
            offsets = _frame_offsets(frame)
            if frame["unit"] != "range" or not offsets:
                continue
            _require(len(spec["orders"]) == 1, "range threshold key")
            order = doc[spec["orders"][0]]
            _require(
                _thresholds_exact(
                    doc[doc[order["read"]]["realization"]], order["direction"], offsets
                ),
                "range threshold arithmetic",
            )
        for kind in ("window_order_item", "window_partition"):
            for ref in doc.all(kind):
                binding = doc[ref]["binding"]
                _require(
                    type(binding) is MappingProxyType
                    and tuple(binding) == ("policy", "position", "role")
                    and binding["role"]
                    == ("order" if kind == "window_order_item" else "partition"),
                    "window binding",
                )
                if kind == "window_order_item":
                    _require(
                        doc[ref]["direction"] in ("asc", "desc"), "window direction"
                    )
        for ref in doc.all("aggregate_value_column"):
            column = doc[ref]
            _require(
                column["spelling"] in schema.AGGREGATE_SPELLING, "aggregate spelling"
            )
            _require(
                not column["distinct"] or column["argument"] is not None,
                "aggregate distinct",
            )
            for order in column["order_by"]:
                _require(
                    doc[order]["direction"] in ("asc", "desc"),
                    "aggregate order direction",
                )
        # R14-PG-NAVIGATION-RESULT-V1, R15-MYSQL-WINDOW-RESULT-V1 and the B1
        # boundary: each value-window result publishes exactly the width and
        # interval its documented carrier and default literal imply.
        for ref in doc.all("window_column"):
            column = doc[ref]
            arguments = [doc[item] for item in column["arguments"]]
            if self.family == "postgres":
                function = column["function"]
                roles = tuple(argument["role"] for argument in arguments)
                native_position = None
                if function == "ntile":
                    _require(
                        roles == ("bucket",),
                        "postgres window structural argument roles",
                    )
                    native_position = 0
                elif function == "nth_value":
                    _require(
                        roles == ("value", "position"),
                        "postgres window structural argument roles",
                    )
                    native_position = 1
                elif function in {"lag", "lead"}:
                    _require(
                        roles
                        in (
                            ("value",),
                            ("value", "offset"),
                            ("value", "offset", "default"),
                        ),
                        "postgres window structural argument roles",
                    )
                    if len(arguments) > 1:
                        native_position = 1
                if native_position is not None:
                    argument = arguments[native_position]
                    literal = argument["literal"]
                    _require(
                        type(literal) is str
                        and re.fullmatch(r"0|[1-9][0-9]*", literal) is not None
                        and (0 if function in {"lag", "lead"} else 1)
                        <= int(literal)
                        <= 2147483647,
                        "postgres window structural argument range",
                    )
            if column["function"] not in _VALUE_WINDOWS:
                continue
            reads = [
                doc[item["read"]] for item in arguments if item["read"] is not None
            ]
            _require(len(reads) == 1, "window value carrier")
            defaults = [
                item["literal"] for item in arguments if item["role"] == "default"
            ]
            result = doc[doc[column["column"]]["realization"]]
            expected = _window_value_representation(
                self.family,
                reads[0],
                doc[reads[0]["realization"]],
                defaults[0] if defaults else None,
                doc,
            )
            _require(
                expected is not None
                and expected == (dict(result["storage"]), dict(result["domain"])),
                "window value result representation",
            )

    def run(self) -> None:
        self.roots()
        units = self.units()
        self.values()
        self.shapes()
        _Tokens(self, units).run()
        _Requirements(self, units).run()


class _Tokens:
    """Token partition, lexical forms and (role, subject) bindings to the AST."""

    def __init__(self, check: _Check, units: list[Ref]) -> None:
        self.check = check
        self.doc = check.doc
        self.family = check.family
        self.units = units
        doc = self.doc
        self.events = [doc[ref] for ref in check.rendered["events"]]
        self.overlays = [doc[ref] for ref in check.rendered["expression_ranges"]]
        self.texts: list[str] = []

    def index(self, kind: str, field: str) -> dict[Any, list[Mapping[str, Any]]]:
        result: dict[Any, list[Mapping[str, Any]]] = {}
        for ref in self.doc.all(kind):
            result.setdefault(self.doc[ref][field], []).append(self.doc[ref])
        return result

    def one(self, table, key, detail: str):
        items = table.get(key, [])
        _require(len(items) >= 1, detail)
        return items[0]

    def run(self) -> None:
        self.partition()
        self.bindings()
        self.overlay_alignment()
        self.int8_widening()
        self.origins()

    def partition(self) -> None:
        sql = self.check.sql
        _require(self.events, "token stream")
        offset = 0
        for event in self.events:
            _require(
                event["kind"] in ("syntax", "identifier", "literal", "parameter"),
                "token kind",
            )
            start, end = event["start"], event["end"]
            _require(start == offset and start < end <= len(sql), "token coverage")
            _require(
                (sql[start] & 0xC0) != 0x80
                and (end == len(sql) or (sql[end] & 0xC0) != 0x80),
                "UTF-8 boundary",
            )
            self.texts.append(sql[start:end].decode("utf-8"))
            offset = end
        _require(offset == len(sql), "token coverage")
        depth = 0
        previous = ""
        for event, text in zip(self.events, self.texts, strict=True):
            _require(
                (previous[-1:] + text[:1]) not in ("--", "/*", "*/"), "comment forming"
            )
            previous = text
            if event["kind"] == "syntax":
                for char in text:
                    depth += {"(": 1, ")": -1}.get(char, 0)
                    _require(depth >= 0, "parenthesis balance")
        _require(depth == 0, "parenthesis balance")

    def segments(self) -> list[tuple[Ref, int, int]]:
        """Each unit's own token interval, from the WITH preamble structure."""
        doc, events = self.doc, self.events
        units = self.units
        if events[0]["role"] != "with":
            _require(len(units) == 1, "unit segmentation")
            return [(units[0], 0, len(events))]
        result = []
        i = 1
        for u, unit in enumerate(units[:-1]):
            plan = _unit_plan(doc, unit)
            if u:
                _require(events[i]["role"] == "cte_separator", "cte separator")
                i += 1
            name = self.identifier(i)
            _require(
                events[i]["role"] == "cte_name" and events[i]["subject"] == plan,
                "cte name",
            )
            symbol = (
                doc[unit]["symbol"]
                if unit.kind in UNITS
                else doc[self.cte_of(unit)]["symbol"]
            )
            _require(name == doc[symbol]["name"], "cte name")
            i += 1
            _require(events[i]["role"] == "cte_columns_open", "cte columns")
            i += 1
            columns = (
                doc[unit]["cte_columns"]
                if unit.kind in UNITS
                else doc[self.cte_of(unit)]["columns"]
            )
            for j, column in enumerate(columns):
                if j:
                    _require(events[i]["role"] == "terminal_separator", "cte columns")
                    i += 1
                symbol = doc[column]
                _require(
                    events[i]["role"] == "terminal_column"
                    and events[i]["subject"] == symbol["binding"]
                    and self.identifier(i) == symbol["name"],
                    "cte column",
                )
                i += 1
            _require(
                events[i]["role"] == "cte_body_open" and events[i]["subject"] == plan,
                "cte body",
            )
            start = i + 1
            while not (
                events[i]["role"] == "cte_body_close" and events[i]["subject"] == plan
            ):
                i += 1
                _require(i < len(events), "cte body")
            result.append((unit, start, i))
            i += 1
        _require(
            events[i]["role"] == "with_body"
            and events[i]["subject"] == _unit_plan(doc, units[-1]),
            "with body",
        )
        result.append((units[-1], i + 1, len(events)))
        return result

    def cte_of(self, select: Ref) -> Ref:
        for cte in self.doc[self.check.ast]["ctes"]:
            if self.doc[cte]["body"] == select:
                return cte
        raise _Reject(Status.INVALID_RELATION, "cte body")

    def identifier(self, i: int) -> str:
        text = self.texts[i]
        _require(self.events[i]["kind"] == "identifier", "identifier token")
        quote = schema.QUOTES[self.family]
        _require(
            len(text) >= 3 and text[0] == quote and text[-1] == quote,
            "identifier quoting",
        )
        inner = text[1:-1]
        _require(inner.replace(quote * 2, "").count(quote) == 0, "identifier quoting")
        return inner.replace(quote * 2, quote)

    def aliases(self, unit: Ref) -> set[str]:
        doc, fields = self.doc, self.doc[unit]
        if unit.kind == "join_body":
            return {doc[doc[item]["symbol"]]["name"] for item in fields["inputs"]}
        if unit.kind == "set_body":
            return {doc[doc[item]["symbol"]]["name"] for item in fields["operands"]}
        return {doc[doc[fields["scan"]]["symbol"]]["name"]}

    def labels(self, unit: Ref) -> list[str]:
        doc, fields = self.doc, self.doc[unit]
        labels = [doc[column]["label"] for column in fields["columns"]]
        if unit.kind == "set_body":
            return labels * len(fields["operands"])
        return labels

    def bindings(self) -> None:
        doc, family = self.doc, self.family
        names: dict[PlanRef, set[str]] = {}
        for ref in doc.all("stage_column"):
            names.setdefault(doc[ref]["terminal"], set()).add(doc[ref]["name"])
        for kind in UNITS:
            for unit in doc.all(kind):
                for symbol in doc[unit]["cte_columns"]:
                    names.setdefault(doc[symbol]["binding"], set()).add(
                        doc[symbol]["name"]
                    )
        for cte in doc.all("sql_cte"):
            for symbol in doc[cte]["columns"]:
                names.setdefault(doc[symbol]["binding"], set()).add(doc[symbol]["name"])
        for column in doc.all("sql_column"):
            fields = doc[column]
            names.setdefault(fields["source_port"], set()).add(
                doc[fields["symbol"]]["name"]
            )
        relations: dict[PlanRef, set[tuple[str, str]]] = {}
        for kind, field in (
            ("sql_scan", "realization"),
            ("row_scan", "realization"),
            ("join_input", "producer"),
            ("set_operand_body", "producer"),
            ("sql_block_target", "producer"),
        ):
            for ref in doc.all(kind):
                fields = doc[ref]
                if (
                    fields.get("source", None) is None
                    or fields[field].kind != "bound_source"
                ):
                    continue
                bound = doc[fields[field]]
                relations.setdefault(fields["source"], set()).add(
                    (bound["namespace"], bound["name"])
                )
        unit_names: dict[PlanRef, set[str]] = {}
        for kind in UNITS:
            for unit in doc.all(kind):
                if doc[unit]["symbol"] is not None:
                    unit_names.setdefault(_unit_plan(doc, unit), set()).add(
                        doc[doc[unit]["symbol"]]["name"]
                    )
        for cte in doc.all("sql_cte"):
            definition = doc[doc[cte]["definition"]]["original"]
            unit_names.setdefault(definition, set()).add(
                doc[doc[cte]["symbol"]]["name"]
            )
        for item in doc.all("join_input"):
            producer = doc[item]["producer"]
            if producer.kind != "bound_source" and doc[producer]["symbol"] is not None:
                unit_names.setdefault(doc[item]["original"], set()).add(
                    doc[doc[producer]["symbol"]]["name"]
                )
        block_reads = self.index("sql_block_read", "original")
        for key, values in self.index("sql_any_read", "original").items():
            block_reads.setdefault(key, []).extend(values)
        any_references = self.index("sql_any_reference", "port")
        block_aliases = {
            doc[ref]["use"]: doc[doc[ref]["symbol"]]["name"]
            for ref in doc.all("sql_block_target")
        }
        block_source_columns: dict[PlanRef, set[str]] = {}
        for ref in doc.all("sql_block_target"):
            target = doc[ref]
            if target["source"] is not None:
                block_source_columns.setdefault(target["source"], set()).update(
                    doc[field]["column"] for field in doc[target["producer"]]["fields"]
                )
        operations = self.index("sql_operation", "original")
        unaries = self.index("sql_unary", "original")
        anchors = self.index("sql_anchor", "original")
        literals = self.index("sql_literal", "site")
        nulls = self.index("sql_null", "site")
        parameters = self.index("sql_parameter", "site")
        aggregates = self.index("aggregate_value_column", "aggregate")
        windows = self.index("window_column", "window")
        sets = self.index("set_body", "body")
        joins = self.index("join_body", "join")
        order_items = self.index("result_order_item", "item")
        limits = self.index("result_limit", "limit")
        definitions: dict[PlanRef, Mapping[str, Any]] = {}
        for ref in doc.all("window_definition"):
            definitions[doc[doc[ref]["symbol"]]["binding"]] = doc[ref]
        specifications: dict[PlanRef, Mapping[str, Any]] = {}
        for ref in doc.all("window_column"):
            column = doc[ref]
            spec = doc[column["specification"]]
            if spec["symbol"] is None:
                specifications[column["window"]] = spec
        for binding, definition in definitions.items():
            specifications[binding] = doc[definition["specification"]]
        per_subject: dict[tuple[str, PlanRef], list[Any]] = {}
        # An inline let body opens and closes its own alias and label scope
        # inside its reading unit; a captured reference names that unit's row.
        inline_blocks = {doc[body]["block"]: body for body in self.check.inline}
        captures = self.index("sql_captured_reference", "capture")
        opened: set[Ref] = set()
        for unit, start, end in self.segments():
            frames: list[tuple[Ref, set[str], list[str]]] = [
                (unit, self.aliases(unit), [])
            ]
            active_any: list[tuple[Mapping[str, Any], PlanRef, bool]] = []
            for i in range(start, end):
                event, text = self.events[i], self.texts[i]
                if event["role"] == "exists_open":
                    values = block_reads.get(event["subject"])
                    if values is None or len(values) != 1:
                        raise _Reject(Status.INVALID_RELATION, "ANY token subject")
                    active_any.append((values[0], event["subject"], False))
                elif event["role"] == "exists_where":
                    _require(bool(active_any), "ANY WHERE scope")
                    entry = active_any[-1]
                    _require(
                        entry[1] == event["subject"]
                        and entry[0].get("predicate") is not None
                        and not entry[2],
                        "ANY WHERE subject",
                    )
                    active_any[-1] = (entry[0], entry[1], True)
                elif event["role"] == "exists_close":
                    _require(bool(active_any), "ANY token scope")
                    entry = active_any.pop()
                    _require(
                        entry[1] == event["subject"]
                        and entry[2] == (entry[0].get("predicate") is not None),
                        "ANY token closure",
                    )
                role, subject, kind = event["role"], event["subject"], event["kind"]
                _require(role not in PREAMBLE_ROLES, "token role placement")
                if role == "inline_open":
                    body = inline_blocks.get(subject)
                    _require(body is not None and body not in opened, "inline unit")
                    assert body is not None
                    opened.add(body)
                    frames.append((body, self.aliases(body), []))
                elif role == "inline_close":
                    _require(len(frames) > 1, "inline unit")
                    body, _, inline_labels = frames.pop()
                    _require(
                        doc[body]["block"] == subject
                        and inline_labels == self.labels(body),
                        "inline unit",
                    )
                aliases, labels = frames[-1][1], frames[-1][2]
                if kind == "identifier":
                    name = self.identifier(i)
                    if role == "label":
                        labels.append(name)
                    elif role == "capture_scope":
                        captured = self.one(captures, subject, "capture scope")
                        _require(
                            len(frames) > 1
                            and name == doc[captured["scope"]]["name"]
                            and name in frames[0][1],
                            "capture scope",
                        )
                    elif role in SCOPE_ROLES:
                        local = (
                            any_references.get(subject, ())
                            if role == "value_scope"
                            else ()
                        )
                        local_allowed = any(
                            entry[2]
                            and doc[entry[0]["target"]]["use"] == item["use"]
                            and doc[item["scope"]]["name"] == name
                            for entry in active_any
                            for item in local
                        )
                        _require(name in aliases or local_allowed, "scope alias")
                    elif role in COLUMN_ROLES:
                        _require(name in names.get(subject, ()), "column name")
                    elif role in RELATION_ROLES:
                        slot = 0 if RELATION_ROLES[role] == "namespace" else 1
                        _require(
                            name in {pair[slot] for pair in relations.get(subject, ())},
                            "relation name",
                        )
                    elif role in UNIT_REFERENCE_ROLES:
                        _require(name in unit_names.get(subject, ()), "unit reference")
                    elif role in (
                        "exists_scope",
                        "scalar_scope",
                        "in_scope",
                        "in_column_scope",
                    ):
                        _require(block_aliases.get(subject) == name, "block alias")
                    elif role == "scalar_column":
                        read = self.one(block_reads, subject, "scalar column")
                        _require(
                            read["kind"] == "scalar"
                            and name
                            == _block_column_name(
                                doc, doc[read["target"]], read["column"]
                            ),
                            "scalar column",
                        )
                    elif role == "in_source_column":
                        _require(
                            name in block_source_columns.get(subject, ()),
                            "membership source column",
                        )
                    elif role == "window_definition":
                        _require(
                            subject in definitions
                            and name == doc[definitions[subject]["symbol"]]["name"],
                            "window definition",
                        )
                    elif role == "window_reference":
                        column = self.one(windows, subject, "window reference")
                        symbol = doc[column["specification"]]["symbol"]
                        _require(
                            symbol is not None and doc[symbol]["name"] == name,
                            "window reference",
                        )
                    else:
                        raise _Reject(Status.INVALID_RELATION, "identifier role")
                elif kind == "parameter":
                    leaf = self.one(parameters, subject, "parameter site")
                    use = doc[leaf["use"]]
                    tag = doc[leaf["fixed"]]["value"].tag
                    expected = (
                        "?" if family == "mysql" else "$" + str(use["server_index"])
                    )
                    _require(role == tag and text == expected, "parameter token")
                elif kind == "literal":
                    if role in schema.TAGS:
                        if subject in nulls:
                            leaf = self.one(nulls, subject, "null literal site")
                            _require(
                                role == leaf["tag"] and text == "NULL", "literal token"
                            )
                        else:
                            leaf = self.one(literals, subject, "literal site")
                            value = leaf["value"]
                            _require(
                                role == value.tag
                                and text
                                == schema.literal_token(value.tag, value.value, family),
                                "literal token",
                            )
                    elif role == "limit_value":
                        limit = self.one(limits, subject, "limit value")
                        _require(text == str(limit["value"]), "limit value")
                    elif role == "membership_sentinel":
                        join = self.one(joins, subject, "membership sentinel")
                        _require(
                            text == "1" and join["membership"] is not None,
                            "membership sentinel",
                        )
                    elif role == "window_argument_literal":
                        per_subject.setdefault((role, subject), []).append(text)
                    elif role == "exists_sentinel":
                        self.one(block_reads, subject, "existence sentinel")
                        _require(text == "1", "existence sentinel")
                    else:
                        raise _Reject(Status.INVALID_RELATION, "literal role")
                elif role == "in_operator":
                    read = self.one(block_reads, subject, "membership operator")
                    _require(
                        read["kind"] in ("in", "not_in")
                        and text
                        == (" NOT IN (" if read["kind"] == "not_in" else " IN ("),
                        "membership operator",
                    )
                else:
                    self.syntax(
                        role,
                        subject,
                        text,
                        per_subject,
                        operations,
                        unaries,
                        anchors,
                        aggregates,
                        windows,
                        sets,
                        joins,
                        order_items,
                        specifications,
                    )
            _require(not active_any, "ANY token scope")
            _require(len(frames) == 1, "inline unit")
            _require(frames[0][2] == self.labels(unit), "output labels")
        _require(opened == set(self.check.inline), "inline unit")
        for (role, subject), texts in per_subject.items():
            if role == "c5_scalar_tokens":
                operation = self.one(operations, subject, "scalar call subject")
                name = operation["operator"]
                realization = doc[operation["realization"]]
                if name == "round":
                    if len(operation["operands"]) == 2:
                        expected = [
                            ("scalar_call_open", "round("),
                            ("scalar_call_separator", ", CAST("),
                            ("scalar_call_close", " AS pg_catalog.int4))"),
                        ]
                    elif realization["tag"] == "Decimal":
                        expected = [
                            ("scalar_call_open", "round("),
                            ("scalar_call_close", ")"),
                        ]
                    else:
                        expected = [
                            ("scalar_call_open", "(CASE WHEN abs(("),
                            ("scalar_call_separator", ") - trunc("),
                            ("scalar_call_separator", ") ) >= 0.5 THEN trunc("),
                            ("scalar_call_separator", " ) + (CASE WHEN "),
                            (
                                "scalar_call_separator",
                                " < 0 THEN -1.0 ELSE 1.0 END) ELSE trunc(",
                            ),
                            ("scalar_call_close", " ) END)"),
                        ]
                else:
                    expected = (
                        [
                            ("scalar_call_open", "CAST(date_trunc("),
                            ("scalar_call_separator", ", CAST("),
                            ("scalar_call_close", " AS timestamp))"),
                            ("scalar_call_close", " AS date)"),
                        ]
                        if realization["tag"] == "Date"
                        else [
                            ("scalar_call_open", "date_trunc("),
                            ("scalar_call_separator", ", "),
                            ("scalar_call_close", ")"),
                        ]
                    )
                _require(texts == expected, "C5 scalar token sequence")
            elif role == "window_argument_literal":
                column = self.one(windows, subject, "window arguments")
                expected = [
                    doc[a]["literal"]
                    for a in column["arguments"]
                    if doc[a]["literal"] is not None
                ]
            else:
                _require(subject in specifications, "window order")
                expected = [
                    schema.DIRECTIONS[doc[item]["direction"]]
                    for item in specifications[subject]["orders"]
                ]
            _require(texts == expected, "window token sequence")
        for subject, columns in aggregates.items():
            column = self.one(aggregates, subject, "aggregate subject")
            aggregate_tokens = [
                (event["role"], self.texts[position])
                for position, event in enumerate(self.events)
                if event["kind"] == "syntax"
                and event["subject"] == subject
                and event["role"].startswith("aggregate_")
            ]
            if column["function"] == "string_agg":
                expected = [
                    ("aggregate_open", "string_agg("),
                    ("aggregate_separator", ", "),
                    ("aggregate_order", " ORDER BY "),
                ]
                for position, item in enumerate(column["order_by"]):
                    if position:
                        expected.append(("aggregate_order_separator", ", "))
                    expected.append(
                        (
                            "aggregate_order_direction",
                            " ASC" if doc[item]["direction"] == "asc" else " DESC",
                        )
                    )
                expected.append(("aggregate_close", ")"))
                _require(
                    aggregate_tokens == expected,
                    "string_agg token sequence",
                )
            else:
                expected = []
                if column["result_cast"] is not None:
                    expected.append(("aggregate_result_cast_open", "CAST("))
                expected.append(("aggregate_open", column["spelling"] + "("))
                if column["argument"] is None:
                    expected.append(("aggregate_row_count", "*"))
                if column["distinct"]:
                    expected.append(("aggregate_distinct", "DISTINCT "))
                if column["argument_cast"] is not None:
                    expected.append(("aggregate_argument_cast_open", "CAST("))
                    expected.append(
                        (
                            "aggregate_argument_cast_close",
                            " AS " + column["argument_cast"] + ")",
                        )
                    )
                expected.append(("aggregate_close", ")"))
                if column["result_cast"] is not None:
                    expected.append(
                        (
                            "aggregate_result_cast_close",
                            " AS " + column["result_cast"] + ")",
                        )
                    )
                _require(aggregate_tokens == expected, "aggregate token sequence")
        parameters_in_order = [
            event["subject"] for event in self.events if event["kind"] == "parameter"
        ]
        uses = self.check.artifact["parameter_uses"]
        _require(len(parameters_in_order) == len(uses), "parameter tokens")
        for site, use in zip(parameters_in_order, uses, strict=True):
            _require(
                self.one(parameters, site, "parameter site")["use"] == use,
                "parameter order",
            )

    def syntax(
        self,
        role,
        subject,
        text,
        per_subject,
        operations,
        unaries,
        anchors,
        aggregates,
        windows,
        sets,
        joins,
        order_items,
        specifications,
    ) -> None:
        doc = self.doc
        node = operations.get(subject, [None])[0]
        if role in {"not_open", "not_close"}:
            _require(node is not None and node["kind"] == "not", "not subject")
            _require(
                text == {"not_open": "(NOT ", "not_close": ")"}[role], "not spelling"
            )
            return
        if role.startswith("conditional_"):
            _require(
                node is not None and node["kind"] == "conditional",
                "conditional subject",
            )
            _require(
                text
                == {
                    "conditional_open": "(CASE WHEN ",
                    "conditional_then": " THEN ",
                    "conditional_else": " ELSE ",
                    "conditional_close": " END)",
                }[role],
                "conditional spelling",
            )
            return
        if role.startswith("membership_") and node is not None:
            _require(node["kind"] == "membership", "membership subject")
            expected = {
                "membership_constant": "TRUE"
                if node["operator"] == "not_in"
                else "FALSE",
                "membership_open": "(",
                "membership_operator": " NOT IN ("
                if node["operator"] == "not_in"
                else " IN (",
                "membership_separator": ", ",
                "membership_close": "))",
            }[role]
            _require(text == expected, "membership spelling")
            return
        if role in {"cast_open", "cast_close"}:
            _require(node is not None and node["kind"] == "cast", "cast subject")
            assert node is not None
            operator = node["operator"]
            text_cast = operator == "int_to_text"
            _require(
                operator == "int_to_float"
                or (operator == "int_to_text" and self.family == "postgres"),
                "cast operation",
            )
            _require(
                text
                == (
                    "(CAST("
                    if text_cast and role == "cast_open"
                    else "CAST("
                    if role == "cast_open"
                    else ' AS pg_catalog.text) COLLATE "C")'
                    if text_cast and self.family == "postgres"
                    else " AS pg_catalog.float8)"
                    if self.family == "postgres"
                    else " AS DOUBLE)"
                ),
                "cast spelling",
            )
            return
        if role == "comparison_escape":
            _require(
                node is not None
                and node["kind"] == "comparison"
                and node["operator"] in {"like", "not like"}
                and text == " ESCAPE '!'",
                "comparison escape",
            )
            return
        if role.startswith("scalar_call_"):
            _require(
                node is not None and node["kind"] == "scalar_call",
                "scalar call subject",
            )
            assert node is not None
            name = node["operator"]
            if name in {"round", "date_trunc"}:
                per_subject.setdefault(("c5_scalar_tokens", subject), []).append(
                    (role, text)
                )
                return
            simple = {
                "postgres": {
                    "lower": "lower",
                    "upper": "upper",
                    "trim": "trim",
                    "replace": "replace",
                    "abs": "abs",
                    "nullif": "NULLIF",
                    "coalesce": "COALESCE",
                },
                "mysql": {
                    "lower": "LOWER",
                    "upper": "UPPER",
                    "trim": "TRIM",
                    "replace": "REPLACE",
                    "abs": "ABS",
                    "nullif": "NULLIF",
                    "coalesce": "COALESCE",
                },
            }[self.family]
            if role == "scalar_call_open":
                if name == "substr":
                    expected = (
                        "substring(" if self.family == "postgres" else "SUBSTRING("
                    )
                elif name == "len":
                    expected = (
                        "CAST(length("
                        if self.family == "postgres"
                        else "CAST(CHAR_LENGTH("
                    )
                elif name == "date_of":
                    expected = "CAST(" if self.family == "postgres" else "DATE("
                elif name == "contains":
                    expected = "(strpos(" if self.family == "postgres" else "(INSTR("
                elif name in {"starts_with", "ends_with"}:
                    function = "left" if name == "starts_with" else "right"
                    expected = (
                        "("
                        + (function if self.family == "postgres" else function.upper())
                        + "("
                    )
                elif name in {"year", "month", "day", "hour", "minute"}:
                    expected = (
                        "CAST(EXTRACT(" + name.upper() + " FROM "
                        if self.family == "postgres"
                        else "CAST(" + name.upper() + "("
                    )
                elif name == "sign":
                    expected = (
                        "CAST("
                        + ("sign" if self.family == "postgres" else "SIGN")
                        + "("
                    )
                else:
                    expected = simple.get(name, "") + "("
                _require(bool(expected) and text == expected, "scalar call spelling")
            elif role == "scalar_call_close":
                if name in {"substr", "starts_with", "ends_with"} or name in simple:
                    expected = ")"
                elif name == "date_of":
                    expected = " AS date)" if self.family == "postgres" else ")"
                elif name == "contains":
                    expected = ") > 0)"
                else:
                    expected = (
                        ") AS pg_catalog.int8)"
                        if self.family == "postgres"
                        else ") AS SIGNED)"
                    )
                _require(text == expected, "scalar call spelling")
            elif role == "scalar_call_separator":
                _require(
                    text
                    in (
                        {" FROM ", " FOR "}
                        if self.family == "postgres" and name == "substr"
                        else {", "}
                    ),
                    "scalar call separator",
                )
            elif role == "scalar_call_index_cast_open":
                _require(
                    name == "substr" and self.family == "postgres" and text == "CAST(",
                    "scalar index cast",
                )
            elif role == "scalar_call_index_cast_close":
                _require(
                    name == "substr"
                    and self.family == "postgres"
                    and text == " AS pg_catalog.int4)",
                    "scalar index cast",
                )
            elif role == "scalar_call_nested_open":
                _require(
                    name in {"starts_with", "ends_with"}
                    and text
                    == ("length(" if self.family == "postgres" else "CHAR_LENGTH("),
                    "scalar nested spelling",
                )
            elif role == "scalar_call_nested_close":
                _require(
                    name in {"starts_with", "ends_with"} and text == ")",
                    "scalar nested spelling",
                )
            else:
                _require(
                    name in {"starts_with", "ends_with"} and text == " ) = ",
                    "scalar call operator",
                )
            return
        if role in ("aggregate_argument_cast_open", "aggregate_result_cast_open"):
            column = self.one(aggregates, subject, "aggregate subject")
            _require(
                column[role[len("aggregate_") : -len("_open")]] is not None
                and text == schema.SYNTAX[role],
                "aggregate cast",
            )
            return
        elif role in schema.SYNTAX:
            _require(text == schema.SYNTAX[role], "syntax spelling")
            return
        if role in (
            "unary_open",
            "is_null_test",
            "arithmetic_operator",
            "logical_operator",
            "comparison_operator",
        ):
            node = operations.get(subject, [None])[0] or self.one(
                unaries, subject, "operator subject"
            )
            operator = node["operator"]
            expected = {
                "unary_open": "(" + operator,
                "is_null_test": " " + operator.upper(),
                "arithmetic_operator": " " + operator + " ",
                "logical_operator": " " + operator.upper() + " ",
                "comparison_operator": schema.COMPARISON_SPELLING.get(operator),
            }[role]
            _require(text == expected, "operator spelling")
        elif role == "anchor_close":
            anchor = self.one(anchors, subject, "anchor subject")
            _require(
                text == schema.ANCHOR_SUFFIX[anchor["physical_type"]], "anchor spelling"
            )
        elif role == "aggregate_open":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(text == column["spelling"] + "(", "aggregate spelling")
        elif role in ("aggregate_argument_cast_close", "aggregate_result_cast_close"):
            column = self.one(aggregates, subject, "aggregate subject")
            cast = column[role[len("aggregate_") : -len("_close")]]
            _require(cast is not None and text == " AS " + cast + ")", "aggregate cast")
        elif role == "aggregate_order_direction":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(
                column["function"] == "string_agg" and text in {" ASC", " DESC"},
                "aggregate order direction",
            )
        elif role == "window_open":
            column = self.one(windows, subject, "window subject")
            _require(
                text == schema.WINDOW_SPELLING[column["function"]] + "(",
                "window spelling",
            )
        elif role == "window_order_direction":
            per_subject.setdefault((role, subject), []).append(text)
        elif role in (
            "window_frame_unit",
            "window_frame_start",
            "window_frame_end",
            "window_frame_exclusion",
        ):
            _require(subject in specifications, "window frame subject")
            frame = specifications[subject]["frame"]
            _require(frame is not None, "window frame")
            frame = doc[frame]
            expected = {
                "window_frame_unit": schema.FRAME_UNITS[frame["unit"]] + " BETWEEN ",
                "window_frame_start": frame["start"][1],
                "window_frame_end": frame["end"][1],
                "window_frame_exclusion": schema.EXCLUSIONS.get(frame["exclusion"]),
            }[role]
            _require(text == expected, "window frame spelling")
        elif role == "order_direction":
            item = self.one(order_items, subject, "order subject")
            _require(text == schema.DIRECTIONS[item["direction"]], "order direction")
        elif role == "set_operator":
            unit = self.one(sets, subject, "set subject")
            _require(
                text == schema.set_spelling(unit["kind"], unit["quantifier"]),
                "set spelling",
            )
        elif role in ("join_kind", "membership_open"):
            join = self.one(joins, subject, "join subject")
            expected = (
                schema.JOIN_SPELLING.get(join["join_kind"])
                if role == "join_kind"
                else schema.MEMBERSHIP_SPELLING.get(join["membership"])
            )
            _require(text == expected, "join spelling")
        else:
            raise _Reject(Status.INVALID_RELATION, "syntax role")

    def overlay_alignment(self) -> None:
        doc = self.doc
        self.carriers: dict[str, dict[PlanRef, tuple[set, set]]] = {
            "reference": {},
            "grouping": {},
            "order_item": {},
            "capture": {},
        }
        for kind, role, key, port, read in (
            ("sql_stage_reference", "reference", "original", "port", "column"),
            ("sql_any_reference", "reference", "original", "port", "column"),
            ("sql_captured_reference", "capture", "original", "capture", "column"),
            ("aggregate_key_column", "grouping", "key", "input_port", "read"),
            ("result_order_item", "order_item", "item", "port", "read"),
        ):
            for ref in doc.all(kind):
                fields = doc[ref]
                ports, terminals = self.carriers[role].setdefault(
                    fields[key], (set(), set())
                )
                ports.add(fields[port])
                terminals.add(doc[fields[read]]["terminal"])
        starts = {event["start"]: i for i, event in enumerate(self.events)}
        ends = {event["end"]: i for i, event in enumerate(self.events)}
        spans = []
        for overlay in self.overlays:
            _require(overlay["kind"] == "expression_range", "overlay kind")
            _require(overlay["role"] in schema.OVERLAYS, "overlay role")
            first, last = schema.OVERLAYS[overlay["role"]]
            _require(
                overlay["start"] in starts and overlay["end"] in ends,
                "overlay boundary",
            )
            i, j = starts[overlay["start"]], ends[overlay["end"]]
            _require(i <= j, "overlay boundary")
            opening, closing = self.events[i], self.events[j]
            _require(
                opening["role"] in first and closing["role"] in last, "overlay tokens"
            )
            subject = overlay["subject"]
            if overlay["role"] in ("reference", "grouping", "order_item", "capture"):
                _require(
                    i + 2 <= j and self.events[i + 1]["subject"] == subject,
                    "overlay subject",
                )
                ports, terminals = self.carriers[overlay["role"]].get(
                    subject, (set(), set())
                )
                _require(
                    opening["subject"] in ports
                    and self.events[i + 2]["subject"] in terminals,
                    "overlay carrier",
                )
            else:
                _require(
                    opening["subject"] == subject and closing["subject"] == subject,
                    "overlay subject",
                )
            spans.append((overlay["start"], overlay["end"]))
        enclosing: list[int] = []
        for start, end in sorted(spans, key=lambda span: (span[0], -span[1])):
            while enclosing and enclosing[-1] <= start:
                enclosing.pop()
            _require(not enclosing or end <= enclosing[-1], "overlay nesting")
            enclosing.append(end)

    def int8_widening(self) -> None:
        """PostgreSQL `sign`, arithmetic and `abs` over int2/int4 operands are
        widened to bigint exactly when their exact range leaves the operands'
        own type: one first-operand CAST, never a redundant one."""
        doc = self.doc
        expected: set[PlanRef] = set()
        for ref in doc.all("sql_operation"):
            op = doc[ref]
            if not (
                op["kind"] in ("sign", "arithmetic")
                or op["kind"] == "scalar_call"
                and op["operator"] == "abs"
            ):
                continue
            result = doc[op["realization"]]
            kinds = [
                (_value_realization(doc, operand) or {"storage": {}})["storage"].get(
                    "kind"
                )
                for operand in op["operands"]
            ]
            narrow = [
                kind
                for kind in kinds
                if type(kind) is str and kind in ("pg_int2", "pg_int4")
            ]
            if (
                self.family != "postgres"
                or result["tag"] != "Int"
                or dict(result["storage"]) != {"kind": "pg_int8"}
                or not kinds
                or len(narrow) != len(kinds)
            ):
                continue
            bits = max(_SIGNED_STORAGE_BITS[kind] for kind in narrow)
            _require(_is_pg_int(result), "int8 widening")
            low, high = int(result["domain"]["min"]), int(result["domain"]["max"])
            _require(
                low < -(1 << (bits - 1)) or high > (1 << (bits - 1)) - 1,
                "int8 widening",
            )
            expected.add(op["original"])
        starts = {event["start"]: i for i, event in enumerate(self.events)}
        ends = {event["end"]: i for i, event in enumerate(self.events)}
        seen: list[PlanRef] = []
        for overlay in self.overlays:
            if overlay["role"] != "int8_widen":
                continue
            subject = overlay["subject"]
            i, j = starts[overlay["start"]], ends[overlay["end"]]
            _require(
                subject in expected
                and 0 < i
                and j + 1 < len(self.events)
                and self.events[i - 1]["subject"] == subject
                and self.events[i - 1]["role"]
                in ("binary_open", "unary_open", "scalar_call_open")
                and self.events[j + 1]["subject"] == subject
                and self.events[j + 1]["role"]
                in ("arithmetic_operator", "unary_close", "scalar_call_close"),
                "int8 widening",
            )
            seen.append(subject)
        _require(len(seen) == len(set(seen)) and set(seen) == expected, "int8 widening")

    def origins(self) -> None:
        by_subject: dict[PlanRef, tuple[Ref, ...]] = {}
        for event in (*self.events, *self.overlays):
            known = by_subject.setdefault(event["subject"], event["origins"])
            _require(known == event["origins"], "origins per subject")
        for ref in self.doc.all("origin"):
            origin = self.doc[ref]
            _require(origin["ref"].kind == "origin", "origin reference")
            positions = [self.doc[a]["position"] for a in origin["associations"]]
            _require(positions == sorted(set(positions)), "association order")
            for association in origin["associations"]:
                location = self.doc[association]["location"]
                _require(
                    type(location) is MappingProxyType
                    and tuple(location)
                    == (
                        "availability",
                        "column",
                        "end_column",
                        "end_line",
                        "line",
                        "path",
                    )
                    and location["availability"]
                    in ("complete", "partial", "unavailable"),
                    "association location",
                )


class _ProvenIntRanges:
    """Rebuild the Int proof carried by the closed public provenance graph."""

    _UNKNOWN = object()
    _EMPTY = object()
    _COLUMN_PRODUCERS = (
        "row_carry_column",
        "row_value_column",
        "aggregate_key_column",
        "aggregate_value_column",
        "aggregate_projection_column",
        "window_column",
        "window_projection_column",
        "result_column",
        "set_column",
        "join_column",
    )

    def __init__(self, doc: _Doc, family: str) -> None:
        self.doc = doc
        self.family = family
        self.columns: dict[Ref, tuple[Ref, ...]] = {}
        self.terminals: dict[PlanRef, tuple[Ref, ...]] = {}
        for kind in self._COLUMN_PRODUCERS:
            for ref in doc.all(kind):
                fields = doc[ref]
                column = fields.get("column")
                if isinstance(column, Ref):
                    self.columns[column] = (*self.columns.get(column, ()), ref)
                terminal = fields["port" if kind == "join_column" else "export"]
                self.terminals[terminal] = (*self.terminals.get(terminal, ()), ref)
        for kind in ("row_body", "row_result_body", "set_body"):
            for ref in doc.all(kind):
                body = doc[ref]
                for terminal, column in zip(
                    body["terminals"], body["columns"], strict=True
                ):
                    producers = self.terminals.get(terminal, ())
                    if column not in producers:
                        self.terminals[terminal] = (*producers, column)
        self.values: dict[Ref, tuple[int, int] | object] = {}
        self.visiting: set[Ref] = set()

    def value(self, ref: Ref) -> tuple[int, int] | object:
        if self.family != "postgres":
            return self._UNKNOWN
        if ref in self.values:
            return self.values[ref]
        if ref in self.visiting:
            return self._UNKNOWN
        self.visiting.add(ref)
        try:
            result = self._value(ref)
        finally:
            self.visiting.remove(ref)
        self.values[ref] = result
        return result

    def _value(self, ref: Ref) -> tuple[int, int] | object:
        doc = self.doc
        if ref.kind in {
            "sql_stage_reference",
            "sql_captured_reference",
            "sql_any_reference",
        }:
            return self.column(doc[ref]["column"])
        if ref.kind == "sql_block_read":
            read, target = doc[ref], doc[doc[ref]["target"]]
            if read["kind"] != "scalar" or type(read["column"]) is not int:
                return self._UNKNOWN
            producer = target["producer"]
            if producer.kind == "bound_source":
                fields = [
                    field
                    for field in doc[producer]["fields"]
                    if doc[field]["ordinal"] == read["column"]
                ]
                return self.field(fields[0]) if len(fields) == 1 else self._UNKNOWN
            columns = doc[producer]["columns"]
            index = read["column"]
            return (
                self.column(doc[columns[index]]["column"])
                if 0 <= index < len(columns)
                else self._UNKNOWN
            )
        if ref.kind == "sql_anchor":
            value = _literal_int(doc, ref)
            if value is not None:
                return value, value
            leaf = doc[ref]["operand"]
            fixed = (
                doc[leaf]["value"]
                if leaf.kind == "sql_literal"
                else doc[doc[leaf]["fixed"]]["value"]
                if leaf.kind == "sql_parameter"
                else None
            )
            return (
                fixed.tag
                if fixed is not None and fixed.tag in {"Float", "Decimal"}
                else self._UNKNOWN
            )
        if ref.kind == "sql_null":
            return self._EMPTY
        if ref.kind == "sql_unary":
            value = self.value(doc[ref]["operand"])
            interval = self.as_range(value)
            if interval is None:
                return value
            return (
                interval
                if doc[ref]["operator"] == "+"
                else (-interval[1], -interval[0])
            )
        if ref.kind != "sql_operation":
            return self._UNKNOWN
        op = doc[ref]
        if op["kind"] == "cast" and op["operator"] == "Float":
            return "Float"
        if op["kind"] == "scalar_call" and op["operator"] == "round":
            value = self.value(op["operands"][0])
            return value if value in {"Float", "Decimal"} else self._UNKNOWN
        if op["kind"] == "conditional" and len(op["operands"]) == 3:
            return self.union(
                (self.value(op["operands"][0]), self.value(op["operands"][2]))
            )
        if op["kind"] == "scalar_call" and op["operator"] == "nullif":
            return (
                self.value(op["operands"][0])
                if len(op["operands"]) == 2
                else self._UNKNOWN
            )
        if op["kind"] == "scalar_call" and op["operator"] == "coalesce":
            return self.union(tuple(self.value(value) for value in op["operands"]))
        if op["kind"] == "scalar_call" and op["operator"] == "len":
            return _I64_MIN, _I64_MAX
        if op["kind"] == "scalar_call" and op["operator"] == "sign":
            return -1, 1
        if op["kind"] == "scalar_call" and op["operator"] in {
            "year",
            "month",
            "day",
            "hour",
            "minute",
        }:
            return {
                "year": (1000, 9999),
                "month": (1, 12),
                "day": (1, 31),
                "hour": (0, 23),
                "minute": (0, 59),
            }[op["operator"]]
        raw = self.operation(ref)
        interval = self.as_range(raw)
        return self.checked(interval) if interval is not None else raw

    def field(self, ref: Ref) -> tuple[int, int] | object:
        try:
            field = self.doc[ref]
            representation = json.loads(field["representation"])
            tag = field["logical"]["name"]
            kind = representation["storage"]["kind"]
            realization = {"tag": tag, **representation}
        except (KeyError, TypeError, ValueError):
            return self._UNKNOWN
        if tag == "Decimal" and _pg_decimal_parameters(realization) is not None:
            return "Decimal"
        if _is_realization(
            realization,
            "Float",
            {"kind": "pg_float8"},
            {"kind": "finite_float", "format": "binary64"},
        ):
            return "Float"
        if tag != "Int" or kind not in {"pg_int2", "pg_int4", "pg_int8"}:
            return self._UNKNOWN
        bits = _SIGNED_STORAGE_BITS.get(kind)
        return (
            self._UNKNOWN
            if bits is None
            else (-(1 << (bits - 1)), (1 << (bits - 1)) - 1)
        )

    def column(self, ref: Ref) -> tuple[int, int] | object:
        if ref in self.values:
            return self.values[ref]
        if ref in self.visiting:
            return self._UNKNOWN
        self.visiting.add(ref)
        try:
            result = self._column(ref)
        finally:
            self.visiting.remove(ref)
        self.values[ref] = result
        return result

    def _column(self, ref: Ref) -> tuple[int, int] | object:
        column = self.doc[ref]
        if column["field"] is not None:
            return self.field(column["field"])
        if column["literal"] is not None:
            return self.value(self.doc[column["literal"]]["value"])
        if column["aggregate"] is not None:
            origin = self.doc[column["aggregate"]]
            values = [
                ref
                for ref in self.doc.all("aggregate_value_column")
                if self.doc[ref]["aggregate"] == origin["aggregate"]
            ]
            return (
                self.aggregate(self.doc[values[0]])
                if len(values) == 1
                else self._UNKNOWN
            )
        if column["window"] is not None:
            origin = self.doc[column["window"]]
            windows = [
                ref
                for ref in self.doc.all("window_column")
                if self.doc[ref]["window"] == origin["window"]
            ]
            return (
                self.window(self.doc[windows[0]])
                if len(windows) == 1
                else self._UNKNOWN
            )
        # Reads may be distinct serialized views of the same exported occurrence.
        producers = self.terminals.get(column["terminal"], self.columns.get(ref, ()))
        defining = tuple(
            producer
            for producer in producers
            if producer.kind
            in {
                "row_value_column",
                "aggregate_value_column",
                "window_column",
                "set_column",
            }
        )
        if len(defining) == 1:
            producer = defining[0]
        elif len(producers) == 1:
            producer = producers[0]
        else:
            return self._UNKNOWN
        fields = self.doc[producer]
        if producer.kind in {
            "row_carry_column",
            "aggregate_key_column",
            "aggregate_projection_column",
            "window_projection_column",
            "result_column",
            "join_column",
        }:
            return self.column(fields["read"])
        if producer.kind == "row_value_column":
            return self.value(fields["value"])
        if producer.kind == "set_column":
            values = tuple(self.column(value) for value in fields["inputs"])
            return self.union(values)
        if producer.kind == "aggregate_value_column":
            return self.aggregate(fields)
        if producer.kind == "window_column":
            return self.window(fields)
        return self._UNKNOWN

    def aggregate(self, column: Mapping[str, Any]) -> tuple[int, int] | object:
        function = column["function"]
        if function in {"count", "count_distinct"}:
            return 0, _I64_MAX
        if function == "sum":
            return _I64_MIN, _I64_MAX
        if function == "avg":
            return "Float"
        if function in {"min", "max"} and column["argument"] is not None:
            return self.value(column["argument"])
        return self._UNKNOWN

    def window(self, column: Mapping[str, Any]) -> tuple[int, int] | object:
        function = column["function"]
        if function in {"percent_rank", "cume_dist", "avg"}:
            return "Float"
        if function in {"row_number", "rank", "dense_rank", "count"}:
            return 0, _I64_MAX
        if function == "sum":
            return _I64_MIN, _I64_MAX
        if function == "ntile":
            return 1, (1 << 31) - 1
        arguments = [self.doc[item] for item in column["arguments"]]
        reads = [item["read"] for item in arguments if item["read"] is not None]
        if function in {"min", "max"}:
            return self.column(reads[0]) if len(reads) == 1 else self._UNKNOWN
        if function not in _VALUE_WINDOWS or len(reads) != 1:
            return self._UNKNOWN
        value = self.column(reads[0])
        defaults = [item["literal"] for item in arguments if item["role"] == "default"]
        if not defaults or defaults[0] == "NULL" or value in {"Float", "Decimal"}:
            return value
        try:
            default = int(defaults[0])
        except (TypeError, ValueError):
            return self._UNKNOWN
        return self.union((value, (default, default)))

    @classmethod
    def known(cls, value: tuple[int, int] | object) -> bool:
        return isinstance(value, tuple)

    @staticmethod
    def as_range(value: tuple[int, int] | object) -> tuple[int, int] | None:
        return value if isinstance(value, tuple) else None

    def union(self, values) -> tuple[int, int] | object:
        if any(value is self._UNKNOWN for value in values):
            return self._UNKNOWN
        present = tuple(value for value in values if value is not self._EMPTY)
        if any(value in {"Float", "Decimal"} for value in present):
            return (
                present[0]
                if all(value == present[0] for value in present)
                else self._UNKNOWN
            )
        known = tuple(value for value in present if self.known(value))
        if not known:
            return self._EMPTY
        ranges = cast(tuple[tuple[int, int], ...], known)
        return min(low for low, _ in ranges), max(high for _, high in ranges)

    def checked(self, value: tuple[int, int]) -> tuple[int, int] | object:
        low, high = max(value[0], _I64_MIN), min(value[1], _I64_MAX)
        return (low, high) if low <= high else self._UNKNOWN

    def operation(self, ref: Ref) -> tuple[int, int] | object:
        op = self.doc[ref]
        supported = op["kind"] in {"sign", "arithmetic"} or (
            op["kind"] == "scalar_call" and op["operator"] == "abs"
        )
        if not supported:
            return self._UNKNOWN
        values = tuple(self.value(value) for value in op["operands"])
        if any(value is self._UNKNOWN for value in values):
            return self._UNKNOWN
        if any(value is self._EMPTY for value in values):
            return self._EMPTY
        if any(value in {"Float", "Decimal"} for value in values):
            return values[0] if len(values) == 1 else self._UNKNOWN
        ranges = cast(tuple[tuple[int, int], ...], values)
        if op["kind"] == "sign" and len(ranges) == 1:
            low, high = ranges[0]
            return (-high, -low) if op["operator"] == "-" else (low, high)
        if op["kind"] == "arithmetic" and len(ranges) == 2:
            (a, b), (c, d) = ranges
            if op["operator"] == "+":
                return a + c, b + d
            if op["operator"] == "-":
                return a - d, b - c
            if op["operator"] == "*":
                products = (a * c, a * d, b * c, b * d)
                return min(products), max(products)
        if op["kind"] == "scalar_call" and op["operator"] == "abs" and len(ranges) == 1:
            low, high = ranges[0]
            return max(low, -high, 0), max(-low, high)
        return self._UNKNOWN

    def target_checked(self, ref: Ref) -> tuple[int, int] | object | None:
        if self.family != "postgres" or ref.kind != "sql_operation":
            return None
        op = self.doc[ref]
        supported = op["kind"] in {"sign", "arithmetic"} or (
            op["kind"] == "scalar_call" and op["operator"] == "abs"
        )
        if not supported:
            return None
        result = self.doc[op["realization"]]
        raw = self.operation(ref)
        if raw is self._EMPTY:
            return None
        if raw in {"Float", "Decimal"}:
            return None if result["tag"] == raw else self._UNKNOWN
        if result["tag"] != "Int" or raw is self._UNKNOWN:
            return self._UNKNOWN
        interval = self.as_range(raw)
        if interval is None:
            return self._UNKNOWN
        if interval[1] < _I64_MIN or interval[0] > _I64_MAX:
            return self._UNKNOWN
        return (
            self.checked(interval)
            if interval[0] < _I64_MIN or interval[1] > _I64_MAX
            else None
        )


class _Requirements:
    """Independent re-enumeration of both requirement inventories."""

    def __init__(self, check: _Check, units: list[Ref]) -> None:
        self.check = check
        self.doc = check.doc
        self.family = check.family
        self.units = units
        doc = self.doc
        self.premises = [(ref, doc[ref]) for ref in check.request["premises"]]
        self.expected: list[tuple[str, Any, str, Any, Any]] = []
        self.ranges = _ProvenIntRanges(doc, self.family)

    def statement(self, *keys: str) -> tuple[Ref, ...]:
        return tuple(
            ref
            for ref, p in self.premises
            if p["scope"] == "statement" and p["key"] in keys
        )

    def add(
        self, kind: str, subject: Any, rule: str, premises: Any, evidence: Any = ()
    ) -> None:
        self.expected.append((kind, subject, rule, premises, evidence))

    def checked_evidence(self, evidence: Any, value: Ref) -> None:
        """Q2 evidence follows the independently rebuilt operand proof."""
        interval = self.ranges.target_checked(value)
        _require(interval is not self.ranges._UNKNOWN, "target checked proof")
        if interval is None:
            _require(evidence == (), "target checked evidence")
            return
        proven = self.ranges.as_range(interval)
        _require(proven is not None, "target checked proof")
        if proven is None:
            return
        low, high = proven
        result = self.doc[self.doc[value]["realization"]]
        _require(
            _is_pg_int(result)
            and dict(result["storage"]) == {"kind": "pg_int8"}
            and dict(result["domain"])
            == {"kind": "int_range", "min": str(low), "max": str(high)},
            "target checked result",
        )
        _require(evidence == (_TARGET_CHECKED,), "target checked evidence")

    def applicable(self, owner: Ref, field: bool) -> Any:
        required = tuple(
            ref
            for ref, p in self.premises
            if p["scope"] == "statement" or p["scope"] == owner
        )
        allowed = tuple(
            ref
            for ref, p in self.premises
            if p["scope"] == "statement"
            or p["scope"] == owner
            or (field and type(p["scope"]) is tuple and p["scope"][0] == owner)
        )
        return required if not field else ("between", required, allowed)

    def tag(self, value: Ref) -> str:
        doc = self.doc
        if value.kind in (
            "sql_stage_reference",
            "sql_any_reference",
            "sql_operation",
            "sql_block_read",
            "sql_any_read",
            "sql_captured_reference",
        ):
            return doc[doc[value]["realization"]]["tag"]
        if value.kind == "sql_null":
            return doc[value]["tag"]
        while value.kind == "sql_unary":
            value = doc[value]["operand"]
        return doc[value]["tag"]

    def node_premises(
        self, tag: str, operands: tuple[str, ...], kind: str
    ) -> tuple[Ref, ...]:
        keys = ["operator_environment"]
        if tag == "Text" or "Text" in operands:
            keys.append("client_encoding")
        if kind == "parameter":
            keys.append("parameter_protocol")
        return self.statement(*keys)

    def scan(self, subject: Ref, bound: Ref) -> None:
        doc = self.doc
        owner = doc[bound]["owner"]
        self.add("qualified_scan", subject, "R01", self.applicable(owner, False))
        for field in doc[bound]["fields"]:
            self.add(
                "source_representation", field, "R02", self.applicable(owner, True)
            )

    def constant(self, value: Ref) -> None:
        doc = self.doc
        tag = self.tag(value)
        if value.kind == "sql_null":
            self.add(
                "literal",
                doc[value]["original"],
                "R04",
                self.node_premises(tag, (), "literal"),
            )
            return
        chain = []
        while value.kind == "sql_unary":
            chain.append(value)
            value = doc[value]["operand"]
        chain.append(value)
        chain.append(doc[value]["operand"])
        for node in chain:
            kind = {
                "sql_unary": "unary",
                "sql_anchor": "type_anchor",
                "sql_parameter": "parameter",
                "sql_literal": "literal",
            }[node.kind]
            self.add(
                kind, doc[node]["original"], "R04", self.node_premises(tag, (), kind)
            )

    def value(self, value: Ref) -> None:
        doc = self.doc
        if value.kind in ("sql_block_read", "sql_any_read"):
            fields = doc[value]
            _require(
                fields["kind"] in ("exists", "scalar", "in", "not_in"),
                "block read kind",
            )
            kind = (
                "relation_membership"
                if fields["kind"] in ("in", "not_in")
                else fields["kind"]
            )
            # Membership compares its operand with one column of that tag.
            operands = tuple(self.tag(operand) for operand in fields["operands"])
            self.add(
                kind,
                fields["original"],
                "R11",
                self.node_premises(self.tag(value), operands, kind),
            )
            target = doc[fields["target"]]
            if target["source"] is not None:
                bound = target["producer"]
                owner = doc[bound]["owner"]
                self.add(
                    "qualified_scan",
                    fields["target"],
                    "R01",
                    self.applicable(owner, False),
                )
                for field in doc[bound]["fields"]:
                    self.add(
                        "source_representation",
                        field,
                        "R02",
                        self.applicable(owner, True),
                    )
            elif target["producer"] in self.check.inline:
                self.inline(target["producer"])
            for operand in fields["operands"]:
                self.value(operand)
            if value.kind == "sql_any_read":
                self.value(fields["predicate"])
            return
        if value.kind == "sql_captured_reference":
            self.add(
                "capture",
                doc[value]["original"],
                "R11",
                self.node_premises(self.tag(value), (), "capture"),
            )
            return
        if value.kind in ("sql_stage_reference", "sql_any_reference"):
            fields = doc[value]
            self.add(
                "reference",
                fields["original"],
                "R05",
                self.node_premises(self.tag(value), (), "reference"),
            )
            return
        if value.kind != "sql_operation":
            self.constant(value)
            return
        fields = doc[value]
        kind = "arithmetic" if fields["kind"] == "sign" else fields["kind"]
        operands = tuple(self.tag(operand) for operand in fields["operands"])
        self.add(
            kind,
            fields["original"],
            "R06" if kind in {"logical", "not"} else "R05",
            self.node_premises(self.tag(value), operands, kind),
            ("checked", value) if kind in ("arithmetic", "scalar_call") else (),
        )
        operands = fields["operands"]
        if fields["kind"] == "conditional":
            operands = (operands[1], operands[0], operands[2])
        for operand in operands:
            self.value(operand)

    def run(self) -> None:
        self.original()
        if self.check.ast.kind == "sql_select":
            self.direct()
        else:
            self.rows()
        actual = [
            self.doc[ref] for ref in self.check.artifact["generated_requirements"]
        ]
        _require(len(actual) == len(self.expected), "generated inventory size")
        for item, (kind, subject, rule, premises, evidence) in zip(
            actual, self.expected, strict=True
        ):
            _require(
                (item["kind"], item["subject"], item["rule"]) == (kind, subject, rule),
                "generated inventory entry",
            )
            if evidence[:1] == ("checked",):
                self.checked_evidence(item["evidence"], evidence[1])
            else:
                _require(item["evidence"] == evidence, "generated evidence")
            if type(premises) is tuple and premises[:1] == ("between",):
                _, required, allowed = premises
                have = item["premises"]
                _require(
                    set(required) <= set(have)
                    and list(have) == [ref for ref in allowed if ref in have],
                    "generated premise scope",
                )
            else:
                _require(item["premises"] == premises, "generated premises")

    def original(self) -> None:
        doc = self.doc
        demands: dict[PlanRef, set[str]] = {}
        for position, ref in enumerate(self.check.artifact["original_requirements"]):
            item = doc[ref]
            _require(
                item["entry"] == PlanRef("demand", position)
                and item["rule"] in schema.RULES,
                "original inventory entry",
            )
            _require(
                type(item["evidence"]) is tuple
                and all(
                    type(aspect) is tuple and all(type(s) is str for s in aspect)
                    for aspect in item["evidence"]
                ),
                "original evidence",
            )
            demands.setdefault(item["subject"], set()).add(item["family"])
        for kind in (
            "sql_operation",
            "sql_stage_reference",
            "sql_any_reference",
            "sql_captured_reference",
            "sql_unary",
            "sql_anchor",
        ):
            for ref in doc.all(kind):
                _require(
                    "expression" in demands.get(doc[ref]["original"], ()),
                    "original expression demand",
                )
        for ref in doc.all("row_predicate"):
            _require(
                "filter" in demands.get(doc[ref]["original"], ()),
                "original filter demand",
            )

    def direct(self) -> None:
        doc = self.doc
        naming = self.statement("identifier_case")
        select = doc[self.check.ast]
        for cte in select["ctes"]:
            definition = doc[doc[cte]["definition"]]
            self.add("cte_definition", definition["original"], "R03", naming)
            for terminal in definition["terminals"]:
                self.add("terminal_column", terminal, "R03", naming)
        for body in self.units:
            fields = doc[body]
            scan = fields["scan"]
            if scan.kind == "sql_scan":
                self.scan(scan, doc[scan]["realization"])
            else:
                self.add("named_use", doc[scan]["use"], "R03", naming)
                for binding in doc[doc[scan]["binding"]]["bindings"]:
                    self.add(
                        "immediate_terminal", doc[binding]["terminal"], "R03", naming
                    )
            for column in fields["columns"]:
                item = doc[column]
                if column.kind == "sql_literal_column":
                    self.add("value_projection", item["projection"], "R04", ())
                    if item["value"] is not None:
                        self.constant(item["value"])
                    continue
                owner = doc[doc[item["origin"]]["realization"]]["owner"]
                self.add(
                    "field_projection", column, "R02", self.applicable(owner, True)
                )
            self.add("read_only_select_bytes", body, "R23", ())
        if select["ctes"]:
            self.add("nonrecursive_with_bytes", self.check.ast, "R23", ())

    def rows(self) -> None:
        doc = self.doc
        naming = self.statement("identifier_case")
        encoding = self.statement("client_encoding")
        units = self.units
        for unit in units[:-1]:
            self.add("cte_definition", _unit_plan(doc, unit), "R03", naming)
            for symbol in doc[unit]["cte_columns"]:
                self.add("terminal_column", doc[symbol]["binding"], "R03", naming)
        for unit in units:
            fields = doc[unit]
            if unit.kind == "join_body":
                self.join(unit, naming)
                continue
            if unit.kind == "set_body":
                self.add("set_operation", fields["body"], "R22", naming)
                for operand in fields["operands"]:
                    item = doc[operand]
                    self.add("set_operand", item["operand"], "R22", naming)
                    if item["source"] is not None:
                        self.scan(item["producer"], item["producer"])
                for column in fields["columns"]:
                    item = doc[column]
                    tag = doc[item["realization"]]["tag"]
                    self.add(
                        "set_column",
                        item["source"],
                        "R22",
                        encoding if tag == "Text" else (),
                    )
                if fields["requires_equivalence"]:
                    self.add("set_row_equivalence", fields["body"], "R22", ())
                self.add("read_only_select_bytes", unit, "R23", ())
                continue
            if unit.kind == "row_result_body":
                body = doc[doc[fields["scan"]]["body"]]
                self.add("stage_use", body["block"], "R03", naming)
                for symbol in body["cte_columns"]:
                    self.add("stage_terminal", doc[symbol]["binding"], "R03", naming)
                self.result(unit, naming, encoding)
                self.add("read_only_select_bytes", unit, "R23", ())
                continue
            self.row_body(unit)
        if len(units) > 1:
            self.add("nonrecursive_with_bytes", self.check.ast, "R23", ())

    def inline(self, body: Ref) -> None:
        """An inline let's bodies, innermost first, at the read rendering them."""
        doc = self.doc
        scan = doc[body]["scan"]
        if scan.kind == "row_stage_use" and doc[scan]["body"] in self.check.inline:
            self.inline(doc[scan]["body"])
        self.row_body(body)

    def row_body(self, unit: Ref) -> None:
        doc = self.doc
        naming = self.statement("identifier_case")
        operators = self.statement("operator_environment")
        fields = doc[unit]
        scan = fields["scan"]
        item = doc[scan]
        if scan.kind == "row_scan":
            self.scan(scan, item["realization"])
        elif scan.kind == "row_named_use":
            self.add("named_use", item["use"], "R03", naming)
            for binding in doc[item["binding"]]["bindings"]:
                self.add("immediate_terminal", doc[binding]["terminal"], "R03", naming)
        elif scan.kind == "row_join_use":
            self.add("join_use", item["tail"], "R07", naming)
            for symbol in doc[item["body"]]["cte_columns"]:
                self.add("join_terminal", doc[symbol]["binding"], "R07", naming)
        elif item["body"] in self.check.inline:
            self.add("inline_stage_use", item["block"], "R11", naming)
        else:
            self.add("stage_use", item["block"], "R03", naming)
            for symbol in doc[item["body"]]["cte_columns"]:
                self.add("stage_terminal", doc[symbol]["binding"], "R03", naming)
        if fields["aggregation"] is not None:
            self.add(
                "aggregation",
                doc[fields["aggregation"]]["aggregation"],
                "R12",
                operators,
            )
        for column in fields["columns"]:
            item = doc[column]
            kind = column.kind
            if kind == "row_carry_column":
                self.add("carry_projection", item["export"], "R05", ())
            elif kind == "aggregate_key_column":
                self.add("group_key", item["key"], "R12", operators)
            elif kind == "aggregate_value_column":
                self.add(
                    "aggregate",
                    item["aggregate"],
                    "R13",
                    operators,
                    () if item["result_cast"] is None else (_TARGET_CHECKED,),
                )
                if item["argument"] is not None:
                    self.value(item["argument"])
                if item["delimiter"] is not None:
                    self.value(item["delimiter"])
                for order in item["order_by"]:
                    self.value(doc[order]["value"])
            elif kind == "aggregate_projection_column":
                self.add("result_projection", item["projection"], "R12", ())
            elif kind == "window_column":
                origin = doc[doc[item["column"]]["window"]]
                spec = doc[item["specification"]]
                self.add("window_computation", item["window"], "R14", operators)
                self.add("window_specification", origin["policy"], "R15", ())
                frame = None if spec["frame"] is None else doc[spec["frame"]]
                if frame is not None and _frame_offsets(frame):
                    self.add("window_frame_offset_domain", origin["policy"], "R15", ())
                    if frame["unit"] == "range":
                        self.add(
                            "window_range_arithmetic",
                            origin["policy"],
                            "R15",
                            operators,
                        )
                for partition in spec["partitions"]:
                    read = doc[doc[partition]["read"]]
                    _require(
                        _source_field_matches_stage(doc, read)
                        and _is_key_value(
                            doc[read["realization"]], self.family, partition=True
                        ),
                        "window comparison carrier",
                    )
                    self.add("window_partition_comparison", read["terminal"], "R14", ())
                for order in spec["orders"]:
                    read = doc[doc[order]["read"]]
                    _require(
                        _source_field_matches_stage(doc, read)
                        and _is_key_value(doc[read["realization"]], self.family),
                        "window comparison carrier",
                    )
                    self.add("window_order_comparison", read["terminal"], "R14", ())
            elif kind == "window_projection_column":
                self.add("window_result_projection", item["projection"], "R17", ())
            else:
                self.add("computed_projection", item["export"], "R05", ())
                self.value(item["value"])
        if fields["predicate"] is not None:
            predicate = doc[fields["predicate"]]
            satisfying = fields["block_kind"] == "satisfying"
            self.add(
                "satisfying_root" if satisfying else "predicate_root",
                predicate["original"],
                "R12" if satisfying else "R06",
                operators,
            )
            self.value(predicate["value"])
        self.add("read_only_select_bytes", unit, "R23", ())

    def join(self, unit: Ref, naming) -> None:
        doc = self.doc
        fields = doc[unit]
        kind = fields["join_kind"]
        rule = (
            "R11"
            if kind in ("semi", "anti")
            else "R09"
            if kind == "full"
            else "R08"
            if kind in ("left", "right")
            else "R07"
        )
        self.add("join", fields["join"], rule, naming)
        for item in fields["inputs"]:
            input_fields = doc[item]
            self.add("join_input", input_fields["original"], "R07", naming)
            if input_fields["producer"].kind == "bound_source":
                self.scan(item, input_fields["producer"])
        for item in fields["equalities"]:
            self.add("relationship_equality", doc[item]["original"], "R07", naming)
        if fields["predicate"] is not None:
            self.add(
                "match_condition",
                fields["on"],
                "R07",
                self.node_premises(
                    self.tag(fields["predicate"]), (), "match_condition"
                ),
            )
            self.value(fields["predicate"])
        if kind == "full":
            self.add("full_condition", fields["join"], "R09", naming)
        if fields["membership"] is not None:
            self.add("membership", fields["join"], "R11", naming)
            self.add("correlation", fields["join"], "R11", naming)
            self.add("sentinel", fields["sentinel"], "R11", naming)
            right = doc[fields["inputs"][1]]
            if right["producer"].kind in ("row_result_body", "set_body"):
                self.add("complete_right_terminal", right["original"], "R11", naming)
        for column in fields["columns"]:
            item = doc[column]
            self.add("join_output", item["port"], "R07", naming)
            if item["nulling"]:
                self.add("null_extension", item["port"], "R08", naming)

    def result(self, unit: Ref, naming, encoding) -> None:
        doc = self.doc
        fields = doc[unit]
        if fields["distinct"] is not None:
            distinct = doc[fields["distinct"]]
            self.add("distinct_quotient", distinct["distinct"], "R18", ())
            for field, column in zip(
                distinct["fields"], fields["columns"], strict=True
            ):
                tag = doc[doc[doc[column]["read"]]["realization"]]["tag"]
                self.add(
                    "quotient_field_comparison",
                    field,
                    "R18",
                    encoding if tag == "Text" else (),
                )
        if fields["order"] is not None:
            order = doc[fields["order"]]
            self.add("relation_ordering", order["order"], "R19", ())
            for item in order["items"]:
                entry = doc[item]
                realization = doc[doc[entry["read"]]["realization"]]
                self.add(
                    "order_item",
                    entry["item"],
                    "R19",
                    encoding if realization["tag"] == "Text" else (),
                )
                if realization["nullable"] is not False:
                    self.add("order_null_posture", entry["item"], "R19", ())
        if fields["limit"] is not None:
            self.add("static_limit", doc[fields["limit"]]["limit"], "R21", ())
        if not fields["final"] and (
            fields["order"] is not None or fields["limit"] is not None
        ):
            self.add("inner_result_boundary", fields["boundaries"][0], "R21", naming)
        for column in fields["columns"]:
            self.add("result_terminal_column", doc[column]["output"], "R03", naming)


# -- canonical bytes and immutable view --------------------------------------


def _wire(value: Any) -> Any:
    if type(value) is Ref:
        return [value.kind, value.index]
    if type(value) is PlanRef:
        return {"kind": value.kind, "position": value.position}
    if type(value) is Fixed:
        return {"tag": value.tag, "value": value.wire}
    if type(value) is MappingProxyType:
        return {key: _wire(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_wire(item) for item in value]
    return value


def _canonical(records: dict[Ref, Record], order: list[Ref]) -> bytes:
    document = {
        "format": schema.FORMAT,
        "root": list(schema.ROOT),
        "records": [
            {
                "ref": [ref.kind, ref.index],
                "fields": {k: _wire(v) for k, v in records[ref].fields.items()},
            }
            for ref in order
        ],
    }
    data = schema.canonical_bytes(document)
    _require(
        len(data) <= schema.MAX_DOCUMENT_BYTES, "document size", Status.RESOURCE_LIMIT
    )
    return data


class View:
    """Immutable data view of one consistent private observation."""

    __slots__ = (
        "canonical_bytes",
        "records",
        "order",
        "sql",
        "family",
        "ranges",
        "_plans",
    )

    def __init__(self, records, order, canonical_bytes, plans) -> None:
        doc = _Doc(records)
        artifact = doc[Ref(*schema.ROOT)]
        rendered = doc[artifact["rendered"]]
        ranges = []
        for position, ref in enumerate(
            (*rendered["events"], *rendered["expression_ranges"])
        ):
            event = doc[ref]
            ranges.append(
                Range(
                    position,
                    event["kind"],
                    event["role"],
                    event["subject"],
                    event["start"],
                    event["end"],
                    event["origins"],
                )
            )
        for name, value in (
            ("canonical_bytes", canonical_bytes),
            ("records", MappingProxyType(dict(records))),
            ("order", tuple(order)),
            ("sql", rendered["sql"].encode("utf-8")),
            ("family", doc[artifact["request"]]["family"]),
            ("ranges", tuple(ranges)),
            ("_plans", frozenset(plans)),
        ):
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError("An observation view is immutable.")

    def __repr__(self) -> str:
        return (
            f"View(records=<{len(self.records)}>, sql=<{len(self.sql)} bytes>, "
            f"ranges=<{len(self.ranges)}>)"
        )

    def record(self, ref: Ref) -> Record:
        if type(ref) is not Ref or ref not in self.records:
            raise ValueError("Observation query requires an owned record reference.")
        return self.records[ref]

    def kind(self, kind: str) -> tuple[Record, ...]:
        if type(kind) is not str or kind not in schema.RECORDS:
            raise ValueError("Observation query requires a closed record kind.")
        return tuple(self.records[ref] for ref in self.order if ref.kind == kind)

    def _offset(self, value, name):
        if type(value) is not int or not 0 <= value <= len(self.sql):
            raise ValueError(f"{name} must be an int within [0, len(sql)].")
        return value

    def at(self, offset: int) -> tuple[Range, ...]:
        """Every range with `start <= offset < end`; `len(sql)` has no hit."""
        point = self._offset(offset, "offset")
        return tuple(r for r in self.ranges if r.start <= point < r.end)

    def overlapping(self, start: int, end: int) -> tuple[Range, ...]:
        low, high = self._offset(start, "start"), self._offset(end, "end")
        if high < low:
            raise ValueError("Interval ends before its start.")
        if high == low:
            return ()
        return tuple(r for r in self.ranges if r.start < high and low < r.end)

    def ranges_of(self, reference: PlanRef | Ref) -> tuple[Range, ...]:
        """All ranges of one retained subject, or carrying one retained origin."""
        if (
            type(reference) is Ref
            and reference.kind == "origin"
            and reference in self.records
        ):
            return tuple(r for r in self.ranges if reference in r.origins)
        if type(reference) is PlanRef and reference in self._plans:
            return tuple(r for r in self.ranges if r.subject == reference)
        raise ValueError("Reference is not retained by this observation.")


def evaluate_emission_observation(value: object) -> Outcome:
    """Check an already-parsed builtin mapping; duplicate-key history is not
    recoverable on this route."""
    try:
        _input_tree(value)
        records, order, children, plans = _decode(value)
        _canonical_order(records, order, children)
        _Check(_Doc(records)).run()
        data = _canonical(records, order)
        return Outcome(Status.OK, View(records, order, data, plans), data)
    except _Reject as error:
        return Outcome(error.status, detail=error.detail)
    except (RecursionError, MemoryError):
        return Outcome(Status.RESOURCE_LIMIT, detail="resources")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return Outcome(Status.INVALID_RELATION, detail="inconsistent structure")
