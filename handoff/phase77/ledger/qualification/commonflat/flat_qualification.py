"""Materialize closed Phase77 flat qualification plans without a database."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
from judge import PLAN_FORMAT  # noqa: E402


CLEANUP = {"connection": "closed", "relations": "dropped", "transaction": "rolled_back"}
CASE_NAMES = ("s10_group", "s12_text", "s12_temporal", "s14_join")
EXPECTED = {
    "s10_group": ((2, False, True), (0, False, False), (0, False, False)),
    "s12_text": (("x-", "00x"), ("雪-", "00雪"), (None, None)),
    "s12_temporal": (("2024-02-29", {"kind": "utc_timestamp6"}),),
    "s14_join": ((1, 1), (2, 0)),
}
SEEDS = {
    "s10_group": {"agg": (
        (1, 0, True, "a", {"decimal": "0.00"}, 0.0, 1),
        (1, 0, True, "a", {"decimal": "0.00"}, 0.0, 2),
        (1, 0, False, "b", {"decimal": "0.00"}, 0.0, 3),
        (1, None, None, None, {"decimal": "0.00"}, 0.0, 4),
        (2, 0, False, "b", {"decimal": "0.00"}, 0.0, 5),
        (2, None, None, None, {"decimal": "0.00"}, 0.0, 6),
        (3, None, None, None, {"decimal": "0.00"}, 0.0, 7),
    )},
    "s12_text": {"rows": (
        (1, True, "x", {"decimal": "0.00"}, 0.0),
        (2, False, "雪", {"decimal": "0.00"}, 0.0),
        (3, None, None, {"decimal": "0.00"}, 0.0),
    )},
    "s12_temporal": {"rows": ((1, "2024-01-31T00:00:00.000000", None, "2024-01-31", None, "00000000-0000-0000-0000-000000000001"),)},
    "s14_join": {"lhs": ((1, 1, "left"), (2, 2, "left")), "rhs": ((1, 1, "UP"),)},
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def imports(repo: Path):
    for directory in (repo / "src", repo / "tests"):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    import _pietto_sql_emission as emission
    from pietto._project import project_sql_emission
    return emission, project_sql_emission


def mark_nullable(contract: dict[str, object], source_name: str, field_name: str) -> None:
    source = next(item for item in contract["sources"] if item["selector"]["name"] == source_name)
    next(item for item in source["fields"] if item["name"] == field_name)["representation"]["nullable"] = True


def temporal_contract(emission, target: str) -> dict[str, object]:
    contract = json.loads(emission.fixture(target, "T_row_direct", "table_preserve")["contract"])
    physical = {
        "Int": ({"kind": "pg_int4" if target == "postgres" else "my_int"}, {"kind": "int_range", "min": "-2147483648", "max": "2147483647"}),
        "Timestamp": ({"kind": "pg_timestamp" if target == "postgres" else "my_datetime", "fractional_seconds": 6}, {"kind": "timestamp"}),
        "Date": ({"kind": "pg_date" if target == "postgres" else "my_date"}, {"kind": "date"}),
        "UUID": ({"kind": "pg_uuid" if target == "postgres" else "my_uuid_bytes"}, {"kind": "uuid", "encoding": "standard_bytes"}),
    }
    fields = (("id", "Int", False), ("ts", "Timestamp", False), ("ts2", "Timestamp", True), ("d", "Date", False), ("d2", "Date", True), ("u", "UUID", False))
    contract["sources"][0]["fields"] = [
        {"ordinal": index, "name": name, "column": name, "representation": {"storage": physical[kind][0], "domain": physical[kind][1], "nullable": nullable}}
        for index, (name, kind, nullable) in enumerate(fields)
    ]
    return contract


def quote(target: str, value: str) -> str:
    return f'"{value}"' if target == "postgres" else f'`{value}`'


def table(target: str, relation: dict[str, str]) -> str:
    return f"{quote(target, relation['namespace'])}.{quote(target, relation['name'])}"


def sql_type(target: str, representation: dict[str, object]) -> str:
    storage = representation["storage"]
    kind = storage["kind"]
    choices = {
        "pg_int8": "BIGINT", "my_bigint": "BIGINT", "pg_int4": "INTEGER", "my_int": "INT",
        "pg_bool": "BOOLEAN", "my_signed_bool": "TINYINT(1)", "my_bool01": "TINYINT(1)", "pg_float8": "DOUBLE PRECISION", "my_double": "DOUBLE",
        "pg_date": "DATE", "my_date": "DATE", "pg_uuid": "UUID", "my_uuid_bytes": "BINARY(16)",
        "pg_text": 'TEXT COLLATE "C"', "my_varchar": "VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
        "pg_timestamp": "TIMESTAMP(6)", "my_datetime": "DATETIME(6)",
    }
    if kind in {"pg_numeric", "my_decimal"}:
        return ("NUMERIC" if target == "postgres" else "DECIMAL") + f"({storage['precision']}, {storage['scale']})"
    if kind not in choices:
        raise ValueError(f"unsupported fixture storage {kind!r}")
    return choices[kind]


def fixture(target: str, contract: dict[str, object], rows: dict[str, tuple[tuple[object, ...], ...]]) -> dict[str, object]:
    sources = contract["sources"]
    namespaces = {item["relation"]["namespace"] for item in sources}
    if len(namespaces) != 1:
        raise ValueError("fixture namespaces")
    namespace = next(iter(namespaces))
    ddl = ([f'CREATE SCHEMA IF NOT EXISTS "{namespace}"'] if target == "postgres" else [f"CREATE DATABASE IF NOT EXISTS `{namespace}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin"])
    statements = []
    for source in sources:
        fields = source["fields"]
        ddl.append("CREATE TABLE " + table(target, source["relation"]) + " (" + ", ".join(
            f"{quote(target, field['column'])} {sql_type(target, field['representation'])} {'NULL' if field['representation']['nullable'] else 'NOT NULL'}" for field in fields) + ")")
        placeholders = [f"${index}" for index in range(1, len(fields) + 1)] if target == "postgres" else ["%s"] * len(fields)
        statements.append({"sql": f"INSERT INTO {table(target, source['relation'])} ({', '.join(quote(target, field['column']) for field in fields)}) VALUES ({', '.join(placeholders)})", "columns": [
            {"ordinal": field["ordinal"], "name": field["column"], "storage": field["representation"]["storage"], "nullable": field["representation"]["nullable"]} for field in fields], "rows": [list(row) for row in rows[source["selector"]["name"]]]})
    return {"ddl": ddl, "typed_seed": {"statements": statements}}


def metadata(target: str, columns: list[dict[str, object]]) -> list[dict[str, object]]:
    codes = {"postgres": {"Int": 20, "Bool": 16, "Text": 25, "Date": 1082, "Timestamp": 1114}, "mysql": {"Int": 8, "Bool": 1, "Text": 253, "Date": 10, "Timestamp": 12}}[target]
    python = {"Int": "int", "Bool": "bool", "Text": "str", "Date": "str", "Timestamp": "str"}
    return [{"ordinal": item["ordinal"], "name": item["label"], "type_code": codes[item["logical_type"]["name"]], "flags": 0, "charset": 309 if target == "mysql" and item["logical_type"]["name"] == "Text" else (63 if target == "mysql" else None), "python_type": python[item["logical_type"]["name"]], "nullable": item["nullable"]} for item in columns]


def manifest(repo: Path, emission, reader, wheel: Path | None) -> dict[str, object]:
    def git(*args: str) -> str:
        result = subprocess.run(("git", "-C", str(repo), *args), text=True, capture_output=True, check=False)
        if result.returncode:
            raise ValueError("candidate repository identity")
        return result.stdout
    try:
        head = git("rev-parse", "HEAD").strip()
        tree = git("write-tree").strip()
        patch = git("diff", "--binary", "HEAD")
        untracked = [line for line in git("ls-files", "--others", "--exclude-standard").splitlines() if line]
    except ValueError:
        raise ValueError("candidate repository needs a Git tree identity")
    untracked_bytes = []
    for relative in untracked:
        path = repo / relative
        if path.is_file():
            untracked_bytes.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    readers = [{"identity": identity, "sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()} for identity, module in (("tests._pietto_sql_emission", emission), ("pietto._project.project_sql_emission.serialize_project_sql_emission", reader))]
    candidate_identity: dict[str, object] = {"kind": "git_head_index_tree_worktree", "head": head, "tree": tree, "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(), "untracked": untracked_bytes}
    if wheel is not None:
        candidate_identity["wheel"] = {"name": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
    return {"candidate_identity": candidate_identity, "reader_identities": readers}


def document(outcome, serialize, directory: Path, contract: dict[str, object]) -> dict[str, object]:
    public = json.loads(serialize(outcome))
    return {"source": (directory / "main.pietto").read_text(encoding="utf-8"), "config": (directory / "pietto.toml").read_text(encoding="utf-8"), "contract": contract, "artifact": {"format": "project_sql_emission", "sha256": digest(public)}, "sql": public["sql"], "fixed_values": public["fixed_values"], "parameter_uses": public["parameter_uses"], "columns": public["columns"]}


def add_case(cases: dict[str, object], name: str, outcome, serialize, directory: Path, contract: dict[str, object], target: str) -> None:
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        raise ValueError(f"{name}: candidate compiler did not verify")
    candidate = document(outcome, serialize, directory, contract)
    cases[name] = {"candidate": candidate, "fixture": fixture(target, contract, SEEDS[name]), "expected": {"metadata": metadata(target, candidate["columns"]), "values": [list(row) for row in EXPECTED[name]], "warnings": [], "terminal": {"kind": "rowset_eof", "close": "clean", "buffered_row_error": None}}}


def compile_cases(repo: Path, directory: Path, target: str, wheel: Path | None = None) -> dict[str, object]:
    emission, reader = imports(repo)
    serialize = reader.serialize_project_sql_emission
    directory.mkdir(parents=True, exist_ok=True)
    cases: dict[str, object] = {}
    item = emission.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    contract = json.loads(item["contract"])
    mark_nullable(contract, "agg", "label")
    source = emission.AGGREGATE_HEADER.format(target=target).replace("label: Text\n", "label: Text | None\n") + "query result:\n    from agg\n    group by:\n        key\n    select:\n        n = sum(1 for o in group if o.flag)\n        a = all(o.flag for o in group)\n        b = any(o.label == \"a\" for o in group)\n"
    _, outcome = emission.build_case(directory / "s10_group", source, json.dumps(contract), item["policy"])
    add_case(cases, "s10_group", outcome, serialize, directory / "s10_group", contract, target)
    item = emission.parameterized_fixture(target, "table result:\n    from rows\n    select:\n        joined = concat(text, \"-\")\n        padded = lpad(text, 3, \"0\")\n", "preserve_literals", protocol=False)
    contract = json.loads(item["contract"])
    mark_nullable(contract, "rows", "text")
    source = item["source"].replace("text: Text\n", "text: Text | None\n", 1)
    _, outcome = emission.build_case(directory / "s12_text", source, json.dumps(contract), item["policy"])
    add_case(cases, "s12_text", outcome, serialize, directory / "s12_text", contract, target)
    contract = temporal_contract(emission, target)
    source = "shape Row:\n    id: Int\n    ts: Timestamp\n    ts2: Timestamp | None\n    d: Date\n    d2: Date | None\n    u: UUID\nsource rows: Row = " + target + ".table(\"opaque.locator.not.sql\")\ntable result:\n    from rows\n    select:\n        moved = add_months(d, 1)\n        seen = now()\n"
    _, outcome = emission.build_case(directory / "s12_temporal", source, json.dumps(contract), "preserve_literals")
    add_case(cases, "s12_temporal", outcome, serialize, directory / "s12_temporal", contract, target)
    body = "query result:\n    from lhs\n    let r = rhs\n    left join r on lhs.id == r.id\n    group by lhs.id\n    select:\n        a = lhs.id\n        n = count(lower(r.label))\n"
    item = emission.labelled_join_witness(target, body)
    contract = json.loads(item["contract"])
    _, outcome = emission.build_case(directory / "s14_join", item["source"], item["contract"], item["policy"])
    add_case(cases, "s14_join", outcome, serialize, directory / "s14_join", contract, target)
    base_manifest = manifest(repo, emission, reader, wheel)
    unsigned = {"format": PLAN_FORMAT, "target": target, "manifest": base_manifest | {"closure_sha256": None}, "cases": cases, "cleanup": CLEANUP}
    return unsigned | {"manifest": base_manifest | {"closure_sha256": digest(unsigned)}}


def self_check(repo: Path, compile_check: bool) -> None:
    if set(EXPECTED) != set(CASE_NAMES) or set(SEEDS) != set(CASE_NAMES):
        raise ValueError("pack inventory")
    if compile_check:
        with tempfile.TemporaryDirectory() as root:
            for target in ("postgres", "mysql"):
                if tuple(compile_cases(repo, Path(root) / target, target)["cases"]) != CASE_NAMES:
                    raise ValueError("compiler inventory")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", choices=("postgres", "mysql"))
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--compile-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check(args.repo.resolve(), args.compile_check)
    if args.write_plan:
        if args.target is None:
            raise SystemExit("--target is required with --write-plan")
        wheel = None if args.wheel is None else args.wheel.resolve()
        if wheel is not None and not wheel.is_file():
            raise SystemExit("--wheel must name an existing wheel")
        args.write_plan.write_text(json.dumps(compile_cases(args.repo.resolve(), args.write_plan.parent / "build", args.target, wheel), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
