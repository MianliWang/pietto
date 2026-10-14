from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any, cast


import _pietto_differential_process_acquisition as acquisition
import _pietto_project_graph_differential as phase59_probe
import _pietto_ir_window_differential as phase60_probe
import _pietto_ir_project_differential as phase61_probe
import _pietto_ir_join_differential as phase62_probe
import _pietto_ir_query_block_differential as phase63_probe
import _pietto_ir_flat_differential as phase64_probe
import _pietto_plan_differential as phase65_probe
import _pietto_sql_emission_differential as phase66_probe
import _pietto_project_explain_differential_probe as phase58_probe


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice2-differential-probe-process-acquisition-optimization-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
DIFFERENTIAL_TESTS = (
    "tests/test_harness_project_explain_differential.py",
    "tests/test_harness_compatibility_differential.py",
    "tests/test_harness_window_differential.py",
    "tests/test_harness_project_ir_differential.py",
    "tests/test_harness_join_differential.py",
    "tests/test_harness_query_block_ir_differential.py",
    "tests/test_harness_ir_differential.py",
    "tests/test_harness_plan_portability.py",
    "tests/test_harness_sql_emission_portability.py",
)
PROBES = {
    "phase58": phase58_probe,
    "phase59": phase59_probe,
    "phase60": phase60_probe,
    "phase61": phase61_probe,
    "phase62": phase62_probe,
    "phase63": phase63_probe,
    "phase64": phase64_probe,
    "phase65": phase65_probe,
    "phase66": phase66_probe,
}
TWO_INTERPRETERS = {(3, 13): "python3.13", (3, 12): "python3.12"}
HISTORICAL_FAMILIES = ("phase58", "phase59", "phase60", "phase61", "phase62", "phase63")
PREVIOUS_FAMILIES = (*HISTORICAL_FAMILIES, "phase64")
PHASE65_FAMILIES = (*PREVIOUS_FAMILIES, "phase65")
CURRENT_FAMILIES = (*PHASE65_FAMILIES, "phase66")
EXPECTED_SUPPORT_MANIFEST = (
    "_pietto_differential_probe_batch.py",
    "_pietto_project_explain_scenarios.py",
    "_pietto_project_explain_differential_probe.py",
    "_pietto_project_graph_differential.py",
    "_pietto_ir_window_differential.py",
    "_pietto_ir_project_differential.py",
    "_pietto_ir_join_differential.py",
    "_pietto_ir_query_block_differential.py",
    "_pietto_ir_flat_differential.py",
    "_pietto_plan_differential.py",
    "_pietto_sql_emission.py",
    "_pietto_sql_emission_differential.py",
)
# Copied support files that are not themselves family probes.
SUPPORT_ONLY = (
    "_pietto_differential_probe_batch.py",
    "_pietto_project_explain_scenarios.py",
    "_pietto_sql_emission.py",
)


def expected_request_manifest():
    """Independent keys, environments and ordering; no live registry reads."""
    current = tuple(sys.version_info[:2])
    versions = ((3, 13), (3, 12))
    seeds = ("0", "1", "7", "4294967295")
    rows = []
    for family in CURRENT_FAMILIES:
        if family in ("phase58", "phase59", "phase60", "phase61"):
            for seed in seeds:
                rows.append(
                    (family, f"seed:{seed}", current, seed, "checkout", f"seed-{seed}")
                )
            for version in versions:
                if version != current:
                    key = f"python{version[0]}.{version[1]}"
                    rows.append((family, key, version, "0", "checkout", key))
            rows.append(
                (
                    family,
                    "project-relocated",
                    current,
                    "0",
                    "checkout",
                    "project-relocated",
                )
            )
            rows.append(
                (
                    family,
                    "source-relocated",
                    current,
                    "0",
                    "relocated",
                    "source-relocated",
                )
            )
            if family != "phase58":
                for version, seed in (((3, 12), "1"), ((3, 13), "4294967295")):
                    key = (
                        f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
                    )
                    rows.append((family, key, version, seed, "relocated", key))
            rows.append(
                (
                    family,
                    "installed-wheel",
                    current,
                    "0",
                    "installed",
                    "installed-wheel",
                )
            )
        else:
            for version in versions:
                for seed in seeds:
                    key = f"source:python{version[0]}.{version[1]}:seed:{seed}"
                    rows.append((family, key, version, seed, "checkout", key))
            for mode in ("relocated", "installed"):
                for version in versions:
                    key = f"{mode}:python{version[0]}.{version[1]}:seed:7"
                    rows.append((family, key, version, "7", mode, key))
    return tuple(rows)


EXPECTED_REQUESTS = expected_request_manifest()
EXPECTED_FAMILY_REQUEST_COUNTS = {
    family: sum(row[0] == family for row in EXPECTED_REQUESTS)
    for family in CURRENT_FAMILIES
}
EXPECTED_CELL_COUNT = len({row[2:5] for row in EXPECTED_REQUESTS})
EXPECTED_LOGICAL_REQUESTS = len(EXPECTED_REQUESTS)
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright", "--threads", "4")),
    (
        "test typing",
        (
            "uv",
            "run",
            "pyright",
            "--project",
            "pyrightconfig.tests.json",
            "--threads",
            "4",
        ),
    ),
    ("tests", ("uv", "run", "pytest")),
)
FORBIDDEN_CACHE_TOKENS = (
    "lru_cache",
    "functools.cache",
    "shelve",
    "pickle",
    "sqlite3",
)


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_interlude_ii_slice2_validate",
        VALIDATE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _normalized(heading: str) -> str:
    return " ".join(_section(SPEC.read_text(encoding="utf-8"), heading).split())


def _plan() -> dict[acquisition.Cell, tuple[acquisition.Request, ...]]:
    return acquisition.cell_plan(TWO_INTERPRETERS)


def _run_batch(
    root: Path,
    families: tuple[str, ...],
    *,
    expect_success: bool = True,
    broken: str | None = None,
) -> tuple[subprocess.CompletedProcess[bytes], Path]:
    root.mkdir(parents=True, exist_ok=True)
    requests = []
    for family in families:
        workspace = root / family / "workspace"
        if family == broken:
            workspace.parent.mkdir(parents=True, exist_ok=True)
            workspace.write_text("not a directory", encoding="utf-8")
        requests.append(
            {
                "family": family,
                "key": f"{family}/only",
                "ambient": f"{family}-ambient",
                "workspace": str(workspace),
                "cwd": str(root / family / "run"),
            }
        )
    manifest = root / "manifest.json"
    output = root / "cell.json"
    manifest.write_text(
        json.dumps({"requests": requests}, separators=(",", ":")),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "7"
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        (
            sys.executable,
            str(acquisition.BATCH_CHILD),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ),
        capture_output=True,
        cwd=root,
        env=environment,
    )
    if expect_success:
        assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed, output


def _results(output: Path) -> dict[str, bytes]:
    payload = json.loads(output.read_text(encoding="utf-8"))
    return {
        key: base64.b64decode(value)
        for key, value in cast(dict[str, str], payload["results"]).items()
    }


validate = cast(Any, _load_validate_module())
