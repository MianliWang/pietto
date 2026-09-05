from __future__ import annotations

import base64
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier, Thread
from types import ModuleType
from typing import Any, cast

import pytest

import _pietto_differential_probe_batch as batch
import _pietto_differential_process_acquisition as acquisition
import _pietto_phase59_graph_differential_probe as phase59_probe
import _pietto_phase60_window_differential_probe as phase60_probe
import _pietto_phase61_project_ir_differential_probe as phase61_probe
import _pietto_phase62_join_differential_probe as phase62_probe
import _pietto_phase63_query_block_ir_differential_probe as phase63_probe
import _pietto_project_explain_differential_probe as phase58_probe
import _pietto_project_explain_scenarios as scenarios


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice2-differential-probe-process-acquisition-optimization-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
DIFFERENTIAL_TESTS = (
    "tests/test_phase58_slice16_pure_differential_compatibility_assurance.py",
    "tests/test_phase59_slice11_differential_compatibility_assurance.py",
    "tests/test_phase60_slice12_differential_compatibility.py",
    "tests/test_phase61_slice11_differential_compatibility.py",
    "tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
    "tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py",
)
PROBES = {
    "phase58": phase58_probe,
    "phase59": phase59_probe,
    "phase60": phase60_probe,
    "phase61": phase61_probe,
    "phase62": phase62_probe,
    "phase63": phase63_probe,
}
TWO_INTERPRETERS = {(3, 13): "python3.13", (3, 12): "python3.12"}
EXPECTED_FAMILY_REQUEST_COUNTS = {
    "phase58": 8,
    "phase59": 10,
    "phase60": 10,
    "phase61": 10,
    "phase62": 12,
    "phase63": 12,
}
EXPECTED_CELL_COUNT = 16
EXPECTED_LOGICAL_REQUESTS = 62
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
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


def test_process_cells_never_merge_incompatible_environment_facts() -> None:
    plan = _plan()
    assert len(plan) == EXPECTED_CELL_COUNT
    assert sum(len(requests) for requests in plan.values()) == EXPECTED_LOGICAL_REQUESTS

    for cell, requests in plan.items():
        assert requests
        for request in requests:
            assert request.cell == cell
        # A cell is exactly one (version, seed, mode) triple.
        assert {(cell.version, cell.seed, cell.mode)} == {
            (item.cell.version, item.cell.seed, item.cell.mode) for item in requests
        }
        # Every request keeps its own identity, workspace, cwd and ambient
        # marker; ambient markers are family-local, so uniqueness is per family.
        assert len({item.request_id for item in requests}) == len(requests)
        for family in acquisition.FAMILY_ORDER:
            local = [item for item in requests if item.family == family]
            assert len({item.ambient for item in local}) == len(local)

    versions = {cell.version for cell in plan}
    seeds = {cell.seed for cell in plan}
    modes = {cell.mode for cell in plan}
    assert versions == {(3, 12), (3, 13)}
    assert seeds == set(acquisition.SEEDS)
    assert modes == set(acquisition.MODES)

    # No cell mixes interpreters, seeds, or import roots.
    for left in plan:
        for right in plan:
            if left == right:
                continue
            assert (left.version, left.seed, left.mode) != (
                right.version,
                right.seed,
                right.mode,
            )

    # Compatible families genuinely share cells.
    shared = [cell for cell, requests in plan.items() if len(requests) > 1]
    assert len(shared) == EXPECTED_CELL_COUNT
    largest = max(plan.items(), key=lambda item: len(item[1]))
    assert len(largest[1]) == 10
    assert {item.family for item in largest[1]} == set(acquisition.FAMILY_ORDER)


