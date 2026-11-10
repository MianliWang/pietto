#!/usr/bin/env python3
"""Materialize the Phase77 Decimal target-qualification inputs.

This script only runs Pietto's public project compiler.  It never opens a
database; the flat target runner owns connection, statement execution and raw
receipt capture.  Expected values are independently computed with Decimal.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = (
    {"id": -2, "flag": None, "text": "alpha", "money": "12.34", "ratio": "0.125"},
    {"id": 3, "flag": True, "text": "beta", "money": "-1.20", "ratio": "-2.500"},
)


def _render(value: Decimal, scale: int) -> str:
    with localcontext() as context:
        context.prec = 80
        return format(value.quantize(Decimal(1).scaleb(-scale)), "f")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_identity(path: Path, root: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "byte_count": len(data),
        "sha256": _sha256(data),
    }


def _candidate_code_identity(
    candidate_root: Path, wheel: Path | None, expected_tree: str | None
) -> dict[str, object]:
    files = sorted((candidate_root / "src" / "pietto").rglob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(candidate_root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    head = subprocess.run(
        ("git", "-C", str(candidate_root), "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    patch = subprocess.run(
        ("git", "-C", str(candidate_root), "diff", "--binary", "HEAD"),
        check=True,
        capture_output=True,
    ).stdout
    tree = subprocess.run(
        ("git", "-C", str(candidate_root), "write-tree"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if expected_tree is not None and tree != expected_tree:
        raise ValueError("candidate index tree differs from the frozen B2 tree")
    identity: dict[str, object] = {
        "git_head": head,
        "git_index_tree": tree,
        "dirty_patch_sha256": _sha256(patch),
        "source_file_count": len(files),
        "source_sha256": digest.hexdigest(),
    }
    if wheel is not None:
        data = wheel.read_bytes()
        identity["wheel"] = {
            "filename": wheel.name,
            "byte_count": len(data),
            "sha256": _sha256(data),
        }
    return identity


def _money(row: dict[str, object]) -> Decimal:
    return Decimal(str(row["money"]))


def _ratio(row: dict[str, object]) -> Decimal:
    return Decimal(str(row["ratio"]))


def _values(kind: str) -> tuple[list[str], list[list[str]], list[int]]:
    if kind == "decimal_int":
        return (
            ["added", "subtracted"],
            [[_render(_money(row) + Decimal(int(row["id"])), 2), _render(_money(row) - Decimal(int(row["id"])), 2)] for row in SEED],
            [2, 2],
        )
    if kind == "different_scale":
        return (
            ["added", "subtracted"],
            [[_render(_money(row) + _ratio(row), 3), _render(_money(row) - _ratio(row), 3)] for row in SEED],
            [3, 3],
        )
    if kind == "money_times_id":
        return (["result"], [[_render(_money(row) * Decimal(int(row["id"])), 2)] for row in SEED], [2])
    if kind == "id_times_money":
        return (["result"], [[_render(Decimal(int(row["id"])) * _money(row), 2)] for row in SEED], [2])
    if kind == "money_times_literal":
        return (["result"], [[_render(_money(row) * 2, 2)] for row in SEED], [2])
    if kind == "neg_money":
        return (["result"], [[_render(-_money(row), 2)] for row in SEED], [2])
    if kind == "pos_money":
        return (["result"], [[_render(+_money(row), 2)] for row in SEED], [2])
    if kind == "neg_product":
        return (["result"], [[_render(-(_money(row) * Decimal(int(row["id"]))), 2)] for row in SEED], [2])
    if kind == "edge_65_30":
        return (
            ["result"],
            [[_render(_money(row) * Decimal(int(row["id"])), 30)] for row in SEED],
            [30],
        )
    raise ValueError(f"unknown independent oracle {kind!r}")


def _case(name: str, body: str, oracle: str | None, *, source_change: str | None = None,
          contract_change: tuple[str, int, int] | None = None, terminal_policy: str,
          targets: tuple[str, ...] = ("postgres", "mysql")) -> dict[str, object]:
    return {
        "name": name,
        "body": body,
        "oracle": oracle,
        "source_change": source_change,
        "contract_change": contract_change,
        "terminal_policy": terminal_policy,
        "targets": targets,
    }


CASES = (
    _case(
        "decimal_int_add_sub",
        """table result:
    from rows
    select:
        added = money + id
        subtracted = money - id
