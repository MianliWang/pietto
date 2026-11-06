"""Cross-module `def` imports and exports in EXPLICIT_MODULES projects.

A def is bound by the same exports and imports as every other declaration,
before any call is inlined; its body and signature are
checked once, in the module that declares it, and a call inlines there as a
call of a local def does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli

SOURCE = (
    "shape Row:\n"
    "    id: Int\n"
    "    amount: Int\n"
    'source rows: Row = postgres.table("rows")\n'
)
DEFS = (
    "export def pos, source rows\n" + SOURCE + "def pos(x: Int) -> Bool:\n"
    "    return x > 0\n"
    "def helper(x: Int) -> Int:\n"
    "    return x + 1\n"
)


def _query(condition: str) -> str:
    return f"query q:\n    from rows\n    where {condition}\n    select:\n        id\n"


def _check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> list[tuple[str, str, int, int, str]]:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, text in files.items():
        (root / name).write_text(text)
    code = cli.main(["check", "--project", str(root), "--format", "json"])
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    assert code == (1 if diagnostics else 0)
    return [
        (
            item["code"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
            item["message"],
        )
        for item in diagnostics
    ]


@pytest.mark.parametrize(
    "files",
    (
        {
            "b.pietto": 'from "a.pietto" import def pos, source rows\n'
            + _query("pos(amount)")
        },
        {
            "b.pietto": 'from "a.pietto" import (\n    def pos as p,\n    source rows,\n)\n'
            + _query("p(amount)")
        },
        # A re-export of a re-export, renamed on the way.
        {
            "m.pietto": 'from "a.pietto" import def pos as positive\nexport def positive\n',
            "n.pietto": 'from "m.pietto" import def positive\nexport (def positive)\n',
            "b.pietto": 'from "a.pietto" import source rows\n'
            'from "n.pietto" import def positive\n' + _query("positive(amount)"),
        },
        # A def that calls a private helper of its module, and a local def
        # that calls an imported one.
        {
            "a.pietto": DEFS.replace("return x > 0", "return helper(x) > 1"),
            "b.pietto": 'from "a.pietto" import def pos, source rows\n'
            "def neg(x: Int) -> Bool:\n    return not pos(x)\n" + _query("neg(amount)"),
        },
        # The importer's alias of the same name never types the signature.
        {
            "a.pietto": DEFS.replace(
                "def pos(x: Int)", "type Amount = Int\ndef pos(x: Amount)"
            ),
            "b.pietto": 'from "a.pietto" import def pos, source rows\n'
            "type Amount = Text\n" + _query("pos(amount)"),
        },
    ),
)
def test_an_imported_def_is_called_by_the_name_its_import_binds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> None:
    assert _check(tmp_path, capsys, {"a.pietto": DEFS, **files}) == []


def test_each_failed_def_import_is_reported_at_its_item_and_none_wins(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    importer = (
        'from "a.pietto" import (\n'
        "    def helper,\n"
        "    def pos,\n"
        "    def pos as concat,\n"
        "    def pos as Float,\n"
        "    def pos as round,\n"
        "    def pos as rel,\n"
        "    source rows,\n"
        ")\n"
        "constraint pos(x: Int) -> Bool:\n    return x > 2\n"
        "relationship rel(a: Row, b: Row): a.id == b.id\n" + _query("missing > 0")
        # A def import error stops the check before semantic analysis, as a
        # def error does: the unknown field is not reported.
    )
    collision = "Import binding collides with a local declaration"
    assert _check(tmp_path, capsys, {"a.pietto": DEFS, "b.pietto": importer}) == [
        (
            "PIE-S2705",
            "b.pietto",
            2,
            9,
            'Imported declaration is private or not exported: def helper from "a.pietto"',
        ),
        ("PIE-S2706", "b.pietto", 3, 9, f"{collision}: pos; import def pos as <name>"),
        # A module's relationship is a local declaration of the binder too.
        ("PIE-S2706", "b.pietto", 7, 16, f"{collision}: rel; import def pos as <name>"),
        *(
            (
                "PIE-S2398",
                "b.pietto",
                line,
                5,
                f"Import binding {name} has the name of a built-in function; a def "
                "cannot shadow one",
            )
            for line, name in ((4, "concat"), (5, "Float"), (6, "round"))
        ),
    ]


def test_two_imports_of_one_local_name_are_ambiguous(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = "export def pos\ndef pos(x: Int) -> Bool:\n    return x > 1\n"
    importer = (
        'from "a.pietto" import def pos, source rows\n'
        'from "c.pietto" import def pos\n' + _query("pos(amount)")
    )
    assert _check(
        tmp_path, capsys, {"a.pietto": DEFS, "c.pietto": other, "b.pietto": importer}
    ) == [
        (
            "PIE-S2706",
            "b.pietto",
            1,
            28,
            "Import binding name is ambiguous: pos; import def pos as <name>",
        )
    ]


@pytest.mark.parametrize(
    ("items", "column"), (("source rows, def rows", 31), ("def rows, source rows", 28))
)
def test_an_ambiguous_name_hints_the_def_import_whatever_comes_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], items: str, column: int
) -> None:
    exporter = (
        DEFS.replace("export def pos,", "export def rows, def pos,")
        + "def rows(x: Int) -> Bool:\n    return x > 5\n"
    )
    importer = f'from "a.pietto" import {items}\n' + _query("rows(amount)")
    assert _check(tmp_path, capsys, {"a.pietto": exporter, "b.pietto": importer}) == [
        (
            "PIE-S2706",
            "b.pietto",
            1,
            column,
            "Import binding name is ambiguous: rows; import def rows as <name>",
        )
    ]


@pytest.mark.parametrize("declared", (True, False))
def test_a_module_exports_its_own_def_beside_an_imported_source_of_its_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], declared: bool
) -> None:
    middle = 'from "a.pietto" import source rows\nexport def rows, source rows\n'
    if declared:
        middle += "def rows(x: Int) -> Bool:\n    return x > 1\n"
    importer = 'from "m.pietto" import def rows as r, source rows\n' + _query(
        "r(amount)"
    )
    assert _check(
        tmp_path, capsys, {"a.pietto": DEFS, "m.pietto": middle, "b.pietto": importer}
    ) == (
        []
        if declared
        else [
            (
                "PIE-S2704",
                "m.pietto",
                2,
                12,
                "Invalid imported export candidate: def rows; rows is a source",
            )
        ]
    )


def test_an_unknown_export_of_a_def_is_refused_at_the_export(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exporter = DEFS.replace("export def pos,", "export def pos, def nope,")
    importer = 'from "a.pietto" import def pos, source rows\n' + _query("pos(amount)")
    assert _check(tmp_path, capsys, {"a.pietto": exporter, "b.pietto": importer}) == [
        ("PIE-S2704", "a.pietto", 1, 21, "Unknown export binding: def nope")
    ]


@pytest.mark.parametrize(
    ("call", "hint"),
    (
        (
            "pos(amount)",
            'pos is a def exported by a.pietto: import it with from "a.pietto" '
            "import def pos",
        ),
        (
            "helper(amount) > 1",
            "helper is a def declared but not exported by a.pietto: export it "
            'there with export def helper, then import it with from "a.pietto" '
            "import def helper",
        ),
        # A qualified call is told to call the imported name.
        (
            "a.pos(amount)",
            'pos is a def exported by a.pietto: import it with from "a.pietto" '
            "import def pos, then call pos(...)",
        ),
    ),
)
def test_an_unknown_function_says_how_to_import_the_def_of_another_module(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], call: str, hint: str
) -> None:
    importer = 'from "a.pietto" import source rows\n' + _query(call)
    name = call.partition("(")[0]
    assert _check(tmp_path, capsys, {"a.pietto": DEFS, "b.pietto": importer}) == [
        ("PIE-S2103", "b.pietto", 4, 11, f"Unknown function: {name}; {hint}")
    ]


def test_call_errors_are_at_the_call_and_def_errors_at_the_def_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    importer = 'from "a.pietto" import def pos as p, source rows\n'
    assert _check(
        tmp_path,
        capsys,
        {"a.pietto": DEFS, "b.pietto": importer + _query("p(amount, id)")},
    ) == [
        (
            "PIE-S2395",
            "b.pietto",
            4,
            11,
            "Invalid arguments for def p: expected 1, got 2",
        )
    ]
    (tmp_path / "project").rename(tmp_path / "count")
    assert _check(
        tmp_path, capsys, {"a.pietto": DEFS, "b.pietto": importer + _query('p("x")')}
    ) == [
        (
            "PIE-S2395",
            "b.pietto",
            4,
            11,
            "Invalid argument for def p at position 1 (x): expected Int, got Text",
        )
    ]
    # A def with an error of its own is reported once, at the def; its
    # importers are not inlined and add nothing.
    (tmp_path / "project").rename(tmp_path / "type")
    assert _check(
        tmp_path,
        capsys,
        {
            "a.pietto": DEFS.replace("return x > 0", "return x + True"),
            "b.pietto": importer + _query("p(amount)"),
            "c.pietto": importer + _query("p(id)").replace("query q", "query r"),
        },
    ) == [
        (
            "PIE-S2105",
            "a.pietto",
            7,
            12,
            "Invalid operands for operator +: expected numeric operands",
        )
    ]


@pytest.mark.parametrize(
    ("broken", "through"), (("bad", False), ("pos", False), ("bad", True))
)
def test_a_def_error_in_one_module_hides_none_of_its_importers_own(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], broken: str, through: bool
) -> None:
    # The imported def or another def of its module fails; the importer's own
    # def errors are still reported, while a call of the failed def, and a
    # def that calls it, add nothing.
    declaring = (
        DEFS + "def bad(x: Int) -> Int:\n    return x + True\n"
        if broken == "bad"
        else DEFS.replace("return x > 0", "return x + True")
    )
    head = 'from "a.pietto" import def pos, source rows\n'
    files = {"a.pietto": declaring}
    if through:
        files["m.pietto"] = 'from "a.pietto" import def pos\nexport def pos\n'
        head = 'from "m.pietto" import def pos\nfrom "a.pietto" import source rows\n'
    files["b.pietto"] = (
        head
        + "def twice(x: Int) -> Bool:\n    return pos(x) and pos(x + 1)\n"
        + "def neg(x: Int) -> Bool:\n    return x - True\n"
        + _query("pos(amount) and twice(id) and neg(amount) and pos(1, 2)")
    )
    assert _check(tmp_path, capsys, files) == [
        (
            "PIE-S2105",
            "a.pietto",
            11 if broken == "bad" else 7,
            12,
            "Invalid operands for operator +: expected numeric operands",
        ),
        (
            "PIE-S2105",
            "b.pietto",
            head.count("\n") + 4,
            12,
            "Invalid operands for operator -: expected numeric operands",
        ),
    ]


def _balanced(leaves: int) -> str:
    return (
        "x" if leaves == 1 else f"({_balanced(leaves // 2)} + {_balanced(leaves // 2)})"
    )


@pytest.mark.parametrize("imported", (True, False))
def test_an_expansion_over_the_size_bound_is_refused_at_the_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], imported: bool
) -> None:
    big = f"def big(x: Int) -> Int:\n    return {_balanced(64)}\n"
    head = 'from "a.pietto" import source rows\nfrom "s.pietto" import def big\n'
    files = (
        {"s.pietto": "export def big\n" + big, "b.pietto": head}
        if imported
        else {"b.pietto": head.splitlines(keepends=True)[0] + big}
    )
    files["b.pietto"] += _query(f"big({' + '.join(['amount'] * 9)}) > 0")
    line = 5 if imported else 6
    assert _check(tmp_path, capsys, {"a.pietto": DEFS, **files}) == [
        (
            "PIE-S2399",
            "b.pietto",
            line,
            11,
            "The expansion of def big has 1151 expression nodes nested 15 deep; an "
            "expansion, with its arguments, has at most 1000 nodes nested at most "
            "64 deep",
        )
    ]


def test_a_def_imported_along_an_import_cycle_is_blocked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The cycle is reported; neither call is inlined, and neither adds an
    # unknown function or argument error.
    declaring = DEFS.replace(
        "export def pos, source rows",
        'export def pos, source rows\nfrom "b.pietto" import def neg',
    )
    importer = (
        'from "a.pietto" import def pos, source rows\n'
        "export def neg\n"
        "def neg(x: Int) -> Bool:\n    return pos(0 - x)\n" + _query("neg(amount)")
    )
    assert _check(tmp_path, capsys, {"a.pietto": declaring, "b.pietto": importer}) == [
        (
            "PIE-S2703",
            "b.pietto",
            1,
            6,
            "Module import cycle detected: a.pietto -> b.pietto -> a.pietto",
        )
    ]


LABEL = (
    "export def label, shape Row, source lhs, source rhs\n"
    "shape Row:\n"
    "    id: Int\n"
    "    name: Text\n"
    "    row_key = unique(id)\n"
    'source lhs: Row = postgres.table("lhs")\n'
    'source rhs: Row = postgres.table("rhs")\n'
    "def label(x: Text) -> Text:\n"
    '    return concat(x, "!")\n'
)
LABEL_IMPORT = 'from "a.pietto" import def label, shape Row, source lhs, source rhs\n'
CONCAT_DEF = "def concat(x: Text) -> Text:\n    return lower(x)\n"
CONCAT_CONSTRAINT = 'constraint concat(x: Text) -> Bool:\n    return x == ""\n'
LABEL_QUERY = "query q:\n    from lhs\n    where {}\n    select:\n        id\n"


@pytest.mark.parametrize(
    "files",
    (
        {
            "b.pietto": LABEL_IMPORT
            + CONCAT_DEF
            + LABEL_QUERY.format("label(name) == concat(name)")
        },
        {
            "b.pietto": LABEL_IMPORT
            + CONCAT_CONSTRAINT
            + LABEL_QUERY.format('label(name) == "a!"')
        },
        {
            "b.pietto": LABEL_IMPORT
            + "derive concat(x: Text) -> Text:\n    return lower(x)\n"
            + LABEL_QUERY.format('label(name) == "a!"')
        },
        {
            "b.pietto": LABEL_IMPORT
            + "relationship concat(a: Row, b: Row): a.id == b.id\n"
            + LABEL_QUERY.format('label(name) == "a!"')
        },
        # A local def that calls the imported one, and a relationship whose
        # body calls it, expanded at the join.
        {
            "b.pietto": LABEL_IMPORT
            + CONCAT_DEF
            + "def shout(x: Text) -> Text:\n    return label(concat(x))\n"
            + LABEL_QUERY.format('shout(name) == "a!"')
        },
        {
            "b.pietto": LABEL_IMPORT
            + CONCAT_DEF
            + "relationship Same(a: Row, b: Row):\n"
            "    a.id == b.id and label(a.name) == b.name\n"
            "query q:\n    from lhs\n    inner join rhs on Same(lhs, rhs)\n"
            "    select:\n        id = lhs.id\n"
        },
        # Re-exported by a module that declares its own `concat` too.
        {
            "m.pietto": 'from "a.pietto" import def label as tag\nexport def tag\n'
            + CONCAT_DEF,
            "b.pietto": 'from "a.pietto" import source lhs\n'
            'from "m.pietto" import def tag\n'
            + CONCAT_CONSTRAINT
            + LABEL_QUERY.format('tag(name) == "a!"'),
        },
    ),
)
def test_an_imported_def_keeps_the_builtin_concat_its_module_bound(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> None:
    # The body is bound once, in a.pietto: an importer's own callable
    # `concat` does not take its `concat` call.
    assert _check(tmp_path, capsys, {"a.pietto": LABEL, **files}) == []


@pytest.mark.parametrize(
    ("declared", "condition", "expected"),
    (
        (
            CONCAT_CONSTRAINT,
            'label(name) == "a!" and concat(name, name) == "x"',
            (
                "PIE-S2103",
                35,
                "Unknown function: concat; concat is a constraint, which cannot be "
                "called; write a `def` instead",
            ),
        ),
        (
            CONCAT_DEF,
            'label(name) + name == "a!"',
            (
                "PIE-S2105",
                11,
                "Invalid operands for operator +: expected numeric operands; string "
                "concatenation is not supported yet",
            ),
        ),
    ),
)
def test_the_importer_text_keeps_its_own_concat(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    declared: str,
    condition: str,
    expected: tuple[str, int, str],
) -> None:
    code, column, message = expected
    importer = LABEL_IMPORT + declared + LABEL_QUERY.format(condition)
    assert _check(tmp_path, capsys, {"a.pietto": LABEL, "b.pietto": importer}) == [
        (code, "b.pietto", 6, column, message)
    ]


@pytest.mark.parametrize("stopped", (False, True))
def test_a_local_def_never_collides_with_an_import_of_another_kind(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stopped: bool
) -> None:
    # Also when an error elsewhere stops the check before semantic analysis.
    importer = (
        'from "a.pietto" import source rows, def pos\n'
        "def rows(x: Int) -> Bool:\n    return x > 1\n"
        + _query("rows(amount) and pos(id)")
    )
    files = {"a.pietto": DEFS, "b.pietto": importer}
    if stopped:
        files["c.pietto"] = "def bad(x: Int) -> Int:\n    return x + True\n"
    assert _check(tmp_path, capsys, files) == (
        [
            (
                "PIE-S2105",
                "c.pietto",
                2,
                12,
                "Invalid operands for operator +: expected numeric operands",
            )
        ]
        if stopped
        else []
    )
