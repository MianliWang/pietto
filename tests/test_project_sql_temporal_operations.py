"""Q3 physical admission for temporal/UUID equality, ordering, grouping and DISTINCT."""

import uuid

import pytest

from pietto._project import project_sql_emission_aggregation as aggregation
from pietto._project import project_sql_emission_results as results
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_verification as verification
from pietto._project import project_sql_emission_windows as windows


def _realization(family: str, tag: str) -> rows.Realization:
    if tag == "Timestamp":
        return rows.Realization(
            tag,
            {
                "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                "fractional_seconds": 6,
            },
            False,
            {"kind": "timestamp"},
        )
    if tag == "Date":
        return rows.Realization(
            tag,
            {"kind": "pg_date" if family == "postgres" else "my_date"},
            True,
            {"kind": "date"},
        )
    return rows.Realization(
        tag,
        {"kind": "pg_uuid" if family == "postgres" else "my_uuid_bytes"},
        True,
        {"kind": "uuid", "encoding": "standard_bytes"},
    )


def _compared(family, left, right, operator):
    return rows.resolved_comparison_realization(
        family, "Bool", True, left, right, operator
    )[1]


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("tag", ("Timestamp", "Date", "UUID"))
def test_exact_q3_carriers_support_equality_grouping_counts_and_distinct(family, tag):
    carrier = _realization(family, tag)

    assert aggregation.grouping_problem(carrier) is None
    assert aggregation.resolved_argument_problem("count", True, carrier, family) is None
    assert (
        aggregation.resolved_argument_problem("count_distinct", True, carrier, family)
        is None
    )
    assert results.distinct_problem(family, carrier) is None
    assert _compared(family, carrier, carrier, "==") is None
    assert _compared(family, carrier, carrier, "!=") is None
    assert windows.partition_key_admitted(carrier)


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("tag", ("Timestamp", "Date"))
def test_one_temporal_carrier_orders_and_compares(family, tag):
    carrier = _realization(family, tag)

    for operator in ("<", "<=", ">", ">="):
        assert _compared(family, carrier, carrier, operator) is None
    realized, problem = rows.resolved_between_realization(
        family, "Bool", False, (carrier, carrier, carrier)
    )
    assert problem is None and realized is not None
    assert tag in results.ORDER_TAGS and results.order_admitted(family, carrier)
    assert windows.order_key_admitted(carrier, family)
    assert verification._order_key(carrier, family)
    assert verification._partition_key(carrier, family)
    # PostgreSQL MIN/MAX keep the exact carrier; MySQL's result metadata is
    # not reviewed yet.
    for function in ("min", "max"):
        problem = aggregation.resolved_argument_problem(function, True, carrier, family)
        if family == "postgres":
            assert problem is None
        else:
            assert problem == (
                "PIE-B1003",
                function + "_argument_outside_reviewed_int_domain",
            )


@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_uuid_orders_on_postgresql_and_mixed_temporal_carriers_stay_unordered(
    family,
):
    """Q3: a UUID orders by its unsigned big-endian bytes on PostgreSQL; MySQL
    keeps it equality-only until its BINARY(16) order has a differential."""
    uuid = _realization(family, "UUID")
    stamp = _realization(family, "Timestamp")
    date = _realization(family, "Date")
    ordered = family == "postgres"

    for operator in ("<", "<=", ">", ">="):
        assert _compared(family, uuid, uuid, operator) == (
            None if ordered else ("PIE-B1003", "comparison_type_pair_not_admitted")
        )
    realized, problem = rows.resolved_between_realization(
        family, "Bool", False, (uuid, uuid, uuid)
    )
    assert (realized is not None, problem) == (
        (True, None)
        if ordered
        else (False, ("PIE-B1003", "between_type_pair_not_admitted"))
    )
    # One UUID carrier compares only with the same carrier.
    other = rows.Realization(
        "UUID", {"kind": "typed_null"}, True, {"kind": "typed_null"}
    )
    assert _compared(family, uuid, other, "<") == (
        "PIE-B1003",
        "comparison_type_pair_not_admitted",
    )
    assert _compared(family, stamp, date, "<") == (
        "PIE-B1003",
        "comparison_type_pair_not_admitted",
    )
    assert _compared(family, stamp, date, "==") == (
        "PIE-B1003",
        "comparison_type_pair_not_admitted",
    )
    assert results.order_admitted(family, uuid) is ordered
    assert windows.order_key_admitted(uuid, family) is ordered
    assert verification._order_key(uuid, family) is ordered
    assert verification._partition_key(uuid, family)
    # The semantic layer refuses min/max of a UUID (PIE-S2314); the emission
    # argument law refuses it too.
    for function in ("min", "max"):
        assert aggregation.resolved_argument_problem(function, True, uuid, family) == (
            "PIE-B1003",
            function + "_argument_outside_reviewed_int_domain",
        )


