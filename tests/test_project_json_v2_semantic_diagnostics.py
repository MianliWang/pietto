from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto._project import model as project_model

REPO_ROOT = Path(__file__).resolve().parents[1]

_VALID_PROJECT_SOURCE = (
    "shape Row:\n"
    "    id: Int\n"
    'source rows: Row = postgres.table("rows")\n'
    "table projected:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
)


@pytest.mark.parametrize(
    ("source_name", "source_text", "expected_code", "expected_message"),
    (
        (
            "duplicate.pietto",
            "shape Row:\n    id: Int\nshape Row:\n    id: Int\n",
            "PIE-S2001",
            "Duplicate symbol name in type namespace: Row",
        ),
        (
            "unknown_type.pietto",
            "shape Broken:\n    id: MissingType\n",
            "PIE-S2002",
            "Unknown type: MissingType",
        ),
        (
            "bad_shape.pietto",
            'enum Status:\n    active\nsource rows: Status = postgres.table("rows")\n',
            "PIE-S2303",
            "Source shape must refer to a shape: Status",
        ),
        (
            "missing_relation.pietto",
            "table projected:\n    from missing_relation\n    select:\n        id\n",
            "PIE-S2301",
            "Unknown relation: missing_relation",
        ),
    ),
)
def test_project_json_v2_reports_semantic_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source_name: str,
    source_text: str,
    expected_code: str,
    expected_message: str,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, source_name, source_text)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": source_name,
            "kind": "source",
            "status": "parsed",
        }
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 0,
            "files_with_errors": 1,
        }
    }
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        (expected_code, expected_message)
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["suggestion"] is None
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == source_name
    serialized = json.dumps(document)
    assert str(root) not in serialized
    for private_fact in (
        "ProjectSymbol",
        "catalog",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
    ):
        assert private_fact not in serialized


def test_project_json_v2_does_not_compute_semantics_after_parser_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project JSON semantics must not run after parse errors")

    monkeypatch.setattr(
        project_model, "build_empty_project_semantic_result", unexpected_builder
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["cli_errors"] == []
    assert document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        }
    ]
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-P1000"]


def test_project_json_v2_does_not_compute_semantics_after_project_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project JSON semantics must not run after project errors")

    monkeypatch.setattr(
        project_model, "build_empty_project_semantic_result", unexpected_builder
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "source_read",
            "message": "Project source file must be valid UTF-8.",
            "path": "bad.pietto",
        }
    ]


def test_valid_cross_file_project_json_v2_remains_success_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(root, "models/a_shape.pietto", "shape Row:\n    id: Int\n")
    _write(
        root,
        "models/b_source.pietto",
        'source rows: Row = postgres.table("rows")\n',
    )
    _write(
        root,
        "models/c_table.pietto",
        "table projected:\n    from rows\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 3,
            "files_ok": 3,
            "files_with_errors": 0,
        }
    }


