"""`first` and `last` in SQL (Phase74 S12): PostgreSQL writes the first element
of an ordered `ARRAY_AGG`, `last` with every key direction flipped, in single
files and projects; MySQL has no ordered first or last yet and refuses both.

Project verdicts are the independent public consumer's over the published
bytes."""

from __future__ import annotations

import json

import pytest

import _pietto_sql_emission as probe
from pietto import cli
from pietto._project.project_sql_emission import serialize_project_sql_emission

FILE = """shape Sale:
    id: Int
    shop_id: Int
    plant: Text
    pot: Text | None
    price_cents: Int
    weight: Float | None
    sold_at: Timestamp
    sale_key = unique(id)
source sales: Sale = {target}.table("nursery.sales")
"""


def _emit_file(tmp_path, capsys, target: str, body: str) -> dict:
    path = tmp_path / "main.pietto"
    path.write_text(FILE.format(target=target) + body)
    cli.main(["emit-sql", "--dialect", target, str(path), "--format", "json"])
    return json.loads(capsys.readouterr().out)


def test_postgres_writes_the_first_element_of_an_ordered_array_agg(
    tmp_path, capsys
) -> None:
    document = _emit_file(
        tmp_path,
        capsys,
        "postgres",
        "query q:\n    from sales\n    let t = sold_at\n"
        "    where weight is not None\n    group by shop_id\n    select:\n"
        "        shop_id\n        earliest = first(pot, order by t, id)\n"
        "        latest = last(plant, order by sold_at, id)\n"
        "        priciest = first(plant, order by price_cents desc, id)\n"
        "        lightest = last(plant, order by weight desc, sales.id)\n",
    )

    assert document["diagnostics"] == []
    assert [artifact["sql"] for artifact in document["artifacts"]] == [
        "SELECT\n"
        '    "shop_id" AS "shop_id",\n'
        '    (ARRAY_AGG("pot" ORDER BY "sold_at" ASC, "id" ASC))[1] AS "earliest",\n'
        '    (ARRAY_AGG("plant" ORDER BY "sold_at" DESC, "id" DESC))[1] AS "latest",\n'
        '    (ARRAY_AGG("plant" ORDER BY "price_cents" DESC, "id" ASC))[1] '
        'AS "priciest",\n'
        '    (ARRAY_AGG("plant" ORDER BY "weight" ASC, "sales"."id" DESC))[1] '
        'AS "lightest"\n'
        'FROM "nursery"."sales" AS "sales"\n'
        'WHERE "weight" IS NOT NULL\n'
        "GROUP BY\n"
        '    "shop_id"'
    ]


def test_postgres_first_over_a_whole_input_is_one_row(tmp_path, capsys) -> None:
    document = _emit_file(
        tmp_path,
        capsys,
        "postgres",
        "query q:\n    from sales\n    select:\n"
        "        latest = last(plant, order by sold_at, id)\n        n = count()\n",
    )

    assert [artifact["sql"] for artifact in document["artifacts"]] == [
        "SELECT\n"
        '    (ARRAY_AGG("plant" ORDER BY "sold_at" DESC, "id" DESC))[1] AS "latest",\n'
        '    COUNT(*) AS "n"\n'
        'FROM "nursery"."sales"'
    ]


def test_postgres_orders_by_an_enum_key_as_a_relation_does(tmp_path, capsys) -> None:
    """An order key may be any direct field a relation ORDER BY takes, an enum
    included, as for `string_agg`."""
    document = _emit_file(
        tmp_path,
        capsys,
        "postgres",
        "enum Grade:\n    low\n    high\nshape Pot:\n    id: Int\n"
        "    shop_id: Int\n    plant: Text\n    grade: Grade\n"
        '    pot_key = unique(id)\nsource pots: Pot = postgres.table("nursery.pots")\n'
        "query q:\n    from pots\n    group by shop_id\n    select:\n"
        "        shop_id\n        a = first(plant, order by grade, id)\n",
    )

    assert document["diagnostics"] == []
    assert [artifact["sql"] for artifact in document["artifacts"]] == [
        "SELECT\n"
        '    "shop_id" AS "shop_id",\n'
        '    (ARRAY_AGG("plant" ORDER BY "grade" ASC, "id" ASC))[1] AS "a"\n'
        'FROM "nursery"."pots"\n'
        "GROUP BY\n"
        '    "shop_id"'
    ]


