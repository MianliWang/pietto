"""Partial analysis for the editor (`check_project_diagnostics`): a project
check that leaves out each module that stops it, and each module that imports
one, and checks the other modules again. Every case checks the three laws:
a module still checked reports what `check --project --format json` reports
with the left-out modules in `[sources].exclude` (restriction), that check
completes (completeness), and each left-out module has an error or one
not-checked message (accounting)."""

from __future__ import annotations

import contextlib
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

import pietto._project.check as project_check
from pietto import cli_json
from pietto._project.check import (
    ProjectDiagnosticsReport,
    check_project_diagnostics,
    check_project_parse_only,
)
from pietto.cli import main
from pietto.errors import Severity, SourceLocation

_MODELS = (
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text | None\n"
    "\n"
    'source users: User = postgres.table("public.users")\n'
    "\n"
    "def pos(x: Int) -> Bool:\n"
    "    return x > 0\n"
    "\n"
    "export (\n"
    "    shape User,\n"
    "    source users,\n"
    "    def pos,\n"
    ")\n"
)
_USES = 'from "models.pietto" import (\n    source users,\n)\n\n'
_SEMANTIC = (
    _USES + "table active:\n    from users\n    where nope is None\n    select:\n"
    "        id\n"
)
_SYNTAX = "table broken:\n    from users\n    select\n        id\n"
_NAMING = (
    _USES + "query emails:\n    from users\n    let n = 1\n    let n = 2\n"
    "    select:\n        email\n"
)
_AFTER_NAMING = (
    _USES + "query lagged(p: Int):\n    from users\n    let held = p + 1\n"
    "    select:\n        n = lag(id, 1) window(order by held)\n"
)
_PLAIN = "table {name}:\n    from users\n    select:\n        id\n"
_BAD_DEF_IMPORT = (
    'from "models.pietto" import (\n    source users,\n    def nope,\n)\n\n'
    + _PLAIN.format(name="b_rows")
)
_BAD_SHAPE_IMPORT = (
    'from "models.pietto" import (\n    source users,\n    shape Nope,\n)\n\n'
    + _PLAIN.format(name="g_rows")
)
_CYCLE_E = (
    'from "f.pietto" import (\n    table f_rows,\n)\n\n'
    "table e_rows:\n    from f_rows\n    select:\n        id\n\n"
    "export (\n    table e_rows,\n)\n"
)
_CYCLE_F = (
    'from "e.pietto" import (\n    table e_rows,\n)\n'
    + _USES
    + _PLAIN.format(name="f_rows")
    + "\nexport (\n    table f_rows,\n)\n"
)


def _imports(*targets: str) -> str:
    return "".join(
        f'from "{target}" import (\n    table {target.removesuffix(".pietto")}_rows,\n)\n'
        for target in targets
    )


def _exporting(name: str, body: str) -> str:
    return body + f"\nexport (\n    table {name}_rows,\n)\n"


def _not_checked(path: str, line: int, target: str, *failed: str) -> object:
    listed = (
        failed[0] if len(failed) == 1 else f"{', '.join(failed[:-1])} and {failed[-1]}"
    )
    verb = "has" if len(failed) == 1 else "have"
    return (
        SourceLocation(
            path=path,
            line=line,
            column=6,
            end_line=line,
            end_column=6 + len(target) + 2,
        ),
        f"Not checked: this module imports {listed}, which {verb} errors.",
    )


