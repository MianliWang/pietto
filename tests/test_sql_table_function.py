"""Bounded table-function emission: exact PostgreSQL SQL and MySQL refusal.

A `generate_series` input is one generated CTE read by its body. Its call is
alone in that CTE's FROM, written schema-qualified with each fixed argument CAST
to `pg_catalog.int8`, so the one admitted overload is fixed by the SQL itself
and its binding is its alias and only column. The plan, emission and byte
verifiers re-derive the function identity, the three values and the row bound
from the authored call. MySQL has no such function in this phase.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_values as valuing
from pietto._project import project_sql_plan_values as valuesplan
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_verification import (
    verify_row_bytes,
    verify_row_query,
)

PG_LHS = '"public"."phase66 lhs é"'


def _series(start: int, stop: int, step: int) -> str:
    return (
        "pg_catalog.generate_series("
        f"CAST({start} AS pg_catalog.int8), CAST({stop} AS pg_catalog.int8), "
        f'CAST({step} AS pg_catalog.int8)) AS "n"("n")'
    )


def _emit(tmp_path: Path, target: str, body: str, policy="preserve_literals"):
    item = probe.join_witness(target, body, policy=policy)
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return checked, outcome, json.loads(serialize_project_sql_emission(outcome))


TOP = "query result:\n    from generate_series(1, 3, 1) as n\n    select:\n        n\n"
WHERE = (
    "query result:\n    from generate_series(1, 10, 2) as n\n    where n > 3\n"
    "    select:\n        m = n.n\n"
)
LET_DESCENDING = (
    "query result:\n    let s:\n        from generate_series(3, 1, -1) as n\n"
    "        select:\n            n\n    from s\n    select:\n        n\n"
)
# The series on either side of a JOIN with a physical source.
LET_JOIN = (
    "query result:\n    let s:\n        from generate_series(1, 2, 1) as n\n"
    "        select:\n            n\n    from lhs\n    inner join s as t:\n"
    "        from lhs\n        on lhs.id == t.n\n    select:\n        a = lhs.id\n"
    "        b = t.n\n"
)
LEFT_JOIN = (
    "query result:\n    from generate_series(1, 2, 1) as n\n"
    "    inner join lhs as l:\n        from n\n        on n.n == l.id\n"
    "    select:\n        a = n.n\n        b = l.id\n"
)
BODIES = {
    "top": TOP,
    "where": WHERE,
    "let_descending": LET_DESCENDING,
    "let_join": LET_JOIN,
    "left_join": LEFT_JOIN,
}
EXPECTED = {
    "top": (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 3, 1)}) '
        'SELECT "s0"."c0" AS "n" FROM "p0" AS "s0"'
    ),
    "where": (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 10, 2)}), '
        '"p1" ("c0") AS (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0" '
        'WHERE ("s0"."c0" > CAST(3 AS pg_catalog.int8))) '
        'SELECT "t1"."c0" AS "m" FROM "p1" AS "t1"'
    ),
    "let_descending": (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(3, 1, -1)}), '
        '"p1" ("c0") AS (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0") '
        'SELECT "s1"."c0" AS "n" FROM "p1" AS "s1"'
    ),
    "let_join": (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 2, 1)}), '
        '"p1" ("c0") AS (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0"), '
        '"p2" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" '
        f'FROM {PG_LHS} AS "m0" INNER JOIN "p1" AS "m1" '
        'ON ("m0"."order.id" = "m1"."c0")) '
        'SELECT "t0"."c0" AS "a", "t0"."c2" AS "b" FROM "p2" AS "t0"'
    ),
    "left_join": (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 2, 1)}), '
        '"p1" ("c0", "c1", "c2") AS (SELECT "m0"."c0" AS "c0", '
        '"m1"."order.id" AS "c1", "m1"."key value" AS "c2" '
        f'FROM "p0" AS "m0" INNER JOIN {PG_LHS} AS "m1" '
        'ON ("m0"."c0" = "m1"."order.id")) '
        'SELECT "t0"."c0" AS "a", "t0"."c1" AS "b" FROM "p1" AS "t0"'
    ),
}


@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_a_series_emits_exact_qualified_postgres_sql(tmp_path: Path, case: str) -> None:
    _, outcome, document = _emit(tmp_path, "postgres", BODIES[case])
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == EXPECTED[case]
    # The independent public decoder re-derives every token, value and bound.
    probe.decode_public(serialize_project_sql_emission(outcome))
    # Bind-safe binds ordinary literals; the three arguments stay fixed.
    _, bound_outcome, bound = _emit(
        tmp_path / "bind", "postgres", BODIES[case], "bind_safe_literals"
    )
    assert bound["status"] == "VERIFIED", bound
    assert len(bound["fixed_values"]) == (1 if case == "where" else 0)
    assert bound["sql"] == EXPECTED[case].replace(
        "> CAST(3 AS pg_catalog.int8)", "> CAST($1 AS pg_catalog.int8)"
    )
    probe.decode_public(serialize_project_sql_emission(bound_outcome))


def test_the_published_evidence_names_identity_values_and_rows(tmp_path: Path) -> None:
    _, _, document = _emit(tmp_path, "postgres", LET_DESCENDING)
    evidence = [
        (r["kind"], r["rule"], r["evidence"])
        for r in document["requirements"]
        if r["kind"] in {"table_function", "values_column"}
    ]
    assert evidence == [
        (
            "table_function",
            "R04",
            [
                {
                    "arguments": ["3", "1", "-1"],
                    "function": "pg_catalog.generate_series("
                    "pg_catalog.int8,pg_catalog.int8,pg_catalog.int8)",
                    "rows": 3,
                }
            ],
        ),
        ("values_column", "R02", [{"nullable": False, "position": 0, "tag": "Int"}]),
    ]


@pytest.mark.parametrize(
    ("case", "line"), (("top", 7), ("let_join", 8), ("left_join", 7))
)
def test_mysql_refuses_a_series_alone_or_joined(
    tmp_path: Path, case: str, line: int
) -> None:
    _, _, document = _emit(tmp_path, "mysql", BODIES[case])
    assert document["status"] == "BLOCKED"
    assert [
        (
            b["code"],
            b["subject"]["detail"],
            b["subject"]["reference"],
            b["location"]["line"],
            b["location"]["column"],
        )
        for b in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "table_function_not_admitted_on_target",
            {"kind": "values_body", "position": 0},
            line,
            5 if line == 7 else 9,
        )
    ]


def _verified_plan(tmp_path: Path, monkeypatch, change=None):
    """Build and verify the WHERE witness, optionally through a forging builder."""
    if change is not None:
        original = valuesplan.build_body

        def forged(definition, ref, port):
            body, columns, outputs = original(definition, ref, port)
            return replace(body, **change(body)), columns, outputs

        monkeypatch.setattr(valuesplan, "build_body", forged)
    checked, _, _ = _emit(tmp_path, "postgres", WHERE)
    return checked


@pytest.mark.parametrize(
    "change",
    (
        # A different, equally valid series: its own arguments and row count.
        lambda body: {"arguments": (1, 12, 2), "row_count": 6},
        lambda body: {"arguments": (10, 1, -2), "row_count": 5},
        # The right values with an off-by-one bound or another overload.
        lambda body: {"row_count": body.row_count + 1},
        lambda body: {
            "function": body.function.replace("int8", "int4"),
        },
        lambda body: {"function": None, "arguments": (), "row_count": None},
    ),
)
def test_the_plan_verifier_rederives_the_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change
) -> None:
    # The unforged witness verifies in test_a_series_emits_exact_qualified_postgres_sql.
    assert not _verified_plan(tmp_path, monkeypatch, change).verified


_BUILD_UNIT = valuing.build_values_unit


def _blockers(document: dict) -> list[tuple[str, dict, Any]]:
    return [
        (b["code"], b["subject"], b["location"]) for b in document.get("blockers", ())
    ]


def _forged_unit(tmp_path: Path, monkeypatch, body: str, change) -> dict:
    """Emit `body` with each zero-input unit the builder makes passed through
    `change`, so the changed unit is the one rendered, required and verified."""

    def forged(*arguments, **keywords):
        unit, problem = _BUILD_UNIT(*arguments, **keywords)
        return (None if unit is None else replace(unit, **change(unit))), problem

    monkeypatch.setattr(valuing, "build_values_unit", forged)
    _, _, document = _emit(tmp_path, "postgres", body)
    return document


CORRESPONDENCE = [
    (
        "PIE-B1008",
        {
            "detail": "plan_ast_correspondence",
            "reference": {"kind": "selected_plan", "position": 0},
        },
        None,
    )
]


def test_the_emission_verifier_rejects_a_series_unit_the_builder_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each change is rendered and required consistently, so only the unit's
    independent re-derivation from the plan and the authored call refuses it;
    the unchanged control through the same builder verifies."""
    control = _forged_unit(tmp_path / "control", monkeypatch, LET_JOIN, lambda u: {})
    assert (control["status"], control["sql"]) == ("VERIFIED", EXPECTED["let_join"])
    for position, change in enumerate(
        (
            # Another valid series, a different start, another overload, alias
            # or column type, and no function at all.
            lambda u: {"arguments": (1, 3, 1)},
            lambda u: {"arguments": (2, 1, 1)},
            lambda u: {"function": u.function.replace("int8", "int4")},
            lambda u: {"scope": replace(u.scope, name="m")},
            lambda u: {"function": None, "arguments": ()},
            lambda u: {"columns": (replace(u.columns[0], physical="pg_int4"),)},
        )
    ):
        document = _forged_unit(tmp_path / str(position), monkeypatch, LET_JOIN, change)
        assert (document["status"], _blockers(document)) == (
            "BLOCKED",
            CORRESPONDENCE,
        ), position


