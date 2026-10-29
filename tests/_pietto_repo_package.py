"""Shared package-artifact fixtures."""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = REPO_ROOT / "scripts" / "package_smoke.py"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = cast(Any, _load_module("pietto_package_smoke", SMOKE_PATH))


LICENSE_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "LICENSES/ANTLR-4.13.2.txt",
    "LICENSES/ANTLR-4.13.2-Python3-template-header.txt",
    "LICENSES/pgvector-0.8.6.txt",
    "LICENSES/PostgreSQL-18.6.txt",
    "LICENSES/SOURCES.md",
)


def license_members() -> dict[str, bytes]:
    """The reviewed license files and their repository bytes, in declared order."""
    return {path: (REPO_ROOT / path).read_bytes() for path in LICENSE_FILES}


def runtime_dependency_specifiers() -> tuple[str, ...]:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = pyproject["project"]["dependencies"]
    assert isinstance(dependencies, list)
    assert all(isinstance(dependency, str) for dependency in dependencies)
    return tuple(cast(list[str], dependencies))


def metadata_bytes() -> bytes:
    dependency_metadata = b"".join(
        f"Requires-Dist: {dependency}\n".encode("utf-8")
        for dependency in runtime_dependency_specifiers()
    )
    license_metadata = b"".join(
        f"License-File: {path}\n".encode("utf-8") for path in license_members()
    )
    contract = smoke._project_contract()
    classifier_metadata = b"".join(
        f"Classifier: {value}\n".encode("utf-8") for value in contract.classifiers
    )
    url_metadata = b"".join(
        f"Project-URL: {label}, {url}\n".encode("utf-8") for label, url in contract.urls
    )
    return b"".join(
        (
            b"Metadata-Version: 2.4\n",
            b"Name: pietto\n",
            f"Version: {contract.version}\n".encode("utf-8"),
            f"Keywords: {','.join(contract.keywords)}\n".encode("utf-8"),
            b"License-Expression: MIT\n",
            license_metadata,
            classifier_metadata,
            b"Requires-Python: >=3.12\n",
            url_metadata,
            dependency_metadata,
            b"Provides-Extra: arrow\n",
            b"Requires-Dist: pyarrow==26.0.0; extra == 'arrow'\n",
            b"Provides-Extra: execute-postgres\n",
            b"Requires-Dist: pyarrow==26.0.0; extra == 'execute-postgres'\n",
            b"Requires-Dist: psycopg[binary]==3.3.5; extra == 'execute-postgres'\n",
            b"Provides-Extra: execute-mysql\n",
            b"Requires-Dist: pyarrow==26.0.0; extra == 'execute-mysql'\n",
            b"Requires-Dist: mysql-connector-python==26.10.0; extra == 'execute-mysql'\n",
            b"Provides-Extra: execute-postgres-adbc\n",
            b"Requires-Dist: pyarrow==26.0.0; extra == 'execute-postgres-adbc'\n",
            b"Requires-Dist: adbc-driver-postgresql==1.12.0; extra == 'execute-postgres-adbc'\n",
            b"Requires-Dist: adbc-driver-manager==1.12.0; extra == 'execute-postgres-adbc'\n",
            b"Description-Content-Type: text/markdown\n",
            b"\n",
            (REPO_ROOT / "README.md").read_bytes(),
        )
    )