# Each case: its modules, the modules each pass leaves out, every module left
# out in the end, the not-checked messages, and the codes each checked module
# reports.
_CASES = {
    # A read, parse or admission stop hides a naming stop (b) and an import
    # cycle (e and f), the naming stop hides the checks after naming (d), and
    # those hide the semantic error in a: four passes.
    "stages": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "b.pietto": _NAMING,
            "c.pietto": _SYNTAX,
            "d.pietto": _AFTER_NAMING,
            "e.pietto": _CYCLE_E,
            "f.pietto": _CYCLE_F,
        },
        ((), ("c",), ("b", "c", "e", "f"), ("b", "c", "d", "e", "f")),
        ("b", "c", "d", "e", "f"),
        (_not_checked("e.pietto", 1, "f.pietto", "f.pietto"),),
        {
            "a.pietto": ["PIE-S2102"],
            "b.pietto": ["PIE-S2604"],
            "c.pietto": ["PIE-P1000"],
            "d.pietto": ["PIE-S2355"],
            "f.pietto": ["PIE-S2703"],
        },
    ),
    # A failed def import stops the check before naming; the parse error in c
    # hides it. The shape import error in g stops nothing: g stays checked.
    "def import": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "b.pietto": _BAD_DEF_IMPORT,
            "c.pietto": _SYNTAX,
            "d.pietto": _NAMING,
            "e.pietto": _AFTER_NAMING,
            "g.pietto": _BAD_SHAPE_IMPORT,
        },
        ((), ("c",), ("b", "c"), ("b", "c", "d"), ("b", "c", "d", "e")),
        ("b", "c", "d", "e"),
        (),
        {
            "a.pietto": ["PIE-S2102"],
            "b.pietto": ["PIE-S2705"],
            "c.pietto": ["PIE-P1000"],
            "d.pietto": ["PIE-S2604"],
            "e.pietto": ["PIE-S2355"],
            "g.pietto": ["PIE-S2705"],
        },
    ),
    # The modules that import a failed module, directly or through another,
    # are left out too.
    "chain": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "x.pietto": _exporting("x", _SYNTAX),
            "y.pietto": _exporting(
                "y", _imports("x.pietto") + _PLAIN.format(name="y_rows")
            ),
            "z.pietto": _imports("y.pietto") + _PLAIN.format(name="z_rows"),
        },
        ((), ("x", "y", "z")),
        ("x", "y", "z"),
        (
            _not_checked("y.pietto", 1, "x.pietto", "x.pietto"),
            _not_checked("z.pietto", 1, "y.pietto", "x.pietto"),
        ),
        {"a.pietto": ["PIE-S2102"], "x.pietto": ["PIE-P1000"]},
    ),
    "diamond": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "l.pietto": _exporting("l", _SYNTAX),
            "r.pietto": _exporting("r", _SYNTAX),
            "s.pietto": _exporting("s", _SYNTAX),
            "top.pietto": _USES
            + _imports("s.pietto", "r.pietto", "l.pietto")
            + _PLAIN.format(name="top_rows"),
        },
        ((), ("l", "r", "s", "top")),
        ("l", "r", "s", "top"),
        (
            _not_checked(
                "top.pietto", 5, "s.pietto", "l.pietto", "r.pietto", "s.pietto"
            ),
        ),
        {
            "a.pietto": ["PIE-S2102"],
            "l.pietto": ["PIE-P1000"],
            "r.pietto": ["PIE-P1000"],
            "s.pietto": ["PIE-P1000"],
        },
    ),
    # A module that is not UTF-8 fails with its discovery error.
    "unreadable": (
        {"models.pietto": _MODELS, "a.pietto": _SEMANTIC, "c.pietto": b"\xff\xfe"},
        ((), ("c",)),
        ("c",),
        (),
        {"a.pietto": ["PIE-S2102"]},
    ),
    # A retired spelling stops the check at admission.
    "admission": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "c.pietto": _USES
            + "table c_rows:\n    from users\n    where email == null\n"
            "    select:\n        id\n",
        },
        ((), ("c",)),
        ("c",),
        (),
        {"a.pietto": ["PIE-S2102"], "c.pietto": ["PIE-P1000"]},
    ),
    # A def named like a built-in stops the check at its header.
    "def header": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "h.pietto": "def lpad(x: Int) -> Int:\n    return x\n",
        },
        ((), ("h",)),
        ("h",),
        (),
        {"a.pietto": ["PIE-S2102"], "h.pietto": ["PIE-S2398"]},
    ),
    # Semantic analysis stops at an import cycle; its members are left out,
    # and the member without an error of its own says why.
    "semantic cycle": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "e.pietto": _CYCLE_E,
            "f.pietto": _CYCLE_F,
        },
        ((), ("e", "f")),
        ("e", "f"),
        (_not_checked("e.pietto", 1, "f.pietto", "f.pietto"),),
        {"a.pietto": ["PIE-S2102"], "f.pietto": ["PIE-S2703"]},
    ),
    # A def import along an import cycle stops the check before naming.
    "def cycle": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "f.pietto": 'from "g.pietto" import (\n    def gp,\n)\n\n'
            "def fp(x: Int) -> Bool:\n    return x > 0\n\n"
            "export (\n    def fp,\n)\n",
            "g.pietto": 'from "f.pietto" import (\n    def fp,\n)\n\n'
            "def gp(x: Int) -> Bool:\n    return x > 0\n\n"
            "export (\n    def gp,\n)\n",
        },
        ((), ("f", "g")),
        ("f", "g"),
        (_not_checked("f.pietto", 1, "g.pietto", "g.pietto"),),
        {"a.pietto": ["PIE-S2102"], "g.pietto": ["PIE-S2703"]},
    ),
    # One member of a longer cycle has the cycle error: the messages of the
    # other members, and of a module that imports the cycle, name only it.
    "longer cycle": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            **{
                f"{name}.pietto": _exporting(
                    name,
                    _imports(f"{target}.pietto")
                    + _USES
                    + _PLAIN.format(name=f"{name}_rows"),
                )
                for name, target in (("e", "f"), ("f", "g"), ("g", "e"), ("k", "e"))
            },
        },
        ((), ("e", "f", "g", "k")),
        ("e", "f", "g", "k"),
        (
            _not_checked("e.pietto", 1, "f.pietto", "g.pietto"),
            _not_checked("f.pietto", 1, "g.pietto", "g.pietto"),
            _not_checked("k.pietto", 1, "e.pietto", "g.pietto"),
        ),
        {"a.pietto": ["PIE-S2102"], "g.pietto": ["PIE-S2703"]},
    ),
    # A def import from a module that is not selected fails its module.
    "unresolved def import": (
        {
            "models.pietto": _MODELS,
            "a.pietto": _SEMANTIC,
            "b.pietto": 'from "nowhere.pietto" import (\n    def pos,\n)\n'
            + _USES
            + _PLAIN.format(name="b_rows"),
        },
        ((), ("b",)),
        ("b",),
        (),
        {"a.pietto": ["PIE-S2102"], "b.pietto": ["PIE-S2701"]},
    ),
    # Every module fails or imports one that does: no pass runs on nothing.
    "nothing left": (
        {
            "models.pietto": _MODELS.replace("shape User:", "shape User"),
            "a.pietto": _SEMANTIC,
            "b.pietto": _NAMING,
        },
        ((),),
        ("models", "a", "b"),
        (
            _not_checked("a.pietto", 1, "models.pietto", "models.pietto"),
            _not_checked("b.pietto", 1, "models.pietto", "models.pietto"),
        ),
        {"models.pietto": ["PIE-P1000"]},
    ),
}


