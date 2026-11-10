"""Strict, data-only judge for one parent-captured Phase77 flat receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PLAN_FORMAT = "pietto.phase77.flat-qualification-plan.v2"
RECEIPT_FORMAT = "pietto.phase77.flat-qualification-receipt.v2"


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def mapping(value: object, keys: set[str], message: str) -> dict[str, object]:
    require(type(value) is dict and set(value) == keys, message)
    return value


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc_timestamp6(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{6}\+00:00", value) is not None


def value_bag(expected: object, actual: object, name: str) -> None:
    require(type(expected) is list and type(actual) is list, f"{name}: values")
    require(len(expected) == len(actual), f"{name}: value count")
    remaining = list(actual)
    for wanted in expected:
        require(type(wanted) is list, f"{name}: expected value")
        for index, observed in enumerate(remaining):
            if type(observed) is not list or len(observed) != len(wanted):
                continue
            if all(
                utc_timestamp6(got) if want == {"kind": "utc_timestamp6"} else got == want
                for want, got in zip(wanted, observed, strict=True)
            ):
                remaining.pop(index)
                break
        else:
            raise ValueError(f"{name}: value bag")
    require(not remaining, f"{name}: extra value")


def judge(plan: object, raw: object) -> None:
    plan = mapping(plan, {"format", "target", "manifest", "cases", "cleanup"}, "plan envelope")
    require(type(plan["format"]) is str and plan["format"].startswith("pietto.phase77.") and plan["format"].endswith("-plan.v2"), "plan format")
    require(plan["target"] in {"postgres", "mysql"}, "plan target")
    manifest = mapping(plan["manifest"], {"candidate_identity", "reader_identities", "closure_sha256"}, "plan manifest")
    require(type(manifest["reader_identities"]) in {list, dict} and manifest["reader_identities"], "plan readers")
    unsigned = plan | {"manifest": manifest | {"closure_sha256": None}}
    require(manifest["closure_sha256"] == digest(unsigned), "plan closure")
    cases = plan["cases"]
    require(type(cases) is dict and cases, "plan inventory")
    raw = mapping(raw, {"format", "target", "manifest", "cases", "cleanup"}, "receipt envelope")
    require(raw["format"] == plan["format"].replace("-plan.", "-receipt."), "receipt format")
    require(raw["target"] == plan["target"], "target identity")
    require(raw["manifest"] == manifest, "candidate/reader identity")
    require(raw["cleanup"] == plan["cleanup"], "cleanup")
    received = raw["cases"]
    require(type(received) is dict and list(received) == list(cases), "receipt inventory")
    for name in cases:
        item = mapping(cases[name], {"candidate", "fixture", "expected"}, f"{name}: plan case")
        candidate = mapping(item["candidate"], {"source", "config", "contract", "artifact", "sql", "fixed_values", "parameter_uses", "columns"}, f"{name}: candidate")
        fixture = mapping(item["fixture"], {"ddl", "typed_seed"}, f"{name}: fixture")
        expected = mapping(item["expected"], {"metadata", "values", "warnings", "terminal"}, f"{name}: expected")
        observed = mapping(received[name], {"sql", "parameters", "parameter_uses", "fixture", "metadata", "values", "warnings", "terminal"}, f"{name}: receipt case")
        require(observed["sql"] == candidate["sql"], f"{name}: not emitted SQL")
        require(observed["parameters"] == candidate["fixed_values"], f"{name}: parameter values")
        require(observed["parameter_uses"] == candidate["parameter_uses"], f"{name}: parameter uses")
        require(observed["fixture"] == fixture, f"{name}: fixture identity")
        require(observed["metadata"] == expected["metadata"], f"{name}: physical metadata")
        require(observed["warnings"] == expected["warnings"], f"{name}: warnings")
        require(observed["terminal"] == expected["terminal"], f"{name}: terminal")
        value_bag(expected["values"], observed["values"], name)


def self_check() -> None:
    candidate = {"source": "", "config": "", "contract": {}, "artifact": {}, "sql": "SELECT 1", "fixed_values": [], "parameter_uses": [], "columns": []}
    fixture = {"ddl": ["CREATE TABLE t (x INT NOT NULL)"], "typed_seed": {"statements": []}}
    expected = {"metadata": [], "values": [[1]], "warnings": [], "terminal": {"kind": "rowset_eof", "close": "clean", "buffered_row_error": None}}
    names = ("s10_group", "s12_text", "s12_temporal", "s14_join")
    plan = {"format": PLAN_FORMAT, "target": "mysql", "manifest": {"candidate_identity": {"kind": "content", "value": "x"}, "reader_identities": [{"identity": "reader", "sha256": "x"}], "closure_sha256": None}, "cases": {name: {"candidate": candidate, "fixture": fixture, "expected": expected} for name in names}, "cleanup": {"connection": "closed", "relations": "dropped", "transaction": "rolled_back"}}
    plan["manifest"]["closure_sha256"] = digest(plan)
    received = {"sql": "SELECT 1", "parameters": [], "parameter_uses": [], "fixture": fixture, "metadata": [], "values": [[1]], "warnings": [], "terminal": expected["terminal"]}
    raw = {"format": RECEIPT_FORMAT, "target": "mysql", "manifest": plan["manifest"], "cases": {name: received.copy() for name in names}, "cleanup": plan["cleanup"]}
    judge(plan, raw)
    tampered_plan = json.loads(json.dumps(plan))
    tampered_plan["cases"]["s10_group"]["candidate"]["sql"] = "SELECT 2"
    try:
        judge(tampered_plan, raw)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted a tampered plan")
    changes = (
        lambda value: value["cases"]["s10_group"].__setitem__("metadata", [{"ordinal": 0}]),
        lambda value: value["cases"]["s10_group"].__setitem__("parameter_uses", [{"ordinal": 0}]),
        lambda value: value["cases"]["s10_group"].__setitem__("fixture", {"ddl": [], "typed_seed": {"statements": []}}),
        lambda value: value["cases"]["s10_group"].__setitem__("values", [[2]]),
        lambda value: value["cases"].__setitem__("grafted", received.copy()),
    )
    for change in changes:
        probe = json.loads(json.dumps(raw))
        change(probe)
        try:
            judge(plan, probe)
        except ValueError:
            continue
        raise AssertionError("accepted damaged actual receipt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
    elif args.plan and args.raw:
        judge(json.loads(args.plan.read_text(encoding="utf-8")), json.loads(args.raw.read_text(encoding="utf-8")))
    else:
        raise SystemExit("need --self-check or --plan/--raw")
