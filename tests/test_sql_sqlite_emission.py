from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.sqlite import emit_sqlite_sql
from pietto.sql.sqlite_render import (
    SqliteRenderError,
    quote_identifier,
    render_literal,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "tests/fixtures/sqlite/single_file.pietto"
SQL_GOLDEN = REPO_ROOT / "tests/fixtures/golden/emit_sqlite_single_file.sql"
JSON_GOLDEN = REPO_ROOT / "tests/fixtures/golden/emit_sqlite_single_file.json"
HEADER = """shape User:
    id: Int
    name: Text
    active: Bool
    score: Float | None
    amount: Decimal(10, 2)
    born: Date
    seen: Timestamp
    uid: UUID

shape Order:
    id: Int
    user_id: Int

source users: User = sqlite.table("users")
source orders: Order = sqlite.table("orders")
source others: User = postgres.table("others")

"""
REFUSED = "SQLite SQL emission is not implemented for RelationIR: q. "
NO = "SQLite single-file SQL has no "
VALUES = "SQLite single-file SQL reads only Int, Text, Bool and Float values; "


def test_text_cli_matches_the_reviewed_golden(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["emit-sql", str(SOURCE), "--dialect", "sqlite"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == SQL_GOLDEN.read_bytes()

    output = tmp_path / "out.sql"
    arguments = ["emit-sql", str(SOURCE), "--dialect", "sqlite", "--output"]
    assert cli.main([*arguments, str(output)]) == 0
    assert capsys.readouterr() == ("", "")
    assert output.read_bytes() == SQL_GOLDEN.read_bytes()


def test_json_cli_matches_the_structural_v1_golden(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    path = SOURCE.relative_to(REPO_ROOT).as_posix()

    assert cli.main(["emit-sql", path, "--dialect", "sqlite", "--format=json"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    golden = json.loads(JSON_GOLDEN.read_text(encoding="utf-8"))
    # The CLI spells the input path as the platform does.
    assert document == {**golden, "path": str(Path(golden["path"]))}
    assert (document["schema_version"], document["dialect"]) == (1, "sqlite")


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (
            "query q:\n    from orders\n"
            "    inner join users on orders.user_id == users.id\n"
            "    select:\n        oid = orders.id\n",
            f"{NO}JOIN yet",
        ),
        (
            "query p:\n    from users\n    select:\n        id\n\n"
            "query q:\n    from p\n    select:\n        id\n",
            "SQLite single-file SQL reads a sqlite.table source directly; a table "
            "or query that reads another is not supported yet",
        ),
        (
            "query q:\n    from others\n    select:\n        id\n",
            "SQLite relation emission requires sqlite.table(Text)",
        ),
        (
            "query q:\n    from users\n    select:\n        id\n"
            "        r = row_number() window(order by id)\n    qualify r == 1\n",
            f"{NO}qualify yet",
        ),
        (
            "query q:\n    from users\n    select:\n        id\n"
            "        r = row_number() window(order by id)\n",
            f"{NO}window yet",
        ),
        (
            "query q:\n    from users\n    select:\n        id > 1\n",
            "SQLite single-file SQL needs a name for each output",
        ),
        (
            "query q:\n    from users\n    select:\n        x = id + 1\n",
            f"{NO}arithmetic yet",
        ),
        (
            "query q:\n    from users\n    where id > -5\n    select:\n        id\n",
            f"{NO}arithmetic yet; a sign before a number is arithmetic too",
        ),
        (
            "query q:\n    from users\n    select:\n        x = +0.0\n",
            f"{NO}arithmetic yet; a sign before a number is arithmetic too",
        ),
        (
            "query q:\n    from users\n    select:\n        x = lower(name)\n",
            f"{NO}function lower yet",
        ),
        (
            'query q:\n    from users\n    where starts_with(name, "a")\n'
            "    select:\n        id\n",
            f"{NO}function starts_with yet",
        ),
        (
            'query q:\n    from users\n    where name like "a%"\n'
            "    select:\n        id\n",
            f"{NO}operator like yet",
        ),
        (
            "query q:\n    from users\n    select:\n        x = 1 if active else 2\n",
            f"{NO}conditional expression yet",
        ),
        (
            "query q:\n    from users\n    where id in (1, 2)\n    select:\n        id\n",
            f"{NO}`in` test yet",
        ),
        (
            "query q:\n    from users\n    where 1 <= id <= 3\n    select:\n        id\n",
            f"{NO}range comparison yet",
        ),
        (
            "query q:\n    from users\n    select:\n        x = Float(id)\n",
            f"{NO}cast yet",
        ),
        (
            "query q:\n    from users\n"
            "    where any(o.user_id == users.id for o in orders)\n"
            "    select:\n        id\n",
            f"{NO}`any(...)` read yet",
        ),
        (
            "query q:\n    from users\n    select:\n        n = None\n",
            f"{NO}None literal yet",
        ),
        (
            "query q:\n    from users\n    where id < 1.5\n    select:\n        id\n",
            "SQLite single-file SQL compares only values of one type; this "
            "comparison has Int and Float",
        ),
        (
            "query q:\n    from users\n    where score == 1\n    select:\n        id\n",
            "SQLite single-file SQL compares only values of one type; this "
            "comparison has Float and Int",
        ),
        (
            'query q:\n    from users\n    where name == "a\x00b"\n'
            "    select:\n        id\n",
            "SQLite string literal must not contain NUL",
        ),
        (
            'source odd: User = sqlite.table("a\x00b")\n\n'
            "query q:\n    from odd\n    select:\n        id\n",
            "SQLite table identifier must not contain NUL",
        ),
        (
            "query q:\n    from users\n    select:\n        amount\n",
            f"{VALUES}field amount has type Decimal",
        ),
        (
            "query q:\n    from users\n    where born is None\n    select:\n        id\n",
            f"{VALUES}field born has type Date",
        ),
        (
            "query q:\n    from users\n    select:\n        seen\n",
            f"{VALUES}field seen has type Timestamp",
        ),
        (
            "query q:\n    from users\n    select:\n        uid\n",
            f"{VALUES}field uid has type UUID",
        ),
        (
            "query q:\n    from users\n    select:\n        s = sum(id)\n",
            f"{NO}aggregate sum yet",
        ),
        (
            "query q:\n    from users\n    select:\n        n = count_distinct(score)\n",
            "SQLite aggregate count_distinct supports only Int, Text and Bool fields",
        ),
        (
            "query q:\n    from users\n    select:\n        a = avg(score)\n",
            "SQLite aggregate avg supports only Int fields",
        ),
        (
            "query q:\n    from users\n    select:\n        id\n"
            "    order by:\n        score is None\n",
            "SQLite ORDER BY key must be a field",
        ),
    ],
)
def test_each_form_outside_the_subset_is_refused_at_its_relation(
    body: str, reason: str
) -> None:
    script_ir = _compile(HEADER + body)
    relation = next(
        item
        for item in script_ir.definitions
        if isinstance(item, RelationIR) and item.name == "q"
    )

    result = emit_sqlite_sql(script_ir)

    assert "q" not in [artifact.name for artifact in result.artifacts]
    assert [
        (item.code, item.severity, item.message) for item in result.diagnostics
    ] == [("PIE-B1000", Severity.ERROR, REFUSED + reason)]
    location = result.diagnostics[0].location
    assert (
        location.line,
        location.column,
        location.end_line,
        location.end_column,
    ) == (
        relation.span.line,
        relation.span.column,
        relation.span.end_line,
        relation.span.end_column,
    )


def test_each_comparison_and_none_test_emits_its_own_operator() -> None:
    script_ir = _compile(
        HEADER + "query q:\n    from users\n"
        '    where score is None and name != "x"\n'
        "    select:\n"
        "        eq = id == 1\n        ne = id != 2\n        lt = id < 3\n"
        "        le = id <= 4\n        gt = id > 5\n        ge = id >= 6\n"
        "        missing = score is None\n        present = score is not None\n"
        "        yes = active == True\n"
    )

    result = emit_sqlite_sql(script_ir)

    assert result.diagnostics == ()
    assert [(item.name, item.sql) for item in result.artifacts] == [
        (
            "q",
            "SELECT\n"
            "    `users`.`id` = 1 AS `eq`,\n"
            "    `users`.`id` <> 2 AS `ne`,\n"
            "    `users`.`id` < 3 AS `lt`,\n"
            "    `users`.`id` <= 4 AS `le`,\n"
            "    `users`.`id` > 5 AS `gt`,\n"
            "    `users`.`id` >= 6 AS `ge`,\n"
            "    `users`.`score` IS NULL AS `missing`,\n"
            "    `users`.`score` IS NOT NULL AS `present`,\n"
            "    `users`.`active` = 1 AS `yes`\n"
            "FROM `users`\n"
            "WHERE (`users`.`score` IS NULL) AND (`users`.`name` <> 'x')",
        )
    ]


def test_having_count_distinct_and_avg_emit_their_sql() -> None:
    """PL.47's single-file T2 forms: HAVING writes each selected aggregate and
    GROUP BY key itself, never an output alias, and a Bool literal as 1 or 0,
    as everywhere, which no output named TRUE or FALSE can shadow."""

    script_ir = _compile(
        HEADER + "query q:\n    from users\n    where score is not None\n"
        "    group by:\n        active\n        name\n"
        "    select:\n        active\n        name\n        id = count()\n"
        "        d = count_distinct(id)\n        TRUE = avg(id)\n"
        '    having id > 1 and active == True or name != "x" and TRUE < 2.5\n'
        "    order by:\n        d desc\n        TRUE\n"
    )

    result = emit_sqlite_sql(script_ir)

    assert result.diagnostics == ()
    assert [(item.name, item.sql) for item in result.artifacts] == [
        (
            "q",
            "SELECT\n"
            "    `users`.`active` AS `active`,\n"
            "    `users`.`name` AS `name`,\n"
            "    COUNT(*) AS `id`,\n"
            "    COUNT(DISTINCT `users`.`id`) AS `d`,\n"
            "    AVG(CAST(`users`.`id` AS REAL)) AS `TRUE`\n"
            "FROM `users`\n"
            "WHERE `users`.`score` IS NOT NULL\n"
            "GROUP BY\n"
            "    `users`.`active`,\n"
            "    `users`.`name`\n"
            "HAVING ((COUNT(*) > 1) AND (`users`.`active` = 1))"
            " OR ((`users`.`name` <> 'x') AND (AVG(CAST(`users`.`id` AS REAL)) < 2.5))\n"
            "ORDER BY\n"
            "    COUNT(DISTINCT `users`.`id`) DESC NULLS FIRST,\n"
            "    AVG(CAST(`users`.`id` AS REAL)) ASC NULLS LAST",
        )
    ]


def test_refusals_keep_backend_order_and_the_other_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mixed.pietto"
    path.write_text(
        HEADER
        + "query first_ok:\n    from users\n    select:\n        id\n\n"
        + "query bad:\n    from users\n    select:\n        x = id + 1\n\n"
        + "table second_ok:\n    from users\n    where active\n"
        + "    select:\n        name\n    limit 0\n\n"
        + "query worse:\n    from users\n    select:\n        amount\n",
        encoding="utf-8",
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "sqlite"]) == 1
    captured = capsys.readouterr()
    assert captured.out == (
        "-- first_ok\nSELECT\n    `users`.`id` AS `id`\nFROM `users`;\n\n"
        "-- second_ok\nSELECT\n    `users`.`name` AS `name`\nFROM `users`\n"
        "WHERE `users`.`active`\nLIMIT 0;\n"
    )
    assert [
        line.split(" error: ", maxsplit=1)[1].split(". ", maxsplit=1)[0]
        for line in captured.err.splitlines()
    ] == [
        "SQLite SQL emission is not implemented for RelationIR: bad",
        "SQLite SQL emission is not implemented for RelationIR: worse",
    ]

    assert (
        cli.main(["emit-sql", str(path), "--dialect", "sqlite", "--format=json"]) == 1
    )
    document = json.loads(capsys.readouterr().out)
    assert document["ok"] is False and document["dialect"] == "sqlite"
    assert [item["name"] for item in document["artifacts"]] == ["first_ok", "second_ok"]
    assert [item["code"] for item in document["diagnostics"]] == ["PIE-B1000"] * 2


@pytest.mark.parametrize("output", ["text", "json"])
def test_a_file_with_a_top_level_constant_refuses_every_relation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], output: str
) -> None:
    """D78.01: the IR holds a constant read as its literal, so SQLite refuses
    every relation of a file that declares a constant, with `--set` or not,
    naming the first constant in source order."""

    path = tmp_path / "constant.pietto"
    path.write_text(
        HEADER
        + "cutoff: Int = 5\n\nbase: Int = 1\n\n"
        + "query reads:\n    from users\n    where id > cutoff\n"
        + "    select:\n        id\n\n"
        + "query other:\n    from users\n    select:\n        name\n",
        encoding="utf-8",
    )
    reason = (
        "SQLite single-file SQL reads no top-level constant yet, and this file "
        "declares constant cutoff"
    )
    for settings in ((), ("--set", "cutoff=7")):
        arguments = ["emit-sql", str(path), "--dialect", "sqlite", *settings]
        assert cli.main([*arguments, f"--format={output}"]) == 1
        captured = capsys.readouterr()
        if output == "json":
            document = json.loads(captured.out)
            assert document["artifacts"] == []
            messages = [item["message"] for item in document["diagnostics"]]
        else:
            assert captured.out == ""
            messages = [
                line.split(" error: ", maxsplit=1)[1]
                for line in captured.err.splitlines()
            ]
        assert messages == [
            f"SQLite SQL emission is not implemented for RelationIR: {name}. {reason}"
            for name in ("reads", "other")
        ]


def test_each_backend_requires_its_own_connector() -> None:
    script_ir = _compile(
        HEADER
        + "query lite:\n    from users\n    select:\n        id\n\n"
        + "query pg:\n    from others\n    select:\n        id\n"
    )

    assert [
        item.message.split(". ", maxsplit=1)[1]
        for item in emit_postgres_sql(script_ir).diagnostics
    ] == ["PostgreSQL relation emission requires postgres.table(Text)"]
    assert [
        item.message.split(". ", maxsplit=1)[1]
        for item in emit_mysql_sql(script_ir).diagnostics
    ] == [
        "MySQL relation emission requires mysql.table(Text)",
        "MySQL relation emission requires mysql.table(Text)",
    ]
    sqlite = emit_sqlite_sql(script_ir)
    assert [artifact.name for artifact in sqlite.artifacts] == ["lite"]
    assert [item.message.split(". ", maxsplit=1)[1] for item in sqlite.diagnostics] == [
        "SQLite relation emission requires sqlite.table(Text)"
    ]


def test_names_are_backtick_quoted_and_literals_unsigned() -> None:
    script_ir = _compile(
        "shape T:\n    id: Int\n\n"
        'source t: T = sqlite.table("odd`name é")\n\n'
        "query q:\n    from t\n    select:\n        id\n"
    )
    (artifact,) = emit_sqlite_sql(script_ir).artifacts
    assert artifact.sql == (
        "SELECT\n    `odd``name é`.`id` AS `id`\nFROM `odd``name é`"
    )

    assert quote_identifier("a`b") == "`a``b`"
    assert [render_literal(value) for value in (True, False, 0, 2**63 - 1)] == [
        "1",
        "0",
        "0",
        "9223372036854775807",
    ]
    assert [render_literal(value) for value in (0.0, 0.1, 1e300)] == [
        "0.0",
        "0.1",
        "1e+300",
    ]
    assert render_literal("it's `x`\n") == "'it''s `x`\n'"
    for name in ("", "a\x00b", "\ud800"):
        with pytest.raises(SqliteRenderError):
            quote_identifier(name)
    for value in (
        -1,
        2**63,
        -0.0,
        -1.5,
        float("inf"),
        float("nan"),
        None,
        "a\x00",
        "\udc80",
        b"bytes",
    ):
        with pytest.raises(SqliteRenderError):
            render_literal(value)


def test_the_cli_alone_dispatches_the_sqlite_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AD78.03 and D78.04: single-file `--dialect sqlite` reaches the SQLite
    emitter and never the PostgreSQL or MySQL one, and only the CLI and the
    SQLite modules themselves import `pietto.sql.sqlite`."""

    from pietto import sql as sql_api
    from pietto.sql import mysql as mysql_backend
    from pietto.sql import sqlite as sqlite_backend

    calls: list[str] = []

    def spy(owner: Any, name: str) -> None:
        original = getattr(owner, name)

        def recorded(*arguments: Any, **keywords: Any) -> Any:
            calls.append(name)
            return original(*arguments, **keywords)

        monkeypatch.setattr(owner, name, recorded)

    spy(sql_api, "emit_postgres_sql")
    spy(mysql_backend, "emit_mysql_sql")
    spy(sqlite_backend, "emit_sqlite_sql")
    assert cli._select_sql_emitter("sqlite") is sqlite_backend.emit_sqlite_sql
    for output in ("text", "json"):
        cli.main(["emit-sql", str(SOURCE), "--dialect=sqlite", f"--format={output}"])
    capsys.readouterr()
    assert calls == ["emit_sqlite_sql", "emit_sqlite_sql"]

    # Each import names absolute modules: a relative `from` resolves against
    # the file's package, and `from P import x` also names `P.x`.
    importers = set()
    for path in (REPO_ROOT / "src" / "pietto").rglob("*.py"):
        package = ".".join(path.relative_to(REPO_ROOT / "src").parts[:-1])
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = importlib.util.resolve_name(
                    "." * node.level + (node.module or ""), package
                )
                names = [base, *(f"{base}.{alias.name}" for alias in node.names)]
            if any(name.startswith("pietto.sql.sqlite") for name in names):
                importers.add(path.relative_to(REPO_ROOT).as_posix())
    assert importers == {
        "src/pietto/cli.py",
        "src/pietto/sql/sqlite.py",
        "src/pietto/sql/sqlite_relations.py",
    }
    # The SQLite modules consume IR and the SQL model only: no other backend,
    # project, execution or database module.
    for name in ("sqlite.py", "sqlite_relations.py", "sqlite_render.py"):
        tree = ast.parse((REPO_ROOT / "src/pietto/sql" / name).read_text("utf-8"))
        modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert all(
            module in {"__future__", "collections.abc", "math", "typing"}
            or module.startswith(("pietto.ir", "pietto.errors", "pietto.sql.model"))
            or module.startswith("pietto.sql.sqlite")
            for module in modules
        ), (name, modules)


def _compile(text: str) -> ScriptIR:
    parsed = parse_source(text, path="sqlite.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert all(item.severity is not Severity.ERROR for item in semantic.diagnostics)
    assert semantic.script is not None
    result = build_ir(semantic.script, semantic.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result.ir