LET_VALUES = (
    "query result:\n    let seed:\n        values(id: Int not null):\n"
    "            7\n            8\n            9\n    from seed\n    select:\n"
    "        id\n"
)


def test_a_values_unit_cannot_pass_as_a_series(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One non-null Int column of three rows has a series' node count, so only
    the VALUES unit's own function fields tell the two apart."""
    control = _forged_unit(tmp_path / "control", monkeypatch, LET_VALUES, lambda u: {})
    assert control["status"] == "VERIFIED"
    assert "generate_series" not in control["sql"] and "VALUES" in control["sql"]
    for position, change in enumerate(
        (
            lambda u: {"function": valuing.SERIES_IDENTITY, "arguments": (1, 1000, 1)},
            lambda u: {"function": valuing.SERIES_IDENTITY},
            lambda u: {"arguments": (7, 9, 1)},
        )
    ):
        document = _forged_unit(
            tmp_path / str(position), monkeypatch, LET_VALUES, change
        )
        assert (document["status"], _blockers(document)) == (
            "BLOCKED",
            CORRESPONDENCE,
        ), position


def test_the_byte_verifier_rederives_every_series_token(tmp_path: Path) -> None:
    _, outcome, document = _emit(tmp_path, "postgres", LET_JOIN)
    assert document["status"] == "VERIFIED"
    artifact = cast(Any, outcome.artifact)
    query = artifact.ast
    assert verify_row_query(artifact.request, query)
    assert verify_row_bytes(query, artifact.rendered)
    for old, new in (
        (b"CAST(2 AS", b"CAST(3 AS"),
        (b"pg_catalog.generate_series", b"generate_series"),
        (b'CAST(1 AS pg_catalog.int8)) AS "n"', b'CAST(1 AS pg_catalog.int4)) AS "n"'),
        (b'AS "n"("n")', b'AS "n"("m")'),
    ):
        tampered = replace(
            artifact.rendered, sql=artifact.rendered.sql.replace(old, new, 1)
        )
        assert tampered.sql != artifact.rendered.sql
        assert not verify_row_bytes(query, tampered)


@pytest.mark.parametrize("length", (63, 64))
def test_a_binding_postgres_cannot_spell_is_blocked_at_its_call(
    tmp_path: Path, length: int
) -> None:
    """The binding is the CTE body's alias and column: 63 bytes is the most a
    PostgreSQL identifier holds, so a longer one is a representation blocker
    at the call, not a correspondence failure."""
    name = "n" * length
    body = (
        f"query result:\n    from generate_series(1, 3, 1) as {name}\n"
        f"    select:\n        m = {name}\n"
    )
    _, _, document = _emit(tmp_path, "postgres", body)
    if length == 63:
        assert document["status"] == "VERIFIED", document
        assert f'AS "{name}"("{name}")' in document["sql"]
        return
    assert document["status"] == "BLOCKED"
    assert [
        (
            b["code"],
            b["subject"],
            (b["location"]["line"], b["location"]["column"]),
        )
        for b in document["blockers"]
    ] == [
        (
            "PIE-B1002",
            {
                "detail": "table_function_binding_unrepresentable",
                "reference": {"kind": "values_body", "position": 0},
            },
            (7, 5),
        )
    ]


@pytest.mark.parametrize(
    ("target", "code", "reason", "detail"),
    (
        (
            "postgres",
            "PIE-B1002",
            "REPRESENTATION",
            "table_function_binding_unrepresentable",
        ),
        (
            "mysql",
            "PIE-B1003",
            "UNSUPPORTED_RULE",
            "table_function_not_admitted_on_target",
        ),
    ),
)
def test_every_refused_call_is_blocked_at_its_own_input_in_source_order(
    tmp_path: Path, target: str, code: str, reason: str, detail: str
) -> None:
    """Each binding PostgreSQL cannot spell, and on MySQL each call, is its own
    blocker at its own input. The let written first joins the later one, so it
    is planned second: the blockers still follow the source."""
    first, second = "a" * 64, "b" * 64
    body = (
        f"query result:\n    let s:\n        from generate_series(1, 2, 1) as {first}\n"
        f"        inner join u as t:\n            from {first}\n"
        f"            on {first}.{first} == t.w\n"
        f"        select:\n            v = {first}.{first}\n"
        f"    let u:\n        from generate_series(1, 2, 1) as {second}\n"
        f"        select:\n            w = {second}\n"
        "    from s\n    select:\n        v\n"
    )
    _, _, document = _emit(tmp_path, target, body)
    assert document["status"] == "BLOCKED"
    assert document["diagnostics"] == []
    assert document["blockers"] == [
        {
            "code": code,
            "reason": reason,
            "subject": {
                "reference": {"kind": "values_body", "position": position},
                "detail": detail,
            },
            "location": {
                "path": "main.pietto",
                "line": line,
                "column": 9,
                "end_line": line,
                "end_column": 106,
            },
            "related": [],
        }
        for position, line in ((1, 8), (0, 15))
    ]


@pytest.mark.parametrize("grouped", (True, False))
def test_a_series_read_through_a_let_can_be_aggregated(
    tmp_path: Path, grouped: bool
) -> None:
    """Aggregating directly over the input is PIE-S2333 for now; through a let
    the series is an ordinary named producer."""
    group = "    group by:\n        n\n" if grouped else ""
    select = "        n\n        c = count()\n" if grouped else "        c = count()\n"
    body = (
        "query result:\n    let s:\n        from generate_series(1, 5, 1) as n\n"
        "        select:\n            n\n    from s\n"
        + group
        + "    select:\n"
        + select
    )
    _, outcome, document = _emit(tmp_path, "postgres", body)
    assert document["status"] == "VERIFIED", document
    assert document["sql"].startswith(
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 5, 1)}), '
    )
    probe.decode_public(serialize_project_sql_emission(outcome))


