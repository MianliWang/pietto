#!/usr/bin/env python3
"""Materialize public S16 Text-window inputs; never open a database."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BODY = """query result:
    from rows
    select:
        id
        previous_empty = lag(text, 1, "") window(order by id)
        following_unicode = lead(text, 1, "雪") window(order by id)
        following_null = lead(text, 1) window(order by id)
"""
SEED = (
    (1, None, "alpha", {"decimal": "0.00"}, 0.0),
    (2, None, "雪", {"decimal": "0.00"}, 0.0),
    (3, None, "", {"decimal": "0.00"}, 0.0),
    (4, None, None, {"decimal": "0.00"}, 0.0),
)
EXPECTED_ROWS = (
    (1, "", "雪", "雪"),
    (2, "alpha", "", ""),
    (3, "雪", None, None),
    (4, "", "雪", None),
)


def _imports(candidate: Path):
    for path in (candidate / "src", candidate / "tests"):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
    import _pietto_sql_emission as emission
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    return emission, serialize_project_sql_emission


def _source_and_contract(emission, target: str) -> tuple[str, dict[str, object], str]:
    item = emission.parameterized_fixture(
        target, BODY, "preserve_literals", protocol=False
    )
    source = item["source"].replace("text: Text\n", "text: Text | None\n", 1)
    contract = json.loads(item["contract"])
    text = next(
        field
        for field in contract["sources"][0]["fields"]
        if field["name"] == "text"
    )
    text["representation"]["nullable"] = True
    return source, contract, item["policy"]


def _relation(contract: dict[str, object]) -> tuple[str, str, list[str]]:
    source = contract["sources"][0]
    return (
        source["relation"]["namespace"],
        source["relation"]["name"],
        [field["column"] for field in source["fields"]],
    )


def _ddl(target: str, contract: dict[str, object]) -> list[str]:
    namespace, name, columns = _relation(contract)
    if target == "postgres":
        table = f'"{namespace}"."{name}"'
        quoted = [f'"{column}"' for column in columns]
        return [
            f'CREATE SCHEMA IF NOT EXISTS "{namespace}"',
            (
                f'CREATE TABLE {table} ({quoted[0]} BIGINT NOT NULL, '
                f'{quoted[1]} BOOLEAN NULL, {quoted[2]} TEXT COLLATE "C" NULL, '
                f'{quoted[3]} NUMERIC(9, 2) NOT NULL, '
                f'{quoted[4]} DOUBLE PRECISION NOT NULL)'
            ),
        ]
    table = f'`{namespace}`.`{name}`'
    quoted = [f'`{column}`' for column in columns]
    return [
        (
            f'CREATE DATABASE IF NOT EXISTS `{namespace}` CHARACTER SET utf8mb4 '
            'COLLATE utf8mb4_0900_bin'
        ),
        (
            f'CREATE TABLE {table} ({quoted[0]} BIGINT NOT NULL, '
            f'{quoted[1]} TINYINT(1) NULL, {quoted[2]} VARCHAR(64) '
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL, '
            f'{quoted[3]} DECIMAL(9, 2) NOT NULL, {quoted[4]} DOUBLE NOT NULL)'
        ),
    ]


def _insert(target: str, contract: dict[str, object]) -> dict[str, object]:
    namespace, name, columns = _relation(contract)
    table = (
        f'"{namespace}"."{name}"' if target == "postgres" else f'`{namespace}`.`{name}`'
    )
    quoted = [f'"{column}"' if target == "postgres" else f'`{column}`' for column in columns]
    placeholders = (
        [f"${index}" for index in range(1, len(columns) + 1)]
        if target == "postgres"
        else ["%s"] * len(columns)
    )
    return {
        "sql": f"INSERT INTO {table} ({', '.join(quoted)}) VALUES ({', '.join(placeholders)})",
        "rows": [list(row) for row in SEED],
        "seed_order": "written id ascending; window order is id ascending",
    }


def _metadata(target: str) -> list[dict[str, object]]:
    if target == "postgres":
        return [
            {
                "ordinal": 0,
                "name": "id",
                "type_code": 20,
                "flags": 0,
                "charset": None,
                "python_type": "int",
                "nullable": False,
            },
            *(
                {
                    "ordinal": ordinal,
                    "name": name,
                    "type_code": 25,
                    "flags": 0,
                    "charset": None,
                    "python_type": "str",
                    "nullable": True,
                }
                for ordinal, name in enumerate(
                    ("previous_empty", "following_unicode", "following_null"), 1
                )
            ),
        ]
    return [
        {
            "ordinal": 0,
            "name": "id",
            "type_code": 8,
            "flags": 0,
            "charset": 63,
            "python_type": "int",
            "nullable": False,
        },
        *(
            {
                "ordinal": ordinal,
                "name": name,
                "type_code": 253,
                "flags": 0,
                "charset": 309,
                "python_type": "str",
                "nullable": True,
            }
            for ordinal, name in enumerate(
                ("previous_empty", "following_unicode", "following_null"), 1
            )
        ),
    ]


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _closure_sha256(plan: dict[str, object]) -> str:
    manifest = plan["manifest"]
    assert isinstance(manifest, dict)
    frozen = {
        "format": plan["format"],
        "target": plan["target"],
        "manifest": {
            "candidate_identity": manifest["candidate_identity"],
            "reader_identities": manifest["reader_identities"],
            "closure_sha256": None,
        },
        "cases": plan["cases"],
        "cleanup": plan["cleanup"],
    }
    return _sha256(
        json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _candidate_identity(candidate: Path, wheel: Path | None) -> dict[str, str | None]:
    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ("git", "-C", str(candidate), *arguments), text=True
        ).strip()

    patch = subprocess.check_output(
        ("git", "-C", str(candidate), "diff", "--binary", "HEAD")
    )
    return {
        "base_head": git("rev-parse", "HEAD"),
        "tree": git("write-tree"),
        "worktree_patch_sha256": _sha256(patch),
        "wheel_sha256": _sha256(wheel.read_bytes()) if wheel is not None else None,
    }


def build(candidate: Path, output: Path, wheel: Path | None) -> None:
    emission, serialize = _imports(candidate)
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    output.mkdir(parents=True, exist_ok=True)
    for target in ("postgres", "mysql"):
        source, contract, policy = _source_and_contract(emission, target)
        with tempfile.TemporaryDirectory() as directory:
            checked, outcome = emission.build_case(
                Path(directory), source, json.dumps(contract), policy
            )
            if not checked.verified or outcome.status != "VERIFIED" or outcome.artifact is None:
                raise ValueError(f"{target}: public candidate compilation did not verify")
            artifact_bytes = serialize(outcome)
            document = json.loads(artifact_bytes)
            built = build_compiled(outcome.artifact)
            loaded = load_compiled(
                built.payload,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
            compiled = emit_compiled(loaded, ())
            if compiled.rendered.sql != outcome.artifact.rendered.sql:
                raise ValueError(f"{target}: compiled reader changed SQL bytes")
        config = emission.CONFIG
        candidate_case = {
            "source": source,
            "config": config,
            "contract": contract,
            "artifact": artifact_bytes.decode("utf-8"),
            "sql": document["sql"],
            "fixed_values": document["fixed_values"],
            "parameter_uses": document["parameter_uses"],
            "columns": document["columns"],
        }
        fixture = {"ddl": _ddl(target, contract), "typed_seed": _insert(target, contract)}
        reader_identities = {
            "public_artifact": _sha256(artifact_bytes),
            "compiled_payload": _sha256(built.payload),
            "compiled_sql": _sha256(compiled.rendered.sql),
        }
        reader_identity_list = [
            {
                "kind": "public_artifact",
                "sha256": reader_identities["public_artifact"],
            },
            {
                "kind": "compiled",
                "payload_sha256": reader_identities["compiled_payload"],
                "sql_sha256": reader_identities["compiled_sql"],
            },
        ]
        candidate_identity = _candidate_identity(candidate, wheel)
        expected = {
            "metadata": _metadata(target),
            "values": [list(row) for row in EXPECTED_ROWS],
            "warnings": [],
            "terminal": {
                "kind": "rowset_eof",
                "close": "clean",
                "buffered_row_error": None,
            },
        }
        cleanup = {
            "connection": "closed",
            "relations": "dropped",
            "transaction": "rolled_back",
        }
        plan = {
            "format": "pietto.phase77.flat-qualification-plan.v2",
            "target": target,
            "manifest": {
                "candidate_identity": candidate_identity,
                "reader_identities": reader_identity_list,
                "closure_sha256": None,
            },
            "cases": {
                "s16_text_windows": {
                    "candidate": candidate_case,
                    "fixture": fixture,
                    "expected": expected,
                }
            },
            "cleanup": cleanup,
        }
        plan["manifest"]["closure_sha256"] = _closure_sha256(plan)
        validate(plan)
        (output / f"{target}.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def validate(plan: dict[str, object]) -> None:
    if set(plan) != {"format", "target", "manifest", "cases", "cleanup"} or plan.get(
        "format"
    ) != "pietto.phase77.flat-qualification-plan.v2":
        raise ValueError("wrong plan identity")
    target = plan.get("target")
    if target not in {"postgres", "mysql"}:
        raise ValueError("wrong target")
    cases = plan.get("cases")
    if not isinstance(cases, dict) or set(cases) != {"s16_text_windows"}:
        raise TypeError("missing case envelope")
    case = cases["s16_text_windows"]
    if not isinstance(case, dict) or set(case) != {"candidate", "fixture", "expected"}:
        raise TypeError("wrong case envelope")
    candidate, fixture, expected = (
        case["candidate"],
        case["fixture"],
        case["expected"],
    )
    if not isinstance(candidate, dict) or not isinstance(fixture, dict) or not isinstance(expected, dict):
        raise TypeError("missing case contents")
    if set(candidate) != {
        "source", "config", "contract", "artifact", "sql", "fixed_values",
        "parameter_uses", "columns",
    } or set(fixture) != {"ddl", "typed_seed"} or set(expected) != {
        "metadata", "values", "warnings", "terminal",
    }:
        raise ValueError("wrong case keys")
    if candidate.get("fixed_values") != [] or candidate.get("parameter_uses") != []:
        raise ValueError("unexpected execution bindings")
    columns = candidate.get("columns")
    if not isinstance(columns, list) or [column.get("label") for column in columns] != [
        "id", "previous_empty", "following_unicode", "following_null"
    ]:
        raise ValueError("unexpected public output columns")
    if [column.get("logical_type", {}).get("name") for column in columns] != [
        "Int", "Text", "Text", "Text"
    ]:
        raise ValueError("unexpected logical output types")
    if len(expected.get("values", ())) != len(SEED) or expected.get("warnings") != []:
        raise ValueError("incomplete independent oracle")
    manifest = plan.get("manifest")
    if not isinstance(manifest, dict) or set(manifest) != {
        "candidate_identity", "reader_identities", "closure_sha256"
    }:
        raise ValueError("missing input manifest")
    if not isinstance(manifest["reader_identities"], list) or not manifest[
        "reader_identities"
    ]:
        raise ValueError("missing reader identities")
    if manifest["closure_sha256"] != _closure_sha256(plan):
        raise ValueError("closure identity drift")
    if not isinstance(manifest["closure_sha256"], str) or len(manifest["closure_sha256"]) != 64:
        raise ValueError("invalid closure identity")
    metadata = expected["metadata"]
    if not isinstance(metadata, list) or len(metadata) != 4:
        raise ValueError("missing native metadata expectation")
    if target == "mysql" and any(
        item != {
            "ordinal": ordinal,
            "name": name,
            "type_code": 253,
            "flags": 0,
            "charset": 309,
            "python_type": "str",
            "nullable": True,
        }
        for ordinal, name, item in zip(
            (1, 2, 3),
            ("previous_empty", "following_unicode", "following_null"),
            metadata[1:],
            strict=True,
        )
    ):
        raise ValueError("MySQL Text metadata must stay text, not binary")


def _receipt(plan: dict[str, object]) -> dict[str, object]:
    cases = {}
    for name, item in plan["cases"].items():
        candidate, fixture, expected = (
            item["candidate"],
            item["fixture"],
            item["expected"],
        )
        cases[name] = {
            "sql": candidate["sql"],
            "parameters": candidate["fixed_values"],
            "parameter_uses": candidate["parameter_uses"],
            "fixture": fixture,
            "metadata": expected["metadata"],
            "values": expected["values"],
            "warnings": expected["warnings"],
            "terminal": expected["terminal"],
        }
    return {
        "format": plan["format"].replace("-plan.", "-receipt."),
        "target": plan["target"],
        "manifest": plan["manifest"],
        "cases": cases,
        "cleanup": plan["cleanup"],
    }


def judge_self_check(plan: dict[str, object], judge_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("p77_common_judge", judge_path)
    if spec is None or spec.loader is None:
        raise ValueError("common judge could not load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = _receipt(plan)
    module.judge(plan, receipt)
    changes = (
        lambda raw: raw["cases"]["s16_text_windows"]["metadata"].__setitem__(1, {
            **raw["cases"]["s16_text_windows"]["metadata"][1], "type_code": 252
        }),
        lambda raw: raw["cases"]["s16_text_windows"]["metadata"].__setitem__(1, {
            **raw["cases"]["s16_text_windows"]["metadata"][1], "flags": 128
        }),
        lambda raw: raw["cases"]["s16_text_windows"]["values"][2].__setitem__(3, "not-null"),
        lambda raw: raw["cases"]["s16_text_windows"]["values"].__setitem__(0, [1, "wrong", "雪", "雪"]),
        lambda raw: raw["cases"]["s16_text_windows"]["metadata"].reverse(),
        lambda raw: raw["cases"]["s16_text_windows"].__setitem__("grafted", {}),
        lambda raw: raw["cases"].__setitem__("extra", {}),
    )
    for change in changes:
        damaged = copy.deepcopy(receipt)
        change(damaged)
        try:
            module.judge(plan, damaged)
        except ValueError:
            continue
        raise AssertionError("common judge accepted damaged S16 receipt")


def plan_self_check(plan: dict[str, object]) -> None:
    validate(plan)
    changes = (
        lambda value: value["cases"]["s16_text_windows"]["candidate"].__setitem__(
            "source", "changed source"
        ),
        lambda value: value["cases"]["s16_text_windows"]["candidate"].__setitem__(
            "config", "changed config"
        ),
        lambda value: value["cases"]["s16_text_windows"]["candidate"].__setitem__(
            "sql", "SELECT changed"
        ),
        lambda value: value["cases"]["s16_text_windows"]["fixture"]["typed_seed"][
            "rows"
        ].__setitem__(0, [0]),
        lambda value: value["cases"]["s16_text_windows"]["expected"]["values"].__setitem__(
            0, [0]
        ),
    )
    for change in changes:
        damaged = copy.deepcopy(plan)
        change(damaged)
        try:
            validate(damaged)
        except ValueError:
            continue
        raise AssertionError("accepted a plan with changed closure input")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--judge-self-check", type=Path)
    args = parser.parse_args()
    if args.self_check:
        for target in ("postgres", "mysql"):
            plan_self_check(
                json.loads((args.output / f"{target}.json").read_text(encoding="utf-8"))
            )
        print("S16 qualification self-check passed")
        return
    if args.judge_self_check:
        for target in ("postgres", "mysql"):
            plan = json.loads((args.output / f"{target}.json").read_text(encoding="utf-8"))
            judge_self_check(plan, args.judge_self_check)
        print("S16 common-judge negative self-check passed")
        return
    if args.candidate_root is None:
        raise SystemExit("--candidate-root is required to materialize a plan")
    wheel = args.wheel.resolve() if args.wheel is not None else None
    if wheel is not None and not wheel.is_file():
        raise SystemExit("--wheel must name an existing wheel")
    build(args.candidate_root.resolve(), args.output.resolve(), wheel)
    print("S16 qualification plan prepared")


if __name__ == "__main__":
    main()
