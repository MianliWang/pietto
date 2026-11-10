"""Bind the flat PostgreSQL parent to its B2 candidate without execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPECTED_TREE = "9e688596fdb52667531b120d10ace4d836c426f2"
EXPECTED_WHEEL_SHA256 = "b7f62d1174361257fe065b8718ef1741555b078367405aa425d3c6d452e115b3"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_tree(repository: Path) -> str:
    index = HERE / "candidate.index"
    index.unlink(missing_ok=True)
    environment = {"GIT_INDEX_FILE": str(index)}
    for command in (("git", "read-tree", "HEAD"), ("git", "add", "-A")):
        subprocess.run(command, cwd=repository, env=environment, check=True)
    subprocess.run(("git", "reset", "--", "INTEGRATION-STATUS.md"), cwd=repository, env=environment, check=True)
    return subprocess.check_output(("git", "write-tree"), cwd=repository, env=environment, text=True).strip()


def self_check(repository: Path, wheel: Path) -> None:
    if candidate_tree(repository) != EXPECTED_TREE:
        raise ValueError("candidate tree differs")
    if digest(wheel) != EXPECTED_WHEEL_SHA256:
        raise ValueError("candidate wheel differs")
    with zipfile.ZipFile(wheel) as archive:
        members = [name for name in archive.namelist() if name.startswith("pietto/")]
    if not members:
        raise ValueError("candidate wheel lacks Pietto package")
    for name in ("flat_qualification.py", "common_judge.py", "relay.py"):
        if not (HERE / name).is_file():
            raise ValueError("missing parent input: " + name)
    print(json.dumps({
        "candidate_tree": EXPECTED_TREE,
        "wheel": str(wheel),
        "wheel_sha256": EXPECTED_WHEEL_SHA256,
        "wheel_pietto_members": len(members),
        "native": "NOT_STARTED",
        "waiting_for": ["decimal_plan", "s16_plan", "reviewed_native_dispatch"],
    }, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-repository", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if not args.self_check:
        parser.error("only --self-check is available before reviewed native inputs arrive")
    self_check(args.candidate_repository.resolve(), args.wheel.resolve())


if __name__ == "__main__":
    main()