SERIES_READS = (
    "query result:\n    let s:\n        from generate_series(1, 3, 1) as n\n"
    "        select:\n            n\n    from lhs\n"
    "    where exists s and id in s and id not in s\n"
    "    select:\n        a = lhs.id\n"
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_series_let_is_read_by_exists_and_in(tmp_path: Path, target: str) -> None:
    """A let over a series is one read block: PostgreSQL emits it once and
    reads it as a subquery per read; MySQL blocks its one input."""
    _, outcome, document = _emit(tmp_path, target, SERIES_READS)
    if target == "mysql":
        assert document["status"] == "BLOCKED"
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in document["blockers"]
        ] == [("PIE-B1003", "table_function_not_admitted_on_target", 8)]
        return
    assert document["status"] == "VERIFIED", document
    sql = document["sql"]
    assert sql.count("generate_series") == 1
    plain = sql.replace('"', "")
    assert "EXISTS (SELECT 1 FROM p1 AS e0)" in plain
    assert "IN (SELECT e1.c0 FROM p1 AS e1)" in plain
    assert "NOT IN (SELECT e2.c0 FROM p1 AS e2)" in plain
    probe.decode_public(serialize_project_sql_emission(outcome))


# A let with capture lines reads a series through another let, and a body over
# a series may capture the binding of its JOIN (by `exists` or LATERAL); the
# series stays the CTE its own body reads. MySQL blocks the series input.
CAPTURED_SERIES = {
    "own_from_series": """query result:
    let s:
        from generate_series(1, 3, 1) as n
        select:
            n
    let m:
        capture lhs
        from s
        where s.n <= lhs.id
        select:
            n
    from lhs
    where exists m
    select:
        a = lhs.id
""",
    "join_binding_exists": """query result:
    let m:
        capture l
        from rhs
        where rhs.id == l.id
        select:
            id
    from generate_series(1, 3, 1) as n
    inner join lhs as l:
        from n
        on n.n == l.id
    where exists m
    select:
        a = n.n
""",
    "join_binding_lateral": """query result:
    let m:
        capture l
        from rhs
        where rhs.id == l.id
        select:
            id
    from generate_series(1, 3, 1) as n
    left join lhs as l:
        from n
        on n.n == l.id
    cross join m as o:
        from l
    select:
        a = n.n
        b = o.id
""",
}
CAPTURED_SERIES_SQL = {
    ("own_from_series", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT "n"."n" FROM '
        "pg_catalog.generate_series(CAST(1 AS pg_catalog.int8), CAST(3 AS "
        'pg_catalog.int8), CAST(1 AS pg_catalog.int8)) AS "n"("n")), "p1" '
        '("c0") AS (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0"), "p2" '
        '("c0", "c1") AS (SELECT "s2"."order.id" AS "c0", "s2"."key value" '
        'AS "c1" FROM "public"."phase66 lhs é" AS "s2" WHERE EXISTS (SELECT '
        '1 FROM (SELECT "t2"."c0" AS "c0" FROM (SELECT "s1"."c0" AS "c0" '
        'FROM "p1" AS "s1" WHERE ("s1"."c0" <= "s2"."order.id")) AS "t2") '
        'AS "e0")) SELECT "t4"."c0" AS "a" FROM "p2" AS "t4"'
    ),
    ("join_binding_exists", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT "n"."n" FROM '
        "pg_catalog.generate_series(CAST(1 AS pg_catalog.int8), CAST(3 AS "
        'pg_catalog.int8), CAST(1 AS pg_catalog.int8)) AS "n"("n")), "p1" '
        '("c0", "c1", "c2") AS (SELECT "m0"."c0" AS "c0", "m1"."order.id" '
        'AS "c1", "m1"."key value" AS "c2" FROM "p0" AS "m0" INNER JOIN '
        '"public"."phase66 lhs é" AS "m1" ON ("m0"."c0" = '
        '"m1"."order.id")), "p2" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS '
        '"c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2" FROM "p1" AS "t0" WHERE '
        'EXISTS (SELECT 1 FROM (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s0" WHERE ("s0"."order.id" = '
        '"t0"."c1")) AS "t1") AS "e0")) SELECT "t3"."c0" AS "a" FROM "p2" '
        'AS "t3"'
    ),
    ("join_binding_lateral", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT "n"."n" FROM '
        "pg_catalog.generate_series(CAST(1 AS pg_catalog.int8), CAST(3 AS "
        'pg_catalog.int8), CAST(1 AS pg_catalog.int8)) AS "n"("n")), "p1" '
        '("c0", "c1", "c2") AS (SELECT "m0"."c0" AS "c0", "m1"."order.id" '
        'AS "c1", "m1"."key value" AS "c2" FROM "p0" AS "m0" LEFT JOIN '
        '"public"."phase66 lhs é" AS "m1" ON ("m0"."c0" = '
        '"m1"."order.id")), "p2" ("c0", "c1", "c2", "c3") AS (SELECT '
        '"m2"."c0" AS "c0", "m2"."c1" AS "c1", "m2"."c2" AS "c2", "m3"."c0" '
        'AS "c3" FROM "p1" AS "m2" CROSS JOIN LATERAL (SELECT "t1"."c0" AS '
        '"c0" FROM (SELECT "s0"."order.id" AS "c0", "s0"."key value" AS '
        '"c1" FROM "public"."phase66 rhs é" AS "s0" WHERE ("s0"."order.id" '
        '= "m2"."c1")) AS "t1") AS "m3") SELECT "t0"."c0" AS "a", "t0"."c3" '
        'AS "b" FROM "p2" AS "t0"'
    ),
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", sorted(CAPTURED_SERIES))
def test_a_capturing_let_composes_with_a_series(
    tmp_path: Path, target: str, shape: str
) -> None:
    _, outcome, document = _emit(tmp_path, target, CAPTURED_SERIES[shape])
    if target == "mysql":
        assert document["status"] == "BLOCKED"
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in document["blockers"]
        ] == [
            (
                "PIE-B1003",
                "table_function_not_admitted_on_target",
                8 if shape == "own_from_series" else 13,
            )
        ]
        return
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == CAPTURED_SERIES_SQL[shape, target]


