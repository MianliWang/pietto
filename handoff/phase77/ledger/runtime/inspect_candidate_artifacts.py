#!/usr/bin/env python3
"""Capture candidate source closure and built-distribution RECORD identity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(candidate: Path, *args: str) -> str:
    return subprocess.check_output(("git", "-C", str(candidate), *args), text=True).strip()


def main() -> int:
    runtime = Path(__file__).resolve().parent
    candidate = runtime.parent / "candidates" / "maintenance"
    source_before = runtime / "reports" / "source-before.sha256"
    source_after = runtime / "reports" / "source-after.sha256"
    artifacts = []
    for artifact in sorted((runtime / "dist").iterdir()):
        record = None
        if artifact.suffix == ".whl":
            with zipfile.ZipFile(artifact) as archive:
                record_name = next(name for name in archive.namelist() if name.endswith(".dist-info/RECORD"))
                record = {
                    "path": record_name,
                    "sha256": hashlib.sha256(archive.read(record_name)).hexdigest(),
                }
        artifacts.append(
            {
                "filename": artifact.name,
                "sha256": digest(artifact),
                "size": artifact.stat().st_size,
                "record": record,
            }
        )
    value = {
        "format": "pietto.phase77.runtime-candidate-artifacts.v1",
        "candidate": str(candidate),
        "head": git(candidate, "rev-parse", "HEAD"),
        "tree": git(candidate, "rev-parse", "HEAD^{tree}"),
        "source_closure": {
            "paths": ["src/**", "pyproject.toml", "uv.lock"],
            "before_sha256": digest(source_before),
            "after_sha256": digest(source_after),
            "unchanged": source_before.read_bytes() == source_after.read_bytes(),
        },
        "artifacts": artifacts,
    }
    (runtime / "candidate-artifacts-manifest.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
