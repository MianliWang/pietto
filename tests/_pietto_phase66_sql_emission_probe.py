"""Closed installed probe and independent data-only public artifact consumer."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast

CONFIG = 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
VARIANTS = {
    "G_emission_table_bag": ("bag",),
    "H_emission_query_bag": ("bag",),
    "I_emission_table_empty": ("empty",),
    "J_emission_query_empty": ("empty",),
    "K_emission_rejected": ("duplicate_selector", "ordinal_bool", "stale_selector"),
    "L_emission_blocked": (
        "missing_source",
        "bool_domain",
        "decimal_mismatch",
        "timestamp_meaning",
        "uuid_meaning",
        "where_later",
    ),
    "M_named_chain": ("table_bag", "query_bag", "empty", "long_intermediate"),
    "N_imported_chain": ("bag", "empty"),
    "O_named_later": (
        "self_join",
        "union_dag",
        "two_facades",
        "order_ordinary",
        "order_rebound",
        "order_completed",
        "producer_filter",
    ),
}
LABELS = ("display_text", "record_id", "active", "amount", "ratio")
LOGICAL = ("Text", "Int", "Bool", "Decimal", "Float")
CHAIN_LABELS = (*LABELS, "repeated")
CHAIN_LOGICAL = (*LOGICAL, "Int")
CODES = {
    "PIE-B1001": "SOURCE_REALIZATION",
    "PIE-B1002": "REPRESENTATION",
    "PIE-B1003": "UNSUPPORTED_RULE",
    "PIE-B1004": "MISSING_EVIDENCE",
    "PIE-B1005": "PREMISE_CONFLICT",
    "PIE-B1006": "UNFULFILLED_REQUIREMENT",
    "PIE-B1007": "TARGET_RESOURCE",
    "PIE-B1008": "ARTIFACT_INTEGRITY",
}


def encoded(value):
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def fixture(target, case="G_emission_table_bag", variant="bag"):
    if (
        target not in {"postgres", "mysql"}
        or case not in VARIANTS
        or variant not in VARIANTS[case]
    ):
        raise ValueError("unknown emission fixture")
    if case in {"M_named_chain", "N_imported_chain", "O_named_later"}:
        return chain_fixture(target, case, variant)
    kind = (
        "table"
        if case in {"G_emission_table_bag", "I_emission_table_empty"}
        else "query"
    )
    source = f"""shape Row:
    id: Int not null
    flag: Bool nullable
    text: Text not null
    money: Decimal(9, 2) not null
    ratio: Float not null
source rows: Row is {target}.table("opaque.locator.not.sql")
{kind} result:
    from rows
    select:
        display_text = text
        record_id = id
        active = flag
        amount = money
        ratio
"""
    representations = (
        {
            "storage": {"kind": "pg_int8" if target == "postgres" else "my_bigint"},
            "nullable": False,
            "domain": {
                "kind": "int_range",
                "min": "-9007199254740993",
                "max": "9007199254740993",
            },
        },
        {
            "storage": {"kind": "pg_bool" if target == "postgres" else "my_bool01"},
            "nullable": True,
            "domain": {"kind": "bool01"},
        },
        {
            "storage": {"kind": "pg_text"}
            if target == "postgres"
            else {"kind": "my_varchar", "length": 64},
            "nullable": False,
            "domain": {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8" if target == "postgres" else "utf8mb4",
                "collation": "C" if target == "postgres" else "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        },
        {
            "storage": {
                "kind": "pg_numeric" if target == "postgres" else "my_decimal",
                "precision": 9,
                "scale": 2,
            },
            "nullable": False,
            "domain": {"kind": "decimal", "precision": 9, "scale": 2},
        },
        {
            "storage": {"kind": "pg_float8" if target == "postgres" else "my_double"},
            "nullable": False,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
    )
    contract = {
        "format": "pietto.emission-contract.v1",
        "target": {
            "family": target,
            "release": "18.6" if target == "postgres" else "8.4.12",
        },
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": "rows"},
                "relation": {
                    "namespace": "public" if target == "postgres" else "phase66",
                    "name": "phase66 empty é"
                    if variant == "empty"
                    else "phase66 source é",
                },
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": i,
                        "name": name,
                        "column": column,
                        "representation": representation,
                    }
                    for i, (name, column, representation) in enumerate(
                        zip(
                            ("id", "flag", "text", "money", "ratio"),
                            (
                                "order.id",
                                "flag value",
                                'text `"é',
                                "amount value",
                                "ratio value",
                            ),
                            representations,
                            strict=True,
                        )
                    )
                ],
                "premises": [
                    {"key": key, "scope": "source", "value": True}
                    for key in ("row_domain_matches", "read_only_object")
                ],
            }
        ],
        "environment": [
            {
                "key": "client_encoding",
                "scope": "statement",
                "value": "UTF8" if target == "postgres" else "utf8mb4",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
        ],
    }
    description = contract["sources"][0]
    if variant == "duplicate_selector":
        contract["sources"].append(deepcopy(description))
    elif variant == "ordinal_bool":
        description["fields"][0]["ordinal"] = True
    elif variant == "stale_selector":
        description["selector"]["name"] = "absent"
    elif variant == "missing_source":
        contract["sources"] = []
    elif variant == "bool_domain":
        description["fields"][1]["representation"]["domain"] = {
            "kind": "int_range",
            "min": "0",
            "max": "2",
        }
    elif variant == "decimal_mismatch":
        description["fields"][3]["representation"]["storage"]["scale"] = 1
    elif variant in {"timestamp_meaning", "uuid_meaning"}:
        temporal = variant == "timestamp_meaning"
        source = source.replace(
            "ratio: Float", "ratio: " + ("Timestamp" if temporal else "UUID")
        )
        description["fields"][4]["representation"] = {
            "storage": {
                "kind": ("pg_timestamp" if target == "postgres" else "my_datetime"),
                "fractional_seconds": 6,
            }
            if temporal
            else {"kind": "pg_uuid" if target == "postgres" else "my_uuid_bytes"},
            "nullable": False,
            "domain": {"kind": "timestamp"}
            if temporal
            else {"kind": "uuid", "encoding": "standard_bytes"},
        }
    elif variant == "where_later":
        source = source.replace("    select:", "    where id > 0\n    select:")
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if case in {"H_emission_query_bag", "I_emission_table_empty"}
        else "preserve_literals",
    }


def chain_fixture(target, case, variant):
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    text_label = (
        "intermediate_" + "x" * 280 if variant == "long_intermediate" else "TextValue"
    )
    first_kind = "query" if variant == "query_bag" else "table"
    first = f"""{first_kind} first:
    from rows
    select:
        {text_label} = text
        Key = id
        key = money
        FlagValue = flag
        AmountValue = money
        RatioValue = ratio
        omitted = text
