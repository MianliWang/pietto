"""pietto.interop without PyArrow: lazy import, signatures, the first
TypeError and the installed consumer's report checker."""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
from typing import Any

import pytest

from _pietto_ci_workflow import job
import _pietto_results_interop as consumer
import pietto.interop as interop

adapters: Any = interop

ROOT = Path(__file__).resolve().parents[1]
HEAVY = ("pyarrow", "pandas", "polars", "numpy", "scipy", "matplotlib")
SIGNATURES = {
    "plot_line": "(batch: 'ResultBatch', x: 'int', y: 'int', *,"
    " ax: 'matplotlib.axes.Axes') -> 'matplotlib.lines.Line2D'",
    "plot_scatter": "(batch: 'ResultBatch', x: 'int', y: 'int', *,"
    " ax: 'matplotlib.axes.Axes') -> 'matplotlib.collections.PathCollection'",
    "to_numpy": "(batch: 'ResultBatch', column: 'int') -> 'numpy.ndarray'",
    "to_pandas": "(batch: 'ResultBatch') -> 'pandas.DataFrame'",
    "to_polars": "(batch: 'ResultBatch') -> 'polars.DataFrame'",
    "to_scipy_csr": "(batch: 'ResultBatch', row: 'int', column: 'int',"
    " value: 'int', shape: 'tuple[int, int]') -> 'scipy.sparse.csr_array'",
}


