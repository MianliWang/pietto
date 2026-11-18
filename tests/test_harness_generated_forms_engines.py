"""Generated forms run in process on SQLite and DuckDB against engine oracles.

Each registered case (tests/_pietto_harness_generated_forms.py) gets seeded
rows, and its own SQL (tests/_pietto_harness_engine_oracle.py) runs in an
in-memory SQLite database and, where the ``execute-duckdb`` extra is
installed, in DuckDB; the two engines must agree, and no column that the
generator's oracle types ``non_null`` may hold a NULL. Then, wherever the
product accepts the case, its public outputs must return the oracle's rows:
the SQL of single-file ``emit-sql --dialect sqlite`` and of ``compile_query``
for a SQLite project, run on the same database, and ``execute`` on the
``duckdb_arrow`` route of a DuckDB project's ``compile_query``, whose result
columns must also be the oracle's. Only public outputs are read; no JOIN
key, grain or single-match fact is (PL.62). A case the product refuses on a
target is outside that target's opened forms and is not compared, except a
witness, which keeps each route's reach.
"""

from __future__ import annotations

import ast
from contextlib import closing, redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import sqlite3
from typing import Any

import _pietto_harness_engine_oracle as engines
import _pietto_harness_generated_forms as forms
import _pietto_sql_duckdb as duckdb_files
import _pietto_sql_sqlite as sqlite_files
import pytest

from pietto import cli, execution

# The registered campaign: the generator's registered seeds of both profiles.
SEEDS = range(40)
# For each route, a row case and an aggregate case it must accept and compare.
WITNESSES = {
    "single-file sqlite": {(0, "narrow"), (17, "narrow")},
    "sqlite project": {(32, "narrow"), (17, "narrow")},
    "duckdb project": {(29, "broad"), (11, "broad")},
}
_NULLABLE = {True: forms.NULLABLE, False: forms.NON_NULL, "unknown": forms.UNKNOWN}


def _module(case: forms.Case, connector: str) -> str:
    """The case's module over ``connector``'s bare tables ``t`` and ``u``."""
    text = forms.module_text(case, "postgres")
    return text.replace('postgres.table("app.', f'{connector}("')


def _project(root: Path, case: forms.Case, connector: str, files: Any) -> Path:
    document = files.contract(*(files.source_entry(s, case.fields) for s in "tu"))
    files.write(root, "", document, header=_module(case, connector))
    return root


def _compiled(case: forms.Case, root: Path, dialect: str) -> Any:
    """``compile_query`` of the case, or None when the target refuses it."""
    files = {"sqlite": sqlite_files, "duckdb": duckdb_files}[dialect]
    if any(kind not in files.REPRESENTATIONS for _, kind, _ in case.fields):
        return None
    connector = {"sqlite": "sqlite.table", "duckdb": "duckdb.arrow"}[dialect]
    project = _project(root / dialect, case, connector, files)
    try:
        return execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="q",
            dialect=dialect,
            emission_contract="contract.json",
        )
    except execution.CompileRejected:
        return None


def _columns(emission: bytes | None) -> list[tuple[str, str, str]]:
    columns = json.loads(emission or b"null")["columns"]
    return [
        (c["label"], c["logical_type"]["name"], _NULLABLE[c["nullable"]])
        for c in columns
    ]


