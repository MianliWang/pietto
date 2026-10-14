"""Optional distribution selection; real clean install cells live in package_smoke."""

from __future__ import annotations

import io
from pathlib import Path
import tarfile
import zipfile


from _pietto_repo_package import (
    REPO_ROOT,
    license_members,
    smoke,
)


RESULT_OWNERS = (
    "project_result_contract",
    "project_result_binding",
    "project_arrow_result",
    "project_result_contract_pure_boundary",
    "project_result_contract_portable",
    "project_result_contract_correspondence",
    "project_scalar_meaning",
    "project_result_reader",
    "project_arrow_interop",
    "project_result_ingress",
    "project_result_ipc",
)


EXTRAS_DIFFER = "artifact Provides-Extra declarations differ"
REQUIREMENTS_DIFFER = "artifact runtime dependency/extra declarations differ"


def _artifact(
    tmp_path: Path,
    kind: str,
    metadata: bytes,
    *,
    missing: str = "",
    project: bytes | None = None,
    entry: bytes | None = None,
    license_damage: str = "",
) -> Path:
    contract = smoke._project_contract()
    licenses = license_members()
    if license_damage == "missing":
        licenses.pop("LICENSE")
    elif license_damage == "altered":
        licenses["LICENSE"] += b"\n"
    stem = f"{contract.name}-{contract.version}"
    if kind == "wheel":
        path = tmp_path / f"{stem}-py3-none-any.whl"
        info = f"{stem}.dist-info/"
        with zipfile.ZipFile(path, "w") as archive:
            for name in smoke._required_runtime_files("pietto"):
                if not name.endswith(missing) or not missing:
                    archive.writestr(name, b"")
            archive.writestr(info + "METADATA", metadata)
            archive.writestr(info + "WHEEL", "Wheel-Version: 1.0\n")
            archive.writestr(
                info + "entry_points.txt",
                entry or b"[console_scripts]\npietto = pietto.cli:main\n",
            )
            for name, content in licenses.items():
                archive.writestr(f"{info}licenses/{name}", content)
        return path
    path = tmp_path / f"{stem}.tar.gz"
    members = {
        name: b""
        for name in smoke._required_runtime_files(f"{stem}/src/pietto")
        if not missing or not name.endswith(missing)
    }
    members.update(
        {
            f"{stem}/PKG-INFO": metadata,
            f"{stem}/pyproject.toml": project
            or (REPO_ROOT / "pyproject.toml").read_bytes(),
            f"{stem}/README.md": (REPO_ROOT / contract.readme).read_bytes(),
        }
    )
    members.update({f"{stem}/{n}": c for n, c in licenses.items()})
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path


def _inspect(path: Path, kind: str) -> None:
    checker = smoke._inspect_wheel if kind == "wheel" else smoke._inspect_sdist
    checker(path, smoke._project_contract())