def test_logical_request_matrices_and_witness_cells_are_unchanged() -> None:
    assert acquisition.SEEDS == ("0", "1", "7", "4294967295")
    assert acquisition.SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert acquisition.FAMILY_ORDER == tuple(PROBES)
    assert set(batch.FAMILY_MODULES) == set(PROBES)
    assert batch.CLI_SESSION_FAMILIES == frozenset({"phase58", "phase59", "phase60"})

    for family, expected in EXPECTED_FAMILY_REQUEST_COUNTS.items():
        requests = acquisition.family_requests(family, TWO_INTERPRETERS)
        assert len(requests) == expected
        assert len({item.key for item in requests}) == expected

    plan = _plan()
    relocated = {cell for cell in plan if cell.mode == "relocated"}
    installed = {cell for cell in plan if cell.mode == "installed"}
    assert {(cell.version, cell.seed) for cell in relocated} == {
        ((3, 13), "0"),
        ((3, 12), "1"),
        ((3, 13), "4294967295"),
        ((3, 13), "7"),
        ((3, 12), "7"),
    }
    assert {(cell.version, cell.seed) for cell in installed} == {
        ((3, 13), "0"),
        ((3, 13), "7"),
        ((3, 12), "7"),
    }
    assert {cell.version for cell in installed} == {(3, 12), (3, 13)}

    # Deliberate independent constructions are untouched.
    assert inspect.getsource(phase59_probe.observation).count("_real_graph(") == 2
    for probe in (phase60_probe, phase61_probe, phase62_probe, phase63_probe):
        assert inspect.getsource(probe.observation).count("_construction(") == 2


def test_batch_child_is_a_closed_allowlist_with_separate_exact_results(
    tmp_path: Path,
) -> None:
    assert sorted(batch.FAMILY_MODULES) == sorted(batch.FAMILY_AMBIENT)
    with pytest.raises(KeyError):
        batch._module("phase99")
    for family, module in PROBES.items():
        declared = getattr(module, "SEED_ENVIRONMENT", None)
        if declared is not None:
            assert declared == batch.FAMILY_AMBIENT[family]

    families = ("phase61", "phase63")
    _forward_process, forward_output = _run_batch(tmp_path / "forward", families)
    _reverse_process, reverse_output = _run_batch(
        tmp_path / "reverse", tuple(reversed(families))
    )
    forward = _results(forward_output)
    reverse = _results(reverse_output)

    assert set(forward) == set(reverse) == {f"{family}/only" for family in families}
    for family in families:
        key = f"{family}/only"
        assert forward[key] == reverse[key]
        assert forward[key].endswith(b"\n")
        assert not forward[key].endswith(b"\n\n")
    assert forward["phase61/only"] != forward["phase63/only"]


def test_one_failed_request_rejects_the_whole_cell(tmp_path: Path) -> None:
    completed, output = _run_batch(
        tmp_path / "broken",
        ("phase61", "phase63"),
        expect_success=False,
        broken="phase63",
    )
    assert completed.returncode == 1
    assert not output.exists()
    assert not tuple(tmp_path.glob("**/cell.json"))
    assert not tuple(tmp_path.glob("**/*.pending"))
    assert b"Traceback" in completed.stderr


