#!/usr/bin/env python3
"""Pure verifier for recorded MySQL nested raw-candidate observations.

Usage:
  python p77_nested_raw_hook.py --write-plan plan.json
  python p77_nested_raw_hook.py --write-fixture observations.json
  python p77_nested_raw_hook.py --verify observations.json
  python p77_nested_raw_hook.py --self-check

No command opens a database. A human-run future probe records its own SQL under
RAW_CANDIDATE_NOT_PIETTO_EMITTED; this tool verifies the raw record only.
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
from typing import Any
from uuid import UUID

import p77_nested_raw_oracle as oracle

_INT = re.compile(r"-?(?:0|[1-9][0-9]*)$")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_UUID = re.compile(r"[0-9a-f]{32}$")


class Refusal(ValueError):
    pass


def _json(text: str) -> Any:
    if type(text) is not str:
        raise Refusal("raw JSON must be text")
    try:
        return json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise Refusal("invalid raw JSON") from exc


def _float_equal(left: float, right: float) -> bool:
    return type(left) is float and type(right) is float and oracle.float_bits(left) == oracle.float_bits(right)


def _leaf(value: Any, expected: Any, kind: str) -> None:
    if kind == "Float":
        if type(value) is not float or not _float_equal(value, expected):
            raise Refusal("Float binary64 mismatch")
        return
    if kind == "Int":
        if type(value) is not str or _INT.fullmatch(value) is None:
            raise Refusal("Int wire grammar")
        if int(value) != int(expected) or not -(2**63) <= int(value) < 2**63:
            raise Refusal("Int value")
        return
    if kind == "Decimal":
        if type(value) is not str or _DECIMAL.fullmatch(value) is None:
            raise Refusal("Decimal wire grammar")
        try:
            actual = Decimal(value)
            wanted = Decimal(expected)
        except InvalidOperation as exc:
            raise Refusal("Decimal value") from exc
        if not actual.is_finite() or actual != wanted:
            raise Refusal("Decimal value")
        return
    if kind == "Date":
        if type(value) is not str or _DATE.fullmatch(value) is None:
            raise Refusal("Date wire grammar")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise Refusal("Date value") from exc
        if parsed.isoformat() != expected:
            raise Refusal("Date value")
        return
    if kind == "UUID":
        if type(value) is not str or _UUID.fullmatch(value) is None:
            raise Refusal("UUID wire grammar")
        try:
            parsed = UUID(hex=value)
        except ValueError as exc:
            raise Refusal("UUID value") from exc
        if parsed.bytes.hex() != expected:
            raise Refusal("UUID value")
        return
    if kind == "Text":
        if type(value) is not str or value != expected:
            raise Refusal("Text value")
        return
    raise Refusal("unsupported oracle leaf")


def _rows(case: dict, envelope: dict) -> tuple[tuple[Any, ...], ...]:
    if set(envelope) != {"v", "n", "r"} or envelope["v"] != oracle.ENVELOPE_VERSION:
        raise Refusal("envelope shape")
    count, rows = envelope["n"], envelope["r"]
    if type(count) is bool or type(count) is not int or not 0 <= count <= oracle.MAX_CHILD_ROWS:
        raise Refusal("envelope count")
    if type(rows) is not list or len(rows) != count:
        raise Refusal("envelope row count")
    checked = []
    expected_sequences = case.get("allowed_rows", (case.get("expected_rows", ()),))
    width = 1
    for candidate in rows:
        if type(candidate) is not list or len(candidate) != width:
            raise Refusal("child row width")
        checked.append(tuple(candidate))
    checked_tuple = tuple(checked)
    for expected in expected_sequences:
        if len(expected) != len(checked_tuple):
            continue
        try:
            for observed_row, expected_row in zip(checked_tuple, expected, strict=True):
                _leaf(observed_row[0], expected_row[0], case["leaf"])
        except Refusal:
            continue
        return checked_tuple
    raise Refusal("logical result mismatch")


def verify_document(document: Any) -> dict:
    if type(document) is not dict or document.get("schema") != oracle.SCHEMA:
        raise Refusal("observation schema")
    records = document.get("records")
    if type(records) is not list or len(records) != len(oracle.CASES):
        raise Refusal("record count")
    seen = set()
    decoded = {}
    for record in records:
        if type(record) is not dict:
            raise Refusal("record type")
        identifier = record.get("case")
        if type(identifier) is not str or identifier in seen:
            raise Refusal("record identity")
        try:
            case = oracle.case_by_id(identifier)
        except KeyError as exc:
            raise Refusal("unknown case") from exc
        seen.add(identifier)
        if (
            record.get("parent") != case["parent"]
            or record.get("sql_kind") != oracle.RAW_CANDIDATE
            or type(record.get("raw_candidate_sql")) is not str
            or not record["raw_candidate_sql"]
        ):
            raise Refusal("candidate provenance")
        if case.get("absent"):
            if set(record) != {"case", "parent", "sql_kind", "raw_candidate_sql", "raw_kind"} or record["raw_kind"] != "sql_null":
                raise Refusal("outer absence")
            decoded[identifier] = None
            continue
        if set(record) != {"case", "parent", "sql_kind", "raw_candidate_sql", "raw_kind", "raw_json"} or record["raw_kind"] != "json_text":
            raise Refusal("raw carrier shape")
        envelope = _json(record["raw_json"])
        if type(envelope) is not dict:
            raise Refusal("JSON null or non-object envelope")
        decoded[identifier] = _rows(case, envelope)
    if seen != set(oracle.case_ids()):
        raise Refusal("case coverage")
    return decoded


def _raw_json(case: dict) -> str:
    rows = case.get("expected_rows")
    if rows is None:
        rows = case["allowed_rows"][0]
    return json.dumps({"v": 1, "n": len(rows), "r": [list(row) for row in rows]}, ensure_ascii=False, separators=(",", ":"))


def fixture() -> dict:
    records = []
    for case in oracle.CASES:
        common = {
            "case": case["id"],
            "parent": case["parent"],
            "sql_kind": oracle.RAW_CANDIDATE,
            "raw_candidate_sql": "/* RAW CANDIDATE ONLY: recorder must replace this text */ SELECT ...",
        }
        if case.get("absent"):
            records.append({**common, "raw_kind": "sql_null"})
        else:
            records.append({**common, "raw_kind": "json_text", "raw_json": _raw_json(case)})
    return {"schema": oracle.SCHEMA, "records": records}


def plan() -> dict:
    return {
        "schema": "pietto.phase77.mysql-nested-raw-plan.v1",
        "status": "PRE_GATE1_NO_DB",
        "sql_label": oracle.RAW_CANDIDATE,
        "prohibition": "SQL text is a future raw probe, never Pietto emitted SQL or support evidence.",
        "pg_control": {case["id"]: case["pg_control"] for case in oracle.CASES},
        "experiments": {
            "float": "Record raw JSON text for -0.0, +0.0 and adjacent binary64; verifier compares IEEE bits.",
            "int64": "Record signed endpoints as JSON strings; native numeric JSON is not accepted.",
            "decimal_date_uuid": "Record strict decimal/date/lowercase-hex UUID strings; decoder has no normalization fallback.",
            "order": "Use a candidate window/aggregate query with unique order and permitted-tie controls; unique sequence must match exactly, tie has two allowed sequences only.",
            "states": "Record empty as JSON envelope and outer absence as SQL NULL in different records.",
        },
        "required_observation_cases": list(oracle.case_ids()),
        "observation_schema": oracle.SCHEMA,
    }


def _tampered(document: dict, identifier: str, change) -> dict:
    altered = json.loads(json.dumps(document))
    record = next(row for row in altered["records"] if row["case"] == identifier)
    change(record)
    return altered


def self_check() -> dict:
    good = fixture()
    verify_document(good)
    changes = {
        "float_sign": ("float_bits", lambda row: row.update(raw_json=row["raw_json"].replace("-0.0", "0.0", 1))),
        "int_number": ("int64", lambda row: row.update(raw_json=row["raw_json"].replace('"-9223372036854775808"', "-9223372036854775808", 1))),
        "decimal_exponent": ("decimal_string", lambda row: row.update(raw_json=row["raw_json"].replace('"-12.30"', '"-1.230e1"', 1))),
        "date_invalid": ("date_string", lambda row: row.update(raw_json=row["raw_json"].replace('"2026-11-08"', '"2026-13-08"', 1))),
        "uuid_uppercase": ("uuid_bytes", lambda row: row.update(raw_json=row["raw_json"].replace("80ff00112233445566778899aabbccdd", "80FF00112233445566778899AABBCCDD", 1))),
        "unique_order_swap": ("window_order_unique", lambda row: row.update(raw_json=row["raw_json"].replace('"first"],["second"', '"second"],["first"', 1))),
        "empty_as_absent": ("empty", lambda row: (row.pop("raw_json"), row.update(raw_kind="sql_null"))),
        "absent_as_json_null": ("outer_absent", lambda row: row.update(raw_kind="json_text", raw_json="null")),
        "wrong_count": ("int64", lambda row: row.update(raw_json=row["raw_json"].replace('"n":3', '"n":2', 1))),
        "extra_key": ("date_string", lambda row: row.update(raw_json=row["raw_json"][:-1] + ',"x":1}')),
    }
    refused = {}
    for name, (identifier, change) in changes.items():
        try:
            verify_document(_tampered(good, identifier, change))
        except Refusal as exc:
            refused[name] = str(exc)
        else:
            raise AssertionError(f"tamper was accepted: {name}")
    return {"accepted_fixture": len(verify_document(good)), "refused_tampers": refused}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-plan", type=Path)
    group.add_argument("--write-fixture", type=Path)
    group.add_argument("--verify", type=Path)
    group.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    try:
        if args.write_plan:
            args.write_plan.write_text(json.dumps(plan(), indent=2, sort_keys=True) + "\n")
            return 0
        if args.write_fixture:
            args.write_fixture.write_text(json.dumps(fixture(), indent=2, ensure_ascii=False) + "\n")
            return 0
        if args.verify:
            result = verify_document(json.loads(args.verify.read_text()))
        else:
            result = self_check()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, Refusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

