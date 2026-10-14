from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import site
import subprocess
import sys

import pytest

import _pietto_extension_catalog_differential_vectors as vectors
from pietto._project.extension_catalog_inspection_pure_boundary import (
    ExtensionCatalogInspectionPureDocument,
    evaluate_extension_catalog_inspection_document,
)
from pietto.semantic.extension_catalog_pure_boundary import (
    ExtensionCatalogPureDocument,
    evaluate_extension_catalog_document,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
_SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))
_SEEDS = (None, "0", "1", "4294967295")
_IDENTIFIER_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


def _evaluate(vector: vectors.ExtensionCatalogDifferentialVector):
    if vector.boundary is vectors.ExtensionCatalogDifferentialBoundary.CATALOG:
        assert type(vector.document) is ExtensionCatalogPureDocument
        return evaluate_extension_catalog_document(vector.document)
    assert type(vector.document) is ExtensionCatalogInspectionPureDocument
    return evaluate_extension_catalog_inspection_document(vector.document)


def _run_corpus() -> tuple[tuple[str, str, str, int | None, int | None, bool], ...]:
    rows = []
    identifiers: set[str] = set()
    for vector in vectors.differential_vectors():
        assert type(vector) is vectors.ExtensionCatalogDifferentialVector
        assert (
            vector.vector_format == vectors.EXTENSION_CATALOG_DIFFERENTIAL_VECTOR_FORMAT
        )
        assert vector.vector_id and not (set(vector.vector_id) - _IDENTIFIER_CHARACTERS)
        assert vector.vector_id not in identifiers
        identifiers.add(vector.vector_id)
        assert vector.purposes and all(vector.purposes)
        outcome = _evaluate(vector)
        accepted = outcome.status.value == "ok"
        witness_matches = (
            outcome.canonical_bytes is not None
            and len(outcome.canonical_bytes) == vector.expected_byte_length
            and hashlib.sha256(outcome.canonical_bytes).hexdigest()
            == vector.expected_sha256
            if accepted
            else outcome.canonical_bytes is None
        )
        matched = (
            outcome.status is vector.expected_status
            and outcome.item_position == vector.expected_item_position
            and outcome.field_position == vector.expected_field_position
            and witness_matches
        )
        rows.append(
            (
                vector.vector_id,
                vector.boundary.value,
                outcome.status.value,
                outcome.item_position,
                outcome.field_position,
                matched,
            )
        )
    return tuple(rows)


def _corpus_digest() -> str:
    payload = "\n".join(
        f"{vector_id}:{boundary}:{status}:"
        f"{item if item is not None else '-'}:"
        f"{field if field is not None else '-'}:{matched}"
        for vector_id, boundary, status, item, field, matched in _run_corpus()
    )
    return hashlib.sha256(payload.encode()).hexdigest()


_SUBPROCESS_WITNESS = r"""
import hashlib
import _pietto_extension_catalog_differential_vectors as vectors
from pietto.semantic.extension_catalog_pure_boundary import evaluate_extension_catalog_document
from pietto._project.extension_catalog_inspection_pure_boundary import evaluate_extension_catalog_inspection_document
from pietto.semantic.extension_catalog_pgvector import PGVECTOR_V086_POSTGRESQL18_CATALOG
from pietto.semantic.extension_catalog_pg_trgm import PG_TRGM_V16_POSTGRESQL18_CATALOG
import _pietto_project_extension_inspection as slice11
rows = []
for vector in vectors.differential_vectors():
    outcome = (evaluate_extension_catalog_document(vector.document)
               if vector.boundary is vectors.ExtensionCatalogDifferentialBoundary.CATALOG
               else evaluate_extension_catalog_inspection_document(vector.document))
    accepted = outcome.status.value == "ok"
    witness = ((outcome.canonical_bytes is not None
                and len(outcome.canonical_bytes) == vector.expected_byte_length
                and hashlib.sha256(outcome.canonical_bytes).hexdigest() == vector.expected_sha256)
               if accepted else outcome.canonical_bytes is None)
    matched = (outcome.status is vector.expected_status
               and outcome.item_position == vector.expected_item_position
               and outcome.field_position == vector.expected_field_position
               and witness)
    item = outcome.item_position if outcome.item_position is not None else "-"
    field = outcome.field_position if outcome.field_position is not None else "-"
    rows.append(f"{vector.vector_id}:{vector.boundary.value}:{outcome.status.value}:{item}:{field}:{matched}")
corpus = hashlib.sha256("\n".join(rows).encode()).hexdigest()
vector = PGVECTOR_V086_POSTGRESQL18_CATALOG
trgm = PG_TRGM_V16_POSTGRESQL18_CATALOG
inspection = slice11._inspection(slice11._production_context()).canonical_bytes
print(f"{corpus}|{len(vector.canonical_bytes)}:{vector.content_sha256}|"
      f"{len(trgm.canonical_bytes)}:{trgm.content_sha256}|"
      f"{len(inspection)}:{hashlib.sha256(inspection).hexdigest()}", end="")
"""