""",
        "decimal_int",
        terminal_policy="must_success_no_warnings",
    ),
    _case(
        "different_scale_decimal_add_sub",
        """table result:
    from rows
    select:
        added = money + ratio
        subtracted = money - ratio
""",
        "different_scale",
        source_change="ratio: Float",
        contract_change=("ratio", 8, 3),
        terminal_policy="must_success_no_warnings",
    ),
    _case("decimal_times_int", "table result:\n    from rows\n    select:\n        result = money * id\n", "money_times_id", terminal_policy="must_success_no_warnings"),
    _case("int_times_decimal", "table result:\n    from rows\n    select:\n        result = id * money\n", "id_times_money", terminal_policy="must_success_no_warnings"),
    _case("decimal_times_literal", "table result:\n    from rows\n    select:\n        result = money * 2\n", "money_times_literal", terminal_policy="must_success_no_warnings"),
    _case("unary_minus_decimal", "table result:\n    from rows\n    select:\n        result = -money\n", "neg_money", terminal_policy="must_success_no_warnings"),
    _case("unary_plus_decimal", "table result:\n    from rows\n    select:\n        result = +money\n", "pos_money", terminal_policy="must_success_no_warnings"),
    _case("unary_minus_decimal_product", "table result:\n    from rows\n    select:\n        result = -(money * id)\n", "neg_product", terminal_policy="must_success_no_warnings"),
    _case(
        "precision_65_scale_30_product",
        "table result:\n    from rows\n    select:\n        result = money * id\n",
        "edge_65_30",
        source_change="money: Decimal(9, 2)",
        contract_change=("money", 46, 30),
        terminal_policy="must_success_no_warnings_exact_decimal_65_30",
    ),
    _case("sum_remains_refused", "table result:\n    from rows\n    select:\n        result = sum(money)\n", None, terminal_policy="compiler_blocked_no_sql", targets=("mysql",)),
    _case("int_producer_remains_refused", """table result:
    from rows
    let intermediate = id + 1
    select:
        result = money + intermediate