@pytest.mark.parametrize("case", tuple(_CASES))
def test_partial_analysis_checks_past_each_stop_by_the_three_laws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    files, passes, left_out, not_checked, codes = _CASES[case]
    root = _project(tmp_path, files)

    report, excluded = _partial(root, monkeypatch)

    assert excluded == [{f"{name}.pietto" for name in item} for item in passes]
    assert report.not_checked == not_checked
    assert {
        path: [item.code for item in report.diagnostics if item.location.path == path]
        for path in report.paths
        if any(item.location.path == path for item in report.diagnostics)
    } == codes
    assert report.paths == tuple(sorted(files))
    _assert_laws(root, report, {f"{name}.pietto" for name in left_out})


def test_a_check_that_completes_reports_what_the_cli_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = {
        "models.pietto": _MODELS,
        "a.pietto": _SEMANTIC,
        "b.pietto": _SEMANTIC.replace("nope", "nope_b"),
        "g.pietto": _BAD_SHAPE_IMPORT,
    }
    root = _project(tmp_path, files)

    report, excluded = _partial(root, monkeypatch)

    assert excluded == [set()]
    assert report.not_checked == ()
    assert report.texts == files
    doc = _cli_json(root)
    assert _report_json(report, report.paths) == [
        item
        for path in report.paths
        for item in doc["diagnostics"]
        if item["location"]["path"] == path
    ]
    _assert_laws(root, report, set())