def test_project_text_check_still_reports_semantic_diagnostics_after_slice8(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "private_relation_error.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private_relation_error.pietto:2:5 PIE-S2301 error" in captured.err
    assert "Unknown relation: missing_relation" in captured.err


_FLAT_HEAD = (
    "shape T:\n"
    "    id: Int\n"
    "    n: Int | None\n"
    "    t: Text | None\n"
    'source src: T = postgres.table("src")\n'
)
_FLAT_EXPRESSION_ERRORS = (
    "query q:\n"
    "    from src\n"
    "    select:\n"
    "        id\n"
    "        a = id + t\n"
    "        b = Float(t)\n"
    "        c = nosuch + 1\n"
    "        d = lower(id)\n"
)


@pytest.mark.parametrize(
    ("files", "path", "line"),
    (
        ({"main.pietto": _FLAT_HEAD + _FLAT_EXPRESSION_ERRORS}, "main.pietto", 10),
        (
            {
                "a.pietto": _FLAT_HEAD.replace("    t:", "    x: Int\n    t:")
                + 'source raw = postgres.table("raw")\n',
                "b.pietto": _FLAT_EXPRESSION_ERRORS,
            },
            "b.pietto",
            5,
        ),
    ),
    ids=("one_file", "two_files"),
)
def test_a_legacy_flat_check_reports_each_expression_error_as_a_single_file_does(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    files: dict[str, str],
    path: str,
    line: int,
) -> None:
    """Its files are checked as one single file, a query reading a source of
    another file included; the check-mode diagnostics that a project command
    cannot select, for the implicit `x: Int` and the source without a shape,
    are not reported."""
    root = _project_root(tmp_path, include=("*.pietto",))
    for name, source in files.items():
        _write(root, name, source)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert _located(document) == [
        (
            "PIE-S2105",
            (path, line, 13, line, 19),
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
        ),
        (
            "PIE-S2105",
            (path, line + 1, 13, line + 1, 21),
            "Invalid cast from Text to Float: "
            "only Int-to-Float conversion is supported; write Float(expression)",
        ),
        ("PIE-S2102", (path, line + 2, 13, line + 2, 19), "Unknown field: nosuch"),
        (
            "PIE-S2104",
            (path, line + 3, 13, line + 3, 22),
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        ),
    ]


def test_a_legacy_flat_check_names_a_constraint_or_derive_of_another_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Its files are one callable namespace, so a call of a constraint or
    derive declared in another file says that it cannot be called, as in a
    single file. Before, the hint was looked up in the calling file only."""
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a.pietto",
        _FLAT_HEAD
        + 'constraint valid(x: Text) -> Bool:\n    return x like "%a%"\n'
        + "derive normalized(x: Text) -> Text:\n    return lower(x)\n",
    )
    _write(
        root,
        "b.pietto",
        "query q:\n    from src\n    where valid(t)\n    select:\n        id\n"
        "        m = normalized(t)\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    assert _located(_read_json_document(capsys)) == [
        (
            "PIE-S2103",
            ("b.pietto", 3, 11, 3, 19),
            "Unknown function: valid; valid is a constraint, which cannot be "
            "called; write a `def` instead",
        ),
        (
            "PIE-S2103",
            ("b.pietto", 6, 13, 6, 26),
            "Unknown function: normalized; normalized is a derive, which cannot "
            "be called; write a `def` instead",
        ),
    ]


def test_a_legacy_flat_check_reports_its_model_errors_first_and_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The single-file errors follow the project model's own diagnostics,
    which they do not repeat, such as the unknown relation."""
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "main.pietto",
        _FLAT_HEAD
        + "query q:\n    from src\n    select:\n        a = id + t\n"
        + "query lost:\n    from nowhere\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    assert _located(_read_json_document(capsys)) == [
        ("PIE-S2301", ("main.pietto", 11, 5, 11, 17), "Unknown relation: nowhere"),
        (
            "PIE-S2105",
            ("main.pietto", 9, 13, 9, 19),
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
        ),
    ]


