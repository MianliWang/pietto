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
    if carrier["tag"] == "Text":
        if default in {None, "NULL"}:
            return dict(storage), dict(domain)
        if family != "postgres" or not isinstance(default, str):
            return None
        if not (default.startswith("E'") and default.endswith("'")):
            return None
        encoded, octets = default[2:-1], bytearray()
        while encoded:
            if (
                len(encoded) < 4
                or encoded[0] != "\\"
                or any(character not in "01234567" for character in encoded[1:4])
            ):
                return None
            octet = int(encoded[1:4], 8)
            if octet == 0 or octet > 255:
                return None
            octets.append(octet)
            encoded = encoded[4:]
        try:
            width = len(octets.decode("utf-8"))
        except UnicodeDecodeError:
            return None
        if (
            domain.get("kind") != "text"
            or type(domain.get("max_characters")) is not int
        ):
            return None
        result = dict(domain)
        result["max_characters"] = max(result["max_characters"], width)
        return dict(storage), result
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
AGGREGATE_COLUMNS = frozenset({"aggregate_key_column", "aggregate_value_column"})
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
        "rank_scope",
        "rank_carry_scope",
        "rank_partition_scope",
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
        "rank_carry_column",
        "rank_partition_column",
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


def _float_literal(doc, value) -> bool:
    """One direct, possibly signed, Float literal or bound literal value: the
    operand a static Float fold reads (never a let, field or parameter read)."""

    while value.kind == "sql_unary":
        value = doc[value]["operand"]
    if value.kind != "sql_anchor":
        return False
    leaf = doc[value]["operand"]
    fixed = (
        doc[leaf]["value"]
        if leaf.kind == "sql_literal"
        else doc[doc[leaf]["fixed"]]["value"]
        if leaf.kind == "sql_parameter"
        else None
    )
    return fixed is not None and fixed.tag == "Float"


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


def _is_float(realization, family: str) -> bool:
    """The family's finite binary64 carrier."""
    return _is_realization(
        realization,
        "Float",
        {"kind": "pg_float8" if family == "postgres" else "my_double"},
        {"kind": "finite_float", "format": "binary64"},
    )


# Phase77 S06: the MySQL Float comparisons of two row reads that the native
# qualification judged READY, as (shape, place, form), restated from the
# emitter's cell table because this module imports no compiler.
_MYSQL_FLOAT_ROW_CELLS = frozenset(
    {
        *(
            ("same_row", place, form)
            for place in ("select", "where")
            for form in ("==", "!=", "not !=", "same_value", "not same_value")
        ),
        *(
            (kind, key, form)
            for kind, form in (("inner", "=="), ("inner", "not !="), ("left", "=="))
            for key in ("none", "text")
        ),
    }
)
# The fields of each source of a cell as carriers (_mysql_float_carrier) in
# declaration order, restated from the emitter's MYSQL_FLOAT_CELL_TABLES:
# exactly those of the qualification's tables, `f6s` (id, f1, f2) for a
# same-row cell, `f6o` and `f6i` (id, v, kn, kw) for a JOIN cell.
_MYSQL_FLOAT_CELL_TABLES = {
    "same_row": ("int", "float", "float"),
    "inner": ("int", "float", 64, 1000),
    "left": ("int", "float", 64, 1000),
}
# The record kinds a cell's document may hold; any other is never a cell.
_MYSQL_FLOAT_CELL_KINDS = frozenset(
    {
        "artifact",
        "association",
        "bound_field",
        "bound_source",
        "event",
        "generated_requirement",
        "origin",
        "original_requirement",
        "owner",
        "premise",
        "realization",
        "rendered",
        "request",
        "scope_definition",
        "scope_use",
        "sql_symbol",
        "stage_column",
        "terminal_binding",
        "sql_row_query",
        "sql_join_query",
        "row_body",
        "row_scan",
        "row_stage_use",
        "row_join_use",
        "row_value_column",
        "row_carry_column",
        "row_predicate",
        "join_body",
        "join_input",
        "join_column",
        "sql_operation",
        "sql_stage_reference",
    }
)


def _reads_row(doc, value) -> bool:
    """The emitter's row-read test: a field (also inside ANY), captured or
    block read."""
    if value.kind in {
        "sql_stage_reference",
        "sql_any_reference",
        "sql_captured_reference",
        "sql_block_read",
    }:
        return True
    if value.kind == "sql_operation":
        return any(_reads_row(doc, child) for child in doc[value]["operands"])
    if value.kind == "sql_unary":
        return _reads_row(doc, doc[value]["operand"])
    return False


def _mysql_float_carrier(representation):
    """The emitter's mysql_float_cell_carrier, restated: "float" for the
    nullable binary64 DOUBLE, "int" for a non-null BIGINT Int, the width for
    a NOT NULL binary VARCHAR(64) or (1000); else None."""
    try:
        described = _json(representation)
    except _Reject:
        return None
    if type(described) is not dict:
        return None
    if described == {
        "domain": {"format": "binary64", "kind": "finite_float"},
        "nullable": True,
        "storage": {"kind": "my_double"},
    }:
        return "float"
    domain = described.get("domain")
    if (
        described.get("storage") == {"kind": "my_bigint"}
        and described.get("nullable") is False
        and type(domain) is dict
        and domain.get("kind") == "int_range"
    ):
        return "int"
    for width in (64, 1000):
        if described == {
            "domain": {
                "collation": "utf8mb4_0900_bin",
                "encoding": "utf8mb4",
                "kind": "text",
                "max_characters": width,
                "padding": "NO PAD",
            },
            "nullable": False,
            "storage": {"kind": "my_varchar", "length": width},
        }:
            return width
    return None


def _mysql_float_read(doc, value):
    """(carrier, source, stage column) of a reference that reads a source field
    directly, its carrier from _mysql_float_carrier; None otherwise."""
    if value.kind != "sql_stage_reference":
        return None
    stage = doc[doc[value]["column"]]
    owners = tuple(
        ref for ref in doc.all("bound_source") if stage["field"] in doc[ref]["fields"]
    )
    if (
        stage["field"] is None
        or stage["source_port"] is None
        or stage["literal"] is not None
        or stage["aggregate"] is not None
        or stage["window"] is not None
        or len(owners) != 1
    ):
        return None
    carrier = _mysql_float_carrier(doc[stage["field"]]["representation"])
    return carrier, owners[0], doc[value]["column"]


def _mysql_float_cell(doc, ref):
    """The cell of the MySQL Float comparison or `same_value` call ``ref``
    from the document's own structure, as emission derives it from its plan:
    one source under a projection, or under a WHERE and a projection, the
    tree the whole WHERE or one SELECT item's whole value; or one INNER or
    LEFT JOIN of two bound sources of different tables under one projection,
    the tree its whole ON or, before `and`, one `==` of two Text keys. The
    tree is ``ref`` or `not` over it; its operands read different qualified
    Float fields (one of each JOIN input), the keys qualified keys of one
    width of different inputs, every other SELECT item a non-null BIGINT Int
    (also a qualified Float beside a WHERE or a JOIN), each source the
    fields of a qualification table (_MYSQL_FLOAT_CELL_TABLES); the document
    holds no other operation or record kind. None outside every cell. A
    relation alias `let`, an unused named window or an inlined `def`, which
    emission refuses, changes the document only in source positions and
    source bytes, so this reader cannot tell it from the direct program."""
    operations = doc.all("sql_operation")
    artifacts = doc.all("artifact")
    if (
        not set(doc.kinds) <= _MYSQL_FLOAT_CELL_KINDS
        or len(operations) > 4
        or len(artifacts) != 1
    ):
        return None

    def operation(value, kind, operator, count):
        found = value.kind == "sql_operation" and (
            doc[value]["kind"],
            doc[value]["operator"],
            len(doc[value]["operands"]),
        ) == (kind, operator, count)
        return doc[value]["operands"] if found else None

    ast, keys, inputs = doc[artifacts[0]]["ast"], (), None
    if ast.kind == "sql_join_query":
        units = doc[ast]["units"]
        if [unit.kind for unit in units] != ["join_body", "row_body"]:
            return None
        join, body = doc[units[0]], doc[units[1]]
        inputs = join["inputs"]
        producers = tuple(doc[item]["producer"] for item in inputs)
        if (
            join["join_kind"] not in ("inner", "left")
            or join["equalities"]
            or len(inputs) != 2
            or any(item.kind != "bound_source" for item in producers)
            or len({(doc[s]["namespace"], doc[s]["name"]) for s in producers}) != 2
            or body["scan"].kind != "row_join_use"
            or doc[body["scan"]]["body"] != units[0]
        ):
            return None
        root, place = join["predicate"], "none"
        if root is None:
            return None
        sides = operation(root, "logical", "and", 2)
        if sides is not None:
            root, key = sides
            keys, place = operation(key, "comparison", "==", 2), "text"
            if keys is None:
                return None
        shape = (join["join_kind"], place)
        selected = tuple(doc[column]["value"] for column in body["columns"])
        sources = producers
    elif ast.kind == "sql_row_query":
        bodies = doc[ast]["bodies"]
        if (
            len(bodies) not in (1, 2)
            or doc[bodies[0]]["scan"].kind != "row_scan"
            or doc[doc[bodies[0]]["scan"]]["realization"].kind != "bound_source"
        ):
            return None
        body = doc[bodies[-1]]
        values = tuple(doc[column]["value"] for column in body["columns"])
        if len(bodies) == 2:
            where = doc[bodies[0]]
            if (
                where["block_kind"] != "where"
                or where["predicate"] is None
                or body["scan"].kind != "row_stage_use"
                or doc[body["scan"]]["body"] != bodies[0]
            ):
                return None
            root, place, selected = doc[where["predicate"]]["value"], "where", values
        else:
            trees = tuple(value for value in values if value.kind == "sql_operation")
            if len(trees) != 1:
                return None
            root, place = trees[0], "select"
            selected = tuple(value for value in values if value.kind != "sql_operation")
        shape = ("same_row", place)
        sources = (doc[doc[bodies[0]]["scan"]]["realization"],)
    else:
        return None
    if body["block_kind"] != "projection" or body["predicate"] is not None:
        return None
    inner = operation(root, "not", "not", 1)
    node = root if inner is None else inner[0]
    if node != ref:
        return None
    operands = doc[node]["operands"]
    form = {
        ("comparison", "=="): "==",
        ("comparison", "!="): "!=",
        ("scalar_call", "same_value"): "same_value",
    }.get((doc[node]["kind"], doc[node]["operator"]))
    negated = inner is not None
    if (
        form is None
        or len(operands) != 2
        or len(operations) != 1 + negated + 2 * bool(keys)
    ):
        return None
    found = tuple(
        _mysql_float_read(doc, value) for value in (*operands, *keys, *selected)
    )
    reads = tuple(item for item in found if item is not None)
    if len(reads) != len(found):
        return None
    carriers = tuple(carrier for carrier, _, _ in reads)
    owners = tuple(owner for _, owner, _ in reads)
    cell = (*shape, "not " + form if negated else form)
    allowed = ("int",) if shape[1] == "select" else ("int", "float")
    if (
        any(
            tuple(
                _mysql_float_carrier(doc[field]["representation"])
                for field in doc[source]["fields"]
            )
            != _MYSQL_FLOAT_CELL_TABLES[shape[0]]
            for source in sources
        )
        or carriers[:2] != ("float", "float")
        or doc[reads[0][2]]["source_port"] == doc[reads[1][2]]["source_port"]
        or any(carrier not in allowed for carrier in carriers[2 + len(keys) :])
        or inputs is not None
        and any(
            # The ON reads each JOIN input's own scan columns, one per input.
            not any(
                doc[item]["producer"] == owner and column in doc[item]["columns"]
                for item in inputs
            )
            for _, owner, column in reads[: 2 + len(keys)]
        )
        or inputs is not None
        and owners[0] == owners[1]
        or keys
        and (
            carriers[2] != carriers[3]
            or carriers[2] not in (64, 1000)
            or owners[2] == owners[3]
        )
    ):
        return None
    return cell


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


