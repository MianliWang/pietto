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
# A root with header parameters (an unbound template) is tagged v2; S11 owns
# its transport, so decode refuses the tag until then.
PARAMETERIZED_FORMAT = "pietto.compiled-execution.v2"
# schema, semantic, occurrence, profile; 2/2: declaration records carry ``let``;
# 3/3: typed ``values`` relation records (Phase70 S06; one bump per batch);
# 4/4: expression_block_use records (Phase70 S08).
VERSIONS = (5, 1, 5, 1)  # 5/5: capture records (Phase70 batch 4, S10)
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
    # ``let`` is null for a module declaration and the source position of one
    # relation let inside the declaration at ``position`` otherwise.
    "declaration": (
        "module",
        "module_position",
        "position",
        "namespace",
        "kind",
        "label",
        "let",
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
    # ExpressionBlockUseV1: one expression occurrence of ``consumer`` reads the
    # whole ``producer`` through ``operation``; never a ``use`` and never an
    # input slot. ``column`` is the read output ordinal (null for an existence
    # read). Records follow the statement's block use order, and record ``n``
    # renders the relation alias ``e<n>``.
    "expression_block_use": ("operation", "consumer", "producer", "column"),
    # CaptureV1: capture line ``ordinal`` of the let an expression block use
    # ``read`` executes inline reads the current row of that read's consumer;
    # ``ports`` are the consumer input's producer ports of the captured fields.
    # A captured field is a ``read`` (role "capture") of one of those ports
    # through the consumer's own use; aliases and columns are derived.
    "capture_use": ("read", "ordinal", "ports"),
    "port": ("owner", "ordinal", "label", "source", "logical"),
    "literal": ("tag", "value", "site"),
    "null_literal": ("site",),
    "read": ("port", "use", "role"),
    "operation": ("operator", "operands", "logical", "site"),
    "site": ("owner", "role", "ordinal", "ancestry", "disposition", "reason"),
    "slot": ("site", "literal", "tag"),
    # `slot` names the occurrence owner: a bind-safe slot or a parameter read.
    "native_use": ("slot", "ordinal", "index", "physical"),
    "parameter": ("declaration", "ordinal", "label", "tag", "nullable"),
    "parameter_read": ("parameter",),
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
    # A zero-input typed VALUES relation: ``fields`` describe its declared
    # columns (``field.source`` is this record), ``rows`` hold the fixed cells
    # inline as scalars or null, in source order.
    "values": ("owner", "fields", "rows", "outputs", "layout"),
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
    parameterized = any(
        record.address.kind == "parameter" for record in description.records
    )
    document = {
        "format": PARAMETERIZED_FORMAT if parameterized else FORMAT,
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


def declaration_values(owner) -> tuple:
    """The exact ``declaration`` record values of one live relation owner."""

    return (
        owner.identity.module_path,
        owner.module_position,
        owner.declaration_position,
        owner.identity.namespace.value,
        owner.identity.declaration_kind.value,
        owner.identity.declared_name,
        owner.let_position,
    )


_SCALAR_CONTAINERS = frozenset(
    {"operation", "aggregate_value", "window_value", "join_value", "set_value"}
)


def executed_operations(records, relation):
    """Operations reachable from one relation's own values, never across uses."""
    found, seen = set(), set()
    pending = list(records[relation].values)
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(value)
            continue
        if (
            type(value) is not Address
            or value in seen
            or value.kind not in _SCALAR_CONTAINERS
        ):
            continue
        seen.add(value)
        if value.kind == "operation":
            found.add(value)
        pending.extend(records[value].values)
    return found


# Operators of an expression block use. A membership read's one operand is
# its left value; the others have no operand of their own.
BLOCK_READ_OPERATORS = (
    ("exists", "exists"),
    ("scalar", "scalar"),
    ("relation_membership", "in"),
    ("relation_membership", "not_in"),
)


def scalar_read_port(records, operation):
    """The producer output a scalar read operation reads through its block use.

    It is the producer's port whose ordinal is the block use's ``column``; an
    existence read, a missing use or a missing port has none.
    """
    uses = tuple(
        r
        for r in records.values()
        if r.address.kind == "expression_block_use" and r.get("operation") == operation
    )
    if len(uses) != 1 or records[operation].get("operator") != ("scalar", "scalar"):
        return None
    producer, column = uses[0].get("producer"), uses[0].get("column")
    ports = tuple(
        r.address
        for r in records.values()
        if r.address.kind == "port"
        and r.get("owner") == producer
        and r.get("ordinal") == column
    )
    return ports[0] if len(ports) == 1 and type(column) is int else None


def unit_position(record):
    """A unit's layout position; an inline let's units have none."""
    layout = record.get("layout")
    if type(layout) is not tuple or len(layout) != 5:
        raise CompiledError("COMPILED_LAYOUT")
    return layout[-1]


def inline_units(records, block_use):
    """The inline let units one expression block use renders, outermost first."""
    chain, current = [], records[block_use].get("producer")
    while "layout" in FIELDS[current.kind] and unit_position(records[current]) is None:
        producers = tuple(
            r.get("producer")
            for r in records.values()
            if r.address.kind == "use" and r.get("consumer") == current
        )
        if current in chain or len(producers) != 1:
            raise CompiledError("COMPILED_INLINE_CHAIN")
        chain.append(current)
        current = producers[0]
    return tuple(chain)


def row_bindings(records, use):
    """The row bindings of one use's ports, each in port order.

    A JOIN producer's output port belongs to the JOIN input it reads, through
    the earlier JOINs of the same declaration; a row or window stage of the
    reading declaration carries the port it reads into that port's binding
    (the first port carrying each field) and computes a value of no binding;
    any other producer's row is one binding.
    """
    owner = records[records[use].get("consumer")].get("owner")
    groups: dict[Any, dict[Address, Address]] = {}
    for port in records[use].get("ports"):
        binding, chain = _carried(records, owner, port)
        if chain:
            groups.setdefault(binding, {}).setdefault(chain[-1].address, port)
    return tuple(tuple(ports.values()) for ports in groups.values())


def _carried(records, owner, port):
    """One port's row binding and the ports that carry it from that binding's
    input, the port first; no ports for a value a stage computes."""
    binding, chain, seen = None, [records[port]], set()
    while chain[-1].address not in seen:
        current = chain[-1]
        seen.add(current.address)
        unit = records[current.get("owner")]
        if unit.address.kind in ("row", "window") and unit.get("owner") == owner:
            if current.get("source").kind != "read":
                return None, []
            chain.append(records[records[current.get("source")].get("port")])
            continue
        if unit.address.kind != "join":
            break
        value = records[current.get("source")]
        if value.address.kind != "join_value":
            raise CompiledError("COMPILED_CAPTURE_BINDING")
        read = records[value.get("input")]
        binding = read.get("use")
        chain.append(records[read.get("port")])
        producer = records[binding].get("producer")
        if producer.kind != "join" or records[producer].get("owner") != unit.get(
            "owner"
        ):
            break
    return binding, chain


def captured_logical(records, read):
    """A captured field read's type: its port's, nullable when any port that
    carries the field from its binding's input is. An outer JOIN may
    null-extend the binding; neither a JOIN ON nor a WHERE narrows it."""
    use = records[records[read].get("use")]
    owner = records[use.get("consumer")].get("owner")
    _, chain = _carried(records, owner, records[read].get("port"))
    tag, nullability = records[records[read].get("port")].get("logical")
    if any(p.get("logical")[1] == "nullable" for p in chain):
        nullability = "nullable"
    return tag, nullability


def captured_reads(records):
    """Each captured field read with the capturing read and record it names.

    A captured read lies in the inline units of one capturing read; its record
    is the one of that read whose ports, one row binding, hold its port (None
    when no single record does). A read found twice is listed twice.
    """
    described: dict[Address, list[Record]] = {}
    for record in records.values():
        if record.address.kind == "capture_use":
            described.setdefault(record.get("read"), []).append(record)
    found: dict[Address, list[tuple[Address, Any]]] = {}
    for block, captures in described.items():
        for unit in inline_units(records, block):
            seen, pending = set(), list(records[unit].values)
            while pending:
                value = pending.pop()
                if type(value) is tuple:
                    pending.extend(value)
                    continue
                if type(value) is not Address or value in seen:
                    continue
                seen.add(value)
                if value.kind in _SCALAR_CONTAINERS:
                    pending.extend(records[value].values)
                elif value.kind == "read" and records[value].get("role") == "capture":
                    port = records[value].get("port")
                    owners = tuple(
                        c.address for c in captures if port in c.get("ports")
                    )
                    found.setdefault(value, []).append(
                        (block, owners[0] if len(owners) == 1 else None)
                    )
    return {read: tuple(pairs) for read, pairs in found.items()}


def selected_relations(records, entry):
    """Current execution closure; retained request roots are checked separately.

    A relation reaches its ``use`` producers and the producer of every
    expression block use whose operation it actually executes.
    """
    incoming, reads = {}, {}
    for record in records.values():
        if record.address.kind == "use":
            incoming.setdefault(record.get("consumer"), []).append(
                record.get("producer")
            )
        elif record.address.kind == "expression_block_use":
            reads.setdefault(record.get("consumer"), []).append(record)
    reached, pending = set(), [entry.get("terminal")]
    while pending:
        address = pending.pop()
        if address in reached:
            continue
        reached.add(address)
        pending.extend(incoming.get(address, ()))
        local = reads.get(address)
        if local:
            executed = executed_operations(records, address)
            pending.extend(
                read.get("producer")
                for read in local
                if read.get("operation") in executed
            )
    return frozenset(reached)


def selected_records(records, entry):
    """Follow the actual selected relation/scalar inputs, never a supplied set.

    A scalar read has no operand; it reaches the producer port its block use
    names, which no record value of a source scanned by no stage references.
    """
    reached = set()
    pending = list(selected_relations(records, entry))
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(value)
        elif type(value) is Address and value not in reached:
            reached.add(value)
            pending.extend(records[value].values)
            if value.kind == "operation" and records[value].get("operator") == (
                "scalar",
                "scalar",
            ):
                pending.append(scalar_read_port(records, value))
    return frozenset(reached)
