"""Generated forms run in process on SQLite and DuckDB against engine oracles.

Each registered case (tests/_pietto_harness_generated_forms.py) gets seeded
rows, and its own SQL (tests/_pietto_harness_engine_oracle.py) runs in an
in-memory SQLite database and, where the ``execute-duckdb`` extra is
installed, in DuckDB; the two engines must agree, and no column that the
generator's oracle types ``non_null`` may hold a NULL. Then, wherever the
product accepts the case, its public outputs must return the oracle's rows:
the SQL of single-file ``emit-sql --dialect sqlite`` and of ``compile_query``
for a SQLite project, run on the same database, and ``execute`` on the
``duckdb_arrow`` route of a DuckDB project's ``compile_query``, with one
input per source the statement reads (D79.19), whose result columns and
Arrow types must also be the oracle's. Only public outputs are read; no JOIN
key, grain or single-match fact is (PL.62). Only a target's refusal leaves a
case uncompared: a single-file exit 1 whose errors are all PIE-B codes, a
project whose field types the target's representation table lacks, or a
``CompileRejected`` that is BLOCKED by PIE-B blockers alone; any other
failure fails the case, and a witness must be accepted.

A census requires the registered seeds to reach, on each route, each form
that route opens (``REACH``, at least one accepted case of each), and records
what each route reaches, its counts included, as an observation. Cases built
outside the registered seeds put a NULL in a deciding ORDER BY key,
ascending and descending, with and without a LIMIT, on all three routes;
their oracle rows change when the NULL places swap, so none passes without
the target's NULL order. One more keeps a row that a LEFT JOIN matches with
no row, on both project routes; its oracle rows change when the JOIN is read
as INNER, so it cannot pass with LEFT emitted as INNER.

Product SQLite SQL runs only on the measured build, under the SQLite class
of docs/development.md ("SQLite target validation"): elsewhere the oracle,
the reach and the project columns are still checked, and then no product row
is compared under ``hosted-refusal``, ``qualified`` fails and ``report``
skips with a counted ``PIETTO_NOT_RUN sqlite-native`` line. The DuckDB half
needs the ``execute-duckdb`` extra and skips without it; the integration
host runs it with the extra and admits no skip there (docs/development.md,
"DuckDB native qualification").
"""

from __future__ import annotations

import ast
from collections import Counter
from contextlib import closing, redirect_stdout
from dataclasses import replace
from datetime import date
import io
import itertools
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

import _pietto_harness_engine_oracle as engines
import _pietto_harness_generated_forms as forms
import _pietto_sql_duckdb as duckdb_files
import _pietto_sql_sqlite as sqlite_files
import pytest

from pietto import cli, execution

# For each route, registered cases it must accept and compare: a row case and
# an aggregate case, on each project route its INNER and LEFT JOIN, and on
# DuckDB its Date paths.
WITNESSES = {
    "single-file sqlite": {(0, "narrow"), (17, "narrow")},
    "sqlite project": {
        (32, "narrow"),
        (17, "narrow"),
        (2, "narrow"),  # INNER JOIN
        (26, "narrow"),  # LEFT JOIN whose WHERE keeps matched rows only
    },
    "duckdb project": {
        (29, "broad"),
        (11, "broad"),
        (2, "narrow"),  # INNER JOIN
        (15, "broad"),  # LEFT JOIN with a Date field
        (33, "narrow"),  # LEFT JOIN with a Date field
        (9, "narrow"),  # aggregate over a Date field
    },
}
# What each route opens, as the census's lower bound of one accepted case per
# form: a later opening does not fail it, a route that stops opening a form
# does, and fewer cases of a form that stays open do not.
REACH = {
    "single-file sqlite": {"row", "aggregate"},
    "sqlite project": {"row", "aggregate", "inner join", "left join"},
    "duckdb project": {"row", "aggregate", "inner join", "left join", "Date"},
}
SQLITE_ROUTES = ("single-file sqlite", "sqlite project")
# Explicit cases whose first ORDER BY key is an optional field holding NULLs.
NULL_ORDERS = [
    (kind, descending, limit)
    for kind in ("Int", "Text")
    for descending in (False, True)
    for limit in (None, 2)
]
_NULLABLE = {True: forms.NULLABLE, False: forms.NON_NULL, "unknown": forms.UNKNOWN}


def _module(case: forms.Case, connector: str) -> str:
    """The case's module over ``connector``'s bare tables ``t`` and ``u``."""
    text = forms.module_text(case, "postgres")
    return text.replace('postgres.table("app.', f'{connector}("')


def _project(root: Path, case: forms.Case, connector: str, files: Any) -> Path:
    document = files.contract(*(files.source_entry(s, case.fields) for s in "tu"))
    files.write(root, "", document, header=_module(case, connector))
    return root


