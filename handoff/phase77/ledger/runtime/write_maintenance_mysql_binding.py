#!/usr/bin/env python3
"""Write fresh non-executing inputs for the already-authorized MySQL launcher."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> int:
    runtime = Path(__file__).resolve().parent
    evidence = runtime.parent / "evidence" / "mysql-maintenance-preflight-20261109T000000-0500"
    wheel = next((runtime / "dist").glob("*.whl"))
    with wheel.open("rb") as handle:
        wheel_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    value = {
        "format": "pietto.phase77.run-maintenance-mysql-binding.v1",
        "status": "PREPARED_NO_DB_EXECUTION",
        "interpreter": str(runtime / "venvs" / "native" / "bin" / "python"),
        "candidate": str(runtime.parent / "candidates" / "maintenance"),
        "wheel": str(wheel),
        "wheel_sha256": wheel_hash,
        "house_parent": str(evidence / "house"),
        "house_directory": str(evidence / "house" / "pietto-phase68-slice18-wheelhouse"),
        "otel_house": str(evidence / "otel-house"),
        "expected_binding": str(evidence / "expected-binding.json"),
        "lock": "/tmp/claude-1000/pietto-docker-campaign-mysql.lock",
        "manifest": str(runtime / "wheelhouse-rebind-manifest.json"),
        "candidate_manifest": str(runtime / "candidate-artifacts-rebind-manifest.json"),
    }
    (runtime / "run-maintenance-mysql-binding.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