def test_q3_temporal_carriers_reject_a_non_reviewed_storage_shape():
    carrier = rows.Realization(
        "Timestamp",
        {"kind": "pg_timestamp", "fractional_seconds": 3},
        False,
        {"kind": "timestamp"},
    )
    date = rows.Realization("Date", {"kind": "pg_date"}, False, {"kind": "timestamp"})

    for value in (carrier, date):
        assert aggregation.grouping_problem(value) == (
            "PIE-B1002",
            "group_key_temporal_physical_representation_mismatch",
        )
        assert aggregation.resolved_argument_problem(
            "count", True, value, "postgres"
        ) == (
            "PIE-B1002",
            "group_key_temporal_physical_representation_mismatch",
        )
        assert aggregation.resolved_argument_problem(
            "min", True, value, "postgres"
        ) == (
            "PIE-B1002",
            "group_key_temporal_physical_representation_mismatch",
        )
        assert results.distinct_problem("postgres", value) == (
            "distinct_field_temporal_physical_representation_mismatch"
        )
        assert not windows.order_key_admitted(value, "postgres")
    assert not verification._order_key(carrier, "postgres")


def _emitted(tmp_path, target, body):
    import _pietto_sql_emission as probe
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    checked, outcome = probe.temporal_case(tmp_path, target, body)
    assert checked.verified
    if outcome.status != "VERIFIED":
        return outcome, None
    return outcome, probe.decode_public(serialize_project_sql_emission(outcome))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_temporal_filters_compare_one_carrier_and_refuse_the_rest(tmp_path, target):
    outcome, public = _emitted(
        tmp_path / "admitted",
        target,
        "    from rows\n    where ts < ts2 and d >= d2 and ts <= ts2 <= ts\n"
        "    select:\n        t = ts\n",
    )
    assert public is not None, outcome.blockers
    q = '"' if target == "postgres" else "`"

    def col(name):
        return f"{q}s0{q}.{q}{name}{q}"

    assert (
        f"WHERE ((({col('ts')} < {col('ts2')}) AND ({col('d')} >= {col('d2')}))"
        f" AND ({col('ts2')} BETWEEN {col('ts')} AND {col('ts')}))"
    ) in public["sql"]
    for name, body in (
        ("mixed", "    from rows\n    where ts < d\n    select:\n        t = ts\n"),
        ("mixed_eq", "    from rows\n    where ts == d\n    select:\n        t = ts\n"),
        *(
            ()
            if target == "postgres"
            else (
                (
                    "uuid",
                    "    from rows\n    where u < u\n    select:\n        t = ts\n",
                ),
            )
        ),
    ):
        outcome, _ = _emitted(tmp_path / name, target, body)
        assert outcome.status == "BLOCKED"
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            ("PIE-B1003", "comparison_type_pair_not_admitted")
        ]


