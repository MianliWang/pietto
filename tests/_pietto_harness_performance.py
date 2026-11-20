"""The compile-time benchmark and the ten-node profile (PL.50 Q9, PL.58).

Two workloads, kept apart because they measure different things:

- **The compile-time benchmark** (``compile``) times the public
  ``pietto.compiler.compile_sql`` over the registered corpus of
  tests/_pietto_harness_generated_forms.py: seeds 0 to 39 of both profiles,
  each case compiled as an explicit-module project for PostgreSQL, and also
  for MySQL in the narrow profile, the project routes of
  tests/test_harness_generated_forms.py (120 compilations). It is a synthetic
  compiler workload of generated programs; it is not the ten-node profile and
  has no ten nodes. The project files are written once, as UTF-8 bytes with
  LF line ends, before any timing. ``warmup`` untimed passes run first, then
  ``repeats`` timed passes; each pass compiles every unit once in a fixed
  order after ``gc.collect()``. The report gives each pass's total, their
  median and each unit's median, in seconds from ``time.perf_counter_ns``,
  and the status and SHA-256 of each unit's output. Every pass must give the
  same outputs; a change is reported, never hidden. ``--product-root`` runs
  another checkout's ``src/pietto`` over the same corpus, which this file's
  own generator writes, so a base and a newer checkout compile the same
  bytes.
- **The ten-node profile** (``profile``) is the bounded profile of step 4 of
  docs/development.md ("Phase-end acquisition consolidation"): ten slowest
  in-process pytest nodes of a natural CI's health, each run alone, in a
  fresh process, under cProfile. ``HISTORICAL_TEN`` is the last recorded ten,
  the table of docs/phases/phase-78/completion-audit.md ("Ten-slowest
  profile", the health of natural CI ``44006845752``, Python 3.13); a newer
  health's ten are given with ``--nodes-file``. The profile window is each
  node's setup, call and teardown, not collection. Each node reports its
  phase seconds under the profiler, the runs of the complete verifier bodies
  that tests/test_project_verification_scope.py counts, per top-level call
  (an entry into ``pietto`` from a file outside it), the product
  functions called most often, the top self time, and the child processes it
  started, so that a child-dominated node is recorded as such.

Timings are observations, never assertions: no command here passes or fails
on a number. ``compare`` refuses two reports that are not the same
measurement (workload, corpus, warmup, repeats, unit, Python, hash seed) and
otherwise prints the medians side by side. The host is recorded, not judged:
the profile asks for a quiet host, which ``load_average`` lets a reader
check where the platform reports it.

Importing this module opens nothing and imports no ``pietto``; pytest checks
the entry points (tests/test_harness_performance.py). Run it explicitly, from
the repository root (docs/spec/generated-form-assurance-v1.md)::

    python tests/_pietto_harness_performance.py compile --directory OUT
    python tests/_pietto_harness_performance.py profile --directory OUT
    python tests/_pietto_harness_performance.py compare BASE.json OTHER.json
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
import cProfile
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import subprocess
import sys
import time
from typing import Any

import _pietto_harness_generated_forms as forms
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FORMAT = "pietto.harness.performance.v1"

# ---- the compile-time benchmark ----

WORKLOAD = "generated-forms-compile-sql"
ENTRY = "pietto.compiler.compile_sql"
# The generator's registered campaign (tests/test_harness_generated_forms.py,
# SEEDS and CORPUS_SHA256); the test owner checks that the two agree.
SEEDS = range(40)
WARMUP = 1
REPEATS = 5
UNIT = "seconds"
CLOCK = "time.perf_counter_ns"

Unit = tuple[int, str, str]  # (seed, profile, target)


def units(seeds: Iterable[int]) -> list[Unit]:
    """The compilations of the benchmark in their fixed order: PostgreSQL for
    both profiles and MySQL for the narrow one, as the generator's test owner
    compiles its projects."""
    return [
        (seed, profile, target)
        for seed in seeds
        for profile in forms.PROFILES
        for target in (("postgres", "mysql") if profile == "narrow" else ("postgres",))
    ]


def label(unit: Unit) -> str:
    seed, profile, target = unit
    return f"{profile}:{seed}:{target}"


def corpus_digest(seeds: Iterable[int]) -> str:
    """The digest of the generated cases, by the generator test's own rule."""
    digest = hashlib.sha256()
    for seed in seeds:
        for profile in forms.PROFILES:
            digest.update(repr(forms.generate(seed, profile)).encode() + b"\n")
    return digest.hexdigest()


