"""Closed installed probe and independent data-only public artifact consumer."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
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
    "P_native_identifiers": (
        "preserve",
        "bind",
        "plain_preserve",
        "plain_bind",
        "named_preserve",
        "named_bind",
        "empty_preserve",
        "empty_bind",
    ),
    "R_fixed_direct": (
        "table_preserve",
        "table_bind",
        "query_preserve",
        "query_bind",
        "empty_preserve",
        "empty_bind",
    ),
    "S_fixed_named": (
        "named_preserve",
        "named_bind",
        "imported_preserve",
        "imported_bind",
        "empty_preserve",
        "empty_bind",
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
    if case == "P_native_identifiers":
        return native_fixture(target, variant)
    if case in {"R_fixed_direct", "S_fixed_named"}:
        return fixed_fixture(target, case, variant)
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


def native_fixture(target, variant):
    base = fixture(target)
    contract = json.loads(base["contract"])
    description = contract["sources"][0]
    description["relation"]["name"] = (
        "phase66 native empty" if variant.startswith("empty") else "phase66 native"
    )
    original = description["fields"][0]["representation"]
    description["fields"] = [
        {
            "ordinal": i,
            "name": name,
            "column": column,
            "representation": {
                "storage": deepcopy(original["storage"]),
                "nullable": i == 3,
                "domain": {"kind": "int_range", "min": "0", "max": "99"},
            },
        }
        for i, (name, column) in enumerate(
            zip(
                ("id", "decoy", "plain", "neighbor"),
                ('%s"', '?"', "%s", "neighbor"),
                strict=True,
            )
        )
    ]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    source = f"""shape Row:
    id: Int not null
    decoy: Int not null
    plain: Int not null
    neighbor: Int nullable
source rows: Row is {target}.table("opaque")
"""
    if variant.startswith("named"):
        source += """table first:
    from rows
    select:
        kept = id
query result:
    from first
    select:
        id = kept
"""
    else:
        source += "query result:\n    from rows\n    select:\n        id = "
        source += "plain\n" if variant.startswith("plain") else "id\n"
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if variant.endswith("bind")
        else "preserve_literals",
    }


FIXED_LABELS = (
    "id",
    "neighbor",
    "truth",
    "lie",
    "one",
    "real_one",
    "zero",
    "positive",
    "negative",
    "positive_zero",
    "negative_zero",
    "fraction",
    "big",
    "equal_a",
    "equal_b",
    "empty_text",
    "trailing_text",
    "unicode_text",
    "markers",
    "escaped",
)
FIXED_TAGS = (
    "Int",
    "Int",
    "Bool",
    "Bool",
    "Int",
    "Float",
    "Int",
    "Int",
    "Int",
    "Float",
    "Float",
    "Float",
    "Int",
    "Int",
    "Int",
    "Text",
    "Text",
    "Text",
    "Text",
    "Text",
)
FIXED_NAMED_LABELS = ("id", "neighbor", "literal", "again", "ratio", "zero", "added")
FIXED_NAMED_TAGS = ("Int", "Int", "Int", "Int", "Float", "Float", "Text")


def fixed_fixture(target, case, variant):
    base = native_fixture(
        target, "empty_preserve" if variant.startswith("empty") else "preserve"
    )
    contract = json.loads(base["contract"])
    bound = variant.endswith("bind")
    if bound:
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = base["source"].split("query result:", 1)[0]
    if case == "R_fixed_direct":
        expressions = (
            "id",
            "neighbor",
            "true",
            "false",
            "1",
            "1.0",
            "0",
            "+2",
            "-2",
            "+0.0",
            "-0.0",
            "-1.5",
            "9007199254740993",
            "17",
            "17",
            json.dumps("", ensure_ascii=False),
            json.dumps("a  ", ensure_ascii=False),
            json.dumps("雪e\u0301😀", ensure_ascii=False),
            json.dumps("? %s $1", ensure_ascii=False),
            json.dumps("\"'\\\n", ensure_ascii=False),
        )
        kind = "table" if variant.startswith("table") else "query"
        source = header + f"{kind} result:\n    from rows\n    select:\n"
        source += "".join(
            f"        {label} = {expression}\n"
            for label, expression in zip(FIXED_LABELS, expressions, strict=True)
        )
    else:
        first = """table first:
    from rows
    select:
        id
        neighbor
        base = 17
        unused = true
        zero = -0.0
"""
        second = """table second:
    from first
    select:
        record_id = id
        neighbor
        renamed = base
        repeated = base
        ratio = 1.5
        zero
"""
        final = """query result:
    from second
    select:
        id = record_id
        neighbor
        literal = renamed
        again = repeated
        ratio
        zero
        added = "雪?%s $1"
