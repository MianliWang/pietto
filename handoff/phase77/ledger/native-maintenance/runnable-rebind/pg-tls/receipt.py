"""Write one complete, same-run receipt for C76-06.

The judge treats a missing or incomplete receipt as a failed campaign.  This
module never reads credentials; it records public file identities and client
exit statuses only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_exits(path: Path) -> list[dict[str, object]]:
    rows = []
    for line in path.read_text().splitlines():
        cell, route, status = line.split("\t")
        rows.append({"cell": cell, "route": route, "status": int(status)})
    return rows


def finish(raw: Path, base: str, patch: str, wheel: str, lock: str, image: str, network: str, ready: str) -> None:
    here = Path(__file__).resolve().parent
    required = ("relay.log", "pg-server.log", "campaign.log", "cell-exits.tsv", "cleanup.json")
    if any(not (raw / name).is_file() for name in required):
        raise SystemExit("missing campaign evidence")
    cell_paths = sorted(raw.glob("cell-*-*.json"))
    if not cell_paths:
        raise SystemExit("missing cell records")
    receipt = {
        "schema": 1,
        "complete": True,
        "candidate_base": base,
        "candidate_patch_sha256": patch,
        "candidate_wheel_sha256": wheel,
        "candidate_lock_sha256": lock,
        "image": image,
        "network": network,
        "invocation": json.loads((here / "target-invocation.json").read_text()),
        "cleanup": json.loads((raw / "cleanup.json").read_text()),
        "inputs": {
            name: digest(here / name)
            for name in (
                "ORACLE.md",
                "judge.py",
                "client.py",
                "receipt.py",
                "relay.py",
                "pg.sh",
                "gen-tls.sh",
                "fresh_binding.py",
                "fresh-start.sh",
                "target-run.sh",
                "fresh-binding.json",
                "in/fixture.sql",
                "in/pg_hba.conf",
                "sql/statement.sql",
                "candidate.patch",
                "tls/ca.pem",
                "tls/other-ca.pem",
                "tls/server.pem",
                "tls/elsewhere.pem",
            )
        },
        "ambient_home_root_sha256": digest(raw / "home/.postgresql/root.crt"),
        "ready": ready == "1",
        "cells": read_exits(raw / "cell-exits.tsv"),
        "raw": {
            path.name: digest(path)
            for path in (*cell_paths, *(raw / name for name in required))
        },
    }
    (raw / "campaign.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    _, raw, base, patch, wheel, lock, image, network, ready = sys.argv
    finish(Path(raw), base, patch, wheel, lock, image, network, ready)