def test_a_legacy_flat_check_past_the_expression_bound_reports_its_model_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A project is not held to the single-file expression bound (PIE-S2006):
    an expression nested past it in any file leaves only the project model's
    diagnostics, without the semantic checks of every file."""
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a.pietto",
        _FLAT_HEAD
        + "query q:\n    from src\n    select:\n        a = id + t\n"
        + "query lost:\n    from nowhere\n    select:\n        id\n",
    )
    command = ["check", "--project", str(root), "--format", "json"]
    unknown_relation = (
        "PIE-S2301",
        ("a.pietto", 11, 5, 11, 17),
        "Unknown relation: nowhere",
    )

    assert cli.main(command) == 1
    assert _located(_read_json_document(capsys)) == [
        unknown_relation,
        (
            "PIE-S2105",
            ("a.pietto", 9, 13, 9, 19),
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
        ),
    ]

    _write(
        root,
        "b.pietto",
        "query deep:\n    from src\n    select:\n        x = id" + " + 1" * 460 + "\n",
    )

    assert cli.main(command) == 1
    assert _located(_read_json_document(capsys)) == [unknown_relation]


_LEGACY_FLAT_JOIN_WINDOWS = _FLAT_HEAD + (
    "query d:\n    from src\n    select:\n        id\n        n\n"
    "query lagged:\n    from src\n    let r = d\n"
    "    inner join r on src.id == r.id\n    select:\n        id = src.id\n"
    "        p = lag(r.n) window(order by src.id)\n"
    "        f = first_value(r.n) window(order by src.id)\n"
    "table joined:\n    from src\n    let r = d\n"
    "    inner join r on src.id == r.id\n    select:\n        id = src.id\n        v = r.n\n"
    "query windowed:\n    from joined\n    select:\n        id\n"
    "        x = lag(v) window(order by id)\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_SINGLE_FILE_SQL_LIMITS = (
    "enum Status:\n    active\n    closed\ntype A = Status\n"
    "shape T:\n    id: Int\n    n: Int | None\n    t: Text | None\n"
    "    s: A\n"
    'source src: T = postgres.table("app.src.x")\n'
    "query lets:\n    from src\n    let lo = lower(t)\n    let a0 = n + n\n"
    + "".join(f"    let a{i} = a{i - 1} + a{i - 1}\n" for i in range(1, 19))
    + "    select:\n        id\n        lo\n        big = a18\n"
    "query windows:\n    from src\n    select:\n        id\n"
    "        p = lag(s) window(order by id)\n"
    "        b = lag(n, 9223372036854775808) window(order by id)\n"
    "        f = first_value(n) window(order by id rows between "
    "9223372036854775808 preceding and current row)\n"
    "query ordered:\n    from src\n    select:\n        id\n    order by:\n        -1\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_CONNECTORS = (
    "shape T:\n    id: Int\n"
    "source dotted: T = postgres.table(app.src)\n"
    "source one: T = postgres.table(1)\n"
    'source two: T = postgres.table("a", "b")\n'
    'source three: T = mysql.table("app.src.x")\n'
)
_LEGACY_FLAT_SHARED_REFUSALS = (
    "enum Status:\n    active\n    closed\ntype A = Status\n"
    "shape T:\n    id: Int\n    n: Int | None\n    m: Int\n"
    "    u: Text\n    s: A\n    e: Status\n"
    'source src: T = postgres.table("src")\n'
    "query conflict:\n    from src\n    let k = n + 1\n    select:\n"
    "        k = id\n"
    "table t2:\n    from src\n    select:\n        id\n"
    "        v0 = n * m if False else -1 * len(u)\n"
    "query q:\n    from t2\n    select:\n        id\n"
    "        r0 = lag(v0, 1, 0) window(order by id)\n"
    "query d:\n    from src\n    select:\n        id\n"
    "        p = lag(s, 1, 5) window(order by id)\n"
)
_LEGACY_FLAT_GROUPED_LET = _FLAT_HEAD + (
    "query grouped:\n    from src\n    let g = n + id\n"
    "    group by g\n"
    "    select:\n        g\n        m = max(g)\n        c = count()\n"
    "query ranked:\n    from grouped\n    select:\n        g\n"
    "        p = lag(c) window(order by g)\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_RANGE_OFFSETS = _FLAT_HEAD + (
    "query q:\n    from src\n    select:\n        id\n"
    '        f = first_value(n) window(order by id range "abc" preceding)\n'
)
_LEGACY_FLAT_LET_EXTREMA = _FLAT_HEAD + (
    "query extrema:\n    from src\n    let w = n\n    let e = id + t\n"
    "    where e > 1\n    select:\n        m = max(w)\n        k = min(w)\n"
)
_PLUS_TEXT = (
    "Invalid operands for operator +: expected numeric operands; "
    "string concatenation is not supported yet"
)
# A legacy-flat project has no JOIN in the current syntax: each JOIN `on` of
# these sources is PIE-S2334 there, before the shared diagnostics.
_LEGACY_FLAT_JOIN_REFUSALS = {
    _LEGACY_FLAT_JOIN_WINDOWS: [
        (
            "PIE-S2334",
            ("main.pietto", line, 18, line, 35),
            "JOIN r: a schema_version = 1 project has no JOIN in the current "
            "syntax; set schema_version = 2 to check it.",
        )
        for line in (14, 22)
    ],
}


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            _LEGACY_FLAT_JOIN_WINDOWS,
            [("PIE-S2105", ("main.pietto", 34, 13, 34, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_SINGLE_FILE_SQL_LIMITS,
            [("PIE-S2105", ("main.pietto", 53, 13, 53, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_GROUPED_LET,
            [("PIE-S2105", ("main.pietto", 22, 13, 22, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_CONNECTORS,
            [
                (
                    "PIE-S2306",
                    ("main.pietto", 4, 17, 4, 34),
                    "Invalid source connector arguments for postgres.table",
                ),
                (
                    "PIE-S2306",
                    ("main.pietto", 5, 17, 5, 41),
                    "Invalid source connector arguments for postgres.table",
                ),
            ],
        ),
        (
            _LEGACY_FLAT_SHARED_REFUSALS,
            [
                (
                    "PIE-S2329",
                    ("main.pietto", 15, 5, 15, 18),
                    "Let binding conflicts with projection output name: k",
                ),
                (
                    "PIE-S2104",
                    ("main.pietto", 27, 14, 27, 27),
                    "Invalid arguments for function lag: value type must be concrete",
                ),
                (
                    "PIE-S2104",
                    ("main.pietto", 32, 13, 32, 25),
                    "Invalid arguments for function lag: "
                    "value and default must have the same exact type",
                ),
            ],
        ),
        (
            _LEGACY_FLAT_LET_EXTREMA,
            [("PIE-S2105", ("main.pietto", 9, 13, 9, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_RANGE_OFFSETS,
            [
                (
                    "PIE-S2104",
                    ("main.pietto", 10, 13, 10, 27),
                    "Invalid window frame for function first_value: RANGE "
                    "offsets must be nonnegative integer literals up to "
                    "9223372036854775807",
                )
            ],
        ),
    ),
    ids=(
        "join_binding_windows",
        "single_file_sql_limits",
        "grouped_let",
        "connectors",
        "shared_refusals",
        "let_extrema",
        "range_offsets",
    ),
)
def test_a_legacy_flat_check_refuses_what_an_explicit_module_check_refuses(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source: str,
    expected: list[tuple[str, tuple[object, ...], str]],
) -> None:
    """A legacy-flat check (schema version 1) types as an explicit-module one
    (schema version 2), except that it refuses each JOIN `on`, having no JOIN
    in the current syntax: windows over JOIN binding fields, a computed `let:`
    group key and its maximum, and windows over relations that read them
    pass, and so do the forms that only single-file SQL refuses (a selected
    `let:` name, the let inline limit, ROWS and GROUPS window literal ranges,
    a constant ORDER BY key, a window over an alias of an enum, a `min` or
    `max` of a `let:` name without GROUP BY, and connector table names that
    are not one string `<table>` or `<schema>.<table>`), except an ORDER BY
    key written as a constant in a relation without JOIN inputs, which an
    explicit-module check refuses (PIE-S2380); a connector argument
    of another type or count, a let/output conflict, a
    window value of no concrete type, a default of another type and a RANGE
    offset that is not a nonnegative Int literal are refused in both modes."""
    for schema_version in (1, 2):
        root = _project_root(
            tmp_path / f"v{schema_version}",
            include=("*.pietto",),
            schema_version=schema_version,
        )
        _write(root, "main.pietto", source)

        assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

        assert _located(_read_json_document(capsys)) == (
            [*_LEGACY_FLAT_JOIN_REFUSALS.get(source, ()), *expected]
            if schema_version == 1
            else [*_EXPLICIT_MODULE_REFUSALS.get(source, ()), *expected]
        )


_EXPLICIT_MODULE_REFUSALS = {
    _LEGACY_FLAT_SINGLE_FILE_SQL_LIMITS: [
        (
            "PIE-S2380",
            ("main.pietto", 49, 9, 49, 11),
            "Constant ORDER BY key: a target reads a bare constant key as a "
            "column position or rejects it",
        )
    ],
}
_LEGACY_FLAT_ORDER_BY_OUTPUTS = _FLAT_HEAD + (
    "query bare:\n    from src\n    select:\n        id\n        x = n + 1\n"
    "    order by:\n        x desc\n        id\n"
    "query computed:\n    from src\n    select:\n        id\n        x = n + 1\n"
    "    order by:\n        x + 1\n        -x\n"
    "query input:\n    from src\n    select:\n        n = id\n    order by:\n        n\n"
    "query grouped:\n    from src\n    group by:\n        id\n    select:\n"
    "        id\n        x = max(n)\n    order by:\n        x\n"
)


def test_a_legacy_flat_check_reads_ungrouped_order_by_keys_as_a_single_file_does(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Outside a grouped query an ORDER BY key that is a SELECT output name
    alone reads that output, a key that computes with an output name reads
    input fields only, and a key naming both an input field and an output of
    another value is ambiguous; a grouped key can name an output."""
    root = _project_root(tmp_path, include=("*.pietto",))
    single = _write(root, "main.pietto", _LEGACY_FLAT_ORDER_BY_OUTPUTS)
    # Before: `x desc` was PIE-S2102 (an ORDER BY key outside a grouped query
    # could not name a SELECT output) and `n` silently sorted by the input
    # field.
    expected = [
        ("PIE-S2102", ("main.pietto", 20, 9, 20, 10), "Unknown field: x"),
        ("PIE-S2102", ("main.pietto", 21, 10, 21, 11), "Unknown field: x"),
        (
            "PIE-S2102",
            ("main.pietto", 27, 9, 27, 10),
            "Ambiguous field: n is both the input field src.n and a SELECT "
            "output; write src.n, or give the output another name",
        ),
    ]

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == expected

    assert cli.main(["check", str(single), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        (code, (str(single), *location[1:]), message)
        for code, location, message in expected
    ]


_LEGACY_FLAT_JOINS_WITHOUT_ON = (
    "shape T:\n    id: Int\n    n: Int | None\n"
    'source src: T = postgres.table("src")\n'
    'source d: T = postgres.table("d")\n'
    "query read:\n    from src\n    let r = d\n    left join r\n"
    "    select:\n        id = src.id\n        v = r.n\n"
    "query direct:\n    from src\n    inner join d\n    select:\n        id = src.id\n"
    "query later:\n    from src\n    let r = d\n    inner join r on src.id == r.id\n"
    "    left join d\n    select:\n        id = src.id\n"
)


_NO_JOIN = (
    ": a schema_version = 1 project has no JOIN in the current syntax; "
    "set schema_version = 2 to check it."
)
_NO_ANY = (
    "any(...): a schema_version = 1 project has no any(...) in the current "
    "syntax; set schema_version = 2 to check it."
)


def test_a_legacy_flat_check_refuses_a_join_without_on_as_one_with_on(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A schema_version = 1 project has no JOIN in the current syntax: an
    INNER or LEFT JOIN without `on` is PIE-S2334 at the JOIN with the text of
    a JOIN `on`, which is at the `on`, in source order, also in a relation
    that reads a field of its binding. A single file refuses those JOINs for
    their missing `on` (PIE-S2335), naming the FROM input."""
    root = _project_root(tmp_path, include=("*.pietto",))
    single = _write(root, "main.pietto", _LEGACY_FLAT_JOINS_WITHOUT_ON)
    joins = (("r", (9, 5, 9, 16)), ("d", (15, 5, 15, 17)), ("d", (22, 5, 22, 16)))

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        ("PIE-S2334", ("main.pietto", 9, 5, 9, 16), "JOIN r" + _NO_JOIN),
        ("PIE-S2334", ("main.pietto", 15, 5, 15, 17), "JOIN d" + _NO_JOIN),
        ("PIE-S2334", ("main.pietto", 21, 18, 21, 35), "JOIN r" + _NO_JOIN),
        ("PIE-S2334", ("main.pietto", 22, 5, 22, 16), "JOIN d" + _NO_JOIN),
    ]

    assert cli.main(["check", str(single), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        (
            "PIE-S2335",
            (str(single), *span),
            f"JOIN {binding}: write `on` with the condition that matches src to d",
        )
        for binding, span in joins
    ]


_LEGACY_FLAT_JOIN_AND_ANY_KINDS = (
    "shape T:\n    id: Int\n    n: Int | None\n"
    'source src: T = postgres.table("src")\n'
    'source d: T = postgres.table("d")\n'
    "query kinds:\n    from src\n"
    "    where any(x.id == src.id for x in d)\n"
    "    let r = d\n    right join r on src.id == r.id\n"
    "    let c = d\n    cross join c\n"
    "    let f = d\n    full join f on src.id == f.id\n"
    "    where not any(y.n == src.n for y in d)\n"
    "    select:\n        id = src.id\n"
    "        found = any(any(z.id == w.id for z in d) for w in d)\n"
)


def test_a_legacy_flat_check_refuses_each_join_and_any_once_in_source_order(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A schema_version = 1 project has neither JOIN nor any(...) in the
    current syntax: each JOIN, of any kind, is one PIE-S2334 at its `on` or
    else at the JOIN, and each any(...), before a JOIN or after, nested or
    not, is one PIE-S2334 at the any(...), never naming the hidden JOIN that
    a prefix any(...) lowers to, all in source order. A single file and a
    schema_version = 2 project check the same file."""
    single = _write(tmp_path / "single", "main.pietto", _LEGACY_FLAT_JOIN_AND_ANY_KINDS)

    assert cli.main(["check", str(single), "--format", "json"]) == 0
    assert _read_json_document(capsys)["diagnostics"] == []
    for schema_version in (2, 1):
        root = _project_root(
            tmp_path / f"v{schema_version}",
            include=("*.pietto",),
            schema_version=schema_version,
        )
        _write(root, "main.pietto", _LEGACY_FLAT_JOIN_AND_ANY_KINDS)

        code = cli.main(["check", "--project", str(root), "--format", "json"])

        if schema_version == 2:
            assert (code, _read_json_document(capsys)["diagnostics"]) == (0, [])
            continue
        assert (code, _located(_read_json_document(capsys))) == (
            1,
            [
                ("PIE-S2334", ("main.pietto", 8, 11, 8, 41), _NO_ANY),
                ("PIE-S2334", ("main.pietto", 10, 18, 10, 35), "JOIN r" + _NO_JOIN),
                ("PIE-S2334", ("main.pietto", 12, 5, 12, 17), "JOIN c" + _NO_JOIN),
                ("PIE-S2334", ("main.pietto", 14, 17, 14, 34), "JOIN f" + _NO_JOIN),
                ("PIE-S2334", ("main.pietto", 15, 15, 15, 43), _NO_ANY),
                ("PIE-S2334", ("main.pietto", 18, 17, 18, 61), _NO_ANY),
                ("PIE-S2334", ("main.pietto", 18, 21, 18, 49), _NO_ANY),
            ],
        )


_TEXT_PLUS = (
    "Invalid operands for operator +: expected numeric operands; string "
    "concatenation is not supported yet"
)
_NO_DISTINCT = (
    "SELECT DISTINCT is available only when an EXPLICIT_MODULES project "
    "(schema version 2) completes it."
)
_LEGACY_FLAT_REFUSAL_HEAD = (
    "shape T:\n    id: Int\n    n: Int | None\n"
    'source src: T = postgres.table("src")\n'
    'source d: T = postgres.table("d")\n'
    "query q:\n    from src\n"
)


@pytest.mark.parametrize(
    ("body", "legacy_flat", "single_file"),
    (
        (
            "    inner join nosuch\n"
            "    select:\n        id = src.id\n        v = nosuch.n\n",
            [("PIE-S2334", (8, 5, 8, 22), "JOIN nosuch" + _NO_JOIN)],
            [("PIE-S2301", (8, 5, 8, 22), "Unknown relation: nosuch")],
        ),
        (
            "    select found = any(x.id == src.id for x in nowhere)\n",
            [("PIE-S2334", (8, 20, 8, 56), _NO_ANY)],
            [
                (
                    "PIE-S2301",
                    (8, 48, 8, 55),
                    "Unknown or unavailable ANY relation: nowhere",
                )
            ],
        ),
        (
            "    select found = any(x.nope == src.id for x in d)\n",
            [("PIE-S2334", (8, 20, 8, 52), _NO_ANY)],
            [
                (
                    "PIE-S2102",
                    (8, 24, 8, 30),
                    "Unknown or unavailable field in ANY predicate: x.nope",
                )
            ],
        ),
        (
            '    select found = any(x.id == "a" for x in d)\n',
            [("PIE-S2334", (8, 20, 8, 47), _NO_ANY)],
            [
                (
                    "PIE-S2105",
                    (8, 24, 8, 35),
                    "Invalid operands for operator ==: expected comparable operands",
                )
            ],
        ),
        (
            "    where any(count() > 0 for x in d)\n    select:\n        id = src.id\n",
            [("PIE-S2334", (8, 11, 8, 38), _NO_ANY)],
            [
                (
                    "PIE-S2335",
                    (8, 15, 8, 26),
                    "Aggregate expressions are unavailable in ANY predicates.",
                )
            ],
        ),
        (
            "    group by src.id\n    select:\n        id = src.id\n"
            "    having any(x.id == 1 for x in d)\n",
            [
                ("PIE-S2334", (11, 12, 11, 37), _NO_ANY),
                (
                    "PIE-S2320",
                    (8, 5, 8, 20),
                    "Grouped output without an aggregate is not supported yet",
                ),
            ],
            [("PIE-S2334", (11, 12, 11, 37), "ANY is not supported in this context")],
        ),
        (
            "    where any(True for x in d)\n    let later = d\n    cross join later\n"
            "    select:\n        id = src.id\n",
            [
                ("PIE-S2334", (8, 11, 8, 31), _NO_ANY),
                ("PIE-S2334", (10, 5, 10, 21), "JOIN later" + _NO_JOIN),
            ],
            [],
        ),
        (
            "    let r = d\n    inner join r on src.id == r.id\n"
            "    where any(x.id == src.id for x in d)\n"
            "    select:\n        id = src.id\n"
            'source d: T = postgres.table("d2")\n',
            [
                (
                    "PIE-S2001",
                    (13, 1, 13, 35),
                    "Duplicate symbol name in relation namespace: d",
                ),
                ("PIE-S2334", (9, 18, 9, 35), "JOIN r" + _NO_JOIN),
                ("PIE-S2334", (10, 11, 10, 41), _NO_ANY),
                ("PIE-S2604", (8, 13, 8, 14), "Ambiguous relation name: d"),
            ],
            [
                ("PIE-S2604", (8, 13, 8, 14), "Ambiguous relation name: d"),
                ("PIE-S2604", (10, 11, 10, 41), "Ambiguous ANY input: d"),
            ],
        ),
        (
            "    inner join nosuch\n    select:\n        id = src.id\n",
            [("PIE-S2334", (8, 5, 8, 22), "JOIN nosuch" + _NO_JOIN)],
            [("PIE-S2301", (8, 5, 8, 22), "Unknown relation: nosuch")],
        ),
        (
            "    let r = d\n    inner join r on Has(src)\n"
            "    select:\n        id = src.id\n"
            "relationship Has(a: T, b: T):\n    a.id == b.id\n",
            [("PIE-S2334", (9, 18, 9, 29), "JOIN r" + _NO_JOIN)],
            [
                (
                    "PIE-S2604",
                    (9, 21, 9, 29),
                    "Invalid arguments for relationship Has: expected 2, got 1",
                )
            ],
        ),
        (
            '    select:\n        id = src.id\n        bad = src.id + "a"\n'
            "relationship Has(a: T, b: T):\n"
            "    a.id == b.id and any(x.id == a.id for x in d)\n",
            [
                ("PIE-S2334", (12, 22, 12, 50), _NO_ANY),
                ("PIE-S2105", (10, 15, 10, 27), _TEXT_PLUS),
            ],
            [("PIE-S2334", (12, 22, 12, 50), "ANY is not supported in this context")],
        ),
        (
            '    select:\n        id = src.id\n        bad = src.id + "a"\n'
            "constraint Big(value: Int) -> Bool:\n"
            "    return any(x.id == value for x in d)\n",
            [
                ("PIE-S2334", (12, 12, 12, 41), _NO_ANY),
                ("PIE-S2105", (10, 15, 10, 27), _TEXT_PLUS),
            ],
            [("PIE-S2334", (12, 12, 12, 41), "ANY is not supported in this context")],
        ),
        (
            "    let r = d\n    inner join r on src.id == r.id\n"
            "    select:\n        id = src.id\n"
            "relationship Has(a: T, b: T):\n    any(x.id == a.id for x in d)\n"
            'source d: T = postgres.table("d2")\n',
            [
                (
                    "PIE-S2001",
                    (14, 1, 14, 35),
                    "Duplicate symbol name in relation namespace: d",
                ),
                ("PIE-S2334", (9, 18, 9, 35), "JOIN r" + _NO_JOIN),
                ("PIE-S2334", (13, 5, 13, 33), _NO_ANY),
                ("PIE-S2604", (8, 13, 8, 14), "Ambiguous relation name: d"),
            ],
            [("PIE-S2334", (13, 5, 13, 33), "ANY is not supported in this context")],
        ),
        (
            "    where any(x.id == src.id for x in d)\n"
            "    let r = d\n    inner join r on src.id == r.id\n"
            "    select:\n        id = src.id\n"
            'query other:\n    from src\n    select:\n        bad = src.id + "a"\n',
            [
                ("PIE-S2334", (8, 11, 8, 41), _NO_ANY),
                ("PIE-S2334", (10, 18, 10, 35), "JOIN r" + _NO_JOIN),
                ("PIE-S2105", (16, 15, 16, 27), _TEXT_PLUS),
            ],
            [("PIE-S2105", (16, 15, 16, 27), _TEXT_PLUS)],
        ),
        (
            "    let r = d\n    inner join r on src.id == r.id\n"
            "    select distinct:\n        id = src.id\n"
            "        f = any(x.id == src.id for x in d)\n",
            [
                ("PIE-S2334", (9, 18, 9, 35), "JOIN r" + _NO_JOIN),
                ("PIE-S2334", (10, 12, 10, 20), _NO_DISTINCT),
                ("PIE-S2334", (12, 13, 12, 43), _NO_ANY),
            ],
            [("PIE-S2334", (10, 12, 10, 20), _NO_DISTINCT)],
        ),
    ),
    ids=(
        "join_to_an_unknown_target_whose_binding_is_read",
        "any_of_an_unknown_relation",
        "any_reading_an_unknown_field",
        "any_with_a_type_error",
        "any_with_an_aggregate",
        "any_in_having",
        "prefix_any_lowered_to_a_hidden_join",
        "duplicate_relation_name",
        "join_to_an_unknown_target_whose_binding_is_not_read",
        "relationship_call_error_in_on",
        "any_in_a_relationship_predicate",
        "any_in_a_constraint",
        "duplicate_relation_name_and_an_any_in_a_relationship_predicate",
        "prefix_any_beside_an_error_elsewhere",
        "distinct_between_a_join_and_an_any",
    ),
)
def test_a_legacy_flat_check_refuses_a_join_or_any_whatever_else_it_holds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    legacy_flat: list[tuple[str, tuple[int, int, int, int], str]],
    single_file: list[tuple[str, tuple[int, int, int, int], str]],
) -> None:
    """A schema_version = 1 project checks no JOIN and no any(...): each is
    one PIE-S2334 and nothing inside it is reported, whatever error a single
    file finds there, also when the relation reads a field of the JOIN's
    binding and when the project model has a declaration error, before the
    project's other diagnostics. An any(...) where a single file stops at
    it, as in HAVING, a declaration or a relationship predicate, keeps none of
    those back."""
    root = _project_root(tmp_path, include=("*.pietto",))
    single = _write(root, "main.pietto", _LEGACY_FLAT_REFUSAL_HEAD + body)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        (code, ("main.pietto", *span), message) for code, span, message in legacy_flat
    ]

    assert cli.main(["check", str(single), "--format", "json"]) == int(
        bool(single_file)
    )
    document = _read_json_document(capsys)
    assert (_located(document) if document["diagnostics"] else []) == [
        (code, (str(single), *span), message) for code, span, message in single_file
    ]


