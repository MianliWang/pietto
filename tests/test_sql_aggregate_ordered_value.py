"""`first` and `last` in SQL (Phase74 S12): PostgreSQL writes the first element
of an ordered `ARRAY_AGG`, `last` with every key direction flipped, in single
files and projects. A MySQL single file refuses both; a MySQL project writes
them over a ROW_NUMBER derived table in the Phase77 S13 statement class only.

Project verdicts are the independent public consumer's over the published
bytes, except the MySQL S13 forms, which emission, its verifier, compiled
replay and the pure observation boundary each judge from their own input; a
relation alias leaves no trace past the plan, and the pure boundary has no
header parameter."""

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


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("body", "code"),
    (
        (
            "query q:\n    from sales\n    select:\n        rest = weight % 0.1\n",
            "PIE-B1000",
        ),
        (
            "query q:\n    from sales\n    select:\n        rest = 1.0 % 0.1\n",
            "PIE-B1000",
        ),
        (
            "query q:\n    from sales\n    select:\n        rest = -0.0 % 0.1\n",
            "PIE-B1000",
        ),
        (
            "query q:\n    from sales\n    select:\n        rest = weight % 0.0\n",
            "PIE-B1000",
        ),
        (
            "query q:\n    from sales\n    select:\n        total = count(weight % 0.1)\n",
            "PIE-B1000",
        ),
        (
            "def remainder(x: Float) -> Float: return x % 0.1\n"
            "query q:\n    from sales\n    select:\n        rest = remainder(weight)\n",
            None,
        ),
    ),
)
def test_single_file_float_remainder_remains_target_refused(
    tmp_path, capsys, target, body, code
):
    """E5's exact Float remainder is project-only until each target qualifies."""
    document = _emit_file(
        tmp_path,
        capsys,
        target,
        body,
    )

    assert document["artifacts"] == []
    assert document["diagnostics"]
    if code is not None:
        assert any(item["code"] == code for item in document["diagnostics"])


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
    import _pietto_sql_emission_portable as portable

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
            "this first or last form is not admitted on MySQL yet.",
        )
        for row in (line, line + 1)
    ]