def _unrepresented(case: forms.Case, dialect: str) -> bool:
    """Whether the target's representation table lacks a field type."""
    files = {"sqlite": sqlite_files, "duckdb": duckdb_files}[dialect]
    return any(kind not in files.REPRESENTATIONS for _, kind, _ in case.fields)


def _compiled(case: forms.Case, root: Path, dialect: str) -> Any:
    """``compile_query`` of the case, or None when the target refuses it: its
    field types lack a representation, or its emission is BLOCKED by PIE-B
    blockers alone. Any other refusal fails the case."""
    files = {"sqlite": sqlite_files, "duckdb": duckdb_files}[dialect]
    if _unrepresented(case, dialect):
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
    except execution.CompileRejected as rejected:
        document = json.loads(rejected.emission)
        codes = [blocker["code"] for blocker in document["blockers"]]
        errors = [d for d in document["diagnostics"] if d["severity"] == "error"]
        assert (
            rejected.status == document["status"] == "BLOCKED"
            and codes
            and all(code.startswith("PIE-B") for code in codes)
            and not errors
            and not document["cli_errors"]
        ), rejected.emission
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
    assert code in (0, 1), out.getvalue()
    if code:  # only the target's refusal: every error is a PIE-B code
        codes = [
            d["code"]
            for d in json.loads(out.getvalue())["diagnostics"]
            if d["severity"] == "error"
        ]
        assert codes and all(c.startswith("PIE-B") for c in codes), out.getvalue()
        return None
    (sql,) = [a["sql"] for a in json.loads(out.getvalue())["artifacts"]]
    return sql


class _Routes:
    """The disagreements of one case's routes with the oracle."""

    def __init__(
        self, case: forms.Case, wanted: list[tuple], *, witness: tuple[str, ...] = ()
    ) -> None:
        self.case, self.wanted, self.witness = case, wanted, witness
        self.problems: list[str] = []

    def reach(self, route: str, accepted: bool) -> None:
        """A witness must be accepted, whether or not its rows are compared:
        a registered one of ``WITNESSES``, or a built case on each route of
        ``witness``."""
        witness = (
            route in self.witness
            or (self.case.seed, self.case.profile) in WITNESSES[route]
        )
        if not accepted and witness:
            self.problems.append(f"{route}: refused a witness")

    def compare(self, route: str, records: list[Any] | None) -> None:
        self.reach(route, records is not None)
        if records is None:
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


@pytest.fixture(scope="module")
def sqlite_build(request: pytest.FixtureRequest) -> tuple[str | None, str]:
    """The part of this SQLite build's identity that differs from the
    measured build, or None, and the declared SQLite class."""
    declared = sqlite_files.sqlite_class(
        os.environ, request.config.getoption("--pietto-sqlite-class")
    )
    with closing(sqlite3.connect(":memory:")) as connection:
        return sqlite_files.refusal(sqlite_files.observe(connection)), declared


def _on_sqlite(
    case: forms.Case,
    root: Path,
    sqlite_build: tuple[str | None, str],
    *,
    witness: tuple[str, ...] = (),
) -> None:
    category, declared = sqlite_build
    with closing(_sqlite_oracle(case)) as connection:
        wanted = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
        routes = _Routes(case, wanted, witness=witness)
        nulls = engines.null_in_non_null(case, wanted)
        if nulls:
            routes.problems.append(f"oracle: NULL in non_null columns {nulls}")
        sql = _single_file_sql(case, root)
        query = _compiled(case, root, "sqlite")
        columns = None if query is None else _columns(query.emission)
        if columns not in (None, list(forms.expected_columns(case))):
            routes.problems.append(f"sqlite project: {columns}")
        if category is None:  # the measured build: product SQL runs
            routes.compare(
                "single-file sqlite",
                None if sql is None else connection.execute(sql).fetchall(),
            )
            records = None
            if query is not None:
                emitted = json.loads(query.emission or b"null")["sql"]
                records = connection.execute(emitted).fetchall()
            routes.compare("sqlite project", records)
        else:
            routes.reach("single-file sqlite", sql is not None)
            routes.reach("sqlite project", query is not None)
    assert not routes.problems, routes.report()
    if category is not None:
        sqlite_files.decide(category, declared)


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", forms.SEEDS)
def test_generated_case_on_sqlite(
    seed: int, profile: str, tmp_path: Path, sqlite_build: tuple[str | None, str]
) -> None:
    _on_sqlite(forms.generate(seed, profile), tmp_path, sqlite_build)


def _zero(rows: list[tuple]) -> list[tuple]:
    # SQLite negates 0.0 to 0.0 and DuckDB to -0.0; the engines agree up to that.
    return [tuple(v + 0.0 if type(v) is float else v for v in row) for row in rows]


