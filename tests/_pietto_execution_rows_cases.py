"""S05 named admitted domain; fixture/oracle owners remain independently authored."""

from typing import Any

import _pietto_sql_emission as emission

# A mechanism denominator, not a Cartesian promise about operator scalar domains.
CASES = (
    ("G_emission_table_bag", "bag"),
    ("G_scan_row_domains", "partitioned_root"),
    ("I_emission_table_empty", "empty"),
    ("N_imported_chain", "bag"),
    ("N_imported_chain", "empty"),
    ("O_named_later", "self_join"),
    ("R_fixed_direct", "table_preserve"),
    ("S_fixed_named", "imported_bind"),
    ("T_row_direct", "query_bind"),
    ("T_row_direct", "empty_preserve"),
    ("U_row_named", "imported_bind"),
    ("W_join_shapes", "cross"),
    ("W_join_shapes", "inner"),
    ("W_join_shapes", "semi"),
    ("W_join_shapes", "anti"),
    ("W_join_values", "left_marker"),
    ("W_join_values", "right_accumulated"),
    ("V_join_full", "null_keys"),
    ("X_aggregate_global", "bag"),
    ("X_aggregate_global", "empty"),
    ("X_aggregate_global", "all_null"),
    ("X_aggregate_grouped", "hidden"),
    ("X_aggregate_grouped", "empty"),
    ("Z_aggregate_composition", "imported"),
    ("A_window_ranking", "peers"),
    ("A_window_distribution", "spread"),
    ("A_window_navigation", "offsets"),
    ("A_window_frame", "rows"),
    ("A_window_frame", "range"),
    ("A_window_groups", "exclude"),
    ("A_window_qualify", "hidden"),
    ("O_result_distinct", "hidden_group"),
    ("O_result_order", "ordinary_desc"),
    ("O_result_limit", "zero"),
    ("O_result_limit", "inner_then_filter"),
    ("O_result_window", "qualify_order_limit"),
    *(("S_set_forms", form) for form in emission.VARIANTS["S_set_forms"]),
    ("S_set_multiplicity", "empty_left"),
    ("S_set_boundaries", "ordered_operands"),
    ("S_set_producers", "grouped_union"),
    ("O_named_later", "two_facades"),
)


def build(directory, target, case, variant):
    item = emission.fixture(target, case, variant)
    checked, outcome = emission.build_case(
        directory,
        item["source"],
        item["contract"],
        item.get("policy", "preserve_literals"),
    )
    assert checked.verified
    assert outcome.status == emission.expected_status(case, variant, target)
    return outcome


def expected(target, case, variant):
    """Read independent fixture semantics, never proposed output facts or PASS."""
    import _pietto_target_conformance_cases as oracle

    ordered = False
    if case == "G_scan_row_domains":
        rows, _, _, ordered = oracle.row_domain_expectation(target, variant)
    elif case in {"R_fixed_direct", "S_fixed_named"}:
        rows = oracle.fixed_rows(
            target, named=case == "S_fixed_named", empty=variant.startswith("empty")
        )
    elif case in {"T_row_direct", "U_row_named"}:
        rows = (
            oracle.truth_rows(target)
            if (case, variant) == ("T_row_direct", "truth_table")
            else oracle.row_result_rows(target, empty=variant.startswith("empty"))
        )
    elif case in {"W_join_shapes", "W_join_values", "V_join_full"}:
        rows = oracle.join_rows(variant)
    elif (case, variant) in oracle.MIGRATED_JOIN_ROWS:
        rows = oracle.MIGRATED_JOIN_ROWS[case, variant]
    elif case in emission.AGGREGATE_CASES:
        rows = oracle.aggregate_rows(target, case, variant)
    elif case in emission.WINDOW_CASES:
        rows = oracle.WINDOW_EXPECTATIONS[oracle.window_key(case, variant)]
    elif case in emission.SET_CASES or (case, variant) in oracle.SET_MIGRATED:
        rows, _, _, _, ordered = oracle.set_expectation(target, case, variant)
    elif case in emission.RESULT_CASES or (case, variant) in oracle.RESULT_MIGRATED:
        rows, _, _, _, ordered = oracle.result_expectation(target, case, variant)
    else:
        rows = (
            oracle.chain_rows
            if case in {"N_imported_chain", "M_named_chain", "O_named_later"}
            else oracle.emission_rows
        )(target, empty=variant == "empty")
    return rows, ordered


def seven_rows(target, precision=39) -> tuple[tuple[Any, ...], ...]:
    import _pietto_results_product as product

    rows = product.temporal_rows(target, mixed=True)
    if precision == 65:
        for row in rows:
            row[8] = product.decimal_literal(10**65 - 1, 30)
    return (*map(tuple, rows), tuple(rows[0]), (None,) * 9)


