"""Bounded private result descriptions; stdlib only, never runtime authority."""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
import math
from pathlib import PurePosixPath
import re
from typing import Any

__all__: tuple[str, ...] = ()
FORMAT = "pietto.result-contract.v1"
NULLABILITY = {"non_null", "nullable", "unknown"}
BUILTINS = {
    "Int",
    "Float",
    "Bool",
    "Text",
    "Decimal",
    "Date",
    "Timestamp",
    "UUID",
    "Bytes",
    "Any",
    "Json",
}


class ContractDocumentError(ValueError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


def require(condition, category="DOCUMENT"):
    if not condition:
        raise ContractDocumentError(category)


@dataclass(frozen=True, slots=True)
class DocumentLimits:
    bytes: int = 4 * 1024 * 1024
    depth: int = 48
    values: int = 65536
    records: int = 8192
    references: int = 16384
    text: int = 131072
    total_text: int = 2 * 1024 * 1024
    fields: int = 1024


def limits_for(limits):
    require(type(limits) is DocumentLimits, "LIMIT")
    hard = DocumentLimits()
    values = {}
    for f in fields(hard):
        value = getattr(limits, f.name)
        require(type(value) is int and value >= 0, "LIMIT")
        values[f.name] = min(value, getattr(hard, f.name))
    return DocumentLimits(**values)


class Budget:
    """Shared low-level resource accounting, with no semantic projection."""

    def __init__(self, limits=DocumentLimits()):
        self.limits = limits_for(limits)
        self.values = self.records = self.text = self.references = 0

    def value(self, value, depth=0):
        self.values += 1
        require(
            self.values <= self.limits.values and depth <= self.limits.depth, "LIMIT"
        )
        if type(value) is str:
            require(len(value) <= self.limits.text, "LIMIT")
            try:
                size = len(value.encode("utf-8"))
            except UnicodeError as exc:
                raise ContractDocumentError("TEXT") from exc
            self.text += size
            require(
                size <= self.limits.text and self.text <= self.limits.total_text,
                "LIMIT",
            )
        elif type(value) is dict:
            self.records += 1
            require(self.records <= self.limits.records, "LIMIT")
        elif type(value) is int:
            require(0 <= value <= 2**31 - 1, "NUMBER")
        else:
            require(value is None or type(value) in (bool, list), "DOCUMENT")

    def reference(self):
        self.references += 1
        require(self.references <= self.limits.references, "LIMIT")


def bounded(value, limits):
    budget = Budget(limits)
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        budget.value(current, depth)
        if type(current) is dict:
            if set(current) == {"kind", "position"}:
                budget.reference()
            for key, item in current.items():
                require(type(key) is str)
                stack.extend(((key, depth + 1), (item, depth + 1)))
        elif type(current) is list:
            stack.extend((item, depth + 1) for item in current)
    return budget


def record(value, names):
    require(type(value) is dict and set(value) == set(names.split()))


def index(value):
    require(type(value) is int and 0 <= value <= 2**31 - 1, "INDEX")


def text(value, *, empty=False):
    require(type(value) is str and (empty or bool(value)), "TEXT")


def path(value):
    text(value)
    p = PurePosixPath(value)
    require(
        not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in value
        and p.as_posix() == value,
        "PATH",
    )


def location(value):
    if value is None:
        return
    record(value, "path line column end_line end_column")
    if value["path"] is not None:
        path(value["path"])
    for key in ("line", "column", "end_line", "end_column"):
        if value[key] is not None:
            index(value[key])
            require(value[key] >= 1)
    require(value["line"] is not None and value["column"] is not None)


def nominal(value):
    record(value, "module namespace kind name")
    path(value["module"])
    text(value["name"])
    require(value["namespace"] in ("type", "relation", "callable"))
    require(
        value["kind"]
        in {"type", "enum", "shape", "source", "table", "query", "constraint", "derive"}
    )
    require(
        (value["namespace"] == "type") == (value["kind"] in {"type", "enum", "shape"})
    )


def owner(value):
    record(value, "identity module_position declaration_position")
    nominal(value["identity"])
    index(value["module_position"])
    index(value["declaration_position"])


def coordinate(value, kinds):
    record(value, "kind position")
    require(value["kind"] in kinds, "REFERENCE")
    index(value["position"])


def expression(value):
    require(type(value) is dict)
    tag = value.get("tag")
    names = {
        "literal": "tag kind value location",
        "name": "tag name location",
        "dotted": "tag parts location",
        "call": "tag callee arguments location",
        "unary": "tag operator operand location",
        "binary": "tag operator left right location",
        "comparison": "tag operator left right location",
        "between": "tag value lower upper location",
        "is_null": "tag value negated location",
    }
    require(type(tag) is str and tag in names, "TAG")
    record(value, names[tag])
    location(value["location"])
    if tag == "literal":
        kind, item = value["kind"], value["value"]
        require(kind in {"Int", "Float", "Bool", "Text", "Null"}, "TAG")
        if kind == "Int":
            require(
                type(item) is str
                and re.fullmatch(r"0|-?[1-9][0-9]*", item) is not None,
                "NUMBER",
            )
        elif kind == "Float":
            try:
                number = float.fromhex(item) if type(item) is str else float("nan")
            except (ValueError, OverflowError) as exc:
                raise ContractDocumentError("NUMBER") from exc
            require(math.isfinite(number) and number.hex() == item, "NUMBER")
        elif kind == "Bool":
            require(type(item) is bool, "NUMBER")
        elif kind == "Null":
            require(item is None)
        else:
            text(item, empty=True)
    elif tag == "name":
        text(value["name"])
    elif tag == "dotted":
        require(type(value["parts"]) is list and len(value["parts"]) >= 2)
        for item in value["parts"]:
            text(item)
    elif tag == "call":
        expression(value["callee"])
        require(value["callee"]["tag"] in {"name", "dotted"})
        require(type(value["arguments"]) is list)
        for item in value["arguments"]:
            expression(item)
    else:
        children = {
            "unary": ("operand",),
            "binary": ("left", "right"),
            "comparison": ("left", "right"),
            "between": ("value", "lower", "upper"),
            "is_null": ("value",),
        }[tag]
        for key in children:
            expression(value[key])
        if tag == "is_null":
            require(type(value["negated"]) is bool)
        elif tag != "between":
            text(value["operator"])


def declared(value):
    if value is None:
        return
    record(value, "name arguments nullability location")
    text(value["name"])
    require(value["nullability"] in {"implicit", "nullable", "not_null"})
    location(value["location"])
    require(type(value["arguments"]) is list)
    for argument in value["arguments"]:
        record(argument, "name value")
        if argument["name"] is not None:
            text(argument["name"])
        expression(argument["value"])


def symbol(value):
    if value is None:
        return
    record(value, "identity location")
    nominal(value["identity"])
    location(value["location"])


def output(value):
    record(value, "kind position producer owner field_count")
    require(value["kind"] == "relation_output")
    for key in ("position", "producer", "field_count"):
        index(value[key])
    owner(value["owner"])


def origin(value):
    """A retained nominal access route, without loading its modules."""
    record(value, "module namespace kind local_name target local import hops")
    path(value["module"])
    text(value["local_name"])
    owner(value["target"])
    require(value["namespace"] == value["target"]["identity"]["namespace"])
    require(value["kind"] == value["target"]["identity"]["kind"])
    require(type(value["hops"]) is list)
    if value["local"] is not None:
        owner(value["local"])
        require(
            value["local"] == value["target"]
            and value["import"] is None
            and not value["hops"]
        )
        require(value["module"] == value["target"]["identity"]["module"])
        require(value["local_name"] == value["target"]["identity"]["name"])
    else:
        import_site(value["import"])
        require(bool(value["hops"]))
        require(value["hops"][0]["import"] == value["import"])
    for hop in value["hops"]:
        record(hop, "import facade origin target")
        import_site(hop["import"])
        record(hop["facade"], "module namespace kind name statement item")
        facade = hop["facade"]
        path(facade["module"])
        text(facade["name"])
        index(facade["statement"])
        index(facade["item"])
        nominal(hop["target"])
        require(hop["target"] == value["target"]["identity"])
        require(
            hop["import"]["target_module"] == facade["module"]
            and hop["import"]["exported_name"] == facade["name"]
        )
        text(hop["origin"])
    for first, second in zip(value["hops"], value["hops"][1:]):
        require(first["facade"]["module"] == second["import"]["module"])


def import_site(value):
    record(
        value,
        "module namespace kind local_name target_module exported_name statement item",
    )
    for key in ("module", "target_module"):
        path(value[key])
    for key in ("local_name", "exported_name"):
        text(value[key])
    for key in ("statement", "item"):
        index(value[key])
    require(value["namespace"] in {"type", "relation", "callable"})
    require(
        value["kind"]
        in {"type", "enum", "shape", "source", "table", "query", "constraint", "derive"}
    )


def reference(value):
    record(value, "owner role position")
    owner(value["owner"])
    require(value["role"] in {"type_alias_base", "shape_field_type"}, "REFERENCE")
    index(value["position"])
    require(
        value["owner"]["identity"]["kind"]
        == ("type" if value["role"] == "type_alias_base" else "shape"),
        "REFERENCE",
    )


def provenance_paths(value):
    record(value, "reference paths")
    reference(value["reference"])
    require(type(value["paths"]) is list and bool(value["paths"]))
    require(
        len({json.dumps(v, sort_keys=True) for v in value["paths"]})
        == len(value["paths"]),
        "REFERENCE",
    )
    for path in value["paths"]:
        record(path, "hops builtin terminal_reference terminal_target")
        require(type(path["hops"]) is list)
        require(
            (path["builtin"] is None) != (path["terminal_target"] is None), "REFERENCE"
        )
        if path["builtin"] is not None:
            require(path["builtin"] in BUILTINS)
            reference(path["terminal_reference"])
        else:
            owner(path["terminal_target"])
            require(
                path["terminal_reference"] is None and bool(path["hops"]), "REFERENCE"
            )
        previous = None
        targets = []
        for hop in path["hops"]:
            record(hop, "reference target origin")
            reference(hop["reference"])
            owner(hop["target"])
            origin(hop["origin"])
            require(hop["target"] == hop["origin"]["target"], "REFERENCE")
            require(
                hop["origin"]["module"]
                == hop["reference"]["owner"]["identity"]["module"],
                "REFERENCE",
            )
            require(
                hop["reference"] == value["reference"]
                if previous is None
                else hop["reference"]["owner"] == previous,
                "REFERENCE",
            )
            previous = hop["target"]
            targets.append(json.dumps(previous, sort_keys=True))
        require(len(set(targets)) == len(targets), "REFERENCE")
        if previous is None:
            require(path["terminal_reference"] == value["reference"], "REFERENCE")
        elif path["builtin"] is None:
            require(path["terminal_target"] == previous, "REFERENCE")
        else:
            require(path["terminal_reference"]["owner"] == previous, "REFERENCE")


def order_value_type(value, types, reached, budget):
    record(value, "kind type_kind name nullability declaration")
    require(
        value["kind"] == "known"
        and value["type_kind"] in {"builtin", "type_alias", "enum"}
    )
    text(value["name"])
    require(value["nullability"] in NULLABILITY)
    ref = value["declaration"]
    if ref is not None:
        record(ref, "kind index")
        require(ref["kind"] == "type_declaration", "REFERENCE")
        index(ref["index"])
        require(ref["index"] < len(types), "REFERENCE")
        budget.reference()
        if ref["index"] not in reached:
            reached.append(ref["index"])
    elif value["type_kind"] != "builtin":
        raise ContractDocumentError("REFERENCE")


def prepared_order(value, types, reached, budget):
    record(value, "order item expression value value_type uses")
    coordinate(value["order"], {"relation_order"})
    coordinate(value["item"], {"order_item"})
    coordinate(value["expression"], {"order_expression"})
    coordinate(value["value"], {"order_expression", "hidden_order_requirement"})
    require(type(value["uses"]) is list)
    for position, use in enumerate(value["uses"]):
        record(use, "position expression value_type scope ports requirement")
        require(type(use["position"]) is int and use["position"] == position, "INDEX")
        expression(use["expression"])
        order_value_type(use["value_type"], types, reached, budget)
        coordinate(use["scope"], {"definition", "result_boundary"})
        require(type(use["ports"]) is list)
        for port in use["ports"]:
            coordinate(
                port,
                {
                    "source_port",
                    "input_port",
                    "export",
                    "stage_port",
                    "join_port",
                    "result_port",
                    "set_column",
                    "group_key",
                    "aggregate",
                    "window",
                    "let_value",
                    "expression",
                    "aggregate_projection",
                    "window_projection",
                },
            )
        if use["requirement"] is not None:
            coordinate(use["requirement"], {"hidden_order_requirement"})
        require(bool(use["ports"]) != (use["requirement"] is not None), "REFERENCE")
    order_value_type(value["value_type"], types, reached, budget)


def _validate_document(doc, *, limits=DocumentLimits()):
    budget = bounded(doc, limits)
    record(doc, "format owner output field_count fields types multiplicity ordering")
    require(doc["format"] == FORMAT, "VERSION")
    owner(doc["owner"])
    require(doc["owner"]["identity"]["kind"] in {"table", "query"})
    output(doc["output"])
    require(doc["output"]["owner"] == doc["owner"])
    index(doc["field_count"])
    require(doc["field_count"] <= budget.limits.fields, "LIMIT")
    require(
        type(doc["fields"]) is list
        and len(doc["fields"]) == doc["field_count"] == doc["output"]["field_count"]
    )
    require(doc["multiplicity"] == "bag")
    require(type(doc["types"]) is list)
    types = doc["types"]
    for position, typ in enumerate(types):
        record(typ, "id owner base ensures members")
        require(type(typ["id"]) is int and typ["id"] == position, "INDEX")
        owner(typ["owner"])
        kind = typ["owner"]["identity"]["kind"]
        require(kind in {"type", "enum"})
        declared(typ["base"])
        require(type(typ["ensures"]) is list and type(typ["members"]) is list)
        require((kind == "type") == (typ["base"] is not None))
        require(not typ["members"] if kind == "type" else not typ["ensures"])
        for item in typ["ensures"]:
            expression(item)
        for item in typ["members"]:
            text(item)
    require(
        len({json.dumps(t["owner"], sort_keys=True) for t in types}) == len(types),
        "REFERENCE",
    )
    reached = []
    port_keys = set()
    for position, leaf in enumerate(doc["fields"]):
        record(
            leaf,
            "ordinal label identity port output position declared canonical nullability declared_nullability role provenance type_resolution",
        )
        require(type(leaf["ordinal"]) is int and leaf["ordinal"] == position, "INDEX")
        text(leaf["label"])
        record(leaf["identity"], "owner kind position name")
        ident = leaf["identity"]
        owner(ident["owner"])
        require(
            ident["owner"] == doc["owner"]
            and ident["kind"] == "relation_output"
            and type(ident["position"]) is int
            and ident["position"] == position
            and ident["name"] == leaf["label"],
            "REFERENCE",
        )
        record(leaf["port"], "coordinate owner producer")
        coordinate(leaf["port"]["coordinate"], {"export"})
        coordinate(leaf["port"]["owner"], {"definition"})
        if leaf["port"]["producer"] is not None:
            coordinate(
                leaf["port"]["producer"], {"source_port", "input_port", "export"}
            )
        port_key = leaf["port"]["coordinate"]["position"]
        require(port_key not in port_keys, "REFERENCE")
        port_keys.add(port_key)
        output(leaf["output"])
        index(leaf["position"])
        require(
            leaf["output"] == doc["output"] and leaf["position"] == position,
            "REFERENCE",
        )
        require(leaf["port"]["owner"] == doc["fields"][0]["port"]["owner"], "REFERENCE")
        declared(leaf["declared"])
        record(leaf["canonical"], "kind name symbol")
        canonical = leaf["canonical"]
        require(canonical["kind"] in {"builtin", "type", "enum"}, "TAG")
        text(canonical["name"])
        symbol(canonical["symbol"])
        require((canonical["kind"] == "builtin") == (canonical["symbol"] is None))
        if canonical["kind"] == "builtin":
            require(canonical["name"] in BUILTINS, "TAG")
        require(
            leaf["nullability"] in NULLABILITY
            and leaf["declared_nullability"] in NULLABILITY
        )
        require(
            leaf["role"]
            in {"ordinary_row_value", "group_key", "aggregate_result", "window_result"}
        )
        provenance = leaf["provenance"]
        if provenance is not None:
            record(provenance, "kind symbol location")
            require(
                provenance["kind"]
                in {
                    "source_field",
                    "direct_projection",
                    "derived_expression",
                    "let_derived",
                    "expression",
                    "aggregate",
                    "unknown",
                }
            )
            symbol(provenance["symbol"])
            location(provenance["location"])
        resolution = leaf["type_resolution"]
        if resolution is not None:
            record(
                resolution,
                "direct_kind canonical_kind canonical_name aliases target origins",
            )
            require(leaf["declared"] is not None)
            require(
                resolution["canonical_kind"] == canonical["kind"]
                and resolution["canonical_name"] == canonical["name"]
            )
            require(resolution["direct_kind"] in {"builtin", "type", "enum"})
            require(
                type(resolution["aliases"]) is list
                and type(resolution["origins"]) is list
            )
            local = []
            for ref in resolution["aliases"] + (
                [] if resolution["target"] is None else [resolution["target"]]
            ):
                record(ref, "kind index")
                require(ref["kind"] == "type_declaration", "REFERENCE")
                index(ref["index"])
                require(ref["index"] < len(types), "REFERENCE")
                budget.reference()
                local.append(ref["index"])
                if ref["index"] not in reached:
                    reached.append(ref["index"])
            require(len(local) == len(set(local)), "REFERENCE")
            require(
                all(
                    types[r["index"]]["owner"]["identity"]["kind"] == "type"
                    for r in resolution["aliases"]
                ),
                "REFERENCE",
            )
            require(
                (resolution["direct_kind"] == "type") == bool(resolution["aliases"])
            )
            require(
                (resolution["canonical_kind"] == "enum")
                == (resolution["target"] is not None)
            )
            if resolution["target"] is not None:
                target = types[resolution["target"]["index"]]
                require(
                    target["owner"]["identity"]["kind"] == "enum"
                    and target["owner"]["identity"]["name"]
                    == resolution["canonical_name"],
                    "REFERENCE",
                )
            require(bool(resolution["origins"]), "REFERENCE")
            for item in resolution["origins"]:
                provenance_paths(item)
    ordering = doc["ordering"]
    if ordering is not None:
        record(ordering, "kind owner keys")
        require(ordering["kind"] in {"provided", "final"})
        owner(ordering["owner"])
        require(ordering["owner"] == doc["owner"])
        require(type(ordering["keys"]) is list and bool(ordering["keys"]))
        for position, key in enumerate(ordering["keys"]):
            record(
                key, "position expression authored_direction direction nulls prepared"
            )
            require(
                type(key["position"]) is int and key["position"] == position, "INDEX"
            )
            expression(key["expression"])
            require(key["authored_direction"] in {None, "asc", "desc"})
            require(key["direction"] == (key["authored_direction"] or "asc"))
            require(key["nulls"] == "unspecified")
            prepared_order(key["prepared"], types, reached, budget)
            require(
                key["prepared"]["order"] == ordering["keys"][0]["prepared"]["order"],
                "REFERENCE",
            )
        require(
            len({key["prepared"]["item"]["position"] for key in ordering["keys"]})
            == len(ordering["keys"]),
            "REFERENCE",
        )
    require(reached == list(range(len(types))), "REFERENCE")
    return doc


def validate_document(doc, *, limits=DocumentLimits()):
    try:
        return _validate_document(doc, limits=limits)
    except (
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        RecursionError,
        OverflowError,
    ) as exc:
        raise ContractDocumentError("DOCUMENT") from exc


def _canonical(doc):
    return (
        json.dumps(
            doc,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def encode_document(doc, *, limits=DocumentLimits()):
    validate_document(doc, limits=limits)
    result = _canonical(doc)
    require(len(result) <= limits_for(limits).bytes, "LIMIT")
    return result


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _no_number(value):
    raise ContractDocumentError("NUMBER")


def _integer(value):
    require(
        len(value) <= 10 and re.fullmatch(r"0|[1-9][0-9]*", value) is not None, "NUMBER"
    )
    number = int(value)
    index(number)
    return number


def _read(data, limits):
    require(type(data) is bytes, "INPUT")
    limit = limits_for(limits)
    require(len(data) <= limit.bytes, "LIMIT")
    try:
        source = data.decode("utf-8")
    except UnicodeError as exc:
        raise ContractDocumentError("UTF8") from exc
    # Only count structural delimiters outside strings; JSON syntax stays stdlib-owned.
    depth = values = records = 0
    quoted = escaped = scalar = False
    for char in source:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            scalar = False
            values += 1
        elif char in "[{":
            depth += 1
            values += 1
            records += char == "{"
            scalar = False
        elif char in "]}":
            depth -= 1
            scalar = False
        elif char in ",: \t\r\n":
            scalar = False
        elif not scalar:
            values += 1
            scalar = True
        require(
            depth <= limit.depth
            and values <= limit.values
            and records <= limit.records,
            "LIMIT",
        )
    try:
        doc = json.loads(
            source,
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_no_number,
            parse_constant=_no_number,
        )
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, ContractDocumentError):
            raise
        raise ContractDocumentError("JSON") from exc
    validate_document(doc, limits=limit)
    require(_canonical(doc) == data, "CANONICAL")
    return doc


@dataclass(frozen=True, slots=True)
class ContractView:
    canonical_bytes: bytes

    @property
    def document(self) -> dict[str, Any]:
        return _read(self.canonical_bytes, DocumentLimits())

    @property
    def fields(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.document["fields"])


def decode_contract(data, *, limits=DocumentLimits()):
    _read(data, limits)
    return ContractView(data)


def reencode_contract(view, *, limits=DocumentLimits()):
    require(type(view) is ContractView, "INPUT")
    return encode_document(_read(view.canonical_bytes, limits), limits=limits)
