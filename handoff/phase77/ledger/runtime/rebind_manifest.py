#!/usr/bin/env python3
"""Bind retained artifacts to the current maintenance dirty tree without rebuilding."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run(candidate: Path, *args: str) -> bytes:
    return subprocess.check_output(("git", "-C", str(candidate), *args))


def snapshot(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        values[relative] = digest
    return values


def source_paths(candidate: Path) -> list[Path]:
    return [
        path
        for path in sorted((candidate / "src").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    ]


def main() -> int:
    runtime = Path(__file__).resolve().parent
    candidate = runtime.parent / "candidates" / "maintenance"
    previous_path = runtime / "candidate-artifacts-manifest.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    previous_source = snapshot(runtime / "reports" / "source-after.sha256")
    wheel = next((runtime / "dist").glob("*.whl"))
    sdist = next((runtime / "dist").glob("*.tar.gz"))
    current: dict[str, str] = {}
    files = [candidate / "README.md", *source_paths(candidate)]
    files = [path for path in files if path.is_file()]
    with tarfile.open(sdist, "r:gz") as archive:
        prefix = archive.getnames()[0].split("/", 1)[0]
        for path in files:
            relative = path.relative_to(candidate).as_posix()
            member = archive.extractfile(f"{prefix}/{relative}")
            if member is None:
                raise ValueError(f"sdist missing {relative}")
            archived = hashlib.sha256(member.read()).hexdigest()
            local = digest(path)
            if local != archived:
                raise ValueError(f"artifact content drift {relative}")
            current[relative] = local
    for path in [candidate / "pyproject.toml", *source_paths(candidate)]:
        if not path.is_file():
            continue
        relative = path.relative_to(candidate).as_posix()
        if previous_source.get(relative) != digest(path):
            raise ValueError(f"previous source snapshot drift {relative}")
        current[relative] = digest(path)
    with zipfile.ZipFile(wheel) as archive:
        record_name = next(name for name in archive.namelist() if name.endswith(".dist-info/RECORD"))
        record_hash = hashlib.sha256(archive.read(record_name)).hexdigest()
    status = run(candidate, "status", "--porcelain=v1").decode("utf-8")
    patch = run(candidate, "diff", "--binary")
    lock = candidate / "uv.lock"
    value = {
        "format": "pietto.phase77.runtime-candidate-rebind.v1",
        "previous_artifact_manifest": {
            "path": str(previous_path),
            "sha256": digest(previous_path),
            "snapshot": previous,
        },
        "current_candidate": {
            "path": str(candidate),
            "head": run(candidate, "rev-parse", "HEAD").decode().strip(),
            "tree": run(candidate, "rev-parse", "HEAD^{tree}").decode().strip(),
            "dirty_status": status.splitlines(),
            "dirty_patch_sha256": hashlib.sha256(patch).hexdigest(),
            "uv_lock_sha256": digest(lock),
            "readme_pyproject_src": {
                "file_count": len(current),
                "closure_sha256": hashlib.sha256(
                    "".join(f"{key}\0{value}\n" for key, value in sorted(current.items())).encode()
                ).hexdigest(),
                "readme_and_src_match_sdist": True,
                "pyproject_and_src_match_previous_build_snapshot": True,
            },
        },
        "retained_artifacts": {
            "wheel": {"path": str(wheel), "sha256": digest(wheel), "record_sha256": record_hash},
            "sdist": {"path": str(sdist), "sha256": digest(sdist)},
        },
    }
    (runtime / "candidate-artifacts-rebind-manifest.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