"""
        source = header + first + second + final
        if variant.startswith("imported"):
            source = {
                "a.pietto": header + first + "export:\n    table first\n",
                "b.pietto": 'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n',
                "main.pietto": 'import "b.pietto":\n    table Public as Alias\n'
                + second.replace("from first", "from Alias")
                + final,
            }
            contract["sources"][0]["selector"]["module"] = "a.pietto"
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals" if bound else "preserve_literals",
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


def _field_compatibility(representation, family):
    """One source-field logical/storage/domain/NULL law shared by both decode routes."""
    _keys(representation, ("storage", "nullable", "domain"))
    _need(
        type(representation["nullable"]) is bool
        or representation["nullable"] == "unknown",
        "unsupported NULL posture",
    )
    storage, domain = representation["storage"], representation["domain"]
    widths = {
        "pg_int2": 16,
        "pg_int4": 32,
        "pg_int8": 64,
        "my_smallint": 16,
        "my_int": 32,
        "my_bigint": 64,
    }
    tags = {
        **dict.fromkeys(widths, "Int"),
        "pg_bool": "Bool",
        "my_bool01": "Bool",
        "pg_text": "Text",
        "my_varchar": "Text",
        "pg_numeric": "Decimal",
        "my_decimal": "Decimal",
        "pg_float8": "Float",
        "my_double": "Float",
    }
    kind = storage["kind"]
    _need(
        kind in tags and kind.startswith("pg_" if family == "postgres" else "my_"),
        "unsupported physical source storage",
    )
    tag = tags[kind]
    _need(
        domain["kind"]
        == {
            "Int": "int_range",
            "Bool": "bool01",
            "Text": "text",
            "Decimal": "decimal",
            "Float": "finite_float",
        }[tag],
        "physical storage and value domain disagree",
    )
    parameters = None
    if tag == "Int":
        limit = 1 << (widths[kind] - 1)
        bounds = []
        for key in ("min", "max"):
            spelling = domain[key]
            _need(
                type(spelling) is str
                and re.fullmatch(r"-?(0|[1-9][0-9]*)", spelling) is not None,
                "noncanonical declared range",
            )
            bound = int(spelling)
            _need(-limit <= bound < limit, "declared range outside signed storage")
            bounds.append(bound)
        _need(bounds[0] <= bounds[1], "empty declared range")
    elif tag == "Text":
        _need(
            domain["encoding"] == ("UTF8" if family == "postgres" else "utf8mb4")
            and domain["collation"]
            == ("C" if family == "postgres" else "utf8mb4_0900_bin")
            and domain["padding"] == "NO PAD",
            "unsupported text domain",
        )
        _need(
            _ordinal(domain["max_characters"]) and domain["max_characters"] > 0,
            "empty declared text length",
        )
        _need(
            kind != "my_varchar"
            or (
                _ordinal(storage["length"])
                and domain["max_characters"] <= storage["length"]
            ),
            "declared text length outside storage",
        )
    elif tag == "Decimal":
        parameters = {k: domain[k] for k in ("precision", "scale")}
        _need(
            all(_ordinal(v) for v in parameters.values())
            and 1 <= parameters["precision"] <= 65
            and 0 <= parameters["scale"] <= min(parameters["precision"], 30),
            "unsupported decimal precision or scale",
        )
        _need(
            all(storage[k] == parameters[k] for k in parameters),
            "decimal storage and value domain disagree",
        )
    elif tag == "Float":
        _need(domain["format"] == "binary64", "unsupported float format")
    return {"kind": "builtin", "name": tag, "parameters": parameters}


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
        "expression": ["expression"],
        "literal_site": ["literal_site"],
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
    field_uses = []
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
            field_uses.append((field["ordinal"], projection["position"], len(bodies)))
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
        generated.append(("cte_definition", "R03", cte["definition"], "naming"))
        generated.extend(
            ("terminal_column", "R03", c["terminal"], "naming") for c in cte["columns"]
        )
    for body in bodies:
        if body["producer"] is None:
            generated.append(("qualified_scan", "R01", None, "scan"))
            generated.extend(
                ("source_representation", "R02", None, ("field", field["ordinal"]))
                for field in description["fields"]
            )
        else:
            generated.append(("named_use", "R03", body["use"], "naming"))
            generated.extend(
                ("immediate_terminal", "R03", c["terminal"], "naming")
                for c in body["producer_columns"]
            )
        generated.extend(
            ("field_projection", "R02", None, ("field", c["field"]["ordinal"]))
            for c in body["columns"]
        )
        generated.append(("read_only_select_bytes", "R23", None, "none"))
    generated.append(("nonrecursive_with_bytes", "R23", None, "none"))
    _need(all(len(body["columns"]) <= limits["columns"] for body in bodies))
    _need(
        3 * len(bodies)
        + 2 * projection_base
        + 2 * len(ctes)
        + sum(len(c["columns"]) for c in ctes.values())
        <= limits["nodes"]
    )
    return originals, generated, field_uses


def _fixed_payload(tag, value):
    if tag == "Bool":
        _need(type(value) is bool)
        return value
    if tag == "Int":
        _need(
            type(value) is str and re.fullmatch(r"-?(0|[1-9][0-9]*)", value) is not None
        )
        result = int(value)
        _need(str(result) == value and -(1 << 63) <= result < 1 << 63)
        return result
    if tag == "Float":
        _need(type(value) is str)
        try:
            result = float.fromhex(value)
        except OverflowError as error:
            raise ValueError("nonfinite binary64 payload") from error
        _need(math.isfinite(result) and result.hex() == value)
        return result
    _need(tag == "Text" and type(value) is str)
    value.encode("utf-8")
    return value


def _fixed_physical(family, tag):
    return {
        "postgres": {
            "Bool": "pg_bool",
            "Int": "pg_int8",
            "Float": "pg_float8",
            "Text": "pg_text",
        },
        "mysql": {
            "Bool": "my_signed_bool",
            "Int": "my_signed_int",
            "Float": "my_double",
            "Text": "my_utf8mb4_text",
        },
    }[family][tag]


def decoded_arguments(document):
    """Ordered native values only from the independently decoded public map."""
    result, assigned, slot_indices = [], {}, {}
    family = document["target"]["family"]
    for use in document["parameter_uses"]:
        value = document["fixed_values"][use["slot"]]
        decoded = _fixed_payload(value["tag"], value["value"])
        if family == "mysql" and value["tag"] == "Bool":
            decoded = int(decoded)
        index = use["server_index"]
        if family == "postgres" and use["slot"] in slot_indices:
            _need(index == slot_indices[use["slot"]])
        if index in assigned:
            _need(
                family == "postgres"
                and assigned[index] == (use["slot"], use["physical_type"])
            )
        else:
            _need(type(index) is int and index == len(result) + 1)
            assigned[index] = use["slot"], use["physical_type"]
            result.append(decoded)
            slot_indices[use["slot"]] = index
    return tuple(result)


def _selected_scan(document, contract, premises, family):
    """The one physical scan both public grammars must agree on, with its premises."""
    statements = [i for i, p in enumerate(premises) if p["scope"] == "statement"]
    scans = [
        r
        for r in document["requirements"]
        if r.get("denominator") == "generated" and r.get("kind") == "qualified_scan"
    ]
    _need(len(scans) == 1)
    candidates = []
    base = len(contract["environment"])
    for source in contract["sources"]:
        positions = [
            base + i for i, p in enumerate(source["premises"]) if p["scope"] == "source"
        ]
        if scans[0]["premises"] == sorted([*statements, *positions]):
            candidates.append((source, positions))
        base += len(source["premises"])
    _need(len(candidates) == 1, "ambiguous physical row source")
    description, source_positions = candidates[0]
    for key in ("row_domain_matches", "read_only_object"):
        _need(
            any(
                premises[i]["key"] == key and premises[i]["value"] is True
                for i in source_positions
            ),
            "unestablished physical scan premise",
        )
    for key, expected in (
        ("operator_environment", "builtin_only"),
        ("client_encoding", "UTF8" if family == "postgres" else "utf8mb4"),
    ):
        found = [premises[i]["value"] for i in statements if premises[i]["key"] == key]
        _need(bool(found) and all(value == expected for value in found))
    return description, source_positions, statements


def _premise_domain(premises, selector, scoped, sites):
    """Statement/source premises, plus expression premises at these exact sites."""
    result = list(scoped)
    for position, premise in enumerate(premises):
        if any(
            premise["scope"]
            == {
                "kind": "expression",
                "source": selector,
                "site": {"kind": "expression_site", "position": projection},
                "context": {"kind": "select_block", "position": block},
            }
            for projection, block in sites
        ):
            result.append(position)
    return sorted(result)


def _field_premises(premises, description, scoped, field_uses):
    """One applicable premise domain per retained field, keyed by its ordinal."""
    return {
        field["ordinal"]: _premise_domain(
            premises,
            description["selector"],
            scoped,
            [(p, b) for ordinal, p, b in field_uses if ordinal == field["ordinal"]],
        )
        for field in description["fields"]
    }


def _requirement_premises(key, naming, scan_premises, physical):
    if key == "naming":
        return naming
    if key == "scan":
        return scan_premises
    return physical[key[1]] if type(key) is tuple else []


def _decode_fixed_public(document, limits):
    """Independent finite SELECT/WITH/leaf/sign grammar, including unused values."""
    family = document["target"]["family"]
    contract = document["request"]["contract"]
    premises = _public_premises(contract)
    description, source_positions, statements = _selected_scan(
        document, contract, premises, family
    )
    provenance = _named_range_provenance(document)
    literal_evidence, unary_evidence = {}, {}
    for requirement in document["requirements"]:
        if requirement.get("denominator") != "generated":
            continue
        kind = requirement.get("kind")
        if kind not in {"literal", "unary"}:
            continue
        subject = requirement["subject"]
        _reference(subject)
        _need(subject["kind"] == "expression")
        evidence = requirement["evidence"]
        _need(type(evidence) is list and len(evidence) == 1)
        evidence_item = cast(dict[str, Any], evidence[0])
        mapping = literal_evidence if kind == "literal" else unary_evidence
        _need(subject["position"] not in mapping)
        if kind == "literal":
            _keys(evidence_item, ("tag", "value"))
            _fixed_payload(evidence_item["tag"], evidence_item["value"])
        else:
            _keys(evidence_item, ("operator",))
            _need(evidence_item["operator"] in {"+", "-"})
        mapping[subject["position"]] = evidence_item

    def ref(kind, position):
        return {"kind": kind, "position": position}

    def cause(reference):
        group = provenance[reference["kind"], reference["position"]]
        causes = [
            next(s["location"] for s in o["sources"] if s["kind"] == "authored_cause")
            for o in group
        ]
        _need(all(c == causes[0] for c in causes))
        return causes[0]

    def within(child, parent):
        return child["path"] == parent["path"] and (
            parent["line"],
            parent["column"],
        ) <= (child["line"], child["column"]) <= (
            child["end_line"],
            child["end_column"],
        ) <= (parent["end_line"], parent["end_column"])

    sql = document["sql"].encode()
    lexical, enclosures = [], []
    offset = 0
    for interval in document["ranges"]:
        _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
        _need(type(interval["start"]) is int and type(interval["end"]) is int)
        _reference(interval["subject"])
        _need(0 <= interval["start"] < interval["end"] <= len(sql))
        if interval["kind"] == "expression_range":
            enclosures.append(interval)
            continue
        _need(not enclosures and interval["start"] == offset)
        _need(interval["kind"] in {"identifier", "syntax", "literal", "parameter"})
        text = sql[offset : interval["end"]].decode()
        if interval["kind"] == "identifier":
            text = _identifier_token(text, family, interval["role"])
        lexical.append((interval, text))
        offset = interval["end"]
    _need(offset == len(sql))
    fixed = document["fixed_values"]
    for i, value in enumerate(fixed):
        _keys(value, ("slot", "reference", "site", "tag", "value"))
        _need(type(value["slot"]) is int and value["slot"] == i)
        _reference(value["reference"])
        _reference(value["site"])
        _need(
            value["reference"] == ref("literal_slot", i)
            and value["site"]["kind"] == "literal_site"
        )
        _fixed_payload(value["tag"], value["value"])
    _need(
        len({(v["site"]["kind"], v["site"]["position"]) for v in fixed}) == len(fixed)
    )
    uses = document["parameter_uses"]
    _need(len(uses) <= limits["parameters"])
    bound = document["request"]["literal_policy"] == "bind_safe_literals"
    _need(bound or not fixed and not uses)
    if fixed:
        protocols = [
            premises[i]["value"]
            for i in statements
            if premises[i]["key"] == "parameter_protocol"
        ]
        _need(
            bool(protocols)
            and all(
                v == ("postgres_extended" if family == "postgres" else "mysql_prepared")
                for v in protocols
            )
        )
    cursor = expression_count = projection_count = input_count = 0
    scalar_ids, seen_sites, used_slots, expected_ranges = set(), {}, set(), []
    bodies, ctes, field_uses = [], {}, []

    def take(kind, role, text=None, subject=None):
        nonlocal cursor
        _need(cursor < len(lexical))
        interval, actual = lexical[cursor]
        cursor += 1
        _need(interval["kind"] == kind and interval["role"] == role)
        _need(text is None or text == actual)
        _need(subject is None or subject == interval["subject"])
        return interval, actual

    def peek():
        return lexical[cursor][0]["role"] if cursor < len(lexical) else None

    used = 0
    scalar_nodes = 0

    def scalar(projection):
        nonlocal expression_count, used, scalar_nodes
        start_ref = ref("expression", expression_count)
        signs, requirements = [], []
        while peek() == "unary_open":
            original = ref("expression", expression_count)
            interval, text = take("syntax", "unary_open", subject=original)
            _need(text in {"(+", "(-"})
            _need(unary_evidence[expression_count]["operator"] == text[1])
            signs.append((original, text[1], interval["start"]))
            scalar_ids.add(expression_count)
            expression_count += 1
        original = ref("expression", expression_count)
        opened, _ = take("syntax", "anchor_open", "CAST(", original)
        scalar_ids.add(expression_count)
        expression_count += 1
        _need(cursor < len(lexical))
        interval, token = lexical[cursor]
        cursor_kind, tag = interval["kind"], interval["role"]
        _need(tag in {"Bool", "Int", "Float", "Text"})
        _need(interval["subject"]["kind"] == "literal_site")
        site = interval["subject"]
        _need(
            within(cause(original), cause(projection))
            and cause(site) == cause(original)
        )
        _need(site["position"] not in seen_sites)
        seen_sites[site["position"]] = original
        take(cursor_kind, tag, token, site)
        physical = _fixed_physical(family, tag)
        if cursor_kind == "parameter":
            _need(bound and used < len(uses))
            use = uses[used]
            _keys(use, ("use", "slot", "server_index", "physical_type", "range"))
            _keys(use["range"], ("start", "end"))
            _need(type(use["use"]) is int and use["use"] == used)
            _need(_ordinal(use["slot"]) and use["slot"] < len(fixed))
            _need(type(use["server_index"]) is int and use["server_index"] > 0)
            _need(use["physical_type"] == physical)
            _need(use["range"] == {"start": interval["start"], "end": interval["end"]})
            _need(all(type(use["range"][k]) is int for k in ("start", "end")))
            value = fixed[use["slot"]]
            _need(value["site"] == site and value["tag"] == tag)
            _need(
                token
                == ("$" + str(use["server_index"]) if family == "postgres" else "?")
            )
            payload = _fixed_payload(tag, value["value"])
            slot = use["slot"]
            used_slots.add(slot)
            used += 1
        else:
            _need(cursor_kind == "literal" and not bound)
            slot = None
            if tag == "Bool":
                _need(token in {"TRUE", "FALSE"})
                payload = token == "TRUE"
            elif tag == "Int":
                payload = _fixed_payload(tag, token)
            elif tag == "Float":
                if family == "postgres":
                    _need(token.startswith("'") and token.endswith("'"))
                    spelling = token[1:-1]
                else:
                    _need("e" in token)
                    spelling = token[:-2] if token.endswith("e0") else token
                payload = float(spelling)
                _need(math.isfinite(payload) and repr(payload) == spelling)
            elif family == "postgres":
                _need(re.fullmatch(r"E'(?:\\[0-3][0-7]{2})*'", token) is not None)
                payload = bytes(
                    int(token[i + 1 : i + 4], 8) for i in range(2, len(token) - 1, 4)
                ).decode()
            else:
                _need(re.fullmatch(r"X'(?:[0-9a-f]{2})*'", token) is not None)
                payload = bytes.fromhex(token[2:-1]).decode()
            evidence = literal_evidence[original["position"]]
            _need(evidence["tag"] == tag)
            expected = _fixed_payload(tag, evidence["value"])
            _need(type(payload) is type(expected))
            if isinstance(payload, float):
                _need(type(expected) is float)
                assert isinstance(expected, float)
                _need(payload.hex() == expected.hex())
            else:
                _need(payload == expected)
        if tag == "Text":
            _need(type(payload) is str)
            assert isinstance(payload, str)
            _need(family != "postgres" or "\0" not in payload)
        close = (
            " AS "
            + {
                "pg_bool": "pg_catalog.bool",
                "pg_int8": "pg_catalog.int8",
                "pg_float8": "pg_catalog.float8",
                "pg_text": "pg_catalog.text",
                "my_signed_bool": "SIGNED",
                "my_signed_int": "SIGNED",
                "my_double": "DOUBLE",
                "my_utf8mb4_text": "CHAR CHARACTER SET utf8mb4",
            }[physical]
            + ")"
        )
        if tag == "Text":
            close += (
                ' COLLATE "C"' if family == "postgres" else " COLLATE utf8mb4_0900_bin"
            )
        closed, _ = take("syntax", "anchor_close", close, original)
        expected_ranges.append(("anchor", original, opened["start"], closed["end"]))
        for sign_ref, sign, start in reversed(signs):
            _need(tag in {"Int", "Float"})
            _need(type(payload) in {int, float})
            assert isinstance(payload, (int, float))
            _need(within(cause(original), cause(sign_ref)))
            payload = -payload if sign == "-" else +payload
            _need(
                -(1 << 63) <= payload < 1 << 63
                if tag == "Int"
                else math.isfinite(payload)
            )
            closed, _ = take("syntax", "unary_close", ")", sign_ref)
            expected_ranges.append(("unary", sign_ref, start, closed["end"]))
        requirements.extend(("unary", sign_ref, tag) for sign_ref, _, _ in signs)
        requirements.extend(
            (("type_anchor", original, tag), (cursor_kind, original, tag))
        )
        scalar_nodes += 3 + len(signs)
        return {
            "tag": tag,
            "value": payload,
            "expression": start_ref,
            "leaf": original,
            "site": site,
            "slot": slot,
            "requirements": requirements,
        }

    def source_type(field):
        # The same field law the field-only route applies, before deriving output.
        return _field_compatibility(field["representation"], family)

    def value_representation(value):
        tag, payload = value["tag"], value["value"]
        if tag == "Bool":
            domain = {"kind": "bool01"}
        elif tag == "Int":
            domain = {"kind": "int_range", "min": str(payload), "max": str(payload)}
        elif tag == "Float":
            domain = {"kind": "finite_float", "format": "binary64"}
        else:
            domain = {
                "kind": "text",
                "max_characters": len(payload),
                "encoding": "UTF8" if family == "postgres" else "utf8mb4",
                "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
                "padding": "NO PAD",
            }
        return {
            "storage": {"kind": _fixed_physical(family, tag)},
            "nullable": False,
            "domain": domain,
        }

    def select(owner, final=False):
        nonlocal expression_count, projection_count, input_count
        take("syntax", "select", "SELECT ", owner)
        selected = []
        while True:
            i = len(selected)
            projection = ref("projection", projection_count + i)
            export = ref("export", projection_count + i)
            if i:
                take("syntax", "separator", ", ", projection)
            expression = ref("expression", expression_count)
            if peek() == "column_scope":
                scope, alias = take("identifier", "column_scope")
                take("syntax", "qualifier", ".", projection)
                token, name = take("identifier", "column")
                value = {"reference": (alias, scope["subject"], name, token["subject"])}
                expression_count += 1
            else:
                value = {"literal": scalar(projection)}
            take("syntax", "alias", " AS ", projection)
            _, label = take("identifier", "label", None if final else f"c{i}", export)
            _need(
                cause(export) == cause(projection)
                and within(cause(projection), cause(owner))
            )
            selected.append((value, label, projection, export, expression))
            if peek() != "separator":
                break
        token, _ = take("syntax", "from", " FROM ")
        producer_ref = token["subject"]
        producer_name = None
        if peek() == "namespace":
            _need(not bodies and producer_ref == ref("definition", 0))
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
            _need(cause(producer_ref)["path"] == description["selector"]["module"])
            incoming = [
                {
                    "name": f["column"],
                    "terminal": ref("source_port", f["ordinal"]),
                    "canonical": ref("source_port", f["ordinal"]),
                    "field": f,
                    "literal": None,
                }
                for f in description["fields"]
            ]
            for f in description["fields"]:
                source_type(f)
        else:
            _, producer_name = take("identifier", "cte_reference", subject=producer_ref)
            _need(
                producer_name in ctes
                and ctes[producer_name]["definition"] == producer_ref
            )
            incoming = ctes[producer_name]["columns"]
        use = ref("input_use", len(bodies))
        take("syntax", "alias", " AS ", use)
        _, alias = take("identifier", "relation_scope", f"s{len(bodies)}", use)
        _need(within(cause(use), cause(owner)))
        route = provenance[use["kind"], use["position"]][0]["sources"]
        _need(
            any(
                s["kind"] == "referenced_declaration"
                and s["location"] == cause(producer_ref)
                for s in route
            )
        )
        hops = [s for s in route if s["kind"] in {"import_item", "export_item"}]
        module = cause(owner)["path"]
        _need(len(hops) % 2 == 0)
        for imported, exported in zip(hops[::2], hops[1::2], strict=True):
            _need(
                imported["kind"] == "import_item"
                and imported["path"] == module
                and exported["kind"] == "export_item"
            )
            module = exported["path"]
        _need(module == cause(producer_ref)["path"])
        names = {c["name"]: (i, c) for i, c in enumerate(incoming)}
        _need(len(names) == len(incoming))
        output = []
        for i, (item, label, projection, export, expression) in enumerate(selected):
            terminal = ref("result_port", projection_count + i)
            link, input_ref = None, None
            if "reference" in item:
                qualifier, input_ref, name, observed_terminal = item["reference"]
                _need(qualifier == alias and name in names)
                index, source = names[name]
                _need(input_ref == ref("input_port", input_count + index))
                _need(observed_terminal == source["terminal"])
                _need(
                    cause(input_ref) == cause(use)
                    and cause(observed_terminal) == cause(producer_ref)
                )
                field, value = source["field"], source["literal"]
                link = {"export": source["canonical"], "terminal": source["terminal"]}
                if field is not None:
                    field_uses.append(
                        (field["ordinal"], projection["position"], len(bodies))
                    )
            else:
                field, value = None, item["literal"]
                value["origin"] = {
                    k: value[k] for k in ("expression", "leaf", "site", "slot")
                }
                value["origin"].update(export=export, terminal=terminal)
            entry = {
                "name": label,
                "terminal": terminal,
                "canonical": export,
                "field": field,
                "literal": value,
                "new_value": item.get("literal"),
                "projection": projection,
            }
            output.append(entry)
            if final:
                _need(i < len(document["columns"]))
                if field is None:
                    correspondence = {
                        "literal_origin": value["origin"],
                        "expression": expression,
                        "input_port": input_ref,
                        "producer": link,
                        "export": export,
                        "projection": projection,
                        "sql_symbol": i + 1,
                    }
                    logical = {
                        "kind": "builtin",
                        "name": value["tag"],
                        "parameters": None,
                    }
                    representation = value_representation(value)
                else:
                    correspondence = {
                        "source": description["selector"],
                        "field": field["ordinal"],
                        "source_port": ref("source_port", field["ordinal"]),
                        "input_port": input_ref,
                        "export": export,
                        "projection": projection,
                        "sql_symbol": i + 1,
                    }
                    logical, representation = (
                        source_type(field),
                        field["representation"],
                    )
                expected = {
                    "ordinal": i,
                    "label": label,
                    "logical_type": logical,
                    "nullable": representation["nullable"],
                    "representation": representation,
                    "correspondence": correspondence,
                }
                # JSON type equality matters: bool is never an ordinal.
                _need(
                    encoded(document["columns"][i]) == encoded(expected),
                    "literal/field output correspondence",
                )
        _need(not final or len(output) == len(document["columns"]))
        _need(len(output) <= limits["columns"])
        bodies.append(
            {
                "producer": producer_name,
                "use": use,
                "incoming": incoming,
                "columns": output,
            }
        )
        projection_count += len(output)
        input_count += len(incoming)
        return output

    naming = [i for i in statements if premises[i]["key"] == "identifier_case"]
    if peek() == "with":
        expected_case = (
            "quoted_exact" if family == "postgres" else "lower_case_table_names=0"
        )
        _need(
            bool(naming) and all(premises[i]["value"] == expected_case for i in naming)
        )
        take("syntax", "with", "WITH ", ref("selected_plan", 0))
        while True:
            index = len(ctes)
            definition = ref("definition", index + 1)
            if index:
                take("syntax", "cte_separator", ", ", definition)
            _, name = take("identifier", "cte_name", f"p{index}", definition)
            take("syntax", "cte_columns_open", " (", definition)
            header = []
            while True:
                term = ref("result_port", projection_count + len(header))
                if header:
                    take("syntax", "terminal_separator", ", ", term)
                take("identifier", "terminal_column", f"c{len(header)}", term)
                _need(cause(term) == cause(definition))
                header.append(term)
                if peek() != "terminal_separator":
                    break
            take("syntax", "cte_body_open", ") AS (", definition)
            columns = select(definition)
            _need(header == [c["terminal"] for c in columns])
            take("syntax", "cte_body_close", ")", definition)
            ctes[name] = {
                "definition": definition,
                "columns": columns,
                "producer": bodies[-1]["producer"],
            }
            if peek() != "cte_separator":
                break
        take("syntax", "with_body", " ", ref("definition", len(ctes) + 1))
        _need(cause(ref("definition", len(ctes) + 1)) == cause(ref("selected_plan", 0)))
    select(ref("selected_plan", 0), final=True)
    _need(
        cursor == len(lexical)
        and used == len(uses)
        and used_slots == set(range(len(fixed)))
    )
    _need(
        cause(ref("selected_plan", 0))["path"] == document["request"]["owner"]["module"]
    )
    visited, previous = set(), bodies[-1]["producer"]
    while previous is not None:
        _need(previous not in visited)
        visited.add(previous)
        previous = ctes[previous]["producer"]
    _need(visited == set(ctes))
    _need(len(enclosures) == len(expected_ranges))
    for interval, (role, subject, start, end) in zip(
        enclosures, expected_ranges, strict=True
    ):
        _need(
            (interval["role"], interval["subject"], interval["start"], interval["end"])
            == (role, subject, start, end)
        )
    decoded_arguments(document)
    # Independent complete denominators from the parsed bodies and literal tokens.
    original_subjects = {
        "source_realization": [ref("definition", 0)],
        "export_representation": [ref("export", i) for i in range(projection_count)],
        "expression": [ref("expression", i) for i in range(expression_count)],
        "stage_value": [ref("stage_port", i) for i in range(input_count)],
        "scope": [ref("select_block", i) for i in range(len(bodies))],
        "result": [
            ref(kind, i)
            for kind in ("result_port", "result_export")
            for i in range(projection_count)
        ],
        "fixed_literal_transport": [ref("bind_use", i) for i in range(len(fixed))],
    }
    generated = []
    scan_premises = sorted([*statements, *source_positions])
    physical = _field_premises(premises, description, scan_premises, field_uses)
    for cte in ctes.values():
        generated.append(("cte_definition", "R03", cte["definition"], naming))
        generated.extend(
            ("terminal_column", "R03", c["terminal"], naming) for c in cte["columns"]
        )
    for body in bodies:
        if body["producer"] is None:
            generated.append(("qualified_scan", "R01", None, scan_premises))
            generated.extend(
                ("source_representation", "R02", None, physical[field["ordinal"]])
                for field in description["fields"]
            )
        else:
            generated.append(("named_use", "R03", body["use"], naming))
            generated.extend(
                ("immediate_terminal", "R03", c["terminal"], naming)
                for c in body["incoming"]
            )
        for column in body["columns"]:
            if column["field"] is not None:
                positions = physical[column["field"]["ordinal"]]
                generated.append(("field_projection", "R02", None, positions))
            else:
                generated.append(("value_projection", "R04", column["projection"], []))
                if column["new_value"] is not None:
                    for kind, subject, tag in column["new_value"]["requirements"]:
                        keys = {"operator_environment"}
                        if tag == "Text":
                            keys.add("client_encoding")
                        if kind == "parameter":
                            keys.add("parameter_protocol")
                        positions = [
                            i for i in statements if premises[i]["key"] in keys
                        ]
                        generated.append((kind, "R04", subject, positions))
        generated.append(("read_only_select_bytes", "R23", None, []))
    if ctes:
        generated.append(("nonrecursive_with_bytes", "R23", None, []))
    originals, actual_generated = [], []
    for requirement in document["requirements"]:
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
            and requirement["disposition"] == "checked_rule"
        )
        _reference(requirement["subject"])
        _need(
            type(requirement["premises"]) is list
            and all(_ordinal(i) and i < len(premises) for i in requirement["premises"])
        )
        _need(type(requirement["evidence"]) is list)
        bucket = (
            originals if requirement["denominator"] == "original" else actual_generated
        )
        _need(
            type(requirement["ordinal"]) is int
            and requirement["ordinal"] == len(bucket)
        )
        bucket.append(requirement)
    for kind, subjects in original_subjects.items():
        actual = [r for r in originals if r["kind"] == kind]
        _need(
            Counter(encoded(r["subject"]) for r in actual)
            == Counter(encoded(s) for s in subjects)
        )
        for r in actual:
            rule = (
                "R04"
                if kind == "fixed_literal_transport"
                or kind == "expression"
                and r["subject"]["position"] in scalar_ids
                else "R03"
                if kind == "scope" and ctes
                else "R01"
                if kind in {"source_realization", "expression", "scope"}
                else "R02"
            )
            _need(r["rule"] == rule and r["premises"] == [])
    _need(len(originals) == sum(len(s) for s in original_subjects.values()))
    _need(len(generated) == len(actual_generated))
    for i, (actual, (kind, rule, subject, positions)) in enumerate(
        zip(actual_generated, generated, strict=True)
    ):
        _need(actual["kind"] == kind and actual["rule"] == rule)
        if kind not in {"literal", "unary"}:
            _need(actual["evidence"] == [])
        _need(actual["subject"] == (subject if subject is not None else ref(kind, i)))
        _need(actual["premises"] == positions)
    _need(
        3 * len(bodies)
        + 2 * projection_count
        + 2 * len(ctes)
        + sum(len(c["columns"]) for c in ctes.values())
        + scalar_nodes
        <= limits["nodes"]
    )


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
        _need(
            type(document["fixed_values"]) is list
            and type(document["parameter_uses"]) is list
        )
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
        if any(
            interval.get("kind") in {"literal", "parameter", "expression_range"}
            for interval in _records(document["ranges"])
        ):
            _decode_fixed_public(document, limits)
            return document
        _need(document["fixed_values"] == [] and document["parameter_uses"] == [])
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
            # JSON type equality matters: a copied dictionary is not a check.
            _need(
                field["ordinal"] == correspondence["field"]
                and encoded(column["representation"])
                == encoded(field["representation"])
            )
            _keys(column["representation"], ("storage", "nullable", "domain"))
            _need(
                encoded(column["logical_type"])
                == encoded(
                    _field_compatibility(field["representation"], target["family"])
                ),
                "declared output type is not the physical source type",
            )
            _need(
                column["nullable"] == column["representation"]["nullable"]
                and (
                    type(column["nullable"]) is bool or column["nullable"] == "unknown"
                )
            )
            fields.append((column, description, field))
        _need(all(item[1] is fields[0][1] for item in fields))
        # The same selected scan, field law and premise obligations as the
        # literal-containing grammar; a grammar never owns a weaker contract.
        description, source_positions, statements = _selected_scan(
            document, contract, all_premises, target["family"]
        )
        _need(description is fields[0][1], "selected scan is not the projected source")
        scan_premises = sorted([*statements, *source_positions])
        for field in fields[0][1]["fields"]:
            _field_compatibility(field["representation"], target["family"])
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
                ("qualified_scan", "R01", None, "scan"),
                *[
                    ("source_representation", "R02", None, ("field", f["ordinal"]))
                    for f in fields[0][1]["fields"]
                ],
                *[
                    (
                        "field_projection",
                        "R02",
                        None,
                        ("field", c["correspondence"]["field"]),
                    )
                    for c, _, _ in fields
                ],
                ("read_only_select_bytes", "R23", None, "none"),
            ]
            field_uses = [
                (
                    c["correspondence"]["field"],
                    c["correspondence"]["projection"]["position"],
                    0,
                )
                for c, _, _ in fields
            ]
        else:
            expected_original, expected_generated, field_uses = _decode_named_sql(
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
        physical = _field_premises(all_premises, description, scan_premises, field_uses)
        for i, (actual, (kind, rule, subject, key)) in enumerate(
            zip(generated, expected_generated, strict=True)
        ):
            _need(actual["kind"] == kind and actual["rule"] == rule)
            _need(
                actual["premises"]
                == _requirement_premises(key, naming, scan_premises, physical),
                "requirement premise domain",
            )
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
