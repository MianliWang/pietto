from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]

_VALID_PROJECT_SOURCE = (
    "shape Row:\n"
    "    id: Int\n"
    'source rows: Row is postgres.table("rows")\n'
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
            'enum Status:\n    active\nsource rows: Status is postgres.table("rows")\n',
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
            "files_ok": 1,
            "files_with_errors": 0,
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

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)

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

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)

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
        'source rows: Row is postgres.table("rows")\n',
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
    "    id: Int not null\n"
    "    n: Int nullable\n"
    "    t: Text nullable\n"
    'source src: T is postgres.table("src")\n'
)
_FLAT_EXPRESSION_ERRORS = (
    "query q:\n"
    "    from src\n"
    "    select:\n"
    "        id\n"
    "        a = id + t\n"
    "        b = cast(n as Text)\n"
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
                + 'source raw is postgres.table("raw")\n',
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
            (path, line + 1, 13, line + 1, 28),
            "Invalid cast: cast(Int as Text) is not supported; "
            "expected cast(Int as Float), the only supported cast",
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
        + 'constraint valid(x: Text not null) -> Bool not null:\n    x like "%a%"\n'
        + "derive normalized(x: Text not null) -> Text not null:\n    lower(x)\n",
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
    "relationship near:\n    endpoint l: src\n    endpoint r: d\n    on l.id == r.id\n"
    "query lagged:\n    from src\n    inner join d as r:\n        from src\n"
    "        via near: l -> r\n    select:\n        id = src.id\n"
    "        p = lag(r.n) window:\n            order by: src.id\n"
    "        f = first_value(r.n) window:\n            order by: src.id\n"
    "table joined:\n    from src\n    inner join d as r:\n        from src\n"
    "        via near: l -> r\n    select:\n        id = src.id\n        v = r.n\n"
    "query windowed:\n    from joined\n    select:\n        id\n"
    "        x = lag(v) window:\n            order by: id\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_SINGLE_FILE_SQL_LIMITS = (
    "enum Status:\n    active\n    closed\ntype A = Status\n"
    "shape T:\n    id: Int not null\n    n: Int nullable\n    t: Text nullable\n"
    "    s: A not null\n"
    'source src: T is postgres.table("app.src.x")\n'
    "query lets:\n    from src\n    let:\n        lo = lower(t)\n        a0 = n + n\n"
    + "".join(f"        a{i} = a{i - 1} + a{i - 1}\n" for i in range(1, 19))
    + "    select:\n        id\n        lo\n        big = a18\n"
    "query windows:\n    from src\n    select:\n        id\n"
    "        p = lag(s) window:\n            order by: id\n"
    "        b = lag(n, 9223372036854775808) window:\n            order by: id\n"
    "        f = first_value(n) window:\n            order by: id\n"
    "            rows between 9223372036854775808 preceding and current row\n"
    "query ordered:\n    from src\n    select:\n        id\n    order by:\n        -1\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_CONNECTORS = (
    "shape T:\n    id: Int not null\n"
    "source dotted: T is postgres.table(app.src)\n"
    "source one: T is postgres.table(1)\n"
    'source two: T is postgres.table("a", "b")\n'
    'source three: T is mysql.table("app.src.x")\n'
)
_LEGACY_FLAT_SHARED_REFUSALS = (
    "enum Status:\n    active\n    closed\ntype A = Status\n"
    "shape T:\n    id: Int not null\n    n: Int nullable\n    m: Int not null\n"
    "    u: Text not null\n    s: A not null\n    e: Status not null\n"
    'source src: T is postgres.table("src")\n'
    "query conflict:\n    from src\n    let:\n        k = n + 1\n    select:\n"
    "        k = id\n"
    "table t2:\n    from src\n    select:\n        id\n"
    "        v0 = n * m if false else -1 * len(u)\n"
    "query q:\n    from t2\n    select:\n        id\n"
    "        r0 = lag(v0, 1, 0) window:\n            order by: id\n"
    "query d:\n    from src\n    select:\n        id\n"
    "        p = lag(s, 1, 5) window:\n            order by: id\n"
)
_LEGACY_FLAT_GROUPED_LET = _FLAT_HEAD + (
    "query grouped:\n    from src\n    let:\n        g = n + id\n"
    "    group by:\n        g\n"
    "    select:\n        g\n        m = max(g)\n        c = count()\n"
    "query ranked:\n    from grouped\n    select:\n        g\n"
    "        p = lag(c) window:\n            order by: g\n"
    "query plain:\n    from src\n    select:\n        a = id + t\n"
)
_LEGACY_FLAT_RANGE_OFFSETS = _FLAT_HEAD + (
    "query q:\n    from src\n    select:\n        id\n"
    "        f = first_value(n) window:\n            order by: id\n"
    '            range "abc" preceding\n'
)
_LEGACY_FLAT_LET_EXTREMA = _FLAT_HEAD + (
    "query extrema:\n    from src\n    let:\n        w = n\n        e = id + t\n"
    "    where e > 1\n    select:\n        m = max(w)\n        k = min(w)\n"
)
_PLUS_TEXT = (
    "Invalid operands for operator +: expected numeric operands; "
    "string concatenation is not supported yet"
)


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            _LEGACY_FLAT_JOIN_WINDOWS,
            [("PIE-S2105", ("main.pietto", 43, 13, 43, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_SINGLE_FILE_SQL_LIMITS,
            [("PIE-S2105", ("main.pietto", 58, 13, 58, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_GROUPED_LET,
            [("PIE-S2105", ("main.pietto", 25, 13, 25, 19), _PLUS_TEXT)],
        ),
        (
            _LEGACY_FLAT_CONNECTORS,
            [
                (
                    "PIE-S2306",
                    ("main.pietto", 4, 18, 4, 35),
                    "Invalid source connector arguments for postgres.table",
                ),
                (
                    "PIE-S2306",
                    ("main.pietto", 5, 18, 5, 42),
                    "Invalid source connector arguments for postgres.table",
                ),
            ],
        ),
        (
            _LEGACY_FLAT_SHARED_REFUSALS,
            [
                (
                    "PIE-S2329",
                    ("main.pietto", 16, 9, 16, 18),
                    "Let binding conflicts with projection output name: k",
                ),
                (
                    "PIE-S2104",
                    ("main.pietto", 28, 14, 28, 27),
                    "Invalid arguments for function lag: value type must be concrete",
                ),
                (
                    "PIE-S2104",
                    ("main.pietto", 34, 13, 34, 25),
                    "Invalid arguments for function lag: "
                    "value and default must have the same exact type",
                ),
            ],
        ),
        (
            _LEGACY_FLAT_LET_EXTREMA,
            [("PIE-S2105", ("main.pietto", 10, 13, 10, 19), _PLUS_TEXT)],
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
    (schema version 2): windows over JOIN binding fields, a computed `let:`
    group key and its maximum, and windows over relations that read them
    pass, and so do the forms that only single-file SQL refuses (a selected
    `let:` name, the let inline limit, ROWS and GROUPS window literal ranges,
    a constant ORDER BY key, a window over an alias of an enum, a `min` or
    `max` of a `let:` name without GROUP BY, and connector table names that
    are not one string `<table>` or `<schema>.<table>`); a connector argument
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

        assert _located(_read_json_document(capsys)) == expected


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
    """Outside a grouped query an ORDER BY key reads input fields, not SELECT
    outputs, whether it names the output or computes with it; a grouped key
    can name an output."""
    root = _project_root(tmp_path, include=("*.pietto",))
    single = _write(root, "main.pietto", _LEGACY_FLAT_ORDER_BY_OUTPUTS)
    expected = [
        (
            "PIE-S2102",
            ("main.pietto", 12, 9, 12, 10),
            "Unknown field: x; outside a grouped query an ORDER BY key cannot "
            "name a SELECT output (restate its expression or bind it in `let:`)",
        ),
        ("PIE-S2102", ("main.pietto", 20, 9, 20, 10), "Unknown field: x"),
        ("PIE-S2102", ("main.pietto", 21, 10, 21, 11), "Unknown field: x"),
    ]

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == expected

    assert cli.main(["check", str(single), "--format", "json"]) == 1
    assert _located(_read_json_document(capsys)) == [
        (code, (str(single), *location[1:]), message)
        for code, location, message in expected
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
