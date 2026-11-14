"""Closed installed probe and independent data-only public artifact consumer."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast
from uuid import UUID

from copy import copy

CONFIG = 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
COLLECT_VARIANTS = (
    "closed",
    "captured",
    "topk",
    "ties",
    "hidden_nullable_key",
    "siblings",
    "distinct_let",
    "grouped_let",
    "parent_order_limit",
    "text_quoting",
    "int4_child",
    "decimal_child",
)
VARIANTS = {
    "G_emission_table_bag": ("bag",),
    # Pre-Slice16 corrective closure: C06 physical row domains (inheritance,
    # view, partition root), carrying the G6 bind-safe LIMIT and the G3
    # narrow-key wide-offset witnesses.
    "G_scan_row_domains": ("inherited_parent", "view_rows", "partitioned_root"),
    "H_emission_query_bag": ("bag",),
    "I_emission_table_empty": ("empty",),
    "J_emission_query_empty": ("empty",),
    "K_emission_rejected": ("duplicate_selector", "ordinal_bool", "stale_selector"),
    "L_emission_blocked": (
        "missing_source",
        "bool_domain",
        "decimal_mismatch",
        "timestamp_meaning",
        "uuid_meaning",
        "where_later",
    ),
    "M_named_chain": ("table_bag", "query_bag", "empty", "long_intermediate"),
    "N_imported_chain": ("bag", "empty"),
    # Phase70 S03: closed relation lets, each emitted as its own named block.
    # S05: `diamond_limit` reads one let from two lets declared before it.
    "L_let_relations": ("chain", "imported", "hidden_join", "diamond_limit"),
    # Phase70 S06: typed VALUES; a statement without a physical source is
    # PostgreSQL only, and a rejected VALUES body never reaches SQL. A VALUES
    # let joined with the published relation, with rows or with none, runs on
    # both targets. S16: `reads` feeds forward and reused VALUES lets to every
    # closed read kind beside that JOIN.
    "Q_values_rows": ("top", "rejected", "let_join", "zero_left_join", "reads"),
    # Phase70 S08: closed EXISTS / NOT EXISTS reads in WHERE; S10: lets with
    # capture lines read by them.
    "L_relation_exists": ("kept", "correlated"),
    # Phase70 S07: closed scalar reads in WHERE.
    "L_relation_scalar": ("kept",),
    # Phase70 S09: closed `[not] in` reads; one three-valued SELECT table over
    # empty, duplicated, NULL-only and full candidates, and one WHERE filter
    # over a closed LIMIT let emitted as a top-level CTE; S14: a correlated
    # `in` and a correlated `scalar` read in WHERE.
    "L_relation_membership": ("select_truth", "where_limit", "correlated"),
    # Phase70 S15: PostgreSQL generate_series alone and joined with the
    # published relation; MySQL has no table function in this phase.
    "Q_table_function_series": ("ascending", "joined"),
    # Phase71 S08 (AC-F7, delivered by S12): PostgreSQL Collect reads of the
    # selected query, each one LEFT JOIN LATERAL count-and-arrays carrier;
    # MySQL refuses every Collect read (PIE-B1003).
    "L_relation_collect": COLLECT_VARIANTS,
    "L_retained_collection": ("unnest", "outer"),
    "O_named_later": (
        "self_join",
        "union_dag",
        "two_facades",
        "order_ordinary",
        "order_rebound",
        "order_completed",
        "producer_filter",
    ),
    "P_native_identifiers": (
        "preserve",
        "bind",
        "plain_preserve",
        "plain_bind",
        "named_preserve",
        "named_bind",
        "empty_preserve",
        "empty_bind",
    ),
    # Phase70 S04: one v2 template per literal policy, then the S04r result and
    # post-aggregation positions (PARAMETER_POSITION_VARIANTS) and the S11
    # relation-let reads (`let_bind`); PARAMETER_BINDINGS gives each variant's
    # caller values.
    "Q_query_parameters": (
        "preserve",
        "bind",
        "grouped_null_high",
        "grouped_value_high",
        "grouped_zero_collapse",
        "result_contains_a",
        "result_null_label",
        "let_bind",
        # Decimal, Date and Timestamp, then UUID, header
        # parameters over the Q1 meaning sources (PostgreSQL; MySQL refuses
        # them: `date_of(ratio) == day` and `unset is None` sit outside the
        # MySQL typed cells).
        "typed_timestamp",
        "typed_uuid",
    ),
    "R_fixed_direct": (
        "table_preserve",
        "table_bind",
        "query_preserve",
        "query_bind",
        "empty_preserve",
        "empty_bind",
    ),
    "S_fixed_named": (
        "named_preserve",
        "named_bind",
        "imported_preserve",
        "imported_bind",
        "empty_preserve",
        "empty_bind",
    ),
    "T_row_direct": (
        "table_preserve",
        "query_bind",
        "empty_preserve",
        "truth_table",
    ),
    "U_row_named": ("named_preserve", "imported_bind", "empty_preserve"),
    "W_join_shapes": ("cross", "inner", "semi", "anti"),
    "W_join_values": (
        "left_marker",
        "right_accumulated",
        "via_refined",
        "left_scalar_projections",
    ),
    "V_join_full": ("restricted", "null_keys"),
    # Phase77 S06 (D77.52 O9): `same_value` in a JOIN `on`, unit C on both targets.
    "V_join_nullsafe": ("inner_nulls", "left_nulls", "right_nulls"),
    "V_row_blocked": (
        "float_arithmetic",
        "float_comparison",
        "bool_comparison",
        "int_overflow",
        "unary_overflow",
        "modulo",
        "between",
        "match_join",
    ),
    "X_aggregate_global": ("bag", "empty", "all_null", "where_false"),
    "X_aggregate_grouped": ("hidden", "visible", "empty"),
    "Y_aggregate_constant": ("grouped", "empty"),
    # S05g: an explicit-module computed LET determinant and MAX over a LET value;
    # the bound variant carries every literal as one CTE-stage native parameter.
    # S05j: a determinant computed from both sides of a fanning-out JOIN.
    "Y_aggregate_computed": ("let_key", "bind", "join_key"),
    "Y_aggregate_satisfying": ("retained", "let_reference", "bind", "before_input"),
    "Y_aggregate_domains": ("bool_key", "text_key", "decimal_key"),
    "Z_aggregate_composition": (
        "named",
        "imported",
        "let_where",
        "downstream_filter",
        "source_keys",
    ),
    "Z_aggregate_joined": (
        "inner_fanout",
        "left_nullable",
        "right_accumulated",
        "full_restricted",
    ),
    "Z_aggregate_membership": (
        "semi_global",
        "anti_global",
        "semi_grouped",
        "anti_grouped",
        "filtered_global",
        "satisfying_right",
    ),
    "Z_aggregate_transport": ("outer_null",),
    "A_window_ranking": ("peers",),
    "A_window_distribution": ("spread",),
    "A_window_navigation": ("offsets",),
    "A_window_frame": ("rows", "range"),
    "A_window_groups": ("exclude",),
    "A_window_named": ("shared", "use_local"),
    "A_window_qualify": ("selected", "hidden"),
    "V_window_blocked": ("ignore_nulls", "from_last", "offset_range_keys"),
    "V_aggregate_blocked": (
        "sum_direct",
        "avg_direct",
        "stddev_direct",
        "stddev_float",
        "spread_direct",
        "spread_float",
        "sum_float",
        "avg_float",
        "postgres_carriers",
        "inline_arguments",
        "count_distinct_tuple",
        "sum_hidden_right",
        "float_key",
        "bool_domain_key",
        "decimal_parameter_key",
    ),
    "O_result_distinct": ("visible_int", "null_duplicates", "hidden_group"),
    "O_result_order": (
        "ordinary_desc",
        "nullable_key",
        "constant_key",
        "helper_hidden",
    ),
    "O_result_limit": ("positive", "zero", "inner_then_filter", "filter_then_limit"),
    "O_result_sharing": ("order_limit_self_join",),
    "O_result_membership": ("semi_limit1", "anti_limit1", "semi_limit0", "anti_limit0"),
    "O_result_window": ("qualify_distinct", "selected_order", "qualify_order_limit"),
    "V_result_blocked": ("hidden_strict_fd", "float_distinct", "order_expression"),
    "S_set_forms": (
        "union_all",
        "union_distinct",
        "intersect_all",
        "intersect_distinct",
        "except_all",
        "except_distinct",
    ),
    "S_set_multiplicity": (
        "intersect_all",
        "intersect_distinct",
        "empty_left",
        "empty_right",
    ),
    "S_set_positions": (
        "two_column_intersect_distinct",
        "two_column_except_all",
        "renamed_labels_union_all",
    ),
    "S_set_domains": (
        "text_union_distinct",
        "decimal_intersect_all",
        "big_int_except_all",
        "bool_union_distinct",
        "float_union_all",
        "timestamp_union_all",
        "timestamp_union_distinct",
    ),
    "S_set_nesting": ("left_fold_except", "right_nested_except", "mixed_union_except"),
    "S_set_boundaries": (
        "ordered_operands",
        "limit_zero_operand",
        "distinct_operand",
        "outer_consumer",
    ),
    "S_set_producers": (
        "grouped_union",
        "global_empty_union",
        "satisfying_union",
        "window_union_distinct",
        "set_to_window",
    ),
    "S_set_membership": (
        "semi_except",
        "anti_except",
        "semi_intersect",
        "anti_intersect",
    ),
    "S_set_literals": ("preserve", "bind"),
    "V_set_blocked": (
        "physical_mismatch",
        "float_intersect_all",
        "arity_mismatch",
        "type_mismatch",
    ),
    # Slice15: executed premises of target-side metamorphic laws.
    "M_metamorphic_composition": (
        "join_chain_accumulated",
        "union_filter_outer",
        "union_filter_operands",
    ),
    # Phase72 Lane E: the Float value contract (F2-F5) over the published ±0
    # seeds; `fp_*` bind a header parameter. See FLOAT_BODIES.
    "F_float_values": (
        "fc_where",
        "fc_rows",
        "fp_zeros",
        "fw_windows",
        "fh_average",
        "fh_key",
        "fj_inner",
        "fj_left",
        "fx_any",
        "fx_not_any",
        "fo_ascending",
        "fo_descending",
        "fo_limit",
        "fd_rows",
        "fd_negative",
        "fd_positive",
        "fu_left_right",
        "fu_negative",
        "fi_distinct",
        "fi_all",
        "fi_negative",
        "fe_distinct",
        "fe_all",
        "fe_rows_all",
        "fv_distinct",
        "fv_union",
        "fg_ratio",
        "fg_signed_let",
        "fg_widened",
    ),
}
FLOAT_CASE = "F_float_values"
# Comparisons with a constant operand, membership, nullif, window ratios and
# avg(Int): MySQL emits these in Branch B as well.
FLOAT_ON_BOTH_TARGETS = frozenset(
    {
        "fc_where",
        "fc_rows",
        "fp_zeros",
        "fw_windows",
        "fh_average",
        # MySQL orders a Float by real value too (-0.0 and 0.0 tie).
        "fo_ascending",
        "fo_descending",
        "fo_limit",
        # Phase77 S07: the GROUP BY of one Float field is a cell.
        "fg_ratio",
    }
)
SET_CASES = frozenset(
    {
        "S_set_forms",
        "S_set_multiplicity",
        "S_set_positions",
        "S_set_domains",
        "S_set_nesting",
        "S_set_boundaries",
        "S_set_producers",
        "S_set_membership",
        "S_set_literals",
        "V_set_blocked",
    }
)
RESULT_CASES = frozenset(
    {
        "O_result_distinct",
        "O_result_order",
        "O_result_limit",
        "O_result_sharing",
        "O_result_membership",
        "O_result_window",
        "V_result_blocked",
    }
)
AGGREGATE_CASES = (
    "X_aggregate_global",
    "X_aggregate_grouped",
    "Y_aggregate_constant",
    "Y_aggregate_computed",
    "Y_aggregate_satisfying",
    "Y_aggregate_domains",
    "Z_aggregate_composition",
    "Z_aggregate_joined",
    "Z_aggregate_membership",
    "Z_aggregate_transport",
    "V_aggregate_blocked",
)
LABELS = ("display_text", "record_id", "active", "amount", "ratio")
LOGICAL = ("Text", "Int", "Bool", "Decimal", "Float")
CHAIN_LABELS = (*LABELS, "repeated")
CHAIN_LOGICAL = (*LOGICAL, "Int")
ROW_LABELS = (
    "record_id",
    "next_id",
    "twice",
    "positive",
    "both",
    "missing",
    "same_text",
)
ROW_LOGICAL = ("Int", "Int", "Int", "Bool", "Bool", "Bool", "Bool")
# Every ordered (left, right) pair of TRUE/FALSE/NULL appears once for AND and once
# for OR across these ten outputs and the authored flag column's three values.
TRUTH_LABELS = (
    "and_true",
    "and_false",
    "and_self",
    "true_and",
    "false_and",
    "or_true",
    "or_false",
    "or_self",
    "true_or",
    "false_or",
)
# One reusable scope/qualifier/column grammar per carried column role.
CARRIER_ROLES = {
    "carry_scope": ("carry", "carry_scope", "carry_qualifier", "carry_column"),
    "group_key_scope": (
        "group_key",
        "group_key_scope",
        "group_key_qualifier",
        "group_key_column",
    ),
    "result_scope": ("result", "result_scope", "result_qualifier", "result_column"),
    "window_result_scope": (
        "window_result",
        "window_result_scope",
        "window_result_qualifier",
        "window_result_column",
    ),
}
CARRIED_KINDS = frozenset({"carry", "group_key", "result", "window_result"})
WINDOW_RANK_FUNCTIONS = frozenset({"row_number", "rank", "dense_rank", "ntile"})
WINDOW_DISTRIBUTION_FUNCTIONS = frozenset({"percent_rank", "cume_dist"})
AGGREGATE_SPELLINGS = {
    "COUNT(": "count",
    "SUM(": "sum",
    "AVG(": "avg",
    "MIN(": "min",
    "MAX(": "max",
    "string_agg(": "string_agg",
    "VAR_SAMP(": "stddev",
    "VAR_POP(": "pstdev",
    # `median` writes the fraction 0.5; a `quantile` its literal fraction.
    "PERCENTILE_CONT(": "quantile",
    # `(ARRAY_AGG(x ORDER BY ...))[1]`: `first`, or `last` when its directions
    # are reversed (`aggregate_order_reversed_direction`).
    "ARRAY_AGG(": "first",
}
# The variance aggregates by spelling and square root: a deviation is the
# SQRT of the float8 variance.
SPREAD_FUNCTIONS = {
    ("VAR_SAMP(", True): "stddev",
    ("VAR_SAMP(", False): "variance",
    ("VAR_POP(", True): "pstdev",
    ("VAR_POP(", False): "pvariance",
}
# Phase77 S05: MySQL spells each of the four as its own primitive, uncast and
# never under SQRT, only in the one cell whose primitive was qualified: the
# public token roles below (a relation's namespace and its dot aside), that is
# one global aggregate of one direct source column, selected once. A relation
# `let` (`let x = t`, read through `from x` or not) publishes the same SQL and
# token roles, so this decoder cannot refuse one.
MYSQL_SPREAD_FUNCTIONS = {
    "STDDEV_SAMP(": "stddev",
    "VAR_SAMP(": "variance",
    "VAR_POP(": "pvariance",
    "STDDEV_POP(": "pstdev",
}
MYSQL_SPREAD_CELL_ROLES = (
    "with",
    "cte_name",
    "cte_columns_open",
    "terminal_column",
    "cte_body_open",
    "select",
    "aggregate_open",
    "value_scope",
    "value_qualifier",
    "value_column",
    "aggregate_close",
    "alias",
    "label",
    "from",
    "relation",
    "alias",
    "relation_scope",
    "cte_body_close",
    "with_body",
    "select",
    "result_scope",
    "result_qualifier",
    "result_column",
    "alias",
    "label",
    "from",
    "stage_reference",
    "alias",
    "stage_scope",
    "reference",
    "aggregate",
)
# The eleven admitted Slice9 identities, keyed by the exact emitted call token.
WINDOW_SPELLINGS = {
    "ROW_NUMBER(": "row_number",
    "RANK(": "rank",
    "DENSE_RANK(": "dense_rank",
    "PERCENT_RANK(": "percent_rank",
    "CUME_DIST(": "cume_dist",
    "NTILE(": "ntile",
    "LAG(": "lag",
    "LEAD(": "lead",
    "FIRST_VALUE(": "first_value",
    "LAST_VALUE(": "last_value",
    "NTH_VALUE(": "nth_value",
}
WINDOW_FRAME_UNITS = ("ROWS BETWEEN ", "RANGE BETWEEN ", "GROUPS BETWEEN ")
I64_MIN, I64_MAX = -(1 << 63), (1 << 63) - 1
SIGNED_BITS = {
    "pg_int2": 16,
    "pg_int4": 32,
    "pg_int8": 64,
    "my_smallint": 16,
    "my_int": 32,
    "my_bigint": 64,
    "my_signed_int": 64,
}


def range_thresholds_exact(realization, direction, offsets):
    """R15-INT-OFFSET-V1 from the decoded key alone, independent of production.

    The key's documented domain sits inside its signed storage, and each finite
    endpoint's translation of that whole domain (below the key for ASC PRECEDING
    and DESC FOLLOWING, above it otherwise) stays inside signed64.
    """
    bits = SIGNED_BITS.get(realization["storage"].get("kind"))
    domain = realization["domain"]
    if bits is None or domain.get("kind") != "int_range":
        return False
    low, high = int(domain["min"]), int(domain["max"])
    if not -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1:
        return False
    for suffix, offset in offsets:
        below = (suffix == "PRECEDING") == (direction == "asc")
        lower, upper = (
            (low - offset, high - offset) if below else (low + offset, high + offset)
        )
        if lower < I64_MIN or upper > I64_MAX:
            return False
    return True


GROUPING_TAGS = frozenset(
    {"Int", "Bool", "Text", "Decimal", "Timestamp", "Date", "UUID", "Float"}
)
FINITE_FLOAT = {"kind": "finite_float", "format": "binary64"}


def _pg_finite_float(realization) -> bool:
    """A Float groups, deduplicates, orders and sets by equality only on
    PostgreSQL, over its finite binary64 carrier (MySQL stays refused)."""
    return (
        realization["tag"] == "Float"
        and realization["storage"] == {"kind": "pg_float8"}
        and realization["domain"] == FINITE_FLOAT
    )


def _pg_float_key(realization) -> bool:
    """E6: a PostgreSQL key also takes a window percent_rank/cume_dist
    result, a finite float8 in [0, 1] (domain float64)."""
    return _pg_finite_float(realization) or (
        realization["tag"] == "Float"
        and realization["storage"] == {"kind": "pg_float8"}
        and realization["domain"] == {"kind": "float64"}
    )


def _float_key(realization) -> bool:
    """A GROUP BY key carrier: PostgreSQL's (_pg_float_key) or, since Phase77
    S07, MySQL's finite binary64 DOUBLE, which the product readers admit only
    in their S07 cells."""
    return _pg_float_key(realization) or (
        realization["tag"] == "Float"
        and realization["storage"] == {"kind": "my_double"}
        and realization["domain"] == FINITE_FLOAT
    )


COUNT_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
FLOAT_STORAGE = {"postgres": "pg_float8", "mysql": "my_double"}
COUNT_MAX = (1 << 63) - 1
# Q1/Q2 evidence: a bigint result the target's checked operation bounds.
TARGET_CHECKED = "target_checked_signed64_narrowing"
TARGET_CHECKED_BINARY64 = "target_checked_binary64_overflow"
AGGREGATE_DEMAND_RULES = {
    "aggregation": "R12",
    "group_key": "R12",
    "aggregate": "R13",
    "aggregate_projection": "R12",
    "aggregate_risk": "R12",
}
# R14 owns the occurrence, its input uses and its arguments, R15 the realized
# frame, modifiers and named components, R17 the visible result projection.
WINDOW_DEMAND_RULES = {
    "window": "R14",
    "window_use": "R14",
    "window_argument": "R14",
    "window_policy": "R15",
    "window_projection": "R17",
}
WINDOW_NAVIGATION_FUNCTIONS = frozenset({"lag", "lead"})
# Slice10 result demands: R18 owns the quotient, R19 relation ORDER, R20 the
# pending hidden requirement and R21 the static LIMIT; a boundary is a generated
# scope (R03) and every other result witness keeps the prior generic rule.
# Slice11: every retained SET demand belongs to R22.
SET_DEMAND_RULE = "R22"
RESULT_DEMAND_RULES = {
    "result_boundary": "R03",
    "distinct": "R18",
    "quotient_field": "R18",
    "relation_order": "R19",
    "order_item": "R19",
    "order_expression": "R19",
    "order_use": "R19",
    "hidden_order_requirement": "R20",
    "result_limit": "R21",
}
CODES = {
    "PIE-B1001": "SOURCE_REALIZATION",
    "PIE-B1002": "REPRESENTATION",
    "PIE-B1003": "UNSUPPORTED_RULE",
    "PIE-B1004": "MISSING_EVIDENCE",
    "PIE-B1005": "PREMISE_CONFLICT",
    "PIE-B1006": "UNFULFILLED_REQUIREMENT",
    "PIE-B1007": "TARGET_RESOURCE",
    "PIE-B1008": "ARTIFACT_INTEGRITY",
}


def encoded(value):
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def fixture(target, case="G_emission_table_bag", variant="bag"):
    if (
        target not in {"postgres", "mysql"}
        or case not in VARIANTS
        or variant not in VARIANTS[case]
    ):
        raise ValueError("unknown emission fixture")
    if (case, variant) in CORRECTIVE_BODIES:
        return corrective_fixture(target, case, variant)
    if case == FLOAT_CASE:
        return float_fixture(target, variant)
    if case == "P_native_identifiers":
        return native_fixture(target, variant)
    if case == "Q_query_parameters":
        return parameter_fixture(target, variant)
    if case == "M_metamorphic_composition":
        return metamorphic_fixture(target, variant)
    if case in {"R_fixed_direct", "S_fixed_named"}:
        return fixed_fixture(target, case, variant)
    if case in {"M_named_chain", "N_imported_chain", "O_named_later"}:
        return chain_fixture(target, case, variant)
    if case == "L_let_relations":
        return let_fixture(target, variant)
    if case == "Q_values_rows":
        return values_fixture(target, variant)
    if case == "L_relation_exists":
        return exists_fixture(target, variant)
    if case == "L_relation_scalar":
        return scalar_fixture(target, variant)
    if case == "L_relation_membership":
        return membership_fixture(target, variant)
    if case == "L_relation_collect":
        return collect_fixture(target, variant)
    if case == "L_retained_collection":
        return retained_collection_fixture(target, variant)
    if case == "Q_table_function_series":
        return series_fixture(target, variant)
    if case in {"T_row_direct", "U_row_named", "V_row_blocked"}:
        return row_fixture(target, case, variant)
    if case in WINDOW_CASES:
        return window_fixture(target, case, variant)
    if case in RESULT_CASES:
        return result_fixture(target, case, variant)
    if case in SET_CASES:
        return set_fixture(target, case, variant)
    if case in {"W_join_shapes", "W_join_values", "V_join_full"}:
        return join_fixture(target, case, variant)
    if case in AGGREGATE_CASES:
        return aggregate_fixture(target, case, variant)
    kind = (
        "table"
        if case in {"G_emission_table_bag", "I_emission_table_empty"}
        else "query"
    )
    source = f"""shape Row:
    id: Int
    flag: Bool | None
    text: Text
    money: Decimal(9, 2)
    ratio: Float
source rows: Row = {target}.table("opaque.locator.not.sql")
{kind} result:
    from rows
    select:
        display_text = text
        record_id = id
        active = flag
        amount = money
        ratio
"""
    representations = (
        {
            "storage": {"kind": "pg_int8" if target == "postgres" else "my_bigint"},
            "nullable": False,
            "domain": {
                "kind": "int_range",
                "min": "-9007199254740993",
                "max": "9007199254740993",
            },
        },
        {
            "storage": {"kind": "pg_bool" if target == "postgres" else "my_bool01"},
            "nullable": True,
            "domain": {"kind": "bool01"},
        },
        {
            "storage": {"kind": "pg_text"}
            if target == "postgres"
            else {"kind": "my_varchar", "length": 64},
            "nullable": False,
            "domain": {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8" if target == "postgres" else "utf8mb4",
                "collation": "C" if target == "postgres" else "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        },
        {
            "storage": {
                "kind": "pg_numeric" if target == "postgres" else "my_decimal",
                "precision": 9,
                "scale": 2,
            },
            "nullable": False,
            "domain": {"kind": "decimal", "precision": 9, "scale": 2},
        },
        {
            "storage": {"kind": "pg_float8" if target == "postgres" else "my_double"},
            "nullable": False,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
    )
    contract = {
        "format": "pietto.emission-contract.v1",
        "target": {
            "family": target,
            "release": "18.6" if target == "postgres" else "8.4.12",
        },
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": "rows"},
                "relation": {
                    "namespace": "public" if target == "postgres" else "phase66",
                    "name": "phase66 empty é"
                    if variant == "empty"
                    else "phase66 source é",
                },
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": i,
                        "name": name,
                        "column": column,
                        "representation": representation,
                    }
                    for i, (name, column, representation) in enumerate(
                        zip(
                            ("id", "flag", "text", "money", "ratio"),
                            (
                                "order.id",
                                "flag value",
                                'text `"é',
                                "amount value",
                                "ratio value",
                            ),
                            representations,
                            strict=True,
                        )
                    )
                ],
                "premises": [
                    {"key": key, "scope": "source", "value": True}
                    for key in ("row_domain_matches", "read_only_object")
                ],
            }
        ],
        "environment": [
            {
                "key": "client_encoding",
                "scope": "statement",
                "value": "UTF8" if target == "postgres" else "utf8mb4",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
        ],
    }
    description = contract["sources"][0]
    if variant == "duplicate_selector":
        contract["sources"].append(deepcopy(description))
    elif variant == "ordinal_bool":
        description["fields"][0]["ordinal"] = True
    elif variant == "stale_selector":
        description["selector"]["name"] = "absent"
    elif variant == "missing_source":
        contract["sources"] = []
    elif variant == "bool_domain":
        description["fields"][1]["representation"]["domain"] = {
            "kind": "int_range",
            "min": "0",
            "max": "2",
        }
    elif variant == "decimal_mismatch":
        description["fields"][3]["representation"]["storage"]["scale"] = 1
    elif variant in {"timestamp_meaning", "uuid_meaning"}:
        temporal = variant == "timestamp_meaning"
        source = source.replace(
            "ratio: Float", "ratio: " + ("Timestamp" if temporal else "UUID")
        )
        description["relation"]["name"] = (
            "phase66 timestamp source" if temporal else "phase66 uuid source"
        )
        description["fields"][4]["representation"] = {
            "storage": {
                "kind": ("pg_timestamp" if target == "postgres" else "my_datetime"),
                "fractional_seconds": 6,
            }
            if temporal
            else {"kind": "pg_uuid" if target == "postgres" else "my_uuid_bytes"},
            "nullable": False,
            "domain": {"kind": "timestamp"}
            if temporal
            else {"kind": "uuid", "encoding": "standard_bytes"},
        }
    elif variant == "where_later":
        # The retained filter now realizes a real generated stage scope, so this
        # input must declare the identifier-case premise that scope already
        # required in Slice4. Changed input identity; same source purpose.
        source = source.replace("    select:", "    where id > 0\n    select:")
        contract["environment"].append(
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "quoted_exact"
                if target == "postgres"
                else "lower_case_table_names=0",
            }
        )
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if case in {"H_emission_query_bag", "I_emission_table_empty"}
        else "preserve_literals",
    }


def native_fixture(target, variant):
    base = fixture(target)
    contract = json.loads(base["contract"])
    description = contract["sources"][0]
    description["relation"]["name"] = (
        "phase66 native empty" if variant.startswith("empty") else "phase66 native"
    )
    original = description["fields"][0]["representation"]
    description["fields"] = [
        {
            "ordinal": i,
            "name": name,
            "column": column,
            "representation": {
                "storage": deepcopy(original["storage"]),
                "nullable": i == 3,
                "domain": {"kind": "int_range", "min": "0", "max": "99"},
            },
        }
        for i, (name, column) in enumerate(
            zip(
                ("id", "decoy", "plain", "neighbor"),
                ('%s"', '?"', "%s", "neighbor"),
                strict=True,
            )
        )
    ]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    source = f"""shape Row:
    id: Int
    decoy: Int
    plain: Int
    neighbor: Int | None
source rows: Row = {target}.table("opaque")
"""
    if variant.startswith("named"):
        source += """table first:
    from rows
    select:
        kept = id
query result:
    from first
    select:
        id = kept
"""
    else:
        source += "query result:\n    from rows\n    select:\n        id = "
        source += "plain\n" if variant.startswith("plain") else "id\n"
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if variant.endswith("bind")
        else "preserve_literals",
    }


PARAMETER_BODY = """query result(low: Int, label: Text | None):
    from rows
    where id > low and plain != 3
    select:
        id
        echo = label
        above = low + 1
"""
# Phase70 S04r: header parameters in post-aggregation and result positions over
# the published emission rows. `id` proves over its whole int8 carrier, so on
# MySQL `id * low` binds only low 0 or 1 and `id + high` only high 0 or NULL;
# the product binder refuses any other value before execution (D70.01). On
# PostgreSQL a bound range that meets signed 64 bits binds under the checked
# bigint rule (Q2).
PARAMETER_POSITION_BODIES = {
    # Computed key, LET aggregates, SATISFYING and grouped ORDER over parameters.
    "grouped": """query result(low: Int, high: Int | None):
    from rows
    let k = id * low
    let s = id + high
    group by:
        k
    select:
        k
        c = count()
        n = count(s)
        a = avg(s)
        m = max(s)
    having:
        c > low
    order by:
        n desc
""",
    # A closed builtin value argument, QUALIFY arithmetic and a matched ORDER key.
    "result": """query result(low: Int, label: Text | None):
    from rows
    where contains(text, label)
    select:
        id
        s = id * low
        u = lower(label)
        r = row_number() window(order by id)
    qualify:
        r <= low + 1
    order by:
        id * low
""",
}
# Each S04r variant binds one position body.
PARAMETER_POSITION_VARIANTS = {
    "grouped_null_high": "grouped",
    "grouped_value_high": "grouped",
    "grouped_zero_collapse": "grouped",
    "result_contains_a": "result",
    "result_null_label": "result",
}
# The same result through a relation let that reads both parameters; the
# entry body reads `low` again in a later CTE stage.
PARAMETER_LET_BODY = """query result(low: Int, label: Text | None):
    let kept:
        from rows
        where id > low and plain != 3
        select:
            id
            echo = label
            above = low + 1
    from kept
    where id > low
    select:
        id
        echo
        above
"""
# The caller values of each Q_query_parameters variant, by parameter name.
PARAMETER_BINDINGS = {
    ("Q_query_parameters", "preserve"): {"low": 10, "label": "雪?%s $1"},
    ("Q_query_parameters", "bind"): {"low": -5, "label": None},
    ("Q_query_parameters", "grouped_null_high"): {"low": 1, "high": None},
    ("Q_query_parameters", "grouped_value_high"): {"low": 1, "high": 0},
    ("Q_query_parameters", "grouped_zero_collapse"): {"low": 0, "high": None},
    ("Q_query_parameters", "result_contains_a"): {"low": 1, "label": "a"},
    ("Q_query_parameters", "result_null_label"): {"low": 1, "label": None},
    ("Q_query_parameters", "let_bind"): {"low": 4, "label": "x"},
    ("Q_query_parameters", "typed_timestamp"): {
        "since": datetime(1970, 1, 1),
        "day": date(1970, 1, 1),
        "floor": Decimal("0"),
    },
    ("Q_query_parameters", "typed_uuid"): {
        "key": UUID("00112233-4455-6677-8899-aabbccddeeff"),
        "unset": None,
    },
    (FLOAT_CASE, "fp_zeros"): {"p": -0.0, "q": 0.0},
}


def bindings(case, variant):
    """The caller's header values for one emission variant (None: no header)."""
    return PARAMETER_BINDINGS.get((case, variant))


def parameterized_fixture(
    target,
    body,
    policy="preserve_literals",
    *,
    protocol=True,
    limits=None,
    case="G_emission_table_bag",
    variant="bag",
):
    """The published one-source fixture with ``body`` as its query ``result``.

    The contract adds exact identifier case, ``limits`` as its resource limits
    and, unless ``protocol`` is false, the native parameter protocol every
    parameter read requires. ``case`` and ``variant`` pick the published
    fixture whose header and contract the body reuses.
    """
    base = fixture(target, case, variant)
    contract = json.loads(base["contract"])
    if limits is not None:
        contract["environment"].append(
            {"key": "resource_limits", "scope": "statement", "value": limits}
        )
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if protocol:
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    return {
        "source": base["source"].split("table result:", 1)[0] + body,
        "contract": encoded(contract).decode(),
        "policy": policy,
    }


def scalar_words_world(target, body, policy="preserve_literals"):
    """The qualification world `s12_words` of the MySQL project `lpad` and
    `now()` pairs: source `words` with the published one-source fixture's
    `id` and 64-character `text` fields and `ntext`, a nullable `text`, and
    ``body`` beside it. Returns the source and the contract."""
    contract = json.loads(
        parameterized_fixture(
            target, "", policy, protocol=policy == "bind_safe_literals"
        )["contract"]
    )
    source = contract["sources"][0]
    fields = {field["name"]: field for field in source["fields"]}
    ntext = deepcopy(fields["text"])
    ntext["name"] = ntext["column"] = "ntext"
    ntext["representation"]["nullable"] = True
    source["fields"] = [fields["id"], fields["text"], ntext]
    for ordinal, field in enumerate(source["fields"]):
        field["ordinal"] = ordinal
    source["selector"]["name"] = "words"
    header = (
        "shape Word:\n    id: Int\n    text: Text\n    ntext: Text | None\n"
        f'source words: Word = {target}.table("opaque.locator.not.sql")\n'
    )
    return header + body, encoded(contract).decode()


def scalar_pair_world(target, body, policy="preserve_literals"):
    """The qualification world `s12_pair` of the same pairs: sources `lhs` and
    `rhs` of one keyed shape over the published fixture's `id` field, a
    nullable Int `key` and a nullable `label` Text, and ``body`` beside
    them. Returns the source and the contract."""
    contract = json.loads(
        parameterized_fixture(
            target, "", policy, protocol=policy == "bind_safe_literals"
        )["contract"]
    )
    fields = {field["name"]: field for field in contract["sources"][0]["fields"]}
    key, label = deepcopy(fields["id"]), deepcopy(fields["text"])
    key["name"] = key["column"] = "key"
    label["name"] = label["column"] = "label"
    for field in (key, label):
        field["representation"]["nullable"] = True
    sources = []
    for name in ("lhs", "rhs"):
        source = deepcopy(contract["sources"][0])
        source["fields"] = deepcopy([fields["id"], key, label])
        for ordinal, field in enumerate(source["fields"]):
            field["ordinal"] = ordinal
        source["selector"]["name"] = name
        source["relation"]["name"] = f"phase66 {name} rel"
        sources.append(source)
    contract["sources"] = sources
    header = (
        "shape Row:\n    id: Int\n    key: Int | None\n    label: Text | None\n"
        "    row_key = unique(id)\n"
        f'source lhs: Row = {target}.table("lhs.locator.not.sql")\n'
        f'source rhs: Row = {target}.table("rhs.locator.not.sql")\n'
    )
    return header + body, encoded(contract).decode()


def fieldless_world(target, body, refusal=None):
    """Sources `rows` and `rows2`, whose shape declares only a check and so
    no field, and `items` with the published fixture's `id` field, then
    ``body``. Returns the source and the contract. ``refusal`` is one
    contract change main already refuses: `read_only` drops the
    `read_only_object` premise of `rows`, `naming` the `identifier_case`
    declaration, and `sql_bytes` or `artifact_bytes` sets that limit to 200."""
    contract = json.loads(parameterized_fixture(target, "", protocol=False)["contract"])
    base = contract["sources"][0]
    sources = []
    for name, fields in (("rows", []), ("rows2", []), ("items", base["fields"][:1])):
        source = deepcopy(base)
        source["selector"]["name"] = source["relation"]["name"] = name
        source["fields"] = fields
        sources.append(source)
    contract["sources"] = sources
    environment = contract["environment"]
    if refusal == "read_only":
        premises = sources[0]["premises"]
        premises[:] = [p for p in premises if p["key"] != "read_only_object"]
    elif refusal == "naming":
        environment[:] = [e for e in environment if e["key"] != "identifier_case"]
    elif refusal is not None:
        environment.append(
            {"key": "resource_limits", "scope": "statement", "value": {refusal: 200}}
        )
    header = (
        "shape Row:\n    always = check(True)\nshape Item:\n    id: Int\n"
        + "".join(
            f'source {name}: {shape} = {target}.table("{name}.locator")\n'
            for name, shape in (("rows", "Row"), ("rows2", "Row"), ("items", "Item"))
        )
    )
    return header + body, encoded(contract).decode()


# The bodies of the preregistered native qualification pairs of MySQL project
# `lpad` and `now()` (D74.09), keyed by form id: P-S12-1..6 in the world
# `s12_words` (scalar_words_world), P-S12-7 in `s12_pair` (scalar_pair_world).
# Each is its definition block with `{name}` written `result`.
LPAD_NOW_PAIRS = {
    "s12_lpad_field": """table result:
    from words
    select:
        id
        p5 = lpad(text, 5, "0")
        p7 = lpad(text, 7, "雪")
        p0 = lpad(text, 0, "x")
""",
    "s12_lpad_nullable": """table result:
    from words
    select:
        id
        n5 = lpad(ntext, 5, "0")
        n9 = lpad(ntext, 9, " ")
""",
    "s12_lpad_literal": """table result:
    from words
    select:
        id
        a = lpad("ab", 5, "雪")
        b = lpad("abcdef", 3, "0")
        c = lpad("", 2, "𝄞")
""",
    "s12_lpad_256": """table result:
    from words
    select:
        id
        w = lpad(text, 256, "𝄞")
        z = lpad(ntext, 256, "0")
""",
    "s12_now": """table result:
    from words
    select:
        id
        t1 = now()
        t2 = now()
        t3 = now()
        d = date_of(now())
""",
    "s12_context": """table result:
    from words
    let t = text
    let u = t
    let g = ntext
    where id > 2
    select:
        id
        r = row_number() window(order by id)
        p = lpad(t, 6, "-")
        p2 = lpad(u, 7, "-")
        q = g
        t0 = now()
        d = date_of(now())
""",
    "s12_capture_context": """table result:
    let matched:
        capture lhs
        from rhs
        where rhs.id == lhs.id and rhs.label == "x"
        select:
            id
            label
    from lhs
    select:
        id
        m = scalar matched.label
        a = lpad(label, 5, "0")
        t0 = now()
        d = date_of(now())
""",
}


def lpad_now_world(directory, world, target, body, policy="preserve_literals"):
    """Build one body in a named world: `rows` (the published one-source
    fixture, with the native parameter protocol), `nullable` (the same with a
    nullable `text`), `labelled` (the labelled two-source witness), `temporal`
    (TEMPORAL_FIELDS over `rows`), `words` or `pair` (the pairs' worlds)."""
    if world in ("words", "pair"):
        build = scalar_words_world if world == "words" else scalar_pair_world
        source, contract = build(target, body, policy)
        return build_case(directory, source, contract, policy)
    if world == "temporal":
        entry, block = body.split("\n", 1)
        return temporal_case(directory, target, block, policy, entry=entry)
    if world == "labelled":
        item = labelled_join_witness(target, body, policy=policy)
        return build_case(directory, item["source"], item["contract"], policy)
    item = parameterized_fixture(target, body, policy)
    source, contract = item["source"], item["contract"]
    if world == "nullable":
        source = source.replace("    text: Text\n", "    text: Text | None\n", 1)
        document = json.loads(contract)
        document["sources"][0]["fields"][2]["representation"]["nullable"] = True
        contract = encoded(document).decode()
    return build_case(directory, source, contract, policy)


_L = 'lpad(text, 5, "0")'
_LL = 'lpad(label, 5, "0")'
_PADW = 'def padw(x: Text, w: Int) -> Text: return lpad(x, w, "0")\n'
_CAPTURE = (
    "    let matched:\n        capture lhs\n        from rhs\n"
    '        where rhs.id == lhs.id and rhs.label == "x"\n'
    "        select:\n            id\n            label\n"
)
_RECENT = (
    "    let recent:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            id\n"
)
_IDS = "    let ids:\n        from rhs\n        select:\n            id\n"
_ONE = (
    "    let one:\n        from rhs\n        where rhs.id == 1\n"
    "        select:\n            label\n"
)
_QUALIFY = "    qualify row_number() window(order by id) <= 3\n"
_UPSTREAM = "table base:\n    from rhs\n    select:\n        id\n        label\n"


def _rows(*items, head="", tail="", before="", entry="table result:"):
    lines = "".join(f"        {item}\n" for item in items)
    return f"{before}{entry}\n    from rows\n{head}    select:\n{lines}{tail}"


def _beside(let, *items, before="", head=""):
    """A body of `lhs` beside the relation let(s) ``let``."""
    lines = "".join(f"        {item}\n" for item in items)
    return f"{before}table result:\n{let}    from lhs\n{head}    select:\n{lines}"


def _capturing(*lines):
    """The capturing let `matched` of `lhs` with these body lines."""
    body = "".join(f"        {line}\n" for line in lines)
    return f"    let matched:\n        capture lhs\n{body}"


_READS_BASE = ("from base", "where base.id == lhs.id", "select:", "    label")
_CAPTURE_READS = ("id", "m = scalar matched.label", "a = " + _LL)
_PRESERVE, _BIND_SAFE = "preserve_literals", "bind_safe_literals"
# MySQL project lpad and now() outside their cells, by the rows of the cell
# matrix: the width (B), the text (C), a let (D), a grouped query (E), a
# WHERE (F), result stages (G, H), JOINs (I), other queries (J, K), nested
# calls (L), several refused forms (M), QUALIFY (N), block reads and what a
# capturing let reads (O), header and server parameters (P) and aggregates
# (Q). Each is (world, policy, body). The positions where checking refuses
# now() (PIE-S2387) are the semantic owner's.
LPAD_NOW_REFUSALS = {
    "width_257": ("rows", _PRESERVE, _rows("id", 'p = lpad(text, 257, "0")')),
    "width_16384": ("rows", _PRESERVE, _rows("id", 'p = lpad(text, 16384, "0")')),
    "width_negative": ("rows", _PRESERVE, _rows("id", 'p = lpad(text, -3, "0")')),
    "width_unary_plus": ("rows", _PRESERVE, _rows("id", 'p = lpad(text, +5, "0")')),
    "width_field": ("rows", _PRESERVE, _rows("id", 'p = lpad(text, id, "0")')),
    "width_conditional": (
        "rows",
        _PRESERVE,
        _rows("id", 'p = lpad(text, 5 if id > 1 else 3, "0")'),
    ),
    "width_let": (
        "rows",
        _PRESERVE,
        _rows("id", 'p = lpad(text, w, "0")', head="    let w = 5\n"),
    ),
    "width_def_300": (
        "rows",
        _PRESERVE,
        _rows("id", "p = padw(text, 300)", before=_PADW),
    ),
    "text_let_computed": (
        "rows",
        _PRESERVE,
        _rows("id", 'p = lpad(t, 5, "0")', head="    let t = lower(text)\n"),
    ),
    "text_let_literal": (
        "rows",
        _PRESERVE,
        _rows("id", 'p = lpad(t, 5, "0")', head='    let t = "ab"\n'),
    ),
    "text_alias_of_computed": (
        "rows",
        _PRESERVE,
        _rows(
            "id", 'p = lpad(u, 5, "0")', head="    let t = lower(text)\n    let u = t\n"
        ),
    ),
    "text_conditional": (
        "nullable",
        _PRESERVE,
        _rows("id", 'p = lpad(text if id > 1 else "z", 5, "0")'),
    ),
    "text_coalesce": (
        "nullable",
        _PRESERVE,
        _rows("id", 'p = lpad(coalesce(text, "z"), 5, "0")'),
    ),
    "text_capture_read": (
        "labelled",
        _PRESERVE,
        _beside(_CAPTURE, 'a = lpad(scalar matched.label, 5, "0")'),
    ),
    "lpad_in_let": ("rows", _PRESERVE, _rows("id", "p", head=f"    let p = {_L}\n")),
    "grouped_lpad": (
        "rows",
        _PRESERVE,
        'table result:\n    from rows\n    group by text\n    select:\n        text\n        p = lpad(text, 5, "0")\n        n = count(id)\n',
    ),
    "grouped_now": (
        "rows",
        _PRESERVE,
        "table result:\n    from rows\n    group by text\n    select:\n        text\n        t = now()\n        n = count(id)\n",
    ),
    "grouped_having": (
        "rows",
        _PRESERVE,
        'table result:\n    from rows\n    group by text\n    select:\n        text\n        p = lpad(text, 5, "0")\n        n = count(id)\n    having:\n        n > 0\n',
    ),
    "grouped_without_aggregate": (
        "rows",
        _PRESERVE,
        'table result:\n    from rows\n    group by text\n    select:\n        text\n        p = lpad(text, 5, "0")\n',
    ),
    "lpad_where": ("rows", _PRESERVE, _rows("id", head=f'    where {_L} == "00abc"\n')),
    "now_where": (
        "rows",
        _PRESERVE,
        _rows("id", head="    where date_of(now()) > date_of(now())\n"),
    ),
    "order_other": (
        "rows",
        _PRESERVE,
        _rows("id", f"p = {_L}", tail="    order by id\n"),
    ),
    "order_names_the_item": (
        "rows",
        _PRESERVE,
        _rows("id", f"p = {_L}", tail="    order by p\n"),
    ),
    "limit_only": ("rows", _PRESERVE, _rows("id", f"p = {_L}", tail="    limit 2\n")),
    "limit_only_now": (
        "rows",
        _PRESERVE,
        _rows("id", "t = now()", tail="    limit 2\n"),
    ),
    "distinct": (
        "rows",
        _PRESERVE,
        'table result:\n    from rows\n    select distinct:\n        id\n        p = lpad(text, 5, "0")\n        t = now()\n',
    ),
    "join_inner": (
        "labelled",
        _PRESERVE,
        'table result:\n    from lhs\n    inner join rhs on rhs.id == lhs.id\n    select:\n        id = lhs.id\n        a = lpad(lhs.label, 5, "0")\n        t = now()\n',
    ),
    "join_left": (
        "labelled",
        _PRESERVE,
        'table result:\n    from lhs\n    left join rhs on rhs.id == lhs.id\n    select:\n        id = lhs.id\n        a = lpad(lhs.label, 5, "0")\n',
    ),
    "upstream_cell": (
        "rows",
        _PRESERVE,
        'table a:\n    from rows\n    select:\n        id\n        p = lpad(text, 5, "0")\n\ntable result:\n    from a\n    select:\n        id\n        p\n',
    ),
    "union_operands": (
        "rows",
        _PRESERVE,
        'table a:\n    from rows\n    select:\n        id\n        p = lpad(text, 5, "0")\n\ntable b:\n    from rows\n    select:\n        id\n        p = lpad(text, 5, "1")\n\ntable result:\n    union all a, b\n',
    ),
    "capture_body_lpad": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(
                "from rhs",
                "where rhs.id == lhs.id",
                "select:",
                "    id",
                '    p = lpad(label, 5, "0")',
            ),
            "m = scalar matched.p",
        ),
    ),
    "upstream_named": (
        "rows",
        _PRESERVE,
        'table a:\n    from rows\n    select:\n        id\n        text\n\ntable result:\n    from a\n    select:\n        id\n        p = lpad(text, 5, "0")\n        t = now()\n',
    ),
    "relation_let_from": (
        "rows",
        _PRESERVE,
        'table result:\n    let r:\n        from rows\n        select:\n            id\n            text\n    from r\n    select:\n        id\n        p = lpad(text, 5, "0")\n',
    ),
    "union_input": (
        "rows",
        _PRESERVE,
        'table a:\n    from rows\n    select:\n        id\n        text\n\ntable b:\n    from rows\n    select:\n        id\n        text\n\ntable u:\n    union all a, b\n\ntable result:\n    from u\n    select:\n        id\n        p = lpad(text, 5, "0")\n',
    ),
    "nested_lpad": (
        "rows",
        _PRESERVE,
        _rows("id", 'p = lpad(lpad(text, 3, "0"), 5, "1")'),
    ),
    "lower_of_lpad": ("rows", _PRESERVE, _rows("id", f"p = lower({_L})")),
    "concat_of_lpad": ("rows", _PRESERVE, _rows("id", f'p = concat({_L}, "x")')),
    "len_of_lpad": ("rows", _PRESERVE, _rows("id", f"n = len({_L})")),
    "compare_in_select": ("rows", _PRESERVE, _rows("id", f'b = {_L} == "x"')),
    "now_compare": ("rows", _PRESERVE, _rows("id", "b = now() > now()")),
    "hour_of_now": ("temporal", _PRESERVE, _rows("id", "h = hour(now())")),
    "minute_of_now": ("temporal", _PRESERVE, _rows("id", "m = minute(now())")),
    "date_of_conditional_now": (
        "temporal",
        _PRESERVE,
        _rows("id", "d = date_of(now() if id > 1 else ts)"),
    ),
    "date_of_coalesce_now": (
        "temporal",
        _PRESERVE,
        _rows("id", "d = date_of(coalesce(ts2, now()))"),
    ),
    "cells_beside_concat": (
        "rows",
        _PRESERVE,
        _rows("id", f"p = {_L}", "t = now()", 'c = concat(text, "x")'),
    ),
    "mixed_multi": (
        "labelled",
        _BIND_SAFE,
        'table result:\n    let matched:\n        capture lhs\n        from rhs\n        where rhs.id == lhs.id and rhs.label == "x" and rhs.id > 7\n        select:\n            id\n            label\n    from lhs\n    select:\n        a = lpad(lhs.label, 300, "0")\n        b = lpad(scalar matched.label, 4, "雪")\n        c = now()\n        d = concat(lhs.label, lhs.label)\n',
    ),
    "qualify_lpad_field": ("rows", _PRESERVE, _rows("id", f"p = {_L}", tail=_QUALIFY)),
    "qualify_lpad_literal_bind_safe": (
        "rows",
        _BIND_SAFE,
        _rows("id", 'p = lpad("ab", 5, "0")', tail=_QUALIFY),
    ),
    "qualify_now": ("rows", _PRESERVE, _rows("id", "t = now()", tail=_QUALIFY)),
    "qualify_date_of_now": (
        "rows",
        _PRESERVE,
        _rows("id", "d = date_of(now())", tail=_QUALIFY),
    ),
    "qualify_where_nullable": (
        "nullable",
        _PRESERVE,
        _rows("id", f"p = {_L}", head="    where id > 1\n", tail=_QUALIFY),
    ),
    "qualify_selected_window": (
        "rows",
        _PRESERVE,
        _rows(
            "id",
            "r = row_number() window(order by id)",
            "t = now()",
            tail="    qualify r <= 2\n",
        ),
    ),
    "exists_where": (
        "labelled",
        _PRESERVE,
        _beside(
            _RECENT, "id", "a = " + _LL, "t = now()", head="    where exists recent\n"
        ),
    ),
    "scalar_where": (
        "labelled",
        _PRESERVE,
        _beside(
            _CAPTURE, "id", "a = " + _LL, head='    where scalar matched.label == "x"\n'
        ),
    ),
    "in_where": (
        "labelled",
        _PRESERVE,
        _beside(_IDS, "id", "a = " + _LL, head="    where id in ids\n"),
    ),
    "any_where": (
        "labelled",
        _PRESERVE,
        _beside(
            "", "id", "a = " + _LL, head="    where any(r.id == lhs.id for r in rhs)\n"
        ),
    ),
    "exists_select": (
        "labelled",
        _PRESERVE,
        _beside(_RECENT, "id", "e = exists recent", "a = " + _LL),
    ),
    "in_select": (
        "labelled",
        _PRESERVE,
        _beside(_IDS, "id", "i = id in ids", "a = " + _LL),
    ),
    "any_select": (
        "labelled",
        _PRESERVE,
        _beside("", "id", "y = any(r.id == lhs.id for r in rhs)", "a = " + _LL),
    ),
    "scalar_read_without_capture": (
        "labelled",
        _PRESERVE,
        _beside(_ONE, "id", "m = scalar one.label", "a = " + _LL),
    ),
    "capture_beside_where": (
        "labelled",
        _PRESERVE,
        _beside(_CAPTURE, *_CAPTURE_READS, head="    where id > 1\n"),
    ),
    "capture_beside_row_let": (
        "labelled",
        _PRESERVE,
        _beside(
            _CAPTURE,
            "id",
            "m = scalar matched.label",
            'a = lpad(t, 5, "0")',
            head="    let t = label\n",
        ),
    ),
    "capture_read_inside_an_item": (
        "labelled",
        _PRESERVE,
        _beside(
            _CAPTURE, "id", 'm = coalesce(scalar matched.label, "z")', "a = " + _LL
        ),
    ),
    "capture_reads_no_captured_field": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing("from rhs", "select:", "    id", "    label"),
            *_CAPTURE_READS,
            "t0 = now()",
        ),
    ),
    "capture_reads_an_upstream": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(
                "from base", "where base.id == lhs.id", "select:", "    id", "    label"
            ),
            *_CAPTURE_READS,
            "t0 = now()",
            before=_UPSTREAM + "\n",
        ),
    ),
    "capture_reads_a_relation_let": (
        "labelled",
        _PRESERVE,
        _beside(
            "    let base:\n        from rhs\n        select:\n            id\n            label\n"
            + _capturing(
                "from base", "where base.id == lhs.id", "select:", "    id", "    label"
            ),
            *_CAPTURE_READS,
        ),
    ),
    "capture_reads_an_upstream_window": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(*_READS_BASE),
            *_CAPTURE_READS,
            before=_UPSTREAM + "        r = row_number() window(order by id)\n\n",
        ),
    ),
    "capture_reads_an_upstream_qualify": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(*_READS_BASE),
            *_CAPTURE_READS,
            "t0 = now()",
            before=_UPSTREAM + "    qualify row_number() window(order by id) <= 3\n\n",
        ),
    ),
    "capture_reads_an_upstream_distinct": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(*_READS_BASE),
            *_CAPTURE_READS,
            before="table base:\n    from rhs\n    select distinct:\n        id\n        label\n\n",
        ),
    ),
    "capture_reads_an_upstream_limit": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(*_READS_BASE),
            *_CAPTURE_READS,
            before=_UPSTREAM + "    order by id\n    limit 2\n\n",
        ),
    ),
    "capture_body_order_limit": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(
                "from rhs",
                "where rhs.id == lhs.id",
                "select:",
                "    label",
                "order by id",
                "limit 1",
            ),
            *_CAPTURE_READS,
        ),
    ),
    "capture_body_limit_only": (
        "labelled",
        _PRESERVE,
        _beside(
            _capturing(
                "from rhs", "where rhs.id == lhs.id", "select:", "    label", "limit 1"
            ),
            *_CAPTURE_READS,
        ),
    ),
    "header_parameter_in_where": (
        "rows",
        _PRESERVE,
        _rows(
            "id",
            f"p = {_L}",
            head="    where id > low\n",
            entry="query result(low: Int):",
        ),
    ),
    "header_parameter_in_where_now": (
        "rows",
        _PRESERVE,
        _rows(
            "id",
            "t = now()",
            head="    where id > low\n",
            entry="query result(low: Int):",
        ),
    ),
    "header_parameter_unread": (
        "rows",
        _PRESERVE,
        _rows("id", f"p = {_L}", entry="query result(low: Int):"),
    ),
    "bind_safe_where": (
        "rows",
        _BIND_SAFE,
        _rows("id", f"p = {_L}", head="    where id > 2\n"),
    ),
    "bind_safe_select_literal": (
        "rows",
        _BIND_SAFE,
        _rows("id", f"p = {_L}", 'q = "x"'),
    ),
    "bind_safe_context": ("words", _BIND_SAFE, LPAD_NOW_PAIRS["s12_context"]),
    "bind_safe_capture_context": (
        "pair",
        _BIND_SAFE,
        LPAD_NOW_PAIRS["s12_capture_context"],
    ),
    "having_ungrouped": (
        "rows",
        _PRESERVE,
        _rows("id", f"p = {_L}", tail="    having:\n        id > 0\n"),
    ),
    "global_aggregate": (
        "rows",
        _PRESERVE,
        _rows("n = count(id)", 'p = lpad("ab", 5, "0")', "t = now()"),
    ),
    "global_aggregate_window": (
        "rows",
        _PRESERVE,
        _rows(
            "n = count(id)",
            "r = row_number() window(order by n)",
            'p = lpad("ab", 5, "0")',
        ),
    ),
    "grouped_window": (
        "rows",
        _PRESERVE,
        'table result:\n    from rows\n    group by text\n    select:\n        text\n        r = row_number() window(order by text)\n        p = lpad("ab", 5, "0")\n',
    ),
}


# Each typed variant reads its header over one Q1 meaning source
# (`ratio` is that source's Timestamp or UUID column).
TYPED_PARAMETER_BODIES = {
    "typed_timestamp": (
        "timestamp_meaning",
        """query result(since: Timestamp, day: Date, floor: Decimal(9, 2)):
    from rows
    where ratio >= since and date_of(ratio) == day and money >= floor
    select:
        id
""",
    ),
    "typed_uuid": (
        "uuid_meaning",
        """query result(key: UUID, unset: UUID | None):
    from rows
    where ratio == key and unset is None
    select:
        id
""",
    ),
}


def typed_parameter_fixture(target, variant):
    """A typed v2 template over the Q1 meaning source of ``variant``."""
    meaning, body = TYPED_PARAMETER_BODIES[variant]
    base = fixture(target, "L_emission_blocked", meaning)
    item = parameterized_fixture(target, body)
    contract = json.loads(item["contract"])
    contract["sources"] = json.loads(base["contract"])["sources"]
    return {
        "source": base["source"].split("query result:", 1)[0] + body,
        "contract": encoded(contract).decode(),
        "policy": item["policy"],
    }


def parameter_fixture(target, variant):
    """A v2 template over the native rows: two header parameters, read in WHERE
    and SELECT, and a deferred Int range check (`low + 1`); an S04r variant
    binds one position body over the published emission rows instead, and the
    `let_bind` variant reads them in a relation let and in the entry body."""
    if variant in TYPED_PARAMETER_BODIES:
        return typed_parameter_fixture(target, variant)
    if variant in PARAMETER_POSITION_VARIANTS:
        return parameterized_fixture(
            target, PARAMETER_POSITION_BODIES[PARAMETER_POSITION_VARIANTS[variant]]
        )
    base = native_fixture(target, variant)
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended" if target == "postgres" else "mysql_prepared",
        }
    )
    header = base["source"].split("query result:", 1)[0]
    return {
        "source": header
        + (PARAMETER_LET_BODY if variant.startswith("let") else PARAMETER_BODY),
        "contract": encoded(contract).decode(),
        "policy": base["policy"],
    }


# Slice15. The chain's second JOIN reads the first JOIN unit as its left input, so
# the LEFT nulling must survive into the RIGHT match. The two UNION ALL forms place
# the same NULL-dropping filter over the union or inside each operand.
METAMORPHIC_BODIES = {
    "join_chain_accumulated": """query result:
    from rows
    let r = rows
    left join r on rows.id > r.id
    let last = rows
    right join last on r.id == last.id
    select:
        a = rows.id
        b = last.id
""",
    "union_filter_outer": """table a:
    from rows
    select:
        k = neighbor
table b:
    from rows
    select:
        k = id
table u:
    union all:
        from a
        from b
query result:
    from u
    where k > 10
    select:
        k
""",
    "union_filter_operands": """table a:
    from rows
    where neighbor > 10
    select:
        k = neighbor
table b:
    from rows
    where id > 10
    select:
        k = id
query result:
    union all:
        from a
        from b
""",
}


def metamorphic_fixture(target, variant):
    """The native table, or its one-column `phase66_rows` relative for the chain."""
    base = native_fixture(target, "preserve")
    contract = json.loads(base["contract"])
    header = base["source"].split("query result:", 1)[0]
    if variant == "join_chain_accumulated":
        source = contract["sources"][0]
        source["relation"]["name"] = "phase66_rows"
        source["fields"] = source["fields"][:1]
        source["fields"][0]["column"] = "id"
        header = (
            f'shape One:\n    id: Int\nsource rows: One = {target}.table("opaque")\n'
        )
    return {
        "source": header + METAMORPHIC_BODIES[variant],
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


FIXED_LABELS = (
    "id",
    "neighbor",
    "truth",
    "lie",
    "one",
    "real_one",
    "zero",
    "positive",
    "negative",
    "positive_zero",
    "negative_zero",
    "fraction",
    "big",
    "equal_a",
    "equal_b",
    "empty_text",
    "trailing_text",
    "unicode_text",
    "markers",
    "escaped",
)
FIXED_TAGS = (
    "Int",
    "Int",
    "Bool",
    "Bool",
    "Int",
    "Float",
    "Int",
    "Int",
    "Int",
    "Float",
    "Float",
    "Float",
    "Int",
    "Int",
    "Int",
    "Text",
    "Text",
    "Text",
    "Text",
    "Text",
)
FIXED_NAMED_LABELS = ("id", "neighbor", "literal", "again", "ratio", "zero", "added")
FIXED_NAMED_TAGS = ("Int", "Int", "Int", "Int", "Float", "Float", "Text")


def fixed_fixture(target, case, variant):
    base = native_fixture(
        target, "empty_preserve" if variant.startswith("empty") else "preserve"
    )
    contract = json.loads(base["contract"])
    bound = variant.endswith("bind")
    if bound:
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = base["source"].split("query result:", 1)[0]
    if case == "R_fixed_direct":
        expressions = (
            "id",
            "neighbor",
            "True",
            "False",
            "1",
            "1.0",
            "0",
            "+2",
            "-2",
            "+0.0",
            "-0.0",
            "-1.5",
            "9007199254740993",
            "17",
            "17",
            json.dumps("", ensure_ascii=False),
            json.dumps("a  ", ensure_ascii=False),
            json.dumps("雪e\u0301😀", ensure_ascii=False),
            json.dumps("? %s $1", ensure_ascii=False),
            json.dumps("\"'\\\n", ensure_ascii=False),
        )
        kind = "table" if variant.startswith("table") else "query"
        source = header + f"{kind} result:\n    from rows\n    select:\n"
        source += "".join(
            f"        {label} = {expression}\n"
            for label, expression in zip(FIXED_LABELS, expressions, strict=True)
        )
    else:
        first = """table first:
    from rows
    select:
        id
        neighbor
        base = 17
        unused = True
        zero = -0.0
"""
        second = """table second:
    from first
    select:
        record_id = id
        neighbor
        renamed = base
        repeated = base
        ratio = 1.5
        zero
"""
        final = """query result:
    from second
    select:
        id = record_id
        neighbor
        literal = renamed
        again = repeated
        ratio
        zero
        added = "雪?%s $1"
"""
        source = header + first + second + final
        if variant.startswith("imported"):
            source = {
                "a.pietto": header + first + "export table first\n",
                "b.pietto": 'from "a.pietto" import table first as Public\nexport table Public\n',
                "main.pietto": 'from "b.pietto" import table Public as Alias\n'
                + second.replace("from first", "from Alias")
                + final,
            }
            contract["sources"][0]["selector"]["module"] = "a.pietto"
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals" if bound else "preserve_literals",
    }


# One shape over five modest fixed aggregation inputs. Every case below names the
# exact relation it reads, so one authored surface covers empty, all-null, fanout
# and membership inputs without multiplying declarations.
AGGREGATE_HEADER = """shape Agg:
    key: Int | None
    value: Int | None
    flag: Bool | None
    label: Text
    amount: Decimal(9, 2)
    ratio: Float
    rid: Int
    agg_row = unique(rid)
source agg: Agg = {target}.table("aggregate.locator.not.sql")
"""
AGGREGATE_KEYS_SOURCE = 'source keys: Agg = {target}.table("keys.locator.not.sql")\n'
AGGREGATE_COLUMNS = (
    ("key", "group key"),
    ("value", "value é"),
    ("flag", "flag value"),
    ("label", 'text `"é'),
    ("amount", "amount value"),
    ("ratio", "ratio value"),
    ("rid", "row id"),
)
AGGREGATE_RELATIONS = {
    "grouped": "phase66 agg é",
    "empty": "phase66 agg empty é",
    "trio": "phase66 agg trio é",
    "nulls": "phase66 agg nulls é",
    "keys": "phase66 agg keys é",
    "dupes": "phase66 agg dupes é",
    # Slice11 SET witnesses: C17 operands, a common-class multiplicity partner
    # and the membership left side.
    "sa": "phase66 set left é",
    "sb": "phase66 set right é",
    "sc": "phase66 set sextet é",
    "sl": "phase66 set outer é",
}
# Which fixed relation each variant's `agg` source reads. `keys` is always the
# four-occurrence left input when a case declares it.
AGGREGATE_INPUTS = {
    ("X_aggregate_global", "bag"): "trio",
    ("X_aggregate_global", "empty"): "empty",
    ("X_aggregate_global", "all_null"): "nulls",
    ("X_aggregate_global", "where_false"): "trio",
    ("X_aggregate_grouped", "empty"): "empty",
    ("Y_aggregate_constant", "empty"): "empty",
    ("Z_aggregate_membership", "semi_global"): "empty",
    ("Z_aggregate_membership", "anti_global"): "empty",
    ("Z_aggregate_membership", "semi_grouped"): "empty",
    ("Z_aggregate_membership", "anti_grouped"): "empty",
    ("Z_aggregate_membership", "filtered_global"): "empty",
}
GLOBAL_BODY = """query result:
    from agg
{filter}    select:
        c = count()
        cf = count(value)
        cd = count_distinct(value)
        lo = min(value)
        hi = max(value)
"""
# The determinant is the established LET column and only that column is grouped;
# MAX reads another LET column and keeps that value's own proven range.
AGGREGATE_COMPUTED = """query result:
    from agg
    let bucket = 1 if key > 1 else 0
    let weight = 2 if value > 15 else 1
    group by:
        bucket
    select:
        b = bucket
        total = count()
        top = max(weight)
"""
# S05j: the determinant reads both JOIN sides (and a literal); only the LET
# column it establishes is grouped, and COUNT(*) counts joined occurrences.
# MIN/MAX read the joined LET value `level`, which is the right side's rid.
AGGREGATE_COMPUTED_JOIN = """query result:
    from agg
    let r = agg
    inner join r on agg.key == r.key
    let later = agg.rid > r.rid or r.rid > 12
    let level = r.rid + agg.rid * 0
    group by:
        later
    select:
        b = later
        total = count()
        low = min(level)
        top = max(level)
"""
GROUPED_HIDDEN = """query result:
    from agg
    group by:
        key
    select:
        total = count()
        cf = count(value)
"""
AGGREGATE_BODIES = {
    ("X_aggregate_global", "bag"): GLOBAL_BODY.format(filter=""),
    ("X_aggregate_global", "empty"): GLOBAL_BODY.format(filter=""),
    ("X_aggregate_global", "all_null"): GLOBAL_BODY.format(filter=""),
    # A pre-input filter that keeps no row must not erase the one GLOBAL row.
    ("X_aggregate_global", "where_false"): GLOBAL_BODY.format(
        filter="    where key > 100\n"
    ),
    ("X_aggregate_grouped", "hidden"): GROUPED_HIDDEN,
    ("X_aggregate_grouped", "empty"): GROUPED_HIDDEN,
    ("X_aggregate_grouped", "visible"): """query result:
    from agg
    group by:
        key
        flag
    select:
        f = flag
        renamed = key
        again = key
        total = count()
""",
    ("Y_aggregate_constant", "empty"): """table marked:
    from agg
    select:
        pid = key
        marker = 1
query result:
    from marked
    group by:
        marker
    select:
        c0 = marker
        total = count()
""",
    ("Y_aggregate_constant", "grouped"): """table marked:
    from agg
    select:
        pid = key
        marker = 1
query result:
    from marked
    group by:
        marker
    select:
        c0 = marker
        total = count()
""",
    ("Y_aggregate_satisfying", "retained"): """query result:
    from agg
    group by:
        key
    select:
        k = key
        total = count()
        lo = min(value)
    having:
        total < 2 and lo > 5 and total >= 1
""",
    ("Y_aggregate_satisfying", "let_reference"): """query result:
    from agg
    let taken = value
    group by:
        key
    select:
        k = key
        total = count(taken)
    having:
        total > 0 and count(taken) < 2
""",
    ("Y_aggregate_satisfying", "before_input"): """query result:
    from agg
    where value > 5
    group by:
        key
    select:
        k = key
        total = count()
        lo = min(value)
""",
    ("Y_aggregate_domains", "bool_key"): """query result:
    from agg
    group by:
        flag
    select:
        f = flag
        total = count()
""",
    ("Y_aggregate_domains", "text_key"): """query result:
    from agg
    group by:
        label
    select:
        t = label
        total = count()
""",
    ("Y_aggregate_domains", "decimal_key"): """query result:
    from agg
    group by:
        amount
    select:
        m = amount
        total = count()
""",
    ("Y_aggregate_computed", "let_key"): AGGREGATE_COMPUTED,
    ("Y_aggregate_computed", "bind"): AGGREGATE_COMPUTED,
    ("Y_aggregate_computed", "join_key"): AGGREGATE_COMPUTED_JOIN,
    ("Z_aggregate_composition", "let_where"): """query result:
    from agg
    let taken = value
    where key > 0
    group by:
        key
    select:
        k = key
        total = count()
        cf = count(taken)
""",
    ("Z_aggregate_composition", "downstream_filter"): """table grouped:
    from agg
    group by:
        key
    select:
        k = key
        total = count()
query result:
    from grouped
    where total > 1
    select:
        a = k
        b = total
""",
    # A non-unique join key multiplies occurrences, so this count is the joined
    # occurrence count, never a unique base-entity count.
    ("Z_aggregate_joined", "inner_fanout"): """query result:
    from agg
    let r = agg
    inner join r on agg.key == r.key
    group by:
        agg.key
    select:
        k = agg.key
        total = count()
""",
    # A right-side field aggregate needs the retained unique-row grain, so this
    # LEFT joins on that unique key: an unmatched left occurrence still counts.
    ("Z_aggregate_joined", "left_nullable"): """query result:
    from keys
    let r = agg
    left join r on keys.rid == r.rid
    group by:
        keys.rid
    select:
        k = keys.rid
        total = count()
        cf = count(r.value)
""",
    ("Z_aggregate_transport", "outer_null"): """table grouped:
    from agg
    group by:
        key
    select:
        k = key
        total = count()
query result:
    from keys
    let r = grouped
    left join r on keys.key == r.k
    select:
        a = keys.key
        b = r.total
""",
    ("V_aggregate_blocked", "sum_direct"): """query result:
    from agg
    select:
        s = sum(value)
""",
    ("V_aggregate_blocked", "avg_direct"): """query result:
    from agg
    select:
        a = avg(value)
""",
    ("V_aggregate_blocked", "stddev_direct"): """query result:
    from agg
    select:
        d = stddev(value)
""",
    ("V_aggregate_blocked", "stddev_float"): """query result:
    from agg
    select:
        d = stddev(ratio)
""",
    ("V_aggregate_blocked", "spread_direct"): """query result:
    from agg
    select:
        v = variance(rid)
        pv = pvariance(rid)
        ps = pstdev(rid)
""",
    ("V_aggregate_blocked", "spread_float"): """query result:
    from agg
    select:
        v = variance(ratio)
        pv = pvariance(ratio)
        ps = pstdev(ratio)
""",
    ("V_aggregate_blocked", "sum_float"): """query result:
    from agg
    select:
        s = sum(ratio)
""",
    ("V_aggregate_blocked", "avg_float"): """query result:
    from agg
    select:
        a = avg(ratio)
""",
    ("V_aggregate_blocked", "postgres_carriers"): """query result:
    from agg
    select:
        n = count(label)
        d = count_distinct(label)
        f = count_distinct(flag)
        lo = min(amount)
        hi = max(ratio)
""",
    ("V_aggregate_blocked", "inline_arguments"): """query result:
    from agg
    select:
        s = sum(value * 2)
        c = count(value + 1)
        a = avg(value + 1)
""",
    ("V_aggregate_blocked", "count_distinct_tuple"): """query result:
    from agg
    select:
        lf = count_distinct(label, flag)
        ar = count_distinct(amount, ratio)
        kv = count_distinct(key, value)
        lr = count_distinct(label, amount, rid)
""",
    ("V_aggregate_blocked", "sum_hidden_right"): """table g:
    from agg
    select:
        total = sum(value)
query result:
    from keys
    let r = g
    where any(keys.key == r.total for r in r)
    select:
        a = keys.key
""",
    ("V_aggregate_blocked", "float_key"): """query result:
    from agg
    group by:
        ratio
    select:
        r = ratio
        total = count()
""",
    ("V_aggregate_blocked", "bool_domain_key"): """query result:
    from agg
    group by:
        flag
    select:
        f = flag
        total = count()
""",
    ("V_aggregate_blocked", "decimal_parameter_key"): """query result:
    from agg
    group by:
        amount
    select:
        m = amount
        total = count()
""",
}
AGGREGATE_NAMED = """table grouped:
    from agg
    group by:
        key
    select:
        k = key
        total = count()
"""
AGGREGATE_LEFTISH = """table leftish:
    from agg
    where key > 1
    select:
        lid = rid
"""
AGGREGATE_MEMBERSHIP = """query result:
    from keys
    let r = g
    where {negation}any(keys.key == r.{port} for r in r)
    select:
        a = keys.key
"""
AGGREGATE_LABELS = {
    ("X_aggregate_global", None): ("c", "cf", "cd", "lo", "hi"),
    ("X_aggregate_grouped", "hidden"): ("total", "cf"),
    ("X_aggregate_grouped", "empty"): ("total", "cf"),
    ("X_aggregate_grouped", "visible"): ("f", "renamed", "again", "total"),
    ("Y_aggregate_constant", None): ("c0", "total"),
    ("Y_aggregate_computed", None): ("b", "total", "top"),
    ("Y_aggregate_computed", "join_key"): ("b", "total", "low", "top"),
    ("Y_aggregate_satisfying", "retained"): ("k", "total", "lo"),
    ("Y_aggregate_satisfying", "bind"): ("k", "total", "lo"),
    ("Y_aggregate_satisfying", "before_input"): ("k", "total", "lo"),
    ("Y_aggregate_satisfying", "let_reference"): ("k", "total"),
    ("Y_aggregate_domains", "bool_key"): ("f", "total"),
    ("Y_aggregate_domains", "text_key"): ("t", "total"),
    ("Y_aggregate_domains", "decimal_key"): ("m", "total"),
    ("Z_aggregate_composition", "named"): ("a", "b"),
    ("Z_aggregate_composition", "imported"): ("a", "b"),
    ("Z_aggregate_composition", "let_where"): ("k", "total", "cf"),
    ("Z_aggregate_composition", "downstream_filter"): ("a", "b"),
    ("Z_aggregate_composition", "source_keys"): ("i", "t", "total"),
    ("Z_aggregate_joined", "inner_fanout"): ("k", "total"),
    ("Z_aggregate_joined", "left_nullable"): ("k", "total", "cf"),
    ("Z_aggregate_joined", "right_accumulated"): ("k", "total"),
    ("Z_aggregate_joined", "full_restricted"): ("k", "total"),
    ("Z_aggregate_membership", None): ("a",),
    ("Z_aggregate_transport", None): ("a", "b"),
    ("V_aggregate_blocked", "avg_direct"): ("a",),
    ("V_aggregate_blocked", "stddev_direct"): ("d",),
    ("V_aggregate_blocked", "stddev_float"): ("d",),
    ("V_aggregate_blocked", "spread_direct"): ("v", "pv", "ps"),
    ("V_aggregate_blocked", "spread_float"): ("v", "pv", "ps"),
    ("V_aggregate_blocked", "sum_float"): ("s",),
    ("V_aggregate_blocked", "avg_float"): ("a",),
    ("V_aggregate_blocked", "postgres_carriers"): ("n", "d", "f", "lo", "hi"),
    ("V_aggregate_blocked", "inline_arguments"): ("s", "c", "a"),
    ("V_aggregate_blocked", "count_distinct_tuple"): ("lf", "ar", "kv", "lr"),
    ("V_aggregate_blocked", "sum_direct"): ("s",),
    ("V_aggregate_blocked", "sum_hidden_right"): ("a",),
}
AGGREGATE_LOGICAL = {
    ("X_aggregate_global", None): ("Int",) * 5,
    ("X_aggregate_grouped", "hidden"): ("Int", "Int"),
    ("X_aggregate_grouped", "empty"): ("Int", "Int"),
    ("X_aggregate_grouped", "visible"): ("Bool", "Int", "Int", "Int"),
    ("Y_aggregate_constant", None): ("Int", "Int"),
    ("Y_aggregate_computed", None): ("Int", "Int", "Int"),
    ("Y_aggregate_computed", "join_key"): ("Bool", "Int", "Int", "Int"),
    ("Y_aggregate_satisfying", "retained"): ("Int", "Int", "Int"),
    ("Y_aggregate_satisfying", "bind"): ("Int", "Int", "Int"),
    ("Y_aggregate_satisfying", "before_input"): ("Int", "Int", "Int"),
    ("Y_aggregate_satisfying", "let_reference"): ("Int", "Int"),
    ("Y_aggregate_domains", "bool_key"): ("Bool", "Int"),
    ("Y_aggregate_domains", "text_key"): ("Text", "Int"),
    ("Y_aggregate_domains", "decimal_key"): ("Decimal", "Int"),
    ("Z_aggregate_composition", "named"): ("Int", "Int"),
    ("Z_aggregate_composition", "imported"): ("Int", "Int"),
    ("Z_aggregate_composition", "let_where"): ("Int", "Int", "Int"),
    ("Z_aggregate_composition", "downstream_filter"): ("Int", "Int"),
    ("Z_aggregate_composition", "source_keys"): ("Int", "Text", "Int"),
    ("Z_aggregate_joined", "inner_fanout"): ("Int", "Int"),
    ("Z_aggregate_joined", "left_nullable"): ("Int", "Int", "Int"),
    ("Z_aggregate_joined", "right_accumulated"): ("Int", "Int"),
    ("Z_aggregate_joined", "full_restricted"): ("Int", "Int"),
    ("Z_aggregate_membership", None): ("Int",),
    ("Z_aggregate_transport", None): ("Int", "Int"),
    ("V_aggregate_blocked", "avg_direct"): ("Float",),
    ("V_aggregate_blocked", "stddev_direct"): ("Float",),
    ("V_aggregate_blocked", "stddev_float"): ("Float",),
    ("V_aggregate_blocked", "spread_direct"): ("Float",) * 3,
    ("V_aggregate_blocked", "spread_float"): ("Float",) * 3,
    ("V_aggregate_blocked", "sum_float"): ("Float",),
    ("V_aggregate_blocked", "avg_float"): ("Float",),
    ("V_aggregate_blocked", "postgres_carriers"): (
        "Int",
        "Int",
        "Int",
        "Decimal",
        "Float",
    ),
    ("V_aggregate_blocked", "inline_arguments"): ("Int", "Int", "Float"),
    ("V_aggregate_blocked", "count_distinct_tuple"): ("Int",) * 4,
    ("V_aggregate_blocked", "sum_direct"): ("Int",),
    ("V_aggregate_blocked", "sum_hidden_right"): ("Int",),
}


def aggregate_labels(table, case, variant):
    return table.get((case, variant)) or table[case, None]


def aggregate_source(target, case, variant):
    """The authored module text of one aggregate case, as one string or module map."""
    if case == "Y_aggregate_satisfying" and variant == "bind":
        return AGGREGATE_BODIES["Y_aggregate_satisfying", "retained"]
    if case == "Z_aggregate_membership":
        if variant == "satisfying_right":
            producer = (
                AGGREGATE_NAMED.replace("table grouped:", "table g:")
                + "    having:\n        total < 2\n"
            )
            return producer + AGGREGATE_MEMBERSHIP.format(negation="", port="k")
        if variant == "filtered_global":
            return (
                "table g:\n    from agg\n    select:\n        total = count()\n"
                "table f:\n    from g\n    where total > 0\n"
                "    select:\n        t = total\n"
                + AGGREGATE_MEMBERSHIP.format(negation="", port="t").replace(
                    "let r = g", "let r = f"
                )
            )
        if variant.endswith("global"):
            producer = "table g:\n    from agg\n    select:\n        total = count()\n"
            port = "total"
        else:
            producer = AGGREGATE_NAMED.replace("table grouped:", "table g:")
            port = "k"
        negation = "" if variant.startswith("semi") else "not "
        return producer + AGGREGATE_MEMBERSHIP.format(negation=negation, port=port)
    if case == "Z_aggregate_joined" and variant in {
        "right_accumulated",
        "full_restricted",
    }:
        kind = "right" if variant == "right_accumulated" else "full"
        return (
            AGGREGATE_LEFTISH
            + f"""query result:
    from leftish
    let r = agg
    {kind} join r on leftish.lid == r.key
    group by:
        r.key
    select:
        k = r.key
        total = count()
"""
        )
    if case == "Z_aggregate_composition" and variant in {"named", "imported"}:
        consumer = """query result:
    from grouped
    select:
        a = k
        b = total
"""
        if variant == "named":
            return AGGREGATE_NAMED + consumer
        return {
            "a.pietto": "{header}" + AGGREGATE_NAMED + "export table grouped\n",
            "b.pietto": 'from "a.pietto" import table grouped as Public\n'
            "export table Public\n",
            "main.pietto": 'from "b.pietto" import table Public as Alias\n'
            + consumer.replace("from grouped", "from Alias"),
        }
    return AGGREGATE_BODIES[case, variant]


def _aggregate_representations(target):
    integer = {
        "storage": {"kind": "pg_int8" if target == "postgres" else "my_bigint"},
        "nullable": True,
        "domain": {
            "kind": "int_range",
            "min": "-9007199254740993",
            "max": "9007199254740993",
        },
    }
    return (
        deepcopy(integer),
        deepcopy(integer),
        {
            "storage": {"kind": "pg_bool" if target == "postgres" else "my_bool01"},
            "nullable": True,
            "domain": {"kind": "bool01"},
        },
        {
            "storage": {"kind": "pg_text"}
            if target == "postgres"
            else {"kind": "my_varchar", "length": 64},
            "nullable": False,
            "domain": {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8" if target == "postgres" else "utf8mb4",
                "collation": "C" if target == "postgres" else "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        },
        {
            "storage": {
                "kind": "pg_numeric" if target == "postgres" else "my_decimal",
                "precision": 9,
                "scale": 2,
            },
            "nullable": False,
            "domain": {"kind": "decimal", "precision": 9, "scale": 2},
        },
        {
            "storage": {"kind": "pg_float8" if target == "postgres" else "my_double"},
            "nullable": False,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
        {
            "storage": {"kind": "pg_int8" if target == "postgres" else "my_bigint"},
            "nullable": False,
            "domain": {
                "kind": "int_range",
                "min": "-9007199254740993",
                "max": "9007199254740993",
            },
        },
    )


def _aggregate_descriptor(target, name, relation):
    return {
        "selector": {"module": "main.pietto", "kind": "source", "name": name},
        "relation": {
            "namespace": "public" if target == "postgres" else "phase66",
            "name": relation,
        },
        "scan": "relation_rows",
        "fields": [
            {
                "ordinal": i,
                "name": field,
                "column": column,
                "representation": representation,
            }
            for i, ((field, column), representation) in enumerate(
                zip(
                    AGGREGATE_COLUMNS,
                    _aggregate_representations(target),
                    strict=True,
                )
            )
        ],
        "premises": [
            {"key": key, "scope": "source", "value": True}
            for key in ("row_domain_matches", "read_only_object")
        ],
    }


def nullable_ratio_fixture(target, body, policy="preserve_literals"):
    """Phase77 S05: one body over the aggregation source whose `ratio` is a
    nullable Float (a nullable DOUBLE on MySQL), the one carrier the raw
    statistics qualification ran."""
    item = aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    contract = json.loads(item["contract"])
    for source in contract["sources"]:
        for field in source["fields"]:
            if field["name"] == "ratio":
                field["representation"]["nullable"] = True
    if policy == "bind_safe_literals":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = AGGREGATE_HEADER.format(target=target)
    return {
        "source": header.replace("    ratio: Float\n", "    ratio: Float | None\n")
        + body,
        "contract": encoded(contract).decode(),
        "policy": policy,
    }


def aggregate_fixture(target, case, variant):
    """One aggregation case over the fixed inputs, with its own exact contract."""
    if (case, variant) == ("Z_aggregate_composition", "source_keys"):
        base = fixture(target)
        base_source = base["source"]
        assert type(base_source) is str
        contract = json.loads(base["contract"])
        contract["environment"].append(
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "quoted_exact"
                if target == "postgres"
                else "lower_case_table_names=0",
            }
        )
        source = base_source.split("query result:", 1)[0].split("table result:", 1)[0]
        source += """query result:
    from rows
    group by:
        id
        text
    select:
        i = id
        t = text
        total = count()
"""
        return {
            "source": source,
            "contract": encoded(contract).decode(),
            "policy": "preserve_literals",
        }
    keyed = (
        case in {"Z_aggregate_membership", "Z_aggregate_transport"}
        or (
            case,
            variant,
        )
        == ("Z_aggregate_joined", "left_nullable")
        or (
            case,
            variant,
        )
        == ("V_aggregate_blocked", "sum_hidden_right")
    )
    relation = AGGREGATE_RELATIONS[AGGREGATE_INPUTS.get((case, variant), "grouped")]
    header = AGGREGATE_HEADER.format(target=target)
    if keyed:
        header += AGGREGATE_KEYS_SOURCE.format(target=target)
    body = aggregate_source(target, case, variant)
    source: str | dict[str, str]
    if type(body) is dict:
        modules = {
            name: content.replace("{header}", header) for name, content in body.items()
        }
        modules["main.pietto"] = header + modules["main.pietto"]
        source = modules
    else:
        assert type(body) is str
        source = header + body
    contract = {
        "format": "pietto.emission-contract.v1",
        "target": {
            "family": target,
            "release": "18.6" if target == "postgres" else "8.4.12",
        },
        "sources": [_aggregate_descriptor(target, "agg", relation)],
        "environment": [
            {
                "key": "client_encoding",
                "scope": "statement",
                "value": "UTF8" if target == "postgres" else "utf8mb4",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "quoted_exact"
                if target == "postgres"
                else "lower_case_table_names=0",
            },
        ],
    }
    if keyed:
        contract["sources"].append(
            _aggregate_descriptor(target, "keys", AGGREGATE_RELATIONS["keys"])
        )
    if type(source) is dict:
        contract["sources"][0]["selector"]["module"] = "a.pietto"
    if variant == "bind":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    if variant == "bool_domain_key":
        contract["sources"][0]["fields"][2]["representation"]["domain"] = {
            "kind": "int_range",
            "min": "0",
            "max": "2",
        }
    elif variant == "decimal_parameter_key":
        contract["sources"][0]["fields"][4]["representation"]["storage"]["scale"] = 1
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals" if variant == "bind" else "preserve_literals",
    }


def ordered_string_agg_witness(target):
    """One C5 ordered aggregate witness outside the historical generation corpus."""

    item = aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    return {
        **item,
        "source": AGGREGATE_HEADER.format(target=target)
        + """table result:
    from agg
    select:
        summary = string_agg(label, "//", order by key desc, key desc)
""",
        "case": "C5_ordered_string_agg",
        "variant": "duplicate_desc",
    }


def chain_fixture(target, case, variant):
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    text_label = (
        "intermediate_" + "x" * 280 if variant == "long_intermediate" else "TextValue"
    )
    first_kind = "query" if variant == "query_bag" else "table"
    first = f"""{first_kind} first:
    from rows
    select:
        {text_label} = text
        Key = id
        key = money
        FlagValue = flag
        AmountValue = money
        RatioValue = ratio
        omitted = text
"""
    second = f"""table second:
    from first
    select:
        amount2 = key
        txt2 = {text_label}
        id2 = Key
        flag2 = FlagValue
        ratio2 = RatioValue
        again = Key
"""
    final_kind = "table" if variant == "table_bag" else "query"
    final = f"""{final_kind} result:
    from second
    select:
        display_text = txt2
        record_id = id2
        active = flag2
        amount = amount2
        ratio = ratio2
        repeated = again
"""
    source: str | dict[str, str] = header + first + second + final
    description = contract["sources"][0]
    if variant == "empty":
        description["relation"]["name"] = "phase66 empty é"
    if case == "N_imported_chain" or variant == "two_facades":
        source = {
            "a.pietto": header + first + "export table first\n",
            "b.pietto": 'from "a.pietto" import table first as Public\nexport table Public\n',
            "main.pietto": 'from "b.pietto" import table Public as Alias\n'
            + second.replace("from first", "from Alias")
            + final,
        }
        description["selector"]["module"] = "a.pietto"
        if variant != "empty":
            description["relation"]["name"] = "p0"
        if variant == "two_facades":
            source["c.pietto"] = source["b.pietto"]
            source["main.pietto"] = """from "b.pietto" import table Public as Left
from "c.pietto" import table Public as Right
query result:
    union all:
        from Left
        from Right
"""
    elif case == "O_named_later":
        if variant == "self_join":
            source = (
                header
                + first
                + """query result:
    from first
    let r = first
    inner join r on first.Key == r.Key
    select:
        id = first.Key
"""
            )
        elif variant == "union_dag":
            chain_text = header + first
            previous = "first"
            for i in range(3):
                chain_text += f"table shared{i}:\n    union all:\n        from {previous}\n        from {previous}\n"
                previous = f"shared{i}"
            source = (
                chain_text
                + f"query result:\n    from {previous}\n    select:\n        Key\n"
            )
        elif variant == "order_ordinary":
            source = (
                header
                + first
                + """query result:
    from first
    select:
        Key
    order by:
        Key
"""
            )
        elif variant == "order_rebound":
            source = (
                header
                + """table upstream:
    from rows
    select:
        id
        w = row_number() window(order by id)
    qualify:
        row_number() window(order by id) <= 3 and w <= 2
query result:
    from upstream
    select:
        id
    order by:
        id
    limit 1
"""
            )
        elif variant == "order_completed":
            source = (
                header
                + f'source other: Row = {target}.table("other")\n'
                + """table upstream:
    from rows
    let r = other
    cross join r
    select:
        id = rows.id
query result:
    from upstream
    select:
        id
    order by:
        id
"""
            )
            other = deepcopy(description)
            other["selector"]["name"] = "other"
            contract["sources"].append(other)
        elif variant == "producer_filter":
            source = (
                header
                + first.replace("    select:", "    where id > 0\n    select:")
                + second
                + final
            )
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if variant == "query_bag"
        else "preserve_literals",
    }


def _as_let(name, declaration):
    """One `table`/`query` body, re-indented as a relation let of that name."""
    body = declaration.split(":\n", 1)[1]
    return f"    let {name}:\n" + "".join(
        "    " + line + "\n" for line in body.splitlines()
    )


def let_fixture(target, variant):
    """Relation lets over published sources and data, with independent oracles.

    `chain` is M_named_chain/query_bag with both producers as lets of `result`;
    `imported` is N_imported_chain/bag whose imported table reads its source
    only inside a let; `hidden_join` joins the published source with a let that
    alone reads a second source (the `p0` relation, which holds the same rows);
    `diamond_limit` reads one LIMIT let, declared last, from two filtering lets
    whose WHERE must stay outside that LIMIT.
    """
    if variant == "diamond_limit":
        item = join_fixture(target, "W_join_shapes", "inner")
        item["source"] = (
            item["source"].split("query result:", 1)[0]
            + """query result:
    let low:
        from top
        where id < 2
        select:
            a = id
    let high:
        from top
        where id > 0
        select:
            a = id
    let top:
        from rows
        select:
            id
        order by:
            id
        limit 3
    union all:
        from low
        from high
"""
        )
        return item
    if variant == "hidden_join":
        item = join_fixture(target, "W_join_shapes", "inner")
        contract = json.loads(item["contract"])
        other = deepcopy(contract["sources"][0])
        other["selector"]["name"] = "other"
        other["relation"]["name"] = "p0"
        contract["sources"].append(other)
        header = item["source"].split("query result:", 1)[0]
        source = (
            header
            + f'source other: Row = {target}.table("other")\n'
            + """query result:
    let picked:
        from other
        select:
            id
    from rows
    let r = picked
    inner join r on rows.id == r.id
    select:
        a = rows.id
"""
        )
        return {
            "source": source,
            "contract": encoded(contract).decode(),
            "policy": item["policy"],
        }
    if variant == "chain":
        item = chain_fixture(target, "M_named_chain", "query_bag")
        source = item["source"]
        head, rest = source.split("query first:", 1)
        first, rest = rest.split("table second:", 1)
        second, final = rest.split("query result:\n", 1)
        item["source"] = (
            head
            + "query result:\n"
            + _as_let("first", "first:" + first)
            + _as_let("second", "second:" + second)
            + final
        )
        return item
    item = chain_fixture(target, "N_imported_chain", "bag")
    modules = dict(item["source"])
    head, rest = modules["a.pietto"].split("table first:", 1)
    first, exported = rest.split("export ", 1)
    names = [
        line.strip().split(" = ")[0]
        for line in first.split("select:\n", 1)[1].splitlines()
    ]
    modules["a.pietto"] = (
        head
        + "table first:\n"
        + _as_let("staged", "staged:" + first)
        + "    from staged\n    select:\n"
        + "".join(f"        {name}\n" for name in names)
        + "export "
        + exported
    )
    item["source"] = modules
    return item


VALUES_BODIES = {
    "top": """query result:
    values(id: Int, label: Text | None, ratio: Float | None, flag: Bool | None):
        1, "a", 0.5, True
        1, "a", 0.5, True
        2, None, None, None
""",
    "rejected": """query result:
    values(id: Int):
        1 + 1
""",
    "let_join": """query result:
    let seed:
        values(rid: Int, label: Text | None):
            0, "z"
            1, None
            1, "y"
    from rows
    let s = seed
    inner join s on rows.id == s.rid
    select:
        a = rows.id
        b = s.label
""",
    "zero_left_join": """query result:
    let seed:
        values(rid: Int, n: Int | None)
    from rows
    let s = seed
    left join s on rows.id == s.rid
    select:
        a = rows.id
        b = s.n
""",
    # `seed` is read before it is written, by `picked`, and again as the JOIN
    # target; `spare` (the published empty table) is read only through `not
    # exists gone`; `hit` is true, false and NULL across the three rows, and
    # `kept` tests a 64-character Text against a zero-row Text column.
    "reads": """query result:
    let picked:
        from seed
        where label == "y"
        select:
            rid
    let gone:
        from spare
        select:
            id
    let seed:
        values(rid: Int, label: Text | None):
            0, "z"
            1, None
            1, "y"
    let labels:
        values(t: Text):
            "y"
    let nulls:
        values(k: Int | None):
            1
            None
    let none:
        values(t: Text | None)
    let top:
        values(n: Int):
            0
    from rows
    let s = seed
    inner join s on rows.id == s.rid
    where exists picked and not exists gone
    select:
        a = rows.id
        b = s.label
        hit = s.label in labels
        miss = rows.id not in nulls
        kept = rows.text not in none
        low = scalar top.n
""",
}
VALUES_LABELS = {
    "top": ("id", "label", "ratio", "flag"),
    "let_join": ("a", "b"),
    "zero_left_join": ("a", "b"),
    "reads": ("a", "b", "hit", "miss", "kept", "low"),
}


def values_fixture(target, variant):
    """Typed VALUES beside the published source, which the statement never reads.

    `reads` also declares `spare` over the published empty table.
    """
    item = join_fixture(target, "W_join_shapes", "inner")
    header = item["source"].split("query result:", 1)[0]
    if variant != "reads":
        return {**item, "source": header + VALUES_BODIES[variant]}
    contract = json.loads(item["contract"])
    spare = deepcopy(contract["sources"][0])
    spare["selector"]["name"] = "spare"
    spare["relation"]["name"] = "phase66 empty é"
    contract["sources"].append(spare)
    spare_source = f'source spare: Row = {target}.table("opaque.spare.locator")\n'
    return {
        **item,
        "source": header + spare_source + VALUES_BODIES[variant],
        "contract": encoded(contract).decode(),
    }


def exists_fixture(target, variant):
    """M_named_chain/query_bag kept by `exists first and not exists none`.

    `first` is read again only through EXISTS and `none` keeps no row, so both
    reads are true, no new physical scan is added and the chain oracle states
    the kept rows independently.
    """
    _need(variant in ("kept", "correlated"), "unknown existence variant")
    item = chain_fixture(target, "M_named_chain", "query_bag")
    head, final = item["source"].split("query result:\n    from second\n", 1)
    if variant == "correlated":
        # Each `second` row has its own `first` row (same Key) and none with a
        # smaller Key equal to it, so both correlated reads keep every row.
        item["source"] = (
            head
            + "query result:\n    let same:\n        capture second\n"
            + "        from first\n        where first.Key == second.id2\n"
            + "        select:\n            Key\n"
            + "    let smaller:\n        capture second\n        from first\n"
            + "        where first.Key == second.id2 and first.Key < second.again\n"
            + "        select:\n            Key\n"
            + "    from second\n    where exists same and not exists smaller\n"
            + final
        )
        return item
    item["source"] = (
        head
        + "query none:\n    from first\n    where Key < Key\n"
        + "    select:\n        Key\n"
        + "query result:\n    from second\n"
        + "    where exists first and not exists none\n"
        + final
    )
    return item


def scalar_fixture(target, variant):
    """M_named_chain/query_bag kept by three scalar reads in WHERE.

    `low` is the one-row MIN of every id (0), `none` keeps no row so its read
    is NULL, and `counted` is the one-row COUNT of that empty input (0, not
    NULL, so it equals `low.k`); every chain row satisfies all four reads, no
    literal or new physical scan is added and the chain oracle states the kept
    rows independently.
    """
    _need(variant == "kept", "unknown scalar variant")
    item = chain_fixture(target, "M_named_chain", "query_bag")
    head, final = item["source"].split("query result:\n    from second\n", 1)
    item["source"] = (
        head
        + "query low:\n    from first\n    select:\n        k = min(Key)\n"
        + "query none:\n    from first\n    where Key < Key\n"
        + "    select:\n        Key\n"
        + "query counted:\n    from none\n    select:\n        n = count()\n"
        + "query result:\n    from second\n"
        + "    where id2 >= scalar low.k and scalar none.Key is None"
        + " and scalar counted.n == scalar low.k\n"
        + final
    )
    return item


# Single-column candidate relations over the flags of `first` (true, true,
# false, NULL): none, the two duplicated true flags, the NULL flag and all four.
MEMBERSHIP_CANDIDATES = """query flags:
    from first
    select:
        FlagValue
query none_flags:
    from flags
    where FlagValue and not FlagValue
    select:
        FlagValue
query true_flags:
    from flags
    where FlagValue
    select:
        FlagValue
query null_flags:
    from flags
    where FlagValue is None
    select:
        FlagValue
"""
MEMBERSHIP_RELATIONS = {
    "none": "none_flags",
    "true": "true_flags",
    "null": "null_flags",
    "all": "flags",
}
MEMBERSHIP_TRUTH_LABELS = tuple(
    f"{prefix}_{candidates}"
    for candidates in ("none", "true", "null", "all")
    for prefix in ("in", "out")
)


def membership_fixture(target, variant):
    """M_named_chain/query_bag read through closed `[not] in` relation reads.

    Every candidate relation reads `first`, so no physical scan is added.
    `select_truth` tests each flag against no, duplicated, NULL-only and all
    candidates; `where_limit` keeps the rows whose id is not the smallest id,
    held by a closed LIMIT 1 let that only a top-level CTE carries.
    """
    _need(variant in VARIANTS["L_relation_membership"], "unknown membership variant")
    item = chain_fixture(target, "M_named_chain", "query_bag")
    head, final = item["source"].split("query result:\n    from second\n", 1)
    if variant == "correlated":
        # Each `second` row has its own `first` rows (same Key, duplicates
        # included) and none with a smaller Key equal to it: `in` is true over
        # duplicated candidates and the scalar read of no row is NULL; every
        # row stays.
        item["source"] = (
            head
            + "query result:\n    let same:\n        capture second\n"
            + "        from first\n        where first.Key == second.id2\n"
            + "        select:\n            Key\n"
            + "    let smaller:\n        capture second\n        from first\n"
            + "        where first.Key == second.id2 and first.Key < second.again\n"
            + "        select:\n            Key\n"
            + "    from second\n    where id2 in same and scalar smaller.Key is None\n"
            + final
        )
        return item
    if variant == "select_truth":
        body = "query result:\n    from second\n    select:\n" + "".join(
            f"        {label} = flag2 {'in' if label.startswith('in_') else 'not in'}"
            f" {MEMBERSHIP_RELATIONS[label.split('_', 1)[1]]}\n"
            for label in MEMBERSHIP_TRUTH_LABELS
        )
        item["source"] = head + MEMBERSHIP_CANDIDATES + body
        return item
    item["source"] = (
        head
        + "query result:\n    let firsts:\n        from first\n"
        + "        select:\n            Key\n        order by:\n            Key\n"
        + "        limit 1\n    from second\n    where id2 not in firsts\n"
        + final
    )
    return item


COLLECT_HEADER = """shape Customer:
    id: Int
    name: Text
shape Order:
    id: Int
    customer_id: Int | None
    v: Int | None
    k: Int | None
    note: Text | None
    price: Decimal(9, 2) | None
    small: Int | None
shape Payment:
    id: Int
    customer_id: Int | None
source customers: Customer = {target}.table("customers")
source orders: Order = {target}.table("orders")
source payments: Payment = {target}.table("payments")
"""


def _captured_let(name, table, select, order, limit=None):
    """One let of `table` rows whose customer is the parent row."""
    lines = [
        f"    let {name}:",
        "        capture customers",
        f"        from {table}",
        f"        where {table}.customer_id == customers.id",
        "        select:",
        *(f"            {item}" for item in select),
        "        order by:",
        *(f"            {item}" for item in order),
    ]
    return "\n".join([*lines, *([f"        limit {limit}"] if limit else [])]) + "\n"


def _closed_let(name, select, order, *, limit=None, distinct=False, group=None):
    lines = [f"    let {name}:", "        from orders"]
    if group:
        lines += ["        group by:", f"            {group}"]
    lines += [
        "        select distinct:" if distinct else "        select:",
        *(f"            {item}" for item in select),
        "        order by:",
        *(f"            {item}" for item in order),
    ]
    return "\n".join([*lines, *([f"        limit {limit}"] if limit else [])]) + "\n"


def _collect_query(lets, fields, tail=""):
    return (
        "query result:\n"
        + "".join(lets)
        + "    from customers\n    select:\n        id\n"
        + "".join(f"        {field} = collect {field}\n" for field in fields)
        + tail
    )


COLLECT_BODIES = {
    "closed": _collect_query([_closed_let("bag", ["v"], ["v"])], ["bag"]),
    "captured": _collect_query(
        [_captured_let("kids", "orders", ["v"], ["v desc"])], ["kids"]
    ),
    "topk": _collect_query(
        [_captured_let("top", "orders", ["v"], ["v desc"], limit=2)], ["top"]
    ),
    "ties": _collect_query(
        [_closed_let("tied", ["id", "k"], ["k"], limit=3)], ["tied"]
    ),
    "hidden_nullable_key": _collect_query(
        [
            _closed_let("up", ["id"], ["k", "id"], limit=3),
            _closed_let("down", ["id"], ["k desc", "id"], limit=3),
        ],
        ["up", "down"],
    ),
    "siblings": _collect_query(
        [
            _captured_let("items", "orders", ["id"], ["id"]),
            _captured_let("paid", "payments", ["id"], ["id"]),
        ],
        ["items", "paid"],
    ),
    "distinct_let": _collect_query(
        [_closed_let("values", ["v"], ["v desc"], distinct=True)], ["values"]
    ),
    "grouped_let": _collect_query(
        [
            _closed_let(
                "totals",
                ["customer_id", "n = count()"],
                ["n desc", "customer_id"],
                group="customer_id",
            )
        ],
        ["totals"],
    ),
    "parent_order_limit": _collect_query(
        [_captured_let("kids", "orders", ["v"], ["v desc"])],
        ["kids"],
        "    order by:\n        customers.id desc\n    limit 2\n",
    ),
    "text_quoting": _collect_query(
        [_captured_let("notes", "orders", ["note"], ["id"])], ["notes"]
    ),
    "int4_child": _collect_query(
        [_captured_let("smalls", "orders", ["small"], ["id"])], ["smalls"]
    ),
    "decimal_child": _collect_query(
        [_captured_let("prices", "orders", ["price"], ["id"])], ["prices"]
    ),
}
# (name, column, logical) of every declared field, in declaration order.
COLLECT_SOURCES = {
    "customers": (("id", "Int", False), ("name", "Text", False)),
    "orders": (
        ("id", "Int", False),
        ("customer_id", "Int", True),
        ("v", "Int", True),
        ("k", "Int", True),
        ("note", "Text", True),
        ("price", "Decimal", True),
        ("small", "Int4", True),
    ),
    "payments": (("id", "Int", False), ("customer_id", "Int", True)),
}


def collect_relation(name):
    """The physical relation name of one Collect source."""
    return f"phase71 collect {name}"


def retained_collection_fixture(target, variant):
    """Self-contained input for the copied, isolated installed generator."""
    _need(variant in ("unnest", "outer"), "unknown retained collection variant")
    parent = f"""shape Row:
    id: Int
    other: Int | None
shape Order:
    id: Int
    customer_id: Int
    total: Int
    created_at: Int
source rows: Row = {target}.table("rows")
source orders: Order = {target}.table("orders")
query parent:
    let recent:
        from orders
        select:
            id
            total
        order by id
    let held:
        from rows
        select:
            id
        order by id
    from rows
    select:
        id
        nested = collect recent
        sibling = collect held
export (
    query parent,
)
"""
    header = (
        'from "parent.pietto" import (\n    query parent,\n)\nshape Tag:\n    id: Int\n    other: Int | None\n'
        + f'source tags: Tag = {target}.table("tags")\n'
    )
    body = (
        """query result:
    let p = parent
    from p
    let child = unnest(p.nested)
    cross join child
    inner join tags on child.id == tags.id
    select:
        parent_id = p.id
        child_id = child.id
        tag_id = tags.id
        retained = p.sibling
"""
        if variant == "unnest"
        else """query result:
    let p = parent
    from tags
    left join p on tags.id == p.id
    select:
        id = tags.id
        retained = p.sibling
"""
    )
    contract = json.loads(fixture(target)["contract"])
    contract["sources"] = [
        {
            "scan": "relation_rows",
            "selector": {"module": module, "kind": "source", "name": name},
            "relation": {
                "namespace": "public" if target == "postgres" else "phase66",
                "name": "phase71 retained " + name,
            },
            "fields": [
                {
                    "ordinal": i,
                    "name": field,
                    "column": field,
                    "representation": {
                        "storage": {
                            "kind": "pg_int8" if target == "postgres" else "my_bigint"
                        },
                        "nullable": nullable,
                        "domain": {
                            "kind": "int_range",
                            "min": str(-(2**63)),
                            "max": str(2**63 - 1),
                        },
                    },
                }
                for i, (field, nullable) in enumerate(fields)
            ],
            "premises": [
                {"key": key, "scope": "source", "value": True}
                for key in ("row_domain_matches", "read_only_object")
            ],
        }
        for module, name, fields in (
            ("parent.pietto", "rows", (("id", False), ("other", True))),
            (
                "parent.pietto",
                "orders",
                (
                    ("id", False),
                    ("customer_id", False),
                    ("total", False),
                    ("created_at", False),
                ),
            ),
            ("main.pietto", "tags", (("id", False), ("other", True))),
        )
    ]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    return {
        "source": {"parent.pietto": parent, "main.pietto": header + body},
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


def collect_fixture(target, variant):
    """A parent `customers` row per output row and Collect reads of `orders`
    and `payments` rows. Every relation and column is declared exactly; only
    PostgreSQL admits a Collect read, so MySQL reports one refusal per read."""
    _need(variant in COLLECT_VARIANTS, "unknown collect variant")
    postgres = target == "postgres"
    text = {
        "storage": {"kind": "pg_text"}
        if postgres
        else {"kind": "my_varchar", "length": 64},
        "domain": {
            "kind": "text",
            "max_characters": 64,
            "encoding": "UTF8" if postgres else "utf8mb4",
            "collation": "C" if postgres else "utf8mb4_0900_bin",
            "padding": "NO PAD",
        },
    }

    def integer(bits):
        kinds = {64: ("pg_int8", "my_bigint"), 32: ("pg_int4", "my_int")}[bits]
        return {
            "storage": {"kind": kinds[0] if postgres else kinds[1]},
            "domain": {
                "kind": "int_range",
                "min": str(-(2 ** (bits - 1))),
                "max": str(2 ** (bits - 1) - 1),
            },
        }

    leaves = {
        "Int": integer(64),
        "Int4": integer(32),
        "Text": text,
        "Decimal": {
            "storage": {
                "kind": "pg_numeric" if postgres else "my_decimal",
                "precision": 9,
                "scale": 2,
            },
            "domain": {"kind": "decimal", "precision": 9, "scale": 2},
        },
    }
    contract = json.loads(fixture(target)["contract"])
    contract["sources"] = [
        {
            "selector": {"module": "main.pietto", "kind": "source", "name": name},
            "relation": {
                "namespace": "public" if postgres else "phase66",
                "name": collect_relation(name),
            },
            "scan": "relation_rows",
            "fields": [
                {
                    "ordinal": i,
                    "name": column,
                    "column": column,
                    "representation": {
                        "storage": leaves[leaf]["storage"],
                        "nullable": nullable,
                        "domain": leaves[leaf]["domain"],
                    },
                }
                for i, (column, leaf, nullable) in enumerate(fields)
            ],
            "premises": [
                {"key": key, "scope": "source", "value": True}
                for key in ("row_domain_matches", "read_only_object")
            ],
        }
        for name, fields in COLLECT_SOURCES.items()
    ]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact" if postgres else "lower_case_table_names=0",
        }
    )
    return {
        "source": COLLECT_HEADER.format(target=target) + COLLECT_BODIES[variant],
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


SERIES_BODIES = {
    "ascending": """query result:
    from generate_series(1, 3, 1) as n
    select:
        n
""",
    "joined": """query result:
    from generate_series(0, 2, 1) as n
    let r = rows
    inner join r on n.n == r.id
    select:
        n = n.n
        id = r.id
""",
}
SERIES_LABELS = {"ascending": ("n",), "joined": ("n", "id")}


def series_fixture(target, variant):
    """A bounded series alone, or joined with the published relation."""
    item = join_fixture(target, "W_join_shapes", "inner")
    header = item["source"].split("query result:", 1)[0]
    return {**item, "source": header + SERIES_BODIES[variant]}


ROW_DIRECT_BODY = """    from rows
    let bumped = id + 1
    let doubled = bumped * 2
    where id > 0
    select:
        record_id = id
        next_id = bumped
        twice = doubled
        positive = id > 0
        both = id > 0 and flag
        missing = flag is None
        same_text = text == text
"""
ROW_PRODUCER = """table first:
    from rows
    let bumped = id + 1
    where id > 0
    select:
        kept = id
        stepped = bumped
        flagged = flag
        label = text
"""
ROW_CONSUMER = """query result:
    from {producer}
    let doubled = stepped * 2
    select:
        record_id = kept
        next_id = stepped
        twice = doubled
        positive = kept > 0
        both = kept > 0 and flagged
        missing = flagged is None
        same_text = label == label
"""
ROW_BLOCKED_BODY = {
    "float_arithmetic": "        total = ratio + ratio\n",
    "float_comparison": "        same = ratio == ratio\n",
    "bool_comparison": "        same = flag == flag\n",
    "int_overflow": "        big = id + 1\n",
    "unary_overflow": "        negated = -id\n",
    "modulo": "        rest = id % 2\n",
    "between": "        inside = 0 <= id <= 1\n",
}


WINDOW_CASES = frozenset(
    {
        "A_window_ranking",
        "A_window_distribution",
        "A_window_navigation",
        "A_window_frame",
        "A_window_groups",
        "A_window_named",
        "A_window_qualify",
        "V_window_blocked",
    }
)
# One authored body per admitted law. Peers are what separate row_number, rank
# and dense_rank, so the ranking witness orders by a duplicated key.
WINDOW_BODIES = {
    ("A_window_ranking", "peers"): """query result:
    from rows
    select:
        record_id = id
        numbered = row_number() window(order by id)
        ranked = rank() window(order by id)
        densely = dense_rank() window(order by id)
""",
    ("A_window_distribution", "spread"): """query result:
    from rows
    select:
        record_id = id
        fraction = percent_rank() window(partition by id order by id)
        cumulative = cume_dist() window(partition by id order by id)
        bucket = ntile(2) window(order by id)
""",
    ("A_window_navigation", "offsets"): """query result:
    from rows
    select:
        record_id = id
        previous = lag(id, 1, 0) window(order by id)
        upcoming = lead(id, 1) window(order by id)
""",
    ("A_window_frame", "rows"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window(order by id rows between 1 preceding and current row)
        latest = last_value(id) window(order by id rows between 1 preceding and current row)
""",
    ("A_window_frame", "range"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window(order by id range between 1 preceding and current row)
""",
    ("A_window_groups", "exclude"): """query result:
    from rows
    select:
        record_id = id
        peers = first_value(id) window(order by id groups between 1 preceding and current row exclude current row)
""",
    ("A_window_named", "shared"): """query result:
    from rows
    let ordered = window(order by id)
    select:
        record_id = id
        ranked = rank() window ordered
        densely = dense_rank() window ordered
""",
    ("A_window_qualify", "selected"): """query result:
    from rows
    select:
        record_id = id
        numbered = row_number() window(order by id)
    qualify:
        numbered <= 2
""",
    ("A_window_qualify", "hidden"): """query result:
    from rows
    select:
        record_id = id
    qualify:
        row_number() window(order by id) <= 2
""",
    ("V_window_blocked", "ignore_nulls"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) ignore nulls window(order by id rows between unbounded preceding and current row)
""",
    ("V_window_blocked", "from_last"): """query result:
    from rows
    select:
        record_id = id
        second = nth_value(id, 2) from last window(order by id rows between unbounded preceding and current row)
""",
    ("V_window_blocked", "offset_range_keys"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window(order by id, flag range between 1 preceding and current row)
""",
}


def window_fixture(target, case, variant):
    """One admitted window body over the published emission source shape."""
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    body = WINDOW_BODIES[case, variant]
    if case == "A_window_qualify":
        # G8: the same selected/hidden QUALIFY decides outer membership.
        # Both sources read only id from the unchanged four physical rows.
        contract["sources"][0]["fields"] = contract["sources"][0]["fields"][:1]
        header = (
            f'shape One:\n    id: Int\nsource rows: One = {target}.table("opaque")\n'
        )
        negation = "" if variant == "selected" else "not "
        body = body.replace("query result:", "table ranked:", 1) + (
            "query result:\n    from rows\n"
            "    let r = ranked\n"
            f"    where {negation}any(rows.id == r.record_id for r in r)\n"
            "    select:\n        record_id = rows.id\n"
        )
    if (case, variant) == ("A_window_frame", "range"):
        # Every old RANGE row/column remains; the extra column realizes an
        # anchored literal through a named producer and a window.
        contract["sources"][0]["fields"] = contract["sources"][0]["fields"][:1]
        contract["sources"][0]["relation"]["name"] = "phase66 safe int source"
        contract["sources"][0]["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": "5"},
        }
        header = (
            "shape One:\n    id: Int\n"
            f'source rows: One = {target}.table("opaque")\n'
            "table input:\n    from rows\n    select:\n        id\n        one = 1\n"
        )
        body = body.replace("from rows", "from input", 1) + (
            "        w = first_value(one) window(order by id)\n"
        )
    return {
        "source": header + body,
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


# Slice10 result boundaries over the published emission source. Every ORDER key
# is an input-scope value, a constant key is first established through LET, and
# the C13 witnesses author the same filter on both sides of a LIMIT boundary.
RESULT_BODIES = {
    ("O_result_distinct", "visible_int"): """query result:
    from rows
    select distinct:
        record_id = id
""",
    ("O_result_distinct", "null_duplicates"): """query result:
    from agg
    select distinct:
        v = value
""",
    ("O_result_distinct", "hidden_group"): """query result:
    from rows
    group by:
        id
    select distinct:
        total = count()
""",
    ("O_result_order", "ordinary_desc"): """query result:
    from rows
    select:
        record_id = id
    order by:
        id desc
""",
    ("O_result_order", "nullable_key"): """query result:
    from rows
    select:
        record_id = id
        active = flag
    order by:
        flag
        id
""",
    ("O_result_order", "constant_key"): """query result:
    from rows
    let one = 1
    select:
        record_id = id
    order by:
        one
        id desc
""",
    ("O_result_order", "helper_hidden"): """query result:
    from rows
    select:
        record_id = id
    order by:
        text
        id desc
""",
    ("O_result_limit", "positive"): """query result:
    from rows
    select:
        record_id = id
    order by:
        id
    limit 2
""",
    ("O_result_limit", "zero"): """query result:
    from rows
    select:
        record_id = id
    limit 0
""",
    ("O_result_limit", "inner_then_filter"): """table top:
    from rows
    select:
        rid = id
    order by:
        id
    limit 1
query result:
    from top
    where rid > 0
    select:
        rid
""",
    ("O_result_limit", "filter_then_limit"): """query result:
    from rows
    where id > 0
    select:
        rid = id
    order by:
        id
    limit 1
""",
    ("O_result_sharing", "order_limit_self_join"): """table top:
    from rows
    select:
        rid = id
    order by:
        id
    limit 2
query result:
    from top
    let r = top
    inner join r on top.rid == r.rid
    select:
        a = top.rid
        b = r.rid
""",
    ("O_result_window", "qualify_distinct"): """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window(order by id) <= 4
""",
    ("O_result_window", "selected_order"): """query result:
    from rows
    select:
        record_id = id
        n = row_number() window(order by id)
    order by:
        n desc
    limit 2
""",
    ("O_result_window", "qualify_order_limit"): """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window(order by id) <= 3
    order by:
        id desc
    limit 2
""",
    ("V_result_blocked", "hidden_strict_fd"): """query result:
    from rows
    select distinct:
        record_id = id
    order by:
        text
""",
    ("V_result_blocked", "float_distinct"): """query result:
    from rows
    select distinct:
        r = ratio
""",
    ("V_result_blocked", "order_expression"): """query result:
    from rows
    select:
        record_id = id
    order by:
        id + 1
""",
}
MEMBERSHIP_RIGHT = {
    "limit1": "table ranked:\n    from rows\n    select:\n        rid = id\n"
    "    order by:\n        id\n    limit 1\n",
    "limit0": "table ranked:\n    from rows\n    select:\n        rid = id\n"
    "    limit 0\n",
}


def membership_body(variant):
    kind, right = variant.split("_", 1)
    negation = "" if kind == "semi" else "not "
    return MEMBERSHIP_RIGHT[right] + (
        "query result:\n    from rows\n    let r = ranked\n"
        f"    where {negation}any(rows.id == r.rid for r in r)\n    select:\n"
        "        a = rows.id\n"
    )


def result_fixture(target, case, variant):
    """One Slice10 result-boundary body over the published sources."""
    if (case, variant) == ("O_result_distinct", "null_duplicates"):
        # The exact R18 witness: value = [1, 1, NULL, NULL] collapses to [1, NULL].
        contract = json.loads(
            aggregate_fixture(target, "X_aggregate_global", "bag")["contract"]
        )
        contract["sources"] = [
            _aggregate_descriptor(target, "agg", AGGREGATE_RELATIONS["dupes"])
        ]
        return {
            "source": AGGREGATE_HEADER.format(target=target)
            + RESULT_BODIES[case, variant],
            "contract": encoded(contract).decode(),
            "policy": "preserve_literals",
        }
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    if (case, variant) == ("V_result_blocked", "hidden_strict_fd"):
        # The visible key is unique, so the hidden Text key is STRICT-FD
        # determined: exactly the R20 pending requirement.
        header = header.replace(
            "shape Row:\n    id: Int\n",
            "shape Row:\n    id: Int\n    by_id = unique(id)\n",
        )
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    body = (
        membership_body(variant)
        if case == "O_result_membership"
        else RESULT_BODIES[case, variant]
    )
    return {
        "source": header + body,
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


# Slice11 SET witnesses. `agg` bodies read the fixed SET relations through the
# Agg shape; `rows` bodies read the published emission source. Every operand is
# a named producer, every SET owner is `query result`, and the C17 base pair is
# SA.key = [1, 1, NULL] against SB.key = [1, NULL, NULL].
SET_ONE = (
    "table {name}:\n    from sb\n    where key == 1\n    select:\n        k = key\n"
)
SET_KEYS = (
    "table a:\n    from sa\n    select:\n        k = key\n"
    "table b:\n    from sb\n    select:\n        k = key\n"
)
SET_ROWS_AB = (
    "table a:\n    from rows\n    select:\n        k = id\n"
    "table b:\n    from rows\n    where id > 0\n    select:\n        k = id\n"
)
SET_BODIES = {
    ("S_set_multiplicity", "intersect_all"): (
        ("dupes", "sc"),
        "table a:\n    from dupes\n    select:\n        v = value\n"
        "table b:\n    from sc\n    select:\n        v = key\n"
        "query result:\n    intersect all:\n        from a\n        from b\n",
    ),
    ("S_set_multiplicity", "intersect_distinct"): (
        ("dupes", "sc"),
        "table a:\n    from dupes\n    select:\n        v = value\n"
        "table b:\n    from sc\n    select:\n        v = key\n"
        "query result:\n    intersect distinct:\n        from a\n        from b\n",
    ),
    ("S_set_multiplicity", "empty_left"): (
        ("empty", "sa"),
        "table a:\n    from empty\n    select:\n        k = key\n"
        "table b:\n    from sa\n    select:\n        k = key\n"
        "query result:\n    except all:\n        from a\n        from b\n",
    ),
    ("S_set_multiplicity", "empty_right"): (
        ("empty", "sa"),
        "table a:\n    from empty\n    select:\n        k = key\n"
        "table b:\n    from sa\n    select:\n        k = key\n"
        "query result:\n    except all:\n        from b\n        from a\n",
    ),
    ("S_set_positions", "two_column_intersect_distinct"): (
        ("sa", "sb"),
        "table a:\n    from sa\n    select:\n        v = value\n        t = label\n"
        "table b:\n    from sb\n    select:\n        v = value\n        t = label\n"
        "query result:\n    intersect distinct:\n        from a\n        from b\n",
    ),
    ("S_set_positions", "two_column_except_all"): (
        ("sa", "sb"),
        "table a:\n    from sa\n    select:\n        v = value\n        t = label\n"
        "table b:\n    from sb\n    select:\n        v = value\n        t = label\n"
        "query result:\n    except all:\n        from a\n        from b\n",
    ),
    ("S_set_positions", "renamed_labels_union_all"): (
        ("sa", "sb"),
        "table a:\n    from sa\n    select:\n        k = key\n        t = label\n"
        "table b:\n    from sb\n    select:\n        n = key\n        s = label\n"
        "query result:\n    union all:\n        from a\n        from b\n",
    ),
    ("S_set_domains", "text_union_distinct"): (
        (),
        "table a:\n    from rows\n    select:\n        t = text\n"
        "query result:\n    union distinct:\n        from a\n        from a\n",
    ),
    ("S_set_domains", "decimal_intersect_all"): (
        (),
        "table a:\n    from rows\n    select:\n        m = money\n"
        "table b:\n    from rows\n    where id > 0\n    select:\n        m = money\n"
        "query result:\n    intersect all:\n        from a\n        from b\n",
    ),
    ("S_set_domains", "big_int_except_all"): (
        (),
        "table a:\n    from rows\n    select:\n        k = id\n"
        "table b:\n    from rows\n    where id > 1\n    select:\n        k = id\n"
        "query result:\n    except all:\n        from a\n        from b\n",
    ),
    ("S_set_domains", "bool_union_distinct"): (
        (),
        "table a:\n    from rows\n    select:\n        f = flag\n"
        "query result:\n    union distinct:\n        from a\n        from a\n",
    ),
    ("S_set_domains", "float_union_all"): (
        (),
        "table a:\n    from rows\n    select:\n        r = ratio\n"
        "query result:\n    union all:\n        from a\n        from a\n",
    ),
    ("S_set_nesting", "left_fold_except"): (
        ("sb",),
        SET_ONE.format(name="a")
        + SET_ONE.format(name="b")
        + SET_ONE.format(name="c")
        + "query result:\n    except distinct:\n        from a\n        from b\n        from c\n",
    ),
    ("S_set_nesting", "right_nested_except"): (
        ("sb",),
        SET_ONE.format(name="a")
        + SET_ONE.format(name="b")
        + SET_ONE.format(name="c")
        + "table bc:\n    except distinct:\n        from b\n        from c\n"
        "query result:\n    except distinct:\n        from a\n        from bc\n",
    ),
    ("S_set_nesting", "mixed_union_except"): (
        ("sb",),
        SET_ONE.format(name="a")
        + SET_ONE.format(name="b")
        + "table u:\n    union all:\n        from a\n        from a\n"
        "query result:\n    except all:\n        from u\n        from b\n",
    ),
    ("S_set_boundaries", "ordered_operands"): (
        (),
        "table top:\n    from rows\n    select:\n        k = id\n    order by:\n        id\n    limit 2\n"
        "query result:\n    union all:\n        from top\n        from top\n",
    ),
    ("S_set_boundaries", "limit_zero_operand"): (
        (),
        "table a:\n    from rows\n    select:\n        k = id\n"
        "table none:\n    from rows\n    select:\n        k = id\n    limit 0\n"
        "query result:\n    union all:\n        from a\n        from none\n",
    ),
    ("S_set_boundaries", "distinct_operand"): (
        (),
        "table d:\n    from rows\n    select distinct:\n        k = id\n"
        "query result:\n    union all:\n        from d\n        from d\n",
    ),
    ("S_set_boundaries", "outer_consumer"): (
        (),
        SET_ROWS_AB + "table u:\n    union all:\n        from a\n        from b\n"
        "query result:\n    from u\n    where k > 0\n    select:\n        k\n"
        "    order by:\n        k\n    limit 1\n",
    ),
    ("S_set_producers", "grouped_union"): (
        (),
        "table g:\n    from rows\n    group by:\n        id\n    select:\n        k = id\n        total = count()\n"
        "query result:\n    union all:\n        from g\n        from g\n",
    ),
    ("S_set_producers", "global_empty_union"): (
        ("empty",),
        "table ge:\n    from empty\n    select:\n        c = count()\n"
        "query result:\n    union all:\n        from ge\n        from ge\n",
    ),
    ("S_set_producers", "satisfying_union"): (
        (),
        "table s:\n    from rows\n    group by:\n        id\n    select:\n        k = id\n        total = count()\n"
        "    having:\n        total > 1\n"
        "query result:\n    union all:\n        from s\n        from s\n",
    ),
    ("S_set_producers", "window_union_distinct"): (
        (),
        "table w:\n    from rows\n    select:\n        k = id\n    qualify:\n"
        "        row_number() window(order by id) <= 2\n"
        "table top:\n    from rows\n    select:\n        k = id\n    order by:\n        id\n    limit 2\n"
        "query result:\n    union distinct:\n        from w\n        from top\n",
    ),
    ("S_set_producers", "set_to_window"): (
        (),
        SET_ROWS_AB + "table u:\n    union all:\n        from a\n        from b\n"
        "query result:\n    from u\n    select:\n        k\n"
        "        n = row_number() window(order by k)\n",
    ),
    ("S_set_literals", "preserve"): (
        (),
        "table lit:\n    from rows\n    select:\n        k = id\n        m = 1\n"
        "query result:\n    union all:\n        from lit\n        from lit\n",
    ),
    ("S_set_literals", "bind"): (
        (),
        "table lit:\n    from rows\n    select:\n        k = id\n        m = 1\n"
        "query result:\n    union all:\n        from lit\n        from lit\n",
    ),
    ("V_set_blocked", "physical_mismatch"): (
        ("second",),
        "table a:\n    from rows\n    select:\n        k = id\n"
        "table b:\n    from second\n    select:\n        k = id\n"
        "query result:\n    union all:\n        from a\n        from b\n",
    ),
    ("V_set_blocked", "float_intersect_all"): (
        (),
        "table a:\n    from rows\n    select:\n        r = ratio\n"
        "query result:\n    intersect all:\n        from a\n        from a\n",
    ),
    ("V_set_blocked", "arity_mismatch"): (
        (),
        "table a:\n    from rows\n    select:\n        k = id\n"
        "table two:\n    from rows\n    select:\n        k = id\n        t = text\n"
        "query result:\n    union all:\n        from a\n        from two\n",
    ),
    ("V_set_blocked", "type_mismatch"): (
        (),
        "table a:\n    from rows\n    select:\n        k = id\n"
        "table txt:\n    from rows\n    select:\n        t = text\n"
        "query result:\n    union all:\n        from a\n        from txt\n",
    ),
}
SET_AGG_SOURCES = frozenset({"sa", "sb", "sc", "sl", "dupes", "empty"})


def set_body(case, variant):
    if case == "S_set_forms":
        kind, quantifier = variant.split("_", 1)
        return ("sa", "sb"), SET_KEYS + (
            f"query result:\n    {kind} {quantifier}:\n        from a\n        from b\n"
        )
    if case == "S_set_membership":
        join, kind = variant.split("_", 1)
        negation = "" if join == "semi" else "not "
        return ("sl", "sa", "sb"), (
            "table a:\n    from sa\n    select:\n        v = value\n"
            "table b:\n    from sb\n    select:\n        v = key\n"
            f"table r:\n    {kind} distinct:\n        from a\n        from b\n"
            "query result:\n    from sl\n    let x = r\n"
            f"    where {negation}any(sl.key == x.v for x in x)\n"
            "    select:\n        a = sl.key\n"
        )
    return SET_BODIES[case, variant]


def set_fixture(target, case, variant):
    """One Slice11 SET witness over the fixed relations or the emission source."""
    if case == "S_set_domains" and variant in {
        "timestamp_union_all",
        "timestamp_union_distinct",
    }:
        contract = json.loads(fixture(target)["contract"])
        source = contract["sources"][0]
        source["relation"]["name"] = "phase66 timestamp set source"
        source["fields"] = [
            {
                "ordinal": 0,
                "name": "stamp",
                "column": "stamp",
                "representation": {
                    "storage": {
                        "kind": "pg_timestamp"
                        if target == "postgres"
                        else "my_datetime",
                        "fractional_seconds": 6,
                    },
                    "nullable": True,
                    "domain": {"kind": "timestamp"},
                },
            }
        ]
        contract["environment"].append(
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "quoted_exact"
                if target == "postgres"
                else "lower_case_table_names=0",
            }
        )
        quantifier = variant.removeprefix("timestamp_union_")
        header = f'shape Stamp:\n    stamp: Timestamp | None\nsource rows: Stamp = {target}.table("timestamp.set")\n'
        body = (
            "table a:\n    from rows\n    select:\n        t = stamp\n"
            + f"query result:\n    union {quantifier}:\n        from a\n        from a\n"
        )
        return {
            "source": header + body,
            "contract": encoded(contract).decode(),
            "policy": "preserve_literals",
        }
    sources, body = set_body(case, variant)
    if sources and set(sources) <= SET_AGG_SOURCES:
        header = AGGREGATE_HEADER.format(target=target).split("source agg:", 1)[0]
        header += "".join(
            f'source {name}: Agg = {target}.table("{name}.locator.not.sql")\n'
            for name in sources
        )
        contract = json.loads(
            aggregate_fixture(target, "X_aggregate_global", "bag")["contract"]
        )
        contract["sources"] = [
            _aggregate_descriptor(target, name, AGGREGATE_RELATIONS[name])
            for name in sources
        ]
        return {
            "source": header + body,
            "contract": encoded(contract).decode(),
            "policy": "preserve_literals",
        }
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if sources == ("second",):
        # A second physical relation whose Int field is a narrower valid
        # representation: each operand is admitted alone, the pair is not.
        second = deepcopy(contract["sources"][0])
        second["selector"]["name"] = "second"
        second["relation"]["name"] = "p0"
        second["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
        }
        contract["sources"].append(second)
        header += f'source second: Row = {target}.table("second.locator.not.sql")\n'
    if variant == "bind":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    return {
        "source": header + body,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals" if variant == "bind" else "preserve_literals",
    }


# Phase72 Lane E (B10): Pietto-emitted Float programs over the published seeds.
# `rows` holds ratio -0, -0, 1.5, +0 at ids BIG, BIG, 0, 1; `sa` holds 1.5, -0,
# +0 and `sb` 1.5, +0, +0. Each body names the sources it reads beside `rows`
# (empty: `rows` only); the oracle is _pietto_target_conformance_cases.
# FLOAT_EXPECTED.
FLOAT_SELECT = "    select:\n        record_id = id\n        r = ratio\n"
FLOAT_ZEROS = (
    "    let zeros:\n        from sb\n        where ratio < 1.0\n"
    "        select:\n            z = ratio\n"
)
FLOAT_NEGATIVES = "table negatives:\n    from rows\n    where id > 1\n    select:\n        r = ratio\n"
FLOAT_SET_TABLES = (
    "table a:\n    from sa\n    select:\n        r = ratio\n"
    "table b:\n    from sb\n    select:\n        r = ratio\n"
)
FLOAT_VALUES = (
    "table zero:\n    values(r: Float):\n        0.0\n"
    "table negative:\n    values(r: Float):\n        -0.0\n"
)


def _float_set(operator, left, right, tables=FLOAT_SET_TABLES):
    return tables + (
        f"query result:\n    {operator}:\n        from {left}\n        from {right}\n"
    )


FLOAT_BODIES = {
    # Cells are merged into few programs: each public document is about 73 KB
    # (PostgreSQL), and the receipt reader has a fixed byte reserve.
    "fc_where": (
        (),
        "query result:\n    from rows\n"
        "    where ratio == 0.0 and ratio == -0.0 and 0.0 <= ratio <= 0.0\n"
        + FLOAT_SELECT,
    ),
    # One truth table per row: every comparison, `in`, relation membership,
    # `nullif` and Float(Int). Both reads go through `seeded`, so no physical
    # scan is added (as in L_relation_membership).
    "fc_rows": (
        (),
        "table seeded:\n    from rows\n    select:\n        record_id = id\n"
        "        r = ratio\n"
        "table seeded_negatives:\n    from seeded\n    where record_id > 1\n"
        "    select:\n        n = r\n"
        "query result:\n    from seeded\n    select:\n        record_id\n        r\n"
        "        eq = r == 0.0\n        eq_negative = r == -0.0\n"
        "        ne = r != 0.0\n        lt = r < 0.0\n"
        "        le = r <= -0.0\n        gt = r > -0.0\n        ge = r >= 0.0\n"
        "        listed = r in (-0.0)\n        unlisted = r not in (-0.0)\n"
        "        member = r in seeded_negatives\n"
        "        outsider = r not in seeded_negatives\n"
        "        unless_zero = nullif(r, 0.0)\n"
        "        unless_negative_zero = nullif(r, -0.0)\n"
        "        widened = Float(record_id)\n"
        "        widened_big = Float(record_id) == 9007199254740992.0\n",
    ),
    "fp_zeros": (
        (),
        "query result(p: Float, q: Float):\n    from rows\n"
        "    where ratio == p and ratio == q\n" + FLOAT_SELECT,
    ),
    "fw_windows": (
        (),
        "query result:\n    from rows\n    select:\n        record_id = id\n"
        "        p = percent_rank() window(order by id)\n"
        "        c = cume_dist() window(order by id)\n"
        "    qualify:\n        p > 0.5 or c <= 0.25\n",
    ),
    "fh_average": (
        (),
        "query result:\n    from rows\n    group by:\n        id\n"
        "    select:\n        record_id = id\n        a = avg(id)\n"
        "    having:\n        a < 2.0\n",
    ),
    "fh_key": (
        (),
        "query result:\n    from rows\n    group by:\n        ratio\n"
        "    select:\n        ratio\n        n = count()\n"
        "    having:\n        ratio == 0.0\n",
    ),
    "fj_inner": (
        ("sa", "sb"),
        "query result:\n    from sa\n    let o = sb\n"
        "    inner join o on sa.ratio == o.ratio\n"
        "    select:\n        left_ratio = sa.ratio\n        right_ratio = o.ratio\n",
    ),
    "fj_left": (
        ("sa", "sb"),
        "query result:\n"
        + FLOAT_ZEROS
        + "    from sa\n    let o = zeros\n    left join o on sa.ratio == o.z\n"
        "    select:\n        left_ratio = sa.ratio\n        right_ratio = o.z\n",
    ),
    **{
        name: (
            ("sa", "sb"),
            # ANY reads a named producer, so the zeros are a table here.
            "table zeros:\n    from sb\n    where ratio < 1.0\n"
            "    select:\n        z = ratio\n"
            "query result:\n    from sa\n    let x = zeros\n"
            f"    where {negation}any(x.z == sa.ratio for x in x)\n"
            "    select:\n        r = sa.ratio\n",
        )
        for name, negation in (("fx_any", ""), ("fx_not_any", "not "))
    },
    **{
        name: (
            (),
            "query result:\n    from rows\n    select:\n        record_id = id\n"
            f"        ratio\n    order by:\n        ratio{direction}\n{limit}",
        )
        for name, direction, limit in (
            ("fo_ascending", "", ""),
            ("fo_descending", " desc", ""),
            ("fo_limit", "", "    limit 2\n"),
        )
    },
    "fd_rows": (
        (),
        "query result:\n    from rows\n    select distinct:\n        r = ratio\n",
    ),
    "fd_negative": (
        (),
        "query result:\n    from rows\n    where id > 1\n"
        "    select distinct:\n        r = ratio\n",
    ),
    "fd_positive": (
        ("sb",),
        "query result:\n    from sb\n    where ratio < 1.0\n"
        "    select distinct:\n        r = ratio\n",
    ),
    "fu_left_right": (("sa", "sb"), _float_set("union distinct", "a", "b")),
    "fu_negative": (
        (),
        _float_set("union distinct", "negatives", "negatives", FLOAT_NEGATIVES),
    ),
    "fi_distinct": (("sa", "sb"), _float_set("intersect distinct", "a", "b")),
    "fi_all": (("sa", "sb"), _float_set("intersect all", "a", "b")),
    "fi_negative": (
        (),
        _float_set("intersect distinct", "negatives", "negatives", FLOAT_NEGATIVES),
    ),
    "fe_distinct": (("sa", "sb"), _float_set("except distinct", "a", "b")),
    "fe_all": (("sa", "sb"), _float_set("except all", "a", "b")),
    "fe_rows_all": (
        ("rows", "sa"),
        _float_set(
            "except all",
            "every",
            "a",
            "table every:\n    from rows\n    select:\n        r = ratio\n"
            "table a:\n    from sa\n    select:\n        r = ratio\n",
        ),
    ),
    "fv_distinct": (
        (),
        "query result:\n    let pair:\n        values(r: Float):\n"
        "            0.0\n            -0.0\n"
        "    from pair\n    select distinct:\n        r\n",
    ),
    "fv_union": (
        (),
        _float_set("union distinct", "negative", "zero", FLOAT_VALUES),
    ),
    "fg_ratio": (
        (),
        "query result:\n    from rows\n    group by:\n        ratio\n"
        "    select:\n        ratio\n        n = count()\n",
    ),
    "fg_signed_let": (
        (),
        "query result:\n    from rows\n    let k = -0.0 if id > 1 else 0.0\n"
        "    group by:\n        k\n    select:\n        k\n        n = count()\n",
    ),
    "fg_widened": (
        (),
        "query result:\n    from rows\n    let k = Float(id)\n"
        "    group by:\n        k\n    select:\n        k\n        n = count()\n",
    ),
}


def float_fixture(target, variant):
    """One Lane E Float program over `rows` and the Agg seeds it names."""
    sources, body = FLOAT_BODIES[variant]
    item = parameterized_fixture(target, body, protocol=variant.startswith("fp_"))
    header = item["source"].removesuffix(body)
    contract = json.loads(item["contract"])
    agg = tuple(name for name in sources if name != "rows")
    if agg:
        if "rows" not in sources:
            # Only read sources are declared, as a compiled export binds each.
            header = header.split("source rows:", 1)[0]
            contract["sources"] = []
        header += AGGREGATE_HEADER.format(target=target).split("source agg:", 1)[0]
        header += "".join(
            f'source {name}: Agg = {target}.table("{name}.locator.not.sql")\n'
            for name in agg
        )
        contract["sources"].extend(
            _aggregate_descriptor(target, name, AGGREGATE_RELATIONS[name])
            for name in agg
        )
    return {
        "source": header + body,
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


def row_fixture(target, case, variant):
    """Ordered LET stages, a retained filter and admitted scalar projections."""
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    description = contract["sources"][0]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if variant.endswith("bind"):
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    if case in {"T_row_direct", "U_row_named"}:
        description["relation"]["name"] = "phase66 safe int source"
        description["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": "5"},
        }
    if variant.startswith("empty"):
        description["relation"]["name"] = (
            "phase66 safe int empty"
            if case in {"T_row_direct", "U_row_named"}
            else "phase66 empty é"
        )
    source: str | dict[str, str]
    if variant == "truth_table":
        source = (
            header
            + "table result:\n    from rows\n    select:\n"
            + "".join(
                f"        {label} = {expression}\n"
                for label, expression in zip(
                    TRUTH_LABELS,
                    (
                        "flag and True",
                        "flag and False",
                        "flag and flag",
                        "True and flag",
                        "False and flag",
                        "flag or True",
                        "flag or False",
                        "flag or flag",
                        "True or flag",
                        "False or flag",
                    ),
                    strict=True,
                )
            )
        )
    elif case == "T_row_direct":
        kind = "query" if variant.startswith("query") else "table"
        source = header + kind + " result:\n" + ROW_DIRECT_BODY
    elif case == "U_row_named":
        if variant.startswith("imported"):
            source = {
                "a.pietto": header + ROW_PRODUCER + "export table first\n",
                "main.pietto": 'from "a.pietto" import table first as Public\n'
                + ROW_CONSUMER.format(producer="Public"),
            }
            description["selector"]["module"] = "a.pietto"
        else:
            source = header + ROW_PRODUCER + ROW_CONSUMER.format(producer="first")
    elif variant == "match_join":
        # A retained MATCH exercises the same scalar domain; whole JOIN emission
        # stays with Slice7, so this input has no usable partial SQL.
        source = (
            header
            + """query result:
    from rows
    let r = rows
    inner join r on rows.id == r.id
    select:
        record_id = rows.id
"""
        )
    else:
        if variant in {"int_overflow", "unary_overflow"}:
            # The declared source domain is the whole signed 64-bit range, so the
            # result overflows on BOTH targets, not only the narrower one.
            description["fields"][0]["representation"]["domain"] = {
                "kind": "int_range",
                "min": "-9223372036854775808",
                "max": "9223372036854775807",
            }
        source = (
            header + "table result:\n    from rows\n    select:\n"
        ) + ROW_BLOCKED_BODY[variant]
    return {
        "source": source,
        "contract": encoded(contract).decode(),
        "policy": "bind_safe_literals"
        if variant.endswith("bind")
        else "preserve_literals",
    }


JOIN_LABELS = {
    "left_scalar_projections": (
        "a",
        "raw",
        "coalesced",
        "conditional",
        "membership",
        "floating",
        "bounded",
    ),
    "cross": ("a",),
    "inner": ("a",),
    "semi": ("a",),
    "anti": ("a",),
    "left_marker": ("a", "p", "m", "c", "t"),
    "right_accumulated": ("a", "b"),
    "via_refined": ("a", "k"),
    "restricted": ("a", "b"),
    "null_keys": ("a", "b"),
    **dict.fromkeys(
        ("inner_nulls", "left_nulls", "right_nulls"), ("l_id", "l_v", "r_id", "r_v")
    ),
}
# One filtered producer carrying, in one row, a retained source value, an authored
# literal, a computed value and an ordered LET result. A LEFT row with no match
# must null-extend every one of them.
JOIN_ENRICHED = """table enriched:
    from rows
    let step = id + 1
    where id > 0
    select:
        pid = id
        marker = 1
        computed = id + 1
        stepped = step
"""
# Two rows of the same source, so a RIGHT/FULL input has unmatched partners.
JOIN_LEFTISH = """table leftish:
    from rows
    where id > 1
    select:
        lid = id
"""
JOIN_BODIES = {
    "left_scalar_projections": JOIN_ENRICHED
    + """query result:
    from rows
    let r = enriched
    left join r on rows.id == r.pid
    select:
        a = rows.id
        raw = r.pid
        coalesced = coalesce(r.pid, rows.id)
        conditional = rows.id if r.pid is None else r.pid
        membership = rows.id in (1, 2)
        floating = Float(rows.id)
        bounded = 1 <= rows.id <= 9
""",
    "cross": """query result:
    from rows
    let r = rows
    cross join r
    select:
        a = rows.id
""",
    "inner": """query result:
    from rows
    let r = rows
    inner join r on rows.id == r.id
    select:
        a = rows.id
""",
    "semi": """query result:
    from rows
    let r = rows
    where any(rows.id == r.id for r in r)
    select:
        a = rows.id
""",
    "anti": """query result:
    from rows
    let r = rows
    where not any(rows.id == r.id for r in r)
    select:
        a = rows.id
""",
    "left_marker": JOIN_ENRICHED
    + """query result:
    from rows
    let r = enriched
    left join r on rows.id == r.pid
    select:
        a = rows.id
        p = r.pid
        m = r.marker
        c = r.computed
        t = r.stepped
""",
    "right_accumulated": JOIN_LEFTISH
    + """query result:
    from leftish
    let r = rows
    right join r on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
    "via_refined": """relationship link(l: Row, r: Row):
    l.id == r.id
query result:
    from rows
    let r = rows
    inner join r on link(rows, r) and rows.money == r.money
    select:
        a = rows.id
        k = r.id
""",
    "restricted": JOIN_LEFTISH
    + """query result:
    from leftish
    let r = rows
    full join r on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
}


# Pre-Slice16 corrective closure witnesses. Each one declares only the fields it
# reads of an existing relation, or of one of the finite row-domain relations the
# facility creates, so every document stays small inside the receipt ceiling.
CORRECTIVE_BODIES = {
    # G1 + G4: `base` is used plainly first and extended by a frame second, so
    # each occurrence keeps its own complete window (a first-use collapse would
    # give `earliest` the default frame); the nullable value distinguishes the
    # NULL-respecting results. The other encounter order, a PARTITION extension
    # and equal-content declarations are offline witnesses.
    ("A_window_named", "use_local"): """query result:
    from agg
    let base = window(order by rid)
    select:
        record_id = rid
        previous = lag(value) window base
        earliest = first_value(value) window base(rows between 1 preceding and current row)
""",
    # G2 / R09: left keys [1,2,NULL] against a filtered producer's [2,NULL,3].
    ("V_join_full", "null_keys"): """table rr:
    from agg
    where rid > 11
    select:
        rk = key
query result:
    from sa
    let r = rr
    full join r on sa.value == r.rk
    select:
        a = sa.value
        b = r.rk
""",
    # D77.52 O9: the unit-C statement (two sources over different tables, no
    # key, exactly `id` and a nullable Int `v`, every field selected in order)
    # over left keys [1,1,2,NULL,3] and right keys [0,1,1,NULL]; for RIGHT the
    # same text is the cell S1r.
    **{
        ("V_join_nullsafe", kind + "_nulls"): f"""query result:
    from lhs
    {kind} join rhs on same_value(lhs.v, rhs.v)
    select:
        l_id = lhs.id
        l_v = lhs.v
        r_id = rhs.id
        r_v = rhs.v
"""
        for kind in ("inner", "left", "right")
    },
    # G5 / C06 + G6: the declared relation's whole exposed domain, including a
    # duplicate key across parent and child, under BIND_SAFE with a bound data
    # literal and a structural LIMIT larger than the domain.
    ("G_scan_row_domains", "inherited_parent"): """query result:
    from rows
    where id > 0
    select:
        id
    order by:
        id
    limit 5
""",
    ("G_scan_row_domains", "view_rows"): """query result:
    from rows
    select:
        id
""",
    # G5 + G3: a SMALLINT partition root under an offset RANGE whose threshold is
    # wider than the key's own storage.
    ("G_scan_row_domains", "partitioned_root"): """query result:
    from rows
    select:
        id
        low = first_value(id) window(order by id range between 40000 preceding and current row)
        high = lag(id, 1, 999999999) window(order by id)
""",
}
ROW_DOMAIN_RELATIONS = {
    ("postgres", "inherited_parent"): "phase66 parent",
    ("mysql", "inherited_parent"): "phase66 family",
    ("postgres", "view_rows"): "phase66 parent only",
    ("mysql", "view_rows"): "phase66 parent only",
    ("postgres", "partitioned_root"): "phase66 part",
    ("mysql", "partitioned_root"): "phase66 part",
}


def _int_field(target, name, column, *, nullable, low, high, width=64):
    storage = {
        ("postgres", 16): "pg_int2",
        ("postgres", 64): "pg_int8",
        ("mysql", 16): "my_smallint",
        ("mysql", 64): "my_bigint",
    }[target, width]
    return {
        "name": name,
        "column": column,
        "representation": {
            "storage": {"kind": storage},
            "nullable": nullable,
            "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
        },
    }


def _declared_source(target, name, relation, fields):
    return {
        "selector": {"module": "main.pietto", "kind": "source", "name": name},
        "relation": {
            "namespace": "public" if target == "postgres" else "phase66",
            "name": relation,
        },
        "scan": "relation_rows",
        "fields": [{"ordinal": i, **field} for i, field in enumerate(fields)],
        "premises": [
            {"key": key, "scope": "source", "value": True}
            for key in ("row_domain_matches", "read_only_object")
        ],
    }


def corrective_fixture(target, case, variant):
    """One corrective witness over its exactly declared fields and relations."""
    wide = {"low": -9007199254740993, "high": 9007199254740993}
    policy = "preserve_literals"
    if case == "A_window_named":
        header = (
            "shape Keyed:\n    key: Int | None\n    value: Int | None\n"
            "    rid: Int\n"
            f'source agg: Keyed = {target}.table("aggregate.locator.not.sql")\n'
        )
        sources = [
            _declared_source(
                target,
                "agg",
                AGGREGATE_RELATIONS["grouped"],
                [
                    _int_field(target, "key", "group key", nullable=True, **wide),
                    _int_field(target, "value", "value é", nullable=True, **wide),
                    _int_field(target, "rid", "row id", nullable=False, **wide),
                ],
            )
        ]
    elif case == "V_join_full":
        header = (
            "shape Left:\n    value: Int | None\n"
            "shape Keyed:\n    key: Int | None\n    rid: Int\n"
            f'source sa: Left = {target}.table("sa.locator.not.sql")\n'
            f'source agg: Keyed = {target}.table("aggregate.locator.not.sql")\n'
        )
        sources = [
            _declared_source(
                target,
                "sa",
                AGGREGATE_RELATIONS["sa"],
                [_int_field(target, "value", "value é", nullable=True, **wide)],
            ),
            _declared_source(
                target,
                "agg",
                AGGREGATE_RELATIONS["grouped"],
                [
                    _int_field(target, "key", "group key", nullable=True, **wide),
                    _int_field(target, "rid", "row id", nullable=False, **wide),
                ],
            ),
        ]
    elif case == "V_join_nullsafe":
        header = (
            "shape Side:\n    id: Int\n    v: Int | None\n"
            f'source lhs: Side = {target}.table("lhs.locator.not.sql")\n'
            f'source rhs: Side = {target}.table("rhs.locator.not.sql")\n'
        )
        sources = [
            _declared_source(
                target,
                name,
                AGGREGATE_RELATIONS[relation],
                [
                    _int_field(target, "id", "row id", nullable=False, **wide),
                    _int_field(target, "v", "group key", nullable=True, **wide),
                ],
            )
            for name, relation in (("lhs", "grouped"), ("rhs", "keys"))
        ]
    else:
        header = (
            "shape One:\n    id: Int\n"
            f'source rows: One = {target}.table("row.domain.locator.not.sql")\n'
        )
        width = 16 if variant == "partitioned_root" else 64
        sources = [
            _declared_source(
                target,
                "rows",
                ROW_DOMAIN_RELATIONS[target, variant],
                [
                    _int_field(
                        target, "id", "id", nullable=False, low=0, high=99, width=width
                    )
                ],
            )
        ]
        if variant == "inherited_parent":
            policy = "bind_safe_literals"
    contract = json.loads(
        aggregate_fixture(target, "X_aggregate_global", "bag")["contract"]
    )
    contract["sources"] = sources
    if policy == "bind_safe_literals":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    return {
        "source": header + CORRECTIVE_BODIES[case, variant],
        "contract": encoded(contract).decode(),
        "policy": policy,
    }


def join_fixture(target, case, variant):
    """Authored JOIN shapes over the published source, for both pinned targets."""
    base = fixture(target)
    base_source = base["source"]
    assert type(base_source) is str
    header = base_source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if case == "W_join_values" and variant in {
        "left_marker",
        "left_scalar_projections",
    }:
        contract["sources"][0]["relation"]["name"] = "phase66 safe int source"
        contract["sources"][0]["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": "5"},
        }
    return {
        "source": header + JOIN_BODIES[variant],
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


JOIN_WITNESS_HEADER = """shape Row:
    id: Int
    key: Int | None
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
"""
JOIN_WITNESS_LINK = """relationship link(l: Row, r: Row):
    l.id == r.id
"""


def join_witness(target, body, *, link=False, policy="preserve_literals", module=None):
    """One authored two-source JOIN witness and its own emission contract.

    The second declared field is a NULLABLE Int, which the single published source
    does not offer, so an ON-induced narrowing and an outer null extension can be
    observed on the same column.
    """
    base = json.loads(fixture(target)["contract"])
    left = base["sources"][0]
    left["selector"]["module"] = module or "main.pietto"
    left["selector"]["name"] = "lhs"
    left["relation"]["name"] = "phase66 lhs é"
    identity = deepcopy(left["fields"][0])
    key = deepcopy(identity)
    key["ordinal"] = 1
    key["name"] = "key"
    key["column"] = "key value"
    key["representation"]["nullable"] = True
    left["fields"] = [identity, key]
    right = deepcopy(left)
    right["selector"]["name"] = "rhs"
    right["relation"]["name"] = "phase66 rhs é"
    base["sources"] = [left, right]
    base["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if policy == "bind_safe_literals":
        base["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = JOIN_WITNESS_HEADER.format(target=target) + (
        JOIN_WITNESS_LINK if link else ""
    )
    return {
        "source": header + body if type(body) is str else body,
        "contract": encoded(base).decode(),
        "policy": policy,
    }


LABELLED_HEADER = """shape Row:
    id: Int
    key: Int | None
    label: Text | None
    row_key = unique(id)
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
def band(x: Int) -> Int: return 1 if x <= 3 else 2
"""


def labelled_join_witness(target, body, *, policy="preserve_literals"):
    """`join_witness` whose sources also carry a nullable Text `label`, keyed
    by a unique `id`, with a def `band` that inlines to a conditional."""
    item = join_witness(
        target,
        {"main.pietto": LABELLED_HEADER.format(target=target) + body},
        policy=policy,
    )
    contract = json.loads(item["contract"])
    text = json.loads(fixture(target)["contract"])["sources"][0]["fields"][2]
    for source in contract["sources"]:
        label = deepcopy(text) | {"ordinal": 2, "name": "label", "column": "label"}
        label["representation"]["nullable"] = True
        source["fields"].append(label)
    return item | {"contract": encoded(contract).decode()}


def source_bytes(source):
    return source.encode("utf-8") if type(source) is str else encoded(source)


def source_files(source):
    return {"main.pietto": source} if type(source) is str else source


# Inputs whose only blocker was the not-yet-implemented WHERE family. Slice6
# implements that family, so each one now emits an independently checked query.
# The retained source purpose and the historical outcome are unchanged history;
# the variant name is not status authority.
MIGRATED_TO_SUCCESS = (
    # Phase77 S07: the GROUP BY of one Float field is a cell.
    ("V_aggregate_blocked", "float_key"),
    ("L_emission_blocked", "where_later"),
    # Q1 admits the exact qualified Timestamp and UUID source carriers.
    ("L_emission_blocked", "timestamp_meaning"),
    ("L_emission_blocked", "uuid_meaning"),
    ("O_named_later", "producer_filter"),
    # Slice7 implements the JOIN family that was these two inputs' only remaining
    # restriction. Their retained source purpose is unchanged history; a variant name
    # containing blocked or later is not outcome authority.
    ("O_named_later", "self_join"),
    ("V_row_blocked", "match_join"),
    # Slice10 realizes the three relation ORDER carriers these inputs retained
    # for structural inspection only; their source purpose is unchanged history.
    ("O_named_later", "order_ordinary"),
    ("O_named_later", "order_rebound"),
    ("O_named_later", "order_completed"),
    # Slice11 realizes the repeated UNION ALL graph and the two import facades
    # these inputs retained for structural inspection only.
    ("O_named_later", "union_dag"),
    ("O_named_later", "two_facades"),
    # Q2/Q3 admit checked Int BETWEEN and AVG(Int)'s target Float result.
    ("V_row_blocked", "between"),
    ("V_aggregate_blocked", "avg_direct"),
)
# PostgreSQL alone admits the published restricted FULL domain; MySQL keeps its
# typed non-support, so these variants are per-target.
PER_TARGET_STATUS = {
    # D73.14: MySQL refuses each Decimal, Date, Timestamp and UUID
    # declaration of these variants, whose reads sit outside its typed cells.
    ("Q_query_parameters", "typed_timestamp"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    ("Q_query_parameters", "typed_uuid"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ("V_join_full", "restricted"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ("Z_aggregate_joined", "full_restricted"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    # R15 admits GROUPS and its exclusion on PostgreSQL only; MySQL keeps a
    # typed blocker and is never given an emulation.
    ("A_window_groups", "exclude"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    # R09: the NULL-key FULL minimum positive is PostgreSQL only; MySQL keeps
    # its approved FULL non-support.
    ("V_join_full", "null_keys"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    # Q1/Q2: PostgreSQL's checked bigint operators and SUM narrowing bound a
    # result that may leave signed 64 bits (SQLSTATE 22003, never a wrapped
    # value); MySQL keeps PIE-B1002 and PIE-B1004 for the same programs.
    ("V_row_blocked", "int_overflow"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ("V_row_blocked", "unary_overflow"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ("V_row_blocked", "modulo"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    # S02: a direct sum of a nullable BIGINT field is a MySQL cell.
    ("V_aggregate_blocked", "sum_direct"): {
        "postgres": "VERIFIED",
        "mysql": "VERIFIED",
    },
    # Lane F: stddev is SQRT(CAST(VAR_SAMP(x) AS float8)) on PostgreSQL; MySQL
    # keeps Int refused (it computes BIGINT in DOUBLE) and Float unproved.
    ("V_aggregate_blocked", "stddev_direct"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    ("V_aggregate_blocked", "stddev_float"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    # The sample and population variances and the population deviation are
    # CAST(VAR_SAMP(x) ...), CAST(VAR_POP(x) ...) and SQRT(CAST(VAR_POP(x)
    # ...)) on PostgreSQL; MySQL keeps them refused as stddev.
    ("V_aggregate_blocked", "spread_direct"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    ("V_aggregate_blocked", "spread_float"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    # S16: PostgreSQL sums and averages a finite float8 and lowers a row
    # expression argument as a LET would; MySQL keeps a Float sum or average
    # unproved and this Int expression outside BIGINT's proven range.
    **dict.fromkeys(
        (
            ("V_aggregate_blocked", variant)
            for variant in (
                "sum_float",
                "avg_float",
                "inline_arguments",
                # MySQL keeps a project COUNT(DISTINCT a, b) refused.
                "count_distinct_tuple",
            )
        ),
        {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ),
    # Both targets count, deduplicate and compare Text, Bool, Float and
    # Decimal carriers by the group-key law (MySQL too).
    ("V_aggregate_blocked", "postgres_carriers"): {
        "postgres": "VERIFIED",
        "mysql": "VERIFIED",
    },
    ("V_aggregate_blocked", "sum_hidden_right"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    # D70.05: a statement without a physical source is refused on MySQL.
    ("Q_values_rows", "top"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    # D70.05: generate_series is PostgreSQL only, alone or joined.
    ("Q_table_function_series", "ascending"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    ("Q_table_function_series", "joined"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    **{
        ("L_retained_collection", variant): {"postgres": "VERIFIED", "mysql": "BLOCKED"}
        for variant in ("unnest", "outer")
    },
    # D-S08-4: Collect is PostgreSQL only; MySQL refuses every Collect read.
    **{
        ("L_relation_collect", variant): {"postgres": "VERIFIED", "mysql": "BLOCKED"}
        for variant in COLLECT_VARIANTS
    },
    # Phase72 Lane E (Branch B): MySQL keeps Float GROUP BY, DISTINCT, UNION
    # DISTINCT and `==` between two row reads refused (it kept -0.0 and 0.0
    # apart beside a wide key) outside the Phase77 S06 and S07 cells, and
    # refuses Float INTERSECT/EXCEPT and VALUES; PostgreSQL emits each of
    # these programs (relation ORDER is open on both, FLOAT_ON_BOTH_TARGETS).
    **{
        key: {"postgres": "VERIFIED", "mysql": "BLOCKED"}
        for key in (
            ("V_row_blocked", "float_comparison"),
            # E4: PostgreSQL emits Float field arithmetic (MySQL Phase77).
            ("V_row_blocked", "float_arithmetic"),
            ("V_result_blocked", "float_distinct"),
            ("V_set_blocked", "float_intersect_all"),
            *(
                (FLOAT_CASE, variant)
                for variant in VARIANTS[FLOAT_CASE]
                if variant not in FLOAT_ON_BOTH_TARGETS
            ),
        )
    },
}


def expected_status(case, variant, target=None):
    if target is not None and (case, variant) in PER_TARGET_STATUS:
        return PER_TARGET_STATUS[case, variant][target]
    if (case, variant) in MIGRATED_TO_SUCCESS:
        return "VERIFIED"
    if (case, variant) == ("Q_values_rows", "rejected"):
        return "BLOCKED"
    if case in {
        "V_row_blocked",
        "V_aggregate_blocked",
        "V_window_blocked",
        "V_result_blocked",
        "V_set_blocked",
    }:
        return "BLOCKED"
    return (
        "INPUT_REJECTED"
        if case == "K_emission_rejected"
        else "BLOCKED"
        if case in {"L_emission_blocked", "O_named_later"}
        else "VERIFIED"
    )


def generation_inputs(target):
    return [
        {"id": case, "variant": variant, **fixture(target, case, variant)}
        for case, variants in VARIANTS.items()
        for variant in variants
    ]


# Slice13: the finite installed-console witnesses. Each one drives the real
# installed `pietto emit-sql --project ...` command over an already-published
# fixture, so every console document must be byte-identical to the API record
# of the same (id, variant). Six public documents, four VERIFIED submissions.
CONSOLE_WITNESSES = (
    ("W1_table_text_output", "G_emission_table_bag", "bag", "table", "text", True),
    (
        "W2_fixed_bind_json_output",
        "R_fixed_direct",
        "table_bind",
        "table",
        "json",
        True,
    ),
    ("W3_imported_json", "N_imported_chain", "bag", "query", "json", False),
    ("W4_set_json", "S_set_forms", "union_all", "query", "json", False),
    (
        "W5_rejected_json",
        "K_emission_rejected",
        "duplicate_selector",
        "query",
        "json",
        False,
    ),
    ("W6_blocked_json", "L_emission_blocked", "missing_source", "query", "json", False),
)
CONSOLE_CASE = "CLI_console_emission"


def console_inputs(target):
    result = []
    for witness, case, variant, kind, presentation, output in CONSOLE_WITNESSES:
        item = fixture(target, case, variant)
        result.append(
            {
                "witness": witness,
                "id": case,
                "variant": variant,
                "kind": kind,
                "format": presentation,
                "output": output,
                "policy": item["policy"],
                "source_sha256": hashlib.sha256(
                    source_bytes(item["source"])
                ).hexdigest(),
                "contract_sha256": hashlib.sha256(
                    item["contract"].encode()
                ).hexdigest(),
            }
        )
    return result


# The closed CLI error vocabulary of the public emission family (Slice13).
CLI_ERROR_KINDS = frozenset(
    {
        "usage",
        "unsupported_dialect",
        "project_root",
        "config_read",
        "config_parse",
        "config_schema",
        "project_path",
        "project_glob",
        "project_resource",
        "source_read",
        "output_path",
        "output_write",
        "batch_output_limit",
        "batch_output_platform",
        "emission_contract_read",
        "emission_contract_schema",
        "emission_selector",
    }
)


def _need(value, message="invalid public artifact"):
    if not value:
        raise ValueError(message)


def _keys(value, keys):
    _need(type(value) is dict and set(value) == set(keys))


def _ordinal(value):
    return type(value) is int and value >= 0


def _pairs(items):
    value = {}
    for key, item in items:
        _need(key not in value, "duplicate public field")
        value[key] = item
    return value


def _location(value):
    if value is None:
        return
    _keys(value, ("path", "line", "column", "end_line", "end_column"))
    _need(value["path"] is None or type(value["path"]) is str)
    for key in ("line", "column", "end_line", "end_column"):
        _need(value[key] is None or (type(value[key]) is int and value[key] >= 1))


def _reference(value):
    _keys(value, ("kind", "position"))
    _need(type(value["kind"]) is str and _ordinal(value["position"]))


def _records(value) -> list[dict[str, Any]]:
    _need(type(value) is list and all(type(item) is dict for item in value))
    return cast(list[dict[str, Any]], value)


def _premise_shape(premise, enclosing=None):
    _keys(premise, ("key", "scope", "value"))
    local = {
        "row_domain_matches",
        "read_only_object",
        "value_domain",
        "encoding",
        "collation",
        "padding",
        "comparison_prefix_bytes",
    }
    statement = {
        "session_sql_mode",
        "session_time_zone",
        "client_encoding",
        "identifier_case",
        "parameter_protocol",
        "operator_environment",
        "resource_limits",
    }
    key, scope, value = premise["key"], premise["scope"], premise["value"]
    _need(type(key) is str and key in local | statement)
    if scope == "source":
        _need(enclosing is not None)
        scope = {"kind": "source", "selector": enclosing}
    if scope != "statement":
        _need(type(scope) is dict and scope.get("kind") in {"source", "expression"})
        _keys(
            scope,
            ("kind", "selector")
            if scope["kind"] == "source"
            else ("kind", "source", "site", "context"),
        )
        selector = cast(
            dict[str, Any],
            scope["selector"] if scope["kind"] == "source" else scope["source"],
        )
        _keys(selector, ("module", "kind", "name"))
        _need(
            selector["kind"] == "source"
            and all(
                type(selector[k]) is str and selector[k] for k in ("module", "name")
            )
        )
        if scope["kind"] == "expression":
            _reference(scope["site"])
            _reference(scope["context"])
            _need(key not in {"row_domain_matches", "read_only_object"})
    _need((key in statement) == (scope == "statement"))
    if key in {"row_domain_matches", "read_only_object"}:
        _need(type(value) is bool)
    elif key == "comparison_prefix_bytes":
        _need(_ordinal(value) and value > 0)
    elif key == "resource_limits":
        _need(
            type(value) is dict
            and bool(value)
            and not set(value)
            - {"sql_bytes", "artifact_bytes", "nodes", "parameters", "columns"}
            and all(_ordinal(v) for v in value.values())
        )
    elif key == "value_domain":
        _need(type(value) is dict and type(value.get("kind")) is str)
        value = cast(dict[str, Any], value)
        keys = {
            "int_range": {"kind", "min", "max"},
            "bool01": {"kind"},
            "text": {"kind", "max_characters", "encoding", "collation", "padding"},
            "decimal": {"kind", "precision", "scale"},
            "timestamp": {"kind"},
            "uuid": {"kind", "encoding"},
            "finite_float": {"kind", "format"},
            "date": {"kind"},
        }
        _need(value["kind"] in keys)
        _keys(value, keys[value["kind"]])
        _need(
            all(
                _ordinal(v)
                if k in {"precision", "scale", "max_characters"}
                else type(v) is str
                for k, v in value.items()
            )
        )
    else:
        _need(type(value) is str and bool(value))
    return key, json.dumps(scope, sort_keys=True), json.dumps(value, sort_keys=True)


def _contract_shape(contract):
    """Independent input-document schema checks, without selector resolution."""
    _keys(contract, ("format", "target", "sources", "environment"))
    selectors = set()
    premises = []
    storage_keys = {
        kind: {"kind"}
        for kind in (
            "pg_int2",
            "pg_int4",
            "pg_int8",
            "pg_bool",
            "pg_text",
            "pg_uuid",
            "pg_float8",
            "my_smallint",
            "my_int",
            "my_bigint",
            "my_bool01",
            "my_uuid_bytes",
            "my_double",
            "pg_date",
            "my_date",
        )
    }
    storage_keys.update(
        {
            "pg_numeric": {"kind", "precision", "scale"},
            "my_decimal": {"kind", "precision", "scale"},
            "my_varchar": {"kind", "length"},
            "pg_timestamp": {"kind", "fractional_seconds"},
            "my_datetime": {"kind", "fractional_seconds"},
        }
    )
    domain_keys = {
        "int_range": {"kind", "min", "max"},
        "bool01": {"kind"},
        "text": {"kind", "max_characters", "encoding", "collation", "padding"},
        "decimal": {"kind", "precision", "scale"},
        "timestamp": {"kind"},
        "uuid": {"kind", "encoding"},
        "finite_float": {"kind", "format"},
        "date": {"kind"},
    }
    for source in _records(contract["sources"]):
        _keys(source, ("selector", "relation", "scan", "fields", "premises"))
        _keys(source["selector"], ("module", "kind", "name"))
        _need(
            source["selector"]["kind"] == "source"
            and all(
                type(source["selector"][k]) is str and source["selector"][k]
                for k in ("module", "name")
            )
        )
        selector = json.dumps(source["selector"], sort_keys=True)
        _need(selector not in selectors)
        selectors.add(selector)
        _keys(source["relation"], ("namespace", "name"))
        _need(
            source["scan"] == "relation_rows"
            and all(type(v) is str and v for v in source["relation"].values())
        )
        ordinals, columns = set(), set()
        for field in _records(source["fields"]):
            _keys(field, ("ordinal", "name", "column", "representation"))
            _need(
                _ordinal(field["ordinal"])
                and field["ordinal"] not in ordinals
                and type(field["name"]) is str
                and field["name"]
                and type(field["column"]) is str
                and field["column"]
                and field["column"] not in columns
            )
            ordinals.add(field["ordinal"])
            columns.add(field["column"])
            representation = field["representation"]
            _keys(representation, ("storage", "nullable", "domain"))
            _need(
                type(representation["nullable"]) is bool
                or representation["nullable"] == "unknown"
            )
            for part, kinds in (("storage", storage_keys), ("domain", domain_keys)):
                value = representation[part]
                _need(
                    type(value) is dict
                    and type(value.get("kind")) is str
                    and value["kind"] in kinds
                )
                _keys(value, kinds[value["kind"]])
                for key, scalar in value.items():
                    _need(
                        (
                            _ordinal(scalar)
                            if key
                            in {
                                "precision",
                                "scale",
                                "length",
                                "max_characters",
                                "fractional_seconds",
                            }
                            else type(scalar) is str
                        )
                    )
        for premise in _records(source["premises"]):
            premises.append(_premise_shape(premise, source["selector"]))
    for premise in _records(contract["environment"]):
        premises.append(_premise_shape(premise))
    declared = {}
    for key, scope, value in premises:
        _need((key, scope) not in declared or declared[key, scope] == value)
        declared[key, scope] = value


def _field_compatibility(representation, family):
    """One source-field logical/storage/domain/NULL law shared by both decode routes."""
    _keys(representation, ("storage", "nullable", "domain"))
    _need(
        type(representation["nullable"]) is bool
        or representation["nullable"] == "unknown",
        "unsupported NULL posture",
    )
    storage, domain = representation["storage"], representation["domain"]
    widths = {
        "pg_int2": 16,
        "pg_int4": 32,
        "pg_int8": 64,
        "my_smallint": 16,
        "my_int": 32,
        "my_bigint": 64,
    }
    tags = {
        **dict.fromkeys(widths, "Int"),
        "pg_bool": "Bool",
        "my_bool01": "Bool",
        "pg_text": "Text",
        "my_varchar": "Text",
        "pg_numeric": "Decimal",
        "my_decimal": "Decimal",
        "pg_float8": "Float",
        "my_double": "Float",
        "pg_timestamp": "Timestamp",
        "my_datetime": "Timestamp",
        "pg_uuid": "UUID",
        "my_uuid_bytes": "UUID",
        "pg_date": "Date",
        "my_date": "Date",
    }
    kind = storage["kind"]
    _need(
        kind in tags and kind.startswith("pg_" if family == "postgres" else "my_"),
        "unsupported physical source storage",
    )
    tag = tags[kind]
    _need(
        domain["kind"]
        == {
            "Int": "int_range",
            "Bool": "bool01",
            "Text": "text",
            "Decimal": "decimal",
            "Float": "finite_float",
            "Timestamp": "timestamp",
            "UUID": "uuid",
            "Date": "date",
        }[tag],
        "physical storage and value domain disagree",
    )
    parameters = None
    if tag == "Int":
        limit = 1 << (widths[kind] - 1)
        bounds = []
        for key in ("min", "max"):
            spelling = domain[key]
            _need(
                type(spelling) is str
                and re.fullmatch(r"-?(0|[1-9][0-9]*)", spelling) is not None,
                "noncanonical declared range",
            )
            bound = int(spelling)
            _need(-limit <= bound < limit, "declared range outside signed storage")
            bounds.append(bound)
        _need(bounds[0] <= bounds[1], "empty declared range")
    elif tag == "Text":
        _need(
            domain["encoding"] == ("UTF8" if family == "postgres" else "utf8mb4")
            and domain["collation"]
            == ("C" if family == "postgres" else "utf8mb4_0900_bin")
            and domain["padding"] == "NO PAD",
            "unsupported text domain",
        )
        _need(
            _ordinal(domain["max_characters"]) and domain["max_characters"] > 0,
            "empty declared text length",
        )
        _need(
            kind != "my_varchar"
            or (
                _ordinal(storage["length"])
                and domain["max_characters"] <= storage["length"]
            ),
            "declared text length outside storage",
        )
    elif tag == "Decimal":
        parameters = {k: domain[k] for k in ("precision", "scale")}
        _need(
            all(_ordinal(v) for v in parameters.values())
            and 1 <= parameters["precision"] <= 65
            and 0 <= parameters["scale"] <= min(parameters["precision"], 30),
            "unsupported decimal precision or scale",
        )
        _need(
            all(storage[k] == parameters[k] for k in parameters),
            "decimal storage and value domain disagree",
        )
    elif tag == "Float":
        _need(domain["format"] == "binary64", "unsupported float format")
    elif tag == "Timestamp":
        _need(
            storage
            == {
                "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                "fractional_seconds": 6,
            },
            "unsupported timestamp storage",
        )
    elif tag == "UUID":
        _need(
            storage == {"kind": "pg_uuid" if family == "postgres" else "my_uuid_bytes"}
            and domain["encoding"] == "standard_bytes",
            "unsupported uuid storage",
        )
    return {"kind": "builtin", "name": tag, "parameters": parameters}


def _temporal_carrier(realization, family):
    """One exactly ordered Timestamp or Date carrier of its reviewed storage."""
    if realization["tag"] == "Timestamp":
        return realization["domain"] == {"kind": "timestamp"} and realization[
            "storage"
        ] == {
            "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
            "fractional_seconds": 6,
        }
    return (
        realization["tag"] == "Date"
        and realization["domain"] == {"kind": "date"}
        and realization["storage"]
        == {"kind": "pg_date" if family == "postgres" else "my_date"}
    )


def _public_premises(contract):
    return [
        *contract["environment"],
        *[p for source in contract["sources"] for p in source["premises"]],
    ]


def _identifier_token(text, family, role):
    quote = '"' if family == "postgres" else "`"
    _need(
        re.fullmatch(
            re.escape(quote)
            + "(?:"
            + re.escape(quote * 2)
            + "|[^"
            + re.escape(quote)
            + "])*"
            + re.escape(quote),
            text,
        )
        is not None
    )
    value = text[1:-1].replace(quote * 2, quote)
    _need(bool(value) and "\0" not in value, "unrepresentable identifier")
    if family == "postgres":
        _need(len(value.encode("utf-8")) <= 63, "identifier byte limit")
    else:
        _need(
            len(value) <= (256 if role == "label" else 64), "identifier character limit"
        )
        _need(all(ord(char) <= 0xFFFF for char in value))
        _need(role == "label" or not value.endswith(" "))
        if role in {"namespace", "relation"}:
            _need(not any(char in value for char in (".", "/", "\\")))
    return value


def _scan_definitions(document, occurrences):
    """Pair every emitted scan occurrence with the definition it names.

    Scan-naming tokens appear in exact emission order, which is also the order the
    reconciled occurrences were read in, so the pairing is positional and checked:
    one definition may never name two declared sources, and the counts must agree.
    """
    naming = [
        interval["subject"]
        for interval in sorted(
            _records(document["ranges"]), key=lambda item: (item["start"], item["end"])
        )
        if interval.get("role")
        in {"namespace", "join_namespace", "set_namespace", "exists_namespace"}
    ]
    _need(len(naming) == len(occurrences), "scan occurrence and relation counts")
    paired, selectors = [], {}
    for subject, (description, _) in zip(naming, occurrences, strict=True):
        _reference(subject)
        _need(subject["kind"] == "definition", "scan definition kind")
        key = subject["position"]
        selector = _selector_key(description)
        _need(
            selectors.setdefault(key, selector) == selector,
            "one definition cannot scan two declared sources",
        )
        paired.append((key, description))
    return paired


def _source_descriptors(document, reached):
    """Definition subjects that declare a physical source descriptor.

    A source definition publishes its own descriptor; a named producer does not.
    The admitted count is fixed independently by the reconciled scan occurrences,
    so neither an invented nor a dropped descriptor is accepted, and two distinct
    sources may not share one declaration site.
    """
    descriptors, causes = set(), []
    for interval in _records(document["ranges"]):
        subject = interval["subject"]
        _reference(subject)
        if subject["kind"] != "definition":
            continue
        if [o.get("role") for o in _records(interval["origins"])] != [
            "definition",
            "source_descriptor",
        ]:
            continue
        if subject["position"] in descriptors:
            continue
        descriptors.add(subject["position"])
        origin = cast(dict[str, Any], interval["origins"][1])
        causes.append(
            tuple(
                sorted(
                    (source["path"], _ordinal_location(source["location"]))
                    for source in _records(origin["sources"])
                    if source["kind"] == "authored_cause"
                )
            )
        )
    _need(len(descriptors) == len(reached), "declared source descriptor count")
    _need(len(set(causes)) == len(causes), "repeated source declaration site")
    return descriptors


def _ordinal_location(location):
    _need(location is not None)
    return (
        location["line"],
        location["column"],
        location["end_line"],
        location["end_column"],
    )


def _range_provenance(document):
    """Range provenance with the source descriptors fixed by the real scans."""
    contract = document["request"]["contract"]
    premises = _public_premises(contract)
    occurrences, _ = _scan_occurrences(
        document, contract, premises, document["target"]["family"]
    )
    reached = {_selector_key(description) for description, _ in occurrences}
    return _named_range_provenance(document, _source_descriptors(document, reached))


def _selector_key(description):
    selector = description["selector"]
    return selector["module"], selector["kind"], selector["name"]


# A node copied by relationship predicate expansion, row normalization or an
# ANY generator publishes its authored sources in place of an authored cause.
# The expansion leads the origin's sources and its first source is the copy's
# authored site in the owner: the call, the normalized expression or the ANY.
EXPANSION_SITES = {
    "relationship_predicate_call",
    "relationship_predicate_generated_call",
    "normalized_expression",
    "existence_generator_expansion",
    "existence_value_expansion",
}
EXPANSIONS = EXPANSION_SITES | {
    "relationship_predicate_body",
    "relationship_predicate_argument",
    "relationship_predicate_generated_argument",
}


def _cause_location(origin):
    """The authored cause, or the authored site of a validated expansion."""
    sources = origin["sources"]
    return next(
        (s["location"] for s in sources if s["kind"] == "authored_cause"),
        sources[0]["location"],
    )


# S6: the EXISTS read an `any` value expands into is caused by that `any`
# call, not by an authored clause: its own read tokens and its block use only.
EXISTENCE_EXPANSION = "existence_value_expansion"
EXISTENCE_EXPANSION_ROLES = {
    "expression": frozenset(
        {
            "exists_open",
            "exists_select",
            "exists_sentinel",
            "exists_from",
            "exists_where",
            "exists_close",
            "exists",
        }
    ),
    "expression_block_use": frozenset({"exists_alias", "exists_scope"}),
}
# S6: a JOIN-prefix `any` becomes one hidden SEMI/ANTI JOIN, caused by that
# `any` expansion: every subject with a range inside that JOIN's own CTE.
GENERATOR_EXPANSION = "existence_generator_expansion"


def _hidden_membership_subjects(document):
    """Subjects of each membership JOIN CTE no authored JOIN clause causes."""
    intervals = sorted(
        _records(document["ranges"]), key=lambda item: (item["start"], item["end"])
    )
    found = set()
    for opening in intervals:
        if opening.get("role") != "membership_open":
            continue
        join = opening["subject"]
        names = [
            i for i in intervals if i["role"] == "cte_name" and i["subject"] == join
        ]
        closes = [
            i
            for i in intervals
            if i["role"] == "cte_body_close" and i["subject"] == join
        ]
        if len(names) != 1 or len(closes) != 1:
            continue
        start, end = names[0]["start"], closes[0]["end"]
        found.update(
            (i["subject"]["kind"], i["subject"]["position"])
            for i in intervals
            if start <= i["start"] and i["end"] <= end
        )
    return found


def _named_range_provenance(document, descriptors):
    modules = {source["module"] for source in document["request"]["sources"]}
    subjects, positions = {}, {}
    hidden = _hidden_membership_subjects(document)
    roles = {
        "selected_plan": ["selected_owner"],
        "definition": ["definition"],
        "source_port": ["source_port"],
        "result_port": ["result_port"],
        "input_use": ["input_use"],
        "input_port": ["input_port"],
        "projection": ["projection"],
        # A SELECT export is both a stage export and an export; a SET-owned
        # export has no SELECT stage behind it.
        "export": (["stage_export", "export"], ["stage_export"]),
        "expression": ["expression"],
        "literal_site": ["literal_site"],
        # Slice6 stage bodies own their own generated scope, carried stage ports
        # and filter root; each one still declares exactly its own origin role.
        "select_block": ["select_block"],
        "stage_port": ["stage_port"],
        "filter": ["filter"],
        # Slice8 aggregation stages own their determinants and occurrences.
        "aggregation": ["aggregation"],
        "group_key": ["group_key"],
        "aggregate": ["aggregate"],
        "aggregate_projection": ["aggregate_projection"],
        # Slice9 window stages own their own occurrence and its policy.
        "window": ["window"],
        "window_policy": ["window_policy"],
        # Slice7 JOIN units own their own occurrence, inputs, ports and tail.
        "join": ["join"],
        "join_input": ["join_input"],
        "join_port": ["join_port"],
        "join_tail": ["join_tail"],
        "relationship_match": ["relationship_match"],
        # Slice10 result boundaries own their own boundary, quotient, ORDER
        # occurrence/items and static LIMIT.
        "result_boundary": ["result_boundary"],
        "distinct": ["distinct"],
        "relation_order": ["relation_order"],
        "order_item": ["order_item"],
        "result_limit": ["result_limit"],
        # Slice11 SET units own their body, each operand use and each input.
        "set_body": ["set_body"],
        "set_operand": ["set_operand"],
        "set_input": ["set_input"],
        # Phase70 VALUES units own their body and each declared column.
        "values_body": ["values_body"],
        "values_column": ["values_column"],
        # Phase70: one expression block use per relation read.
        "expression_block_use": ["expression_block_use"],
        # Phase70 S10: one capture record per capture line.
        "capture": ["capture"],
        # Phase71 S08: one record per Collect read.
        "collect": ["collect"],
        "unnest": ["unnest"],
    }
    associations = {
        "authored_cause",
        "expression_body",
        "field_declaration",
        "type_reference",
        "referenced_declaration",
        "import_item",
        "export_item",
        "source_connector",
        # Slice9 window provenance associates an effective occurrence with its
        # authored one, each component with the occurrence that authored or
        # inherited it, and a named use with its declaration.
        "effective_to_authored_window",
        "authored_or_inherited_window_component",
        "named_window_declaration",
        *EXPANSIONS,
    }
    for interval in _records(document["ranges"]):
        expansion = interval.get("role") in EXISTENCE_EXPANSION_ROLES.get(
            interval["subject"]["kind"], ()
        )
        generated = (
            interval["subject"]["kind"],
            interval["subject"]["position"],
        ) in hidden
        _reference(interval["subject"])
        key = interval["subject"]["kind"], interval["subject"]["position"]
        origins = _records(interval["origins"])
        expected = (
            ["definition", "source_descriptor"]
            if key[0] == "definition" and key[1] in descriptors
            else roles.get(key[0])
        )
        alternatives = expected if type(expected) is tuple else (expected,)
        _need(
            expected is not None and [o.get("role") for o in origins] in alternatives,
            "range origin roles",
        )
        _need(
            key not in subjects or subjects[key] == origins,
            "inconsistent repeated-subject provenance",
        )
        subjects[key] = origins
        previous = -1
        for origin in origins:
            _keys(origin, ("position", "role", "sources"))
            _need(_ordinal(origin["position"]) and origin["position"] > previous)
            previous = origin["position"]
            _need(
                origin["position"] not in positions
                or positions[origin["position"]] == key,
                "foreign origin subject",
            )
            positions[origin["position"]] = key
            kinds = []
            for source in _records(origin["sources"]):
                _keys(source, ("path", "kind", "location"))
                # S6: a lone existence expansion causes only the EXISTS read an
                # `any` value expands into (its read tokens and block use) or a
                # subject inside the hidden SEMI/ANTI JOIN of a JOIN-prefix `any`.
                misplaced = len(origin["sources"]) == 1 and (
                    source["kind"] == EXISTENCE_EXPANSION
                    and not expansion
                    or source["kind"] == GENERATOR_EXPANSION
                    and not generated
                )
                _need(
                    source["path"] in modules
                    and source["kind"] in associations
                    and not misplaced,
                    "range origin module or association",
                )
                _location(source["location"])
                location = source["location"]
                if location is None:
                    raise ValueError("missing origin location")
                _need(location["path"] == source["path"])
                _need(
                    all(
                        type(location[k]) is int
                        for k in ("line", "column", "end_line", "end_column")
                    )
                )
                _need(
                    (location["line"], location["column"])
                    <= (location["end_line"], location["end_column"])
                )
                kinds.append(source["kind"])
            # Exactly one authored cause, or else a copy's leading expansion.
            expanded = [kind for kind in kinds if kind in EXPANSIONS]
            having_bridge = (
                kinds.count("authored_cause") == 1
                and bool(expanded)
                and all(kind == "normalized_expression" for kind in expanded)
                and document["target"]["family"] == "postgres"
                and any(item["role"] == "satisfying" for item in document["ranges"])
            )
            _need(
                having_bridge
                or kinds.count("authored_cause") + bool(expanded) == 1
                and kinds[: len(expanded)] == expanded
                and (not expanded or expanded[0] in EXPANSION_SITES),
                "missing authored range cause",
            )
    return subjects


def _decode_named_sql(document, fields, limits):
    """Read the finite WITH grammar from bytes; never import compiler machinery."""
    sql = document["sql"].encode("utf-8")
    provenance = _range_provenance(document)
    expected_case = (
        "quoted_exact"
        if document["target"]["family"] == "postgres"
        else "lower_case_table_names=0"
    )
    cases = [
        p["value"]
        for p in _public_premises(document["request"]["contract"])
        if p["key"] == "identifier_case" and p["scope"] == "statement"
    ]
    _need(bool(cases) and all(value == expected_case for value in cases))
    tokens = []
    offset = 0
    for interval in _records(document["ranges"]):
        _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
        _need(type(interval["start"]) is int and type(interval["end"]) is int)
        _need(interval["start"] == offset < interval["end"] <= len(sql))
        text = sql[offset : interval["end"]].decode("utf-8")
        _need(interval["kind"] in {"identifier", "syntax"})
        if interval["kind"] == "identifier":
            text = _identifier_token(
                text, document["target"]["family"], interval["role"]
            )
        tokens.append((interval["kind"], interval["role"], text, interval["subject"]))
        offset = interval["end"]
    _need(offset == len(sql))
    cursor = 0

    def reference(kind, position):
        return {"kind": kind, "position": position}

    def origins(ref):
        return provenance[ref["kind"], ref["position"]]

    def cause(ref):
        locations = [_cause_location(o) for o in origins(ref)]
        _need(
            all(location == locations[0] for location in locations),
            "conflicting subject causes",
        )
        return locations[0]

    def within(child, parent):
        return child["path"] == parent["path"] and (
            parent["line"],
            parent["column"],
        ) <= (child["line"], child["column"]) <= (
            child["end_line"],
            child["end_column"],
        ) <= (parent["end_line"], parent["end_column"])

    def take(kind, role, text=None, subject=None):
        nonlocal cursor
        _need(cursor < len(tokens), "missing SQL token")
        actual_kind, actual_role, actual_text, actual_subject = tokens[cursor]
        cursor += 1
        _need((actual_kind, actual_role) == (kind, role))
        _need(text is None or actual_text == text)
        _need(subject is None or actual_subject == subject)
        return actual_text, actual_subject

    def peek():
        return tokens[cursor][1] if cursor < len(tokens) else None

    ctes = {}
    bodies = []
    field_uses = []
    projection_base = 0
    input_base = 0
    physical_count = 0
    description = fields[0][1]
    originals = Counter()

    def select(owner, final=False):
        nonlocal projection_base, input_base, physical_count
        take("syntax", "select", "SELECT ", owner)
        selected = []
        while True:
            i = len(selected)
            projection = reference("projection", projection_base + i)
            export = reference("export", projection_base + i)
            if i:
                take("syntax", "separator", ", ", projection)
            alias, input_ref = take("identifier", "column_scope")
            _need(input_ref["kind"] == "input_port")
            take("syntax", "qualifier", ".", projection)
            name, terminal = take("identifier", "column")
            take("syntax", "alias", " AS ", projection)
            label, _ = take("identifier", "label", None if final else f"c{i}", export)
            selected.append(
                (alias, input_ref, name, terminal, label, projection, export)
            )
            if peek() != "separator":
                break
        _, producer_ref = take("syntax", "from", " FROM ")
        _need(producer_ref["kind"] == "definition")
        producer_name = None
        if peek() == "namespace":
            _need(producer_ref == reference("definition", 0))
            take(
                "identifier",
                "namespace",
                description["relation"]["namespace"],
                producer_ref,
            )
            take("syntax", "qualifier", ".", producer_ref)
            take(
                "identifier", "relation", description["relation"]["name"], producer_ref
            )
            producer_columns = [
                {
                    "name": f["column"],
                    "terminal": reference("source_port", f["ordinal"]),
                    "field": f,
                }
                for f in description["fields"]
            ]
            physical_count += 1
        else:
            producer_name, _ = take("identifier", "cte_reference", subject=producer_ref)
            _need(producer_name in ctes, "forward or captured CTE reference")
            _need(ctes[producer_name]["definition"] == producer_ref)
            producer_columns = ctes[producer_name]["columns"]
        use = reference("input_use", len(bodies))
        take("syntax", "alias", " AS ", use)
        alias, _ = take("identifier", "relation_scope", f"s{len(bodies)}", use)
        consumer_cause, producer_cause, use_cause = (
            cause(owner),
            cause(producer_ref),
            cause(use),
        )
        _need(within(use_cause, consumer_cause), "use outside consumer source scope")
        route = origins(use)[0]["sources"]
        _need(
            any(
                s["kind"] == "referenced_declaration"
                and s["location"] == producer_cause
                for s in route
            ),
            "missing immediate producer declaration",
        )
        hops = [s for s in route if s["kind"] in {"import_item", "export_item"}]
        module = consumer_cause["path"]
        _need(len(hops) % 2 == 0)
        for imported, exported in zip(hops[::2], hops[1::2], strict=True):
            _need(
                imported["kind"] == "import_item"
                and imported["path"] == module
                and exported["kind"] == "export_item",
                "broken import provenance trail",
            )
            module = exported["path"]
        _need(module == producer_cause["path"], "missing import provenance trail")
        names = {
            column["name"]: (i, column) for i, column in enumerate(producer_columns)
        }
        _need(len(names) == len(producer_columns))
        output = []
        for i, (
            qualifier,
            input_ref,
            name,
            terminal,
            label,
            projection,
            export,
        ) in enumerate(selected):
            _need(qualifier == alias and name in names)
            index, producer_column = names[name]
            _need(input_ref == reference("input_port", input_base + index))
            _need(terminal == producer_column["terminal"], "wrong immediate terminal")
            _need(cause(input_ref) == use_cause, "input port outside its use")
            _need(
                cause(terminal) == producer_cause,
                "terminal outside producer source scope",
            )
            _need(
                cause(export) == cause(projection)
                and within(cause(projection), consumer_cause),
                "projection/export source correspondence",
            )
            field = producer_column["field"]
            if final:
                _need(i < len(fields))
                public = fields[i][0]
                correspondence = public["correspondence"]
                _need(label == public["label"] and field is fields[i][2])
                _need(correspondence["input_port"] == input_ref)
                _need(
                    correspondence["projection"] == projection
                    and correspondence["export"] == export
                )
                _need(
                    correspondence["source_port"]
                    == reference("source_port", field["ordinal"])
                )
            field_uses.append((field["ordinal"], projection["position"], len(bodies)))
            output.append(
                {
                    "name": label,
                    "terminal": reference("result_port", projection_base + i),
                    "field": field,
                }
            )
        _need(not final or len(output) == len(fields))
        n = len(output)
        originals.update(
            {
                "export_representation": n,
                "expression": n,
                "stage_value": len(producer_columns),
                "scope": 1,
                "result": 2 * n,
            }
        )
        bodies.append(
            {
                "producer": producer_name,
                "producer_columns": producer_columns,
                "use": use,
                "columns": output,
            }
        )
        projection_base += n
        input_base += len(producer_columns)
        return output

    take("syntax", "with", "WITH ", reference("selected_plan", 0))
    _need(
        cause(reference("selected_plan", 0))["path"]
        == document["request"]["owner"]["module"]
    )
    _need(
        cause(reference("definition", 0))["path"] == description["selector"]["module"]
    )
    while True:
        index = len(ctes)
        definition = reference("definition", index + 1)
        if index:
            take("syntax", "cte_separator", ", ", definition)
        name, _ = take("identifier", "cte_name", f"p{index}", definition)
        take("syntax", "cte_columns_open", " (", definition)
        header = []
        while True:
            position = len(header)
            terminal = reference("result_port", projection_base + position)
            if position:
                take("syntax", "terminal_separator", ", ", terminal)
            take("identifier", "terminal_column", f"c{position}", terminal)
            _need(
                cause(terminal) == cause(definition),
                "CTE header outside defining source",
            )
            header.append(terminal)
            if peek() != "terminal_separator":
                break
        take("syntax", "cte_body_open", ") AS (", definition)
        output = select(definition)
        _need(header == [c["terminal"] for c in output])
        take("syntax", "cte_body_close", ")", definition)
        ctes[name] = {
            "definition": definition,
            "columns": output,
            "producer": bodies[-1]["producer"],
        }
        if peek() != "cte_separator":
            break
    take("syntax", "with_body", " ", reference("definition", len(ctes) + 1))
    _need(
        cause(reference("definition", len(ctes) + 1))
        == cause(reference("selected_plan", 0))
    )
    select(reference("selected_plan", 0), final=True)
    _need(cursor == len(tokens) and physical_count == 1)
    visited = set()
    producer = bodies[-1]["producer"]
    while producer is not None:
        _need(producer not in visited)
        visited.add(producer)
        producer = ctes[producer]["producer"]
    _need(visited == set(ctes), "unreferenced SQL definition")
    originals["source_realization"] = 1
    generated = []
    for cte in ctes.values():
        generated.append(("cte_definition", "R03", cte["definition"], "naming"))
        generated.extend(
            ("terminal_column", "R03", c["terminal"], "naming") for c in cte["columns"]
        )
    for body in bodies:
        if body["producer"] is None:
            generated.append(("qualified_scan", "R01", None, "scan"))
            generated.extend(
                ("source_representation", "R02", None, ("field", field["ordinal"]))
                for field in description["fields"]
            )
        else:
            generated.append(("named_use", "R03", body["use"], "naming"))
            generated.extend(
                ("immediate_terminal", "R03", c["terminal"], "naming")
                for c in body["producer_columns"]
            )
        generated.extend(
            ("field_projection", "R02", None, ("field", c["field"]["ordinal"]))
            for c in body["columns"]
        )
        generated.append(("read_only_select_bytes", "R23", None, "none"))
    generated.append(("nonrecursive_with_bytes", "R23", None, "none"))
    _need(all(len(body["columns"]) <= limits["columns"] for body in bodies))
    _need(
        3 * len(bodies)
        + 2 * projection_base
        + 2 * len(ctes)
        + sum(len(c["columns"]) for c in ctes.values())
        <= limits["nodes"]
    )
    return originals, generated, field_uses


def _fixed_payload(tag, value):
    if value is None:
        _need(tag in {"Bool", "Int", "Float", "Text", "Date", "Timestamp", "UUID"})
        return None
    if tag == "Bool":
        _need(type(value) is bool)
        return value
    if tag == "Int":
        if type(value) is int:
            _need(-(1 << 63) <= value < 1 << 63)
            return value
        _need(
            type(value) is str and re.fullmatch(r"-?(0|[1-9][0-9]*)", value) is not None
        )
        result = int(value)
        _need(str(result) == value and -(1 << 63) <= result < 1 << 63)
        return result
    if tag == "Float":
        _need(type(value) is str)
        try:
            result = float.fromhex(value)
        except OverflowError as error:
            raise ValueError("nonfinite binary64 payload") from error
        _need(math.isfinite(result) and result.hex() == value)
        return result
    _need(tag == "Text" and type(value) is str)
    value.encode("utf-8")
    return value


def _fixed_physical(family, tag):
    return {
        "postgres": {
            "Bool": "pg_bool",
            "Int": "pg_int8",
            "Float": "pg_float8",
            "Text": "pg_text",
        },
        "mysql": {
            "Bool": "my_signed_bool",
            "Int": "my_signed_int",
            "Float": "my_double",
            "Text": "my_utf8mb4_text",
        },
    }[family][tag]


def parameter_text(tag, value):
    """The wire text of one Decimal, Date, Timestamp or UUID header value
    (None: not a value of ``tag``): plain decimal digits without trailing
    zeros (``0`` for any zero), ISO date and timestamp (space, six fractional
    digits) in the civil interval from 1000-01-01, canonical lower-case UUID."""
    if tag == "Decimal" and type(value) is Decimal and value.is_finite():
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return "0" if text in ("0", "-0") else text
    if tag == "Date" and type(value) is date and value >= date(1000, 1, 1):
        return value.isoformat()
    if (
        tag == "Timestamp"
        and type(value) is datetime
        and value.tzinfo is None
        and datetime(1000, 1, 1) <= value <= datetime(9999, 12, 31, 23, 59, 59, 499999)
    ):
        return value.isoformat(" ", "microseconds")
    if tag == "UUID" and type(value) is UUID:
        return str(value)
    return None


def _binding_value(family, tag, value):
    """One caller binding of a v2 header parameter, exactly as the driver sends it."""
    if tag in PARAMETER_PHYSICAL[family]:
        return parameter_text(tag, value) is not None
    if tag == "Bool":
        return type(value) is bool
    if tag == "Int":
        return type(value) is int and -(1 << 63) <= value < 1 << 63
    if tag == "Float":
        return type(value) is float and math.isfinite(value)
    if tag != "Text" or type(value) is not str:
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    # PostgreSQL text cannot hold NUL; MySQL text can.
    return family == "mysql" or "\0" not in value


def decoded_arguments(document, bindings=None):
    """Ordered native values only from the independently decoded public map.

    A v2 template names its header parameters but carries no value for them;
    ``bindings`` gives one by parameter name, exactly the caller's values."""
    result, assigned, owner_indices = [], {}, {}
    family = document["target"]["family"]
    header = document.get("parameters", [])
    _need(
        (bindings is None) == (not header)
        and (bindings is None or set(bindings) == {p["name"] for p in header})
    )
    # Every declared parameter is bound, whether or not the statement reads it.
    for parameter in header:
        assert bindings is not None
        value = bindings[parameter["name"]]
        _need(
            parameter["nullable"]
            if value is None
            else _binding_value(family, parameter["tag"], value),
            "binding outside its parameter",
        )
    for use in document["parameter_uses"]:
        owner = use.get("owner", {"kind": "slot", "slot": use.get("slot")})
        if owner["kind"] == "slot":
            key = ("slot", owner["slot"])
            value = document["fixed_values"][owner["slot"]]
            tag = value["tag"]
            decoded = _fixed_payload(tag, value["value"])
        else:
            _need(owner["kind"] == "parameter" and bindings is not None)
            assert bindings is not None
            key = ("parameter", owner["parameter"])
            parameter = header[owner["parameter"]]
            tag, decoded = parameter["tag"], bindings[parameter["name"]]
            if tag in PARAMETER_PHYSICAL[family] and decoded is not None:
                # The anchor casts the value's canonical text.
                decoded = parameter_text(tag, decoded)
        if family == "mysql" and tag == "Bool" and decoded is not None:
            _need(type(decoded) is bool, "MySQL Bool fixed payload")
            assert type(decoded) is bool
            decoded = int(decoded)
        index = use["server_index"]
        if family == "postgres" and key in owner_indices:
            _need(index == owner_indices[key])
        if index in assigned:
            _need(
                family == "postgres" and assigned[index] == (key, use["physical_type"])
            )
        else:
            _need(type(index) is int and index == len(result) + 1)
            assigned[index] = key, use["physical_type"]
            result.append(decoded)
            owner_indices[key] = index
    return tuple(result)


def _declared_sources(contract, premises):
    """Each declared source with its source-scoped premise positions, in order:
    `"source"` in its own premises, or a `{"kind": "source"}` scope selecting it."""
    result = []
    base = len(contract["environment"])
    for source in contract["sources"]:
        selected = {"kind": "source", "selector": source["selector"]}
        own = range(base, base + len(source["premises"]))
        positions = [
            i
            for i, p in enumerate(premises)
            if p["scope"] == selected or (i in own and p["scope"] == "source")
        ]
        result.append((source, positions))
        base += len(source["premises"])
    return result


def _statement_premises(premises, family):
    statements = [i for i, p in enumerate(premises) if p["scope"] == "statement"]
    for key, expected in (
        ("operator_environment", "builtin_only"),
        ("client_encoding", "UTF8" if family == "postgres" else "utf8mb4"),
    ):
        found = [premises[i]["value"] for i in statements if premises[i]["key"] == key]
        _need(bool(found) and all(value == expected for value in found))
    return statements


def _scan_occurrences(document, contract, premises, family):
    """One record per emitted physical scan occurrence, in requirement order.

    One declared source may legitimately be scanned by several uses, so these are
    occurrences, not sources: they are never deduplicated by selector, relation
    spelling or premise closure. A named CTE reference is not a scan occurrence and
    contributes no record here.
    """
    statements = _statement_premises(premises, family)
    declared = _declared_sources(contract, premises)
    occurrences = []
    for requirement in document["requirements"]:
        if requirement.get("denominator") != "generated" or (
            requirement.get("kind") != "qualified_scan"
        ):
            continue
        candidates = [
            (source, positions)
            for source, positions in declared
            if requirement["premises"] == sorted([*statements, *positions])
        ]
        _need(len(candidates) == 1, "ambiguous physical row source")
        description, source_positions = candidates[0]
        for key in ("row_domain_matches", "read_only_object"):
            _need(
                any(
                    premises[i]["key"] == key and premises[i]["value"] is True
                    for i in source_positions
                ),
                "unestablished physical scan premise",
            )
        occurrences.append((description, source_positions))
    valued = any(
        r.get("denominator") == "generated"
        and r.get("kind") in {"values_rows", "table_function"}
        for r in document["requirements"]
    )
    _need(
        bool(occurrences) or valued,
        "an emitted query must reach a physical relation or a VALUES body",
    )
    return occurrences, statements


def _selected_scan(document, contract, premises, family):
    """The one physical scan a single-input public grammar must agree on."""
    occurrences, statements = _scan_occurrences(document, contract, premises, family)
    _need(len(occurrences) == 1)
    description, source_positions = occurrences[0]
    return description, source_positions, statements


def _premise_domain(premises, selector, scoped, sites):
    """Statement/source premises, plus expression premises at these exact sites."""
    result = list(scoped)
    for position, premise in enumerate(premises):
        if any(
            premise["scope"]
            == {
                "kind": "expression",
                "source": selector,
                "site": {"kind": "expression_site", "position": projection},
                "context": {"kind": "select_block", "position": block},
            }
            for projection, block in sites
        ):
            result.append(position)
    return sorted(result)


def _field_premises(premises, description, scoped, field_uses):
    """One applicable premise domain per retained field, keyed by its ordinal."""
    return {
        field["ordinal"]: _premise_domain(
            premises,
            description["selector"],
            scoped,
            [(p, b) for ordinal, p, b in field_uses if ordinal == field["ordinal"]],
        )
        for field in description["fields"]
    }


def _requirement_premises(key, naming, scan_premises, physical):
    """Resolve one premise sentinel; a JOIN names its own scan occurrence."""
    if key == "naming":
        return naming
    if key == "scan":
        return scan_premises[0]
    if type(key) is not tuple:
        return []
    if key[0] == "scan":
        return scan_premises[key[1]]
    if key[0] == "field" and len(key) == 3:
        return physical[key[1]][key[2]]
    return physical[0][key[1]]


def _decode_row_denominators(
    document, limits, premises, statements, occurrences, naming, walk
):
    """Both requirement denominators for one decoded stage pipeline."""
    bodies = walk["bodies"]
    field_uses = []
    for column in document["columns"]:
        origin = column["correspondence"].get("computed_origin")
        if origin is None or origin.get("field") is None:
            continue
        _reference(origin["site"])
        _reference(origin["stage"])
        _need(
            origin["site"]["kind"] == "expression_site"
            and origin["stage"]["kind"] == "select_block",
            "computed origin context kinds",
        )
        field_uses.append(
            (origin["field"], origin["site"]["position"], origin["stage"]["position"])
        )
    scan_premises = [sorted([*statements, *positions]) for _, positions in occurrences]
    physical = [
        _field_premises(premises, item, scan_premises[i], field_uses)
        for i, (item, _) in enumerate(occurrences)
    ]
    expected = [*walk["scopes"], *walk["generated"]]
    # A statement with a WITH clause names its generated scopes. An inline let
    # (a captured let a Collect read collects) is a body without one.
    generated_scopes = bool(walk["ctes"])
    if generated_scopes:
        expected.append(("nonrecursive_with_bytes", None, "R23", [], None))
    originals, actual = [], []
    for requirement in document["requirements"]:
        _keys(
            requirement,
            (
                "denominator",
                "ordinal",
                "kind",
                "subject",
                "rule",
                "disposition",
                "premises",
                "evidence",
            ),
        )
        _need(
            requirement["denominator"] in {"original", "generated"}
            and requirement["disposition"] == "checked_rule"
        )
        _reference(requirement["subject"])
        _need(
            type(requirement["premises"]) is list
            and all(_ordinal(i) and i < len(premises) for i in requirement["premises"])
        )
        _need(type(requirement["evidence"]) is list)
        bucket = originals if requirement["denominator"] == "original" else actual
        _need(
            type(requirement["ordinal"]) is int
            and requirement["ordinal"] == len(bucket)
        )
        bucket.append(requirement)
    _need(len(expected) == len(actual), "generated requirement denominator")
    opaque_subjects = set()
    for i, (item, (kind, subject, rule, key, evidence)) in enumerate(
        zip(actual, expected, strict=True)
    ):
        _need((item["kind"], item["rule"]) == (kind, rule), "generated requirement")
        if type(subject) is tuple and subject[0] == "opaque":
            _need(
                item["subject"]["kind"] == subject[1]
                and encoded(item["subject"]) not in opaque_subjects,
                "generated opaque requirement subject",
            )
            opaque_subjects.add(encoded(item["subject"]))
        else:
            _need(
                item["subject"]
                == (subject if subject is not None else {"kind": kind, "position": i}),
                "generated requirement subject",
            )
        positions = (
            _requirement_premises(key, naming, scan_premises, physical)
            if type(key) in {str, tuple}
            else key
        )
        _need(item["premises"] == positions, "generated requirement premises")
        if evidence is None:
            _need(item["evidence"] == [], "generated requirement evidence")
        elif evidence == "checked":
            continue
        elif type(evidence) is dict:
            _need(item["evidence"] == [evidence], "generated operator evidence")
        elif type(evidence) is list:
            _need(item["evidence"] == evidence, "generated checked evidence")
        elif type(evidence) is tuple and evidence[0] == "result":
            _need(len(item["evidence"]) == 1, "result requirement evidence")
            entry = cast(dict[str, Any], item["evidence"][0])
            _need(
                entry.get("carrier") in {"ordinary", "rebound", "completed"}
                and all(entry.get(k) == v for k, v in evidence[1].items()),
                "result requirement evidence",
            )
        else:
            _, block, expression = evidence
            _need(len(item["evidence"]) == 1, "reference evidence")
            entry = cast(dict[str, Any], item["evidence"][0])
            _keys(entry, ("site", "context"))
            _reference(entry["site"])
            _need(
                entry["site"]["kind"] == "expression_site"
                and entry["context"] == block,
                "a reference declares the stage it was read in",
            )
    # Original demands: every family keeps its own re-derived rule and no premise.
    # A JOIN unit is its own generated scope, not an authored stage block, so the
    # retained scope demands cover exactly the emitted stage bodies.
    blocks = sorted(
        (
            body["block"]
            for body in bodies
            if not body.get("join")
            and not body.get("result")
            and not body.get("set")
            and not body.get("values")
        ),
        key=lambda block: block["position"],
    )
    families: dict[str, list[dict[str, Any]]] = {}
    for item in originals:
        families.setdefault(item["kind"], []).append(item)
        _need(item["premises"] == [], "original requirement premises")
    _need(
        [item["subject"] for item in families.get("scope", ())] == blocks,
        "scope demands do not match the emitted stage bodies",
    )
    _need(
        [item["subject"] for item in families.get("filter", ())]
        == sorted(walk["filters"], key=lambda filter_ref: filter_ref["position"]),
        "filter demands do not match the emitted predicate roots",
    )
    _need(
        [item["subject"] for item in families.get("source_realization", ())]
        == walk["source_definitions"],
        "source realization demand",
    )
    positions = sorted(
        item["subject"]["position"] for item in families.get("expression", ())
    )
    _need(
        all(
            item["subject"]["kind"] == "expression"
            for item in families.get("expression", ())
        )
        and positions == sorted(walk["expressions"])
        and positions == list(range(len(positions))),
        "expression demands do not match the decoded expressions",
    )
    stage_positions = sorted(
        item["subject"]["position"] for item in families.get("stage_value", ())
    )
    _need(
        all(
            item["subject"]["kind"] == "stage_port"
            for item in families.get("stage_value", ())
        )
        and stage_positions == list(range(len(stage_positions))),
        "stage value demands",
    )
    for key in walk["ports"]:
        port = json.loads(key)
        _need(port["position"] in stage_positions, "a read port has no stage demand")
    for item in originals:
        kind, subject = item["kind"], item["subject"]
        if kind == "filter":
            rule = "R06"
        elif kind == "expression":
            rule = walk["rules"].get(subject["position"], "R01")
        elif kind == "fixed_literal_transport":
            rule = "R04"
        elif kind == "scope":
            rule = "R03" if generated_scopes else "R01"
        elif kind == "source_realization":
            rule = "R01"
        elif kind == "aggregation":
            rule = AGGREGATE_DEMAND_RULES.get(subject["kind"], "R12")
        elif kind == "window":
            rule = WINDOW_DEMAND_RULES.get(subject["kind"], "R14")
        elif kind == "result":
            rule = RESULT_DEMAND_RULES.get(subject["kind"], "R02")
        elif kind == "set":
            rule = SET_DEMAND_RULE
        elif kind == "collection":
            rule = "R27"
        else:
            rule = "R02"
        _need(item["rule"] == rule, "original requirement rule")
    actual_result_ports = [
        item["subject"]["position"]
        for item in families.get("result", ())
        if item["subject"]["kind"] == "result_port"
    ]
    allocated_result_ports = walk["result_ports"]
    _need(
        sorted(actual_result_ports) == allocated_result_ports
        and allocated_result_ports == list(range(len(allocated_result_ports))),
        "complete result port allocation inventory",
    )
    # Phase71 S08: each Collect read keeps S06's three COLLECTION demands (its
    # read twice, then its nested export), in read order, and only those.
    collects = walk.get("collects", [])
    _need(
        [lateral["collect"] for lateral in collects]
        == [{"kind": "collect", "position": i} for i in range(len(collects))],
        "Collect reads are emitted in read order",
    )
    _need(
        [item["subject"] for item in families.get("collection", ())]
        == [
            subject
            for lateral in collects
            for subject in (
                lateral["collect"],
                lateral["collect"],
                lateral["export"],
            )
        ]
        + [export for _collect, export in walk.get("carried_collections", ())]
        + [entry["ref"] for entry in walk.get("unnests", ()) for _ in range(2)],
        "COLLECTION demands do not match the emitted Collect reads",
    )
    _need(
        3 * len(bodies)
        + 2 * sum(len(body["columns"]) for body in bodies)
        + sum(2 + len(body["columns"]) for body in bodies[:-1])
        + walk["scalar_nodes"]
        <= limits["nodes"]
    )


def _decode_fixed_public(document, limits):
    """Independent finite SELECT/WITH/leaf/sign grammar, including unused values."""
    family = document["target"]["family"]
    mysql_spread_cell = (
        family == "mysql"
        and not document["parameter_uses"]
        and not document["fixed_values"]
        and tuple(
            item["role"]
            for item in document["ranges"]
            if item["role"] not in {"namespace", "qualifier"}
        )
        == MYSQL_SPREAD_CELL_ROLES
    )
    contract = document["request"]["contract"]
    premises = _public_premises(contract)
    joined = any(
        r.get("denominator") == "generated" and r.get("kind") == "join"
        for r in document["requirements"]
    )
    scan_occurrences, statements = _scan_occurrences(
        document, contract, premises, family
    )
    setted = any(
        r.get("denominator") == "generated" and r.get("kind") == "set_operation"
        for r in document["requirements"]
    )
    valued = any(
        r.get("denominator") == "generated"
        and r.get("kind") in {"values_rows", "table_function"}
        for r in document["requirements"]
    )
    captured = any(
        r.get("denominator") == "generated" and r.get("kind") == "capture"
        for r in document["requirements"]
    )
    # An existence read may scan its own relation; the walk binds every scan.
    existence = any(
        r.get("denominator") == "generated" and r.get("kind") == "exists"
        for r in document["requirements"]
    )
    # Phase71 S08: a Collect read scans its collected let beside its parent.
    collected = any(
        r.get("denominator") == "generated" and r.get("kind") == "collect_lateral"
        for r in document["requirements"]
    )
    if not (joined or setted or captured or existence or collected):
        _need(
            len(scan_occurrences) == 1 or valued and len(scan_occurrences) <= 1,
            "one physical scan without a JOIN",
        )
    description, source_positions = (
        scan_occurrences[0] if scan_occurrences else (cast(Any, None), [])
    )
    scan_order = list(scan_occurrences)
    scan_definitions = _scan_definitions(document, scan_occurrences)
    # One source definition owns one contiguous block of plan source ports, and the
    # blocks follow definition position, not the order the scans are emitted in. A
    # second scan of the SAME definition therefore repeats that definition's own
    # ports rather than opening a new block.
    source_port_base, source_port_owner, running = {}, [], 0
    for position in sorted({item for item, _ in scan_definitions}):
        owner = next(item for key, item in scan_definitions if key == position)
        source_port_base[position] = running
        source_port_owner.append((running, owner))
        running += len(owner["fields"])

    def next_scan():
        """The next emitted physical scan occurrence, in exact emission order."""
        _need(bool(scan_order), "more physical scans than declared occurrences")
        return scan_order.pop(0)

    provenance = _range_provenance(document)
    literal_evidence, unary_evidence = {}, {}
    for requirement in document["requirements"]:
        if requirement.get("denominator") != "generated":
            continue
        kind = requirement.get("kind")
        if kind not in {"literal", "unary"}:
            continue
        subject = requirement["subject"]
        _reference(subject)
        _need(subject["kind"] == "expression")
        evidence = requirement["evidence"]
        _need(type(evidence) is list and len(evidence) == 1)
        evidence_item = cast(dict[str, Any], evidence[0])
        mapping = literal_evidence if kind == "literal" else unary_evidence
        if kind == "literal":
            _keys(evidence_item, ("tag", "value"))
            _fixed_payload(evidence_item["tag"], evidence_item["value"])
        else:
            _keys(evidence_item, ("operator",))
            _need(evidence_item["operator"] in {"+", "-"})
        # Shared expression nodes retain one equal proof at every rendered use.
        _need(
            subject["position"] not in mapping
            or encoded(mapping[subject["position"]]) == encoded(evidence_item),
            "repeated literal evidence",
        )
        mapping[subject["position"]] = evidence_item

    null_expression_positions = iter(
        sorted(
            position
            for position, evidence in literal_evidence.items()
            if evidence["value"] is None
        )
    )
    membership_constant_refs = {}
    generated_requirements = [
        item for item in document["requirements"] if item["denominator"] == "generated"
    ]
    for index, requirement in enumerate(generated_requirements[:-1]):
        next_requirement = generated_requirements[index + 1]
        if (
            requirement["kind"] == "membership"
            and requirement["subject"]["kind"] == "expression"
            and next_requirement["kind"] == "reference"
            and next_requirement["subject"]["kind"] == "expression"
        ):
            membership_constant_refs[requirement["subject"]["position"]] = (
                next_requirement["subject"]
            )

    def ref(kind, position):
        return {"kind": kind, "position": position}

    def cause(reference):
        group = provenance[reference["kind"], reference["position"]]
        causes = [_cause_location(o) for o in group]
        _need(all(c == causes[0] for c in causes))
        return causes[0]

    def within(child, parent):
        return child["path"] == parent["path"] and (
            parent["line"],
            parent["column"],
        ) <= (child["line"], child["column"]) <= (
            child["end_line"],
            child["end_column"],
        ) <= (parent["end_line"], parent["end_column"])

    bridge_sources = {
        key: tuple(
            source["location"]
            for origin in origins
            for source in origin["sources"]
            if source["kind"] == "normalized_expression"
        )
        for key, origins in provenance.items()
        if any(
            source["kind"] == "authored_cause"
            for origin in origins
            for source in origin["sources"]
        )
        and any(
            source["kind"] == "normalized_expression"
            for origin in origins
            for source in origin["sources"]
        )
    }
    having_context: list[Any] = [None]
    having_ranges = []
    having_uses = []
    canonical_preservations = []

    def shared_having_literal(site, block):
        matches = [
            key
            for key in bridge_sources
            if key[0] == "literal_site"
            and cause({"kind": key[0], "position": key[1]}) == cause(site)
        ]
        if not matches:
            return False
        canonical_preservations.append((site, block, matches))
        return True

    def source_within(reference, owner):
        if within(cause(reference), cause(owner)):
            return True
        context = having_context[0]
        locations = bridge_sources.get((reference["kind"], reference["position"]), ())
        return bool(
            context is not None
            and owner == context[0]
            and locations
            and all(within(location, cause(owner)) for location in locations)
        )

    def verify_having_bridges():
        ranges_by_subject = {}
        for item in document["ranges"]:
            subject = item["subject"]
            key = subject["kind"], subject["position"]
            ranges_by_subject.setdefault(key, []).append((item["start"], item["end"]))
            if subject["kind"] in {
                "expression",
                "literal_site",
                "literal_slot",
                "bind_use",
                "fixed_value",
            }:
                for low, high, predicate, _ in having_ranges:
                    if (
                        low <= item["start"]
                        and item["end"] <= high
                        and not within(cause(subject), cause(predicate))
                    ):
                        _need(key in bridge_sources, "missing HAVING source bridge")
        groups = {}
        bridge_owners = {}
        for (kind, position), locations in bridge_sources.items():
            subject = {"kind": kind, "position": position}
            spans = sorted(
                set(ranges_by_subject.get((kind, position), ())),
                key=lambda value: (value[0], -value[1]),
            )
            outer = []
            for start, end in spans:
                if not outer or not (outer[-1][0] <= start and end <= outer[-1][1]):
                    outer.append((start, end))
            scopes = []
            for start, end in outer:
                matches = [
                    (predicate, owner)
                    for low, high, predicate, owner in having_ranges
                    if low <= start and end <= high
                ]
                _need(len(matches) == 1, "HAVING expansion scope")
                scopes.append(matches[0])
            _need(
                bool(scopes) and all(scope == scopes[0] for scope in scopes),
                "HAVING expansion owner",
            )
            predicate, owner = scopes[0]
            bridge_owners[kind, position] = owner
            _need(
                all(within(location, cause(predicate)) for location in locations),
                "HAVING alias use source",
            )
            selected = {
                (column["export"]["kind"], column["export"]["position"])
                for body in row_bodies
                if body["projection"] and body["definition"] == owner
                for column in body["columns"]
                if column["export"]["kind"] == "export"
                and within(cause(subject), cause(column["export"]))
            }
            _need(len(selected) == 1, "HAVING expanded selected source")
            # ORDER/DISTINCT stages carry the same canonical export again.
            (selected_export,) = selected
            key = encoded((predicate, owner, selected_export, locations))
            groups.setdefault(key, []).append((subject, outer, locations))
        for entries in groups.values():
            expressions = [
                entry for entry in entries if entry[0]["kind"] == "expression"
            ]
            roots = [
                entry
                for entry in expressions
                if not any(
                    cause(entry[0]) != cause(other[0])
                    and within(cause(entry[0]), cause(other[0]))
                    for other in expressions
                )
            ]
            _need(len(roots) == 1, "HAVING composition source root")
            root_subject, root_ranges, locations = roots[0]
            coordinates = [
                (
                    location["path"],
                    location["line"],
                    location["column"],
                    location["end_line"],
                    location["end_column"],
                )
                for location in locations
            ]
            _need(
                coordinates == sorted(coordinates)
                and len(set(coordinates)) == len(coordinates),
                "HAVING alias source order",
            )
            _need(
                len(root_ranges) == len(locations), "HAVING alias occurrence inventory"
            )
            uses = [use for use in having_uses if use[0] == root_subject]
            _need(len(uses) == len(locations), "HAVING parent operand inventory")
            parents = {}
            for _, context, parent, position, siblings in uses:
                key = encoded((context, parent, siblings))
                parents.setdefault(key, (parent, siblings, []))[2].append(position)
            for parent, siblings, positions in parents.values():
                _need(
                    len(set(positions)) == len(positions),
                    "HAVING parent operand identity",
                )
                eligible = [
                    location
                    for location in locations
                    if within(location, cause(parent))
                    and all(
                        (location["end_line"], location["end_column"])
                        <= (sibling["line"], sibling["column"])
                        or (sibling["end_line"], sibling["end_column"])
                        <= (location["line"], location["column"])
                        for sibling in siblings
                    )
                ]
                _need(len(eligible) == len(positions), "HAVING alias parent operand")
            # Native round/lpad may render an operand several times inside one
            # already-proved composition occurrence.
            for _, ranges, _ in entries:
                _need(
                    all(
                        sum(low <= start and end <= high for low, high in root_ranges)
                        == 1
                        for start, end in ranges
                    ),
                    "HAVING expansion root containment",
                )

        for site, block, matches in canonical_preservations:
            bodies = [
                body
                for body in row_bodies
                if body["block"] == block and body["projection"]
            ]
            _need(
                len(bodies) == 1
                and all(
                    bridge_owners.get(key) == bodies[0]["definition"] for key in matches
                ),
                "shared literal owner",
            )
            original = seen_sites[site["position"]]
            _need(
                all(
                    encoded(literal_evidence[seen_sites[key[1]]["position"]])
                    == encoded(literal_evidence[original["position"]])
                    for key in matches
                ),
                "shared literal value",
            )

    sql = document["sql"].encode()
    lexical, enclosures = [], []
    offset = 0
    for interval in document["ranges"]:
        _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
        _need(type(interval["start"]) is int and type(interval["end"]) is int)
        _reference(interval["subject"])
        _need(0 <= interval["start"] < interval["end"] <= len(sql))
        if interval["kind"] == "expression_range":
            enclosures.append(interval)
            continue
        _need(not enclosures and interval["start"] == offset)
        _need(interval["kind"] in {"identifier", "syntax", "literal", "parameter"})
        text = sql[offset : interval["end"]].decode()
        if interval["kind"] == "identifier":
            text = _identifier_token(text, family, interval["role"])
        lexical.append((interval, text))
        offset = interval["end"]
    _need(offset == len(sql))
    fixed = document["fixed_values"]
    for i, value in enumerate(fixed):
        _keys(value, ("slot", "reference", "site", "tag", "value"))
        _need(type(value["slot"]) is int and value["slot"] == i)
        _reference(value["reference"])
        _reference(value["site"])
        _need(
            value["reference"] == ref("literal_slot", i)
            and value["site"]["kind"] == "literal_site"
        )
        _fixed_payload(value["tag"], value["value"])
    _need(
        len({(v["site"]["kind"], v["site"]["position"]) for v in fixed}) == len(fixed)
    )
    uses = document["parameter_uses"]
    _need(len(uses) <= limits["parameters"])
    bound = document["request"]["literal_policy"] == "bind_safe_literals"
    _need(bound or not fixed and not uses)
    if fixed:
        protocols = [
            premises[i]["value"]
            for i in statements
            if premises[i]["key"] == "parameter_protocol"
        ]
        _need(
            bool(protocols)
            and all(
                v == ("postgres_extended" if family == "postgres" else "mysql_prepared")
                for v in protocols
            )
        )
    cursor = expression_count = projection_count = input_count = 0
    scalar_ids, seen_sites, used_slots, expected_ranges = set(), {}, set(), []
    bodies, ctes, field_uses = [], {}, []
    seen_expressions: set[int] = set()

    def take(kind, role, text=None, subject=None):
        nonlocal cursor
        _need(cursor < len(lexical))
        interval, actual = lexical[cursor]
        cursor += 1
        _need(interval["kind"] == kind and interval["role"] == role)
        _need(text is None or text == actual)
        _need(subject is None or subject == interval["subject"])
        return interval, actual

    def peek():
        return lexical[cursor][0]["role"] if cursor < len(lexical) else None

    def following(*roles):
        """Whether the next tokens have exactly these roles."""
        return all(
            cursor + i < len(lexical) and lexical[cursor + i][0]["role"] == role
            for i, role in enumerate(roles)
        )

    used = 0
    scalar_nodes = 0

    def expression_ref(positional, allow_seen=False):
        """The expression a token declares.

        The projection grammar numbers expressions in exactly rendering order, so
        it predicts the next position and the token must confirm it. A stage body
        renders its values in stage order, which is not that counter, so there the
        token declares its own expression and the walk records which ones it saw.
        """
        _need(cursor < len(lexical))
        subject = lexical[cursor][0]["subject"]
        if positional:
            _need(subject == ref("expression", expression_count))
            return subject
        _need(subject["kind"] == "expression" and _ordinal(subject["position"]))
        _need(
            allow_seen
            or having_context[0] is not None
            or subject["position"] not in seen_expressions
        )
        return subject

    def scalar(projection, positional=True, repeated=False):
        nonlocal expression_count, used, scalar_nodes
        signs, requirements = [], []
        start_ref = None
        while peek() == "unary_open":
            original = expression_ref(positional, repeated)
            interval, text = take("syntax", "unary_open", subject=original)
            _need(text in {"(+", "(-"})
            _need(unary_evidence[original["position"]]["operator"] == text[1])
            signs.append((original, text[1], interval["start"]))
            scalar_ids.add(original["position"])
            seen_expressions.add(original["position"])
            start_ref = start_ref or original
            expression_count += positional
        original = expression_ref(positional, repeated)
        opened, _ = take("syntax", "anchor_open", "CAST(", original)
        scalar_ids.add(original["position"])
        seen_expressions.add(original["position"])
        start_ref = start_ref or original
        expression_count += positional
        _need(cursor < len(lexical))
        interval, token = lexical[cursor]
        cursor_kind, tag = interval["kind"], interval["role"]
        _need(tag in {"Bool", "Int", "Float", "Text"})
        _need(interval["subject"]["kind"] == "literal_site")
        site = interval["subject"]
        _need(
            within(cause(original), cause(projection))
            and cause(site) == cause(original)
        )
        if site["position"] in seen_sites:
            _need(
                (repeated or having_context[0] is not None)
                and seen_sites[site["position"]] == original
            )
        else:
            seen_sites[site["position"]] = original
        take(cursor_kind, tag, token, site)
        physical = _fixed_physical(family, tag)
        if cursor_kind == "parameter":
            _need(bound and used < len(uses))
            use = uses[used]
            _keys(use, ("use", "slot", "server_index", "physical_type", "range"))
            _keys(use["range"], ("start", "end"))
            _need(type(use["use"]) is int and use["use"] == used)
            _need(_ordinal(use["slot"]) and use["slot"] < len(fixed))
            _need(type(use["server_index"]) is int and use["server_index"] > 0)
            _need(use["physical_type"] == physical)
            _need(use["range"] == {"start": interval["start"], "end": interval["end"]})
            _need(all(type(use["range"][k]) is int for k in ("start", "end")))
            value = fixed[use["slot"]]
            _need(value["site"] == site and value["tag"] == tag)
            _need(
                token
                == ("$" + str(use["server_index"]) if family == "postgres" else "?")
            )
            payload = _fixed_payload(tag, value["value"])
            slot = use["slot"]
            used_slots.add(slot)
            used += 1
        else:
            # Under BIND_SAFE a literal may only survive in a position the
            # extraction rule never admits as a slot; satisfying is that
            # position here, and every ordinary one still has to be bound.
            _need(
                cursor_kind == "literal"
                and (
                    not bound
                    or specialized[0]
                    or call_argument_depth[0]
                    or shared_having_literal(site, projection)
                ),
            )
            slot = None
            evidence = literal_evidence[original["position"]]
            _need(evidence["tag"] == tag)
            if evidence["value"] is None:
                _need(token == "NULL" and not signs and not opened)
                requirements.append(("literal", original, tag))
                scalar_nodes += not repeated
                return {
                    "tag": tag,
                    "value": None,
                    "expression": start_ref,
                    "leaf": original,
                    "site": site,
                    "slot": slot,
                    "requirements": requirements,
                    "duplicate": repeated,
                }
            if tag == "Bool":
                _need(token in {"TRUE", "FALSE"})
                payload = token == "TRUE"
            elif tag == "Int":
                payload = _fixed_payload(tag, token)
            elif tag == "Float":
                if family == "postgres":
                    _need(token.startswith("'") and token.endswith("'"))
                    spelling = token[1:-1]
                else:
                    _need("e" in token)
                    spelling = token[:-2] if token.endswith("e0") else token
                payload = float(spelling)
                _need(math.isfinite(payload) and repr(payload) == spelling)
            elif family == "postgres":
                _need(re.fullmatch(r"E'(?:\\[0-3][0-7]{2})*'", token) is not None)
                payload = bytes(
                    int(token[i + 1 : i + 4], 8) for i in range(2, len(token) - 1, 4)
                ).decode()
            else:
                _need(re.fullmatch(r"X'(?:[0-9a-f]{2})*'", token) is not None)
                payload = bytes.fromhex(token[2:-1]).decode()
            expected = _fixed_payload(tag, evidence["value"])
            _need(type(payload) is type(expected))
            if isinstance(payload, float):
                _need(type(expected) is float)
                assert isinstance(expected, float)
                _need(payload.hex() == expected.hex())
            else:
                _need(payload == expected)
        if tag == "Text":
            _need(type(payload) is str)
            assert isinstance(payload, str)
            _need(family != "postgres" or "\0" not in payload)
        close = (
            " AS "
            + {
                "pg_bool": "pg_catalog.bool",
                "pg_int8": "pg_catalog.int8",
                "pg_float8": "pg_catalog.float8",
                "pg_text": "pg_catalog.text",
                "my_signed_bool": "SIGNED",
                "my_signed_int": "SIGNED",
                "my_double": "DOUBLE",
                "my_utf8mb4_text": "CHAR CHARACTER SET utf8mb4",
            }[physical]
            + ")"
        )
        if tag == "Text":
            close += (
                ' COLLATE "C"' if family == "postgres" else " COLLATE utf8mb4_0900_bin"
            )
        closed, _ = take("syntax", "anchor_close", close, original)
        expected_ranges.append(("anchor", original, opened["start"], closed["end"]))
        for sign_ref, sign, start in reversed(signs):
            _need(tag in {"Int", "Float"})
            _need(type(payload) in {int, float})
            assert isinstance(payload, (int, float))
            _need(within(cause(original), cause(sign_ref)))
            payload = -payload if sign == "-" else +payload
            _need(
                -(1 << 63) <= payload < 1 << 63
                if tag == "Int"
                else math.isfinite(payload)
            )
            closed, _ = take("syntax", "unary_close", ")", sign_ref)
            expected_ranges.append(("unary", sign_ref, start, closed["end"]))
        requirements.extend(("unary", sign_ref, tag) for sign_ref, _, _ in signs)
        requirements.extend(
            (("type_anchor", original, tag), (cursor_kind, original, tag))
        )
        scalar_nodes += (3 + len(signs)) * (not repeated)
        return {
            "tag": tag,
            "value": payload,
            "expression": start_ref,
            "leaf": original,
            "site": site,
            "slot": slot,
            "requirements": requirements,
            "duplicate": repeated,
        }

    def source_type(field):
        # The same field law the field-only route applies, before deriving output.
        return _field_compatibility(field["representation"], family)

    def value_representation(value):
        tag, payload = value["tag"], value["value"]
        if tag == "Bool":
            domain = {"kind": "bool01"}
        elif tag == "Int":
            domain = {"kind": "int_range", "min": str(payload), "max": str(payload)}
        elif tag == "Float":
            domain = {"kind": "finite_float", "format": "binary64"}
        else:
            domain = {
                "kind": "text",
                "max_characters": len(payload),
                "encoding": "UTF8" if family == "postgres" else "utf8mb4",
                "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
                "padding": "NO PAD",
            }
        return {
            "storage": {"kind": _fixed_physical(family, tag)},
            "nullable": False,
            "domain": domain,
        }

    def select(owner, final=False):
        nonlocal expression_count, projection_count, input_count
        take("syntax", "select", "SELECT ", owner)
        selected = []
        while True:
            i = len(selected)
            projection = ref("projection", projection_count + i)
            export = ref("export", projection_count + i)
            if i:
                take("syntax", "separator", ", ", projection)
            expression = ref("expression", expression_count)
            if peek() == "column_scope":
                scope, alias = take("identifier", "column_scope")
                take("syntax", "qualifier", ".", projection)
                token, name = take("identifier", "column")
                value = {"reference": (alias, scope["subject"], name, token["subject"])}
                expression_count += 1
            else:
                value = {"literal": scalar(projection)}
            take("syntax", "alias", " AS ", projection)
            _, label = take("identifier", "label", None if final else f"c{i}", export)
            _need(
                cause(export) == cause(projection)
                and within(cause(projection), cause(owner))
            )
            selected.append((value, label, projection, export, expression))
            if peek() != "separator":
                break
        token, _ = take("syntax", "from", " FROM ")
        producer_ref = token["subject"]
        producer_name = None
        if peek() == "namespace":
            _need(not bodies and producer_ref == ref("definition", 0))
            take(
                "identifier",
                "namespace",
                description["relation"]["namespace"],
                producer_ref,
            )
            take("syntax", "qualifier", ".", producer_ref)
            take(
                "identifier", "relation", description["relation"]["name"], producer_ref
            )
            _need(cause(producer_ref)["path"] == description["selector"]["module"])
            incoming = [
                {
                    "name": f["column"],
                    "terminal": ref("source_port", f["ordinal"]),
                    "canonical": ref("source_port", f["ordinal"]),
                    "field": f,
                    "literal": None,
                }
                for f in description["fields"]
            ]
            for f in description["fields"]:
                source_type(f)
        else:
            _, producer_name = take("identifier", "cte_reference", subject=producer_ref)
            _need(
                producer_name in ctes
                and ctes[producer_name]["definition"] == producer_ref
            )
            incoming = ctes[producer_name]["columns"]
        use = ref("input_use", len(bodies))
        take("syntax", "alias", " AS ", use)
        _, alias = take("identifier", "relation_scope", f"s{len(bodies)}", use)
        _need(within(cause(use), cause(owner)))
        route = provenance[use["kind"], use["position"]][0]["sources"]
        _need(
            any(
                s["kind"] == "referenced_declaration"
                and s["location"] == cause(producer_ref)
                for s in route
            )
        )
        hops = [s for s in route if s["kind"] in {"import_item", "export_item"}]
        module = cause(owner)["path"]
        _need(len(hops) % 2 == 0)
        for imported, exported in zip(hops[::2], hops[1::2], strict=True):
            _need(
                imported["kind"] == "import_item"
                and imported["path"] == module
                and exported["kind"] == "export_item"
            )
            module = exported["path"]
        _need(module == cause(producer_ref)["path"])
        names = {c["name"]: (i, c) for i, c in enumerate(incoming)}
        _need(len(names) == len(incoming))
        output = []
        for i, (item, label, projection, export, expression) in enumerate(selected):
            terminal = ref("result_port", projection_count + i)
            link, input_ref = None, None
            if "reference" in item:
                qualifier, input_ref, name, observed_terminal = item["reference"]
                _need(qualifier == alias and name in names)
                index, source = names[name]
                _need(input_ref == ref("input_port", input_count + index))
                _need(observed_terminal == source["terminal"])
                _need(
                    cause(input_ref) == cause(use)
                    and cause(observed_terminal) == cause(producer_ref)
                )
                field, value = source["field"], source["literal"]
                link = {"export": source["canonical"], "terminal": source["terminal"]}
                if field is not None:
                    field_uses.append(
                        (field["ordinal"], projection["position"], len(bodies))
                    )
            else:
                field, value = None, item["literal"]
                value["origin"] = {
                    k: value[k] for k in ("expression", "leaf", "site", "slot")
                }
                value["origin"].update(export=export, terminal=terminal)
            entry = {
                "name": label,
                "terminal": terminal,
                "canonical": export,
                "field": field,
                "literal": value,
                "new_value": item.get("literal"),
                "projection": projection,
            }
            output.append(entry)
            if final:
                _need(i < len(document["columns"]))
                if field is None:
                    correspondence = {
                        "literal_origin": value["origin"],
                        "expression": expression,
                        "input_port": input_ref,
                        "producer": link,
                        "export": export,
                        "projection": projection,
                        "sql_symbol": i + 1,
                    }
                    logical = {
                        "kind": "builtin",
                        "name": value["tag"],
                        "parameters": None,
                    }
                    representation = value_representation(value)
                else:
                    correspondence = {
                        "source": description["selector"],
                        "field": field["ordinal"],
                        "source_port": ref("source_port", field["ordinal"]),
                        "input_port": input_ref,
                        "export": export,
                        "projection": projection,
                        "sql_symbol": i + 1,
                    }
                    logical, representation = (
                        source_type(field),
                        field["representation"],
                    )
                expected = {
                    "ordinal": i,
                    "label": label,
                    "logical_type": logical,
                    "nullable": representation["nullable"],
                    "representation": representation,
                    "correspondence": correspondence,
                }
                # JSON type equality matters: bool is never an ordinal.
                _need(
                    encoded(document["columns"][i]) == encoded(expected),
                    "literal/field output correspondence",
                )
        _need(not final or len(output) == len(document["columns"]))
        _need(len(output) <= limits["columns"])
        bodies.append(
            {
                "producer": producer_name,
                "use": use,
                "incoming": incoming,
                "columns": output,
            }
        )
        projection_count += len(output)
        input_count += len(incoming)
        return output

    # ---- Slice6 stage grammar ----------------------------------------------
    # One generated SELECT per actual original stage block. The shared contract,
    # field, premise, constant-leaf and parameter machinery above is reused; only
    # the carried ports, admitted operator nodes, stage scopes and the filter root
    # are new, and this walk derives their realization itself. Structure is parsed
    # first (tokens, spans, enclosures), then resolved against the body's own
    # immediate incoming columns once the FROM has named the producer.
    INT_BITS = {
        "pg_int2": 16,
        "pg_int4": 32,
        "pg_int8": 64,
        "my_smallint": 16,
        "my_int": 32,
        "my_bigint": 64,
        "my_signed_int": 64,
    }
    ARITHMETIC_TOKENS = {" + ", " - ", " * ", " / ", " % "}
    LOGICAL_TOKENS = {" AND ", " OR "}
    COMPARISON_TOKENS = {" = ", " <> ", " < ", " <= ", " > ", " >= "}
    COMPARABLE = ("Bool", "Int", "Text", "Decimal", "Float", "Timestamp", "Date")
    row_bodies: list[dict[str, Any]] = []
    row_generated: list[Any] = []
    row_port_reads: dict[str, Any] = {}
    row_stage_ports: set[str] = set()
    row_rules: dict[int, str] = {}
    row_filters: list[Any] = []
    row_block: list[Any] = [None]
    # Phase70 S10: the reading body row each inline let's captured fields read,
    # and the definitions of the inline lets a reading body renders.
    capture_frames: list[dict[str, Any]] = []
    inline_owners: list[Any] = []
    # Phase71 S08: each parsed Collect lateral, in emission order, and the
    # nested carrier and ordinal columns the CTE header being parsed declared.
    row_collects: list[dict[str, Any]] = []
    carried_collection_exports: list[tuple[dict[str, Any], dict[str, Any]]] = []
    collect_bindings: dict[str, dict[str, Any]] = {}
    terminal_producers: dict[str, dict[str, Any]] = {}
    producer_terminals: dict[str, dict[str, Any]] = {}

    row_unnests: list[dict[str, Any]] = []
    ROW_OPERATORS = {
        " + ": "+",
        " - ": "-",
        " * ": "*",
        " / ": "/",
        " DIV ": "/",
        " % ": "%",
        " AND ": "and",
        " OR ": "or",
        " = ": "==",
        " <> ": "!=",
        " < ": "<",
        " <= ": "<=",
        " > ": ">",
        " >= ": ">=",
        " LIKE ": "like",
        " NOT LIKE ": "not like",
    }

    def row_node_premises(tag, operand_tags, kind):
        keys = {"operator_environment"}
        if tag == "Text" or "Text" in operand_tags:
            keys.add("client_encoding")
        if kind == "parameter":
            keys.add("parameter_protocol")
        return [i for i in statements if premises[i]["key"] in keys]

    def row_bool(nullable):
        return {
            "tag": "Bool",
            "storage": {
                "kind": "pg_bool" if family == "postgres" else "my_signed_bool"
            },
            "nullable": nullable,
            "domain": {"kind": "bool01"},
        }

    def row_interval(value):
        _need(
            value["tag"] == "Int"
            and type(value.get("proven_int_range")) is tuple
            and len(value["proven_int_range"]) == 2
            and all(type(bound) is int for bound in value["proven_int_range"])
            and value["proven_int_range"][0] <= value["proven_int_range"][1],
            "integer range proof",
        )
        return value["proven_int_range"]

    def row_int(operands, low, high, nullable, widened=False, operation=False):
        if family == "mysql":
            _need(not widened, "MySQL computes no bigint widening")
            storage = {"kind": "my_signed_int"}
        else:
            widths = [INT_BITS.get(o["storage"]["kind"]) for o in operands]
            _need(all(w is not None for w in widths), "integer operand storage")
            narrow = max(w for w in widths if w is not None)
            if widened:
                # A narrow operation whose exact range leaves its own type is
                # computed in bigint; a redundant widening is not admitted.
                _need(
                    narrow < 64
                    and not (
                        -(1 << (narrow - 1)) <= low <= high <= (1 << (narrow - 1)) - 1
                    ),
                    "int8 widening",
                )
                narrow = 64
            storage = {"kind": {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"}[narrow]}
        bits = INT_BITS[storage["kind"]]
        checked = False
        if (
            operation
            and (
                storage == {"kind": "pg_int8"}
                # S01: a MySQL cell over nullable BIGINT fields; the readers
                # under test derive the rest of the cell.
                or storage == {"kind": "my_signed_int"}
                and all(
                    o["storage"] == {"kind": "my_bigint"} and o["nullable"] is True
                    for o in operands
                )
            )
            and not (I64_MIN <= low <= high <= I64_MAX)
            and low <= I64_MAX
            and high >= I64_MIN
        ):
            # Q2: PostgreSQL's checked bigint operation refuses a value outside
            # signed 64 bits, so the result keeps the part of its exact range
            # inside them and publishes the target-checked evidence.
            low, high, checked = max(low, I64_MIN), min(high, I64_MAX), True
        _need(
            -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1,
            "integer result outside its physical range",
        )
        result = {
            "tag": "Int",
            "storage": storage,
            "nullable": nullable,
            "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
            "proven_int_range": (low, high),
        }
        if checked:
            result["checked"] = True
        return result

    def widened_operand(block, port_kind, original):
        """One first operand, CAST to pg_catalog.int8 when its narrow
        PostgreSQL operation is computed in bigint."""
        if peek() != "int8_widen_open":
            return row_parse(block, port_kind), False
        opened, _ = take("syntax", "int8_widen_open", "CAST(", original)
        operand = row_parse(block, port_kind)
        closed, _ = take("syntax", "int8_widen_close", " AS pg_catalog.int8)", original)
        expected_ranges.append(("int8_widen", original, opened["start"], closed["end"]))
        return operand, True

    def null_cast_operand(block, port_kind, original):
        """One typed NULL operand of Int arithmetic, CAST to the target's
        Int carrier."""
        if peek() != "null_cast_open":
            return None, False
        opened, _ = take("syntax", "null_cast_open", "CAST(", original)
        operand = row_parse(block, port_kind)
        _need(
            operand["kind"] == "constant" and operand["value"]["value"] is None,
            "typed NULL cast operand",
        )
        close = " AS pg_catalog.int8)" if family == "postgres" else " AS SIGNED)"
        closed, _ = take("syntax", "null_cast_close", close, original)
        expected_ranges.append(("null_cast", original, opened["start"], closed["end"]))
        return operand, True

    def constant_ahead():
        index = cursor
        while index < len(lexical) and lexical[index][0]["role"] == "unary_open":
            index += 1
        return index < len(lexical) and lexical[index][0]["role"] == "anchor_open"

    specialized = [False]
    call_argument_depth = [0]
    any_frames: list[dict[str, Any]] = []

    def inline_read(producer):
        """A let with capture lines read inline: its parsed final body and its
        obligations, which follow the read's own (Phase70 S10, S14)."""
        projection_frame = None
        if not capture_frames:
            reads, projection_frame = projection_inline_frame()
            _need(bool(reads), "a correlated read outside its row")
            assert projection_frame is not None
            inline_owners.append(next_row_definition())
            capture_frames.append(projection_frame)
        take("syntax", "inline_open", "(", producer)
        mark, outer_block = len(row_generated), row_block[0]
        body = (
            result_select(producer, False, None, inline=True)
            if producer["kind"] == "result_boundary"
            else row_select(producer, False, None, inline=True)
        )
        row_block[0] = outer_block
        inline = row_generated[mark:]
        del row_generated[mark:]
        take("syntax", "inline_close", ")", producer)
        if projection_frame is not None:
            _need(capture_frames.pop() is projection_frame)
        return body, inline

    def ordinal_parse():
        """Phase71 S08: ``ROW_NUMBER() OVER (ORDER BY <keys>) AS <name>``, one
        collected terminal's private sequence; its keys are checked against the
        ORDER they restate by the caller."""
        token, _ = take("syntax", "ordinal_window", "ROW_NUMBER() OVER (ORDER BY ")
        order = token["subject"]
        _need(order["kind"] == "relation_order", "ordinal ORDER subject kind")
        keys = []
        while True:
            separator = None
            if keys:
                separator, _ = take("syntax", "order_separator", ", ")
            scope_token, scope = take("identifier", "order_scope")
            qualifier, _ = take("syntax", "order_qualifier", ".")
            item = qualifier["subject"]
            _need(
                item["kind"] == "order_item"
                and (separator is None or separator["subject"] == item),
                "ordinal key subject",
            )
            column_token, name = take("identifier", "order_column")
            direction_token, direction = take("syntax", "order_direction")
            _need(
                direction in {" ASC", " DESC"} and direction_token["subject"] == item,
                "ordinal key direction",
            )
            keys.append(
                {
                    "item": item,
                    "port": scope_token["subject"],
                    "scope": scope,
                    "name": name,
                    "terminal": column_token["subject"],
                    "direction": direction.strip().lower(),
                }
            )
            if peek() != "order_separator":
                break
        take("syntax", "ordinal_window", ")", order)
        take("syntax", "alias", " AS ", order)
        _, name = take("identifier", "ordinal_column", None, order)
        _need(
            all(key["scope"] == keys[0]["scope"] for key in keys),
            "one ordinal reads one scope",
        )
        return {"order": order, "keys": keys, "scope": keys[0]["scope"], "name": name}

    def ordinal_restates(ordinal, terminal, scope, columns):
        """The ordinal keys are exactly the terminal's ORDER items, in order,
        read through ``scope`` by the column names ``columns`` gives them."""
        items = terminal["order_items"]
        return (
            terminal["order_ref"] is not None
            and ordinal["order"] == terminal["order_ref"]
            and ordinal["scope"] == scope
            and len(ordinal["keys"]) == len(items)
            and all(
                (key["item"], key["port"], key["terminal"], key["direction"])
                == (
                    entry["item"],
                    entry["port"],
                    entry["read"]["terminal"],
                    entry["direction"],
                )
                and key["name"] == columns(entry)
                for key, entry in zip(ordinal["keys"], items, strict=True)
            )
        )

    def collect_lateral(alias, incoming):
        """Phase71 S08: one Collect read, ``LEFT JOIN LATERAL (SELECT COUNT(*)
        AS "n", ARRAY_AGG(e.c<j> ORDER BY e.c<V>) AS "a<j>", ... FROM <terminal>
        AS e) AS g ON TRUE``, after the FROM of its parent body. The terminal is
        the collected let's ordered result body: a CTE, or a captured let's
        inline chain reading the parent row; a DISTINCT terminal is wrapped by
        its ordinal. Returns the lateral and its requirements, in order."""
        _need(family == "postgres", "a Collect read is PostgreSQL only")
        collect = lexical[cursor][0]["subject"]
        _need(collect["kind"] == "collect", "Collect lateral subject kind")
        take("syntax", "collect_lateral_open", " LEFT JOIN LATERAL (", collect)
        take("syntax", "select", "SELECT ", collect)
        take("syntax", "collect_count", "COUNT(*)", collect)
        take("syntax", "alias", " AS ", collect)
        take("identifier", "label", "n", collect)
        arrays = []
        while peek() == "separator":
            separator, _ = take("syntax", "separator", ", ")
            child = separator["subject"]
            _need(child["kind"] == "export", "Collect child subject kind")
            take("syntax", "collect_array", "ARRAY_AGG(", child)
            use_token, scope = take("identifier", "collect_reference")
            use = use_token["subject"]
            _need(
                use["kind"] == "expression_block_use"
                and scope == f"e{use['position']}",
                "Collect read scope",
            )
            take("syntax", "qualifier", ".", child)
            _, read = take("identifier", "collect_array", None, child)
            take("syntax", "collect_array_order", " ORDER BY ", child)
            take("identifier", "collect_reference", scope, use)
            take("syntax", "qualifier", ".", child)
            _, sequence = take("identifier", "ordinal_column", None, child)
            take("syntax", "collect_array", ")", child)
            take("syntax", "alias", " AS ", child)
            take("identifier", "label", f"a{len(arrays)}", child)
            arrays.append(
                {"child": child, "read": read, "sequence": sequence, "use": use}
            )
        _need(bool(arrays), "a Collect read has at least one child field")
        use = arrays[0]["use"]
        n = use["position"]
        _need(
            all(a["use"] == use for a in arrays)
            and len({encoded(a["child"]) for a in arrays}) == len(arrays),
            "one Collect read reads one terminal",
        )
        take("syntax", "from", " FROM ", collect)
        mark = len(row_generated)
        wrapper = None
        if peek() == "distinct_wrapper_open":
            take("syntax", "distinct_wrapper_open", "(", collect)
            take("syntax", "select", "SELECT ", collect)
            wrapped = []
            for position, entry in enumerate(arrays):
                if position:
                    take("syntax", "separator", ", ", entry["child"])
                take("identifier", "result_carry_scope", f"d{n}", entry["child"])
                take("syntax", "result_carry_qualifier", ".", entry["child"])
                _, source = take(
                    "identifier", "result_carry_column", None, entry["child"]
                )
                take("syntax", "alias", " AS ", entry["child"])
                take("identifier", "label", entry["read"], entry["child"])
                wrapped.append(source)
            separator, _ = take("syntax", "separator", ", ")
            wrapper = {"sources": wrapped, "ordinal": ordinal_parse()}
            _need(
                separator["subject"] == wrapper["ordinal"]["order"],
                "wrapper ordinal separator",
            )
            take("syntax", "from", " FROM ", collect)
        producer = lexical[cursor][0]["subject"]
        _need(producer["kind"] == "result_boundary", "a Collect read reads a result")
        inline = peek() == "inline_open"
        if inline:
            # A captured let is the derived relation of its own read; its
            # captured fields read this parent row.
            frame = {"alias": alias, "incoming": incoming}
            capture_frames.append(frame)
            take("syntax", "inline_open", "(", producer)
            terminal = result_select(producer, False, None, inline=True)
            take("syntax", "inline_close", ")", producer)
            _need(capture_frames.pop() is frame)
        else:
            _, name = take("identifier", "collect_reference", None, producer)
            terminal = row_ctes.get(name)
            _need(terminal is not None, "a Collect read names a complete terminal")
        assert terminal is not None
        inline_generated = row_generated[mark:]
        del row_generated[mark:]
        if wrapper is not None:
            take("syntax", "alias", " AS ", collect)
            take("identifier", "result_scope", f"d{n}", collect)
            take("syntax", "distinct_wrapper_close", ")", collect)
        take("syntax", "alias", " AS ", use)
        take("identifier", "collect_reference", f"e{n}", use)
        take("syntax", "collect_lateral_close", ") AS ", collect)
        take("identifier", "collect_scope", f"g{n}", collect)
        take("syntax", "collect_on_true", " ON TRUE", collect)
        visible = terminal["outgoing"]
        names = [column["name"] for column in visible]
        _need(
            terminal["block"] == producer
            and terminal.get("result") is True
            and terminal["projection"]
            and not terminal["final"]
            and terminal["order_ref"] is not None
            and len(arrays) == len(visible)
            and [a["child"] for a in arrays]
            == [c["export"] for c in terminal["columns"]]
            and all(column.get("group") is None for column in visible),
            "a Collect read reads every column of one ordered closed terminal",
        )
        width = len(arrays)
        if wrapper is None:
            _need(
                terminal["distinct"] is None
                and terminal["ordinal"] is not None
                and [a["read"] for a in arrays] == names
                and all(a["sequence"] == f"c{width}" for a in arrays),
                "a Collect read orders by its terminal's own ordinal",
            )
        else:

            def visible_name(entry):
                matches = [
                    i
                    for i, read in enumerate(terminal["visible_inputs"])
                    if read is entry["read"]
                ]
                _need(len(matches) == 1, "a DISTINCT ORDER key is one visible column")
                return names[matches[0]]

            _need(
                terminal["distinct"] is not None
                and terminal["ordinal"] is None
                and wrapper["sources"] == names
                and [a["read"] for a in arrays] == [f"c{j}" for j in range(width)]
                and wrapper["ordinal"]["name"] == f"c{width}"
                and all(a["sequence"] == f"c{width}" for a in arrays)
                and ordinal_restates(
                    wrapper["ordinal"], terminal, f"d{n}", visible_name
                ),
                "a DISTINCT terminal is wrapped by exactly its ordinal",
            )
        claims = [
            entry["evidence"]
            for entry in document["requirements"]
            if entry.get("denominator") == "generated"
            and entry.get("kind") == "collect_lateral"
            and entry.get("subject") == collect
        ]
        _need(
            bool(claims)
            and all(type(value) is list and len(value) == 1 for value in claims),
            "one Collect binding evidence object per occurrence",
        )
        _need(
            all(value == claims[0] for value in claims),
            "conflicting Collect binding evidence",
        )
        binding = claims[0][0]
        _keys(binding, ("use", "producer", "terminal", "children"))
        for key in ("use", "producer", "terminal"):
            _reference(binding[key])
        _need(type(binding["children"]) is list, "Collect binding children")
        for child in binding["children"]:
            _reference(child)
        expected_binding = {
            "use": use,
            "producer": binding["producer"],
            "terminal": producer,
            "children": [a["child"] for a in arrays],
        }
        _need(
            binding == expected_binding
            and binding["producer"]["kind"] == "definition"
            and binding["producer"]["position"] not in source_definition_positions,
            "Collect binding does not describe the actual terminal",
        )
        ckey, tkey, pkey = (
            encoded(value).decode()
            for value in (collect, producer, binding["producer"])
        )
        _need(
            collect_bindings.setdefault(ckey, binding) == binding
            and terminal_producers.setdefault(tkey, binding["producer"])
            == binding["producer"]
            and producer_terminals.setdefault(pkey, producer) == producer,
            "Collect producer/terminal binding drift",
        )
        requirements = [
            ("collect_lateral", collect, "R27", "naming", expected_binding),
            ("collect_count", None, "R27", [], None),
            *(("collect_array", a["child"], "R27", [], None) for a in arrays),
        ]
        if wrapper is not None:
            requirements.append(
                ("collect_ordinal", wrapper["ordinal"]["order"], "R27", [], None)
            )
            requirements.append(("read_only_select_bytes", None, "R23", [], None))
        if inline:
            requirements.extend(inline_generated)
        else:
            _need(not inline_generated, "a named Collect terminal adds no body")
        requirements.append(("read_only_select_bytes", None, "R23", [], None))
        lateral = {
            "collect": collect,
            "use": use,
            "producer": binding["producer"],
            "arrays": arrays,
            "terminal": terminal,
            "wrapper": wrapper is not None,
            "requirements": requirements,
        }
        row_collects.append(lateral)
        return lateral

    def carrier_group(
        scope_role, scope_subject, final, position, *, count_kinds=("export",)
    ):
        """Phase71 S08: one nested group's 1+F physical columns read through one
        scope: the count under the field's label, then each child's array."""
        carriers = []
        scope = None
        count_start = lexical[cursor][0]["start"]
        count_end = None
        while True:
            separator = None
            if carriers:
                separator, _ = take("syntax", "separator", ", ")
            scope_token, alias = take("identifier", scope_role)
            _need(
                scope_token["subject"] == scope_subject
                and (scope is None or alias == scope),
                "one nested group reads one scope",
            )
            scope = alias
            qualifier, _ = take("syntax", "qualifier", ".")
            subject = qualifier["subject"]
            _need(
                subject["kind"] in (count_kinds if not carriers else ("export",))
                and (separator is None or separator["subject"] == subject),
                "nested carrier subject",
            )
            token, name = take("identifier", "collect_carrier_column", None, subject)
            if not carriers:
                count_end = token["end"]
            take("syntax", "alias", " AS ", subject)
            _, label = take("identifier", "label", None, subject)
            carriers.append({"subject": subject, "name": name, "label": label})
            if not (
                following("separator", scope_role, "qualifier")
                and lexical[cursor + 1][0]["subject"] == scope_subject
            ):
                break
        _need(
            len({encoded(c["subject"]) for c in carriers}) == len(carriers)
            and len(carriers) > 1,
            "a nested group is a count and at least one array",
        )
        _need(
            final
            or [c["label"] for c in carriers]
            == [
                f"c{position}",
                *(f"c{position}_{j}" for j in range(len(carriers) - 1)),
            ],
            "nested carrier labels",
        )
        return {
            "count_span": (count_start, count_end),
            "export": carriers[0]["subject"],
            "label": carriers[0]["label"],
            "scope": scope,
            "carriers": carriers,
        }

    def result_group(final, position):
        """A result body's carried nested group, read by its projection port."""
        port = lexical[cursor][0]["subject"]
        _need(port["kind"] == "result_port", "nested result port kind")
        group = carrier_group("result_carry_scope", port, final, position)
        return {
            **group,
            "port": port,
            "name": group["carriers"][0]["name"],
            "alias": group["scope"],
        }

    def collect_output(
        position, item, lateral, published=None, *, container_nullable=False
    ):
        """Independently rebuild one published nested column (Q1 option (a)):
        a ``collection`` of the terminal's child fields carried by its count
        and one array per child (``pg_column_arrays_v1``)."""
        _need(position < len(document["columns"]), "published column denominator")
        if published is None:
            published = document["columns"][position]
        published_columns = document["columns"]
        physical = position + 1
        for earlier in published_columns[:position]:
            element = earlier["logical_type"].get("element")
            physical += 0 if element is None else len(element)
        terminal = lateral["terminal"]
        carriers = item["carriers"]
        _need(
            len(carriers) == 1 + len(lateral["arrays"])
            and [c["subject"] for c in carriers[1:]]
            == [a["child"] for a in lateral["arrays"]]
            and carriers[0]["subject"] == item["export"],
            "nested output carriers",
        )
        elements, fields = [], []
        for j, (carrier, column) in enumerate(
            zip(carriers[1:], terminal["outgoing"], strict=True)
        ):
            realization = column["realization"]
            _need(type(realization["nullable"]) is bool, "child nullability")
            elements.append(
                {
                    "ordinal": j,
                    "label": carrier["label"],
                    "logical_type": {
                        "kind": "builtin",
                        "name": realization["tag"],
                        "parameters": {
                            "precision": realization["domain"]["precision"],
                            "scale": realization["domain"]["scale"],
                        }
                        if realization["tag"] == "Decimal"
                        else None,
                    },
                    "nullable": realization["nullable"],
                }
            )
            fields.append(
                {
                    "role": "field",
                    "child": j,
                    "storage": realization["storage"],
                    "sql_symbol": physical + 1 + j,
                }
            )
        expected = {
            "ordinal": position,
            "label": carriers[0]["label"],
            "logical_type": {
                "kind": "collection",
                "name": None,
                "parameters": None,
                "element": elements,
            },
            "nullable": container_nullable,
            "representation": {
                "carrier": "pg_column_arrays_v1",
                "columns": [{"role": "count", "sql_symbol": physical}, *fields],
            },
            "correspondence": {
                "collect": lateral["collect"],
                "use": lateral["use"],
                "producer": lateral["producer"],
                "children": [a["child"] for a in lateral["arrays"]],
                "export": item["export"],
                "sql_symbol": position + 1,
            },
        }
        _need(encoded(published) == encoded(expected), "nested output published")

    parsed_occurrences = {}

    def node_expression(node):
        return (
            node.get("expression")
            if node["kind"] != "constant"
            else node["value"]["expression"]
        )

    def row_parse(block, port_kind="stage_port", repeated=False):
        start = cursor
        node = _row_parse(block, port_kind, repeated=repeated)
        expression = node.get("expression")
        if expression is None and node["kind"] == "constant":
            expression = node["value"]["expression"]
        if expression is not None:
            key = encoded(expression)
            current = (encoded(block), start, cursor)
            previous = parsed_occurrences.setdefault(key, current)
            if previous != current:
                _need(
                    previous[0] == current[0]
                    and previous[2] - previous[1] == cursor - start,
                    "shared expression scope",
                )
                _need(
                    all(
                        (left["kind"], left["role"], left["subject"], left_text)
                        == (right["kind"], right["role"], right["subject"], right_text)
                        for (left, left_text), (right, right_text) in zip(
                            lexical[previous[1] : previous[2]],
                            lexical[start:cursor],
                            strict=True,
                        )
                    ),
                    "shared expression structure",
                )
        return node

    def _row_parse(block, port_kind="stage_port", repeated=False):
        """Parse one admitted value; a matching scope reads pre-match JOIN ports."""
        nonlocal scalar_nodes
        role, start = peek(), lexical[cursor][0]["start"]
        if role is not None and lexical[cursor][0]["kind"] == "literal":
            token, text = take("literal", role)
            _need(text == "NULL", "contextual NULL spelling")
            position = next(null_expression_positions)
            evidence = literal_evidence[position]
            _need(evidence["value"] is None)
            expression = ref("expression", position)
            seen_expressions.add(position)
            scalar_nodes += 1
            return {
                "kind": "constant",
                "value": {
                    "tag": evidence["tag"],
                    "value": None,
                    "expression": expression,
                    "leaf": expression,
                    "site": token["subject"],
                    "slot": None,
                    "requirements": [("literal", expression, evidence["tag"])],
                },
            }
        if role == "capture_scope":
            # A captured field: the reading body's own row, named by its alias.
            capture = lexical[cursor][0]["subject"]
            _need(capture["kind"] == "capture", "captured reference record")
            _, alias = take("identifier", "capture_scope", subject=capture)
            original = expression_ref(False, repeated)
            take("syntax", "capture_qualifier", ".", original)
            seen_expressions.add(original["position"])
            token, name = take("identifier", "capture_column")
            expected_ranges.append(("capture", original, start, token["end"]))
            return {
                "kind": "capture",
                "expression": original,
                "capture": capture,
                "name": name,
                "terminal": token["subject"],
                "alias": alias,
                "duplicate": repeated,
            }
        if role == "value_scope":
            port = lexical[cursor][0]["subject"]
            _, alias = take("identifier", "value_scope", subject=port)
            # S6: inside an `any` read, its own alias names the read's row.
            frame = next(
                (item for item in reversed(any_frames) if item["alias"] == alias), None
            )
            _need(
                port["kind"] == (port_kind if frame is None else frame["port_kind"]),
                "reference port kind",
            )
            original = expression_ref(False, repeated)
            take("syntax", "value_qualifier", ".", original)
            seen_expressions.add(original["position"])
            token, name = take("identifier", "value_column")
            expected_ranges.append(("reference", original, start, token["end"]))
            if port_kind == "stage_port" and frame is None:
                row_stage_ports.add(encoded(port).decode())
            return {
                "kind": "reference",
                "expression": original,
                "port": port,
                "name": name,
                "terminal": token["subject"],
                "alias": alias,
                "duplicate": repeated,
                "frame": frame,
            }
        if role == "anchor_open" or (role == "unary_open" and constant_ahead()):
            return {
                "kind": "constant",
                "value": scalar(block, positional=False, repeated=repeated),
                "duplicate": repeated,
            }
        original = expression_ref(False)
        seen_expressions.add(original["position"])
        if role == "unary_open":
            _, text = take("syntax", "unary_open", subject=original)
            _need(text in {"(+", "(-"}, "unary operator")
            operand, widened = widened_operand(block, port_kind, original)
            closed, _ = take("syntax", "unary_close", ")", original)
            expected_ranges.append(("unary", original, start, closed["end"]))
            return {
                "kind": "sign",
                "expression": original,
                "operator": text[1],
                "operands": [operand],
                "widened": widened,
            }
        if role == "is_null_open":
            take("syntax", "is_null_open", "(", original)
            operand = row_parse(block, port_kind)
            _, text = take("syntax", "is_null_test", subject=original)
            _need(text in {" IS NULL", " IS NOT NULL"}, "null test spelling")
            closed, _ = take("syntax", "is_null_close", ")", original)
            expected_ranges.append(("is_null", original, start, closed["end"]))
            return {
                "kind": "null_test",
                "expression": original,
                "operator": "is not null" if "NOT" in text else "is null",
                "operands": [operand],
            }
        if role == "not_open":
            take("syntax", "not_open", "(NOT ", original)
            operand = row_parse(block, port_kind)
            closed, _ = take("syntax", "not_close", ")", original)
            expected_ranges.append(("not", original, start, closed["end"]))
            return {"kind": "not", "expression": original, "operands": [operand]}
        if role == "between_open":
            take("syntax", "between_open", "(", original)
            value = row_parse(block, port_kind)
            take("syntax", "between_operator", " BETWEEN ", original)
            low = row_parse(block, port_kind)
            take("syntax", "between_separator", " AND ", original)
            high = row_parse(block, port_kind)
            closed, _ = take("syntax", "between_close", ")", original)
            expected_ranges.append(("between", original, start, closed["end"]))
            return {
                "kind": "between",
                "expression": original,
                "operands": [value, low, high],
            }
        if role == "conditional_open":
            take("syntax", "conditional_open", "(CASE WHEN ", original)
            predicate = row_parse(block, port_kind)
            take("syntax", "conditional_then", " THEN ", original)
            then_value = row_parse(block, port_kind)
            take("syntax", "conditional_else", " ELSE ", original)
            else_value = row_parse(block, port_kind)
            closed, _ = take("syntax", "conditional_close", " END)", original)
            expected_ranges.append(("conditional", original, start, closed["end"]))
            return {
                "kind": "conditional",
                "expression": original,
                "operands": [then_value, predicate, else_value],
            }
        if role == "membership_constant":
            _, token = take("syntax", "membership_constant", subject=original)
            _need(token in {"TRUE", "FALSE"}, "membership constant spelling")
            hidden = membership_constant_refs.get(original["position"])
            _need(hidden is not None, "empty membership hidden operand")
            assert hidden is not None
            seen_expressions.add(hidden["position"])
            expected_ranges.append(
                ("membership", original, start, lexical[cursor - 1][0]["end"])
            )
            return {
                "kind": "membership",
                "expression": original,
                "constant": token == "TRUE",
                "hidden_reference": hidden,
                "operands": [],
            }
        if role == "membership_open":
            take("syntax", "membership_open", "(", original)
            operands = [row_parse(block, port_kind)]
            _, token = take("syntax", "membership_operator", subject=original)
            _need(token in {" IN (", " NOT IN ("}, "membership spelling")
            while True:
                operands.append(row_parse(block, port_kind))
                if peek() != "membership_separator":
                    break
                take("syntax", "membership_separator", ", ", original)
            closed, _ = take("syntax", "membership_close", "))", original)
            expected_ranges.append(("membership", original, start, closed["end"]))
            return {
                "kind": "membership",
                "expression": original,
                "constant": None,
                "negated": token == " NOT IN (",
                "operands": operands,
            }
        if role == "cast_open":
            _, opening = take("syntax", "cast_open", subject=original)
            text_cast = opening == "(CAST("
            _need(
                opening == ("(CAST(" if text_cast else "CAST(")
                and (not text_cast or family == "postgres"),
                "cast spelling",
            )
            operand = row_parse(block, port_kind)
            _, token = take("syntax", "cast_close", subject=original)
            _need(
                token
                == (
                    ' AS pg_catalog.text) COLLATE "C")'
                    if text_cast
                    else " AS pg_catalog.float8)"
                    if family == "postgres"
                    else " AS DOUBLE)"
                ),
                "cast spelling",
            )
            expected_ranges.append(
                ("cast", original, start, lexical[cursor - 1][0]["end"])
            )
            return {
                "kind": "cast",
                "expression": original,
                "operator": "int_to_text" if text_cast else "int_to_float",
                "operands": [operand],
            }
        if role == "scalar_call_open":
            _, opening = take("syntax", "scalar_call_open", subject=original)
            call_argument_depth[0] += 1
            widened = False
            ordinary = {
                "postgres": {
                    "lower(": "lower",
                    "upper(": "upper",
                    "trim(": "trim",
                    "length(": "len",
                    "replace(": "replace",
                    "abs(": "abs",
                    "NULLIF(": "nullif",
                    "COALESCE(": "coalesce",
                },
                "mysql": {
                    "LOWER(": "lower",
                    "UPPER(": "upper",
                    "TRIM(": "trim",
                    "CHAR_LENGTH(": "len",
                    "REPLACE(": "replace",
                    "ABS(": "abs",
                    "NULLIF(": "nullif",
                    "COALESCE(": "coalesce",
                },
            }[family]
            if opening == "round(" and family == "postgres":
                operands = [row_parse(block, port_kind)]
                if peek() == "scalar_call_separator":
                    take("syntax", "scalar_call_separator", ", CAST(", original)
                    operands.append(row_parse(block, port_kind))
                    take(
                        "syntax",
                        "scalar_call_close",
                        " AS pg_catalog.int4))",
                        original,
                    )
                    close = None
                else:
                    close = ")"
                name = "round"
            elif opening == "(CASE WHEN abs((" and family == "postgres":
                operands = [row_parse(block, port_kind)]
                separators = (
                    ") - trunc(",
                    ") ) >= 0.5 THEN trunc(",
                    " ) + (CASE WHEN ",
                    " < 0 THEN -1.0 ELSE 1.0 END) ELSE trunc(",
                )
                for separator in separators:
                    take("syntax", "scalar_call_separator", separator, original)
                    repeated = row_parse(block, port_kind, repeated=True)
                    _need(
                        repeated["expression"] == operands[0]["expression"],
                        "Float round repeated operand",
                    )
                name, close = "round", " ) END)"
            elif (
                opening in {"CAST(date_trunc(", "date_trunc("} and family == "postgres"
            ):
                unit = row_parse(block, port_kind)
                date = opening == "CAST(date_trunc("
                take(
                    "syntax",
                    "scalar_call_separator",
                    ", CAST(" if date else ", ",
                    original,
                )
                temporal = row_parse(block, port_kind)
                operands, name = [unit, temporal], "date_trunc"
                if date:
                    take(
                        "syntax",
                        "scalar_call_close",
                        " AS timestamp))",
                        original,
                    )
                    close = " AS date)"
                else:
                    close = ")"
            elif opening in {"substring(", "SUBSTRING("}:
                _need(
                    opening == ("substring(" if family == "postgres" else "SUBSTRING(")
                )
                operands = [row_parse(block, port_kind)]
                take(
                    "syntax",
                    "scalar_call_separator",
                    " FROM " if family == "postgres" else ", ",
                    original,
                )
                if family == "postgres":
                    take("syntax", "scalar_call_index_cast_open", "CAST(", original)
                operands.append(row_parse(block, port_kind))
                if family == "postgres":
                    take(
                        "syntax",
                        "scalar_call_index_cast_close",
                        " AS pg_catalog.int4)",
                        original,
                    )
                take(
                    "syntax",
                    "scalar_call_separator",
                    " FOR " if family == "postgres" else ", ",
                    original,
                )
                if family == "postgres":
                    take("syntax", "scalar_call_index_cast_open", "CAST(", original)
                operands.append(row_parse(block, port_kind))
                if family == "postgres":
                    take(
                        "syntax",
                        "scalar_call_index_cast_close",
                        " AS pg_catalog.int4)",
                        original,
                    )
                name, close = "substr", ")"
            elif opening == "(statement_timestamp() AT TIME ZONE 'UTC'":
                # `now()` without operands, on PostgreSQL ...
                _need(family == "postgres", "now family")
                operands, name, close = [], "now", ")"
            elif opening == "UTC_TIMESTAMP(6":
                # ... and in a MySQL project's cells.
                _need(family == "mysql", "now family")
                operands, name, close = [], "now", ")"
            elif opening == "(":
                # PostgreSQL `concat` and `same_value` both open with `(`; the
                # separator after the first operand tells them apart.
                operands = [row_parse(block, port_kind)]
                if (
                    family == "postgres"
                    and cursor < len(lexical)
                    and lexical[cursor][1] == " || "
                ):
                    while peek() == "scalar_call_separator":
                        take("syntax", "scalar_call_separator", " || ", original)
                        operands.append(row_parse(block, port_kind))
                    _need(len(operands) >= 2, "concat arity")
                    name, close = "concat", ")"
                else:
                    take(
                        "syntax",
                        "scalar_call_separator",
                        " IS NOT DISTINCT FROM " if family == "postgres" else " <=> ",
                        original,
                    )
                    operands.append(row_parse(block, port_kind))
                    name, close = "same_value", ")"
            elif opening in {"(strpos(", "(INSTR("}:
                _need(opening == ("(strpos(" if family == "postgres" else "(INSTR("))
                first = row_parse(block, port_kind)
                take("syntax", "scalar_call_separator", ", ", original)
                second = row_parse(block, port_kind)
                operands = [first, second]
                name, close = "contains", ") > 0)"
            elif opening in {"(left(", "(right(", "(LEFT(", "(RIGHT("}:
                name = {
                    "(left(": "starts_with",
                    "(LEFT(": "starts_with",
                    "(right(": "ends_with",
                    "(RIGHT(": "ends_with",
                }.get(opening)
                _need(
                    name is not None
                    and opening
                    == (
                        {"starts_with": "(left(", "ends_with": "(right("}[name]
                        if family == "postgres"
                        else {"starts_with": "(LEFT(", "ends_with": "(RIGHT("}[name]
                    )
                )
                left = row_parse(block, port_kind)
                take("syntax", "scalar_call_separator", ", ", original)
                take(
                    "syntax",
                    "scalar_call_nested_open",
                    "length(" if family == "postgres" else "CHAR_LENGTH(",
                    original,
                )
                right = row_parse(block, port_kind)
                take("syntax", "scalar_call_nested_close", ")", original)
                take("syntax", "scalar_call_operator", " ) = ", original)
                repeated_operand = row_parse(block, port_kind, repeated=True)
                _need(
                    right["kind"] == repeated_operand["kind"]
                    and (
                        right["expression"] == repeated_operand["expression"]
                        if right["kind"] == "reference"
                        else right["value"]["expression"]
                        == repeated_operand["value"]["expression"]
                        if right["kind"] == "constant"
                        else False
                    ),
                    "starts/ends repeated operand",
                )
                operands, close = [left, right], ")"
            elif opening == "CAST(" and family == "postgres":
                operands, name, close = (
                    [row_parse(block, port_kind)],
                    "date_of",
                    " AS date)",
                )
            elif opening.startswith("CAST("):
                names = {
                    "CAST(length(": "len",
                    "CAST(CHAR_LENGTH(": "len",
                    "CAST(sign(": "sign",
                    "CAST(SIGN(": "sign",
                    "CAST(EXTRACT(YEAR FROM ": "year",
                    "CAST(EXTRACT(MONTH FROM ": "month",
                    "CAST(EXTRACT(DAY FROM ": "day",
                    "CAST(EXTRACT(HOUR FROM ": "hour",
                    "CAST(EXTRACT(MINUTE FROM ": "minute",
                    "CAST(YEAR(": "year",
                    "CAST(MONTH(": "month",
                    "CAST(DAY(": "day",
                    "CAST(HOUR(": "hour",
                    "CAST(MINUTE(": "minute",
                }
                name = names.get(opening)
                _need(name is not None, "scalar cast spelling")
                assert name is not None
                expected = (
                    "CAST(length("
                    if family == "postgres" and name == "len"
                    else "CAST(CHAR_LENGTH("
                    if name == "len"
                    else "CAST(EXTRACT(" + name.upper() + " FROM "
                    if family == "postgres"
                    and name in {"year", "month", "day", "hour", "minute"}
                    else "CAST(sign("
                    if family == "postgres"
                    else "CAST(" + ("SIGN" if name == "sign" else name.upper()) + "("
                )
                _need(opening == expected, "scalar cast spelling")
                operands = [row_parse(block, port_kind)]
                close = (
                    ") AS pg_catalog.int8)" if family == "postgres" else ") AS SIGNED)"
                )
            else:
                if opening == "DATE(" and family == "mysql":
                    operands, name, close = (
                        [row_parse(block, port_kind)],
                        "date_of",
                        ")",
                    )
                else:
                    name = ordinary.get(opening)
                    _need(name is not None, "closed scalar call spelling")
                    first, widened = widened_operand(block, port_kind, original)
                    _need(not widened or name == "abs", "int8 widening")
                    operands = [first]
                    while peek() == "scalar_call_separator":
                        take("syntax", "scalar_call_separator", ", ", original)
                        operands.append(row_parse(block, port_kind))
                    close = ")"
            if close is not None:
                take("syntax", "scalar_call_close", close, original)
            elif peek() == "scalar_call_close":
                _need(False, "starts/ends close role")
            end = lexical[cursor - 1][0]["end"]
            expected_ranges.append(("scalar_call", original, start, end))
            call_argument_depth[0] -= 1
            return {
                "kind": "scalar_call",
                "expression": original,
                "name": name,
                "operands": operands,
                "widened": name == "abs" and widened,
            }
        if role == "exists_open":
            # An existence read of one complete named producer terminal; a
            # physical source target is not part of this grammar.
            take("syntax", "exists_open", "EXISTS (", original)
            take("syntax", "exists_select", "SELECT ", original)
            take("literal", "exists_sentinel", "1", original)
            take("syntax", "exists_from", " FROM ", original)
            producer = lexical[cursor][0]["subject"]
            inline = scan = None
            if peek() == "inline_open":
                # Phase70 S10: a let with capture lines is the derived relation
                # of its own read; its obligations follow the read's own.
                source_body, inline = inline_read(producer)
            elif peek() == "exists_namespace":
                # S6: an `any` over a source scans that source again, under
                # its own alias; only a correlated read (below) may.
                item, index = bind_scan(producer)
                take(
                    "identifier",
                    "exists_namespace",
                    item["relation"]["namespace"],
                    producer,
                )
                take("syntax", "exists_qualifier", ".", producer)
                take(
                    "identifier", "exists_relation", item["relation"]["name"], producer
                )
                _need(cause(producer)["path"] == item["selector"]["module"])
                scan = {"description": item, "index": index}
                source_body = None
            else:
                _, name = take("identifier", "exists_reference", subject=producer)
                source_body = row_ctes.get(name)
            _need(
                scan is not None
                or source_body is not None
                and source_body["block"] == producer
                and source_body["projection"],
                "an existence read must read a complete definition terminal",
            )
            use = lexical[cursor][0]["subject"]
            _need(use["kind"] == "expression_block_use", "existence read use")
            take("syntax", "exists_alias", " AS ", use)
            _, alias = take("identifier", "exists_scope", subject=use)
            _need(alias == f"e{use['position']}", "existence read alias")
            correlated = None
            if peek() == "exists_where":
                # S6: `any(P for x in X)` keeps the rows of X for which P is
                # TRUE; P reads that row by the read's alias and the outer row.
                _need(inline is None, "a capture read has no correlated predicate")
                take("syntax", "exists_where", " WHERE ", original)
                if scan is not None:
                    columns = [
                        {
                            "name": field["column"],
                            "terminal": source_port(producer, field),
                            "realization": row_field_realization(field),
                        }
                        for field in scan["description"]["fields"]
                    ]
                else:
                    assert source_body is not None
                    columns = source_body["outgoing"]
                any_frames.append(
                    {
                        "alias": alias,
                        "columns": columns,
                        "port_kind": "source_port" if scan else "result_port",
                    }
                )
                predicate = row_parse(block)
                any_frames.pop()
                correlated = {"scan": scan, "predicate": predicate}
            _need(
                scan is None or correlated is not None,
                "a source read by an existence value is correlated",
            )
            closed, _ = take("syntax", "exists_close", ")", original)
            expected_ranges.append(("exists", original, start, closed["end"]))
            return {
                "kind": "exists",
                "expression": original,
                "use": use,
                "inline": inline,
                "correlated": correlated,
            }
        if role == "scalar_open":
            # A scalar read of one output of one complete named producer
            # terminal; a physical source target is not part of this grammar.
            take("syntax", "scalar_open", "(", original)
            take("syntax", "scalar_select", "SELECT ", original)
            use = lexical[cursor][0]["subject"]
            _need(use["kind"] == "expression_block_use", "scalar read use")
            _, alias = take("identifier", "scalar_scope", subject=use)
            _need(alias == f"e{use['position']}", "scalar read alias")
            take("syntax", "scalar_column_qualifier", ".", original)
            _, column = take("identifier", "scalar_column", subject=original)
            take("syntax", "scalar_from", " FROM ", original)
            producer = lexical[cursor][0]["subject"]
            inline = None
            if peek() == "inline_open":
                # Phase70 S14: a let with capture lines read by `scalar` is
                # the derived relation of its own read, like an EXISTS read.
                source_body, inline = inline_read(producer)
            else:
                _, name = take("identifier", "scalar_reference", subject=producer)
                source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and source_body["block"] == producer
                and source_body["projection"],
                "a scalar read must read a complete definition terminal",
            )
            assert source_body is not None
            names = [item["name"] for item in source_body["outgoing"]]
            _need(names.count(column) == 1, "scalar read column")
            take("syntax", "scalar_alias", " AS ", use)
            _, again = take("identifier", "scalar_scope", subject=use)
            _need(again == alias, "scalar read alias")
            closed, _ = take("syntax", "scalar_close", ")", original)
            expected_ranges.append(("scalar", original, start, closed["end"]))
            return {
                "kind": "scalar",
                "expression": original,
                "use": use,
                "read": source_body["outgoing"][names.index(column)],
                "inline": inline,
            }
        if role == "in_open":
            # Phase70 S09: a three-valued membership in the one column of one
            # complete named producer terminal; a source target is not part of
            # this independent grammar.
            take("syntax", "in_open", "(", original)
            operand = row_parse(block, port_kind)
            _, token = take("syntax", "in_operator", subject=original)
            _need(token in {" IN (", " NOT IN ("}, "membership read spelling")
            take("syntax", "in_select", "SELECT ", original)
            use = lexical[cursor][0]["subject"]
            _need(use["kind"] == "expression_block_use", "membership read use")
            _, scope = take("identifier", "in_column_scope", subject=use)
            _need(scope == f"e{use['position']}", "membership read alias")
            take("syntax", "in_column_qualifier", ".", use)
            column_token, column = take("identifier", "in_column")
            take("syntax", "in_from", " FROM ", original)
            producer = lexical[cursor][0]["subject"]
            inline = None
            if peek() == "inline_open":
                # Phase70 S14: a let with capture lines read by `in`.
                source_body, inline = inline_read(producer)
            else:
                _, name = take("identifier", "in_reference", subject=producer)
                source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and source_body["block"] == producer
                and source_body["projection"]
                and len(source_body["outgoing"]) == 1
                and column == source_body["outgoing"][0]["name"]
                and column_token["subject"] == source_body["outgoing"][0]["terminal"],
                "a membership read compares with the one column of a complete "
                "definition terminal",
            )
            assert source_body is not None
            take("syntax", "in_alias", " AS ", use)
            _, alias = take("identifier", "in_scope", subject=use)
            _need(alias == scope, "membership read scope")
            closed, _ = take("syntax", "in_close", "))", original)
            expected_ranges.append(
                ("relation_membership", original, start, closed["end"])
            )
            return {
                "kind": "relation_membership",
                "expression": original,
                "negated": token == " NOT IN (",
                "operands": [operand],
                "column": source_body["outgoing"][0]["realization"],
                "inline": inline,
            }
        _need(
            role in {"binary_open", "comparison_open", "decimal_arithmetic_open"},
            "row expression node",
        )
        take(
            "syntax",
            role,
            "CAST((" if role == "decimal_arithmetic_open" else "(",
            original,
        )
        left, left_cast = null_cast_operand(block, port_kind, original)
        widened = False
        if not left_cast:
            left, widened = widened_operand(block, port_kind, original)
        operator_role = peek()
        _, token = take("syntax", operator_role, subject=original)
        right, right_cast = null_cast_operand(block, port_kind, original)
        if not right_cast:
            right = row_parse(block, port_kind)
        if operator_role == "comparison_operator" and token in {" LIKE ", " NOT LIKE "}:
            take("syntax", "comparison_escape", " ESCAPE '!'", original)
        closing = (
            "decimal_arithmetic_close"
            if role == "decimal_arithmetic_open"
            else "binary_close"
            if role == "binary_open"
            else "comparison_close"
        )
        closed, closing_text = take("syntax", closing, subject=original)
        if operator_role == "arithmetic_operator":
            _need(
                role in {"binary_open", "decimal_arithmetic_open"}
                and (
                    token in ARITHMETIC_TOKENS
                    # R08: MySQL's integer division.
                    or family == "mysql"
                    and token == " DIV "
                ),
                "operator",
            )
            kind, enclosure = "arithmetic", "binary"
        elif operator_role == "logical_operator":
            _need(role == "binary_open" and token in LOGICAL_TOKENS, "operator")
            kind, enclosure = "logical", "binary"
        else:
            _need(role == "comparison_open" and operator_role == "comparison_operator")
            if token in {" LIKE ", " NOT LIKE "}:
                pass
            else:
                _need(token in COMPARISON_TOKENS, "operator")
            kind, enclosure = "comparison", "comparison"
        _need(not widened or kind == "arithmetic", "int8 widening")
        _need(kind == "arithmetic" or not (left_cast or right_cast), "typed NULL cast")
        if role == "decimal_arithmetic_open":
            _need(
                closing_text.startswith(") AS pg_catalog.numeric(")
                and closing_text.endswith("))"),
                "Decimal arithmetic cast",
            )
        else:
            _need(closing_text == ")", "row expression close")
        expected_ranges.append((enclosure, original, start, closed["end"]))
        return {
            "kind": kind,
            "expression": original,
            "operator": token,
            "operands": [left, right],
            "widened": widened,
            "null_casts": [left_cast, right_cast],
        }

    def parsed_terminals(node):
        """The terminal of every stage read in one parsed value, in preorder."""
        if node["kind"] == "reference":
            return [node["terminal"]]
        return [
            terminal
            for operand in node.get("operands", ())
            for terminal in parsed_terminals(operand)
        ]

    def row_resolve(node, incoming, alias, owner, scopes=None, context=None):
        """Realize one parsed value against its own immediate columns.

        `scopes` names the per-alias pre-match inputs of one JOIN; without it the
        value reads this stage body's single immediate scan.
        """
        if node["kind"] == "constant":
            value = node["value"]
            if value["value"] is None:
                if not node.get("duplicate"):
                    for kind, subject, tag in value["requirements"]:
                        row_generated.append(
                            (
                                kind,
                                subject,
                                "R04",
                                row_node_premises(tag, (), kind),
                                "checked",
                            )
                        )
                        row_rules[subject["position"]] = "R04"
                return {
                    "tag": value["tag"],
                    "storage": None,
                    "nullable": True,
                    "domain": None,
                    "null": True,
                    "root": value["expression"],
                    "value": value,
                }
            realization = {"tag": value["tag"], **value_representation(value)}
            if value["tag"] == "Int":
                _need(type(value["value"]) is int, "Int literal proof")
                realization["proven_int_range"] = (value["value"], value["value"])
            if not node.get("duplicate"):
                for kind, subject, tag in value["requirements"]:
                    row_generated.append(
                        (
                            kind,
                            subject,
                            "R04",
                            row_node_premises(tag, (), kind),
                            "checked",
                        )
                    )
                    row_rules[subject["position"]] = "R04"
            return {**realization, "root": value["expression"], "value": value}
        if node["kind"] == "reference" and node.get("frame") is not None:
            # S6: one column of the row an enclosing `any` read scans.
            matches = [
                c
                for c in node["frame"]["columns"]
                if c["name"] == node["name"] and c["terminal"] == node["terminal"]
            ]
            _need(
                len(matches) == 1 and node["port"] == node["terminal"],
                "an existence predicate reads one column of its own row",
            )
            read = matches[0]
            _need(source_within(node["expression"], owner))
            if not node.get("duplicate"):
                row_generated.append(
                    (
                        "reference",
                        node["expression"],
                        "R05",
                        row_node_premises(read["realization"]["tag"], (), "reference"),
                        (
                            "reference",
                            row_block[0] if context is None else context,
                            node["expression"],
                        ),
                    )
                )
            row_rules[node["expression"]["position"]] = "R01"
            return {
                **read["realization"],
                "root": node["expression"],
                "read": read,
                "strict": read["realization"]["nullable"] is not True,
                "proof": read["realization"]["nullable"] is False,
            }
        if node["kind"] == "reference":
            if scopes is None:
                _need(node["alias"] == alias, "stage reference scope")
                visible = incoming
            else:
                item = scopes.get(node["alias"])
                _need(
                    item is not None,
                    "a matching reference must read one of this JOIN's own inputs",
                )
                assert item is not None
                visible = item["columns"]
            matches = [
                c
                for c in visible
                if c["name"] == node["name"] and c["terminal"] == node["terminal"]
            ]
            _need(len(matches) == 1, "reference outside the immediate stage scope")
            read = matches[0]
            key = encoded(node["port"]).decode()
            _need(
                row_port_reads.setdefault(key, read) is read, "stage port binding drift"
            )
            _need(source_within(node["expression"], owner))
            if not node.get("duplicate"):
                row_generated.append(
                    (
                        "reference",
                        node["expression"],
                        "R05",
                        row_node_premises(read["realization"]["tag"], (), "reference"),
                        (
                            "reference",
                            row_block[0] if context is None else context,
                            node["expression"],
                        ),
                    )
                )
            row_rules[node["expression"]["position"]] = "R01"
            return {
                **read["realization"],
                "root": node["expression"],
                "read": read,
                "literal": read.get("literal"),
                "strict": read.get("strict", False)
                or read["realization"]["nullable"] is not True,
                "proof": read.get("proof", False)
                or read["realization"]["nullable"] is False,
            }
        if node["kind"] == "capture":
            _need(bool(capture_frames), "a captured field outside its reading row")
            frame = capture_frames[-1]
            _need(node["alias"] == frame["alias"], "captured reference scope")
            matches = [
                c
                for c in frame["incoming"]
                if c["name"] == node["name"] and c["terminal"] == node["terminal"]
            ]
            _need(len(matches) == 1, "captured reference outside its reading row")
            read = matches[0]
            _need(source_within(node["expression"], owner))
            if not node.get("duplicate"):
                # Like an existence read, the public subject is its own record.
                row_generated.append(
                    (
                        "capture",
                        ("opaque", "capture"),
                        "R11",
                        row_node_premises(read["realization"]["tag"], (), "capture"),
                        None,
                    )
                )
            row_rules[node["expression"]["position"]] = "R01"
            return {
                **read["realization"],
                "root": node["expression"],
                "strict": read["realization"]["nullable"] is not True,
            }
        original = node["expression"]
        if node["kind"] == "exists":
            # Existence is never NULL; the read keeps its own block use.
            _need(source_within(original, owner))
            row_generated.append(
                (
                    "exists",
                    ("opaque", "exists"),
                    "R11",
                    row_node_premises("Bool", (), "exists"),
                    None,
                )
            )
            row_generated.extend(node.get("inline") or ())
            correlated = node.get("correlated")
            if correlated is not None:
                scan = correlated["scan"]
                if scan is not None:
                    index = scan["index"]
                    row_generated.append(
                        ("qualified_scan", None, "R01", ("scan", index), None)
                    )
                    row_generated.extend(
                        (
                            "source_representation",
                            None,
                            "R02",
                            ("field", index, field["ordinal"]),
                            None,
                        )
                        for field in scan["description"]["fields"]
                    )
                predicate = row_resolve(
                    correlated["predicate"], incoming, alias, owner, scopes, context
                )
                _need(
                    predicate["tag"] == "Bool"
                    and predicate["domain"]["kind"] == "bool01",
                    "an existence predicate is a Boolean value",
                )
            row_rules[original["position"]] = "R11"
            return {
                **row_bool(False),
                "root": original,
                "operands": [],
                "kind": "exists",
                "strict": True,
            }
        if node["kind"] == "scalar":
            # The read column's own carrier, NULL when its producer has no row.
            _need(source_within(original, owner))
            realization = {**node["read"]["realization"], "nullable": True}
            row_generated.append(
                (
                    "scalar",
                    ("opaque", "scalar"),
                    "R11",
                    row_node_premises(realization["tag"], (), "scalar"),
                    None,
                )
            )
            row_generated.extend(node.get("inline") or ())
            row_rules[original["position"]] = "R11"
            return {
                **realization,
                "root": original,
                "operands": [],
                "kind": "scalar",
                "strict": False,
            }
        if node["kind"] == "relation_membership":
            # Three-valued membership is nullable; the read precedes its operand.
            _need(source_within(original, owner))
            slot = len(row_generated)
            row_generated.append(None)
            # An inline let's obligations follow the read's, before its value's.
            row_generated.extend(node.get("inline") or ())
            left = row_resolve(
                node["operands"][0], incoming, alias, owner, scopes, context
            )
            column = node["column"]

            def text_carrier(item):
                # The family's one admitted Text profile at any width its
                # storage holds: the widths of the two sides may differ.
                domain, storage = item["domain"], item["storage"]
                width = domain.get("max_characters")
                return (
                    set(domain)
                    == {"kind", "max_characters", "encoding", "collation", "padding"}
                    and domain["kind"] == "text"
                    and type(width) is int
                    and 0 <= width
                    and (family == "postgres" or width <= 16383)
                    and (domain["encoding"], domain["collation"], domain["padding"])
                    == (
                        ("UTF8", "C", "NO PAD")
                        if family == "postgres"
                        else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
                    )
                    and (
                        storage == {"kind": "pg_text"}
                        if family == "postgres"
                        else storage == {"kind": "my_utf8mb4_text"}
                        or storage.get("kind") == "my_varchar"
                        and type(storage.get("length")) is int
                        and width <= storage["length"] <= 16383
                    )
                )

            # The product's carrier rule (`_membership_carrier_matches`): one
            # tag; Int ranges, Bool 0/1 values, one Text profile, or one
            # identical carrier otherwise.
            _need(
                left["tag"] == column["tag"]
                and (
                    left.get("null")
                    or left["tag"] == "Int"
                    and left["storage"]["kind"] in INT_BITS
                    and column["storage"]["kind"] in INT_BITS
                    and left["domain"]["kind"]
                    == column["domain"]["kind"]
                    == "int_range"
                    or left["tag"] == "Bool"
                    and left["domain"] == column["domain"] == {"kind": "bool01"}
                    or left["tag"] == "Text"
                    and text_carrier(left)
                    and text_carrier(column)
                    or left["tag"] != "Text"
                    and left["storage"] == column["storage"]
                    and left["domain"] == column["domain"]
                ),
                "membership read carrier",
            )
            row_generated[slot] = (
                "relation_membership",
                ("opaque", "relation_membership"),
                "R11",
                row_node_premises(
                    "Bool", (left["tag"], column["tag"]), "relation_membership"
                ),
                None,
            )
            row_rules[original["position"]] = "R11"
            return {
                **row_bool(True),
                "root": original,
                "operands": [left["root"]],
                "kind": "relation_membership",
                "strict": False,
            }
        kind = "arithmetic" if node["kind"] == "sign" else node["kind"]
        rule = "R06" if kind in {"logical", "not"} else "R05"
        # One requirement per node in exact rendering order: the node, then the
        # nodes of each operand, so the slot is reserved before descending.
        slot = len(row_generated)
        row_generated.append(None)
        order = (
            (1, 0, 2) if node["kind"] == "conditional" else range(len(node["operands"]))
        )
        resolved_operands = {}
        if having_context[0] is not None and within(
            cause(original), cause(having_context[0][0])
        ):
            authored = [node_expression(child) for child in node["operands"]]
            siblings = tuple(
                cause(reference)
                for reference in authored
                if reference is not None
                and within(cause(reference), cause(having_context[0][0]))
            )
            for position, reference in enumerate(authored):
                if reference is not None and not within(
                    cause(reference), cause(having_context[0][0])
                ):
                    having_uses.append(
                        (reference, having_context[0], original, position, siblings)
                    )
        for position in order:
            resolved_operands[position] = row_resolve(
                node["operands"][position], incoming, alias, owner, scopes, context
            )
        operands = [
            resolved_operands[position] for position in range(len(node["operands"]))
        ]
        tags = tuple(item["tag"] for item in operands)
        # Upstream NULL evidence is preserved, never strengthened here: an operator
        # result is not independently derivable, so it stays None and only a claim
        # of NON_NULL over a nullable operand is rejected later.
        strict = all(o.get("strict", o["nullable"] is False) for o in operands)
        nullable = None
        carrier = next((item for item in operands if not item.get("null")), None)

        def compatible(left, right):
            if left["tag"] == right["tag"] == "Int" and not (
                left.get("null") or right.get("null")
            ):
                return (
                    left["storage"]["kind"] in INT_BITS
                    and right["storage"]["kind"] in INT_BITS
                    and left["domain"]["kind"] == right["domain"]["kind"] == "int_range"
                    and left.get("proven_int_range") is not None
                    and right.get("proven_int_range") is not None
                )
            return left["tag"] == right["tag"] and (
                left.get("null")
                or right.get("null")
                or (
                    left["storage"] == right["storage"]
                    and left["domain"] == right["domain"]
                )
            )

        def membership_matches(first, value):
            if value.get("null"):
                return value["tag"] == first["tag"]
            if value["tag"] != first["tag"]:
                return False
            if first["tag"] == "Int":
                return (
                    first["storage"]["kind"] in INT_BITS
                    and value["storage"]["kind"] in INT_BITS
                    and first["domain"]["kind"]
                    == value["domain"]["kind"]
                    == "int_range"
                )
            if first["tag"] == "Text":
                try:
                    text_carrier_result((first, value))
                except ValueError:
                    return False
                return True
            if first["tag"] == "Bool":
                return first["domain"] == value["domain"] == {"kind": "bool01"} and (
                    first["storage"] == value["storage"] == {"kind": "pg_bool"}
                    or family == "mysql"
                    and first["storage"]
                    in ({"kind": "my_bool01"}, {"kind": "my_signed_bool"})
                    and value["storage"]
                    in ({"kind": "my_bool01"}, {"kind": "my_signed_bool"})
                )
            if value["storage"] != first["storage"]:
                return False
            if first["tag"] == "Decimal":
                return all(
                    first["domain"].get(key) == value["domain"].get(key)
                    for key in ("precision", "scale")
                )
            if first["tag"] == "Float":
                return (
                    first["domain"]
                    == value["domain"]
                    == {"kind": "finite_float", "format": "binary64"}
                )
            return first["domain"] == value["domain"]

        def text_result(value, maximum=None):
            _need(value["tag"] == "Text" and not value.get("null"), "Text operand")
            domain = dict(value["domain"])
            storage = dict(value["storage"])
            source_maximum = domain.get("max_characters")
            _need(
                type(source_maximum) is int and source_maximum >= 0, "Text source bound"
            )
            if maximum is not None:
                _need(type(maximum) is int and maximum >= 0, "Text result bound")
            if family == "postgres":
                _need(storage == {"kind": "pg_text"}, "Text storage")
            else:
                _need(
                    storage == {"kind": "my_utf8mb4_text"}
                    or (
                        storage.get("kind") == "my_varchar"
                        and type(storage.get("length")) is int
                        and source_maximum <= storage["length"] <= 16383
                    ),
                    "Text storage",
                )
            if maximum is not None:
                domain["max_characters"] = maximum
            if family == "mysql":
                _need(domain["max_characters"] <= 16383, "Text result bound")
                storage = {"kind": "my_varchar", "length": domain["max_characters"]}
            return {
                "tag": "Text",
                "storage": storage,
                "nullable": nullable,
                "domain": domain,
            }

        def text_carrier_result(values, maximum=None):
            concrete = [item for item in values if not item.get("null")]
            _need(
                bool(concrete) and all(item["tag"] == "Text" for item in concrete),
                "Text carrier",
            )
            profile = tuple(
                concrete[0]["domain"].get(key)
                for key in ("encoding", "collation", "padding")
            )
            widths = []
            for item in concrete:
                domain, storage = item["domain"], item["storage"]
                width = domain.get("max_characters")
                _need(
                    domain.get("kind") == "text"
                    and type(width) is int
                    and width >= 0
                    and tuple(
                        domain.get(key) for key in ("encoding", "collation", "padding")
                    )
                    == profile,
                    "Text carrier domain",
                )
                if family == "postgres":
                    _need(storage == {"kind": "pg_text"}, "Text carrier storage")
                else:
                    _need(
                        storage == {"kind": "my_utf8mb4_text"}
                        or (
                            storage.get("kind") == "my_varchar"
                            and type(storage.get("length")) is int
                            and width <= storage["length"] <= 16383
                        ),
                        "Text carrier storage",
                    )
                widths.append(width)
            return text_result(concrete[0], max(widths) if maximum is None else maximum)

        def int_carrier_result(values):
            concrete = [item for item in values if not item.get("null")]
            _need(
                bool(concrete) and all(item["tag"] == "Int" for item in concrete),
                "Int carrier",
            )
            bounds = [row_interval(item) for item in concrete]
            return row_int(
                concrete,
                min(low for low, _ in bounds),
                max(high for _, high in bounds),
                nullable,
            )

        def bool_carrier_result(values):
            concrete = [item for item in values if not item.get("null")]
            _need(
                bool(concrete)
                and all(
                    item["tag"] == "Bool" and item["domain"] == {"kind": "bool01"}
                    for item in concrete
                ),
                "Bool carrier",
            )
            if family == "postgres":
                _need(
                    all(item["storage"] == {"kind": "pg_bool"} for item in concrete),
                    "Bool carrier storage",
                )
            else:
                _need(
                    all(
                        item["storage"]
                        in ({"kind": "my_bool01"}, {"kind": "my_signed_bool"})
                        for item in concrete
                    ),
                    "Bool carrier storage",
                )
            return row_bool(nullable)

        def static_literal(value):
            literal = value.get("value") or value.get("literal")
            return None if literal is None else literal.get("value")

        def comparison_pair(left, right, operator):
            if left["tag"] == "UUID":
                # Q3: a UUID orders by its unsigned big-endian bytes: the
                # PostgreSQL uuid order and the MySQL BINARY(16) order.
                _need(
                    operator in COMPARISON_TOKENS and compatible(left, right),
                    "uuid comparison pair",
                )
            elif left["tag"] in {"Timestamp", "Date"}:
                # One temporal carrier orders by its exact instant or day.
                _need(
                    operator in COMPARISON_TOKENS and compatible(left, right),
                    "temporal comparison pair",
                )
            else:
                _need(
                    left["tag"] in COMPARABLE and left["tag"] == right["tag"],
                    "comparison type pair",
                )
            if left["tag"] == "Text":
                _need(
                    all(
                        left["domain"].get(k) == right["domain"].get(k) is not None
                        for k in ("encoding", "collation", "padding")
                    ),
                    "text comparison domain",
                )
            if left["tag"] == "Decimal":
                _need(
                    left["storage"] == right["storage"]
                    and all(
                        left["domain"].get(k) == right["domain"].get(k) is not None
                        for k in ("precision", "scale")
                    ),
                    "decimal comparison parameters",
                )

        def scalar_result(name):
            nonlocal nullable
            if name == "now":
                # The statement's UTC start, never NULL.
                _need(family in {"postgres", "mysql"} and not operands, "now carrier")
                return {
                    "tag": "Timestamp",
                    "storage": {
                        "kind": "pg_timestamp"
                        if family == "postgres"
                        else "my_datetime",
                        "fractional_seconds": 6,
                    },
                    "nullable": False,
                    "domain": {"kind": "timestamp"},
                }
            if name == "round":
                _need(family == "postgres", "round family")
                value = operands[0]
                if value["tag"] == "Float":
                    _need(
                        len(operands) == 1
                        and value["storage"] == {"kind": "pg_float8"}
                        and value["domain"]
                        == {"kind": "finite_float", "format": "binary64"},
                        "Float round carrier",
                    )
                    return {
                        "tag": "Float",
                        "storage": {"kind": "pg_float8"},
                        "nullable": nullable,
                        "domain": {"kind": "finite_float", "format": "binary64"},
                    }
                _need(value["tag"] == "Decimal", "Decimal round operand")
                parameters = value["domain"]
                _need(
                    value["storage"]
                    == {
                        "kind": "pg_numeric",
                        "precision": parameters.get("precision"),
                        "scale": parameters.get("scale"),
                    }
                    and type(parameters.get("precision")) is int
                    and type(parameters.get("scale")) is int,
                    "Decimal round carrier",
                )
                scale = 0 if len(operands) == 1 else static_literal(operands[1])
                _need(
                    len(operands) == 1
                    or (
                        operands[1]["tag"] == "Int"
                        and type(scale) is int
                        and -30 <= scale <= 30
                    ),
                    "Decimal round scale",
                )
                assert type(scale) is int
                result_scale = min(parameters["scale"], max(scale, 0))
                result_precision = (
                    parameters["precision"]
                    if scale >= parameters["scale"]
                    else parameters["precision"]
                    - parameters["scale"]
                    + 1
                    + result_scale
                )
                _need(
                    1 <= result_precision <= 65
                    and 0 <= result_scale <= min(result_precision, 30),
                    "Decimal round result carrier",
                )
                return {
                    "tag": "Decimal",
                    "storage": {
                        "kind": "pg_numeric",
                        "precision": result_precision,
                        "scale": result_scale,
                    },
                    "nullable": nullable,
                    "domain": {
                        "kind": "decimal",
                        "precision": result_precision,
                        "scale": result_scale,
                    },
                }
            if name == "date_trunc":
                _need(family == "postgres" and len(operands) == 2, "date_trunc family")
                unit, temporal = operands
                value = static_literal(unit)
                _need(
                    unit["tag"] == "Text" and type(value) is str,
                    "date_trunc unit literal",
                )
                if temporal["tag"] == "Date":
                    _need(
                        value in {"year", "month", "day"}
                        and temporal["storage"] == {"kind": "pg_date"}
                        and temporal["domain"] == {"kind": "date"},
                        "date_trunc Date carrier",
                    )
                    return {
                        "tag": "Date",
                        "storage": {"kind": "pg_date"},
                        "nullable": nullable,
                        "domain": {"kind": "date"},
                    }
                _need(
                    value in {"year", "month", "day", "hour", "minute"}
                    and temporal["tag"] == "Timestamp"
                    and temporal["storage"]
                    == {"kind": "pg_timestamp", "fractional_seconds": 6}
                    and temporal["domain"] == {"kind": "timestamp"},
                    "date_trunc Timestamp carrier",
                )
                return {
                    "tag": "Timestamp",
                    "storage": {"kind": "pg_timestamp", "fractional_seconds": 6},
                    "nullable": nullable,
                    "domain": {"kind": "timestamp"},
                }
            if name in {"lower", "upper", "trim"} and len(operands) == 1:
                return text_result(operands[0])
            if (
                name == "len"
                and len(operands) == 1
                and operands[0]["tag"] == "Text"
                and not operands[0].get("null")
            ):
                maximum = operands[0]["domain"].get("max_characters")
                _need(type(maximum) is int and maximum >= 0, "Text length bound")
                return {
                    "tag": "Int",
                    "storage": {
                        "kind": "pg_int8" if family == "postgres" else "my_bigint"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "int_range", "min": "0", "max": str(maximum)},
                    "proven_int_range": (-(1 << 63), (1 << 63) - 1),
                }
            if name == "substr" and len(operands) == 3:
                text, start, count = operands
                _need(
                    text["tag"] == "Text"
                    and count["tag"] == "Int"
                    and not text.get("null")
                    and not count.get("null"),
                    "substring operands",
                )
                start_bounds = row_interval(start)
                _, high = row_interval(count)
                _need(high >= 0, "substring count")
                if family == "postgres":
                    _need(
                        all(
                            -(1 << 31) <= bound <= (1 << 31) - 1
                            for bound in (*start_bounds, *row_interval(count))
                        ),
                        "substring index physical range",
                    )
                return text_result(text, min(text["domain"]["max_characters"], high))
            if name == "replace" and len(operands) == 3:
                text, needle, replacement = operands
                _need(
                    text["tag"] == "Text"
                    and not text.get("null")
                    and all(
                        item.get("null") or item["tag"] == "Text"
                        for item in (needle, replacement)
                    ),
                    "replace operands",
                )
                return text_carrier_result(
                    (text, needle, replacement),
                    text["domain"]["max_characters"]
                    * max(1, replacement["domain"]["max_characters"]),
                )
            if name == "concat" and len(operands) >= 2:
                _need(
                    all(item["tag"] == "Text" for item in operands), "concat operands"
                )
                return text_carrier_result(
                    operands,
                    sum(
                        item["domain"]["max_characters"]
                        for item in operands
                        if not item.get("null")
                    ),
                )
            if name == "same_value":
                # NULL-safe equality of two values `==` compares: never NULL.
                _need(len(operands) == 2, "same_value arity")
                comparison_pair(operands[0], operands[1], " = ")
                return row_bool(False)
            if name in {"contains", "starts_with", "ends_with"} and len(operands) == 2:
                _need(
                    operands[0]["tag"] == operands[1]["tag"] == "Text",
                    "Text predicate operands",
                )
                text_carrier_result(operands)
                return row_bool(nullable)
            if name in {"coalesce", "nullif"}:
                _need(
                    (name == "coalesce" and len(operands) >= 2)
                    or (name == "nullif" and len(operands) == 2),
                    "coalesce/nullif arity",
                )
                if carrier is not None and carrier["tag"] == "Text":
                    _need(
                        all(
                            item.get("null") or item["tag"] == "Text"
                            for item in operands
                        ),
                        "coalesce/nullif Text operands",
                    )
                    return text_carrier_result(
                        operands,
                        None
                        if name == "coalesce"
                        else operands[0]["domain"].get("max_characters"),
                    )
                if carrier is not None and carrier["tag"] == "Int":
                    _need(
                        all(
                            item.get("null") or item["tag"] == "Int"
                            for item in operands
                        ),
                        "coalesce/nullif Int operands",
                    )
                    if name == "nullif":
                        _need(not operands[0].get("null"), "nullif Int lhs")
                        int_carrier_result(operands)
                        proof = operands[0].get("proven_int_range")
                        _need(proof is not None, "nullif Int proof")
                        return {
                            "tag": "Int",
                            "storage": operands[0]["storage"],
                            "nullable": nullable,
                            "domain": operands[0]["domain"],
                            "proven_int_range": proof,
                        }
                    return int_carrier_result(operands)
                if carrier is not None and carrier["tag"] == "Bool":
                    _need(
                        all(
                            item.get("null") or item["tag"] == "Bool"
                            for item in operands
                        ),
                        "coalesce/nullif Bool operands",
                    )
                    if name == "nullif":
                        _need(not operands[0].get("null"), "nullif Bool lhs")
                        bool_carrier_result(operands)
                        return {
                            "tag": "Bool",
                            "storage": operands[0]["storage"],
                            "nullable": nullable,
                            "domain": operands[0]["domain"],
                        }
                    return bool_carrier_result(operands)
                _need(
                    carrier is not None
                    and all(compatible(carrier, item) for item in operands),
                    "coalesce/nullif operands",
                )
                assert carrier is not None
                return {
                    "tag": carrier["tag"],
                    "storage": carrier["storage"],
                    "nullable": nullable,
                    "domain": carrier["domain"],
                }
            if name == "abs" and len(operands) == 1:
                _need(
                    operands[0]["tag"] in {"Int", "Float", "Decimal"}
                    and not operands[0].get("null"),
                    "abs operand",
                )
                if operands[0]["tag"] == "Int":
                    low, high = row_interval(operands[0])
                    return row_int(
                        [operands[0]],
                        max(low, -high, 0),
                        max(-low, high),
                        nullable,
                        node.get("widened", False),
                        operation=True,
                    )
                return {
                    "tag": operands[0]["tag"],
                    "storage": operands[0]["storage"],
                    "nullable": nullable,
                    "domain": operands[0]["domain"],
                }
            if name == "sign" and len(operands) == 1:
                _need(operands[0]["tag"] in {"Int", "Decimal"}, "sign operand")
                return {
                    "tag": "Int",
                    "storage": {
                        "kind": "pg_int8" if family == "postgres" else "my_signed_int"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "int_range", "min": "-1", "max": "1"},
                    "proven_int_range": (-1, 1),
                }
            if name == "date_of" and len(operands) == 1:
                value = operands[0]
                _need(
                    value["tag"] == "Timestamp"
                    and (
                        value.get("null")
                        or (
                            value["storage"]
                            == {
                                "kind": "pg_timestamp"
                                if family == "postgres"
                                else "my_datetime",
                                "fractional_seconds": 6,
                            }
                            and value["domain"] == {"kind": "timestamp"}
                        )
                    ),
                    "civil timestamp carrier",
                )
                return {
                    "tag": "Date",
                    "storage": {
                        "kind": "pg_date" if family == "postgres" else "my_date"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "date"},
                }
            if (
                name in {"year", "month", "day", "hour", "minute"}
                and len(operands) == 1
            ):
                value = operands[0]
                _need(
                    (
                        value["tag"] == "Timestamp"
                        and value["storage"]
                        == {
                            "kind": "pg_timestamp"
                            if family == "postgres"
                            else "my_datetime",
                            "fractional_seconds": 6,
                        }
                        and value["domain"] == {"kind": "timestamp"}
                    )
                    or (
                        name in {"year", "month", "day"}
                        and value["tag"] == "Date"
                        and value["storage"]
                        == {"kind": "pg_date" if family == "postgres" else "my_date"}
                        and value["domain"] == {"kind": "date"}
                    ),
                    "civil timestamp carrier",
                )
                low, high = {
                    "year": (1000, 9999),
                    "month": (1, 12),
                    "day": (1, 31),
                    "hour": (0, 23),
                    "minute": (0, 59),
                }[name]
                return {
                    "tag": "Int",
                    "storage": {
                        "kind": "pg_int8" if family == "postgres" else "my_signed_int"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
                    "proven_int_range": (low, high),
                }
            _need(False, "closed scalar call realization")
            raise AssertionError

        if node["kind"] == "sign":
            if operands[0]["tag"] == "Decimal":
                _need(family == "postgres", "Decimal sign target")
                result = {
                    "tag": "Decimal",
                    "storage": operands[0]["storage"],
                    "domain": operands[0]["domain"],
                    "nullable": nullable,
                }
            elif operands[0]["tag"] == "Float":
                source = operands[0].get("float_value")
                if source is None and "value" in operands[0]:
                    source = operands[0]["value"]["value"]
                result = {
                    "tag": "Float",
                    "storage": {
                        "kind": "pg_float8" if family == "postgres" else "my_double"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "finite_float", "format": "binary64"},
                }
                if source is None:
                    # E4: a PostgreSQL float8 sign over a finite field value
                    # flips or keeps its sign bit exactly.
                    _need(
                        family == "postgres"
                        and operands[0]["storage"] == {"kind": "pg_float8"}
                        and operands[0]["domain"] == FINITE_FLOAT,
                        "finite Float literal/sign",
                    )
                else:
                    _need(
                        type(source) is float and math.isfinite(source),
                        "finite Float literal/sign",
                    )
                    assert type(source) is float
                    result["float_value"] = (
                        -source if node["operator"] == "-" else source
                    )
            else:
                low, high = row_interval(operands[0])
                if node["operator"] == "-":
                    low, high = -high, -low
                result = row_int(
                    [operands[0], operands[0]],
                    low,
                    high,
                    nullable,
                    node.get("widened", False),
                    operation=True,
                )
        elif node["kind"] == "arithmetic":
            if any(item["tag"] == "Decimal" for item in operands) and all(
                item["tag"] in {"Decimal", "Int"} for item in operands
            ):
                _need(
                    all(
                        "read" in item
                        and (item["read"]["field"] is not None or family == "postgres")
                        or item["tag"] == "Int"
                        and "value" in item
                        or family == "postgres"
                        and item.get("kind") in {"arithmetic", "sign", "scalar_call"}
                        for item in operands
                    ),
                    "Decimal direct source operands",
                )
                left, right = operands
                expected_kind = "pg_numeric" if family == "postgres" else "my_decimal"
                _need(
                    all(
                        item["tag"] == "Int"
                        or item["storage"].get("kind") == expected_kind
                        and item["storage"].get("precision")
                        == item["domain"].get("precision")
                        and item["storage"].get("scale") == item["domain"].get("scale")
                        for item in operands
                    ),
                    "Decimal physical carrier",
                )

                def digits(item):
                    if item["tag"] == "Decimal":
                        return item["domain"]["precision"], item["domain"]["scale"]
                    low, high = row_interval(item)
                    if "value" in item:
                        _need(low == high, "Int literal digits")
                        return max(1, len(str(abs(low)))), 0
                    return {"pg_int2": 5, "pg_int4": 10, "pg_int8": 19}[
                        item["storage"]["kind"]
                    ], 0

                lp, ls = digits(left)
                rp, rs = digits(right)
                if node["operator"] in {" + ", " - "}:
                    _need(family == "postgres" or ls == rs, "Decimal scale")
                    scale = max(ls, rs)
                    precision = max(lp - ls, rp - rs) + 1 + scale
                elif node["operator"] == " * " and {
                    item["tag"] for item in operands
                } == {"Decimal", "Int"}:
                    _need(family == "postgres", "Decimal product target")
                    precision, scale = (
                        (lp, ls) if left["tag"] == "Decimal" else (rp, rs)
                    )
                    precision += 19
                else:
                    _need(node["operator"] == " * ", "Decimal operator")
                    precision, scale = lp + rp, ls + rs
                _need(precision <= 65 and scale <= 30, "Decimal result carrier")
                result = {
                    "tag": "Decimal",
                    "storage": {
                        "kind": expected_kind,
                        "precision": precision,
                        "scale": scale,
                    },
                    "nullable": nullable,
                    "domain": {
                        "kind": "decimal",
                        "precision": precision,
                        "scale": scale,
                    },
                }
            elif all(item["tag"] == "Float" for item in operands):
                values = []
                for item in operands:
                    value = item.get("float_value")
                    if value is None and "value" in item:
                        value = item["value"]["value"]
                    values.append(value)
                result = {
                    "tag": "Float",
                    "storage": {
                        "kind": "pg_float8" if family == "postgres" else "my_double"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "finite_float", "format": "binary64"},
                }
                if family == "mysql" and node["operator"] == " % ":
                    # S15: a cell over two DOUBLE fields, MySQL's `fmod`; the
                    # readers under test derive the rest of the cell.
                    _need(
                        all(
                            item["storage"] == {"kind": "my_double"}
                            and item["domain"] == FINITE_FLOAT
                            for item in operands
                        ),
                        "MySQL Float remainder operands",
                    )
                elif None in values or node["operator"] == " / ":
                    # E4: no literal fold proves the result finite; PostgreSQL's
                    # checked float8 operator refuses an infinity (22003).
                    _need(
                        family == "postgres"
                        and all(
                            item["storage"] == {"kind": "pg_float8"}
                            and item["domain"] == FINITE_FLOAT
                            for item in operands
                        ),
                        "finite Float literal operands",
                    )
                    result["checked_binary64"] = True
                else:
                    _need(
                        all(type(v) is float and math.isfinite(v) for v in values),
                        "finite Float literal operands",
                    )
                    value = {
                        " + ": values[0] + values[1],
                        " - ": values[0] - values[1],
                        " * ": values[0] * values[1],
                    }[node["operator"]]
                    _need(math.isfinite(value), "finite Float result")
                    result["float_value"] = value
            elif family == "mysql" and node["operator"] == " % ":
                # S15: a cell over two BIGINT fields, inside signed 64 bits;
                # the readers under test derive the rest of the cell.
                _need(
                    all(
                        item["tag"] == "Int"
                        and item["storage"] == {"kind": "my_bigint"}
                        for item in operands
                    ),
                    "MySQL Int remainder operands",
                )
                result = {
                    "tag": "Int",
                    "storage": {"kind": "my_bigint"},
                    "nullable": nullable,
                    "domain": {
                        "kind": "int_range",
                        "min": str(I64_MIN),
                        "max": str(I64_MAX),
                    },
                    "proven_int_range": (I64_MIN, I64_MAX),
                }
            elif node["operator"] == " DIV ":
                # R08: a MySQL Int `/` cell (D77.27), an unsigned Int literal
                # of 0 or more over a SMALLINT, INT or BIGINT field, or such a
                # field over one of 2 or more; the readers under test derive
                # the rest of the cell.
                def division_literal(item, low):
                    value = item.get("value")
                    return (
                        value is not None
                        and not item.get("null")
                        and type(value["value"]) is int
                        and value["value"] >= low
                        and not any(r[0] == "unary" for r in value["requirements"])
                    )

                def division_field(item):
                    return (
                        "value" not in item
                        and item["tag"] == "Int"
                        and item["storage"]
                        in (
                            {"kind": "my_smallint"},
                            {"kind": "my_int"},
                            {"kind": "my_bigint"},
                        )
                    )

                _need(
                    family == "mysql"
                    and nullable is not False
                    and (
                        division_literal(operands[0], 0)
                        and division_field(operands[1])
                        or division_field(operands[0])
                        and division_literal(operands[1], 2)
                    ),
                    "MySQL Int division operands",
                )
                result = {
                    "tag": "Int",
                    "storage": {"kind": "my_bigint"},
                    "nullable": nullable,
                    "domain": {
                        "kind": "int_range",
                        "min": str(I64_MIN),
                        "max": str(I64_MAX),
                    },
                    "proven_int_range": (I64_MIN, I64_MAX),
                }
            elif node["operator"] in {" / ", " % "}:
                _need(
                    family == "postgres"
                    and all(
                        item["tag"] == "Int" and item["storage"]["kind"] in INT_BITS
                        for item in operands
                    ),
                    "PostgreSQL integer division operands",
                )
                result = row_int(
                    ({"storage": {"kind": "pg_int8"}},),
                    I64_MIN,
                    I64_MAX,
                    nullable,
                )
            elif [bool(item.get("null")) for item in operands].count(True) == 1:
                # D-12: a typed NULL operand nulls every row; it is CAST to the
                # target's Int carrier, which types the result, which claims
                # the single value 0, as no row has one.
                _need(
                    node["null_casts"] == [bool(item.get("null")) for item in operands],
                    "typed NULL cast",
                )
                (other,) = (item for item in operands if not item.get("null"))
                result = row_int(
                    (other, {"storage": {"kind": "pg_int8"}}), 0, 0, nullable
                )
            else:
                (low_l, high_l), (low_r, high_r) = (row_interval(o) for o in operands)
                if node["operator"] == " + ":
                    low, high = low_l + low_r, high_l + high_r
                elif node["operator"] == " - ":
                    low, high = low_l - high_r, high_l - low_r
                else:
                    products = [a * b for a in (low_l, high_l) for b in (low_r, high_r)]
                    low, high = min(products), max(products)
                result = row_int(
                    operands,
                    low,
                    high,
                    nullable,
                    node.get("widened", False),
                    operation=True,
                )
        elif node["kind"] == "logical":
            _need(
                all(
                    o["tag"] == "Bool" and o["domain"]["kind"] == "bool01"
                    for o in operands
                ),
                "logical operand domain",
            )
            result = row_bool(nullable)
        elif node["kind"] == "null_test":
            result = row_bool(False)
        elif node["kind"] == "not":
            _need(
                operands[0]["tag"] == "Bool"
                and operands[0]["domain"] == {"kind": "bool01"},
                "not operand",
            )
            result = row_bool(nullable)
        elif node["kind"] == "between":
            # A window distribution result (float64) compares with finite bounds.
            float_chain = all(
                item["tag"] == "Float"
                and item["storage"] == operands[0]["storage"]
                and item["domain"] in (FINITE_FLOAT, {"kind": "float64"})
                for item in operands
            )
            _need(
                (
                    float_chain
                    or all(compatible(operands[0], item) for item in operands[1:])
                )
                and (operands[0]["tag"] in COMPARABLE or operands[0]["tag"] == "UUID"),
                "between type pair",
            )
            result = row_bool(nullable)
        elif node["kind"] == "conditional":
            _need(
                operands[1]["tag"] == "Bool"
                and operands[1]["domain"] == {"kind": "bool01"},
                "conditional predicate",
            )
            if carrier is not None and carrier["tag"] == "Text":
                _need(
                    all(
                        item.get("null") or item["tag"] == "Text"
                        for item in (operands[0], operands[2])
                    ),
                    "conditional Text branches",
                )
                result = text_carrier_result((operands[0], operands[2]))
            elif carrier is not None and carrier["tag"] == "Int":
                _need(
                    all(
                        item.get("null") or item["tag"] == "Int"
                        for item in (operands[0], operands[2])
                    ),
                    "conditional Int branches",
                )
                result = int_carrier_result((operands[0], operands[2]))
            elif carrier is not None and carrier["tag"] == "Bool":
                _need(
                    all(
                        item.get("null") or item["tag"] == "Bool"
                        for item in (operands[0], operands[2])
                    ),
                    "conditional Bool branches",
                )
                result = bool_carrier_result((operands[0], operands[2]))
            else:
                _need(
                    compatible(operands[0], operands[2]) and carrier is not None,
                    "conditional branches",
                )
                assert carrier is not None
                result = {
                    "tag": carrier["tag"],
                    "storage": carrier["storage"],
                    "nullable": nullable,
                    "domain": carrier["domain"],
                }
        elif node["kind"] == "membership":
            if node.get("constant") is not None:
                result = row_bool(False)
            else:
                first = next((item for item in operands if not item.get("null")), None)
                _need(
                    first is not None
                    and first["tag"] in COMPARABLE
                    and all(membership_matches(first, item) for item in operands[1:]),
                    "membership type pair",
                )
                result = row_bool(nullable)
        elif node["kind"] == "cast":
            _need(
                operands[0]["tag"] == "Int" and not operands[0].get("null"),
                "cast operand",
            )
            row_interval(operands[0])
            if node["operator"] == "int_to_text":
                _need(family == "postgres", "Text cast family")
                result = {
                    "tag": "Text",
                    "storage": {"kind": "pg_text"},
                    "nullable": nullable,
                    "domain": {
                        "kind": "text",
                        "max_characters": 20,
                        "encoding": "UTF8",
                        "collation": "C",
                        "padding": "NO PAD",
                    },
                }
            else:
                _need(node["operator"] == "int_to_float", "cast operation")
                result = {
                    "tag": "Float",
                    "storage": {
                        "kind": "pg_float8" if family == "postgres" else "my_double"
                    },
                    "nullable": nullable,
                    "domain": {"kind": "finite_float", "format": "binary64"},
                }
        elif node["kind"] == "scalar_call":
            result = scalar_result(node["name"])
        else:
            comparison_pair(operands[0], operands[1], node["operator"])
            result = row_bool(nullable)
        _need(source_within(original, owner))
        spelling = (
            {"callable": node["name"], "namespace": "callable"}
            if node["kind"] == "scalar_call"
            else {"operator": "between"}
            if node["kind"] == "between"
            else None
            if node["kind"] in {"conditional", "membership", "cast", "not"}
            else node["operator"]
            if node["kind"] in {"sign", "null_test"}
            else ROW_OPERATORS[node["operator"]]
        )
        generated_subject = (
            ("opaque", node["kind"])
            if node["kind"] in {"scalar_call", "conditional", "not", "cast", "between"}
            else original
        )
        evidence = (
            spelling
            if type(spelling) is dict or spelling is None
            else {"operator": spelling}
        )
        if result.get("checked"):
            evidence = [evidence, {"overflow": TARGET_CHECKED}]
        elif result.get("checked_binary64"):
            evidence = [evidence, {"overflow": TARGET_CHECKED_BINARY64}]
        row_generated[slot] = (
            kind,
            generated_subject,
            rule,
            row_node_premises(result["tag"], tags, kind),
            evidence,
        )
        if node["kind"] == "membership" and node.get("constant") is not None:
            hidden = node["hidden_reference"]
            _need(hidden is not None, "empty membership hidden operand")
            row_generated.append(
                (
                    "reference",
                    hidden,
                    "R05",
                    row_node_premises("Bool", (), "reference"),
                    ("reference", row_block[0] if context is None else context, hidden),
                )
            )
        # A field sign is a generated arithmetic requirement, but its retained
        # demand is still the R04 literal/unary family, like any authored sign.
        row_rules[original["position"]] = (
            "R04" if node["kind"] in {"sign", "scalar_call", "not"} else rule
        )
        result_strict = strict and node["kind"] != "null_test"
        if node["kind"] == "conditional":
            result_strict = all(
                item["nullable"] is False for item in (operands[0], operands[2])
            )
        elif node["kind"] == "membership" and node.get("constant") is not None:
            result_strict = True
        elif node["kind"] == "scalar_call" and node["name"] == "coalesce":
            result_strict = any(item["nullable"] is False for item in operands)
        elif node["kind"] == "scalar_call" and node["name"] == "nullif":
            result_strict = False
        elif node["kind"] == "scalar_call" and node["name"] == "same_value":
            result_strict = True
        # The semantic NON_NULL proof a carried computed value may claim mirrors
        # the let value's own typing, not physical strictness: comparison,
        # logical, arithmetic and BETWEEN results stay UNKNOWN there.
        proofs = [item.get("proof", item["nullable"] is False) for item in operands]
        if node["kind"] == "conditional":
            result_proof = proofs[0] and proofs[2]
        elif node["kind"] == "null_test" or (
            node["kind"] == "membership" and not proofs
        ):
            result_proof = True
        elif node["kind"] == "scalar_call" and node["name"] == "coalesce":
            result_proof = any(proofs)
        elif node["kind"] == "scalar_call" and node["name"] == "nullif":
            result_proof = False
        elif node["kind"] == "scalar_call" and node["name"] == "same_value":
            result_proof = True
        else:
            result_proof = node["kind"] in {
                "sign",
                "not",
                "cast",
                "membership",
                "scalar_call",
            } and all(proofs)
        return {
            **result,
            "root": original,
            "operands": [item["root"] for item in operands],
            "kind": kind,
            "strict": result_strict,
            "proof": result_proof,
        }

    row_counts = {
        "projection": 0,
        "result": 0,
        "aggregate_projection": 0,
        "window_projection": 0,
        "quotient_field": 0,
        "set_column": 0,
        "values_column": 0,
    }
    result_nodes = [0]

    def window_specification_parse(subject):
        """One OVER body: partitions, orders and an optional exact frame."""
        partitions, orders = [], []
        if peek() == "window_partition":
            take("syntax", "window_partition", "PARTITION BY ", subject)
            while True:
                _, alias = take("identifier", "window_partition_scope")
                take("syntax", "window_partition_qualifier", ".", subject)
                token, name = take("identifier", "window_partition_column")
                partitions.append(
                    {"alias": alias, "name": name, "terminal": token["subject"]}
                )
                if peek() != "window_partition_separator":
                    break
                take("syntax", "window_partition_separator", ", ", subject)
        if peek() == "window_spec_separator":
            take("syntax", "window_spec_separator", " ", subject)
        if peek() == "window_order":
            take("syntax", "window_order", "ORDER BY ", subject)
            while True:
                _, alias = take("identifier", "window_order_scope")
                take("syntax", "window_order_qualifier", ".", subject)
                token, name = take("identifier", "window_order_column")
                _, direction = take("syntax", "window_order_direction", subject=subject)
                _need(direction in {" ASC", " DESC"}, "window order direction")
                orders.append(
                    {
                        "alias": alias,
                        "name": name,
                        "terminal": token["subject"],
                        "direction": direction.strip().lower(),
                    }
                )
                if peek() != "window_order_separator":
                    break
                take("syntax", "window_order_separator", ", ", subject)
        frame = None
        if peek() == "window_frame_separator":
            take("syntax", "window_frame_separator", " ", subject)
        if peek() == "window_frame_unit":
            _, unit = take("syntax", "window_frame_unit", subject=subject)
            _need(unit in WINDOW_FRAME_UNITS, "window frame unit")
            _, start_bound = take("syntax", "window_frame_start", subject=subject)
            take("syntax", "window_frame_and", " AND ", subject)
            _, end_bound = take("syntax", "window_frame_end", subject=subject)
            exclusion = None
            if peek() == "window_frame_exclusion":
                _, exclusion = take("syntax", "window_frame_exclusion", subject=subject)
                _need(
                    exclusion
                    in {" EXCLUDE CURRENT ROW", " EXCLUDE GROUP", " EXCLUDE TIES"},
                    "window frame exclusion",
                )
            frame = {
                "unit": unit.split(" ")[0].lower(),
                "start": start_bound,
                "end": end_bound,
                "exclusion": exclusion,
            }
        return {"partitions": partitions, "orders": orders, "frame": frame}

    def window_parse(block):
        """One window occurrence: its spelling, arguments and OVER specification."""
        start = lexical[cursor][0]["start"]
        subject = lexical[cursor][0]["subject"]
        _need(subject["kind"] == "window", "window occurrence kind")
        _, spelling = take("syntax", "window_open", subject=subject)
        _need(spelling in WINDOW_SPELLINGS, "window spelling")
        arguments = []
        while peek() not in {"window_close", None}:
            if peek() == "window_argument_separator":
                take("syntax", "window_argument_separator", ", ", subject)
            if peek() == "window_argument_scope":
                _, alias = take("identifier", "window_argument_scope")
                take("syntax", "window_argument_qualifier", ".", subject)
                token, name = take("identifier", "window_argument_column")
                arguments.append({"kind": "port", "alias": alias, "name": name})
            else:
                _, literal = take("literal", "window_argument_literal", subject=subject)
                arguments.append({"kind": "literal", "value": literal})
        take("syntax", "window_close", ")", subject)
        take("syntax", "window_over", " OVER ", subject)
        if peek() == "window_reference":
            _, symbol = take("identifier", "window_reference")
            specification = {"reference": symbol}
        else:
            inner = lexical[cursor][0]["start"]
            take("syntax", "window_spec_open", "(", subject)
            specification = window_specification_parse(subject)
            closed, _ = take("syntax", "window_spec_close", ")", subject)
            expected_ranges.append(
                ("window_specification", subject, inner, closed["end"])
            )
        end = lexical[cursor - 1][0]["end"]
        expected_ranges.append(("window", subject, start, end))
        return {
            "window": subject,
            "spelling": spelling,
            "arguments": arguments,
            "specification": specification,
        }

    def window_clause_parse():
        """The generated WINDOW clause, definition by definition."""
        if peek() != "window_clause":
            return []
        stage, _ = take("syntax", "window_clause", " WINDOW ")
        definitions = []
        while True:
            token, symbol = take("identifier", "window_definition")
            subject = token["subject"]
            take("syntax", "window_definition_as", " AS ", subject)
            start = lexical[cursor][0]["start"]
            take("syntax", "window_spec_open", "(", subject)
            specification = window_specification_parse(subject)
            closed, _ = take("syntax", "window_spec_close", ")", subject)
            expected_ranges.append(
                ("window_specification", subject, start, closed["end"])
            )
            definitions.append({"symbol": symbol, "specification": specification})
            if peek() != "window_clause_separator":
                break
            take("syntax", "window_clause_separator", ", ", stage["subject"])
        _need(
            [item["symbol"] for item in definitions]
            == [f"w{index}" for index in range(len(definitions))],
            "generated window symbols",
        )
        return definitions

    def aggregate_parse(block):
        """One aggregate occurrence: exact spelling, DISTINCT role and argument."""
        start = lexical[cursor][0]["start"]
        subject = lexical[cursor][0]["subject"]
        _need(subject["kind"] == "aggregate", "aggregate occurrence kind")
        if peek() == "aggregate_guard_open":
            # S02: a MySQL SUM of an Int under its overflow guard, which reads
            # the argument three times.
            _need(family == "mysql", "guarded SUM family")
            arguments = []
            for role, text in MYSQL_SUM_GUARD[:-1]:
                take("syntax", role, text, subject)
                arguments.append(row_parse(block, repeated=bool(arguments)))
            closed, _ = take("syntax", *MYSQL_SUM_GUARD[-1], subject)
            _need(
                len({encoded(dict(item, duplicate=None)) for item in arguments}) == 1,
                "guarded SUM argument",
            )
            expected_ranges.append(("aggregate", subject, start, closed["end"]))
            return {
                "aggregate": subject,
                "spelling": "SUM(",
                "distinct": False,
                "argument": arguments[0],
                "delimiter": None,
                "order_by": [],
                "result_cast": None,
                "argument_cast": None,
                "function": "sum",
                "extra_arguments": [],
            }
        if (
            family == "mysql"
            and peek() == "aggregate_zero_open"
            and cursor + 1 < len(lexical)
            and lexical[cursor + 1][0]["role"] == "aggregate_guard_open"
        ):
            # S03: COALESCE(the guarded SUM of CASE WHEN test THEN x END, 0),
            # which reads the test and the argument three times each.
            take("syntax", "aggregate_zero_open", "COALESCE(", subject)
            tests, arguments = [], []
            unseen, unsited = set(seen_expressions), set(seen_sites)
            for role, text in MYSQL_SUM_GUARD[:-1]:
                take("syntax", role, text, subject)
                take("syntax", "aggregate_filter_open", "CASE WHEN ", subject)
                # The test's expressions and literal sites are seen again at
                # each later read.
                seen_expressions.intersection_update(unseen)
                for site in set(seen_sites) - unsited:
                    del seen_sites[site]
                tests.append(row_parse(block, repeated=bool(tests)))
                take("syntax", "aggregate_filter_then", " THEN ", subject)
                arguments.append(row_parse(block, repeated=bool(arguments)))
                take("syntax", "aggregate_filter_close", " END", subject)
            take("syntax", *MYSQL_SUM_GUARD[-1], subject)
            closed, _ = take("syntax", "aggregate_zero_close", ", 0)", subject)
            _need(
                all(
                    len({encoded(dict(item, duplicate=None)) for item in group}) == 1
                    for group in (tests, arguments)
                ),
                "guarded conditional sum operands",
            )
            expected_ranges.append(("aggregate", subject, start, closed["end"]))
            return {
                "aggregate": subject,
                "spelling": "SUM(",
                "distinct": False,
                "argument": arguments[0],
                "delimiter": tests[0],
                "order_by": [],
                "result_cast": None,
                "argument_cast": None,
                "function": "filtered_sum",
                "extra_arguments": [],
            }
        # A PostgreSQL test of a group is (COUNT(CASE ...) > 0) or = 0.
        tested = peek() == "aggregate_test_open"
        if tested:
            take("syntax", "aggregate_test_open", "(", subject)
        # A PostgreSQL conditional sum is COALESCE(CAST(SUM(CASE ...)), 0).
        zero = peek() == "aggregate_zero_open"
        if zero:
            take("syntax", "aggregate_zero_open", "COALESCE(", subject)
        root = peek() == "aggregate_root_open"
        if root:
            take("syntax", "aggregate_root_open", "SQRT(", subject)
        element = peek() == "aggregate_element_open"
        if element:
            take("syntax", "aggregate_element_open", "(", subject)
        result_cast = None
        if peek() == "aggregate_result_cast_open":
            take("syntax", "aggregate_result_cast_open", "CAST(", subject)
            result_cast = "pending"
        _, spelling = take("syntax", "aggregate_open", subject=subject)
        mysql_spread = (
            family == "mysql" and not root and spelling in MYSQL_SPREAD_FUNCTIONS
        )
        _need(spelling in AGGREGATE_SPELLINGS or mysql_spread, "aggregate spelling")
        # Only a PostgreSQL variance is CAST(VAR_SAMP(x) AS float8) or
        # VAR_POP, and only a deviation is under SQRT; a MySQL one is uncast.
        spread = family == "postgres" and (spelling, root) in SPREAD_FUNCTIONS
        _need(
            (not root or spread)
            and (not spread or result_cast is not None)
            and (not mysql_spread or result_cast is None),
            "variance square root",
        )
        if spread:
            result_cast = "pg_catalog.float8"
        distinct, argument, delimiter, order_by = False, None, None, []
        argument_cast, extra_arguments = None, []
        function = (
            MYSQL_SPREAD_FUNCTIONS[spelling]
            if mysql_spread
            else SPREAD_FUNCTIONS.get((spelling, root), AGGREGATE_SPELLINGS[spelling])
        )
        _need(element is (spelling == "ARRAY_AGG("), "ARRAY_AGG element")
        if element:
            # (ARRAY_AGG(x ORDER BY k ...))[1]; `last` writes each authored
            # direction reversed, under its own role.
            _need(family == "postgres", "ARRAY_AGG family")
            argument = row_parse(block)
            take("syntax", "aggregate_order", " ORDER BY ", subject)
            roles = set()
            while True:
                value = row_parse(block)
                role, direction = (
                    peek(),
                    take("syntax", peek(), subject=subject)[1],
                )
                _need(
                    role
                    in {
                        "aggregate_order_direction",
                        "aggregate_order_reversed_direction",
                    }
                    and direction in {" ASC", " DESC"},
                    "ARRAY_AGG direction",
                )
                roles.add(role)
                reversed_ = role == "aggregate_order_reversed_direction"
                order_by.append((value, (direction == " DESC") is not reversed_))
                if peek() != "aggregate_order_separator":
                    break
                take("syntax", "aggregate_order_separator", ", ", subject)
            _need(len(roles) == 1, "one direction role per ARRAY_AGG")
            if roles == {"aggregate_order_reversed_direction"}:
                function = "last"
        elif peek() == "aggregate_filter_open":
            # COUNT(CASE WHEN test THEN 1 END), or SUM(CASE WHEN test THEN
            # CAST(x AS pg_catalog.int8) END) under its checked CAST: the test
            # of a sum in the delimiter slot.
            counted = spelling == "COUNT("
            _need(
                family == "postgres"
                and spelling in {"COUNT(", "SUM("}
                and zero is not counted
                and (result_cast is None) is counted,
                "conditional aggregate shape",
            )
            _need(not tested or counted and not zero, "group test shape")
            take("syntax", "aggregate_filter_open", "CASE WHEN ", subject)
            test = row_parse(block)
            take("syntax", "aggregate_filter_then", " THEN ", subject)
            if tested and peek() == "aggregate_filter_else":
                take("syntax", "aggregate_filter_else", "NULL ELSE 1", subject)
                argument, function = test, "group_all"
            elif counted:
                take("syntax", "aggregate_filter_one", "1", subject)
                argument = test
                function = "group_any" if tested else "filtered_count"
            else:
                take("syntax", "aggregate_argument_cast_open", "CAST(", subject)
                argument = row_parse(block)
                take(
                    "syntax",
                    "aggregate_argument_cast_close",
                    " AS pg_catalog.int8)",
                    subject,
                )
                argument_cast, delimiter = "pg_catalog.int8", test
                function = "filtered_sum"
            take("syntax", "aggregate_filter_close", " END", subject)
        elif spelling == "PERCENTILE_CONT(":
            # PERCENTILE_CONT(fraction) WITHIN GROUP (ORDER BY CAST(x AS float8)).
            _need(family == "postgres", "PERCENTILE_CONT family")
            if peek() == "aggregate_fraction":
                take("syntax", "aggregate_fraction", "0.5", subject)
                function = "median"
            else:
                # An aggregate argument literal stays a literal under
                # BIND_SAFE, a specialized position as in the product.
                held = specialized[0]
                specialized[0] = True
                delimiter = row_parse(block)
                specialized[0] = held
            take("syntax", "aggregate_within", ") WITHIN GROUP (ORDER BY ", subject)
            take("syntax", "aggregate_argument_cast_open", "CAST(", subject)
            argument = row_parse(block)
            _, token = take("syntax", "aggregate_argument_cast_close", subject=subject)
            _need(token == " AS pg_catalog.float8)", "PERCENTILE_CONT order cast")
            argument_cast = "pg_catalog.float8"
        elif peek() == "aggregate_row_count":
            take("syntax", "aggregate_row_count", "*", subject)
            _need(spelling == "COUNT(", "only a row count has no argument")
        else:
            if peek() == "aggregate_distinct":
                take("syntax", "aggregate_distinct", "DISTINCT ", subject)
                distinct = True
                _need(spelling == "COUNT(", "only count_distinct spells DISTINCT")
            if peek() == "aggregate_tuple_open":
                # PostgreSQL COUNT(DISTINCT CASE WHEN a IS NOT NULL AND b IS NOT
                # NULL THEN ROW(a, b) END): each field read twice, in order.
                _need(family == "postgres" and distinct, "count_distinct_tuple form")
                take("syntax", "aggregate_tuple_open", "CASE WHEN ", subject)
                members = [row_parse(block)]
                while peek() == "aggregate_tuple_and":
                    take("syntax", "aggregate_tuple_and", " IS NOT NULL AND ", subject)
                    members.append(row_parse(block))
                take(
                    "syntax", "aggregate_tuple_then", " IS NOT NULL THEN ROW(", subject
                )
                for position, member in enumerate(members):
                    if position:
                        take("syntax", "aggregate_separator", ", ", subject)
                    again = row_parse(block, repeated=True)
                    _need(
                        member["kind"] == again["kind"] == "reference"
                        and member["expression"] == again["expression"],
                        "count_distinct_tuple field read again",
                    )
                take("syntax", "aggregate_tuple_close", ") END", subject)
                _need(len(members) > 1, "count_distinct_tuple fields")
                function = "count_distinct_tuple"
                argument, *extra_arguments = members
            elif spelling == "string_agg(":
                _need(family == "postgres", "string_agg family")
                argument = row_parse(block)
                take("syntax", "aggregate_separator", ", ", subject)
                delimiter = row_parse(block)
                take("syntax", "aggregate_order", " ORDER BY ", subject)
                while True:
                    value = row_parse(block)
                    _, direction = take(
                        "syntax", "aggregate_order_direction", subject=subject
                    )
                    _need(direction in {" ASC", " DESC"}, "string_agg direction")
                    order_by.append((value, direction == " DESC"))
                    if peek() != "aggregate_order_separator":
                        break
                    take("syntax", "aggregate_order_separator", ", ", subject)
            else:
                has_argument_cast = peek() == "aggregate_argument_cast_open"
                if has_argument_cast:
                    take("syntax", "aggregate_argument_cast_open", "CAST(", subject)
                argument = row_parse(block)
                if not has_argument_cast and peek() == "aggregate_argument_cast_close":
                    _need(False, "aggregate argument cast close")
                if has_argument_cast:
                    _, token = take(
                        "syntax", "aggregate_argument_cast_close", subject=subject
                    )
                    _need(
                        token.startswith(" AS ") and token.endswith(")"),
                        "aggregate argument cast",
                    )
                    argument_cast = token[4:-1]
        closed, _ = take("syntax", "aggregate_close", ")", subject)
        if result_cast is not None:
            _need(
                family == "postgres" and spelling in {"SUM(", "VAR_SAMP(", "VAR_POP("},
                "sum result cast",
            )
            closed, token = take(
                "syntax", "aggregate_result_cast_close", subject=subject
            )
            _need(token.startswith(" AS ") and token.endswith(")"), "sum result cast")
            actual_cast = token[4:-1]
            _need(
                result_cast == "pending" or actual_cast == result_cast,
                "sum result cast",
            )
            result_cast = actual_cast
        if root:
            closed, _ = take("syntax", "aggregate_root_close", ")", subject)
        _need(not zero or function == "filtered_sum", "conditional sum zero")
        if zero:
            closed, _ = take("syntax", "aggregate_zero_close", ", 0)", subject)
        _need(tested is (function in {"group_any", "group_all"}), "group test")
        if tested:
            closed, _ = take(
                "syntax",
                "aggregate_test_close",
                " > 0)" if function == "group_any" else " = 0)",
                subject,
            )
        if element:
            closed, _ = take("syntax", "aggregate_element_close", ")[1]", subject)
        expected_ranges.append(("aggregate", subject, start, closed["end"]))
        return {
            "aggregate": subject,
            "spelling": spelling,
            "distinct": distinct,
            "argument": argument,
            "delimiter": delimiter,
            "order_by": order_by,
            "result_cast": result_cast,
            "argument_cast": argument_cast if argument is not None else None,
            "function": function
            if function == "count_distinct_tuple"
            else "count_distinct"
            if distinct
            else function,
            "extra_arguments": extra_arguments,
        }

    def aggregate_realization(
        function,
        argument,
        argument_cast,
        delimiter=None,
        order_by=(),
        result_cast=None,
        grouped=True,
    ):
        """This result's own domain: a count is not its argument's value range."""
        floating = argument is not None and argument["tag"] == "Float"
        decimal_sum = argument is not None and argument["tag"] == "Decimal"
        _need(
            (result_cast is not None)
            is (
                function in set(SPREAD_FUNCTIONS.values())
                and family == "postgres"
                or function in {"sum", "filtered_sum"}
                and not floating
                and family == "postgres"
            ),
            "sum result cast",
        )
        if function in {"group_any", "group_all"}:
            # A count of a Bool test compared with 0: a computed Bool, never NULL.
            _need(
                family == "postgres"
                and argument is not None
                and argument["tag"] == "Bool"
                and argument_cast is None
                and delimiter is None
                and not order_by,
                "group test arguments",
            )
            return {
                "tag": "Bool",
                "storage": {"kind": "pg_bool"},
                "nullable": False,
                "domain": {"kind": "bool01"},
            }
        if function in {"filtered_count", "filtered_sum"}:
            # Never NULL: a count bounded by the count premise, a sum by its
            # checked bigint CAST, 0 when no row's test is True.
            counted = function == "filtered_count"
            test = argument if counted else delimiter
            # S03: a MySQL conditional sum is a guarded SUM of a BIGINT, uncast.
            guarded = family == "mysql" and not counted
            _need(
                (family == "postgres" or guarded)
                and argument is not None
                and test is not None
                and test["tag"] == "Bool"
                and (counted or argument["tag"] == "Int")
                and (not guarded or argument["storage"] == {"kind": "my_bigint"})
                and argument_cast == (None if counted or guarded else "pg_catalog.int8")
                and not order_by,
                "conditional aggregate arguments",
            )
            low = 0 if counted else -(1 << 63)
            return {
                "tag": "Int",
                "storage": {"kind": "my_signed_int" if guarded else "pg_int8"},
                "nullable": False,
                "domain": {
                    "kind": "int_range",
                    "min": str(low),
                    "max": str((1 << 63) - 1),
                },
                "proven_int_range": (low, (1 << 63) - 1),
            }
        if function in {"sum", "avg"} and floating:
            # A PostgreSQL float8 SUM or AVG of a finite binary64 argument,
            # uncast, NULL for an empty input.
            assert argument is not None
            _need(
                family == "postgres"
                and argument_cast is None
                and argument["storage"] == {"kind": "pg_float8"}
                and argument["domain"]
                == {"kind": "finite_float", "format": "binary64"},
                "float sum or avg casts",
            )
            return {
                "tag": "Float",
                "storage": {"kind": "pg_float8"},
                "nullable": True,
                "domain": {"kind": "finite_float", "format": "binary64"},
            }
        if function in set(SPREAD_FUNCTIONS.values()):
            # The variance or deviation of an Int or a finite binary64 Float,
            # NULL below two values (sample) or for none (population); on
            # MySQL only in its cell, of a nullable DOUBLE, uncast (S05).
            _need(
                argument is not None
                and argument_cast is None
                and (
                    family == "postgres"
                    and argument["tag"] in {"Int", "Float"}
                    and result_cast == "pg_catalog.float8"
                    or mysql_spread_cell
                    and argument["tag"] == "Float"
                    and argument["storage"] == {"kind": "my_double"}
                    and argument["nullable"] is True
                    and result_cast is None
                ),
                "stddev casts",
            )
            return {
                "tag": "Float",
                "storage": {
                    "kind": "pg_float8" if family == "postgres" else "my_double"
                },
                "nullable": True,
                "domain": {"kind": "finite_float", "format": "binary64"},
            }
        if function == "sum" and family == "mysql":
            # S02, S03: only a guarded SUM over a BIGINT (a source field, a
            # count or a guarded SUM), whose BIGINT arithmetic raises 1690
            # outside signed 64 bits, NULL for an empty input.
            assert argument is not None
            _need(
                argument["tag"] == "Int"
                and argument["storage"]
                in ({"kind": "my_bigint"}, {"kind": "my_signed_int"})
                and argument_cast is None
                and result_cast is None,
                "guarded SUM argument",
            )
            return {
                "tag": "Int",
                "storage": {"kind": "my_signed_int"},
                "nullable": True,
                "domain": {
                    "kind": "int_range",
                    "min": str(-(1 << 63)),
                    "max": str((1 << 63) - 1),
                },
                "proven_int_range": (-(1 << 63), (1 << 63) - 1),
            }
        if function == "sum":
            # Q1: an exact PostgreSQL sum narrowed to bigint by a checked CAST,
            # NULL for an empty input.
            if decimal_sum:
                assert argument is not None
                storage, domain = argument["storage"], argument["domain"]
                precision, scale = storage.get("precision"), storage.get("scale")
                _need(
                    family == "postgres"
                    and argument_cast is None
                    and storage
                    == {"kind": "pg_numeric", "precision": precision, "scale": scale}
                    and domain
                    == {"kind": "decimal", "precision": precision, "scale": scale}
                    and type(precision) is int
                    and type(scale) is int
                    and 0 <= scale <= precision <= 46
                    and result_cast == f"pg_catalog.numeric({precision + 19}, {scale})",
                    "SUM Decimal cast",
                )
                return {
                    "tag": "Decimal",
                    "storage": {
                        "kind": "pg_numeric",
                        "precision": precision + 19,
                        "scale": scale,
                    },
                    "nullable": True,
                    "domain": {
                        "kind": "decimal",
                        "precision": precision + 19,
                        "scale": scale,
                    },
                }
            _need(
                family == "postgres"
                and argument is not None
                and argument["tag"] == "Int"
                and argument_cast == result_cast == "pg_catalog.int8",
                "SUM bigint casts",
            )
            return {
                "tag": "Int",
                "storage": {"kind": "pg_int8"},
                "nullable": True,
                "domain": {
                    "kind": "int_range",
                    "min": str(-(1 << 63)),
                    "max": str((1 << 63) - 1),
                },
                "proven_int_range": (-(1 << 63), (1 << 63) - 1),
            }
        if function in {"count", "count_distinct", "count_distinct_tuple"}:
            _need(argument_cast is None, "count has no aggregate argument cast")
            return {
                "tag": "Int",
                "storage": {"kind": COUNT_STORAGE[family]},
                "nullable": False,
                "domain": {"kind": "int_range", "min": "0", "max": str(COUNT_MAX)},
                "proven_int_range": (0, COUNT_MAX),
            }
        _need(argument is not None, "an aggregate value needs its own argument")
        assert argument is not None
        if function in {"first", "last"}:
            # One row's value as it is, NULL where it is or for an empty input;
            # each key orders like a relation ORDER BY key.
            _need(
                family == "postgres"
                and argument_cast is None
                and delimiter is None
                and bool(order_by)
                and all(
                    value["tag"]
                    in {"Int", "Bool", "Text", "Decimal", "Timestamp"}
                    | {"Date", "Float", "UUID"}
                    for value, _ in order_by
                ),
                "ARRAY_AGG arguments",
            )
            return {
                key: value
                for key, value in argument.items()
                if key in {"tag", "storage", "domain", "proven_int_range"}
            } | {"nullable": argument["nullable"] is not False or not grouped}
        if function in {"median", "quantile"}:
            # The interpolated percentile of float8 images of an Int, NULL for
            # no value; a `quantile` fraction is a Float constant.
            _need(
                family == "postgres"
                and argument["tag"] == "Int"
                and argument_cast == "pg_catalog.float8"
                and (delimiter is None) is (function == "median")
                and (delimiter is None or delimiter["tag"] == "Float")
                and not order_by,
                "PERCENTILE_CONT arguments",
            )
            return {
                "tag": "Float",
                "storage": {"kind": "pg_float8"},
                "nullable": True,
                "domain": {"kind": "finite_float", "format": "binary64"},
            }
        if function == "string_agg":
            _need(
                family == "postgres"
                and argument_cast is None
                and delimiter is not None
                and argument["tag"] == delimiter["tag"] == "Text"
                and bool(order_by),
                "string_agg arguments",
            )
            return {
                "tag": "Text",
                "storage": {"kind": "pg_text"},
                "nullable": True,
                "domain": {
                    "kind": "text",
                    "max_characters": None,
                    "encoding": "UTF8",
                    "collation": "C",
                    "padding": "NO PAD",
                },
            }
        if function == "avg":
            _need(argument["tag"] == "Int", "AVG accepts the reviewed Int carrier")
            _need(
                argument_cast
                == ("pg_catalog.float8" if family == "postgres" else "DOUBLE"),
                "AVG input cast",
            )
            return {
                "tag": "Float",
                "storage": {
                    "kind": "pg_float8" if family == "postgres" else "my_double"
                },
                "nullable": True,
                "domain": {"kind": "finite_float", "format": "binary64"},
            }
        _need(argument_cast is None, "non-AVG aggregate argument cast")
        # An empty or all-null input has no extreme value, so the result is
        # nullable even over a non-null source column.
        result = {
            "tag": argument["tag"],
            "storage": argument["storage"],
            "nullable": True,
            "domain": argument["domain"],
        }
        if argument["tag"] == "Int" and "proven_int_range" in argument:
            result["proven_int_range"] = argument["proven_int_range"]
        return result

    def window_realization(function, value, default=None, literal=None):
        """This window result's own domain, derived here and not read back.

        A ranking or bucket result is the target's own signed64; a distribution
        result is its own double; a navigation or frame-sensitive result carries
        its value argument and gains only the possibility of NULL.
        """
        if function in WINDOW_RANK_FUNCTIONS:
            # A bucket result is the width the target itself returns: PostgreSQL's
            # ntile sends int4 where its ranking functions send int8.
            bucket = function == "ntile" and family == "postgres"
            storage = "pg_int4" if bucket else COUNT_STORAGE[family]
            bound = (1 << 31) - 1 if bucket else COUNT_MAX
            return {
                "tag": "Int",
                "storage": {"kind": storage},
                "nullable": False,
                "domain": {"kind": "int_range", "min": "0", "max": str(bound)},
                "proven_int_range": (0, bound),
            }
        if function in WINDOW_DISTRIBUTION_FUNCTIONS:
            return {
                "tag": "Float",
                "storage": {
                    "kind": "pg_float8" if family == "postgres" else "my_double"
                },
                "nullable": False,
                "domain": {"kind": "float64"},
            }
        _need(value is not None, "a window value result needs its own argument")
        assert value is not None
        tag = value["realization"]["tag"]
        # B1: MySQL returns a Bool value's window result as an INT, which no
        # reviewed storage describes, so no Phase66 document may publish one.
        _need(
            family != "mysql" or tag != "Bool",
            "MySQL publishes no Bool window value result in Phase66",
        )
        storage, domain = (
            value["realization"]["storage"],
            value["realization"]["domain"],
        )
        proof = None
        if tag == "Int":
            storage, domain, proof = window_integer(value, literal)
        # A navigation offset or a frame position may address no row at all, so
        # this result gains NULL over a non-null source column unless the
        # occurrence names its own default for that missing row.
        result = {
            "tag": tag,
            "storage": storage,
            "nullable": True
            if default is None
            else bool(value["realization"]["nullable"] or default),
            "domain": domain,
        }
        if proof is not None:
            result["proven_int_range"] = proof
        return result

    def window_integer(value, literal):
        """One Int value-window result's width and interval, re-derived here.

        PostgreSQL's anycompatible lag/lead default joins the width through its
        own literal type (int4, int8 beyond signed32). MySQL's result is INT
        below ten display characters of a source column or earlier window result
        (6, 11, 20 by field class) or of a d-digit default literal (d + 1), and
        BIGINT from ten. Grouped results read materialized fields; literal
        carriers retain their checked SIGNED anchor (display 21). A non-null
        default widens the interval to its least enclosure, never further.
        """
        carrier = value["realization"]
        kind = carrier["storage"]["kind"]
        domain_low = int(carrier["domain"]["min"])
        domain_high = int(carrier["domain"]["max"])
        low, high = row_interval(carrier)
        number = None
        if literal is not None and literal != "NULL":
            _need(
                re.fullmatch(r"0|[1-9][0-9]*", literal) is not None
                and int(literal) <= I64_MAX,
                "an integer window default stays a signed64 literal",
            )
            number = int(literal)
            low, high = min(low, number), max(high, number)
            domain_low, domain_high = min(domain_low, number), max(domain_high, number)
        if family == "postgres":
            _need(kind in {"pg_int2", "pg_int4", "pg_int8"}, "PostgreSQL window width")
            bits = SIGNED_BITS[kind]
            if number is not None:
                bits = max(bits, 32 if number < 1 << 31 else 64)
            result = {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"}[bits]
        else:
            origin = value.get("origin")
            fields = {"my_smallint": 6, "my_int": 11, "my_bigint": 20}
            if origin is not None and origin["role"] in {
                "aggregate_result",
                "group_key",
            }:
                display = {**fields, "my_signed_int": 20}.get(kind)
            elif value.get("literal") is not None:
                # row_parse already checked the emitted SIGNED anchor, including
                # its literal/native parameter and every unary sign.
                display = 21 if kind == "my_signed_int" else None
            else:
                reviewed = (
                    value["field"] is not None
                    and origin is None
                    or value["field"] is None
                    and origin is not None
                    and origin["role"] == "window_result"
                )
                display = fields.get(kind) if reviewed else None
            _need(display is not None, "a MySQL window value reads a reviewed carrier")
            assert display is not None
            if number is not None:
                display = max(display, len(str(number)) + 1)
            result = "my_int" if display < 10 else "my_bigint"
        bits = SIGNED_BITS[result]
        _need(
            -(1 << (bits - 1)) <= low and high <= (1 << (bits - 1)) - 1,
            "a window value interval stays inside its storage",
        )
        return (
            {"kind": result},
            {"kind": "int_range", "min": str(domain_low), "max": str(domain_high)},
            (low, high),
        )

    def row_field_realization(field):
        realization = {"tag": source_type(field)["name"], **field["representation"]}
        if realization["tag"] == "Int":
            bits = INT_BITS.get(realization["storage"]["kind"])
            _need(bits is not None, "Int source storage proof")
            assert bits is not None
            realization["proven_int_range"] = (
                -(1 << (bits - 1)),
                (1 << (bits - 1)) - 1,
            )
        return realization

    def literal_origin(value, export, terminal):
        """One literal's own origin, at the stage that actually produced it."""
        return {
            **{key: value[key] for key in ("expression", "leaf", "site", "slot")},
            "export": export,
            "terminal": terminal,
        }

    row_aggregations: dict[str, Any] = {}

    def aggregate_origin(published, origin):
        """One aggregate provenance, rebuilt from bytes with one declared owner.

        Everything but the aggregation's own reference is re-derived here; that
        one reference is read under an exact kind and must stay the single owner
        of this decoded stage, so a GLOBAL body cannot claim a second one.
        """
        declared = published["correspondence"].get("aggregate_origin") or published[
            "correspondence"
        ].get("aggregate_transport")
        _need(type(declared) is dict, "an aggregate output declares its origin")
        owner = declared.get("aggregation")
        _reference(owner)
        _need(owner["kind"] == "aggregation", "aggregation reference kind")
        key = encoded(origin["stage"]).decode()
        _need(
            row_aggregations.setdefault(key, owner) == owner,
            "one decoded aggregation stage has one owner",
        )
        return {"aggregation": owner, **origin}

    result_allocations: dict[tuple[str, str], list[dict[str, Any]]] = {}
    result_owners: dict[int, tuple[str, str]] = {}

    def result_ports(block, role, width, anchor: list[dict[str, Any]] | None = None):
        key = (encoded(block).decode(), role)
        if key in result_allocations:
            prior = result_allocations[key]
            _need(
                len(prior) == width and (anchor is None or anchor == prior),
                "result allocation drift",
            )
            return prior
        if anchor is None:
            anchor = [
                ref("result_port", row_counts["result"] + i) for i in range(width)
            ]
        _need(
            type(anchor) is list and len(anchor) == width and width > 0,
            "result allocation width",
        )
        for item in anchor:
            _reference(item)
            _need(item["kind"] == "result_port", "result allocation kind")
        start = anchor[0]["position"]
        _need(
            [item["position"] for item in anchor] == list(range(start, start + width))
            and all(item["position"] not in result_owners for item in anchor),
            "overlapping result allocation",
        )
        result_allocations[key] = anchor
        for item in anchor:
            result_owners[item["position"]] = key
        while row_counts["result"] in result_owners:
            row_counts["result"] += 1
        return anchor

    row_definition_count = [0]
    source_definition_positions = {position for position, _ in scan_definitions}

    root_first: list[Any] = [None]

    def root_first_body():
        """The lexical start of the selected definition's first body: the last
        top-level body that opens a definition of its own rather than reading
        an earlier stage, a JOIN unit or a result of its definition."""
        if root_first[0] is None:
            if not lexical or lexical[0][0]["role"] != "with":
                starts = [(0, lexical[0][0]["subject"] if lexical else None)]
            else:
                starts = [
                    (i + 1, token["subject"])
                    for i, (token, _) in enumerate(lexical)
                    if token["role"] in ("cte_body_open", "with_body")
                ]
            fresh = []
            for start, block in starts:
                if block is None or block["kind"] in ("result_boundary", "join"):
                    continue
                if block["kind"] != "select_block":
                    fresh.append(start)
                    continue
                depth = 0
                for j in range(start, len(lexical) - 1):
                    role = lexical[j][0]["role"]
                    if role == "inline_open":
                        depth += 1
                    elif role == "inline_close":
                        depth -= 1
                    elif depth == 0 and role == "from":
                        if lexical[j + 1][0]["role"] != "stage_reference":
                            fresh.append(start)
                        break
            root_first[0] = fresh[-1] if fresh else -1
        return root_first[0]

    def next_row_definition():
        while row_definition_count[0] in source_definition_positions:
            row_definition_count[0] += 1
        owner = ref("definition", row_definition_count[0])
        row_definition_count[0] += 1
        return owner

    row_window_arguments: dict[str, list[dict[str, Any]]] = {}
    row_window_uses: dict[str, list[dict[str, Any]]] = {}
    row_window_projection_count = [0]
    row_window_shape: dict[str, tuple[int, int, int]] = {}

    def window_origin(published, origin):
        """One window provenance, rebuilt from bytes with declared plan identities.

        The occurrence, its stage, its input BAG and its own result are all
        re-derived here. The plan identities it retains - one owning definition,
        one policy per occurrence, its arguments and its uses - are read under
        exact kinds and must stay unique and agree with the emitted arity, so no
        two occurrences can claim one policy, one argument or one use.
        """
        declared = published["correspondence"].get("window_origin") or published[
            "correspondence"
        ].get("window_transport")
        _need(type(declared) is dict, "a window output declares its origin")
        _keys(
            declared,
            (
                "role",
                "function",
                "selected",
                "window",
                "stage",
                "definition",
                "policy",
                "arguments",
                "uses",
                "inputs",
                "result",
            ),
        )
        definition = declared["definition"]
        _reference(definition)
        _need(definition["kind"] == "definition", "window definition kind")
        _need(
            definition == origin["definition"],
            "a window belongs to its decoded definition",
        )
        policy = declared["policy"]
        _reference(policy)
        _need(
            policy == ref("window_policy", origin["window"]["position"]),
            "window policy belongs to its occurrence",
        )
        key = encoded(origin["window"]).decode()
        arity, components, width = row_window_shape[key]
        inputs = cast(list[Any], declared["inputs"])
        _need(
            type(inputs) is list
            and len(inputs) == width
            and inputs == origin["inputs"],
            "a window reads its whole established row shape",
        )
        for item in inputs:
            _reference(item)
            _need(item["kind"] == "stage_port", "window input port kind")
        _need(
            encoded(origin["result"]) not in {encoded(item) for item in inputs},
            "a window result is never its own input",
        )
        arguments = cast(list[Any], declared["arguments"])
        uses = cast(list[Any], declared["uses"])
        _need(
            type(arguments) is list
            and len(arguments) == arity
            and arguments == row_window_arguments[key],
            "window argument denominator",
        )
        _need(
            type(uses) is list
            and len(uses) == components
            and uses == row_window_uses[key],
            "window use denominator",
        )
        for item in arguments:
            _reference(item)
            _need(item["kind"] == "window_argument", "window argument kind")
        for item in uses:
            _reference(item)
            _need(item["kind"] == "window_use", "window use kind")
        return {
            "definition": definition,
            "policy": policy,
            "arguments": arguments,
            "uses": uses,
            "inputs": inputs,
            **origin,
        }

    def row_output(
        position,
        label,
        node,
        root,
        read,
        realization,
        block,
        terminal,
        export,
        scan,
        alias,
        origin=None,
        *,
        published=None,
        bases=None,
    ):
        """Independently rebuild one published output column and compare it.

        A result body publishes the columns of the closed projection it reads,
        so that projection's description is checked later against the published
        column with its result stages removed and its own counters restored.
        """
        _need(position < len(document["columns"]), "published column denominator")
        if published is None:
            published = document["columns"][position]
        counts = row_counts if bases is None else bases
        _keys(
            published,
            (
                "ordinal",
                "label",
                "logical_type",
                "nullable",
                "representation",
                "correspondence",
            ),
        )
        nullable = realization["nullable"]
        if nullable is None:
            nullable = published["nullable"]
            _need(
                nullable is True or nullable is False or nullable == "unknown",
                "computed nullability",
            )
            # A carried computed determinant keeps its producer's own proof.
            strict = root["strict"] if root is not None else read.get("proof", False)
            _need(
                nullable is not False or strict,
                "NON_NULL claimed over a nullable operand: " + label,
            )
            realization = {**realization, "nullable": nullable}
        logical = {
            "kind": "builtin",
            "name": realization["tag"],
            "parameters": {
                "precision": realization["domain"]["precision"],
                "scale": realization["domain"]["scale"],
            }
            if realization["tag"] == "Decimal"
            else None,
        }
        if node["kind"] == "result":
            assert origin is not None
            correspondence = {
                "aggregate_origin": aggregate_origin(published, origin),
                "input_port": node["port"],
                "export": export,
                "projection": ref(
                    "aggregate_projection",
                    counts["aggregate_projection"],
                ),
                "sql_symbol": position + 1,
            }
            carried = None if read is None else read.get("literal")
            if carried is not None:
                correspondence = {"literal_origin": carried["origin"], **correspondence}
            expected = {
                "ordinal": position,
                "label": label,
                "logical_type": {
                    "kind": "builtin",
                    "name": realization["tag"],
                    "parameters": {
                        "precision": realization["domain"]["precision"],
                        "scale": realization["domain"]["scale"],
                    }
                    if realization["tag"] == "Decimal"
                    else None,
                },
                "nullable": realization["nullable"],
                "representation": {
                    "storage": realization["storage"],
                    "nullable": realization["nullable"],
                    "domain": realization["domain"],
                },
                "correspondence": correspondence,
            }
            _need(encoded(published) == encoded(expected), "aggregate output published")
            return realization
        if node["kind"] == "window_result":
            assert origin is not None
            expected = {
                "ordinal": position,
                "label": label,
                "logical_type": logical,
                "nullable": realization["nullable"],
                "representation": {
                    "storage": realization["storage"],
                    "nullable": realization["nullable"],
                    "domain": realization["domain"],
                },
                "correspondence": {
                    "window_origin": window_origin(published, origin),
                    "input_port": node["port"],
                    "export": export,
                    "projection": ref("window_projection", counts["window_projection"]),
                    "sql_symbol": position + 1,
                },
            }
            _need(encoded(published) == encoded(expected), "window output published")
            return realization
        projection = ref("projection", counts["projection"])
        link = None
        if scan["kind"] in {"scan", "named"} and root is not None and "read" in root:
            correspondence_link = published["correspondence"]
            _reference(correspondence_link["input_port"])
            _need(
                correspondence_link["input_port"]["kind"] == "input_port",
                "immediate input port",
            )
            producer = correspondence_link["producer"]
            _keys(producer, ("export", "terminal"))
            _reference(producer["export"])
            _reference(producer["terminal"])
            _need(
                producer["terminal"] == read["terminal"],
                "a named read must declare the terminal it read",
            )
            link = (correspondence_link["input_port"], producer)
        correspondence: dict[str, Any] = {
            "expression": root["root"] if root is not None else None,
            "input_port": None if link is None else link[0],
            "producer": None if link is None else link[1],
            "export": export,
            "projection": projection,
            "sql_symbol": position + 1,
        }
        _need(node["kind"] == "value", "the selected body carries no column")
        assert root is not None
        if origin is not None:
            # A carried result keeps its producer's own provenance: a window
            # result travels as its window, anything else as its aggregation.
            transport = (
                {"window_transport": window_origin(published, origin)}
                if origin["role"] == "window_result"
                else {"aggregate_transport": aggregate_origin(published, origin)}
            )
            correspondence = {**transport, **correspondence}
        carried = None if read is None else read.get("literal")
        if "value" in root:
            correspondence = {
                "literal_origin": literal_origin(root["value"], export, terminal),
                **correspondence,
            }
        elif carried is not None and (read is None or read["field"] is None):
            # A value that entered as a literal keeps its OWN producing origin
            # through every later carrier, including a JOIN port that may
            # null-extend it. Becoming transportable never turns a pre-JOIN marker
            # into a post-JOIN constant.
            correspondence = {"literal_origin": carried["origin"], **correspondence}
        else:
            site = published["correspondence"]["computed_origin"]["site"]
            role = published["correspondence"]["computed_origin"]["role"]
            _reference(site)
            _need(site["kind"] == "expression_site" and role == "select", "value site")
            correspondence = {
                "computed_origin": {
                    "kind": root["kind"] if "kind" in root else "reference",
                    "expression": root["root"],
                    "site": site,
                    "role": role,
                    "stage": block,
                    "export": export,
                    "terminal": terminal,
                    "operands": root.get("operands", []),
                    "source": None
                    if read is None or read["field"] is None
                    else scanned_source(read)["selector"],
                    "field": None
                    if read is None or read["field"] is None
                    else read["field"]["ordinal"],
                    "source_port": None if read is None else read.get("source_port"),
                },
                **correspondence,
            }
        expected = {
            "ordinal": position,
            "label": label,
            "logical_type": logical,
            "nullable": realization["nullable"],
            "representation": {
                "storage": realization["storage"],
                "nullable": realization["nullable"],
                "domain": realization["domain"],
            },
            "correspondence": correspondence,
        }
        _need(
            encoded(published) == encoded(expected),
            "row output correspondence: " + label,
        )
        return realization

    def row_select(block, final, cte_terminals, inline=False):
        """One stage body: parse its columns, bind its scan, then realize them.

        An inline body (Phase70 S10) is a let with capture lines nested in its
        reading body's existence read; it is never a CTE.
        """
        body_start = cursor
        take("syntax", "select", "SELECT ", block)
        parsed = []
        windows_seen: list[dict[str, Any]] = []
        _, projection_input = projection_inline_frame()
        while True:
            separator = None
            if parsed:
                separator, _ = take("syntax", "separator", ", ")
            if peek() == "collect_scope":
                # Phase71 S08: one Collect read's count and arrays, read from
                # its lateral, which follows this body's FROM.
                collect = lexical[cursor][0]["subject"]
                _need(collect["kind"] == "collect", "nested group subject kind")
                group = carrier_group("collect_scope", collect, final, len(parsed))
                _need(
                    separator is None or separator["subject"] == group["export"],
                    "separator",
                )
                parsed.append(
                    {
                        "node": {"kind": "collect", "collect": collect, "group": group},
                        "export": group["export"],
                        "label": group["label"],
                        "helper": False,
                    }
                )
                if peek() != "separator":
                    break
                continue
            if peek() == "result_carry_scope":
                port = lexical[cursor][0]["subject"]
                _need(port["kind"] == "stage_port", "nested stage input port")
                group = carrier_group(
                    "result_carry_scope",
                    port,
                    final,
                    len(parsed),
                    count_kinds=("stage_port", "export"),
                )
                _need(
                    separator is None or separator["subject"] == group["export"],
                    "nested separator",
                )
                if group["export"]["kind"] == "export":
                    begin, end = group["count_span"]
                    overlays = [
                        r
                        for r in _records(document["ranges"])
                        if r["kind"] == "expression_range"
                        and r["role"] == "reference"
                        and (r["start"], r["end"]) == (begin, end)
                    ]
                    _need(len(overlays) == 1, "one authored nested reference range")
                    reference = overlays[0]["subject"]
                    _reference(reference)
                    _need(
                        reference["kind"] == "expression"
                        and within(cause(reference), cause(block)),
                        "nested reference expression scope",
                    )
                    seen_expressions.add(reference["position"])
                    expected_ranges.append(("reference", reference, begin, end))
                parsed.append(
                    {
                        "node": {
                            "kind": "group",
                            "port": port,
                            "alias": group["scope"],
                            "carriers": group["carriers"],
                        },
                        "export": group["export"],
                        "label": group["label"],
                        "helper": False,
                    }
                )
                row_stage_ports.add(encoded(port).decode())
                if peek() != "separator":
                    break
                continue
            carrier = CARRIER_ROLES.get(peek() or "")
            if carrier is not None:
                kind, scope_role, qualifier_role, column_role = carrier
                port = lexical[cursor][0]["subject"]
                _need(port["kind"] == "stage_port", "carried port kind")
                _, carry_alias = take("identifier", scope_role, subject=port)
                qualifier, _ = take("syntax", qualifier_role, ".")
                token, name = take("identifier", column_role)
                node = {
                    "kind": kind,
                    "port": port,
                    "name": name,
                    "terminal": token["subject"],
                    "alias": carry_alias,
                    "qualifier": qualifier["subject"],
                }
                row_stage_ports.add(encoded(port).decode())
            elif peek() in (
                "aggregate_open",
                "aggregate_result_cast_open",
                "aggregate_root_open",
                "aggregate_zero_open",
                "aggregate_test_open",
                "aggregate_element_open",
                "aggregate_guard_open",
            ):
                node = {"kind": "aggregate", **aggregate_parse(block)}
            elif peek() == "window_open":
                node = {"kind": "window", **window_parse(block)}
            else:
                node = {"kind": "value", "value": row_parse(block)}
            alias_token, _ = take("syntax", "alias", " AS ")
            export = alias_token["subject"]
            # A closed projection stage may end with hidden ORDER helpers: exact
            # carries of pre-projection ports whose export is a projection-role
            # result port rather than a canonical export.
            helper = node["kind"] == "carry" and export["kind"] == "result_port"
            _need(helper or export["kind"] in {"stage_port", "export"}, "export kind")
            _, label = take("identifier", "label", None, export)
            _need(separator is None or separator["subject"] == export, "separator")
            _need(
                node["kind"] not in CARRIED_KINDS or node["qualifier"] == export,
                "carried qualifier",
            )
            parsed.append(
                {"node": node, "export": export, "label": label, "helper": helper}
            )
            if node["kind"] == "window":
                windows_seen.append(node)
            if peek() != "separator":
                break
        from_token, _ = take("syntax", "from", " FROM ")
        producer = from_token["subject"]
        scan: dict[str, Any] = {}
        if peek() == "namespace":
            item, scan_index = bind_scan(producer)
            take("identifier", "namespace", item["relation"]["namespace"], producer)
            take("syntax", "qualifier", ".", producer)
            take("identifier", "relation", item["relation"]["name"], producer)
            _need(cause(producer)["path"] == item["selector"]["module"])
            incoming = []
            for field in item["fields"]:
                realization = row_field_realization(field)
                incoming.append(
                    {
                        "name": field["column"],
                        "terminal": source_port(producer, field),
                        "source_port": source_port(producer, field),
                        "realization": realization,
                        "field": field,
                        "literal": None,
                    }
                )
            scan = {"kind": "scan", "description": item, "index": scan_index}
        elif peek() == "join_reference":
            _need(producer["kind"] == "join", "joined tail producer kind")
            _, name = take("identifier", "join_reference", subject=producer)
            source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and source_body.get("join") is True
                and source_body["block"] == producer
                and source_body is row_bodies[-1],
                "a joined tail must read its own final JOIN",
            )
            assert source_body is not None
            incoming = source_body["outgoing"]
            scan = {"kind": "join", "body": source_body}
        elif peek() == "cte_reference":
            _need(
                producer["kind"]
                in {"select_block", "result_boundary", "set_body", "values_body"},
                "named producer kind",
            )
            _, name = take("identifier", "cte_reference", subject=producer)
            source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and source_body["block"] == producer
                and source_body["projection"]
                and producer["kind"]
                == (
                    "set_body"
                    if source_body.get("set")
                    else "values_body"
                    if source_body.get("values")
                    else "result_boundary"
                    if source_body.get("result")
                    else "select_block"
                ),
                "named use must read a complete definition terminal",
            )
            assert source_body is not None
            incoming = source_body["outgoing"]
            scan = {"kind": "named", "body": source_body}
        elif peek() == "inline_open":
            _need(inline and producer["kind"] == "select_block", "inline stage use")
            take("syntax", "inline_open", "(", producer)
            source_body = row_select(producer, False, None, inline=True)
            take("syntax", "inline_close", ")", producer)
            _need(
                source_body["block"] == producer and not source_body["projection"],
                "an inline stage reads its own inline predecessor",
            )
            incoming = source_body["outgoing"]
            scan = {"kind": "stage", "body": source_body, "inline": True}
        else:
            _need(producer["kind"] == "select_block", "stage producer kind")
            _, name = take("identifier", "stage_reference", subject=producer)
            source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and (
                    source_body is row_bodies[-1]
                    or projection_input is not None
                    and source_body is projection_input.get("body")
                )
                and source_body["block"] == producer
                and not source_body["projection"],
                "stage use must read its immediately preceding stage",
            )
            assert source_body is not None
            incoming = source_body["outgoing"]
            scan = {"kind": "stage", "body": source_body}
        alias_token, _ = take("syntax", "alias", " AS ")
        binding = alias_token["subject"]
        if scan["kind"] == "join":
            _need(binding["kind"] == "join_tail", "joined tail scope binding")
            _, alias = take("identifier", "join_scope", None, binding)
            _need(alias == f"t{binding['position']}", "joined tail scope spelling")
        elif scan["kind"] == "stage":
            _need(binding == block, "stage scope binding")
            _, alias = take("identifier", "stage_scope", None, binding)
            _need(alias == f"t{block['position']}", "stage scope spelling")
        else:
            _need(binding["kind"] == "input_use", "relation scope binding")
            _, alias = take("identifier", "relation_scope", None, binding)
            _need(alias == f"s{binding['position']}", "relation scope spelling")
            scan["use"] = binding
        _need(within(cause(binding), cause(block)))
        if scan["kind"] == "stage":
            owner = scan["body"]["definition"]
        elif inline:
            _need(bool(inline_owners), "an inline let outside its reading body")
            owner = inline_owners.pop(0)
        else:
            # The inline lets this body reads are planned before it.
            body_end = next(
                (
                    i
                    for i in range(cursor, len(lexical))
                    if lexical[i][0]["role"] == "cte_body_close"
                ),
                len(lexical),
            )
            # Phase71 S08: a Collect read is a read of the selected definition
            # (D-S08-4), which is planned last; each captured let it collects
            # is planned before it, at its first body, wherever it is read.
            collect_end = body_end if body_start != root_first_body() else len(lexical)
            inline_owners.extend(
                next_row_definition()
                for i in range(cursor, len(lexical) - 1)
                if lexical[i + 1][0]["role"] == "inline_open"
                and (
                    i < body_end - 1
                    and lexical[i][0]["role"]
                    in ("exists_from", "scalar_from", "in_from")
                    or i < collect_end - 1
                    and lexical[i][0]["role"] == "from"
                    and lexical[i][0]["subject"]["kind"] == "collect"
                )
            )
            owner = next_row_definition()
        row_block[0] = block
        laterals = []
        while peek() == "collect_lateral_open":
            _need(not inline, "a Collect read's parent row")
            laterals.append(collect_lateral(alias, incoming))
            row_block[0] = block
        groups = [item["node"] for item in parsed if item["node"]["kind"] == "collect"]
        _need(
            [node["collect"] for node in groups]
            == [lateral["collect"] for lateral in laterals],
            "each nested group reads its own lateral, in order",
        )
        for node, lateral in zip(groups, laterals, strict=True):
            carriers = node["group"]["carriers"]
            _need(
                node["group"]["scope"] == f"g{lateral['use']['position']}"
                and [c["name"] for c in carriers]
                == ["n", *(f"a{j}" for j in range(len(lateral["arrays"])))]
                and [c["subject"] for c in carriers[1:]]
                == [a["child"] for a in lateral["arrays"]],
                "a nested group reads exactly its lateral's count and arrays",
            )
            node["lateral"] = lateral
            lateral["export"] = node["group"]["export"]
        determinants = []
        if peek() == "group_by":
            _need(not laterals, "a Collect read is never grouped")
            token, _ = take("syntax", "group_by", " GROUP BY ")
            _need(token["subject"]["kind"] == "aggregation", "grouping owner kind")
            while True:
                if determinants:
                    take("syntax", "group_separator", ", ")
                start = lexical[cursor][0]["start"]
                port = lexical[cursor][0]["subject"]
                _need(port["kind"] == "stage_port", "grouping input port kind")
                take("identifier", "grouping_scope", alias, port)
                qualifier, _ = take("syntax", "grouping_qualifier", ".")
                key = qualifier["subject"]
                _need(key["kind"] == "group_key", "grouping determinant kind")
                column_token, name = take("identifier", "grouping_column")
                expected_ranges.append(("grouping", key, start, column_token["end"]))
                determinants.append(
                    {
                        "key": key,
                        "port": port,
                        "name": name,
                        "terminal": column_token["subject"],
                    }
                )
                if peek() != "group_separator":
                    break
        if scan["kind"] == "scan":
            index = scan["index"]
            row_generated.append(("qualified_scan", None, "R01", ("scan", index), None))
            for field in scan["description"]["fields"]:
                row_generated.append(
                    (
                        "source_representation",
                        None,
                        "R02",
                        ("field", index, field["ordinal"]),
                        None,
                    )
                )
        elif scan["kind"] == "join":
            row_generated.append(("join_use", binding, "R07", "naming", None))
            for column in scan["body"]["header"]:
                row_generated.append(("join_terminal", column, "R07", "naming", None))
        elif scan["kind"] == "named":
            row_generated.append(("named_use", binding, "R03", "naming", None))
            for column in incoming:
                row_generated.append(
                    ("immediate_terminal", column["terminal"], "R03", "naming", None)
                )
        elif scan.get("inline"):
            row_generated.append(
                (
                    "inline_stage_use",
                    ("opaque", "inline_stage_use"),
                    "R11",
                    "naming",
                    None,
                )
            )
        else:
            row_generated.append(("stage_use", block, "R03", "naming", None))
            for column in scan["body"]["header"]:
                row_generated.append(("stage_terminal", column, "R03", "naming", None))
        for item in parsed:
            node = item["node"]
            if node["kind"] != "group":
                continue
            matches = [
                column
                for column in incoming
                if column.get("group") is not None
                and not column.get("withheld", False)
                and [c["name"] for c in column["group"]["carriers"]]
                == [c["name"] for c in node["carriers"]]
                and [c["subject"] for c in column["group"]["carriers"][1:]]
                == [c["subject"] for c in node["carriers"][1:]]
            ]
            _need(
                len(matches) == 1 and node["alias"] == alias, "nested immediate group"
            )
            read = matches[0]
            _need(
                row_port_reads.setdefault(encoded(node["port"]).decode(), read) is read,
                "nested stage port binding drift",
            )
            item["source_group"] = read["group"]
            item["source_nulled"] = bool(read.get("nulled", False))

        def is_carry(item):
            return item["node"]["kind"] == "carry" or (
                item["node"]["kind"] == "group"
                and item["export"]["kind"] == "stage_port"
            )

        helpers = sum(1 for item in parsed if item["helper"])
        _need(
            all(item["helper"] for item in parsed[len(parsed) - helpers :])
            and (helpers == 0 or not final),
            "hidden ORDER helpers trail the visible columns of a closed stage",
        )
        visible_items = parsed[: len(parsed) - helpers]
        carries = sum(is_carry(item) for item in visible_items)
        _need(
            all(is_carry(item) for item in visible_items[:carries]),
            "carried columns precede computed ones",
        )
        kinds = [
            "carry" if is_carry(item) else item["node"]["kind"]
            for item in visible_items
        ]
        aggregate_body = "group_key" in kinds or "aggregate" in kinds
        result_body = "result" in kinds
        _need(
            not (aggregate_body and result_body)
            and not (aggregate_body and carries)
            and not (result_body and carries)
            and (
                not result_body
                or set(kinds)
                <= ({"result", "value"} if family == "postgres" else {"result"})
            )
            and (not aggregate_body or set(kinds) <= {"group_key", "aggregate"})
            and kinds.count("group_key") == len(determinants)
            and (aggregate_body or not determinants),
            "one aggregation stage publishes only its determinants and results",
        )
        if aggregate_body:
            _need(
                kinds[: len(determinants)] == ["group_key"] * len(determinants)
                and kinds.count("aggregate") > 0,
                "determinants precede occurrences and an aggregation has one",
            )
        mode = "grouped" if determinants else "global"
        empty_input = "no_groups" if determinants else "one_global_row"
        projection_body = carries == 0 and not aggregate_body
        window_definitions = window_clause_parse()
        window_declared = {
            item["symbol"]: item["specification"] for item in window_definitions
        }
        referenced = {
            node["specification"]["reference"]
            for node in windows_seen
            if "reference" in node["specification"]
        }
        # A named use may only read a definition this body actually declared, and
        # a declaration that nothing uses is never emitted.
        _need(referenced <= set(window_declared), "window reference outside its clause")
        _need(set(window_declared) <= referenced, "unused generated window definition")
        outgoing, columns, deferred = [], [], []
        if aggregate_body:
            row_generated.append(
                (
                    "aggregation",
                    None,
                    "R12",
                    [
                        i
                        for i in statements
                        if premises[i]["key"] == "operator_environment"
                    ],
                    None,
                )
            )
        projection_terminals = (
            result_ports(block, "projection", len(parsed), cte_terminals)
            if projection_body
            else None
        )
        carriers_header = {}
        for position, item in enumerate(parsed):
            node, export, label = item["node"], item["export"], item["label"]
            _need(final or label == f"c{position}", "stage column label")
            if projection_body:
                assert projection_terminals is not None
                terminal = projection_terminals[position]
            else:
                terminal = export
            if node["kind"] == "group":
                carriers = node["carriers"]
                group = item["source_group"]
                _need(
                    (export["kind"] == "export") is projection_body,
                    "nested stage output kind",
                )
                _need(
                    cte_terminals is None or cte_terminals[position] == terminal,
                    "declared nested stage terminal",
                )
                row_generated.append(("carry_projection", export, "R05", [], None))
                if final:
                    collect_output(
                        position,
                        {"export": export, "carriers": carriers},
                        group["lateral"],
                        container_nullable=item["source_nulled"],
                    )
                else:
                    carriers_header[position] = [c["subject"] for c in carriers[1:]]
                renamed = {
                    **group,
                    "carriers": [
                        {"subject": c["subject"], "name": c["label"]} for c in carriers
                    ],
                }
                outgoing.append(
                    {
                        "name": f"c{position}",
                        "terminal": terminal,
                        "source_port": None,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "origin": None,
                        "helper": False,
                        "strict": False,
                        "proof": False,
                        "nulled": item["source_nulled"],
                        "group": renamed,
                    }
                )
                columns.append(
                    {
                        "label": label,
                        "export": export,
                        "terminal": terminal,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "root": None,
                        "position": position,
                        "origin": None,
                        "group": renamed,
                    }
                )
                if projection_body:
                    _need(
                        encoded(group["collect"]).decode() in collect_bindings,
                        "carried collection has no actual lateral",
                    )
                    carried_collection_exports.append((group["collect"], export))
                    row_counts["projection"] += 1
                continue
            if node["kind"] == "collect":
                _need(projection_body, "a nested group is a projection column")
                lateral = node["lateral"]
                requirements = list(lateral["requirements"])
                requirements[1] = ("collect_count", export, "R27", [], None)
                row_generated.extend(requirements)
                if cte_terminals is not None:
                    _need(cte_terminals[position] == terminal, "declared terminal")
                carriers = node["group"]["carriers"]
                if final:
                    collect_output(
                        position, {"export": export, "carriers": carriers}, lateral
                    )
                else:
                    carriers_header[position] = [c["subject"] for c in carriers[1:]]
                    deferred.append(("collect", position, lateral))
                group = {
                    "collect": node["collect"],
                    "lateral": lateral,
                    "carriers": [
                        {"subject": c["subject"], "name": c["label"]} for c in carriers
                    ],
                }
                # A nested group is no scalar projection of its body.
                outgoing.append(
                    {
                        "name": f"c{position}",
                        "terminal": terminal,
                        "source_port": None,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "origin": None,
                        "helper": False,
                        "strict": False,
                        "proof": False,
                        "group": group,
                    }
                )
                columns.append(
                    {
                        "label": label,
                        "export": export,
                        "terminal": terminal,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "root": None,
                        "position": position,
                        "origin": None,
                        "group": group,
                    }
                )
                continue
            origin = None
            if node["kind"] in CARRIED_KINDS:
                if node["kind"] == "carry" and not item["helper"]:
                    _need(position < len(incoming), "carried column beyond the scan")
                    read = incoming[position]
                else:
                    matches = [
                        c
                        for c in incoming
                        if c["name"] == node["name"]
                        and c["terminal"] == node["terminal"]
                    ]
                    _need(len(matches) == 1, "carried column outside the stage scope")
                    read = matches[0]
                _need(
                    node["alias"] == alias
                    and node["name"] == read["name"]
                    and node["terminal"] == read["terminal"],
                    "carried column is not the immediate pass-through",
                )
                key = encoded(node["port"]).decode()
                _need(
                    row_port_reads.setdefault(key, read) is read,
                    "carried port binding drift",
                )
                realization, field = read["realization"], read["field"]
                literal = read.get("literal")
                origin = read.get("origin")
                root = None
                if node["kind"] == "carry":
                    row_generated.append(("carry_projection", export, "R05", [], None))
                elif node["kind"] == "group_key":
                    bound = determinants[position]
                    _need(
                        bound["port"] == node["port"]
                        and bound["name"] == node["name"]
                        and bound["terminal"] == node["terminal"],
                        "GROUP BY must bind this determinant's own input value",
                    )
                    _need(
                        realization["tag"] in GROUPING_TAGS
                        and (
                            realization["tag"] != "Bool"
                            or realization["domain"]["kind"] == "bool01"
                        )
                        and (
                            realization["tag"] != "Text"
                            or all(
                                realization["domain"].get(k) is not None
                                for k in ("encoding", "collation", "padding")
                            )
                        )
                        and (
                            realization["tag"] != "Decimal"
                            or all(
                                realization["domain"].get(k) is not None
                                for k in ("precision", "scale")
                            )
                        )
                        and (realization["tag"] != "Float" or _float_key(realization)),
                        "group determinant comparison domain",
                    )
                    origin = {
                        "role": "group_key",
                        "mode": mode,
                        "empty_input": empty_input,
                        "stage": block,
                        "function": None,
                        "determinant": bound["key"],
                        "aggregate": None,
                        "arguments": [],
                        "inputs": [read["terminal"]],
                        "result": export,
                    }
                    row_generated.append(
                        (
                            "group_key",
                            bound["key"],
                            "R12",
                            [
                                i
                                for i in statements
                                if premises[i]["key"] == "operator_environment"
                            ],
                            None,
                        )
                    )
                elif node["kind"] == "window_result":
                    row_window_projection_count[0] += 1
                    _need(
                        origin is not None and origin["role"] == "window_result",
                        "a window projection reads an established window result",
                    )
                    row_generated.append(
                        ("window_result_projection", None, "R17", [], None)
                    )
                else:
                    _need(origin is not None, "a result column reads a result port")
                    row_generated.append(
                        (
                            "result_projection",
                            ref(
                                "aggregate_projection",
                                row_counts["aggregate_projection"],
                            ),
                            "R12",
                            [],
                            None,
                        )
                    )
            elif node["kind"] == "aggregate":
                requirement = len(row_generated)
                row_generated.append(
                    (
                        "aggregate",
                        node["aggregate"],
                        "R13",
                        [
                            i
                            for i in statements
                            if premises[i]["key"] == "operator_environment"
                        ],
                        None
                        if node["result_cast"] is None
                        else [{"overflow": TARGET_CHECKED}],
                    )
                )
                argument = None
                if node["argument"] is not None:
                    argument = row_resolve(
                        node["argument"], incoming, alias, node["aggregate"]
                    )
                    if node["function"] == "string_agg":
                        _need(
                            "read" in argument and argument["tag"] == "Text",
                            "string_agg value carrier",
                        )
                    elif node["function"] in {"first", "last"}:
                        _need("read" in argument, "first or last value carrier")
                    else:
                        # One established field, or one row expression that
                        # reads a row, lowered as a LET would be.
                        _need(
                            "read" in argument
                            or bool(parsed_terminals(node["argument"])),
                            "an aggregate argument is one direct established field",
                        )
                        _need(
                            argument["tag"] == "Int"
                            or (
                                family == "postgres"
                                and node["function"] == "sum"
                                and argument["tag"] == "Decimal"
                            )
                            or (
                                node["function"]
                                in {"sum", "avg", *SPREAD_FUNCTIONS.values()}
                                and family == "postgres"
                                and argument["tag"] == "Float"
                            )
                            or (
                                node["function"] in SPREAD_FUNCTIONS.values()
                                and mysql_spread_cell
                                and argument["tag"] == "Float"
                            )
                            or (
                                node["function"]
                                in {"count", "count_distinct", "count_distinct_tuple"}
                                and argument["tag"] in {"Timestamp", "Date", "UUID"}
                            )
                            or (
                                node["function"] in {"min", "max"}
                                and argument["tag"] in {"Timestamp", "Date"}
                            )
                            or (
                                node["function"]
                                in {
                                    "count",
                                    "count_distinct",
                                    "count_distinct_tuple",
                                    "min",
                                    "max",
                                }
                                and argument["tag"] == "Decimal"
                            )
                            or (
                                # MySQL deduplicates no Float: -0.0 and 0.0
                                # stayed apart beside a wide key.
                                node["function"]
                                in {
                                    "count",
                                    "count_distinct",
                                    "count_distinct_tuple",
                                    "min",
                                    "max",
                                }
                                and argument["tag"] == "Float"
                                and (
                                    family == "postgres"
                                    or node["function"]
                                    not in {"count_distinct", "count_distinct_tuple"}
                                )
                            )
                            or (
                                node["function"]
                                in {"count", "count_distinct", "count_distinct_tuple"}
                                and argument["tag"] in {"Text", "Bool"}
                            )
                            or (
                                node["function"]
                                in {"filtered_count", "group_any", "group_all"}
                                and family == "postgres"
                                and argument["tag"] == "Bool"
                            ),
                            "aggregate argument carrier",
                        )
                delimiter = (
                    None
                    if node["delimiter"] is None
                    else row_resolve(
                        node["delimiter"], incoming, alias, node["aggregate"]
                    )
                )
                extras = [
                    row_resolve(value, incoming, alias, node["aggregate"])
                    for value in node["extra_arguments"]
                ]
                for member in extras:
                    # A field of a distinct-tuple count, as count_distinct(x).
                    _need(
                        "read" in member
                        and (
                            member["tag"] in {"Int", "Timestamp", "Date", "UUID"}
                            or family == "postgres"
                            and member["tag"] in {"Float", "Decimal", "Text", "Bool"}
                        ),
                        "count_distinct_tuple field carrier",
                    )
                order_by = [
                    (
                        row_resolve(value, incoming, alias, node["aggregate"]),
                        descending,
                    )
                    for value, descending in node["order_by"]
                ]
                realization = aggregate_realization(
                    node["function"],
                    argument,
                    node["argument_cast"],
                    delimiter,
                    order_by,
                    node["result_cast"],
                    grouped=mode == "grouped",
                )
                if node["function"] in {"sum", "avg", *SPREAD_FUNCTIONS.values()}:
                    # Evidence follows the function and argument tag: only a
                    # Float sum, average, variance or deviation rests on the
                    # target's overflow check.
                    assert argument is not None
                    if argument["tag"] == "Float":
                        row_generated[requirement] = (
                            *row_generated[requirement][:4],
                            [{"overflow": TARGET_CHECKED_BINARY64}],
                        )
                    elif node["function"] == "sum" and argument["tag"] == "Decimal":
                        row_generated[requirement] = (
                            *row_generated[requirement][:4],
                            [{"overflow": "target_checked_decimal_overflow"}],
                        )
                    elif node["function"] == "sum" and family == "mysql":
                        # S02: the guard's checked BIGINT arithmetic, uncast.
                        row_generated[requirement] = (
                            *row_generated[requirement][:4],
                            [{"overflow": TARGET_CHECKED}],
                        )
                    elif node["function"] in SPREAD_FUNCTIONS.values():
                        row_generated[requirement] = (
                            *row_generated[requirement][:4],
                            None,
                        )
                if node["function"] == "filtered_sum" and family == "mysql":
                    # S03: the guard's checked BIGINT arithmetic, uncast.
                    row_generated[requirement] = (
                        *row_generated[requirement][:4],
                        [{"overflow": TARGET_CHECKED}],
                    )
                read, field, literal, root = None, None, None, None
                origin = {
                    "role": "aggregate_result",
                    "mode": mode,
                    "empty_input": empty_input,
                    "stage": block,
                    "function": node["function"],
                    "determinant": None,
                    "aggregate": node["aggregate"],
                    "arguments": [
                        value["root"]
                        for value in (argument, delimiter, *extras)
                        if value is not None
                    ],
                    # Every read of each input value tree, in source order.
                    "inputs": [
                        terminal
                        for value in (
                            node["argument"],
                            node["delimiter"],
                            *node["extra_arguments"],
                            *(item for item, _ in node["order_by"]),
                        )
                        if value is not None
                        for terminal in parsed_terminals(value)
                    ]
                    or [column["terminal"] for column in incoming],
                    "result": export,
                }
            elif node["kind"] == "window":
                function = WINDOW_SPELLINGS[node["spelling"]]
                specification = node["specification"]
                if "reference" in specification:
                    resolved = window_declared.get(specification["reference"])
                    _need(
                        resolved is not None,
                        "a named window use reads its own declaration",
                    )
                    assert resolved is not None
                    specification = resolved
                operators = [
                    i
                    for i in statements
                    if premises[i]["key"] == "operator_environment"
                ]
                # R14 owns the computation and its comparison domains, R15 owns the
                # realized specification, so each structure keeps its own cause.
                row_generated.append(
                    ("window_computation", None, "R14", operators, None)
                )
                row_generated.append(("window_specification", None, "R15", [], None))
                # R15-INT-OFFSET-V1: a finite offset is an exact signed64 count or
                # distance, and a RANGE one also owns its threshold arithmetic.
                offsets = []
                frame = specification["frame"]
                for bound in () if frame is None else (frame["start"], frame["end"]):
                    head, _, tail = bound.partition(" ")
                    if head.isdigit():
                        _need(
                            re.fullmatch(r"0|[1-9][0-9]*", head) is not None
                            and tail in {"PRECEDING", "FOLLOWING"}
                            and int(head) <= I64_MAX,
                            "a finite frame offset stays inside signed64",
                        )
                        offsets.append((tail, int(head)))
                if offsets and frame is not None:
                    row_generated.append(
                        ("window_frame_offset_domain", None, "R15", [], None)
                    )
                    if frame["unit"] == "range":
                        row_generated.append(
                            ("window_range_arithmetic", None, "R15", operators, None)
                        )
                for _binding in specification["partitions"]:
                    row_generated.append(
                        ("window_partition_comparison", None, "R14", [], None)
                    )
                for _item in specification["orders"]:
                    row_generated.append(
                        ("window_order_comparison", None, "R14", [], None)
                    )

                def window_input(binding):
                    """The one established input column this component reads."""
                    _need(binding["alias"] == alias, "window component scope")
                    matched = [
                        column
                        for column in incoming
                        if column["name"] == binding["name"]
                    ]
                    _need(
                        len(matched) == 1,
                        "a window component reads one established input column",
                    )
                    return matched[0]

                for binding in (
                    *specification["partitions"],
                    *specification["orders"],
                ):
                    window_input(binding)
                if offsets and frame is not None and frame["unit"] == "range":
                    _need(
                        len(specification["orders"]) == 1,
                        "an offset RANGE keeps one ORDER key",
                    )
                    key = specification["orders"][0]
                    _need(
                        range_thresholds_exact(
                            window_input(key)["realization"], key["direction"], offsets
                        ),
                        "every RANGE threshold of the key domain stays inside signed64",
                    )
                ports = [
                    window_input(item)
                    for item in node["arguments"]
                    if item["kind"] == "port"
                ]
                value = ports[0] if ports else None
                default = literal = None
                if (
                    function in WINDOW_NAVIGATION_FUNCTIONS
                    and len(node["arguments"]) == 3
                ):
                    third = node["arguments"][2]
                    if third["kind"] == "port":
                        default = window_input(third)["realization"]["nullable"]
                    else:
                        # A NULL default is itself returned for a missing row.
                        literal = third["value"]
                        default = literal == "NULL"
                realization = window_realization(function, value, default, literal)
                read, field, literal, root = None, None, None, None
                origin = {
                    "role": "window_result",
                    "function": function,
                    "selected": True,
                    "window": node["window"],
                    "stage": block,
                    "definition": owner,
                    "inputs": [
                        item["node"]["port"] for item in parsed[: len(incoming)]
                    ],
                    "result": export,
                }
                window_key = encoded(node["window"]).decode()
                _need(window_key not in row_window_shape, "duplicate window occurrence")
                argument_base = sum(
                    len(items) for items in row_window_arguments.values()
                )
                row_window_arguments[window_key] = [
                    ref("window_argument", argument_base + i)
                    for i in range(len(node["arguments"]))
                ]
                # Ranking/distribution calls without a scalar read retain one
                # relation-input dependency; value calls retain their read(s).
                use_count = (
                    max(1, len(ports))
                    + len(specification["partitions"])
                    + len(specification["orders"])
                )
                use_base = sum(len(items) for items in row_window_uses.values())
                row_window_uses[window_key] = [
                    ref("window_use", use_base + i) for i in range(use_count)
                ]
                row_window_shape[window_key] = (
                    len(node["arguments"]),
                    use_count,
                    len(incoming),
                )
            else:
                row_generated.append(("computed_projection", export, "R05", [], None))
                resolved = row_resolve(node["value"], incoming, alias, export)
                realization = {
                    k: resolved[k] for k in ("tag", "storage", "nullable", "domain")
                }
                if "proven_int_range" in resolved:
                    realization["proven_int_range"] = resolved["proven_int_range"]
                read = resolved.get("read")
                field = None if read is None else read["field"]
                origin = None if read is None else read.get("origin")
                if "value" in resolved:
                    literal = {
                        **resolved["value"],
                        "origin": literal_origin(resolved["value"], export, terminal),
                    }
                else:
                    # A reference keeps whatever its own carrier holds, so a literal
                    # stays a literal and a field read stays a field read.
                    literal = None if read is None else read.get("literal")
                root = resolved
            if cte_terminals is not None:
                _need(cte_terminals[position] == terminal, "declared stage terminal")
            if final:
                realization = row_output(
                    position,
                    label,
                    node,
                    root,
                    read,
                    realization,
                    block,
                    terminal,
                    export,
                    scan,
                    alias,
                    origin,
                )
            elif projection_body and not item["helper"]:
                deferred.append(
                    (
                        position,
                        node,
                        root,
                        read,
                        realization,
                        block,
                        terminal,
                        export,
                        scan,
                        alias,
                        origin,
                        dict(row_counts),
                    )
                )
            if projection_body and not item["helper"]:
                counter = {
                    "window_result": "window_projection",
                    "result": "aggregate_projection",
                }.get(node["kind"], "projection")
                row_counts[counter] += 1
            outgoing.append(
                {
                    "name": f"c{position}",
                    "terminal": terminal,
                    "source_port": None if read is None else read.get("source_port"),
                    "realization": realization,
                    "field": field,
                    "literal": literal,
                    "origin": origin,
                    "helper": item["helper"],
                    "strict": (
                        realization["nullable"] is False
                        if root is None
                        else root.get("strict", realization["nullable"] is False)
                    ),
                    # A carried computed value keeps its producer's own non-null
                    # proof; only a later NON_NULL claim may consume it.
                    "proof": (
                        root.get("proof", False)
                        if root is not None
                        else read is not None
                        and node["kind"] in CARRIED_KINDS
                        and read.get("proof", False)
                    ),
                }
            )
            columns.append(
                {
                    "label": label,
                    "export": export,
                    "terminal": terminal,
                    "realization": realization,
                    "field": field,
                    "literal": literal,
                    "root": root,
                    "position": position,
                    "origin": origin,
                }
            )
        if peek() in {"where", "satisfying"}:
            satisfying = peek() == "satisfying"
            where_token, _ = take("syntax", peek(), " WHERE ")
            predicate = where_token["subject"]
            _need(predicate["kind"] == "filter", "filter root kind")
            _need(projection_body is False, "a filter body carries its rows")
            _need(not aggregate_body, "a filter is its own stage, not the grouping")
            row_generated.append(
                (
                    "satisfying_root" if satisfying else "predicate_root",
                    predicate,
                    "R12" if satisfying else "R06",
                    [
                        i
                        for i in statements
                        if premises[i]["key"] == "operator_environment"
                    ],
                    None,
                )
            )
            specialized[0] = satisfying
            if not inline:
                capture_frames.append({"alias": alias, "incoming": incoming})
            outer_having = having_context[0]
            having_context[0] = (predicate, owner) if satisfying else None
            predicate_start = lexical[cursor][0]["start"]
            parsed_predicate = row_parse(block)
            if satisfying:
                root_reference = node_expression(parsed_predicate)
                if root_reference is not None and not within(
                    cause(root_reference), cause(predicate)
                ):
                    having_uses.append(
                        (root_reference, (predicate, owner), predicate, 0, ())
                    )
                having_ranges.append(
                    (predicate_start, lexical[cursor - 1][0]["end"], predicate, owner)
                )
            # An inline let's own filters are planned before its reader's.
            row_filters.append(predicate)
            root = row_resolve(parsed_predicate, incoming, alias, predicate)
            having_context[0] = outer_having
            if not inline:
                capture_frames.pop()
            specialized[0] = False
            _need(
                root["tag"] == "Bool" and root["domain"]["kind"] == "bool01",
                "predicate root is not a Boolean value",
            )
            _need(carries == len(incoming), "a filter body must carry every column")
            if satisfying:
                # Only an already-computed aggregate stage value can be filtered
                # after grouping; a raw input or row LET value cannot reach here.
                _need(
                    all(column.get("origin") is not None for column in incoming),
                    "satisfying reads only established aggregate stage results",
                )
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        body = {
            "block": block,
            "columns": columns,
            "outgoing": outgoing,
            "projection": projection_body,
            "definition": owner,
            "final": final,
            "scan": scan,
            "header": cte_terminals,
            "deferred": deferred,
            "helpers": helpers,
            "carriers": carriers_header,
        }
        row_bodies.append(body)
        _need(
            sum(len(c["group"]["carriers"]) if c.get("group") else 1 for c in columns)
            <= limits["columns"],
            "physical body width",
        )
        return body

    def result_select(block, final, cte_terminals, inline=False):
        """One result body: DISTINCT, the carried visible tuple, ORDER BY, LIMIT.

        The stage law is re-derived from the token order alone: the body reads
        its own closed projection, DISTINCT precedes the columns, ORDER BY
        follows the scan and LIMIT closes the body; every ORDER key is a quoted
        carried column of the stage alias, never an ordinal or a label, and no
        NULLS spelling exists. Result ports are counted independently from the
        projection width, so a terminal cannot silently skip a boundary.
        """
        _need(block["kind"] == "result_boundary", "result body scope")
        take("syntax", "select", "SELECT ", block)
        distinct = None
        if peek() == "distinct":
            token, _ = take("syntax", "distinct", "DISTINCT ")
            distinct = token["subject"]
            _need(distinct["kind"] == "distinct", "DISTINCT subject kind")
        parsed = []
        while True:
            separator = None
            if parsed:
                separator, _ = take("syntax", "separator", ", ")
            if following("result_carry_scope", "qualifier"):
                # Phase71 S08: a carried nested group, its count then arrays.
                group = result_group(final, len(parsed))
                _need(
                    separator is None or separator["subject"] == group["export"],
                    "separator",
                )
                parsed.append(group)
                if peek() != "separator" or following("separator", "ordinal_window"):
                    break
                continue
            scope_token, carry_alias = take("identifier", "result_carry_scope")
            projection_port = scope_token["subject"]
            _need(projection_port["kind"] == "result_port", "result carry port kind")
            qualifier, _ = take("syntax", "result_carry_qualifier", ".")
            export = qualifier["subject"]
            _need(export["kind"] == "export", "result carry export kind")
            column_token, name = take("identifier", "result_carry_column")
            _need(
                column_token["subject"] == projection_port,
                "a result column reads exactly its own projection port",
            )
            alias_token, _ = take("syntax", "alias", " AS ")
            _need(alias_token["subject"] == export, "result column alias subject")
            _, label = take("identifier", "label", None, export)
            _need(separator is None or separator["subject"] == export, "separator")
            _need(final or label == f"c{len(parsed)}", "result column label")
            parsed.append(
                {
                    "port": projection_port,
                    "export": export,
                    "name": name,
                    "label": label,
                    "alias": carry_alias,
                }
            )
            if peek() != "separator" or following("separator", "ordinal_window"):
                break
        ordinal = None
        if following("separator", "ordinal_window"):
            # Phase71 S08: a collected terminal's private ordinal column.
            separator, _ = take("syntax", "separator", ", ")
            ordinal = ordinal_parse()
            _need(separator["subject"] == ordinal["order"], "ordinal separator")
        from_token, _ = take("syntax", "from", " FROM ")
        producer = from_token["subject"]
        _need(producer["kind"] == "select_block", "result producer kind")
        inline_source = peek() == "inline_open"
        if inline_source:
            _need(inline)
            take("syntax", "inline_open", "(", producer)
            source_body = row_select(producer, False, None, inline=True)
            take("syntax", "inline_close", ")", producer)
        else:
            _, name = take("identifier", "stage_reference", subject=producer)
            source_body = row_ctes.get(name)
        _need(
            source_body is not None
            and source_body["block"] == producer
            and source_body["projection"]
            and not source_body["final"]
            and (inline_source or source_body is row_bodies[-1]),
            "a result body reads its own immediately preceding closed projection",
        )
        assert source_body is not None
        alias_token, _ = take("syntax", "alias", " AS ")
        _need(alias_token["subject"] == block, "result scope binding")
        _, alias = take("identifier", "result_scope", None, block)
        _need(alias == f"t{block['position']}", "result scope spelling")
        incoming = source_body["outgoing"]
        visible = [column for column in incoming if not column["helper"]]
        _need(
            len(parsed) == len(visible)
            and all(
                item["alias"] == alias
                and item["name"] == column["name"]
                and item["port"] == column["terminal"]
                and (item.get("carriers") is None) == (column.get("group") is None)
                and (
                    item.get("carriers") is None
                    or [c["name"] for c in item["carriers"]]
                    == [c["name"] for c in column["group"]["carriers"]]
                    and [c["subject"] for c in item["carriers"]]
                    == [c["subject"] for c in column["group"]["carriers"]]
                )
                for item, column in zip(parsed, visible, strict=True)
            ),
            "the result tuple is exactly the visible projection, in order",
        )
        _need(
            distinct is None or all(c.get("group") is None for c in visible),
            "a DISTINCT body never compares a nested group",
        )
        width = len(incoming)
        encoding = [i for i in statements if premises[i]["key"] == "client_encoding"]
        order_items = []
        order_ref = None
        if peek() == "order_by":
            token, _ = take("syntax", "order_by", " ORDER BY ")
            order_ref = token["subject"]
            _need(order_ref["kind"] == "relation_order", "ORDER BY subject kind")
            while True:
                if order_items:
                    separator, _ = take("syntax", "order_separator", ", ")
                start = lexical[cursor][0]["start"]
                scope_token, scope_alias = take("identifier", "order_scope")
                port = scope_token["subject"]
                _need(
                    scope_alias == alias and port["kind"] == "result_port",
                    "an ORDER key reads the result scope through a result port",
                )
                qualifier, _ = take("syntax", "order_qualifier", ".")
                item = qualifier["subject"]
                _need(item["kind"] == "order_item", "ORDER item subject kind")
                _need(
                    not order_items
                    or (separator is not None and separator["subject"] == item),
                    "ORDER separator subject",
                )
                column_token, column_name = take("identifier", "order_column")
                matches = [
                    column
                    for column in incoming
                    if column["name"] == column_name
                    and column["terminal"] == column_token["subject"]
                ]
                _need(len(matches) == 1, "an ORDER key is one established column")
                read = matches[0]
                _need(
                    read.get("group") is None
                    and (
                        read["realization"]["tag"] in ("Int", "Bool", "Text", "Decimal")
                        or _temporal_carrier(read["realization"], family)
                        # A finite Float orders by real value on both targets,
                        # a PostgreSQL distribution result too (E6).
                        or read["realization"]["tag"] == "Float"
                        and read["realization"]["storage"]
                        == {"kind": FLOAT_STORAGE[family]}
                        and read["realization"]["domain"] == FINITE_FLOAT
                        or family == "postgres"
                        and _pg_float_key(read["realization"])
                        or read["realization"]["tag"] == "UUID"
                        and read["realization"]["storage"]
                        == {
                            "kind": "pg_uuid"
                            if family == "postgres"
                            else "my_uuid_bytes"
                        },
                    ),
                    "relation ORDER comparison domain",
                )
                _need(
                    distinct is None or not read["helper"],
                    "DISTINCT ORDER keys are visible quotient columns",
                )
                direction_token, direction = take("syntax", "order_direction")
                _need(
                    direction in {" ASC", " DESC"}
                    and direction_token["subject"] == item,
                    "ORDER direction spelling",
                )
                expected_ranges.append(
                    ("order_item", item, start, direction_token["end"])
                )
                order_items.append(
                    {
                        "item": item,
                        "port": port,
                        "read": read,
                        "direction": direction.strip().lower(),
                    }
                )
                if peek() != "order_separator":
                    break
        limit = None
        if peek() == "limit":
            token, _ = take("syntax", "limit", " LIMIT ")
            limit_ref = token["subject"]
            _need(limit_ref["kind"] == "result_limit", "LIMIT subject kind")
            _, text = take("literal", "limit_value", None, limit_ref)
            _need(re.fullmatch(r"0|[1-9][0-9]*", text) is not None, "LIMIT spelling")
            limit = {"limit": limit_ref, "value": int(text)}
        if ordinal is not None:
            _need(
                distinct is None
                and not final
                and ordinal["name"] == f"c{len(parsed)}"
                and ordinal_restates(
                    ordinal,
                    {"order_ref": order_ref, "order_items": order_items},
                    alias,
                    lambda entry: entry["read"]["name"],
                ),
                "a collected terminal's ordinal restates its ORDER",
            )
        # Independent result-port accounting: every boundary consumes its inputs
        # and re-publishes the visible outputs; the terminal is the last output.
        stage_count = sum(
            (distinct is not None, order_ref is not None, limit is not None)
        )
        _need(stage_count > 0, "result boundary chain")
        total_width = width + len(visible) + (stage_count - 1) * 2 * len(visible)
        anchor = cte_terminals
        if anchor is None and final:
            anchor = [
                column["correspondence"]["result_origin"]["terminal"]
                for column in document["columns"]
            ]
        if anchor is not None:
            _need(len(anchor) == len(visible), "result terminal width")
            for port in anchor:
                _reference(port)
            cursor_position = anchor[0]["position"] - (total_width - len(visible))
            _need(cursor_position >= 0, "result boundary span")
        else:
            prior = result_allocations.get((encoded(block).decode(), "boundary_inputs"))
            cursor_position = (
                row_counts["result"] if prior is None else prior[0]["position"]
            )
        stages = []
        boundary_position = block["position"]
        for present, kind in (
            (distinct is not None, "distinct"),
            (order_ref is not None, "relation_ordering"),
            (limit is not None, "limit"),
        ):
            if not present:
                continue
            inputs = [ref("result_port", cursor_position + i) for i in range(width)]
            outputs = [
                ref("result_port", cursor_position + width + i)
                for i in range(len(visible))
            ]
            boundary_ref = ref("result_boundary", boundary_position)
            result_ports(boundary_ref, "boundary_inputs", len(inputs), inputs)
            result_ports(boundary_ref, "boundary_outputs", len(outputs), outputs)
            stages.append(
                {
                    "kind": kind,
                    "boundary": ref("result_boundary", boundary_position),
                    "inputs": inputs,
                    "outputs": outputs,
                }
            )
            cursor_position += width + len(visible)
            width = len(visible)
            boundary_position += 1
        _need(stages and stages[0]["boundary"] == block, "result boundary chain")
        for entry in order_items:
            order_stage = [
                stage for stage in stages if stage["kind"] == "relation_ordering"
            ]
            _need(
                entry["port"] in order_stage[0]["inputs"],
                "an ORDER key binds an input port of its own boundary",
            )
        terminals = stages[-1]["outputs"]
        if anchor is not None:
            _need(anchor == terminals, "declared result terminals")
        quotient_base = row_counts["quotient_field"]
        if distinct is not None:
            row_counts["quotient_field"] += len(visible)
        if inline_source:
            row_generated.append(
                (
                    "inline_stage_use",
                    ("opaque", "inline_stage_use"),
                    "R11",
                    "naming",
                    None,
                )
            )
        else:
            row_generated.append(("stage_use", producer, "R03", "naming", None))
            row_generated.extend(
                ("stage_terminal", column, "R03", "naming", None)
                for column in source_body["header"]
            )
        if distinct is not None:
            _need(
                all(
                    column["realization"]["tag"] in GROUPING_TAGS
                    and (
                        column["realization"]["tag"] != "Float"
                        or _pg_float_key(column["realization"])
                    )
                    for column in visible
                ),
                "DISTINCT comparison domain",
            )
            row_generated.append(
                ("distinct_quotient", distinct, "R18", [], {"fields": len(visible)})
            )
            for i, column in enumerate(visible):
                row_generated.append(
                    (
                        "quotient_field_comparison",
                        ref("quotient_field", quotient_base + i),
                        "R18",
                        encoding if column["realization"]["tag"] == "Text" else [],
                        None,
                    )
                )
        if order_ref is not None:
            row_generated.append(
                (
                    "relation_ordering",
                    order_ref,
                    "R19",
                    [],
                    None if inline else ("result", {"items": len(order_items)}),
                )
            )
            for entry in order_items:
                evidence = (
                    None
                    if inline
                    else (
                        "result",
                        {
                            "direction": entry["direction"],
                            "nulls": "target_defined",
                            "value_port": entry["port"],
                        },
                    )
                )
                row_generated.append(
                    (
                        "order_item",
                        entry["item"],
                        "R19",
                        encoding
                        if entry["read"]["realization"]["tag"] == "Text"
                        else [],
                        evidence,
                    )
                )
                value = entry["read"]
                # A carried computed value omits the posture exactly when its own
                # producer proof shows it non-null, as for a published column.
                claimed = value["realization"]["nullable"] is None and value.get(
                    "proof", False
                )
                if value["realization"]["nullable"] is not False and not claimed:
                    row_generated.append(
                        ("order_null_posture", entry["item"], "R19", [], evidence)
                    )
        if limit is not None:
            row_generated.append(
                (
                    "static_limit",
                    limit["limit"],
                    "R21",
                    [],
                    None if inline else {"value": limit["value"]},
                )
            )
        if not final and (order_ref is not None or limit is not None):
            row_generated.append(
                ("inner_result_boundary", block, "R21", "naming", None)
            )
        for terminal in terminals:
            row_generated.append(
                ("result_terminal_column", terminal, "R03", "naming", None)
            )
        if ordinal is not None:
            row_generated.append(("collect_ordinal", order_ref, "R27", [], None))
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        result_nodes[0] += (
            (0 if distinct is None else 1)
            + len(order_items)
            + (0 if limit is None else 1)
        )
        outgoing, columns = [], []
        carriers = {}
        for position, (item, column) in enumerate(zip(parsed, visible, strict=True)):
            terminal = terminals[position]
            if column.get("group") is not None:
                group = column["group"]
                if final:
                    _need(position < len(document["columns"]), "published columns")
                    published = document["columns"][position]
                    correspondence = dict(published["correspondence"])
                    origin = correspondence.pop("result_origin", None)
                    _keys(origin, ("terminal", "projection_port", "stages"))
                    _need(
                        origin["terminal"] == terminal
                        and origin["projection_port"] == item["port"]
                        and origin["stages"]
                        == [
                            {
                                "kind": stage["kind"],
                                "boundary": stage["boundary"],
                                "input_port": stage["inputs"][position],
                                "output_port": stage["outputs"][position],
                                "quotient_field": None,
                            }
                            for stage in stages
                        ],
                        "nested result origin",
                    )
                    collect_output(
                        position,
                        item,
                        group["lateral"],
                        {**published, "correspondence": correspondence},
                        container_nullable=bool(column.get("nulled", False)),
                    )
                else:
                    carriers[position] = [c["subject"] for c in item["carriers"][1:]]
                renamed = {
                    **group,
                    "carriers": [{**c, "name": c["label"]} for c in item["carriers"]],
                }
                outgoing.append(
                    {
                        **column,
                        "name": f"c{position}",
                        "terminal": terminal,
                        "group": renamed,
                    }
                )
                columns.append(
                    {
                        "label": item["label"],
                        "export": item["export"],
                        "terminal": terminal,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "root": None,
                        "position": position,
                        "origin": None,
                        "group": renamed,
                    }
                )
                continue
            if final:
                _need(position < len(document["columns"]), "published columns")
                published = document["columns"][position]
                correspondence = dict(published["correspondence"])
                origin = correspondence.pop("result_origin", None)
                _keys(origin, ("terminal", "projection_port", "stages"))
                expected_stages = [
                    {
                        "kind": stage["kind"],
                        "boundary": stage["boundary"],
                        "input_port": stage["inputs"][position],
                        "output_port": stage["outputs"][position],
                        "quotient_field": ref(
                            "quotient_field", quotient_base + position
                        )
                        if stage["kind"] == "distinct"
                        else None,
                    }
                    for stage in stages
                ]
                _need(
                    origin["terminal"] == terminal
                    and origin["projection_port"] == item["port"]
                    and origin["stages"] == expected_stages,
                    "result origin",
                )
                stripped = {**published, "correspondence": correspondence}
                deferred = source_body["deferred"][position]
                (
                    inner_position,
                    node,
                    root,
                    read,
                    realization,
                    inner_block,
                    inner_terminal,
                    export,
                    scan,
                    inner_alias,
                    inner_origin,
                    bases,
                ) = deferred
                _need(inner_position == position and export == item["export"])
                row_output(
                    position,
                    item["label"],
                    node,
                    root,
                    read,
                    realization,
                    inner_block,
                    inner_terminal,
                    export,
                    scan,
                    inner_alias,
                    inner_origin,
                    published=stripped,
                    bases=bases,
                )
            outgoing.append({**column, "name": f"c{position}", "terminal": terminal})
            columns.append(
                {
                    "label": item["label"],
                    "export": item["export"],
                    "terminal": terminal,
                    "realization": column["realization"],
                    "field": column["field"],
                    "literal": column["literal"],
                    "root": None,
                    "position": position,
                    "origin": column["origin"],
                }
            )
        if final:
            _need(len(document["columns"]) == len(columns), "published columns")
        body = {
            "block": block,
            "columns": columns,
            "outgoing": outgoing,
            "projection": True,
            "final": final,
            "definition": source_body["definition"],
            "scan": {"kind": "result", "body": source_body},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "result": True,
            # Phase71 S08: what a Collect read of this terminal re-derives.
            "distinct": distinct,
            "order_ref": order_ref,
            "order_items": order_items,
            "visible_inputs": visible,
            "ordinal": None if ordinal is None else ordinal["order"],
            "carriers": carriers,
        }
        row_bodies.append(body)
        _need(
            sum(len(c["group"]["carriers"]) if c.get("group") else 1 for c in columns)
            + (ordinal is not None)
            <= limits["columns"],
            "physical result width",
        )
        return body

    def set_realization(kind, quantifier, reads):
        """Independently derive one SET output's realization from operand reads."""
        tags = {read["realization"]["tag"] for read in reads}
        _need(len(tags) == 1, "SET column logical tags")
        (tag,) = tags
        union_all = (kind, quantifier) == ("union", "all")
        _need(
            tag in {"Int", "Bool", "Text", "Decimal"}
            or (union_all and tag == "Float")
            or (tag == "Float" and all(_pg_float_key(r["realization"]) for r in reads))
            or (kind == "union" and tag == "Timestamp"),
            "SET comparison domain",
        )
        first = reads[0]["realization"]
        storage = first["storage"]
        domain = dict(first["domain"])
        proofs = []
        widths = {
            "pg_int2": 16,
            "pg_int4": 32,
            "pg_int8": 64,
            "my_smallint": 16,
            "my_int": 32,
            "my_bigint": 64,
            "my_signed_int": 64,
        }
        if tag == "Int":
            _need(
                len({widths.get(r["realization"]["storage"]["kind"]) for r in reads})
                == 1
                and all(
                    r["realization"]["domain"]["kind"] == "int_range" for r in reads
                ),
                "SET Int width",
            )
            domain = {
                "kind": "int_range",
                "min": str(min(int(r["realization"]["domain"]["min"]) for r in reads)),
                "max": str(max(int(r["realization"]["domain"]["max"]) for r in reads)),
            }
            proofs = [r["realization"].get("proven_int_range") for r in reads]
        else:
            _need(
                all(r["realization"]["storage"] == storage for r in reads),
                "SET storage",
            )
            if tag == "Text":
                keys = ("encoding", "collation", "padding")
                _need(
                    len(
                        {
                            tuple(r["realization"]["domain"].get(k) for k in keys)
                            for r in reads
                        }
                    )
                    == 1,
                    "SET text domain",
                )
                domain["max_characters"] = max(
                    int(r["realization"]["domain"].get("max_characters", 0))
                    for r in reads
                )
            elif tag == "Decimal":
                _need(
                    len(
                        {
                            (
                                r["realization"]["domain"].get("precision"),
                                r["realization"]["domain"].get("scale"),
                            )
                            for r in reads
                        }
                    )
                    == 1,
                    "SET decimal parameters",
                )
            else:
                _need(
                    all(r["realization"]["domain"] == first["domain"] for r in reads),
                    "SET domain",
                )
        states = tuple(r["realization"]["nullable"] for r in reads)
        if kind == "except":
            nullable = states[0]
        elif kind == "intersect" and False in states:
            nullable = False
        elif all(state is False for state in states):
            nullable = False
        elif "unknown" in states:
            nullable = "unknown"
        else:
            nullable = True
        result = {
            "tag": tag,
            "storage": storage,
            "nullable": nullable,
            "domain": domain,
        }
        if tag == "Int" and all(type(proof) is tuple for proof in proofs):
            bounds = [
                row_interval({"tag": "Int", "proven_int_range": proof})
                for proof in proofs
            ]
            result["proven_int_range"] = (
                min(low for low, _ in bounds),
                max(high for _, high in bounds),
            )
        return result

    def set_select(block, final, cte_terminals):
        """One SET unit: explicitly grouped operand SELECTs over complete terminals.

        The operator, quantifier, explicit left-fold grouping, every operand's
        immediate terminal read, the positional column map and the SET-owned
        labels are re-derived from the token order alone; an operand body is
        never inlined and no column is compared independently of its tuple.
        """
        _need(block["kind"] == "set_body", "SET body scope")
        opened = 0
        while peek() == "set_fold_open":
            token, _ = take("syntax", "set_fold_open", "(")
            _need(token["subject"] == block, "SET fold subject")
            opened += 1
        operands = []
        operator = None

        def operand_select():
            open_token, _ = take("syntax", "set_operand_open", "(")
            reference = open_token["subject"]
            _need(reference["kind"] == "set_operand", "SET operand subject kind")
            take("syntax", "select", "SELECT ", reference)
            parsed = []
            while True:
                separator = None
                if parsed:
                    separator, _ = take("syntax", "separator", ", ")
                scope_token, alias = take("identifier", "set_input_scope")
                subject = scope_token["subject"]
                _need(subject["kind"] == "set_input", "SET input subject kind")
                _need(
                    separator is None or separator["subject"] == subject,
                    "SET separator",
                )
                take("syntax", "set_input_qualifier", ".", subject)
                column_token, name = take("identifier", "set_input_column")
                take("syntax", "alias", " AS ", subject)
                label_token, label = take("identifier", "label")
                export = label_token["subject"]
                _need(export["kind"] == "export", "SET label export kind")
                parsed.append(
                    {
                        "input": subject,
                        "alias": alias,
                        "name": name,
                        "terminal": column_token["subject"],
                        "export": export,
                        "label": label,
                    }
                )
                if peek() != "separator":
                    break
            take("syntax", "from", " FROM ", reference)
            reads = []
            if peek() == "set_namespace":
                relation = lexical[cursor][0]["subject"]
                item, index = bind_scan(relation)
                take(
                    "identifier",
                    "set_namespace",
                    item["relation"]["namespace"],
                    relation,
                )
                take("syntax", "set_qualifier", ".", relation)
                take("identifier", "set_relation", item["relation"]["name"], relation)
                _need(cause(relation)["path"] == item["selector"]["module"])
                for field in item["fields"]:
                    reads.append(
                        {
                            "name": field["column"],
                            "terminal": source_port(relation, field),
                            "source_port": source_port(relation, field),
                            "realization": row_field_realization(field),
                            "field": field,
                            "literal": None,
                        }
                    )
                scan = {"kind": "scan", "description": item, "index": index}
            else:
                producer_token, name = take("identifier", "set_reference")
                producer = producer_token["subject"]
                body = row_ctes.get(name)
                _need(
                    body is not None
                    and body["block"] == producer
                    and body["projection"]
                    and not body["final"],
                    "a SET operand reads a complete definition terminal",
                )
                assert body is not None
                reads = list(body["outgoing"])
                scan = {"kind": "named", "body": body}
            alias_token, _ = take("syntax", "set_alias", " AS ")
            _need(alias_token["subject"] == reference, "SET alias subject")
            _, alias = take("identifier", "set_scope", None, reference)
            _need(alias == f"o{reference['position']}", "SET operand alias spelling")
            _need(
                len(parsed) == len(reads)
                and all(
                    item["alias"] == alias
                    and item["name"] == read["name"]
                    and item["terminal"] == read["terminal"]
                    for item, read in zip(parsed, reads, strict=True)
                ),
                "a SET operand carries exactly its producer's terminal columns",
            )
            take("syntax", "set_operand_close", ")", reference)
            return {
                "operand": reference,
                "columns": parsed,
                "reads": reads,
                "scan": scan,
            }

        operands.append(operand_select())
        closed = 0
        while peek() == "set_operator":
            token, text = take("syntax", "set_operator")
            _need(token["subject"] == block, "SET operator subject")
            _need(operator is None or text == operator, "one operator per SET body")
            operator = text
            operands.append(operand_select())
            if peek() == "set_fold_close":
                token, _ = take("syntax", "set_fold_close", ")")
                _need(token["subject"] == block, "SET fold close subject")
                closed += 1
        count = len(operands)
        _need(count >= 2 and operator is not None, "a SET body has two operands")
        assert operator is not None
        _need(
            opened == count - 2 and closed == count - 2,
            "explicit left-fold grouping",
        )
        spelled = operator.strip().split(" ")
        _need(
            len(spelled) == 2
            and spelled[0] in {"UNION", "INTERSECT", "EXCEPT"}
            and spelled[1] in {"ALL", "DISTINCT"},
            "SET operator spelling",
        )
        kind, quantifier = spelled[0].lower(), spelled[1].lower()
        width = len(operands[0]["columns"])
        _need(
            width > 0 and all(len(item["columns"]) == width for item in operands),
            "SET positional arity",
        )
        labels = [item["label"] for item in operands[0]["columns"]]
        exports = [item["export"] for item in operands[0]["columns"]]
        _need(
            all(
                [c["label"] for c in item["columns"]] == labels
                and [c["export"] for c in item["columns"]] == exports
                for item in operands
            ),
            "every operand carries the SET-owned labels",
        )
        _need(final or labels == [f"c{i}" for i in range(width)], "SET column labels")
        terminals = result_ports(block, "set", width, cte_terminals)
        column_base = row_counts["set_column"]
        row_counts["set_column"] += width
        if cte_terminals is not None:
            _need(cte_terminals == terminals, "declared SET terminals")
        naming_key = "naming"
        row_generated.append(
            (
                "set_operation",
                block,
                "R22",
                naming_key,
                {
                    "kind": kind,
                    "quantifier": quantifier,
                    "operands": count,
                    "fold": "source_order_left_fold",
                },
            )
        )
        for item in operands:
            row_generated.append(
                ("set_operand", item["operand"], "R22", naming_key, None)
            )
            scan = item["scan"]
            if scan["kind"] == "scan":
                index = scan["index"]
                row_generated.append(
                    ("qualified_scan", None, "R01", ("scan", index), None)
                )
                for field in scan["description"]["fields"]:
                    row_generated.append(
                        (
                            "source_representation",
                            None,
                            "R02",
                            ("field", index, field["ordinal"]),
                            None,
                        )
                    )
        encoding = [i for i in statements if premises[i]["key"] == "client_encoding"]
        outgoing, columns = [], []
        for position in range(width):
            reads = [item["reads"][position] for item in operands]
            realization = set_realization(kind, quantifier, reads)
            row_generated.append(
                (
                    "set_column",
                    ref("set_column", column_base + position),
                    "R22",
                    encoding if realization["tag"] == "Text" else [],
                    {
                        "position": position,
                        "tag": realization["tag"],
                        "nullable": realization["nullable"],
                    },
                )
            )
            terminal = terminals[position]
            if final:
                _need(position < len(document["columns"]), "published SET columns")
                published = document["columns"][position]
                expected = {
                    "ordinal": position,
                    "label": labels[position],
                    "logical_type": {
                        "kind": "builtin",
                        "name": realization["tag"],
                        "parameters": {
                            "precision": realization["domain"]["precision"],
                            "scale": realization["domain"]["scale"],
                        }
                        if realization["tag"] == "Decimal"
                        else None,
                    },
                    "nullable": realization["nullable"],
                    "representation": {
                        "storage": realization["storage"],
                        "nullable": realization["nullable"],
                        "domain": realization["domain"],
                    },
                    "correspondence": {
                        "set_origin": {
                            "body": block,
                            "column": ref("set_column", column_base + position),
                            "kind": kind,
                            "quantifier": quantifier,
                            "fold": "source_order_left_fold",
                            "operands": [
                                {
                                    "operand": item["operand"],
                                    "input": item["columns"][position]["input"],
                                    "terminal": item["columns"][position]["terminal"],
                                }
                                for item in operands
                            ],
                            "terminal": terminal,
                        },
                        "export": exports[position],
                        "sql_symbol": position + 1,
                    },
                }
                _need(encoded(published) == encoded(expected), "SET output published")
            outgoing.append(
                {
                    "name": f"c{position}",
                    "terminal": terminal,
                    "source_port": None,
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "origin": None,
                    "helper": False,
                }
            )
            columns.append(
                {
                    "label": labels[position],
                    "export": exports[position],
                    "terminal": terminal,
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "root": None,
                    "position": position,
                    "origin": None,
                }
            )
        if final:
            _need(len(document["columns"]) == width, "published SET columns")
        if (kind, quantifier) != ("union", "all"):
            row_generated.append(
                (
                    "set_row_equivalence",
                    block,
                    "R22",
                    [],
                    {
                        "kind": kind,
                        "quantifier": quantifier,
                        "operands": count,
                        "fold": "source_order_left_fold",
                    },
                )
            )
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        result_nodes[0] += 3 + count * (2 + width)
        body = {
            "block": block,
            "columns": columns,
            "outgoing": outgoing,
            "projection": True,
            "final": final,
            "definition": next_row_definition(),
            "scan": {"kind": "set"},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "set": True,
        }
        row_bodies.append(body)
        return body

    values_evidence = {
        encoded(r["subject"]): r["evidence"]
        for r in document["requirements"]
        if r.get("denominator") == "generated" and r.get("kind") == "values_column"
    }

    def values_cell(tag, token):
        """One fixed cell token, decoded by its declared tag alone."""
        if token == "NULL":
            return None
        if tag == "Bool":
            _need(token in {"TRUE", "FALSE"}, "VALUES Bool cell")
            return token == "TRUE"
        if tag == "Int":
            return _fixed_payload("Int", token)
        if tag == "Float":
            if family == "postgres":
                _need(token.startswith("'") and token.endswith("'"), "VALUES Float")
                spelling = token[1:-1]
            else:
                _need("e" in token, "VALUES Float exponent")
                spelling = token[:-2] if token.endswith("e0") else token
            value = float(spelling)
            _need(math.isfinite(value) and repr(value) == spelling, "VALUES Float")
            return value
        if family == "postgres":
            _need(re.fullmatch(r"E'(?:\\[0-3][0-7]{2})*'", token) is not None)
            value = bytes(
                int(token[i + 1 : i + 4], 8) for i in range(2, len(token) - 1, 4)
            ).decode()
            _need("\0" not in value, "VALUES PostgreSQL text NUL")
            return value
        _need(re.fullmatch(r"X'(?:[0-9a-f]{2})*'", token) is not None)
        return bytes.fromhex(token[2:-1]).decode()

    def values_anchor_close(tag):
        physical = _fixed_physical(family, tag)
        close = (
            " AS "
            + {
                "pg_bool": "pg_catalog.bool",
                "pg_int8": "pg_catalog.int8",
                "pg_float8": "pg_catalog.float8",
                "pg_text": "pg_catalog.text",
                "my_signed_bool": "SIGNED",
                "my_signed_int": "SIGNED",
                "my_double": "DOUBLE",
                "my_utf8mb4_text": "CHAR CHARACTER SET utf8mb4",
            }[physical]
            + ")"
        )
        if tag == "Text":
            close += (
                ' COLLATE "C"' if family == "postgres" else " COLLATE utf8mb4_0900_bin"
            )
        return physical, close

    def values_cast(tag):
        """One `CAST(<cell> AS <declared type>)`, returning its decoded cell."""
        token, _ = take("syntax", "anchor_open", "CAST(")
        column = token["subject"]
        _need(column["kind"] == "values_column", "VALUES cell column subject")
        literal, text = take("literal", tag, None, column)
        _, close = values_anchor_close(tag)
        take("syntax", "anchor_close", close, column)
        return values_cell(tag, text)

    function_evidence = {
        encoded(r["subject"]): r["evidence"]
        for r in document["requirements"]
        if r.get("denominator") == "generated" and r.get("kind") == "table_function"
    }

    def function_select(block, final, cte_terminals):
        """One table-function CTE: its one column read from the qualified call.

        The identity, the three CAST values and the row bound are decoded from
        the tokens alone and must equal the published requirement evidence.
        """
        _need(family == "postgres" and not final, "a PostgreSQL table-function CTE")
        reference = ref("values_column", row_counts["values_column"])
        _need(
            values_evidence.get(encoded(reference))
            == [{"position": 0, "tag": "Int", "nullable": False}],
            "the table-function column is Int",
        )
        take("syntax", "select", "SELECT ", block)
        _, binding = take("identifier", "function_scope", None, reference)
        take("syntax", "function_qualifier", ".", reference)
        take("identifier", "function_column", binding, reference)
        take("syntax", "from", " FROM ", block)
        take("syntax", "function", "pg_catalog.generate_series", block)
        take("syntax", "function_open", "(", block)
        values = []
        for position in range(3):
            if position:
                take("syntax", "separator", ", ", block)
            take("syntax", "anchor_open", "CAST(", block)
            _, text = take("literal", "Int", None, block)
            values.append(_fixed_payload("Int", text))
            take("syntax", "anchor_close", " AS pg_catalog.int8)", block)
        take("syntax", "function_close", ") AS ", block)
        take("identifier", "function_alias", binding, block)
        take("syntax", "function_columns_open", "(", block)
        take("identifier", "function_column_alias", binding, reference)
        take("syntax", "function_columns_close", ")", block)
        start, stop, step = values
        _need(step != 0, "a nonzero step")
        rows = (
            0
            if (step > 0 and start > stop) or (step < 0 and start < stop)
            else abs(stop - start) // abs(step) + 1
        )
        _need(rows <= 1 << 20, "the static row bound")
        evidence = {
            "function": "pg_catalog.generate_series("
            "pg_catalog.int8,pg_catalog.int8,pg_catalog.int8)",
            "arguments": [str(value) for value in values],
            "rows": rows,
        }
        _need(
            function_evidence.get(encoded(block)) == [evidence],
            "published table-function evidence",
        )
        (terminal,) = result_ports(block, "function", 1, cte_terminals)
        row_counts["values_column"] += 1
        _need(cte_terminals == [terminal], "declared table-function terminal")
        row_generated.append(("table_function", block, "R04", "naming", evidence))
        row_generated.append(
            (
                "values_column",
                reference,
                "R02",
                [],
                {"position": 0, "tag": "Int", "nullable": False},
            )
        )
        realization = {
            "tag": "Int",
            "storage": {"kind": "pg_int8"},
            "nullable": False,
            "domain": {
                "kind": "int_range",
                "min": str(-(1 << 63)),
                "max": str((1 << 63) - 1),
            },
            "proven_int_range": (-(1 << 63), (1 << 63) - 1),
        }
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        result_nodes[0] += 2 + 1 + 3
        body = {
            "block": block,
            "columns": [
                {
                    "label": "c0",
                    "export": None,
                    "terminal": terminal,
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "root": None,
                    "position": 0,
                    "origin": None,
                }
            ],
            "outgoing": [
                {
                    "name": "c0",
                    "terminal": terminal,
                    "source_port": None,
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "origin": None,
                    "helper": False,
                }
            ],
            "projection": True,
            "final": False,
            "definition": next_row_definition(),
            "scan": {"kind": "values"},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "values": True,
        }
        row_bodies.append(body)
        return body

    def values_select(block, final, cte_terminals):
        """One VALUES unit: typed fixed rows, every alias written by the SQL.

        Column tags come from the published declared-column evidence; each cell
        is decoded from its own literal token under its CAST, and the realization
        of every column is re-derived from those cells alone.
        """
        _need(block["kind"] == "values_body", "VALUES body scope")
        if encoded(block) in function_evidence:
            return function_select(block, final, cte_terminals)
        base = row_counts["values_column"]
        columns_seen: list[dict[str, Any]] = []
        rows: list[list[Any]] = []
        labelled = peek() == "select"
        scope_name = f"v{block['position']}"

        def declared(position):
            reference = ref("values_column", base + position)
            evidence = values_evidence.get(encoded(reference))
            _need(
                type(evidence) is list and len(evidence) == 1,
                "declared VALUES column evidence",
            )
            item = cast(dict[str, Any], cast(list, evidence)[0])
            _keys(item, ("position", "tag", "nullable"))
            _need(
                item["position"] == position
                and item["tag"] in {"Bool", "Int", "Float", "Text"}
                and type(item["nullable"]) is bool,
                "declared VALUES column",
            )
            return reference, item["tag"], item["nullable"]

        if labelled:
            take("syntax", "select", "SELECT ", block)
            while True:
                position = len(columns_seen)
                reference, tag, nullable = declared(position)
                if position:
                    take("syntax", "separator", ", ", reference)
                if peek() == "values_scope":
                    take("identifier", "values_scope", scope_name, reference)
                    take("syntax", "values_qualifier", ".", reference)
                    take("identifier", "values_column", f"c{position}", reference)
                    empty = False
                else:
                    _need(values_cast(tag) is None, "a zero-row column is NULL")
                    empty = True
                take("syntax", "alias", " AS ", reference)
                label_token, label = take("identifier", "label")
                export = label_token["subject"]
                _need(export["kind"] == "export", "VALUES label export kind")
                columns_seen.append(
                    {
                        "reference": reference,
                        "tag": tag,
                        "nullable": nullable,
                        "label": label,
                        "export": export,
                        "empty": empty,
                    }
                )
                if peek() != "separator":
                    break
            width = len(columns_seen)
            _need(len({c["empty"] for c in columns_seen}) == 1, "one VALUES spelling")
            if columns_seen[0]["empty"]:
                take("syntax", "values_empty", " WHERE FALSE", block)
            else:
                _need(final, "only a selected VALUES statement labels its table")
                take("syntax", "values_open", " FROM (", block)
        else:
            # A VALUES CTE is as wide as its own column list; the columns of a
            # later VALUES body of the statement follow its columns directly.
            _need(cte_terminals is not None, "VALUES CTE column list")
            width = len(cast(list, cte_terminals))
            columns_seen = [
                dict(
                    zip(
                        ("reference", "tag", "nullable"),
                        declared(position),
                        strict=True,
                    ),
                    label=f"c{position}",
                    export=None,
                    empty=False,
                )
                for position in range(width)
            ]
        _need(width > 0, "a VALUES body declares columns")
        if not columns_seen[0]["empty"]:
            take("syntax", "values", "VALUES ", block)
            while True:
                if rows:
                    take("syntax", "values_row_separator", ", ", block)
                take(
                    "syntax",
                    "values_row_open",
                    "(" if family == "postgres" else "ROW(",
                    block,
                )
                row = []
                for position, column in enumerate(columns_seen):
                    if position:
                        take("syntax", "separator", ", ", column["reference"])
                    value = values_cast(column["tag"])
                    _need(
                        value is not None or column["nullable"],
                        "a NULL cell needs a nullable column",
                    )
                    row.append(value)
                take("syntax", "values_row_close", ")", block)
                rows.append(row)
                if peek() != "values_row_separator":
                    break
            if final:
                take("syntax", "values_close", ") AS ", block)
                take("identifier", "values_alias", scope_name, block)
                take("syntax", "values_columns_open", " (", block)
                for position, column in enumerate(columns_seen):
                    if position:
                        take("syntax", "separator", ", ", column["reference"])
                    take(
                        "identifier",
                        "values_column_alias",
                        f"c{position}",
                        column["reference"],
                    )
                take("syntax", "values_columns_close", ")", block)
        _need(len(rows) <= 1000 and width <= 64, "VALUES static bounds")
        if not final:
            _need(
                [c["label"] for c in columns_seen] == [f"c{i}" for i in range(width)],
                "VALUES CTE column labels",
            )
        terminals = result_ports(block, "values", width, cte_terminals)
        row_counts["values_column"] += width
        if cte_terminals is not None:
            _need(cte_terminals == terminals, "declared VALUES terminals")
        encoding = [i for i in statements if premises[i]["key"] == "client_encoding"]
        row_generated.append(
            (
                "values_rows",
                block,
                "R04",
                "naming",
                {"rows": len(rows), "columns": width},
            )
        )
        outgoing, published = [], []
        for position, column in enumerate(columns_seen):
            tag = column["tag"]
            present = [row[position] for row in rows if row[position] is not None]
            proven = None
            if tag == "Int":
                low, high = (
                    (min(present), max(present))
                    if present
                    else (-(1 << 63), (1 << 63) - 1)
                )
                domain: dict[str, Any] = {
                    "kind": "int_range",
                    "min": str(low),
                    "max": str(high),
                }
                proven = (-(1 << 63), (1 << 63) - 1)
            elif tag == "Text":
                domain = {
                    "kind": "text",
                    "max_characters": max((len(v) for v in present), default=0),
                    "encoding": "UTF8" if family == "postgres" else "utf8mb4",
                    "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
                    "padding": "NO PAD",
                }
            elif tag == "Float":
                domain = {"kind": "finite_float", "format": "binary64"}
            else:
                domain = {"kind": "bool01"}
            realization = {
                "tag": tag,
                "storage": {"kind": _fixed_physical(family, tag)},
                "nullable": column["nullable"],
                "domain": domain,
            }
            if proven is not None:
                realization["proven_int_range"] = proven
            row_generated.append(
                (
                    "values_column",
                    column["reference"],
                    "R02",
                    encoding if tag == "Text" else [],
                    {"position": position, "tag": tag, "nullable": column["nullable"]},
                )
            )
            outgoing.append(
                {
                    "name": f"c{position}",
                    "terminal": terminals[position],
                    "source_port": None,
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "origin": None,
                    "helper": False,
                }
            )
            published.append(
                {
                    "label": column["label"],
                    "export": column["export"],
                    "terminal": terminals[position],
                    "realization": realization,
                    "field": None,
                    "literal": None,
                    "root": None,
                    "position": position,
                    "origin": None,
                }
            )
            if final:
                _need(position < len(document["columns"]), "published VALUES columns")
                expected = {
                    "ordinal": position,
                    "label": column["label"],
                    "logical_type": {
                        "kind": "builtin",
                        "name": tag,
                        "parameters": None,
                    },
                    "nullable": column["nullable"],
                    "representation": {
                        "storage": realization["storage"],
                        "nullable": column["nullable"],
                        "domain": domain,
                    },
                    "correspondence": {
                        "export": column["export"],
                        "sql_symbol": position + 1,
                    },
                }
                _need(
                    encoded(document["columns"][position]) == encoded(expected),
                    "VALUES output published",
                )
        if final:
            _need(len(document["columns"]) == width, "published VALUES columns")
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        result_nodes[0] += 2 + width * (1 + len(rows))
        body = {
            "block": block,
            "columns": published,
            "outgoing": outgoing,
            "projection": True,
            "final": final,
            "definition": next_row_definition(),
            "scan": {"kind": "values"},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "values": True,
        }
        row_bodies.append(body)
        return body

    row_ctes: dict[str, Any] = {}
    row_scopes: list[Any] = []
    row_source_definitions: list[Any] = []
    row_scan_index: dict[str, int] = {}

    def bind_scan(producer):
        """Consume the next emitted scan occurrence and bind it to this relation."""
        _need(producer["kind"] == "definition", "scan definition kind")
        item, positions = next_scan()
        index = len(scan_occurrences) - len(scan_order) - 1
        _need(
            scan_definitions[index][0] == producer["position"],
            "scan occurrence names its own definition",
        )
        if producer not in row_source_definitions:
            row_source_definitions.append(producer)
            row_source_definitions.sort(key=lambda value: value["position"])
        key = encoded(producer).decode()
        seen = row_scan_index.setdefault(key, index)
        _need(
            encoded(scan_occurrences[seen][0]["selector"]) == encoded(item["selector"]),
            "one definition cannot scan two declared sources",
        )
        return item, index

    def source_port(definition, field):
        """This source definition's own plan port for one of its declared fields."""
        base = source_port_base[definition["position"]]
        return ref("source_port", base + field["ordinal"])

    def projection_inline_frame():
        """Read one SELECT's own outer row before its inline bytes."""
        depth = 0
        reads = int(peek() == "inline_open")
        for index in range(cursor, len(lexical)):
            token, _ = lexical[index]
            role = token["role"]
            if depth == 0 and role in {"exists_from", "scalar_from", "in_from"}:
                reads += int(lexical[index + 1][0]["role"] == "inline_open")
            if role == "inline_open":
                depth += 1
                continue
            if role == "inline_close":
                depth -= 1
                continue
            if depth or role != "from":
                continue
            if not reads:
                return 0, None
            producer = token["subject"]
            lookahead = index + 1
            next_token, name = lexical[lookahead]
            next_role = next_token["role"]
            if next_role in {"cte_reference", "stage_reference"}:
                lookahead += 1
                body = row_ctes.get(name)
                _need(lexical[lookahead][0]["role"] == "alias")
                lookahead += 1
                alias_token, alias = lexical[lookahead]
                _need(
                    body is not None
                    and alias_token["role"]
                    == (
                        "relation_scope"
                        if next_role == "cte_reference"
                        else "stage_scope"
                    ),
                    "projected correlated named row",
                )
                assert body is not None
                return reads, {
                    "alias": alias,
                    "incoming": body["outgoing"],
                    "body": body,
                }
            _need(
                producer["kind"] == "definition" and next_role == "namespace",
                "a projected correlated read needs its physical row",
            )
            owners = [
                description
                for position, description in scan_definitions
                if position == producer["position"]
            ]
            _need(bool(owners) and all(item == owners[0] for item in owners))
            lookahead += 1
            _need(lexical[lookahead][0]["role"] == "qualifier")
            lookahead += 1
            _need(lexical[lookahead][0]["role"] == "relation")
            lookahead += 1
            _need(lexical[lookahead][0]["role"] == "alias")
            lookahead += 1
            alias_token, alias = lexical[lookahead]
            _need(
                alias_token["role"] == "relation_scope",
                "projected correlated row alias",
            )
            return reads, {
                "alias": alias,
                "incoming": [
                    {
                        "name": field["column"],
                        "terminal": source_port(producer, field),
                        "source_port": source_port(producer, field),
                        "realization": row_field_realization(field),
                        "field": field,
                        "literal": None,
                    }
                    for field in owners[0]["fields"]
                ],
            }
        return 0, None

    def scanned_source(read):
        """The declared source a read reaches, resolved through its OWN port.

        Several sources may be scanned in one document, so the first one is never
        an answer for every column.
        """
        port = read.get("source_port")
        _need(port is not None, "a source field read declares its own port")
        _reference(port)
        _need(port["kind"] == "source_port", "source port kind")
        owner = [
            description
            for position, description in source_port_owner
            if position <= port["position"] < position + len(description["fields"])
        ]
        _need(len(owner) == 1, "a source port belongs to exactly one declared source")
        return owner[0]

    naming = [i for i in statements if premises[i]["key"] == "identifier_case"]

    def row_case_premise():
        expected_case = (
            "quoted_exact" if family == "postgres" else "lower_case_table_names=0"
        )
        _need(
            bool(naming) and all(premises[i]["value"] == expected_case for i in naming),
            "generated stage scopes need the identifier-case premise",
        )

    NATIVE_JOIN_KINDS = {
        " CROSS JOIN ": "cross",
        " INNER JOIN ": "inner",
        " LEFT JOIN ": "left",
        " RIGHT JOIN ": "right",
        " FULL JOIN ": "full",
    }
    # Which side one JOIN kind null-extends. A membership wrapper adds none.
    JOIN_NULLS = {
        "cross": (),
        "inner": (),
        "left": (1,),
        "right": (0,),
        "full": (0, 1),
    }

    join_aliases: set[str] = set()

    def unnest_relation(left):
        """Rebuild the one S13 right input from its already parsed left group."""
        _need(
            family == "postgres" and not row_unnests and left is not None,
            "Unnest route",
        )
        assert left is not None
        event, _ = take("syntax", "unnest_rows_open", "LATERAL ROWS FROM (")
        input_ref = event["subject"]
        _need(input_ref["kind"] == "join_input", "Unnest input subject")
        unnest_ref = ref("unnest", 0)
        source_ref = None
        names = []
        while True:
            if names:
                take("syntax", "separator", ", ", unnest_ref)
            take("syntax", "unnest_function", "pg_catalog.unnest(", unnest_ref)
            scoped, _ = take("identifier", "unnest_scope", left["alias"])
            if source_ref is None:
                source_ref = scoped["subject"]
            _need(
                scoped["subject"] == source_ref and source_ref["kind"] == "join_port",
                "Unnest source port",
            )
            take("syntax", "qualifier", ".", source_ref)
            _, name = take("identifier", "unnest_array", subject=source_ref)
            names.append(name)
            take("syntax", "unnest_function_close", ")", unnest_ref)
            if peek() != "separator":
                break
        groups = [
            (i, column["group"])
            for i, column in enumerate(left["columns"])
            if column.get("group") is not None
            and not column.get("withheld", False)
            and [item["name"] for item in column["group"]["carriers"][1:]] == names
        ]
        _need(len(groups) == 1, "one exact Unnest collection source")
        group_position, group = groups[0]
        children = group["lateral"]["terminal"]["outgoing"]
        arrays = group["carriers"][1:]
        _need(bool(children) and len(arrays) == len(children), "Unnest array width")
        for child in children:
            realization = child["realization"]
            _need(
                realization["tag"]
                in {
                    "Int",
                    "Bool",
                    "Text",
                    "Float",
                    "Decimal",
                    "Date",
                    "Timestamp",
                    "UUID",
                },
                "Unnest child leaf",
            )
            if realization["tag"] == "Text":
                _need(
                    realization["domain"].get("kind") == "text"
                    and type(realization["domain"].get("max_characters")) is int
                    and realization["domain"]["max_characters"] > 0,
                    "Unnest finite Text",
                )
        take("syntax", "unnest_rows_close", ")", input_ref)
        take("syntax", "join_alias", " AS ", input_ref)
        _, alias = take(
            "identifier", "join_scope", f"m{input_ref['position']}", input_ref
        )
        _need(alias not in join_aliases, "Unnest alias collision")
        join_aliases.add(alias)
        take("syntax", "unnest_columns_open", " (", input_ref)
        columns, exports = [], []
        for i, child in enumerate(children):
            if i:
                take("syntax", "separator", ", ", input_ref)
            event, _ = take("identifier", "unnest_column", f"c{i}")
            _need(event["subject"]["kind"] == "export", "Unnest output export kind")
            exports.append(event["subject"])
            columns.append(
                {
                    **child,
                    "name": f"c{i}",
                    "terminal": event["subject"],
                    "nulled": False,
                }
            )
        _need(
            len({encoded(value) for value in exports}) == len(children),
            "complete unique Unnest output vector",
        )
        take("syntax", "unnest_columns_close", ")", input_ref)
        descriptor = {
            "ref": unnest_ref,
            "definition": next_row_definition(),
            "source": source_ref,
            "group_position": group_position,
            "exports": exports,
            "group": group,
        }
        row_unnests.append(descriptor)
        return {
            "kind": "unnest",
            "input": input_ref,
            "alias": alias,
            "columns": columns,
            "description": None,
            "index": None,
            "body": None,
            "unnest": descriptor,
        }

    def join_relation(expected_kind, lateral_frame=None):
        """One JOIN input relation, its capture-free alias and pre-match columns."""
        role = peek()
        if role == "unnest_rows_open":
            _need(
                expected_kind == "right" and lateral_frame is not None,
                "Unnest must be the right input",
            )
            return unnest_relation(lateral_frame)
        if role == "join_namespace":
            relation = lexical[cursor][0]["subject"]
            item, index = bind_scan(relation)
            take(
                "identifier", "join_namespace", item["relation"]["namespace"], relation
            )
            take("syntax", "join_qualifier", ".", relation)
            take("identifier", "join_relation", item["relation"]["name"], relation)
            _need(cause(relation)["path"] == item["selector"]["module"])
            columns = [
                {
                    "name": field["column"],
                    "terminal": source_port(relation, field),
                    "source_port": source_port(relation, field),
                    "realization": row_field_realization(field),
                    "field": field,
                    "literal": None,
                    "nulled": False,
                }
                for field in item["fields"]
            ]
            record = {"kind": "scan", "description": item, "index": index, "body": None}
        elif role == "lateral_open":
            _need(expected_kind == "right" and lateral_frame is not None)
            assert lateral_frame is not None
            producer = lexical[cursor][0]["subject"]
            _need(producer["kind"] == "join_input", "LATERAL input subject kind")
            take("syntax", "lateral_open", "LATERAL (", producer)
            block = lexical[cursor][0]["subject"]
            _need(
                block["kind"] in {"select_block", "result_boundary"},
                "LATERAL body scope",
            )
            inline_owners.append(next_row_definition())
            frame = {
                "alias": lateral_frame["alias"],
                "incoming": lateral_frame["columns"],
            }
            capture_frames.append(frame)
            mark = len(row_generated)
            body = (
                result_select(block, False, None, inline=True)
                if block["kind"] == "result_boundary"
                else row_select(block, False, None, inline=True)
            )
            generated = row_generated[mark:]
            del row_generated[mark:]
            _need(capture_frames.pop() is frame)
            take("syntax", "lateral_close", ")", producer)
            columns = [
                {**column, "nulled": column.get("nulled", False)}
                for column in body["outgoing"]
            ]
            record = {
                "kind": "lateral",
                "description": None,
                "index": None,
                "body": body,
                "generated": generated,
            }
        else:
            _need(role == "join_reference", "JOIN input relation role")
            producer = lexical[cursor][0]["subject"]
            _need(producer["kind"] == "join_input", "JOIN input subject kind")
            _, name = take("identifier", "join_reference", subject=producer)
            body = row_ctes.get(name)
            _need(
                body is not None,
                "a JOIN input must read an emitted definition or earlier JOIN",
            )
            assert body is not None
            _need(
                body["projection"] or body.get("join") is True,
                "a JOIN input reads a complete terminal, never a partial stage",
            )
            columns = [
                {**column, "nulled": column.get("nulled", False)}
                for column in body["outgoing"]
            ]
            record = {
                "kind": "join" if body.get("join") else "named",
                "description": None,
                "index": None,
                "body": body,
            }
        alias_event, _ = take("syntax", "join_alias", " AS ")
        producer = alias_event["subject"]
        _need(producer["kind"] == "join_input", "JOIN input subject kind")
        _, alias = take("identifier", "join_scope", None, producer)
        _need(alias == f"m{producer['position']}", "JOIN scope spelling")
        _need(alias not in join_aliases, "JOIN aliases must stay capture-free")
        join_aliases.add(alias)
        return {"input": producer, "alias": alias, "columns": columns, **record}

    def join_condition(inputs, join_ref, owner):
        """Every emitted condition component, in its own role and order."""
        scopes = {item["alias"]: item for item in inputs}
        equalities, predicate = [], None
        while peek() in {"equality_open", "equality_separator"}:
            if peek() == "equality_separator":
                take("syntax", "equality_separator", " AND ")
            open_token, _ = take("syntax", "equality_open", "(")
            match = open_token["subject"]
            _need(
                match["kind"] == "relationship_match",
                "relationship equality subject kind",
            )
            start = open_token["start"]
            left = join_equality_side(scopes, match)
            take("syntax", "equality_operator", " = ", match)
            right = join_equality_side(scopes, match)
            closed, _ = take("syntax", "equality_close", ")", match)
            _need(
                left["alias"] != right["alias"],
                "a relationship equality must cross its two inputs",
            )
            _need(
                left["read"]["realization"]["tag"]
                == right["read"]["realization"]["tag"],
                "relationship equality type pair",
            )
            if left["read"]["realization"]["tag"] in {"Timestamp", "Date", "UUID"}:
                _need(
                    left["read"]["realization"]["storage"]
                    == right["read"]["realization"]["storage"]
                    and left["read"]["realization"]["domain"]
                    == right["read"]["realization"]["domain"],
                    "temporal/uuid relationship representation",
                )
            expected_ranges.append(
                ("relationship_equality", match, start, closed["end"])
            )
            equalities.append({"match": match, "left": left, "right": right})
        if equalities:
            if peek() == "condition_separator":
                take("syntax", "condition_separator", " AND ")
                predicate = row_parse(owner, "join_port")
        else:
            predicate = row_parse(owner, "join_port")
        _need(
            bool(equalities) or predicate is not None,
            "an emitted JOIN condition needs one component",
        )
        return equalities, predicate, scopes

    def join_equality_side(scopes, match):
        """One equality operand: an exact pre-match port of one of the inputs."""
        scope_token, alias = take("identifier", "equality_scope")
        port = scope_token["subject"]
        _need(port["kind"] == "join_port", "equality operand port kind")
        take("syntax", "equality_qualifier", ".", match)
        token, name = take("identifier", "equality_column")
        item = scopes.get(alias)
        _need(item is not None, "an equality operand reads one of this JOIN's inputs")
        assert item is not None
        matches = [
            c
            for c in item["columns"]
            if c["name"] == name and c["terminal"] == token["subject"]
        ]
        _need(len(matches) == 1, "equality operand outside its pre-match input")
        key = encoded(port).decode()
        _need(
            row_port_reads.setdefault(key, matches[0]) is matches[0],
            "pre-match port binding drift",
        )
        return {"alias": alias, "port": port, "read": matches[0]}

    def join_null_rejected(kind, inputs, equalities, predicate):
        """Pre-match carriers this JOIN's own condition proves can never be NULL.

        Only a matched-pairs INNER join publishes every row through its condition,
        so only there does a NULL operand remove the row. A top-level AND conjunct
        proves its own direct comparison operands; an OR branch, a null test and a
        computed operand prove nothing. This is derived from the parsed condition
        alone -- never from a published realization.
        """
        if kind != "inner":
            return []
        proved = [
            side["read"]
            for item in equalities
            for side in (item["left"], item["right"])
        ]
        scoped = {item["alias"]: item for item in inputs}
        pending = [] if predicate is None else [predicate]
        while pending:
            node = pending.pop()
            if node["kind"] == "logical":
                if node["operator"] == " AND ":
                    pending.extend(node["operands"])
                continue
            if node["kind"] != "comparison":
                continue
            for operand in node["operands"]:
                if operand["kind"] != "reference":
                    continue
                item = scoped.get(operand["alias"])
                if item is None:
                    continue
                proved.extend(
                    column
                    for column in item["columns"]
                    if column["name"] == operand["name"]
                    and column["terminal"] == operand["terminal"]
                )
        return proved

    def join_select(join_ref, header, header_names):
        """One JOIN occurrence's own generated SELECT, independently reconciled."""
        take("syntax", "select", "SELECT ", join_ref)
        parsed = []
        while True:
            separator = None
            if parsed:
                separator, _ = take("syntax", "separator", ", ")
            if following("join_column_scope", "qualifier"):
                match = lexical[cursor][0]["subject"]
                _need(
                    match["kind"] == "join_port" and len(parsed) < len(header_names),
                    "JOIN nested input",
                )
                position = int(header_names[len(parsed)][1:])
                group = carrier_group(
                    "join_column_scope",
                    match,
                    False,
                    position,
                    count_kinds=("join_port",),
                )
                _need(
                    separator is None or separator["subject"] == group["export"],
                    "JOIN nested separator",
                )
                parsed.append(
                    {
                        "kind": "group",
                        "alias": group["scope"],
                        "match": match,
                        "port": group["export"],
                        "label": group["label"],
                        "carriers": group["carriers"],
                    }
                )
                if peek() != "separator":
                    break
                continue
            scope_token, alias = take("identifier", "join_column_scope")
            match = scope_token["subject"]
            _need(match["kind"] == "join_port", "carried pre-match port kind")
            qualifier, _ = take("syntax", "join_column_qualifier", ".")
            token, name = take("identifier", "join_column")
            alias_token, _ = take("syntax", "alias", " AS ")
            port = alias_token["subject"]
            _need(port["kind"] == "join_port", "published JOIN port kind")
            _need(qualifier["subject"] == port, "published port qualifier")
            _, label = take("identifier", "label", None, port)
            _need(separator is None or separator["subject"] == port, "separator")
            _need(
                re.fullmatch(r"c[0-9]+", label) is not None,
                "published JOIN column label",
            )
            parsed.append(
                {
                    "kind": "flat",
                    "alias": alias,
                    "match": match,
                    "name": name,
                    "terminal": token["subject"],
                    "port": port,
                    "label": label,
                }
            )
            if peek() != "separator":
                break
        take("syntax", "from", " FROM ", join_ref)
        left = join_relation("left")
        membership, kind = None, None
        if peek() == "join_kind":
            _, token = take("syntax", "join_kind", subject=join_ref)
            _need(token in NATIVE_JOIN_KINDS, "native JOIN kind spelling")
            kind = NATIVE_JOIN_KINDS[token]
            right = join_relation(
                "right", left if kind in {"cross", "inner", "left"} else None
            )
            if kind == "cross":
                equalities, predicate, scopes = (
                    [],
                    None,
                    {item["alias"]: item for item in (left, right)},
                )
            else:
                take("syntax", "join_on", " ON ", join_ref)
                equalities, predicate, scopes = join_condition(
                    (left, right), join_ref, join_ref
                )
        else:
            token_event, token = take("syntax", "membership_open", subject=join_ref)
            _need(
                token in {" WHERE EXISTS (", " WHERE NOT EXISTS ("},
                "membership wrapper spelling",
            )
            membership = "exists" if token == " WHERE EXISTS (" else "not_exists"
            kind = "semi" if membership == "exists" else "anti"
            take("syntax", "membership_select", "SELECT ", join_ref)
            take("literal", "membership_sentinel", "1", join_ref)
            take("syntax", "membership_from", " FROM ", join_ref)
            right = join_relation("right")
            take("syntax", "correlation", " WHERE ", join_ref)
            equalities, predicate, scopes = join_condition(
                (left, right), join_ref, join_ref
            )
            take("syntax", "membership_close", ")", join_ref)
        inputs = (left, right)
        carriers = [*left["columns"], *right["columns"]]
        nulls = () if membership is not None else JOIN_NULLS[kind]
        rejected = join_null_rejected(kind, inputs, equalities, predicate)
        widths = (len(left["columns"]), len(right["columns"]))
        logical_width = widths[0] if membership is not None else len(carriers)
        _need(bool(parsed), "nonempty published JOIN")
        positions = [int(item["label"][1:]) for item in parsed]
        _need(
            positions == sorted(set(positions))
            and all(0 <= i < logical_width for i in positions)
            and header_names == [item["label"] for item in parsed],
            "published JOIN port arity/names",
        )
        base = parsed[0]["match"]["position"] - positions[0]
        _need(
            base >= 0
            and all(
                item["match"] == ref("join_port", base + i)
                and item["port"] == ref("join_port", base + len(carriers) + i)
                and item["label"] == f"c{i}"
                for i, item in zip(positions, parsed, strict=True)
            ),
            "JOIN match/output identity",
        )
        if right["kind"] == "unnest":
            descriptor = right["unnest"]
            _need(
                descriptor["source"]
                == ref("join_port", base + descriptor["group_position"]),
                "Unnest exact logical source slot",
            )
        omitted = set(range(logical_width)) - set(positions)
        _need(
            all(carriers[i].get("group") is not None for i in omitted),
            "only nested JOIN ports may be withheld",
        )
        outgoing, columns = [], []
        for position, item in zip(positions, parsed, strict=True):
            side = 0 if position < widths[0] else 1
            carrier = carriers[position]
            _need(
                not carrier.get("withheld", False), "withheld JOIN input cannot be read"
            )
            if item["kind"] == "group":
                group = carrier.get("group")
                _need(
                    group is not None
                    and item["alias"] == inputs[side]["alias"]
                    and [c["name"] for c in item["carriers"]]
                    == [c["name"] for c in group["carriers"]]
                    and [c["subject"] for c in item["carriers"][1:]]
                    == [c["subject"] for c in group["carriers"][1:]],
                    "JOIN carried group source",
                )
                assert group is not None
                nulled = bool(carrier.get("nulled", False)) or side in nulls
                renamed = {
                    **group,
                    "carriers": [
                        {"subject": c["subject"], "name": c["label"]}
                        for c in item["carriers"]
                    ],
                }
                outgoing.append(
                    {
                        "name": item["label"],
                        "terminal": item["port"],
                        "source_port": None,
                        "realization": None,
                        "field": None,
                        "literal": None,
                        "origin": None,
                        "helper": False,
                        "strict": False,
                        "proof": False,
                        "nulled": nulled,
                        "group": renamed,
                        "withheld": False,
                    }
                )
                columns.append({"port": item["port"], "nulled": nulled})
                continue
            _need(
                item["alias"] == inputs[side]["alias"]
                and item["name"] == carrier["name"]
                and item["terminal"] == carrier["terminal"],
                "a published JOIN port must carry its own pre-match column",
            )
            nulled = bool(carrier["nulled"]) or side in nulls
            # A computed carrier (nullable None) keeps its publication and its
            # own NON NULL proof unless this JOIN null-extends it.
            computed = carrier["realization"]["nullable"] is None and not nulled
            narrowed = (
                bool(carrier["realization"]["nullable"])
                and not nulled
                and any(carrier is item for item in rejected)
            )
            realization = {
                **carrier["realization"],
                "nullable": None
                if computed
                else (
                    nulled
                    or (bool(carrier["realization"]["nullable"]) and not narrowed)
                ),
            }
            outgoing.append(
                {
                    "name": item["label"],
                    "terminal": item["port"],
                    "source_port": carrier.get("source_port"),
                    "realization": realization,
                    "field": carrier["field"],
                    "literal": carrier["literal"],
                    # An outer JOIN may null-extend an already computed aggregate
                    # value; it never recomputes it, so the origin rides along.
                    "origin": carrier.get("origin"),
                    "nulled": nulled,
                    "proof": computed and bool(carrier.get("proof", False)),
                }
            )
            columns.append({"port": item["port"], "nulled": nulled})
        _need(header == [item["port"] for item in parsed], "declared JOIN terminals")
        carrier_ports = [item["match"] for item in parsed]
        _need(
            len({encoded(item).decode() for item in carrier_ports}) == len(parsed)
            and not (
                {encoded(item).decode() for item in carrier_ports}
                & {encoded(item["port"]).decode() for item in parsed}
            ),
            "each published port carries its own distinct pre-match port",
        )
        by_position = dict(zip(positions, outgoing, strict=True))
        logical_outputs, logical_outgoing = [], []
        for i, carrier in enumerate(carriers[:logical_width]):
            side = 0 if i < widths[0] else 1
            port = ref("join_port", base + len(carriers) + i)
            nulled = bool(carrier.get("nulled", False)) or side in nulls
            logical_outputs.append({"port": port, "nulled": nulled})
            logical_outgoing.append(
                by_position[i]
                if i in by_position
                else {
                    **carrier,
                    "name": f"c{i}",
                    "terminal": port,
                    "withheld": True,
                    "nulled": nulled,
                }
            )
        join_generated(
            join_ref,
            kind,
            membership,
            inputs,
            equalities,
            predicate,
            logical_outputs,
            scopes,
        )
        body = {
            "block": join_ref,
            "columns": columns,
            "outgoing": logical_outgoing,
            "projection": False,
            "final": False,
            "scan": {"kind": "join"},
            "header": header,
            "join": True,
            "kind": kind,
            "inputs": inputs,
            "carriers": {
                i: [c["subject"] for c in item["carriers"][1:]]
                for i, item in enumerate(parsed)
                if item["kind"] == "group"
            },
        }
        row_bodies.append(body)
        _need(
            sum(
                len(item["carriers"]) if item["kind"] == "group" else 1
                for item in parsed
            )
            <= limits["columns"],
            "JOIN physical column limit",
        )
        return body

    def join_generated(
        join_ref, kind, membership, inputs, equalities, predicate, columns, scopes
    ):
        """This JOIN's own requirement expectations, in the exact emitted order."""
        rule = (
            "R11"
            if membership is not None
            else "R09"
            if kind == "full"
            else "R08"
            if kind in {"left", "right"}
            else "R07"
        )
        row_generated.append(("join", join_ref, rule, "naming", None))
        for item in inputs:
            row_generated.append(("join_input", item["input"], "R07", "naming", None))
            if item["kind"] == "scan":
                index = item["index"]
                row_generated.append(
                    ("qualified_scan", None, "R01", ("scan", index), None)
                )
                for field in item["description"]["fields"]:
                    row_generated.append(
                        (
                            "source_representation",
                            None,
                            "R02",
                            ("field", index, field["ordinal"]),
                            None,
                        )
                    )
            elif item["kind"] == "lateral":
                row_generated.append(
                    (
                        "lateral_input",
                        ("opaque", "lateral_input"),
                        "R11",
                        "naming",
                        None,
                    )
                )
                row_generated.extend(item["generated"])
        for item in equalities:
            row_generated.append(
                ("relationship_equality", item["match"], "R07", "naming", None)
            )
        if predicate is not None:
            root_ref = (
                predicate["value"]["expression"]
                if predicate["kind"] == "constant"
                else predicate["expression"]
            )
            row_generated.append(
                (
                    "match_condition",
                    root_ref,
                    "R07",
                    row_node_premises("Bool", (), "match_condition"),
                    None,
                )
            )
            root = row_resolve(predicate, [], None, join_ref, scopes, join_ref)
            _need(
                root["tag"] == "Bool" and root["domain"]["kind"] == "bool01",
                "a JOIN matching root is not a Boolean value",
            )
        if kind == "full":
            row_generated.append(("full_condition", join_ref, "R09", "naming", None))
        if membership is not None:
            row_generated.append(("membership", join_ref, "R11", "naming", None))
            row_generated.append(("correlation", join_ref, "R11", "naming", None))
            row_generated.append(("sentinel", join_ref, "R11", "naming", None))
            right = inputs[1]
            if right.get("body") is not None and (
                right["body"].get("result") or right["body"].get("set")
            ):
                # The right side is a complete post-DISTINCT/ORDER/LIMIT terminal.
                row_generated.append(
                    ("complete_right_terminal", right["input"], "R11", "naming", None)
                )
        for item in columns:
            row_generated.append(("join_output", item["port"], "R07", "naming", None))
            if item["nulled"]:
                row_generated.append(
                    ("null_extension", item["port"], "R08", "naming", None)
                )

    def row_driver():
        """Walk every emitted stage definition once, in dependency order."""
        if peek() != "with":
            block = lexical[cursor][0]["subject"]
            if block["kind"] == "values_body":
                values_select(block, True, None)
                return
            _need(block["kind"] == "select_block", "stage body scope")
            row_select(block, True, None)
            return
        row_case_premise()
        take("syntax", "with", "WITH ", ref("selected_plan", 0))
        while True:
            index = len(row_ctes)
            separator = None
            if index:
                separator, _ = take("syntax", "cte_separator", ", ")
            name_token, name = take("identifier", "cte_name")
            block = name_token["subject"]
            _need(
                block["kind"]
                in {
                    "select_block",
                    "join",
                    "result_boundary",
                    "set_body",
                    "values_body",
                },
                "a generated CTE binds a select block, one JOIN, a result, SET or VALUES",
            )
            _need(name == f"p{index}" and name not in row_ctes, "stage CTE name")
            _need(separator is None or separator["subject"] == block, "CTE separator")
            take("syntax", "cte_columns_open", " (", block)
            header = []
            header_names = []
            header_carriers: dict[int, list[Any]] = {}
            header_ordinal = None
            while True:
                terminal_separator = None
                if header:
                    terminal_separator, _ = take("syntax", "terminal_separator", ", ")
                token, text = take("identifier", "terminal_column")
                _need(
                    text == f"c{len(header)}"
                    if block["kind"] != "join"
                    else re.fullmatch(r"c[0-9]+", text) is not None,
                    "declared terminal name",
                )
                header_names.append(text)
                _need(
                    token["subject"]["kind"]
                    in {"stage_port", "result_port", "join_port"},
                    "declared terminal kind",
                )
                _need(
                    terminal_separator is None
                    or terminal_separator["subject"] == token["subject"],
                    "terminal separator",
                )
                _need(token["subject"] not in header, "duplicate declared terminal")
                header.append(token["subject"])
                # Phase71 S08: a nested group's array columns follow its count,
                # and a collected terminal's ordinal closes the header.
                carriers = []
                while following("terminal_separator", "collect_carrier_column"):
                    carrier_separator, _ = take("syntax", "terminal_separator", ", ")
                    carrier, carrier_name = take("identifier", "collect_carrier_column")
                    _need(
                        carrier_name
                        == (
                            f"{text}_{len(carriers)}"
                            if block["kind"] == "join"
                            else f"c{len(header) - 1}_{len(carriers)}"
                        )
                        and carrier_separator["subject"] == carrier["subject"]
                        and carrier["subject"]["kind"] == "export",
                        "declared nested carrier column",
                    )
                    carriers.append(carrier["subject"])
                if carriers:
                    header_carriers[len(header) - 1] = carriers
                if following("terminal_separator", "ordinal_column"):
                    ordinal_separator, _ = take("syntax", "terminal_separator", ", ")
                    ordinal, ordinal_name = take("identifier", "ordinal_column")
                    _need(
                        ordinal_name == f"c{len(header)}"
                        and ordinal_separator["subject"] == ordinal["subject"]
                        and ordinal["subject"]["kind"] == "relation_order",
                        "declared collect ordinal column",
                    )
                    header_ordinal = ordinal["subject"]
                    break
                if peek() != "terminal_separator":
                    break
            take("syntax", "cte_body_open", ") AS (", block)
            row_scopes.append(("cte_definition", block, "R03", "naming", None))
            row_scopes.extend(
                ("terminal_column", terminal, "R03", "naming", None)
                for terminal in header
            )
            row_ctes[name] = (
                join_select(block, header, header_names)
                if block["kind"] == "join"
                else result_select(block, False, header)
                if block["kind"] == "result_boundary"
                else set_select(block, False, header)
                if block["kind"] == "set_body"
                else values_select(block, False, header)
                if block["kind"] == "values_body"
                else row_select(block, False, header)
            )
            _need(
                row_ctes[name].get("carriers", {}) == header_carriers
                and row_ctes[name].get("ordinal") == header_ordinal,
                "a CTE header declares exactly its body's nested and ordinal columns",
            )
            take("syntax", "cte_body_close", ")", block)
            if peek() != "cte_separator":
                break
        final_token, _ = take("syntax", "with_body", " ")
        final_block = final_token["subject"]
        _need(
            final_block["kind"]
            in {"select_block", "result_boundary", "set_body", "values_body"},
            "final stage scope",
        )
        if final_block["kind"] == "result_boundary":
            result_select(final_block, True, None)
        elif final_block["kind"] == "set_body":
            set_select(final_block, True, None)
        elif final_block["kind"] == "values_body":
            values_select(final_block, True, None)
        else:
            row_select(final_block, True, None)

    row_grammar = any(
        interval["role"] in {"select", "values"}
        and interval["subject"]["kind"] in {"select_block", "values_body"}
        for interval, _ in lexical
    )
    if row_grammar:
        row_driver()
        verify_having_bridges()
    elif peek() == "with":
        expected_case = (
            "quoted_exact" if family == "postgres" else "lower_case_table_names=0"
        )
        _need(
            bool(naming) and all(premises[i]["value"] == expected_case for i in naming)
        )
        take("syntax", "with", "WITH ", ref("selected_plan", 0))
        while True:
            index = len(ctes)
            definition = ref("definition", index + 1)
            if index:
                take("syntax", "cte_separator", ", ", definition)
            _, name = take("identifier", "cte_name", f"p{index}", definition)
            take("syntax", "cte_columns_open", " (", definition)
            header = []
            while True:
                term = ref("result_port", projection_count + len(header))
                if header:
                    take("syntax", "terminal_separator", ", ", term)
                take("identifier", "terminal_column", f"c{len(header)}", term)
                _need(cause(term) == cause(definition))
                header.append(term)
                if peek() != "terminal_separator":
                    break
            take("syntax", "cte_body_open", ") AS (", definition)
            columns = select(definition)
            _need(header == [c["terminal"] for c in columns])
            take("syntax", "cte_body_close", ")", definition)
            ctes[name] = {
                "definition": definition,
                "columns": columns,
                "producer": bodies[-1]["producer"],
            }
            if peek() != "cte_separator":
                break
        take("syntax", "with_body", " ", ref("definition", len(ctes) + 1))
        _need(cause(ref("definition", len(ctes) + 1)) == cause(ref("selected_plan", 0)))
    if not row_grammar:
        select(ref("selected_plan", 0), final=True)
    _need(
        cursor == len(lexical)
        and used == len(uses)
        and used_slots == set(range(len(fixed)))
    )
    # A single stage body emits no WITH, so the selected plan is not a range
    # subject there; the selected definition's own last body carries the owner.
    _need(
        cause(row_bodies[-1]["block"] if row_grammar else ref("selected_plan", 0))[
            "path"
        ]
        == document["request"]["owner"]["module"]
    )
    if not row_grammar:
        visited, previous = set(), bodies[-1]["producer"]
        while previous is not None:
            _need(previous not in visited)
            visited.add(previous)
            previous = ctes[previous]["producer"]
        _need(visited == set(ctes))
    _need(len(enclosures) == len(expected_ranges))
    for interval, (role, subject, start, end) in zip(
        enclosures, expected_ranges, strict=True
    ):
        _need(
            (interval["role"], interval["subject"], interval["start"], interval["end"])
            == (role, subject, start, end)
        )
    decoded_arguments(document)
    if row_grammar:
        # Check complete statement inventories, including windows whose results
        # are consumed by a later body rather than published as final columns.
        window_demands: dict[str, list[Any]] = {}
        for requirement in document["requirements"]:
            if (
                requirement["denominator"] == "original"
                and requirement["kind"] == "window"
            ):
                subject = requirement["subject"]
                window_demands.setdefault(subject["kind"], []).append(subject)
        expected_windows = [json.loads(key) for key in row_window_shape]
        _need(
            window_demands.get("window", []) == expected_windows,
            "statement window inventory",
        )
        for kind, count in (
            ("window_policy", len(expected_windows)),
            (
                "window_argument",
                sum(len(items) for items in row_window_arguments.values()),
            ),
            ("window_projection", row_window_projection_count[0]),
            ("window_use", sum(len(items) for items in row_window_uses.values())),
        ):
            _need(
                window_demands.get(kind, []) == [ref(kind, i) for i in range(count)],
                "statement window component inventory",
            )
        _decode_row_denominators(
            document,
            limits,
            premises,
            statements,
            scan_occurrences,
            naming,
            {
                "bodies": row_bodies,
                "source_definitions": row_source_definitions,
                "scopes": row_scopes,
                "generated": row_generated,
                "rules": row_rules,
                "filters": row_filters,
                "ports": row_stage_ports,
                "expressions": seen_expressions,
                "fixed": fixed,
                "scalar_nodes": scalar_nodes + result_nodes[0],
                "ctes": row_ctes,
                "collects": row_collects,
                "carried_collections": carried_collection_exports,
                "result_ports": sorted(result_owners),
                "unnests": row_unnests,
            },
        )
        return
    # Independent complete denominators from the parsed bodies and literal tokens.
    original_subjects = {
        "source_realization": [ref("definition", 0)],
        "export_representation": [ref("export", i) for i in range(projection_count)],
        "expression": [ref("expression", i) for i in range(expression_count)],
        "stage_value": [ref("stage_port", i) for i in range(input_count)],
        "scope": [ref("select_block", i) for i in range(len(bodies))],
        "result": [
            ref(kind, i)
            for kind in ("result_port", "result_export")
            for i in range(projection_count)
        ],
        "fixed_literal_transport": [ref("bind_use", i) for i in range(len(fixed))],
    }
    generated = []
    scan_premises = sorted([*statements, *source_positions])
    physical = _field_premises(premises, description, scan_premises, field_uses)
    for cte in ctes.values():
        generated.append(("cte_definition", "R03", cte["definition"], naming))
        generated.extend(
            ("terminal_column", "R03", c["terminal"], naming) for c in cte["columns"]
        )
    for body in bodies:
        if body["producer"] is None:
            generated.append(("qualified_scan", "R01", None, scan_premises))
            generated.extend(
                ("source_representation", "R02", None, physical[field["ordinal"]])
                for field in description["fields"]
            )
        else:
            generated.append(("named_use", "R03", body["use"], naming))
            generated.extend(
                ("immediate_terminal", "R03", c["terminal"], naming)
                for c in body["incoming"]
            )
        for column in body["columns"]:
            if column["field"] is not None:
                positions = physical[column["field"]["ordinal"]]
                generated.append(("field_projection", "R02", None, positions))
            else:
                generated.append(("value_projection", "R04", column["projection"], []))
                if column["new_value"] is not None:
                    for kind, subject, tag in column["new_value"]["requirements"]:
                        keys = {"operator_environment"}
                        if tag == "Text":
                            keys.add("client_encoding")
                        if kind == "parameter":
                            keys.add("parameter_protocol")
                        positions = [
                            i for i in statements if premises[i]["key"] in keys
                        ]
                        generated.append((kind, "R04", subject, positions))
        generated.append(("read_only_select_bytes", "R23", None, []))
    if ctes:
        generated.append(("nonrecursive_with_bytes", "R23", None, []))
    originals, actual_generated = [], []
    for requirement in document["requirements"]:
        _keys(
            requirement,
            (
                "denominator",
                "ordinal",
                "kind",
                "subject",
                "rule",
                "disposition",
                "premises",
                "evidence",
            ),
        )
        _need(
            requirement["denominator"] in {"original", "generated"}
            and requirement["disposition"] == "checked_rule"
        )
        _reference(requirement["subject"])
        _need(
            type(requirement["premises"]) is list
            and all(_ordinal(i) and i < len(premises) for i in requirement["premises"])
        )
        _need(type(requirement["evidence"]) is list)
        bucket = (
            originals if requirement["denominator"] == "original" else actual_generated
        )
        _need(
            type(requirement["ordinal"]) is int
            and requirement["ordinal"] == len(bucket)
        )
        bucket.append(requirement)
    for kind, subjects in original_subjects.items():
        actual = [r for r in originals if r["kind"] == kind]
        _need(
            Counter(encoded(r["subject"]) for r in actual)
            == Counter(encoded(s) for s in subjects)
        )
        for r in actual:
            rule = (
                "R04"
                if kind == "fixed_literal_transport"
                or kind == "expression"
                and r["subject"]["position"] in scalar_ids
                else "R03"
                if kind == "scope" and ctes
                else "R01"
                if kind in {"source_realization", "expression", "scope"}
                else "R02"
            )
            _need(r["rule"] == rule and r["premises"] == [])
    _need(len(originals) == sum(len(s) for s in original_subjects.values()))
    _need(len(generated) == len(actual_generated))
    for i, (actual, (kind, rule, subject, positions)) in enumerate(
        zip(actual_generated, generated, strict=True)
    ):
        _need(actual["kind"] == kind and actual["rule"] == rule)
        if kind not in {"literal", "unary"}:
            _need(actual["evidence"] == [])
        _need(actual["subject"] == (subject if subject is not None else ref(kind, i)))
        _need(actual["premises"] == positions)
    _need(
        3 * len(bodies)
        + 2 * projection_count
        + 2 * len(ctes)
        + sum(len(c["columns"]) for c in ctes.values())
        + scalar_nodes
        <= limits["nodes"]
    )


PARAMETERIZED_FORMAT = "pietto.sql-emission.v2"
# Header parameter carriers beyond the fixed-value tags, by family (MySQL
# emits them only in its typed cells).
PARAMETER_PHYSICAL = {
    "postgres": {
        "Decimal": "pg_numeric",
        "Date": "pg_date",
        "Timestamp": "pg_timestamp",
        "UUID": "pg_uuid",
    },
    "mysql": {
        "Decimal": "my_decimal",
        "Date": "my_date",
        "Timestamp": "my_datetime",
    },
}
BINDING_OBLIGATION_KINDS = frozenset({"int_range_representable", "text_result_width"})
# A window offset, bucket count or position (S04w): its subject is the window
# argument the parameter fills, and MySQL renders it as a bare placeholder.
COUNT_OBLIGATION = "structural_count_interval"


def _decode_parameterized_public(document, limits):
    """The v2 template as data: its header, owner-named native occurrences and
    deferred binding checks. Every placeholder is one lexical ``parameter``
    interval; a read keeps its typed anchor and one R04 requirement."""
    family = document["target"]["family"]
    sql = document["sql"].encode("utf-8")
    premises = _public_premises(document["request"]["contract"])
    statements = _statement_premises(premises, family)
    if _records(document["parameter_uses"]):
        # Only a rendered placeholder needs the protocol; an all-unread header
        # renders none (as v1 needs it only for a fixed value).
        protocols = [
            premises[i]["value"]
            for i in statements
            if premises[i]["key"] == "parameter_protocol"
        ]
        _need(
            bool(protocols)
            and all(
                v == ("postgres_extended" if family == "postgres" else "mysql_prepared")
                for v in protocols
            )
        )
    lexical, anchors, offset = [], {}, 0
    for interval in _records(document["ranges"]):
        _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
        _reference(interval["subject"])
        _need(type(interval["start"]) is int and type(interval["end"]) is int)
        _need(0 <= interval["start"] < interval["end"] <= len(sql))
        if interval["kind"] == "expression_range":
            if interval["role"] == "anchor":
                key = (interval["subject"]["kind"], interval["subject"]["position"])
                anchors[key] = (interval["start"], interval["end"])
            continue
        _need(interval["kind"] in {"identifier", "syntax", "literal", "parameter"})
        _need(interval["start"] == offset)
        offset = interval["end"]
        lexical.append(interval)
    _need(offset == len(sql))
    fixed = document["fixed_values"]
    for i, value in enumerate(_records(fixed)):
        _keys(value, ("slot", "reference", "site", "tag", "value"))
        _need(type(value["slot"]) is int and value["slot"] == i)
        _reference(value["reference"])
        _reference(value["site"])
        _need(
            value["reference"] == {"kind": "literal_slot", "position": i}
            and value["site"]["kind"] == "literal_site"
        )
        _fixed_payload(value["tag"], value["value"])
    _need(not fixed or document["request"]["literal_policy"] == "bind_safe_literals")
    header = _records(document["parameters"])
    _need(bool(header))
    # Phase77 S05: the MySQL statistic's cell declares no header parameter, so
    # no template that has one, read or not, spells a MySQL statistic.
    _need(
        family != "mysql"
        or not any(
            interval["role"] == "aggregate_open"
            and sql[interval["start"] : interval["end"]].decode()
            in MYSQL_SPREAD_FUNCTIONS
            for interval in lexical
        ),
        "mysql statistic header parameter",
    )
    names, reads = set(), {}
    for j, parameter in enumerate(header):
        _keys(parameter, ("parameter", "name", "tag", "nullable", "reads"))
        _need(
            parameter["parameter"] == j
            and type(parameter["name"]) is str
            and bool(parameter["name"])
            and parameter["name"] not in names
            and parameter["tag"]
            in {"Bool", "Int", "Float", "Text", *PARAMETER_PHYSICAL[family]}
            and type(parameter["nullable"]) is bool
        )
        names.add(parameter["name"])
        # A declared parameter may be unread; its `reads` list is then empty.
        for read in _records(parameter["reads"]):
            _reference(read)
            key = (read["kind"], read["position"])
            _need(read["kind"] in {"expression", "window_argument"})
            _need(key not in reads)
            reads[key] = j
    counts = set()
    for obligation in _records(document["binding_obligations"]):
        if type(obligation) is dict and obligation.get("kind") == COUNT_OBLIGATION:
            _reference(obligation.get("subject"))
            subject = obligation["subject"]
            counts.add((subject["kind"], subject["position"]))
    placeholders = [i for i in lexical if i["kind"] == "parameter"]
    uses = _records(document["parameter_uses"])
    _need(len(uses) == len(placeholders) and len(uses) <= limits["parameters"])
    first, seen_reads = {}, set()
    for i, (use, interval) in enumerate(zip(uses, placeholders, strict=True)):
        _keys(use, ("use", "owner", "server_index", "physical_type", "range"))
        _keys(use["range"], ("start", "end"))
        _need(
            use["use"] == i
            and use["range"] == {"start": interval["start"], "end": interval["end"]}
        )
        owner, subject = use["owner"], interval["subject"]
        if owner.get("kind") == "slot":
            _keys(owner, ("kind", "slot"))
            _need(_ordinal(owner["slot"]) and owner["slot"] < len(fixed))
            key, tag = ("slot", owner["slot"]), fixed[owner["slot"]]["tag"]
            _need(subject == fixed[owner["slot"]]["site"])
        else:
            _keys(owner, ("kind", "parameter"))
            _need(owner["kind"] == "parameter" and _ordinal(owner["parameter"]))
            _need(owner["parameter"] < len(header))
            key, tag = (
                ("parameter", owner["parameter"]),
                header[owner["parameter"]]["tag"],
            )
            read = (subject["kind"], subject["position"])
            _need(reads.get(read) == owner["parameter"] and read not in seen_reads)
            seen_reads.add(read)
            # The placeholder sits inside the read's own typed anchor; only a
            # MySQL window count is a bare placeholder.
            if family == "mysql" and read in counts:
                _need(read not in anchors and tag == "Int")
            else:
                _need(read in anchors)
                start, end = anchors[read]
                _need(start < interval["start"] and interval["end"] < end)
        _need(
            interval["role"] == tag
            and use["physical_type"]
            == (
                PARAMETER_PHYSICAL[family][tag]
                if tag in PARAMETER_PHYSICAL[family]
                else _fixed_physical(family, tag)
            )
        )
        index = first.setdefault(key, len(first) + 1) if family == "postgres" else i + 1
        _need(use["server_index"] == index)
        token = sql[interval["start"] : interval["end"]].decode()
        _need(token == ("$" + str(index) if family == "postgres" else "?"))
    _need(seen_reads == set(reads))
    described = {}
    for requirement in _records(document["requirements"]):
        if requirement.get("kind") != "query_parameter":
            continue
        _need(
            requirement["denominator"] == "generated"
            and requirement["rule"] == "R04"
            and requirement["disposition"] == "checked_rule"
        )
        subject = requirement["subject"]
        _reference(subject)
        key = (subject["kind"], subject["position"])
        _need(key in reads and key not in described)
        _need(requirement["evidence"] == [{"parameter": reads[key]}])
        described[key] = True
    _need(set(described) == set(reads))
    for k, obligation in enumerate(_records(document["binding_obligations"])):
        _keys(obligation, ("obligation", "kind", "subject", "parameters"))
        _reference(obligation["subject"])
        _need(type(obligation["parameters"]) is list)
        depends = cast(list[int], obligation["parameters"])
        subject = (obligation["subject"]["kind"], obligation["subject"]["position"])
        _need(
            obligation["obligation"] == k
            and (
                obligation["kind"] in BINDING_OBLIGATION_KINDS
                and subject[0] == "expression"
                # A count checks the one Int parameter its argument reads.
                or obligation["kind"] == COUNT_OBLIGATION
                and subject in reads
                and depends == [reads[subject]]
                and header[reads[subject]]["tag"] == "Int"
                and header[reads[subject]]["nullable"] is False
            )
            and bool(depends)
            and all(_ordinal(j) and j < len(header) for j in depends)
            and depends == sorted(set(depends))
        )
    for ordinal, column in enumerate(_records(document["columns"])):
        _keys(
            column,
            (
                "ordinal",
                "label",
                "logical_type",
                "nullable",
                "representation",
                "correspondence",
            ),
        )
        _need(
            column["ordinal"] == ordinal
            and type(column["label"]) is str
            and bool(column["label"])
        )


def decode_batch_public(data: bytes) -> dict[str, Any]:
    """Strictly decode the additive batch envelope and every contained document."""
    _need(type(data) is bytes and 0 < len(data) <= 64 * 1024 * 1024)
    try:
        document: dict[str, Any] = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
        _keys(document, ("failure", "format", "items", "status"))
        _need(
            document["format"] == "pietto.sql-emission.batch.v1"
            and document["status"] in {"VERIFIED", "BLOCKED", "INPUT_REJECTED"}
            and type(document["items"]) is list
        )
        failure = document["failure"]
        _need(failure is None or type(failure) is dict)
        failure_status = None
        if failure is not None:
            failed = decode_public(encoded(failure))
            failure_status = failed["status"]
            _need(
                failure_status != "VERIFIED"
                and (
                    not document["items"]
                    and document["status"] == failure_status
                    or (
                        document["items"]
                        and document["status"] == failure_status == "INPUT_REJECTED"
                    )
                )
            )
        statuses: list[str] = []
        owners: set[tuple[str, str, str]] = set()
        for ordinal, item in enumerate(document["items"]):
            _keys(item, ("document", "owner", "path"))
            _keys(item["owner"], ("kind", "module", "name"))
            _need(
                item["owner"]["kind"] in {"table", "query"}
                and all(
                    type(item["owner"][key]) is str and item["owner"][key]
                    for key in ("module", "name")
                )
                and item["path"] == f"artifacts/{ordinal:06d}.json"
                and type(item["document"]) is dict
            )
            identity = (
                item["owner"]["module"],
                item["owner"]["kind"],
                item["owner"]["name"],
            )
            _need(identity not in owners)
            owners.add(identity)
            child = decode_public(encoded(item["document"]))
            statuses.append(child["status"])
            if child["status"] == "VERIFIED":
                _need(child["request"]["owner"] == item["owner"])
        _need(
            (failure_status is not None and not document["items"])
            or (
                failure_status == "INPUT_REJECTED"
                and bool(statuses)
                and set(statuses) == {"VERIFIED"}
            )
            or (
                document["status"] == "VERIFIED"
                and statuses
                and set(statuses) == {"VERIFIED"}
            )
            or (
                document["status"] == "BLOCKED"
                and "BLOCKED" in statuses
                and "INPUT_REJECTED" not in statuses
            )
            or (document["status"] == "INPUT_REJECTED" and "INPUT_REJECTED" in statuses)
        )
        return document
    except (KeyError, TypeError, UnicodeDecodeError, ValueError):
        raise ValueError("invalid batch public emission document") from None


_VALIDATED_PUBLIC: set[bytes] | None = None


@contextmanager
def public_validation_memo() -> Iterator[None]:
    """Validate each distinct public artifact once inside the block.

    Validation is a pure function of the bytes, so a repeated artifact is
    decoded afresh without validating it again; no two callers share a
    document."""
    global _VALIDATED_PUBLIC
    outer = _VALIDATED_PUBLIC
    if outer is None:
        _VALIDATED_PUBLIC = set()
    try:
        yield
    finally:
        _VALIDATED_PUBLIC = outer


# S02: MySQL's guarded SUM of an Int, as (role, text) around its three
# argument reads; restated here, never imported from the emitter.
MYSQL_SUM_GUARD = (
    ("aggregate_guard_open", "CASE WHEN SUM("),
    (
        "aggregate_guard_high",
        ") > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED)"
        " + CAST(1 AS SIGNED) WHEN SUM(",
    ),
    (
        "aggregate_guard_low",
        ") < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED)"
        " - CAST(1 AS SIGNED) ELSE CAST(SUM(",
    ),
    ("aggregate_guard_close", ") AS SIGNED) END"),
)


def decode_public(data: bytes) -> dict[str, Any]:
    """Validate data only. A decoded document grants no compiler authority."""
    validated = _VALIDATED_PUBLIC
    if validated is not None and type(data) is bytes and data in validated:
        return json.loads(data.decode("utf-8"))
    document = _validated_public(data)
    if validated is not None:
        validated.add(data)
    return document


def _validated_public(data: bytes) -> dict[str, Any]:
    _need(type(data) is bytes and len(data) <= 16 * 1024 * 1024)
    try:
        document: dict[str, Any] = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
        _need(
            type(document) is dict
            and document.get("format")
            in {"pietto.sql-emission.v1", PARAMETERIZED_FORMAT}
        )
        status = document.get("status")
        _need(status in {"VERIFIED", "INPUT_REJECTED", "BLOCKED"})
        # Only a VERIFIED query with a parameter header is v2 (D70.02).
        parameterized = document["format"] == PARAMETERIZED_FORMAT
        _need(not parameterized or status == "VERIFIED")
        _need(type(document.get("diagnostics")) is list)
        for diagnostic in document["diagnostics"]:
            _keys(diagnostic, ("code", "severity", "message", "location", "suggestion"))
            _need(
                type(diagnostic["code"]) is str
                and re.fullmatch(r"PIE-[PSIBR][0-9]{4}", diagnostic["code"]) is not None
            )
            _need(
                diagnostic["severity"] in {"error", "warning", "info"}
                and type(diagnostic["message"]) is str
            )
            _need(
                diagnostic["suggestion"] is None
                or type(diagnostic["suggestion"]) is str
            )
            _location(diagnostic["location"])
        if status != "VERIFIED":
            _keys(
                document,
                (
                    "format",
                    "status",
                    "artifact",
                    "blockers",
                    "diagnostics",
                    "cli_errors",
                ),
            )
            _need(
                document["artifact"] is None
                and type(document["blockers"]) is list
                and type(document["cli_errors"]) is list
            )
            for blocker in _records(document["blockers"]):
                _keys(
                    blocker,
                    ("code", "reason", "subject", "location", "related", "suggestion"),
                )
                _need(
                    type(blocker["suggestion"]) is str
                    and bool(blocker["suggestion"].strip())
                )
                blocker["suggestion"].encode("utf-8")
                _need(
                    type(blocker["code"]) is str
                    and CODES.get(blocker["code"]) == blocker["reason"]
                )
                _keys(blocker["subject"], ("reference", "detail"))
                _reference(blocker["subject"]["reference"])
                _need(type(blocker["subject"]["detail"]) is str)
                _location(blocker["location"])
                _need(type(blocker["related"]) is list)
                for location in blocker["related"]:
                    _location(location)
            for error in _records(document["cli_errors"]):
                _keys(error, ("kind", "message", "path"))
                _need(
                    error["kind"] in CLI_ERROR_KINDS and type(error["message"]) is str
                )
                _need(error["path"] is None or type(error["path"]) is str)
            _need(bool(document["cli_errors"]) == (status == "INPUT_REJECTED"))
            _need(
                status == "INPUT_REJECTED"
                or document["blockers"]
                or any(d["severity"] == "error" for d in document["diagnostics"])
            )
            return document
        _keys(
            document,
            (
                "format",
                "status",
                "target",
                "request",
                "sql",
                "fixed_values",
                "parameter_uses",
                "columns",
                "ranges",
                "requirements",
                "diagnostics",
                *(("parameters", "binding_obligations") if parameterized else ()),
            ),
        )
        _need(
            type(document["fixed_values"]) is list
            and type(document["parameter_uses"]) is list
        )
        _need(not any(d["severity"] == "error" for d in document["diagnostics"]))
        target, request = document["target"], document["request"]
        _keys(target, ("family", "release", "environment"))
        _need(
            (target["family"], target["release"])
            in {("postgres", "18.6"), ("mysql", "8.4.12")}
        )
        _keys(request, ("owner", "sources", "contract", "literal_policy"))
        _keys(request["owner"], ("module", "kind", "name"))
        _need(request["owner"]["kind"] in {"table", "query"})
        _need(
            all(
                type(request["owner"][k]) is str and request["owner"][k]
                for k in ("module", "name")
            )
        )
        _need(request["literal_policy"] in {"preserve_literals", "bind_safe_literals"})
        _need(type(request["sources"]) is list and bool(request["sources"]))
        modules = set()
        for source in request["sources"]:
            _keys(source, ("module", "sha256", "byte_count"))
            _need(
                type(source["module"]) is str
                and bool(source["module"])
                and source["module"] not in modules
                and type(source["sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None
                and _ordinal(source["byte_count"])
            )
            modules.add(source["module"])
        _need(request["owner"]["module"] in [s["module"] for s in request["sources"]])
        contract = request["contract"]
        _contract_shape(contract)
        _keys(contract, ("format", "target", "sources", "environment"))
        _need(
            contract["format"] == "pietto.emission-contract.v1"
            and contract["target"]
            == {"family": target["family"], "release": target["release"]}
            and contract["environment"] == target["environment"]
        )
        _need(
            type(document["sql"]) is str
            and type(document["columns"]) is list
            and bool(document["columns"])
        )
        sql = document["sql"].encode("utf-8")
        named = sql.startswith(b"WITH ")
        all_premises = _public_premises(contract)
        limits = {
            "sql_bytes": 8 * 1024 * 1024,
            "artifact_bytes": 16 * 1024 * 1024,
            "nodes": 32768,
            "parameters": 65535,
            "columns": 1664 if target["family"] == "postgres" else 4096,
        }
        for premise in all_premises:
            if premise["key"] == "resource_limits" and premise["scope"] == "statement":
                for key, value in premise["value"].items():
                    limits[key] = min(limits[key], value)
        _need(len(sql) <= limits["sql_bytes"] and len(data) <= limits["artifact_bytes"])
        _need(len(document["columns"]) <= limits["columns"])
        _need(
            type(document["ranges"]) is list and type(document["requirements"]) is list
        )
        sources = _records(contract["sources"])
        # Only a statement that reads a physical relation needs a contract
        # source; a VALUES-only statement compiles with none.
        _need(
            bool(sources)
            or not any(
                type(interval.get("subject")) is dict
                and interval["subject"].get("kind") == "source_port"
                for interval in _records(document["ranges"])
            )
        )
        if parameterized:
            _decode_parameterized_public(document, limits)
            return document
        if any(
            interval.get("kind") in {"literal", "parameter", "expression_range"}
            for interval in _records(document["ranges"])
        ):
            _decode_fixed_public(document, limits)
            return document
        _need(document["fixed_values"] == [] and document["parameter_uses"] == [])
        fields = []
        for ordinal, column in enumerate(document["columns"]):
            _keys(
                column,
                (
                    "ordinal",
                    "label",
                    "logical_type",
                    "nullable",
                    "representation",
                    "correspondence",
                ),
            )
            _need(
                type(column["ordinal"]) is int
                and column["ordinal"] == ordinal
                and type(column["label"]) is str
                and bool(column["label"])
            )
            _keys(column["logical_type"], ("kind", "name", "parameters"))
            _need(
                column["logical_type"]["kind"] == "builtin"
                and column["logical_type"]["name"]
                in {
                    "Int",
                    "Bool",
                    "Text",
                    "Decimal",
                    "Float",
                    "Timestamp",
                    "Date",
                    "UUID",
                }
            )
            correspondence = column["correspondence"]
            _keys(
                correspondence,
                (
                    "source",
                    "field",
                    "source_port",
                    "input_port",
                    "export",
                    "projection",
                    "sql_symbol",
                ),
            )
            _need(
                _ordinal(correspondence["field"])
                and type(correspondence["sql_symbol"]) is int
                and correspondence["sql_symbol"] == ordinal + 1
            )
            for key in ("source_port", "input_port", "export", "projection"):
                _reference(correspondence[key])
                _need(correspondence[key]["kind"] == key)
                if not named or key == "source_port":
                    _need(
                        correspondence[key]["position"]
                        == (
                            correspondence["field"]
                            if key in {"source_port", "input_port"}
                            else ordinal
                        )
                    )
            matches = [s for s in sources if s["selector"] == correspondence["source"]]
            _need(len(matches) == 1)
            description = matches[0]
            _keys(description, ("selector", "relation", "scan", "fields", "premises"))
            _need(
                description["scan"] == "relation_rows"
                and type(description["fields"]) is list
            )
            _need(correspondence["field"] < len(description["fields"]))
            field = description["fields"][correspondence["field"]]
            _keys(field, ("ordinal", "name", "column", "representation"))
            # JSON type equality matters: a copied dictionary is not a check.
            _need(
                field["ordinal"] == correspondence["field"]
                and encoded(column["representation"])
                == encoded(field["representation"])
            )
            _keys(column["representation"], ("storage", "nullable", "domain"))
            _need(
                encoded(column["logical_type"])
                == encoded(
                    _field_compatibility(field["representation"], target["family"])
                ),
                "declared output type is not the physical source type",
            )
            _need(
                column["nullable"] == column["representation"]["nullable"]
                and (
                    type(column["nullable"]) is bool or column["nullable"] == "unknown"
                )
            )
            fields.append((column, description, field))
        _need(all(item[1] is fields[0][1] for item in fields))
        # The same selected scan, field law and premise obligations as the
        # literal-containing grammar; a grammar never owns a weaker contract.
        description, source_positions, statements = _selected_scan(
            document, contract, all_premises, target["family"]
        )
        _need(description is fields[0][1], "selected scan is not the projected source")
        scan_premises = sorted([*statements, *source_positions])
        for field in fields[0][1]["fields"]:
            _field_compatibility(field["representation"], target["family"])
        ranges = iter(document["ranges"])
        offset = 0

        def token(kind, role, expected, subject):
            nonlocal offset
            interval = next(ranges)
            _keys(interval, ("start", "end", "kind", "role", "subject", "origins"))
            _need(
                type(interval["start"]) is int
                and type(interval["end"]) is int
                and interval["start"] == offset
                and offset < interval["end"] <= len(sql)
            )
            _need((interval["kind"], interval["role"]) == (kind, role))
            _reference(interval["subject"])
            _need(interval["subject"] == subject)
            _need(type(interval["origins"]) is list)
            for origin in interval["origins"]:
                _keys(origin, ("position", "role", "sources"))
                _need(
                    _ordinal(origin["position"])
                    and type(origin["role"]) is str
                    and type(origin["sources"]) is list
                )
                for source in origin["sources"]:
                    _keys(source, ("path", "kind", "location"))
                    _need(type(source["path"]) is str and type(source["kind"]) is str)
                    _location(source["location"])
            text = sql[offset : interval["end"]].decode("utf-8")
            if kind == "identifier":
                _need(_identifier_token(text, target["family"], role) == expected)
            else:
                _need(text == expected)
            offset = interval["end"]

        if not named:
            token(
                "syntax", "select", "SELECT ", {"kind": "selected_plan", "position": 0}
            )
            for i, (column, description, field) in enumerate(fields):
                if i:
                    token(
                        "syntax",
                        "separator",
                        ", ",
                        column["correspondence"]["projection"],
                    )
                token(
                    "identifier",
                    "column_scope",
                    "s0",
                    column["correspondence"]["input_port"],
                )
                token(
                    "syntax", "qualifier", ".", column["correspondence"]["projection"]
                )
                token(
                    "identifier",
                    "column",
                    field["column"],
                    column["correspondence"]["source_port"],
                )
                token("syntax", "alias", " AS ", column["correspondence"]["projection"])
                token(
                    "identifier",
                    "label",
                    column["label"],
                    column["correspondence"]["export"],
                )
            definition = {"kind": "definition", "position": 0}
            use = {"kind": "input_use", "position": 0}
            token("syntax", "from", " FROM ", definition)
            token(
                "identifier",
                "namespace",
                fields[0][1]["relation"]["namespace"],
                definition,
            )
            token("syntax", "qualifier", ".", definition)
            token(
                "identifier", "relation", fields[0][1]["relation"]["name"], definition
            )
            token("syntax", "alias", " AS ", use)
            token("identifier", "relation_scope", "s0", use)
            _need(next(ranges, None) is None and offset == len(sql))
        original, generated = [], []
        for requirement in _records(document["requirements"]):
            _keys(
                requirement,
                (
                    "denominator",
                    "ordinal",
                    "kind",
                    "subject",
                    "rule",
                    "disposition",
                    "premises",
                    "evidence",
                ),
            )
            _need(
                requirement["denominator"] in {"original", "generated"}
                and requirement["rule"]
                in ({"R01", "R02", "R03", "R23"} if named else {"R01", "R02", "R23"})
                and requirement["disposition"] == "checked_rule"
            )
            _reference(requirement["subject"])
            _need(
                type(requirement["premises"]) is list
                and all(_ordinal(v) for v in requirement["premises"])
                and type(requirement["evidence"]) is list
            )
            bucket = original if requirement["denominator"] == "original" else generated
            _need(
                type(requirement["ordinal"]) is int
                and requirement["ordinal"] == len(bucket)
            )
            bucket.append(requirement)
        if not named:
            n = len(fields)
            _need(3 + 2 * n <= limits["nodes"])
            expected_original = Counter(
                {
                    "source_realization": 1,
                    "export_representation": n,
                    "expression": n,
                    "stage_value": len(fields[0][1]["fields"]),
                    "scope": 1,
                    "result": 2 * n,
                }
            )
            expected_generated = [
                ("qualified_scan", "R01", None, "scan"),
                *[
                    ("source_representation", "R02", None, ("field", f["ordinal"]))
                    for f in fields[0][1]["fields"]
                ],
                *[
                    (
                        "field_projection",
                        "R02",
                        None,
                        ("field", c["correspondence"]["field"]),
                    )
                    for c, _, _ in fields
                ],
                ("read_only_select_bytes", "R23", None, "none"),
            ]
            field_uses = [
                (
                    c["correspondence"]["field"],
                    c["correspondence"]["projection"]["position"],
                    0,
                )
                for c, _, _ in fields
            ]
        else:
            expected_original, expected_generated, field_uses = _decode_named_sql(
                document, fields, limits
            )
        _need(
            Counter(r["kind"] for r in original) == expected_original,
            "original requirement denominator",
        )
        for requirement in original:
            expected_rule = (
                "R03"
                if named and requirement["kind"] == "scope"
                else "R01"
                if requirement["kind"] in {"source_realization", "expression", "scope"}
                else "R02"
            )
            _need(requirement["rule"] == expected_rule)
        _need(
            len(generated) == len(expected_generated),
            "generated requirement denominator",
        )
        naming = [
            i
            for i, premise in enumerate(all_premises)
            if premise["key"] == "identifier_case" and premise["scope"] == "statement"
        ]
        # This grammar has exactly one physical scan occurrence, so it resolves its
        # premise sentinels through the same occurrence-indexed shape the staged
        # grammar uses rather than a second, flat convention.
        occurrence_premises = [scan_premises]
        physical = [
            _field_premises(all_premises, description, scan_premises, field_uses)
        ]
        for i, (actual, (kind, rule, subject, key)) in enumerate(
            zip(generated, expected_generated, strict=True)
        ):
            _need(actual["kind"] == kind and actual["rule"] == rule)
            _need(
                actual["premises"]
                == _requirement_premises(key, naming, occurrence_premises, physical),
                "requirement premise domain",
            )
            _need(
                actual["subject"]
                == (subject if subject is not None else {"kind": kind, "position": i})
            )
        return document
    except (
        KeyError,
        IndexError,
        TypeError,
        StopIteration,
        UnicodeError,
        RecursionError,
    ) as error:
        raise ValueError("malformed public emission artifact") from error


def inspect_case(outcome, data):
    """Exercise the private runtime view against the data-only decoding of `data`.

    Runs inside the generation child while the runtime artifact still exists, so
    the view is bound before the public record leaves the process. Every check is
    a bounded scan of the retained ranges; a drift raises and fails generation.
    A failure outcome has no artifact and no view.
    """
    from pietto._project.project_sql_emission_inspection import (
        inspect_project_sql_emission,
    )

    artifact = outcome.artifact
    if artifact is None:
        return None
    view = inspect_project_sql_emission(artifact, artifact.request)
    document = decode_public(data)
    drift = "runtime inspection drift"
    _need(document["status"] == "VERIFIED", drift)
    _need(view.sql == document["sql"].encode("utf-8"), drift)
    _need(len(view.ranges) == len(document["ranges"]), drift)
    for item, described in zip(view.ranges, document["ranges"], strict=True):
        _need(
            (item.start, item.end, item.kind, item.role)
            == (
                described["start"],
                described["end"],
                described["kind"],
                described["role"],
            ),
            drift,
        )
        _need(len(item.origins) == len(described["origins"]), drift)
        for (entry, associations), origin in zip(
            item.origins, described["origins"], strict=True
        ):
            _need(entry.position == origin["position"], drift)
            _need(len(associations) == len(origin["sources"]), drift)
    _need(
        [column.label for column in view.columns]
        == [column["label"] for column in document["columns"]],
        drift,
    )
    _need(len(view.parameter_uses) == len(document["parameter_uses"]), drift)
    for (use, token), described in zip(
        view.parameter_uses, document["parameter_uses"], strict=True
    ):
        _need(
            (use.server_index, token.start, token.end)
            == (
                described["server_index"],
                described["range"]["start"],
                described["range"]["end"],
            ),
            drift,
        )
        _need(token in view.at(token.start), drift)
        _need(token in view.ranges_of(token.subject), drift)
    for item in (view.ranges[0], view.ranges[-1]):
        _need(item in view.at(item.start), drift)
        _need(item in view.overlapping(item.start, item.end), drift)
        _need(item in view.ranges_of(item.subject), drift)
    _need(view.at(len(view.sql)) == (), drift)
    return view


def block_reads(query):
    """Every expression block read of one realized statement, in no order."""
    import dataclasses

    from pietto._project.project_sql_emission_rows import SQLBlockRead

    found, pending, seen = [], [query], set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is SQLBlockRead:
            found.append(value)
        if type(value) is tuple:
            pending.extend(value)
        elif type(value).__module__.startswith(
            "pietto._project.project_sql_emission"
        ) and dataclasses.is_dataclass(value):
            pending.extend(getattr(value, f.name) for f in dataclasses.fields(value))
    return found


# One source of exact Q3/Date carriers beside a signed int4, for both targets.
TEMPORAL_FIELDS = (
    ("id", "Int", False),
    ("ts", "Timestamp", False),
    ("ts2", "Timestamp", True),
    ("d", "Date", False),
    ("d2", "Date", True),
    ("u", "UUID", False),
)


def temporal_case(
    directory,
    target,
    body,
    policy="preserve_literals",
    *,
    representations=None,
    fields=TEMPORAL_FIELDS,
    entry="table result:",
    environment=(),
    modules=None,
):
    """Build ``entry`` (``body`` is its indented block) over ``fields``
    (default ``TEMPORAL_FIELDS``) with the base fixture's premises and
    ``environment`` after them; ``representations`` replaces named fields'
    contract representations and ``modules`` adds other modules beside
    main.pietto."""
    contract = json.loads(fixture(target, "T_row_direct", "table_preserve")["contract"])
    pg = target == "postgres"
    physical = {
        "Int": (
            {"kind": "pg_int4" if pg else "my_int"},
            {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
        ),
        "Timestamp": (
            {"kind": "pg_timestamp" if pg else "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "Date": ({"kind": "pg_date" if pg else "my_date"}, {"kind": "date"}),
        "UUID": (
            {"kind": "pg_uuid" if pg else "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
        "Decimal(9, 2)": (
            {"kind": "pg_numeric" if pg else "my_decimal", "precision": 9, "scale": 2},
            {"kind": "decimal", "precision": 9, "scale": 2},
        ),
    }
    contract["sources"][0]["fields"] = [
        {
            "ordinal": i,
            "name": name,
            "column": name,
            "representation": {
                "storage": physical[kind][0],
                "nullable": nullable,
                "domain": physical[kind][1],
            },
        }
        for i, (name, kind, nullable) in enumerate(fields)
    ]
    for field in contract["sources"][0]["fields"]:
        field["representation"] = (representations or {}).get(
            field["name"], field["representation"]
        )
    contract["environment"].extend(environment)
    source = (
        "shape Row:\n"
        + "".join(
            f"    {name}: {kind}{' | None' if nullable else ''}\n"
            for name, kind, nullable in fields
        )
        + f'source rows: Row = {target}.table("opaque.locator.not.sql")\n'
        + entry
        + "\n"
        + body
    )
    files = {"main.pietto": source, **(modules or {})}
    directory.mkdir(parents=True, exist_ok=True)
    # The contract beside the modules, for a public compile of the project.
    (directory / "contract.json").write_bytes(encoded(contract))
    return build_case(directory, files, encoded(contract).decode(), policy)


def build_case(
    directory, source, contract, policy="preserve_literals", *, target_request=None
):
    # Imported only in the generation child or explicit offline behavior tests.
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
    from pietto._project.project_sql_emission import emit_project_sql

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(CONFIG)
    for name, content in sorted(source_files(source).items()):
        if Path(name).name != name or not name.endswith(".pietto"):
            raise ValueError("closed fixture module path required")
        (directory / name).write_text(content, encoding="utf-8", newline="\n")
    parsed = check_project_parse_only(directory)
    if not parsed.ok:
        raise ValueError("probe source failed parsing")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    if type(completed) is not ProjectConcreteCompletedSemanticResult:
        raise ValueError("probe completion has no concrete root")
    ir = build_project_query_block_ir(completed)
    checked_ir = verify_project_query_block_ir(ir)
    bundle = build_project_query_block_ir_analysis_bundle(checked_ir)
    owners = tuple(owner for owner in ir.owners if owner.definition.name == "result")
    if len(owners) != 1:
        raise ValueError("probe selection is not unique")
    selected = owners[0]
    literal_policy = ProjectSQLLiteralPolicy(policy)
    plan = build_project_sql_plan(
        completed, bundle, selected, literal_policy=literal_policy
    )
    checked = verify_project_sql_plan(
        plan, completed, bundle, selected, literal_policy=literal_policy
    )
    return checked, emit_project_sql(
        checked,
        contract.encode() if type(contract) is str else contract,
        target_request=target_request,
    )


def installed_origins():
    """Wheel-relative origins of every pietto module this child actually loaded."""
    origins = {}
    prefix = Path(sys.prefix).resolve()
    for name, module in tuple(sys.modules.items()):
        if name == "pietto" or name.startswith("pietto."):
            filename = getattr(module, "__file__", None)
            if filename:
                path = Path(filename).resolve()
                if not path.is_relative_to(prefix) or "site-packages" not in path.parts:
                    raise ValueError("checkout production import")
                index = path.parts.index("site-packages")
                origins[name] = {
                    "member": "/".join(path.parts[index + 1 :]),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
    return origins


def console_main(target, console):
    """Run the installed console entrypoint with real argv over real project files."""
    import contextlib
    import io
    import runpy

    console_path = Path(console).resolve()
    if not console_path.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("foreign console")
    records = []
    for item, (_, case, variant, kind, presentation, output) in zip(
        console_inputs(target), CONSOLE_WITNESSES, strict=True
    ):
        fixture_item = fixture(target, case, variant)
        with TemporaryDirectory(prefix="console-", dir=Path.cwd()) as scratch:
            root = Path(scratch)
            (root / "pietto.toml").write_text(CONFIG)
            for name, content in sorted(source_files(fixture_item["source"]).items()):
                (root / name).write_text(content, encoding="utf-8")
            (root / "contract.json").write_text(
                fixture_item["contract"], encoding="utf-8"
            )
            artifact = root / "artifact.json"
            argv = [
                str(console_path),
                "emit-sql",
                "--project",
                root.name,
                "--module",
                "main.pietto",
                "--kind",
                kind,
                "--name",
                "result",
                "--dialect",
                target,
                "--emission-contract",
                "contract.json",
                "--format",
                presentation,
            ]
            if fixture_item["policy"] == "bind_safe_literals":
                argv += ["--literal-policy", "bind-safe"]
            if output:
                argv += ["--output", str(Path(root.name) / "artifact.json")]
            out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")
            err = io.StringIO()
            saved = sys.argv
            sys.argv = argv
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        runpy.run_path(str(console_path), run_name="__main__")
                    except SystemExit as exit_request:
                        code = exit_request.code
                        status = code if type(code) is int else 0 if code is None else 1
                    else:
                        status = 0
            finally:
                sys.argv = saved
            out.flush()
            stdout = out.buffer.getvalue().decode("utf-8")
            artifact_text = (
                artifact.read_text(encoding="utf-8") if artifact.exists() else None
            )
        # The receipt keeps the console document by SHA-256 against the API record
        # of the same input (whose full bytes the receipt already carries); only
        # the text presentation is retained verbatim.
        public = artifact_text if output else stdout
        records.append(
            {
                **item,
                "exit_code": status,
                "stderr": err.getvalue(),
                "stdout": stdout if presentation == "text" else None,
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "artifact_sha256": None
                if artifact_text is None
                else hashlib.sha256(artifact_text.encode()).hexdigest(),
                "public_sha256": hashlib.sha256((public or "").encode()).hexdigest(),
            }
        )
    print(
        encoded(
            {
                "records": records,
                "origins": installed_origins(),
                "isolated": sys.flags.isolated,
                "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "config_sha256": hashlib.sha256(CONFIG.encode()).hexdigest(),
                "console_sha256": hashlib.sha256(console_path.read_bytes()).hexdigest(),
            }
        ).decode(),
        end="",
    )


def main():
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    if sys.flags.isolated != 1 or sys.argv[1:2] not in (["postgres"], ["mysql"]):
        raise ValueError("closed isolated emission probe required")
    if len(sys.argv) == 4 and sys.argv[2] == "console":
        console_main(sys.argv[1], sys.argv[3])
        return
    if len(sys.argv) != 2:
        raise ValueError("closed isolated emission probe required")
    target = sys.argv[1]
    records = []
    for item in generation_inputs(target):
        with TemporaryDirectory(prefix="emission-", dir=Path.cwd()) as scratch:
            _, outcome = build_case(
                Path(scratch), item["source"], item["contract"], item["policy"]
            )
            data = serialize_project_sql_emission(outcome)
            # The runtime view is bound and checked here, in the same child,
            # before this case's public record is exported.
            inspect_case(outcome, data)
            records.append(
                {
                    "id": item["id"],
                    "variant": item["variant"],
                    "source_sha256": hashlib.sha256(
                        source_bytes(item["source"])
                    ).hexdigest(),
                    "contract_sha256": hashlib.sha256(
                        item["contract"].encode()
                    ).hexdigest(),
                    "public": data.decode(),
                    "public_sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    print(
        encoded(
            {
                "records": records,
                "origins": installed_origins(),
                "isolated": sys.flags.isolated,
                "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "config_sha256": hashlib.sha256(CONFIG.encode()).hexdigest(),
            }
        ).decode(),
        end="",
    )


if __name__ == "__main__":
    main()


S05_POSTGRES_BODY = """table result:
    from rows
    let plus_id = money + id
    let left_literal = 1 + money
    select:
        plus_id
        left_literal
"""


def emit_aggregate_composition(
    tmp_path, body, *, target="postgres", policy="preserve_literals"
):
    item = aggregate_fixture(target, "X_aggregate_global", "bag")
    source = item["source"].split("query result:", 1)[0] + body
    contract = json.loads(item["contract"])
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended" if target == "postgres" else "mysql_prepared",
        }
    )
    return build_case(tmp_path, source, encoded(contract), policy)


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


# Phase77 S01/S02: one source over the native qualification's carriers: `a`
# and `b` nullable BIGINT over all of signed 64 bits, `k` a non-null INT
# (PostgreSQL integer) group key, `id` and `n` non-null BIGINT and `c` a
# nullable INT.
NUMERIC_HEADER = """shape Row:
    id: Int
    a: Int | None
    b: Int | None
    k: Int
    n: Int
    c: Int | None
source rows: Row = {target}.table("opaque.locator.not.sql")
"""


def numeric_world(directory, target, body, policy="preserve_literals"):
    """``body`` over NUMERIC_HEADER's source, with exact identifier case and
    the native parameter protocol; a dict ``body`` maps module paths to their
    text, main.pietto's after the header."""
    contract = json.loads(fixture(target)["contract"])
    contract["environment"] += [
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        },
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended" if target == "postgres" else "mysql_prepared",
        },
    ]
    wide, narrow = (
        ("pg_int8", "pg_int4")
        if target == "postgres"
        else (
            "my_bigint",
            "my_int",
        )
    )
    ranges = {
        wide: {"kind": "int_range", "min": str(-(1 << 63)), "max": str((1 << 63) - 1)},
        narrow: {
            "kind": "int_range",
            "min": str(-(1 << 31)),
            "max": str((1 << 31) - 1),
        },
    }
    contract["sources"][0]["fields"] = [
        {
            "ordinal": ordinal,
            "name": name,
            "column": column,
            "representation": {
                "storage": {"kind": kind},
                "nullable": nullable,
                "domain": ranges[kind],
            },
        }
        for ordinal, (name, column, kind, nullable) in enumerate(
            (
                ("id", "id", wide, False),
                ("a", "left_value", wide, True),
                ("b", "right_value", wide, True),
                ("k", "group_key", narrow, False),
                ("n", "nn", wide, False),
                ("c", "narrow", narrow, True),
            )
        )
    ]
    files = dict(body) if type(body) is dict else {"main.pietto": body}
    files["main.pietto"] = NUMERIC_HEADER.format(target=target) + files.get(
        "main.pietto", ""
    )
    return build_case(directory, files, encoded(contract).decode(), policy)


# The bodies whose MySQL `Int` sign, arithmetic, `abs` (S01) and `sum(Int)`
# (S02) are in their cells, the SQL each emits (also the candidate emission
# experiment's byte source), other spellings of a cell, and refused bodies
# with the MySQL blockers (code, detail, line, column) main reports for them,
# under either literal policy.
NUMERIC_CELLS = {
    "s01_families": "query result:\n    from rows\n    select:\n        id\n        s = a + b\n        d = a - b\n        m = a * b\n        neg = -a\n        ab = abs(b)\n        p = +a\n        aa = a + a\n",
    "s01_where": "query result:\n    from rows\n    where id > 3\n    select:\n        s = a + b\n",
    "s01_table": "table result:\n    from rows\n    select:\n        m = a * b\n",
    "s01_beside_field": "query result:\n    from rows\n    select:\n        a\n        neg = -b\n",
    "s02_scalar": "query result:\n    from rows\n    select:\n        total = sum(a)\n",
    "s02_where": "query result:\n    from rows\n    where id > 3\n    select:\n        total = sum(a)\n",
    "s02_grouped": "query result:\n    from rows\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    "s02_unselected_key": "query result:\n    from rows\n    group by k\n    select:\n        total = sum(a)\n",
    "s02_two_sums": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n        y = sum(b)\n",
    "s02_beside_count": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n        c2 = count(b)\n        lo = min(a)\n",
    "s02_bigint_key": "query result:\n    from rows\n    group by n\n    select:\n        n\n        x = sum(a)\n",
    "s02_key_alias": "query result:\n    from rows\n    group by k\n    select:\n        kk = k\n        x = sum(a)\n",
}
NUMERIC_CELL_SQL = {
    ("s01_families", "postgres"): (
        'SELECT "s0"."id" AS "id", ("s0"."left_value" + "s0"."right_value") AS "s", ("s0"."left_value" - "s0"."right_value") AS "d", ("s0"."left_value" * "s0"."right_value") AS "m", (-"s0"."left_value") AS "neg", abs("s0"."right_value") AS "ab", (+"s0"."left_value") AS "p", ("s0"."left_value" + "s0"."left_value") AS "aa" FROM "public"."phase66 source é" AS "s0"'
    ),
    ("s01_families", "mysql"): (
        "SELECT `s0`.`id` AS `id`, (`s0`.`left_value` + `s0`.`right_value`) AS `s`, (`s0`.`left_value` - `s0`.`right_value`) AS `d`, (`s0`.`left_value` * `s0`.`right_value`) AS `m`, (-`s0`.`left_value`) AS `neg`, ABS(`s0`.`right_value`) AS `ab`, (+`s0`.`left_value`) AS `p`, (`s0`.`left_value` + `s0`.`left_value`) AS `aa` FROM `phase66`.`phase66 source é` AS `s0`"
    ),
    ("s01_where", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."id" AS "c0", "s0"."left_value" AS "c1", "s0"."right_value" AS "c2", "s0"."group_key" AS "c3", "s0"."nn" AS "c4", "s0"."narrow" AS "c5" FROM "public"."phase66 source é" AS "s0" WHERE ("s0"."id" > CAST(3 AS pg_catalog.int8))) SELECT ("t1"."c1" + "t1"."c2") AS "s" FROM "p0" AS "t1"'
    ),
    ("s01_where", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`id` AS `c0`, `s0`.`left_value` AS `c1`, `s0`.`right_value` AS `c2`, `s0`.`group_key` AS `c3`, `s0`.`nn` AS `c4`, `s0`.`narrow` AS `c5` FROM `phase66`.`phase66 source é` AS `s0` WHERE (`s0`.`id` > CAST(3 AS SIGNED))) SELECT (`t1`.`c1` + `t1`.`c2`) AS `s` FROM `p0` AS `t1`"
    ),
    ("s01_table", "postgres"): (
        'SELECT ("s0"."left_value" * "s0"."right_value") AS "m" FROM "public"."phase66 source é" AS "s0"'
    ),
    ("s01_table", "mysql"): (
        "SELECT (`s0`.`left_value` * `s0`.`right_value`) AS `m` FROM `phase66`.`phase66 source é` AS `s0`"
    ),
    ("s01_beside_field", "postgres"): (
        'SELECT "s0"."left_value" AS "a", (-"s0"."right_value") AS "neg" FROM "public"."phase66 source é" AS "s0"'
    ),
    ("s01_beside_field", "mysql"): (
        "SELECT `s0`.`left_value` AS `a`, (-`s0`.`right_value`) AS `neg` FROM `phase66`.`phase66 source é` AS `s0`"
    ),
    ("s02_scalar", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c0" FROM "public"."phase66 source é" AS "s0") SELECT "t1"."c0" AS "total" FROM "p0" AS "t1"'
    ),
    ("s02_scalar", "mysql"): (
        "WITH `p0` (`c0`) AS (SELECT CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c0` FROM `phase66`.`phase66 source é` AS `s0`) SELECT `t1`.`c0` AS `total` FROM `p0` AS `t1`"
    ),
    ("s02_where", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."id" AS "c0", "s0"."left_value" AS "c1", "s0"."right_value" AS "c2", "s0"."group_key" AS "c3", "s0"."nn" AS "c4", "s0"."narrow" AS "c5" FROM "public"."phase66 source é" AS "s0" WHERE ("s0"."id" > CAST(3 AS pg_catalog.int8))), "p1" ("c0") AS (SELECT CAST(SUM(CAST("t1"."c1" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c0" FROM "p0" AS "t1") SELECT "t2"."c0" AS "total" FROM "p1" AS "t2"'
    ),
    ("s02_where", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`id` AS `c0`, `s0`.`left_value` AS `c1`, `s0`.`right_value` AS `c2`, `s0`.`group_key` AS `c3`, `s0`.`nn` AS `c4`, `s0`.`narrow` AS `c5` FROM `phase66`.`phase66 source é` AS `s0` WHERE (`s0`.`id` > CAST(3 AS SIGNED))), `p1` (`c0`) AS (SELECT CASE WHEN SUM(`t1`.`c1`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`t1`.`c1`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`t1`.`c1`) AS SIGNED) END AS `c0` FROM `p0` AS `t1`) SELECT `t2`.`c0` AS `total` FROM `p1` AS `t2`"
    ),
    ("s02_grouped", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."group_key" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."group_key") SELECT "t1"."c0" AS "k", "t1"."c1" AS "total" FROM "p0" AS "t1"'
    ),
    ("s02_grouped", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`group_key` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`group_key`) SELECT `t1`.`c0` AS `k`, `t1`.`c1` AS `total` FROM `p0` AS `t1`"
    ),
    ("s02_unselected_key", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."group_key" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."group_key") SELECT "t1"."c1" AS "total" FROM "p0" AS "t1"'
    ),
    ("s02_unselected_key", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`group_key` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`group_key`) SELECT `t1`.`c1` AS `total` FROM `p0` AS `t1`"
    ),
    ("s02_two_sums", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."group_key" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1", CAST(SUM(CAST("s0"."right_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c2" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."group_key") SELECT "t1"."c0" AS "k", "t1"."c1" AS "x", "t1"."c2" AS "y" FROM "p0" AS "t1"'
    ),
    ("s02_two_sums", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `s0`.`group_key` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1`, CASE WHEN SUM(`s0`.`right_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`right_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`right_value`) AS SIGNED) END AS `c2` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`group_key`) SELECT `t1`.`c0` AS `k`, `t1`.`c1` AS `x`, `t1`.`c2` AS `y` FROM `p0` AS `t1`"
    ),
    ("s02_beside_count", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "s0"."group_key" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1", COUNT("s0"."right_value") AS "c2", MIN("s0"."left_value") AS "c3" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."group_key") SELECT "t1"."c0" AS "k", "t1"."c1" AS "x", "t1"."c2" AS "c2", "t1"."c3" AS "lo" FROM "p0" AS "t1"'
    ),
    ("s02_beside_count", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `s0`.`group_key` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1`, COUNT(`s0`.`right_value`) AS `c2`, MIN(`s0`.`left_value`) AS `c3` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`group_key`) SELECT `t1`.`c0` AS `k`, `t1`.`c1` AS `x`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `lo` FROM `p0` AS `t1`"
    ),
    ("s02_bigint_key", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."nn" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."nn") SELECT "t1"."c0" AS "n", "t1"."c1" AS "x" FROM "p0" AS "t1"'
    ),
    ("s02_bigint_key", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`nn` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`nn`) SELECT `t1`.`c0` AS `n`, `t1`.`c1` AS `x` FROM `p0` AS `t1`"
    ),
    ("s02_key_alias", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."group_key" AS "c0", CAST(SUM(CAST("s0"."left_value" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."group_key") SELECT "t1"."c0" AS "kk", "t1"."c1" AS "x" FROM "p0" AS "t1"'
    ),
    ("s02_key_alias", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`group_key` AS `c0`, CASE WHEN SUM(`s0`.`left_value`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s0`.`left_value`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s0`.`left_value`) AS SIGNED) END AS `c1` FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`group_key`) SELECT `t1`.`c0` AS `kk`, `t1`.`c1` AS `x` FROM `p0` AS `t1`"
    ),
}
NUMERIC_SPELLINGS = {
    "s01_def": "def add(x: Int | None, y: Int | None) -> Int | None: return x + y\nquery result:\n    from rows\n    select:\n        s = add(a, b)\n",
    "s01_parenthesized": "query result:\n    from rows\n    select:\n        s = (a + b)\n",
    "s01_def_nested": "def add(x: Int | None, y: Int | None) -> Int | None: return x + y\ndef twice(x: Int | None, y: Int | None) -> Int | None: return add(x, y)\nquery result:\n    from rows\n    select:\n        s = twice(a, b)\n",
    "s01_identity_def": "def idf(x: Int | None) -> Int | None: return x\nquery result:\n    from rows\n    select:\n        s = idf(a) + b\n",
    "s01_qualified": "query result:\n    from rows\n    select:\n        s = rows.a + rows.b\n",
    "s01_def_whole": "def idf(x: Int | None) -> Int | None: return x\nquery result:\n    from rows\n    select:\n        s = idf(a + b)\n",
    "s01_def_swapped": "def radd(x: Int | None, y: Int | None) -> Int | None: return y + x\nquery result:\n    from rows\n    select:\n        s = radd(b, a)\n",
    "s02_group_block": "query result:\n    from rows\n    group by:\n        k\n    select:\n        k\n        total = sum(a)\n",
    "s02_table": "table result:\n    from rows\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    "s02_parenthesized": "query result:\n    from rows\n    group by k\n    select:\n        k\n        total = sum((a))\n",
    "s02_identity_def": "def idf(x: Int | None) -> Int | None: return x\nquery result:\n    from rows\n    group by k\n    select:\n        k\n        total = sum(idf(a))\n",
    "s02_qualified": "query result:\n    from rows\n    group by k\n    select:\n        k\n        total = sum(rows.a)\n",
}
# A source of main.pietto that other.pietto imports as ``{0}`` and reads.
_NUMERIC_IMPORT = {
    "main.pietto": "export source rows\n",
    "other.pietto": 'from "main.pietto" import (\n    source {0},\n)\n',
}
NUMERIC_REFUSALS = {
    "nonnull_operand": "query result:\n    from rows\n    select:\n        s = n + a\n",
    "literal_operand": "query result:\n    from rows\n    select:\n        s = a + 1\n",
    "narrow_operand": "query result:\n    from rows\n    select:\n        s = c + a\n",
    "chained": "query result:\n    from rows\n    select:\n        s = a + b + a\n",
    "negated_sum": "query result:\n    from rows\n    select:\n        s = -(a + b)\n",
    "abs_of_negation": "query result:\n    from rows\n    select:\n        s = abs(-a)\n",
    "conditional": "query result:\n    from rows\n    select:\n        s = a + b if id > 0 else a\n",
    "coalesce": "query result:\n    from rows\n    select:\n        s = coalesce(a + b, 0)\n",
    "in_let": "query result:\n    from rows\n    let t = a + b\n    select:\n        s = t\n",
    "in_where": "query result:\n    from rows\n    where a + b > 0\n    select:\n        id\n",
    "abs_in_where": "query result:\n    from rows\n    where abs(a) > 3\n    select:\n        id\n",
    "order_by": "query result:\n    from rows\n    select:\n        s = a + b\n        id\n    order by:\n        id\n",
    "limit": "query result:\n    from rows\n    select:\n        s = a + b\n    limit 3\n",
    "distinct": "query result:\n    from rows\n    select distinct:\n        s = a + b\n",
    "header_parameter": "query result(x: Int):\n    from rows\n    where id > x\n    select:\n        s = a + b\n",
    "upstream_fields": "query up:\n    from rows\n    select:\n        a\n        b\nquery result:\n    from up\n    select:\n        s = a + b\n",
    "upstream_operation": "query up:\n    from rows\n    select:\n        s = a + b\nquery result:\n    from up\n    select:\n        s\n",
    "join": "query result:\n    from rows\n    let r = rows\n    inner join r on rows.id == r.id\n    select:\n        s = rows.a + r.b\n",
    "union_operand": "query one:\n    from rows\n    select:\n        s = a + b\nquery two:\n    from rows\n    select:\n        s = a\nquery result:\n    union all one, two\n",
    "sum_argument": "query result:\n    from rows\n    group by k\n    select:\n        k\n        s = sum(a + b)\n",
    "sum_nonnull": "query result:\n    from rows\n    select:\n        x = sum(n)\n",
    "sum_narrow": "query result:\n    from rows\n    select:\n        x = sum(c)\n",
    "sum_nullable_key": "query result:\n    from rows\n    group by a\n    select:\n        a\n        x = sum(b)\n",
    "sum_two_keys": "query result:\n    from rows\n    group by k, id\n    select:\n        k\n        id\n        x = sum(a)\n",
    "sum_composed": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a) + 1\n",
    "sum_coalesced": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = coalesce(sum(a), 0)\n",
    "sum_having": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n    having:\n        x > 1\n",
    "sum_order_by": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n    order by:\n        k\n",
    "sum_limit": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n    limit 2\n",
    "sum_upstream": "query up:\n    from rows\n    select:\n        k\n        a\nquery result:\n    from up\n    group by k\n    select:\n        k\n        x = sum(a)\n",
    "sum_let_argument": "query result:\n    from rows\n    let t = a\n    group by k\n    select:\n        k\n        x = sum(t)\n",
    "sum_filtered": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(o.a for o in group if o.id > 0)\n",
    "sum_header_parameter": "query result(lo: Int):\n    from rows\n    where id > lo\n    group by k\n    select:\n        k\n        x = sum(a)\n",
    # D77.24: no relation alias, no unread header parameter, no let and no
    # aggregate beyond sum, count and min beside a sum.
    "row_input_alias": "query result:\n    let x = rows\n    from x\n    select:\n        s = a + b\n",
    "row_input_alias_chain": "query result:\n    let x = rows\n    let y = x\n    from y\n    select:\n        s = a + b\n",
    "unused_header_parameter": "query result(z: Int):\n    from rows\n    select:\n        s = a + b\n",
    "let_carry": "query result:\n    from rows\n    let t = a\n    select:\n        s = t + b\n",
    "abs_nonnull": "query result:\n    from rows\n    select:\n        s = abs(n)\n",
    "sum_row_input_alias": "query result:\n    let x = rows\n    from x\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    "sum_row_input_alias_chain": "query result:\n    let x = rows\n    let y = x\n    from y\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    "sum_unused_header_parameter": "query result(z: Int):\n    from rows\n    group by k\n    select:\n        k\n        t = sum(a)\n",
    "sum_beside_avg": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n        y = avg(a)\n",
    # A relation alias that nothing reads leaves no trace in the plan.
    "unread_row_input_alias": "query result:\n    let x = rows\n    from rows\n    select:\n        s = a + b\n",
    "sum_unread_row_input_alias": "query result:\n    let x = rows\n    from rows\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    "unread_window": "query result:\n    from rows\n    let w = window(order by id)\n    select:\n        s = a + b\n",
    "sum_unread_window": "query result:\n    from rows\n    let w = window(order by id)\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    # A source of another module, imported under its own name or another.
    "imported_source": {
        **_NUMERIC_IMPORT,
        "other.pietto": _NUMERIC_IMPORT["other.pietto"].format("rows")
        + "query result:\n    from rows\n    select:\n        s = a + b\n",
    },
    "imported_source_alias": {
        **_NUMERIC_IMPORT,
        "other.pietto": _NUMERIC_IMPORT["other.pietto"].format("rows as r")
        + "query result:\n    from r\n    select:\n        s = a + b\n",
    },
    "sum_imported_source_alias": {
        **_NUMERIC_IMPORT,
        "other.pietto": _NUMERIC_IMPORT["other.pietto"].format("rows as r")
        + "query result:\n    from r\n    group by k\n    select:\n        k\n        total = sum(a)\n",
    },
    # Owner 2026-11-13T00:20Z: a cell beside another refused form keeps
    # main's refusal too.
    "beside_literal_operand": "query result:\n    from rows\n    select:\n        s = a + b\n        t = a + 1\n",
    "beside_two_refusals": "query result:\n    from rows\n    select:\n        s = a + b\n        t = n + a\n        u = -a\n",
    "beside_division": "query result:\n    from rows\n    select:\n        s = a + b\n        t = a / b\n",
    "sum_beside_sum_argument": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n        y = sum(a + b)\n",
    "sum_beside_sum_nonnull": "query result:\n    from rows\n    group by k\n    select:\n        k\n        x = sum(a)\n        y = sum(n)\n",
}
# Relation aliases and windows, read or not, imported sources and the direct
# read each spells: only emission (the authored body and the source's module)
# tells them apart, as compiled records and the pure document are the direct
# read's apart from source positions and the source digest.
NUMERIC_ALIASES = {
    "row_input_alias": NUMERIC_SPELLINGS["s01_parenthesized"],
    "row_input_alias_chain": NUMERIC_SPELLINGS["s01_parenthesized"],
    "unread_row_input_alias": NUMERIC_SPELLINGS["s01_parenthesized"],
    "sum_row_input_alias": NUMERIC_CELLS["s02_grouped"],
    "sum_row_input_alias_chain": NUMERIC_CELLS["s02_grouped"],
    "sum_unread_row_input_alias": NUMERIC_CELLS["s02_grouped"],
    "unread_window": NUMERIC_SPELLINGS["s01_parenthesized"],
    "sum_unread_window": NUMERIC_CELLS["s02_grouped"],
    "imported_source": NUMERIC_SPELLINGS["s01_parenthesized"],
    "imported_source_alias": NUMERIC_SPELLINGS["s01_parenthesized"],
    "sum_imported_source_alias": NUMERIC_CELLS["s02_grouped"],
}
NUMERIC_REFUSAL_BLOCKERS = {
    "nonnull_operand": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "literal_operand": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "narrow_operand": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "chained": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "negated_sum": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "abs_of_negation": [("PIE-B1002", "unary_result_outside_physical_range", 12, 9)],
    "conditional": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "coalesce": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "in_let": [("PIE-B1002", "arithmetic_outside_physical_range", 11, 5)],
    "in_where": [("PIE-B1002", "arithmetic_outside_physical_range", 11, 5)],
    "abs_in_where": [("PIE-B1002", "abs_result_outside_physical_range", 11, 5)],
    "order_by": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "limit": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "distinct": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "header_parameter": [("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)],
    "upstream_fields": [("PIE-B1002", "arithmetic_outside_physical_range", 17, 9)],
    "upstream_operation": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "join": [("PIE-B1002", "arithmetic_outside_physical_range", 14, 9)],
    "union_operand": [("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)],
    "sum_argument": [("PIE-B1002", "arithmetic_outside_physical_range", 14, 9)],
    "sum_nonnull": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 12, 9)],
    "sum_narrow": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 12, 9)],
    "sum_nullable_key": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "sum_two_keys": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)],
    "sum_composed": [
        ("PIE-B1003", "aggregate_composition_not_admitted_on_target", 14, 13)
    ],
    "sum_coalesced": [
        ("PIE-B1003", "aggregate_composition_not_admitted_on_target", 14, 13)
    ],
    "sum_having": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "sum_order_by": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "sum_limit": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "sum_upstream": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 19, 9)],
    "sum_let_argument": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)],
    "sum_filtered": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "sum_header_parameter": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)
    ],
    "row_input_alias": [("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)],
    "row_input_alias_chain": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 14, 9)
    ],
    "unused_header_parameter": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)
    ],
    "let_carry": [("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)],
    "abs_nonnull": [("PIE-B1002", "abs_result_outside_physical_range", 12, 9)],
    "sum_row_input_alias": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)
    ],
    "sum_row_input_alias_chain": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 16, 9)
    ],
    "sum_unused_header_parameter": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)
    ],
    "sum_beside_avg": [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9)],
    "unread_row_input_alias": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)
    ],
    "sum_unread_row_input_alias": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)
    ],
    "unread_window": [("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)],
    "sum_unread_window": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9)
    ],
    "imported_source": [("PIE-B1002", "arithmetic_outside_physical_range", 7, 9)],
    "imported_source_alias": [("PIE-B1002", "arithmetic_outside_physical_range", 7, 9)],
    "sum_imported_source_alias": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 9, 9)
    ],
    "beside_literal_operand": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 12, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 13, 9),
    ],
    "beside_two_refusals": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 12, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 13, 9),
        ("PIE-B1002", "unary_result_outside_physical_range", 14, 9),
    ],
    "beside_division": [
        ("PIE-B1002", "arithmetic_outside_physical_range", 12, 9),
        ("PIE-B1003", "binary_operator_not_admitted", 13, 9),
    ],
    "sum_beside_sum_argument": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 15, 9),
    ],
    "sum_beside_sum_nonnull": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 14, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15, 9),
    ],
}


def numeric_law_inputs(directory, body):
    """The arguments emission passes to the MySQL S01/S02 cell laws while it
    emits ``body`` (rows.mysql_checked_cell, mysql_sum_query, mysql_sum_cell),
    the first call of each, for tests that edit one input at a time."""
    from _pytest.monkeypatch import MonkeyPatch
    from pietto._project import project_sql_emission_rows as rows

    seen: dict[str, tuple] = {}
    patch = MonkeyPatch()
    try:
        for name in ("mysql_checked_cell", "mysql_sum_query", "mysql_sum_cell"):
            law = getattr(rows, name)
            patch.setattr(
                rows,
                name,
                lambda *args, _law=law, _name=name: (
                    seen.setdefault(_name, args) and _law(*args)
                ),
            )
        _, outcome = numeric_world(directory, "mysql", body)
    finally:
        patch.undo()
    assert outcome.status == "VERIFIED", outcome.blockers
    return seen


def numeric_readers_accept(outcome):
    """Every reader accepts a VERIFIED artifact: plain verification (plan),
    the pure boundary (document), the independent public decoder, compiled
    replay and its template (records) and the live template, with the
    emitted SQL byte for byte; a bind-safe template binds its fixed values."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
        prepare_live_template,
    )
    from pietto._project.project_sql_emission import serialize_project_sql_emission
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    parsed = pure.parse_emission_observation(observed.canonical_bytes)
    assert parsed.status is pure.Status.OK, parsed.detail
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    assert decode_public(serialize_project_sql_emission(outcome))["status"] == (
        "VERIFIED"
    )
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    fixed = tuple(value.value for value in artifact.fixed_values)
    assert emit_compiled(loaded, fixed).rendered.sql == artifact.rendered.sql
    for template in (
        prepare_compiled_template(loaded),
        prepare_live_template(artifact),
    ):
        assert len(template.slots) == len(fixed) and template.parameters == ()
        bound = tuple(zip(template.slots, fixed, strict=True))
        assert bind_values(template, bound, ()).artifact.rendered.sql == (
            artifact.rendered.sql
        )


# Phase77 S03: the two sources of the native qualification's sum forms, in its
# own carriers: BIGINT `id`, `amount`, `nn`, `order_id`, `qty` (`amount` and
# `qty` nullable), an INT group key `customer` and a nullable 0/1 Bool `flag`.
S03_HEADER = """shape Order:
    id: Int
    customer: Int
    amount: Int | None
    nn: Int
    flag: Bool | None
    order_key = unique(id)
shape Item:
    id: Int
    order_id: Int
    qty: Int | None
    item_key = unique(id)
source orders: Order = {target}.table("orders")
source items: Item = {target}.table("items")
"""
_S03_FIELDS = {
    "orders": (
        ("id", "wide", False),
        ("customer", "narrow", False),
        ("amount", "wide", True),
        ("nn", "wide", False),
        ("flag", "bool", True),
    ),
    "items": (
        ("id", "wide", False),
        ("order_id", "wide", False),
        ("qty", "wide", True),
    ),
}


def s03_world(
    directory, target, body, policy="preserve_literals", names=None, extra=None
):
    """``body`` over S03_HEADER, its contract binding the sources the body
    names, with exact identifier case and the native parameter protocol;
    ``names`` renames identifiers (whole words) in the header, the body and
    the contract's selectors and fields alike, and ``extra`` adds nullable
    BIGINT fields after a source's own, as {source: (name, ...)}. A dict
    ``body`` maps module paths to their text, main.pietto's after the
    header."""
    names, extra = names or {}, extra or {}
    header = S03_HEADER
    for source, last in (
        ("orders", "    flag: Bool | None\n"),
        ("items", "    qty: Int | None\n"),
    ):
        header = header.replace(
            last,
            last
            + "".join(f"    {name}: Int | None\n" for name in extra.get(source, ())),
        )

    def renamed(text):
        return (
            re.sub(
                r"\b(%s)\b" % "|".join(map(re.escape, names)),
                lambda match: names[match[0]],
                text,
            )
            if names
            else text
        )

    files = dict(body) if type(body) is dict else {"main.pietto": body}
    text = "\n".join(files.values())
    contract = json.loads(fixture(target)["contract"])
    contract["environment"] += [
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        },
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended" if target == "postgres" else "mysql_prepared",
        },
    ]
    storage = {
        "wide": ("pg_int8" if target == "postgres" else "my_bigint", 63),
        "narrow": ("pg_int4" if target == "postgres" else "my_int", 31),
        "bool": ("pg_bool" if target == "postgres" else "my_bool01", None),
    }
    template = contract["sources"][0]
    contract["sources"] = [
        {
            **template,
            "selector": {**template["selector"], "name": renamed(source)},
            "relation": {**template["relation"], "name": "s03 " + source},
            "fields": [
                {
                    "ordinal": ordinal,
                    "name": renamed(name),
                    "column": name,
                    "representation": {
                        "storage": {"kind": storage[kind][0]},
                        "nullable": nullable,
                        "domain": {"kind": "bool01"}
                        if kind == "bool"
                        else {
                            "kind": "int_range",
                            "min": str(-(1 << storage[kind][1])),
                            "max": str((1 << storage[kind][1]) - 1),
                        },
                    },
                }
                for ordinal, (name, kind, nullable) in enumerate(
                    (*fields, *((name, "wide", True) for name in extra.get(source, ())))
                )
            ],
        }
        for source, fields in _S03_FIELDS.items()
        if re.search(r"\b%s\b" % source, text)
    ]
    files["main.pietto"] = renamed(
        header.format(target=target) + files.get("main.pietto", "")
    )
    return build_case(
        directory,
        {
            path: renamed(content) if path != "main.pietto" else content
            for path, content in files.items()
        },
        encoded(contract).decode(),
        policy,
    )


# The nine paired forms (the qualification pack's forms.json, PREREG Forms)
# and the SQL each emits, also the candidate emission experiment's source.
S03_FORMS = {
    "C1": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n",
    "C2": "query result:\n    from orders\n    select:\n        x = sum(o.amount for o in group if not o.flag)\n        y = sum(o.amount for o in group if o.flag is None)\n",
    "C3": "query result:\n    from orders\n    select:\n        z = sum(o.amount for o in group if o.id > 3)\n",
    "C4": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        t = sum(o.nn for o in group if o.flag)\n",
    "J1": "query result:\n    from items\n    let o = orders\n    inner join o on o.id == items.order_id\n    group by o.customer\n    select:\n        customer = o.customer\n        qty = sum(items.qty)\n",
    "J2": "query result:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id\n    select:\n        id = orders.id\n        qty = sum(i.qty)\n",
    "J3": "query result:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id, orders.customer\n    select:\n        id = orders.id\n        customer = orders.customer\n        qty = sum(i.qty)\n",
    "T1": "query per_order:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id, orders.customer, orders.amount\n    select:\n        id = orders.id\n        customer = orders.customer\n        amount = orders.amount\n        lines = count(i.id)\nquery result:\n    from per_order\n    group by customer\n    select:\n        customer\n        revenue = sum(amount)\n        lines = sum(lines)\n",
    "T2": "query per_order:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id, orders.customer\n    select:\n        id = orders.id\n        customer = orders.customer\n        qty = sum(i.qty)\nquery result:\n    from per_order\n    group by customer\n    select:\n        customer\n        qty = sum(qty)\n",
}
# Other spellings of a form, names, aliases and SELECT item order aside, and
# subsets of its items with one sum at least, with the form each is; C3 over
# 0 and over the largest Int (S03_FORM_SQL pins both families' bytes).
S03_SPELLINGS = {
    "c1_table": ("C1", S03_FORMS["C1"].replace("query result", "table result")),
    "c1_sum_only": (
        "C1",
        S03_FORMS["C1"].replace("        customer\n        paid", "        paid"),
    ),
    "c1_key_alias": (
        "C1",
        S03_FORMS["C1"].replace(
            "        customer\n        paid", "        c = customer\n        paid"
        ),
    ),
    "c1_reordered": (
        "C1",
        "query result:\n    from orders\n    group by customer\n    select:\n        paid = sum(o.amount for o in group if o.flag)\n        customer\n",
    ),
    "c2_none_only": (
        "C2",
        "query result:\n    from orders\n    select:\n        y = sum(o.amount for o in group if o.flag is None)\n",
    ),
    "c3_zero": ("C3", S03_FORMS["C3"].replace("> 3", "> 0")),
    "c3_largest": ("C3", S03_FORMS["C3"].replace("> 3", "> 9223372036854775807")),
    "j1_sum_only": (
        "J1",
        S03_FORMS["J1"].replace("        customer = o.customer\n", ""),
    ),
    "j3_reordered": (
        "J3",
        "query result:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id, orders.customer\n    select:\n        qty = sum(i.qty)\n        customer = orders.customer\n        id = orders.id\n",
    ),
    "t1_revenue_only": (
        "T1",
        S03_FORMS["T1"]
        .replace("        lines = sum(lines)\n", "")
        .replace("        customer\n        revenue", "        revenue"),
    ),
    "t2_table": ("T2", S03_FORMS["T2"].replace("query per_order", "table per_order")),
}
# Relations and fields renamed (whole words) for s03_world.
S03_RENAMES = {
    "orders": "sales",
    "items": "lines_",
    "customer": "buyer",
    "amount": "total",
    "qty": "units",
    "flag": "paid_flag",
}
# Shapes outside the forms: the pack's 19 controls (forms.json) and others,
# each keeping main's MySQL blockers (S03_REFUSAL_BLOCKERS) under the policies
# it lists (both when none). An imported source, a relation alias, a read
# qualified by its source's name and parentheses also leave the compiled
# records and pure document of a form (S03_ALIASES).
S03_REFUSALS = {
    "ctl_c_beside_count": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n        c = count()\n",
    "ctl_c_beside_direct_sum": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        x = sum(amount)\n        y = sum(o.amount for o in group if o.flag)\n        c = count()\n",
    "ctl_c_bind_safe_literal": S03_FORMS["C3"],
    "ctl_c_compound_test": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag and o.id > 3)\n",
    "ctl_c_narrow_argument": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        paid = sum(o.customer for o in group if o.flag)\n",
    "ctl_c_negative_literal": "query result:\n    from orders\n    select:\n        z = sum(o.amount for o in group if o.id > -5)\n",
    "ctl_c_order_by": "query result:\n    from orders\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n    order by customer\n",
    "ctl_c_other_operator": "query result:\n    from orders\n    select:\n        z = sum(o.amount for o in group if o.id >= 3)\n",
    "ctl_c_row_alias": "query result:\n    let x = orders\n    from x\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n",
    "ctl_c_test_on_int_isnone": "query result:\n    from orders\n    select:\n        x = sum(o.amount for o in group if not o.flag)\n        y = sum(o.amount for o in group if o.amount is None)\n",
    "ctl_c_upstream": "query up:\n    from orders\n    select:\n        customer\n        amount\n        flag\nquery result:\n    from up\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n",
    "ctl_c_where": "query result:\n    from orders\n    where nn > 0\n    group by customer\n    select:\n        customer\n        paid = sum(o.amount for o in group if o.flag)\n",
    "ctl_j_from_side_key": "query result:\n    from items\n    let o = orders\n    inner join o on o.id == items.order_id\n    group by items.order_id\n    select:\n        order_id = items.order_id\n        qty = sum(items.qty)\n",
    "ctl_j_inner_joined_side": "query result:\n    from orders\n    let i = items\n    inner join i on i.order_id == orders.id\n    group by orders.id\n    select:\n        id = orders.id\n        qty = sum(i.qty)\n",
    "ctl_j_two_sums": "query result:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id\n    select:\n        id = orders.id\n        qty = sum(i.qty)\n        ids = sum(i.id)\n",
    "ctl_j_where": "query result:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    where orders.nn > 0\n    group by orders.id\n    select:\n        id = orders.id\n        qty = sum(i.qty)\n",
    "ctl_t_plain_first_level": "query up:\n    from orders\n    select:\n        customer\n        amount\nquery result:\n    from up\n    group by customer\n    select:\n        customer\n        total = sum(amount)\n",
    "ctl_t_second_where": S03_FORMS["T1"].replace(
        "    from per_order\n", "    from per_order\n    where lines > 0\n"
    ),
    "ctl_t_third_level": "query per_order:\n    from orders\n    let i = items\n    left join i on i.order_id == orders.id\n    group by orders.id, orders.customer\n    select:\n        id = orders.id\n        customer = orders.customer\n        qty = sum(i.qty)\nquery mid:\n    from per_order\n    group by customer\n    select:\n        customer\n        qty = sum(qty)\nquery result:\n    from mid\n    select:\n        all_qty = sum(qty)\n",
    "j1_left": S03_FORMS["J1"].replace("inner join", "left join"),
    "j2_on_reversed": S03_FORMS["J2"].replace(
        "i.order_id == orders.id", "orders.id == i.order_id"
    ),
    "c1_qualified_key": S03_FORMS["C1"].replace(
        "group by customer", "group by orders.customer"
    ),
    "c1_beside_composed": S03_FORMS["C1"] + "        extra = sum(amount) + 1\n",
    "c2_two_fields": "query result:\n    from orders\n    select:\n        x = sum(o.amount for o in group if not o.flag)\n        y = sum(o.nn for o in group if o.flag is None)\n",
    "t2_extra_upstream_count": S03_FORMS["T2"].replace(
        "        qty = sum(i.qty)\nquery result",
        "        qty = sum(i.qty)\n        n = count()\nquery result",
    ),
    # A two-level form's per_order selects exactly its form's items.
    "t1_upstream_subset": S03_FORMS["T1"].replace("        id = orders.id\n", ""),
    "t2_upstream_subset": S03_FORMS["T2"].replace("        id = orders.id\n", ""),
    # D77.24: parentheses are no form's spelling, though the records and
    # the document are the form's (S03_ALIASES).
    "c1_parenthesized_argument": S03_FORMS["C1"].replace(
        "sum(o.amount for", "sum((o.amount) for"
    ),
    "c2_parenthesized_test": S03_FORMS["C2"].replace(
        "if not o.flag", "if not (o.flag)"
    ),
    "j2_parenthesized_on": S03_FORMS["J2"].replace(
        "on i.order_id == orders.id", "on (i.order_id == orders.id)"
    ),
    "j2_parenthesized_sum": S03_FORMS["J2"].replace(
        "qty = sum(i.qty)", "qty = (sum(i.qty))"
    ),
    "imported_source": {
        "main.pietto": "export source orders\n",
        "other.pietto": 'from "main.pietto" import (\n    source orders,\n)\n'
        + S03_FORMS["C1"],
    },
}
S03_REFUSAL_POLICIES = {"ctl_c_bind_safe_literal": ("bind_safe_literals",)}
# A JOIN form's SQL carries every field of both sources, so a source with a
# field beyond the qualification's tables is no form; a conditional form
# reads only its fields and stays one. Per shape: (form, extra fields).
S03_WIDER = {
    "j2_wider_items": ("J2", {"items": ("note",)}),
    "t1_wider_orders": ("T1", {"orders": ("note",)}),
    "c1_wider_orders": ("C1", {"orders": ("note",)}),
}
# A refused shape whose compiled records and pure document are a form's.
S03_ALIASES = {
    "ctl_c_row_alias": "C1",
    "imported_source": "C1",
    "c1_qualified_key": "C1",
    "c1_parenthesized_argument": "C1",
    "c2_parenthesized_test": "C2",
    "j2_parenthesized_on": "J2",
    "j2_parenthesized_sum": "J2",
}
# The SQL of each form (and of C3 over 0 and over the largest Int), PostgreSQL's
# main's own.
S03_FORM_SQL = {
    ("C1", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."customer" AS "c0", COALESCE(CAST(SUM(CASE WHEN "s0"."flag" THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c1" FROM "public"."s03 orders" AS "s0" GROUP BY "s0"."customer") SELECT "t1"."c0" AS "customer", "t1"."c1" AS "paid" FROM "p0" AS "t1"'
    ),
    ("C1", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`customer` AS `c0`, COALESCE(CASE WHEN SUM(CASE WHEN `s0`.`flag` THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN `s0`.`flag` THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN `s0`.`flag` THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c1` FROM `phase66`.`s03 orders` AS `s0` GROUP BY `s0`.`customer`) SELECT `t1`.`c0` AS `customer`, `t1`.`c1` AS `paid` FROM `p0` AS `t1`"
    ),
    ("C2", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT COALESCE(CAST(SUM(CASE WHEN (NOT "s0"."flag") THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c0", COALESCE(CAST(SUM(CASE WHEN ("s0"."flag" IS NULL) THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c1" FROM "public"."s03 orders" AS "s0") SELECT "t1"."c0" AS "x", "t1"."c1" AS "y" FROM "p0" AS "t1"'
    ),
    ("C2", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT COALESCE(CASE WHEN SUM(CASE WHEN (NOT `s0`.`flag`) THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN (NOT `s0`.`flag`) THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN (NOT `s0`.`flag`) THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c0`, COALESCE(CASE WHEN SUM(CASE WHEN (`s0`.`flag` IS NULL) THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN (`s0`.`flag` IS NULL) THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN (`s0`.`flag` IS NULL) THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c1` FROM `phase66`.`s03 orders` AS `s0`) SELECT `t1`.`c0` AS `x`, `t1`.`c1` AS `y` FROM `p0` AS `t1`"
    ),
    ("C3", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT COALESCE(CAST(SUM(CASE WHEN ("s0"."id" > CAST(3 AS pg_catalog.int8)) THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c0" FROM "public"."s03 orders" AS "s0") SELECT "t1"."c0" AS "z" FROM "p0" AS "t1"'
    ),
    ("C3", "mysql"): (
        "WITH `p0` (`c0`) AS (SELECT COALESCE(CASE WHEN SUM(CASE WHEN (`s0`.`id` > CAST(3 AS SIGNED)) THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN (`s0`.`id` > CAST(3 AS SIGNED)) THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN (`s0`.`id` > CAST(3 AS SIGNED)) THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c0` FROM `phase66`.`s03 orders` AS `s0`) SELECT `t1`.`c0` AS `z` FROM `p0` AS `t1`"
    ),
    ("C4", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."customer" AS "c0", COALESCE(CAST(SUM(CASE WHEN "s0"."flag" THEN CAST("s0"."nn" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c1" FROM "public"."s03 orders" AS "s0" GROUP BY "s0"."customer") SELECT "t1"."c0" AS "customer", "t1"."c1" AS "t" FROM "p0" AS "t1"'
    ),
    ("C4", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`customer` AS `c0`, COALESCE(CASE WHEN SUM(CASE WHEN `s0`.`flag` THEN `s0`.`nn` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN `s0`.`flag` THEN `s0`.`nn` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN `s0`.`flag` THEN `s0`.`nn` END) AS SIGNED) END, 0) AS `c1` FROM `phase66`.`s03 orders` AS `s0` GROUP BY `s0`.`customer`) SELECT `t1`.`c0` AS `customer`, `t1`.`c1` AS `t` FROM `p0` AS `t1`"
    ),
    ("J1", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT "m0"."id" AS "c0", "m0"."order_id" AS "c1", "m0"."qty" AS "c2", "m1"."id" AS "c3", "m1"."customer" AS "c4", "m1"."amount" AS "c5", "m1"."nn" AS "c6", "m1"."flag" AS "c7" FROM "public"."s03 items" AS "m0" INNER JOIN "public"."s03 orders" AS "m1" ON ("m1"."id" = "m0"."order_id")), "p1" ("c0", "c1") AS (SELECT "t0"."c4" AS "c0", CAST(SUM(CAST("t0"."c2" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "p0" AS "t0" GROUP BY "t0"."c4") SELECT "t1"."c0" AS "customer", "t1"."c1" AS "qty" FROM "p1" AS "t1"'
    ),
    ("J1", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT `m0`.`id` AS `c0`, `m0`.`order_id` AS `c1`, `m0`.`qty` AS `c2`, `m1`.`id` AS `c3`, `m1`.`customer` AS `c4`, `m1`.`amount` AS `c5`, `m1`.`nn` AS `c6`, `m1`.`flag` AS `c7` FROM `phase66`.`s03 items` AS `m0` INNER JOIN `phase66`.`s03 orders` AS `m1` ON (`m1`.`id` = `m0`.`order_id`)), `p1` (`c0`, `c1`) AS (SELECT `t0`.`c4` AS `c0`, CASE WHEN SUM(`t0`.`c2`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`t0`.`c2`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`t0`.`c2`) AS SIGNED) END AS `c1` FROM `p0` AS `t0` GROUP BY `t0`.`c4`) SELECT `t1`.`c0` AS `customer`, `t1`.`c1` AS `qty` FROM `p1` AS `t1`"
    ),
    ("J2", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT "m0"."id" AS "c0", "m0"."customer" AS "c1", "m0"."amount" AS "c2", "m0"."nn" AS "c3", "m0"."flag" AS "c4", "m1"."id" AS "c5", "m1"."order_id" AS "c6", "m1"."qty" AS "c7" FROM "public"."s03 orders" AS "m0" LEFT JOIN "public"."s03 items" AS "m1" ON ("m1"."order_id" = "m0"."id")), "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", CAST(SUM(CAST("t0"."c7" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "p0" AS "t0" GROUP BY "t0"."c0") SELECT "t1"."c0" AS "id", "t1"."c1" AS "qty" FROM "p1" AS "t1"'
    ),
    ("J2", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT `m0`.`id` AS `c0`, `m0`.`customer` AS `c1`, `m0`.`amount` AS `c2`, `m0`.`nn` AS `c3`, `m0`.`flag` AS `c4`, `m1`.`id` AS `c5`, `m1`.`order_id` AS `c6`, `m1`.`qty` AS `c7` FROM `phase66`.`s03 orders` AS `m0` LEFT JOIN `phase66`.`s03 items` AS `m1` ON (`m1`.`order_id` = `m0`.`id`)), `p1` (`c0`, `c1`) AS (SELECT `t0`.`c0` AS `c0`, CASE WHEN SUM(`t0`.`c7`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`t0`.`c7`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`t0`.`c7`) AS SIGNED) END AS `c1` FROM `p0` AS `t0` GROUP BY `t0`.`c0`) SELECT `t1`.`c0` AS `id`, `t1`.`c1` AS `qty` FROM `p1` AS `t1`"
    ),
    ("J3", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT "m0"."id" AS "c0", "m0"."customer" AS "c1", "m0"."amount" AS "c2", "m0"."nn" AS "c3", "m0"."flag" AS "c4", "m1"."id" AS "c5", "m1"."order_id" AS "c6", "m1"."qty" AS "c7" FROM "public"."s03 orders" AS "m0" LEFT JOIN "public"."s03 items" AS "m1" ON ("m1"."order_id" = "m0"."id")), "p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", CAST(SUM(CAST("t0"."c7" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c2" FROM "p0" AS "t0" GROUP BY "t0"."c0", "t0"."c1") SELECT "t1"."c0" AS "id", "t1"."c1" AS "customer", "t1"."c2" AS "qty" FROM "p1" AS "t1"'
    ),
    ("J3", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT `m0`.`id` AS `c0`, `m0`.`customer` AS `c1`, `m0`.`amount` AS `c2`, `m0`.`nn` AS `c3`, `m0`.`flag` AS `c4`, `m1`.`id` AS `c5`, `m1`.`order_id` AS `c6`, `m1`.`qty` AS `c7` FROM `phase66`.`s03 orders` AS `m0` LEFT JOIN `phase66`.`s03 items` AS `m1` ON (`m1`.`order_id` = `m0`.`id`)), `p1` (`c0`, `c1`, `c2`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, CASE WHEN SUM(`t0`.`c7`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`t0`.`c7`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`t0`.`c7`) AS SIGNED) END AS `c2` FROM `p0` AS `t0` GROUP BY `t0`.`c0`, `t0`.`c1`) SELECT `t1`.`c0` AS `id`, `t1`.`c1` AS `customer`, `t1`.`c2` AS `qty` FROM `p1` AS `t1`"
    ),
    ("T1", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT "m0"."id" AS "c0", "m0"."customer" AS "c1", "m0"."amount" AS "c2", "m0"."nn" AS "c3", "m0"."flag" AS "c4", "m1"."id" AS "c5", "m1"."order_id" AS "c6", "m1"."qty" AS "c7" FROM "public"."s03 orders" AS "m0" LEFT JOIN "public"."s03 items" AS "m1" ON ("m1"."order_id" = "m0"."id")), "p1" ("c0", "c1", "c2", "c3") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2", COUNT("t0"."c5") AS "c3" FROM "p0" AS "t0" GROUP BY "t0"."c0", "t0"."c1", "t0"."c2"), "p2" ("c0", "c1", "c2", "c3") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3" FROM "p1" AS "t1"), "p3" ("c0", "c1", "c2") AS (SELECT "s2"."c1" AS "c0", CAST(SUM(CAST("s2"."c2" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1", CAST(SUM(CAST("s2"."c3" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c2" FROM "p2" AS "s2" GROUP BY "s2"."c1") SELECT "t3"."c0" AS "customer", "t3"."c1" AS "revenue", "t3"."c2" AS "lines" FROM "p3" AS "t3"'
    ),
    ("T1", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT `m0`.`id` AS `c0`, `m0`.`customer` AS `c1`, `m0`.`amount` AS `c2`, `m0`.`nn` AS `c3`, `m0`.`flag` AS `c4`, `m1`.`id` AS `c5`, `m1`.`order_id` AS `c6`, `m1`.`qty` AS `c7` FROM `phase66`.`s03 orders` AS `m0` LEFT JOIN `phase66`.`s03 items` AS `m1` ON (`m1`.`order_id` = `m0`.`id`)), `p1` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, COUNT(`t0`.`c5`) AS `c3` FROM `p0` AS `t0` GROUP BY `t0`.`c0`, `t0`.`c1`, `t0`.`c2`), `p2` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3` FROM `p1` AS `t1`), `p3` (`c0`, `c1`, `c2`) AS (SELECT `s2`.`c1` AS `c0`, CASE WHEN SUM(`s2`.`c2`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s2`.`c2`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s2`.`c2`) AS SIGNED) END AS `c1`, CASE WHEN SUM(`s2`.`c3`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s2`.`c3`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s2`.`c3`) AS SIGNED) END AS `c2` FROM `p2` AS `s2` GROUP BY `s2`.`c1`) SELECT `t3`.`c0` AS `customer`, `t3`.`c1` AS `revenue`, `t3`.`c2` AS `lines` FROM `p3` AS `t3`"
    ),
    ("T2", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT "m0"."id" AS "c0", "m0"."customer" AS "c1", "m0"."amount" AS "c2", "m0"."nn" AS "c3", "m0"."flag" AS "c4", "m1"."id" AS "c5", "m1"."order_id" AS "c6", "m1"."qty" AS "c7" FROM "public"."s03 orders" AS "m0" LEFT JOIN "public"."s03 items" AS "m1" ON ("m1"."order_id" = "m0"."id")), "p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", CAST(SUM(CAST("t0"."c7" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c2" FROM "p0" AS "t0" GROUP BY "t0"."c0", "t0"."c1"), "p2" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2" FROM "p1" AS "t1"), "p3" ("c0", "c1") AS (SELECT "s2"."c1" AS "c0", CAST(SUM(CAST("s2"."c2" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" FROM "p2" AS "s2" GROUP BY "s2"."c1") SELECT "t3"."c0" AS "customer", "t3"."c1" AS "qty" FROM "p3" AS "t3"'
    ),
    ("T2", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT `m0`.`id` AS `c0`, `m0`.`customer` AS `c1`, `m0`.`amount` AS `c2`, `m0`.`nn` AS `c3`, `m0`.`flag` AS `c4`, `m1`.`id` AS `c5`, `m1`.`order_id` AS `c6`, `m1`.`qty` AS `c7` FROM `phase66`.`s03 orders` AS `m0` LEFT JOIN `phase66`.`s03 items` AS `m1` ON (`m1`.`order_id` = `m0`.`id`)), `p1` (`c0`, `c1`, `c2`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, CASE WHEN SUM(`t0`.`c7`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`t0`.`c7`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`t0`.`c7`) AS SIGNED) END AS `c2` FROM `p0` AS `t0` GROUP BY `t0`.`c0`, `t0`.`c1`), `p2` (`c0`, `c1`, `c2`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2` FROM `p1` AS `t1`), `p3` (`c0`, `c1`) AS (SELECT `s2`.`c1` AS `c0`, CASE WHEN SUM(`s2`.`c2`) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(`s2`.`c2`) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(`s2`.`c2`) AS SIGNED) END AS `c1` FROM `p2` AS `s2` GROUP BY `s2`.`c1`) SELECT `t3`.`c0` AS `customer`, `t3`.`c1` AS `qty` FROM `p3` AS `t3`"
    ),
    ("c3_zero", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT COALESCE(CAST(SUM(CASE WHEN ("s0"."id" > CAST(0 AS pg_catalog.int8)) THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c0" FROM "public"."s03 orders" AS "s0") SELECT "t1"."c0" AS "z" FROM "p0" AS "t1"'
    ),
    ("c3_zero", "mysql"): (
        "WITH `p0` (`c0`) AS (SELECT COALESCE(CASE WHEN SUM(CASE WHEN (`s0`.`id` > CAST(0 AS SIGNED)) THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN (`s0`.`id` > CAST(0 AS SIGNED)) THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN (`s0`.`id` > CAST(0 AS SIGNED)) THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c0` FROM `phase66`.`s03 orders` AS `s0`) SELECT `t1`.`c0` AS `z` FROM `p0` AS `t1`"
    ),
    ("c3_largest", "postgres"): (
        'WITH "p0" ("c0") AS (SELECT COALESCE(CAST(SUM(CASE WHEN ("s0"."id" > CAST(9223372036854775807 AS pg_catalog.int8)) THEN CAST("s0"."amount" AS pg_catalog.int8) END) AS pg_catalog.int8), 0) AS "c0" FROM "public"."s03 orders" AS "s0") SELECT "t1"."c0" AS "z" FROM "p0" AS "t1"'
    ),
    ("c3_largest", "mysql"): (
        "WITH `p0` (`c0`) AS (SELECT COALESCE(CASE WHEN SUM(CASE WHEN (`s0`.`id` > CAST(9223372036854775807 AS SIGNED)) THEN `s0`.`amount` END) > 9223372036854775807 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(CASE WHEN (`s0`.`id` > CAST(9223372036854775807 AS SIGNED)) THEN `s0`.`amount` END) < -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(CASE WHEN (`s0`.`id` > CAST(9223372036854775807 AS SIGNED)) THEN `s0`.`amount` END) AS SIGNED) END, 0) AS `c0` FROM `phase66`.`s03 orders` AS `s0`) SELECT `t1`.`c0` AS `z` FROM `p0` AS `t1`"
    ),
}
# main's MySQL blockers (code, detail, line, column) of each S03_REFUSALS shape,
# under either policy it is refused with.
S03_REFUSAL_BLOCKERS = {
    "c1_beside_composed": [
        ("PIE-B1003", "aggregate_composition_not_admitted_on_target", 21, 17),
    ],
    "c1_parenthesized_argument": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "c1_qualified_key": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "c2_parenthesized_test": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 19, 9),
    ],
    "c2_two_fields": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 19, 9),
    ],
    "ctl_c_beside_count": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "ctl_c_beside_direct_sum": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 21, 9),
    ],
    "ctl_c_bind_safe_literal": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
    ],
    "ctl_c_compound_test": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "ctl_c_narrow_argument": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "ctl_c_negative_literal": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
    ],
    "ctl_c_order_by": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 20, 9),
    ],
    "ctl_c_other_operator": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
    ],
    "ctl_c_row_alias": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 21, 9),
    ],
    "ctl_c_test_on_int_isnone": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 18, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 19, 9),
    ],
    "ctl_c_upstream": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 26, 9),
    ],
    "ctl_c_where": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 21, 9),
    ],
    "ctl_j_from_side_key": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "ctl_j_inner_joined_side": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "ctl_j_two_sums": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 23, 9),
    ],
    "ctl_j_where": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 23, 9),
    ],
    "ctl_t_plain_first_level": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 25, 9),
    ],
    "ctl_t_second_where": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 31, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 32, 9),
    ],
    "ctl_t_third_level": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 23, 9),
    ],
    "imported_source": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 9, 9),
    ],
    "j1_left": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "j2_on_reversed": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "j2_parenthesized_on": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "j2_parenthesized_sum": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
    "t2_extra_upstream_count": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 23, 9),
    ],
    "t1_upstream_subset": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 29, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 30, 9),
    ],
    "t2_upstream_subset": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9),
    ],
}


# Phase77 S15: the candidate emission experiment's world (its forms.json
# `world`): `id`, `n` and `d` non-null and `a` and `b` nullable BIGINT over all
# of signed 64 bits, `u` and `v` non-null and `x` and `y` nullable finite
# DOUBLE. ``side=True`` (MySQL only) adds the refusal probes' narrow INT `k`,
# DECIMAL(9, 2) `c` and VARCHAR(64) `t`.
_REMAINDER_FIELDS = (
    ("id", "Int", False),
    ("a", "Int", True),
    ("b", "Int", True),
    ("n", "Int", False),
    ("d", "Int", False),
    ("x", "Float", True),
    ("y", "Float", True),
    ("u", "Float", False),
    ("v", "Float", False),
)
_REMAINDER_SIDE_FIELDS = (
    ("k", "Int", False),
    ("c", "Decimal(9, 2)", True),
    ("t", "Text", True),
)
_REMAINDER_SELECT = "table result:\n    from nums\n    select:\n"
_REMAINDER_BODY = _REMAINDER_SELECT + "        id\n"


def _numeric_contract(target, sources):
    """The S15 and R08 experiments' contract: each of ``sources`` as (source,
    relation, fields, premises), its relation in `phase66` (MySQL) or
    `public`, its ``fields`` as (name, nullable, storage, domain) and its
    ``premises`` after the two that every source states."""
    mysql = target == "mysql"
    return {
        "format": "pietto.emission-contract.v1",
        "target": {"family": target, "release": "8.4.12" if mysql else "18.6"},
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": source},
                "relation": {
                    "namespace": "phase66" if mysql else "public",
                    "name": relation,
                },
                "scan": "relation_rows",
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                    *premises,
                ],
                "fields": [
                    {
                        "ordinal": ordinal,
                        "name": name,
                        "column": name,
                        "representation": {
                            "storage": storage,
                            "nullable": nullable,
                            "domain": domain,
                        },
                    }
                    for ordinal, (name, nullable, storage, domain) in enumerate(fields)
                ],
            }
            for source, relation, fields, premises in sources
        ],
        "environment": [
            {
                "key": "client_encoding",
                "scope": "statement",
                "value": "utf8mb4" if mysql else "UTF8",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "lower_case_table_names=0" if mysql else "quoted_exact",
            },
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "mysql_prepared" if mysql else "postgres_extended",
            },
        ],
    }


def remainder_world(directory, target, body, policy="preserve_literals", side=False):
    """``body`` after the S15 world's header (main.pietto is the experiment's
    form source when ``body`` is one of REMAINDER_CELLS)."""
    fields = _REMAINDER_FIELDS + (_REMAINDER_SIDE_FIELDS if side else ())
    assert target == "mysql" or not side
    int64 = {"kind": "int_range", "min": str(-(1 << 63)), "max": str((1 << 63) - 1)}
    physical = {
        "Int": ({"kind": "pg_int8" if target == "postgres" else "my_bigint"}, int64),
        "Float": (
            {"kind": "pg_float8" if target == "postgres" else "my_double"},
            {"kind": "finite_float", "format": "binary64"},
        ),
        "k": (
            {"kind": "my_int"},
            {"kind": "int_range", "min": str(-(1 << 31)), "max": str((1 << 31) - 1)},
        ),
        "c": (
            {"kind": "my_decimal", "precision": 9, "scale": 2},
            {"kind": "decimal", "precision": 9, "scale": 2},
        ),
        "t": (
            {"kind": "my_varchar", "length": 64},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        ),
    }
    carriers = {
        name: physical[name if name in physical else tag] for name, tag, _ in fields
    }
    contract = _numeric_contract(
        target,
        [
            (
                "nums",
                "s15 nums",
                [(name, nullable, *carriers[name]) for name, tag, nullable in fields],
                (),
            )
        ],
    )
    header = "".join(
        f"    {name}: {tag}{' | None' if nullable else ''}\n"
        for name, tag, nullable in fields
    )
    source = (
        f"shape Num:\n{header}"
        f'source nums: Num = {target}.table("opaque.locator.not.sql")\n{body}'
    )
    return build_case(
        directory, {"main.pietto": source}, encoded(contract).decode(), policy
    )


# The experiment's open forms (P-S15-1..3, 7..10), each a MySQL S15 cell, the
# SQL each emits (also the experiment's byte source), and its four MySQL
# `Float /` forms (P-S15-4..6, 11), which keep main's refusal.
REMAINDER_CELLS = {
    "s15_int_mod_nullable": _REMAINDER_BODY + "        r = a % b\n",
    "s15_int_mod_nonnull": _REMAINDER_BODY + "        r = n % d\n",
    "s15_int_mod_mixed": _REMAINDER_BODY + "        r1 = a % d\n        r2 = n % b\n",
    "s15_float_mod_nullable": _REMAINDER_BODY + "        r = x % y\n",
    "s15_float_mod_nonnull": _REMAINDER_BODY + "        r = u % v\n",
    "s15_float_mod_mixed": _REMAINDER_BODY + "        r1 = x % v\n        r2 = u % y\n",
    "s15_mod_cells": _REMAINDER_BODY
    + "        a\n        x\n        r = a % b\n        m = x % y\n",
}
REMAINDER_DIVISIONS = {
    "s15_float_div_nullable": _REMAINDER_BODY + "        q = x / y\n",
    "s15_float_div_nonnull": _REMAINDER_BODY + "        q = u / v\n",
    "s15_float_div_mixed": _REMAINDER_BODY + "        q1 = x / v\n        q2 = u / y\n",
    "s15_all_cells": _REMAINDER_BODY
    + "        a\n        x\n        r = a % b\n        q = x / y\n        m = x % y\n",
}
# The MySQL SQL of each open form, under either literal policy (PostgreSQL's
# keeps main's bytes; its Float `%` is the exact binary64 lowering).
REMAINDER_CELL_SQL = {
    "s15_int_mod_nullable": "SELECT `s0`.`id` AS `id`, (`s0`.`a` % `s0`.`b`) AS `r` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_int_mod_nonnull": "SELECT `s0`.`id` AS `id`, (`s0`.`n` % `s0`.`d`) AS `r` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_int_mod_mixed": "SELECT `s0`.`id` AS `id`, (`s0`.`a` % `s0`.`d`) AS `r1`, (`s0`.`n` % `s0`.`b`) AS `r2` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_float_mod_nullable": "SELECT `s0`.`id` AS `id`, (`s0`.`x` % `s0`.`y`) AS `r` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_float_mod_nonnull": "SELECT `s0`.`id` AS `id`, (`s0`.`u` % `s0`.`v`) AS `r` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_float_mod_mixed": "SELECT `s0`.`id` AS `id`, (`s0`.`x` % `s0`.`v`) AS `r1`, (`s0`.`u` % `s0`.`y`) AS `r2` FROM `phase66`.`s15 nums` AS `s0`",
    "s15_mod_cells": "SELECT `s0`.`id` AS `id`, `s0`.`a` AS `a`, `s0`.`x` AS `x`, (`s0`.`a` % `s0`.`b`) AS `r`, (`s0`.`x` % `s0`.`y`) AS `m` FROM `phase66`.`s15 nums` AS `s0`",
}
_REMAINDER_WHERE = "table result:\n    from nums\n    where n == d\n    select:\n"
_REMAINDER_IDENTITY = "def f(p: Int | None) -> Int | None: return p\n"
# Refused MySQL bodies over remainder_world(side=True), each `%` outside its
# cell, with the blockers (code, detail, line, column) main reports for them
# under either literal policy (observed on 0.1.11, byte for byte the same
# documents as the candidate's). The first ten are the forged shapes.
REMAINDER_REFUSALS = {
    "beside_s01": _REMAINDER_SELECT + "        r = a % b\n        s = a + b\n",
    "beside_comparison": _REMAINDER_SELECT + "        r = a % b\n        e = n == d\n",
    "under_where": _REMAINDER_WHERE + "        r = a % b\n",
    "beside_decimal": _REMAINDER_SELECT + "        c\n        r = a % b\n",
    "beside_text": _REMAINDER_SELECT + "        t\n        r = a % b\n",
    "beside_narrow": _REMAINDER_SELECT + "        k\n        r = a % b\n",
    "narrow_operand": _REMAINDER_SELECT + "        r = k % a\n",
    "float_beside_s01": _REMAINDER_SELECT + "        m = x % y\n        s = a + b\n",
    "float_beside_comparison": _REMAINDER_SELECT
    + "        m = x % y\n        e = n == d\n",
    "float_under_where": _REMAINDER_WHERE + "        m = x % y\n",
    "def_cell": "def m(p: Int | None, q: Int | None) -> Int | None: return p % q\n"
    + _REMAINDER_SELECT
    + "        r = m(a, b)\n",
    "def_beside": _REMAINDER_IDENTITY
    + _REMAINDER_SELECT
    + "        f(a)\n        r = a % b\n",
    "def_argument": _REMAINDER_IDENTITY + _REMAINDER_SELECT + "        r = f(a % b)\n",
    "literal_operand": _REMAINDER_SELECT + "        r = a % 2\n",
    "nested": _REMAINDER_SELECT + "        r = (a % b) + n\n",
    "beside_abs": _REMAINDER_SELECT + "        r = a % b\n        s = abs(a)\n",
    "beside_int_division": _REMAINDER_SELECT + "        r = a % b\n        q = a / b\n",
    "beside_float_division": _REMAINDER_SELECT
    + "        r = a % b\n        q = x / y\n",
}
_INT_MOD = ("PIE-B1003", "binary_operator_not_admitted")
_FLOAT_MOD = ("PIE-B1003", "float_remainder_exact_binary64_not_realized")
REMAINDER_REFUSAL_BLOCKERS = {
    "beside_s01": [
        (*_INT_MOD, 18, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 19, 9),
    ],
    "beside_comparison": [(*_INT_MOD, 18, 9)],
    "under_where": [(*_INT_MOD, 19, 9)],
    "beside_decimal": [(*_INT_MOD, 19, 9)],
    "beside_text": [(*_INT_MOD, 19, 9)],
    "beside_narrow": [(*_INT_MOD, 19, 9)],
    "narrow_operand": [(*_INT_MOD, 18, 9)],
    "float_beside_s01": [
        (*_FLOAT_MOD, 18, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 19, 9),
    ],
    "float_beside_comparison": [(*_FLOAT_MOD, 18, 9)],
    "float_under_where": [(*_FLOAT_MOD, 19, 9)],
    "def_cell": [(*_INT_MOD, 19, 9)],
    "def_beside": [(*_INT_MOD, 20, 9)],
    "def_argument": [(*_INT_MOD, 19, 9)],
    "literal_operand": [(*_INT_MOD, 18, 9)],
    "nested": [(*_INT_MOD, 18, 9)],
    "beside_abs": [
        (*_INT_MOD, 18, 9),
        ("PIE-B1002", "abs_result_outside_physical_range", 19, 9),
    ],
    "beside_int_division": [(*_INT_MOD, 18, 9), (*_INT_MOD, 19, 9)],
    "beside_float_division": [
        (*_INT_MOD, 18, 9),
        ("PIE-B1003", "float_division_not_realized", 19, 9),
    ],
}
# The four MySQL `Float /` forms over remainder_world, as main refuses them.
REMAINDER_DIVISION_BLOCKERS = {
    "s15_float_div_nullable": [("PIE-B1003", "float_division_not_realized", 16, 9)],
    "s15_float_div_nonnull": [("PIE-B1003", "float_division_not_realized", 16, 9)],
    "s15_float_div_mixed": [
        ("PIE-B1003", "float_division_not_realized", 16, 9),
        ("PIE-B1003", "float_division_not_realized", 17, 9),
    ],
    "s15_all_cells": [
        (*_INT_MOD, 18, 9),
        ("PIE-B1003", "float_division_not_realized", 19, 9),
        (*_FLOAT_MOD, 20, 9),
    ],
}


# Phase77 R08: the candidate emission experiment's world (its forms.json
# `world`, r08_nums: BIGINT `id`, `b` and `d`, INT `i` and `j` and SMALLINT
# `s` and `t`, `i`, `s` and `b` nullable) and its refusal controls' sources
# `more`, of the same shape, and `narrow` (non-null BIGINT `id`, `x` declared
# over [-100, 100] and `y` over [2, 100], and INT `j`); every other field is
# declared over exactly its storage's signed range.
_DIVISION_SHAPES = {
    "Num": (
        ("id", 64, False, None),
        ("i", 32, True, None),
        ("j", 32, False, None),
        ("s", 16, True, None),
        ("t", 16, False, None),
        ("b", 64, True, None),
        ("d", 64, False, None),
    ),
    "Narrow": (
        ("id", 64, False, None),
        ("x", 64, False, (-100, 100)),
        ("y", 64, False, (2, 100)),
        ("j", 32, False, None),
    ),
}
# Each source as (name, shape, locator), in declaration order.
_DIVISION_SOURCES = (
    ("nums", "Num", "opaque"),
    ("more", "Num", "more"),
    ("narrow", "Narrow", "narrow"),
)
_DIVISION_STORAGE = {
    "postgres": {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"},
    "mysql": {16: "my_smallint", 32: "my_int", 64: "my_bigint"},
}
DIVISION_SELECT = "table result:\n    from nums\n    select:\n"


def division_world(directory, target, body, policy="preserve_literals", premise=None):
    """``body`` after the shapes and sources of the R08 world that it names,
    as the experiment's observation writes them (main.pietto is the
    experiment's form source when ``body`` is one of DIVISION_CELLS). With
    ``premise``, the contract also states a `value_domain` premise of that
    field equal to its declared domain, scoped to expression site 1: the
    reads in the one cell item of a value_domain control."""
    shapes, lines, sources = [], [], []
    for name, shape, locator in _DIVISION_SOURCES:
        if re.search(rf"\b{name}\b", body) is None:
            continue
        if shape not in shapes:
            shapes.append(shape)
        lines.append(
            f'source {name}: {shape} = {target}.table("{locator}.locator.not.sql")\n'
        )
        selector = {"module": "main.pietto", "kind": "source", "name": name}
        fields, premises = [], []
        for field, bits, nullable, declared in _DIVISION_SHAPES[shape]:
            low, high = declared or (-(1 << (bits - 1)), (1 << (bits - 1)) - 1)
            domain = {"kind": "int_range", "min": str(low), "max": str(high)}
            fields.append(
                (field, nullable, {"kind": _DIVISION_STORAGE[target][bits]}, domain)
            )
            if field == premise:
                premises.append(
                    {
                        "key": "value_domain",
                        "scope": {
                            "kind": "expression",
                            "source": selector,
                            "site": {"kind": "expression_site", "position": 1},
                            "context": {"kind": "select_block", "position": 0},
                        },
                        "value": domain,
                    }
                )
        sources.append((name, f"r08 {name}", fields, premises))
    header = "".join(
        f"shape {shape}:\n"
        + "".join(
            f"    {field}: Int{' | None' if nullable else ''}\n"
            for field, _, nullable, _ in _DIVISION_SHAPES[shape]
        )
        for shape in shapes
    )
    return build_case(
        directory,
        {"main.pietto": header + "".join(lines) + body},
        encoded(_numeric_contract(target, sources)).decode(),
        policy,
    )


def _division_items(*items):
    return DIVISION_SELECT + "".join(f"        {item}\n" for item in items)


# The experiment's six forms (P-R08-1..6), each MySQL `/` a cell of shape b
# (a literal over a field) or c (a field over a literal of 2 or more).
DIVISION_CELLS = {
    "r08_literal_by_bigint": _division_items("id", "q = 100 / b"),
    "r08_literal_dividends": _division_items(
        "id",
        "q1 = 9223372036854775807 / d",
        "q2 = 2147483647 / i",
        "q3 = 32767 / t",
    ),
    "r08_bigint_by_literal": _division_items("id", "q = b / 2"),
    "r08_bigint_by_literal_nonnull": _division_items("id", "q = d / 3"),
    "r08_narrow_by_literal": _division_items(
        "id", "q1 = s / 2", "q2 = j / 3", "q3 = t / 9223372036854775807"
    ),
    "r08_literal_cells": _division_items(
        "id",
        "d",
        "q1 = d / 9223372036854775807",
        "q2 = b / 7",
        "q3 = 7 / s",
        "q4 = i / 2",
    ),
}

# Each form's SQL as (preserve, bind-safe) by target: MySQL's bare
# `(l DIV r)`, PostgreSQL's main bytes (P76-PERF-1).
DIVISION_CELL_SQL = {
    "mysql": {
        "r08_literal_by_bigint": (
            "SELECT `s0`.`id` AS `id`, (CAST(100 AS SIGNED) DIV `s0`.`b`) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, (CAST(? AS SIGNED) DIV `s0`.`b`) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
        ),
        "r08_literal_dividends": (
            "SELECT `s0`.`id` AS `id`, (CAST(9223372036854775807 AS SIGNED) DIV `s0`.`d`) AS `q1`, (CAST(2147483647 AS SIGNED) DIV `s0`.`i`) AS `q2`, (CAST(32767 AS SIGNED) DIV `s0`.`t`) AS `q3` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, (CAST(? AS SIGNED) DIV `s0`.`d`) AS `q1`, (CAST(? AS SIGNED) DIV `s0`.`i`) AS `q2`, (CAST(? AS SIGNED) DIV `s0`.`t`) AS `q3` FROM `phase66`.`r08 nums` AS `s0`",
        ),
        "r08_bigint_by_literal": (
            "SELECT `s0`.`id` AS `id`, (`s0`.`b` DIV CAST(2 AS SIGNED)) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, (`s0`.`b` DIV CAST(? AS SIGNED)) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
        ),
        "r08_bigint_by_literal_nonnull": (
            "SELECT `s0`.`id` AS `id`, (`s0`.`d` DIV CAST(3 AS SIGNED)) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, (`s0`.`d` DIV CAST(? AS SIGNED)) AS `q` FROM `phase66`.`r08 nums` AS `s0`",
        ),
        "r08_narrow_by_literal": (
            "SELECT `s0`.`id` AS `id`, (`s0`.`s` DIV CAST(2 AS SIGNED)) AS `q1`, (`s0`.`j` DIV CAST(3 AS SIGNED)) AS `q2`, (`s0`.`t` DIV CAST(9223372036854775807 AS SIGNED)) AS `q3` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, (`s0`.`s` DIV CAST(? AS SIGNED)) AS `q1`, (`s0`.`j` DIV CAST(? AS SIGNED)) AS `q2`, (`s0`.`t` DIV CAST(? AS SIGNED)) AS `q3` FROM `phase66`.`r08 nums` AS `s0`",
        ),
        "r08_literal_cells": (
            "SELECT `s0`.`id` AS `id`, `s0`.`d` AS `d`, (`s0`.`d` DIV CAST(9223372036854775807 AS SIGNED)) AS `q1`, (`s0`.`b` DIV CAST(7 AS SIGNED)) AS `q2`, (CAST(7 AS SIGNED) DIV `s0`.`s`) AS `q3`, (`s0`.`i` DIV CAST(2 AS SIGNED)) AS `q4` FROM `phase66`.`r08 nums` AS `s0`",
            "SELECT `s0`.`id` AS `id`, `s0`.`d` AS `d`, (`s0`.`d` DIV CAST(? AS SIGNED)) AS `q1`, (`s0`.`b` DIV CAST(? AS SIGNED)) AS `q2`, (CAST(? AS SIGNED) DIV `s0`.`s`) AS `q3`, (`s0`.`i` DIV CAST(? AS SIGNED)) AS `q4` FROM `phase66`.`r08 nums` AS `s0`",
        ),
    },
    "postgres": {
        "r08_literal_by_bigint": (
            'SELECT "s0"."id" AS "id", (CAST(100 AS pg_catalog.int8) / "s0"."b") AS "q" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", (CAST($1 AS pg_catalog.int8) / "s0"."b") AS "q" FROM "public"."r08 nums" AS "s0"',
        ),
        "r08_literal_dividends": (
            'SELECT "s0"."id" AS "id", (CAST(9223372036854775807 AS pg_catalog.int8) / "s0"."d") AS "q1", (CAST(2147483647 AS pg_catalog.int8) / "s0"."i") AS "q2", (CAST(32767 AS pg_catalog.int8) / "s0"."t") AS "q3" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", (CAST($1 AS pg_catalog.int8) / "s0"."d") AS "q1", (CAST($2 AS pg_catalog.int8) / "s0"."i") AS "q2", (CAST($3 AS pg_catalog.int8) / "s0"."t") AS "q3" FROM "public"."r08 nums" AS "s0"',
        ),
        "r08_bigint_by_literal": (
            'SELECT "s0"."id" AS "id", ("s0"."b" / CAST(2 AS pg_catalog.int8)) AS "q" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", ("s0"."b" / CAST($1 AS pg_catalog.int8)) AS "q" FROM "public"."r08 nums" AS "s0"',
        ),
        "r08_bigint_by_literal_nonnull": (
            'SELECT "s0"."id" AS "id", ("s0"."d" / CAST(3 AS pg_catalog.int8)) AS "q" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", ("s0"."d" / CAST($1 AS pg_catalog.int8)) AS "q" FROM "public"."r08 nums" AS "s0"',
        ),
        "r08_narrow_by_literal": (
            'SELECT "s0"."id" AS "id", ("s0"."s" / CAST(2 AS pg_catalog.int8)) AS "q1", ("s0"."j" / CAST(3 AS pg_catalog.int8)) AS "q2", ("s0"."t" / CAST(9223372036854775807 AS pg_catalog.int8)) AS "q3" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", ("s0"."s" / CAST($1 AS pg_catalog.int8)) AS "q1", ("s0"."j" / CAST($2 AS pg_catalog.int8)) AS "q2", ("s0"."t" / CAST($3 AS pg_catalog.int8)) AS "q3" FROM "public"."r08 nums" AS "s0"',
        ),
        "r08_literal_cells": (
            'SELECT "s0"."id" AS "id", "s0"."d" AS "d", ("s0"."d" / CAST(9223372036854775807 AS pg_catalog.int8)) AS "q1", ("s0"."b" / CAST(7 AS pg_catalog.int8)) AS "q2", (CAST(7 AS pg_catalog.int8) / "s0"."s") AS "q3", ("s0"."i" / CAST(2 AS pg_catalog.int8)) AS "q4" FROM "public"."r08 nums" AS "s0"',
            'SELECT "s0"."id" AS "id", "s0"."d" AS "d", ("s0"."d" / CAST($1 AS pg_catalog.int8)) AS "q1", ("s0"."b" / CAST($2 AS pg_catalog.int8)) AS "q2", (CAST($3 AS pg_catalog.int8) / "s0"."s") AS "q3", ("s0"."i" / CAST($4 AS pg_catalog.int8)) AS "q4" FROM "public"."r08 nums" AS "s0"',
        ),
    },
}
# Each form's bind-safe fixed values in slot order, on both targets: its
# literal tokens from left to right.
DIVISION_CELL_FIXED = {
    "r08_literal_by_bigint": (100,),
    "r08_literal_dividends": (9223372036854775807, 2147483647, 32767),
    "r08_bigint_by_literal": (2,),
    "r08_bigint_by_literal_nonnull": (3,),
    "r08_narrow_by_literal": (2, 3, 9223372036854775807),
    "r08_literal_cells": (9223372036854775807, 7, 7, 2),
}
_DIVISION_HEADER_QUERY = "query result(k: Int):\n    from nums\n    select:\n"
_DIVISION_NARROW = "table result:\n    from narrow\n    select:\n        id\n"
_IDENTITY_DEF = "def idn(x: Int) -> Int:\n    return x\n"
_TWO_DEF = "def two() -> Int:\n    return 2\n"
# The experiment's refusal controls (its forms.json refusal_controls, the
# value_domain ones with DIVISION_PREMISES) and nine more: an operand of a
# `def`, its argument or its body (one call over two lines), a cell under a
# WHERE, and one beside a literal, a negation or an `abs` item. Each is a MySQL
# `/` outside T08-1, with the blockers main reports for it as (code, detail,
# line, column) under either literal policy: one PIE-B1003
# `binary_operator_not_admitted` per item holding a `/` unless
# DIVISION_REFUSAL_BLOCKERS says otherwise. No field proves anything: not its
# storage, a declared domain or a premise.
DIVISION_REFUSALS = {
    "bigint_dividend": _division_items("id", "q = b / i"),
    "bigint_dividend_nonnull": _division_items("id", "q = d / j"),
    "storage_int_by_bigint": _division_items("id", "q = i / b"),
    "storage_int_by_bigint_nonnull": _division_items("id", "q = j / d"),
    "storage_int_by_int": _division_items("id", "q = j / i"),
    "storage_small_by_small": _division_items("id", "q = t / s"),
    "storage_small_by_bigint": _division_items("id", "q = s / d"),
    "storage_int_by_small": _division_items("id", "q = i / t"),
    "storage_all_cells": _division_items(
        "id", "i", "t", "b", "q1 = i / b", "q2 = t / d", "q3 = j / s"
    ),
    "declared_narrow_dividend": _DIVISION_NARROW + "        q = x / j\n",
    "declared_narrow_divisor": _DIVISION_NARROW + "        q = id / y\n",
    "value_domain_dividend": _DIVISION_NARROW + "        q = x / x\n",
    "value_domain_divisor": _DIVISION_NARROW + "        q = y / y\n",
    "bigint_by_one": _division_items("id", "q = b / 1"),
    "bigint_by_zero": _division_items("id", "q = b / 0"),
    "bigint_by_negative_literal": _division_items("id", "q = b / -2"),
    "narrow_by_one": _division_items("id", "q = i / 1"),
    "narrow_by_zero": _division_items("id", "q = i / 0"),
    "narrow_by_negative_literal": _division_items("id", "q = i / -2"),
    "bigint_by_nested_literal": _division_items("id", "q = b / (2 + 1)"),
    "literal_by_literal": _division_items("id", "q = 100 / 7"),
    "nested_dividend": _division_items("id", "q = (i + 1) / b"),
    "abs_dividend": _division_items("id", "q = abs(i) / 2"),
    "negated_dividend": _division_items("id", "q = -i / 2"),
    "nested_in_operation": _division_items("id", "q = b / 2 + d"),
    "chain": _division_items("id", "q = b / 2 / t"),
    "in_where": "table result:\n    from nums\n    where b / 2 == d\n    select:\n"
    "        id\n",
    "in_let": "table result:\n    from nums\n    let q = b / 2\n    select:\n"
    "        id\n        q\n",
    "header_dividend": _DIVISION_HEADER_QUERY + "        id\n        q = k / 2\n",
    "header_divisor": _DIVISION_HEADER_QUERY + "        id\n        q = 100 / k\n",
    "beside_narrow_sum": _division_items("id", "q = b / 2", "p = i + j"),
    "beside_s01_cell": _division_items("id", "q = b / 2", "p = b + b"),
    "beside_s15": _division_items("id", "q = b / 2", "r = b % d"),
    "upstream": "query base:\n    from nums\n    select:\n        id\n        b\n"
    "table result:\n    from base\n    select:\n        id\n        q = b / 2\n",
    "join": "table result:\n    from nums\n    inner join more on more.id == nums.id\n"
    "    select:\n        id = nums.id\n        q = nums.b / 2\n",
    "def_argument_divisor": _IDENTITY_DEF + _division_items("id", "q = b / idn(2)"),
    "def_argument_dividend": _IDENTITY_DEF + _division_items("id", "q = idn(100) / b"),
    "def_body_divisor": _TWO_DEF + _division_items("id", "q = b / two()"),
    "def_body_dividend": _TWO_DEF + _division_items("id", "q = two() / b"),
    "def_body_multiline": "def _9() -> Int:\n    return 9\n"
    + _division_items("id", "q = b / _9(\n                )"),
    "under_where": "table result:\n    from nums\n    where id > 0\n    select:\n"
    "        id\n        q = b / 2\n",
    "beside_literal": _division_items("id", "q = b / 2", "c = 5"),
    "beside_negation": _division_items("id", "q = b / 2", "n = -b"),
    "beside_abs": _division_items("id", "q = b / 2", "a = abs(i)"),
}
DIVISION_PREMISES = {"value_domain_dividend": "x", "value_domain_divisor": "y"}
_INT_DIVISION = ("PIE-B1003", "binary_operator_not_admitted")
DIVISION_REFUSAL_BLOCKERS = {
    "storage_all_cells": [
        (*_INT_DIVISION, 17, 9),
        (*_INT_DIVISION, 18, 9),
        (*_INT_DIVISION, 19, 9),
    ],
    "in_where": [(*_INT_DIVISION, 12, 5)],
    "in_let": [(*_INT_DIVISION, 12, 5)],
    "beside_s01_cell": [
        (*_INT_DIVISION, 14, 9),
        ("PIE-B1002", "arithmetic_outside_physical_range", 15, 9),
    ],
    "beside_s15": [(*_INT_DIVISION, 14, 9), (*_INT_DIVISION, 15, 9)],
    "upstream": [(*_INT_DIVISION, 19, 9)],
    **dict.fromkeys(
        (
            "declared_narrow_dividend",
            "declared_narrow_divisor",
            "value_domain_dividend",
            "value_domain_divisor",
        ),
        [(*_INT_DIVISION, 11, 9)],
    ),
    "join": [(*_INT_DIVISION, 16, 9)],
    **dict.fromkeys(
        (
            "def_argument_divisor",
            "def_argument_dividend",
            "def_body_divisor",
            "def_body_dividend",
            "def_body_multiline",
        ),
        [(*_INT_DIVISION, 16, 9)],
    ),
    "under_where": [(*_INT_DIVISION, 15, 9)],
    "beside_negation": [
        (*_INT_DIVISION, 14, 9),
        ("PIE-B1002", "unary_result_outside_physical_range", 15, 9),
    ],
}