def test_a_fresh_import_loads_no_arrow_target_or_execution_owner() -> None:
    probe = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(ROOT / 'src')!r})\n"
        "import pietto.interop\n"
        "print(json.dumps(sorted(sys.modules)))\n"
    )
    loaded = json.loads(
        subprocess.run(
            [sys.executable, "-I", "-B", "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            # Python's subprocess documentation asks for SYSTEMROOT on Windows.
            env={k: os.environ[k] for k in ("PATH", "SYSTEMROOT") if k in os.environ},
        ).stdout
    )
    assert [m for m in loaded if m.partition(".")[0] in HEAVY] == []
    assert [m for m in loaded if m.startswith(("pietto.execution", "pietto._"))] == []
    assert [m for m in loaded if m.startswith("pietto.interop")] == [
        "pietto.interop",
        "pietto.interop._common",
    ]


def test_interop_imports_only_the_public_batch_and_nothing_upstream_imports_it() -> (
    None
):
    def imported(path: Path) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.add(node.module)
        return names

    package = ROOT / "src/pietto/interop"
    inside = set().union(*(imported(path) for path in package.glob("*.py")))
    assert {n for n in inside if n.startswith("pietto")} == {
        "pietto.execution",
        "pietto.interop",
    }
    outside = [
        path.relative_to(ROOT)
        for path in (ROOT / "src/pietto").rglob("*.py")
        if package not in path.parents
        and any(n.startswith("pietto.interop") for n in imported(path))
    ]
    assert outside == []


def test_the_six_adapters_keep_their_names_and_signatures() -> None:
    assert interop.__all__ == sorted(SIGNATURES)
    assert {
        name: str(inspect.signature(getattr(interop, name))) for name in SIGNATURES
    } == SIGNATURES


@pytest.mark.parametrize(
    ("call", "message"),
    (
        (lambda: adapters.to_pandas(None), "to_pandas: batch must be a"),
        (lambda: adapters.to_polars(object()), "to_polars: batch must be a"),
        (lambda: adapters.to_numpy({}, True), "to_numpy: batch must be a"),
        (
            lambda: adapters.to_scipy_csr(1, 0.0, 1, 2, None),
            "to_scipy_csr: batch must be",
        ),
        (lambda: adapters.plot_line([], "0", 1, ax=None), "plot_line: batch must be a"),
        (lambda: adapters.plot_scatter("", 0, 1, ax=None), "plot_scatter: batch must"),
    ),
)
def test_a_non_batch_is_the_first_type_error_and_imports_nothing(call, message) -> None:
    before = {m for m in sys.modules if m.partition(".")[0] in HEAVY}
    with pytest.raises(TypeError, match="^" + message) as raised:
        call()
    assert raised.value.__context__ is None
    assert {m for m in sys.modules if m.partition(".")[0] in HEAVY} == before


@pytest.mark.skipif(
    (platform.system(), platform.machine()) != ("Linux", "x86_64"),
    reason="the installed consumer runs only on Linux x86-64",
)
def test_a_consumer_without_its_target_fails_and_writes_no_report(tmp_path) -> None:
    report = tmp_path / "pandas.json"
    with pytest.raises(SystemExit, match="cell pandas holds targets"):
        consumer.main(["--cell", "pandas", "--report", str(report)])
    assert not report.exists()


def _report(cell: str) -> dict:
    cases = consumer.expected_common(cell)
    if cell == "numpy":
        cases |= consumer.expected_numpy()
    elif cell == "scipy":
        cases |= consumer.expected_scipy()
    elif cell == "matplotlib":
        cases |= consumer.expected_plots()
    elif cell != "arrow":
        cases |= consumer.expected_frames(cell, consumer.frame_inputs())
    versions = {"pyarrow": consumer.PYARROW} | {
        t: consumer.PINS[t] for t in consumer.CELLS[cell]
    }
    return {
        "format": consumer.FORMAT,
        "context": {"checkout": "c" * 40, "python": "3.13"},
        "cell": cell,
        "versions": versions,
        "origins": {
            "pietto.interop": "/env/lib/python3.13/site-packages/pietto/interop/__init__.py"
        },
        "cases": {name: cases[name] for name in consumer.cases_of(cell)},
    }


def _verify(report: dict, cell: str) -> None:
    consumer.verify_report(report, cell=cell, python="3.13", checkout="c" * 40)


def _damaged(cell: str):
    first = consumer.cases_of(cell)[0]
    yield "cell", lambda r: r.update(cell="arrow" if cell == "numpy" else "numpy")
    yield "python", lambda r: r["context"].update(python="3.12")
    yield "checkout", lambda r: r["context"].update(checkout="d" * 40)
    yield "missing case", lambda r: r["cases"].pop(first)
    yield "empty cases", lambda r: r.update(cases={})
    yield "reordered", lambda r: r.update(cases=dict(reversed(r["cases"].items())))
    yield "skipped target", lambda r: r["versions"].pop(next(reversed(r["versions"])))
    yield "wrong pyarrow", lambda r: r["versions"].update(pyarrow="26.0.0")
    yield (
        "source origin",
        lambda r: r["origins"].update(
            {"pietto.interop": str(ROOT / "src/pietto/interop/__init__.py")}
        ),
    )
    yield "no refusal", lambda r: r["cases"]["missing_extra"].clear()
    yield "batch closed", lambda r: r["cases"]["inert"][-1].__setitem__(3, True)
    yield "two reads", lambda r: r["cases"]["inert"][-1][2].update(array=2)
    yield "wrapped", lambda r: r["cases"]["unwrapped_failure"].__setitem__(3, "pandas")
    if cell == "numpy":
        yield from _damaged_numpy()
    elif cell == "scipy":
        yield from _damaged_scipy()
    elif cell == "matplotlib":
        yield from _damaged_plots()
    elif cell != "arrow":
        matrix = f"{cell}_matrix"
        yield "wrong pin", lambda r: r["versions"].update({cell: "0.0.0"})
        yield (
            "lost null",
            lambda r: r["cases"][matrix]["scalar"]["columns"][1].__setitem__(
                1, ["int", "0"]
            ),
        )
        yield (
            "signed zero",
            lambda r: r["cases"][matrix]["scalar"]["columns"][4][1].__setitem__(
                1, "0" * 16
            ),
        )
        yield (
            "cast type",
            lambda r: r["cases"][matrix]["numeric"]["types"].__setitem__(
                4, r["cases"][matrix]["numeric"]["types"][0]
            ),
        )
        yield "reordered rows", lambda r: r["cases"][f"{cell}_order"][0].reverse()
        yield "frame reread", lambda r: r["cases"][f"{cell}_reads"][1].update(array=2)
        yield "lost after close", lambda r: r["cases"][f"{cell}_after_close"][0].pop()
        if cell == "pandas":
            yield "short index accepted", lambda r: r["cases"]["pandas_drift"].pop(1)


def _damaged_numpy():
    def case(name):
        return lambda r: r["cases"][f"numpy_{name}"]

    matrix, copied = case("matrix"), case("copy")
    yield "wrong pin", lambda r: r["versions"].update(numpy="0.0.0")
    yield "cast type", lambda r: matrix(r)["fields"][0].__setitem__(1, "float64")
    yield "reordered rows", lambda r: matrix(r)["fields"][0][3].reverse()
    yield "lost bits", lambda r: matrix(r)["fields"][1][3][1].__setitem__(1, "0" * 16)
    yield "lost sign", lambda r: case("signed_zero")(r).__setitem__(1, False)
    yield "not empty", lambda r: case("empty")(r)[0][2].__setitem__(0, 1)
    yield "view", lambda r: copied(r)[0].__setitem__(2, False)
    yield "shared buffer", lambda r: copied(r)[0].__setitem__(4, True)
    yield "write reached batch", lambda r: copied(r)[0].__setitem__(6, copied(r)[0][5])
    yield "label lookup", lambda r: case("labels")(r).reverse()
    yield "nullable admitted", lambda r: case("refusals")(r).pop(0)
    yield "cast accepted", lambda r: r["cases"].update(numpy_drift=[])
    yield "width accepted", lambda r: case("drift")(r).pop()
    yield "two reads", lambda r: case("inert")(r)[1].update(array=2)
    yield "lost after close", lambda r: case("after_close")(r).pop()


def _damaged_scipy():
    def cases(r):
        return r["cases"]

    yield "wrong pin", lambda r: r["versions"].update(scipy="0.0.0")
    yield "dropped zero", lambda r: cases(r)["scipy_matrix"]["int64"][0]["data"].pop()
    yield (
        "wide indices",
        lambda r: cases(r)["scipy_matrix"]["int16"][0]["dtypes"].__setitem__(
            0, "int64"
        ),
    )
    yield "changed width", lambda r: cases(r)["scipy_empty"][3]["dtypes"].pop()
    yield (
        "batch closed",
        lambda r: cases(r)["scipy_matrix"]["int32"].__setitem__(1, True),
    )
    yield (
        "order dependent",
        lambda r: cases(r)["scipy_permutations"].append(
            deepcopy(cases(r)["scipy_permutations"][0])
        ),
    )
    yield "unbounded", lambda r: cases(r)["scipy_bound"]["indptr"].pop()
    yield "drift accepted", lambda r: cases(r)["scipy_drift"].pop()
    yield "columns accepted", lambda r: cases(r)["scipy_drift"].pop(2)
    yield "pointers accepted", lambda r: cases(r)["scipy_drift"].pop(4)
    yield "data width accepted", lambda r: cases(r)["scipy_drift"].pop(5)
    yield "two reads", lambda r: cases(r)["scipy_inert"][1].update(array=2)
    yield "lost after close", lambda r: cases(r)["scipy_after_close"][1].pop()


def _damaged_plots():
    def case(name):
        return lambda r: r["cases"][f"matplotlib_{name}"]

    draw, order = case("draw"), case("order")
    yield "wrong pin", lambda r: r["versions"].update(matplotlib="0.0.0")
    yield "signed zero", lambda r: draw(r)[0][5][1][1].__setitem__(1, "0" * 16)
    yield "int dtype", lambda r: draw(r)[2].__setitem__(3, "int64")
    yield "foreign axes", lambda r: draw(r)[1].__setitem__(1, False)
    yield "current axes drawn", lambda r: draw(r)[3][1].__setitem__(0, 1)
    yield "int array passed", lambda r: draw(r)[-1][0][1][0].__setitem__(1, "int64")
    yield "keyword passed", lambda r: draw(r)[-1][1][2].append("color")
    yield "empty shape", lambda r: case("empty")(r)[1][4].__setitem__(1, 1)
    yield "reordered points", lambda r: order(r)[0][5].reverse()
    yield "artist after refusal", lambda r: case("refusals")(r)[-1].__setitem__(0, 1)
    yield "two reads", lambda r: case("inert")(r)[0][2].update(array=2)
    yield "pyplot loaded", lambda r: case("inert")(r)[2].append("matplotlib.pyplot")
    yield "lost after close", lambda r: case("after_close")(r)[0][5].pop()


@pytest.mark.parametrize("cell", tuple(consumer.CELLS))
def test_the_report_checker_refuses_every_incomplete_or_changed_report(cell) -> None:
    valid = _report(cell)
    _verify(deepcopy(valid), cell)
    for name, damage in _damaged(cell):
        report = deepcopy(valid)
        damage(report)
        with pytest.raises(ValueError, match="^interop "):
            _verify(report, cell)
        assert json.dumps(report) != json.dumps(valid), name
    with pytest.raises(ValueError, match="^interop cell$"):
        consumer.verify_report(valid, cell="pyarrow", python="3.13", checkout="c" * 40)


def test_each_python_job_runs_every_interop_cell_at_its_extra_pin() -> None:
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = extras["project"]["optional-dependencies"]
    targets = [cell for cell in consumer.CELLS if cell != "arrow"]
    for target in targets:
        assert extras[consumer.EXTRA[target]] == [f"{target}=={consumer.PINS[target]}"]
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    run = '/bin/python" -I tests/_pietto_results_interop.py --cell '
    for python, word in (("3.12", "twelve"), ("3.13", "thirteen")):
        checks = job(workflow, "checks_" + word)
        for target in targets:
            extra = consumer.EXTRA[target]
            assert f'--extra-env "{extra}=$RUNNER_TEMP/{extra}"' in checks
        step = checks.split("- name: Run real isolated interop consumers\n")[1]
        step = step.split("\n      - name: ")[0]
        assert f'"$RUNNER_TEMP/arrow-ready{run}arrow ' in step
        assert f"for cell in {' '.join(targets)}; do" in step
        assert f'"$RUNNER_TEMP/interop-$cell{run}"$cell" ' in step
        assert step.count(f"-{python}.json") == 2