def test_mysql_has_no_ordered_first_or_last_yet(tmp_path, capsys) -> None:
    document = _emit_file(
        tmp_path,
        capsys,
        "mysql",
        "query q:\n    from sales\n    group by shop_id\n    select:\n"
        "        shop_id\n        latest = last(plant, order by sold_at, id)\n",
    )

    assert document["artifacts"] == []
    assert [
        (row["code"], row["location"]["line"], row["message"])
        for row in document["diagnostics"]
    ] == [
        (
            "PIE-B1000",
            FILE.count("\n") + 1,
            "MySQL SQL emission is not implemented for RelationIR: q. MySQL has no "
            "ordered first or last yet; emit with --dialect postgres",
        )
    ]


def _emit_project(tmp_path, target: str, body: str):
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    _, outcome = probe.build_case(
        tmp_path,
        probe.AGGREGATE_HEADER.format(target=target) + body,
        item["contract"],
        item["policy"],
    )
    return outcome


def _public(outcome) -> dict:
    return probe.decode_public(serialize_project_sql_emission(outcome))


def _column(data: dict, label: str) -> dict:
    (found,) = (item for item in data["columns"] if item["label"] == label)
    return found


@pytest.mark.parametrize("grouped", [True, False])
def test_a_project_writes_first_and_last_as_a_file_does(tmp_path, grouped) -> None:
    """The value keeps its carrier; it may be None where it is, or for an
    empty input without GROUP BY. A Float key orders by its real value."""
    keys = (
        "    group by label\n    select:\n        label\n"
        if grouped
        else ("    select:\n")
    )
    outcome = _emit_project(
        tmp_path,
        "postgres",
        "query result:\n    from agg\n"
        + keys
        + "        f = first(amount, order by ratio desc, rid)\n"
        "        l = last(value, order by rid)\n",
    )

    assert outcome.status == "VERIFIED", outcome.blockers
    data = _public(outcome)
    assert _column(data, "f")["representation"] == {
        "storage": {"kind": "pg_numeric", "precision": 9, "scale": 2},
        "nullable": not grouped,
        "domain": {"kind": "decimal", "precision": 9, "scale": 2},
    }
    assert _column(data, "l")["representation"]["nullable"] is True
    assert (
        '(ARRAY_AGG("s0"."amount value" ORDER BY "s0"."ratio value" DESC, '
        '"s0"."row id" ASC))[1] AS "c'
    ) in data["sql"]
    assert (
        '(ARRAY_AGG("s0"."value é" ORDER BY "s0"."row id" DESC))[1] AS "c'
        in (data["sql"])
    )
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [[], []]
    from pietto._project import project_sql_emission_portable as portable

    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


def test_a_mysql_project_refuses_first_and_last(tmp_path) -> None:
    outcome = _emit_project(
        tmp_path,
        "mysql",
        "query result:\n    from agg\n    group by label\n    select:\n"
        "        label\n        f = first(amount, order by rid)\n"
        "        l = last(value, order by rid)\n",
    )

    data = _public(outcome)
    assert data["status"] == "BLOCKED"
    line = probe.AGGREGATE_HEADER.count("\n") + 6
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "first_last_not_admitted_on_target",
            row,
            "Emit this first or last for PostgreSQL, or keep it in check/plan: "
            "MySQL has no ordered first or last yet.",
        )
        for row in (line, line + 1)
    ]
