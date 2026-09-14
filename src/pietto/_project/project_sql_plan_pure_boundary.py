"""Bounded JSON decoding and document consistency; never executable plan import."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import math
import re
from types import MappingProxyType
from collections.abc import Mapping
from collections import Counter
from typing import Any, cast

from pietto._project import project_sql_plan_portable_schema as schema

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


@dataclass(frozen=True, slots=True)
class Outcome:
    status: Status
    document: schema.Document | None = None
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None


class _Reject(Exception):
    def __init__(
        self, status: Status, record: int | None = None, field: int | None = None
    ):
        self.status, self.record, self.field = status, record, field


def _require(condition, status=Status.INVALID_VALUE):
    if not condition:
        raise _Reject(status)


def _text(value):
    _require(type(value) is str)
    _require(len(value) <= schema.MAX_TEXT, Status.RESOURCE_LIMIT)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise _Reject(Status.INVALID_UTF8) from None


def _integer(text):
    _require(type(text) is str)
    _require(len(text.removeprefix("-")) <= schema.MAX_DIGITS, Status.RESOURCE_LIMIT)
    _require(text != "-0" and re.fullmatch(r"-?(0|[1-9][0-9]*)", text) is not None)
    return int(text)


def _float(text):
    _require(type(text) is str and len(text) <= 64)
    try:
        value = float.fromhex(text)
    except (OverflowError, ValueError):
        raise _Reject(Status.INVALID_VALUE) from None
    _require(math.isfinite(value) and value.hex() == text)
    return value


def _ref(ref):
    _require(type(ref) is schema.Ref, Status.INVALID_REF)
    _require(type(ref.domain) is str and bool(ref.domain), Status.INVALID_REF)
    _require(
        type(ref.position) is int and 0 <= ref.position < schema.MAX_RECORDS,
        Status.INVALID_REF,
    )


def _validate_value(
    value: schema.Value,
    shape: schema.Shape,
    references: list[schema.Ref],
    active: set[int],
    depth=0,
):
    _require(depth <= schema.MAX_DEPTH, Status.RESOURCE_LIMIT)
    _require(type(value) is schema.Value and type(value.tag) is schema.Tag)
    _require(value.tag in shape.tags)
    _require(id(value) not in active, Status.INVALID_VALUE)
    active.add(id(value))
    data, tag = value.data, value.tag
    if tag is schema.Tag.ABSENT:
        _require(data is None)
    elif tag is schema.Tag.BOOLEAN:
        _require(type(data) is bool)
    elif tag in (schema.Tag.TEXT, schema.Tag.ENUM):
        _text(data)
        if tag is schema.Tag.ENUM:
            _require(data in shape.enums)
    elif tag is schema.Tag.INTEGER:
        _integer(data)
    elif tag is schema.Tag.FLOAT:
        _float(data)
    elif tag is schema.Tag.REF:
        _ref(data)
        assert isinstance(data, schema.Ref)
        _require(data.domain in shape.domains, Status.INVALID_REF)
        references.append(data)
        _require(len(references) <= schema.MAX_EDGES, Status.RESOURCE_LIMIT)
    else:
        _require(type(data) is tuple)
        assert isinstance(data, tuple)
        _require(len(data) <= schema.MAX_EDGES, Status.RESOURCE_LIMIT)
        _require(shape.items is not None or not data)
        if tag is schema.Tag.SEQUENCE:
            for child in data:
                assert shape.items is not None
                _validate_value(child, shape.items, references, active, depth + 1)
        else:
            _require(tag is schema.Tag.MAPPING and shape.keys is not None)
            keys = set()
            for pair in data:
                _require(
                    type(pair) is schema.Value
                    and pair.tag is schema.Tag.SEQUENCE
                    and type(pair.data) is tuple
                    and len(pair.data) == 2
                )
                assert (
                    isinstance(pair.data, tuple)
                    and shape.keys is not None
                    and shape.items is not None
                )
                key, child = pair.data
                _validate_value(key, shape.keys, references, active, depth + 1)
                _validate_value(child, shape.items, references, active, depth + 1)
                _require(key not in keys)
                keys.add(key)
    active.remove(id(value))


def _wire_value(value):
    data = value.data
    if value.tag is schema.Tag.REF:
        data = [data.domain, data.position]
    elif value.tag in (schema.Tag.SEQUENCE, schema.Tag.MAPPING):
        data = [_wire_value(child) for child in data]
    return [value.tag.value, data]


def _wire(document):
    return {
        "format": document.format,
        "records": [
            {
                "kind": record.kind,
                "ref": [record.ref.domain, record.ref.position],
                "fields": [
                    [field.name, _wire_value(field.value)] for field in record.fields
                ],
            }
            for record in document.records
        ],
    }


def _canonical(document):
    value = (
        json.dumps(
            _wire(document), ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")
    _require(len(value) <= schema.MAX_BYTES, Status.RESOURCE_LIMIT)
    return value


def _check(document):
    _require(type(document) is schema.Document, Status.INVALID_DOCUMENT)
    _require(
        type(document.format) is str and document.format == schema.FORMAT,
        Status.UNKNOWN_FORMAT,
    )
    _require(
        type(document.records) is tuple and bool(document.records),
        Status.INVALID_DOCUMENT,
    )
    _require(len(document.records) <= schema.MAX_RECORDS, Status.RESOURCE_LIMIT)
    declared = {}
    positions = {}
    references = []
    value_count = text_bytes = 0
    for position, record in enumerate(document.records):
        _require(type(record) is schema.Record, Status.INVALID_RECORD)
        _require(
            type(record.kind) is str and record.kind in schema.RECORD_RULES,
            Status.INVALID_RECORD,
        )
        rule = schema.RECORD_RULES[record.kind]
        _ref(record.ref)
        _require(
            record.ref.domain == rule.domain and record.ref not in declared,
            Status.INVALID_REF,
        )
        _require(
            record.ref.position == positions.get(record.ref.domain, 0),
            Status.INVALID_REF,
        )
        positions[record.ref.domain] = record.ref.position + 1
        declared[record.ref] = record
        _require(
            type(record.fields) is tuple and len(record.fields) == len(rule.fields),
            Status.INVALID_FIELD,
        )
        pending = [(f.value, 0) for f in record.fields if type(f) is schema.Field]
        while pending:
            value, depth = pending.pop()
            _require(depth <= schema.MAX_DEPTH, Status.RESOURCE_LIMIT)
            value_count += 1
            _require(value_count <= schema.MAX_EDGES * 8, Status.RESOURCE_LIMIT)
            _require(type(value) is schema.Value, Status.INVALID_VALUE)
            if type(value.data) is str:
                _require(len(value.data) <= schema.MAX_TEXT, Status.RESOURCE_LIMIT)
                text_bytes += len(value.data.encode("utf-8"))
                _require(text_bytes <= schema.MAX_BYTES, Status.RESOURCE_LIMIT)
            elif type(value.data) is tuple:
                _require(len(value.data) <= schema.MAX_EDGES, Status.RESOURCE_LIMIT)
                pending.extend((item, depth + 1) for item in value.data)
        for ordinal, (field, expected) in enumerate(
            zip(record.fields, rule.fields, strict=True)
        ):
            try:
                _require(
                    type(field) is schema.Field
                    and type(field.name) is str
                    and field.name == expected.name,
                    Status.INVALID_FIELD,
                )
                _validate_value(field.value, expected.shape, references, set())
            except _Reject as error:
                raise _Reject(error.status, position, ordinal) from None
    _require(all(ref in declared for ref in references), Status.INVALID_REF)
    _relationships(document, declared)
    return declared


def _data(value: Any) -> Any:
    if value.tag in (schema.Tag.SEQUENCE, schema.Tag.MAPPING):
        return tuple(_data(item) for item in value.data)
    return value.data


def _acyclic(edges):
    """Only declared execution dependencies use this rule."""
    incoming = {node: 0 for node in edges}
    for parents in edges.values():
        for parent in parents:
            incoming[parent] = incoming.get(parent, 0) + 1
    pending = [node for node, count in incoming.items() if count == 0]
    visited = 0
    while pending:
        node = pending.pop()
        visited += 1
        for parent in edges.get(node, ()):
            incoming[parent] -= 1
            if incoming[parent] == 0:
                pending.append(parent)
    _require(visited == len(incoming), Status.INVALID_RELATION)


def _relationships(document, declared):
    """Check document claims, without compiler construction or source authority."""
    fields = {
        ref: {f.name: _data(f.value) for f in record.fields}
        for ref, record in declared.items()
    }
    kinds = {}
    for record in document.records:
        kinds.setdefault(record.kind, []).append(record.ref)

    def require(condition):
        _require(condition, Status.INVALID_RELATION)

    def one(kind):
        values = kinds.get(kind, ())
        require(len(values) == 1)
        return values[0]

    roles = {
        "definition": ("definition",),
        "producer": ("definition",),
        "consumer": ("definition",),
        "block": ("select_block", "join"),
        "boundary": ("select_block", "result_boundary", "set_body"),
        "input_use": ("input_use",),
        "input_port": ("input_port",),
        "source_port": ("source_port", "export"),
        "export": ("export",),
        "origin": ("origin",),
        "ordering": ("relation_order",),
        "distinct": ("distinct",),
        "aggregation": ("aggregation",),
        "window": ("window",),
        "obligation": ("single_match",),
        "join": ("join",),
        "predicate": ("expression",),
        "symbol": ("symbol",),
        "body": ("set_body",),
        "child": ("expression",),
    }
    for record in document.records:
        for name, value in fields[record.ref].items():
            if type(value) is not schema.Ref or value.domain != "project_sql_plan_ref":
                continue
            allowed = roles.get(name)
            if name == "expression":
                allowed = (
                    ("order_expression",)
                    if record.kind == "project_sql_order_item"
                    else ("expression",)
                )
            elif name in ("left", "right"):
                allowed = (
                    ("join_port",)
                    if record.kind == "project_sql_relationship_match"
                    else ("expression",)
                )
            elif name == "operand":
                allowed = (
                    ("set_operand",)
                    if record.kind == "project_sql_set_input"
                    else ("expression",)
                )
            elif name == "parent":
                allowed = (
                    ("single_match_proof",)
                    if record.kind == "project_sql_single_match_proof"
                    else ("expression",)
                )
            if allowed is not None:
                require(fields[value]["kind"] in allowed)

    root = one("observation")
    require(document.records[0].ref == root)
    p = fields[one("project_sql_plan")]
    report = fields[fields[root]["report"]]
    source_map = fields[one("project_sql_source_map")]
    require(
        fields[root]["plan"]
        == report["plan"]
        == source_map["plan"]
        == one("project_sql_plan")
    )
    require(declared[fields[root]["report"]].kind == "project_sql_requirement_report")
    require(fields[root]["source_map"] == one("project_sql_source_map"))
    require(
        p["literal_policy"] == report["literal_policy"] == source_map["literal_policy"]
    )
    require(p["fixed_envelope"] == report["envelope"] == source_map["envelope"])
    require(p["input_uses"] == report["input_uses"])
    bindings = fields[p["bindings"]]

    def grouped_by(collection, name):
        groups = {}
        for ref in collection:
            groups.setdefault(fields[ref][name], []).append(ref)
        return groups

    operand_groups = grouped_by(p["operands"], "parent")
    window_use_groups = grouped_by(p["window_uses"], "window")
    window_argument_groups = grouped_by(p["window_arguments"], "window")
    aggregate_groups = grouped_by(p["aggregates"], "aggregation")
    group_key_groups = grouped_by(p["group_keys"], "aggregation")
    risk_groups = grouped_by(p["aggregate_risks"], "aggregation")
    source_associations = grouped_by(source_map["associations"], "entry")
    require(p["scope"] == bindings["scope"] == one("project_sql_plan_scope"))
    for name in (
        "sources",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "boundaries",
    ):
        require(p[name] == bindings[name])
    require(p["symbols"][: len(bindings["symbols"])] == bindings["symbols"])

    # Every plan reference has one primary declaration. Source descriptors and
    # report/map endpoints refer back to it and are not second declarations.
    primary = {}
    for name in (
        "definitions",
        "literal_sites",
        "literal_slots",
        "bind_uses",
        "blocks",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "projections",
        "boundaries",
        "symbols",
        "origins",
        "demands",
        "expression_sites",
        "expressions",
        "operands",
        "stage_ports",
        "let_values",
        "filters",
        "joins",
        "join_inputs",
        "join_ports",
        "relationship_matches",
        "join_tails",
        "single_matches",
        "single_match_proofs",
        "aggregations",
        "group_keys",
        "aggregates",
        "aggregate_projections",
        "aggregate_risks",
        "windows",
        "window_uses",
        "window_arguments",
        "window_policies",
        "window_projections",
        "result_boundaries",
        "result_ports",
        "distincts",
        "quotient_fields",
        "orders",
        "order_items",
        "order_expressions",
        "order_uses",
        "hidden_order_requirements",
        "result_limits",
        "result_exports",
        "set_bodies",
        "set_operands",
        "set_inputs",
        "set_columns",
        "values",
    ):
        values = (
            bindings[name]
            if name == "definitions"
            else fields[p["fixed_envelope"]][name]
            if name == "values"
            else p[name]
        )
        for value in values:
            ref = fields[value]["ref"]
            require(ref not in primary)
            primary[ref] = value
    require(set(primary) == set(kinds.get("project_sql_plan_ref", ())))
    positions = {}
    for ref in kinds.get("project_sql_plan_ref", ()):
        item = fields[ref]
        require(item["scope"] == p["scope"])
        # Plan ordinals are domain-local authority order, independent of the
        # portable record's breadth-first allocation order.
        positions.setdefault(item["kind"], []).append(int(item["position"]))
    for values in positions.values():
        require(sorted(values) == list(range(len(values))))

    expression_roles = {
        "project_sql_unary": ("operand",),
        "project_sql_binary": ("left", "right"),
        "project_sql_comparison": ("left", "right"),
        "project_sql_is_null": ("value",),
        "project_sql_between": ("value", "lower", "upper"),
    }
    expression_edges = {}
    for ref in p["expressions"]:
        expression = fields[ref]
        children = tuple(
            expression[name] for name in expression_roles.get(declared[ref].kind, ())
        )
        if declared[ref].kind == "project_sql_aggregate_argument_call":
            children = expression["arguments"]
        expression_edges[expression["ref"]] = children
        for name, child in zip(expression_roles.get(declared[ref].kind, ()), children):
            require(fields[child]["kind"] == "expression")
            require(
                fields[primary[child]]["expression"]
                == fields[expression["expression"]][name]
            )
        operands = tuple(fields[r] for r in operand_groups.get(expression["ref"], ()))
        require(tuple(item["child"] for item in operands) == children)
        require(
            tuple(int(item["position"]) for item in operands)
            == tuple(range(len(children)))
        )
    _acyclic(expression_edges)
    dependencies = {fields[d]["ref"]: [] for d in bindings["definitions"]}
    for use in p["input_uses"]:
        dependencies[fields[use]["consumer"]].append(fields[use]["producer"])
    _acyclic(dependencies)
    _acyclic(
        {
            fields[r]["ref"]: ()
            if fields[r]["predecessor"] is None
            else (fields[r]["predecessor"],)
            for r in (*p["blocks"], *p["result_boundaries"])
        }
    )

    require(bool(bindings["definitions"]) and bool(p["exports"]))
    selected_owner = fields[p["scope"]]["selected_owner"]
    require(
        declared[fields[selected_owner]["definition"]].kind
        in ("table_def", "query_def", "set_relation_def")
    )
    selected_definitions = tuple(
        r
        for r in bindings["definitions"]
        if fields[fields[r]["entry"]]["owner"] == selected_owner
    )
    require(
        len(selected_definitions) == 1
        and fields[selected_definitions[0]]["exports"] == p["exports"]
    )
    blocks_by_definition = grouped_by(p["blocks"], "definition")
    sets_by_definition = grouped_by(p["set_bodies"], "definition")
    sources_by_definition = grouped_by(p["sources"], "ref")
    for ref in bindings["definitions"]:
        definition = fields[ref]
        owner = fields[fields[definition["entry"]]["owner"]]
        kind = declared[owner["definition"]].kind
        blocks = blocks_by_definition.get(definition["ref"], ())
        bodies = sets_by_definition.get(definition["ref"], ())
        sources = sources_by_definition.get(definition["ref"], ())
        if kind == "source_def":
            require(len(sources) == 1 and not blocks and not bodies)
        elif kind == "set_relation_def":
            require(len(bodies) == 1 and not blocks and not sources)
            require(fields[bodies[0]]["source"] == definition["entry"])
            require(
                fields[fields[bodies[0]]["operation"]]["owner"]
                == fields[definition["entry"]]["owner"]
            )
        else:
            require(
                kind in ("table_def", "query_def")
                and bool(blocks)
                and not bodies
                and not sources
            )
    require(
        tuple(fields[entry]["demand"] for entry in report["entries"]) == p["demands"]
    )
    families = {
        "project_sql_source_realization_demand": "source_realization",
        "project_sql_export_representation_demand": "export_representation",
        "project_sql_expression_demand": "expression",
        "project_sql_stage_value_demand": "stage_value",
        "project_sql_filter_demand": "filter",
        "project_sql_scope_demand": "scope",
        "project_sql_join_demand": "join",
        "project_sql_aggregate_demand": "aggregation",
        "project_sql_window_demand": "window",
        "project_sql_result_demand": "result",
        "project_sql_set_demand": "set",
        "project_sql_literal_demand": "fixed_literal_transport",
    }
    for entry, demand in zip(report["entries"], p["demands"], strict=True):
        require(fields[entry]["ref"] == fields[demand]["ref"])
        require(fields[entry]["subject"] == fields[demand]["subject"])
        family = families[declared[demand].kind]
        require(fields[entry]["family"] == family)
        data = fields[demand]
        if family in ("expression", "filter"):
            subkind = fields[data["site"]]["role"]
        elif family in ("stage_value", "scope"):
            subkind = fields[primary[data["subject"]]]["kind"]
        elif family == "fixed_literal_transport":
            subkind = fields[fields[data["use"]]["slot"]]["tag"]
        else:
            subkind = data.get("kind")
        require(fields[entry]["subkind"] == subkind)
        require(fields[entry]["origin"] == primary[data["origin"]])
        scope = fields[fields[entry]["scope"]]
        require(
            fields[fields[primary[scope["definition"]]]["entry"]]["owner"]
            == fields[fields[entry]["origin"]]["owner"]
        )
        require(
            all(
                fields[primary[r]]["definition"] == scope["definition"]
                for r in scope["stages"]
            )
        )
        require(
            all(
                fields[primary[r]]["consumer"] == scope["definition"]
                for r in scope["input_uses"]
            )
        )
    require(
        tuple(fields[entry]["original"] for entry in source_map["entries"])
        == p["origins"]
    )
    require(fields[report["summary"]]["target"] == "not_assessed")
    require(int(fields[report["summary"]]["demand_count"]) == len(p["demands"]))
    expected_demands = []
    for collection, kind in (
        ("sources", "project_sql_source_realization_demand"),
        ("all_exports", "project_sql_export_representation_demand"),
        ("expressions", "project_sql_expression_demand"),
        ("stage_ports", "project_sql_stage_value_demand"),
        ("filters", "project_sql_filter_demand"),
        ("blocks", "project_sql_scope_demand"),
        ("bind_uses", "project_sql_literal_demand"),
    ):
        expected_demands.extend((kind, fields[r]["ref"], None) for r in p[collection])
    for collection, kind, subkind in (
        ("joins", "project_sql_join_demand", "join_rows"),
        ("join_inputs", "project_sql_join_demand", "match_input"),
        ("relationship_matches", "project_sql_join_demand", "relationship_equality"),
        ("join_tails", "project_sql_join_demand", "post_match_scope"),
        ("single_matches", "project_sql_join_demand", "single_match"),
        ("single_match_proofs", "project_sql_join_demand", "proof_context"),
        ("aggregations", "project_sql_aggregate_demand", "grouping_and_empty_input"),
        ("group_keys", "project_sql_aggregate_demand", "group_comparison"),
        ("aggregates", "project_sql_aggregate_demand", "aggregate_operation"),
        ("aggregate_projections", "project_sql_aggregate_demand", "result_projection"),
        ("aggregate_risks", "project_sql_aggregate_demand", "retained_risk"),
        ("windows", "project_sql_window_demand", "input_bag_and_result"),
        ("window_uses", "project_sql_window_demand", "input_use"),
        ("window_arguments", "project_sql_window_demand", "argument"),
        (
            "window_policies",
            "project_sql_window_demand",
            "frame_modifiers_named_components",
        ),
        ("window_projections", "project_sql_window_demand", "result_projection"),
        (
            "result_boundaries",
            "project_sql_result_demand",
            "result_scope_and_membership",
        ),
        ("result_ports", "project_sql_result_demand", "result_value_representation"),
        ("distincts", "project_sql_result_demand", "visible_row_quotient"),
        (
            "quotient_fields",
            "project_sql_result_demand",
            "field_equivalence_nulls_and_type_sources",
        ),
        ("orders", "project_sql_result_demand", "relation_order_scope"),
        ("order_items", "project_sql_result_demand", "order_direction_nulls_and_ties"),
        (
            "order_expressions",
            "project_sql_result_demand",
            "order_expression_type_and_operands",
        ),
        ("order_uses", "project_sql_result_demand", "order_value_use"),
        (
            "hidden_order_requirements",
            "project_sql_result_demand",
            "pending_strict_fd_order_realization",
        ),
        ("result_limits", "project_sql_result_demand", "static_row_count_upper_bound"),
        ("result_exports", "project_sql_result_demand", "canonical_result_image"),
        ("set_operands", "project_sql_set_demand", "set_operand_membership"),
        (
            "set_inputs",
            "project_sql_set_demand",
            "set_input_type_null_and_representation",
        ),
        (
            "set_columns",
            "project_sql_set_demand",
            "set_positional_column_and_value_sources",
        ),
    ):
        expected_demands.extend(
            (kind, fields[r]["ref"], subkind) for r in p[collection]
        )
    for ref in p["join_ports"]:
        expected_demands.append(
            (
                "project_sql_join_demand",
                fields[ref]["ref"],
                "match_field" if fields[ref]["kind"] == "match" else "output_field",
            )
        )
    for ref in p["set_bodies"]:
        kinds_for_body = [
            "set_operation_quantifier_multiplicity_and_membership",
            "set_properties_and_row_domain",
        ]
        if fields[ref]["requires_equivalence"]:
            kinds_for_body.append("set_whole_row_equivalence")
        expected_demands.extend(
            ("project_sql_set_demand", fields[ref]["ref"], kind)
            for kind in kinds_for_body
        )
    actual_demands = []
    for position, ref in enumerate(p["demands"]):
        demand = fields[ref]
        require(int(fields[demand["ref"]]["position"]) == position)
        actual_demands.append(
            (declared[ref].kind, demand["subject"], demand.get("kind"))
        )
        if "witness" in demand:
            require(fields[demand["witness"]]["ref"] == demand["subject"])
    require(Counter(actual_demands) == Counter(expected_demands))

    images = {}
    for ref in p["result_exports"]:
        entry = fields[ref]
        require(entry["canonical"] not in images)
        canonical = fields[entry["canonical"]]
        require(canonical["owner"] == entry["definition"])
        require(entry["port"] in primary)
        require(fields[entry["port"]]["kind"] in ("export", "result_port"))
        images[entry["canonical"]] = entry["port"]
    require(set(images) == set(p["all_exports"]))
    for ref in p["input_uses"]:
        entry = fields[ref]
        require(fields[entry["producer"]]["kind"] == "definition")
        require(fields[entry["consumer"]]["kind"] == "definition")
        require(entry["producer"] != entry["consumer"])
        exports = fields[primary[entry["producer"]]]["exports"]
        require(len(exports) == len(entry["ports"]))
        for port, canonical in zip(entry["ports"], exports, strict=True):
            require(fields[port]["owner"] == entry["ref"])
            require(fields[port]["producer_port"] == fields[canonical]["ref"])

    envelope = fields[p["fixed_envelope"]]
    require(
        envelope["scope"] == p["scope"] and envelope["policy"] == p["literal_policy"]
    )
    require(envelope["slots"] == p["literal_slots"])
    require(len(envelope["values"]) == len(p["literal_slots"]))
    tags = {
        "Bool": schema.Tag.BOOLEAN,
        "Int": schema.Tag.INTEGER,
        "Float": schema.Tag.FLOAT,
        "Text": schema.Tag.TEXT,
    }
    for slot, fixed in zip(p["literal_slots"], envelope["values"], strict=True):
        s, v = fields[slot], fields[fixed]
        require(v["slot"] == slot and v["tag"] == s["tag"])
        value = next(f.value for f in declared[fixed].fields if f.name == "value")
        require(value.tag is tags[s["tag"]])
        require(fields[s["site"]]["disposition"] == "bound")
        position = fields[fields[s["site"]]["position"]]
        literal = next(
            f.value for f in declared[position["literal"]].fields if f.name == "value"
        )
        require(value == literal)
    bound_sites = tuple(
        ref for ref in p["literal_sites"] if fields[ref]["disposition"] == "bound"
    )
    require(tuple(fields[slot]["site"] for slot in p["literal_slots"]) == bound_sites)
    if p["literal_policy"] == "preserve_literals":
        require(not bound_sites and not p["bind_uses"])
    bound = tuple(
        ref
        for ref in p["expressions"]
        if declared[ref].kind == "project_sql_bound_literal"
    )
    require(tuple(fields[ref]["use"] for ref in bound) == p["bind_uses"])
    for expression, use in zip(bound, p["bind_uses"], strict=True):
        require(fields[use]["expression"] == fields[expression]["ref"])
        require(fields[use]["slot"] in p["literal_slots"])
        require(
            fields[expression]["value_type"]
            == fields[fields[use]["slot"]]["value_type"]
        )
    literal_demands = tuple(
        ref
        for ref in p["demands"]
        if declared[ref].kind == "project_sql_literal_demand"
    )
    require(tuple(fields[ref]["use"] for ref in literal_demands) == p["bind_uses"])
    for ref in literal_demands:
        demand = fields[ref]
        require(
            demand["requirements"]
            == (
                "exact_data_representation",
                "original_nullability",
                "exact_range_and_precision",
                "typed_operator_and_operand_context",
                "applicable_collation_and_overload",
            )
        )
        require(demand["value"] in envelope["values"])
        require(fields[demand["value"]]["slot"] == fields[demand["use"]]["slot"])

    for ref in p["set_bodies"]:
        body = fields[ref]
        operands = tuple(primary[r] for r in body["operands"])
        columns = tuple(primary[r] for r in body["columns"])
        require(len(operands) >= 2 and bool(columns))
        require(body["fold"] == "source_order_left_fold")
        require(
            tuple(fields[r]["body"] for r in operands) == (body["ref"],) * len(operands)
        )
        require(
            tuple(int(fields[r]["position"]) for r in operands)
            == tuple(range(len(operands)))
        )
        require(
            tuple(fields[r]["body"] for r in columns) == (body["ref"],) * len(columns)
        )
        require(
            tuple(int(fields[r]["position"]) for r in columns)
            == tuple(range(len(columns)))
        )
        require(tuple(fields[r]["output"] for r in columns) == body["outputs"])
        for operand in operands:
            item = fields[operand]
            require(len(item["fields"]) == len(columns))
            require(fields[item["use"]]["producer"] == item["producer"])
            for field in item["fields"]:
                source = fields[primary[field]]
                require(source["operand"] == item["ref"])
                terminal = fields[source["terminal"]]
                require(terminal["ref"] in primary)
                require(
                    fields[terminal["ref"]]["kind"]
                    in ("export", "source_port", "result_port")
                )
        for position, column in enumerate(columns):
            item = fields[column]
            inputs = tuple(fields[r]["fields"][position] for r in operands)
            require(item["inputs"] == inputs)
            require(
                item["value_inputs"]
                == (inputs[:1] if body["kind"] == "except" else inputs)
            )
            output = fields[primary[item["output"]]]
            require(output["canonical"] is not None)
            require(output["definition"] == body["definition"])
            require(fields[output["canonical"]]["field"] == item["field"])
            require(
                fields[output["canonical"]]["identity"]
                == fields[item["semantic"]]["identity"]
            )

    for ref in p["distincts"]:
        item = fields[ref]
        quotient = tuple(primary[r] for r in item["fields"])
        require(bool(quotient))
        require(
            tuple(int(fields[r]["position"]) for r in quotient)
            == tuple(range(len(quotient)))
        )
        for q in quotient:
            field = fields[q]
            require(field["distinct"] == item["ref"])
            require(fields[primary[field["input"]]]["canonical"] == field["canonical"])
            require(fields[primary[field["output"]]]["canonical"] == field["canonical"])
            require(field["canonical"] in p["all_exports"])
    for ref in kinds.get("project_row_equivalence_field", ()):
        item = fields[ref]
        require(item["parents"] == fields[item["selected"]]["type_sources"])
        for parent in item["parents"]:
            require(fields[parent]["types"] == item["types"])
        if item["decimal"] is not None:
            decimal = fields[item["decimal"]]
            require(
                0 < int(decimal["precision"])
                and 0 <= int(decimal["scale"]) <= int(decimal["precision"])
            )
            if item["parents"] and item["reason"] is None:
                require(item["decimal"] == fields[item["parents"][0]]["decimal"])
    for ref in kinds.get("project_ir_output_determination_result", ()):
        result = fields[ref]
        seed, requested, closure = (
            fields[result["seed"]],
            fields[result["requested"]],
            fields[result["closure"]],
        )
        require(closure["seed"] == result["seed"])
        final = fields[closure["classes"]]
        require(seed["index"] == requested["index"] == final["index"])
        index = fields[seed["index"]]
        available = set(seed["classes"])
        for step in closure["witness"]:
            witness = fields[step]
            fact = fields[witness["fact"]]
            require(witness["fact"] in index["facts"] and fact["strength"] == "strict")
            require(bool(fact["supports"]) and set(fact["determinants"]) <= available)
            require(
                tuple(r for r in fact["dependents"] if r not in available)
                == witness["derived"]
            )
            require(bool(witness["derived"]))
            available.update(witness["derived"])
        require(
            tuple(r for r in index["universe"] if r in available) == final["classes"]
        )
        require(
            (set(requested["classes"]) <= available) == (result["status"] == "proven")
        )
    for ref in p["hidden_order_requirements"]:
        item = fields[ref]
        proof = fields[item["proof"]]
        require(proof["status"] == "proven")
        require(
            tuple(pair[0] for pair in item["determinants"])
            == fields[proof["seed"]]["classes"]
        )
        for cls, ports in item["determinants"]:
            require(bool(ports))
            require(all(port in primary for port in ports))
        require(fields[proof["requested"]]["classes"] == item["requested"])
        require(fields[primary[item["item"]]]["value"] == item["ref"])
        require(
            item["ref"] not in tuple(fields[r]["port"] for r in p["result_exports"])
        )
    for ref in p["order_items"]:
        item = fields[ref]
        determination = item["determination"]
        if determination is not None:
            require(len(determination) in (2, 3) and determination[0] == item["source"])
            if len(determination) == 2:
                require(fields[item["value"]]["kind"] == "hidden_order_requirement")
                require(fields[primary[item["value"]]]["proof"] == determination[1])
            else:
                require(set(determination[2]) <= set(determination[1]))
    for ref in p["result_limits"]:
        limit = fields[ref]
        require(
            0 <= int(limit["value"]) <= int(limit["maximum"])
            and limit["value"] == limit["row_count_upper_bound"]
        )
        literal = next(
            f.value for f in declared[limit["literal"]].fields if f.name == "value"
        )
        require(literal.tag is schema.Tag.INTEGER and literal.data == limit["value"])

    for ref in p["windows"]:
        window = fields[ref]
        require(window["result"] in primary)
        policy = fields[primary[window["policy"]]]
        require(policy["window"] == window["ref"])
        require(
            tuple(fields[r]["ref"] for r in window_use_groups.get(window["ref"], ()))
            == window["uses"]
        )
        require(
            tuple(
                fields[r]["ref"] for r in window_argument_groups.get(window["ref"], ())
            )
            == window["arguments"]
        )
        for position, use in enumerate(window["uses"]):
            require(int(fields[primary[use]]["position"]) == position)
    require(
        tuple(fields[r]["window"] for r in p["window_policies"])
        == tuple(fields[r]["ref"] for r in p["windows"])
    )
    for ref in p["aggregations"]:
        item = fields[ref]
        authority = fields[item["authority"]]
        require(item["mode"] == authority["mode"])
        require(
            item["empty_input"]
            == ("one_global_row" if item["mode"] == "global" else "no_groups")
        )
        require(
            tuple(fields[r]["ref"] for r in aggregate_groups.get(item["ref"], ()))
            == item["aggregates"]
        )
        require(
            tuple(fields[r]["ref"] for r in group_key_groups.get(item["ref"], ()))
            == item["keys"]
        )
        require(
            tuple(fields[primary[r]]["source"] for r in item["keys"])
            == authority["keys"]
        )
        require(
            tuple(fields[primary[r]]["source"] for r in item["aggregates"])
            == authority["aggregates"]
        )
        require(
            tuple(fields[r]["source"] for r in risk_groups.get(item["ref"], ()))
            == authority["risks"]
        )
    for ref in kinds.get("project_joined_group_protection", ()):
        protection = fields[ref]
        properties = fields[protection["input_properties"]]
        strict = tuple(
            r for r in properties["keys"] if fields[r]["strength"] == "strict"
        )
        require(
            protection["strict_keys"] == strict
            and len(protection["determinations"]) == len(strict)
        )
        for key, proof in zip(strict, protection["determinations"], strict=True):
            require(fields[proof]["seed"] == protection["seed"])
            require(
                fields[fields[proof]["requested"]]["classes"]
                == fields[key]["determinants"]
            )
        if not any(
            fields[r]["status"] == "proven" for r in protection["determinations"]
        ):
            require(not protection["protected_factors"])

    row_rules = {
        "inner": "matched_pairs",
        "left": "left_preserved",
        "cross": "cartesian_pairs",
        "right": "right_preserved",
        "full": "both_preserved",
        "semi": "left_exists",
        "anti": "left_not_exists",
    }
    for ref in p["joins"]:
        join = fields[ref]
        require(join["rows"] == row_rules[join["kind"]])
        require(len(join["inputs"]) == 2)
        inputs = tuple(fields[primary[r]] for r in join["inputs"])
        require(tuple(int(r["ordinal"]) for r in inputs) == (0, 1))
        require(all(r["join"] == join["ref"] for r in inputs))
        for item in inputs:
            require((item["producer"] is None) != (item["predecessor"] is None))
            if item["producer"] is not None:
                if item["binding_use"] is not None:
                    require(
                        fields[primary[item["binding_use"]]]["producer"]
                        == item["producer"]
                    )
                sources = tuple(
                    fields[r]["ref"]
                    for r in fields[primary[item["producer"]]]["exports"]
                )
            else:
                require(item["binding_use"] is None)
                require(fields[item["predecessor"]]["kind"] == "join")
                sources = fields[primary[item["predecessor"]]]["outputs"]
            require(
                tuple(fields[primary[r]]["source"] for r in item["ports"]) == sources
            )
            for port in item["ports"]:
                member = fields[primary[port]]
                require(member["kind"] == "match" and member["input"] == item["ref"])
                expected_nulling = fields[member["field"]].get("nulling_joins", ())
                require(member["nulling"] == expected_nulling)
        left_width = len(inputs[0]["ports"])
        expected_width = (
            left_width
            if join["kind"] in ("semi", "anti")
            else left_width + len(inputs[1]["ports"])
        )
        require(len(join["outputs"]) == expected_width)
        original = fields[fields[join["source"]]["source"]]
        require(original["kind"] == join["kind"])
        node = fields[fields[join["source"]]["node"]]["ref"]
        for position, output in enumerate(join["outputs"]):
            port = fields[primary[output]]
            require(port["block"] == join["ref"] and port["kind"] == "output")
            require(int(port["position"]) == position)
            null_extended = (
                join["kind"] == "full"
                or (join["kind"] == "left" and position >= left_width)
                or (join["kind"] == "right" and position < left_width)
            )
            require((node in port["nulling"]) == null_extended)
    for ref in p["single_matches"]:
        match = fields[ref]
        original = fields[match["assessment"]]
        require(fields[match["source"]]["assessment"] == match["assessment"])
        require(original["request"] == match["request"])
        require(original["diagnostic"] == match["diagnostic"])
        require(
            original["downstream_enforcement_required"]
            == match["downstream_enforcement_required"]
        )
        proved = original["state"] == "proved"
        require(original["state"] in ("proved", "legal_unproved"))
        require(bool(match["proofs"]) == bool(original["proofs"]) == proved)
        require(match["downstream_enforcement_required"] == (not proved))
        require(
            match["input_pairs"]
            == tuple(fields[primary[j]]["inputs"] for j in match["joins"])
        )
        require(
            tuple(fields[primary[r]]["source"] for r in match["proofs"])
            == fields[match["source"]]["proofs"]
        )
        for proof in match["proofs"]:
            require(fields[primary[proof]]["obligation"] == match["ref"])
            require(fields[primary[proof]]["parent"] is None)
    for ref in p["single_match_proofs"]:
        proof = fields[ref]
        image = fields[proof["source"]]
        require(len(proof["joins"]) == len(image["boundaries"]))
        for join, boundary in zip(proof["joins"], image["boundaries"], strict=True):
            source = fields[primary[join]]["source"]
            require(
                (
                    source
                    if declared[boundary].kind == "project_ir_composed_join"
                    else fields[source]["source"]
                )
                == boundary
            )
        require(
            tuple(fields[primary[r]]["entry"] for r in proof["producers"])
            == image["producers"]
        )
        kind = fields[image["source"]]["kind"]
        roots = fields[image["source"]]["roots"]
        premise_nodes = []
        for producer in image["producers"]:
            entry = fields[producer]
            if declared[producer].kind == "project_ir_completed_query_block_output":
                premise_nodes.extend(
                    fields[op]["node"]
                    for op in entry["operators"]
                    if fields[op]["evidence"] in roots
                )
            elif declared[producer].kind == "project_ir_reused_effective_output":
                premise_nodes.extend(
                    fields[op]["node"] for op in entry["operators"] if op in roots
                )
            elif declared[producer].kind == "project_ir_rebound_existing_output":
                require(len(entry["operators"]) == len(entry["original_operators"]))
                premise_nodes.extend(
                    fields[new]["node"]
                    for old, new in zip(
                        entry["original_operators"], entry["operators"], strict=True
                    )
                    if old in roots
                )
        require(tuple(premise_nodes) == image["premise_nodes"])
        if kind in ("right_limit", "right_global"):
            require(
                bool(image["premise_nodes"])
                and bool(proof["producers"])
                and not proof["children"]
            )
        if kind == "whole_path":
            require(bool(proof["children"]))
            require(
                set(proof["joins"])
                == {
                    j
                    for child in proof["children"]
                    for j in fields[primary[child]]["joins"]
                }
            )
        for child in proof["children"]:
            require(fields[primary[child]]["parent"] == proof["ref"])
            require(fields[primary[child]]["obligation"] == proof["obligation"])
        require(
            tuple(fields[primary[r]]["source"] for r in proof["children"])
            == image["children"]
        )

    syntax = {
        "expression",
        "let_value",
        "filter",
        "projection",
        "group_key",
        "aggregate",
        "aggregate_projection",
        "window",
        "window_use",
        "window_argument",
        "window_projection",
        "relationship_match",
        "distinct",
        "relation_order",
        "order_item",
        "order_expression",
        "result_limit",
    }
    for kind in ("span", "source_location"):
        for ref in kinds.get(kind, ()):
            location = fields[ref]
            require(int(location["line"]) >= 1 and int(location["column"]) >= 1)
            require(
                all(
                    location[n] is None or int(location[n]) >= 1
                    for n in ("end_line", "end_column")
                )
            )
            if kind == "span":
                require(
                    location["end_line"] is not None
                    and location["end_column"] is not None
                )
            if location["end_line"] is not None:
                require(int(location["end_line"]) >= int(location["line"]))
                if location["end_column"] is not None:
                    require(
                        (int(location["end_line"]), int(location["end_column"]))
                        >= (int(location["line"]), int(location["column"]))
                    )
    for ref in kinds.get("project_sql_source_position", ()):
        position = fields[ref]
        coordinates = tuple(
            position[n] for n in ("line", "column", "end_line", "end_column")
        )
        if position["original"] is None:
            require(
                position["availability"] == "unavailable"
                and position["path"] is None
                and coordinates == (None,) * 4
            )
        else:
            require(
                position["availability"]
                == ("partial" if None in coordinates else "complete")
            )
            require(all(v is not None and int(v) >= 1 for v in coordinates[:2]))
            require(all(v is None or int(v) >= 1 for v in coordinates[2:]))
    for entry in source_map["entries"]:
        item = fields[entry]
        role = fields[item["original"]]["role"]
        require(
            item["nature"]
            == ("syntax_correspondence" if role in syntax else "generated_structure")
        )
        require(item["generated_reason"] == (None if role in syntax else role))
    for site in source_map["sites"]:
        item = fields[site]
        require(item["source"] in source_map["sources"])
        location = fields[item["location"]]
        require(location["original"] == fields[item["occurrence"]]["span"])
        require(location["path"] == fields[fields[item["source"]]["module"]]["path"])
        require(
            declared[item["container"]].kind
            in (
                "source_def",
                "query_def",
                "table_def",
                "set_relation_def",
                "shape_def",
                "type_def",
                "enum_def",
                "ConstraintDef",
                "DeriveDef",
                "field_def",
                "named_window_declaration",
                "import_statement",
                "export_statement",
                "relationship_metadata",
            )
        )
        container = fields[fields[item["container"]]["span"]]
        require(container["path"] == location["path"])
        require(
            (int(container["line"]), int(container["column"]))
            <= (int(location["line"]), int(location["column"]))
        )
        require(
            (int(location["end_line"]), int(location["end_column"]))
            <= (int(container["end_line"]), int(container["end_column"]))
        )
        if item["declaration"] is not None:
            require(
                fields[item["declaration"]]["module_position"]
                == fields[fields[item["source"]]["module"]]["position"]
            )
        if location["availability"] == "complete":
            require(
                all(
                    location[k] is not None and int(location[k]) >= 1
                    for k in ("line", "column", "end_line", "end_column")
                )
            )
            require(
                (int(location["line"]), int(location["column"]))
                <= (int(location["end_line"]), int(location["end_column"]))
            )
        if location["original"] is not None:
            require(
                all(
                    location[k] == fields[location["original"]][k]
                    for k in ("path", "line", "column", "end_line", "end_column")
                )
            )
    for ref in source_map["associations"]:
        association = fields[ref]
        require(
            association["entry"] in source_map["entries"]
            and association["site"] in source_map["sites"]
        )
        site = fields[association["site"]]
        if association["kind"] == "effective_to_authored_window":
            window = fields[association["evidence"]]
            require(
                site["occurrence"] == window["authored"]
                and association["observed"] == window["effective"]
            )
    origin_entries = {
        fields[fields[r]["original"]]["ref"]: r for r in source_map["entries"]
    }
    grouped = {}
    for entry in source_map["entries"]:
        original = fields[fields[entry]["original"]]
        grouped.setdefault(original["subject"], []).append(entry)
        causes = tuple(
            fields[r]
            for r in source_associations.get(entry, ())
            if fields[r]["kind"] == "authored_cause"
        )
        require(bool(causes))
        for cause in causes:
            require(
                cause["observed"]
                == original["cause"]
                == fields[cause["site"]]["occurrence"]
            )
            require(cause["evidence"] == original["evidence"])
    require(tuple(fields[r]["ref"] for r in source_map["subjects"]) == tuple(grouped))
    subject_entries = {fields[r]["ref"]: r for r in source_map["subjects"]}
    for ref in source_map["subjects"]:
        require(fields[ref]["origins"] == tuple(grouped[fields[ref]["ref"]]))
    link_cursor = 0
    for entry in source_map["entries"]:
        for ordinal, antecedent in enumerate(
            fields[fields[entry]["original"]]["antecedents"]
        ):
            require(link_cursor < len(source_map["links"]))
            link = fields[source_map["links"][link_cursor]]
            origin_endpoint = fields[antecedent]["kind"] == "origin"
            require(link["origin"] == entry and int(link["ordinal"]) == ordinal)
            require(
                link["kind"] == ("origin_ref" if origin_endpoint else "subject_ref")
            )
            require(
                link["target"]
                == (origin_entries if origin_endpoint else subject_entries)[antecedent]
            )
            link_cursor += 1
    require(link_cursor == len(source_map["links"]))

    assessment = fields[root]["assessment"]
    require(
        bool(kinds.get("project_sql_target_assessment")) == (assessment is not None)
    )
    if assessment is not None:
        a = fields[assessment]
        assessed_report = fields[a["report"]]
        require(assessed_report["plan"] == fields[root]["plan"])
        request, summary = fields[a["request"]], fields[a["summary"]]
        require(
            tuple(fields[r]["entry"] for r in a["demands"])
            == assessed_report["entries"]
        )
        require(
            tuple(fields[r]["demand"] for r in assessed_report["entries"])
            == p["demands"]
        )
        require(
            tuple(aspect for d in a["demands"] for aspect in fields[d]["aspects"])
            == a["aspects"]
        )
        residuals = []
        cap_cache = {}

        def cap_value(value):
            if value.tag is schema.Tag.REF:
                ref = value.data
                require(
                    declared[ref].kind
                    in (
                        "capability_key",
                        "capability_fact",
                        "capability_evidence",
                        "capability_disposition",
                    )
                )
                if ref not in cap_cache:
                    cap_cache[ref] = (
                        declared[ref].kind,
                        tuple(
                            (f.name, cap_value(f.value)) for f in declared[ref].fields
                        ),
                    )
                return value.tag, cap_cache[ref]
            if value.tag in (schema.Tag.SEQUENCE, schema.Tag.MAPPING):
                return value.tag, tuple(cap_value(item) for item in value.data)
            return value.tag, value.data

        def cap_record(ref):
            return cap_value(schema.Value(schema.Tag.REF, ref))

        def raw_lookup(ref, key, facts, complete, reason):
            matches = {}
            for fact in facts:
                if cap_record(fields[fact]["key"]) == cap_record(key):
                    matches.setdefault(cap_record(fact), fact)
            matching = tuple(matches.values())
            kind, result = declared[ref].kind, fields[ref]
            if len(matching) == 1:
                require(kind == "found" and result["fact"] == matching[0])
            elif matching:
                require(
                    kind == "conflict"
                    and result["evidence"] == matching
                    and result["reason"] == "conflicting_evidence"
                )
            elif complete:
                require(
                    kind == "absent"
                    and cap_record(result["key"]) == cap_record(key)
                    and result["reason"] == "no_catalog_entry"
                )
            else:
                require(
                    kind == "unknown"
                    and result["reason"]
                    == ("not_evidenced" if reason is None else reason)
                )

        composition = request["composition"]
        occurrences = (
            fields[composition]["effective_occurrences"]
            if composition is not None
            and declared[composition].kind == "capability_profile_composition_success"
            else ()
        )
        if composition is not None:
            composed = fields[composition]
            require(
                composed["base"] == request["base"]
                and composed["overlays"] == request["overlays"]
            )
            if declared[composition].kind == "capability_profile_composition_success":
                profiles = composed["dependency_order"]
                require(
                    len(profiles) == len(request["overlays"]) + 1
                    and set(profiles) == {request["base"], *request["overlays"]}
                )
                expected = tuple(
                    (profile, occurrence)
                    for profile in profiles
                    for occurrence in fields[profile]["capability_occurrences"]
                )
                require(
                    tuple(
                        (fields[r]["profile"], fields[r]["occurrence"])
                        for r in occurrences
                    )
                    == expected
                )
            else:
                require(bool(composed["blockers"]))
        if request["catalog_context"] is not None:
            catalog = fields[request["catalog_context"]]
            selectors = fields[catalog["selectors"]]["occurrences"]
            require(
                len(request["catalog_residuals"])
                == len(catalog["selections"])
                == len(selectors)
            )
            for i, residual in enumerate(request["catalog_residuals"]):
                value = fields[residual]
                require(
                    value["context"] == request["catalog_context"]
                    and value["selector"] == selectors[i]
                    and value["selection"] == catalog["selections"][i]
                )
                require(
                    int(value["position"]) == i
                    and "no_plan_extension_selector_mapping" in value["issues"]
                )
        else:
            require(not request["catalog_residuals"])
        for ref in a["lookups"]:
            lookup = fields[ref]
            inputs = fields[lookup["inputs"]]
            require(lookup["request"] == a["request"])
            require(cap_record(inputs["key"]) == cap_record(lookup["key"]))
            require(lookup["profile_occurrences"] == occurrences)
            raw_lookup(
                lookup["provider_result"],
                lookup["key"],
                inputs["facts"],
                inputs["domain_complete"],
                inputs["unknown_reason"],
            )
            raw_lookup(
                lookup["profile_result"],
                lookup["key"],
                tuple(fields[fields[r]["occurrence"]]["fact"] for r in occurrences),
                False,
                None,
            )
            applicable = not any(
                issue in request["issues"]
                for issue in (
                    "explicit_target_profile_missing",
                    "profile_target_family_or_release_mismatch",
                    "profile_composition_blocked",
                )
            )
            result = fields[lookup["profile_result"]]
            fact_refs = (
                (result["fact"],)
                if declared[lookup["profile_result"]].kind == "found"
                else result["evidence"]
                if declared[lookup["profile_result"]].kind == "conflict"
                else ()
            )
            for fact in fact_refs:
                evidence = tuple(fields[r] for r in fields[fact]["evidence"])
                applicable = (
                    applicable
                    and all(
                        e["extension"]
                        in (None, fields[fields[fact]["key"]]["extension"])
                        for e in evidence
                    )
                    and (
                        any(e["dialect"] is None for e in evidence)
                        or all(
                            e["dialect"] == fields[request["target"]]["family"]
                            for e in evidence
                        )
                    )
                )
            require(lookup["profile_applicable"] == applicable)
        for position, demand in enumerate(a["demands"]):
            local = fields[demand]
            entry = fields[local["entry"]]
            require(int(local["position"]) == position and bool(local["aspects"]))
            family, subkind = entry["family"], entry["subkind"]
            layout = []
            if family == "source_realization":
                layout.append("source_family")
            if family in (
                "export_representation",
                "stage_value",
                "fixed_literal_transport",
            ) or (family == "window" and subkind == "argument"):
                layout.append("compiler_type_identity")
            if family == "expression":
                layout.append("compiler_expression_result")
            if family == "aggregation" and subkind == "aggregate_operation":
                layout.append("compiler_aggregate_signature")
            if family == "window" and subkind == "input_bag_and_result":
                layout.append("compiler_window_signature")
            if family == "fixed_literal_transport":
                layout.append("compiler_literal_result")
            layout.extend(
                ["remaining_original_requirement"]
                * (5 if family == "fixed_literal_transport" else 1)
            )
            actual = tuple(
                fields[fields[r]["proposition"]]["kind"] for r in local["aspects"]
            )
            require(actual == tuple(layout))
            for ordinal, aspect in enumerate(local["aspects"]):
                item = fields[aspect]
                proposition = fields[item["proposition"]]
                require(
                    item["entry"] == local["entry"] and int(item["ordinal"]) == ordinal
                )
                require(proposition["witness"] == entry["demand"])
                if proposition["kind"] == "remaining_original_requirement":
                    require(
                        proposition["key"] is None and proposition["gap"] is not None
                    )
                    residuals.append(aspect)
                    require(
                        item["outcomes"]
                        == (
                            ("not_assessed",)
                            if request["target"] is None
                            else ("unmapped_proposition",)
                        )
                    )
                require(
                    (item["lookup"] is not None)
                    == (
                        proposition["key"] is not None and request["target"] is not None
                    )
                )
                if item["lookup"] is not None:
                    lookup = fields[item["lookup"]]
                    require(
                        lookup["request"] == a["request"]
                        and lookup["kind"] == proposition["kind"]
                    )
                    require(
                        declared[lookup["key"]].fields
                        == declared[proposition["key"]].fields
                    )
                    raw = (lookup["provider_result"], lookup["profile_result"])
                    if any(declared[r].kind == "conflict" for r in raw):
                        require(
                            "conflicting_facts" in item["outcomes"]
                            and "satisfied_exact_subproposition" not in item["outcomes"]
                        )
                    if not lookup["profile_applicable"]:
                        require("inapplicable_declared_evidence" in item["outcomes"])
                    outcomes = set()
                    for raw_ref in raw:
                        raw_kind = declared[raw_ref].kind
                        outcome = {
                            "conflict": "conflicting_facts",
                            "absent": "complete_provider_domain_absent",
                            "unknown": "incomplete_lookup_unknown",
                        }.get(raw_kind)
                        if outcome is not None:
                            outcomes.add(outcome)
                        if (
                            raw_kind == "found"
                            and fields[fields[raw_ref]["fact"]]["support"]
                            == "explicitly_unsupported"
                        ):
                            outcomes.add("exact_negative")
                    if any(
                        issue in request["issues"]
                        for issue in (
                            "explicit_target_profile_missing",
                            "profile_target_family_or_release_mismatch",
                            "profile_composition_blocked",
                        )
                    ):
                        outcomes.add("explicit_input_unresolved")
                    if not lookup["profile_applicable"]:
                        outcomes.add("inapplicable_declared_evidence")
                    if not outcomes and all(
                        declared[r].kind == "found"
                        and fields[fields[r]["fact"]]["support"] == "supported"
                        for r in raw
                    ):
                        outcomes.add("satisfied_exact_subproposition")
                    order = (
                        "satisfied_exact_subproposition",
                        "exact_negative",
                        "complete_provider_domain_absent",
                        "incomplete_lookup_unknown",
                        "conflicting_facts",
                        "unmapped_proposition",
                        "inapplicable_declared_evidence",
                        "explicit_input_unresolved",
                        "not_assessed",
                    )
                    require(
                        item["outcomes"] == tuple(o for o in order if o in outcomes)
                    )
                elif request["target"] is None:
                    require(item["outcomes"] == ("not_assessed",))
                elif proposition["kind"] == "source_family":
                    source = fields[fields[entry["demand"]]["source"]]
                    callee = fields[fields[source["connector"]]["callee"]]
                    spelling = (
                        ".".join(callee["parts"])
                        if "parts" in callee
                        else callee["name"]
                    )
                    family = {
                        "postgres.table": "postgresql",
                        "mysql.table": "mysql",
                    }.get(spelling)
                    require(
                        item["outcomes"]
                        == (
                            ("satisfied_exact_subproposition",)
                            if family == fields[request["target"]]["family"]
                            else ("exact_negative",)
                        )
                    )
                else:
                    require(item["outcomes"] == ("unmapped_proposition",))
            require(
                local["posture"]
                == (
                    "not_assessed"
                    if request["target"] is None
                    else "incomplete_requirement_assessment"
                )
            )
        require(
            summary["posture"]
            == (
                "not_assessed"
                if request["target"] is None
                else "incomplete_requirement_assessment"
            )
        )
        require(summary["pending_realizations"] == tuple(residuals))
        require(summary["original_obligations"] == assessed_report["summary"])
        require(
            summary["input_issues"] == request["issues"]
            and summary["catalog_residuals"] == request["catalog_residuals"]
        )
        require(
            int(summary["demand_count"]) == len(a["demands"])
            and int(summary["aspect_count"]) == len(a["aspects"])
            and int(summary["query_count"]) == len(a["lookups"])
        )
        categories = dict(summary["categories"])
        for category, members in categories.items():
            require(
                members
                == tuple(r for r in a["aspects"] if category in fields[r]["outcomes"])
            )
        require(
            set(categories)
            == {
                "satisfied_exact_subproposition",
                "exact_negative",
                "complete_provider_domain_absent",
                "incomplete_lookup_unknown",
                "conflicting_facts",
                "unmapped_proposition",
                "inapplicable_declared_evidence",
                "explicit_input_unresolved",
                "not_assessed",
            }
        )

    # The format has one deterministic traversal order, including legitimate
    # source and result backreferences. Reachability also rejects extra records.
    pending = [root]
    reached = {root}
    for ref in pending:
        values = [f.value for f in reversed(declared[ref].fields)]
        while values:
            value = values.pop()
            if value.tag is schema.Tag.REF:
                if value.data not in reached:
                    reached.add(value.data)
                    pending.append(value.data)
            elif value.tag in (schema.Tag.SEQUENCE, schema.Tag.MAPPING):
                values.extend(reversed(value.data))
    require(tuple(pending) == tuple(record.ref for record in document.records))


def evaluate_project_sql_plan_document(document: object) -> Outcome:
    try:
        _check(document)
        assert isinstance(document, schema.Document)
        canonical = _canonical(document)
        return Outcome(Status.OK, document, canonical)
    except _Reject as error:
        return Outcome(
            error.status, record_position=error.record, field_position=error.field
        )
    except (RecursionError, MemoryError, OverflowError):
        return Outcome(Status.RESOURCE_LIMIT)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return Outcome(Status.INVALID_DOCUMENT)


def _input_tree(root):
    """Bound parsed containers before constructing immutable records."""
    pending = [(root, 0, False)]
    active = set()
    total = 0
    nodes = 0
    while pending:
        value, depth, leaving = pending.pop()
        if leaving:
            active.remove(id(value))
            continue
        nodes += 1
        _require(nodes <= schema.MAX_EDGES * 8, Status.RESOURCE_LIMIT)
        _require(depth <= schema.MAX_DEPTH, Status.RESOURCE_LIMIT)
        if value is None or type(value) is bool:
            total += 5
        elif type(value) is int:
            _require(0 <= value < schema.MAX_RECORDS)
            total += 8
        elif type(value) is str:
            _text(value)
            total += len(value.encode("utf-8"))
        else:
            _require(type(value) in (list, dict), Status.INVALID_INPUT)
            _require(id(value) not in active, Status.INVALID_INPUT)
            _require(len(value) <= schema.MAX_EDGES, Status.RESOURCE_LIMIT)
            active.add(id(value))
            pending.append((value, depth, True))
            if type(value) is dict:
                _require(all(type(key) is str for key in value), Status.INVALID_FIELD)
                for key, child in value.items():
                    pending.extend(((key, depth + 1, False), (child, depth + 1, False)))
            else:
                pending.extend((child, depth + 1, False) for child in value)
        _require(total <= schema.MAX_BYTES, Status.RESOURCE_LIMIT)


def _decode_ref(data: Any) -> schema.Ref:
    _require(type(data) is list and len(data) == 2, Status.INVALID_REF)
    result = schema.Ref(cast(str, data[0]), cast(int, data[1]))
    _ref(result)
    return result


def _decode_value(data: Any) -> schema.Value:
    _require(type(data) is list and len(data) == 2)
    try:
        tag = schema.Tag(data[0])
    except (TypeError, ValueError):
        raise _Reject(Status.INVALID_VALUE) from None
    value: Any = data[1]
    if tag is schema.Tag.REF:
        value = _decode_ref(value)
    elif tag in (schema.Tag.SEQUENCE, schema.Tag.MAPPING):
        _require(type(value) is list)
        value = tuple(_decode_value(child) for child in cast(list[Any], value))
    return schema.Value(tag, value)


def decode_project_sql_plan_mapping(value: object) -> Outcome:
    """Validate a parsed mapping; duplicate-key history is not recoverable here."""
    try:
        _input_tree(value)
        _require(
            type(value) is dict and set(value) == {"format", "records"},
            Status.INVALID_DOCUMENT,
        )
        assert isinstance(value, dict)
        value = cast(dict[str, Any], value)
        _require(
            type(value["format"]) is str and value["format"] == schema.FORMAT,
            Status.UNKNOWN_FORMAT,
        )
        rows: Any = value["records"]
        _require(
            type(rows) is list and len(rows) <= schema.MAX_RECORDS,
            Status.RESOURCE_LIMIT,
        )
        records = []
        for row in cast(list[Any], rows):
            _require(
                type(row) is dict and set(row) == {"kind", "ref", "fields"},
                Status.INVALID_RECORD,
            )
            row = cast(dict[str, Any], row)
            _require(type(row["fields"]) is list, Status.INVALID_FIELD)
            fields = []
            for item in row["fields"]:
                _require(
                    type(item) is list and len(item) == 2 and type(item[0]) is str,
                    Status.INVALID_FIELD,
                )
                item = cast(list[Any], item)
                fields.append(schema.Field(item[0], _decode_value(item[1])))
            records.append(
                schema.Record(row["kind"], _decode_ref(row["ref"]), tuple(fields))
            )
        return evaluate_project_sql_plan_document(
            schema.Document(value["format"], tuple(records))
        )
    except _Reject as error:
        return Outcome(
            error.status, record_position=error.record, field_position=error.field
        )
    except (RecursionError, MemoryError, OverflowError):
        return Outcome(Status.RESOURCE_LIMIT)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return Outcome(Status.INVALID_DOCUMENT)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Reject(Status.DUPLICATE_KEY)
        result[key] = value
    return result


def _raw_integer(text):
    _require(len(text) <= 5, Status.RESOURCE_LIMIT)
    _require(re.fullmatch(r"0|[1-9][0-9]*", text) is not None, Status.INVALID_VALUE)
    return int(text)


def _raw_float(_text):
    raise _Reject(Status.INVALID_VALUE)


def _raw_depth(text):
    quoted = escaped = False
    depth = 0
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            _require(depth <= schema.MAX_DEPTH, Status.RESOURCE_LIMIT)
        elif char in "]}":
            depth -= 1


def parse_project_sql_plan_document(raw: bytes | str) -> Outcome:
    """Strict raw JSON boundary; every object-key occurrence is inspected."""
    try:
        _require(type(raw) in (bytes, str), Status.INVALID_INPUT)
        _require(len(raw) <= schema.MAX_BYTES, Status.RESOURCE_LIMIT)
        text = raw.decode("utf-8") if type(raw) is bytes else raw
        assert isinstance(text, str)
        _require(len(text.encode("utf-8")) <= schema.MAX_BYTES, Status.RESOURCE_LIMIT)
        _raw_depth(text)
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_raw_integer,
            parse_float=_raw_float,
            parse_constant=_raw_float,
        )
        return decode_project_sql_plan_mapping(value)
    except _Reject as error:
        return Outcome(error.status)
    except UnicodeError:
        return Outcome(Status.INVALID_UTF8)
    except (RecursionError, MemoryError, OverflowError):
        return Outcome(Status.RESOURCE_LIMIT)
    except (TypeError, ValueError):
        return Outcome(Status.INVALID_JSON)


@dataclass(frozen=True, slots=True, init=False)
class Inspection:
    document: schema.Document
    canonical_bytes: bytes
    records: Mapping[schema.Ref, schema.Record]
    kinds: Mapping[str, tuple[schema.Record, ...]]

    def __init__(self, outcome: Outcome):
        if type(outcome) is not Outcome or outcome.status is not Status.OK:
            raise ValueError("Portable inspection requires a checked document.")
        checked = evaluate_project_sql_plan_document(outcome.document)
        if (
            checked.status is not Status.OK
            or checked.canonical_bytes != outcome.canonical_bytes
        ):
            raise ValueError("Portable inspection requires a consistent document.")
        assert checked.document is not None and checked.canonical_bytes is not None
        object.__setattr__(self, "document", checked.document)
        object.__setattr__(self, "canonical_bytes", checked.canonical_bytes)
        object.__setattr__(
            self,
            "records",
            MappingProxyType({r.ref: r for r in checked.document.records}),
        )
        groups = {}
        for record in checked.document.records:
            groups.setdefault(record.kind, []).append(record)
        object.__setattr__(
            self, "kinds", MappingProxyType({k: tuple(v) for k, v in groups.items()})
        )

    def record(self, ref: schema.Ref) -> schema.Record:
        if (
            type(ref) is not schema.Ref
            or type(ref.position) is not int
            or ref not in self.records
        ):
            raise ValueError("Portable query requires an owned document reference.")
        return self.records[ref]

    def for_kind(self, kind: str) -> tuple[schema.Record, ...]:
        if type(kind) is not str or kind not in schema.RECORD_RULES:
            raise ValueError("Portable query requires a closed record kind.")
        return self.kinds.get(kind, ())