# The MySQL project cells of lpad and now(), as emission's MYSQL_SCALAR_CELLS
# (project_sql_emission_rows) lists them; _mysql_scalar_cells derives each
# call's cell from the document alone.
_MYSQL_SCALAR_CELLS = frozenset(
    {
        ("lpad", "select", ("field", "literal", "literal")),
        ("lpad", "select", ("literal", "literal", "literal")),
        ("now", "select", ()),
        ("now", "select_date_of", ()),
    }
)


def _mysql_operand_kind(doc, ref) -> str:
    """The kind of one operand, as emission's mysql_operand_kind gives it."""

    if ref.kind == "sql_anchor":
        return "literal" if doc[ref]["operand"].kind == "sql_literal" else "other"
    if ref.kind != "sql_stage_reference":
        return "other"
    column = doc[doc[ref]["column"]]
    return (
        "field"
        if getattr(column["terminal"], "kind", None) in ("source_port", "stage_port")
        and column["field"] is not None
        and column["source_port"] is not None
        and column["literal"] is None
        and column["aggregate"] is None
        and column["window"] is None
        else "other"
    )


def _mysql_stage(body) -> str | None:
    """A row body's stage from what it renders, not its label or stage
    fields: a predicate makes a where, window columns a window, neither a
    let (or a projection); aggregate columns, or both, make none."""

    kinds = {column.kind for column in body["columns"]}
    if not kinds.isdisjoint(AGGREGATE_COLUMNS):
        return None
    windowed = "window_column" in kinds
    if body["predicate"] is None:
        return "window" if windowed else "let"
    return None if windowed else "where"


def _mysql_body_chain(doc, ref, order) -> int | None:
    """How many row bodies lead from ``ref`` down its stage uses to a source
    scan, each below ``ref`` a stage of ``order`` by its structure, labelled
    so, and in that order: each once at most, a let repeated. None when they
    do not. A QUALIFY body is a where over its window, so it is out of order
    whatever its label."""

    seen, scan = {ref}, doc[ref]["scan"]
    while scan.kind == "row_stage_use":
        inner = doc[scan]["body"]
        stage = _mysql_stage(doc[inner])
        if inner in seen or stage not in order or doc[inner]["block_kind"] != stage:
            return None
        order = order[order.index(stage) + (stage != "let") :]
        seen.add(inner)
        scan = doc[inner]["scan"]
    return len(seen) if scan.kind == "row_scan" else None


def _mysql_capture_read(doc, read, final, whole) -> bool:
    """Q4 from the document: ``read`` is a scalar read and the whole value of
    a column of the ``final`` body (``whole``), which scans its source
    directly, beside a captured reference; the read's target is the capturing
    let's projection body, over one WHERE body of it at most, then a source
    scan, each body a stage by its structure (_mysql_stage); and the document
    holds no other body."""

    producer = doc[doc[read]["target"]]["producer"]
    if (
        doc[read]["kind"] != "scalar"
        or not doc.all("sql_captured_reference")
        or doc[final]["scan"].kind != "row_scan"
        or producer.kind != "row_body"
        or doc[producer]["final"] is not False
        or doc[producer]["block_kind"] != "projection"
        or _mysql_stage(doc[producer]) != "let"
        or doc.all("row_result_body")
        or doc.all("join_body")
        or doc.all("set_body")
        or read not in whole
    ):
        return False
    count = _mysql_body_chain(doc, producer, ("where",))
    return count is not None and len(doc.all("row_body")) == 1 + count


def _mysql_scalar_cells(doc) -> dict:
    """The cell of each MySQL lpad and now() operation, keyed by operation, as
    emission's mysql_scalar_cell derives it from the plan.

    Q1: the operation is the whole value of a column of the final projection
    body, or the one operand of a `date_of` that is, and no other record
    names the column, the value or that operand: records may share one,
    which a SELECT item never does. Q2: that body has no predicate or
    window, and below it are, in emission's order, a window body at most, a
    WHERE body at most and let bodies, then a source scan; each body's stage
    comes from its structure and its label must agree (_mysql_body_chain),
    and no body aggregates. Q3: no
    parameter, native use or fixed value. Q4: no ANY read and at most one
    block read, as _mysql_capture_read admits.
    """

    cells: dict = {}
    reads = doc.all("sql_block_read")
    if (
        doc.all("sql_parameter")
        or doc.all("native_use")
        or doc.all("fixed_value")
        or doc.all("aggregate_stage")
        or doc.all("sql_any_read")
        or len(reads) > 1
    ):
        return cells
    named: dict[Ref, int] = {}
    for record in doc.records.values():
        pending = list(record.fields.values())
        while pending:
            item = pending.pop()
            if type(item) is tuple:
                pending.extend(item)
            elif type(item) is Ref:
                named[item] = named.get(item, 0) + 1
    for body_ref in doc.all("row_body"):
        body = doc[body_ref]
        if (
            body["final"] is not True
            or body["block_kind"] != "projection"
            or _mysql_stage(body) != "let"
            or _mysql_body_chain(doc, body_ref, ("window", "where", "let")) is None
        ):
            continue
        whole = [
            doc[column]["value"]
            for column in body["columns"]
            if column.kind == "row_value_column"
            and named.get(column) == 1
            and named.get(doc[column]["value"]) == 1
        ]
        if reads and not _mysql_capture_read(doc, reads[0], body_ref, whole):
            continue
        for value in whole:
            if value.kind != "sql_operation" or doc[value]["kind"] != "scalar_call":
                continue
            op = doc[value]
            if op["operator"] in ("lpad", "now"):
                cells[value] = (
                    op["operator"],
                    "select",
                    tuple(_mysql_operand_kind(doc, item) for item in op["operands"]),
                )
            elif (
                op["operator"] == "date_of"
                and len(op["operands"]) == 1
                and op["operands"][0].kind == "sql_operation"
                and doc[op["operands"][0]]["kind"] == "scalar_call"
                and doc[op["operands"][0]]["operator"] == "now"
                and named.get(op["operands"][0]) == 1
            ):
                cells[op["operands"][0]] = ("now", "select_date_of", ())
    return cells


def _is_text_input(realization, family: str) -> bool:
    """One ordered Text value of the family's comparison profile."""

    if family == "postgres":
        return _is_pg_text_input(realization)
    return (
        realization is not None
        and realization["tag"] == "Text"
        and _is_key_value(realization, family)
    )


def _is_text_value(doc, value, family: str) -> bool:
    """A row Text carrier or one anchored Text literal of the family."""

    realization = _value_realization(doc, value)
    if realization is not None:
        return _is_text_input(realization, family)
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
        and anchor["physical_type"]
        == {"postgres": "pg_text", "mysql": "my_utf8mb4_text"}[family]
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
# A PostgreSQL sum, avg, variance or deviation of a Float: the target refuses
# an overflowing binary64 accumulation with SQLSTATE 22003, so a result is
# finite.
_TARGET_CHECKED_BINARY64 = "target_checked_binary64_overflow"
_TARGET_CHECKED_DECIMAL = "target_checked_decimal_overflow"
# The sample and population variances and deviations.
_SPREAD_FUNCTIONS = frozenset({"stddev", "variance", "pvariance", "pstdev"})
# Phase77 S05: their MySQL spellings, uncast and without SQRT, only in the
# cell _mysql_spread_cell derives, as emission's MYSQL_SPREAD_SPELLING.
_MYSQL_SPREAD_SPELLING = {
    "stddev": "STDDEV_SAMP",
    "variance": "VAR_SAMP",
    "pvariance": "VAR_POP",
    "pstdev": "STDDEV_POP",
}
# The document kinds that may stand in that cell; any other kind leaves it.
_SPREAD_CELL_KINDS = frozenset(
    {
        "aggregate_origin",
        "aggregate_projection_column",
        "aggregate_stage",
        "aggregate_value_column",
        "artifact",
        "association",
        "bound_field",
        "bound_source",
        "event",
        "generated_requirement",
        "origin",
        "original_requirement",
        "owner",
        "premise",
        "realization",
        "rendered",
        "request",
        "row_body",
        "row_scan",
        "row_stage_use",
        "scope_definition",
        "scope_use",
        "sql_row_query",
        "sql_stage_reference",
        "sql_symbol",
        "stage_column",
        "terminal_binding",
    }
)
# Kinds the cell holds exactly once (and two row bodies).
_SPREAD_CELL_ONCE = (
    "sql_row_query",
    "row_scan",
    "row_stage_use",
    "aggregate_stage",
    "aggregate_value_column",
    "aggregate_projection_column",
    "sql_stage_reference",
)


def _mysql_spread_cell(doc):
    """The one aggregate_value_column in the S05 cell, from the document
    alone, as emission's mysql_spread_cell derives it from the plan, or None.

    The document holds no kind outside _SPREAD_CELL_KINDS (no parameter,
    native use, fixed value, literal, operation, block or ANY read, JOIN,
    set, result or window record), each kind of _SPREAD_CELL_ONCE once and
    two row bodies, which are the query's. The final body is the one that
    scans the stage use: a projection without predicate or window whose one
    column reads the aggregate value's result. The body that stage use reads
    is the aggregate body over the source scan, without predicate or window,
    whose one column is that value, and its global stage has no key and that
    one value. The value is a variance or deviation without order, delimiter,
    extra argument or DISTINCT, and its argument reads a source field
    directly. Bodies are found by these links, never by order or by the
    `final` flag alone. The document records neither a relation `let` (`let
    x = t`, read through `from x` or not) nor an unread header parameter, so
    this reader cannot refuse either; the emitter and the live verifier
    refuse both, and the compiled readers a header parameter."""

    kinds = doc.kinds
    if (
        any(kind not in _SPREAD_CELL_KINDS for kind in kinds)
        or any(len(doc.all(kind)) != 1 for kind in _SPREAD_CELL_ONCE)
        or len(doc.all("row_body")) != 2
    ):
        return None
    ((query,), (scan,), (use,), (stage,), (value,), (selected,), _) = (
        doc.all(kind) for kind in _SPREAD_CELL_ONCE
    )
    bodies = tuple(doc[query]["bodies"])
    finals = [body for body in bodies if doc[body]["scan"] == use]
    inner = doc[use]["body"]
    if (
        sorted(bodies) != sorted(doc.all("row_body"))
        or len(finals) != 1
        or inner not in bodies
        or inner == finals[0]
    ):
        return None
    final, aggregate, column = doc[finals[0]], doc[inner], doc[value]
    argument = column["argument"]
    if (
        final["final"] is not True
        or final["block_kind"] != "projection"
        or final["aggregation"] is not None
        or final["predicate"] is not None
        or final["window"] is not None
        or tuple(final["columns"]) != (selected,)
        or aggregate["final"] is not False
        or aggregate["block_kind"] != "aggregate"
        or aggregate["scan"] != scan
        or aggregate["aggregation"] != stage
        or aggregate["predicate"] is not None
        or aggregate["window"] is not None
        or tuple(aggregate["columns"]) != (value,)
        or doc[stage]["mode"] != "global"
        or tuple(doc[stage]["keys"])
        or tuple(doc[stage]["values"]) != (value,)
        or column["function"] not in _SPREAD_FUNCTIONS
        or column["distinct"]
        or column["delimiter"] is not None
        or tuple(column["order_by"])
        or tuple(column["extra_arguments"])
        or argument is None
        or argument.kind != "sql_stage_reference"
        or doc[doc[selected]["read"]]["terminal"] != column["export"]
    ):
        return None
    read = doc[doc[argument]["column"]]
    if (
        getattr(read["terminal"], "kind", None) != "source_port"
        or read["field"] is None
        or read["source_port"] is None
        or read["literal"] is not None
        or read["aggregate"] is not None
        or read["window"] is not None
    ):
        return None
    return value