def _site_packages() -> str:
    candidates = tuple(site.getsitepackages())
    assert candidates
    return candidates[0]


def _interpreter_version(executable: str) -> tuple[int, int] | None:
    try:
        major, minor = map(
            int,
            subprocess.check_output(
                [executable, "-c", "import sys; print(*sys.version_info[:2])"],
                text=True,
            ).split(),
        )
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    return major, minor


def _available_supported_interpreters() -> dict[tuple[int, int], str]:
    current = sys.version_info[:2]
    assert current in _SUPPORTED_INTERPRETERS
    available = {current: sys.executable}
    for version in _SUPPORTED_INTERPRETERS:
        if version == current:
            continue
        executable = shutil.which(f"python{version[0]}.{version[1]}")
        if executable is not None and _interpreter_version(executable) == version:
            available[version] = executable
    return available


def _subprocess_witness(
    executable: str,
    seed: str | None,
    root: Path,
) -> str:
    environment = dict(os.environ)
    if seed is None:
        environment.pop("PYTHONHASHSEED", None)
    else:
        environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(root / "src"), str(root / "tests"), _site_packages())
    )
    run_root = root / "run"
    run_root.mkdir(exist_ok=True)
    completed = subprocess.run(
        [executable, "-c", _SUBPROCESS_WITNESS],
        check=True,
        text=True,
        capture_output=True,
        env=environment,
        cwd=run_root,
    )
    return completed.stdout


def _relocate_repository(source: Path, target: Path) -> None:
    shutil.copytree(
        source / "src",
        target / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        source / "tests",
        target / "tests",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _build_witness_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, str]:
    roots = (
        tmp_path_factory.mktemp("slice12-relocated-one"),
        tmp_path_factory.mktemp("slice12-relocated-two"),
    )
    for root in roots:
        _relocate_repository(REPO_ROOT, root)
    interpreters = _available_supported_interpreters()
    observed = {
        f"current:{seed if seed is not None else 'default'}": _subprocess_witness(
            sys.executable,
            seed,
            REPO_ROOT,
        )
        for seed in _SEEDS
    }
    for version, executable in interpreters.items():
        # The current interpreter's seed-0 cell is exactly current:0.
        observed[f"python{version[0]}.{version[1]}:0"] = (
            observed["current:0"]
            if version == sys.version_info[:2]
            else _subprocess_witness(executable, "0", REPO_ROOT)
        )
    observed["relocated-one:default"] = _subprocess_witness(
        sys.executable,
        None,
        roots[0],
    )
    observed["relocated-two:default"] = _subprocess_witness(
        sys.executable,
        None,
        roots[1],
    )
    if python312 := interpreters.get((3, 12)):
        observed["combined:python3.12:seed1:relocated-one"] = _subprocess_witness(
            python312,
            "1",
            roots[0],
        )
    if python313 := interpreters.get((3, 13)):
        observed["combined:python3.13:seed4294967295:relocated-two"] = (
            _subprocess_witness(
                python313,
                "4294967295",
                roots[1],
            )
        )
    return observed