ORDERED_READ_BESIDE_SERIES = {
    "series_first": (
        "table t:\n    from generate_series(1, 3, 1) as n\n    select:\n"
        "        n\nquery result:\n    let c:\n        capture lhs\n"
        "        from rhs\n        where rhs.id == lhs.id\n        select:\n"
        "            id\n        order by:\n            id\n        limit 1\n"
        "    from lhs\n    where id in c and exists t\n    select:\n        id\n"
    ),
    "series_later": (
        "query result:\n    let c:\n        capture lhs\n        from rhs\n"
        "        where rhs.id == lhs.id\n        select:\n            id\n"
        "        order by:\n            id\n        limit 1\n"
        "    let s:\n        from generate_series(1, 3, 1) as n\n"
        "        select:\n            n\n    from lhs\n    where exists s\n"
        "    select:\n        id\n        x = scalar c.id\n"
    ),
}


@pytest.mark.parametrize("shape", sorted(ORDERED_READ_BESIDE_SERIES))
def test_mysql_refuses_ordered_reads_beside_a_refused_series(
    tmp_path: Path, shape: str
) -> None:
    """D70.05: the refused series is not realized, but the `scalar` and `in`
    reads of a let ending in ORDER BY and LIMIT are refused too, each at its
    own read, in one source order with the series input."""
    _, _, document = _emit(tmp_path, "mysql", ORDERED_READ_BESIDE_SERIES[shape])
    assert document["status"] == "BLOCKED"
    ordered = "mysql_correlated_order_or_limit_read_not_admitted"
    series = "table_function_not_admitted_on_target"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"])
        for b in document["blockers"]
    ] == (
        [("PIE-B1003", series, 7), ("PIE-B1003", ordered, 21)]
        if shape == "series_first"
        else [("PIE-B1003", series, 17), ("PIE-B1003", ordered, 24)]
    )