def _aggregate_casts(
    family: str, function: str, argument_tag: str | None
) -> tuple[str | None, str | None]:
    """The reviewed argument and result casts of one aggregate: AVG(Int)
    averages binary64, PostgreSQL SUM(Int) is bigint before and after, and a
    PostgreSQL VAR_SAMP or VAR_POP is cast to float8 once. A PostgreSQL SUM or
    AVG of a float8 is already binary64."""
    if function in {"avg", "sum"} and argument_tag == "Float":
        return None, None
    if function == "filtered_sum":
        function = "sum"
    if function == "avg":
        return ("pg_catalog.float8" if family == "postgres" else "DOUBLE"), None
    if function == "sum":
        return "pg_catalog.int8", "pg_catalog.int8"
    if function in _SPREAD_FUNCTIONS:
        return None, ("pg_catalog.float8" if family == "postgres" else None)
    if function in {"median", "quantile"}:
        # PERCENTILE_CONT orders by the float8 image of each Int value.
        return "pg_catalog.float8", None
    return None, None


def _decimal_sum_cast(family: str, function: str, argument, result) -> str | None:
    """The E10 result cast is derived from two retained Decimal carriers."""

    if family != "postgres" or function != "sum":
        return None
    parameters = _pg_decimal_parameters(argument)
    if parameters is None:
        return None
    precision, scale = parameters
    if (
        not 1 <= precision <= 46
        or scale > 30
        or _pg_decimal_parameters(result) != (precision + 19, scale)
        or result["nullable"] is not True
    ):
        return None
    return f"pg_catalog.numeric({precision + 19}, {scale})"


def _aggregate_evidence(function: str, argument_tag: str | None) -> tuple[str, ...]:
    """R13 evidence from the function and its argument tag, never a cast."""
    if function in {"sum", "filtered_sum"} and argument_tag == "Int":
        return (_TARGET_CHECKED,)
    if function == "sum" and argument_tag == "Decimal":
        return (_TARGET_CHECKED_DECIMAL,)
    if function in {"sum", "avg", *_SPREAD_FUNCTIONS} and argument_tag == "Float":
        return (_TARGET_CHECKED_BINARY64,)
    return ()


def _is_pg_order_value(realization) -> bool:
    """The closed PostgreSQL aggregate-order carrier domain; a Float, finite
    or a window distribution result, orders by real value (E6)."""

    if realization is None:
        return False
    if realization["tag"] == "Float":
        return _is_pg_float(realization) or _is_realization(
            realization, "Float", {"kind": "pg_float8"}, {"kind": "float64"}
        )
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