""", None, terminal_policy="compiler_blocked_no_sql", targets=("mysql",)),
    _case("decimal_float_remains_refused", "table result:\n    from rows\n    select:\n        result = money + ratio\n", None, terminal_policy="compiler_rejected_no_sql"),
    _case("decimal_division_remains_refused", "table result:\n    from rows\n    select:\n        result = money / 2\n", None, terminal_policy="compiler_blocked_no_sql"),
    _case(
        "precision_66_scale_30_remains_refused",
        "table result:\n    from rows\n    select:\n        result = money * id\n",
        None,
        source_change="money: Decimal(9, 2)",
        contract_change=("money", 47, 30),
        terminal_policy="compiler_blocked_no_sql_precision_overflow",
    ),
)


def _ddl(target: str, contract: dict[str, object]) -> list[str]:
    source = contract["sources"][0]
    fields = source["fields"]
    relation = source["relation"]
    names = [field["column"] for field in fields]
    money = next(field["representation"] for field in fields if field["name"] == "money")
    ratio = next(field["representation"] for field in fields if field["name"] == "ratio")
    money_type = money["storage"]
    ratio_type = ratio["storage"]
    if target == "postgres":
        table = f'"{relation["namespace"]}"."{relation["name"]}"'
        return [
            f'CREATE SCHEMA IF NOT EXISTS "{relation["namespace"]}"',
            f'CREATE TABLE {table} ("{names[0]}" BIGINT NOT NULL, "{names[1]}" BOOLEAN NULL, "{names[2]}" TEXT COLLATE "C" NOT NULL, "{names[3]}" NUMERIC({money_type["precision"]}, {money_type["scale"]}) NOT NULL, "{names[4]}" ' + (f'NUMERIC({ratio_type["precision"]}, {ratio_type["scale"]})' if ratio_type["kind"] == "pg_numeric" else "DOUBLE PRECISION") + " NOT NULL)",
        ]
    table = f'`{relation["namespace"]}`.`{relation["name"]}`'
    return [
        f'CREATE DATABASE IF NOT EXISTS `{relation["namespace"]}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin',
        f'CREATE TABLE {table} (`{names[0]}` BIGINT NOT NULL, `{names[1]}` BOOLEAN NULL, `{names[2]}` VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL, `{names[3]}` DECIMAL({money_type["precision"]}, {money_type["scale"]}) NOT NULL, `{names[4]}` ' + (f'DECIMAL({ratio_type["precision"]}, {ratio_type["scale"]})' if ratio_type["kind"] == "my_decimal" else "DOUBLE") + " NOT NULL)",
    ]


def _seed(target: str, contract: dict[str, object], decimal_ratio: bool) -> dict[str, object]:
    relation = contract["sources"][0]["relation"]
    table = (f'"{relation["namespace"]}"."{relation["name"]}"' if target == "postgres" else f'`{relation["namespace"]}`.`{relation["name"]}`')
    columns = [field["column"] for field in contract["sources"][0]["fields"]]
    quote = (lambda value: f'"{value}"') if target == "postgres" else (lambda value: f'`{value}`')
    placeholders = [f'${index}' for index in range(1, 6)] if target == "postgres" else ["%s"] * 5
    values = []
    for row in SEED:
        values.append([row["id"], row["flag"], row["text"], {"decimal": row["money"]}, {"decimal": row["ratio"]} if decimal_ratio else float(row["ratio"])])
    return {
        "sql": f"INSERT INTO {table} ({', '.join(quote(column) for column in columns)}) VALUES ({', '.join(placeholders)})",
        "rows": values,
        "row_order": "bag: emitted SELECT has no reviewed ordering; compare multiplicity-preserving unordered rows",
    }


def _load_compiler(candidate_root: Path) -> Any:
    sys.path[:0] = [str(candidate_root / "tests"), str(candidate_root)]
    import _pietto_sql_emission as emission
    from pietto._project.project_sql_emission import serialize_project_sql_emission
    return emission, serialize_project_sql_emission


def _identities(
    candidate_root: Path, candidate_identity: dict[str, object], source: str, config: str, contract: str, artifact: bytes
) -> dict[str, object]:
    return {
        "candidate_code": candidate_identity,
        "source": {"byte_count": len(source.encode("utf-8")), "sha256": _sha256(source.encode("utf-8"))},
        "configuration": {"byte_count": len(config.encode("utf-8")), "sha256": _sha256(config.encode("utf-8"))},
        "contract": {"byte_count": len(contract.encode("utf-8")), "sha256": _sha256(contract.encode("utf-8"))},
        "public_artifact": {"byte_count": len(artifact), "sha256": _sha256(artifact)},
        "readers": {
            "public_fixture_decoder": _file_identity(candidate_root / "tests" / "_pietto_sql_emission.py", candidate_root),
            "pure_boundary": _file_identity(candidate_root / "src" / "pietto" / "_project" / "project_sql_emission_pure_boundary.py", candidate_root),
            "portable_observer": _file_identity(candidate_root / "src" / "pietto" / "_project" / "project_sql_emission_portable.py", candidate_root),
            "compiled_replay": _file_identity(candidate_root / "tests" / "test_execution_compiled_families.py", candidate_root),
        },
    }


def _mutate(item: dict[str, object], spec: dict[str, object], target: str) -> tuple[str, str, bool]:
    source = str(item["source"])
    changed = spec["source_change"]
    decimal_ratio = changed == "ratio: Float"
    if changed is not None:
        field, precision, scale = spec["contract_change"]
        source = source.replace(str(changed), f"{field}: Decimal({precision}, {scale})")
    contract = json.loads(str(item["contract"]))
    if spec["contract_change"] is not None:
        field, precision, scale = spec["contract_change"]
        representation = next(value["representation"] for value in contract["sources"][0]["fields"] if value["name"] == field)
        representation["storage"] = {"kind": "pg_numeric" if target == "postgres" else "my_decimal", "precision": precision, "scale": scale}
        representation["domain"] = {"kind": "decimal", "precision": precision, "scale": scale}
    return source, json.dumps(contract, separators=(",", ":")), decimal_ratio


def _expected(spec: dict[str, object]) -> dict[str, object] | None:
    if spec["oracle"] is None:
        return None
    labels, rows, scales = _values(str(spec["oracle"]))
    precisions = {
        "decimal_int": [22, 22],
        "different_scale": [11, 11],
        "money_times_id": [28],
        "id_times_money": [28],
        "money_times_literal": [28],
        "neg_money": [9],
        "pos_money": [9],
        "neg_product": [28],
        "edge_65_30": [65],
    }[str(spec["oracle"])]
    nullable = (
        [False]
        if spec["oracle"] in {"neg_money", "pos_money"}
        else ["unknown"] * len(labels)
    )
    return {"labels": labels, "logical": ["Decimal"] * len(labels), "nullable": nullable, "precision": precisions, "scale": scales, "rows": rows, "warnings": []}


def _metadata(target: str, columns: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "ordinal": column["ordinal"],
            "name": column["label"],
            "type_code": 1700 if target == "postgres" else 246,
            "flags": 0,
            "charset": None if target == "postgres" else 63,
            "python_type": "Decimal",
            "nullable": column["nullable"],
        }
        for column in columns
    ]


def _closure_sha256(value: dict[str, object]) -> str:
    path = Path("/tmp/pietto-p77-flat-qualification/judge.py")
    spec = importlib.util.spec_from_file_location("p77_common_judge", path)
    if spec is None or spec.loader is None:
        raise ValueError("common qualification judge is unavailable")
    judge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge)
    unsigned = value | {"manifest": value["manifest"] | {"closure_sha256": None}}
    return judge.digest(unsigned)


def _flat_plan(target: str, materialized: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    positive, terminals = {}, {}
    first = next(iter(materialized["cases"].values()))["candidate"]
    for name, envelope in materialized["cases"].items():
        candidate, expected = envelope["candidate"], envelope["expected"]
        if expected is None:
            terminals[name] = envelope
            continue
        positive[name] = {
            "candidate": {
                "source": candidate["source"],
                "config": candidate["configuration"],
                "contract": candidate["contract"],
                "artifact": candidate["public_artifact"],
                "sql": candidate["sql"],
                "fixed_values": candidate["fixed_values"],
                "parameter_uses": candidate["parameter_uses"],
                "columns": candidate["columns"],
            },
            "fixture": {"ddl": candidate["ddl"], "typed_seed": candidate["seed"]},
            "expected": {
                "metadata": _metadata(target, candidate["columns"]),
                "values": expected["rows"],
                "warnings": expected["warnings"],
                "terminal": {"kind": "rowset_eof", "close": "clean", "buffered_row_error": None},
            },
        }
    manifest = {
        "candidate_identity": first["identities"]["candidate_code"],
        "reader_identities": [
            {"name": name, **identity}
            for name, identity in first["identities"]["readers"].items()
        ],
        "closure_sha256": None,
    }
    plan = {
        "format": "pietto.phase77.decimal-qualification-plan.v2",
        "target": target,
        "manifest": manifest,
        "cases": positive,
        "cleanup": {
            "connection": "closed",
            "relations": "dropped",
            "transaction": "rolled_back",
        },
    }
    plan["manifest"]["closure_sha256"] = _closure_sha256(plan)
    return plan, {"format": "pietto.phase77.decimal-compiler-terminals.v1", "target": target, "cases": terminals}


def build(
    candidate_root: Path, output: Path, wheel: Path | None, expected_tree: str | None
) -> None:
    emission, serialize = _load_compiler(candidate_root)
    candidate_identity = _candidate_code_identity(candidate_root, wheel, expected_tree)
    output.mkdir(parents=True, exist_ok=True)
    for target in ("postgres", "mysql"):
        cases: dict[str, object] = {}
        for spec in CASES:
            if target not in spec["targets"]:
                continue
            item = emission.parameterized_fixture(target, spec["body"], protocol=False)
            source, contract_text, decimal_ratio = _mutate(item, spec, target)
            with tempfile.TemporaryDirectory() as directory:
                checked, outcome = emission.build_case(Path(directory), source, contract_text)
                if not checked.verified and not str(spec["terminal_policy"]).startswith("compiler_"):
                    raise ValueError(f"{target}/{spec['name']}: project check did not verify")
                public_artifact = serialize(outcome)
                document = json.loads(public_artifact)
            candidate: dict[str, object] = {
                "compiler_provenance": {
                    "entry": "tests._pietto_sql_emission.parameterized_fixture -> build_case -> serialize_project_sql_emission",
                    "fixture": "G_emission_table_bag/bag",
                },
                "source": source,
                "configuration": emission.CONFIG,
                "contract": json.loads(contract_text),
                "public_artifact": public_artifact.decode("utf-8"),
                "identities": _identities(
                    candidate_root,
                    candidate_identity,
                    source,
                    emission.CONFIG,
                    contract_text,
                    public_artifact,
                ),
                "compiler_status": outcome.status,
                "diagnostics": document.get("diagnostics", []),
                "blockers": [{"code": item.code, "detail": item.detail} for item in outcome.blockers],
            }
            if outcome.artifact is not None:
                candidate.update(
                    sql=document["sql"],
                    fixed_values=document["fixed_values"],
                    parameter_uses=document["parameter_uses"],
                    columns=document["columns"],
                    ddl=_ddl(target, candidate["contract"]),
                    seed=_seed(target, candidate["contract"], decimal_ratio),
                    execute={"comparison": "bag", "parameters": []},
                )
            cases[spec["name"]] = {"candidate": candidate, "expected": _expected(spec), "terminal_policy": spec["terminal_policy"]}
        materialized = {"artifact": "pietto.phase77.decimal_target_qualification.v1", "target": target, "cases": cases}
        validate_materialized(materialized)
        plan, terminals = _flat_plan(target, materialized)
        validate(plan)
        (output / f"{target}.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output / f"{target}.compiler-terminals.json").write_text(json.dumps(terminals, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_materialized(plan: dict[str, object]) -> None:
    if plan.get("artifact") != "pietto.phase77.decimal_target_qualification.v1" or plan.get("target") not in {"postgres", "mysql"}:
        raise ValueError("wrong Decimal qualification plan identity")
    cases = plan.get("cases")
    if not isinstance(cases, dict) or set(cases) != {
        str(spec["name"]) for spec in CASES if plan["target"] in spec["targets"]
    }:
        raise ValueError("wrong Decimal qualification case closure")
    for name, envelope in cases.items():
        candidate, expected, terminal = envelope["candidate"], envelope["expected"], envelope["terminal_policy"]
        if candidate.get("compiler_provenance", {}).get("entry") != "tests._pietto_sql_emission.parameterized_fixture -> build_case -> serialize_project_sql_emission":
            raise ValueError(f"{name}: missing public compile provenance")
        identities = candidate.get("identities")
        if not isinstance(identities, dict):
            raise TypeError(f"{name}: missing candidate/source/config/artifact/reader identities")
        for field, value in (
            ("source", candidate["source"].encode("utf-8")),
            ("configuration", candidate["configuration"].encode("utf-8")),
            ("contract", json.dumps(candidate["contract"], separators=(",", ":")).encode("utf-8")),
            ("public_artifact", candidate["public_artifact"].encode("utf-8")),
        ):
            identity = identities.get(field)
            if not isinstance(identity, dict) or identity != {"byte_count": len(value), "sha256": _sha256(value)}:
                raise ValueError(f"{name}: {field} identity drift")
        readers = identities.get("readers")
        if not isinstance(readers, dict) or set(readers) != {
            "public_fixture_decoder", "pure_boundary", "portable_observer", "compiled_replay"
        } or not all(
            isinstance(value, dict)
            and set(value) == {"path", "byte_count", "sha256"}
            and isinstance(value["path"], str)
            and type(value["byte_count"]) is int
            and isinstance(value["sha256"], str)
            and len(value["sha256"]) == 64
            for value in readers.values()
        ):
            raise ValueError(f"{name}: reader identity closure")
        if terminal.startswith("must_success"):
            if candidate["compiler_status"] != "VERIFIED" or expected is None:
                raise ValueError(f"{name}: success case lacks a verified public artifact")
            if candidate["fixed_values"] != [] or candidate["parameter_uses"] != []:
                raise ValueError(f"{name}: fixture unexpectedly needs binds")
            if not candidate["sql"] or not candidate["ddl"] or len(candidate["seed"]["rows"]) != len(SEED):
                raise ValueError(f"{name}: target execution input is incomplete")
            if candidate["execute"] != {"comparison": "bag", "parameters": []}:
                raise ValueError(f"{name}: target row comparison is not fixed")
            if expected["warnings"] != [] or any(value not in {False, "unknown"} for value in expected["nullable"]):
                raise ValueError(f"{name}: independent result oracle is incomplete")
            columns = candidate["columns"]
            spec = next(value for value in CASES if value["name"] == name)
            if expected != _expected(spec):
                raise ValueError(f"{name}: independent value/scale oracle drift")
            if (
                [column["label"] for column in columns] != expected["labels"]
                or [column["logical_type"]["name"] for column in columns] != expected["logical"]
                or [column["nullable"] for column in columns] != expected["nullable"]
                or [column["representation"]["domain"]["precision"] for column in columns] != expected["precision"]
                or [column["representation"]["domain"]["scale"] for column in columns] != expected["scale"]
            ):
                raise ValueError(f"{name}: emitted carrier differs from the independent oracle")
        elif terminal.startswith("compiler_"):
            if candidate["compiler_status"] not in {"BLOCKED", "INPUT_REJECTED"} or expected is not None:
                raise ValueError(f"{name}: rejected case reached the target")
            if "sql" in candidate:
                raise ValueError(f"{name}: rejected case carries emitted SQL")
        else:
            raise ValueError(f"{name}: unknown terminal policy")


def validate(plan: dict[str, object]) -> None:
    if set(plan) != {"format", "target", "manifest", "cases", "cleanup"} or plan["format"] != "pietto.phase77.decimal-qualification-plan.v2" or plan["target"] not in {"postgres", "mysql"}:
        raise ValueError("wrong flat Decimal plan identity")
    manifest = plan["manifest"]
    if set(manifest) != {"candidate_identity", "reader_identities", "closure_sha256"} or manifest["closure_sha256"] != _closure_sha256(plan):
        raise ValueError("flat Decimal manifest closure")
    if not manifest["candidate_identity"] or not isinstance(manifest["reader_identities"], list) or not manifest["reader_identities"]:
        raise ValueError("flat Decimal identity closure")
    if plan["cleanup"] != {"connection": "closed", "relations": "dropped", "transaction": "rolled_back"}:
        raise ValueError("flat Decimal cleanup authority")
    required_candidate = {"source", "config", "contract", "artifact", "sql", "fixed_values", "parameter_uses", "columns"}
    for name, item in plan["cases"].items():
        if set(item) != {"candidate", "fixture", "expected"} or set(item["candidate"]) != required_candidate:
            raise ValueError(f"{name}: flat case shape")
        if set(item["fixture"]) != {"ddl", "typed_seed"} or set(item["expected"]) != {"metadata", "values", "warnings", "terminal"}:
            raise ValueError(f"{name}: flat fixture or expected shape")
        if item["expected"]["terminal"] != {"kind": "rowset_eof", "close": "clean", "buffered_row_error": None}:
            raise ValueError(f"{name}: flat terminal")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--expected-tree")
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        for target in ("postgres", "mysql"):
            plan = json.loads((args.output / f"{target}.json").read_text(encoding="utf-8"))
            validate(plan)
            case = next(iter(plan["cases"]))
            for mutate in (
                lambda item: item["expected"]["values"].__setitem__(0, ["0"] * len(item["expected"]["values"][0])),
                lambda item: item["expected"]["metadata"][0].__setitem__("type_code", 8),
                lambda item: item["candidate"].__setitem__("source", "grafted source"),
            ):
                tampered = copy.deepcopy(plan)
                mutate(tampered["cases"][case])
                try:
                    validate(tampered)
                except ValueError:
                    continue
                raise AssertionError("Decimal manifest accepted a value, metadata or source graft")
        print("decimal qualification self-check passed")
    else:
        if args.candidate_root is None:
            raise SystemExit("--candidate-root is required to materialize a plan")
        wheel = args.wheel.resolve() if args.wheel is not None else None
        if wheel is not None and not wheel.is_file():
            raise SystemExit("--wheel must name the frozen candidate wheel")
        build(
            args.candidate_root.resolve(),
            args.output.resolve(),
            wheel,
            args.expected_tree,
        )
        print("decimal qualification plan prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
