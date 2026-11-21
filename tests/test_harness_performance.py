"""The entry points of the compile-time benchmark and the ten-node profile.

tests/_pietto_harness_performance.py measures; these tests never read a
timing as a pass or a failure. They check that the benchmark compiles
exactly the generator's registered corpus through ``compile_sql`` and keeps
each output as a direct call gives it, that warmup passes stay out of the
median and a changed output is reported, that a report is void by the
validity rule, that ``compare`` refuses reports that are not the same
measurement, are void or ran without a hash seed, that the profile reads its
nodes from a file and stops a node at its timeout, that a top-level call is
one from the checkout's tests, and that one profiled node runs alone in a
fresh process and measures only its own work. They open no database and use
no network.
"""

from __future__ import annotations

import copy
import cProfile
import hashlib
import importlib.util
import json
from pathlib import Path
import pstats
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, cast

import _pietto_harness_generated_forms as forms
import _pietto_harness_performance as perf
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WITNESS = (
    "tests/test_harness_performance.py::"
    "test_profile_witness_parses_two_generated_modules"
)


def test_benchmark_corpus_is_the_generators_registered_campaign() -> None:
    assert perf.SEEDS == forms.SEEDS
    assert perf.corpus_digest(perf.SEEDS) == forms.CORPUS_SHA256
    plan = perf.units(perf.SEEDS)
    assert len(plan) == len(forms.SEEDS) * 3 == len(set(plan))
    assert {(profile, target) for _, profile, target in plan} == {
        ("broad", "postgres"),
        ("narrow", "postgres"),
        ("narrow", "mysql"),
    }


def test_benchmark_measures_the_corpus_and_preserves_each_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pietto import compiler

    entered: list[tuple[str, str]] = []
    public = compiler.compile_sql

    def counted(project, **arguments):
        entered.append((Path(project).name, arguments["dialect"]))
        return public(project, **arguments)

    monkeypatch.setattr(compiler, "compile_sql", counted)
    root = tmp_path / "projects"
    report = perf.benchmark(root, range(1), warmup=0, repeats=1)
    monkeypatch.undo()

    assert report["units"] == [
        "broad:0:postgres",
        "narrow:0:postgres",
        "narrow:0:mysql",
    ]
    assert entered == [
        ("broad-0-postgres", "postgres"),
        ("narrow-0-postgres", "postgres"),
        ("narrow-0-mysql", "mysql"),
    ]
    assert report["corpus_sha256"] == perf.corpus_digest(range(1))
    assert report["outputs_stable"] and report["output_changes"] == []
    for unit in perf.units(range(1)):
        seed, profile, target = unit
        project = root / f"{profile}-{seed}-{target}"
        files = forms.project_files(forms.generate(seed, profile), target)
        assert sorted(p.name for p in project.iterdir()) == sorted(files)
        assert all((project / n).read_bytes() == t.encode() for n, t in files.items())
        direct = perf.compile_unit(project, target)
        expected = [direct.status, perf.output_digest(direct)]
        assert report["outputs"][perf.label(unit)] == expected
    # Shapes only: no timing is judged.
    assert len(report["pass_ns"]) == 1 and len(report["pass_seconds"]) == 1
    assert set(report["unit_median_seconds"]) == set(report["units"])
    assert (report["unit"], report["clock"], report["entry"]) == (
        "seconds",
        "time.perf_counter_ns",
        "pietto.compiler.compile_sql",
    )