def write_projects(root: Path, plan: Sequence[Unit]) -> tuple[dict[Unit, Path], str]:
    """Each unit's project under ``root``, and the digest of every file's
    name and bytes in order: the exact input the benchmark compiles."""
    digest = hashlib.sha256()
    projects = {}
    for unit in plan:
        seed, profile, target = unit
        project = root / f"{profile}-{seed}-{target}"
        project.mkdir(parents=True)
        for name, text in sorted(
            forms.project_files(forms.generate(seed, profile), target).items()
        ):
            data = text.encode("utf-8")
            (project / name).write_bytes(data)
            digest.update(f"{label(unit)}/{name}\0{len(data)}\0".encode() + data)
        projects[unit] = project
    return projects, digest.hexdigest()


def compile_unit(project: Path, target: str) -> Any:
    """One compilation through the public entry, as the generator's test
    owner calls it."""
    from pietto.compiler import compile_sql

    return compile_sql(
        project,
        module="main.pietto",
        kind="query",
        name="q",
        dialect=target,
        emission_contract="contract.json",
    )


def output_digest(emission: Any) -> str:
    return hashlib.sha256(
        emission.status.encode() + b"\0" + bytes(emission.document)
    ).hexdigest()


def _seconds(nanoseconds: float) -> float:
    return round(nanoseconds / 1e9, 9)


