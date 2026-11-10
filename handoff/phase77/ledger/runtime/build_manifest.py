#!/usr/bin/env python3
"""Write the runtime wheel manifest from pip's resolver reports and local wheels."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


def wheel_tags(name: str) -> list[str]:
    parts = name[:-4].split("-")
    if len(parts) < 5:
        raise ValueError(f"not a wheel filename: {name}")
    return parts[-3:]


def normalized(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def dist_metadata(wheel: Path) -> tuple[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            item for item in archive.namelist() if item.endswith(".dist-info/METADATA")
        )
        lines = archive.read(metadata_name).decode("utf-8").splitlines()
    fields = dict(line.split(": ", 1) for line in lines if ": " in line)
    return fields["Name"], fields["Version"]


def report_records(paths: list[Path]) -> dict[tuple[str, str], dict[str, object]]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for item in report["install"]:
            metadata = item["metadata"]
            records[(normalized(metadata["name"]), metadata["version"])] = item["download_info"]
    return records


def main() -> int:
    runtime = Path(__file__).resolve().parent
    house = runtime / "wheelhouse"
    reports = [runtime / "reports" / "core-dev-resolve.json", runtime / "reports" / "native-resolve.json"]
    downloads = report_records(reports)
    wheels = []
    for wheel in sorted(house.glob("*.whl")):
        name, version = dist_metadata(wheel)
        key = (normalized(name), version)
        download = downloads.get(key)
        if download is None:
            raise ValueError(f"missing resolver URL: {wheel.name} ({name} {version})")
        actual_hash = hashlib.file_digest(wheel.open("rb"), "sha256").hexdigest()
        archive = download["archive_info"]
        expected_hash = archive.get("hashes", {}).get("sha256")
        if expected_hash != actual_hash:
            raise ValueError(f"resolver hash mismatch: {wheel.name}")
        wheels.append(
            {
                "filename": wheel.name,
                "name": name,
                "version": version,
                "official_url": download["url"],
                "sha256": actual_hash,
                "tags": wheel_tags(wheel.name),
            }
        )
    manifest = {
        "format": "pietto.phase77.runtime-wheelhouse.v1",
        "python": "3.13.13",
        "platform": "Linux x86_64",
        "source": {
            "candidate": ".cache/phase77-recovery/candidates/maintenance",
            "lock": "maintenance/uv.lock",
            "registries": ["https://pypi.org/simple", "https://files.pythonhosted.org"],
        },
        "wheels": wheels,
    }
    (runtime / "wheelhouse-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