def test_benchmark_leaves_warmup_out_of_the_median_and_reports_changed_output(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []

    def compile(project: Path, target: str) -> SimpleNamespace:
        calls.append((project.name, target))
        document = b"other" if len(calls) == 12 else b"same"
        return SimpleNamespace(status="VERIFIED", document=document)

    # Pass p (warmup included) spends (p + 1) * 1000 ns on each of 3 units.
    stamps = []
    now = 0
    for index in range(4):
        for _ in range(3):
            stamps += [now, now + (index + 1) * 1000]
            now += 10_000
    loads = iter([9.0, 1.0, 1.5, 1.5, 2.0, 2.0, 3.5])
    report = perf.benchmark(
        tmp_path / "p",
        range(1),
        warmup=1,
        repeats=3,
        compile=compile,
        clock=iter(stamps).__next__,
        load=loads.__next__,
    )
    plan = [
        ("broad-0-postgres", "postgres"),
        ("narrow-0-postgres", "postgres"),
        ("narrow-0-mysql", "mysql"),
    ]
    assert calls == plan * 4
    assert report["pass_ns"] == [6000, 9000, 12000]
    assert report["median_pass_seconds"] == perf._seconds(9000)
    assert report["unit_median_seconds"]["narrow:0:mysql"] == perf._seconds(3000)
    assert not report["outputs_stable"]
    assert len(report["output_changes"]) == 1
    assert report["output_changes"][0].startswith("pass 3: narrow:0:mysql")
    # The warmup pass's load is not recorded; each timed pass's start and end.
    assert report["pass_load"] == [[1.0, 1.5], [1.5, 2.0], [2.0, 3.5]]
    assert report["void"] == []
    assert report["started"] <= report["ended"]
    # A non-integer repeat count is refused at run time; the cast passes it
    # past the signature on purpose.
    fractional = cast(Any, 1.5)
    for warmup, repeats in ((-1, 1), (0, 0), (0, fractional)):
        with pytest.raises(ValueError):
            perf.benchmark(tmp_path / "x", range(1), warmup, repeats, compile=compile)


def _compile_report() -> dict:
    return {
        "format": perf.FORMAT,
        "kind": "compile",
        "workload": perf.WORKLOAD,
        "entry": perf.ENTRY,
        "seeds": [0, 40],
        "units": ["broad:0:postgres"],
        "corpus_sha256": "c",
        "workload_sha256": "w",
        "warmup": 1,
        "repeats": 5,
        "unit": "seconds",
        "clock": perf.CLOCK,
        "median_pass_seconds": 2.0,
        "pass_ns": [2_000_000_000, 2_100_000_000, 3_900_000_000],
        "pass_load": [[1.0, 1.2], [1.2, 2.5], [2.5, 3.99]],
        "outputs_stable": True,
        "outputs": {"broad:0:postgres": ["VERIFIED", "d"]},
        "environment": {
            "python": "3.13.13",
            "implementation": "CPython",
            "pythonhashseed": "0",
            "head": "base",
        },
    }


def test_a_benchmark_report_is_void_by_the_validity_rule() -> None:
    """P17's rule: a pass that ends at a load of 4 or more, or that takes
    more than twice the fastest, voids the report, and so does a report
    without a load or without a pass."""
    assert perf.void_reasons(_compile_report()) == []
    voids = {
        "pass_load": [[1.0, 1.2], [1.2, 4.0], [2.5, 3.0]],
        "pass_ns": [2_000_000_000, 2_100_000_000, 4_000_000_001],
    }
    for key, value in voids.items():
        report = _compile_report()
        report[key] = value
        assert perf.void_reasons(report), key
    for loads in (None, [[None, None]] * 3, [[1.0, 1.0]] * 2):
        report = _compile_report()
        report["pass_load"] = loads
        assert perf.void_reasons(report) == ["no load reported"], loads
    for passes in (None, []):
        report = _compile_report()
        report["pass_ns"], report["pass_load"] = passes, passes
        assert perf.void_reasons(report) == ["no pass reported"], passes


def test_compare_reads_only_reports_of_the_same_measurement() -> None:
    base = _compile_report()
    slower = copy.deepcopy(base)
    slower["median_pass_seconds"] = 300.0  # a timing is never a problem
    slower["outputs"]["broad:0:postgres"] = ["VERIFIED", "e"]
    lines, problems = perf.compare(base, slower)
    assert problems == []
    assert any("2.0 s -> 300.0 s (x150.000)" in line for line in lines)
    assert "units whose output differs: 1 of 1" in lines
    changes = {
        ("environment", "python"): "3.12.13",
        ("environment", "pythonhashseed"): None,
        ("", "warmup"): 0,
        ("", "repeats"): 7,
        ("", "corpus_sha256"): "other",
        ("", "workload_sha256"): "other",
        ("", "outputs_stable"): False,
        ("", "kind"): "profile",
        ("", "pass_load"): [[1.0, 4.5]] * 3,
    }
    for (part, key), value in changes.items():
        other = copy.deepcopy(base)
        (other[part] if part else other)[key] = value
        assert perf.compare(base, other)[1], key
    # A void or unseeded report on either side: no ratio is printed. A seed
    # unset, empty or `random` is drawn afresh for each run.
    void = copy.deepcopy(slower)
    void["pass_ns"] = [1, 3, 9]
    for left, right in ((base, void), (void, base)):
        lines, problems = perf.compare(left, right)
        assert problems and not any("(x" in line for line in lines)
    for seed in (None, "", "random"):
        unseeded = copy.deepcopy(base)
        unseeded["environment"]["pythonhashseed"] = seed
        lines, problems = perf.compare(unseeded, copy.deepcopy(unseeded))
        assert problems == [
            "base: run without a fixed PYTHONHASHSEED",
            "other: run without a fixed PYTHONHASHSEED",
        ], seed
        assert not any("(x" in line for line in lines)


def test_compare_of_two_profiles_shows_verifier_runs_and_missing_bodies() -> None:
    """Each node's verifier runs stand beside its calls, and a side whose
    checkout lacks the verifier bodies is marked so."""
    result = {
        "node": "tests/test_x.py::test_y",
        "outcome": "passed",
        "window_seconds": 1.0,
        "top_level_calls": 2,
        "verifier_runs": {"verify_description": 3, "verify_scope": 1},
    }
    base = {
        "format": perf.FORMAT,
        "kind": "profile",
        "nodes": [result["node"]],
        "environment": {"python": "3.13.13", "pythonhashseed": "0"},
        "results": [result],
    }
    other = copy.deepcopy(base)
    other["results"][0]["verifier_runs"] = {}
    other["results"][0]["verifier_bodies_error"] = "ModuleNotFoundError()"
    lines, problems = perf.compare(base, other)
    assert problems == []
    assert lines[-1].endswith("calls 2 -> 2; verifier runs 4 -> bodies missing")


def test_profile_reads_its_nodes_from_a_file(tmp_path: Path) -> None:
    """No default list: the nodes are the file's lines in order, blank
    lines dropped, and the report records the file's path and digest."""
    path = tmp_path / "nodes.txt"
    path.write_text("\n  b::two  \n\na::one\n", encoding="utf-8")
    nodes, source = perf.read_nodes(path)
    assert nodes == ("b::two", "a::one")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert source == {"path": str(path), "sha256": digest}
    path.write_text("\n \n", encoding="utf-8")
    with pytest.raises(ValueError, match="names no node"):
        perf.read_nodes(path)
    with pytest.raises(SystemExit):
        perf.main(["profile", "--directory", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()


def test_profile_stops_a_node_at_its_timeout(tmp_path: Path) -> None:
    report = perf.profile(
        tmp_path / "out",
        (WITNESS,),
        {"path": "nodes", "sha256": "-"},
        ROOT,
        timeout=0.01,
    )
    (result,) = report["results"]
    assert result["outcome"] == "timeout" and result["node"] == WITNESS
    assert report["timeout_seconds"] == 0.01 and "load_end" in report


def test_the_benchmark_command_refuses_no_warmup(tmp_path: Path) -> None:
    """A timed run warms up first, so it never times the lazy compiler
    import; ``benchmark()`` itself still accepts 0 for these tests."""
    with pytest.raises(SystemExit) as raised:
        perf.main(["compile", "--directory", str(tmp_path / "out"), "--warmup", "0"])
    assert raised.value.code == 2 and not (tmp_path / "out").exists()


def _real_caller(seed: int) -> None:
    """A frame of a file outside the product, entered inside the window."""
    forms.generate(seed, "narrow")


def test_summary_counts_entries_verifier_runs_and_self_time(tmp_path: Path) -> None:
    # A module outside both the product and the tests, as a library that
    # calls back into the product.
    third = tmp_path / "third_party.py"
    third.write_text(
        "def call(function, *arguments):\n    return function(*arguments)\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("third_party", third)
    assert spec is not None and spec.loader is not None
    library = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(library)
    profiler = cProfile.Profile()
    profiler.enable()
    # This frame was running before the window opened, so cProfile records
    # no caller for this call; `_real_caller` is entered inside the window,
    # so its two calls have a recorded caller of a test file.
    forms.generate(0, "broad")
    _real_caller(1)
    _real_caller(2)
    library.call(forms.generate, 3, "narrow")
    profiler.disable()
    stats = pstats.Stats(profiler)
    code = forms.generate.__code__
    (callers,) = [
        values[4]
        for key, values in stats.stats.items()  # type: ignore[attr-defined]
        if key[0] == code.co_filename and key[1] == code.co_firstlineno
    ]
    real = [key for key in callers if key[2] == "_real_caller"]
    assert len(real) == 1 and Path(real[0][0]).resolve() == Path(__file__).resolve()
    assert callers[real[0]][0] == 2
    bodies = {
        "generate": (code.co_filename, code.co_firstlineno),
        "absent": (str(HERE / "nowhere.py"), 1),
    }
    summary = perf.summarize(stats, Path(forms.__file__), bodies)
    # Only the two calls from a test file are top-level: not the call with
    # no recorded caller, not the library's callback, and not the
    # generator's calls of its own functions.
    assert summary["top_level_calls"] == 2
    assert summary["verifier_runs"] == {"generate": 4, "absent": 0}
    assert summary["verifier_runs_per_top_level_call"] == {
        "generate": 2.0,
        "absent": 0.0,
    }
    assert summary["most_called"]
    assert all(
        entry["function"].startswith("tests/_pietto_harness_generated_forms.py:")
        for entry in summary["most_called"]
    )
    calls = [entry["calls"] for entry in summary["most_called"]]
    assert calls == sorted(calls, reverse=True)
    assert len(summary["top_self_time"]) <= perf.TOP
    assert (summary["child_process_starts"], summary["child_wait_seconds"]) == (0, 0)


def test_profile_witness_parses_two_generated_modules() -> None:
    """The node that the profile entry's own test measures: two parses."""
    from pietto.parser_api import parse_source

    for seed in (0, 1):
        text = forms.module_text(forms.generate(seed, "narrow"), "postgres")
        assert parse_source(text).ast is not None


def test_a_profiled_node_runs_alone_and_measures_its_own_work(tmp_path: Path) -> None:
    out, stats = tmp_path / "node.json", tmp_path / "node.prof"
    run = subprocess.run(
        [
            sys.executable,
            str(HERE / "_pietto_harness_performance.py"),
            "profile-node",
            "--node",
            WITNESS,
            "--checkout",
            str(ROOT),
            "--stats",
            str(stats),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        env=perf._child_environment(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["collected"] == [WITNESS] and result["outcome"] == "passed"
    assert sorted(result["phases"]) == ["call", "setup", "teardown"]
    assert Path(result["product"]) == (ROOT / "src" / "pietto").resolve()
    assert "verifier_bodies_error" not in result and result["verifier_runs"]
    assert set(result["verifier_runs"].values()) == {0}  # a parse verifies nothing
    assert result["top_level_calls"] == 2  # ANTLR's callbacks are not counted
    entries = pstats.Stats(str(stats)).stats  # type: ignore[attr-defined]
    parses = [
        values[1]
        for (filename, _, name), values in entries.items()
        if name == "parse_source" and Path(filename).name == "parser_api.py"
    ]
    assert parses == [2]
    assert result["child_process_starts"] == 0 and result["child_dominated"] is False