def benchmark(
    root: Path,
    seeds: range = SEEDS,
    warmup: int = WARMUP,
    repeats: int = REPEATS,
    *,
    compile: Callable[[Path, str], Any] = compile_unit,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    """Run the benchmark over ``seeds`` with projects under ``root``."""
    if type(warmup) is not int or warmup < 0:
        raise ValueError("warmup must be a non-negative integer")
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    plan = units(seeds)
    projects, workload_digest = write_projects(root, plan)
    outputs: dict[str, tuple[str, str]] = {}
    changes: list[str] = []
    passes: list[list[int]] = []
    for index in range(warmup + repeats):
        gc.collect()
        times = []
        for unit in plan:
            start = clock()
            emission = compile(projects[unit], unit[2])
            elapsed = clock() - start
            seen = (emission.status, output_digest(emission))
            first = outputs.setdefault(label(unit), seen)
            if seen != first:
                changes.append(f"pass {index}: {label(unit)} {first} -> {seen}")
            times.append(elapsed)
        if index >= warmup:
            passes.append(times)
    totals = [sum(times) for times in passes]
    return {
        "format": FORMAT,
        "kind": "compile",
        "workload": WORKLOAD,
        "entry": ENTRY,
        "seeds": [seeds.start, seeds.stop],
        "profiles": list(forms.PROFILES),
        "units": [label(unit) for unit in plan],
        "corpus_sha256": corpus_digest(seeds),
        "workload_sha256": workload_digest,
        "warmup": warmup,
        "repeats": repeats,
        "unit": UNIT,
        "clock": CLOCK,
        "gc": "enabled, collected before each pass",
        "pass_ns": totals,
        "pass_seconds": [_seconds(total) for total in totals],
        "median_pass_seconds": _seconds(statistics.median(totals)),
        "min_pass_seconds": _seconds(min(totals)),
        "max_pass_seconds": _seconds(max(totals)),
        "unit_median_seconds": {
            label(unit): _seconds(statistics.median(times[i] for times in passes))
            for i, unit in enumerate(plan)
        },
        "statuses": dict(sorted(Counter(s for s, _ in outputs.values()).items())),
        "outputs": {key: list(value) for key, value in outputs.items()},
        "outputs_stable": not changes,
        "output_changes": changes,
    }


# ---- the ten-node profile ----

# The ten slowest in-process nodes of the health of natural CI 44006845752,
# Python 3.13, as docs/phases/phase-78/completion-audit.md records them; the
# test owner reads that table and checks this list against it.
HISTORICAL_SOURCE = "docs/phases/phase-78/completion-audit.md#b2-acquisition-review"
HISTORICAL_CI = "44006845752"
HISTORICAL_TEN = (
    "tests/test_harness_sql_emission_portability.py::"
    "test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]",
    "tests/test_harness_sql_emission_portability.py::"
    "test_every_admitted_artifact_exports_corresponds_and_decodes[mysql]",
    "tests/test_harness_target_conformance.py::"
    "test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]",
    "tests/test_repo_reader_acquisition.py::"
    "test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition",
    "tests/test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap",
    "tests/test_harness_target_conformance.py::"
    "test_empty_text_anchor_requires_the_observed_var_string_type",
    "tests/test_semantic_capability_facts.py::"
    "test_private_module_has_only_authorized_window_strategy_compiler_consumer",
    "tests/test_project_r2_proposal.py::"
    "test_r2_refuses_a_paired_mysql_form_before_any_workspace",
    "tests/test_execution_compiled_bundle.py::"
    "test_mysql_lpad_and_now_cells_are_derived_in_linear_work[words-_chained_lets]",
    "tests/test_sql_project_scalar_expressions.py::"
    "test_q1_scalar_surface_is_verified_through_both_project_targets[mysql]",
)
TOP = 15  # rows of the most-called and self-time lists
_CHILD_STARTS = {("subprocess.py", "_execute_child")}
_CHILD_WAIT = {("subprocess.py", "wait")}
_CHILD_COMMUNICATE = {("subprocess.py", "communicate")}


def verifier_bodies() -> dict[str, tuple[str, int]]:
    """The complete verifier bodies that the verification budget counts
    (tests/test_project_verification_scope.py, BODIES), by code location."""
    import test_project_verification_scope as scope

    return {
        name: (body.__code__.co_filename, body.__code__.co_firstlineno)
        for name, body in scope.BODIES.items()
    }


class _Inside:
    """Whether a profiled function's file lies under ``product``."""

    def __init__(self, product: Path) -> None:
        self.product = product.resolve()
        self.known: dict[str, bool] = {}

    def __call__(self, filename: str) -> bool:
        if filename not in self.known:
            inside = False
            if filename and not filename.startswith(("~", "<")):
                try:
                    inside = Path(filename).resolve().is_relative_to(self.product)
                except (OSError, ValueError):
                    inside = False
            self.known[filename] = inside
        return self.known[filename]


def _where(key: tuple[str, int, str], root: Path) -> str:
    filename, line, name = key
    if filename.startswith(("~", "<")):
        return name
    path = Path(filename)
    try:
        path = path.resolve().relative_to(root)
    except (OSError, ValueError):
        path = Path(path.name)
    return f"{path.as_posix()}:{line}({name})"


def summarize(
    stats: pstats.Stats,
    product: Path,
    bodies: dict[str, tuple[str, int]],
    root: Path = ROOT,
    top: int = TOP,
) -> dict[str, Any]:
    """What step 4 reads of one profile window.

    cProfile's entries are ``(primitive calls, calls, self, cumulative,
    callers)``, and each caller's ``(calls, primitive calls, self,
    cumulative)``. A top-level call is a call of a product function from a
    Python frame of a file outside the product. A built-in caller is not
    counted, since it is how product code resumes its own generators, and
    neither is a frame without a file, such as the import machinery running
    a module's body. cProfile records a caller only for frames entered while
    it was enabled, so a call from a frame that was already running when the
    window opened has no caller: those calls, a function's calls less the
    calls its recorded callers made, count as top-level too."""
    entries: dict[tuple[str, int, str], Any] = stats.stats  # type: ignore[attr-defined]
    inside = _Inside(product)
    top_level = 0
    for (filename, _, _), (_, calls, _, _, callers) in entries.items():
        if inside(filename):
            recorded = sum(counts[0] for counts in callers.values())
            top_level += max(calls - recorded, 0) + sum(
                counts[0]
                for caller, counts in callers.items()
                if not caller[0].startswith(("~", "<")) and not inside(caller[0])
            )
    located = {
        (str(Path(filename).resolve()), line): calls
        for (filename, line, _), (_, calls, _, _, _) in entries.items()
        if not filename.startswith(("~", "<"))
    }
    runs = {
        name: located.get((str(Path(filename).resolve()), line), 0)
        for name, (filename, line) in bodies.items()
    }
    product_calls = sorted(
        (
            (calls, key)
            for key, (_, calls, _, _, _) in entries.items()
            if inside(key[0])
        ),
        key=lambda item: (-item[0], item[1]),
    )[:top]
    self_time = sorted(
        ((values[2], key) for key, values in entries.items()),
        key=lambda item: (-item[0], item[1]),
    )[:top]

    def matching(names: set[tuple[str, str]], column: int) -> float:
        return sum(
            values[column]
            for (filename, _, name), values in entries.items()
            if (Path(filename).name, name) in names
        )

    def share(count: int) -> float | None:
        return round(count / top_level, 3) if top_level else None

    # `communicate` waits through `wait`, so the larger is the time waited.
    waited = max(matching(_CHILD_WAIT, 3), matching(_CHILD_COMMUNICATE, 3))
    return {
        "top_level_calls": top_level,
        "verifier_runs": runs,
        "verifier_runs_per_top_level_call": {
            name: share(count) for name, count in runs.items()
        },
        "most_called": [
            {
                "function": _where(key, root),
                "calls": calls,
                "per_top_level_call": share(calls),
            }
            for calls, key in product_calls
        ],
        "top_self_time": [
            {"function": _where(key, root), "self_seconds": round(seconds, 6)}
            for seconds, key in self_time
        ],
        "child_process_starts": int(matching(_CHILD_STARTS, 1)),
        "child_wait_seconds": round(waited, 6),
    }


class _Window:
    """A pytest plugin that profiles each node's setup, call and teardown,
    and nothing of collection."""

    def __init__(self) -> None:
        self.profile = cProfile.Profile()
        self.nodes: list[str] = []
        self.phases: dict[str, dict[str, Any]] = {}
        self.window_ns = 0

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item: Any, nextitem: Any) -> Any:
        self.nodes.append(item.nodeid)
        start = time.perf_counter_ns()
        self.profile.enable()
        try:
            return (yield)
        finally:
            self.profile.disable()
            self.window_ns += time.perf_counter_ns() - start

    def pytest_runtest_logreport(self, report: Any) -> None:
        self.phases[report.when] = {
            "outcome": report.outcome,
            "seconds": round(report.duration, 6),
        }


