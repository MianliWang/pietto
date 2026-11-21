"""The compile-time benchmark and the ten-node profile (PL.50 Q9, PL.58).

Two workloads, kept apart because they measure different things:

- **The compile-time benchmark** (``compile``) times the public
  ``pietto.compiler.compile_sql`` over the registered corpus of
  tests/_pietto_harness_generated_forms.py (``SEEDS`` of both profiles),
  each case compiled as an explicit-module project for PostgreSQL, and also
  for MySQL in the narrow profile, the project routes of
  tests/test_harness_generated_forms.py (120 compilations). It is a synthetic
  compiler workload of generated programs; it is not the ten-node profile and
  has no ten nodes. The project files are written once, as UTF-8 bytes with
  LF line ends, before any timing. ``warmup`` untimed passes run first, then
  ``repeats`` timed passes; each pass compiles every unit once in a fixed
  order after ``gc.collect()``. The report gives each pass's total, their
  median and each unit's median, in seconds from ``time.perf_counter_ns``,
  the status and SHA-256 of each unit's output, the start and end of the
  run and the one-minute load at the start and at the end of each pass.
  Every pass must give the same outputs; a change is reported, never
  hidden. A report is void when no load is reported, when a pass ends at a
  load of 4 or more, or when a pass takes more than twice the fastest.
  ``--product-root`` runs another checkout's ``src/pietto`` over the same
  corpus, which this file's own generator writes, so a base and a newer
  checkout compile the same bytes.
- **The ten-node profile** (``profile``) is the bounded profile of step 4 of
  docs/development.md ("Phase-end acquisition consolidation"): nodes of a
  natural CI's health, each run alone, in a fresh process, under cProfile,
  within a timeout. The nodes come from a file, one node id per line, whose
  path and SHA-256 the report records; there is no default list. The
  profile window is each node's setup, call and teardown, not collection.
  Each node reports its phase seconds under the profiler, the runs of the
  complete verifier bodies of tests/_pietto_project_verification_bodies.py
  beside their count per top-level call, the product functions called most
  often, the top self time, and the child processes it started, so that a
  child-dominated node is recorded as such. A top-level call is a call of a
  product function from a frame of a file under the profiled checkout's
  ``tests`` directory; a callback from the standard library or a
  third-party package, such as ANTLR's runtime or a ``json`` hook, is not
  one.

Timings are observations, never assertions: no command here passes or fails
on a number. ``compare`` refuses two reports that are not the same
measurement (format, workload, entry, seeds, units, corpus, workload digest,
warmup, repeats, unit, clock, Python, implementation and hash seed; a
profile's format and nodes), a void report and one run without a fixed
``PYTHONHASHSEED``, and then prints
no ratio; otherwise it prints the medians side by side. Only valid reports of
runs that alternate the base and the newer checkout in one session support
a before-and-after claim.

Importing this module opens nothing and imports no ``pietto``; pytest checks
the entry points (tests/test_harness_performance.py). Run it explicitly, from
the repository root::

    python tests/_pietto_harness_performance.py compile --directory OUT
    python tests/_pietto_harness_performance.py profile --directory OUT --nodes-file NODES
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
SEEDS = forms.SEEDS  # the generator's registered campaign
WARMUP = 1
REPEATS = 5
UNIT = "seconds"
CLOCK = "time.perf_counter_ns"
# A report is void when a pass ends at this one-minute load or above (P17's
# validity rule), or when a pass takes more than SPREAD times the fastest.
QUIET_LOAD = 4.0
SPREAD = 2

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


def _load() -> list[float] | None:
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return None  # not reported on this platform


def _load_one() -> float | None:
    """The one-minute load, or None where the platform reports none."""
    load = _load()
    return None if load is None else load[0]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    load: Callable[[], float | None] = _load_one,
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
    loads: list[list[float | None]] = []
    started = _now()
    for index in range(warmup + repeats):
        gc.collect()
        before = load()
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
            loads.append([before, load()])
    totals = [sum(times) for times in passes]
    report = {
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
        "started": started,
        "ended": _now(),
        "pass_load": loads,
    }
    report["void"] = void_reasons(report)
    return report


def void_reasons(report: dict[str, Any]) -> list[str]:
    """Why a benchmark report is void, from its own figures: no pass or no
    load reported, a pass that ended at a load of ``QUIET_LOAD`` or more, or
    a pass longer than ``SPREAD`` times the fastest. Empty for a valid one."""
    totals = report.get("pass_ns") or []
    loads = report.get("pass_load") or []
    reasons = [] if totals else ["no pass reported"]
    if len(loads) != len(totals) or any(
        type(end) not in (int, float) for _, end in loads
    ):
        reasons.append("no load reported")
    else:
        high = [i for i, (_, end) in enumerate(loads) if end >= QUIET_LOAD]
        if high:
            reasons.append(f"passes {high} ended at a load of {QUIET_LOAD} or more")
    if totals and max(totals) > SPREAD * min(totals):
        reasons.append(f"a pass took more than {SPREAD} times the fastest")
    return reasons


# ---- the ten-node profile ----

TOP = 15  # rows of the most-called and self-time lists
TIMEOUT = 1800.0  # seconds one profiled node may run
_CHILD_STARTS = {("subprocess.py", "_execute_child")}
_CHILD_WAIT = {("subprocess.py", "wait")}
_CHILD_COMMUNICATE = {("subprocess.py", "communicate")}


def verifier_bodies() -> dict[str, tuple[str, int]]:
    """The complete verifier bodies that the verification budget counts
    (tests/_pietto_project_verification_bodies.py), by code location."""
    import _pietto_project_verification_bodies as verification

    return {
        name: (body.__code__.co_filename, body.__code__.co_firstlineno)
        for name, body in verification.BODIES.items()
    }


def read_nodes(path: Path) -> tuple[tuple[str, ...], dict[str, str]]:
    """The node ids of a nodes file, one per line in its order, blank lines
    dropped, and the file's path and SHA-256; an empty list is refused."""
    data = path.read_bytes()
    nodes = tuple(
        line.strip() for line in data.decode("utf-8").splitlines() if line.strip()
    )
    if not nodes:
        raise ValueError(f"{path} names no node")
    return nodes, {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


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
    cumulative)``. A top-level call is a call of a product function whose
    recorded caller is a frame of a file under ``root``'s ``tests``
    directory and outside the product: a test, a fixture or a test helper.
    A call from a standard-library or third-party frame, such as ANTLR's
    runtime or a ``json`` hook, from a built-in or from a frame without a
    file is not one, and neither is a call whose caller cProfile did not
    record."""
    entries: dict[tuple[str, int, str], Any] = stats.stats  # type: ignore[attr-defined]
    inside = _Inside(product)
    tests = _Inside(root / "tests")
    top_level = 0
    for (filename, _, _), (_, _, _, _, callers) in entries.items():
        if inside(filename):
            top_level += sum(
                counts[0]
                for caller, counts in callers.items()
                if tests(caller[0]) and not inside(caller[0])
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
    nodes: Sequence[str],
    nodes_source: dict[str, str],
    checkout: Path = ROOT,
    python: str = sys.executable,
    timeout: float = TIMEOUT,
) -> dict[str, Any]:
    """Run each node alone in a fresh process under cProfile; a node that
    outlives ``timeout`` seconds is stopped and recorded as ``timeout``."""
    directory.mkdir()
    report: dict[str, Any] = {
        "format": FORMAT,
        "kind": "profile",
        "nodes": list(nodes),
        "nodes_source": nodes_source,
        "timeout_seconds": timeout,
        "environment": environment(checkout),
        "started": _now(),
        "results": [],
    }
    for index, node in enumerate(nodes):
        out, stats = directory / f"{index:02d}.json", directory / f"{index:02d}.prof"
        load = _load()
        started = time.perf_counter_ns()
        result: dict[str, Any]
        try:
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
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as expired:
            output = [expired.stdout or "", expired.stderr or ""]
            text = "".join(o.decode() if isinstance(o, bytes) else o for o in output)
            (directory / f"{index:02d}.log").write_text(text, encoding="utf-8")
            result = {"node": node, "outcome": "timeout"}
        else:
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
    report["ended"], report["load_end"] = _now(), _load()
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
# CPython draws a seed when PYTHONHASHSEED is unset, empty or `random`.
_UNSEEDED = (None, "", "random")


def compare(base: dict[str, Any], other: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(lines, problems): the two reports side by side, and every reason they
    are not the same measurement or not valid: a void benchmark report on
    either side, or one run without a fixed ``PYTHONHASHSEED``. A ratio is
    printed only when there is no problem; a timing never makes one."""
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
    for name, report in (("base", base), ("other", other)):
        if report.get("environment", {}).get("pythonhashseed") in _UNSEEDED:
            problems.append(f"{name}: run without a fixed PYTHONHASHSEED")
    lines = [
        "base:  " + str(base.get("environment", {}).get("head")),
        "other: " + str(other.get("environment", {}).get("head")),
    ]
    if kind == "compile":
        for name, report in (("base", base), ("other", other)):
            if not report.get("outputs_stable"):
                problems.append(f"{name}: outputs changed between passes")
            problems += [f"{name}: void: {why}" for why in void_reasons(report)]
        left, right = base["median_pass_seconds"], other["median_pass_seconds"]
        ratio = f" (x{right / left:.3f})" if left and not problems else ""
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
            runs = " -> ".join(_verifier_runs(r) for r in (mine, theirs))
            lines.append(
                f"{mine['node']}: {before} -> {after}; calls {calls};"
                f" verifier runs {runs}"
            )
    return lines, problems