# Q3: the 16 bytes compared as unsigned big-endian values. A signed first
# byte, the little-endian `bytes_le` field order or a version-aware order
# each disagrees with it somewhere in this ascending witness.
UUID_ORDER = tuple(
    uuid.UUID(text)
    for text in (
        "00000000-0000-0000-0000-000000000000",
        "00000000-0000-0000-0000-0000000000ff",
        "00000001-0000-0000-0000-000000000000",
        "7fffffff-ffff-ffff-ffff-ffffffffffff",
        "80000000-0000-0000-0000-000000000000",
        "ffffffff-0000-1000-8000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    )
)


def test_uuid_order_is_unsigned_big_endian_bytes():
    """PostgreSQL uuid_cmp (memcmp of the 16 bytes), MySQL BINARY(16) and
    Python uuid.UUID agree on this order; nearby orders do not."""
    assert list(UUID_ORDER) == sorted(UUID_ORDER, key=lambda u: u.bytes)
    assert (
        list(UUID_ORDER)
        == sorted(UUID_ORDER)
        == sorted(UUID_ORDER, key=lambda u: u.int)
    )
    for other in (
        lambda u: int.from_bytes(u.bytes, "big", signed=True),
        lambda u: u.bytes_le,
        lambda u: (u.version or 0, u.bytes),
    ):
        assert sorted(UUID_ORDER, key=other) != list(UUID_ORDER)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_uuid_filters_compare_by_order_on_postgresql_only(tmp_path, target):
    """A UUID comparison, inclusive chain and result ORDER key are emitted on
    PostgreSQL with the target's own uuid operators; MySQL refuses each."""
    body = (
        "    from rows\n    where u < u or u >= u or u <= u <= u\n"
        "    select:\n        key = u\n"
    )
    outcome, public = _emitted(tmp_path, target, body)
    if target == "mysql":
        assert public is None
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            ("PIE-B1003", "comparison_type_pair_not_admitted")
        ]
        return
    assert public is not None, outcome.blockers
    assert (
        'WHERE ((("s0"."u" < "s0"."u") OR ("s0"."u" >= "s0"."u"))'
        ' OR ("s0"."u" BETWEEN "s0"."u" AND "s0"."u"))'
    ) in public["sql"]
    assert [
        r["evidence"]
        for r in public["requirements"]
        if r["kind"] in {"comparison", "between"}
    ] == [[{"operator": "<"}], [{"operator": ">="}], [{"operator": "between"}]]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_source_and_derived_dates_group_count_distinct_and_compare(tmp_path, target):
    outcome, public = _emitted(
        tmp_path / "grouped",
        target,
        "    from rows\n    where date_of(ts) <= d\n    group by d\n    select:\n"
        "        day = d\n        n = count(d2)\n        k = count_distinct(d2)\n",
    )
    assert public is not None, outcome.blockers
    q = '"' if target == "postgres" else "`"
    assert f"GROUP BY {q}t1{q}.{q}c3{q}" in public["sql"]
    assert f"COUNT(DISTINCT {q}t1{q}.{q}c4{q})" in public["sql"]
    assert (
        f"(CAST({q}s0{q}.{q}ts{q} AS date) <= {q}s0{q}.{q}d{q})" in public["sql"]
        or f"(DATE({q}s0{q}.{q}ts{q}) <= {q}s0{q}.{q}d{q})" in public["sql"]
    )
    outcome, public = _emitted(
        tmp_path / "distinct",
        target,
        "    from rows\n    select distinct:\n        day = d\n        maybe = d2\n",
    )
    assert public is not None, outcome.blockers
    assert "SELECT DISTINCT " in public["sql"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_date_join_keys_admit_inner_left_right_and_refuse_full(tmp_path, target):
    import json

    import _pietto_sql_emission as probe

    contract = json.loads(
        probe.fixture(target, "T_row_direct", "table_preserve")["contract"]
    )
    pg = target == "postgres"
    field = {
        "ordinal": 0,
        "name": "d",
        "column": "d",
        "representation": {
            "storage": {"kind": "pg_date" if pg else "my_date"},
            "nullable": False,
            "domain": {"kind": "date"},
        },
    }
    left = contract["sources"][0]
    left["fields"] = [field]
    right = json.loads(json.dumps(left))
    right["selector"]["name"] = "other"
    right["relation"]["name"] = "other source"
    contract["sources"].append(right)
    header = (
        "shape Row:\n    d: Date\n"
        f'source rows: Row = {target}.table("opaque.rows")\n'
        f'source other: Row = {target}.table("opaque.other")\n'
    )
    for kind in ("inner join", "left join", "right join", "full join"):
        _, outcome = probe.build_case(
            tmp_path / kind.replace(" ", "_"),
            header
            + f"table result:\n    from rows\n    {kind} other on rows.d == other.d\n"
            "    select:\n        x = rows.d\n",
            probe.encoded(contract).decode(),
        )
        if kind != "full join":
            assert outcome.status == "VERIFIED", outcome.blockers
            continue
        assert outcome.status == "BLOCKED"
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            (
                "PIE-B1003",
                "full_join_equality_outside_reviewed_int_domain"
                if pg
                else "mysql_full_join_approved_non_support",
            )
        ]