@pytest.mark.parametrize(
    ("body", "spans"),
    (
        (
            "    select found = False == any(x.id > 0 for x in d) == True\n",
            ((8, 29, 8, 53),),
        ),
        (
            "    where False == any(x.id > src.id for x in d) == True\n"
            "    select:\n        id = src.id\n",
            ((8, 20, 8, 49),),
        ),
        (
            "    let found = False == any(x.id > 0 for x in d) == True\n"
            "    select:\n        id = src.id\n",
            ((8, 26, 8, 50),),
        ),
        (
            "    select found = False == any(x.id > 0 for x in d)"
            " and any(x.id > 1 for x in d) == True\n",
            ((8, 29, 8, 53), (8, 58, 8, 82)),
        ),
    ),
    ids=("chain_in_select", "chain_in_where", "chain_in_let", "two_any_controls"),
)
def test_a_legacy_flat_check_refuses_an_any_in_a_repeated_chain_operand_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    spans: tuple[tuple[int, int, int, int], ...],
) -> None:
    """An any(...) that is the middle operand of a comparison chain is read
    by both of its comparisons, and a schema_version = 1 project still
    refuses it with one PIE-S2334 at the any(...); two any(...) at two
    positions are two."""
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "main.pietto", _LEGACY_FLAT_REFUSAL_HEAD + body)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        ("PIE-S2334", ("main.pietto", *span), _NO_ANY) for span in spans
    ]


def _located(
    document: dict[str, object],
) -> list[tuple[object, tuple[object, ...], object]]:
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert {item["severity"] for item in diagnostics} == {"error"}
    return [
        (
            item["code"],
            tuple(
                cast(dict[str, object], item["location"])[key]
                for key in ("path", "line", "column", "end_line", "end_column")
            ),
            item["message"],
        )
        for item in diagnostics
    ]


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
    schema_version: int = 1,
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        f"schema_version = {schema_version}\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