def _is_key_value(realization, family: str) -> bool:
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
    if tag == "UUID":
        return _is_realization(
            realization,
            "UUID",
            {"kind": "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        )
    return False


# The record kinds a ranked MySQL `first`/`last` document may hold
# (_ranked_stage): one row query over a source, a WHERE body of bare carries
# at most, its aggregation, projection and ordered result, nothing else.
_RANKED_KINDS = frozenset(
    {
        "aggregate_key_column",
        "aggregate_order_item",
        "aggregate_origin",
        "aggregate_projection_column",
        "aggregate_stage",
        "aggregate_value_column",
        "artifact",
        "association",
        "bound_field",
        "bound_source",
        "event",
        "generated_requirement",
        "origin",
        "original_requirement",
        "owner",
        "premise",
        "realization",
        "rendered",
        "request",
        "result_column",
        "result_order",
        "result_order_item",
        "result_stage",
        "row_body",
        "row_carry_column",
        "row_predicate",
        "row_result_body",
        "row_result_use",
        "row_scan",
        "row_stage_use",
        "scope_definition",
        "scope_use",
        "sql_operation",
        "sql_row_query",
        "sql_stage_reference",
        "sql_symbol",
        "stage_column",
        "terminal_binding",
    }
)
# The token roles only a ranked derived table and its MAX(CASE ...) carry.
_RANK_ROLES = frozenset(
    {
        "rank_open",
        "rank_separator",
        "rank_carry_scope",
        "rank_carry_qualifier",
        "rank_carry_column",
        "rank_close",
        "rank_scope",
        "rank_column",
        "rank_label",
        "rank_partition_scope",
        "rank_partition_column",
        "aggregate_rank_open",
        "aggregate_rank_qualifier",
        "aggregate_rank_then",
        "aggregate_rank_close",
        "aggregate_rank_window",
        "aggregate_rank_partition",
        "aggregate_rank_partition_qualifier",
        "aggregate_rank_spec_separator",
        "aggregate_rank_order",
        "aggregate_rank_separator",
        "aggregate_rank_alias",
    }
)


def _is_my_bigint(realization) -> bool:
    return (
        realization is not None
        and realization["tag"] == "Int"
        and dict(realization["storage"]) == {"kind": "my_bigint"}
        and _is_key_value(realization, "mysql")
    )


def _is_my_varchar(realization) -> bool:
    """A binary VARCHAR of a length the S13 qualification used, 32 or 64."""
    length = None if realization is None else realization["storage"].get("length")
    return (
        realization is not None
        and realization["tag"] == "Text"
        and realization["storage"].get("kind") == "my_varchar"
        and type(length) is int
        and length in (32, 64)
        and _is_key_value(realization, "mysql")
    )


def _is_ranked_value(realization) -> bool:
    """A carrier the S13 qualification saw MySQL MAX(CASE ...) keep, as
    emission's ranked_value: a nullable BIGINT, DOUBLE, binary VARCHAR(32) or
    VARCHAR(64), or DECIMAL(65,30)."""
    return (
        realization is not None
        and realization["nullable"] is True
        and (
            _is_my_bigint(realization)
            or _is_float(realization, "mysql")
            or _is_my_varchar(realization)
            or realization["tag"] == "Decimal"
            and dict(realization["storage"])
            == {"kind": "my_decimal", "precision": 65, "scale": 30}
            and _is_key_value(realization, "mysql")
        )
    )


def _is_ranked_key(realization, *, group=False) -> bool:
    """A ROW_NUMBER order key, as emission's ranked_key: a BIGINT or a
    nullable binary VARCHAR; a PARTITION BY key is a non-null BIGINT."""
    if group:
        return _is_my_bigint(realization) and realization["nullable"] is False
    return _is_my_bigint(realization) or (
        _is_my_varchar(realization) and realization["nullable"] is True
    )


def _ranked_doc_filter(doc, ref, seen):
    """A WHERE of the S13 class with no header parameter, each operation named
    once: the source ports of its `and` of `f is not None` tests, each of a
    nullable field, in order, or None."""
    if ref in seen or ref.kind != "sql_operation":
        return None
    seen.add(ref)
    node = doc[ref]
    operands = node["operands"]
    if (node["kind"], node["operator"]) == ("logical", "and"):
        if len(operands) != 2:
            return None
        left, right = (_ranked_doc_filter(doc, operand, seen) for operand in operands)
        return None if left is None or right is None else left + right
    if (
        (node["kind"], node["operator"]) != ("null_test", "is not null")
        or len(operands) != 1
        or operands[0].kind != "sql_stage_reference"
        or doc[doc[operands[0]]["realization"]]["nullable"] is not True
    ):
        return None
    return [doc[doc[operands[0]]["column"]]["source_port"]]


def _ranked_stage(doc, family):
    """Emission's ranked_statement and ranked_inputs from the document alone:
    the one aggregate stage of a MySQL statement of the S13 class, or None.

    The row query's bodies are, in order, a WHERE body at most, the
    aggregation body and its projection, and by a key the result body. Each
    body's stage comes from its structure (predicate, aggregation, window)
    and its label must agree. The WHERE body carries bare columns over the
    source scan under `_ranked_doc_filter`, whose tests each read another
    order key of a `first` or `last`; a document holds no header parameter,
    nor a relation alias, which reads as the source it names. The
    aggregation body scans it or
    the source, computes `first` and `last` only, GLOBAL or by one non-null
    BIGINT key, of `_is_ranked_value` arguments, all in one order of
    `_is_ranked_key` keys and directions; the projection reads its outputs in
    order and, by a key, the key once more, the one ascending order item of
    the result body, which has no DISTINCT or LIMIT. No other record kind is
    present."""
    if family != "mysql" or {ref.kind for ref in doc.records} - _RANKED_KINDS:
        return None
    stages = doc.all("aggregate_stage")
    query = doc[Ref(*schema.ROOT)]["ast"]
    if len(stages) != 1 or query.kind != "sql_row_query":
        return None
    stage_ref, bodies = stages[0], doc[query]["bodies"]
    stage = doc[stage_ref]
    keys, values = stage["keys"], stage["values"]
    rows = [body for body in bodies if body.kind == "row_body"]
    results = [body for body in bodies if body.kind == "row_result_body"]
    if (
        len(set(bodies)) != len(bodies)
        or list(bodies) != rows + results
        or len(rows) not in (2, 3)
        or len(results) != bool(keys)
        or len(keys) > 1
        or not values
        or stage["mode"] != ("grouped" if keys else "global")
    ):
        return None
    *lower, aggregating, projecting = rows
    body, projection = doc[aggregating], doc[projecting]
    scan = body["scan"]
    if (
        body["aggregation"] != stage_ref
        or (body["block_kind"], body["predicate"], body["window"], body["final"])
        != ("aggregate", None, None, False)
        or list(body["columns"]) != [*keys, *values]
        or (
            projection["block_kind"],
            projection["aggregation"],
            projection["predicate"],
            projection["window"],
        )
        != ("projection", None, None, None)
        or projection["scan"].kind != "row_stage_use"
        or doc[projection["scan"]]["body"] != aggregating
    ):
        return None
    seen: set = set()
    tested: list = []
    if lower:
        where = doc[lower[0]]
        if (
            scan.kind != "row_stage_use"
            or doc[scan]["body"] != lower[0]
            or (where["block_kind"], where["aggregation"], where["window"])
            != ("where", None, None)
            or where["predicate"] is None
            or where["final"] is not False
            or where["scan"].kind != "row_scan"
            or any(column.kind != "row_carry_column" for column in where["columns"])
        ):
            return None
        tested = _ranked_doc_filter(doc, doc[where["predicate"]]["value"], seen)
        if tested is None:
            return None
    elif scan.kind != "row_scan":
        return None
    if len(seen) != len(doc.all("sql_operation")):
        return None
    projected = list(projection["columns"][: len(keys) + len(values)])
    extra = projection["columns"][len(projected) :]
    if len(projected) != len(keys) + len(values) or any(
        column.kind != "aggregate_projection_column"
        or doc[doc[column]["read"]]["aggregate"] != doc[doc[own]["column"]]["aggregate"]
        for column, own in zip(projected, [*keys, *values])
    ):
        return None
    if keys:
        origin = doc[doc[keys[0]]["column"]]["aggregate"]
        result = doc[results[0]]
        order = None if result["order"] is None else doc[result["order"]]
        if (
            projection["final"] is not False
            or len(extra) != 1
            or extra[0].kind != "row_carry_column"
            or doc[doc[extra[0]]["read"]]["aggregate"] != origin
            or doc[result["scan"]]["body"] != projecting
            or result["distinct"] is not None
            or result["limit"] is not None
            or result["final"] is not True
            or len(result["columns"]) != len(projected)
            or order is None
            or len(order["items"]) != 1
            or doc[order["items"][0]]["direction"] != "asc"
            or doc[order["items"][0]]["nulls"] is not None
            or doc[order["items"][0]]["read"] != doc[extra[0]]["column"]
            or not _is_ranked_key(
                doc[doc[doc[keys[0]]["read"]]["realization"]], group=True
            )
        ):
            return None
    elif projection["final"] is not True or extra:
        return None
    for value in values:
        column = doc[value]
        if (
            column["function"] not in ("first", "last")
            or column["argument"] is None
            or column["argument"].kind != "sql_stage_reference"
            or column["delimiter"] is not None
            or column["extra_arguments"]
            or not column["order_by"]
            or not _is_ranked_value(_value_realization(doc, column["argument"]))
            or not all(
                _is_ranked_key(_value_realization(doc, doc[item]["value"]))
                for item in column["order_by"]
            )
        ):
            return None
    # One key list for every call; each `is not None` tests a distinct key.
    lists = {
        tuple(
            (
                doc[doc[doc[item]["value"]]["column"]]["source_port"]
                if doc[item]["value"].kind == "sql_stage_reference"
                else item,
                doc[item]["direction"],
            )
            for item in doc[value]["order_by"]
        )
        for value in values
    }
    order = {port for fields in lists for port, _ in fields}
    if (
        len(lists) != 1
        or len(set(tested)) != len(tested)
        or not order.issuperset(tested)
    ):
        return None
    return stage_ref


def _ranked_layout(doc, stage_ref):
    """Emission's ranked_layout from the document: the derived table's read
    column names, keys first, each once, and each `first` or `last`'s
    ROW_NUMBER name by its aggregate, `r<ordinal>` lengthened by `_` past
    every read name that is not ASCII, then while it is an ASCII read name
    without case."""
    stage = doc[stage_ref]
    listed: list[str] = []
    for name in [doc[doc[key]["read"]]["name"] for key in stage["keys"]] + [
        doc[doc[doc[value]["argument"]]["column"]]["name"] for value in stage["values"]
    ]:
        if name not in listed:
            listed.append(name)
    folded = {name.casefold() for name in listed if name.isascii()}
    longest = max((len(name) for name in listed if not name.isascii()), default=0)
    names = {}
    for value in stage["values"]:
        column = doc[value]
        name = "r" + str(column["ordinal"])
        name += "_" * max(0, longest + 1 - len(name))
        while name.casefold() in folded:
            name += "_"
        names[column["aggregate"]] = name
    return listed, names


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
        self.ranked = None

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
        # A body names a window or aggregation stage exactly when it renders
        # one: window columns, or aggregate key or value columns.
        for ref in doc.all("row_body"):
            body = doc[ref]
            kinds = {column.kind for column in body["columns"]}
            _require(
                (body["window"] is not None) is ("window_column" in kinds)
                and (body["aggregation"] is not None)
                is not kinds.isdisjoint(AGGREGATE_COLUMNS),
                "stage columns",
            )
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
        cells = _mysql_scalar_cells(doc) if family == "mysql" else {}
        for ref in doc.all("sql_operation"):
            op = doc[ref]
            _require(op["kind"] in schema.OPERATORS, "operation kind")
            _require(
                op["operator"] in schema.OPERATORS[op["kind"]], "operation operator"
            )
            result = doc[op["realization"]]
            if (
                family == "mysql"
                and (op["kind"], op["operator"])
                in {
                    ("comparison", "=="),
                    ("comparison", "!="),
                    ("scalar_call", "same_value"),
                }
                and len(op["operands"]) == 2
                and all(_value_tag(doc, child) == "Float" for child in op["operands"])
                and all(_reads_row(doc, child) for child in op["operands"])
            ):
                # Phase77 S06: MySQL picks its own join and semijoin plans for a
                # Float equality of two row reads; only a qualified cell emits.
                _require(
                    _mysql_float_cell(doc, ref) in _MYSQL_FLOAT_ROW_CELLS,
                    "MySQL Float row comparison cell",
                )
            if family == "postgres" and result["tag"] == "Decimal":
                operands = tuple(
                    _value_realization(doc, child) for child in op["operands"]
                )
                if op["kind"] == "arithmetic":
                    _require(
                        len(operands) == 2 and op["operator"] in {"+", "-", "*"},
                        "Decimal arithmetic operator",
                    )
                    parameters = []
                    for child, operand in zip(op["operands"], operands, strict=True):
                        decimal = _pg_decimal_parameters(operand)
                        if decimal is not None:
                            parameters.append(decimal)
                        else:
                            _require(_is_pg_int(operand), "Decimal arithmetic operand")
                            literal = _literal_int(doc, child)
                            parameters.append(
                                (
                                    max(1, len(str(abs(literal))))
                                    if literal is not None
                                    else {16: 5, 32: 10, 64: 19}[
                                        _SIGNED_STORAGE_BITS[operand["storage"]["kind"]]
                                    ],
                                    0,
                                )
                            )
                    (lp, ls), (rp, rs) = parameters
                    if op["operator"] in {"+", "-"}:
                        scale = max(ls, rs)
                        precision = max(lp - ls, rp - rs) + 1 + scale
                    elif {operand["tag"] for operand in operands} == {"Decimal", "Int"}:
                        precision, scale = (
                            parameters[0]
                            if operands[0]["tag"] == "Decimal"
                            else parameters[1]
                        )
                        precision += 19
                    else:
                        precision, scale = lp + rp, ls + rs
                    _require(
                        1 <= precision <= 65
                        and 0 <= scale <= min(precision, 30)
                        and _pg_decimal_parameters(result) == (precision, scale)
                        and result["nullable"] == "unknown",
                        "Decimal arithmetic carrier",
                    )
                elif (
                    op["kind"] == "sign"
                    or op["kind"] == "scalar_call"
                    and op["operator"] == "abs"
                ):
                    _require(
                        len(operands) == 1
                        and _pg_decimal_parameters(operands[0]) is not None
                        and _pg_decimal_parameters(result)
                        == _pg_decimal_parameters(operands[0])
                        and result["nullable"] == operands[0]["nullable"],
                        "Decimal unary carrier",
                    )
                elif op["kind"] == "scalar_call" and op["operator"] in {
                    "coalesce",
                    "nullif",
                }:
                    nullabilities = tuple(
                        True if child.kind == "sql_null" else operand["nullable"]
                        for child, operand in zip(op["operands"], operands, strict=True)
                    )
                    nullable = (
                        (True if nullabilities[0] is False else nullabilities[0])
                        if op["operator"] == "nullif"
                        else False
                        if any(value is False for value in nullabilities)
                        else "unknown"
                        if "unknown" in nullabilities
                        else True
                    )
                    carriers = tuple(
                        _pg_decimal_parameters(operand)
                        for operand in operands
                        if operand is not None
                        and operand["storage"].get("kind") != "typed_null"
                    )
                    _require(
                        bool(carriers)
                        and carriers[0] is not None
                        and all(carrier == carriers[0] for carrier in carriers)
                        and _pg_decimal_parameters(result) == carriers[0]
                        and result["nullable"] == nullable,
                        "Decimal scalar carrier",
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
            if op["kind"] == "scalar_call" and op["operator"] == "now":
                _require(
                    family in {"postgres", "mysql"}
                    and _is_realization(
                        doc[op["realization"]],
                        "Timestamp",
                        {
                            "kind": "pg_timestamp"
                            if family == "postgres"
                            else "my_datetime",
                            "fractional_seconds": 6,
                        },
                        {"kind": "timestamp"},
                    )
                    and doc[op["realization"]]["nullable"] is False,
                    "now result carrier",
                )
                _require(
                    family != "mysql" or cells.get(ref) in _MYSQL_SCALAR_CELLS,
                    "mysql scalar cell",
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
                    "same_value": {2},
                    "lpad": {3},
                    "add_months": {2},
                    "now": {0},
                }
                count = len(op["operands"])
                _require(
                    count >= 2
                    if op["operator"] in {"coalesce", "concat"}
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
            elif op["kind"] == "scalar_call" and op["operator"] == "concat":
                _require(family == "postgres", "concat family")
            elif op["kind"] == "scalar_call" and op["operator"] == "lpad":
                fill = _literal_text(doc, operands[2])
                width = _literal_int(doc, operands[1])
                _require(
                    family in {"postgres", "mysql"}
                    and _is_text_value(doc, operands[0], family)
                    and _value_tag(doc, operands[1]) == "Int"
                    and type(fill) is str
                    and len(fill) == 1
                    and _is_text_input(result, family),
                    "lpad realization",
                )
                _require(
                    family != "mysql" or cells.get(ref) in _MYSQL_SCALAR_CELLS,
                    "mysql scalar cell",
                )
                # In its cell a MySQL width is a literal from 0 to 256, as
                # emission's is.
                _require(
                    family != "mysql"
                    or width in range(schema.MYSQL_PACKET_FLOOR_CHARACTERS + 1),
                    "lpad realization",
                )
            elif op["kind"] == "scalar_call" and op["operator"] == "add_months":
                date = {"kind": "pg_date"}, {"kind": "date"}
                _require(
                    family == "postgres"
                    and _is_realization(
                        _value_realization(doc, operands[0]), "Date", *date
                    )
                    and _value_tag(doc, operands[1]) == "Int"
                    and _is_realization(result, "Date", *date),
                    "add_months realization",
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
        spread = _mysql_spread_cell(doc) if family == "mysql" else None
        # A MySQL `first` or `last` only in the S13 statement class.
        self.ranked = _ranked_stage(doc, family)
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
                "stddev": "VAR_SAMP",
                "variance": "VAR_SAMP",
                "pvariance": "VAR_POP",
                "pstdev": "VAR_POP",
                "median": "PERCENTILE_CONT",
                "quantile": "PERCENTILE_CONT",
                "filtered_count": "COUNT",
                "filtered_sum": "SUM",
                "count_distinct_tuple": "COUNT",
                "group_any": "COUNT",
                "group_all": "COUNT",
                "first": "ARRAY_AGG" if family == "postgres" else "MAX",
                "last": "ARRAY_AGG" if family == "postgres" else "MAX",
            }.get(column["function"])
            if family == "mysql" and column["function"] in _SPREAD_FUNCTIONS:
                expected = _MYSQL_SPREAD_SPELLING[column["function"]]
            _require(
                expected is not None and column["spelling"] == expected,
                "aggregate spelling",
            )
            argument = (
                None
                if column["argument"] is None
                else _value_realization(doc, column["argument"])
            )
            argument_tag = None if argument is None else argument.get("tag")
            result = doc[doc[column["column"]]["realization"]]
            argument_cast, result_cast = _aggregate_casts(
                family, column["function"], argument_tag
            )
            decimal_cast = _decimal_sum_cast(
                family, column["function"], argument, result
            )
            if decimal_cast is not None:
                argument_cast, result_cast = None, decimal_cast
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
            if column["function"] in {"sum", "avg"} and argument_tag == "Float":
                # PostgreSQL only: one finite binary64 argument, a nullable
                # finite binary64 result the target's overflow check bounds.
                result = doc[doc[column["column"]]["realization"]]
                _require(
                    family == "postgres"
                    and _is_pg_float(_value_realization(doc, column["argument"]))
                    and _is_pg_float(result)
                    and result["nullable"] is True,
                    "float sum or avg result",
                )
            elif column["function"] == "sum" and decimal_cast is None:
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
            if column["function"] in _SPREAD_FUNCTIONS:
                # PostgreSQL: one signed PostgreSQL Int or finite binary64
                # Float argument; MySQL (S05): only in its cell, one nullable
                # DOUBLE argument. A nullable finite binary64 result.
                argument = _value_realization(doc, column["argument"])
                result = doc[doc[column["column"]]["realization"]]
                _require(family != "mysql" or ref == spread, "mysql statistic cell")
                _require(
                    (
                        family == "postgres"
                        and (
                            _is_pg_float(argument)
                            or _is_pg_int(argument)
                            and argument["storage"]["kind"].startswith("pg_")
                        )
                        or family == "mysql"
                        and _is_float(argument, family)
                        and argument["nullable"] is True
                    )
                    and _is_float(result, family)
                    and result["nullable"] is True,
                    "variance or deviation result",
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
                    _is_text_value(doc, column["argument"], "postgres")
                    and _is_text_value(doc, column["delimiter"], "postgres")
                    and _is_pg_text(result, nullable=True, maximum=None)
                    and all(
                        _is_pg_order_value(_value_realization(doc, doc[item]["value"]))
                        for item in column["order_by"]
                    ),
                    "string_agg typed inputs",
                )
            elif column["function"] in {"filtered_count", "filtered_sum"}:
                # PostgreSQL only: a Bool test, of a sum in the delimiter slot
                # after its Int argument; a non-null bigint result, a count's
                # bounded by the count premise, a sum's by its checked CAST.
                counted = column["function"] == "filtered_count"
                test = column["argument"] if counted else column["delimiter"]
                low = 0 if counted else -(1 << 63)
                result = doc[doc[column["column"]]["realization"]]
                _require(
                    family == "postgres"
                    and test is not None
                    and (_value_realization(doc, test) or {}).get("tag") == "Bool"
                    and (counted or column["delimiter"] is not None)
                    and (
                        counted
                        or (_value_realization(doc, column["argument"]) or {}).get(
                            "tag"
                        )
                        == "Int"
                    )
                    and not column["distinct"]
                    and not column["order_by"]
                    and _is_realization(
                        result,
                        "Int",
                        {"kind": "pg_int8"},
                        {
                            "kind": "int_range",
                            "min": str(low),
                            "max": str((1 << 63) - 1),
                        },
                    )
                    and result["nullable"] is False,
                    "conditional aggregate shape",
                )
            elif column["function"] in {"group_any", "group_all"}:
                # PostgreSQL only: a Bool test, a count of it compared with 0,
                # a non-null computed Bool.
                result = doc[doc[column["column"]]["realization"]]
                _require(
                    family == "postgres"
                    and column["argument"] is not None
                    and (_value_realization(doc, column["argument"]) or {}).get("tag")
                    == "Bool"
                    and column["delimiter"] is None
                    and not column["distinct"]
                    and not column["order_by"]
                    and _is_realization(
                        result, "Bool", {"kind": "pg_bool"}, {"kind": "bool01"}
                    )
                    and result["nullable"] is False,
                    "group test shape",
                )
            elif column["function"] in {"first", "last"}:
                # One argument's value at one row, of its own carrier, NULL
                # where it is or for an empty input; R19 keys on PostgreSQL,
                # and on MySQL only the S13 statement and carriers.
                argument = _value_realization(doc, column["argument"])
                result = doc[doc[column["column"]]["realization"]]
                ranked = self.ranked is not None and ref in doc[self.ranked]["values"]
                _require(
                    (family == "postgres" or ranked)
                    and argument is not None
                    and column["delimiter"] is None
                    and bool(column["order_by"])
                    and all(
                        result[key] == argument[key]
                        for key in ("tag", "storage", "domain")
                    )
                    and (result["nullable"] is True or argument["nullable"] is False)
                    and all(
                        _is_ranked_key(_value_realization(doc, doc[item]["value"]))
                        if ranked
                        else _is_pg_order_value(
                            order := _value_realization(doc, doc[item]["value"])
                        )
                        or order is not None
                        and _is_pg_float(order)
                        for item in column["order_by"]
                    ),
                    "first or last shape",
                )
            elif column["function"] in {"median", "quantile"}:
                # PostgreSQL only: one signed PostgreSQL Int argument, a nullable
                # finite binary64 result, and for `quantile` a Float constant
                # fraction in the delimiter slot.
                argument = _value_realization(doc, column["argument"])
                result = doc[doc[column["column"]]["realization"]]
                fraction = column["delimiter"]
                _require(
                    family == "postgres"
                    and _is_pg_int(argument)
                    and argument["storage"]["kind"].startswith("pg_")
                    and _is_pg_float(result)
                    and result["nullable"] is True
                    and not column["order_by"]
                    and (fraction is None) is (column["function"] == "median")
                    and (
                        fraction is None
                        or fraction.kind == "sql_anchor"
                        and (_value_realization(doc, fraction) or {}).get("tag")
                        == "Float"
                    ),
                    "quantile shape",
                )
            elif column["function"] == "count_distinct_tuple":
                # PostgreSQL only: two or more established direct fields,
                # counted DISTINCT as one anonymous record.
                _require(
                    family == "postgres"
                    and column["distinct"] is True
                    and column["argument"] is not None
                    and column["argument"].kind == "sql_stage_reference"
                    and bool(column["extra_arguments"])
                    and all(
                        member.kind == "sql_stage_reference"
                        for member in column["extra_arguments"]
                    )
                    and column["delimiter"] is None
                    and not column["order_by"],
                    "count_distinct_tuple shape",
                )
            else:
                _require(
                    column["delimiter"] is None and not column["order_by"],
                    "aggregate extra inputs",
                )
            if column["function"] != "count_distinct_tuple":
                _require(not column["extra_arguments"], "aggregate extra arguments")
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
        aggregate_stages: dict[Ref, list[Ref]] = {}
        for ref in doc.all("row_body"):
            body = doc[ref]
            if body["aggregation"] is not None:
                aggregate_stages.setdefault(body["definition"], []).append(ref)
        for ref in doc.all("row_body"):
            body = doc[ref]
            if (
                body["block_kind"] != "projection"
                or body["definition"] not in aggregate_stages
            ):
                continue
            roots = [
                doc[column]["value"]
                for column in body["columns"]
                if column.kind == "row_value_column"
            ]
            if not roots:
                continue
            stages = aggregate_stages[body["definition"]]
            _require(len(stages) == 1, "aggregate composition stage")
            stage_body = doc[stages[0]]
            stage = doc[stage_body["aggregation"]]
            _require(
                bool(stage["values"])
                and stage_body["columns"] == (*stage["keys"], *stage["values"]),
                "aggregate composition stage",
            )
            _require(
                stage["mode"] in {"grouped", "global"}
                and bool(stage["keys"]) is (stage["mode"] == "grouped"),
                "aggregate composition mode",
            )
            _require(self.family == "postgres", "aggregate composition target")
            for root in roots:
                pending = [root]
                seen = set()
                reads_aggregate = False
                while pending:
                    value = pending.pop()
                    if value in seen:
                        continue
                    seen.add(value)
                    fields = doc[value]
                    if value.kind == "sql_operation":
                        _require(
                            fields["kind"] in {"scalar_call", "sign", "arithmetic"},
                            "aggregate composition expression",
                        )
                        pending.extend(fields["operands"])
                    elif value.kind in {"sql_unary", "sql_anchor"}:
                        pending.append(fields["operand"])
                    elif value.kind == "sql_stage_reference":
                        origin_ref = doc[fields["column"]]["aggregate"]
                        _require(origin_ref is not None, "aggregate composition scope")
                        origin = doc[origin_ref]
                        _require(
                            origin["aggregation"] == stage["aggregation"]
                            and origin["kind"] in {"group_key", "aggregate_result"},
                            "aggregate composition scope",
                        )
                        aggregate_result = origin["kind"] == "aggregate_result"
                        subject = "aggregate" if aggregate_result else "key"
                        claimed = stage["values"] if aggregate_result else stage["keys"]
                        _require(
                            sum(
                                doc[column][subject] == origin[subject]
                                and doc[column]["export"] == origin["result"]
                                for column in claimed
                            )
                            == 1,
                            "aggregate composition scope",
                        )
                        reads_aggregate |= aggregate_result
                    else:
                        _require(
                            value.kind in {"sql_literal", "sql_parameter", "sql_null"},
                            "aggregate composition terminal",
                        )
                _require(
                    stage["mode"] == "grouped" or reads_aggregate,
                    "global aggregate composition leaf",
                )
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
                realization = doc[read["realization"]]
                # A finite Float orders a result on both families; PostgreSQL
                # keys (_is_key_value) also take a distribution result (E6).
                _require(
                    _source_field_matches_stage(doc, read)
                    and (
                        _is_key_value(realization, self.family)
                        or _is_float(realization, self.family)
                    ),
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
            function = column["function"]
            # An aggregate over a window: PostgreSQL, one column argument or a
            # row count, and R13's casts; every other window has no cast.
            casts = (column["argument_cast"], column["result_cast"])
            if function in schema.WINDOW_AGGREGATES:
                reads = [
                    doc[argument["read"]]
                    for argument in arguments
                    if argument["read"] is not None
                ]
                _require(
                    self.family == "postgres"
                    and tuple(argument["role"] for argument in arguments)
                    in ((("value",), ()) if function == "count" else (("value",),))
                    and len(reads) == len(arguments)
                    and casts
                    == _aggregate_casts(
                        self.family,
                        function,
                        doc[reads[0]["realization"]]["tag"] if reads else None,
                    ),
                    "window aggregate",
                )
            else:
                _require(casts == (None, None), "window cast")
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
        tokens = _Tokens(self, units)
        tokens.run()
        _Requirements(self, units).run()
        if self.family == "mysql":
            _MysqlCellSql(tokens).run()


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
        self.ranked_table()
        self.overlay_alignment()
        self.int8_widening()
        self.null_casts()
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
        ranked = self.check.ranked
        rank_names = {} if ranked is None else _ranked_layout(doc, ranked)[1]
        _require(
            ranked is not None
            or not any(event["role"] in _RANK_ROLES for event in self.events),
            "rank token outside a ranked statement",
        )
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
                    elif role in ("rank_column", "rank_label"):
                        _require(rank_names.get(subject) == name, "rank name")
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
                elif name == "lpad":
                    expected = (
                        [
                            ("scalar_call_open", "(CASE WHEN length("),
                            ("scalar_call_separator", ") >= "),
                            ("scalar_call_separator", " THEN "),
                            ("scalar_call_separator", " ELSE lpad("),
                            ("scalar_call_separator", ", CAST("),
                            ("scalar_call_separator", " AS pg_catalog.int4), "),
                            ("scalar_call_close", ") END)"),
                        ]
                        if self.family == "postgres"
                        else [
                            ("scalar_call_open", "CASE WHEN CHAR_LENGTH("),
                            ("scalar_call_separator", ") >= "),
                            ("scalar_call_separator", " THEN "),
                            ("scalar_call_separator", " ELSE LPAD("),
                            ("scalar_call_separator", ", "),
                            ("scalar_call_separator", ", "),
                            ("scalar_call_close", ") END"),
                        ]
                    )
                elif name == "add_months":
                    expected = [
                        ("scalar_call_open", "CAST(("),
                        ("scalar_call_separator", " + make_interval(months => CAST("),
                        ("scalar_call_close", " AS pg_catalog.int4))) AS date)"),
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
            elif column["function"] == "count_distinct_tuple":
                count = 1 + len(column["extra_arguments"])
                expected = [
                    ("aggregate_open", "COUNT("),
                    ("aggregate_distinct", "DISTINCT "),
                    ("aggregate_tuple_open", "CASE WHEN "),
                    *[("aggregate_tuple_and", " IS NOT NULL AND ")] * (count - 1),
                    ("aggregate_tuple_then", " IS NOT NULL THEN ROW("),
                    *[("aggregate_separator", ", ")] * (count - 1),
                    ("aggregate_tuple_close", ") END"),
                    ("aggregate_close", ")"),
                ]
                _require(
                    aggregate_tokens == expected, "count_distinct_tuple token sequence"
                )
            elif column["function"] in {"first", "last"} and self.family == "mysql":
                # MAX(CASE WHEN rank = 1 THEN x END), then its ROW_NUMBER over
                # its group in its own order, `last` in the reversed one.
                flip = {"asc": " DESC", "desc": " ASC"}
                ranked = self.check.ranked
                if ranked is None:
                    raise _Reject(Status.INVALID_RELATION, "first or last shape")
                stage = doc[ranked]
                expected = [
                    ("aggregate_open", "MAX("),
                    ("aggregate_rank_open", "CASE WHEN "),
                    ("aggregate_rank_qualifier", "."),
                    ("aggregate_rank_then", " = 1 THEN "),
                    ("aggregate_rank_close", " END"),
                    ("aggregate_close", ")"),
                    ("aggregate_rank_window", "ROW_NUMBER() OVER ("),
                ]
                for position, _key in enumerate(stage["keys"]):
                    expected += [
                        ("aggregate_rank_separator", ", ")
                        if position
                        else ("aggregate_rank_partition", "PARTITION BY "),
                        ("aggregate_rank_partition_qualifier", "."),
                    ]
                if stage["keys"]:
                    expected.append(("aggregate_rank_spec_separator", " "))
                expected.append(("aggregate_rank_order", "ORDER BY "))
                for position, item in enumerate(column["order_by"]):
                    if position:
                        expected.append(("aggregate_rank_separator", ", "))
                    direction = doc[item]["direction"]
                    expected.append(
                        ("aggregate_order_reversed_direction", flip[direction])
                        if column["function"] == "last"
                        else ("aggregate_order_direction", schema.DIRECTIONS[direction])
                    )
                expected.append(("aggregate_rank_alias", ") AS "))
                _require(aggregate_tokens == expected, "ranked token sequence")
            elif column["function"] in {"first", "last"}:
                # `last` is the first element of the reversed order.
                flip = {"asc": " DESC", "desc": " ASC"}
                expected = [
                    ("aggregate_element_open", "("),
                    ("aggregate_open", "ARRAY_AGG("),
                    ("aggregate_order", " ORDER BY "),
                ]
                for position, item in enumerate(column["order_by"]):
                    if position:
                        expected.append(("aggregate_order_separator", ", "))
                    direction = doc[item]["direction"]
                    expected.append(
                        ("aggregate_order_reversed_direction", flip[direction])
                        if column["function"] == "last"
                        else ("aggregate_order_direction", schema.DIRECTIONS[direction])
                    )
                expected += [
                    ("aggregate_close", ")"),
                    ("aggregate_element_close", ")[1]"),
                ]
                _require(aggregate_tokens == expected, "first or last token sequence")
            elif column["function"] in {"median", "quantile"}:
                expected = [("aggregate_open", "PERCENTILE_CONT(")]
                if column["function"] == "median":
                    expected.append(("aggregate_fraction", "0.5"))
                expected += [
                    ("aggregate_within", ") WITHIN GROUP (ORDER BY "),
                    ("aggregate_argument_cast_open", "CAST("),
                    (
                        "aggregate_argument_cast_close",
                        " AS " + str(column["argument_cast"]) + ")",
                    ),
                    ("aggregate_close", ")"),
                ]
                _require(aggregate_tokens == expected, "quantile token sequence")
            elif column["function"] in {"group_any", "group_all"}:
                tested = column["function"] == "group_any"
                expected = [
                    ("aggregate_test_open", "("),
                    ("aggregate_open", column["spelling"] + "("),
                    ("aggregate_filter_open", "CASE WHEN "),
                    ("aggregate_filter_then", " THEN "),
                    ("aggregate_filter_one", "1")
                    if tested
                    else ("aggregate_filter_else", "NULL ELSE 1"),
                    ("aggregate_filter_close", " END"),
                    ("aggregate_close", ")"),
                    ("aggregate_test_close", " > 0)" if tested else " = 0)"),
                ]
                _require(aggregate_tokens == expected, "group test token sequence")
            elif column["function"] in {"filtered_count", "filtered_sum"}:
                counted = column["function"] == "filtered_count"
                expected = [] if counted else [("aggregate_zero_open", "COALESCE(")]
                if column["result_cast"] is not None:
                    expected.append(("aggregate_result_cast_open", "CAST("))
                expected += [
                    ("aggregate_open", column["spelling"] + "("),
                    ("aggregate_filter_open", "CASE WHEN "),
                    ("aggregate_filter_then", " THEN "),
                ]
                if counted:
                    expected.append(("aggregate_filter_one", "1"))
                else:
                    expected += [
                        ("aggregate_argument_cast_open", "CAST("),
                        (
                            "aggregate_argument_cast_close",
                            " AS " + str(column["argument_cast"]) + ")",
                        ),
                    ]
                expected += [
                    ("aggregate_filter_close", " END"),
                    ("aggregate_close", ")"),
                ]
                if column["result_cast"] is not None:
                    expected.append(
                        (
                            "aggregate_result_cast_close",
                            " AS " + column["result_cast"] + ")",
                        )
                    )
                if not counted:
                    expected.append(("aggregate_zero_close", ", 0)"))
                _require(
                    aggregate_tokens == expected, "conditional aggregate token sequence"
                )
            else:
                root = self.family == "postgres" and column["function"] in {
                    "stddev",
                    "pstdev",
                }
                expected = [("aggregate_root_open", "SQRT(")] if root else []
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
                if root:
                    expected.append(("aggregate_root_close", ")"))
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
        if role in {
            "float_remainder_open",
            "float_remainder_between",
            "float_remainder_close",
        }:
            _require(
                node is not None
                and node["kind"] == "arithmetic"
                and node["operator"] == "%"
                and self.family == "postgres",
                "float remainder subject",
            )
            expected = dict(
                zip(
                    (
                        "float_remainder_open",
                        "float_remainder_between",
                        "float_remainder_close",
                    ),
                    schema.FLOAT_REMAINDER_TOKENS,
                    strict=True,
                )
            )[role]
            _require(text == expected, "float remainder spelling")
            return
        if role in {"decimal_arithmetic_open", "decimal_arithmetic_close"}:
            _require(
                node is not None
                and node["kind"] == "arithmetic"
                and node["operator"] in {"+", "-", "*"}
                and self.family == "postgres",
                "Decimal arithmetic subject",
            )
            assert node is not None
            if node["operator"] == "*":
                ranges = _ProvenIntRanges(self.doc, self.family)
                operands = tuple(ranges.value(ref) for ref in node["operands"])
                _require(
                    len(operands) == 2
                    and operands.count("Decimal") == 1
                    and sum(ranges.as_range(value) is not None for value in operands)
                    == 1,
                    "Decimal product cast operands",
                )
            realization = self.doc[node["realization"]]
            storage = realization["storage"]
            precision, scale = storage.get("precision"), storage.get("scale")
            _require(
                realization["tag"] == "Decimal"
                and storage.get("kind") == "pg_numeric"
                and type(precision) is int
                and type(scale) is int
                and 0 <= scale <= precision <= 65
                and text
                == (
                    "CAST(("
                    if role == "decimal_arithmetic_open"
                    else f") AS pg_catalog.numeric({precision}, {scale}))"
                ),
                "Decimal arithmetic spelling",
            )
            return
        if role.startswith("scalar_call_"):
            _require(
                node is not None and node["kind"] == "scalar_call",
                "scalar call subject",
            )
            assert node is not None
            name = node["operator"]
            if name in {"round", "date_trunc", "lpad", "add_months"}:
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
                if name == "now":
                    expected = (
                        "(statement_timestamp() AT TIME ZONE 'UTC'"
                        if self.family == "postgres"
                        else "UTC_TIMESTAMP(6"
                    )
                elif name == "same_value":
                    expected = "("
                elif name == "substr":
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
                if (
                    name
                    in {
                        "substr",
                        "starts_with",
                        "ends_with",
                        "concat",
                        "same_value",
                        "now",
                    }
                    or name in simple
                ):
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
                        else {" || "}
                        if self.family == "postgres" and name == "concat"
                        else {
                            " IS NOT DISTINCT FROM "
                            if self.family == "postgres"
                            else " <=> "
                        }
                        if name == "same_value"
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
        if role in ("window_argument_cast_open", "window_result_cast_open"):
            column = self.one(windows, subject, "window subject")
            _require(
                column[role[len("window_") : -len("_open")]] is not None
                and text == "CAST(",
                "window cast",
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
        elif role == "null_cast_close":
            _require(
                text == schema.ANCHOR_SUFFIX[schema.PHYSICAL[self.family]["Int"]],
                "typed NULL cast",
            )
        elif role == "anchor_close":
            anchor = self.one(anchors, subject, "anchor subject")
            _require(
                text == schema.ANCHOR_SUFFIX[anchor["physical_type"]], "anchor spelling"
            )
        elif role == "aggregate_open":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(text == column["spelling"] + "(", "aggregate spelling")
        elif role == "aggregate_test_close":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(
                text
                == {"group_any": " > 0)", "group_all": " = 0)"}.get(column["function"]),
                "group test comparison",
            )
        elif role in ("aggregate_argument_cast_close", "aggregate_result_cast_close"):
            column = self.one(aggregates, subject, "aggregate subject")
            cast = column[role[len("aggregate_") : -len("_close")]]
            _require(cast is not None and text == " AS " + cast + ")", "aggregate cast")
        elif role == "aggregate_order_direction":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(
                column["function"] in {"string_agg", "first"}
                and text in {" ASC", " DESC"},
                "aggregate order direction",
            )
        elif role == "aggregate_order_reversed_direction":
            column = self.one(aggregates, subject, "aggregate subject")
            _require(
                column["function"] == "last" and text in {" ASC", " DESC"},
                "aggregate order direction",
            )
        elif role in ("window_argument_cast_close", "window_result_cast_close"):
            column = self.one(windows, subject, "window subject")
            cast = column[role[len("window_") : -len("_close")]]
            _require(cast is not None and text == " AS " + cast + ")", "window cast")
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

    def ranked_table(self) -> None:
        """A ranked statement's derived table, token by token, from the
        document: FROM (SELECT its read columns, then each ROW_NUMBER in its
        own order, FROM its body's own scan) AS that scan's alias."""
        ranked = self.check.ranked
        if ranked is None:
            return
        doc, events, stage = self.doc, self.events, self.doc[ranked]
        listed, names = _ranked_layout(doc, ranked)
        (body,) = [b for b in doc.all("row_body") if doc[b]["aggregation"] == ranked]
        scan = doc[body]["scan"]
        alias = doc[doc[scan]["symbol"]]["name"]
        table = stage["aggregation"]
        starts = [
            i
            for i, event in enumerate(events)
            if event["role"] == "from" and event["subject"] == table
        ]
        _require(len(starts) == 1, "ranked table")
        i = starts[0]

        def take(kind, role, subject=None, name=None):
            nonlocal i
            _require(
                i < len(events)
                and (events[i]["kind"], events[i]["role"]) == (kind, role)
                and (subject is None or events[i]["subject"] == subject)
                and (name is None or self.identifier(i) == name),
                "ranked table",
            )
            i += 1

        take("syntax", "from", table)
        take("syntax", "rank_open", table)
        for position, name in enumerate(listed):
            if position:
                take("syntax", "rank_separator", table)
            take("identifier", "rank_carry_scope", table, alias)
            take("syntax", "rank_carry_qualifier", table)
            take("identifier", "rank_carry_column", None, name)
        for value in stage["values"]:
            column = doc[value]
            own = column["aggregate"]
            take("syntax", "rank_separator", own)
            take("syntax", "aggregate_rank_window", own)
            for position, key in enumerate(stage["keys"]):
                take(
                    "syntax",
                    "aggregate_rank_separator"
                    if position
                    else "aggregate_rank_partition",
                    own,
                )
                take("identifier", "rank_partition_scope", own, alias)
                take("syntax", "aggregate_rank_partition_qualifier", own)
                take(
                    "identifier",
                    "rank_partition_column",
                    None,
                    doc[doc[key]["read"]]["name"],
                )
            if stage["keys"]:
                take("syntax", "aggregate_rank_spec_separator", own)
            take("syntax", "aggregate_rank_order", own)
            for position, item in enumerate(column["order_by"]):
                if position:
                    take("syntax", "aggregate_rank_separator", own)
                reference = doc[doc[item]["value"]]
                take("identifier", "value_scope", None, alias)
                take("syntax", "value_qualifier")
                take(
                    "identifier", "value_column", None, doc[reference["column"]]["name"]
                )
                take(
                    "syntax",
                    "aggregate_order_reversed_direction"
                    if column["function"] == "last"
                    else "aggregate_order_direction",
                    own,
                )
            take("syntax", "aggregate_rank_alias", own)
            take("identifier", "rank_label", own, names[own])
        if scan.kind == "row_scan":
            take("syntax", "from")
            take("identifier", "namespace")
            take("syntax", "qualifier")
            take("identifier", "relation")
            take("syntax", "alias")
            take("identifier", "relation_scope", None, alias)
        else:
            take("syntax", "from")
            take("identifier", "stage_reference")
            take("syntax", "alias")
            take("identifier", "stage_scope", None, alias)
        take("syntax", "rank_close", table)
        take("identifier", "rank_scope", table, alias)

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

    def null_casts(self) -> None:
        """Each typed NULL operand of an Int arithmetic operation, and nothing
        else, is CAST to the target's Int carrier (D-12): an untyped NULL
        takes the type the target chooses."""
        doc = self.doc
        expected: dict[PlanRef, Ref] = {}
        for ref in doc.all("sql_operation"):
            op = doc[ref]
            nulls = [item for item in op["operands"] if item.kind == "sql_null"]
            if op["kind"] == "arithmetic" and doc[op["realization"]]["tag"] == "Int":
                _require(len(nulls) <= 1, "typed NULL cast")
                if nulls:
                    expected[op["original"]] = doc[nulls[0]]["site"]
        starts = {event["start"]: i for i, event in enumerate(self.events)}
        ends = {event["end"]: i for i, event in enumerate(self.events)}
        seen: list[PlanRef] = []
        for overlay in self.overlays:
            if overlay["role"] != "null_cast":
                continue
            subject = overlay["subject"]
            i, j = starts[overlay["start"]], ends[overlay["end"]]
            _require(
                subject in expected
                and j == i + 2
                and self.events[i + 1]["kind"] == "literal"
                and self.events[i + 1]["subject"] == expected[subject]
                and self.events[i - 1]["subject"] == subject
                and self.events[i - 1]["role"]
                in ("binary_open", "arithmetic_operator"),
                "typed NULL cast",
            )
            seen.append(subject)
        _require(
            len(seen) == len(set(seen)) and set(seen) == set(expected),
            "typed NULL cast",
        )

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


# The roles a select item's value or a WHERE predicate holds in a MySQL lpad
# or now() document: none spells a clause, a subquery, an aggregate or a
# window (a join's membership_open does, but a join is a unit of its own,
# which no frame below parses), and a parameter is refused by its kind.
_EXPRESSION_ROLES = frozenset(
    {
        "value_scope",
        "value_qualifier",
        "value_column",
        "anchor_open",
        "anchor_close",
        "null_cast_open",
        "null_cast_close",
        "scalar_call_open",
        "scalar_call_separator",
        "scalar_call_close",
        "scalar_call_nested_open",
        "scalar_call_nested_close",
        "scalar_call_operator",
        "comparison_open",
        "comparison_operator",
        "comparison_close",
        "comparison_escape",
        "binary_open",
        "binary_close",
        "arithmetic_operator",
        "logical_operator",
        "unary_open",
        "unary_close",
        "not_open",
        "not_close",
        "is_null_open",
        "is_null_test",
        "is_null_close",
        "between_open",
        "between_operator",
        "between_separator",
        "between_close",
        "conditional_open",
        "conditional_then",
        "conditional_else",
        "conditional_close",
        "cast_open",
        "cast_close",
        "membership_open",
        "membership_operator",
        "membership_separator",
        "membership_close",
        "membership_constant",
        *schema.TAGS,
    }
)
# A capture read's own frames may also name an outer field.
_INLINE_ROLES = _EXPRESSION_ROLES | {
    "capture_scope",
    "capture_qualifier",
    "capture_column",
}
# One window call and its own OVER specification.
_WINDOW_ROLES = frozenset(
    {
        "window_open",
        "window_close",
        "window_over",
        "window_spec_open",
        "window_spec_close",
        "window_spec_separator",
        "window_partition",
        "window_partition_separator",
        "window_partition_scope",
        "window_partition_qualifier",
        "window_partition_column",
        "window_order",
        "window_order_separator",
        "window_order_scope",
        "window_order_qualifier",
        "window_order_column",
        "window_order_direction",
        "window_frame_unit",
        "window_frame_start",
        "window_frame_end",
        "window_frame_exclusion",
        "window_frame_separator",
        "window_frame_and",
        "window_argument_separator",
        "window_argument_scope",
        "window_argument_qualifier",
        "window_argument_column",
        "window_argument_literal",
        "window_argument_cast_open",
        "window_argument_cast_close",
        "window_result_cast_open",
        "window_result_cast_close",
        "window_row_count",
        "window_reference",
    }
)
# A capture read, (SELECT e.c FROM (<let>) AS e), around its let.
_SCALAR_READ = (
    "scalar_open",
    "scalar_select",
    "scalar_scope",
    "scalar_column_qualifier",
    "scalar_column",
    "scalar_from",
    "inline_open",
)
_SCALAR_READ_END = ("inline_close", "scalar_alias", "scalar_scope", "scalar_close")
# The operand each gap between a MySQL lpad's seven tokens renders: CASE WHEN
# CHAR_LENGTH(x) >= w THEN x ELSE LPAD(x, w, fill) END.
_LPAD_SLOTS = (0, 1, 0, 0, 1, 2)


class _MysqlCellSql:
    """Each MySQL lpad and now() in its cell, read from the rendered SQL.

    _mysql_scalar_cells reads columns, predicates, scans and operands that
    the token checks never tie to the SQL, so it can only refuse. This reads
    every unit back from its verified tokens in the grammar _row_select
    renders, SELECT item, ... FROM scan [WINDOW ...] [WHERE predicate], and
    needs each call to be, rendered once, the whole item that its record's
    final column names, over lets, at most one WHERE and at most one window
    below them, then the source, or beside one capture read; and each lpad
    operand to render its own record: an anchored literal, or a reference
    that carried and renamed items lead to the source field that record
    names. Anything else opens no cell."""

    def __init__(self, tokens: _Tokens) -> None:
        self.tokens, self.doc = tokens, tokens.doc
        self.roles = [event["role"] for event in tokens.events]
        self.depth = [0]  # the parenthesis depth before each token
        for event, text in zip(tokens.events, tokens.texts, strict=True):
            change = text.count("(") - text.count(")")
            self.depth.append(
                self.depth[-1] + (change if event["kind"] == "syntax" else 0)
            )

    def run(self) -> None:
        doc, tokens, roles = self.doc, self.tokens, self.roles
        calls = [
            ref
            for ref in doc.all("sql_operation")
            if doc[ref]["kind"] == "scalar_call"
            and doc[ref]["operator"] in ("lpad", "now")
        ]
        if not calls:
            return
        # No record bounds a window argument literal's text; only the Int or
        # NULL the renderer writes keeps every literal free of a comma, a
        # parenthesis, a clause or a comment that the frames below never see.
        for event, text in zip(tokens.events, tokens.texts, strict=True):
            if event["kind"] == "literal" and event["role"] not in schema.TAGS:
                _require(
                    event["role"] == "window_argument_literal"
                    and (text == "NULL" or _INT.fullmatch(text) is not None),
                    "mysql scalar cell",
                )
        segments = tokens.segments()
        # Each CTE's frame and, by column, the source field that a carried or
        # renamed item of it reads (units() names the columns c0, c1, ...).
        frames: dict[str, tuple[dict, dict[str, tuple | None]]] = {}
        for unit, start, end in segments[:-1]:
            frame = self.frame(start, end)
            names = [doc[column]["name"] for column in doc[unit]["cte_columns"]]
            frames[doc[doc[unit]["symbol"]]["name"]] = (
                frame,
                {
                    name: self.source(frames, frame, item["read"])
                    for name, item in zip(names, frame["items"], strict=False)
                    if item["kind"] in ("carry", "value")
                },
            )
        unit, start, end = segments[-1]
        final = self.frame(start, end, final=True)
        captured = any(item["kind"] == "capture" for item in final["items"])
        _require(
            final["stage"] == "let"
            and (not captured or (not frames and final["scan"][0] == "relation")),
            "mysql scalar cell",
        )
        order, scan, seen = ("window", "where", "let"), final["scan"], set()
        while scan[0] == "stage":
            _require(scan[1] in frames and scan[1] not in seen, "mysql scalar cell")
            seen.add(scan[1])
            stage = frames[scan[1]][0]["stage"]
            _require(stage in order, "mysql scalar cell")
            order = order[order.index(stage) + (stage != "let") :]
            scan = frames[scan[1]][0]["scan"]
        opens: dict[PlanRef, int] = {}
        for event in tokens.events:
            if event["role"] == "scalar_call_open":
                opens[event["subject"]] = opens.get(event["subject"], 0) + 1
        # The final column each call is the value of, or the date_of operand of.
        place: dict[Ref, tuple[int, bool]] = {}
        for position, column in enumerate(doc[unit]["columns"]):
            if column.kind == "row_value_column":
                value = doc[column]["value"]
                place[value] = (position, False)
                if (
                    value.kind == "sql_operation"
                    and doc[value]["operator"] == "date_of"
                ):
                    for operand in doc[value]["operands"]:
                        place[operand] = (position, True)
        for ref in calls:
            op = doc[ref]
            _require(
                ref in place and opens.get(op["original"]) == 1, "mysql scalar cell"
            )
            position, date_of = place[ref]
            start, end = final["items"][position]["span"]
            texts = tokens.texts[start:end]
            if op["operator"] == "now":
                # Each now() is rendered once and each item that a now()
                # names holds one: so none is rendered anywhere else.
                _require(
                    texts
                    == (
                        ["DATE(", "UTC_TIMESTAMP(6", ")", ")"]
                        if date_of
                        else ["UTC_TIMESTAMP(6", ")"]
                    ),
                    "mysql scalar cell",
                )
                continue
            marks = [
                k
                for k in range(start, end)
                if tokens.events[k]["subject"] == op["original"]
                and roles[k].startswith("scalar_call_")
            ]
            _require(
                len(marks) == len(_LPAD_SLOTS) + 1
                and marks[0] == start
                and marks[-1] == end - 1,
                "mysql scalar cell",
            )
            for slot, a, b in zip(_LPAD_SLOTS, marks[:-1], marks[1:], strict=True):
                self.operand(
                    op["operands"][slot], tokens.texts[a + 1 : b], final, frames
                )

    def operand(self, operand: Ref, texts, final, frames) -> None:
        """One lpad slot renders its operand's own record: an anchored
        literal, or a reference to the source field that record names."""

        doc = self.doc
        if operand.kind == "sql_anchor":
            anchor = doc[operand]
            leaf = anchor["operand"]
            value = doc[leaf]["value"] if leaf.kind == "sql_literal" else None
            _require(
                value is not None
                and texts
                == [
                    schema.SYNTAX["anchor_open"],
                    schema.literal_token(value.tag, value.value, "mysql"),
                    schema.ANCHOR_SUFFIX.get(anchor["physical_type"]),
                ],
                "mysql scalar cell",
            )
            return
        _require(operand.kind == "sql_stage_reference", "mysql scalar cell")
        reference = doc[operand]
        column = doc[reference["column"]]
        field = column["field"]
        source = next(
            (
                doc[ref]
                for ref in doc.all("bound_source")
                if field in doc[ref]["fields"]
            ),
            None,
        )
        _require(
            source is not None
            and texts
            == [
                schema.quoted(final["alias"], "mysql"),
                ".",
                schema.quoted(column["name"], "mysql"),
            ]
            and self.source(frames, final, column["name"])
            == (source["namespace"], source["name"], doc[field]["column"])
            and _source_field_matches_stage(doc, column)
            and doc[reference["realization"]] == doc[column["realization"]],
            "mysql scalar cell",
        )

    def source(self, frames, frame, column: str) -> tuple | None:
        """The source relation and column that ``column`` of the one scan of
        ``frame`` (a CTE or the final query) is, through the CTEs it scans."""

        scan = frame["scan"]
        if scan[0] == "relation":
            return (*scan[1:], column)
        return frames[scan[1]][1].get(column) if scan[1] in frames else None

    def frame(self, i: int, end: int, *, inline=False, final=False) -> dict:
        """SELECT item, ... FROM scan [WINDOW ...] [WHERE predicate] up to
        ``end``, as _row_select renders one body; an inline scan is a capture
        read's only."""

        roles, base, name = self.roles, self.depth[i], self.tokens.identifier
        _require(i < end and roles[i] == "select", "mysql scalar cell")
        items = []
        while True:
            k = i + 1
            while k < end and not (roles[k] == "alias" and self.depth[k] == base):
                k += 1
            _require(
                i + 1 < k < end - 2 and roles[k + 1] == "label", "mysql scalar cell"
            )
            items.append(self.item(i + 1, k, base, inline=inline, final=final))
            i = k + 2
            if roles[i] != "separator":
                break
        _require(roles[i] == "from", "mysql scalar cell")
        i += 1
        relation = ["namespace", "qualifier", "relation", "alias", "relation_scope"]
        if roles[i : i + 5] == relation:
            scan, alias, i = ("relation", name(i), name(i + 2)), name(i + 4), i + 5
        elif roles[i : i + 3] == ["stage_reference", "alias", "stage_scope"]:
            scan, alias, i = ("stage", name(i)), name(i + 2), i + 3
        else:
            _require(
                inline and roles[i : i + 1] == ["inline_open"], "mysql scalar cell"
            )
            close = self.closing(i, end)
            _require(
                roles[close : close + 3] == ["inline_close", "alias", "stage_scope"],
                "mysql scalar cell",
            )
            inner = self.frame(i + 1, close, inline=True)
            scan, alias, i = ("inline", inner), name(close + 2), close + 3
        windowed = any(item["kind"] == "window" for item in items)
        # WINDOW `w` AS (spec), ..., as _window_clause writes it.
        head = "window_clause"
        while i < end and roles[i] == head:
            close = self.closing(i + 3, end)
            _require(
                roles[i + 1 : i + 4]
                == ["window_definition", "window_definition_as", "window_spec_open"]
                and roles[close] == "window_spec_close"
                and _WINDOW_ROLES.issuperset(roles[i + 4 : close]),
                "mysql scalar cell",
            )
            i, head = close + 1, "window_clause_separator"
        where = i < end and roles[i] == "where"
        if where:
            self.flat(i + 1, end, base)
            self.expression(i + 1, end, inline)
            i = end
        _require(i == end and not (windowed and where), "mysql scalar cell")
        stage = "window" if windowed else "where" if where else "let"
        return {"items": items, "scan": scan, "alias": alias, "stage": stage}

    def item(self, start: int, end: int, base: int, *, inline, final) -> dict:
        roles, name, span = self.roles[start:end], self.tokens.identifier, (start, end)
        self.flat(start, end, base)
        for prefix in ("carry", "value", "window_result"):
            if roles == [f"{prefix}_scope", f"{prefix}_qualifier", f"{prefix}_column"]:
                return {
                    "kind": prefix,
                    "read": name(end - 1),
                    "span": span,
                }
        if roles[0] in ("window_open", "window_result_cast_open"):
            _require(_WINDOW_ROLES.issuperset(roles), "mysql scalar cell")
            return {"kind": "window", "span": span}
        if final and roles[0] == "scalar_open":
            self.capture(start, end)
            return {"kind": "capture", "span": span}
        self.expression(start, end, inline)
        return {"kind": "expression", "span": span}

    def capture(self, start: int, end: int) -> None:
        """Q4's read: of a let over a source scan or over one WHERE body of
        it, naming an outer field."""

        roles = self.roles
        close = end - len(_SCALAR_READ_END)
        _require(
            tuple(roles[start : start + len(_SCALAR_READ)]) == _SCALAR_READ
            and tuple(roles[close:end]) == _SCALAR_READ_END
            and self.closing(start + len(_SCALAR_READ) - 1, end) == close
            and "capture_scope" in roles[start:end],
            "mysql scalar cell",
        )
        let = self.frame(start + len(_SCALAR_READ), close, inline=True)
        scan = let["scan"]
        _require(
            let["stage"] == "let"
            and (
                scan[0] == "relation"
                or (
                    scan[0] == "inline"
                    and scan[1]["stage"] == "where"
                    and scan[1]["scan"][0] == "relation"
                )
            ),
            "mysql scalar cell",
        )

    def expression(self, start: int, end: int, inline) -> None:
        allowed = _INLINE_ROLES if inline else _EXPRESSION_ROLES
        for k in range(start, end):
            _require(
                self.roles[k] in allowed
                and self.tokens.events[k]["kind"] != "parameter",
                "mysql scalar cell",
            )

    def flat(self, start: int, end: int, base: int) -> None:
        """No comma at the frame's own depth, where it would start an item."""

        for k in range(start, end):
            if self.tokens.events[k]["kind"] == "syntax":
                depth = self.depth[k]
                for character in self.tokens.texts[k]:
                    _require(character != "," or depth > base, "mysql scalar cell")
                    depth += {"(": 1, ")": -1}.get(character, 0)

    def closing(self, i: int, end: int) -> int:
        """The token that closes the parenthesis token ``i`` opens."""

        for k in range(i, end):
            if self.depth[k + 1] == self.depth[i]:
                return k
        raise _Reject(Status.INVALID_RELATION, "mysql scalar cell")


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
        if function in {
            "count",
            "count_distinct",
            "count_distinct_tuple",
            "filtered_count",
        }:
            return 0, _I64_MAX
        if function == "filtered_sum":
            return _I64_MIN, _I64_MAX
        if function == "sum" and column["argument"] is not None:
            argument = self.value(column["argument"])
            return (
                argument if argument in {"Float", "Decimal"} else (_I64_MIN, _I64_MAX)
            )
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
        if (
            self.family == "postgres"
            and op["kind"] == "arithmetic"
            and op["operator"] in {"+", "-", "*"}
            and len(values) == 2
            and "Decimal" in values
            and all(value == "Decimal" or self.known(value) for value in values)
        ):
            return "Decimal"
        if any(value in {"Float", "Decimal"} for value in values):
            # A Float or Decimal operation keeps its operands' one shared tag.
            return values[0] if len(set(values)) == 1 else self._UNKNOWN
        ranges = cast(tuple[tuple[int, int], ...], values)
        if op["kind"] == "sign" and len(ranges) == 1:
            low, high = ranges[0]
            return (-high, -low) if op["operator"] == "-" else (low, high)
        if op["kind"] == "arithmetic" and len(ranges) == 2:
            (a, b), (c, d) = ranges
            if op["operator"] in {"/", "%"}:
                result = self.doc[op["realization"]]
                if (
                    self.family == "postgres"
                    and _is_pg_int(result)
                    and dict(result["storage"]) == {"kind": "pg_int8"}
                    and dict(result["domain"])
                    == {"kind": "int_range", "min": str(_I64_MIN), "max": str(_I64_MAX)}
                ):
                    return _I64_MIN, _I64_MAX
                return self._UNKNOWN
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
        """Q2 evidence follows the independently rebuilt operand proof; E4
        evidence marks a PostgreSQL Float `+`, `-` or `*` no fold proves."""
        interval = self.ranges.target_checked(value)
        _require(interval is not self.ranges._UNKNOWN, "target checked proof")
        if interval is None:
            op = self.doc[value] if value.kind == "sql_operation" else None
            unfolded = (
                op is not None
                and self.family == "postgres"
                and op["kind"] == "arithmetic"
                and op["operator"] != "%"
                and self.doc[op["realization"]]["tag"] == "Float"
                and not all(_float_literal(self.doc, item) for item in op["operands"])
            )
            _require(
                evidence == ((_TARGET_CHECKED_BINARY64,) if unfolded else ()),
                "target checked evidence",
            )
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
                    _aggregate_evidence(
                        item["function"],
                        None
                        if item["argument"] is None
                        else (_value_realization(doc, item["argument"]) or {}).get(
                            "tag"
                        ),
                    ),
                )
                if item["argument"] is not None:
                    self.value(item["argument"])
                if item["delimiter"] is not None:
                    self.value(item["delimiter"])
                for extra in item["extra_arguments"]:
                    self.value(extra)
                for order in item["order_by"]:
                    self.value(doc[order]["value"])
            elif kind == "aggregate_projection_column":
                self.add("result_projection", item["projection"], "R12", ())
            elif kind == "window_column":
                origin = doc[doc[item["column"]]["window"]]
                spec = doc[item["specification"]]
                reads = [
                    doc[doc[argument]["read"]]
                    for argument in item["arguments"]
                    if doc[argument]["read"] is not None
                ]
                self.add(
                    "window_computation",
                    item["window"],
                    "R14",
                    operators,
                    _aggregate_evidence(
                        item["function"],
                        doc[reads[0]["realization"]]["tag"] if reads else None,
                    ),
                )
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
                        and _is_key_value(doc[read["realization"]], self.family),
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
