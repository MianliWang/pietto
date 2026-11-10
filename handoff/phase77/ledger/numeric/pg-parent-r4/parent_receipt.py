"""Write the numeric PostgreSQL parent receipt after its owned cleanup."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
CANDIDATE = Path("/tmp/pietto-maintenance-2601-338")
RAW_NAMES = (
    "campaign.log", "relay.log", "pg-server.log", "hook.stdout", "hook.stderr",
    "preflight-hook.stdout", "preflight-hook.stderr", "preflight-materializer.stdout",
    "preflight-materializer.stderr", "preflight-probe.stdout", "preflight-probe.stderr",
    "installed-origin.json", "cleanup.json",
)
HOOK_NAMES = (
    "bootstrap.json", "endpoint.json", "endpoint.json.binding.json", "numeric-receipt.json",
)
INPUT_NAMES = (
    "PREREG.md", "RUN_WRAPPER_PREREG.md", "pg.sh", "relay.py", "gen-tls.sh",
    "numeric_pg_hook.sh", "manifest.json", "materialize_endpoint.py",
    "p77_mysql_numeric_probe.py", "parent_receipt.py", "parent_judge.py", "candidate.patch",
    "tls/ca-key.pem", "tls/ca.pem", "tls/ca.srl", "tls/elsewhere-key.pem",
    "tls/elsewhere.csr", "tls/elsewhere.pem", "tls/other-ca-key.pem",
    "tls/other-ca.pem", "tls/server-key.pem", "tls/server.csr", "tls/server.pem",
)
CANDIDATE_NAMES = {
    "lock": CANDIDATE / "uv.lock",
    "target_pins": CANDIDATE / "tests/phase66_target_pins.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    if any(not (root / name).is_file() for name in names):
        raise SystemExit("missing receipt input")
    return {name: digest(root / name) for name in names}


def main(raw: Path, run: Path, image: str, network: str, container: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise SystemExit("invalid owned container identity")
    raw_hashes = hashes(raw, RAW_NAMES)
    hook_hashes = hashes(run, HOOK_NAMES)
    cleanup = json.loads((raw / "cleanup.json").read_text(encoding="utf-8"))
    if (
        not isinstance(cleanup, dict)
        or cleanup.get("container_absent") is not True
        or cleanup.get("container_id") != container
        or cleanup.get("relay_kill_exit") != 0
        or cleanup.get("relay_reaped") is not True
        or cleanup.get("relay_exit") not in {0, 143}
    ):
        raise SystemExit("incomplete parent cleanup")
    receipt = {
        "format": "pietto.phase77.numeric_pg_parent_receipt.v1",
        "candidate": {
            "base": "f8ccd2c44a2d9adf431a496bd9bbae037783176f",
            "lock_sha256": digest(CANDIDATE_NAMES["lock"]),
            "patch_sha256": "7345ddec240b89308f20867bfbcc9abf6f9cd7c49498b641f95df142cf62da2c",
            "target_pins_sha256": digest(CANDIDATE_NAMES["target_pins"]),
            "wheel_sha256": "f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73",
        },
        "runtime": {"container_id": container, "image": image, "network": network},
        "cleanup": cleanup,
        "inputs": hashes(HERE, INPUT_NAMES),
        "candidate_inputs": {name: digest(path) for name, path in CANDIDATE_NAMES.items()},
        "raw": raw_hashes,
        "hook": {"run": str(run), "files": hook_hashes},
    }
    (raw / "parent-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    _, raw, run, image, network, container = sys.argv
    main(Path(raw), Path(run), image, network, container)
