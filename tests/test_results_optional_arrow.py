"""Optional distribution selection; real clean install cells live in package_smoke."""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile

import pytest

from _pietto_repo_package import (
    REPO_ROOT,
    license_members,
    metadata_bytes,
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


def test_project_and_lock_select_exactly_one_optional_arrow_dependency():
    document = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project = document["project"]
    assert project["dependencies"] == ["antlr4-python3-runtime==4.13.2"]
    # The Arrow extra is unchanged; Phase68 S18 pins its route extras exactly.
    assert project["optional-dependencies"]["arrow"] == ["pyarrow==25.0.1"]
    assert project["scripts"] == {"pietto": "pietto.cli:main"}
    assert "pyarrow" not in json.dumps(document["dependency-groups"]).lower()
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    (package,) = [p for p in lock["package"] if p["name"] == "pietto"]
    assert package["dependencies"] == [{"name": "antlr4-python3-runtime"}]
    assert package["optional-dependencies"]["arrow"] == [{"name": "pyarrow"}]
    assert package["metadata"]["provides-extras"][0] == "arrow"
    requires = package["metadata"]["requires-dist"]
    assert [r for r in requires if "marker" not in r] == [
        {"name": "antlr4-python3-runtime", "specifier": "==4.13.2"}
    ]
    assert [r for r in requires if r.get("marker") == "extra == 'arrow'"] == [
        {"name": "pyarrow", "marker": "extra == 'arrow'", "specifier": "==25.0.1"},
    ]
    (arrow,) = [p for p in lock["package"] if p["name"] == "pyarrow"]
    assert arrow["version"] == "25.0.1"
    verified = (
        REPO_ROOT / "ci/phase67-arrow-compatibility-requirements.txt"
    ).read_text()
    assert "pyarrow==25.0.1" in verified
    for tag in ("cp312-cp312", "cp313-cp313"):
        (tested,) = [
            w for w in arrow["wheels"] if tag + "-manylinux_2_28_x86_64.whl" in w["url"]
        ]
        assert "--hash=" + tested["hash"] in verified


@pytest.mark.parametrize("extra", (None, "arrow", "unknown"))
def test_locked_export_preserves_default_core_and_rejects_unknown_extra(
    extra: str | None,
):
    command = [
        "uv",
        "export",
        "--locked",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
    ]
    if extra is not None:
        command += ["--extra", extra]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "UV_PYTHON": sys.executable,
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        },
    )
    if extra == "unknown":
        assert result.returncode != 0 and "unknown" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert "antlr4-python3-runtime==4.13.2" in result.stdout
        assert ("pyarrow==25.0.1" in result.stdout) is (extra == "arrow")


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "requirement",
    (
        b"pyarrow==25.0.1; extra == 'arrow'",
        b'PyArrow ( == 25.0.1 ) ; extra=="arrow"',
        b'pyarrow == 25.0.1 ; (extra == "arrow")',
    ),
)
def test_artifact_metadata_accepts_equivalent_serialization(
    tmp_path: Path, kind: str, requirement: bytes
):
    metadata = metadata_bytes().replace(
        b"pyarrow==25.0.1; extra == 'arrow'", requirement
    )
    _inspect(_artifact(tmp_path, kind, metadata), kind)