# Phase77 S13: MySQL `first` and `last` in the forms of the raw MySQL 8.4.12
# qualification (wave-b s13, campaign-20261111T1636Z).
RANKED_FIELDS = (
    ("id", "Int", "row id", False),
    ("shop", "Int", "shop id", False),
    ("a", "Int", "order a", True),
    ("b", "Int", "order b", True),
    ("t", "Text", "order t", True),
    ("v_int", "Int", "v int", True),
    ("v_float", "Float", "v float", True),
    ("v_text", "Text", "v text", True),
    ("v_decimal", "Decimal(65, 30)", "v decimal", True),
    ("v_bool", "Bool", "v bool", True),
    ("v_date", "Date", "v date", True),
    ("v_ts", "Timestamp", "v ts", True),
    ("v_uuid", "UUID", "v uuid", True),
    ("n_int", "Int", "n int", False),
    ("n_float", "Float", "n float", False),
    ("n_text", "Text", "n text", False),
    ("v_name", "Text", "vé", True),
    ("n_small", "Int", "n small", False),
    ("v_dec9", "Decimal(9, 2)", "v dec9", True),
    ("v_wide", "Text", "v wide", True),
)
# MySQL carriers the qualification did not use: INT, VARCHAR(255).
RANKED_MYSQL_CARRIERS = {
    "n_small": {
        "storage": {"kind": "my_int"},
        "domain": {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
    },
    "v_wide": {
        "storage": {"kind": "my_varchar", "length": 255},
        "domain": {
            "kind": "text",
            "max_characters": 255,
            "encoding": "utf8mb4",
            "collation": "utf8mb4_0900_bin",
            "padding": "NO PAD",
        },
    },
}
RANKED_HEADER = (
    "shape Row:\n"
    + "".join(
        f"    {name}: {logical}{' | None' if nullable else ''}\n"
        for name, logical, _, nullable in RANKED_FIELDS
    )
    + "    row_key = unique(id)\n"
    + 'source rows: Row = {target}.table("opaque.locator.not.sql")\n'
)
RANKED_LINE = RANKED_HEADER.count("\n")


def _ranked_representation(target: str, logical: str) -> dict:
    postgres = target == "postgres"
    text = (
        {"kind": "pg_text"},
        {"encoding": "UTF8", "collation": "C"},
    )
    if not postgres:
        text = (
            {"kind": "my_varchar", "length": 64},
            {"encoding": "utf8mb4", "collation": "utf8mb4_0900_bin"},
        )
    storage, domain = {
        "Int": (
            {"kind": "pg_int8" if postgres else "my_bigint"},
            {
                "kind": "int_range",
                "min": "-9007199254740993",
                "max": "9007199254740993",
            },
        ),
        "Float": (
            {"kind": "pg_float8" if postgres else "my_double"},
            {"kind": "finite_float", "format": "binary64"},
        ),
        "Text": (
            text[0],
            {"kind": "text", "max_characters": 64, **text[1], "padding": "NO PAD"},
        ),
        "Decimal(65, 30)": (
            {"kind": "pg_numeric" if postgres else "my_decimal"}
            | {"precision": 65, "scale": 30},
            {"kind": "decimal", "precision": 65, "scale": 30},
        ),
        "Decimal(9, 2)": (
            {"kind": "pg_numeric" if postgres else "my_decimal"}
            | {"precision": 9, "scale": 2},
            {"kind": "decimal", "precision": 9, "scale": 2},
        ),
        "Bool": ({"kind": "pg_bool" if postgres else "my_bool01"}, {"kind": "bool01"}),
        "Date": ({"kind": "pg_date" if postgres else "my_date"}, {"kind": "date"}),
        "Timestamp": (
            {"kind": "pg_timestamp" if postgres else "my_datetime"}
            | {"fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "UUID": (
            {"kind": "pg_uuid" if postgres else "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
    }[logical]
    return {"storage": storage, "domain": domain}


def _ranked(directory, target: str, body: str, *, limits=None):
    """One query ``result`` over a source of every first/last carrier, under
    the statement's resource ``limits`` if given."""
    item = probe.parameterized_fixture(
        target, "query result:\n    from rows\n    select:\n        id\n"
    )
    contract = json.loads(item["contract"])
    (source,) = contract["sources"]
    source["fields"] = [
        {
            "column": column,
            "name": name,
            "ordinal": ordinal,
            "representation": {
                **(
                    RANKED_MYSQL_CARRIERS[name]
                    if target == "mysql" and name in RANKED_MYSQL_CARRIERS
                    else _ranked_representation(target, logical)
                ),
                "nullable": nullable,
            },
        }
        for ordinal, (name, logical, column, nullable) in enumerate(RANKED_FIELDS)
    ]
    if limits is not None:
        contract["environment"].append(
            {"key": "resource_limits", "scope": "statement", "value": limits}
        )
    _, outcome = probe.build_case(
        directory,
        RANKED_HEADER.format(target=target) + body,
        json.dumps(contract),
        item["policy"],
    )
    return outcome


def _query(select: str, *, where="", grouped=True, header="") -> str:
    return (
        f"query result{header}:\n    from rows\n"
        + (f"    where {where}\n" if where else "")
        + ("    group by shop\n    select:\n        shop\n" if grouped else "")
        + ("" if grouped else "    select:\n")
        + "".join(f"        {item}\n" for item in select.split("; "))
        + ("    order by shop\n" if grouped else "")
    )


RANKED_BODIES = {
    "grouped_where": _query(
        "fi = first(v_int, order by a, b desc, id); "
        "lt = last(v_text, order by a, b desc, id); "
        "fd = first(v_decimal, order by a, b desc, id); "
        "lf = last(v_float, order by a, b desc, id)",
        where="a is not None and b is not None",
    ),
    "grouped_parameter": _query(
        "fi = first(v_int, order by a, id)",
        where="a is not None and shop == g",
        header="(g: Int)",
    ),
    "global_parameter": _query(
        "fi = first(v_int, order by a, id); lt = last(v_text, order by a, id)",
        where="shop == g and a is not None",
        grouped=False,
        header="(g: Int)",
    ),
    "global": _query(
        "fi = first(v_int, order by id); lf = last(v_float, order by id)",
        grouped=False,
    ),
    "strict_keys": _query(
        "ls = last(v_text, order by n_int desc, id); "
        "fd = first(v_decimal, order by n_int desc, id)"
    ),
    "text_key": _query(
        "fi = first(v_int, order by t, id); ls = last(v_text, order by t asc, id)",
        where="t is not None",
    ),
}


@pytest.mark.parametrize("name", RANKED_BODIES)
def test_a_mysql_project_ranks_first_and_last_in_its_statement_class(
    tmp_path, name
) -> None:
    """Each reader admits the form from its own input and replays the SQL; the
    result keeps the value's carrier, nullable. PostgreSQL keeps ARRAY_AGG."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    body = RANKED_BODIES[name]
    outcome = _ranked(tmp_path / "mysql", "mysql", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql
    assert b"ROW_NUMBER() OVER (" in sql and b"ARRAY_AGG" not in sql
    assert verify_project_sql_emission(artifact, artifact.request).verified
    fields = {row[0]: row for row in RANKED_FIELDS}
    columns = json.loads(serialize_project_sql_emission(outcome))["columns"]
    for line in body.splitlines():
        if "first(" in line or "last(" in line:
            label, call = line.strip().split(" = ")
            value = fields[call.split("(")[1].split(",")[0]]
            (column,) = (c for c in columns if c["label"] == label)
            assert column["representation"] == {
                **_ranked_representation("mysql", value[1]),
                "nullable": True,
            }
    built = build_compiled(artifact)
    compiled = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    for template in (compiled, prepare_live_template(artifact)):
        values = tuple((parameter, 2) for parameter in template.parameters)
        assert bind_values(template, (), values).artifact.rendered.sql == sql
    if "parameter" not in name:
        observed = portable.export_emission_observation(artifact, artifact.request)
        assert observed.canonical_bytes is not None
        assert pure.parse_emission_observation(observed.canonical_bytes).status is (
            pure.Status.OK
        )
        assert portable.verify_emission_observation(
            observed.canonical_bytes, artifact, artifact.request
        ).corresponds
    reference = _ranked(tmp_path / "postgres", "postgres", body)
    assert reference.status == "VERIFIED", reference.blockers
    assert reference.artifact is not None
    assert b"ARRAY_AGG(" in reference.artifact.rendered.sql
    assert b"ROW_NUMBER" not in reference.artifact.rendered.sql


def test_the_mysql_sql_of_ranked_first_and_last(tmp_path) -> None:
    """Keys first, each read column once, one ROW_NUMBER per call; a rank
    name takes `_` past a carried name that is not ASCII."""
    grouped = _ranked(
        tmp_path / "grouped",
        "mysql",
        _query(
            "f = first(v_int, order by t, id); l = last(v_text, order by t, id)",
            where="t is not None",
        ),
    )
    assert grouped.artifact is not None
    assert grouped.artifact.rendered.sql.decode().split("), `p2`")[0].split(", `p1` ")[
        1
    ] == (
        "(`c0`, `c1`, `c2`) AS (SELECT `t1`.`c1` AS `c0`, "
        "MAX(CASE WHEN `t1`.`r1` = 1 THEN `t1`.`c5` END) AS `c1`, "
        "MAX(CASE WHEN `t1`.`r2` = 1 THEN `t1`.`c7` END) AS `c2` "
        "FROM (SELECT `t1`.`c1`, `t1`.`c5`, `t1`.`c7`, ROW_NUMBER() OVER "
        "(PARTITION BY `t1`.`c1` ORDER BY `t1`.`c4` ASC, `t1`.`c0` ASC) AS `r1`, "
        "ROW_NUMBER() OVER (PARTITION BY `t1`.`c1` ORDER BY `t1`.`c4` DESC, "
        "`t1`.`c0` DESC) AS `r2` FROM `p0` AS `t1`) AS `t1` GROUP BY `t1`.`c1`"
    )
    single = _ranked(
        tmp_path / "single",
        "mysql",
        _query("f = first(v_int, order by id)", grouped=False),
    )
    assert single.artifact is not None
    assert single.artifact.rendered.sql == (
        b"WITH `p0` (`c0`) AS (SELECT "
        b"MAX(CASE WHEN `s0`.`r0` = 1 THEN `s0`.`v int` END) AS `c0` "
        b"FROM (SELECT `s0`.`v int`, ROW_NUMBER() OVER (ORDER BY `s0`.`row id` "
        b"ASC) AS `r0` FROM `phase66`.`phase66 source \xc3\xa9` AS `s0`) AS `s0`) "
        b"SELECT `t1`.`c0` AS `f` FROM `p0` AS `t1`"
    )
    accented = _ranked(
        tmp_path / "accented",
        "mysql",
        _query("f = first(v_name, order by id)", grouped=False),
    )
    assert accented.artifact is not None
    assert (
        b"MAX(CASE WHEN `s0`.`r0_` = 1 THEN `s0`.`v\xc3\xa9` END) AS `c0` "
        b"FROM (SELECT `s0`.`v\xc3\xa9`, ROW_NUMBER() OVER (ORDER BY "
        b"`s0`.`row id` ASC) AS `r0_` FROM"
    ) in accented.artifact.rendered.sql


def _custom(*lines: str) -> str:
    return "".join(line + "\n" for line in lines)


FIRST = "f = first(v_int, order by id)"
REFUSED_BODIES = {
    "bool_value": _query("f = first(v_bool, order by id)"),
    "date_value": _query("f = first(v_date, order by id)"),
    "timestamp_value": _query("f = first(v_ts, order by id)"),
    "uuid_value": _query("f = last(v_uuid, order by id)"),
    "non_null_value": _query("f = first(n_int, order by id)"),
    "bool_beside_int": _query(
        "fi = first(v_int, order by id); fb = last(v_bool, order by id)"
    ),
    "nullable_group_key": _custom(
        "query result:",
        "    from rows",
        "    where a is not None",
        "    group by a",
        "    select:",
        "        a",
        "        f = first(v_int, order by id)",
        "    order by a",
    ),
    "text_group_key": _query("f = first(v_int, order by id)").replace("shop", "n_text"),
    "two_group_keys": _custom(
        "query result:",
        "    from rows",
        "    group by shop, n_int",
        "    select:",
        "        shop",
        "        n_int",
        "        f = first(v_int, order by id)",
        "    order by shop, n_int",
    ),
    "float_order_key": _query("f = first(v_int, order by n_float, id)"),
    "non_null_text_order_key": _query("f = first(v_int, order by n_text, id)"),
    "beside_count": _query("f = first(v_int, order by id); k = count()"),
    "key_selected_last": _custom(
        "query result:",
        "    from rows",
        "    group by shop",
        "    select:",
        "        f = first(v_int, order by id)",
        "        shop",
        "    order by shop",
    ),
    "no_order": _query("f = first(v_int, order by id)").replace(
        "    order by shop\n", ""
    ),
    "descending_order": _query("f = first(v_int, order by id)").replace(
        "order by shop", "order by shop desc"
    ),
    "ordered_by_result": _query("f = first(v_int, order by id)").replace(
        "order by shop", "order by f, shop"
    ),
    "limit": _query("f = first(v_int, order by id)") + "    limit 2\n",
    "where_comparison": _query("f = first(v_int, order by id)", where="a > 1"),
    "where_literal": _query("f = first(v_int, order by id)", where="shop == 2"),
    "where_or": _query(
        "f = first(v_int, order by id)",
        where="a is not None or b is not None",
        grouped=False,
    ),
    "row_let": _query("f = first(w, order by id)").replace(
        "    group by", "    let w = v_int\n    group by"
    ),
    "distinct": _query("f = first(v_int, order by id)")
    .replace("select:", "select distinct:")
    .replace("    order by shop\n", ""),
    "set_operation": _custom(
        "query x:",
        "    from rows",
        "    group by shop",
        "    select:",
        "        shop",
        "        f = first(v_int, order by id)",
        "query result:",
        "    union all x, x",
    ),
    # Past the WHERE the qualification witnessed: `is not None` of each
    # nullable order key once, and one group key `== p` of its Int parameter.
    "where_value_test": _query(FIRST, where="v_int is not None"),
    "where_bool_test": _query(FIRST, where="v_bool is not None"),
    "where_test_twice": _query(
        "f = first(v_int, order by a, id)", where="a is not None and a is not None"
    ),
    "where_non_null_test": _query(
        "f = first(v_int, order by n_int, id)", where="n_int is not None"
    ),
    "parameter_not_equal": _query(FIRST, where="shop != g", header="(g: Int)"),
    "parameter_first": _query(FIRST, where="g == shop", header="(g: Int)"),
    "nullable_parameter": _query(FIRST, where="shop == g", header="(g: Int | None)"),
    "float_parameter": _query(FIRST, where="n_float == g", header="(g: Float)"),
    "text_parameter": _query(FIRST, where="n_text == g", header="(g: Text)"),
    "two_parameters": _query(
        FIRST, where="shop == g and shop == h", header="(g: Int, h: Int)"
    ),
    "parameter_twice": _query(
        FIRST, where="shop == g and n_int == g", header="(g: Int)"
    ),
    "parameter_off_key": _query(FIRST, where="n_int == g", header="(g: Int)"),
    "field_compared_with_field": _query(
        FIRST, where="shop == n_int", header="(g: Int)"
    ),
    "parameter_with_expression": _query(
        FIRST, where="shop + 0 == g", header="(g: Int)"
    ),
    "where_bool_field": _query(
        "f = first(v_int, order by a, id)", where="a is not None and v_bool"
    ),
    "where_call_test": _query(FIRST, where="lower(t) is not None"),
    "unread_parameter": _query(FIRST, header="(g: Int)"),
    "global_int_parameter": _query(
        FIRST, where="n_small == g", grouped=False, header="(g: Int)"
    ),
    # A relation alias; compiled records and observations read as `rows`.
    "relation_alias": _query(FIRST).replace(
        "    from rows\n", "    let base = rows\n    from base\n"
    ),
    "relation_alias_chain": _query(FIRST).replace(
        "    from rows\n", "    let base = rows\n    let b2 = base\n    from b2\n"
    ),
    # One authored key list per statement, as the qualification ranked it.
    "two_key_lists": _query(
        "fi = first(v_int, order by id); lf = last(v_float, order by n_int, id)"
    ),
    "key_list_direction": _query(
        "fi = first(v_int, order by a, id); lt = last(v_text, order by a desc, id)",
        where="a is not None",
    ),
    "key_list_order": _query(
        "fi = first(v_int, order by a, id); lt = last(v_text, order by id, a)",
        where="a is not None",
    ),
    # Carrier parameters past DECIMAL(65,30) and VARCHAR(32) or (64).
    "decimal_9_2_value": _query("f = first(v_dec9, order by id)"),
    "varchar_255_value": _query("f = first(v_wide, order by id)"),
    "varchar_255_order_key": _query(
        "f = first(v_int, order by v_wide, id)", where="v_wide is not None"
    ),
}


@pytest.mark.parametrize("name", REFUSED_BODIES)
def test_a_mysql_project_keeps_its_refusal_outside_the_statement_class(
    tmp_path, name
) -> None:
    """Every other form keeps main's refusal, object for object: one PIE-B1003
    `first_last_not_admitted_on_target` per call, at its select item."""
    body = REFUSED_BODIES[name]
    data = _public(_ranked(tmp_path, "mysql", body))
    lines = [
        RANKED_LINE + number
        for number, line in enumerate(body.splitlines(), 1)
        if "first(" in line or "last(" in line
    ]
    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "first_last_not_admitted_on_target",
            line,
            "Emit this first or last for PostgreSQL, or keep it in check/plan: "
            "this first or last form is not admitted on MySQL yet.",
        )
        for line in lines
    ]


# Rule two (owner, 2026-11-13): a statement of the class that another refusal
# stops, before realization (a label past 256 characters) or after it (the
# contract's public artifact byte limit), reports main's whole refusal.
@pytest.mark.parametrize(
    ("label", "limits", "other"),
    [
        ("f" * 257, None, [("PIE-B1002", "output_label_unrepresentable", None)]),
        ("fi", {"artifact_bytes": 100}, []),
    ],
)
def test_a_refused_statement_of_the_class_reports_mains_whole_refusal(
    tmp_path, label, limits, other
) -> None:
    plain = _query(
        "fi = first(v_int, order by a, id); lt = last(v_text, order by a, id)",
        where="a is not None",
    )
    assert _ranked(tmp_path / "admitted", "mysql", plain).status == "VERIFIED"
    body = plain.replace("fi = ", f"{label} = ")
    data = _public(_ranked(tmp_path / "refused", "mysql", body, limits=limits))
    lines = [
        RANKED_LINE + number
        for number, line in enumerate(body.splitlines(), 1)
        if "first(" in line or "last(" in line
    ]
    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], (b.get("location") or {}).get("line"))
        for b in data["blockers"]
    ] == [
        ("PIE-B1003", "first_last_not_admitted_on_target", line) for line in lines
    ] + other


def _admit(law):
    return lambda *_: True


def _no_test(law):
    # A WHERE outside the class read as one that tests and compares nothing.
    return lambda plan, origin: law(plan, origin) or ((), ())


# (emission laws forged, the pure boundary's refusal or None where a header
# parameter keeps the form outside its schema), over REFUSED_BODIES' form
FORGERIES = {
    # A carrier the qualification saw MySQL change, admitted by emission only.
    "bool_value": (
        "ranked_value",
        lambda law: lambda r: law(r) or (r is not None and r.tag == "Bool"),
        "first or last shape",
    ),
    "decimal_9_2_value": (
        "ranked_value",
        lambda law: lambda r: law(r) or (r is not None and r.tag == "Decimal"),
        "first or last shape",
    ),
    "varchar_255_value": (
        "_binary_varchar",
        lambda law: lambda r: law(r) or r.storage.get("length") == 255,
        "first or last shape",
    ),
    "text_group_key": ("ranked_inputs", _admit, "first or last shape"),
    "descending_order": ("ranked_statement", _admit, "first or last shape"),
    "where_comparison": ("_ranked_filter", _no_test, "first or last shape"),
    "limit": ("ranked_statement", _admit, "first or last shape"),
    "where_value_test": ("ranked_statement", _admit, "first or last shape"),
    "where_test_twice": ("ranked_statement", _admit, "first or last shape"),
    "where_non_null_test": ("_ranked_filter", _no_test, "first or last shape"),
    "nullable_parameter": ("_non_null_int", _admit, None),
    "parameter_not_equal": (("ranked_statement", "ranked_inputs"), _admit, None),
    "two_parameters": ("ranked_statement", _admit, None),
    "parameter_off_key": ("ranked_statement", _admit, None),
    "unread_parameter": ("ranked_statement", _admit, None),
    "global_int_parameter": ("ranked_inputs", _admit, None),
    "parameter_first": (("ranked_statement", "ranked_inputs"), _admit, None),
    "field_compared_with_field": (("ranked_statement", "ranked_inputs"), _admit, None),
    "where_call_test": (
        ("ranked_statement", "ranked_inputs"),
        _admit,
        "first or last shape",
    ),
    "two_key_lists": ("ranked_statement", _admit, "first or last shape"),
    "key_list_direction": ("ranked_statement", _admit, "first or last shape"),
    "key_list_order": ("ranked_statement", _admit, "first or last shape"),
}


@pytest.mark.parametrize("name", FORGERIES)
def test_each_reader_refuses_first_or_last_forged_past_the_class(
    tmp_path, monkeypatch, name
) -> None:
    """Emission and its verifier share the plan law, so one forged past it
    emits; the verifier, compiled replay and the pure boundary each refuse the
    artifact again from their own input once the law is back. The pure
    boundary has no header parameter: such a form stays outside its schema."""
    from pietto._project import project_compiled_schema as wire
    from pietto._project import project_sql_emission_aggregation as grouping
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    laws, forged, detail = FORGERIES[name]
    body = REFUSED_BODIES[name]
    for law in (laws,) if type(laws) is str else laws:
        monkeypatch.setattr(grouping, law, forged(getattr(grouping, law)))
    outcome = _ranked(tmp_path / "forged", "mysql", body)
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    observed = portable.export_emission_observation(artifact, artifact.request)
    monkeypatch.undo()

    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
        prepare_compiled_template(
            load_compiled(
                built.payload,
                expected_pin=built.pin,
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )
        )
    if detail is None:
        assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA
        assert observed.canonical_bytes is None
    else:
        assert observed.canonical_bytes is not None
        refused = pure.parse_emission_observation(observed.canonical_bytes)
        assert (refused.status, refused.detail) == (
            pure.Status.INVALID_RELATION,
            detail,
        )
    assert [
        (b.code, b.detail) for b in _ranked(tmp_path / "law", "mysql", body).blockers
    ] == [("PIE-B1003", "first_last_not_admitted_on_target")] * (
        body.count("first(") + body.count("last(")
    )


def test_a_tampered_ranked_bundle_or_observation_is_refused(tmp_path) -> None:
    """A re-pinned bundle whose result is ordered descending, whose WHERE is an
    `or`, whose WHERE row and aggregate another declaration owns or that holds
    an operation no predicate reads, and an observation whose rank names, rank
    test, spelling, carried column or null test differ from the document's
    own, each fail their reader."""
    from pietto._project import project_compiled_schema as wire
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import prepare_compiled_template

    outcome = _ranked(
        tmp_path,
        "mysql",
        _query(
            "fi = first(v_int, order by a, b desc, id); "
            "lt = last(v_text, order by a, b desc, id)",
            where="a is not None and b is not None",
        ),
    )
    artifact = outcome.artifact
    assert artifact is not None
    description = build_compiled(artifact).root.description

    def change(record, field, value):
        values = list(record.values)
        values[wire.FIELDS[record.address.kind].index(field)] = value
        return type(record)(record.address, tuple(values))

    def each(edit):
        return lambda records: tuple(edit(r) for r in records)

    def extra_operation(records):
        operations = [r for r in records if r.address.kind == "operation"]
        if not operations:
            return records
        address = wire.Address("operation", len(operations))
        return (*records, type(operations[1])(address, operations[1].values))

    (source,) = (
        r
        for _, records in description.members
        for r in records
        if r.address.kind == "source"
    )
    for forge in (
        each(
            lambda r: (
                change(r, "ordering", tuple((a, "desc") for a, _ in r.get("ordering")))
                if r.address.kind == "result"
                else r
            )
        ),
        each(
            lambda r: (
                change(r, "operator", ("binary", "or"))
                if r.address.kind == "operation"
                and r.get("operator") == ("binary", "and")
                else r
            )
        ),
        # The aggregate too: a WHERE row alone fails the stage chain first.
        each(
            lambda r: (
                change(r, "owner", source.get("declaration"))
                if r.address.kind == "aggregate"
                or r.address.kind == "row"
                and r.get("stage") == "where"
                else r
            )
        ),
        extra_operation,
    ):
        forged = wire.Description(
            description.compatibility,
            description.producer,
            description.query,
            tuple((member, forge(records)) for member, records in description.members),
        )
        raw = wire.encode(forged)
        with pytest.raises(wire.CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
            prepare_compiled_template(
                load_compiled(
                    raw,
                    expected_pin=wire.content_pin(raw),
                    accepted_producer=forged.producer,
                    accepted_compatibility=forged.compatibility,
                )
            )
    canonical = portable.export_emission_observation(
        artifact, artifact.request
    ).canonical_bytes
    assert canonical is not None

    def tampered(old: str, new: str, edit=None):
        document = json.loads(canonical)
        for record in document["records"]:
            if record["ref"] == ["rendered", 0]:
                assert old in record["fields"]["sql"]
                record["fields"]["sql"] = record["fields"]["sql"].replace(old, new, 1)
            if edit and record["ref"] == edit[0]:
                record["fields"][edit[1]] = edit[2]
        found = pure.evaluate_emission_observation(document)
        return found.status, found.detail

    assert tampered("", "") == (pure.Status.OK, None)
    for old, new, edit, detail in (
        ("AS `r1`", "AS `r9`", None, "rank name"),
        ("`t1`.`r2` = 1", "`t1`.`r9` = 1", None, "rank name"),
        (" = 1 THEN ", " = 2 THEN ", None, "syntax spelling"),
        (
            "MAX(",
            "MIN(",
            (["aggregate_value_column", 0], "spelling", "MIN"),
            "aggregate spelling",
        ),
        (
            "(SELECT `t1`.`c1`, `t1`.`c5`",
            "(SELECT `t1`.`c1`, `t1`.`c6`",
            None,
            "column name",
        ),
        (
            " IS NOT NULL",
            " IS NULL",
            (["sql_operation", 1], "operator", "is null"),
            "first or last shape",
        ),
    ):
        assert tampered(old, new, edit) == (pure.Status.INVALID_RELATION, detail)


def test_the_ranked_where_law_reads_only_is_not_none(tmp_path) -> None:
    """`is None` of an order key fails check (PIE-S2104) and of another field
    tests no order key, so no program brings one to the WHERE law; a plan
    whose `is not None` reads `is None` falls outside it."""
    from dataclasses import replace
    from types import SimpleNamespace

    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project import project_sql_plan_expressions as expressions

    body = _query("f = first(v_int, order by a, id)", where="a is not None")
    refused = _public(_ranked(tmp_path / "is_none", "mysql", body.replace("not ", "")))
    assert [d["code"] for d in refused["diagnostics"]] == ["PIE-S2104"]
    outcome = _ranked(tmp_path / "is_not_none", "mysql", body)
    assert outcome.artifact is not None
    plan = outcome.artifact.request.plan
    flipped = SimpleNamespace(
        filters=plan.filters,
        stage_ports=plan.stage_ports,
        expressions=tuple(
            replace(node, expression=replace(node.expression, negated=False))
            if type(node) is expressions.ProjectSQLIsNull
            else node
            for node in plan.expressions
        ),
    )
    for law, admitted in ((plan, True), (flipped, False)):
        found = grouping._ranked_filter(law, grouping._ranked_origin(law))
        assert (found is not None) is admitted
