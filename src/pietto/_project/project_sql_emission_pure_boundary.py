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
    }
)
RELATION_ROLES = {
    "namespace": "namespace",
    "set_namespace": "namespace",
    "join_namespace": "namespace",
    "relation": "name",
    "set_relation": "name",
    "join_relation": "name",
}
UNIT_REFERENCE_ROLES = frozenset(
    {"cte_reference", "stage_reference", "join_reference", "set_reference"}
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
        _require(
            all(ref in position for kind in UNITS for ref in doc.all(kind)),
            "orphan unit",
        )
        return units

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
        for ref in doc.all("sql_operation"):
            op = doc[ref]
            _require(op["kind"] in schema.OPERATORS, "operation kind")
            _require(
                op["operator"] in schema.OPERATORS[op["kind"]], "operation operator"
            )
            arity = 1 if op["kind"] in ("sign", "null_test") else 2
            _require(len(op["operands"]) == arity, "operation arity")
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
                        and re.fullmatch(r"(0|[1-9][0-9]*) " + suffix, str(text)),
                        "frame offset",
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
        operations = self.index("sql_operation", "original")
        unaries = self.index("sql_unary", "original")
        anchors = self.index("sql_anchor", "original")
        literals = self.index("sql_literal", "site")
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
        per_subject: dict[tuple[str, PlanRef], list[str]] = {}
        for unit, start, end in self.segments():
            aliases = self.aliases(unit)
            labels = []
            for i in range(start, end):
                event, text = self.events[i], self.texts[i]
                role, subject, kind = event["role"], event["subject"], event["kind"]
                _require(role not in PREAMBLE_ROLES, "token role placement")
                if kind == "identifier":
                    name = self.identifier(i)
                    if role == "label":
                        labels.append(name)
                    elif role in SCOPE_ROLES:
                        _require(name in aliases, "scope alias")
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
                    else:
                        raise _Reject(Status.INVALID_RELATION, "literal role")
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
            _require(labels == self.labels(unit), "output labels")
        for (role, subject), texts in per_subject.items():
            if role == "window_argument_literal":
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
        if role in schema.SYNTAX:
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
        }
        for kind, role, key, port, read in (
            ("sql_stage_reference", "reference", "original", "port", "column"),
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
            if overlay["role"] in ("reference", "grouping", "order_item"):
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


class _Requirements:
    """Independent re-enumeration of both requirement inventories."""

    def __init__(self, check: _Check, units: list[Ref]) -> None:
        self.check = check
        self.doc = check.doc
        self.units = units
        doc = self.doc
        self.premises = [(ref, doc[ref]) for ref in check.request["premises"]]
        self.expected: list[tuple[str, Any, str, Any]] = []

    def statement(self, *keys: str) -> tuple[Ref, ...]:
        return tuple(
            ref
            for ref, p in self.premises
            if p["scope"] == "statement" and p["key"] in keys
        )

    def add(self, kind: str, subject: Any, rule: str, premises: Any) -> None:
        self.expected.append((kind, subject, rule, premises))

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
        if value.kind in ("sql_stage_reference", "sql_operation"):
            return doc[doc[value]["realization"]]["tag"]
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
        if value.kind == "sql_stage_reference":
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
            "R06" if kind == "logical" else "R05",
            self.node_premises(self.tag(value), operands, kind),
        )
        for operand in fields["operands"]:
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
        for item, (kind, subject, rule, premises) in zip(
            actual, self.expected, strict=True
        ):
            _require(
                (item["kind"], item["subject"], item["rule"]) == (kind, subject, rule),
                "generated inventory entry",
            )
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
        for kind in ("sql_operation", "sql_stage_reference", "sql_unary", "sql_anchor"):
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
        operators = self.statement("operator_environment")
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
            scan = fields["scan"]
            item = doc[scan]
            if scan.kind == "row_scan":
                self.scan(scan, item["realization"])
            elif scan.kind == "row_named_use":
                self.add("named_use", item["use"], "R03", naming)
                for binding in doc[item["binding"]]["bindings"]:
                    self.add(
                        "immediate_terminal", doc[binding]["terminal"], "R03", naming
                    )
            elif scan.kind == "row_join_use":
                self.add("join_use", item["tail"], "R07", naming)
                for symbol in doc[item["body"]]["cte_columns"]:
                    self.add("join_terminal", doc[symbol]["binding"], "R07", naming)
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
                    self.add("aggregate", item["aggregate"], "R13", operators)
                    if item["argument"] is not None:
                        self.value(item["argument"])
                elif kind == "aggregate_projection_column":
                    self.add("result_projection", item["projection"], "R12", ())
                elif kind == "window_column":
                    origin = doc[doc[item["column"]]["window"]]
                    spec = doc[item["specification"]]
                    self.add("window_computation", item["window"], "R14", operators)
                    self.add("window_specification", origin["policy"], "R15", ())
                    for partition in spec["partitions"]:
                        read = doc[doc[partition]["read"]]
                        self.add(
                            "window_partition_comparison", read["terminal"], "R14", ()
                        )
                    for order in spec["orders"]:
                        read = doc[doc[order]["read"]]
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
        if len(units) > 1:
            self.add("nonrecursive_with_bytes", self.check.ast, "R23", ())

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