EXTRAS_DIFFER = "artifact Provides-Extra declarations differ"
REQUIREMENTS_DIFFER = "artifact runtime dependency/extra declarations differ"
LICENSE_DIFFERS = "artifact license metadata differs"
INDEX_METADATA_DIFFERS = "artifact URL, classifier or keyword metadata differs"
# Each (before, after) damage and the package_smoke failure that must reject it.
METADATA_DAMAGE = {
    (b"Provides-Extra: arrow\n", b""): EXTRAS_DIFFER,
    (b"Provides-Extra: arrow", b"Provides-Extra: results"): EXTRAS_DIFFER,
    (
        b"Provides-Extra: arrow\n",
        b"Provides-Extra: arrow\nProvides-Extra: unknown\n",
    ): EXTRAS_DIFFER,
    (
        b"Provides-Extra: arrow\n",
        b"Provides-Extra: arrow\nProvides-Extra: arrow\n",
    ): EXTRAS_DIFFER,
    (b"pyarrow==25.0.1", b"pyarrow==25.0.0"): REQUIREMENTS_DIFFER,
    (b"pyarrow==25.0.1", b"pyarrow>=25.0.1"): REQUIREMENTS_DIFFER,
    (b"; extra == 'arrow'", b""): REQUIREMENTS_DIFFER,
    (b"; extra == 'arrow'", b"; extra == 'unknown'"): REQUIREMENTS_DIFFER,
    (
        b"; extra == 'arrow'",
        b"; extra == 'ar row'",
    ): "unsupported artifact extra condition",
    (b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\n", b""): REQUIREMENTS_DIFFER,
    (
        b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\n",
        b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\nRequires-Dist: pyarrow==26.0.0; extra == 'arrow'\n",
    ): REQUIREMENTS_DIFFER,
    (b"Requires-Dist: antlr4-python3-runtime==4.13.2\n", b""): REQUIREMENTS_DIFFER,
    (b"Metadata-Version: 2.4", b"Metadata-Version: 2.3"): LICENSE_DIFFERS,
    (b"License-Expression: MIT\n", b""): LICENSE_DIFFERS,
    (b"License-Expression: MIT", b"License-Expression: Apache-2.0"): LICENSE_DIFFERS,
    (b"License-File: LICENSE\n", b""): LICENSE_DIFFERS,
    (
        b"License-Expression: MIT\n",
        b"License-Expression: MIT\nLicense: MIT\n",
    ): LICENSE_DIFFERS,
    (
        b"License-Expression: MIT\n",
        b"License-Expression: MIT\nClassifier: License :: OSI Approved :: MIT License\n",
    ): LICENSE_DIFFERS,
    (b"Classifier: Topic :: Database\n", b""): INDEX_METADATA_DIFFERS,
    (b"Project-URL: Issues, ", b"Project-URL: Bugs, "): INDEX_METADATA_DIFFERS,
    (b"Keywords: sql,", b"Keywords: orm,sql,"): INDEX_METADATA_DIFFERS,
    # Keywords is single-use: the same list split over two headers is invalid.
    (b"Keywords: sql,dsl,", b"Keywords: sql,dsl\nKeywords: "): INDEX_METADATA_DIFFERS,
    # Any current version becomes another one: "9" prefixes its value.
    (b"\nVersion: ", b"\nVersion: 9"): "artifact metadata Version is",
    (
        b"Requires-Python: >=3.12",
        b"Requires-Python: >=3.13",
    ): "artifact metadata Requires-Python is",
    (
        b"Description-Content-Type: text/markdown",
        b"Description-Content-Type: text/plain",
    ): "artifact metadata is missing Markdown README metadata",
    (
        b"# Pietto\n",
        b"# Wrong README\n",
    ): "artifact metadata is missing the declared README body",
}


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize("before,after", tuple(METADATA_DAMAGE))
def test_metadata_damage_fails_each_artifact(
    tmp_path: Path, kind: str, before: bytes, after: bytes
):
    original = metadata_bytes()
    assert before in original
    with pytest.raises(smoke.SmokeFailure, match=METADATA_DAMAGE[before, after]):
        _inspect(_artifact(tmp_path, kind, original.replace(before, after, 1)), kind)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "damage,message",
    (("missing", "missing required files"), ("altered", "license file differs")),
)
def test_license_members_are_required_and_byte_exact(
    tmp_path: Path, kind: str, damage: str, message: str
):
    artifact = _artifact(tmp_path, kind, metadata_bytes(), license_damage=damage)
    # Exactly the LICENSE member is named, whatever the artifact's prefix.
    with pytest.raises(smoke.SmokeFailure, match=rf"{message}: \S*LICENSE$"):
        _inspect(artifact, kind)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize("owner", RESULT_OWNERS)
def test_all_current_private_result_owners_are_required(
    tmp_path: Path, kind: str, owner: str
):
    # Exactly this one owner is missing, whatever the artifact's prefix.
    with pytest.raises(
        smoke.SmokeFailure,
        match=rf"missing required files: \S*pietto/_project/{owner}\.py$",
    ):
        _inspect(
            _artifact(tmp_path, kind, metadata_bytes(), missing=owner + ".py"), kind
        )


def test_console_entry_is_checked_in_wheel_and_sdist(tmp_path: Path):
    with pytest.raises(smoke.SmokeFailure, match="console entry"):
        _inspect(
            _artifact(
                tmp_path,
                "wheel",
                metadata_bytes(),
                entry=b"[console_scripts]\npietto = pietto.cli:wrong\n",
            ),
            "wheel",
        )
    project = (
        (REPO_ROOT / "pyproject.toml")
        .read_bytes()
        .replace(b"pietto.cli:main", b"pietto.cli:wrong")
    )
    with pytest.raises(smoke.SmokeFailure, match="console entry"):
        _inspect(
            _artifact(tmp_path, "sdist", metadata_bytes(), project=project), "sdist"
        )