# Phase70 S16: a series let LEFT JOINed with a VALUES let reads no physical
# relation, so it is emitted against a contract without sources (compile_query
# refuses an unread contract source): PostgreSQL emits both as CTEs and keeps
# the series arguments and VALUES cells fixed; MySQL blocks the one
# table-function input.
SERIES_VALUES_JOIN = (
    "query result:\n    let s:\n        from generate_series(1, 3, 1) as n\n"
    "        select:\n            n\n"
    "    let seed:\n        values(id: Int not null, label: Text nullable):\n"
    '            1, "a"\n            3, null\n'
    "    from s\n    left join seed as v:\n        from s\n        on s.n == v.id\n"
    "    select:\n        n\n        label = v.label\n"
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_series_let_joins_a_values_let_without_a_physical_source(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, SERIES_VALUES_JOIN)
    contract = json.loads(item["contract"])
    contract["sources"] = []
    _, outcome = probe.build_case(
        tmp_path, item["source"], probe.encoded(contract).decode(), item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "mysql":
        assert document["status"] == "BLOCKED" and "sql" not in document
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in document["blockers"]
        ] == [("PIE-B1003", "table_function_not_admitted_on_target", 8)]
        return
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == (
        f'WITH "p0" ("c0") AS (SELECT "n"."n" FROM {_series(1, 3, 1)}), '
        '"p1" ("c0", "c1") AS (VALUES (CAST(1 AS pg_catalog.int8), '
        "CAST(E'\\141' AS pg_catalog.text) COLLATE \"C\"), (CAST(3 AS "
        'pg_catalog.int8), CAST(NULL AS pg_catalog.text) COLLATE "C")), '
        '"p2" ("c0") AS (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0"), '
        '"p3" ("c0", "c1", "c2") AS (SELECT "m0"."c0" AS "c0", "m1"."c0" AS '
        '"c1", "m1"."c1" AS "c2" FROM "p2" AS "m0" LEFT JOIN "p1" AS "m1" ON '
        '("m0"."c0" = "m1"."c0")) SELECT "t0"."c0" AS "n", "t0"."c2" AS "label" '
        'FROM "p3" AS "t0"'
    )
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("n", False),
        ("label", True),
    ]
    assert outcome.artifact is not None and outcome.artifact.request.sources == ()
    probe.decode_public(serialize_project_sql_emission(outcome))