"""
    second = f"""table second:
    from first
    select:
        amount2 = key
        txt2 = {text_label}
        id2 = Key
        flag2 = FlagValue
        ratio2 = RatioValue
        again = Key
"""
    final_kind = "table" if variant == "table_bag" else "query"
    final = f"""{final_kind} result:
    from second
    select:
        display_text = txt2
        record_id = id2
        active = flag2
        amount = amount2
        ratio = ratio2
        repeated = again
"""
    source: str | dict[str, str] = header + first + second + final
    description = contract["sources"][0]
    if variant == "empty":
        description["relation"]["name"] = "phase66 empty é"
    if case == "N_imported_chain" or variant == "two_facades":
        source = {
            "a.pietto": header + first + "export:\n    table first\n",
            "b.pietto": 'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n',
            "main.pietto": 'import "b.pietto":\n    table Public as Alias\n'
            + second.replace("from first", "from Alias")
            + final,
        }
        description["selector"]["module"] = "a.pietto"
        if variant != "empty":
            description["relation"]["name"] = "p0"
        if variant == "two_facades":
            source["c.pietto"] = source["b.pietto"]
            source["main.pietto"] = """import "b.pietto":
    table Public as Left
import "c.pietto":
    table Public as Right
query result:
    union all:
        from Left
        from Right
"""
    elif case == "O_named_later":
        if variant == "self_join":
            source = (
                header
                + first
                + """query result:
    from first
    inner join first as r:
        from first
        on first.Key == r.Key
    select:
        id = first.Key
"""
            )
        elif variant == "union_dag":
            chain_text = header + first
            previous = "first"
            for i in range(3):
                chain_text += f"table shared{i}:\n    union all:\n        from {previous}\n        from {previous}\n"
                previous = f"shared{i}"
            source = (
                chain_text
                + f"query result:\n    from {previous}\n    select:\n        Key\n"
            )
        elif variant == "order_ordinary":
            source = (
                header
                + first
                + """query result:
    from first
    select:
        Key
    order by:
        Key
"""
            )
        elif variant == "order_rebound":
            source = (
                header
                + """table upstream:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and w <= 2
query result:
    from upstream
    select:
        id
    order by:
        id
    limit 1
"""
            )
        elif variant == "order_completed":
            source = (
                header
                + f'source other: Row is {target}.table("other")\n'
                + """table upstream:
    from rows
    cross join other as r:
        from rows
    select:
        id = rows.id
query result:
    from upstream
    select:
        id
    order by:
        id