def seven_artifact(directory, target, *, precision=39, state="values"):
    import json
    import _pietto_results_product as product
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning
    from pietto._project.project_sql_emission import emit_project_sql

    source = product.temporal_source(target, mixed=True, all_nullable=True)
    contract = json.loads(product.temporal_input(target, mixed=True, all_nullable=True))
    contract["sources"][0]["relation"]["name"] = (
        "p68seven" + str(precision) + "_" + state
    )
    contract["environment"].append(
        dict(
            key="identifier_case",
            scope="statement",
            value="quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        )
    )
    if precision == 65:
        source = source.replace("Decimal(39, 4)", "Decimal(65, 30)")
        for part in ("storage", "domain"):
            contract["sources"][0]["fields"][8]["representation"][part].update(
                precision=65, scale=30
            )
    checked = product.build_neutral(directory, {"main.pietto": source})
    meaning = acquire_scalar_meaning(checked)
    outcome = emit_project_sql(
        checked, json.dumps(contract).encode(), scalar_meaning=meaning
    )
    assert outcome.status == "VERIFIED", (outcome.cli_errors, outcome.blockers)
    return outcome.artifact


# -- S10 nested rows (D71.11): pg_column_arrays_v1 from a real PostgreSQL Collect

LOW, HIGH = -(2**63), 2**63 - 1
QUOTED = ',{}"\\'
# The `rows` table above is read by `id` only: 0, 2, 5, 5 and -1.
KIDS_TABLE = (
    'CREATE TABLE "kids"(parent BIGINT NOT NULL,seq BIGINT NOT NULL,'
    "i BIGINT NOT NULL,b BOOLEAN,t TEXT,w4 INTEGER NOT NULL,w2 SMALLINT)"
)
# (parent, seq, i, b, t, w4, w2): a duplicate child row; an all-NULL nullable
# child; Int64 and Int32/Int16 limits; quoting characters, the empty and the
# 'NULL' string, a multibyte one; a tie on seq 2; a kid without a parent row.
KIDS = (
    (0, 1, 7, True, "a", 7, 7),
    (0, 2, 7, True, "a", 7, 7),
    (2, 1, 5, None, None, 5, None),
    (5, 1, LOW, False, QUOTED, -(2**31), -(2**15)),
    (5, 2, HIGH, True, "", 2**31 - 1, 2**15 - 1),
    (5, 2, 0, False, "NULL", 0, None),
    (5, 3, 4, False, "é", 4, 4),
    (99, 1, 1, True, "x", 1, 1),
)
IBT = (("i", "Int8", False), ("b", "Bool", True), ("t", "Text", True))
WIDTHS = (("w4", "Int4", False), ("w2", "Int2", True))
# name: (children, collected options, physical description, Arrow fields).
NESTED_SHAPES: dict[str, Any] = {
    "captured": (IBT, {}),
    "closed": (IBT, {"closed": True}),
    "ordered": (IBT, {"ordered": True}),
    "widths": (WIDTHS, {}),
}
IBT_DESCRIPTION = [["renamed", 20], ["c", 20], ["i", 1016], ["b", 1000], ["t", 1009]]
IBT_FIELDS = [
    ["renamed", "int64", False],
    ["c", "list<item: struct<i: int64 not null, b: bool, t: string> not null>", False],
]
NESTED_DESCRIPTIONS = {
    "captured": IBT_DESCRIPTION,
    "closed": IBT_DESCRIPTION,
    "ordered": IBT_DESCRIPTION,
    "widths": [["renamed", 20], ["c", 20], ["w4", 1007], ["w2", 1005]],
}
NESTED_FIELDS = {
    "captured": IBT_FIELDS,
    "closed": IBT_FIELDS,
    "ordered": IBT_FIELDS,
    "widths": [
        ["renamed", "int64", False],
        ["c", "list<item: struct<w4: int32 not null, w2: int16> not null>", False],
    ],
}


def nested_expected(name):
    """Independent literal oracle: each parent row's children as tie groups
    (in seq order; the order inside one seq is not promised), parent rows as
    a multiset, plus the parent order a parent ORDER BY fixes."""
    labels = ("w4", "w2") if name == "widths" else ("i", "b", "t")
    columns = (5, 6) if name == "widths" else (2, 3, 4)

    def groups(kids):
        result: list[list[dict[str, Any]]] = []
        for seq in sorted({kid[1] for kid in kids}):
            result.append(
                [
                    dict(zip(labels, (kid[c] for c in columns), strict=True))
                    for kid in kids
                    if kid[1] == seq
                ]
            )
        return result

    parents = (5, 5, 2, 0) if name == "ordered" else (0, 2, 5, 5, -1)
    return [
        [
            parent,
            groups(KIDS if name == "closed" else [k for k in KIDS if k[0] == parent]),
        ]
        for parent in parents
    ]