_ARROW = {
    "Int": "int64",
    "Float": "float64",
    "Text": "string",
    "Bool": "bool_",
    "Date": "date32",  # the DuckDB contract's arrow_date32 (_pietto_sql_duckdb)
}
# The Arrow type of a result column of each oracle type, as the route's
# schema names it.
_RESULT_TYPES = {
    "Int": "int64",
    "Float": "double",
    "Text": "string",
    "Bool": "bool",
    "Date": "date32[day]",
}


def _arrow_value(kind: str, value: Any) -> Any:
    # The oracle loads ISO date texts; the route takes dates.
    if kind == "Date" and value is not None:
        return date.fromisoformat(value)
    return value


def _arrow_table(pa: Any, case: forms.Case, source: str) -> Any:
    """The rows of ``source`` as the route's Arrow input."""
    values = engines.rows(case, source)
    return pa.table(
        {
            name: pa.array(
                [_arrow_value(kind, row[i]) for row in values],
                type=getattr(pa, _ARROW[kind])(),
            )
            for i, (name, kind, _) in enumerate(case.fields)
        }
    )


def _on_duckdb(case: forms.Case, root: Path, *, witness: tuple[str, ...] = ()) -> None:
    pa = pytest.importorskip("pyarrow", reason="the route needs PyArrow")
    duckdb = pytest.importorskip("duckdb", reason="the oracle needs the pinned duckdb")
    with closing(duckdb.connect()) as connection:
        engines.load(connection, case, "duckdb")
        wanted = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
    with closing(_sqlite_oracle(case)) as connection:
        other = engines.normalized(
            case, connection.execute(engines.oracle_sql(case)).fetchall()
        )
    routes = _Routes(case, wanted, witness=witness)
    if engines.disagreement(replace(case, limit=None), _zero(other), _zero(wanted)):
        routes.problems.append(f"oracles: sqlite {other} != duckdb {wanted}")
    query = _compiled(case, root, "duckdb")
    records = None
    if query is not None:
        if _columns(query.emission) != list(forms.expected_columns(case)):
            routes.problems.append(f"duckdb project: {_columns(query.emission)}")
        # One input per relation the statement reads, matched by name: a JOIN
        # form reads `u` as `r` beside `t` (D79.19).
        sources = ("t", "u") if case.form == "join" else ("t",)
        access = tuple(
            execution.DuckDBArrowInput(source, _arrow_table(pa, case, source))
            for source in sources
        )
        handle = execution.execute(
            query,
            route="duckdb_arrow",
            access=access[0] if len(access) == 1 else access,
            premise=None,
        )
        # The values are normalized below, so their Arrow types are read first.
        types = [str(field.type) for field in pa.schema(handle)]
        wanted_types = [
            _RESULT_TYPES[kind] for _, kind, _ in forms.expected_columns(case)
        ]
        if types != wanted_types:
            routes.problems.append(f"duckdb project: types {types}")
        with handle as result:
            records = [
                tuple(row.values())
                for batch in result
                for row in pa.record_batch(batch).to_pylist()
            ]
    routes.compare("duckdb project", records)
    assert not routes.problems, routes.report()


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", forms.SEEDS)
def test_generated_case_on_duckdb(seed: int, profile: str, tmp_path: Path) -> None:
    _on_duckdb(forms.generate(seed, profile), tmp_path)


def _null_order_case(kind: str, descending: bool, limit: int | None) -> forms.Case:
    """A row case outside the registered seeds, ordered by an optional
    ``kind`` field and then ``id``, whose rows hold at least two NULLs and two
    other values of that field. Its oracle rows change when the NULL places
    swap, so it cannot pass without the target's NULL order."""

    def drawn(seed: int) -> forms.Case:
        return forms.Case(
            seed=seed,
            profile="narrow",
            form="row",
            fields=(("id", "Int", False), ("f0", kind, True)),
            join=None,
            lets=(),
            where=None,
            keys=(),
            items=(("id", ("field", "id")), ("f0", ("field", "f0"))),
            order=(("f0", descending), ("id", False)),
            limit=limit,
        )

    def nulls(case: forms.Case) -> int:
        return sum(row[1] is None for row in engines.rows(case, "t"))

    case = next(
        case
        for case in map(drawn, itertools.count(1000))
        if 2 <= nulls(case) <= engines.ROWS - 2
    )
    text = engines.oracle_sql(case)
    swapped = re.sub(
        "NULLS (FIRST|LAST)",
        lambda m: "NULLS " + ("LAST" if m[1] == "FIRST" else "FIRST"),
        text,
    )
    with closing(_sqlite_oracle(case)) as connection:
        wanted, other = (
            engines.normalized(case, connection.execute(sql).fetchall())
            for sql in (text, swapped)
        )
    assert engines.disagreement(case, other[:limit], wanted), (case, wanted)
    return case