def test_fake_correct_version_and_cross_cell_paths_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    core, extra = tmp_path / "core", tmp_path / "extra"
    monkeypatch.setattr(smoke.sys, "prefix", str(extra))
    paths = [
        tmp_path / "checkout/pyarrow/__init__.py",
        core / "lib/python3.13/site-packages/pyarrow/__init__.py",
    ]
    for path in paths:
        path.parent.mkdir(parents=True)
        path.write_text('__version__ = "25.0.1"\n')
        with pytest.raises(smoke.SmokeFailure, match="foreign installed origin"):
            smoke._installed_path(path)
    link = extra / "lib/python3.13/site-packages/pyarrow"
    link.parent.mkdir(parents=True)
    link.symlink_to(paths[0].parent, target_is_directory=True)
    with pytest.raises(smoke.SmokeFailure, match="foreign installed origin"):
        smoke._installed_path(link / "__init__.py")


def test_extra_cell_refuses_an_existing_or_symlink_prefix(tmp_path: Path):
    for prefix in (tmp_path, tmp_path / "link"):
        if prefix.name == "link":
            prefix.symlink_to(tmp_path / "absent", target_is_directory=True)
        with pytest.raises(smoke.SmokeFailure, match="new owned path"):
            smoke._install_extra(prefix, tmp_path, tmp_path / "candidate.whl")


def test_core_developer_environment_and_public_import_remain_arrow_free(tmp_path: Path):
    assert importlib.util.find_spec("pyarrow") is None
    (tmp_path / "pyarrow.py").write_text('raise AssertionError("leaked path")\n')
    code = """
import importlib, importlib.metadata, importlib.util, sys
import pietto
from pietto import cli
for name in %r:
    importlib.import_module('pietto._project.' + name)
assert importlib.util.find_spec('pyarrow') is None
assert not any(n == 'pyarrow' or n.startswith('pyarrow.') for n in sys.modules)
assert not hasattr(pietto, 'PiettoResultContract')
assert importlib.util.find_spec('pietto.arrow') is None
assert importlib.util.find_spec('pietto.result') is None
from pietto._project.project_arrow_result import _arrow
from pietto._project.project_result_contract import ResultError
try:
    _arrow()
except ResultError as error:
    assert error.category == 'ARROW_DEPENDENCY_MISSING'
else:
    raise AssertionError('missing dependency accepted')
""" % (RESULT_OWNERS,)
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# Each duplicated singleton line (named by how it starts; Version by its header
# alone, so any version) and the package_smoke failure that must reject it.
SINGLETON_DAMAGE = {
    b"Name: pietto": "artifact metadata Name is",
    b"Version": "artifact metadata Version is",
    b"Requires-Python: >=3.12": "artifact metadata Requires-Python is",
    b"Description-Content-Type: text/markdown": (
        "artifact metadata is missing Markdown README metadata"
    ),
    b"Metadata-Version: 2.4": LICENSE_DIFFERS,
    b"License-Expression: MIT": LICENSE_DIFFERS,
}


@pytest.mark.parametrize("field", tuple(SINGLETON_DAMAGE))
@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_duplicate_singleton_metadata_is_rejected(
    tmp_path: Path, field: bytes, kind: str
):
    metadata, count = re.subn(
        rb"(?m)^(" + re.escape(field) + rb"[^\n]*\n)",
        rb"\1\1",
        metadata_bytes(),
        count=1,
    )
    assert count == 1
    with pytest.raises(smoke.SmokeFailure, match=SINGLETON_DAMAGE[field]):
        _inspect(_artifact(tmp_path, kind, metadata), kind)


def test_main_rejects_dangling_extra_prefix_before_any_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    link = tmp_path / "extra"
    target = tmp_path / "target"
    link.symlink_to(target, target_is_directory=True)

    def forbidden(*args, **kwargs):
        pytest.fail("existing/symlink extra prefix reached acquisition")

    monkeypatch.setattr(smoke, "_run_command", forbidden)
    assert smoke.main(["--extra-env", str(link)]) == 1
    assert link.is_symlink() and not target.exists()
