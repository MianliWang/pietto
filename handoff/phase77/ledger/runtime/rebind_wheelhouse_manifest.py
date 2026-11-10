#!/usr/bin/env python3
"""Record the full wheelhouse after the CP312 witness-wheel addition."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


def normalized(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


def metadata(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        name = next(item for item in archive.namelist() if item.endswith(".dist-info/METADATA"))
        fields = dict(
            line.split(": ", 1)
            for line in archive.read(name).decode("utf-8").splitlines()
            if ": " in line
        )
    return fields["Name"], fields["Version"]


def tags(filename: str) -> list[str]:
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        raise ValueError(filename)
    return parts[-3:]


def main() -> int:
    runtime = Path(__file__).resolve().parent
    reports = [
        runtime / "reports" / "core-dev-resolve.json",
        runtime / "reports" / "native-resolve.json",
        runtime / "reports" / "wrapt-cp312-resolve.json",
        runtime / "reports" / "uv-build-resolve.json",
    ]
    downloads: dict[str, dict[str, object]] = {}
    for report_path in reports:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for item in report["install"]:
            url = item["download_info"]["url"]
            downloads[url.rsplit("/", 1)[1]] = item["download_info"]
    wheels = []
    for path in sorted((runtime / "wheelhouse").glob("*.whl")):
        name, version = metadata(path)
        info = downloads.get(path.name)
        if info is None:
            raise ValueError(f"no resolver provenance for {path.name}")
        actual = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
        expected = info["archive_info"].get("hashes", {}).get("sha256")
        if expected != actual or not info["url"].startswith("https://files.pythonhosted.org/"):
            raise ValueError(f"unverified wheel {path.name}")
        wheels.append({
            "filename": path.name,
            "name": name,
            "version": version,
            "official_url": info["url"],
            "sha256": actual,
            "tags": tags(path.name),
        })
    old = runtime / "wheelhouse-manifest.json"
    value = {
        "format": "pietto.phase77.runtime-wheelhouse-rebind.v1",
        "previous_manifest": {"path": str(old), "sha256": hashlib.file_digest(old.open("rb"), "sha256").hexdigest()},
        "wheel_count": len(wheels),
        "wheels": wheels,
        "otel_house": {
            "consumer_path": str(runtime.parent / "evidence" / "mysql-maintenance-preflight-20261109T000000-0500" / "otel-house"),
            "source_wheelhouse": str(runtime / "wheelhouse"),
            "required": [
                "opentelemetry_api-1.33.1-py3-none-any.whl",
                "opentelemetry_sdk-1.33.1-py3-none-any.whl",
                "opentelemetry_semantic_conventions-0.54b1-py3-none-any.whl",
                "wrapt-2.5.0-cp313-cp313-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl",
                "wrapt-2.5.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl",
            ],
        },
    }
    (runtime / "wheelhouse-rebind-manifest.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
