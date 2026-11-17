"""Build, inspect, install, and smoke test Pietto release artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
import configparser
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CHECK_INPUT = Path("examples/basic/types.pietto")
POSTGRES_INPUT = Path("tests/fixtures/postgres/compatibility_ordering_metadata.pietto")
POSTGRES_GOLDEN = Path(
    "tests/fixtures/golden/emit_sql_compatibility_ordering_metadata.sql"
)
MYSQL_INPUT = Path("tests/fixtures/mysql/compatibility_ordering_metadata.pietto")
MYSQL_GOLDEN = Path(
    "tests/fixtures/golden/emit_mysql_compatibility_ordering_metadata.json"
)
# The README "Project SQL emission" example, exercised through the installed
# console entrypoint as a real subprocess from an unrelated working directory.
PROJECT_EMIT_CONFIG = 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
PROJECT_EMIT_SOURCE = """shape Item:
    id: Int
    label: Text

source items: Item = postgres.table("fixture.items")

table active_items:
    from items
    select:
        id
        label
"""
PROJECT_EMIT_CONTRACT = """{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "postgres", "release": "18.6"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "fixture", "name": "items"},
    "scan": "relation_rows",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "item_id",
       "representation": {"storage": {"kind": "pg_int8"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "label", "column": "item_label",
       "representation": {"storage": {"kind": "pg_text"}, "nullable": false,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "UTF8", "collation": "C",
                                     "padding": "NO PAD"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"}
  ]
}
"""
PROJECT_EMIT_ARGUMENTS = (
    "emit-sql",
    "--project",
    "demo-emit",
    "--module",
    "main.pietto",
    "--kind",
    "table",
    "--name",
    "active_items",
    "--dialect",
    "postgres",
    "--emission-contract",
    "contract.json",
)

# The arrow-ready cell's real `duckdb_arrow` queries, so natural CI holds
# DuckDB native evidence on CPython 3.12 and 3.13 (D79.07): B1's filter;
# B2's grouped aggregate with `having`, `order by` with `limit`, and a filter
# with a literal and two parameters; and the second tier's `Int` arithmetic,
# `Date` and `Decimal` fields with a `Date` parameter, and an inner JOIN over
# a tuple of inputs.
DUCKDB_SOURCE = """shape Item:
    id: Int
    label: Text | None

shape Tag:
    id: Int
    name: Text
    since: Date
    fee: Decimal(6, 2) | None
    key = unique(id)

source items: Item = duckdb.arrow("items")
source tags: Tag = duckdb.arrow("tags")

query result(min_id: Int):
    from items
    where id >= min_id
    select:
        id
        label

query grouped(min_n: Int):
    from items
    group by label
    select:
        label
        n = count()
        filled = count(label)
        total = sum(id)
        high = max(id)
    having n >= min_n

table ordered:
    from items
    select:
        id
        label
    order by:
        label desc
        id
    limit 3

query filtered(low: Int, skip: Text):
    from items
    where id >= low and id != 3 and (label != skip or label is None)
    select:
        id
        label

table computed:
    from items
    select:
        id
        more = id + 1
        twice = id * 2

query dated(start: Date):
    from tags
    where since >= start
    select:
        id
        since
        fee

table joined:
    from items
    inner join tags on items.id == tags.id
    select:
        id = items.id
        label = items.label
        name = tags.name
"""
# Each query's kind, name and parameters, its rows over the check's tables
# (items: id 3, 1, 2, 6, 5, 4; label b, a, NULL, a, NULL, a; tags: id 1, 2, 7;
# since 2024-01-01, 2024-02-29, 2023-12-31), whether their order is part of
# the result, and the result schema's field names, Arrow types and
# nullability.
DUCKDB_ITEM = [("id", "int64", False), ("label", "string", True)]
DUCKDB_QUERIES = (
    ("query", "result", {"min_id": 5}, [(6, "a"), (5, None)], False, DUCKDB_ITEM),
    (
        "query",
        "grouped",
        {"min_n": 2},
        [("a", 3, 3, 11, 6), (None, 2, 0, 7, 5)],
        False,
        [
            ("label", "string", True),
            ("n", "int64", False),
            ("filled", "int64", False),
            ("total", "int64", True),
            ("high", "int64", True),
        ],
    ),
    ("table", "ordered", None, [(2, None), (5, None), (3, "b")], True, DUCKDB_ITEM),
    # Each condition of the filter drops a row that the others keep.
    (
        "query",
        "filtered",
        {"low": 3, "skip": "a"},
        [(5, None)],
        False,
        DUCKDB_ITEM,
    ),
    (
        "table",
        "computed",
        None,
        [(3, 4, 6), (1, 2, 2), (2, 3, 4), (6, 7, 12), (5, 6, 10), (4, 5, 8)],
        False,
        [("id", "int64", False), ("more", "int64", False), ("twice", "int64", False)],
    ),
    (
        "query",
        "dated",
        {"start": date(2024, 1, 1)},
        [(1, date(2024, 1, 1), Decimal("1.50")), (2, date(2024, 2, 29), None)],
        False,
        [
            ("id", "int64", False),
            ("since", "date32[day]", False),
            ("fee", "decimal128(6, 2)", True),
        ],
    ),
    (
        "table",
        "joined",
        None,
        [(1, "a", "x"), (2, None, "y")],
        False,
        [("id", "int64", False), ("label", "string", True), ("name", "string", False)],
    ),
)
# The keys of each query that reads other than `items` alone; one input is
# passed bare, several as a tuple.
DUCKDB_INPUTS = {"dated": ("tags",), "joined": ("items", "tags")}
DUCKDB_CONTRACT = """{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "duckdb", "release": "2.0.1"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "arrow", "name": "items"},
    "scan": "arrow_registration",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "id",
       "representation": {"storage": {"kind": "arrow_int64"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "label", "column": "label",
       "representation": {"storage": {"kind": "arrow_string"}, "nullable": true,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "UTF8", "collation": "C",
                                     "padding": "NO PAD"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }, {
    "selector": {"module": "main.pietto", "kind": "source", "name": "tags"},
    "relation": {"namespace": "arrow", "name": "tags"},
    "scan": "arrow_registration",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "id",
       "representation": {"storage": {"kind": "arrow_int64"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "name", "column": "name",
       "representation": {"storage": {"kind": "arrow_string"}, "nullable": false,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "UTF8", "collation": "C",
                                     "padding": "NO PAD"}}},
      {"ordinal": 2, "name": "since", "column": "since",
       "representation": {"storage": {"kind": "arrow_date32"}, "nullable": false,
                          "domain": {"kind": "date"}}},
      {"ordinal": 3, "name": "fee", "column": "fee",
       "representation": {"storage": {"kind": "arrow_decimal128", "precision": 6,
                                      "scale": 2},
                          "nullable": true,
                          "domain": {"kind": "decimal", "precision": 6, "scale": 2}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"},
    {"key": "parameter_protocol", "scope": "statement", "value": "duckdb_prepared"}
  ]
}
"""

# The extras of each installed cell. A bare --extra-env path is the arrow-ready
# cell, which carries the pinned DuckDB (D79.07); `interop-X=PATH` builds
# pietto[arrow,interop-X] (D80.05). Each cell is pre-seeded with only the
# allowlist blocks of its own locked closure.
INTEROP_EXTRAS = (
    "interop-pandas",
    "interop-polars",
    "interop-numpy",
    "interop-scipy",
    "interop-matplotlib",
)
EXTRA_CELLS = {
    "arrow": ("arrow",),
    "execute-duckdb": ("arrow", "execute-duckdb"),
    **{extra: ("arrow", extra) for extra in INTEROP_EXTRAS},
}
ALLOWLISTS = (
    Path("ci/phase67-arrow-compatibility-requirements.txt"),
    Path("ci/phase80-interop-requirements.txt"),
)
# Optional distributions' import roots that no public, CLI or private import
# may load.
OPTIONAL_ROOTS = frozenset(
    {
        "psycopg",
        "psycopg_binary",
        "pyarrow",
        "duckdb",
        "pandas",
        "polars",
        "numpy",
        "scipy",
        "matplotlib",
    }
)

GENERATED_FILES = frozenset(
    {
        "Pietto.interp",
        "Pietto.tokens",
        "PiettoLexer.interp",
        "PiettoLexer.py",
        "PiettoLexer.tokens",
        "PiettoParser.py",
        "PiettoVisitor.py",
        "__init__.py",
    }
)


@dataclass(frozen=True)
class ProjectContract:
    """Packaging values declared by the current project metadata."""

    name: str
    version: str
    requires_python: str
    dependencies: tuple[str, ...]
    console_entry: str
    readme: str | None
    extras: tuple[tuple[str, tuple[str, ...]], ...]
    license: str | None
    license_files: tuple[str, ...]
    classifiers: tuple[str, ...]
    urls: tuple[tuple[str, str], ...]
    keywords: tuple[str, ...]


class SmokeFailure(Exception):
    """A packaging smoke failure with a process-compatible exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _project_contract(project_text: str | None = None) -> ProjectContract:
    try:
        document = tomllib.loads(
            (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
            if project_text is None
            else project_text
        )
        project = document["project"]
        scripts = project["scripts"]
        return ProjectContract(
            name=project["name"],
            version=project["version"],
            requires_python=project["requires-python"],
            dependencies=tuple(project.get("dependencies", ())),
            console_entry=scripts["pietto"],
            readme=project.get("readme"),
            extras=tuple(
                (name, tuple(deps))
                for name, deps in project.get("optional-dependencies", {}).items()
            ),
            license=project.get("license"),
            license_files=tuple(project.get("license-files", ())),
            classifiers=tuple(project.get("classifiers", ())),
            urls=tuple(project.get("urls", {}).items()),
            keywords=tuple(project.get("keywords", ())),
        )
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise SmokeFailure(f"cannot read packaging contract: {error}") from error


def _run_command(
    stage: str,
    command: tuple[str, ...],
    *,
    cwd: Path,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    print(f"[package-smoke] {stage}: {shlex.join(command)}", flush=True)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=capture_output,
            env=env,
        )
    except OSError as error:
        raise SmokeFailure(f"{stage} could not start: {error}") from error

    if result.returncode == 0:
        return result

    if capture_output:
        if result.stdout:
            print(result.stdout.decode("utf-8", errors="replace"), end="")
        if result.stderr:
            print(
                result.stderr.decode("utf-8", errors="replace"),
                end="",
                file=sys.stderr,
            )
    raise SmokeFailure(
        f"{stage} failed with exit code {result.returncode}",
        result.returncode,
    )


def _find_artifacts(dist_dir: Path) -> tuple[Path, Path]:
    sdists = tuple(sorted(dist_dir.glob("*.tar.gz")))
    wheels = tuple(sorted(dist_dir.glob("*.whl")))
    if len(sdists) != 1 or len(wheels) != 1:
        raise SmokeFailure(
            "build must produce exactly one sdist and one wheel; "
            f"found {len(sdists)} sdist and {len(wheels)} wheel files"
        )
    return sdists[0], wheels[0]


def _required_runtime_files(prefix: str) -> frozenset[str]:
    required = {
        f"{prefix}/__init__.py",
        f"{prefix}/cli.py",
        f"{prefix}/compiler.py",
        f"{prefix}/_batch_output.py",
        f"{prefix}/parser_api.py",
        f"{prefix}/execution/__init__.py",
        f"{prefix}/execution/_access.py",
        f"{prefix}/execution/_duckdb.py",
        f"{prefix}/execution/_errors.py",
        f"{prefix}/execution/_handle.py",
        f"{prefix}/execution/_query.py",
        f"{prefix}/execution/_sqlite.py",
        f"{prefix}/interop/__init__.py",
        f"{prefix}/interop/_common.py",
        f"{prefix}/interop/_matplotlib.py",
        f"{prefix}/interop/_numpy.py",
        f"{prefix}/interop/_pandas.py",
        f"{prefix}/interop/_polars.py",
        f"{prefix}/interop/_scipy.py",
        f"{prefix}/_project_explain/__init__.py",
        f"{prefix}/_project_explain/compatibility_matrix_projection.py",
        f"{prefix}/_project_explain/composition.py",
        f"{prefix}/_project_explain/extension_catalog_evidence_projection.py",
        f"{prefix}/_project_explain/json_v1.py",
        f"{prefix}/_project_explain/model.py",
        f"{prefix}/_project_explain/package_requirement_projection.py",
        f"{prefix}/_project_explain/portability_projection.py",
        f"{prefix}/_project_explain/relation_columns.py",
        f"{prefix}/_project_explain/runtime_builder.py",
        f"{prefix}/_project_explain/text.py",
        f"{prefix}/_project/package_capability_requirements.py",
        f"{prefix}/_project/package_extension_signature_selectors.py",
        f"{prefix}/_project/project_result_contract.py",
        f"{prefix}/_project/project_result_binding.py",
        f"{prefix}/_project/project_public_execution.py",
        f"{prefix}/_project/project_duckdb_contract.py",
        f"{prefix}/_project/project_duckdb_result.py",
        f"{prefix}/_project/project_duckdb_emission.py",
        f"{prefix}/_project/project_duckdb_sql.py",
        f"{prefix}/_project/project_sqlite_result.py",
        f"{prefix}/_project/project_arrow_result.py",
        f"{prefix}/_project/project_result_contract_pure_boundary.py",
        f"{prefix}/_project/project_result_contract_portable.py",
        f"{prefix}/_project/project_scalar_meaning.py",
        f"{prefix}/_project/project_result_reader.py",
        f"{prefix}/_project/project_arrow_interop.py",
        f"{prefix}/_project/project_result_ingress.py",
        f"{prefix}/_project/project_result_ipc.py",
        f"{prefix}/_project/project_capability_environment.py",
        f"{prefix}/_project/extension_catalog_availability.py",
        f"{prefix}/_project/extension_catalog_inspection.py",
        f"{prefix}/_project/extension_catalog_inspection_pure_boundary.py",
        f"{prefix}/_project/extension_signature_provider.py",
        f"{prefix}/semantic/__init__.py",
        f"{prefix}/semantic/extension_catalog.py",
        f"{prefix}/semantic/extension_catalog_pure_boundary.py",
        f"{prefix}/semantic/extension_catalog_pg_trgm.py",
        f"{prefix}/semantic/extension_catalog_pgvector.py",
        f"{prefix}/semantic/extension_signature_requirements.py",
        f"{prefix}/ir/__init__.py",
        f"{prefix}/sql/postgres.py",
        f"{prefix}/sql/mysql.py",
        f"{prefix}/sql/sqlite.py",
        f"{prefix}/sql/sqlite_relations.py",
        f"{prefix}/sql/sqlite_render.py",
    }
    required.update(f"{prefix}/generated/{name}" for name in GENERATED_FILES)
    return frozenset(required)


def _missing_files(inventory: set[str], required: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(required - inventory))


def _dependency(value: str) -> tuple[str, tuple[str, ...], str, str, str | None]:
    """Parse only the current requirement forms (optional requirement extras such
    as `psycopg[binary]`), including legal spacing; the extras stay compared."""
    requirement, separator, marker = value.partition(";")
    specifier = r"(?:>=|==)\s*[0-9]+(?:\.[0-9]+)*"
    identifier = r"[A-Za-z0-9][A-Za-z0-9._-]*"
    match = re.fullmatch(
        rf"\s*({identifier})\s*(?:\[\s*({identifier}(?:\s*,\s*{identifier})*)?\s*\])?"
        rf"\s*(\(\s*{specifier}\s*\)|{specifier})\s*",
        requirement,
    )
    if match is None:
        raise SmokeFailure(f"unsupported artifact dependency {value!r}")
    name, selected_extras, spec = match.groups()
    extras = tuple(
        sorted(
            {
                re.sub(r"[-_.]+", "-", part.strip()).lower()
                for part in (selected_extras or "").split(",")
                if part.strip()
            }
        )
    )
    spec = re.sub(r"[\s()]", "", spec)
    operator = spec[:2]
    extra = None
    if separator:
        marker = marker.strip()
        if marker.startswith("(") and marker.endswith(")"):
            marker = marker[1:-1].strip()
        selected = re.fullmatch(r"extra\s*==\s*(['\"])([A-Za-z0-9._-]+)\1", marker)
        if selected is None:
            raise SmokeFailure(f"unsupported artifact extra condition {value!r}")
        extra = selected[2]
    return re.sub(r"[-_.]+", "-", name).lower(), extras, operator, spec[2:], extra


def _validate_core_metadata(metadata_bytes: bytes, contract: ProjectContract) -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(metadata_bytes)
    expected = {
        "Name": contract.name,
        "Version": contract.version,
        "Requires-Python": contract.requires_python,
    }
    for field, value in expected.items():
        if metadata.get_all(field) != [value]:
            raise SmokeFailure(
                f"artifact metadata {field} is {metadata.get(field)!r}, "
                f"expected {value!r}"
            )

    expected_dependencies = [_dependency(value) for value in contract.dependencies]
    for extra, dependencies in contract.extras:
        expected_dependencies.extend(
            _dependency(f"{value}; extra == '{extra}'") for value in dependencies
        )
    declared_dependencies = [
        _dependency(str(value)) for value in metadata.get_all("Requires-Dist", ())
    ]
    if Counter(declared_dependencies) != Counter(expected_dependencies):
        raise SmokeFailure("artifact runtime dependency/extra declarations differ")
    if Counter(metadata.get_all("Provides-Extra", ())) != Counter(
        name for name, _ in contract.extras
    ):
        raise SmokeFailure("artifact Provides-Extra declarations differ")
    if (
        metadata.get_all("Metadata-Version") != ["2.4"]
        or metadata.get_all("License-Expression") != [contract.license]
        or Counter(metadata.get_all("License-File", ()))
        != Counter(contract.license_files)
        or metadata.get_all("License") is not None
        or any(
            str(value).startswith("License ::")
            for value in metadata.get_all("Classifier", ())
        )
    ):
        raise SmokeFailure("artifact license metadata differs")
    if (
        Counter(metadata.get_all("Classifier", ())) != Counter(contract.classifiers)
        or Counter(
            tuple(part.strip() for part in str(value).split(",", 1))
            for value in metadata.get_all("Project-URL", ())
        )
        != Counter(contract.urls)
        # Keywords is a single-use field: one header carries the whole list.
        or [
            [part.strip() for part in str(value).split(",")]
            for value in metadata.get_all("Keywords", ())
        ]
        != ([list(contract.keywords)] if contract.keywords else [])
    ):
        raise SmokeFailure("artifact URL, classifier or keyword metadata differs")

    if contract.readme is not None:
        if metadata.get_all("Description-Content-Type") != ["text/markdown"]:
            raise SmokeFailure("artifact metadata is missing Markdown README metadata")
        payload = metadata.get_payload(decode=True)
        if not isinstance(payload, bytes) or payload.replace(b"\r\n", b"\n") != (
            REPO_ROOT / contract.readme
        ).read_bytes().replace(b"\r\n", b"\n"):
            raise SmokeFailure("artifact metadata is missing the declared README body")


def _inspect_wheel(wheel: Path, contract: ProjectContract) -> None:
    dist_info = f"{contract.name.replace('-', '_')}-{contract.version}.dist-info"
    metadata_path = f"{dist_info}/METADATA"
    entry_points_path = f"{dist_info}/entry_points.txt"

    try:
        with zipfile.ZipFile(wheel) as archive:
            inventory = set(archive.namelist())
            licenses = {f"{dist_info}/licenses/{p}": p for p in contract.license_files}
            required = _required_runtime_files(contract.name) | frozenset(
                {metadata_path, entry_points_path, f"{dist_info}/WHEEL", *licenses}
            )
            missing = _missing_files(inventory, required)
            if missing:
                raise SmokeFailure(
                    f"wheel is missing required files: {', '.join(missing)}"
                )
            for member, path in licenses.items():
                if archive.read(member) != (REPO_ROOT / path).read_bytes():
                    raise SmokeFailure(f"wheel license file differs: {path}")
            metadata_bytes = archive.read(metadata_path)
            entry_points_text = archive.read(entry_points_path).decode("utf-8")
    except (OSError, UnicodeError, zipfile.BadZipFile, KeyError) as error:
        raise SmokeFailure(f"cannot inspect wheel {wheel.name}: {error}") from error

    _validate_core_metadata(metadata_bytes, contract)
    parser = configparser.ConfigParser()
    try:
        parser.read_string(entry_points_text)
    except configparser.Error as error:
        raise SmokeFailure(f"invalid console entry point metadata: {error}") from error
    if parser.get("console_scripts", "pietto", fallback=None) != contract.console_entry:
        raise SmokeFailure(
            "wheel console entry point does not match "
            f"pietto = {contract.console_entry}"
        )


def _read_tar_member(archive: tarfile.TarFile, name: str) -> bytes:
    member = archive.extractfile(name)
    if member is None:
        raise SmokeFailure(f"sdist member is not a regular file: {name}")
    return member.read()


def _inspect_sdist(sdist: Path, contract: ProjectContract) -> None:
    prefix = f"{contract.name}-{contract.version}"
    metadata_path = f"{prefix}/PKG-INFO"
    required = _required_runtime_files(f"{prefix}/src/{contract.name}") | frozenset(
        {
            metadata_path,
            f"{prefix}/pyproject.toml",
        }
    )
    if contract.readme is not None:
        required |= frozenset({f"{prefix}/{contract.readme}"})
    licenses = {f"{prefix}/{path}": path for path in contract.license_files}
    required |= frozenset(licenses)

    try:
        with tarfile.open(sdist, mode="r:gz") as archive:
            inventory = set(archive.getnames())
            missing = _missing_files(inventory, required)
            if missing:
                raise SmokeFailure(
                    f"sdist is missing required files: {', '.join(missing)}"
                )
            for member, path in licenses.items():
                if _read_tar_member(archive, member) != (REPO_ROOT / path).read_bytes():
                    raise SmokeFailure(f"sdist license file differs: {path}")
            metadata_bytes = _read_tar_member(archive, metadata_path)
            project = _read_tar_member(archive, f"{prefix}/pyproject.toml").decode(
                "utf-8"
            )
            if _project_contract(project) != contract:
                raise SmokeFailure("sdist project metadata/console entry differs")
            if (
                contract.readme is not None
                and _read_tar_member(archive, f"{prefix}/{contract.readme}")
                != (REPO_ROOT / contract.readme).read_bytes()
            ):
                raise SmokeFailure("sdist README differs")
    except (OSError, UnicodeError, tarfile.TarError, KeyError) as error:
        raise SmokeFailure(f"cannot inspect sdist {sdist.name}: {error}") from error

    _validate_core_metadata(metadata_bytes, contract)


def _venv_python(venv_dir: Path) -> Path:
    executable = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return venv_dir / executable


def _venv_cli(venv_dir: Path) -> Path:
    executable = Path("Scripts/pietto.exe") if os.name == "nt" else Path("bin/pietto")
    return venv_dir / executable


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _copy_smoke_inputs(scratch_dir: Path) -> None:
    for relative_path in (CHECK_INPUT, POSTGRES_INPUT, MYSQL_INPUT):
        destination = scratch_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative_path, destination)


def _run_installed_cli(
    cli_path: Path,
    arguments: tuple[str, ...],
    *,
    scratch_dir: Path,
    stage: str,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[bytes]:
    result = _run_command(
        stage,
        (str(cli_path), *arguments),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    if os.name == "nt":
        # stdout ends lines with LF everywhere; Windows stderr ends them with CRLF.
        result.stderr = result.stderr.replace(b"\r\n", b"\n")
    return result


def _smoke_installed_lsp(
    command: tuple[str, ...],
    *,
    scratch_dir: Path,
    environment: dict[str, str],
    version: str,
) -> None:
    """One `initialize`, `shutdown`, `exit` round trip of `pietto lsp`."""

    def framed(*messages: dict[str, object]) -> bytes:
        bodies = [json.dumps(m, separators=(",", ":")).encode() for m in messages]
        return b"".join(b"Content-Length: %d\r\n\r\n%b" % (len(b), b) for b in bodies)

    arguments = (*command, "lsp", "--stdio")
    print(f"[package-smoke] installed CLI lsp: {shlex.join(arguments)}", flush=True)
    try:
        result = subprocess.run(
            arguments,
            input=framed(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
                {"jsonrpc": "2.0", "method": "exit"},
            ),
            cwd=scratch_dir,
            check=False,
            capture_output=True,
            env=environment,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SmokeFailure(f"installed CLI lsp did not finish: {error}") from error
    capabilities = {
        "positionEncoding": "utf-16",
        "textDocumentSync": {"openClose": True, "change": 1},
        "completionProvider": {},
        "hoverProvider": True,
        "definitionProvider": True,
        "documentSymbolProvider": True,
        "documentFormattingProvider": True,
        "workspaceSymbolProvider": True,
        "documentLinkProvider": {"resolveProvider": False},
    }
    expected = framed(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": capabilities,
                "serverInfo": {"name": "pietto", "version": version},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "result": None},
    )
    if (result.returncode, result.stdout, result.stderr) != (0, expected, b""):
        raise SmokeFailure("installed CLI lsp round trip is unexpected")


def _smoke_installed_cli(
    venv_dir: Path,
    scratch_dir: Path,
    contract: ProjectContract,
) -> None:
    try:
        scratch_dir.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        raise SmokeFailure("installed CLI scratch directory must be outside repository")

    cli_path = _venv_cli(venv_dir)
    if not cli_path.is_file():
        raise SmokeFailure(f"installed console script is missing: {cli_path}")

    _copy_smoke_inputs(scratch_dir)
    environment = _clean_environment()

    _run_command(
        "installed private project explain JSON v1 import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.json_v1",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain composition import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.composition",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain portability projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.portability_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain extension catalog evidence projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.extension_catalog_evidence_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain compatibility matrix projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.compatibility_matrix_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain package requirement projection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.package_requirement_projection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain model import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "import pietto._project_explain.model as project_explain_model; "
                "assert project_explain_model.PROJECT_EXPLAIN_ARTIFACT_NAME "
                "== 'Project Explain Artifact v1'; "
                "assert project_explain_model.ProjectExplainFormat."
                "PROJECT_EXPLAIN_V1.value == 'pietto.project-explain.v1'"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog availability import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_catalog_availability",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog inspection import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_catalog_inspection",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog inspection pure evaluation",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "from pietto._project.extension_catalog_inspection_pure_boundary "
                "import ExtensionCatalogInspectionPureDocument, "
                "ExtensionCatalogInspectionPureStatus, "
                "evaluate_extension_catalog_inspection_document, "
                "extension_catalog_inspection_pure_enumeration as e, "
                "extension_catalog_inspection_pure_text as s, "
                "extension_catalog_inspection_pure_tuple as t; "
                "assert evaluate_extension_catalog_inspection_document("
                "ExtensionCatalogInspectionPureDocument(root=t("
                "s('extension_catalog_inspection'), "
                "e('ExtensionCatalogInspectionFormat', "
                "'pietto.extension-catalog-inspection.v1'), "
                "s('consumer'), s('installed'), t(), t()))).status "
                "is ExtensionCatalogInspectionPureStatus.OK"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension catalog pure evaluation",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            (
                "from pietto.semantic.extension_catalog_pure_boundary "
                "import ExtensionCatalogPureDocument, ExtensionCatalogPureStatus, "
                "evaluate_extension_catalog_document; "
                "assert evaluate_extension_catalog_document("
                "ExtensionCatalogPureDocument(root=None)).status "
                "is ExtensionCatalogPureStatus.MISSING_ROOT"
            ),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private pgvector extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog_pgvector",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private pg_trgm extension catalog import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_catalog_pg_trgm",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension signature provider import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.extension_signature_provider",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private extension signature requirements import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto.semantic.extension_signature_requirements",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private package capability requirements import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.package_capability_requirements",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project capability environment import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.project_capability_environment",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private package extension signature selectors import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project.package_extension_signature_selectors",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain runtime builder import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.runtime_builder",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    _run_command(
        "installed private project explain text import",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "import pietto._project_explain.text",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )

    version = _run_installed_cli(
        cli_path,
        ("--version",),
        scratch_dir=scratch_dir,
        stage="installed CLI version",
        environment=environment,
    )
    expected_version = f"pietto {contract.version}\n".encode()
    if version.stdout != expected_version or version.stderr:
        raise SmokeFailure("installed CLI --version output is unexpected")

    help_result = _run_installed_cli(
        cli_path,
        ("--help",),
        scratch_dir=scratch_dir,
        stage="installed CLI help",
        environment=environment,
    )
    for marker in (b"usage: pietto", b"check", b"emit-sql", b"explain"):
        if marker not in help_result.stdout:
            raise SmokeFailure(f"installed CLI --help is missing {marker!r}")
    if help_result.stderr:
        raise SmokeFailure("installed CLI --help wrote unexpected stderr")

    _smoke_installed_lsp(
        (str(cli_path),),
        scratch_dir=scratch_dir,
        environment=environment,
        version=contract.version,
    )

    _run_installed_cli(
        cli_path,
        ("check", CHECK_INPUT.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI check",
        environment=environment,
    )

    project_root = scratch_dir / "project-check"
    project_root.mkdir()
    project_models = project_root / "models"
    project_models.mkdir()
    (project_root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models/*.pietto"]\n',
        encoding="utf-8",
    )
    (project_models / "user.pietto").write_text(
        "shape User:\n    id: Int\n",
        encoding="utf-8",
    )

    project_check_text = _run_installed_cli(
        cli_path,
        ("check", "--project", project_root.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI project check text",
        environment=environment,
    )
    if project_check_text.stdout != b"Project check OK: .\nFiles checked: 1\n":
        raise SmokeFailure("installed CLI project check text output is unexpected")
    if project_check_text.stderr:
        raise SmokeFailure("installed CLI project check text wrote unexpected stderr")

    project_check_json = _run_installed_cli(
        cli_path,
        ("check", "--project", project_root.as_posix(), "--format", "json"),
        scratch_dir=scratch_dir,
        stage="installed CLI project check JSON v2",
        environment=environment,
    )
    try:
        project_check_document = json.loads(project_check_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"cannot decode project check JSON v2: {error}") from error
    if project_check_document != {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {
            "root": ".",
            "config_path": "pietto.toml",
        },
        "inputs": [
            {
                "path": "models/user.pietto",
                "kind": "source",
                "status": "parsed",
            }
        ],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 1,
                "files_ok": 1,
                "files_with_errors": 0,
            }
        },
    }:
        raise SmokeFailure("installed CLI project check JSON v2 envelope is unexpected")
    if project_check_json.stderr:
        raise SmokeFailure(
            "installed CLI project check JSON v2 wrote unexpected stderr"
        )

    project_explain_root = scratch_dir / "project-explain"
    project_explain_package = project_explain_root / "package"
    project_explain_package.mkdir(parents=True)
    project_explain_manifest = (
        b'schema_version = 1\nnamespace = "example"\nname = "root"\n'
        b'version = "1.0.0"\n\n[[assets]]\nkind = "module_source"\n'
        b'path = "main.pietto"\n'
    )
    project_explain_source = b"shape Row:\n    id: Int\n"
    (project_explain_package / "pietto-package.toml").write_bytes(
        project_explain_manifest
    )
    (project_explain_package / "main.pietto").write_bytes(project_explain_source)
    digest_result = _run_command(
        "installed project explain package digest",
        (
            str(_venv_python(venv_dir)),
            "-I",
            "-c",
            "from pietto._project.package_loader import "
            "_compute_package_content_sha256 as compute; "
            f"print(compute({project_explain_manifest!r}, "
            f"(('main.pietto', {project_explain_source!r}),)))",
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=environment,
    )
    project_explain_digest = digest_result.stdout.decode("ascii").strip()
    (project_explain_root / "pietto.toml").write_text(
        'schema_version = 4\n\n[package]\npath = "package"\n'
        'namespace = "example"\nname = "root"\nversion = "1.0.0"\n'
        f'sha256 = "{project_explain_digest}"\n\n[capability_environment]\n',
        encoding="utf-8",
    )
    project_explain_text = _run_installed_cli(
        cli_path,
        ("explain", "--project", project_explain_root.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI project explain text",
        environment=environment,
    )
    for marker in (
        b"Project Explain Artifact v1\n",
        b"Targets (0)\n    none\n",
        b"project: indeterminate reason=no-evaluated-targets requirements=0\n",
    ):
        if marker not in project_explain_text.stdout:
            raise SmokeFailure(
                f"installed CLI project explain text is missing {marker!r}"
            )
    if project_explain_text.stderr:
        raise SmokeFailure("installed CLI project explain text wrote unexpected stderr")

    project_explain_json = _run_installed_cli(
        cli_path,
        (
            "explain",
            "--project",
            project_explain_root.as_posix(),
            "--format",
            "json",
        ),
        scratch_dir=scratch_dir,
        stage="installed CLI project explain JSON v1",
        environment=environment,
    )
    try:
        project_explain_document = json.loads(project_explain_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"cannot decode Project Explain JSON v1: {error}") from error
    if tuple(project_explain_document) != (
        "format",
        "ok",
        "diagnostics",
        "payload",
    ):
        raise SmokeFailure("installed Project Explain JSON field order is unexpected")
    payload = project_explain_document.get("payload")
    if (
        project_explain_document.get("format") != "pietto.project-explain.v1"
        or project_explain_document.get("ok") is not True
        or not isinstance(payload, dict)
        or payload.get("compatibility", {}).get("targets") != []
        or {"outcome", "exit_code"} & project_explain_document.keys()
    ):
        raise SmokeFailure("installed Project Explain JSON v1 envelope is unexpected")
    if (
        project_explain_json.stderr
        or not project_explain_json.stdout.endswith(b"\n")
        or project_explain_json.stdout.endswith(b"\n\n")
    ):
        raise SmokeFailure("installed Project Explain JSON stream is unexpected")

    explain_text = _run_installed_cli(
        cli_path,
        ("explain", CHECK_INPUT.as_posix()),
        scratch_dir=scratch_dir,
        stage="installed CLI explain text",
        environment=environment,
    )
    if b"Semantic Metadata Artifact v1\n" not in explain_text.stdout:
        raise SmokeFailure(
            "installed CLI explain text output is missing artifact header"
        )
    if explain_text.stderr:
        raise SmokeFailure("installed CLI explain text wrote unexpected stderr")

    explain_json = _run_installed_cli(
        cli_path,
        ("explain", CHECK_INPUT.as_posix(), "--format", "json"),
        scratch_dir=scratch_dir,
        stage="installed CLI explain JSON",
        environment=environment,
    )
    try:
        explain_document = json.loads(explain_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"cannot decode explain Artifact v1 JSON: {error}"
        ) from error
    if explain_document.get("artifact") != "Semantic Metadata Artifact v1":
        raise SmokeFailure("installed CLI explain JSON artifact identity is unexpected")
    if explain_document.get("command") != "explain":
        raise SmokeFailure("installed CLI explain JSON command is unexpected")
    if explain_document.get("schema_version") != 1:
        raise SmokeFailure("installed CLI explain JSON schema_version is unexpected")
    if explain_document.get("ok") is not True:
        raise SmokeFailure("installed CLI explain JSON ok field is unexpected")
    if "metadata" not in explain_document or "error" in explain_document:
        raise SmokeFailure("installed CLI explain JSON envelope is unexpected")
    if explain_json.stderr:
        raise SmokeFailure("installed CLI explain JSON wrote unexpected stderr")

    postgres = _run_installed_cli(
        cli_path,
        (
            "emit-sql",
            POSTGRES_INPUT.as_posix(),
            "--dialect",
            "postgres",
        ),
        scratch_dir=scratch_dir,
        stage="installed PostgreSQL text",
        environment=environment,
    )
    expected_postgres = (REPO_ROOT / POSTGRES_GOLDEN).read_bytes()
    if postgres.stdout != expected_postgres or postgres.stderr:
        raise SmokeFailure(
            "installed PostgreSQL text output differs from reviewed golden bytes"
        )

    mysql = _run_installed_cli(
        cli_path,
        (
            "emit-sql",
            MYSQL_INPUT.as_posix(),
            "--dialect",
            "mysql",
            "--format",
            "json",
        ),
        scratch_dir=scratch_dir,
        stage="installed MySQL JSON v1",
        environment=environment,
    )
    try:
        actual_mysql = json.loads(mysql.stdout)
        expected_mysql = json.loads((REPO_ROOT / MYSQL_GOLDEN).read_bytes())
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"cannot decode MySQL JSON v1 smoke output: {error}"
        ) from error
    if actual_mysql != expected_mysql or mysql.stderr:
        raise SmokeFailure(
            "installed MySQL JSON v1 output differs structurally from reviewed golden"
        )

    _smoke_project_emit_sql(cli_path, scratch_dir, environment)

    print(f"[package-smoke] installed CLI version: {version.stdout.decode().strip()}")
    print(
        "[package-smoke] installed CLI verified: --help, check, project check, "
        "single-file and project explain, PostgreSQL byte-exact text, "
        "MySQL JSON v1 structure, project emit-sql JSON/text/atomic file and batch directory",
        flush=True,
    )


def _smoke_project_emit_sql(
    cli_path: Path, scratch_dir: Path, environment: dict[str, str]
) -> None:
    """Run the installed project emit-sql command over real files (Slice13)."""

    project_root = scratch_dir / "demo-emit"
    project_root.mkdir()
    (project_root / "pietto.toml").write_text(PROJECT_EMIT_CONFIG, encoding="utf-8")
    (project_root / "main.pietto").write_text(PROJECT_EMIT_SOURCE, encoding="utf-8")
    (project_root / "contract.json").write_text(PROJECT_EMIT_CONTRACT, encoding="utf-8")
    as_json = _run_installed_cli(
        cli_path,
        PROJECT_EMIT_ARGUMENTS,
        scratch_dir=scratch_dir,
        stage="installed project emit-sql JSON",
        environment=environment,
    )
    try:
        document = json.loads(as_json.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"cannot decode project emit-sql output: {error}") from error
    if (
        as_json.stderr
        or not as_json.stdout.endswith(b"\n")
        or as_json.stdout.count(b"\n") != 1
        or document.get("format") != "pietto.sql-emission.v1"
        or document.get("status") != "VERIFIED"
        or set(document)
        != {
            "format",
            "status",
            "target",
            "request",
            "sql",
            "fixed_values",
            "parameter_uses",
            "columns",
            "ranges",
            "requirements",
            "diagnostics",
        }
        or not str(document.get("sql", "")).startswith("SELECT ")
        or document["request"]["owner"]
        != {"module": "main.pietto", "kind": "table", "name": "active_items"}
        or document["request"]["literal_policy"] != "preserve_literals"
    ):
        raise SmokeFailure("installed project emit-sql JSON document is unexpected")
    as_text = _run_installed_cli(
        cli_path,
        (*PROJECT_EMIT_ARGUMENTS, "--format", "text", "--output", "artifact.json"),
        scratch_dir=scratch_dir,
        stage="installed project emit-sql text with atomic artifact file",
        environment=environment,
    )
    if (
        as_text.stderr
        or not as_text.stdout.startswith(b"pietto.sql-emission.v1 VERIFIED\n")
        or document["sql"].encode("utf-8") not in as_text.stdout
        or (scratch_dir / "artifact.json").read_bytes() != as_json.stdout
        or any(path.suffix == ".tmp" for path in scratch_dir.iterdir())
    ):
        raise SmokeFailure("installed project emit-sql text/file output is unexpected")
    batch_arguments = (*PROJECT_EMIT_ARGUMENTS, "--all")
    batch = _run_installed_cli(
        cli_path,
        batch_arguments,
        scratch_dir=scratch_dir,
        stage="installed batch emit-sql JSON",
        environment=environment,
    )
    expected_batch = {
        "format": "pietto.sql-emission.batch.v1",
        "status": "VERIFIED",
        "items": [
            {
                "owner": document["request"]["owner"],
                "path": "artifacts/000000.json",
                "document": document,
            }
        ],
        "failure": None,
    }
    expected_bytes = (
        json.dumps(
            expected_batch, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")
    if batch.stderr or batch.stdout != expected_bytes:
        raise SmokeFailure("installed batch document differs from single-owner bytes")
    batch_output = subprocess.run(
        (str(cli_path), *batch_arguments, "--output", "batch"),
        cwd=scratch_dir,
        check=False,
        capture_output=True,
        env=environment,
    )
    batch_directory = scratch_dir / "batch"
    supported_directory = sys.platform == "win32" or (
        sys.platform == "linux" and batch_output.returncode == 0
    )
    if supported_directory:
        if (
            batch_output.stderr
            or batch_output.stdout != batch.stdout
            or (batch_directory / "manifest.json").read_bytes() != batch.stdout
            or (batch_directory / "artifacts/000000.json").read_bytes()
            != as_json.stdout
            or sorted(
                path.relative_to(batch_directory).as_posix()
                for path in batch_directory.rglob("*")
            )
            != ["artifacts", "artifacts/000000.json", "manifest.json"]
        ):
            raise SmokeFailure("installed batch directory bytes differ")
        batch_output = subprocess.run(
            (str(cli_path), *batch_arguments, "--output", "batch"),
            cwd=scratch_dir,
            check=False,
            capture_output=True,
            env=environment,
        )
        if (batch_directory / "manifest.json").read_bytes() != batch.stdout or (
            batch_directory / "artifacts/000000.json"
        ).read_bytes() != as_json.stdout:
            raise SmokeFailure("installed batch replaced existing files")
    elif batch_directory.exists():
        raise SmokeFailure("unsupported batch platform created output")
    try:
        batch_failure = json.loads(batch_output.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure("cannot decode installed batch refusal") from error
    expected_kind = "output_path" if supported_directory else "batch_output_platform"
    if (
        batch_output.returncode != 2
        or batch_output.stderr
        or batch_failure.get("status") != "INPUT_REJECTED"
        or batch_failure.get("items") != []
        or [
            error.get("kind")
            for error in batch_failure.get("failure", {}).get("cli_errors", [])
        ]
        != [expected_kind]
    ):
        raise SmokeFailure("installed batch refusal is unexpected")
    rejected = subprocess.run(
        (
            str(cli_path),
            *PROJECT_EMIT_ARGUMENTS[:8],
            "missing",
            *PROJECT_EMIT_ARGUMENTS[9:],
        ),
        cwd=scratch_dir,
        check=False,
        capture_output=True,
        env=environment,
    )
    try:
        failure = json.loads(rejected.stdout)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"cannot decode project emit-sql rejection: {error}"
        ) from error
    if (
        rejected.returncode != 2
        or rejected.stderr
        or failure.get("status") != "INPUT_REJECTED"
        or failure.get("artifact") is not None
        or [error.get("kind") for error in failure.get("cli_errors", [])]
        != ["emission_selector"]
    ):
        raise SmokeFailure("installed project emit-sql rejection is unexpected")
    columns = _run_installed_cli(
        cli_path,
        ("explain", "--project", "demo-emit", "--format", "json"),
        scratch_dir=scratch_dir,
        stage="installed project relation columns JSON",
        environment=environment,
    )
    if columns.stderr or columns.stdout != (
        b'{"cli_errors":[],"diagnostics":[],'
        b'"format":"pietto.project-relation-columns.v1","ok":true,"relations":'
        b'[{"columns":[{"name":"id","nullability":"non_null",'
        b'"type":{"kind":"builtin","name":"Int"}},{"name":"label",'
        b'"nullability":"non_null","type":{"kind":"builtin","name":"Text"}}],'
        b'"kind":"table","module":"main.pietto","name":"active_items"}]}\n'
    ):
        raise SmokeFailure("installed project relation columns document is unexpected")


def _installed_path(path: Path) -> Path:
    resolved = path.resolve()
    if (
        not resolved.is_relative_to(Path(sys.prefix).resolve())
        or "site-packages" not in resolved.parts
        or resolved.is_relative_to(REPO_ROOT)
    ):
        raise SmokeFailure(f"foreign installed origin: {resolved}")
    return resolved


def _installed_check(wheel: Path, extra: str) -> None:
    """Run under the clean installed interpreter, without checkout imports."""
    contract = _project_contract()
    distribution = importlib.metadata.distribution(contract.name)
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.endswith("/") or not (
                member.startswith("pietto/")
                or member.endswith(("/METADATA", "/entry_points.txt", "/WHEEL"))
                or member.startswith(
                    f"{contract.name}-{contract.version}.dist-info/licenses/"
                )
            ):
                continue
            installed = _installed_path(Path(distribution.locate_file(member)))
            if installed.read_bytes() != archive.read(member):
                raise SmokeFailure(f"installed candidate wheel bytes differ: {member}")
        _validate_core_metadata(
            archive.read(f"{contract.name}-{contract.version}.dist-info/METADATA"),
            contract,
        )
    direct = json.loads(distribution.read_text("direct_url.json") or "null")
    if not isinstance(direct, dict) or direct.get("url") != wheel.resolve().as_uri():
        raise SmokeFailure("installed candidate wheel location differs")
    importlib.import_module("pietto")
    cli = importlib.import_module("pietto.cli")
    importlib.import_module("pietto.execution")
    if any(name.split(".", 1)[0] in OPTIONAL_ROOTS for name in sys.modules):
        raise SmokeFailure("public execution import eagerly loaded a route dependency")
    for arguments in (
        ("--version",),
        ("--help",),
        ("check", CHECK_INPUT.as_posix()),
        ("emit-sql", POSTGRES_INPUT.as_posix(), "--dialect", "postgres"),
        ("emit-sql", MYSQL_INPUT.as_posix(), "--dialect", "mysql", "--format", "json"),
    ):
        with redirect_stdout(io.StringIO()):
            try:
                status = cli.main(arguments)
            except SystemExit as error:
                status = error.code
        if status != 0:
            raise SmokeFailure("installed CLI failed")
    for member in _required_runtime_files("pietto"):
        if "/_project/project_" in member:
            try:
                importlib.import_module(member[:-3].replace("/", "."))
            except ModuleNotFoundError as error:
                # The job and saved-result modules need POSIX fcntl; Windows
                # execution is NOTRUN, neither claimed nor newly refused.
                if os.name != "nt" or error.name != "fcntl":
                    raise
    if any(name == "pyarrow" or name.startswith("pyarrow.") for name in sys.modules):
        raise SmokeFailure("public/CLI/private import eagerly loaded PyArrow")
    if any(name.split(".", 1)[0] in OPTIONAL_ROOTS for name in sys.modules):
        raise SmokeFailure(
            "public/CLI/private import eagerly loaded an optional target"
        )
    for name, module in tuple(sys.modules.items()):
        if name == "pietto" or name.startswith("pietto."):
            _installed_path(Path(module.__file__))
    antlr = importlib.import_module("antlr4")
    dependencies = {
        "antlr4-python3-runtime": {
            "version": importlib.metadata.version("antlr4-python3-runtime"),
            "path": str(_installed_path(Path(antlr.__file__))),
        }
    }
    loader = importlib.import_module("pietto._project.project_arrow_result")._arrow
    if extra == "core":
        try:
            importlib.metadata.distribution("pyarrow")
        except importlib.metadata.PackageNotFoundError:
            pass
        else:
            raise SmokeFailure("core installation contains PyArrow distribution")
        if importlib.util.find_spec("pyarrow") is not None:
            raise SmokeFailure("core installation can resolve PyArrow")
        result_error = importlib.import_module(
            "pietto._project.project_result_contract"
        ).ResultError
        try:
            loader()
        except result_error as error:
            if str(error) != "ARROW_DEPENDENCY_MISSING":
                raise SmokeFailure("unexpected missing Arrow diagnostic") from error
        else:
            raise SmokeFailure("missing Arrow dependency was accepted")
    else:
        pa = loader()
        if (
            pa.__version__ != "26.0.1"
            or importlib.metadata.version("pyarrow") != "26.0.1"
        ):
            raise SmokeFailure("installed PyArrow pin differs")
        dependencies["pyarrow"] = {
            "version": pa.__version__,
            "path": str(_installed_path(Path(pa.__file__))),
        }
        for requirement in distribution.requires or ():
            name, _, _, version, selected = _dependency(requirement)
            if selected not in EXTRA_CELLS[extra] or name == "pyarrow":
                continue
            try:
                target = importlib.metadata.distribution(name)
            except importlib.metadata.PackageNotFoundError as error:
                raise SmokeFailure(f"installed {name} is missing") from error
            metadata = [
                file
                for file in target.files or ()
                if file.name == "METADATA" and file.parent.name.endswith(".dist-info")
            ]
            if target.version != version or len(metadata) != 1:
                raise SmokeFailure(f"installed {name} pin differs")
            dependencies[name] = {
                "version": target.version,
                "path": str(_installed_path(Path(target.locate_file(metadata[0])))),
            }
        if extra == "execute-duckdb":
            execution = importlib.import_module("pietto.execution")
            with tempfile.TemporaryDirectory(prefix="pietto-duckdb-") as temporary:
                root = Path(temporary)
                (root / "pietto.toml").write_text(PROJECT_EMIT_CONFIG, encoding="utf-8")
                (root / "main.pietto").write_text(DUCKDB_SOURCE, encoding="utf-8")
                (root / "contract.json").write_text(DUCKDB_CONTRACT, encoding="utf-8")
                queries = [
                    execution.compile_query(
                        root,
                        module="main.pietto",
                        kind=kind,
                        name=name,
                        dialect="duckdb",
                        emission_contract="contract.json",
                    )
                    for kind, name, *_ in DUCKDB_QUERIES
                ]
            tables = {
                "items": pa.table(
                    {
                        "id": pa.array([3, 1, 2, 6, 5, 4], pa.int64()),
                        "label": pa.array(
                            ["b", "a", None, "a", None, "a"], pa.string()
                        ),
                    }
                ),
                "tags": pa.table(
                    {
                        "id": pa.array([1, 2, 7], pa.int64()),
                        "name": pa.array(["x", "y", "z"], pa.string()),
                        "since": pa.array(
                            [date(2024, 1, 1), date(2024, 2, 29), date(2023, 12, 31)],
                            pa.date32(),
                        ),
                        "fee": pa.array(
                            [Decimal("1.50"), None, Decimal("-0.25")],
                            pa.decimal128(6, 2),
                        ),
                    }
                ),
            }
            for query, (_, name, parameters, expected, ordered, schema) in zip(
                queries, DUCKDB_QUERIES, strict=True
            ):
                inputs = tuple(
                    execution.DuckDBArrowInput(key, tables[key])
                    for key in DUCKDB_INPUTS.get(name, ("items",))
                )
                handle = execution.execute(
                    query,
                    route="duckdb_arrow",
                    access=inputs[0] if len(inputs) == 1 else inputs,
                    premise=None,
                    parameters=parameters,
                )
                with handle as result:
                    batches = [pa.record_batch(batch) for batch in result]
                rows = [
                    tuple(row.values())
                    for batch in batches
                    for row in batch.to_pylist()
                ]
                if not ordered:  # without `order by` a result is a bag
                    rows, expected = Counter(rows), Counter(expected)
                if (
                    rows != expected
                    or handle.outcome.end != "COMPLETE"
                    or any(
                        [(f.name, str(f.type), f.nullable) for f in batch.schema]
                        != schema
                        for batch in batches
                    )
                ):
                    raise SmokeFailure(
                        f"installed DuckDB Arrow query {name} result differs"
                    )
    print(
        json.dumps(
            {
                "cell": extra,
                "prefix": str(Path(sys.prefix).resolve()),
                "wheel": str(wheel.resolve()),
                "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "provides_extra": distribution.metadata.get_all("Provides-Extra"),
                "requires_dist": distribution.requires,
                "dependencies": dependencies,
                "lazy_import": True,
                "missing_arrow": extra == "core",
                "duckdb_arrow_query": extra == "execute-duckdb",
            },
            sort_keys=True,
        )
    )


def _check_installed_cell(
    venv_dir: Path, scratch_dir: Path, wheel: Path, extra: str
) -> None:
    result = _run_command(
        f"installed {extra} dependency isolation",
        (
            str(_venv_python(venv_dir)),
            "-I",
            str(Path(__file__).resolve()),
            "--installed-check",
            extra,
            "--wheel",
            str(wheel),
        ),
        cwd=scratch_dir,
        capture_output=True,
        env=_clean_environment(),
    )
    print(result.stdout.decode(), end="", flush=True)


def _pins(text: str, source: str) -> dict[str, str]:
    """Name -> version of each `name==version` requirement line."""
    pins: dict[str, str] = {}
    for line in text.splitlines():
        if not line[:1].isalnum():
            continue
        found = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)", line)
        if found is None:
            raise SmokeFailure(f"unsupported requirement line in {source}")
        name = re.sub(r"[-_.]+", "-", found[1]).lower()
        if name in pins:
            raise SmokeFailure(f"duplicate requirement {name} in {source}")
        pins[name] = found[2]
    return pins


def _allowlist_blocks() -> dict[str, tuple[str, str]]:
    """Name -> (version, hashed requirement block) across every allowlist."""
    blocks: dict[str, tuple[str, str]] = {}
    for relative in ALLOWLISTS:
        source = relative.as_posix()
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for block in re.split(r"\n(?=[^\s#])", text):
            lines = [
                line
                for line in block.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            if not lines:
                continue
            pins = _pins(lines[0], source)
            if (
                len(pins) != 1
                or not set(pins).isdisjoint(blocks)
                or len(lines) == 1
                or not all(
                    re.fullmatch(r"\s+--hash=sha256:[0-9a-f]{64}( \\)?", line)
                    for line in lines[1:]
                )
            ):
                raise SmokeFailure(f"malformed hash allowlist {source}")
            ((name, version),) = pins.items()
            blocks[name] = (version, "\n".join(lines))
    return blocks


def _cell_requirements(scratch_dir: Path, cell: str, core: Path) -> Path:
    """Write the allowlist blocks of exactly this cell's locked closure."""
    command = ["uv", "export", "--locked", "--no-dev", "--no-emit-project"]
    for extra in EXTRA_CELLS[cell]:
        command += ["--extra", extra]
    closure = _run_command(
        f"export locked {cell} closure",
        (*command, "--no-header", "--no-hashes", "--format", "requirements-txt"),
        cwd=REPO_ROOT,
        capture_output=True,
        env=_clean_environment(),
    ).stdout.decode()
    selected = _pins(closure, "locked closure")
    for name in _pins(core.read_text(encoding="utf-8"), "locked core"):
        selected.pop(name, None)
    allowed = _allowlist_blocks()
    blocks = []
    for name, version in sorted(selected.items()):
        if name not in allowed:
            raise SmokeFailure(f"{cell} closure lacks a hash allowlist entry: {name}")
        if allowed[name][0] != version:
            raise SmokeFailure(
                f"{cell} allowlist version differs from the lock: {name}"
            )
        blocks.append(allowed[name][1])
    path = scratch_dir / f"{cell}-requirements.txt"
    path.write_text("\n".join(blocks) + "\n", encoding="utf-8")
    return path


def _install_extra(
    venv_dir: Path, scratch_dir: Path, wheel: Path, cell: str = "arrow"
) -> None:
    if venv_dir.exists() or venv_dir.is_symlink():
        raise SmokeFailure("extra environment must begin at a new owned path")
    _run_command(
        "create clean extra environment",
        ("uv", "venv", "--python", sys.executable, str(venv_dir)),
        cwd=scratch_dir,
        env=_clean_environment(),
    )
    core = scratch_dir / "core-requirements.txt"
    _run_command(
        "export locked core dependencies",
        ("uv", "export", "--locked", "--no-dev", "--no-emit-project", "-o", str(core)),
        cwd=REPO_ROOT,
        env=_clean_environment(),
    )
    selected = _cell_requirements(scratch_dir, cell, core)
    # Hash verification pre-seeds dependencies; the wheel extra resolves them below.
    _run_command(
        "verify tested dependency wheels",
        (
            "uv",
            "pip",
            "install",
            "--python",
            str(_venv_python(venv_dir)),
            "--require-hashes",
            "--only-binary",
            ":all:",
            "--no-deps",
            "-r",
            str(core),
            "-r",
            str(selected),
        ),
        cwd=scratch_dir,
        env=_clean_environment(),
    )
    _run_command(
        f"install candidate {cell} extras",
        (
            "uv",
            "pip",
            "install",
            "--python",
            str(_venv_python(venv_dir)),
            "--no-index",
            f"{wheel}[{','.join(EXTRA_CELLS[cell])}]",
        ),
        cwd=scratch_dir,
        env=_clean_environment(),
    )


def _extra_cells(values: list[str]) -> list[tuple[str, Path]]:
    """The arrow-ready cell of a bare path and each `interop-X=PATH` cell, each
    once and at its own new owned path; any other `name=` value is refused."""
    cells: dict[str, Path] = {}
    for value in values:
        name, separator, path = value.partition("=")
        if separator and name not in INTEROP_EXTRAS:
            raise SmokeFailure(f"unknown extra environment cell {name!r}")
        cell = name if separator else "execute-duckdb"
        prefix = Path(path if separator else value).absolute()
        if cell in cells or prefix in cells.values():
            raise SmokeFailure("each extra environment cell needs its own path")
        if prefix.exists() or prefix.is_symlink():
            raise SmokeFailure("extra environment must begin at a new owned path")
        cells[cell] = prefix
    return list(cells.items())


def main(argv: list[str] | None = None) -> int:
    """Run the independent packaging and installed-CLI smoke validation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument(
        "--extra-env", action="append", default=[], metavar="[interop-X=]PATH"
    )
    parser.add_argument("--installed-check", choices=("core", *EXTRA_CELLS))
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.installed_check:
            if args.wheel is None:
                parser.error("--installed-check requires --wheel")
            _installed_check(args.wheel, args.installed_check)
            return 0
        cells = _extra_cells(args.extra_env)
        if args.dist_dir is not None and (
            args.dist_dir.exists() or args.dist_dir.is_symlink()
        ):
            raise SmokeFailure("dist directory must begin at a new owned path")
        contract = _project_contract()
        with tempfile.TemporaryDirectory(prefix="pietto-package-smoke-") as temporary:
            temporary_root = Path(temporary)
            dist_dir = (
                args.dist_dir.resolve() if args.dist_dir else temporary_root / "dist"
            )
            venv_dir = temporary_root / "venv"
            scratch_dir = temporary_root / "scratch"
            dist_dir.mkdir()
            scratch_dir.mkdir()

            _run_command(
                "build sdist and wheel",
                (
                    "uv",
                    "build",
                    "--sdist",
                    "--wheel",
                    "--out-dir",
                    str(dist_dir),
                ),
                cwd=REPO_ROOT,
            )
            sdist, wheel = _find_artifacts(dist_dir)
            print(f"[package-smoke] built sdist: {sdist.name}")
            print(f"[package-smoke] built wheel: {wheel.name}")

            _inspect_sdist(sdist, contract)
            _inspect_wheel(wheel, contract)
            print("[package-smoke] artifact inventory and metadata verified")

            _run_command(
                "create clean virtual environment",
                (sys.executable, "-m", "venv", str(venv_dir)),
                cwd=temporary_root,
            )
            venv_python = _venv_python(venv_dir)
            _run_command(
                "install wheel",
                (
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(venv_python),
                    str(wheel),
                ),
                cwd=temporary_root,
                env=_clean_environment(),
            )
            _smoke_installed_cli(venv_dir, scratch_dir, contract)
            _check_installed_cell(venv_dir, scratch_dir, wheel, "core")
            for cell, extra_dir in cells:
                extra_scratch = temporary_root / f"{cell}-scratch"
                extra_scratch.mkdir()
                _install_extra(extra_dir, extra_scratch, wheel, cell)
                _smoke_installed_cli(extra_dir, extra_scratch, contract)
                _check_installed_cell(extra_dir, extra_scratch, wheel, cell)
    except SmokeFailure as error:
        print(f"[package-smoke] error: {error}", file=sys.stderr)
        return error.exit_code

    print("[package-smoke] packaging and installed CLI smoke passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