"""
            )
            other = deepcopy(description)
            other["selector"]["name"] = "other"
            contract["sources"].append(other)
        elif variant == "producer_filter":
            source = (
                header
                + first.replace("    select:", "    where id > 0\n    select:")
                + second
                + final
            )
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if variant == "query_bag"
        else "preserve_literals",
    }


def source_bytes(source):
    return source.encode("utf-8") if type(source) is str else encoded(source)


def source_files(source):
    return {"main.pietto": source} if type(source) is str else source


def expected_status(case):
    return (
        "INPUT_REJECTED"
        if case == "K_emission_rejected"
        else "BLOCKED"
        if case in {"L_emission_blocked", "O_named_later"}
        else "VERIFIED"
    )


def generation_inputs(target):
    return [
        {"id": case, "variant": variant, **fixture(target, case, variant)}
        for case, variants in VARIANTS.items()
        for variant in variants
    ]


def _need(value, message="invalid public artifact"):
    if not value:
        raise ValueError(message)


def _keys(value, keys):
    _need(type(value) is dict and set(value) == set(keys))


def _ordinal(value):
    return type(value) is int and value >= 0


def _pairs(items):
    value = {}
    for key, item in items:
        _need(key not in value, "duplicate public field")
        value[key] = item
    return value


def _location(value):
    if value is None:
        return
    _keys(value, ("path", "line", "column", "end_line", "end_column"))
    _need(value["path"] is None or type(value["path"]) is str)
    for key in ("line", "column", "end_line", "end_column"):
        _need(value[key] is None or (type(value[key]) is int and value[key] >= 1))


def _reference(value):
    _keys(value, ("kind", "position"))
    _need(type(value["kind"]) is str and _ordinal(value["position"]))


def _records(value) -> list[dict[str, Any]]:
    _need(type(value) is list and all(type(item) is dict for item in value))
    return cast(list[dict[str, Any]], value)


def _premise_shape(premise, enclosing=None):
    _keys(premise, ("key", "scope", "value"))
    local = {
        "row_domain_matches",
        "read_only_object",
        "value_domain",
        "encoding",
        "collation",
        "padding",
        "comparison_prefix_bytes",
    }
    statement = {
        "session_sql_mode",
        "session_time_zone",
        "client_encoding",
        "identifier_case",
        "parameter_protocol",
        "operator_environment",
        "resource_limits",
    }
    key, scope, value = premise["key"], premise["scope"], premise["value"]
    _need(type(key) is str and key in local | statement)
    if scope == "source":
        _need(enclosing is not None)
        scope = {"kind": "source", "selector": enclosing}
    if scope != "statement":
        _need(type(scope) is dict and scope.get("kind") in {"source", "expression"})
        _keys(
            scope,
            ("kind", "selector")
            if scope["kind"] == "source"
            else ("kind", "source", "site", "context"),
        )
        selector = cast(
            dict[str, Any],
            scope["selector"] if scope["kind"] == "source" else scope["source"],
        )
        _keys(selector, ("module", "kind", "name"))
        _need(
            selector["kind"] == "source"
            and all(
                type(selector[k]) is str and selector[k] for k in ("module", "name")
            )
        )
        if scope["kind"] == "expression":
            _reference(scope["site"])
            _reference(scope["context"])
            _need(key not in {"row_domain_matches", "read_only_object"})
    _need((key in statement) == (scope == "statement"))
    if key in {"row_domain_matches", "read_only_object"}:
        _need(type(value) is bool)
    elif key == "comparison_prefix_bytes":
        _need(_ordinal(value) and value > 0)
    elif key == "resource_limits":
        _need(
            type(value) is dict
            and bool(value)
            and not set(value)
            - {"sql_bytes", "artifact_bytes", "nodes", "parameters", "columns"}
            and all(_ordinal(v) for v in value.values())
        )
    elif key == "value_domain":
        _need(type(value) is dict and type(value.get("kind")) is str)
        value = cast(dict[str, Any], value)
        keys = {
            "int_range": {"kind", "min", "max"},
            "bool01": {"kind"},
            "text": {"kind", "max_characters", "encoding", "collation", "padding"},
            "decimal": {"kind", "precision", "scale"},
            "timestamp": {"kind"},
            "uuid": {"kind", "encoding"},
            "finite_float": {"kind", "format"},
        }
        _need(value["kind"] in keys)
        _keys(value, keys[value["kind"]])
        _need(
            all(
                _ordinal(v)
                if k in {"precision", "scale", "max_characters"}
                else type(v) is str
                for k, v in value.items()
            )
        )
    else:
        _need(type(value) is str and bool(value))
    return key, json.dumps(scope, sort_keys=True), json.dumps(value, sort_keys=True)


def _contract_shape(contract):
    """Independent input-document schema checks, without selector resolution."""
    _keys(contract, ("format", "target", "sources", "environment"))
    selectors = set()
    premises = []
    storage_keys = {
        kind: {"kind"}
        for kind in (
            "pg_int2",
            "pg_int4",
            "pg_int8",
            "pg_bool",
            "pg_text",
            "pg_uuid",
            "pg_float8",
            "my_smallint",
            "my_int",
            "my_bigint",
            "my_bool01",
            "my_uuid_bytes",
            "my_double",
        )
    }
    storage_keys.update(
        {
            "pg_numeric": {"kind", "precision", "scale"},
            "my_decimal": {"kind", "precision", "scale"},
            "my_varchar": {"kind", "length"},
            "pg_timestamp": {"kind", "fractional_seconds"},
            "my_datetime": {"kind", "fractional_seconds"},
        }
    )
    domain_keys = {
        "int_range": {"kind", "min", "max"},
        "bool01": {"kind"},
        "text": {"kind", "max_characters", "encoding", "collation", "padding"},
        "decimal": {"kind", "precision", "scale"},
        "timestamp": {"kind"},
        "uuid": {"kind", "encoding"},
        "finite_float": {"kind", "format"},
    }
    for source in _records(contract["sources"]):
        _keys(source, ("selector", "relation", "scan", "fields", "premises"))
        _keys(source["selector"], ("module", "kind", "name"))
        _need(
            source["selector"]["kind"] == "source"
            and all(
                type(source["selector"][k]) is str and source["selector"][k]
                for k in ("module", "name")
            )
        )
        selector = json.dumps(source["selector"], sort_keys=True)
        _need(selector not in selectors)
        selectors.add(selector)
        _keys(source["relation"], ("namespace", "name"))
        _need(
            source["scan"] == "relation_rows"
            and all(type(v) is str and v for v in source["relation"].values())
        )
        ordinals, columns = set(), set()
        for field in _records(source["fields"]):
            _keys(field, ("ordinal", "name", "column", "representation"))
            _need(
                _ordinal(field["ordinal"])
                and field["ordinal"] not in ordinals
                and type(field["name"]) is str
                and field["name"]
                and type(field["column"]) is str
                and field["column"]
                and field["column"] not in columns
            )
            ordinals.add(field["ordinal"])
            columns.add(field["column"])
            representation = field["representation"]
            _keys(representation, ("storage", "nullable", "domain"))
            _need(
                type(representation["nullable"]) is bool
                or representation["nullable"] == "unknown"
            )
            for part, kinds in (("storage", storage_keys), ("domain", domain_keys)):
                value = representation[part]
                _need(
                    type(value) is dict
                    and type(value.get("kind")) is str
                    and value["kind"] in kinds
                )
                _keys(value, kinds[value["kind"]])
                for key, scalar in value.items():
                    _need(
                        (
                            _ordinal(scalar)
                            if key
                            in {
                                "precision",
                                "scale",
                                "length",
                                "max_characters",
                                "fractional_seconds",
                            }
                            else type(scalar) is str
                        )
                    )
        for premise in _records(source["premises"]):
            premises.append(_premise_shape(premise, source["selector"]))
    for premise in _records(contract["environment"]):
        premises.append(_premise_shape(premise))
    declared = {}
    for key, scope, value in premises:
        _need((key, scope) not in declared or declared[key, scope] == value)
        declared[key, scope] = value


def _public_premises(contract):
    return [
        *contract["environment"],
        *[p for source in contract["sources"] for p in source["premises"]],
    ]


def _identifier_token(text, family, role):
    quote = '"' if family == "postgres" else "`"
    _need(
        re.fullmatch(
            re.escape(quote)
            + "(?:"
            + re.escape(quote * 2)
            + "|[^"
            + re.escape(quote)
            + "])*"
            + re.escape(quote),
            text,
        )
        is not None
    )
    value = text[1:-1].replace(quote * 2, quote)
    _need(bool(value) and "\0" not in value, "unrepresentable identifier")
    if family == "postgres":
        _need(len(value.encode("utf-8")) <= 63, "identifier byte limit")
    else:
        _need(
            len(value) <= (256 if role == "label" else 64), "identifier character limit"
        )
        _need(all(ord(char) <= 0xFFFF for char in value))
        _need(role == "label" or not value.endswith(" "))
        if role in {"namespace", "relation"}:
            _need(not any(char in value for char in (".", "/", "\\")))
    return value


def _named_range_provenance(document):
    modules = {source["module"] for source in document["request"]["sources"]}
    subjects, positions = {}, {}
    roles = {
        "selected_plan": ["selected_owner"],
        "definition": ["definition"],
        "source_port": ["source_port"],
        "result_port": ["result_port"],
        "input_use": ["input_use"],
        "input_port": ["input_port"],
        "projection": ["projection"],
        "export": ["stage_export", "export"],
    }
    associations = {
        "authored_cause",
        "expression_body",
        "field_declaration",
        "type_reference",
        "referenced_declaration",
        "import_item",
        "export_item",
        "source_connector",
    }
    for interval in _records(document["ranges"]):
        _reference(interval["subject"])
        key = interval["subject"]["kind"], interval["subject"]["position"]
        origins = _records(interval["origins"])
        expected = (
            ["definition", "source_descriptor"]
            if key == ("definition", 0)
            else roles.get(key[0])
        )
        _need(
            expected is not None and [o.get("role") for o in origins] == expected,
            "range origin roles",
        )
        _need(
            key not in subjects or subjects[key] == origins,
            "inconsistent repeated-subject provenance",
        )
        subjects[key] = origins
        previous = -1
        for origin in origins:
            _keys(origin, ("position", "role", "sources"))
            _need(_ordinal(origin["position"]) and origin["position"] > previous)
            previous = origin["position"]
            _need(
                origin["position"] not in positions
                or positions[origin["position"]] == key,
                "foreign origin subject",
            )
            positions[origin["position"]] = key
            causes = []
            for source in _records(origin["sources"]):
                _keys(source, ("path", "kind", "location"))
                _need(
                    source["path"] in modules and source["kind"] in associations,
                    "range origin module or association",
                )
                _location(source["location"])
                location = source["location"]
                if location is None:
                    raise ValueError("missing origin location")
                _need(location["path"] == source["path"])
                _need(
                    all(
                        type(location[k]) is int
                        for k in ("line", "column", "end_line", "end_column")
                    )
                )
                _need(
                    (location["line"], location["column"])
                    <= (location["end_line"], location["end_column"])
                )
                if source["kind"] == "authored_cause":
                    causes.append(location)
            _need(len(causes) == 1, "missing authored range cause")
    return subjects


def _decode_named_sql(document, fields, limits):
    """Read the finite WITH grammar from bytes; never import compiler machinery."""
    sql = document["sql"].encode("utf-8")
    provenance = _named_range_provenance(document)
    expected_case = (
        "quoted_exact"
        if document["target"]["family"] == "postgres"
        else "lower_case_table_names=0"
    )
    cases = [
        p["value"]
        for p in _public_premises(document["request"]["contract"])
        if p["key"] == "identifier_case" and p["scope"] == "statement"
    ]
    _need(bool(cases) and all(value == expected_case for value in cases))
    tokens = []
    offset = 0
    for interval in _records(document["ranges"]):
        _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
        _need(type(interval["start"]) is int and type(interval["end"]) is int)
        _need(interval["start"] == offset < interval["end"] <= len(sql))
        text = sql[offset : interval["end"]].decode("utf-8")
        _need(interval["kind"] in {"identifier", "syntax"})
        if interval["kind"] == "identifier":
            text = _identifier_token(
                text, document["target"]["family"], interval["role"]
            )
        tokens.append((interval["kind"], interval["role"], text, interval["subject"]))
        offset = interval["end"]
    _need(offset == len(sql))
    cursor = 0

    def reference(kind, position):
        return {"kind": kind, "position": position}

    def origins(ref):
        return provenance[ref["kind"], ref["position"]]

    def cause(ref):
        locations = [
            next(s["location"] for s in o["sources"] if s["kind"] == "authored_cause")
            for o in origins(ref)
        ]
        _need(
            all(location == locations[0] for location in locations),
            "conflicting subject causes",
        )
        return locations[0]

    def within(child, parent):
        return child["path"] == parent["path"] and (
            parent["line"],
            parent["column"],
        ) <= (child["line"], child["column"]) <= (
            child["end_line"],
            child["end_column"],
        ) <= (parent["end_line"], parent["end_column"])

    def take(kind, role, text=None, subject=None):
        nonlocal cursor
        _need(cursor < len(tokens), "missing SQL token")
        actual_kind, actual_role, actual_text, actual_subject = tokens[cursor]
        cursor += 1
        _need((actual_kind, actual_role) == (kind, role))
        _need(text is None or actual_text == text)
        _need(subject is None or actual_subject == subject)
        return actual_text, actual_subject

    def peek():
        return tokens[cursor][1] if cursor < len(tokens) else None

    ctes = {}
    bodies = []
    projection_base = 0
    input_base = 0
    physical_count = 0
    description = fields[0][1]
    originals = Counter()

    def select(owner, final=False):
        nonlocal projection_base, input_base, physical_count
        take("syntax", "select", "SELECT ", owner)
        selected = []
        while True:
            i = len(selected)
            projection = reference("projection", projection_base + i)
            export = reference("export", projection_base + i)
            if i:
                take("syntax", "separator", ", ", projection)
            alias, input_ref = take("identifier", "column_scope")
            _need(input_ref["kind"] == "input_port")
            take("syntax", "qualifier", ".", projection)
            name, terminal = take("identifier", "column")
            take("syntax", "alias", " AS ", projection)
            label, _ = take("identifier", "label", None if final else f"c{i}", export)
            selected.append(
                (alias, input_ref, name, terminal, label, projection, export)
            )
            if peek() != "separator":
                break
        _, producer_ref = take("syntax", "from", " FROM ")
        _need(producer_ref["kind"] == "definition")
        producer_name = None
        if peek() == "namespace":
            _need(producer_ref == reference("definition", 0))
            take(
                "identifier",
                "namespace",
                description["relation"]["namespace"],
                producer_ref,
            )
            take("syntax", "qualifier", ".", producer_ref)
            take(
                "identifier", "relation", description["relation"]["name"], producer_ref
            )
            producer_columns = [
                {
                    "name": f["column"],
                    "terminal": reference("source_port", f["ordinal"]),
                    "field": f,
                }
                for f in description["fields"]
            ]
            physical_count += 1
        else:
            producer_name, _ = take("identifier", "cte_reference", subject=producer_ref)
            _need(producer_name in ctes, "forward or captured CTE reference")
            _need(ctes[producer_name]["definition"] == producer_ref)
            producer_columns = ctes[producer_name]["columns"]
        use = reference("input_use", len(bodies))
        take("syntax", "alias", " AS ", use)
        alias, _ = take("identifier", "relation_scope", f"s{len(bodies)}", use)
        consumer_cause, producer_cause, use_cause = (
            cause(owner),
            cause(producer_ref),
            cause(use),
        )
        _need(within(use_cause, consumer_cause), "use outside consumer source scope")
        route = origins(use)[0]["sources"]
        _need(
            any(
                s["kind"] == "referenced_declaration"
                and s["location"] == producer_cause
                for s in route
            ),
            "missing immediate producer declaration",
        )
        hops = [s for s in route if s["kind"] in {"import_item", "export_item"}]
        module = consumer_cause["path"]
        _need(len(hops) % 2 == 0)
        for imported, exported in zip(hops[::2], hops[1::2], strict=True):
            _need(
                imported["kind"] == "import_item"
                and imported["path"] == module
                and exported["kind"] == "export_item",
                "broken import provenance trail",
            )
            module = exported["path"]
        _need(module == producer_cause["path"], "missing import provenance trail")
        names = {
            column["name"]: (i, column) for i, column in enumerate(producer_columns)
        }
        _need(len(names) == len(producer_columns))
        output = []
        for i, (
            qualifier,
            input_ref,
            name,
            terminal,
            label,
            projection,
            export,
        ) in enumerate(selected):
            _need(qualifier == alias and name in names)
            index, producer_column = names[name]
            _need(input_ref == reference("input_port", input_base + index))
            _need(terminal == producer_column["terminal"], "wrong immediate terminal")
            _need(cause(input_ref) == use_cause, "input port outside its use")
            _need(
                cause(terminal) == producer_cause,
                "terminal outside producer source scope",
            )
            _need(
                cause(export) == cause(projection)
                and within(cause(projection), consumer_cause),
                "projection/export source correspondence",
            )
            field = producer_column["field"]
            if final:
                _need(i < len(fields))
                public = fields[i][0]
                correspondence = public["correspondence"]
                _need(label == public["label"] and field is fields[i][2])
                _need(correspondence["input_port"] == input_ref)
                _need(
                    correspondence["projection"] == projection
                    and correspondence["export"] == export
                )
                _need(
                    correspondence["source_port"]
                    == reference("source_port", field["ordinal"])
                )
            output.append(
                {
                    "name": label,
                    "terminal": reference("result_port", projection_base + i),
                    "field": field,
                }
            )
        _need(not final or len(output) == len(fields))
        n = len(output)
        originals.update(
            {
                "export_representation": n,
                "expression": n,
                "stage_value": len(producer_columns),
                "scope": 1,
                "result": 2 * n,
            }
        )
        bodies.append(
            {
                "producer": producer_name,
                "producer_columns": producer_columns,
                "use": use,
                "columns": output,
            }
        )
        projection_base += n
        input_base += len(producer_columns)
        return output

    take("syntax", "with", "WITH ", reference("selected_plan", 0))
    _need(
        cause(reference("selected_plan", 0))["path"]
        == document["request"]["owner"]["module"]
    )
    _need(
        cause(reference("definition", 0))["path"] == description["selector"]["module"]
    )
    while True:
        index = len(ctes)
        definition = reference("definition", index + 1)
        if index:
            take("syntax", "cte_separator", ", ", definition)
        name, _ = take("identifier", "cte_name", f"p{index}", definition)
        take("syntax", "cte_columns_open", " (", definition)
        header = []
        while True:
            position = len(header)
            terminal = reference("result_port", projection_base + position)
            if position:
                take("syntax", "terminal_separator", ", ", terminal)
            take("identifier", "terminal_column", f"c{position}", terminal)
            _need(
                cause(terminal) == cause(definition),
                "CTE header outside defining source",
            )
            header.append(terminal)
            if peek() != "terminal_separator":
                break
        take("syntax", "cte_body_open", ") AS (", definition)
        output = select(definition)
        _need(header == [c["terminal"] for c in output])
        take("syntax", "cte_body_close", ")", definition)
        ctes[name] = {
            "definition": definition,
            "columns": output,
            "producer": bodies[-1]["producer"],
        }
        if peek() != "cte_separator":
            break
    take("syntax", "with_body", " ", reference("definition", len(ctes) + 1))
    _need(
        cause(reference("definition", len(ctes) + 1))
        == cause(reference("selected_plan", 0))
    )
    select(reference("selected_plan", 0), final=True)
    _need(cursor == len(tokens) and physical_count == 1)
    visited = set()
    producer = bodies[-1]["producer"]
    while producer is not None:
        _need(producer not in visited)
        visited.add(producer)
        producer = ctes[producer]["producer"]
    _need(visited == set(ctes), "unreferenced SQL definition")
    originals["source_realization"] = 1
    generated = []
    for cte in ctes.values():
        generated.append(("cte_definition", "R03", cte["definition"]))
        generated.extend(
            ("terminal_column", "R03", c["terminal"]) for c in cte["columns"]
        )
    for body in bodies:
        if body["producer"] is None:
            generated.append(("qualified_scan", "R01", None))
            generated.extend(
                ("source_representation", "R02", None) for _ in description["fields"]
            )
        else:
            generated.append(("named_use", "R03", body["use"]))
            generated.extend(
                ("immediate_terminal", "R03", c["terminal"])
                for c in body["producer_columns"]
            )
        generated.extend(("field_projection", "R02", None) for _ in body["columns"])
        generated.append(("read_only_select_bytes", "R23", None))
    generated.append(("nonrecursive_with_bytes", "R23", None))
    _need(all(len(body["columns"]) <= limits["columns"] for body in bodies))
    _need(
        3 * len(bodies)
        + 2 * projection_base
        + 2 * len(ctes)
        + sum(len(c["columns"]) for c in ctes.values())
        <= limits["nodes"]
    )
    return originals, generated


def decode_public(data: bytes) -> dict[str, Any]:
    """Validate data only. A decoded document grants no compiler authority."""
    _need(type(data) is bytes and len(data) <= 16 * 1024 * 1024)
    try:
        document: dict[str, Any] = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
        _need(
            type(document) is dict
            and document.get("format") == "pietto.sql-emission.v1"
        )
        status = document.get("status")
        _need(status in {"VERIFIED", "INPUT_REJECTED", "BLOCKED"})
        _need(type(document.get("diagnostics")) is list)
        for diagnostic in document["diagnostics"]:
            _keys(diagnostic, ("code", "severity", "message", "location", "suggestion"))
            _need(
                type(diagnostic["code"]) is str
                and re.fullmatch(r"PIE-[PSIBR][0-9]{4}", diagnostic["code"]) is not None
            )
            _need(
                diagnostic["severity"] in {"error", "warning", "info"}
                and type(diagnostic["message"]) is str
            )
            _need(
                diagnostic["suggestion"] is None
                or type(diagnostic["suggestion"]) is str
            )
            _location(diagnostic["location"])
        if status != "VERIFIED":
            _keys(
                document,
                (
                    "format",
                    "status",
                    "artifact",
                    "blockers",
                    "diagnostics",
                    "cli_errors",
                ),
            )
            _need(
                document["artifact"] is None
                and type(document["blockers"]) is list
                and type(document["cli_errors"]) is list
            )
            for blocker in _records(document["blockers"]):
                _keys(blocker, ("code", "reason", "subject", "location", "related"))
                _need(
                    type(blocker["code"]) is str
                    and CODES.get(blocker["code"]) == blocker["reason"]
                )
                _keys(blocker["subject"], ("reference", "detail"))
                _reference(blocker["subject"]["reference"])
                _need(type(blocker["subject"]["detail"]) is str)
                _location(blocker["location"])
                _need(type(blocker["related"]) is list)
                for location in blocker["related"]:
                    _location(location)
            for error in _records(document["cli_errors"]):
                _keys(error, ("kind", "message", "path"))
                _need(
                    error["kind"] in {"emission_contract_schema", "emission_selector"}
                    and type(error["message"]) is str
                )
                _need(error["path"] is None or type(error["path"]) is str)
            _need(bool(document["cli_errors"]) == (status == "INPUT_REJECTED"))
            _need(
                status == "INPUT_REJECTED"
                or document["blockers"]
                or any(d["severity"] == "error" for d in document["diagnostics"])
            )
            return document
        _keys(
            document,
            (
                "format",
                "status",
                "target",
                "request",
                "sql",
                "fixed_values",
                "parameter_uses",
                "columns",
                "ranges",
                "requirements",
                "diagnostics",
            ),
        )
        _need(document["fixed_values"] == [] and document["parameter_uses"] == [])
        _need(not any(d["severity"] == "error" for d in document["diagnostics"]))
        target, request = document["target"], document["request"]
        _keys(target, ("family", "release", "environment"))
        _need(
            (target["family"], target["release"])
            in {("postgres", "18.6"), ("mysql", "8.4.12")}
        )
        _keys(request, ("owner", "sources", "contract", "literal_policy"))
        _keys(request["owner"], ("module", "kind", "name"))
        _need(request["owner"]["kind"] in {"table", "query"})
        _need(
            all(
                type(request["owner"][k]) is str and request["owner"][k]
                for k in ("module", "name")
            )
        )
        _need(request["literal_policy"] in {"preserve_literals", "bind_safe_literals"})
        _need(type(request["sources"]) is list and bool(request["sources"]))
        modules = set()
        for source in request["sources"]:
            _keys(source, ("module", "sha256", "byte_count"))
            _need(
                type(source["module"]) is str
                and bool(source["module"])
                and source["module"] not in modules
                and type(source["sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None
                and _ordinal(source["byte_count"])
            )
            modules.add(source["module"])
        _need(request["owner"]["module"] in [s["module"] for s in request["sources"]])
        contract = request["contract"]
        _contract_shape(contract)
        _keys(contract, ("format", "target", "sources", "environment"))
        _need(
            contract["format"] == "pietto.emission-contract.v1"
            and contract["target"]
            == {"family": target["family"], "release": target["release"]}
            and contract["environment"] == target["environment"]
        )
        _need(
            type(document["sql"]) is str
            and type(document["columns"]) is list
            and bool(document["columns"])
        )
        sql = document["sql"].encode("utf-8")
        named = sql.startswith(b"WITH ")
        all_premises = _public_premises(contract)
        limits = {
            "sql_bytes": 8 * 1024 * 1024,
            "artifact_bytes": 16 * 1024 * 1024,
            "nodes": 32768,
            "parameters": 32768,
            "columns": 1664 if target["family"] == "postgres" else 4096,
        }
        for premise in all_premises:
            if premise["key"] == "resource_limits" and premise["scope"] == "statement":
                for key, value in premise["value"].items():
                    limits[key] = min(limits[key], value)
        _need(len(sql) <= limits["sql_bytes"] and len(data) <= limits["artifact_bytes"])
        _need(len(document["columns"]) <= limits["columns"])
        _need(
            type(document["ranges"]) is list and type(document["requirements"]) is list
        )
        sources = _records(contract["sources"])
        _need(bool(sources))
        fields = []
        for ordinal, column in enumerate(document["columns"]):
            _keys(
                column,
                (
                    "ordinal",
                    "label",
                    "logical_type",
                    "nullable",
                    "representation",
                    "correspondence",
                ),
            )
            _need(
                type(column["ordinal"]) is int
                and column["ordinal"] == ordinal
                and type(column["label"]) is str
                and bool(column["label"])
            )
            _keys(column["logical_type"], ("kind", "name", "parameters"))
            _need(
                column["logical_type"]["kind"] == "builtin"
                and column["logical_type"]["name"]
                in {"Int", "Bool", "Text", "Decimal", "Float"}
            )
            correspondence = column["correspondence"]
            _keys(
                correspondence,
                (
                    "source",
                    "field",
                    "source_port",
                    "input_port",
                    "export",
                    "projection",
                    "sql_symbol",
                ),
            )
            _need(
                _ordinal(correspondence["field"])
                and type(correspondence["sql_symbol"]) is int
                and correspondence["sql_symbol"] == ordinal + 1
            )
            for key in ("source_port", "input_port", "export", "projection"):
                _reference(correspondence[key])
                _need(correspondence[key]["kind"] == key)
                if not named or key == "source_port":
                    _need(
                        correspondence[key]["position"]
                        == (
                            correspondence["field"]
                            if key in {"source_port", "input_port"}
                            else ordinal
                        )
                    )
            matches = [s for s in sources if s["selector"] == correspondence["source"]]
            _need(len(matches) == 1)
            description = matches[0]
            _keys(description, ("selector", "relation", "scan", "fields", "premises"))
            _need(
                description["scan"] == "relation_rows"
                and type(description["fields"]) is list
            )
            _need(correspondence["field"] < len(description["fields"]))
            field = description["fields"][correspondence["field"]]
            _keys(field, ("ordinal", "name", "column", "representation"))
            _need(
                field["ordinal"] == correspondence["field"]
                and column["representation"] == field["representation"]
            )
            _keys(column["representation"], ("storage", "nullable", "domain"))
            logical_name = column["logical_type"]["name"]
            allowed = {
                "Int": (
                    {
                        "pg_int2",
                        "pg_int4",
                        "pg_int8",
                        "my_smallint",
                        "my_int",
                        "my_bigint",
                    },
                    "int_range",
                ),
                "Bool": ({"pg_bool", "my_bool01"}, "bool01"),
                "Text": ({"pg_text", "my_varchar"}, "text"),
                "Decimal": ({"pg_numeric", "my_decimal"}, "decimal"),
                "Float": ({"pg_float8", "my_double"}, "finite_float"),
            }
            storage = column["representation"]["storage"]["kind"]
            _need(
                storage in allowed[logical_name][0]
                and column["representation"]["domain"]["kind"]
                == allowed[logical_name][1]
                and storage.startswith(
                    "pg_" if target["family"] == "postgres" else "my_"
                )
            )
            _need(
                column["nullable"] == column["representation"]["nullable"]
                and (
                    type(column["nullable"]) is bool or column["nullable"] == "unknown"
                )
            )
            if column["logical_type"]["name"] == "Decimal":
                parameters = column["logical_type"]["parameters"]
                _keys(parameters, ("precision", "scale"))
                _need(
                    all(type(parameters[k]) is int for k in parameters)
                    and 1 <= parameters["precision"] <= 65
                    and 0 <= parameters["scale"] <= min(parameters["precision"], 30)
                )
                _need(
                    all(
                        column["representation"][part][k] == parameters[k]
                        for part in ("storage", "domain")
                        for k in parameters
                    )
                )
            else:
                _need(column["logical_type"]["parameters"] is None)
            fields.append((column, description, field))
        _need(all(item[1] is fields[0][1] for item in fields))
        ranges = iter(document["ranges"])
        offset = 0

        def token(kind, role, expected, subject):
            nonlocal offset
            interval = next(ranges)
            _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
            _need(
                type(interval["start"]) is int
                and type(interval["end"]) is int
                and interval["start"] == offset
                and offset < interval["end"] <= len(sql)
            )
            _need((interval["kind"], interval["role"]) == (kind, role))
            _reference(interval["subject"])
            _need(interval["subject"] == subject)
            _need(type(interval["origins"]) is list)
            for origin in interval["origins"]:
                _keys(origin, ("position", "role", "sources"))
                _need(
                    _ordinal(origin["position"])
                    and type(origin["role"]) is str
                    and type(origin["sources"]) is list
                )
                for source in origin["sources"]:
                    _keys(source, ("path", "kind", "location"))
                    _need(type(source["path"]) is str and type(source["kind"]) is str)
                    _location(source["location"])
            text = sql[offset : interval["end"]].decode("utf-8")
            if kind == "identifier":
                _need(_identifier_token(text, target["family"], role) == expected)
            else:
                _need(text == expected)
            offset = interval["end"]

        if not named:
            token(
                "syntax", "select", "SELECT ", {"kind": "selected_plan", "position": 0}
            )
            for i, (column, description, field) in enumerate(fields):
                if i:
                    token(
                        "syntax",
                        "separator",
                        ", ",
                        column["correspondence"]["projection"],
                    )
                token(
                    "identifier",
                    "column_scope",
                    "s0",
                    column["correspondence"]["input_port"],
                )
                token(
                    "syntax", "qualifier", ".", column["correspondence"]["projection"]
                )
                token(
                    "identifier",
                    "column",
                    field["column"],
                    column["correspondence"]["source_port"],
                )
                token("syntax", "alias", " AS ", column["correspondence"]["projection"])
                token(
                    "identifier",
                    "label",
                    column["label"],
                    column["correspondence"]["export"],
                )
            definition = {"kind": "definition", "position": 0}
            use = {"kind": "input_use", "position": 0}
            token("syntax", "from", " FROM ", definition)
            token(
                "identifier",
                "namespace",
                fields[0][1]["relation"]["namespace"],
                definition,
            )
            token("syntax", "qualifier", ".", definition)
            token(
                "identifier", "relation", fields[0][1]["relation"]["name"], definition
            )
            token("syntax", "alias", " AS ", use)
            token("identifier", "relation_scope", "s0", use)
            _need(next(ranges, None) is None and offset == len(sql))
        original, generated = [], []
        for requirement in _records(document["requirements"]):
            _keys(
                requirement,
                (
                    "denominator",
                    "ordinal",
                    "kind",
                    "subject",
                    "rule",
                    "disposition",
                    "premises",
                    "evidence",
                ),
            )
            _need(
                requirement["denominator"] in {"original", "generated"}
                and requirement["rule"]
                in ({"R01", "R02", "R03", "R23"} if named else {"R01", "R02", "R23"})
                and requirement["disposition"] == "checked_rule"
            )
            _reference(requirement["subject"])
            _need(
                type(requirement["premises"]) is list
                and all(_ordinal(v) for v in requirement["premises"])
                and type(requirement["evidence"]) is list
            )
            bucket = original if requirement["denominator"] == "original" else generated
            _need(
                type(requirement["ordinal"]) is int
                and requirement["ordinal"] == len(bucket)
            )
            bucket.append(requirement)
        if not named:
            n = len(fields)
            _need(3 + 2 * n <= limits["nodes"])
            expected_original = Counter(
                {
                    "source_realization": 1,
                    "export_representation": n,
                    "expression": n,
                    "stage_value": len(fields[0][1]["fields"]),
                    "scope": 1,
                    "result": 2 * n,
                }
            )
            expected_generated = [
                ("qualified_scan", "R01", None),
                *[("source_representation", "R02", None)] * len(fields[0][1]["fields"]),
                *[("field_projection", "R02", None)] * n,
                ("read_only_select_bytes", "R23", None),
            ]
        else:
            expected_original, expected_generated = _decode_named_sql(
                document, fields, limits
            )
        _need(
            Counter(r["kind"] for r in original) == expected_original,
            "original requirement denominator",
        )
        for requirement in original:
            expected_rule = (
                "R03"
                if named and requirement["kind"] == "scope"
                else "R01"
                if requirement["kind"] in {"source_realization", "expression", "scope"}
                else "R02"
            )
            _need(requirement["rule"] == expected_rule)
        _need(
            len(generated) == len(expected_generated),
            "generated requirement denominator",
        )
        naming = [
            i
            for i, premise in enumerate(all_premises)
            if premise["key"] == "identifier_case" and premise["scope"] == "statement"
        ]
        for i, (actual, (kind, rule, subject)) in enumerate(
            zip(generated, expected_generated, strict=True)
        ):
            _need(actual["kind"] == kind and actual["rule"] == rule)
            _need(all(position < len(all_premises) for position in actual["premises"]))
            if kind in {
                "cte_definition",
                "terminal_column",
                "named_use",
                "immediate_terminal",
            }:
                _need(actual["premises"] == naming)
            _need(
                actual["subject"]
                == (subject if subject is not None else {"kind": kind, "position": i})
            )
        return document
    except (
        KeyError,
        IndexError,
        TypeError,
        StopIteration,
        UnicodeError,
        RecursionError,
    ) as error:
        raise ValueError("malformed public emission artifact") from error


def build_case(
    directory, source, contract, policy="preserve_literals", *, target_request=None
):
    # Imported only in the generation child or explicit offline behavior tests.
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
    from pietto._project.project_sql_emission import emit_project_sql

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(CONFIG)
    for name, content in sorted(source_files(source).items()):
        if Path(name).name != name or not name.endswith(".pietto"):
            raise ValueError("closed fixture module path required")
        (directory / name).write_text(content, encoding="utf-8")
    parsed = check_project_parse_only(directory)
    if not parsed.ok:
        raise ValueError("probe source failed parsing")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    if type(completed) is not ProjectConcreteCompletedSemanticResult:
        raise ValueError("probe completion has no concrete root")
    ir = build_project_query_block_ir(completed)
    checked_ir = verify_project_query_block_ir(ir)
    bundle = build_project_query_block_ir_analysis_bundle(checked_ir)
    owners = tuple(owner for owner in ir.owners if owner.definition.name == "result")
    if len(owners) != 1:
        raise ValueError("probe selection is not unique")
    selected = owners[0]
    literal_policy = ProjectSQLLiteralPolicy(policy)
    plan = build_project_sql_plan(
        completed, bundle, selected, literal_policy=literal_policy
    )
    checked = verify_project_sql_plan(
        plan, completed, bundle, selected, literal_policy=literal_policy
    )
    return checked, emit_project_sql(
        checked,
        contract.encode() if type(contract) is str else contract,
        target_request=target_request,
    )


def main():
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    if (
        len(sys.argv) != 2
        or sys.argv[1] not in {"postgres", "mysql"}
        or sys.flags.isolated != 1
    ):
        raise ValueError("closed isolated emission probe required")
    target = sys.argv[1]
    records = []
    for item in generation_inputs(target):
        with TemporaryDirectory(prefix="emission-", dir=Path.cwd()) as scratch:
            _, outcome = build_case(
                Path(scratch), item["source"], item["contract"], item["policy"]
            )
            data = serialize_project_sql_emission(outcome)
            records.append(
                {
                    "id": item["id"],
                    "variant": item["variant"],
                    "source_sha256": hashlib.sha256(
                        source_bytes(item["source"])
                    ).hexdigest(),
                    "contract_sha256": hashlib.sha256(
                        item["contract"].encode()
                    ).hexdigest(),
                    "public": data.decode(),
                    "public_sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    origins = {}
    prefix = Path(sys.prefix).resolve()
    for name, module in tuple(sys.modules.items()):
        if name == "pietto" or name.startswith("pietto."):
            filename = getattr(module, "__file__", None)
            if filename:
                path = Path(filename).resolve()
                if not path.is_relative_to(prefix) or "site-packages" not in path.parts:
                    raise ValueError("checkout production import")
                index = path.parts.index("site-packages")
                origins[name] = {
                    "member": "/".join(path.parts[index + 1 :]),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
    print(
        encoded(
            {
                "records": records,
                "origins": origins,
                "isolated": sys.flags.isolated,
                "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "config_sha256": hashlib.sha256(CONFIG.encode()).hexdigest(),
            }
        ).decode(),
        end="",
    )


if __name__ == "__main__":
    main()