def _single_file_sql(case: forms.Case, root: Path) -> str | None:
    path = root / "sqlite.pietto"
    path.write_text(_module(case, "sqlite.table"), encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(
            ["emit-sql", str(path), "--dialect", "sqlite", "--format", "json"]
        )
    assert code in (0, 1), out.getvalue()  # 1: the target refuses the case
    if code:
        return None
    (sql,) = [a["sql"] for a in json.loads(out.getvalue())["artifacts"]]
    return sql


class _Routes:
    """The disagreements of one case's routes with the oracle."""

    def __init__(self, case: forms.Case, wanted: list[tuple]) -> None:
        self.case, self.wanted = case, wanted
        self.problems: list[str] = []

    def compare(self, route: str, records: list[Any] | None) -> None:
        if records is None:
            if (self.case.seed, self.case.profile) in WITNESSES[route]:
                self.problems.append(f"{route}: refused a witness")
            return
        seen = engines.normalized(self.case, records)
        why = engines.disagreement(self.case, seen, self.wanted)
        if why:
            self.problems.append(f"{route}: {why}: {seen} != oracle {self.wanted}")

    def report(self) -> str:
        case = self.case
        return "\n".join(
            [f"seed {case.seed}, profile {case.profile}"]
            + [f"{s}: {engines.rows(case, s)}" for s in "tu"]
            + [forms.module_text(case, "postgres"), *self.problems]
        )


def _sqlite_oracle(case: forms.Case) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    engines.load(connection, case, "sqlite")
    return connection


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", SEEDS)
def test_generated_case_on_sqlite(seed: int, profile: str, tmp_path: Path) -> None:
    case = forms.generate(seed, profile)
    with closing(_sqlite_oracle(case)) as connection:
        wanted = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
        routes = _Routes(case, wanted)
        nulls = engines.null_in_non_null(case, wanted)
        if nulls:
            routes.problems.append(f"oracle: NULL in non_null columns {nulls}")
        sql = _single_file_sql(case, tmp_path)
        routes.compare(
            "single-file sqlite",
            None if sql is None else connection.execute(sql).fetchall(),
        )
        query = _compiled(case, tmp_path, "sqlite")
        records = None
        if query is not None:
            if _columns(query.emission) != list(forms.expected_columns(case)):
                routes.problems.append(f"sqlite project: {_columns(query.emission)}")
            emitted = json.loads(query.emission or b"null")["sql"]
            records = connection.execute(emitted).fetchall()
        routes.compare("sqlite project", records)
    assert not routes.problems, routes.report()


def _zero(rows: list[tuple]) -> list[tuple]:
    # SQLite negates 0.0 to 0.0 and DuckDB to -0.0; the engines agree up to that.
    return [tuple(v + 0.0 if type(v) is float else v for v in row) for row in rows]


_ARROW = {"Int": "int64", "Float": "float64", "Text": "string", "Bool": "bool_"}


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", SEEDS)
def test_generated_case_on_duckdb(seed: int, profile: str, tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow", reason="the route needs PyArrow")
    duckdb = pytest.importorskip("duckdb", reason="the oracle needs the pinned duckdb")
    case = forms.generate(seed, profile)
    with closing(duckdb.connect()) as connection:
        engines.load(connection, case, "duckdb")
        wanted = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
    with closing(_sqlite_oracle(case)) as connection:
        other = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
    routes = _Routes(case, wanted)
    if engines.disagreement(replace(case, limit=None), _zero(other), _zero(wanted)):
        routes.problems.append(f"oracles: sqlite {other} != duckdb {wanted}")
    # The route takes one Arrow input per attempt, so a JOIN form is not run.
    query = None if case.form == "join" else _compiled(case, tmp_path, "duckdb")
    records = None
    if query is not None:
        if _columns(query.emission) != list(forms.expected_columns(case)):
            routes.problems.append(f"duckdb project: {_columns(query.emission)}")
        table = pa.table(
            {
                name: pa.array(
                    [row[i] for row in engines.rows(case, "t")],
                    type=getattr(pa, _ARROW[kind])(),
                )
                for i, (name, kind, _) in enumerate(case.fields)
            }
        )
        handle = execution.execute(
            query,
            route="duckdb_arrow",
            access=execution.DuckDBArrowInput("t", table),
            premise=None,
        )
        with handle as result:
            records = [
                tuple(row.values())
                for batch in result
                for row in pa.record_batch(batch).to_pylist()
            ]
    routes.compare("duckdb project", records)
    assert not routes.problems, routes.report()


def test_disagreement_binds_order_limit_and_ties() -> None:
    case = forms.generate(0, "narrow")
    row = replace(case, form="row", limit=None)
    assert not engines.disagreement(row, [(1,), (2,)], [(1,), (2,)])
    assert engines.disagreement(row, [(2,), (1,)], [(1,), (2,)])
    assert engines.disagreement(row, [(0.0,)], [(-0.0,)])
    assert engines.disagreement(row, [(True,)], [(1,)])
    limited = replace(row, limit=1)
    assert not engines.disagreement(limited, [(1,)], [(1,), (2,)])
    assert engines.disagreement(limited, [(2,)], [(1,), (2,)])
    ties = replace(case, form="join", limit=2)
    assert not engines.disagreement(ties, [(3,), (1,)], [(1,), (1,), (3,)])
    assert engines.disagreement(ties, [(3,), (4,)], [(1,), (1,), (3,)])
    assert engines.disagreement(ties, [(1,)], [(1,), (1,), (3,)])
    assert engines.disagreement(replace(ties, limit=None), [(1,)], [(1,), (1,)])


def test_engine_oracle_restates_the_case_without_pietto() -> None:
    tree = ast.parse(Path(engines.__file__).read_text(encoding="utf-8"))
    imported = {
        name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for name in (
            [a.name for a in node.names]
            if isinstance(node, ast.Import)
            else [node.module or ""]
        )
    }
    assert imported == {
        "__future__",
        "_pietto_harness_generated_forms",
        "collections",
        "random",
        "typing",
    }