def _verifier_runs(result: dict[str, Any]) -> str:
    if "verifier_bodies_error" in result or "verifier_runs" not in result:
        return "bodies missing"
    return str(sum(result["verifier_runs"].values()))


# ---- the command ----


def _positive(text: str) -> int:
    """A positive count: a timed run warms the lazy imports up first."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


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
    bench.add_argument("--warmup", type=_positive, default=WARMUP)
    bench.add_argument("--repeats", type=int, default=REPEATS)
    bench.add_argument("--product-root", type=Path, default=ROOT)
    prof = commands.add_parser("profile", help="the ten-node profile")
    prof.add_argument("--directory", type=Path, required=True)
    prof.add_argument("--checkout", type=Path, default=ROOT)
    prof.add_argument(
        "--nodes-file", type=Path, required=True, help="one node id per line"
    )
    prof.add_argument("--timeout", type=float, default=TIMEOUT, help="per node, s")
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
            f" {report['outputs_stable']}, statuses {report['statuses']},"
            f" void {report['void'] or 'no'}"
        )
        return 0 if report["outputs_stable"] else 1
    if args.command == "profile":
        try:
            nodes, source = read_nodes(args.nodes_file)
        except ValueError as error:
            raise SystemExit(str(error)) from None
        report = profile(
            args.directory, nodes, source, args.checkout.resolve(), timeout=args.timeout
        )
        for result in report["results"]:
            print(
                f"{result.get('outcome')}: {result['node']}"
                f" {result.get('window_seconds')} s,"
                f" child dominated {result.get('child_dominated')}"
            )
        complete = all(r.get("outcome") == "passed" for r in report["results"])
        return 0 if complete else 1
    if args.command == "profile-node":
        # The checkout's tests, not this file's directory, must supply helpers,
        # also those that this module has already imported.
        sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
        for name in [m for m in sys.modules if m.startswith("_pietto_")]:
            del sys.modules[name]
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
