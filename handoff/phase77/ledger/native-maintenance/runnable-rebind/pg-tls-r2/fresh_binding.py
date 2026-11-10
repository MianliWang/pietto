"""Produce and verify the strict, local runtime identity for one fresh run."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


VERSIONS = {
    "pietto": "0.1.10",
    "pyarrow": "26.0.1",
    "psycopg": "3.3.8",
    "psycopg-binary": "3.3.8",
    "adbc-driver-postgresql": "1.13.0",
    "adbc-driver-manager": "1.13.0",
}
SOURCES = ("fresh_binding.py", "fresh-start.sh", "target-run.sh", "selftest.sh", "judge.py", "client.py", "receipt.py", "relay.py", "pg.sh", "gen-tls.sh")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_integrity(name: str) -> dict[str, object]:
    distribution = metadata.distribution(name)
    record = Path(distribution.locate_file(f"{distribution.metadata['Name'].replace('-', '_')}-{distribution.version}.dist-info/RECORD"))
    if not record.is_file():
        raise SystemExit(f"{name}: RECORD missing")
    checked = 0
    for row in csv.reader(record.read_text(encoding="utf-8").splitlines()):
        if len(row) != 3 or not row[0] or Path(row[0]).is_absolute():
            raise SystemExit(f"{name}: invalid RECORD entry")
        path, encoded, size = row
        payload = Path(distribution.locate_file(path))
        exempt = path.endswith(".dist-info/RECORD") or path.endswith(".dist-info/direct_url.json")
        if not payload.is_file() or (not encoded and not exempt):
            raise SystemExit(f"{name}: unhashed or missing required RECORD payload {path}")
        if encoded:
            algorithm, value = encoded.split("=", 1)
            if algorithm != "sha256" or not size or hashlib.sha256(payload.read_bytes()).digest() != base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)) or payload.stat().st_size != int(size):
                raise SystemExit(f"{name}: RECORD payload differs {path}")
            checked += 1
    return {"record_sha256": sha256(record), "payloads": checked}


def actual_binding(args: argparse.Namespace) -> dict[str, object]:
    wheel = Path(args.wheel).resolve()
    candidate = Path(args.candidate).resolve()
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.13":
        raise SystemExit("fresh binding requires CPython 3.13.13")
    if sha256(wheel) != args.wheel_sha256:
        raise SystemExit("wheel sha256 differs")
    patch = subprocess.check_output(("git", "-C", str(candidate), "diff", "--binary"))
    if hashlib.sha256(patch).hexdigest() != args.patch_sha256:
        raise SystemExit("candidate patch sha256 differs")
    if sha256(candidate / "uv.lock") != args.lock_sha256:
        raise SystemExit("candidate lock sha256 differs")
    if subprocess.check_output(("git", "-C", str(candidate), "rev-parse", "HEAD"), text=True).strip() != args.base:
        raise SystemExit("candidate base differs")
    origins = {name: str(metadata.distribution(name).locate_file("")) for name in VERSIONS}
    if {name: metadata.version(name) for name in VERSIONS} != VERSIONS or len(set(origins.values())) != 1:
        raise SystemExit("native dependency closure differs")
    import pietto

    distribution = metadata.distribution("pietto")
    direct_url = distribution.read_text("direct_url.json")
    expected_url = json.dumps({"url": wheel.as_uri(), "archive_info": {}}, separators=(",", ":"))
    module = Path(pietto.__file__).resolve()
    record = Path(distribution.locate_file("pietto-0.1.10.dist-info/RECORD")).resolve()
    prefix = Path(origins["pietto"]).resolve()
    if direct_url != expected_url or not module.is_relative_to(prefix) or not record.is_relative_to(prefix):
        raise SystemExit("installed Pietto is not the exact wheel closure")
    return {
        "format": "pietto.phase77.pg-fresh-binding.v1",
        "python": str(Path(sys.executable).resolve()),
        "dependencies": VERSIONS,
        "site_packages": str(prefix),
        "origins": origins,
        "integrity": {name: record_integrity(name) for name in VERSIONS},
        "pietto": {"direct_url": direct_url, "module": str(module), "record": str(record), "record_sha256": sha256(record)},
        "wheel": {"path": str(wheel), "sha256": args.wheel_sha256},
        "candidate": {"path": str(candidate), "base": args.base, "patch_sha256": args.patch_sha256, "lock_sha256": args.lock_sha256},
        "source_sha256": {name: sha256(Path(__file__).resolve().parent / name) for name in SOURCES},
        "candidate_patch": patch.decode(),
    }


def check(binding: dict[str, object], actual: dict[str, object]) -> None:
    if binding.get("format") != "pietto.phase77.pg-fresh-binding.v1" or binding != actual:
        raise SystemExit("fresh binding differs from the current runtime")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("produce", "check"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--patch-sha256", required=True)
    parser.add_argument("--lock-sha256", required=True)
    args = parser.parse_args()
    actual = actual_binding(args)
    if args.action == "produce":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        (args.output.parent / "candidate.patch").write_text(actual.pop("candidate_patch"), encoding="utf-8")
        args.output.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"binding": str(args.output), "wheel": actual["wheel"], "record": actual["pietto"]["record"]}, sort_keys=True))
        return
    expected = json.loads(args.output.read_text(encoding="utf-8"))
    actual.pop("candidate_patch")
    check(expected, actual)
    print(json.dumps({"binding": str(args.output), "status": "exact"}, sort_keys=True))


if __name__ == "__main__":
    main()
