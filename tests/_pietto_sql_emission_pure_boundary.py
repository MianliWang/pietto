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

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import json
import math
import re
from types import MappingProxyType
from typing import Any, cast

from pietto._project import project_sql_emission_portable_schema as schema
from pietto._project import project_sql_emission_sum_forms as sum_forms

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

    return _float_literal_value(doc, value) is not None


def _float_literal_value(doc, value) -> float | None:
    """The signed value of such an operand, or None."""

    negated = False
    while value.kind == "sql_unary":
        negated ^= doc[value]["operator"] == "-"
        value = doc[value]["operand"]
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
    if fixed is None or fixed.tag != "Float":
        return None
    return -fixed.value if negated else fixed.value


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
            for kind, form in (
                ("inner", "=="),
                ("inner", "not !="),
                ("left", "=="),
                ("anti", "=="),
            )
            for key in ("none", "text")
        ),
    }
)
# The fields of each source of a cell as carriers (_mysql_float_carrier) in
# declaration order, restated from the emitter's MYSQL_FLOAT_CELL_TABLES:
# exactly those of the qualification's tables, `f6s` (id, f1, f2) for a
# same-row cell, `f6o` and `f6i` (id, v, kn, kw) for a JOIN cell, and (in any
# order) the outer source's for an ANTI cell (Phase77 R02).
_MYSQL_FLOAT_CELL_TABLES = {
    "same_row": ("int", "float", "float"),
    "inner": ("int", "float", 64, 1000),
    "left": ("int", "float", 64, 1000),
    "anti": ("int", "float", 64, 1000),
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
# The kinds only an ANTI cell's document adds: its one `any(...)` read.
_MYSQL_FLOAT_ANTI_KINDS = frozenset(
    {"sql_any_read", "sql_any_reference", "sql_block_target"}
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
    directly (an ANTI cell's `any(...)` reference included), its carrier from
    _mysql_float_carrier; None otherwise."""
    if value.kind not in ("sql_stage_reference", "sql_any_reference"):
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
    holds no other operation or record kind. ANTI (Phase77 R02): one source O
    under a WHERE and a projection, the whole WHERE `not` over one `exists`
    read of a block target over another bound source I of another table,
    whose predicate is the tree or, before `and`, one `==` of two Text keys;
    each `==` reads one field of I under that target and one of O, and O has
    the fields of its table in any order. None outside every cell. A
    relation alias `let`, an unused named window or an inlined `def`, which
    emission refuses, changes the document only in source positions and
    source bytes, so this reader cannot tell it from the direct program."""
    operations = doc.all("sql_operation")
    artifacts = doc.all("artifact")
    anti = doc.all("sql_any_read")
    if (
        not set(doc.kinds)
        <= _MYSQL_FLOAT_CELL_KINDS | (_MYSQL_FLOAT_ANTI_KINDS if anti else set())
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
        if anti:
            exists = operation(root, "not", "not", 1)
            read = doc[anti[0]]
            producer = doc[read["target"]]["producer"]
            if (
                place != "where"
                or exists is None
                or producer.kind != "bound_source"
                or len(
                    {
                        (doc[item]["namespace"], doc[item]["name"])
                        for item in (*sources, producer)
                    }
                )
                != 2
            ):
                return None
            root, place = read["predicate"], "none"
            sides = operation(root, "logical", "and", 2)
            if sides is not None:
                root, key = sides
                keys, place = operation(key, "comparison", "==", 2), "text"
                if keys is None:
                    return None
            shape = ("anti", place)
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
        or len(operations) != 1 + negated + 2 * bool(keys) + bool(anti)
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
    table = _MYSQL_FLOAT_CELL_TABLES[shape[0]]

    def held(source):
        found = tuple(
            _mysql_float_carrier(doc[field]["representation"])
            for field in doc[source]["fields"]
        )
        # ANTI: O's fields in any order; I's other fields never reach the SQL.
        return Counter(found) if anti else found

    if (
        any(held(source) != (Counter(table) if anti else table) for source in sources)
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
        or (inputs is not None or anti)
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


# Phase77 S07: the MySQL Float GROUP BY cells as (template, key carriers in
# order) and the carriers as (tag, contract representation), restated from
# the emitter's MYSQL_FLOAT_KEY_CELLS and MYSQL_FLOAT_KEY_CARRIERS because
# this module imports no compiler.
_MYSQL_FLOAT_KEY_CELLS = frozenset(
    ("group", keys)
    for keys in (
        ("H",),
        ("F",),
        ("H", "H"),
        ("F", "F"),
        ("H", "N", "H"),
        ("F", "N", "F"),
    )
)
_MYSQL_FLOAT_KEY_CARRIERS = {
    "F": (
        "Float",
        {
            "domain": {"format": "binary64", "kind": "finite_float"},
            "nullable": True,
            "storage": {"kind": "my_double"},
        },
    ),
    "H": (
        "Float",
        {
            "domain": {"format": "binary64", "kind": "finite_float"},
            "nullable": False,
            "storage": {"kind": "my_double"},
        },
    ),
    "N": (
        "Text",
        {
            "domain": {
                "collation": "utf8mb4_0900_bin",
                "encoding": "utf8mb4",
                "kind": "text",
                "max_characters": 64,
                "padding": "NO PAD",
            },
            "nullable": False,
            "storage": {"kind": "my_varchar", "length": 64},
        },
    ),
}
# The record kinds a cell's document may hold; any other is never a cell.
_MYSQL_FLOAT_KEY_KINDS = frozenset(
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
        "row_body",
        "row_scan",
        "scope_definition",
        "scope_use",
        "sql_symbol",
        "stage_column",
        "terminal_binding",
        "sql_row_query",
        "row_stage_use",
        "aggregate_stage",
        "aggregate_key_column",
        "aggregate_value_column",
        "aggregate_projection_column",
        "aggregate_origin",
    }
)


def _mysql_float_key_carrier(doc, field):
    """The emitter's mysql_float_key_carrier of a bound field, restated."""
    logical = doc[field]["logical"]
    try:
        described = _json(doc[field]["representation"])
    except _Reject:
        return None
    if logical.get("kind") != "builtin":
        return None
    for symbol, carrier in _MYSQL_FLOAT_KEY_CARRIERS.items():
        if carrier == (logical.get("name"), described):
            return symbol
    return None


def _mysql_float_key_cell(doc):
    """The S07 cell of the document from its own structure, as emission
    derives it from its plan: an aggregate body scanning the one bound
    source, grouping by one to three key columns with one `count()` of no
    argument, then a projection reading its outputs in order. Each key is a
    direct read of a different field of the bound source, and its carrier
    gives the cell; the document holds no other record kind
    (_MYSQL_FLOAT_KEY_KINDS). None outside every cell. A relation alias
    `let`, an unused named window or an inlined `def`, which emission
    refuses, changes the document only in source positions and source bytes,
    so this reader cannot tell it from the direct program."""
    artifacts = doc.all("artifact")
    if len(artifacts) != 1:
        return None
    ast = doc[artifacts[0]]["ast"]
    if ast.kind != "sql_row_query":
        return None
    units = tuple(doc[ast]["bodies"])
    sources = doc.all("bound_source")
    if (
        not set(doc.kinds) <= _MYSQL_FLOAT_KEY_KINDS
        or len(units) != 2
        or units[0].kind != "row_body"
        or units[1].kind != "row_body"
        or len(sources) != 1
    ):
        return None
    body, unit = doc[units[0]], doc[units[1]]
    scan, terminals = body["scan"], tuple(body["terminals"])
    if (
        scan.kind != "row_scan"
        or doc[scan]["realization"] != sources[0]
        or body["predicate"] is not None
        or body["block_kind"] != "aggregate"
        or body["aggregation"] is None
    ):
        return None
    stage = doc[body["aggregation"]]
    keys, values = tuple(stage["keys"]), tuple(stage["values"])
    if (
        stage["mode"] != "grouped"
        or not 0 < len(keys) <= 3
        or len(values) != 1
        or tuple(body["columns"]) != (*keys, *values)
        or unit["block_kind"] != "projection"
        or unit["predicate"] is not None
        or unit["aggregation"] is not None
        or unit["scan"].kind != "row_stage_use"
        or doc[unit["scan"]]["body"] != units[0]
        or tuple(doc[doc[c]["read"]]["terminal"] for c in unit["columns"]) != terminals
    ):
        return None
    value = doc[values[0]]
    if (
        value["function"],
        value["argument"],
        value["distinct"],
        tuple(value["order_by"]),
        tuple(value["extra_arguments"]),
    ) != ("count", None, False, (), ()):
        return None
    fields = []
    for read in (doc[column]["read"] for column in keys):
        stage = doc[read]
        if (
            stage["field"] is None
            or stage["source_port"] is None
            or stage["literal"] is not None
            or stage["aggregate"] is not None
            or stage["window"] is not None
            or stage["field"] not in doc[sources[0]]["fields"]
        ):
            return None
        fields.append(stage["field"])
    if len(set(fields)) != len(fields):
        return None
    cell = ("group", tuple(_mysql_float_key_carrier(doc, f) for f in fields))
    return cell if cell in _MYSQL_FLOAT_KEY_CELLS else None


# The JOIN `on` `same_value` cells, restated from the emitter's
# NULLSAFE_JOIN_STRUCTURES, NULLSAFE_JOIN_CARRIERS and NULLSAFE_JOIN_CELLS
# (Phase77 S06 null-safe JOIN, D77.52): the whole ON over `o`, the preserved
# side (INNER: the left input), and `i`, as (side, field position) reads.
_NULLSAFE_JOIN_STRUCTURES = {
    ("same_value", ("o", 1), ("i", 1)): "S1",
    ("same_value", ("i", 1), ("o", 1)): "S1r",
    ("and", ("same_value", ("o", 1), ("i", 1)), ("==", ("o", 2), ("i", 2))): "S2",
    ("and", ("==", ("o", 2), ("i", 2)), ("same_value", ("o", 1), ("i", 1))): "S2r",
    (
        "and",
        ("same_value", ("o", 1), ("i", 1)),
        ("same_value", ("o", 2), ("i", 2)),
    ): "S3",
    ("not", ("same_value", ("o", 1), ("i", 1))): "S4",
    ("or", ("same_value", ("o", 1), ("i", 1)), ("==", ("o", 2), ("i", 2))): "S5",
}
_NULLSAFE_SAFE_INT = {
    "kind": "int_range",
    "min": "-9007199254740993",
    "max": "9007199254740993",
}
_NULLSAFE_JOIN_CARRIERS = {
    "postgres": {
        "int": ({"kind": "pg_int8"}, _NULLSAFE_SAFE_INT),
        "text": (
            {"kind": "pg_text"},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8",
                "collation": "C",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "pg_numeric", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "pg_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": ({"kind": "pg_uuid"}, {"kind": "uuid", "encoding": "standard_bytes"}),
        "float": (
            {"kind": "pg_float8"},
            {"kind": "finite_float", "format": "binary64"},
        ),
    },
    "mysql": {
        "int": ({"kind": "my_bigint"}, _NULLSAFE_SAFE_INT),
        "text": (
            {"kind": "my_varchar", "length": 64},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "my_decimal", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "my_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": (
            {"kind": "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
        "float": (
            {"kind": "my_double"},
            {"kind": "finite_float", "format": "binary64"},
        ),
    },
}
_NULLSAFE_JOIN_CELLS = frozenset(
    (family, kind, structure, carrier)
    for family, carriers in _NULLSAFE_JOIN_CARRIERS.items()
    for kind in ("inner", "left", "right")
    for structure in _NULLSAFE_JOIN_STRUCTURES.values()
    for carrier in carriers
)


def _nullsafe_join_fields(family, structure, carrier):
    """The representations of each source's fields in a cell: `id`, `v`
    and, by structure, the Int key `k` (S2, S2r, S5) or the value `w` (S3)."""
    storage, domain = _NULLSAFE_JOIN_CARRIERS[family][carrier]
    key = {
        "domain": _NULLSAFE_SAFE_INT,
        "nullable": False,
        "storage": _NULLSAFE_JOIN_CARRIERS[family]["int"][0],
    }
    value = {"domain": domain, "nullable": True, "storage": storage}
    third = {"S2": (key,), "S2r": (key,), "S5": (key,), "S3": (value,)}
    return (key, value, *third.get(structure, ()))


def _on_operations(doc) -> frozenset:
    """Every operation of a JOIN's `on` tree."""
    pending = [
        doc[ref]["predicate"]
        for ref in doc.all("join_body")
        if doc[ref]["predicate"] is not None
    ]
    seen = set()
    while pending:
        value = pending.pop()
        if value in seen or value.kind != "sql_operation":
            continue
        seen.add(value)
        pending.extend(doc[value]["operands"])
    return frozenset(seen)


def _nullsafe_join_cell(doc, ref, family):
    """The cell of the JOIN `on` `same_value` call ``ref`` from the
    document's own structure, as emission derives it from its plan: one
    INNER, LEFT or RIGHT JOIN of two bound sources of different tables under
    one projection whose columns read every JOIN input column, left then
    right; its whole ON one of _NULLSAFE_JOIN_STRUCTURES over each input's
    own scan columns, ``ref`` one of its `same_value` calls; each source the
    fields _nullsafe_join_fields gives; every JOIN column as nullable as its
    field unless the JOIN null-extends it, so `same_value` narrows none; the
    document holds no other operation or record kind. None outside every
    cell. A relation alias `let`, an unused named window or an inlined `def`,
    which emission refuses, changes the document only in source positions
    and source bytes, so this reader cannot tell it from the direct
    program."""
    artifacts = doc.all("artifact")
    if not set(doc.kinds) <= _MYSQL_FLOAT_CELL_KINDS or len(artifacts) != 1:
        return None
    ast = doc[artifacts[0]]["ast"]
    if ast.kind != "sql_join_query":
        return None
    units = doc[ast]["units"]
    if [unit.kind for unit in units] != ["join_body", "row_body"]:
        return None
    join, body = doc[units[0]], doc[units[1]]
    inputs, kind = join["inputs"], join["join_kind"]
    producers = tuple(doc[item]["producer"] for item in inputs)
    if (
        kind not in ("inner", "left", "right")
        or join["equalities"]
        or join["predicate"] is None
        or len(inputs) != 2
        or any(item.kind != "bound_source" for item in producers)
        or len({(doc[s]["namespace"], doc[s]["name"]) for s in producers}) != 2
        or body["scan"].kind != "row_join_use"
        or doc[body["scan"]]["body"] != units[0]
        or body["block_kind"] != "projection"
        or body["predicate"] is not None
    ):
        return None
    sides = {"o": 1, "i": 0} if kind == "right" else {"o": 0, "i": 1}
    seen, calls = set(), []

    def signature(value):
        if value.kind != "sql_operation" or value in seen:
            return None
        seen.add(value)
        fields = doc[value]
        token, operands = (fields["kind"], fields["operator"]), fields["operands"]
        if token in (("logical", "and"), ("logical", "or")) and len(operands) == 2:
            return (token[1], *(signature(child) for child in operands))
        if token == ("not", "not") and len(operands) == 1:
            return ("not", signature(operands[0]))
        if token == ("scalar_call", "same_value"):
            calls.append(value)
        elif token != ("comparison", "=="):
            return None
        return (token[1], *(read(child) for child in operands))

    def read(value):
        if value.kind != "sql_stage_reference":
            return None
        for side, index in sides.items():
            columns = doc[inputs[index]]["columns"]
            if doc[value]["column"] in columns:
                return (side, list(columns).index(doc[value]["column"]))
        return None

    structure = _NULLSAFE_JOIN_STRUCTURES.get(signature(join["predicate"]))
    written = tuple(
        tuple(_json(doc[field]["representation"]) for field in doc[s]["fields"])
        for s in producers
    )
    carrier = next(
        (
            name
            for name in _NULLSAFE_JOIN_CARRIERS.get(family, {})
            if len(written[0]) > 1
            and written[0][1] == _nullsafe_join_fields(family, "S1", name)[1]
        ),
        None,
    )
    stage = tuple(
        doc[column]["source_port"] for item in inputs for column in doc[item]["columns"]
    )
    values = tuple(doc[column]["value"] for column in body["columns"])
    if (
        structure is None
        or carrier is None
        or ref not in calls
        or len(doc.all("sql_operation")) != len(seen)
        or any(value.kind != "sql_stage_reference" for value in values)
        or tuple(doc[doc[value]["column"]]["source_port"] for value in values) != stage
        or any(
            item != _nullsafe_join_fields(family, structure, carrier)
            for item in written
        )
        or any(
            doc[doc[doc[column]["column"]]["realization"]]["nullable"]
            is not (
                bool(doc[column]["nulling"])
                or doc[doc[doc[column]["read"]]["realization"]]["nullable"]
            )
            for column in join["columns"]
        )
        or (family, kind, structure, carrier) not in _NULLSAFE_JOIN_CELLS
    ):
        return None
    return (family, kind, structure, carrier)


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


def _mysql_field_column(doc, column) -> bool:
    """A stage column that is a source field, as emission's mysql_field reads
    it: never a let value, literal, aggregate or window result."""

    fields = doc[column]
    return (
        fields["field"] is not None
        and fields["source_port"] is not None
        and fields["literal"] is None
        and fields["aggregate"] is None
        and fields["window"] is None
    )


def _mysql_field_read(doc, ref) -> bool:
    return (
        type(ref) is Ref
        and ref.kind == "sql_stage_reference"
        and _mysql_field_column(doc, doc[ref]["column"])
    )


# Phase77 S01/S02 (D77.24 whitelist): the record kinds a MySQL cell's
# document may hold, any literal included; any other kind (a parameter,
# fixed value, native use, block, captured or named read, result, JOIN, set
# or window record, a non-row query, or a kind a later schema adds) closes
# its cells.
_MYSQL_CELL_KINDS = frozenset(
    {
        "aggregate_key_column",
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
        "literal_origin",
        "origin",
        "original_requirement",
        "owner",
        "premise",
        "realization",
        "rendered",
        "request",
        "row_body",
        "row_carry_column",
        "row_predicate",
        "row_scan",
        "row_stage_use",
        "row_value_column",
        "scope_definition",
        "scope_use",
        "sql_anchor",
        "sql_literal",
        "sql_null",
        "sql_operation",
        "sql_row_query",
        "sql_stage_reference",
        "sql_symbol",
        "sql_unary",
        "stage_column",
        "terminal_binding",
    }
)


# R08: the bind-safe slot kinds a division cell's document may also hold;
# they close every other cell.
_MYSQL_SLOT_KINDS = frozenset({"fixed_value", "native_use", "sql_parameter"})


def _mysql_cells(doc) -> tuple[frozenset, frozenset, frozenset, frozenset]:
    """The S01 operations, S02 sum columns, S15 `%` and R08 `/` operations in
    their MySQL cells, as emission derives them from the plan
    (mysql_checked_cell, mysql_sum_query, mysql_remainder_cells,
    mysql_division_cells), here from the document alone; a
    relation alias or a
    window, read or not, and an imported source leave a direct read's
    document apart from source positions and the source digest, so only
    emission refuses them. Every
    record is of a kind in _MYSQL_CELL_KINDS, and the one final projection
    body stands over one aggregate body at most, over one WHERE body at
    most, over a source scan, with no window. An S01 operation is the whole
    value of a column of that body, named once, over reads of nullable
    BIGINT source fields; an S02 sum reads a nullable BIGINT source field,
    its aggregate has one non-null Int source field key at most and sums,
    counts and mins only, and the final body only projects the aggregate's
    columns. S15 cells need one projection body straight over the scan,
    each of whose columns is a read of a source field of its tag's carrier
    (_mysql_remainder_carrier) or a `%` named once over two such reads of
    its own tag; any other column closes them. R08 cells need the same body,
    each of whose columns is a read of an Int source field of a SMALLINT, INT
    or BIGINT storage or a `/` named once of an unsigned Int literal and one
    such read, the law restated here (_mysql_division_literal); a bind-safe
    parameter of any other literal closes them, and any parameter closes
    every other cell. The bound of three bodies only ends the walk early: the
    block kinds and the chain that holds every body imply it."""

    empty: tuple[frozenset, frozenset, frozenset, frozenset] = (
        frozenset(),
        frozenset(),
        frozenset(),
        frozenset(),
    )
    if not (_MYSQL_CELL_KINDS | _MYSQL_SLOT_KINDS).issuperset(doc.kinds):
        return empty
    slotted = not _MYSQL_CELL_KINDS.issuperset(doc.kinds)
    bodies = doc.all("row_body")
    if len(bodies) > 3:
        return empty
    finals = [ref for ref in bodies if doc[ref]["final"] is True]
    if len(finals) != 1:
        return empty
    chain = [finals[0]]
    while doc[chain[-1]]["scan"].kind == "row_stage_use":
        inner = doc[doc[chain[-1]]["scan"]]["body"]
        # Only keeps the walk finite: producer order refuses a cycle first.
        if inner in chain:
            return empty
        chain.append(inner)
    kinds = [doc[ref]["block_kind"] for ref in reversed(chain)]
    if (
        doc[chain[-1]]["scan"].kind != "row_scan"
        or len(chain) != len(bodies)
        or any(doc[ref]["window"] is not None for ref in chain)
    ):
        return empty
    aggregate = None
    if kinds in (["aggregate", "projection"], ["where", "aggregate", "projection"]):
        aggregate = chain[1]
    elif kinds not in (["projection"], ["where", "projection"]):
        return empty
    if (
        any(
            (doc[ref]["aggregation"] is not None) is not (ref == aggregate)
            for ref in chain
        )
        or len(doc.all("aggregate_stage")) != (aggregate is not None)
        or slotted
        and aggregate is not None
    ):
        return empty
    final = doc[chain[0]]
    if aggregate is None:
        named: dict[Ref, int] = {}
        for record in doc.records.values():
            pending = list(record.fields.values())
            while pending:
                item = pending.pop()
                if type(item) is tuple:
                    pending.extend(item)
                elif type(item) is Ref:
                    named[item] = named.get(item, 0) + 1
        operations = set()
        for column in final["columns"]:
            value = doc[column]["value"] if column.kind == "row_value_column" else None
            if (
                type(value) is Ref
                and value.kind == "sql_operation"
                and named.get(column) == 1
                and named.get(value) == 1
                and (
                    doc[value]["kind"] in ("sign", "arithmetic")
                    or doc[value]["kind"] == "scalar_call"
                    and doc[value]["operator"] == "abs"
                )
                and doc[value]["operands"]
                and all(
                    _mysql_field_read(doc, item) and _mysql_checked_carrier(doc, item)
                    for item in doc[value]["operands"]
                )
            ):
                operations.add(value)
        remainders = set()
        for column in final["columns"] if kinds == ["projection"] else ():
            value = doc[column]["value"] if column.kind == "row_value_column" else None
            if type(value) is Ref and value.kind == "sql_operation":
                operation = doc[value]
                if not (
                    named.get(column) == 1
                    and named.get(value) == 1
                    and operation["kind"] == "arithmetic"
                    and operation["operator"] == "%"
                    and len(operation["operands"]) == 2
                    and {
                        _mysql_remainder_carrier(doc, item)
                        for item in operation["operands"]
                    }
                    == {doc[operation["realization"]]["tag"]}
                ):
                    remainders.clear()
                    break
                remainders.add(value)
            elif _mysql_remainder_carrier(doc, value) is None:
                remainders.clear()
                break
        divisions, leaves = set(), set()
        for column in final["columns"] if kinds == ["projection"] else ():
            value = doc[column]["value"] if column.kind == "row_value_column" else None
            if type(value) is Ref and value.kind == "sql_operation":
                operation = doc[value]
                pair = operation["operands"]
                if not (
                    named.get(column) == 1
                    and named.get(value) == 1
                    and operation["kind"] == "arithmetic"
                    and operation["operator"] == "/"
                    and doc[operation["realization"]]["tag"] == "Int"
                    and len(pair) == 2
                    and (
                        _mysql_division_literal(doc, pair[0], 0)
                        and _mysql_division_read(doc, pair[1])
                        or _mysql_division_read(doc, pair[0])
                        and _mysql_division_literal(doc, pair[1], 2)
                    )
                ):
                    divisions.clear()
                    break
                divisions.add(value)
                leaves.update(
                    doc[item]["operand"] for item in pair if item.kind == "sql_anchor"
                )
            elif not _mysql_division_read(doc, value):
                divisions.clear()
                break
        if not leaves.issuperset(doc.all("sql_parameter")):
            divisions.clear()
        if slotted:
            return frozenset(), frozenset(), frozenset(), frozenset(divisions)
        return (
            frozenset(operations),
            frozenset(),
            frozenset(remainders),
            frozenset(divisions),
        )
    stage = doc[doc[aggregate]["aggregation"]]
    if (
        len(stage["keys"]) > 1
        or any(
            column.kind != "aggregate_projection_column" for column in final["columns"]
        )
        or any(
            doc[value]["function"] not in ("sum", "count", "min")
            for value in stage["values"]
        )
    ):
        return empty
    for key in stage["keys"]:
        read = doc[key]["read"]
        realization = doc[doc[read]["realization"]]
        if not (
            _mysql_field_column(doc, read)
            and realization["tag"] == "Int"
            and realization["nullable"] is False
        ):
            return empty
    return (
        frozenset(),
        frozenset(
            value
            for value in stage["values"]
            if doc[value]["function"] == "sum"
            and _mysql_field_read(doc, doc[value]["argument"])
            and _mysql_checked_carrier(doc, doc[value]["argument"])
        ),
        frozenset(),
        frozenset(),
    )


def _mysql_division_read(doc, ref) -> bool:
    """R08: a read of an Int source field of a SMALLINT, INT or BIGINT
    storage."""

    if not _mysql_field_read(doc, ref):
        return False
    realization = doc[doc[ref]["realization"]]
    return realization["tag"] == "Int" and dict(realization["storage"]) in (
        {"kind": "my_smallint"},
        {"kind": "my_int"},
        {"kind": "my_bigint"},
    )


def _mysql_division_literal(doc, ref, low) -> bool:
    """R08's law, restated (D77.27): an unsigned Int literal, fixed or bound,
    of value ``low`` or more (0 for a dividend, 2 for a divisor)."""

    if type(ref) is not Ref or ref.kind != "sql_anchor":
        return False
    value = _literal_int(doc, ref)
    return type(value) is int and value >= low


# S15: the carrier of each operand of a MySQL `%` cell and of each field
# read beside one.
_MYSQL_REMAINDER_CARRIERS = {
    "Int": {"kind": "my_bigint"},
    "Float": {"kind": "my_double"},
}


def _mysql_remainder_carrier(doc, ref) -> str | None:
    """The tag of a read of a source field of that tag's S15 carrier."""

    if not _mysql_field_read(doc, ref):
        return None
    realization = doc[doc[ref]["realization"]]
    tag = realization["tag"]
    return (
        tag
        if _MYSQL_REMAINDER_CARRIERS.get(tag) == dict(realization["storage"])
        else None
    )


# S03 (project_sql_emission_sum_forms): the record kinds a paired statement's
# document may hold besides a cell's: one JOIN of two sources, or one named
# upstream definition.
_MYSQL_S03_KINDS = _MYSQL_CELL_KINDS | {
    "join_body",
    "join_column",
    "join_input",
    "row_join_use",
    "row_named_use",
    "sql_join_query",
}
_NON_NEGATIVE = re.compile(r"0|[1-9][0-9]*")


def _mysql_s03(doc) -> frozenset:
    """The S03 sum and conditional sum columns of a paired MySQL statement,
    from the document alone, as emission derives the statement from what is
    written (mysql_s03_statement): every record is of a kind in
    _MYSQL_S03_KINDS, and the one final projection body stands over an
    aggregate body of its definition, over a source scan, one JOIN of two
    sources, or the named use of another definition's projection over its
    aggregate over such a JOIN; no other body exists. An imported source or
    definition and a relation alias leave the same document, so only
    emission refuses them."""

    if not _MYSQL_S03_KINDS.issuperset(doc.kinds):
        return frozenset()
    bodies = doc.all("row_body")
    finals = [ref for ref in bodies if doc[ref]["final"] is True]
    if len(finals) != 1 or len(bodies) > 4:
        return frozenset()
    requests = doc.all("request")
    preserve = (
        len(requests) == 1 and doc[requests[0]]["literal_policy"] == "preserve_literals"
    )
    used: set = set()
    sums: list = []

    def carrier(field):
        return sum_forms.carrier(doc[field]["representation"])

    def test(ref, column):
        """A conditional sum's test: a read, `not`, `is None` or `>` literal."""
        if type(ref) is not Ref:
            return None
        if ref.kind == "sql_stage_reference":
            value = column(doc[ref]["column"])
            return None if value is None else ("is", value)
        if ref.kind != "sql_operation":
            return None
        operation = doc[ref]
        operands = operation["operands"]
        if not operands or operands[0].kind != "sql_stage_reference":
            return None
        value = column(doc[operands[0]]["column"])
        kind = (operation["kind"], operation["operator"], len(operands))
        if value is None:
            return None
        if kind == ("not", "not", 1):
            return "not", value
        if kind == ("null_test", "is null", 1):
            return "none", value
        if kind != ("comparison", ">", 2) or operands[1].kind != "sql_anchor":
            return None
        anchor = doc[operands[1]]
        literal = anchor["operand"]
        if anchor["tag"] != "Int" or literal.kind != "sql_literal":
            return None
        written = doc[literal]["value"]
        if (
            type(written) is not Fixed
            or written.tag != "Int"
            or type(written.wire) is not str
            or not _NON_NEGATIVE.fullmatch(written.wire)
        ):
            return None
        return ">", value, int(written.wire)

    def level(final, nested):
        """The level of a projection body over its aggregate body: (level,
        its terminals to their items, the upstream level if any), or None."""
        projection = doc[final]
        scan = projection["scan"]
        if (
            projection["block_kind"] != "projection"
            or projection["predicate"] is not None
            or projection["window"] is not None
            or projection["aggregation"] is not None
            or scan.kind != "row_stage_use"
        ):
            return None
        below = doc[scan]["body"]
        body = doc[below]
        if (
            below in used
            or final in used
            or body["block_kind"] != "aggregate"
            or body["predicate"] is not None
            or body["window"] is not None
            or body["aggregation"] is None
            or body["definition"] != projection["definition"]
        ):
            return None
        used.update((final, below))
        scan = body["scan"]
        join, upstream = None, None
        sides = {}

        def side(stage):
            """A stage column of a source field: its side and field."""
            value = doc[stage]
            if not _mysql_field_column(doc, stage) or value["field"] not in sides:
                return None
            return sides[value["field"]], value["field"], carrier(value["field"])

        def column(stage):
            """A column this level reads: a source, JOIN or upstream one."""
            terminal = doc[stage]["terminal"]
            if scan.kind == "row_named_use":
                assert upstream is not None
                item = upstream[1].get(terminal)
                return None if item is None else ("U", item, None)
            expected = "source_port" if scan.kind == "row_scan" else "join_port"
            return side(stage) if terminal.kind == expected else None

        if scan.kind == "row_scan":
            sides = {field: "A" for field in doc[doc[scan]["realization"]]["fields"]}
        elif scan.kind == "row_join_use":
            joined = doc[doc[scan]["body"]]
            inputs = [doc[item] for item in joined["inputs"]]
            predicate = joined["predicate"]
            operands = (
                doc[predicate]["operands"]
                if type(predicate) is Ref and predicate.kind == "sql_operation"
                else ()
            )
            if (
                len(inputs) != 2
                or joined["equalities"]
                or [item["ordinal"] for item in inputs] != [0, 1]
                or any(item["producer"].kind != "bound_source" for item in inputs)
                or inputs[0]["producer"] == inputs[1]["producer"]
                or len(operands) != 2
                or doc[predicate]["kind"] != "comparison"
                or doc[predicate]["operator"] != "=="
                or any(item.kind != "sql_stage_reference" for item in operands)
            ):
                return None
            sides = {
                field: side
                for side, item in zip("AB", inputs, strict=True)
                for field in doc[item["producer"]]["fields"]
            }
            join = (
                joined["join_kind"],
                side(doc[operands[0]]["column"]),
                side(doc[operands[1]]["column"]),
                *(
                    tuple(carrier(field) for field in doc[item["producer"]]["fields"])
                    for item in inputs
                ),
            )
            if None in join:
                return None
        elif scan.kind == "row_named_use" and not nested:
            upper = doc[scan]["body"]
            if doc[upper]["definition"] == body["definition"]:
                return None
            upstream = level(upper, True)
            if upstream is None:
                return None
        else:
            return None
        stage = doc[body["aggregation"]]
        keys = tuple(column(doc[key]["read"]) for key in stage["keys"])
        if None in keys:
            return None
        outputs = {}
        if len(body["columns"]) != len(body["terminals"]) or len(
            projection["columns"]
        ) != len(projection["terminals"]):
            return None
        for ref, terminal in zip(body["columns"], body["terminals"], strict=True):
            current = doc[ref]
            if ref.kind == "aggregate_key_column":
                item = ("key", column(current["read"]))
            elif (
                ref.kind != "aggregate_value_column"
                or current["distinct"]
                or current["order_by"]
                or current["extra_arguments"]
                or type(current["argument"]) is not Ref
                or current["argument"].kind != "sql_stage_reference"
            ):
                return None
            else:
                value = column(doc[current["argument"]]["column"])
                function = current["function"]
                if function in ("sum", "count") and current["delimiter"] is None:
                    item = (function, value)
                elif function == "filtered_sum":
                    condition = test(current["delimiter"], column)
                    item = ("fsum", value, condition) if condition else (function, None)
                else:
                    return None
                if function != "count":
                    sums.append(ref)
            if item[1] is None:
                return None
            outputs[terminal] = item
        if [item for item in outputs.values() if item[0] == "key"] != [
            ("key", key) for key in keys
        ]:
            return None
        items, ports = [], {}
        for ref, terminal in zip(
            projection["columns"], projection["terminals"], strict=True
        ):
            item = (
                outputs.get(doc[doc[ref]["read"]]["terminal"])
                if ref.kind == "aggregate_projection_column"
                else None
            )
            if item is None:
                return None
            items.append(item)
            ports[terminal] = item
        return (join, keys, tuple(items)), ports, upstream

    top = level(finals[0], False)
    if top is None or len(used) != len(bodies):
        return frozenset()
    levels = (top[0],) if top[2] is None else (top[2][0], top[0])
    return frozenset(sums) if sum_forms.paired(levels, preserve) else frozenset()


def _mysql_checked_carrier(doc, ref) -> bool:
    """The S01/S02 operand carrier: a nullable MySQL BIGINT."""

    realization = doc[doc[ref]["realization"]]
    return (
        realization["tag"] == "Int"
        and dict(realization["storage"]) == {"kind": "my_bigint"}
        and realization["nullable"] is True
    )


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
    averages binary64, PostgreSQL SUM(Int) is bigint before and after (a
    MySQL one is the guarded SUM, uncast), and a PostgreSQL VAR_SAMP or
    VAR_POP is cast to float8 once. A PostgreSQL SUM or AVG of a float8 is
    already binary64."""
    if function in {"avg", "sum"} and argument_tag == "Float":
        return None, None
    if function == "filtered_sum":
        function = "sum"
    if function == "avg":
        return ("pg_catalog.float8" if family == "postgres" else "DOUBLE"), None
    if function == "sum":
        if family != "postgres":
            return None, None
        return "pg_catalog.int8", "pg_catalog.int8"
    if function in _SPREAD_FUNCTIONS:
        return None, ("pg_catalog.float8" if family == "postgres" else None)
    if function in {"median", "quantile"}:
        # PERCENTILE_CONT orders by the float8 image of each Int value.
        return "pg_catalog.float8", None
    return None, None


def _rank_cast(family: str, function: str) -> str | None:
    """MySQL sends a rank or bucket as BIGINT UNSIGNED, so it is cast to SIGNED."""
    return (
        "SIGNED"
        if family == "mysql"
        and function in {"row_number", "rank", "dense_rank", "ntile"}
        else None
    )


def _mysql_int_extremum(family: str, function: str, argument) -> bool:
    """A grouped MySQL MIN or MAX of a SMALLINT or INT, over a base table, a
    view or a stage alike: MySQL may return it as BIGINT, so it is always cast
    to SIGNED (PL.67, PL.73)."""
    return (
        family == "mysql"
        and function in {"min", "max"}
        and argument is not None
        and argument.get("tag") == "Int"
        and argument.get("storage") in ({"kind": "my_smallint"}, {"kind": "my_int"})
    )


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


def _mysql_float_membership(doc) -> bool:
    """R01 from the document (emission: rows.mysql_float_memberships): a
    Float `in` or `not in` read of a capturing let's inline body that is no
    SELECT item, that is, not reached from a value column of a projection
    body through operations alone, or reached from a predicate."""

    def reach(roots) -> set:
        seen, pending = set(), list(roots)
        while pending:
            item = pending.pop()
            if item in seen:
                continue
            seen.add(item)
            if item.kind == "sql_operation":
                pending.extend(doc[item]["operands"])
            elif item.kind == "sql_unary":
                pending.append(doc[item]["operand"])
        return seen

    selected = reach(
        doc[column]["value"]
        for body in doc.all("row_body")
        if doc[body]["block_kind"] == "projection"
        for column in doc[body]["columns"]
        if column.kind == "row_value_column"
    )
    filtered = reach(doc[item]["value"] for item in doc.all("row_predicate"))
    return any(
        doc[read]["kind"] in ("in", "not_in")
        and _inline_producer(doc, doc[doc[read]["target"]]["producer"])
        and _value_tag(doc, doc[read]["operands"][0]) == "Float"
        # `in filtered` holds only of a forged document that shares one
        # read between a value column and a predicate; no test forges one.
        and (read not in selected or read in filtered)
        for read in doc.all("sql_block_read")
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
        _require(
            family != "mysql" or not _mysql_float_membership(doc),
            "MySQL Float block membership",
        )
        cells = _mysql_scalar_cells(doc) if family == "mysql" else {}
        _, _, mysql_remainders, mysql_divisions = (
            _mysql_cells(doc)
            if family == "mysql"
            else (frozenset(), frozenset(), frozenset(), frozenset())
        )
        on_operations = _on_operations(doc)
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
                # Float equality of two row reads; only a qualified cell emits,
                # a JOIN `on` `same_value` call's in its null-safe JOIN cell.
                _require(
                    _mysql_float_cell(doc, ref) in _MYSQL_FLOAT_ROW_CELLS
                    or _nullsafe_join_cell(doc, ref, family) is not None,
                    "MySQL Float row comparison cell",
                )
            if (
                family == "mysql"
                and op["kind"] == "arithmetic"
                and op["operator"] == "%"
            ):
                # S15: a MySQL `%` only in its cell, NULL for a zero divisor.
                _require(
                    ref in mysql_remainders,
                    "MySQL Float remainder cell"
                    if result["tag"] == "Float"
                    else "MySQL Int remainder cell",
                )
                _require(
                    result["nullable"] is not False
                    and (
                        _is_float(result, family)
                        or _is_realization(
                            result,
                            "Int",
                            {"kind": "my_bigint"},
                            {
                                "kind": "int_range",
                                "min": str(_I64_MIN),
                                "max": str(_I64_MAX),
                            },
                        )
                    ),
                    "MySQL remainder carrier",
                )
            if (op["kind"], op["operator"]) == ("scalar_call", "same_value") and (
                ref in on_operations
            ):
                # Phase77 S06 null-safe JOIN: an ON `same_value` emits only in
                # a qualified cell.
                _require(
                    _nullsafe_join_cell(doc, ref, family) is not None,
                    "null-safe JOIN condition cell",
                )
            if (
                family == "mysql"
                and op["kind"] == "arithmetic"
                and op["operator"] == "/"
            ):
                # R08: a MySQL `/` only in its Int cell, NULL for a zero
                # divisor.
                _require(ref in mysql_divisions, "MySQL Int division cell")
                _require(
                    result["nullable"] is not False
                    and _is_realization(
                        result,
                        "Int",
                        {"kind": "my_bigint"},
                        {
                            "kind": "int_range",
                            "min": str(_I64_MIN),
                            "max": str(_I64_MAX),
                        },
                    ),
                    "MySQL division carrier",
                )
            folded = tuple(_float_literal_value(doc, child) for child in op["operands"])
            if (
                op["kind"] == "arithmetic"
                and op["operator"] in {"+", "-", "*"}
                and result["tag"] == "Float"
                and len(folded) == 2
                and None not in folded
            ):
                # The emitter's static fold: no infinity, and no product of two
                # non-zero values that rounds to zero (PostgreSQL's 22003).
                left, right = cast(tuple[float, float], folded)
                value = {"+": left + right, "-": left - right, "*": left * right}[
                    op["operator"]
                ]
                _require(
                    math.isfinite(value)
                    and (op["operator"] != "*" or value != 0.0 or 0.0 in folded),
                    "Float literal fold",
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
        mysql_sums = _mysql_cells(doc)[1] if family == "mysql" else frozenset()
        # A MySQL `first` or `last` only in the S13 statement class.
        self.ranked = _ranked_stage(doc, family)
        mysql_s03 = _mysql_s03(doc) if family == "mysql" else frozenset()
        for ref in doc.all("aggregate_value_column"):
            column = doc[ref]
            expected = _AGGREGATE_SPELLING[family].get(column["function"])
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
            if _mysql_int_extremum(family, column["function"], argument):
                # A my_signed_int with its argument's own range.
                result_cast = "SIGNED"
                _require(
                    argument is not None
                    and dict(result["storage"]) == {"kind": "my_signed_int"}
                    and dict(result["domain"]) == dict(argument["domain"]),
                    "signed extreme result",
                )
            elif column["function"] in {"min", "max"} and argument is not None:
                # Any other extreme keeps its argument's carrier and range; one
                # with no argument is the re-rendering's aggregate signature.
                _require(
                    dict(result["storage"]) == dict(argument["storage"])
                    and dict(result["domain"]) == dict(argument["domain"]),
                    "extreme result",
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
                # Q1: the checked bigint narrowing bounds an Int argument's
                # exact sum, NULL for an empty input; on MySQL only an S02
                # cell's guarded SUM over a nullable BIGINT field.
                _require(
                    (
                        family == "postgres"
                        and (_value_realization(doc, column["argument"]) or {}).get(
                            "tag"
                        )
                        == "Int"
                        or family == "mysql"
                        and (ref in mysql_sums or ref in mysql_s03)
                    )
                    and _is_realization(
                        doc[doc[column["column"]]["realization"]],
                        "Int",
                        {
                            "kind": "pg_int8"
                            if family == "postgres"
                            else "my_signed_int"
                        },
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
                # PostgreSQL only, but for an S03 MySQL conditional sum: a
                # Bool test, of a sum in the delimiter slot after its Int
                # argument; a non-null bigint result, a count's bounded by the
                # count premise, a sum's by its checked CAST or guarded SUM.
                counted = column["function"] == "filtered_count"
                test = column["argument"] if counted else column["delimiter"]
                low = 0 if counted else -(1 << 63)
                result = doc[doc[column["column"]]["realization"]]
                _require(
                    (family == "postgres" or family == "mysql" and ref in mysql_s03)
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
                        {
                            "kind": "pg_int8"
                            if family == "postgres"
                            else "my_signed_int"
                        },
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
        if self.family == "mysql":
            # Phase77 S07: a MySQL Float group key emits only in a qualified
            # cell.
            keyed = [doc[c]["read"] for c in doc.all("aggregate_key_column")]
            if any(doc[doc[item]["realization"]]["tag"] == "Float" for item in keyed):
                _require(
                    _mysql_float_key_cell(doc) in _MYSQL_FLOAT_KEY_CELLS,
                    "MySQL Float key cell",
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
            # row count, and R13's casts; a MySQL rank or bucket is cast to
            # SIGNED; every other window has no cast.
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
                _require(
                    casts == (None, _rank_cast(self.family, function)), "window cast"
                )
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
            elif column["function"] in {"lag", "lead"}:
                # A MySQL default is the third argument whatever its role says.
                _require(
                    tuple(argument["role"] for argument in arguments)
                    == ("value", "offset", "default")[: len(arguments)],
                    "window structural argument roles",
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
        # Last, so every document an earlier check refuses keeps its detail.
        _Render(self.doc).run()


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
            elif self.family == "mysql" and column["function"] == "filtered_sum":
                # S03: COALESCE(the guarded SUM of CASE WHEN test THEN x END, 0).
                case = [
                    ("aggregate_filter_open", "CASE WHEN "),
                    ("aggregate_filter_then", " THEN "),
                    ("aggregate_filter_close", " END"),
                ]
                expected = [("aggregate_zero_open", "COALESCE(")]
                for role in (
                    "aggregate_guard_open",
                    "aggregate_guard_high",
                    "aggregate_guard_low",
                ):
                    expected += [(role, schema.SYNTAX[role]), *case]
                expected += [
                    ("aggregate_guard_close", schema.SYNTAX["aggregate_guard_close"]),
                    ("aggregate_zero_close", ", 0)"),
                ]
                _require(
                    aggregate_tokens == expected,
                    "guarded conditional sum token sequence",
                )
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
            elif (
                self.family == "mysql"
                and column["function"] == "sum"
                and column["argument"] is not None
                and (_value_realization(doc, column["argument"]) or {}).get("tag")
                == "Int"
            ):
                # S02: the guarded SUM, its argument read three times.
                expected = [
                    (role, schema.SYNTAX[role])
                    for role in (
                        "aggregate_guard_open",
                        "aggregate_guard_high",
                        "aggregate_guard_low",
                        "aggregate_guard_close",
                    )
                ]
                _require(aggregate_tokens == expected, "guarded sum token sequence")
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
                # R08: a MySQL `/` is only ever an Int cell, MySQL's DIV.
                "arithmetic_operator": " DIV "
                if self.family == "mysql" and operator == "/"
                else " " + operator + " ",
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
        self.mysql_checked, _, self.mysql_remainders, _ = (
            _mysql_cells(doc)
            if family == "mysql"
            else (frozenset(), frozenset(), frozenset(), frozenset())
        )

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
        if self.family == "mysql":
            return self.mysql_target_checked(ref)
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

    def mysql_target_checked(self, ref: Ref) -> tuple[int, int] | object | None:
        """S01: an operation in its MySQL cell (_mysql_cells) over nullable
        BIGINT fields, whose physical range is all of signed 64 bits, relies
        on MySQL's checked BIGINT operator; any other MySQL operation claims
        no target check."""
        if ref not in self.mysql_checked or ref in self.mysql_remainders:
            # An S15 `%` stays inside signed 64 bits: |l % r| < |r|.
            return None
        op = self.doc[ref]
        full = (_I64_MIN, _I64_MAX)
        count = len(op["operands"])
        if op["kind"] == "sign" and count == 1:
            interval = (-_I64_MAX, -_I64_MIN) if op["operator"] == "-" else full
        elif op["kind"] == "scalar_call" and count == 1:
            interval = (0, -_I64_MIN)
        elif (
            op["kind"] == "arithmetic"
            and count == 2
            and op["operator"] in ("+", "-", "*")
        ):
            interval = {
                "+": (2 * _I64_MIN, 2 * _I64_MAX),
                "-": (_I64_MIN - _I64_MAX, _I64_MAX - _I64_MIN),
                "*": (_I64_MIN * _I64_MAX, _I64_MIN * _I64_MIN),
            }[op["operator"]]
        else:
            return self._UNKNOWN
        return self.checked(interval) if interval != full else None


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
            and dict(result["storage"])
            == {"kind": "pg_int8" if self.family == "postgres" else "my_signed_int"}
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


# -- re-rendering: the SQL is the rendering of the records -------------------
#
# Every token, offset, SQL byte and expression range must be what the emitter
# writes for these records, and every record field that steers which tokens
# are written is closed here to the pipeline's image (semantic checks, stage
# construction, AST assembly and emitter; D77.54 keeps the closure here, never
# in _Check). It reads only records, so it never imports the emitter. Any
# difference is the one `rendering` rejection; the subcheck stays private on
# _Mismatch.check. The tables below and the template data beside them are
# pure's own copy of the pipeline (PL.60): the emitter never reads them, so
# a change to a rendered shape or the pipeline's range updates both.

# A fixed scalar call template is a tuple of steps: (role, text) writes one
# syntax token, an int i renders operand i, so its arity is max(i) + 1 (0 for
# none). A variadic call is (opening, separator) around every operand,
# closed by ")".
_OPEN, _SEP, _CLOSE = "scalar_call_open", "scalar_call_separator", "scalar_call_close"
_INDEX_OPEN, _INDEX_CLOSE = (
    "scalar_call_index_cast_open",
    "scalar_call_index_cast_close",
)
_NEST_OPEN, _NEST_CLOSE = "scalar_call_nested_open", "scalar_call_nested_close"


def _field_templates(family, opening, closing):
    return {
        (family, name, None): (
            (_OPEN, opening.format(name.upper())),
            0,
            (_CLOSE, closing),
        )
        for name in ("year", "month", "day", "hour", "minute")
    }


# By (family, function, shape): `round` by its arity or result tag,
# `date_trunc` by its result tag.
_SCALAR_CALL_TEMPLATES = {
    ("postgres", "now", None): (
        (_OPEN, "(statement_timestamp() AT TIME ZONE 'UTC'"),
        (_CLOSE, ")"),
    ),
    ("postgres", "round", "2"): (
        (_OPEN, "round("),
        0,
        (_SEP, ", CAST("),
        1,
        (_CLOSE, " AS pg_catalog.int4))"),
    ),
    ("postgres", "round", "Decimal"): ((_OPEN, "round("), 0, (_CLOSE, ")")),
    ("postgres", "round", "Float"): (
        (_OPEN, "(CASE WHEN abs(("),
        0,
        (_SEP, ") - trunc("),
        0,
        (_SEP, ") ) >= 0.5 THEN trunc("),
        0,
        (_SEP, " ) + (CASE WHEN "),
        0,
        (_SEP, " < 0 THEN -1.0 ELSE 1.0 END) ELSE trunc("),
        0,
        (_CLOSE, " ) END)"),
    ),
    ("postgres", "lpad", None): (
        (_OPEN, "(CASE WHEN length("),
        0,
        (_SEP, ") >= "),
        1,
        (_SEP, " THEN "),
        0,
        (_SEP, " ELSE lpad("),
        0,
        (_SEP, ", CAST("),
        1,
        (_SEP, " AS pg_catalog.int4), "),
        2,
        (_CLOSE, ") END)"),
    ),
    ("postgres", "add_months", None): (
        (_OPEN, "CAST(("),
        0,
        (_SEP, " + make_interval(months => CAST("),
        1,
        (_CLOSE, " AS pg_catalog.int4))) AS date)"),
    ),
    ("postgres", "date_trunc", "Date"): (
        (_OPEN, "CAST(date_trunc("),
        0,
        (_SEP, ", CAST("),
        1,
        (_CLOSE, " AS timestamp))"),
        (_CLOSE, " AS date)"),
    ),
    ("postgres", "date_trunc", "Timestamp"): (
        (_OPEN, "date_trunc("),
        0,
        (_SEP, ", "),
        1,
        (_CLOSE, ")"),
    ),
    ("postgres", "substr", None): (
        (_OPEN, "substring("),
        0,
        (_SEP, " FROM "),
        (_INDEX_OPEN, "CAST("),
        1,
        (_INDEX_CLOSE, " AS pg_catalog.int4)"),
        (_SEP, " FOR "),
        (_INDEX_OPEN, "CAST("),
        2,
        (_INDEX_CLOSE, " AS pg_catalog.int4)"),
        (_CLOSE, ")"),
    ),
    ("postgres", "len", None): (
        (_OPEN, "CAST(length("),
        0,
        (_CLOSE, ") AS pg_catalog.int8)"),
    ),
    ("postgres", "date_of", None): ((_OPEN, "CAST("), 0, (_CLOSE, " AS date)")),
    ("postgres", "same_value", None): (
        (_OPEN, "("),
        0,
        (_SEP, " IS NOT DISTINCT FROM "),
        1,
        (_CLOSE, ")"),
    ),
    ("postgres", "contains", None): (
        (_OPEN, "(strpos("),
        0,
        (_SEP, ", "),
        1,
        (_CLOSE, ") > 0)"),
    ),
    ("postgres", "starts_with", None): (
        (_OPEN, "(left("),
        0,
        (_SEP, ", "),
        (_NEST_OPEN, "length("),
        1,
        (_NEST_CLOSE, ")"),
        ("scalar_call_operator", " ) = "),
        1,
        (_CLOSE, ")"),
    ),
    ("postgres", "ends_with", None): (
        (_OPEN, "(right("),
        0,
        (_SEP, ", "),
        (_NEST_OPEN, "length("),
        1,
        (_NEST_CLOSE, ")"),
        ("scalar_call_operator", " ) = "),
        1,
        (_CLOSE, ")"),
    ),
    ("postgres", "sign", None): (
        (_OPEN, "CAST(sign("),
        0,
        (_CLOSE, ") AS pg_catalog.int8)"),
    ),
    **_field_templates("postgres", "CAST(EXTRACT({} FROM ", ") AS pg_catalog.int8)"),
    ("mysql", "now", None): ((_OPEN, "UTC_TIMESTAMP(6"), (_CLOSE, ")")),
    # MySQL LPAD() cuts a longer text too; its width takes no int4 cast.
    ("mysql", "lpad", None): (
        (_OPEN, "CASE WHEN CHAR_LENGTH("),
        0,
        (_SEP, ") >= "),
        1,
        (_SEP, " THEN "),
        0,
        (_SEP, " ELSE LPAD("),
        0,
        (_SEP, ", "),
        1,
        (_SEP, ", "),
        2,
        (_CLOSE, ") END"),
    ),
    ("mysql", "substr", None): (
        (_OPEN, "SUBSTRING("),
        0,
        (_SEP, ", "),
        1,
        (_SEP, ", "),
        2,
        (_CLOSE, ")"),
    ),
    ("mysql", "len", None): ((_OPEN, "CAST(CHAR_LENGTH("), 0, (_CLOSE, ") AS SIGNED)")),
    ("mysql", "date_of", None): ((_OPEN, "DATE("), 0, (_CLOSE, ")")),
    # Also a JOIN `on` null-safe cell, Float included (8795c02c).
    ("mysql", "same_value", None): ((_OPEN, "("), 0, (_SEP, " <=> "), 1, (_CLOSE, ")")),
    ("mysql", "contains", None): (
        (_OPEN, "(INSTR("),
        0,
        (_SEP, ", "),
        1,
        (_CLOSE, ") > 0)"),
    ),
    ("mysql", "starts_with", None): (
        (_OPEN, "(LEFT("),
        0,
        (_SEP, ", "),
        (_NEST_OPEN, "CHAR_LENGTH("),
        1,
        (_NEST_CLOSE, ")"),
        ("scalar_call_operator", " ) = "),
        1,
        (_CLOSE, ")"),
    ),
    ("mysql", "ends_with", None): (
        (_OPEN, "(RIGHT("),
        0,
        (_SEP, ", "),
        (_NEST_OPEN, "CHAR_LENGTH("),
        1,
        (_NEST_CLOSE, ")"),
        ("scalar_call_operator", " ) = "),
        1,
        (_CLOSE, ")"),
    ),
    ("mysql", "sign", None): ((_OPEN, "CAST(SIGN("), 0, (_CLOSE, ") AS SIGNED)")),
    **_field_templates("mysql", "CAST({}(", ") AS SIGNED)"),
}
_SCALAR_CALL_VARIADIC = {
    "postgres": {
        "lower": ("lower(", ", "),
        "upper": ("upper(", ", "),
        "trim": ("trim(", ", "),
        "replace": ("replace(", ", "),
        "abs": ("abs(", ", "),
        "nullif": ("NULLIF(", ", "),
        "coalesce": ("COALESCE(", ", "),
        # PostgreSQL concat() skips NULL; `||` is NULL when any argument is.
        "concat": ("(", " || "),
    },
    "mysql": {
        "lower": ("LOWER(", ", "),
        "upper": ("UPPER(", ", "),
        "trim": ("TRIM(", ", "),
        "replace": ("REPLACE(", ", "),
        "abs": ("ABS(", ", "),
        "nullif": ("NULLIF(", ", "),
        "coalesce": ("COALESCE(", ", "),
    },
}
# The semantic catalog's arity of each variadic-spelled call; coalesce and
# concat take two or more (builtin_signature, _coalesce_value_type).
_CALL_ARITY = {
    **dict.fromkeys(("lower", "upper", "trim", "abs"), 1),
    "nullif": 2,
    "replace": 3,
}
_CAST_TAG = {"int_to_float": "Float", "int_to_text": "Text"}
# Each aggregate function's emitted name by target: _Check's "aggregate
# spelling" and the re-rendering read this one table. MySQL spells a
# variance or deviation as its own primitive, uncast and without SQRT (S05),
# and a `first` or `last` as MAX over its ranked derived table (S13).
_AGGREGATE_SPELLING = {
    "postgres": {
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
        "first": "ARRAY_AGG",
        "last": "ARRAY_AGG",
    }
}
_AGGREGATE_SPELLING["mysql"] = {
    **_AGGREGATE_SPELLING["postgres"],
    "stddev": "STDDEV_SAMP",
    "variance": "VAR_SAMP",
    "pvariance": "VAR_POP",
    "pstdev": "STDDEV_POP",
    "first": "MAX",
    "last": "MAX",
}

_SCOPE = PlanRef(schema.SCOPE_KIND, 0)
_VALUE_REFS = frozenset({"sql_stage_reference", "sql_any_reference"})
_REALIZED = frozenset(
    {
        "sql_stage_reference",
        "sql_any_reference",
        "sql_operation",
        "sql_block_read",
        "sql_any_read",
        "sql_captured_reference",
    }
)
_NARROW_PG_INTS = ("pg_int2", "pg_int4")
_FILTERED = frozenset({"filtered_count", "filtered_sum", "group_all", "group_any"})
_GROUP_TEST = frozenset({"group_all", "group_any"})
_ORDERED_VALUE = frozenset({"first", "last"})
_ORDERED = frozenset({"string_agg", *_ORDERED_VALUE})
_QUANTILE = frozenset({"median", "quantile"})
# A PostgreSQL deviation is the SQRT of its variance.
_ROOT = frozenset({"pstdev", "stddev"})
_I32_MAX = (1 << 31) - 1
# project_sql_emission_windows.STRUCTURAL_COUNT_INTERVAL: PostgreSQL's
# structural parameters are int4, MySQL's signed64.
_COUNT_INTERVAL = {
    ("postgres", "offset"): (0, _I32_MAX),
    ("postgres", "bucket"): (1, _I32_MAX),
    ("postgres", "position"): (1, _I32_MAX),
    ("mysql", "offset"): (0, _I64_MAX),
    ("mysql", "bucket"): (1, _I64_MAX),
    ("mysql", "position"): (1, _I64_MAX),
}
# windows.ARITY and resolved_arguments: every role tuple a window function
# carries; an aggregate over a window reaches pure on PostgreSQL only.
_NAVIGATION = (("value",), ("value", "offset"), ("value", "offset", "default"))
_WINDOW_SIGNATURES = {
    **dict.fromkeys(
        ("row_number", "rank", "dense_rank", "percent_rank", "cume_dist"), ((),)
    ),
    "ntile": (("bucket",),),
    "lag": _NAVIGATION,
    "lead": _NAVIGATION,
    "first_value": (("value",),),
    "last_value": (("value",),),
    "nth_value": (("value", "position"),),
}
_WINDOW_AGGREGATE_SIGNATURES = {
    **dict.fromkeys(("sum", "avg", "min", "max"), (("value",),)),
    "count": ((), ("value",)),
}
# windows.FRAME_INSENSITIVE and window_semantics' frame policy: a ranking,
# distribution or navigation window never has a frame; every other window has
# one (an omitted frame is materialized as RANGE ... CURRENT ROW).
_FRAME_INSENSITIVE = frozenset(
    {
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    }
)
# window_semantics._WINDOW_FRAME_BOUND_CATEGORY_ORDER (compiled_specification).
_FRAME_BOUND_ORDER = (
    "unbounded_preceding",
    "offset_preceding",
    "current_row",
    "offset_following",
    "unbounded_following",
)
# windows.FRAME_UNIT_TARGETS, EXCLUSION_TARGETS and MYSQL_WINDOW_LIMIT.
_MYSQL_FRAME_UNITS = frozenset({"rows", "range"})
_MYSQL_WINDOW_LIMIT = 127
# project_sql_emission_aggregation: DISTINCT only in the two distinct counts,
# a row count only for count. MySQL renders no string_agg or quantile and a
# `first` or `last` only ranked; _Check admits its group tests, conditional
# count and tuple count (S10, S11) on PostgreSQL only, so they fail closed.
_DISTINCT_AGGREGATES = frozenset({"count_distinct", "count_distinct_tuple"})
_MYSQL_AGGREGATES = frozenset(_AGGREGATE_SPELLING["mysql"]) - {
    "string_agg",
    "median",
    "quantile",
    "count_distinct_tuple",
    *_ORDERED_VALUE,
    *_FILTERED - {"filtered_sum"},
}
# project_sql_emission_ast's body construction (project_compiled_lowering and
# the compiled verifier's ROW_PREDICATE alike): one block kind per generated
# SELECT, and each kind writes only its own column kinds.
_FILTER_KINDS = frozenset({"where", "satisfying", "qualify"})
_BODY_COLUMNS = {
    "let": frozenset({"row_carry_column", "row_value_column"}),
    **dict.fromkeys(_FILTER_KINDS, frozenset({"row_carry_column"})),
    "window": frozenset({"row_carry_column", "window_column"}),
    "aggregate": AGGREGATE_COLUMNS,
    "projection": frozenset(
        {
            "row_carry_column",
            "row_value_column",
            "aggregate_projection_column",
            "window_projection_column",
        }
    ),
}
# project_sql_emission_ast: a let, filter or window body carries one column
# per input port, in port order, before its own columns.
_CARRYING = frozenset({"let", "window", *_FILTER_KINDS})
# pure's "operation arity": the operands each operation kind writes.
_OPERATION_ARITY = {
    **dict.fromkeys(("sign", "null_test", "not", "cast"), 1),
    **dict.fromkeys(("between", "conditional"), 3),
    **dict.fromkeys(("comparison", "logical", "arithmetic"), 2),
}
# The aggregate branches that read the delimiter slot themselves.
_DELIMITED = frozenset({"filtered_sum", *_ORDERED, *_QUANTILE})
# MySQL's guarded SUM of an Int (S02, S03), between reads of its argument.
_MYSQL_SUM_GUARD = tuple(
    (role, schema.SYNTAX[role])
    for role in (
        "aggregate_guard_open",
        "aggregate_guard_high",
        "aggregate_guard_low",
        "aggregate_guard_close",
    )
)


def _canonical_integer(text, low, high) -> bool:
    """A canonical decimal integer token inside [low, high] (low >= 0)."""
    return (
        type(text) is str
        and text.isascii()
        and text.isdigit()
        and str(int(text)) == text
        and low <= int(text) <= high
    )


class _Mismatch(_Reject):
    """The records do not render to the observed SQL; ``check`` names the
    private subcheck, the public detail is always `rendering`."""

    def __init__(self, check: str) -> None:
        super().__init__(Status.INVALID_RELATION, "rendering")
        self.check = check


class _Render:
    """Records-only re-rendering of one checked observation, compared token by
    token, as verification's take() streams: the first difference stops it, so
    the work is bounded by the document's own event count.

    Closure, in the order the reviews found each step. Free text the emitter
    copies (window literals, LIMIT, parameter indexes, Decimal parameters,
    frame offsets) is canonical and inside the emitter's interval; aggregate
    spellings and casts are derived from the function, never copied.
    Signatures, frame policy and bound order, GROUPS and offset RANGE orders
    and named windows follow window_semantics and windows.build_stage. Each
    row body is one block kind with only that kind's columns, a WHERE exactly
    on a filter kind, a GROUP BY stage exactly on an aggregate (its columns
    are its keys then its values) and a window stage exactly on a window; a
    container the SQL writes has the contents the pipeline gives it. SQL
    resolves names, so every identity is compared by the name written: each
    `scope.column` names a column of a relation visible there, that relation
    exposes distinct names (MySQL casefolded) and identities, the identity is
    the one the record reads, anchored to the SQL position that writes it, and
    the alias written is that of the relation whose record lists the read.
    Lists the pipeline fixes (JOIN inputs and columns, set operands, result
    bodies) read their relation's columns by position. A chain read (a stage,
    result or JOIN use, a chained JOIN's left input) reads the body realized
    just before its reader in one definition, at its place in the chain, a
    result use only a projection; every other read, and the statement, reads
    a definition's last unit; every unit is written once and every CTE is
    read. A projection's hidden columns are the distinct keys an ORDER without
    DISTINCT reads, carried last in the order its items first read them, and
    an item reads an export only as an aggregate composition or, under
    DISTINCT, a bare value; a filter's kind is the stage it filters; and a
    call's arity, a cast, an anchor's carrier, a block read's kind and inputs
    and PostgreSQL's $n are the ones the pipeline writes."""

    def __init__(self, doc: _Doc) -> None:
        self.doc = doc
        artifact = doc[Ref(*schema.ROOT)]
        self.family = doc[artifact["request"]]["family"]
        self.quote = schema.QUOTES[self.family]
        self.tokens = 0
        self.ranges: list[tuple[str, Any, int, int]] = []
        self.offset = 0
        # alias -> {column name: identity} of the relations in scope
        self.visible: dict[str, dict[str, Any]] = {}
        # the outermost row body's scan alias, which a capture writes
        self.reader: str | None = None
        self.depth = 0  # inline bodies open around the SQL being written
        self.owned: dict[str, Any] = {}  # JOIN input alias -> its reads, inside ON
        self.any_scopes: dict[Any, str] = {}  # ANY target use -> its alias
        self.ctes: dict[str, Ref] = {}  # CTE name -> unit, as the WITH defines them
        self.before: Ref | None = None  # unit written just before the outer one
        self.chained: list[Ref] = []  # units chain reads read
        self.published: set[Ref] = set()  # units every other read reads
        self.rendered: list[Ref] = []  # units written, in order
        self.numbered: dict[Any, Any] = {}  # parameter slot -> its server index
        rendered = doc[artifact["rendered"]]
        self.events = [doc[ref] for ref in rendered["events"]]
        self.overlays = [doc[ref] for ref in rendered["expression_ranges"]]
        self.sql = rendered["sql"].encode("utf-8")
        self.query = artifact["ast"]

    def run(self) -> None:
        if self.query.kind == "sql_select":
            self.select_query(self.query)
        else:
            self.row_query(self.query)
        if len(self.events) != self.tokens or self.offset != len(self.sql):
            raise _Mismatch("token count")
        if self.family == "postgres" and sorted(self.numbered.values()) != list(
            range(1, len(self.numbered) + 1)
        ):
            raise _Mismatch("parameter index")
        # Ranges stay optional one by one (the observation contract); each
        # present one is a range the rendering encloses, in rendering order,
        # none twice.
        expected = iter(self.ranges)
        for event in self.overlays:
            got = (event["role"], event["subject"], event["start"], event["end"])
            if event["kind"] != "expression_range" or got not in expected:
                raise _Mismatch("range")

    # -- writer -----------------------------------------------------------
    def emit(self, text, kind, role, subject) -> None:
        if type(text) is not str:
            raise _Mismatch("token text")
        if self.tokens >= len(self.events):
            raise _Mismatch("token count")
        chunk = text.encode("utf-8")
        event = self.events[self.tokens]
        end = self.offset + len(chunk)
        if (
            (event["kind"], event["role"], event["subject"]) != (kind, role, subject)
            or (event["start"], event["end"]) != (self.offset, end)
            or self.sql[self.offset : end] != chunk
        ):
            raise _Mismatch("token")
        self.tokens += 1
        self.offset = end

    def ident(self, name, role, subject) -> None:
        if type(name) is not str:
            raise _Mismatch("identifier")
        q = self.quote
        self.emit(q + name.replace(q, q * 2) + q, "identifier", role, subject)

    def syntax(self, text, role, subject) -> None:
        self.emit(text, "syntax", role, subject)

    def enclose(self, role, subject, start) -> None:
        self.ranges.append((role, subject, start, self.offset))

    def __getitem__(self, ref):
        return self.doc[ref]

    def name(self, symbol):
        return self[symbol]["name"]

    # -- name resolution (SQL resolves by name, so identity is by name) ----
    def enter(self, scopes):
        """Make FROM aliases visible (an enclosing query level stays visible):
        none may repeat or shadow a visible one. Returns the outer scope."""
        outer = self.visible
        inner = {**outer, **{alias: dict(columns) for alias, columns in scopes}}
        if len(inner) != len(outer) + len(scopes):
            raise _Mismatch("alias scope")
        self.visible = inner
        return outer

    def owner(self, owned, scope, read) -> None:
        """The alias written for a read names the one relation whose record
        lists that read (visible relations can expose the same identities)."""
        if [alias for alias, reads in owned.items() if read in reads] != [scope]:
            raise _Mismatch("read relation")

    def resolve(self, scope, read) -> None:
        """A written `scope.column` names a column of a visible relation, and
        the column the record reads: a unit's column by the read's terminal,
        a source's column by the read's field."""
        columns = self.visible.get(scope, {})
        if read["name"] not in columns:
            raise _Mismatch("column reference")
        key, identity = columns[read["name"]]
        if read[key] != identity:
            raise _Mismatch("column identity")

    def exposed(self, columns):
        # (name, identity) pairs; a relation's column names are distinct as
        # the target resolves them, and so are its identities (an identity
        # names one position).
        fold = self.family != "postgres"
        names = {name.casefold() if fold else name for name, _ in columns}
        if len(names) != len(columns):
            raise _Mismatch("relation column names")
        if len({identity for _, identity in columns}) != len(columns):
            raise _Mismatch("relation column identities")
        return tuple(columns)

    def columns_of(self, producer):
        """The columns a FROM relation exposes, (name, identity): a source's
        fields by field, an inline body's labels by their exports, a named
        unit's CTE header names by their bindings (anchored: cte_columns)."""
        p = self[producer]
        if producer.kind == "bound_source":
            return self.exposed(
                [(self[f]["column"], ("field", f)) for f in p["fields"]]
            )
        if self.inline(producer):
            return self.exposed(
                [
                    (self[c]["label"], ("terminal", self[c]["export"]))
                    for c in p["columns"]
                ]
            )
        return self.exposed(
            [(self.name(s), ("terminal", self[s]["binding"])) for s in p["cte_columns"]]
        )

    def cte_name(self, name):
        # A WITH defines each name once.
        if name in self.ctes:
            raise _Mismatch("cte names")
        return name

    def cte_reference(self, unit):
        # A name used in FROM is a CTE defined before (a non-recursive WITH);
        # a unit without a symbol has no name to use.
        symbol = self[unit]["symbol"]
        if symbol is None or self.ctes.get(self.name(symbol)) != unit:
            raise _Mismatch("cte reference")
        return self.name(symbol)

    def take(self, reader, unit, chain) -> None:
        """Record one read of a unit, anchored to the unit the pipeline reads:
        a chain read reads the body realized just before its reader (the
        unit written just before it; an inline reader's next inner body) in
        the same definition (a JOIN has none); every other read reads a
        definition's last unit (by_definition)."""
        if chain:
            if self.inline(unit) is not self.inline(reader) or (
                not self.inline(unit) and unit != self.before
            ):
                raise _Mismatch("chain reads")
            if "join_body" not in (reader.kind, unit.kind) and (
                self[reader]["definition"] != self[unit]["definition"]
            ):
                raise _Mismatch("chain reads")
            self.chained.append(unit)
            return
        if unit.kind not in ("row_result_body", "set_body", "sql_cte") and not (
            unit.kind == "row_body" and self[unit]["block_kind"] == "projection"
        ):
            raise _Mismatch("published reads")
        self.published.add(unit)

    def all_read(self, ctes) -> None:
        # The pipeline writes a CTE only for a unit a later unit reads.
        if any(u not in self.chained and u not in self.published for u in ctes):
            raise _Mismatch("cte unread")

    # -- shared predicates ------------------------------------------------
    def block(self, unit):
        u = self[unit]
        if unit.kind == "row_body":
            return u["block"]
        if unit.kind == "row_result_body":
            return u["boundaries"][0]
        if unit.kind == "set_body":
            return u["body"]
        if unit.kind == "join_body":
            return u["join"]
        raise _Mismatch("unit kind")

    def inline(self, unit) -> bool:
        return (
            unit.kind in ("row_body", "row_result_body")
            and self[unit]["symbol"] is None
            and not self[unit]["final"]
        )

    def realization(self, value):
        """tag, storage kind, scale of one value (constants from their anchor)."""
        if value.kind in _REALIZED:
            r = self[self[value]["realization"]]
            return r["tag"], r["storage"].get("kind"), r["storage"].get("scale")
        if value.kind == "sql_null":
            return self[value]["tag"], "typed_null", None
        while value.kind == "sql_unary":
            value = self[value]["operand"]
        if value.kind == "sql_anchor":
            return self[value]["tag"], self[value]["physical_type"], None
        raise _Mismatch("value kind")

    # -- values -----------------------------------------------------------
    def constant(self, value) -> None:
        nodes = []
        while value.kind == "sql_unary":
            nodes.append(value)
            value = self[value]["operand"]
        if value.kind == "sql_null":
            if nodes:
                raise _Mismatch("unary over null")
            leaf = self[value]
            self.emit("NULL", "literal", leaf["tag"], leaf["site"])
            return
        if value.kind != "sql_anchor":
            raise _Mismatch("value kind")
        nodes.append(value)
        opened = []
        for node in nodes:
            opened.append((node, self.offset))
            if node.kind == "sql_unary":
                op = self[node]["operator"]
                if op not in ("+", "-"):
                    raise _Mismatch("unary operator")
                self.syntax("(" + op, "unary_open", self[node]["original"])
            else:
                self.syntax("CAST(", "anchor_open", self[node]["original"])
        anchor = self[value]
        leaf_ref = anchor["operand"]
        leaf = self[leaf_ref]
        if leaf_ref.kind == "sql_literal":
            fixed = leaf["value"]
            if fixed.tag != anchor["tag"]:
                raise _Mismatch("anchor tag")
            self.emit(
                schema.literal_token(fixed.tag, fixed.value, self.family),
                "literal",
                fixed.tag,
                leaf["site"],
            )
        elif leaf_ref.kind == "sql_parameter":
            use = self[leaf["use"]]
            index = use["server_index"]
            if type(index) is not int or index < 1:
                raise _Mismatch("parameter index")
            # parameters.allocate_uses: on PostgreSQL one $n per slot, the
            # slots numbered from 1 (run() checks there is no gap).
            if self.family == "postgres" and (
                self.numbered.setdefault(use["slot"], index) != index
            ):
                raise _Mismatch("parameter index")
            self.emit(
                "$" + str(index) if self.family == "postgres" else "?",
                "parameter",
                anchor["tag"],
                leaf["site"],
            )
        else:
            raise _Mismatch("anchor leaf")
        for node, start in reversed(opened):
            subject = self[node]["original"]
            if node.kind == "sql_unary":
                self.syntax(")", "unary_close", subject)
                self.enclose("unary", subject, start)
            else:
                # parameters.build_value: the family's own carrier of the tag.
                physical = self[node]["physical_type"]
                if physical != schema.PHYSICAL[self.family].get(anchor["tag"]):
                    raise _Mismatch("anchor physical type")
                self.syntax(schema.ANCHOR_SUFFIX[physical], "anchor_close", subject)
                self.enclose("anchor", subject, start)

    def block_column(self, target, column):
        t = self[target]
        producer = t["producer"]
        if t["source"] is not None:
            fields = [
                self[f]
                for f in self[producer]["fields"]
                if self[f]["ordinal"] == column
            ]
            return None if len(fields) != 1 else fields[0]["column"]
        p = self[producer]
        if p["symbol"] is None and not p["final"]:
            if not 0 <= column < len(p["columns"]):
                return None
            return self[p["columns"][column]]["label"]
        if not 0 <= column < len(p["cte_columns"]) or len(p["columns"]) != len(
            p["cte_columns"]
        ):
            return None
        return self.name(p["cte_columns"][column])

    def unit_select(self, unit) -> None:
        self.rendered.append(unit)
        if unit.kind == "join_body":
            self.join_select(unit)
        elif unit.kind == "row_result_body":
            self.result_select(unit)
        elif unit.kind == "set_body":
            self.set_select(unit)
        elif unit.kind == "row_body":
            self.row_select(unit)
        else:
            raise _Mismatch("unit kind")

    def inline_select(self, producer, outer) -> None:
        """An inline body in parentheses: it sees the enclosing query level,
        not the FROM it stands in."""
        block = self.block(producer)
        self.syntax("(", "inline_open", block)
        inner, self.visible = self.visible, outer
        self.depth += 1
        self.unit_select(producer)
        self.depth -= 1
        self.visible = inner
        self.syntax(")", "inline_close", block)

    def block_read(self, value, alias) -> None:
        v = self[value]
        kind = v["kind"]
        # rows and the compiled lowering: an ANY read is an EXISTS with its
        # predicate, and only an IN reads an operand.
        if (value.kind == "sql_any_read" and kind != "exists") or (
            kind not in ("in", "not_in") and v["operands"]
        ):
            raise _Mismatch("block read kind")
        if kind in ("in", "not_in"):
            self.block_membership(value, alias)
            return
        start = self.offset
        reference = v["original"]
        target = v["target"]
        t = self[target]
        producer = t["producer"]
        if producer.kind != "bound_source":
            self.take(None, producer, False)
        scope = self.name(t["symbol"])
        outer = self.enter([(scope, self.columns_of(producer))])
        if kind == "scalar":
            column = (
                None if v["column"] is None else self.block_column(target, v["column"])
            )
            if column is None:
                raise _Mismatch("scalar read column")
            self.syntax("(", "scalar_open", reference)
            self.syntax("SELECT ", "scalar_select", reference)
            self.ident(scope, "scalar_scope", t["use"])
            self.syntax(".", "scalar_column_qualifier", reference)
            self.ident(column, "scalar_column", reference)
        elif kind == "exists":
            self.syntax("EXISTS (", "exists_open", reference)
            self.syntax("SELECT ", "exists_select", reference)
            self.emit("1", "literal", "exists_sentinel", reference)
        else:
            raise _Mismatch("block read kind")
        self.syntax(" FROM ", f"{kind}_from", reference)
        if t["source"] is not None:
            relation = t["source"]
            source = self[producer]
            self.ident(source["namespace"], f"{kind}_namespace", relation)
            self.syntax(".", f"{kind}_qualifier", relation)
            self.ident(source["name"], f"{kind}_relation", relation)
        elif self.inline(producer):
            self.inline_select(producer, outer)
        else:
            self.ident(
                self.cte_reference(producer), f"{kind}_reference", self.block(producer)
            )
        self.syntax(" AS ", f"{kind}_alias", t["use"])
        self.ident(scope, f"{kind}_scope", t["use"])
        if value.kind == "sql_any_read":
            self.syntax(" WHERE ", "exists_where", reference)
            saved = self.any_scopes
            self.any_scopes = {**saved, t["use"]: scope}
            self.scalar(v["predicate"], alias)
            self.any_scopes = saved
        self.syntax(")", f"{kind}_close", reference)
        self.enclose(kind, reference, start)
        self.visible = outer

    def block_membership(self, value, alias) -> None:
        v = self[value]
        start = self.offset
        reference = v["original"]
        target = v["target"]
        t = self[target]
        producer = t["producer"]
        p = self[producer]
        width = len(p["fields"]) if t["source"] is not None else len(p["columns"])
        column = self.block_column(target, 0) if width == 1 else None
        if column is None or len(v["operands"]) != 1:
            raise _Mismatch("membership read")
        if producer.kind != "bound_source":
            self.take(None, producer, False)
        self.syntax("(", "in_open", reference)
        self.scalar(v["operands"][0], alias)
        scope = self.name(t["symbol"])
        outer = self.enter([(scope, self.columns_of(producer))])
        negated = v["kind"] == "not_in"
        self.syntax(" NOT IN (" if negated else " IN (", "in_operator", reference)
        self.syntax("SELECT ", "in_select", reference)
        self.ident(scope, "in_column_scope", t["use"])
        self.syntax(".", "in_column_qualifier", t["use"])
        if t["source"] is not None:
            relation = t["source"]
            self.ident(column, "in_source_column", relation)
            self.syntax(" FROM ", "in_from", reference)
            self.ident(p["namespace"], "in_namespace", relation)
            self.syntax(".", "in_qualifier", relation)
            self.ident(p["name"], "in_relation", relation)
        elif self.inline(producer):
            terminal = self[self[p["columns"][0]]["column"]]["terminal"]
            self.ident(column, "in_column", terminal)
            self.syntax(" FROM ", "in_from", reference)
            self.inline_select(producer, outer)
        else:
            self.ident(column, "in_column", self[p["cte_columns"][0]]["binding"])
            self.syntax(" FROM ", "in_from", reference)
            self.ident(
                self.cte_reference(producer), "in_reference", self.block(producer)
            )
        self.syntax(" AS ", "in_alias", t["use"])
        self.ident(scope, "in_scope", t["use"])
        self.syntax("))", "in_close", reference)
        self.enclose("relation_membership", reference, start)
        self.visible = outer

    def int8_widened(self, value) -> bool:
        v = self[value]
        r = self[v["realization"]]
        return (
            self.family == "postgres"
            and (
                v["kind"] in ("sign", "arithmetic")
                or v["kind"] == "scalar_call"
                and v["operator"] == "abs"
            )
            and r["tag"] == "Int"
            and dict(r["storage"]) == {"kind": "pg_int8"}
            and bool(v["operands"])
            and all(self.realization(o)[1] in _NARROW_PG_INTS for o in v["operands"])
        )

    def operand(self, value, position, alias) -> None:
        v = self[value]
        operands = v["operands"]
        if position >= len(operands):
            raise _Mismatch("operand arity")
        reference = v["original"]
        if (
            v["kind"] == "arithmetic"
            and self[v["realization"]]["tag"] == "Int"
            and operands[position].kind == "sql_null"
        ):
            start = self.offset
            self.syntax("CAST(", "null_cast_open", reference)
            self.scalar(operands[position], alias)
            self.syntax(
                schema.ANCHOR_SUFFIX[schema.PHYSICAL[self.family]["Int"]],
                "null_cast_close",
                reference,
            )
            self.enclose("null_cast", reference, start)
            return
        if position or not self.int8_widened(value):
            self.scalar(operands[position], alias)
            return
        start = self.offset
        self.syntax("CAST(", "int8_widen_open", reference)
        self.scalar(operands[0], alias)
        self.syntax(" AS pg_catalog.int8)", "int8_widen_close", reference)
        self.enclose("int8_widen", reference, start)

    def scalar(self, value, alias) -> None:
        start = self.offset
        kind = value.kind
        if kind in ("sql_block_read", "sql_any_read"):
            self.block_read(value, alias)
            return
        v = self[value]
        if kind == "sql_captured_reference":
            reference = v["original"]
            column = self[v["column"]]
            scope = self.name(v["scope"])
            # A capture sits in a capturing let's inline body and writes the
            # scan alias of the row body that reads the let (_inline_target).
            if not self.depth:
                raise _Mismatch("capture placement")
            if scope != self.reader:
                raise _Mismatch("read relation")
            self.resolve(scope, column)
            self.ident(scope, "capture_scope", v["capture"])
            self.syntax(".", "capture_qualifier", reference)
            self.ident(column["name"], "capture_column", column["terminal"])
            self.enclose("capture", reference, start)
            return
        if kind in _VALUE_REFS:
            reference = v["original"]
            scope = alias if v["scope"] is None else self.name(v["scope"])
            column = self[v["column"]]
            if kind == "sql_any_reference":
                if self.any_scopes.get(v["use"]) != scope:
                    raise _Mismatch("read relation")
            elif v["scope"] is not None:
                # Only a JOIN input's reads carry an alias (AST assembly).
                self.owner(self.owned, scope, v["column"])
            self.resolve(scope, column)
            self.ident(scope, "value_scope", v["port"])
            self.syntax(".", "value_qualifier", reference)
            self.ident(column["name"], "value_column", column["terminal"])
            self.enclose("reference", reference, start)
            return
        if kind != "sql_operation":
            self.constant(value)
            return
        self.operation(value, alias, start)

    def operation(self, value, alias, start) -> None:
        v = self[value]
        family = self.family
        reference = v["original"]
        op_kind, operator, operands = v["kind"], v["operator"], v["operands"]
        realization = self[v["realization"]]
        tag = realization["tag"]
        if operator not in schema.OPERATORS.get(op_kind, ()):
            raise _Mismatch("operator")
        # Every operand the record lists is written.
        if len(operands) != _OPERATION_ARITY.get(op_kind, len(operands)):
            raise _Mismatch("operation arity")
        syntax = self.syntax

        def sub(i):
            if i >= len(operands):
                raise _Mismatch("operand arity")
            self.scalar(operands[i], alias)

        if op_kind == "sign":
            syntax("(" + operator, "unary_open", reference)
            self.operand(value, 0, alias)
            syntax(")", "unary_close", reference)
            self.enclose("unary", reference, start)
            return
        if op_kind == "not":
            syntax("(NOT ", "not_open", reference)
            sub(0)
            syntax(")", "not_close", reference)
            self.enclose("not", reference, start)
            return
        if op_kind == "null_test":
            syntax("(", "is_null_open", reference)
            sub(0)
            negated = operator == "is not null"
            syntax(" IS NOT NULL" if negated else " IS NULL", "is_null_test", reference)
            syntax(")", "is_null_close", reference)
            self.enclose("is_null", reference, start)
            return
        if op_kind == "between":
            syntax("(", "between_open", reference)
            sub(0)
            syntax(" BETWEEN ", "between_operator", reference)
            sub(1)
            syntax(" AND ", "between_separator", reference)
            sub(2)
            syntax(")", "between_close", reference)
            self.enclose("between", reference, start)
            return
        if op_kind == "scalar_call":
            self.call(value, alias, start)
            return
        if op_kind == "conditional":
            syntax("(CASE WHEN ", "conditional_open", reference)
            sub(1)
            syntax(" THEN ", "conditional_then", reference)
            sub(0)
            syntax(" ELSE ", "conditional_else", reference)
            sub(2)
            syntax(" END)", "conditional_close", reference)
            self.enclose("conditional", reference, start)
            return
        if op_kind == "membership":
            negated = operator == "not_in"
            if len(operands) == 1:
                syntax("TRUE" if negated else "FALSE", "membership_constant", reference)
            else:
                syntax("(", "membership_open", reference)
                sub(0)
                text = " NOT IN (" if negated else " IN ("
                syntax(text, "membership_operator", reference)
                for position in range(1, len(operands)):
                    if position > 1:
                        syntax(", ", "membership_separator", reference)
                    sub(position)
                syntax("))", "membership_close", reference)
            self.enclose("membership", reference, start)
            return
        if op_kind == "cast":
            # rows.resolved_cast_realization: an Int to Float, or to Text on
            # PostgreSQL.
            if _CAST_TAG[operator] != tag or (tag == "Text" and family != "postgres"):
                raise _Mismatch("cast")
            physical = (
                "pg_catalog.float8"
                if tag == "Float" and family == "postgres"
                else "DOUBLE"
                if tag == "Float"
                else "pg_catalog.text"
            )
            syntax("(CAST(" if tag == "Text" else "CAST(", "cast_open", reference)
            sub(0)
            syntax(
                " AS " + physical + ') COLLATE "C")'
                if tag == "Text"
                else " AS " + physical + ")",
                "cast_close",
                reference,
            )
            self.enclose("cast", reference, start)
            return
        if op_kind == "comparison" and operator in ("like", "not like"):
            syntax("(", "comparison_open", reference)
            sub(0)
            syntax(
                schema.COMPARISON_SPELLING[operator], "comparison_operator", reference
            )
            sub(1)
            syntax(" ESCAPE '!'", "comparison_escape", reference)
            syntax(")", "comparison_close", reference)
            self.enclose("comparison", reference, start)
            return
        if (
            op_kind == "arithmetic"
            and operator == "%"
            and tag == "Float"
            and family == "postgres"
        ):
            # A MySQL Float `%` is the plain `(l % r)` (S15).
            remainder = schema.FLOAT_REMAINDER_TOKENS
            syntax(remainder[0], "float_remainder_open", reference)
            sub(0)
            syntax(remainder[1], "float_remainder_between", reference)
            sub(1)
            syntax(remainder[2], "float_remainder_close", reference)
            self.enclose("binary", reference, start)
            return
        if op_kind == "comparison":
            token = schema.COMPARISON_SPELLING[operator]
        elif (
            op_kind == "arithmetic"
            and operator == "/"
            and dict(realization["storage"]) == {"kind": "my_bigint"}
        ):
            # R08: MySQL's `/` of integers is DECIMAL; DIV truncates.
            token = " DIV "
        else:
            token = " " + (operator.upper() if op_kind == "logical" else operator) + " "
        if (
            family == "postgres"
            and op_kind == "arithmetic"
            and tag == "Decimal"
            and (
                operator in ("+", "-")
                and len({self.realization(o)[2] for o in operands}) > 1
                or {self.realization(o)[0] for o in operands} == {"Decimal", "Int"}
            )
        ):
            storage = realization["storage"]
            precision, scale = storage.get("precision"), storage.get("scale")
            # rows: a Decimal result is numeric(p, s), 1 <= p <= 65, s <= min(p, 30).
            if (
                operator not in ("+", "-", "*")
                or type(precision) is not int
                or type(scale) is not int
                or not 1 <= precision <= 65
                or not 0 <= scale <= min(precision, 30)
            ):
                raise _Mismatch("decimal arithmetic")
            syntax("CAST((", "decimal_arithmetic_open", reference)
            self.operand(value, 0, alias)
            syntax(token, "arithmetic_operator", reference)
            self.operand(value, 1, alias)
            syntax(
                f") AS pg_catalog.numeric({precision}, {scale}))",
                "decimal_arithmetic_close",
                reference,
            )
            self.enclose("binary", reference, start)
            return
        roles = {
            "arithmetic": (
                "binary_open",
                "arithmetic_operator",
                "binary_close",
                "binary",
            ),
            "logical": ("binary_open", "logical_operator", "binary_close", "binary"),
            "comparison": (
                "comparison_open",
                "comparison_operator",
                "comparison_close",
                "comparison",
            ),
        }
        if op_kind not in roles or len(operands) != 2:
            raise _Mismatch("binary operation")
        opening, middle, closing, role = roles[op_kind]
        syntax("(", opening, reference)
        self.operand(value, 0, alias)
        syntax(token, middle, reference)
        self.operand(value, 1, alias)
        syntax(")", closing, reference)
        self.enclose(role, reference, start)

    def call(self, value, alias, start) -> None:
        v = self[value]
        reference = v["original"]
        name, operands = v["operator"], v["operands"]
        tag = self[v["realization"]]["tag"]
        shape = (
            ("2" if len(operands) == 2 else tag)
            if name == "round"
            else tag
            if name == "date_trunc"
            else None
        )
        steps = _SCALAR_CALL_TEMPLATES.get((self.family, name, shape))
        if steps is not None:
            slots = [step for step in steps if type(step) is int]
            if len(operands) != (max(slots) + 1 if slots else 0):
                raise _Mismatch("call arity")
            for step in steps:
                if type(step) is int:
                    self.scalar(operands[step], alias)
                else:
                    self.syntax(step[1], step[0], reference)
        else:
            variadic = _SCALAR_CALL_VARIADIC[self.family].get(name)
            if variadic is None:
                raise _Mismatch("scalar call")
            if not (
                len(operands) == _CALL_ARITY[name]
                if name in _CALL_ARITY
                else len(operands) >= 2
            ):
                raise _Mismatch("call arity")
            opening, separator = variadic
            self.syntax(opening, "scalar_call_open", reference)
            for position in range(len(operands)):
                if position:
                    self.syntax(separator, "scalar_call_separator", reference)
                self.operand(value, position, alias)
            self.syntax(")", "scalar_call_close", reference)
        self.enclose("scalar_call", reference, start)

    # -- aggregate and window ---------------------------------------------
    def aggregate_value(self, ref, alias) -> None:
        c = self[ref]
        reference = c["aggregate"]
        function = c["function"]
        family = self.family
        start = self.offset

        def o(text, role):
            self.syntax(text, role, reference)

        # Derived, never copied: _Check checks the record's spelling and
        # casts against the same derivation.
        spelling = _AGGREGATE_SPELLING[family].get(function)
        if (
            spelling is None
            or c["distinct"] is not (function in _DISTINCT_AGGREGATES)
            or (c["argument"] is None and function != "count")
            or (family == "mysql" and function not in _MYSQL_AGGREGATES)
        ):
            raise _Mismatch("aggregate signature")
        # A slot the function's rendering never writes stays empty.
        if (
            c["delimiter"] is not None
            and function not in _DELIMITED
            or c["order_by"]
            and function not in (*_ORDERED, *_FILTERED, *_QUANTILE)
        ):
            raise _Mismatch("aggregate extra inputs")
        if c["extra_arguments"] and function != "count_distinct_tuple":
            raise _Mismatch("aggregate extra arguments")
        argument = (
            None
            if c["argument"] is None
            else _value_realization(self.doc, c["argument"])
        )
        argument_tag = None if argument is None else argument.get("tag")
        result = self[self[c["column"]]["realization"]]
        argument_cast, result_cast = _aggregate_casts(family, function, argument_tag)
        if _mysql_int_extremum(family, function, argument):
            result_cast = "SIGNED"
        decimal = _decimal_sum_cast(family, function, argument, result)
        if decimal is not None:
            argument_cast, result_cast = None, decimal
        if (
            family == "mysql"
            and function in ("sum", "filtered_sum")
            and (function == "filtered_sum" or argument_tag == "Int")
        ):
            # S02, S03: the guarded SUM of an Int; a conditional one is
            # COALESCE(the guarded SUM of CASE WHEN test THEN x END, 0).
            test = c["delimiter"]
            filtered = function == "filtered_sum"
            if (
                c["order_by"]
                or argument_cast is not None
                or result_cast is not None
                or (test is None) is filtered
            ):
                raise _Mismatch("guarded sum")
            if filtered:
                o("COALESCE(", "aggregate_zero_open")
            for position, (role, text) in enumerate(_MYSQL_SUM_GUARD):
                if position and filtered:
                    o("CASE WHEN ", "aggregate_filter_open")
                    self.scalar(test, alias)
                    o(" THEN ", "aggregate_filter_then")
                    self.scalar(c["argument"], alias)
                    o(" END", "aggregate_filter_close")
                elif position:
                    self.scalar(c["argument"], alias)
                o(text, role)
            if filtered:
                o(", 0)", "aggregate_zero_close")
            self.enclose("aggregate", reference, start)
            return
        root = family == "postgres" and function in _ROOT
        if function in _GROUP_TEST:
            o("(", "aggregate_test_open")
        if root:
            o("SQRT(", "aggregate_root_open")
        if function == "filtered_sum":
            o("COALESCE(", "aggregate_zero_open")
        if function in _ORDERED_VALUE:
            o("(", "aggregate_element_open")
        if result_cast is not None:
            o("CAST(", "aggregate_result_cast_open")
        o(spelling + "(", "aggregate_open")
        if function in _FILTERED:
            test = c["delimiter"] if function == "filtered_sum" else c["argument"]
            if c["distinct"] or c["order_by"] or test is None:
                raise _Mismatch("conditional aggregate")
            o("CASE WHEN ", "aggregate_filter_open")
            self.scalar(test, alias)
            o(" THEN ", "aggregate_filter_then")
            if function == "group_all":
                o("NULL ELSE 1", "aggregate_filter_else")
            elif function != "filtered_sum":
                o("1", "aggregate_filter_one")
            else:
                if argument_cast is None:
                    raise _Mismatch("conditional sum")
                o("CAST(", "aggregate_argument_cast_open")
                self.scalar(c["argument"], alias)
                o(" AS " + argument_cast + ")", "aggregate_argument_cast_close")
            o(" END", "aggregate_filter_close")
        elif c["argument"] is None:
            o("*", "aggregate_row_count")
        elif function in _ORDERED:
            if (
                c["distinct"]
                or argument_cast is not None
                or (c["delimiter"] is None) is (function == "string_agg")
                or not c["order_by"]
            ):
                raise _Mismatch("ordered aggregate")
            self.scalar(c["argument"], alias)
            if c["delimiter"] is not None:
                o(", ", "aggregate_separator")
                self.scalar(c["delimiter"], alias)
            o(" ORDER BY ", "aggregate_order")
            self.aggregate_order(c, alias, "aggregate_order_separator")
        elif function == "count_distinct_tuple":
            members = (c["argument"], *c["extra_arguments"])
            if not c["distinct"] or len(members) < 2:
                raise _Mismatch("count_distinct_tuple")
            o("DISTINCT ", "aggregate_distinct")
            o("CASE WHEN ", "aggregate_tuple_open")
            for position, member in enumerate(members):
                self.scalar(member, alias)
                last = position == len(members) - 1
                o(
                    " IS NOT NULL THEN ROW(" if last else " IS NOT NULL AND ",
                    "aggregate_tuple_then" if last else "aggregate_tuple_and",
                )
            for position, member in enumerate(members):
                if position:
                    o(", ", "aggregate_separator")
                self.scalar(member, alias)
            o(") END", "aggregate_tuple_close")
        elif function in _QUANTILE:
            fraction = c["delimiter"]
            # rendering's "unrenderable quantile": only `quantile` has a fraction.
            if (
                argument_cast is None
                or c["order_by"]
                or (fraction is None) is not (function == "median")
            ):
                raise _Mismatch("quantile")
            if fraction is None:
                o("0.5", "aggregate_fraction")
            else:
                self.scalar(fraction, alias)
                # aggregates.quantile_fraction_diagnostic: a Float literal 0.0-1.0.
                leaf = (
                    self[fraction]["operand"] if fraction.kind == "sql_anchor" else None
                )
                if (
                    leaf is None
                    or leaf.kind != "sql_literal"
                    or self[leaf]["value"].tag != "Float"
                    or not 0.0 <= self[leaf]["value"].value <= 1.0
                    or math.copysign(1.0, self[leaf]["value"].value) < 0
                ):
                    raise _Mismatch("quantile fraction")
            o(") WITHIN GROUP (ORDER BY ", "aggregate_within")
            o("CAST(", "aggregate_argument_cast_open")
            self.scalar(c["argument"], alias)
            o(" AS " + argument_cast + ")", "aggregate_argument_cast_close")
        else:
            if c["distinct"]:
                o("DISTINCT ", "aggregate_distinct")
            if argument_cast is not None:
                o("CAST(", "aggregate_argument_cast_open")
            self.scalar(c["argument"], alias)
            if argument_cast is not None:
                o(" AS " + argument_cast + ")", "aggregate_argument_cast_close")
        o(")", "aggregate_close")
        if result_cast is not None:
            o(" AS " + result_cast + ")", "aggregate_result_cast_close")
        if root:
            o(")", "aggregate_root_close")
        if function == "filtered_sum":
            o(", 0)", "aggregate_zero_close")
        if function in _GROUP_TEST:
            o(" > 0)" if function == "group_any" else " = 0)", "aggregate_test_close")
        if function in _ORDERED_VALUE:
            o(")[1]", "aggregate_element_close")
        self.enclose("aggregate", reference, start)

    def aggregate_order(self, c, alias, separator, subject=None) -> None:
        """An ordered aggregate's internal order: `last` is the first element
        of the reversed order, so each direction is written flipped."""
        subject = c["aggregate"] if subject is None else subject
        for position, item in enumerate(c["order_by"]):
            if position:
                self.syntax(", ", separator, subject)
            self.scalar(self[item]["value"], alias)
            direction = self[item]["direction"]
            if direction not in ("asc", "desc"):
                raise _Mismatch("aggregate direction")
            if c["function"] == "last":
                text = " DESC" if direction == "asc" else " ASC"
                self.syntax(text, "aggregate_order_reversed_direction", subject)
            else:
                text = " ASC" if direction == "asc" else " DESC"
                self.syntax(text, "aggregate_order_direction", subject)

    def ranked_layout(self, stage):
        """aggregation.ranked_layout: the derived table's read columns, keys
        first, each once by name, and each `first` or `last`'s ROW_NUMBER
        name `r<ordinal>`, lengthened by `_` past every read name that is not
        ASCII, then while it is an ASCII read name without case."""
        listed: dict[str, Any] = {}
        for key in stage["keys"]:
            read = self[self[key]["read"]]
            listed.setdefault(read["name"], read)
        ordered = [
            value
            for value in stage["values"]
            if self[value]["function"] in _ORDERED_VALUE
        ]
        for value in ordered:
            argument = self[value]["argument"]
            if argument is None or argument.kind != "sql_stage_reference":
                raise _Mismatch("ranked aggregate")
            read = self[self[argument]["column"]]
            listed.setdefault(read["name"], read)
        folded = {name.casefold() for name in listed if name.isascii()}
        longest = max((len(name) for name in listed if not name.isascii()), default=0)
        ranks = {}
        for value in ordered:
            name = "r" + str(self[value]["ordinal"])
            name += "_" * max(0, longest + 1 - len(name))
            while name.casefold() in folded:
                name += "_"
            ranks[value] = name
        return listed, ranks

    def ranked_value(self, ref, alias, rank) -> None:
        """A MySQL `first` or `last` (S13): MAX(CASE WHEN <rank> = 1 THEN x END)
        over its ranked derived table."""
        c = self[ref]
        reference = c["aggregate"]
        start = self.offset
        if (
            c["distinct"]
            or c["delimiter"] is not None
            or c["extra_arguments"]
            or not c["order_by"]
        ):
            raise _Mismatch("ranked aggregate")
        self.syntax(
            _AGGREGATE_SPELLING["mysql"][c["function"]] + "(",
            "aggregate_open",
            reference,
        )
        self.syntax("CASE WHEN ", "aggregate_rank_open", reference)
        self.ident(alias, "rank_scope", reference)
        self.syntax(".", "aggregate_rank_qualifier", reference)
        self.ident(rank, "rank_column", reference)
        self.syntax(" = 1 THEN ", "aggregate_rank_then", reference)
        self.scalar(c["argument"], alias)
        self.syntax(" END", "aggregate_rank_close", reference)
        self.syntax(")", "aggregate_close", reference)
        self.enclose("aggregate", reference, start)

    def ranked_rows(self, unit, alias, inputs, listed, ranks, outer) -> None:
        """MySQL's ranked derived table (S13): the columns the aggregation
        reads, then one ROW_NUMBER per `first` or `last` over its group's rows
        in its own order, over the body's own scan."""
        stage = self[self[unit]["aggregation"]]
        reference = stage["aggregation"]
        derived, self.visible = self.visible, {**outer, alias: dict(inputs)}
        self.syntax("(SELECT ", "rank_open", reference)
        for position, read in enumerate(listed.values()):
            if position:
                self.syntax(", ", "rank_separator", reference)
            self.resolve(alias, read)
            self.ident(alias, "rank_carry_scope", reference)
            self.syntax(".", "rank_carry_qualifier", reference)
            self.ident(read["name"], "rank_carry_column", read["terminal"])
        for value, name in ranks.items():
            c = self[value]
            subject = c["aggregate"]
            self.syntax(", ", "rank_separator", subject)
            self.syntax("ROW_NUMBER() OVER (", "aggregate_rank_window", subject)
            if stage["keys"]:
                self.syntax("PARTITION BY ", "aggregate_rank_partition", subject)
                for position, key in enumerate(stage["keys"]):
                    read = self[self[key]["read"]]
                    if position:
                        self.syntax(", ", "aggregate_rank_separator", subject)
                    self.resolve(alias, read)
                    self.ident(alias, "rank_partition_scope", subject)
                    self.syntax(".", "aggregate_rank_partition_qualifier", subject)
                    self.ident(read["name"], "rank_partition_column", read["terminal"])
                self.syntax(" ", "aggregate_rank_spec_separator", subject)
            self.syntax("ORDER BY ", "aggregate_rank_order", subject)
            self.aggregate_order(c, alias, "aggregate_rank_separator", subject)
            self.syntax(") AS ", "aggregate_rank_alias", subject)
            self.ident(name, "rank_label", subject)
        self.scan_from(unit, alias, outer)
        self.syntax(") AS ", "rank_close", reference)
        self.ident(alias, "rank_scope", reference)
        self.visible = derived

    def frame_bound(self, bound):
        kind, text = bound[0], bound[1]
        if kind in schema.FRAME_BOUNDS:
            if text != schema.FRAME_BOUNDS[kind]:
                raise _Mismatch("frame bound text")
            return text
        if kind in schema.FRAME_OFFSETS:
            number, _, word = text.partition(" ")
            if word != schema.FRAME_OFFSETS[kind] or not _canonical_integer(
                number, 0, _I64_MAX
            ):
                raise _Mismatch("frame offset text")
            return text
        raise _Mismatch("frame bound kind")

    def window_specification(self, spec_ref, reference, alias) -> None:
        s = self[spec_ref]

        def o(text, role):
            self.syntax(text, role, reference)

        if s["frame"] is not None:
            frame = self[s["frame"]]
            if self.family == "mysql" and (
                frame["unit"] not in _MYSQL_FRAME_UNITS
                or frame["exclusion"] not in (None, "no_others")
            ):
                raise _Mismatch("frame family")
            # windows.offset_range_problem: an offset RANGE has one ORDER key.
            if (
                frame["unit"] == "range"
                and any(
                    b[0] in schema.FRAME_OFFSETS for b in (frame["start"], frame["end"])
                )
                and len(s["orders"]) != 1
            ):
                raise _Mismatch("range key count")
            # window_semantics._structural_frame_failures.
            start, end = frame["start"][0], frame["end"][0]
            if start not in _FRAME_BOUND_ORDER or end not in _FRAME_BOUND_ORDER:
                raise _Mismatch("frame bound kind")
            if (
                start == "unbounded_following"
                or end == "unbounded_preceding"
                or _FRAME_BOUND_ORDER.index(start) > _FRAME_BOUND_ORDER.index(end)
            ):
                raise _Mismatch("frame bound order")
            # GROUPS_FRAME_REQUIRES_ORDER.
            if frame["unit"] == "groups" and not s["orders"]:
                raise _Mismatch("groups order")
        if s["partitions"]:
            o("PARTITION BY ", "window_partition")
            for position, partition in enumerate(s["partitions"]):
                read = self[self[partition]["read"]]
                if position:
                    o(", ", "window_partition_separator")
                self.resolve(alias, read)
                self.ident(alias, "window_partition_scope", read["terminal"])
                o(".", "window_partition_qualifier")
                self.ident(read["name"], "window_partition_column", read["terminal"])
        if s["orders"]:
            if s["partitions"]:
                o(" ", "window_spec_separator")
            o("ORDER BY ", "window_order")
            for index, item_ref in enumerate(s["orders"]):
                item = self[item_ref]
                read = self[item["read"]]
                if item["position"] != index:
                    raise _Mismatch("window order position")
                if index:
                    o(", ", "window_order_separator")
                self.resolve(alias, read)
                self.ident(alias, "window_order_scope", read["terminal"])
                o(".", "window_order_qualifier")
                self.ident(read["name"], "window_order_column", read["terminal"])
                if item["direction"] not in ("asc", "desc"):
                    raise _Mismatch("window direction")
                o(
                    " ASC" if item["direction"] == "asc" else " DESC",
                    "window_order_direction",
                )
        if s["frame"] is not None:
            frame = self[s["frame"]]
            if s["partitions"] or s["orders"]:
                o(" ", "window_frame_separator")
            if frame["unit"] not in schema.FRAME_UNITS:
                raise _Mismatch("frame unit")
            o(schema.FRAME_UNITS[frame["unit"]] + " BETWEEN ", "window_frame_unit")
            o(self.frame_bound(frame["start"]), "window_frame_start")
            o(" AND ", "window_frame_and")
            o(self.frame_bound(frame["end"]), "window_frame_end")
            if frame["exclusion"] not in schema.EXCLUSIONS:
                raise _Mismatch("frame exclusion")
            spelling = schema.EXCLUSIONS[frame["exclusion"]]
            if spelling is not None:
                o(spelling, "window_frame_exclusion")

    def window_clause(self, stage_ref, alias) -> None:
        if stage_ref is None:
            return
        stage = self[stage_ref]
        if not stage["definitions"]:
            return
        self.syntax(" WINDOW ", "window_clause", stage["ref"])
        names = [self.name(self[d]["symbol"]) for d in stage["definitions"]]
        if len(set(names)) != len(names):
            raise _Mismatch("window definition names")
        for index, definition_ref in enumerate(stage["definitions"]):
            definition = self[definition_ref]
            if definition["index"] != index:
                raise _Mismatch("window definition index")
            if index:
                self.syntax(", ", "window_clause_separator", stage["ref"])
            symbol = self[definition["symbol"]]
            reference = symbol["binding"]
            self.ident(symbol["name"], "window_definition", reference)
            self.syntax(" AS ", "window_definition_as", reference)
            start = self.offset
            self.syntax("(", "window_spec_open", reference)
            self.window_specification(definition["specification"], reference, alias)
            self.syntax(")", "window_spec_close", reference)
            self.enclose("window_specification", reference, start)

    def window_literal(self, column, argument):
        """Closure of the one free-text record field the renderer copies:
        the emitter writes a canonical integer, NULL, or a PostgreSQL Text
        token (project_sql_emission_windows._integer_literal/_text_literal)."""
        literal, role = argument["literal"], argument["role"]
        if type(literal) is not str:
            raise _Mismatch("window literal")
        if (self.family, role) in _COUNT_INTERVAL:
            if not _canonical_integer(literal, *_COUNT_INTERVAL[self.family, role]):
                raise _Mismatch("window literal")
            return literal
        if role == "default":
            if literal == "NULL":
                return literal
            # An integer default only beside an Int value, an E'' text only
            # beside a PostgreSQL Text value; an Int default is a source
            # literal (a negative one is a unary the analyzer refuses) inside
            # signed64 (window_default_integer_out_of_signed64_range).
            values = [
                self[a] for a in column["arguments"] if self[a]["role"] == "value"
            ]
            if len(values) != 1 or values[0]["read"] is None:
                raise _Mismatch("window literal")
            carrier = self[self[values[0]["read"]]["realization"]]["tag"]
            if carrier == "Int" and _canonical_integer(literal, 0, _I64_MAX):
                return literal
            if (
                carrier == "Text"
                and self.family == "postgres"
                and literal.startswith("E'")
                and literal.endswith("'")
            ):
                inner = literal[2:-1]
                if len(inner) % 4 == 0 and all(
                    inner[i] == "\\"
                    and inner[i + 1] in "0123"
                    and all(ch in "01234567" for ch in inner[i + 1 : i + 4])
                    for i in range(0, len(inner), 4)
                ):
                    try:
                        text = bytes(
                            int(inner[i + 1 : i + 4], 8)
                            for i in range(0, len(inner), 4)
                        ).decode("utf-8")
                    except UnicodeDecodeError:
                        raise _Mismatch("window literal") from None
                    if (
                        "\x00" not in text
                        and schema.literal_token("Text", text, "postgres") == literal
                    ):
                        return literal
        raise _Mismatch("window literal")

    def same_specification(self, left, right) -> bool:
        """windows.same_specification on records: partition and order reads by
        reference, directions and NULL posture and frames by value."""
        a, b = self[left], self[right]

        def frame(s):
            if s["frame"] is None:
                return None
            f = self[s["frame"]]
            return f["unit"], f["start"], f["end"], f["exclusion"]

        def orders(s):
            return [
                (self[o]["read"], self[o]["direction"], self[o]["nulls"])
                for o in s["orders"]
            ]

        return (
            [self[p]["read"] for p in a["partitions"]]
            == [self[p]["read"] for p in b["partitions"]]
            and orders(a) == orders(b)
            and frame(a) == frame(b)
        )

    def window_value(self, ref, alias, named, used) -> None:
        c = self[ref]
        reference = c["window"]
        function = c["function"]
        start = self.offset

        def o(text, role):
            self.syntax(text, role, reference)

        if function not in schema.WINDOW_SPELLING:
            raise _Mismatch("window function")
        signatures = _WINDOW_SIGNATURES.get(function)
        if signatures is None and self.family == "postgres":
            signatures = _WINDOW_AGGREGATE_SIGNATURES.get(function)
        arguments = [self[a] for a in c["arguments"]]
        if signatures is None or tuple(a["role"] for a in arguments) not in signatures:
            raise _Mismatch("window signature")
        for index, argument in enumerate(arguments):
            # A value is a column read; every other role is one literal.
            value = argument["role"] == "value"
            if (
                argument["position"] != index
                or (argument["read"] is None) is value
                or (argument["literal"] is None) is not value
            ):
                raise _Mismatch("window argument")
        spec = self[c["specification"]]
        insensitive = function in _FRAME_INSENSITIVE
        if (spec["frame"] is not None) is insensitive:
            raise _Mismatch("window frame policy")
        # WindowComputationAnalysis: only an aggregate may omit ORDER BY.
        if not spec["orders"] and function not in schema.WINDOW_AGGREGATES:
            raise _Mismatch("window order")
        if spec["symbol"] is not None:
            # windows.build_stage: a named use is its definition's whole spec.
            definition = named.get(spec["symbol"])
            if definition is None or not self.same_specification(
                c["specification"], self[definition]["specification"]
            ):
                raise _Mismatch("window named specification")
            used.append(definition)
        # Derived casts (_Check's "window aggregate"/"window cast" relation).
        argument_cast, result_cast = None, _rank_cast(self.family, function)
        if function in schema.WINDOW_AGGREGATES:
            reads = [a["read"] for a in arguments if a["read"] is not None]
            argument_cast, result_cast = _aggregate_casts(
                self.family,
                function,
                self[self[reads[0]]["realization"]]["tag"] if reads else None,
            )
        if result_cast is not None:
            o("CAST(", "window_result_cast_open")
        o(schema.WINDOW_SPELLING[function] + "(", "window_open")
        if function == "count" and not arguments:
            o("*", "window_row_count")
        for index, argument in enumerate(arguments):
            if index:
                o(", ", "window_argument_separator")
            if argument["read"] is not None:
                read = self[argument["read"]]
                if argument_cast is not None:
                    o("CAST(", "window_argument_cast_open")
                self.resolve(alias, read)
                self.ident(alias, "window_argument_scope", read["terminal"])
                o(".", "window_argument_qualifier")
                self.ident(read["name"], "window_argument_column", read["terminal"])
                if argument_cast is not None:
                    o(" AS " + argument_cast + ")", "window_argument_cast_close")
            else:
                self.emit(
                    self.window_literal(c, argument),
                    "literal",
                    "window_argument_literal",
                    reference,
                )
        o(")", "window_close")
        o(" OVER ", "window_over")
        if spec["symbol"] is not None:
            self.ident(self.name(spec["symbol"]), "window_reference", reference)
        else:
            inner = self.offset
            o("(", "window_spec_open")
            self.window_specification(c["specification"], reference, alias)
            o(")", "window_spec_close")
            self.enclose("window_specification", reference, inner)
        if result_cast is not None:
            o(" AS " + result_cast + ")", "window_result_cast_close")
        self.enclose("window", reference, start)

    # -- units ------------------------------------------------------------
    def row_select(self, unit) -> None:
        body = self[unit]
        scan_ref = body["scan"]
        scan = self[scan_ref]
        alias = self.name(scan["symbol"])
        ident = self.ident
        block_kind = body["block_kind"]
        columns = body["columns"]
        kinds = [c.kind for c in columns]
        if block_kind not in _BODY_COLUMNS or any(
            kind not in _BODY_COLUMNS[block_kind] for kind in kinds
        ):
            raise _Mismatch("body columns")
        if len(set(columns)) != len(columns):
            raise _Mismatch("body duplicate column")
        if (body["predicate"] is not None) is not (block_kind in _FILTER_KINDS):
            raise _Mismatch("body predicate")
        if (body["aggregation"] is not None) is not (block_kind == "aggregate"):
            raise _Mismatch("body aggregation")
        if (body["window"] is not None) is not (block_kind == "window"):
            raise _Mismatch("body window")
        stage = None if body["aggregation"] is None else self[body["aggregation"]]
        if stage is not None:
            if tuple(columns) != (*stage["keys"], *stage["values"]):
                raise _Mismatch("body group keys")
            if not stage["values"]:
                raise _Mismatch("body aggregate values")
            # GROUP BY writes alias.name: keys differ by the name written.
            names = [self[self[key]["read"]]["name"] for key in stage["keys"]]
            if len(set(names)) != len(names):
                raise _Mismatch("body key reads")
        if block_kind == "window" and "window_column" not in kinds:
            raise _Mismatch("body window columns")
        if block_kind == "let" and kinds.count("row_value_column") != 1:
            raise _Mismatch("body let value")
        if scan_ref.kind == "row_scan":
            inputs = self.columns_of(scan["realization"])
        elif scan_ref.kind in ("row_named_use", "row_join_use", "row_stage_use"):
            # A stage use reads the body before it, never a projection (the last).
            if (
                scan_ref.kind == "row_stage_use"
                and self[scan["body"]]["block_kind"] == "projection"
            ):
                raise _Mismatch("chain reads")
            self.take(unit, scan["body"], scan_ref.kind != "row_named_use")
            inputs = self.columns_of(scan["body"])
        else:
            raise _Mismatch("scan kind")
        # compiled lowering (ROW_SHAPE): a satisfying filters an aggregate, a
        # qualify a window, and a where neither.
        if block_kind in _FILTER_KINDS:
            under = (
                self[scan["body"]]["block_kind"]
                if scan_ref.kind == "row_stage_use"
                else ""
            )
            if block_kind != {"aggregate": "satisfying", "window": "qualify"}.get(
                under, "where"
            ):
                raise _Mismatch("filter kind")
        # realize_stages: a body's index is its block's place in the definition.
        chained = scan_ref.kind == "row_stage_use"
        if body["index"] != (self[scan["body"]]["index"] + 1 if chained else 0):
            raise _Mismatch("chain reads")
        if block_kind in _CARRYING:
            n = len(inputs)
            carried = [self[self[c]["read"]]["name"] for c in columns[:n]]
            if (
                kinds[:n] != ["row_carry_column"] * n
                or "row_carry_column" in kinds[n:]
                or carried != [name for name, _ in inputs]
            ):
                raise _Mismatch("body carry columns")
        # A CTE's projection also has a select item (the final one:
        # final_columns); a MySQL SELECT always has one (realize_rows'
        # zero_column_stage_not_admitted_on_target).
        if not columns and (
            block_kind == "projection" and not body["final"] or self.family == "mysql"
        ):
            raise _Mismatch("body projection columns")
        # MySQL ranks a `first` or `last` in a derived table (S13).
        ranks: dict[Ref, str] = {}
        listed: dict[str, Any] = {}
        relation = inputs
        if (
            self.family == "mysql"
            and stage is not None
            and any(self[v]["function"] in _ORDERED_VALUE for v in stage["values"])
        ):
            listed, ranks = self.ranked_layout(stage)
            known = dict(inputs)
            if any(name not in known for name in listed):
                raise _Mismatch("column reference")
            relation = self.exposed(
                [(name, known[name]) for name in listed]
                + [(name, ("rank", value)) for value, name in ranks.items()]
            )
        outer = self.enter([(alias, relation)])
        self.syntax("SELECT ", "select", body["block"])
        windows = None if body["window"] is None else self[body["window"]]
        named = (
            {}
            if windows is None
            else {self[d]["symbol"]: d for d in windows["definitions"]}
        )
        used: list[Ref] = []
        if (
            self.family == "mysql"
            and kinds.count("window_column") > _MYSQL_WINDOW_LIMIT
        ):
            raise _Mismatch("window count")
        triples = {
            "row_carry_column": ("carry_scope", "carry_qualifier", "carry_column"),
            "aggregate_key_column": (
                "group_key_scope",
                "group_key_qualifier",
                "group_key_column",
            ),
            "aggregate_projection_column": (
                "result_scope",
                "result_qualifier",
                "result_column",
            ),
            "window_projection_column": (
                "window_result_scope",
                "window_result_qualifier",
                "window_result_column",
            ),
        }
        for position, column_ref in enumerate(columns):
            column = self[column_ref]
            if position:
                self.syntax(", ", "separator", column["export"])
            kind = column_ref.kind
            if kind in triples:
                scope_role, qualifier_role, column_role = triples[kind]
                read = self[column["read"]]
                self.resolve(alias, read)
                ident(alias, scope_role, column["input_port"])
                self.syntax(".", qualifier_role, column["export"])
                ident(read["name"], column_role, read["terminal"])
            elif kind == "aggregate_value_column" and column_ref in ranks:
                self.ranked_value(column_ref, alias, ranks[column_ref])
            elif kind == "aggregate_value_column":
                self.aggregate_value(column_ref, alias)
            elif kind == "window_column":
                self.window_value(column_ref, alias, named, used)
            else:
                self.scalar(column["value"], alias)
            self.syntax(" AS ", "alias", column["export"])
            ident(column["label"], "label", column["export"])
        if ranks:
            assert stage is not None
            self.syntax(" FROM ", "from", stage["aggregation"])
            self.ranked_rows(unit, alias, inputs, listed, ranks, outer)
        else:
            self.scan_from(unit, alias, outer)
        if stage is not None and stage["keys"]:
            self.syntax(" GROUP BY ", "group_by", stage["aggregation"])
            for position, key_ref in enumerate(stage["keys"]):
                key = self[key_ref]
                if position:
                    self.syntax(", ", "group_separator", key["key"])
                start = self.offset
                read = self[key["read"]]
                self.resolve(alias, read)
                ident(alias, "grouping_scope", key["input_port"])
                self.syntax(".", "grouping_qualifier", key["key"])
                ident(read["name"], "grouping_column", read["terminal"])
                self.enclose("grouping", key["key"], start)
        # windows.build_stage: one definition per used declaration and spec,
        # created at its first use, so the clause lists exactly the used ones.
        if windows is not None and list(dict.fromkeys(used)) != list(
            windows["definitions"]
        ):
            raise _Mismatch("window definition use")
        self.window_clause(body["window"], alias)
        if body["predicate"] is not None:
            predicate = self[body["predicate"]]
            role = "satisfying" if block_kind == "satisfying" else "where"
            self.syntax(" WHERE ", role, predicate["original"])
            self.scalar(predicate["value"], alias)
        self.visible = outer

    def scan_from(self, unit, alias, outer) -> None:
        """FROM one body's own scan, AS its alias."""
        ident = self.ident
        scan_ref = self[unit]["scan"]
        scan = self[scan_ref]
        if scan_ref.kind == "row_scan":
            source = self[scan["realization"]]
            self.syntax(" FROM ", "from", scan["source"])
            ident(source["namespace"], "namespace", scan["source"])
            self.syntax(".", "qualifier", scan["source"])
            ident(source["name"], "relation", scan["source"])
            self.syntax(" AS ", "alias", scan["use"])
            ident(alias, "relation_scope", scan["use"])
        elif scan_ref.kind == "row_named_use":
            reference = self.block(scan["body"])
            self.syntax(" FROM ", "from", reference)
            ident(self.cte_reference(scan["body"]), "cte_reference", reference)
            self.syntax(" AS ", "alias", scan["use"])
            ident(alias, "relation_scope", scan["use"])
        elif scan_ref.kind == "row_join_use":
            reference = self[scan["body"]]["join"]
            self.syntax(" FROM ", "from", reference)
            ident(self.cte_reference(scan["body"]), "join_reference", reference)
            self.syntax(" AS ", "alias", scan["tail"])
            ident(alias, "join_scope", scan["tail"])
        else:
            reference = self.block(scan["body"])
            self.syntax(" FROM ", "from", reference)
            if self.inline(scan["body"]):
                self.syntax("(", "inline_open", reference)
                inner, self.visible = self.visible, outer
                self.unit_select(scan["body"])
                self.visible = inner
                self.syntax(")", "inline_close", reference)
            else:
                ident(self.cte_reference(scan["body"]), "stage_reference", reference)
            self.syntax(" AS ", "alias", scan["block"])
            ident(alias, "stage_scope", scan["block"])

    def result_select(self, unit) -> None:
        body = self[unit]
        scan = self[body["scan"]]
        alias = self.name(scan["symbol"])
        ident = self.ident
        projection = scan["body"]
        # results: a result body carries its projection's visible outputs
        # (an export, not a hidden ORDER key's port), in order.
        if projection.kind != "row_body":
            raise _Mismatch("result reads")
        columns = self.columns_of(projection)
        # A result use reads its projection, as a stage use never does.
        if self[projection]["block_kind"] != "projection":
            raise _Mismatch("result projection")
        self.take(unit, projection, True)
        carried = self[projection]["columns"]
        shown = [self[c]["export"].kind == "export" for c in carried]
        hidden = [c for c, show in zip(carried, shown, strict=True) if not show]
        stages = {self[c]["column"]: c for c in carried}
        items = () if body["order"] is None else self[body["order"]]["items"]
        reads = list(dict.fromkeys(self[i]["read"] for i in items))
        # project_sql_plan_results.build: only an ORDER without DISTINCT
        # carries hidden ports (distinct_tuple_includes_hidden_value), after
        # the exports, one carried key per distinct key its items read, in
        # the order they first read them; an item reads its key's hidden
        # port, an aggregate composition's item its exported value (results:
        # bound_port). Under DISTINCT an item reads its target's export (the
        # source ports build gives each ORDER use), which PIE-B1003 keeps to
        # a bare value or an aggregate composition.
        if hidden and body["distinct"] is not None:
            raise _Mismatch("result hidden")
        tail = [self[c]["column"] for c in carried[len(carried) - len(hidden) :]]
        if [r for r in reads if stages.get(r) in hidden] != tail:
            raise _Mismatch("result hidden")
        keys = {
            self[self[c]["read"]]["name"]
            for c in hidden
            if c.kind == "row_carry_column"
        }
        if len(keys) != len(hidden):
            raise _Mismatch("result hidden")
        # A composition only exists over an aggregate in the projection's chain.
        below, aggregated = projection, False
        while self[below]["scan"].kind == "row_stage_use":
            below = self[self[below]["scan"]]["body"]
            aggregated = aggregated or self[below]["block_kind"] == "aggregate"
        values = {
            r: self[c]["value"].kind if c.kind == "row_value_column" else None
            for r, c in stages.items()
        }
        if any(
            r in stages
            and stages[r] not in hidden
            and (
                body["distinct"] is None
                or values[r] not in (None, "sql_stage_reference")
            )
            and not (aggregated and values[r] == "sql_operation")
            for r in reads
        ):
            raise _Mismatch("result hidden")
        visible = [name for (name, _), show in zip(columns, shown, strict=True) if show]
        if [self[self[c]["read"]]["name"] for c in body["columns"]] != visible:
            raise _Mismatch("result reads")
        outer = self.enter([(alias, columns)])
        self.syntax("SELECT ", "select", self.block(unit))
        if body["distinct"] is not None:
            self.syntax("DISTINCT ", "distinct", self[body["distinct"]]["distinct"])
        for position, column_ref in enumerate(body["columns"]):
            column = self[column_ref]
            read = self[column["read"]]
            if position:
                self.syntax(", ", "separator", column["export"])
            self.resolve(alias, read)
            ident(alias, "result_carry_scope", column["projection_port"])
            self.syntax(".", "result_carry_qualifier", column["export"])
            ident(read["name"], "result_carry_column", read["terminal"])
            self.syntax(" AS ", "alias", column["export"])
            ident(column["label"], "label", column["export"])
        reference = self.block(projection)
        self.syntax(" FROM ", "from", reference)
        if self.inline(projection):
            # Only a capturing let's own (inline) result body reads one, and
            # the exporter refuses that body.
            raise _Mismatch("inline result")
        ident(self.cte_reference(projection), "stage_reference", reference)
        self.syntax(" AS ", "alias", scan["boundary"])
        ident(alias, "result_scope", scan["boundary"])
        if body["order"] is not None:
            order = self[body["order"]]
            # results: an ORDER without realized items is order_item_inventory_drift.
            if not order["items"]:
                raise _Mismatch("order items")
            self.syntax(" ORDER BY ", "order_by", order["order"])
            for index, item_ref in enumerate(order["items"]):
                item = self[item_ref]
                read = self[item["read"]]
                if item["position"] != index:
                    raise _Mismatch("order position")
                if index:
                    self.syntax(", ", "order_separator", item["item"])
                start = self.offset
                self.resolve(alias, read)
                ident(alias, "order_scope", item["port"])
                self.syntax(".", "order_qualifier", item["item"])
                ident(read["name"], "order_column", read["terminal"])
                if item["direction"] not in schema.DIRECTIONS:
                    raise _Mismatch("order direction")
                direction = schema.DIRECTIONS[item["direction"]]
                self.syntax(direction, "order_direction", item["item"])
                self.enclose("order_item", item["item"], start)
        if body["limit"] is not None:
            limit = self[body["limit"]]
            self.syntax(" LIMIT ", "limit", limit["limit"])
            if type(limit["value"]) is not int or limit["value"] < 0:
                raise _Mismatch("limit value")
            self.emit(str(limit["value"]), "literal", "limit_value", limit["limit"])
        self.visible = outer

    def cte_columns(self, symbols, exports) -> None:
        """One name per column of the unit (the AST's one symbol per
        terminal), at least one (a CTE header cannot be empty:
        zero_column_stage_not_admitted_on_target); SQL gives name i the value
        of SELECT item i, so symbol i is bound to the one terminal item i
        exports (exports[i])."""
        if not symbols or len(symbols) != len(exports):
            raise _Mismatch("cte columns")
        if any(
            {self[s]["binding"]} != terminals for s, terminals in zip(symbols, exports)
        ):
            raise _Mismatch("cte column identity")
        self.exposed(
            [(self.name(s), ("terminal", self[s]["binding"])) for s in symbols]
        )
        for position, symbol_ref in enumerate(symbols):
            symbol = self[symbol_ref]
            if position:
                self.syntax(", ", "terminal_separator", symbol["binding"])
            self.ident(symbol["name"], "terminal_column", symbol["binding"])

    def set_select(self, unit) -> None:
        body = self[unit]
        reference = body["body"]
        if (
            body["kind"] not in schema.SET_KINDS
            or body["quantifier"] not in schema.SET_QUANTIFIERS
        ):
            raise _Mismatch("set operator")
        operator = (
            " "
            + schema.SET_KINDS[body["kind"]]
            + " "
            + schema.SET_QUANTIFIERS[body["quantifier"]]
            + " "
        )
        operands = body["operands"]
        count = len(operands)
        if count < 2:
            raise _Mismatch("set arity")
        for _ in range(count - 2):
            self.syntax("(", "set_fold_open", reference)
        self.set_operand(unit, operands[0], 0)
        for position, operand in enumerate(operands[1:], start=1):
            self.syntax(operator, "set_operator", reference)
            self.set_operand(unit, operand, position)
            if position < count - 1:
                self.syntax(")", "set_fold_close", reference)

    def set_operand(self, unit, operand_ref, index) -> None:
        unit_columns = self[unit]["columns"]
        operand = self[operand_ref]
        reference = operand["operand"]
        alias = self.name(operand["symbol"])
        ident = self.ident
        producer = operand["producer"]
        if producer.kind != "bound_source":
            self.take(unit, producer, False)
        columns = self.columns_of(producer)
        # UNION aligns by position: an operand selects each of its
        # relation's columns, in order.
        if [self[c]["name"] for c in operand["columns"]] != [
            name for name, _ in columns
        ]:
            raise _Mismatch("set operand reads")
        outer = self.enter([(alias, columns)])
        self.syntax("(", "set_operand_open", reference)
        self.syntax("SELECT ", "select", reference)
        if len(operand["columns"]) != len(unit_columns) or len(
            operand["inputs"]
        ) != len(unit_columns):
            raise _Mismatch("set operand width")
        for position, column_ref in enumerate(operand["columns"]):
            column = self[column_ref]
            subject = operand["inputs"][position]
            # UNION aligns by position: item i is set column i's input here.
            if column_ref != self[unit_columns[position]]["inputs"][index]:
                raise _Mismatch("set operand alignment")
            if position:
                self.syntax(", ", "separator", subject)
            self.resolve(alias, column)
            ident(alias, "set_input_scope", subject)
            self.syntax(".", "set_input_qualifier", subject)
            ident(column["name"], "set_input_column", column["terminal"])
            self.syntax(" AS ", "alias", subject)
            output = self[unit_columns[position]]
            ident(output["label"], "label", output["export"])
        self.syntax(" FROM ", "from", reference)
        if producer.kind == "bound_source":
            source = self[producer]
            ident(source["namespace"], "set_namespace", operand["source"])
            self.syntax(".", "set_qualifier", operand["source"])
            ident(source["name"], "set_relation", operand["source"])
        else:
            ident(self.cte_reference(producer), "set_reference", self.block(producer))
        self.syntax(" AS ", "set_alias", reference)
        ident(alias, "set_scope", reference)
        self.syntax(")", "set_operand_close", reference)
        self.visible = outer

    def join_relation(self, item_ref) -> None:
        item = self[item_ref]
        reference = item["original"]
        producer = item["producer"]
        if producer.kind == "bound_source":
            source = self[producer]
            self.ident(source["namespace"], "join_namespace", item["source"])
            self.syntax(".", "join_qualifier", item["source"])
            self.ident(source["name"], "join_relation", item["source"])
        elif self.inline(producer):
            # The exporter refuses a LATERAL input (portable fields(): _Outside).
            raise _Mismatch("lateral input")
        else:
            self.ident(self.cte_reference(producer), "join_reference", reference)
        self.syntax(" AS ", "join_alias", reference)
        self.ident(self.name(item["symbol"]), "join_scope", reference)

    def full_condition(self, value) -> None:
        """joins._condition_equalities: a FULL JOIN's ON is an AND tree of
        `==` between direct fields of the two inputs (shape only; the
        operands' domain is not re-derived here)."""
        v = self[value] if value.kind == "sql_operation" else None
        if v is not None and (v["kind"], v["operator"]) == ("logical", "and"):
            for operand in v["operands"]:
                self.full_condition(operand)
            return
        if (
            v is None
            or (v["kind"], v["operator"]) != ("comparison", "==")
            or any(o.kind != "sql_stage_reference" for o in v["operands"])
        ):
            raise _Mismatch("full join condition")
        # Two inputs by the alias written (a cloned symbol has a new ref).
        left, right = (self.name(self[o]["scope"]) for o in v["operands"])
        if left == right:
            raise _Mismatch("full join condition")

    def join_select(self, unit) -> None:
        body = self[unit]
        reference = body["join"]
        if len(body["inputs"]) != 2:
            raise _Mismatch("join inputs")
        left, right = body["inputs"]
        ident = self.ident
        for index, item in enumerate((left, right)):
            producer = self[item]["producer"]
            if producer.kind != "bound_source":
                # A chained JOIN's left input reads the JOIN before it.
                self.take(unit, producer, not index and producer.kind == "join_body")
        relations = [
            (self.name(self[item]["symbol"]), self.columns_of(self[item]["producer"]))
            for item in (left, right)
        ]
        # An input's pre-match reads are its relation's columns, in order.
        for item, (_, columns) in zip((left, right), relations, strict=True):
            names = [self[r]["name"] for r in self[item]["columns"]]
            if names != [name for name, _ in columns]:
                raise _Mismatch("join input reads")
        outer = self.enter(relations)
        owned = {
            self.name(self[item]["symbol"]): self[item]["columns"]
            for item in (left, right)
        }
        # _join_body publishes every pre-match read, the left input's then
        # the right's: column i carries read i.
        ordered = (*self[left]["columns"], *self[right]["columns"])
        if len(body["columns"]) != len(ordered):
            raise _Mismatch("join columns")
        kind = body["join_kind"]
        self.syntax("SELECT ", "select", reference)
        for written, column_ref in enumerate(body["columns"]):
            column = self[column_ref]
            read = self[column["read"]]
            if written:
                self.syntax(", ", "separator", column["port"])
            if column["read"] != ordered[written]:
                raise _Mismatch("join columns")
            scope = self.name(column["scope"])
            self.owner(owned, scope, column["read"])
            self.resolve(scope, read)
            # Nulling is the earlier JOIN's (a chained first input keeps it)
            # plus this JOIN where its kind null-extends the side as written.
            side = list(owned).index(scope)
            extended = kind == "full" or (kind, side) in (("left", 1), ("right", 0))
            kept: Any = ()
            if side == 0 and self[left]["producer"].kind == "join_body":
                earlier = self[self[left]["producer"]]["columns"]
                kept = [
                    self[c]["nulling"]
                    for c in earlier
                    if self[c]["port"] == read["terminal"]
                ]
                kept = kept[0] if len(kept) == 1 else None
            nulling = column["nulling"]
            if (
                kept is None
                or nulling[: len(kept)] != kept
                or len(nulling) != len(kept) + extended
            ):
                raise _Mismatch("join nulling")
            ident(scope, "join_column_scope", column["match"])
            self.syntax(".", "join_column_qualifier", column["port"])
            ident(read["name"], "join_column", read["terminal"])
            self.syntax(" AS ", "alias", column["port"])
            ident(column["label"], "label", column["port"])
        self.syntax(" FROM ", "from", reference)
        self.join_relation(left)
        if body["membership"] is not None:
            # SEMI/ANTI: `semi join` fails parsing and `where any` lowers to
            # a block read, so no real document carries one.
            raise _Mismatch("join membership")
        # joins.full_admissible: MySQL has no FULL JOIN.
        if kind not in schema.JOIN_SPELLING or (
            self.family == "mysql" and kind == "full"
        ):
            raise _Mismatch("join kind")
        self.syntax(schema.JOIN_SPELLING[kind], "join_kind", reference)
        self.join_relation(right)
        if kind != "cross":
            self.syntax(" ON ", "join_on", reference)
            # A relationship equality needs the retired source spelling; no
            # modern source writes one, so it fails closed.
            if body["equalities"]:
                raise _Mismatch("relationship equality")
            if body["predicate"] is None:
                raise _Mismatch("join condition")
            if kind == "full":
                self.full_condition(body["predicate"])
            saved, self.owned = self.owned, owned
            self.scalar(body["predicate"], "")
            self.owned = saved
        elif body["predicate"] is not None:
            raise _Mismatch("cross join predicate")
        self.visible = outer

    # -- statements -------------------------------------------------------
    def row_query(self, query) -> None:
        q = self[query]
        units = q["bodies"] if query.kind == "sql_row_query" else q["units"]
        if not units:
            raise _Mismatch("no units")
        *ctes, final = units
        if ctes:
            self.syntax("WITH ", "with", _SCOPE)
            for index, unit in enumerate(ctes):
                reference = self.block(unit)
                if index:
                    self.syntax(", ", "cte_separator", reference)
                if self[unit]["symbol"] is None:
                    raise _Mismatch("cte symbol")
                name = self.cte_name(self.name(self[unit]["symbol"]))
                self.ident(name, "cte_name", reference)
                self.syntax(" (", "cte_columns_open", reference)
                self.cte_columns(
                    self[unit]["cte_columns"],
                    [
                        {self[self[c]["column"]]["terminal"]}
                        for c in self[unit]["columns"]
                    ],
                )
                self.syntax(") AS (", "cte_body_open", reference)
                self.outer_select(unit)
                self.syntax(")", "cte_body_close", reference)
                self.ctes[name] = unit
            self.syntax(" ", "with_body", self.block(final))
        # The statement selects its definition's last unit (by_definition).
        self.take(None, final, False)
        self.final_columns(final)
        self.outer_select(final)
        # The AST assembly writes each unit once, a CTE for a later reader,
        # and a body a chain read reads is read by nothing else.
        self.all_read(ctes)
        chained = set(self.chained)
        if len(chained) != len(self.chained) or chained & self.published:
            raise _Mismatch("chain readers")
        everything = [ref for kind in UNITS for ref in self.doc.all(kind)]
        if len(set(self.rendered)) != len(self.rendered) or set(self.rendered) != set(
            everything
        ):
            raise _Mismatch("unit rendered")

    def outer_select(self, unit) -> None:
        # A capturing let is realized inline at its reader's single read, and
        # its captures write that row body's scan alias (_inline_target).
        reader = unit.kind == "row_body"
        self.reader = self.name(self[self[unit]["scan"]]["symbol"]) if reader else None
        self.unit_select(unit)
        self.before = unit

    def final_columns(self, unit) -> None:
        # The grammar requires a select clause with at least one item.
        if not self[unit]["columns"]:
            raise _Mismatch("final columns")

    def select_query(self, ast) -> None:
        """render_sql: the Slice08-era single SELECT with simple CTEs."""
        a = self[ast]
        ident = self.ident

        def select(body_ref, subject):
            body = self[body_ref]
            scan_ref = body["scan"]
            scan = self[scan_ref]
            scope = self.name(scan["symbol"])
            if scan_ref.kind == "sql_scan":
                inputs = self.columns_of(scan["realization"])
            else:
                self.cte_reference(scan["cte"])
                self.take(None, scan["cte"], False)
                inputs = self.exposed(
                    [
                        (self.name(s), ("terminal", self[s]["binding"]))
                        for s in self[scan["cte"]]["columns"]
                    ]
                )
            outer = self.enter([(scope, inputs)])
            self.syntax("SELECT ", "select", subject)
            for i, column_ref in enumerate(body["columns"]):
                column = self[column_ref]
                if i:
                    self.syntax(", ", "separator", column["projection"])
                literal = column_ref.kind == "sql_literal_column"
                if literal and column["value"] is not None:
                    self.constant(column["value"])
                else:
                    if literal:
                        if column["producer"] is None:
                            raise _Mismatch("literal producer")
                        producer = self[column["producer"]]
                        input_port, port = producer["input_port"], producer["terminal"]
                    else:
                        input_port = column["input_port"]
                        port = (
                            column["source_port"]
                            if scan_ref.kind == "sql_scan"
                            else self[column["producer"]]["terminal"]
                        )
                    read = {
                        "name": self.name(column["symbol"]),
                        "terminal": port,
                        "field": column.get("source_field"),
                    }
                    self.resolve(scope, read)
                    ident(scope, "column_scope", input_port)
                    self.syntax(".", "qualifier", column["projection"])
                    ident(self.name(column["symbol"]), "column", port)
                self.syntax(" AS ", "alias", column["projection"])
                ident(column["label"], "label", column["export"])
            if scan_ref.kind == "sql_scan":
                source = self[scan["realization"]]
                self.syntax(" FROM ", "from", scan["source"])
                ident(source["namespace"], "namespace", scan["source"])
                self.syntax(".", "qualifier", scan["source"])
                ident(source["name"], "relation", scan["source"])
            else:
                cte = self[scan["cte"]]
                ref = self[cte["definition"]]["original"]
                self.syntax(" FROM ", "from", ref)
                ident(self.name(cte["symbol"]), "cte_reference", ref)
            self.syntax(" AS ", "alias", scan["use"])
            ident(scope, "relation_scope", scan["use"])
            self.visible = outer

        # The terminals each export is bound to (an item's value leaves its
        # SELECT through the terminal binding whose canonical is its export).
        bound: dict[Any, set] = {}
        for t in self.doc.all("terminal_binding"):
            bound.setdefault(self[t]["canonical"], set()).add(self[t]["terminal"])
        if a["ctes"]:
            self.syntax("WITH ", "with", _SCOPE)
            for i, cte_ref in enumerate(a["ctes"]):
                cte = self[cte_ref]
                ref = self[cte["definition"]]["original"]
                if i:
                    self.syntax(", ", "cte_separator", ref)
                name = self.cte_name(self.name(cte["symbol"]))
                ident(name, "cte_name", ref)
                self.syntax(" (", "cte_columns_open", ref)
                self.cte_columns(
                    cte["columns"],
                    [
                        bound.get(self[c]["export"], set())
                        for c in self[cte["body"]]["columns"]
                    ],
                )
                self.syntax(") AS (", "cte_body_open", ref)
                select(cte["body"], ref)
                self.syntax(")", "cte_body_close", ref)
                self.ctes[name] = cte_ref
            self.syntax(" ", "with_body", self[a["definition"]]["original"])
        self.final_columns(ast)
        select(ast, _SCOPE)
        self.all_read(a["ctes"])


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