def profile_node(node: str, checkout: Path, stats_path: Path) -> dict[str, Any]:
    """Run ``node`` alone in this process under cProfile and summarize it."""
    window = _Window()
    code = pytest.main(
        ["-p", "no:cacheprovider", "-n", "0", "-q", "--rootdir", str(checkout), node],
        plugins=[window],
    )
    window.profile.dump_stats(stats_path)
    result: dict[str, Any] = {
        "node": node,
        "exit_code": int(code),
        "collected": window.nodes,
        "phases": window.phases,
        "window_seconds": _seconds(window.window_ns),
        "seconds_note": "under cProfile; call counts do not depend on load",
    }
    if window.nodes != [node]:
        result["outcome"] = "not_collected" if not window.nodes else "not_alone"
        return result
    failed = [p for p, v in window.phases.items() if v["outcome"] != "passed"]
    result["outcome"] = "passed" if not failed and code == 0 else "failed"
    try:
        bodies = verifier_bodies()
    except Exception as error:  # an older or newer checkout may lack them
        bodies, result["verifier_bodies_error"] = {}, repr(error)
    import pietto

    product = Path(pietto.__file__).resolve().parent
    result["product"] = str(product)
    result.update(summarize(pstats.Stats(str(stats_path)), product, bodies, checkout))
    result["child_dominated"] = (
        result["child_wait_seconds"] > 0.5 * result["window_seconds"]
        if result["window_seconds"]
        else False
    )
    return result


def _load() -> list[float] | None:
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return None  # not reported on this platform


