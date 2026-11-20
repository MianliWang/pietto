"""The entry points of the compile-time benchmark and the ten-node profile.

tests/_pietto_harness_performance.py measures; these tests never read a
timing as a pass or a failure. They check that the benchmark compiles
exactly the generator's registered corpus through ``compile_sql`` and keeps
each output as a direct call gives it, that warmup passes stay out of the
median and a changed output is reported, that ``compare`` refuses reports
that are not the same measurement, that the registered ten nodes are the
Phase78 audit's table, and that one profiled node runs alone in a fresh
process and measures only its own work. They open no database and use no
network.
"""

from __future__ import annotations

import ast
import copy
import cProfile
import json
from pathlib import Path
import pstats
import re
import subprocess
import sys
from types import SimpleNamespace

import _pietto_harness_generated_forms as forms
import _pietto_harness_performance as perf
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WITNESS = (
    "tests/test_harness_performance.py::"
    "test_profile_witness_parses_two_generated_modules"
)


def _registered_campaign() -> tuple[range, str]:
    """SEEDS and CORPUS_SHA256 of the generator's test owner, read from its
    text so that this owner imports no other test module."""
    path = HERE / "test_harness_generated_forms.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    seeds = values["SEEDS"]
    assert isinstance(seeds, ast.Call) and getattr(seeds.func, "id", "") == "range"
    bounds = [ast.literal_eval(argument) for argument in seeds.args]
    return range(*bounds), ast.literal_eval(values["CORPUS_SHA256"])


def test_benchmark_corpus_is_the_generators_registered_campaign() -> None:
    seeds, digest = _registered_campaign()
    assert perf.SEEDS == seeds
    assert perf.corpus_digest(perf.SEEDS) == digest
    plan = perf.units(perf.SEEDS)
    assert len(plan) == len(seeds) * 3 == len(set(plan))
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
    report = perf.benchmark(
        tmp_path / "p",
        range(1),
        warmup=1,
        repeats=3,
        compile=compile,
        clock=iter(stamps).__next__,
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
    for warmup, repeats in ((-1, 1), (0, 0), (0, 1.5)):
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
        "outputs_stable": True,
        "outputs": {"broad:0:postgres": ["VERIFIED", "d"]},
        "environment": {
            "python": "3.13.13",
            "implementation": "CPython",
            "pythonhashseed": "0",
            "head": "base",
        },
    }


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
    }
    for (part, key), value in changes.items():
        other = copy.deepcopy(base)
        (other[part] if part else other)[key] = value
        assert perf.compare(base, other)[1], key


def _audit_table() -> tuple[str, tuple[str, ...]]:
    """The audit's ten-slowest paragraph and the node ids of its table."""
    text = (ROOT / "docs/phases/phase-78/completion-audit.md").read_text(
        encoding="utf-8"
    )
    start = text.index("**Ten-slowest profile.**")
    section = text[start : text.index("None is a Phase78 node.", start)]
    nodes: list[str] = []
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        base = ""
        for span in re.findall(r"`([^`]+)`", line.split(" | ")[0]):
            if "::" in span:
                base = span.partition("[")[0]
                nodes.append("tests/" + span)
            elif span.startswith("[") and base:
                nodes.append("tests/" + base + span)
    return section, tuple(nodes)


def test_the_registered_ten_are_the_phase78_audit_table() -> None:
    section, nodes = _audit_table()
    assert nodes == perf.HISTORICAL_TEN and len(nodes) == 10
    assert f"From the health of `{perf.HISTORICAL_CI}`, Python 3.13" in section
    audit = (ROOT / perf.HISTORICAL_SOURCE.partition("#")[0]).read_text(
        encoding="utf-8"
    )
    assert "\n## B2 acquisition review\n" in audit


def _real_caller(seed: int) -> None:
    """A frame of a file outside the product, entered inside the window."""
    forms.generate(seed, "narrow")


def test_summary_counts_entries_verifier_runs_and_self_time() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    # This frame was running before the window opened, so cProfile records
    # no caller for this call; `_real_caller` is entered inside the window,
    # so its two calls have a recorded caller of a real file.
    forms.generate(0, "broad")
    _real_caller(1)
    _real_caller(2)
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
    # One unattributed call and two through the real caller; the generator's
    # calls of its own functions are not top-level.
    assert summary["top_level_calls"] == 3
    assert summary["verifier_runs"] == {"generate": 3, "absent": 0}
    assert summary["verifier_runs_per_top_level_call"] == {
        "generate": 1.0,
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
    assert result["top_level_calls"] >= 2
    entries = pstats.Stats(str(stats)).stats  # type: ignore[attr-defined]
    parses = [
        values[1]
        for (filename, _, name), values in entries.items()
        if name == "parse_source" and Path(filename).name == "parser_api.py"
    ]
    assert parses == [2]
    assert result["child_process_starts"] == 0 and result["child_dominated"] is False
