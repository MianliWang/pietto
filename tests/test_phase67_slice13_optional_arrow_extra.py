"""Optional distribution selection; real clean install cells live in package_smoke."""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib
import zipfile

import pytest

from test_phase11_packaging_smoke import REPO_ROOT, _metadata_bytes, smoke


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
) -> Path:
    contract = smoke._project_contract()
    if kind == "wheel":
        path = tmp_path / "pietto-0.1.0-py3-none-any.whl"
        with zipfile.ZipFile(path, "w") as archive:
            for name in smoke._required_runtime_files("pietto"):
                if not name.endswith(missing) or not missing:
                    archive.writestr(name, b"")
            archive.writestr("pietto-0.1.0.dist-info/METADATA", metadata)
            archive.writestr("pietto-0.1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            archive.writestr(
                "pietto-0.1.0.dist-info/entry_points.txt",
                entry or b"[console_scripts]\npietto = pietto.cli:main\n",
            )
        return path
    path = tmp_path / "pietto-0.1.0.tar.gz"
    members = {
        name: b""
        for name in smoke._required_runtime_files("pietto-0.1.0/src/pietto")
        if not missing or not name.endswith(missing)
    }
    members.update(
        {
            "pietto-0.1.0/PKG-INFO": metadata,
            "pietto-0.1.0/pyproject.toml": project
            or (REPO_ROOT / "pyproject.toml").read_bytes(),
            "pietto-0.1.0/README.md": (REPO_ROOT / contract.readme).read_bytes(),
        }
    )
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
    assert (project["name"], project["version"], project["requires-python"]) == (
        "pietto",
        "0.1.0",
        ">=3.12",
    )
    assert project["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    # The Arrow extra is unchanged; Phase68 S18 pins its route extras exactly.
    assert project["optional-dependencies"]["arrow"] == ["pyarrow==25.0.1"]
    assert project["scripts"] == {"pietto": "pietto.cli:main"}
    assert "pyarrow" not in json.dumps(document["dependency-groups"]).lower()
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    (package,) = [p for p in lock["package"] if p["name"] == "pietto"]
    assert package["version"] == "0.1.0"
    assert package["dependencies"] == [{"name": "antlr4-python3-runtime"}]
    assert package["optional-dependencies"]["arrow"] == [{"name": "pyarrow"}]
    assert package["metadata"]["provides-extras"][0] == "arrow"
    requires = package["metadata"]["requires-dist"]
    assert [r for r in requires if "marker" not in r] == [
        {"name": "antlr4-python3-runtime", "specifier": ">=4.13.2"}
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
    metadata = _metadata_bytes().replace(
        b"pyarrow==25.0.1; extra == 'arrow'", requirement
    )
    _inspect(_artifact(tmp_path, kind, metadata), kind)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "before,after",
    (
        (b"Provides-Extra: arrow\n", b""),
        (b"Provides-Extra: arrow", b"Provides-Extra: results"),
        (
            b"Provides-Extra: arrow\n",
            b"Provides-Extra: arrow\nProvides-Extra: unknown\n",
        ),
        (b"Provides-Extra: arrow\n", b"Provides-Extra: arrow\nProvides-Extra: arrow\n"),
        (b"pyarrow==25.0.1", b"pyarrow==25.0.0"),
        (b"pyarrow==25.0.1", b"pyarrow>=25.0.1"),
        (b"; extra == 'arrow'", b""),
        (b"; extra == 'arrow'", b"; extra == 'unknown'"),
        (b"; extra == 'arrow'", b"; extra == 'ar row'"),
        (b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\n", b""),
        (
            b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\n",
            b"Requires-Dist: pyarrow==25.0.1; extra == 'arrow'\nRequires-Dist: pyarrow==26.0.0; extra == 'arrow'\n",
        ),
        (b"Requires-Dist: antlr4-python3-runtime>=4.13.2\n", b""),
        (b"Version: 0.1.0", b"Version: 0.2.0"),
        (b"Requires-Python: >=3.12", b"Requires-Python: >=3.13"),
        (
            b"Description-Content-Type: text/markdown",
            b"Description-Content-Type: text/plain",
        ),
        (b"# Pietto\n", b"# Wrong README\n"),
    ),
)
def test_metadata_damage_fails_each_artifact(
    tmp_path: Path, kind: str, before: bytes, after: bytes
):
    original = _metadata_bytes()
    assert before in original
    with pytest.raises(smoke.SmokeFailure):
        _inspect(_artifact(tmp_path, kind, original.replace(before, after, 1)), kind)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize("owner", RESULT_OWNERS)
def test_all_current_private_result_owners_are_required(
    tmp_path: Path, kind: str, owner: str
):
    with pytest.raises(smoke.SmokeFailure, match=owner):
        _inspect(
            _artifact(tmp_path, kind, _metadata_bytes(), missing=owner + ".py"), kind
        )


def test_console_entry_is_checked_in_wheel_and_sdist(tmp_path: Path):
    with pytest.raises(smoke.SmokeFailure, match="console entry"):
        _inspect(
            _artifact(
                tmp_path,
                "wheel",
                _metadata_bytes(),
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
            _artifact(tmp_path, "sdist", _metadata_bytes(), project=project), "sdist"
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


@pytest.mark.parametrize(
    "field",
    (
        b"Name: pietto",
        b"Version: 0.1.0",
        b"Requires-Python: >=3.12",
        b"Description-Content-Type: text/markdown",
    ),
)
@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_duplicate_singleton_metadata_is_rejected(
    tmp_path: Path, field: bytes, kind: str
):
    metadata = _metadata_bytes().replace(
        field + b"\n", field + b"\n" + field + b"\n", 1
    )
    with pytest.raises(smoke.SmokeFailure):
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