@pytest.mark.parametrize("kind,descending,limit", NULL_ORDERS)
def test_null_order_case_on_sqlite(
    kind: str,
    descending: bool,
    limit: int | None,
    tmp_path: Path,
    sqlite_build: tuple[str | None, str],
) -> None:
    case = _null_order_case(kind, descending, limit)
    _on_sqlite(case, tmp_path, sqlite_build, witness=SQLITE_ROUTES)


@pytest.mark.parametrize("kind,descending,limit", NULL_ORDERS)
def test_null_order_case_on_duckdb(
    kind: str, descending: bool, limit: int | None, tmp_path: Path
) -> None:
    _on_duckdb(
        _null_order_case(kind, descending, limit),
        tmp_path,
        witness=("duckdb project",),
    )


def _left_join_case() -> forms.Case:
    """A LEFT JOIN case outside the registered seeds, some of whose ``t``
    rows match no ``u`` row. Its oracle rows change when the JOIN is read as
    INNER, so it cannot pass with LEFT emitted as INNER; the one registered
    LEFT JOIN that a SQLite project accepts, (26, narrow), keeps matched rows
    only by its WHERE."""

    def drawn(seed: int, kind: str = "left") -> forms.Case:
        return forms.Case(
            seed=seed,
            profile="narrow",
            form="join",
            fields=(("id", "Int", False), ("f0", "Text", False)),
            join=(kind, ("cmp", "==", ("field", "t.f0"), ("field", "r.f0"))),
            lets=(),
            where=None,
            keys=(),
            items=(("o0", ("field", "t.id")), ("o1", ("field", "r.id"))),
            order=(("t.id", False),),
            limit=None,
        )

    def oracle(case: forms.Case) -> list[tuple]:
        with closing(_sqlite_oracle(case)) as connection:
            rows = connection.execute(engines.oracle_sql(case)).fetchall()
            return engines.normalized(case, rows)

    case = next(
        drawn(seed)
        for seed in itertools.count(1000)
        if None in {row[1] for row in oracle(drawn(seed))}
        and oracle(drawn(seed, "inner"))
    )
    wanted, inner = oracle(case), oracle(drawn(case.seed, "inner"))
    assert engines.disagreement(case, inner, wanted), (case, wanted)
    return case


def test_left_join_case_on_sqlite(
    tmp_path: Path, sqlite_build: tuple[str | None, str]
) -> None:
    _on_sqlite(_left_join_case(), tmp_path, sqlite_build, witness=("sqlite project",))


def test_left_join_case_on_duckdb(tmp_path: Path) -> None:
    _on_duckdb(_left_join_case(), tmp_path, witness=("duckdb project",))


def _reached(case: forms.Case) -> set[str]:
    """What a case reaches: its form, JOIN kind, field types and productions."""
    reached = {case.form} | {kind for _, kind, _ in case.fields}
    if case.join is not None:
        reached.add(f"{case.join[0]} join")
    pending = [e for _, e in (*case.items, *case.lets)]
    pending += [e for e in (case.where, case.join and case.join[1]) if e]
    while pending:
        node = pending.pop()
        reached.add(node[0] + (f" {node[1]}" if node[0] in ("call", "agg") else ""))
        pending += [part for part in node[1:] if isinstance(part, tuple)]
    return reached


def test_each_route_reaches_the_forms_it_opens(tmp_path: Path) -> None:
    """Coverage is an observation, not a proof; each route must still accept
    registered cases of each form it opens (``REACH``), so that a route that
    stops opening one cannot pass by comparing nothing. The counts per form,
    JOIN kind, type and production, and of each kind of refusal, are printed
    for the record."""
    accepted = {route: Counter() for route in REACH}
    refused = {route: Counter() for route in REACH}
    for seed in forms.SEEDS:
        for profile in forms.PROFILES:
            case = forms.generate(seed, profile)
            root = tmp_path / f"{profile}-{seed}"
            root.mkdir()
            verdicts = {
                "single-file sqlite": _single_file_sql(case, root) is not None,
                "sqlite project": _compiled(case, root, "sqlite") is not None,
                "duckdb project": _compiled(case, root, "duckdb") is not None,
            }
            for route, verdict in verdicts.items():
                if verdict:
                    accepted[route].update(_reached(case))
                    accepted[route]["cases"] += 1
                else:
                    dialect = {"sqlite project": "sqlite", "duckdb project": "duckdb"}
                    unrepresented = route in dialect and _unrepresented(
                        case, dialect[route]
                    )
                    refused[route]["representation" if unrepresented else "target"] += 1
    for route in REACH:
        print(f"{route}: accepted {dict(sorted(accepted[route].items()))}")
        print(f"{route}: refused {dict(sorted(refused[route].items()))}")
    missing = {
        route: sorted(form for form in forms_ if not accepted[route][form])
        for route, forms_ in REACH.items()
    }
    assert not any(missing.values()), missing


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
