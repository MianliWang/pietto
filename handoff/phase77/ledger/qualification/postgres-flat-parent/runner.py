"""Phase77 PostgreSQL flat-plan parent.

The only database entry point is ``observe``.  It consumes frozen B3 inputs,
does not derive SQL from expectations, and delegates the connection work to a
fresh interpreter installed from the frozen wheel.  ``self-check`` and
``preflight`` are deliberately database-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMMON_JUDGE = HERE / "common_judge.py"
WORKER = HERE / "worker.py"
FREEZE_FORMAT = "pietto.phase77.flat-postgres-freeze.v1"
PLAN_SUFFIX = "-qualification-plan.v2"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def load_judge():
    namespace: dict[str, object] = {"__name__": "p77_common_judge"}
    exec(compile(COMMON_JUDGE.read_bytes(), str(COMMON_JUDGE), "exec"), namespace)
    return namespace


def validate_plan(path: Path) -> dict[str, object]:
    plan = load_json(path)
    require(type(plan) is dict, f"{path}: plan object")
    require(type(plan.get("format")) is str and plan["format"].startswith("pietto.phase77.") and plan["format"].endswith(PLAN_SUFFIX), f"{path}: plan format")
    require(plan.get("target") == "postgres", f"{path}: PostgreSQL plan required")
    require(set(plan) == {"format", "target", "manifest", "cases", "cleanup"}, f"{path}: plan envelope")
    manifest = plan["manifest"]
    require(type(manifest) is dict and set(manifest) == {"candidate_identity", "reader_identities", "closure_sha256"}, f"{path}: manifest")
    unsigned = plan | {"manifest": manifest | {"closure_sha256": None}}
    require(manifest["closure_sha256"] == hashlib.sha256(canonical(unsigned)).hexdigest(), f"{path}: closure")
    cases = plan["cases"]
    require(type(cases) is dict and cases, f"{path}: cases")
    for name, case in cases.items():
        require(type(name) is str and type(case) is dict and set(case) == {"candidate", "fixture", "expected"}, f"{path}: case envelope")
        candidate = case["candidate"]
        fixture = case["fixture"]
        expected = case["expected"]
        require(type(candidate) is dict and set(candidate) == {"source", "config", "contract", "artifact", "sql", "fixed_values", "parameter_uses", "columns"}, f"{path}: {name}: candidate")
        require(type(fixture) is dict and set(fixture) == {"ddl", "typed_seed"}, f"{path}: {name}: fixture")
        require(type(expected) is dict and set(expected) == {"metadata", "values", "warnings", "terminal"}, f"{path}: {name}: expected")
        require(type(candidate["source"]) is str and type(candidate["config"]) is str and type(candidate["sql"]) is str, f"{path}: {name}: source inputs")
        require(type(candidate["fixed_values"]) is list and type(candidate["parameter_uses"]) is list, f"{path}: {name}: bindings")
        declarations = re.findall(r"^(?:table|query) ([A-Za-z_][A-Za-z0-9_]*)\\s*:", candidate["source"], re.MULTILINE)
        require(len(declarations) == 1, f"{path}: {name}: public declaration")
    return plan


def validate_freeze(path: Path, plans: list[Path], wheel: Path) -> dict[str, object]:
    freeze = load_json(path)
    require(type(freeze) is dict and set(freeze) == {"format", "candidate_tree", "wheel_sha256", "plans"}, "freeze envelope")
    require(freeze["format"] == FREEZE_FORMAT, "freeze format")
    require(type(freeze["candidate_tree"]) is str and re.fullmatch(r"[0-9a-f]{40}", freeze["candidate_tree"]) is not None, "freeze candidate tree")
    require(freeze["wheel_sha256"] == sha256(wheel), "freeze wheel")
    recorded = freeze["plans"]
    require(type(recorded) is dict and set(recorded) == {path.name for path in plans}, "freeze plan inventory")
    for plan in plans:
        require(recorded[plan.name] == sha256(plan), f"freeze plan hash: {plan.name}")
    return freeze


def preflight(freeze: Path, plans: list[Path], wheel: Path) -> dict[str, object]:
    require(COMMON_JUDGE.is_file() and WORKER.is_file(), "parent files")
    require(wheel.is_file(), "wheel")
    documents = [validate_plan(path) for path in plans]
    require(len({name for document in documents for name in document["cases"]}) == sum(len(document["cases"]) for document in documents), "case collision")
    frozen = validate_freeze(freeze, plans, wheel)
    return {"freeze": frozen, "plans": {path.name: sha256(path) for path in plans}, "wheel_sha256": sha256(wheel)}


def observe(freeze: Path, plans: list[Path], wheel: Path, python: Path, endpoint: Path, output: Path) -> None:
    facts = preflight(freeze, plans, wheel)
    require(python.is_file() and endpoint.is_file(), "candidate Python or endpoint")
    require(not output.exists(), "owned output already exists")
    output.mkdir(mode=0o700, parents=True)
    (output / "preflight.json").write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [str(python), "-I", "-B", str(WORKER), "--wheel", str(wheel), "--endpoint", str(endpoint), "--output", str(output), *sum((["--plan", str(plan)] for plan in plans), [])]
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "UV_PYTHON": "3.13.13", "UV_OFFLINE": "1"}
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=900, env=environment, check=False)
    except subprocess.TimeoutExpired as error:
        (output / "worker.stderr").write_text((error.stderr or "") if isinstance(error.stderr, str) else "", encoding="utf-8")
        raise RuntimeError("worker timeout; child was reaped") from error
    (output / "worker.stdout").write_text(completed.stdout, encoding="utf-8")
    (output / "worker.stderr").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"worker failed: {completed.returncode}")
    receipt = output / "receipt.json"
    require(receipt.is_file(), "worker receipt")
    judge = load_judge()["judge"]
    for plan in plans:
        # The worker's per-plan receipt is the only document the common judge sees.
        raw = output / (plan.stem + ".receipt.json")
        require(raw.is_file(), f"missing {raw.name}")
        judge(load_json(plan), load_json(raw))


def self_check() -> None:
    judge = load_judge()
    judge["self_check"]()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        plan = {"format": "pietto.phase77.test-qualification-plan.v2", "target": "postgres", "manifest": {"candidate_identity": {"kind": "test"}, "reader_identities": [{"kind": "test"}], "closure_sha256": None}, "cases": {"one": {"candidate": {"source": "table result:\n    from rows\n", "config": "schema_version = 2\n", "contract": {}, "artifact": {}, "sql": "SELECT 1", "fixed_values": [], "parameter_uses": [], "columns": []}, "fixture": {"ddl": [], "typed_seed": {}}, "expected": {"metadata": [], "values": [], "warnings": [], "terminal": {"kind": "rowset_eof", "close": "clean", "buffered_row_error": None}}}}, "cleanup": {"connection": "closed", "relations": "dropped", "transaction": "rolled_back"}}
        plan["manifest"]["closure_sha256"] = hashlib.sha256(canonical(plan)).hexdigest()
        plan_path = root / "one.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        wheel = root / "candidate.whl"
        wheel.write_bytes(b"wheel")
        freeze = {"format": FREEZE_FORMAT, "candidate_tree": "0" * 40, "wheel_sha256": sha256(wheel), "plans": {plan_path.name: sha256(plan_path)}}
        freeze_path = root / "freeze.json"
        freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
        preflight(freeze_path, [plan_path], wheel)
        freeze["plans"][plan_path.name] = "0" * 64
        freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
        try:
            preflight(freeze_path, [plan_path], wheel)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted changed frozen plan")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--plan", type=Path, action="append", default=[])
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--candidate-python", type=Path)
    parser.add_argument("--endpoint", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("flat PostgreSQL parent self-check passed")
        return 0
    if not args.freeze or not args.plan or not args.wheel:
        parser.error("--freeze, --plan and --wheel are required")
    plans = [path.resolve() for path in args.plan]
    if args.preflight:
        print(json.dumps(preflight(args.freeze.resolve(), plans, args.wheel.resolve()), sort_keys=True))
        return 0
    if args.observe:
        if not args.candidate_python or not args.endpoint or not args.output:
            parser.error("--observe needs --candidate-python, --endpoint and --output")
        observe(args.freeze.resolve(), plans, args.wheel.resolve(), args.candidate_python.resolve(), args.endpoint.resolve(), args.output.resolve())
        return 0
    parser.error("choose --self-check, --preflight or --observe")


if __name__ == "__main__":
    raise SystemExit(main())
