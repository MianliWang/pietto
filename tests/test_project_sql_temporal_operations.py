"""Q3 physical admission for temporal/UUID equality, grouping and DISTINCT."""

import pytest

from pietto._project import project_sql_emission_aggregation as aggregation
from pietto._project import project_sql_emission_results as results
from pietto._project import project_sql_emission_rows as rows


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
    return rows.Realization(
        tag,
        {"kind": "pg_uuid" if family == "postgres" else "my_uuid_bytes"},
        True,
        {"kind": "uuid", "encoding": "standard_bytes"},
    )


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("tag", ("Timestamp", "UUID"))
def test_exact_q3_carriers_support_equality_grouping_counts_and_distinct(family, tag):
    carrier = _realization(family, tag)

    assert aggregation.grouping_problem(carrier) is None
    assert aggregation.resolved_argument_problem("count", True, carrier) is None
    assert (
        aggregation.resolved_argument_problem("count_distinct", True, carrier) is None
    )
    assert results.distinct_problem(family, carrier) is None
    assert (
        rows.resolved_comparison_realization(
            family, "Bool", True, carrier, carrier, "=="
        )[1]
        is None
    )
    assert (
        rows.resolved_comparison_realization(
            family, "Bool", True, carrier, carrier, "!="
        )[1]
        is None
    )
    assert rows.resolved_comparison_realization(
        family, "Bool", True, carrier, carrier, "<"
    )[1] == ("PIE-B1003", "comparison_type_pair_not_admitted")


def test_q3_temporal_carriers_reject_a_non_microsecond_storage_shape():
    carrier = rows.Realization(
        "Timestamp",
        {"kind": "pg_timestamp", "fractional_seconds": 3},
        False,
        {"kind": "timestamp"},
    )

    assert aggregation.grouping_problem(carrier) == (
        "PIE-B1002",
        "group_key_temporal_physical_representation_mismatch",
    )
    assert aggregation.resolved_argument_problem("count", True, carrier) == (
        "PIE-B1002",
        "group_key_temporal_physical_representation_mismatch",
    )
    assert results.distinct_problem("postgres", carrier) == (
        "distinct_field_temporal_physical_representation_mismatch"
    )
