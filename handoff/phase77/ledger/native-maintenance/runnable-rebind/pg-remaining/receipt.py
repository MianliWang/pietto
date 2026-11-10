"""Bind one R3 raw result directory to its actual runnable inputs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(raw: Path, base: str, patch: str, wheel: str, lock: str, image: str, network: str) -> None:
    names = ("campaign.log", "relay.log", "pg-server.log", "client.json", "client.err", "cleanup.json")
    if any(not (raw / name).is_file() for name in names):
        raise SystemExit("missing R3 raw record")
    inputs = (
        "PREREG.md",
        "ERRATUM.md",
        "client.py",
        "raw_driver_child.py",
        "judge.py",
        "pg.sh",
        "receipt.py",
        "relay.py",
        "gen-tls.sh",
        "fresh_binding.py",
        "fresh-start.sh",
        "target-run.sh",
        "fresh-binding.json",
        "candidate.patch",
        "in/fixture.sql",
        "in/pg_hba.conf",
        "in/ordered-exec/main.pietto",
        "in/ordered-exec/pietto.toml",
        "in/ordered-exec/contract.json",
        "in/timestamp-exec/main.pietto",
        "in/timestamp-exec/pietto.toml",
        "in/timestamp-exec/contract.json",
        "tls/ca.pem",
        "tls/ca-key.pem",
        "tls/other-ca.pem",
        "tls/other-ca-key.pem",
        "tls/server.pem",
        "tls/server-key.pem",
        "tls/elsewhere.pem",
        "tls/elsewhere-key.pem",
    )
    receipt = {
        "schema": 1,
        "complete": True,
        "candidate_base": base,
        "candidate_patch_sha256": patch,
        "candidate_wheel_sha256": wheel,
        "candidate_lock_sha256": lock,
        "image": image,
        "network": network,
        "invocation": json.loads((HERE / "target-invocation.json").read_text()),
        "cleanup": json.loads((raw / "cleanup.json").read_text()),
        "inputs": {name: digest(HERE / name) for name in inputs},
        "raw": {name: digest(raw / name) for name in names},
    }
    (raw / "campaign.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    _, raw, base, patch, wheel, lock, image, network = sys.argv
    main(Path(raw), base, patch, wheel, lock, image, network)
