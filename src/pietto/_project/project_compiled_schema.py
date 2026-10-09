"""Closed data for compiled programs; decoding never grants execution authority."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any

__all__: tuple[str, ...] = ()

FORMAT = "pietto.compiled-execution.v1"
VERSIONS = (1, 1, 1, 1)
MEMBERS = ("structure", "parameters", "targets", "obligations", "outputs")
MAX_BYTES = 32 * 1024 * 1024
MAX_VALUES = 1 << 20
MAX_RECORDS = 1 << 17
MAX_EDGES = 1 << 19
MAX_DEPTH = 32
MAX_EXPRESSION_DEPTH = 256
MAX_FIELDS = 512
MAX_TEXT_BYTES = 1024 * 1024
CONTENT_DOMAIN = b"pietto.compiled-execution.content.v1\0"

# Each production has one fixed field order. References are typed addresses,
# not names, Python class paths, constructor arguments or persisted handles.
FIELDS = {
    "entry": ("declaration", "terminal", "exports", "requests", "retained"),
    "target": ("family", "release", "contract", "profile"),
    "premise": ("position", "key", "scope", "value"),
    "expression_context": (
        "owner",
        "kind",
        "position",
        "block_kind",
        "block_position",
        "fields",
    ),
    "policy": ("literal_policy", "guarded", "refinement", "sources"),
    "declaration": (
        "module",
        "module_position",
        "position",
        "namespace",
        "kind",
        "label",
    ),
    "source": ("declaration", "namespace", "name", "fields", "family"),
    "source_unique": (
        "source",
        "shape",
        "position",
        "fields",
        "null_policy",
        "origin",
        "trust",
        "enforcement",
    ),
    "field": (
        "source",
        "ordinal",
        "label",
        "column",
        "logical",
        "physical",
        "decimal",
        "meaning",
    ),
    "use": ("consumer", "producer", "ordinal", "ports"),
    "port": ("owner", "ordinal", "label", "source", "logical"),
    "literal": ("tag", "value", "site"),
    "null_literal": ("site",),
    "read": ("port", "use", "role"),
    "operation": ("operator", "operands", "logical", "site"),
    "site": ("owner", "role", "ordinal", "ancestry", "disposition", "reason"),
    "slot": ("site", "literal", "tag"),
    "native_use": ("slot", "ordinal", "index", "physical"),
    "scan": ("owner", "use", "source", "outputs"),
    "row": (
        "owner",
        "use",
        "input",
        "stage",
        "values",
        "predicate",
        "outputs",
        "layout",
    ),
    "join": (
        "owner",
        "ordinal",
        "kind",
        "law",
        "source_positions",
        "inputs",
        "equalities",
        "predicate",
        "outputs",
        "layout",
    ),
    "join_value": ("owner", "input", "logical"),
    "join_equality": ("owner", "left", "right"),
    "aggregate": (
        "owner",
        "use",
        "input",
        "mode",
        "risk_law",
        "keys",
        "values",
        "outputs",
        "layout",
    ),
    "aggregate_value": ("function", "arguments", "logical"),
    "window": ("owner", "use", "input", "definitions", "values", "outputs", "layout"),
    "window_spec": ("partition", "ordering", "frame", "named"),
    "window_definition": ("ordinal", "label", "specification"),
    "window_value": (
        "function",
        "arguments",
        "specification",
        "inputs",
        "selected",
        "logical",
    ),
    "result": (
        "owner",
        "input",
        "projection",
        "distinct",
        "ordering",
        "limit",
        "limit_literal",
        "outputs",
        "layout",
    ),
    "set": ("owner", "kind", "quantifier", "operands", "outputs", "layout"),
    "set_value": ("owner", "inputs", "logical"),
    "request": ("owner", "use", "scope", "unit", "path", "hop", "pairs"),
    "match_use": ("owner", "position", "boundaries", "path"),
    "match_path": ("steps",),
    "match_step": (
        "ordinal",
        "module",
        "module_position",
        "position",
        "source",
        "target",
    ),
    "provider": (
        "source",
        "provider",
        "version",
        "revision",
        "registry",
        "definition",
        "tokens",
        "role",
        "guarantee",
    ),
    "requirement_origin": (
        "subject",
        "role",
        "provenance",
        "owner",
        "location",
        "antecedents",
    ),
    "requirement": (
        "family",
        "subkind",
        "subject",
        "definition",
        "stages",
        "uses",
        "origin",
        "anchors",
    ),
    "requirement_link": ("kind", "source", "target"),
    "output": ("ordinal", "label", "port", "logical", "meaning"),
}


class CompiledError(ValueError):
    """A value-free category; no bundle or parameter content enters diagnostics."""


@dataclass(frozen=True, slots=True)
class Address:
    kind: str
    position: int


@dataclass(frozen=True, slots=True)
class Scalar:
    tag: str
    value: bool | int | float | str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Record:
    address: Address
    values: tuple = field(repr=False)

    def get(self, name: str):
        return self.values[FIELDS[self.address.kind].index(name)]


@dataclass(frozen=True, slots=True)
class Description:
    compatibility: tuple
    producer: str
    query: Address
    members: tuple[tuple[str, tuple[Record, ...]], ...] = field(repr=False)

    @property
    def records(self) -> tuple[Record, ...]:
        return tuple(record for _, records in self.members for record in records)


def scalar_wire(value: Scalar) -> list:
    from pietto._project.project_sql_emission_parameters import value_valid

    if type(value) is not Scalar or not value_valid(value.tag, value.value, "mysql"):
        raise CompiledError("COMPILED_SCALAR")
    payload = value.value
    if value.tag == "Int":
        payload = str(payload)
    elif value.tag == "Float":
        payload = float(payload).hex()
    return [value.tag, payload]


def scalar_read(value: object) -> Scalar:
    if type(value) is not list or len(value) != 2 or type(value[0]) is not str:
        raise CompiledError("COMPILED_SCALAR")
    tag, payload = value
    try:
        if tag == "Int":
            if type(payload) is not str or len(payload) > 20:
                raise CompiledError("COMPILED_SCALAR")
            parsed: Any = int(payload)
            if str(parsed) != payload:
                raise CompiledError("COMPILED_SCALAR")
        elif tag == "Float":
            if type(payload) is not str or len(payload) > 32:
                raise CompiledError("COMPILED_SCALAR")
            parsed = float.fromhex(payload)
            if not math.isfinite(parsed) or parsed.hex() != payload:
                raise CompiledError("COMPILED_SCALAR")
        else:
            parsed = payload
        result = Scalar(tag, parsed)
        if scalar_wire(result) != value:
            raise CompiledError("COMPILED_SCALAR")
        return result
    except (ValueError, TypeError, OverflowError):
        raise CompiledError("COMPILED_SCALAR") from None


def address_read(value: object) -> Address:
    if (
        type(value) is not list
        or len(value) != 2
        or type(value[0]) is not str
        or value[0] not in FIELDS
        or type(value[1]) is not int
        or not 0 <= value[1] < MAX_RECORDS
    ):
        raise CompiledError("COMPILED_ADDRESS")
    return Address(value[0], value[1])


def _wire(value):
    if type(value) is Address:
        return {"ref": [value.kind, value.position]}
    if type(value) is Scalar:
        return {"scalar": scalar_wire(value)}
    if type(value) is tuple:
        return [_wire(item) for item in value]
    if type(value) in (type(None), bool, int, str):
        return value
    raise CompiledError("COMPILED_VALUE")


def _read(value):
    if type(value) is dict:
        if tuple(value) == ("ref",):
            return address_read(value["ref"])
        if tuple(value) == ("scalar",):
            return scalar_read(value["scalar"])
        raise CompiledError("COMPILED_VALUE")
    if type(value) is list:
        return tuple(_read(item) for item in value)
    if type(value) in (type(None), bool, int, str):
        return value
    raise CompiledError("COMPILED_VALUE")


def encode(description: Description) -> bytes:
    if type(description) is not Description:
        raise CompiledError("COMPILED_DESCRIPTION")
    document = {
        "format": FORMAT,
        "compatibility": _wire(description.compatibility),
        "producer": description.producer,
        "query": [description.query.kind, description.query.position],
        "members": [
            [
                name,
                [
                    [r.address.kind, r.address.position, _wire(r.values)]
                    for r in records
                ],
            ]
            for name, records in description.members
        ],
    }
    try:
        return json.dumps(
            document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise CompiledError("COMPILED_ENCODING") from None


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise CompiledError("COMPILED_DUPLICATE_KEY")
        result[key] = value
    return result


def _integer(text):
    if len(text) > 20:
        raise CompiledError("COMPILED_INTEGER")
    value = int(text)
    if not -(1 << 63) <= value < (1 << 63):
        raise CompiledError("COMPILED_INTEGER")
    return value


def _no_float(_text):
    raise CompiledError("COMPILED_NUMBER")


# Quoted spans exactly as _bounded_scan reads them: a backslash escapes any next
# byte and an unterminated tail stays quoted.
_QUOTED = re.compile(rb'"[^"\\]*+(?:\\.[^"\\]*+)*+(?:"|\\?\Z)', re.DOTALL)
_SQUARE = bytes.maketrans(b"{}", b"[]")
_NOT_BRACKET = bytes(b for b in range(256) if b not in b"[]{}")
_FAST_BYTES = 1 << 20  # bounds the accept-only path's transient memory


def _shallow(raw: bytes) -> bool:
    """Accept-only: unquoted brackets balanced and at most MAX_DEPTH deep."""
    nest = _QUOTED.sub(b"", raw).translate(_SQUARE, _NOT_BRACKET)
    for _ in range(MAX_DEPTH):
        if not nest:
            return True
        nest = nest.replace(b"[]", b"")
    return not nest


def _bounded(raw: bytes) -> None:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise CompiledError("COMPILED_BYTE_LIMIT")
    if len(raw) <= _FAST_BYTES and _shallow(raw):
        return
    _bounded_scan(raw)


def _bounded_scan(raw: bytes) -> None:
    # Check syntactic depth before the standard decoder can recurse. Quoted
    # brackets and escaped quotes never change structural depth.
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_DEPTH:
                raise CompiledError("COMPILED_DEPTH_LIMIT")
        elif byte in (93, 125):
            depth -= 1
            if depth < 0:
                raise CompiledError("COMPILED_JSON")


def json_value(raw: bytes):
    """The same finite JSON boundary for the envelope and embedded contracts."""
    _bounded(raw)
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_no_float,
            parse_constant=_no_float,
        )
        pending, count = [value], 0
        while pending:
            item = pending.pop()
            count += 1
            if count > MAX_VALUES:
                raise CompiledError("COMPILED_VALUE_LIMIT")
            if type(item) is str and len(item.encode("utf-8")) > MAX_TEXT_BYTES:
                raise CompiledError("COMPILED_TEXT_LIMIT")
            if type(item) is dict:
                pending.extend(item.keys())
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
        return value
    except CompiledError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise CompiledError("COMPILED_JSON") from None


def decode(raw: bytes) -> Description:
    try:
        value = json_value(raw)
        if type(value) is not dict or tuple(value) != (
            "format",
            "compatibility",
            "producer",
            "query",
            "members",
        ):
            raise CompiledError("COMPILED_HEADER")
        if value["format"] != FORMAT:
            raise CompiledError("COMPILED_FORMAT")
        if type(value["producer"]) is not str or not value["producer"]:
            raise CompiledError("COMPILED_PRODUCER")
        members = value["members"]
        if type(members) is not list or len(members) != len(MEMBERS):
            raise CompiledError("COMPILED_MEMBERS")
        decoded, records = [], 0
        for expected, member in zip(MEMBERS, members, strict=True):
            if (
                type(member) is not list
                or len(member) != 2
                or member[0] != expected
                or type(member[1]) is not list
            ):
                raise CompiledError("COMPILED_MEMBERS")
            group = []
            for record in member[1]:
                records += 1
                if records > MAX_RECORDS:
                    raise CompiledError("COMPILED_RECORD_LIMIT")
                if type(record) is not list or len(record) != 3:
                    raise CompiledError("COMPILED_RECORD")
                address = address_read(record[:2])
                fields = _read(record[2])
                if type(fields) is not tuple or len(fields) != len(
                    FIELDS[address.kind]
                ):
                    raise CompiledError("COMPILED_FIELDS")
                group.append(Record(address, fields))
            decoded.append((expected, tuple(group)))
        compatibility = _read(value["compatibility"])
        if type(compatibility) is not tuple:
            raise CompiledError("COMPILED_COMPATIBILITY")
        result = Description(
            compatibility,
            value["producer"],
            address_read(value["query"]),
            tuple(decoded),
        )
        if encode(result) != raw:
            raise CompiledError("COMPILED_CANONICAL")
        return result
    except CompiledError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError):
        raise CompiledError("COMPILED_JSON") from None


def content_pin(raw: bytes) -> str:
    _bounded(raw)
    return hashlib.sha256(
        CONTENT_DOMAIN + len(raw).to_bytes(8, "big") + raw
    ).hexdigest()


def selected_relations(records, entry):
    """Current execution closure; retained request roots are checked separately."""
    incoming = {}
    for record in records.values():
        if record.address.kind == "use":
            incoming.setdefault(record.get("consumer"), []).append(
                record.get("producer")
            )
    reached, pending = set(), [entry.get("terminal")]
    while pending:
        address = pending.pop()
        if address in reached:
            continue
        reached.add(address)
        pending.extend(incoming.get(address, ()))
    return frozenset(reached)


def selected_records(records, entry):
    """Follow the actual selected relation/scalar inputs, never a supplied set."""
    reached = set()
    pending = list(selected_relations(records, entry))
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(value)
        elif type(value) is Address and value not in reached:
            reached.add(value)
            pending.extend(records[value].values)
    return frozenset(reached)