def test_ephemeral_store_is_run_local_single_winner_and_uncached(
    tmp_path: Path,
) -> None:
    store = acquisition.DifferentialAcquisition(tmp_path / "store")
    assert store.root.is_relative_to(tmp_path)
    assert not store.root.is_relative_to(REPO_ROOT)

    productions: list[int] = []
    barrier = Barrier(4)

    def produce(target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        productions.append(1)

    def worker() -> None:
        barrier.wait()
        store._guarded("shared-resource", produce)

    threads = [Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(productions) == 1
    assert (store.root / "shared-resource.done").is_file()
    assert not (store.root / "shared-resource.lock").exists()

    def failing(target: Path) -> None:
        raise RuntimeError("deliberate acquisition failure")

    with pytest.raises(RuntimeError):
        store._guarded("broken-resource", failing)
    with pytest.raises(acquisition.AcquisitionFailure):
        store._guarded("broken-resource", failing)
    assert (store.root / "broken-resource.failed").is_file()
    assert not (store.root / "broken-resource.lock").exists()
    assert not tuple(store.root.glob("*.pending"))

    source = inspect.getsource(acquisition) + inspect.getsource(batch)
    for forbidden in FORBIDDEN_CACHE_TOKENS:
        assert forbidden not in source
    assert "getbasetemp" in inspect.getsource(acquisition.acquisition)
    assert "PYTEST_XDIST_WORKER" in inspect.getsource(acquisition.acquisition)


def test_cli_worker_session_keeps_separate_main_calls_and_order(
    tmp_path: Path,
) -> None:
    good = ("--version",)
    bad = ("not-a-command",)

    one_shot_good, one_shot_bad = scenarios._run_cli_pair(good, bad, REPO_ROOT)
    assert scenarios.active_cli_session() is None

    original_cwd = os.getcwd()
    with scenarios.cli_worker_session() as session:
        assert scenarios.active_cli_session() is session
        forward_good, forward_bad = scenarios._run_cli_pair(good, bad, REPO_ROOT)
        reverse_bad, reverse_good = scenarios._run_cli_pair(bad, good, REPO_ROOT)
        elsewhere = session.run(good, tmp_path)
    assert scenarios.active_cli_session() is None
    assert os.getcwd() == original_cwd

    def result(process: subprocess.CompletedProcess[bytes]):
        return process.returncode, process.stdout, process.stderr

    assert result(one_shot_good) == result(forward_good) == result(reverse_good)
    assert result(one_shot_bad) == result(forward_bad) == result(reverse_bad)
    assert result(elsewhere) == result(one_shot_good)
    assert forward_good.returncode == 0
    assert forward_good.stdout == b"pietto 0.1.0\n"
    assert forward_good.stderr == b""
    assert forward_bad.returncode != 0
    assert forward_bad.stdout == b""
    assert forward_bad.stderr

    pair_source = inspect.getsource(scenarios._run_cli_pair)
    assert "session.run(first, cwd), session.run(second, cwd)" in pair_source
    assert scenarios._CLI_WORKER_CODE.count("main(arguments)") == 1
    assert scenarios._CLI_PAIR_CODE.count("main(arguments)") == 1
    session_source = inspect.getsource(scenarios.CliWorkerSession)
    for forbidden in FORBIDDEN_CACHE_TOKENS:
        assert forbidden not in session_source
        assert forbidden not in scenarios._CLI_WORKER_CODE


def test_cli_worker_session_shuts_down_and_leaves_no_child() -> None:
    with scenarios.cli_worker_session() as session:
        process = session._process
        assert process.poll() is None
    assert process.poll() is not None
    assert scenarios.active_cli_session() is None


def test_probe_render_is_the_single_encoder_for_standalone_and_batch() -> None:
    for module in PROBES.values():
        render_source = inspect.getsource(module.render)
        main_source = inspect.getsource(module.main)
        assert "json.dumps(" in render_source
        assert "ensure_ascii=False" in render_source
        assert "allow_nan=False" in render_source
        assert 'separators=(",", ":")' in render_source
        assert "json.dumps(" not in main_source
        assert "render(observation(" in main_source
        for forbidden in ("sort_keys=True", ".sort(", "sorted("):
            assert forbidden not in render_source
    assert "module.observation(workspace)" in inspect.getsource(batch._acquire)


def test_static_boundaries_and_witness_matrices_are_zero_delta() -> None:
    assert validate.GATES == EXPECTED_GATES
    assert validate.PYTEST_COMMAND == ("uv", "run", "pytest")
    assert validate.PYTEST_DIST_CHOICES == ("loadfile", "loadscope")
    assert validate.PYTEST_WORKER_MEMORY_BYTES == 512 * 1024 * 1024
    assert validate.PYTEST_MIN_MEMORY_RESERVE_BYTES == 1024 * 1024 * 1024

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("uv run python scripts/validate.py --timings") == 1
    for override in ("--pytest-workers", "--pytest-dist", "--pytest-maxprocesses"):
        assert override not in workflow

    for name in DIFFERENTIAL_TESTS:
        source = (REPO_ROOT / name).read_text(encoding="utf-8")
        for forbidden in (
            "pytest.mark.skip",
            "pytest.mark.xfail",
            "pytest.skip(",
            "pytest.xfail(",
        ):
            assert forbidden not in source
        assert "SEEDS = " in source
        assert "SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))" in source

    acquisition_source = inspect.getsource(acquisition) + inspect.getsource(batch)
    for scheduling_flag in ("--pytest-workers", "--pytest-dist", "--dist=", '"-n"'):
        assert scheduling_flag not in acquisition_source


def test_specification_records_the_measured_optimization_and_closure() -> None:
    answer = _normalized("Answer And Scope")
    authority = _normalized("Starting Authority")
    audit = _normalized("Process Cell Audit")
    law = _normalized("Process Compatibility Law")
    cells = _normalized("Admitted Process Cells")
    gate = _normalized("Cross-family Contamination Gate")
    store = _normalized("Ephemeral Acquisition Store")
    session = _normalized("Nested CLI Worker Session")
    accounting = _normalized("Logical Versus Physical Accounting")
    proof = _normalized("Like-For-Like Performance Proof")
    xdist = _normalized("Xdist Correctness")
    closure = _section(
        SPEC.read_text(encoding="utf-8"), "Changed-Path And Lifecycle Lock"
    )

    assert "`OPTIMIZED`" in answer
    for value in (
        "69cf857310491b29822302f17d494293e33ff65b",
        "1fd51b9179c87988a2373ce62a370b65166abeab",
        "0cebaf14031779f4a824f1c44e5f7d65a0f5e782",
        "33954322616",
        "101274743680",
        "101274743571",
    ):
        assert value in authority
    for family in acquisition.FAMILY_ORDER:
        assert family in audit
    assert "total = 62 logical outer requests" in audit
    for rule in (
        "never simulated by mutating `os.environ` after interpreter startup",
        "Nothing is batched across Python 3.12 versus 3.13",
        "acquisition topology, never semantic identity",
    ):
        assert rule in law
    assert "62 logical requests group into exactly 16 exact cells" in cells
    assert "standalone == forward batch == reverse batch" in gate
    assert "Every family is batch-safe" in gate
    for store_fact in (
        "one pytest invocation",
        "Cross-run reuse | none",
        "Repository artifacts | none",
        "Semantic authority | none",
        "reclaims the lock",
    ):
        assert store_fact in store
    for session_fact in (
        "one separate `main(arguments)` call",
        "its own fresh stdout and stderr capture",
        "no observation cache",
        "no persistent child after context exit",
    ):
        assert session_fact in session
    for row in (
        "Logical request count | 62 | 62 | unchanged",
        "Semantic `pietto.cli.main` calls | 156 | 156 | unchanged",
        "Environment cells | 16 | 16 | unchanged",
        "Physical outer probe processes | 62 | 16",
        "Physical nested CLI worker processes | 78 | 9",
        "Parent-observed direct children | 109 | 38",
    ):
        assert row in accounting
    assert "Only physical acquisition decreases" in accounting
    for measurement in (
        "171.460s",
        "**85.015s**",
        "128.595s",
        "child-wall reduction = 50.42%",
        "targeted-wall reduction = 46.22%",
        "194 passed | 194 passed",
    ):
        assert measurement in proof
    for topology in ("serial", "`-n 2 --dist=loadfile`", "`-n 7 --dist=loadfile`"):
        assert topology in xdist
    assert "exactly 16 cell results from exactly 16 batch executions" in xdist
    assert "claims no scheduling gain" in xdist

    assert "`A4/M18/D0`, 22 paths" in " ".join(closure.split())
    added = tuple(line[2:] for line in closure.splitlines() if line.startswith("A "))
    modified = tuple(line[2:] for line in closure.splitlines() if line.startswith("M "))
    assert not any(line.startswith("D ") for line in closure.splitlines())
    assert len(added) == 4
    assert len(modified) == 18
    for path in (*added, *modified):
        assert (REPO_ROOT / path).is_file()
        assert not path.startswith((".github/", "src/", "scripts/", "grammar/"))
    assert all(name in modified for name in DIFFERENTIAL_TESTS)
    assert "production Python `179` unchanged" in " ".join(closure.split())
    assert "`423 -> 426`" in " ".join(closure.split())
    assert "sole mutable lifecycle-document reader" in " ".join(closure.split())
    assert "Interlude II Slice 3 = NEXT / NOT IMPLEMENTED" in closure
    assert "Interlude II Slice 4 = NOT IMPLEMENTED" in closure
    assert "Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED" in closure
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE3_HEAVY_FILE_XDIST_SCHEDULING_AND_ISOLATION_DECISION"
        in closure
    )