@pytest.mark.parametrize(
    "files",
    (
        {"pietto.toml": "schema_version = 2\n[sources\n", "a.pietto": _SEMANTIC},
        {
            "pietto.toml": 'schema_version = 1\n\n[sources]\ninclude = ["*.pietto"]\n',
            "a.pietto": "shape Row:\n    id: Int\n",
            "c.pietto": _SYNTAX,
        },
    ),
    ids=("bad config", "legacy flat"),
)
def test_a_check_without_modules_to_leave_out_is_the_cli_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    root = _project(tmp_path, files)

    report, excluded = _partial(root, monkeypatch)

    assert excluded == [set()]
    doc = _cli_json(root)
    assert _report_json(report, report.paths) == doc["diagnostics"]
    assert [
        {"kind": error.kind.value, "message": error.message, "path": error.path}
        for error in report.errors
    ] == doc["cli_errors"]
    assert report.not_checked == ()


def test_the_cli_check_still_stops_at_its_first_stop(tmp_path: Path) -> None:
    root = _project(tmp_path, _CASES["stages"][0])

    text = io.StringIO()
    with contextlib.redirect_stderr(text):
        assert main(["check", "--project", str(root)]) == 1
    doc = _cli_json(root)

    assert "c.pietto" in text.getvalue() and "PIE-P1000" in text.getvalue()
    assert all(
        code not in text.getvalue()
        for code in ("PIE-S2102", "PIE-S2604", "PIE-S2355", "PIE-S2703")
    )
    assert [
        (item["code"], item["location"]["path"]) for item in doc["diagnostics"]
    ] == [("PIE-P1000", "c.pietto")]


def _project(tmp_path: Path, files: Mapping[str, str | bytes]) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    if "pietto.toml" not in files:
        _configure(root, ())
    for path, text in files.items():
        if isinstance(text, bytes):
            (root / path).write_bytes(text)
        else:
            # Byte-exact on every platform, as the tests compare the texts read.
            (root / path).write_text(text, encoding="utf-8", newline="\n")
    return root


def _configure(root: Path, exclude: Iterable[str]) -> None:
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
        f"exclude = {json.dumps(sorted(exclude))}\n",
        encoding="utf-8",
    )


def _partial(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ProjectDiagnosticsReport, list[set[str]]]:
    """The report and the modules each pass left out."""

    excluded: list[set[str]] = []
    parse_only = project_check.check_project_parse_only

    def recorded(
        root: Path,
        *,
        overlays: Mapping[str, str] | None = None,
        exclude: frozenset[str] = frozenset(),
    ) -> object:
        excluded.append(set(exclude))
        return parse_only(root, overlays=overlays, exclude=exclude)

    monkeypatch.setattr(project_check, "check_project_parse_only", recorded)
    report = check_project_diagnostics(root, overlays={})
    monkeypatch.undo()
    return report, excluded


def _cli_json(root: Path) -> Any:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        main(["check", "--project", str(root), "--format", "json"])
    return json.loads(out.getvalue())


def _report_json(
    report: ProjectDiagnosticsReport, paths: tuple[str, ...]
) -> list[dict[str, object]]:
    """The report's diagnostics of ``paths`` as project JSON v2 writes them."""

    return [
        {
            **cli_json.diagnostic_to_json_dict(item),
            "related_locations": [
                {"message": None, "location": asdict(location)}
                for location in report.related_locations.get(item, ())
            ],
        }
        for path in paths
        for item in report.diagnostics
        if item.location.path == path
    ]


def _assert_laws(
    root: Path, report: ProjectDiagnosticsReport, left_out: set[str]
) -> None:
    _configure(root, left_out)
    doc = _cli_json(root)
    checked = tuple(path for path in report.paths if path not in left_out)
    # Restriction.
    assert _report_json(report, checked) == [
        item
        for path in checked
        for item in doc["diagnostics"]
        if item["location"]["path"] == path
    ]
    assert [
        (error.kind.value, error.message, error.path)
        for error in report.errors
        if error.path in checked
    ] == [
        (error["kind"], error["message"], error["path"])
        for error in doc["cli_errors"]
        if error["path"] in checked
    ]
    # Completeness.
    if checked:
        assert check_project_parse_only(root).ok
        assert all(item["code"] != "PIE-S2703" for item in doc["diagnostics"])
    # Accounting.
    hinted = [location.path for location, _ in report.not_checked]
    assert len(hinted) == len(set(hinted))
    for path in left_out:
        assert (
            path in hinted
            or any(error.path == path for error in report.errors)
            or any(
                item.location.path == path and item.severity is Severity.ERROR
                for item in report.diagnostics
            )
        )
