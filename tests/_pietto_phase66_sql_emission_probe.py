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
}
LABELS = ("display_text", "record_id", "active", "amount", "ratio")
LOGICAL = ("Text", "Int", "Bool", "Decimal", "Float")
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
        for source in request["sources"]:
            _keys(source, ("module", "sha256", "byte_count"))
            _need(
                type(source["module"]) is str
                and type(source["sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None
                and _ordinal(source["byte_count"])
            )
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
        _need(len(sql) <= 8 * 1024 * 1024)
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
        quote = '"' if target["family"] == "postgres" else "`"

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
                _need(text[1:-1].replace(quote * 2, quote) == expected)
            else:
                _need(text == expected)
            offset = interval["end"]

        token("syntax", "select", "SELECT ", {"kind": "selected_plan", "position": 0})
        for i, (column, description, field) in enumerate(fields):
            if i:
                token(
                    "syntax", "separator", ", ", column["correspondence"]["projection"]
                )
            token(
                "identifier",
                "column_scope",
                "s0",
                column["correspondence"]["input_port"],
            )
            token("syntax", "qualifier", ".", column["correspondence"]["projection"])
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
            "identifier", "namespace", fields[0][1]["relation"]["namespace"], definition
        )
        token("syntax", "qualifier", ".", definition)
        token("identifier", "relation", fields[0][1]["relation"]["name"], definition)
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
                and requirement["rule"] in {"R01", "R02", "R23"}
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
        n = len(fields)
        used_inputs = {
            json.dumps(c["correspondence"]["input_port"], sort_keys=True)
            for c, _, _ in fields
        }
        _need(
            Counter(r["kind"] for r in original)
            == Counter(
                {
                    "source_realization": 1,
                    "export_representation": n,
                    "expression": n,
                    "stage_value": len(used_inputs),
                    "scope": 1,
                    "result": 2 * n,
                }
            ),
            "original requirement denominator",
        )
        _need(
            [r["kind"] for r in generated]
            == [
                "qualified_scan",
                *["source_representation"] * len(fields[0][1]["fields"]),
                *["field_projection"] * n,
                "read_only_select_bytes",
            ],
            "generated requirement denominator",
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
    (directory / "main.pietto").write_text(source, encoding="utf-8")
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
                        item["source"].encode()
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