def _git(checkout: Path, *args: str) -> str | None:
    try:
        run = subprocess.run(
            ["git", "-C", str(checkout), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def environment(checkout: Path) -> dict[str, Any]:
    """The facts that make two reports the same measurement, and the host."""
    status = _git(checkout, "status", "--porcelain")
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpus": os.cpu_count(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "checkout": str(checkout),
        "head": _git(checkout, "rev-parse", "HEAD"),
        "tree": _git(checkout, "rev-parse", "HEAD^{tree}"),
        "dirty": None if status is None else bool(status),
        "load_average": _load(),
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _child_environment(checkout: Path) -> dict[str, str]:
    """The node's environment: this one, with the checkout's sources first
    and no pytest options or worker state inherited."""
    names = ("PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST", "PYTEST_XDIST_WORKER")
    child = {
        key: value
        for key, value in os.environ.items()
        if key not in names and not key.startswith("PYTEST_XDIST_")
    }
    paths = [str(checkout / "src"), child.get("PYTHONPATH", "")]
    child["PYTHONPATH"] = os.pathsep.join(path for path in paths if path)
    return child


def profile(
    directory: Path,
    nodes: Sequence[str] = HISTORICAL_TEN,
    checkout: Path = ROOT,
    python: str = sys.executable,
) -> dict[str, Any]:
    """Run each node alone in a fresh process under cProfile."""
    directory.mkdir()
    report: dict[str, Any] = {
        "format": FORMAT,
        "kind": "profile",
        "nodes": list(nodes),
        "nodes_source": (
            f"{HISTORICAL_SOURCE} (CI {HISTORICAL_CI})"
            if tuple(nodes) == HISTORICAL_TEN
            else "--nodes-file"
        ),
        "environment": environment(checkout),
        "results": [],
    }
    for index, node in enumerate(nodes):
        out, stats = directory / f"{index:02d}.json", directory / f"{index:02d}.prof"
        load = _load()
        started = time.perf_counter_ns()
        run = subprocess.run(
            [
                python,
                str(Path(__file__).resolve()),
                "profile-node",
                "--node",
                node,
                "--checkout",
                str(checkout),
                "--stats",
                str(stats),
                "--out",
                str(out),
            ],
            cwd=checkout,
            env=_child_environment(checkout),
            capture_output=True,
            text=True,
            check=False,
        )
        (directory / f"{index:02d}.log").write_text(
            run.stdout + run.stderr, encoding="utf-8"
        )
        if out.is_file():
            result = json.loads(out.read_text(encoding="utf-8"))
        else:
            result = {"node": node, "outcome": "no_report", "exit": run.returncode}
        result["load_before"] = load
        result["process_seconds"] = _seconds(time.perf_counter_ns() - started)
        report["results"].append(result)
    (directory / "report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


# ---- comparison ----

_SAME = {
    "compile": (
        "format",
        "workload",
        "entry",
        "seeds",
        "units",
        "corpus_sha256",
        "workload_sha256",
        "warmup",
        "repeats",
        "unit",
        "clock",
    ),
    "profile": ("format", "nodes"),
}
_SAME_ENVIRONMENT = ("python", "implementation", "pythonhashseed")


def compare(base: dict[str, Any], other: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(lines, problems): the two reports side by side, and every reason they
    are not the same measurement. Timings never make a problem."""
    problems = []
    kind = base.get("kind")
    if kind not in _SAME or other.get("kind") != kind:
        return [], [f"kind: {kind} != {other.get('kind')}"]
    for key in _SAME[kind]:
        if base.get(key) != other.get(key):
            problems.append(f"{key} differs")
    for key in _SAME_ENVIRONMENT:
        left = base.get("environment", {}).get(key)
        right = other.get("environment", {}).get(key)
        if left != right:
            problems.append(f"environment {key}: {left} != {right}")
    lines = [
        "base:  " + str(base.get("environment", {}).get("head")),
        "other: " + str(other.get("environment", {}).get("head")),
    ]
    if kind == "compile":
        for name, report in (("base", base), ("other", other)):
            if not report.get("outputs_stable"):
                problems.append(f"{name}: outputs changed between passes")
        left, right = base["median_pass_seconds"], other["median_pass_seconds"]
        ratio = f" (x{right / left:.3f})" if left else ""
        passes = f"{base['repeats']} repeats, {base['warmup']} warmup"
        lines.append(f"median pass ({passes}): {left} s -> {right} s{ratio}")
        differ = sorted(
            key
            for key in base.get("outputs", {})
            if base["outputs"][key] != other.get("outputs", {}).get(key)
        )
        total = len(base["units"])
        lines.append(f"units whose output differs: {len(differ)} of {total}")
        lines += [f"  {key}" for key in differ[:10]]
    else:
        others = {r["node"]: r for r in other.get("results", ())}
        for mine in base.get("results", ()):
            theirs = others.get(mine["node"], {})
            before = f"{mine.get('outcome')} {mine.get('window_seconds')} s"
            after = f"{theirs.get('outcome')} {theirs.get('window_seconds')} s"
            calls = f"{mine.get('top_level_calls')} -> {theirs.get('top_level_calls')}"
            lines.append(f"{mine['node']}: {before} -> {after}; calls {calls}")
    return lines, problems


# ---- the command ----


def _seed_range(text: str) -> range:
    start, _, stop = text.partition(":")
    return range(int(start), int(stop))


def _use_product(product_root: Path) -> None:
    """Import ``pietto`` from ``product_root``'s sources, or refuse."""
    if "pietto" in sys.modules:
        raise SystemExit("pietto is already imported; start a fresh process")
    source = (product_root / "src").resolve()
    sys.path.insert(0, str(source))
    import pietto

    if not Path(pietto.__file__).resolve().is_relative_to(source):
        raise SystemExit(f"pietto came from {pietto.__file__}, not {source}")


def main(argv: list[str] | None = None) -> int:
    # The docstring's first paragraph; `python -OO` strips docstrings to None.
    summary = __doc__.split("\n\n")[0] if __doc__ is not None else None
    parser = argparse.ArgumentParser(description=summary)
    commands = parser.add_subparsers(dest="command", required=True)
    bench = commands.add_parser("compile", help="the compile-time benchmark")
    bench.add_argument("--directory", type=Path, required=True)
    bench.add_argument("--seeds", type=_seed_range, default=SEEDS, help="START:STOP")
    bench.add_argument("--warmup", type=int, default=WARMUP)
    bench.add_argument("--repeats", type=int, default=REPEATS)
    bench.add_argument("--product-root", type=Path, default=ROOT)
    prof = commands.add_parser("profile", help="the ten-node profile")
    prof.add_argument("--directory", type=Path, required=True)
    prof.add_argument("--checkout", type=Path, default=ROOT)
    prof.add_argument("--nodes-file", type=Path, help="one node id per line")
    node = commands.add_parser("profile-node", help="internal: one node, one process")
    node.add_argument("--node", required=True)
    node.add_argument("--checkout", type=Path, required=True)
    node.add_argument("--stats", type=Path, required=True)
    node.add_argument("--out", type=Path, required=True)
    pair = commands.add_parser("compare", help="two reports of the same measurement")
    pair.add_argument("base", type=Path)
    pair.add_argument("other", type=Path)
    args = parser.parse_args(argv)

    if args.command == "compile":
        product_root = args.product_root.resolve()
        _use_product(product_root)
        args.directory.mkdir()
        report = benchmark(
            args.directory / "projects", args.seeds, args.warmup, args.repeats
        )
        import pietto

        report["product"] = str(Path(pietto.__file__).resolve().parent)
        report["harness"] = str(Path(__file__).resolve())
        report["environment"] = environment(product_root)
        (args.directory / "report.json").write_text(
            json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            f"median pass {report['median_pass_seconds']} s over {args.repeats}"
            f" repeats, {len(report['units'])} units, outputs stable:"
            f" {report['outputs_stable']}, statuses {report['statuses']}"
        )
        return 0 if report["outputs_stable"] else 1
    if args.command == "profile":
        nodes = HISTORICAL_TEN
        if args.nodes_file is not None:
            text = args.nodes_file.read_text(encoding="utf-8")
            nodes = tuple(line.strip() for line in text.splitlines() if line.strip())
        report = profile(args.directory, nodes, args.checkout.resolve())
        for result in report["results"]:
            print(
                f"{result.get('outcome')}: {result['node']}"
                f" {result.get('window_seconds')} s,"
                f" child dominated {result.get('child_dominated')}"
            )
        complete = all(r.get("outcome") == "passed" for r in report["results"])
        return 0 if complete else 1
    if args.command == "profile-node":
        # The checkout's tests, not this file's directory, must supply helpers.
        sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
        result = profile_node(args.node, args.checkout.resolve(), args.stats)
        args.out.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        return 0
    base, other = (
        json.loads(p.read_text(encoding="utf-8")) for p in (args.base, args.other)
    )
    lines, problems = compare(base, other)
    print("\n".join(lines + [f"NOT COMPARABLE: {p}" for p in problems]))
    return 2 if problems else 0


if __name__ == "__main__":  # explicit entry point; pytest never runs it
    raise SystemExit(main())
