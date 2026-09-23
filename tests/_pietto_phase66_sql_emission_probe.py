"""Closed installed probe and independent data-only public artifact consumer."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast

CONFIG = 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
VARIANTS = {
    "G_emission_table_bag": ("bag",),
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
    "W_join_values": ("left_marker", "right_accumulated", "via_refined"),
    "V_join_full": ("restricted",),
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
    "A_window_named": ("shared",),
    "A_window_qualify": ("selected", "hidden"),
    "V_window_blocked": ("ignore_nulls", "from_last", "offset_range_keys"),
    "V_aggregate_blocked": (
        "sum_direct",
        "avg_direct",
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
}
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
AGGREGATE_SPELLINGS = {"COUNT(": "count", "MIN(": "min", "MAX(": "max"}
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
GROUPING_TAGS = frozenset({"Int", "Bool", "Text", "Decimal"})
COUNT_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
COUNT_MAX = (1 << 63) - 1
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
    if case == "P_native_identifiers":
        return native_fixture(target, variant)
    if case == "M_metamorphic_composition":
        return metamorphic_fixture(target, variant)
    if case in {"R_fixed_direct", "S_fixed_named"}:
        return fixed_fixture(target, case, variant)
    if case in {"M_named_chain", "N_imported_chain", "O_named_later"}:
        return chain_fixture(target, case, variant)
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
    id: Int not null
    flag: Bool nullable
    text: Text not null
    money: Decimal(9, 2) not null
    ratio: Float not null
source rows: Row is {target}.table("opaque.locator.not.sql")
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
    id: Int not null
    decoy: Int not null
    plain: Int not null
    neighbor: Int nullable
source rows: Row is {target}.table("opaque")
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


# Slice15. The chain's second JOIN reads the first JOIN unit as its left input, so
# the LEFT nulling must survive into the RIGHT match. The two UNION ALL forms place
# the same NULL-dropping filter over the union or inside each operand.
METAMORPHIC_BODIES = {
    "join_chain_accumulated": """query result:
    from rows
    left join rows as r:
        from rows
        on rows.id > r.id
    right join rows as last:
        from rows
        on r.id == last.id
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
            "shape One:\n    id: Int not null\n"
            f'source rows: One is {target}.table("opaque")\n'
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
            "true",
            "false",
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
        unused = true
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
                "a.pietto": header + first + "export:\n    table first\n",
                "b.pietto": 'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n',
                "main.pietto": 'import "b.pietto":\n    table Public as Alias\n'
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
    key: Int nullable
    value: Int nullable
    flag: Bool nullable
    label: Text not null
    amount: Decimal(9, 2) not null
    ratio: Float not null
    rid: Int not null
    unique agg_row on rid
source agg: Agg is {target}.table("aggregate.locator.not.sql")
"""
AGGREGATE_KEYS_SOURCE = 'source keys: Agg is {target}.table("keys.locator.not.sql")\n'
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
    satisfying:
        total < 2 and lo > 5 and total >= 1
""",
    ("Y_aggregate_satisfying", "let_reference"): """query result:
    from agg
    let:
        taken = value
    group by:
        key
    select:
        k = key
        total = count(taken)
    satisfying:
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
    ("Z_aggregate_composition", "let_where"): """query result:
    from agg
    let:
        taken = value
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
    inner join agg as r:
        from agg
        on agg.key == r.key
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
    left join agg as r:
        from keys
        on keys.rid == r.rid
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
    left join grouped as r:
        from keys
        on keys.key == r.k
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
    ("V_aggregate_blocked", "sum_hidden_right"): """table g:
    from agg
    select:
        total = sum(value)
query result:
    from keys
    semi join g as r:
        from keys
        on keys.key == r.total
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
    {kind} join g as r:
        from keys
        on keys.key == r.{port}
    select:
        a = keys.key
"""
AGGREGATE_LABELS = {
    ("X_aggregate_global", None): ("c", "cf", "cd", "lo", "hi"),
    ("X_aggregate_grouped", "hidden"): ("total", "cf"),
    ("X_aggregate_grouped", "empty"): ("total", "cf"),
    ("X_aggregate_grouped", "visible"): ("f", "renamed", "again", "total"),
    ("Y_aggregate_constant", None): ("c0", "total"),
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
}
AGGREGATE_LOGICAL = {
    ("X_aggregate_global", None): ("Int",) * 5,
    ("X_aggregate_grouped", "hidden"): ("Int", "Int"),
    ("X_aggregate_grouped", "empty"): ("Int", "Int"),
    ("X_aggregate_grouped", "visible"): ("Bool", "Int", "Int", "Int"),
    ("Y_aggregate_constant", None): ("Int", "Int"),
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
                + "    satisfying:\n        total < 2\n"
            )
            return producer + AGGREGATE_MEMBERSHIP.format(kind="semi", port="k")
        if variant == "filtered_global":
            return (
                "table g:\n    from agg\n    select:\n        total = count()\n"
                "table f:\n    from g\n    where total > 0\n"
                "    select:\n        t = total\n"
                + AGGREGATE_MEMBERSHIP.format(kind="semi", port="t").replace(
                    "join g as r", "join f as r"
                )
            )
        if variant.endswith("global"):
            producer = "table g:\n    from agg\n    select:\n        total = count()\n"
            port = "total"
        else:
            producer = AGGREGATE_NAMED.replace("table grouped:", "table g:")
            port = "k"
        kind = "semi" if variant.startswith("semi") else "anti"
        return producer + AGGREGATE_MEMBERSHIP.format(kind=kind, port=port)
    if case == "Z_aggregate_joined" and variant in {
        "right_accumulated",
        "full_restricted",
    }:
        kind = "right" if variant == "right_accumulated" else "full"
        return (
            AGGREGATE_LEFTISH
            + f"""query result:
    from leftish
    {kind} join agg as r:
        from leftish
        on leftish.lid == r.key
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
            "a.pietto": "{header}" + AGGREGATE_NAMED + "export:\n    table grouped\n",
            "b.pietto": 'import "a.pietto":\n    table grouped as Public\n'
            "export:\n    table Public\n",
            "main.pietto": 'import "b.pietto":\n    table Public as Alias\n'
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
            "a.pietto": header + first + "export:\n    table first\n",
            "b.pietto": 'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n',
            "main.pietto": 'import "b.pietto":\n    table Public as Alias\n'
            + second.replace("from first", "from Alias")
            + final,
        }
        description["selector"]["module"] = "a.pietto"
        if variant != "empty":
            description["relation"]["name"] = "p0"
        if variant == "two_facades":
            source["c.pietto"] = source["b.pietto"]
            source["main.pietto"] = """import "b.pietto":
    table Public as Left
import "c.pietto":
    table Public as Right
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
    inner join first as r:
        from first
        on first.Key == r.Key
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
        w = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and w <= 2
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
                + f'source other: Row is {target}.table("other")\n'
                + """table upstream:
    from rows
    cross join other as r:
        from rows
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


ROW_DIRECT_BODY = """    from rows
    let:
        bumped = id + 1
        doubled = bumped * 2
    where id > 0
    select:
        record_id = id
        next_id = bumped
        twice = doubled
        positive = id > 0
        both = id > 0 and flag
        missing = flag is null
        same_text = text == text
"""
ROW_PRODUCER = """table first:
    from rows
    let:
        bumped = id + 1
    where id > 0
    select:
        kept = id
        stepped = bumped
        flagged = flag
        label = text
"""
ROW_CONSUMER = """query result:
    from {producer}
    let:
        doubled = stepped * 2
    select:
        record_id = kept
        next_id = stepped
        twice = doubled
        positive = kept > 0
        both = kept > 0 and flagged
        missing = flagged is null
        same_text = label == label
"""
ROW_BLOCKED_BODY = {
    "float_arithmetic": "        total = ratio + ratio\n",
    "float_comparison": "        same = ratio == ratio\n",
    "bool_comparison": "        same = flag == flag\n",
    "int_overflow": "        big = id + 1\n",
    "unary_overflow": "        negated = -id\n",
    "modulo": "        rest = id % 2\n",
    "between": "        inside = id between 0 and 1\n",
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
        numbered = row_number() window:
            order by:
                id
        ranked = rank() window:
            order by:
                id
        densely = dense_rank() window:
            order by:
                id
""",
    ("A_window_distribution", "spread"): """query result:
    from rows
    select:
        record_id = id
        fraction = percent_rank() window:
            partition by:
                id
            order by:
                id
        cumulative = cume_dist() window:
            partition by:
                id
            order by:
                id
        bucket = ntile(2) window:
            order by:
                id
""",
    ("A_window_navigation", "offsets"): """query result:
    from rows
    select:
        record_id = id
        previous = lag(id, 1, 0) window:
            order by:
                id
        upcoming = lead(id, 1) window:
            order by:
                id
""",
    ("A_window_frame", "rows"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window:
            order by:
                id
            rows between 1 preceding and current row
        latest = last_value(id) window:
            order by:
                id
            rows between 1 preceding and current row
""",
    ("A_window_frame", "range"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window:
            order by:
                id
            range between 1 preceding and current row
""",
    ("A_window_groups", "exclude"): """query result:
    from rows
    select:
        record_id = id
        peers = first_value(id) window:
            order by:
                id
            groups between 1 preceding and current row exclude current row
""",
    ("A_window_named", "shared"): """query result:
    from rows
    select:
        record_id = id
        ranked = rank() window ordered
        densely = dense_rank() window ordered
    window ordered:
        order by:
            id
""",
    ("A_window_qualify", "selected"): """query result:
    from rows
    select:
        record_id = id
        numbered = row_number() window:
            order by:
                id
    qualify:
        numbered <= 2
""",
    ("A_window_qualify", "hidden"): """query result:
    from rows
    select:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 2
""",
    ("V_window_blocked", "ignore_nulls"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) ignore nulls window:
            order by:
                id
            rows between unbounded preceding and current row
""",
    ("V_window_blocked", "from_last"): """query result:
    from rows
    select:
        record_id = id
        second = nth_value(id, 2) from last window:
            order by:
                id
            rows between unbounded preceding and current row
""",
    ("V_window_blocked", "offset_range_keys"): """query result:
    from rows
    select:
        record_id = id
        earliest = first_value(id) window:
            order by:
                id
                flag
            range between 1 preceding and current row
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
    return {
        "source": header + WINDOW_BODIES[case, variant],
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
    let:
        one = 1
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
    inner join top as r:
        from top
        on top.rid == r.rid
    select:
        a = top.rid
        b = r.rid
""",
    ("O_result_window", "qualify_distinct"): """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 4
""",
    ("O_result_window", "selected_order"): """query result:
    from rows
    select:
        record_id = id
        n = row_number() window:
            order by:
                id
    order by:
        n desc
    limit 2
""",
    ("O_result_window", "qualify_order_limit"): """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 3
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
    return MEMBERSHIP_RIGHT[right] + (
        f"query result:\n    from rows\n    {kind} join ranked as r:\n"
        "        from rows\n        on rows.id == r.rid\n    select:\n"
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
            "shape Row:\n    id: Int not null\n",
            "shape Row:\n    id: Int not null\n    unique by_id on id\n",
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
        "    satisfying:\n        total > 1\n"
        "query result:\n    union all:\n        from s\n        from s\n",
    ),
    ("S_set_producers", "window_union_distinct"): (
        (),
        "table w:\n    from rows\n    select:\n        k = id\n    qualify:\n"
        "        row_number() window:\n            order by:\n                id\n        <= 2\n"
        "table top:\n    from rows\n    select:\n        k = id\n    order by:\n        id\n    limit 2\n"
        "query result:\n    union distinct:\n        from w\n        from top\n",
    ),
    ("S_set_producers", "set_to_window"): (
        (),
        SET_ROWS_AB + "table u:\n    union all:\n        from a\n        from b\n"
        "query result:\n    from u\n    select:\n        k\n"
        "        n = row_number() window:\n            order by:\n                k\n",
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
        return ("sl", "sa", "sb"), (
            "table a:\n    from sa\n    select:\n        v = value\n"
            "table b:\n    from sb\n    select:\n        v = key\n"
            f"table r:\n    {kind} distinct:\n        from a\n        from b\n"
            f"query result:\n    from sl\n    {join} join r as x:\n        from sl\n"
            "        on sl.key == x.v\n    select:\n        a = sl.key\n"
        )
    return SET_BODIES[case, variant]


def set_fixture(target, case, variant):
    """One Slice11 SET witness over the fixed relations or the emission source."""
    sources, body = set_body(case, variant)
    if sources and set(sources) <= SET_AGG_SOURCES:
        header = AGGREGATE_HEADER.format(target=target).split("source agg:", 1)[0]
        header += "".join(
            f'source {name}: Agg is {target}.table("{name}.locator.not.sql")\n'
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
        header += f'source second: Row is {target}.table("second.locator.not.sql")\n'
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
    if variant.startswith("empty"):
        description["relation"]["name"] = "phase66 empty é"
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
                        "flag and true",
                        "flag and false",
                        "flag and flag",
                        "true and flag",
                        "false and flag",
                        "flag or true",
                        "flag or false",
                        "flag or flag",
                        "true or flag",
                        "false or flag",
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
                "a.pietto": header + ROW_PRODUCER + "export:\n    table first\n",
                "main.pietto": 'import "a.pietto":\n    table first as Public\n'
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
    inner join rows as r:
        from rows
        on rows.id == r.id
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
    "cross": ("a",),
    "inner": ("a",),
    "semi": ("a",),
    "anti": ("a",),
    "left_marker": ("a", "p", "m", "c", "t"),
    "right_accumulated": ("a", "b"),
    "via_refined": ("a", "k"),
    "restricted": ("a", "b"),
}
# One filtered producer carrying, in one row, a retained source value, an authored
# literal, a computed value and an ordered LET result. A LEFT row with no match
# must null-extend every one of them.
JOIN_ENRICHED = """table enriched:
    from rows
    let:
        step = id + 1
    where id > 0
    select:
        pid = id
        marker = 1
        computed = id + id
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
    "cross": """query result:
    from rows
    cross join rows as r:
        from rows
    select:
        a = rows.id
""",
    "inner": """query result:
    from rows
    inner join rows as r:
        from rows
        on rows.id == r.id
    select:
        a = rows.id
""",
    "semi": """query result:
    from rows
    semi join rows as r:
        from rows
        on rows.id == r.id
    select:
        a = rows.id
""",
    "anti": """query result:
    from rows
    anti join rows as r:
        from rows
        on rows.id == r.id
    select:
        a = rows.id
""",
    "left_marker": JOIN_ENRICHED
    + """query result:
    from rows
    left join enriched as r:
        from rows
        on rows.id == r.pid
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
    right join rows as r:
        from leftish
        on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
    "via_refined": """relationship link:
    endpoint l: rows
    endpoint r: rows
    on l.id == r.id
query result:
    from rows
    inner join rows as r:
        from rows
        via link: l -> r
        on rows.money == r.money
    select:
        a = rows.id
        k = r.id
""",
    "restricted": JOIN_LEFTISH
    + """query result:
    from leftish
    full join rows as r:
        from leftish
        on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
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
    return {
        "source": header + JOIN_BODIES[variant],
        "contract": encoded(contract).decode(),
        "policy": "preserve_literals",
    }


JOIN_WITNESS_HEADER = """shape Row:
    id: Int not null
    key: Int nullable
source lhs: Row is {target}.table("lhs")
source rhs: Row is {target}.table("rhs")
"""
JOIN_WITNESS_LINK = """relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
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


def source_bytes(source):
    return source.encode("utf-8") if type(source) is str else encoded(source)


def source_files(source):
    return {"main.pietto": source} if type(source) is str else source


# Inputs whose only blocker was the not-yet-implemented WHERE family. Slice6
# implements that family, so each one now emits an independently checked query.
# The retained source purpose and the historical outcome are unchanged history;
# the variant name is not status authority.
MIGRATED_TO_SUCCESS = (
    ("L_emission_blocked", "where_later"),
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
)
# PostgreSQL alone admits the published restricted FULL domain; MySQL keeps its
# typed non-support, so these variants are per-target.
PER_TARGET_STATUS = {
    ("V_join_full", "restricted"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
    ("Z_aggregate_joined", "full_restricted"): {
        "postgres": "VERIFIED",
        "mysql": "BLOCKED",
    },
    # R15 admits GROUPS and its exclusion on PostgreSQL only; MySQL keeps a
    # typed blocker and is never given an emulation.
    ("A_window_groups", "exclude"): {"postgres": "VERIFIED", "mysql": "BLOCKED"},
}


def expected_status(case, variant, target=None):
    if target is not None and (case, variant) in PER_TARGET_STATUS:
        return PER_TARGET_STATUS[case, variant][target]
    if (case, variant) in MIGRATED_TO_SUCCESS:
        return "VERIFIED"
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
    return {"kind": "builtin", "name": tag, "parameters": parameters}


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
        if interval.get("role") in {"namespace", "join_namespace"}
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


def _named_range_provenance(document, descriptors):
    modules = {source["module"] for source in document["request"]["sources"]}
    subjects, positions = {}, {}
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
    }
    for interval in _records(document["ranges"]):
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
            causes = []
            for source in _records(origin["sources"]):
                _keys(source, ("path", "kind", "location"))
                _need(
                    source["path"] in modules and source["kind"] in associations,
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
                if source["kind"] == "authored_cause":
                    causes.append(location)
            _need(len(causes) == 1, "missing authored range cause")
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
        locations = [
            next(s["location"] for s in o["sources"] if s["kind"] == "authored_cause")
            for o in origins(ref)
        ]
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
    if tag == "Bool":
        _need(type(value) is bool)
        return value
    if tag == "Int":
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


def decoded_arguments(document):
    """Ordered native values only from the independently decoded public map."""
    result, assigned, slot_indices = [], {}, {}
    family = document["target"]["family"]
    for use in document["parameter_uses"]:
        value = document["fixed_values"][use["slot"]]
        decoded = _fixed_payload(value["tag"], value["value"])
        if family == "mysql" and value["tag"] == "Bool":
            decoded = int(decoded)
        index = use["server_index"]
        if family == "postgres" and use["slot"] in slot_indices:
            _need(index == slot_indices[use["slot"]])
        if index in assigned:
            _need(
                family == "postgres"
                and assigned[index] == (use["slot"], use["physical_type"])
            )
        else:
            _need(type(index) is int and index == len(result) + 1)
            assigned[index] = use["slot"], use["physical_type"]
            result.append(decoded)
            slot_indices[use["slot"]] = index
    return tuple(result)


def _declared_sources(contract, premises):
    """Each declared source with its own source-scoped premise positions, in order."""
    result = []
    base = len(contract["environment"])
    for source in contract["sources"]:
        positions = [
            base + i for i, p in enumerate(source["premises"]) if p["scope"] == "source"
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
    _need(bool(occurrences), "an emitted query must reach a physical relation")
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
    if len(bodies) > 1:
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
    for i, (item, (kind, subject, rule, key, evidence)) in enumerate(
        zip(actual, expected, strict=True)
    ):
        _need((item["kind"], item["rule"]) == (kind, rule), "generated requirement")
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
    blocks = [
        body["block"]
        for body in bodies
        if not body.get("join") and not body.get("result") and not body.get("set")
    ]
    families: dict[str, list[dict[str, Any]]] = {}
    for item in originals:
        families.setdefault(item["kind"], []).append(item)
        _need(item["premises"] == [], "original requirement premises")
    _need(
        [item["subject"] for item in families.get("scope", ())] == blocks,
        "scope demands do not match the emitted stage bodies",
    )
    _need(
        [item["subject"] for item in families.get("filter", ())] == walk["filters"],
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
    generated_scopes = len(bodies) > 1
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
        else:
            rule = "R02"
        _need(item["rule"] == rule, "original requirement rule")
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
    if not joined and not setted:
        _need(len(scan_occurrences) == 1, "one physical scan without a JOIN")
    description, source_positions = scan_occurrences[0]
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
        _need(subject["position"] not in mapping)
        if kind == "literal":
            _keys(evidence_item, ("tag", "value"))
            _fixed_payload(evidence_item["tag"], evidence_item["value"])
        else:
            _keys(evidence_item, ("operator",))
            _need(evidence_item["operator"] in {"+", "-"})
        mapping[subject["position"]] = evidence_item

    def ref(kind, position):
        return {"kind": kind, "position": position}

    def cause(reference):
        group = provenance[reference["kind"], reference["position"]]
        causes = [
            next(s["location"] for s in o["sources"] if s["kind"] == "authored_cause")
            for o in group
        ]
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

    used = 0
    scalar_nodes = 0

    def expression_ref(positional):
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
        _need(subject["position"] not in seen_expressions)
        return subject

    def scalar(projection, positional=True):
        nonlocal expression_count, used, scalar_nodes
        signs, requirements = [], []
        start_ref = None
        while peek() == "unary_open":
            original = expression_ref(positional)
            interval, text = take("syntax", "unary_open", subject=original)
            _need(text in {"(+", "(-"})
            _need(unary_evidence[original["position"]]["operator"] == text[1])
            signs.append((original, text[1], interval["start"]))
            scalar_ids.add(original["position"])
            seen_expressions.add(original["position"])
            start_ref = start_ref or original
            expression_count += positional
        original = expression_ref(positional)
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
        _need(site["position"] not in seen_sites)
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
            _need(cursor_kind == "literal" and (not bound or specialized[0]))
            slot = None
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
            evidence = literal_evidence[original["position"]]
            _need(evidence["tag"] == tag)
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
        scalar_nodes += 3 + len(signs)
        return {
            "tag": tag,
            "value": payload,
            "expression": start_ref,
            "leaf": original,
            "site": site,
            "slot": slot,
            "requirements": requirements,
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
    ARITHMETIC_TOKENS = {" + ", " - ", " * "}
    LOGICAL_TOKENS = {" AND ", " OR "}
    COMPARISON_TOKENS = {" = ", " <> ", " < ", " <= ", " > ", " >= "}
    COMPARABLE = ("Int", "Text", "Decimal")
    row_bodies: list[dict[str, Any]] = []
    row_generated: list[Any] = []
    row_port_reads: dict[str, Any] = {}
    row_stage_ports: set[str] = set()
    row_rules: dict[int, str] = {}
    row_filters: list[Any] = []
    row_block: list[Any] = [None]
    ROW_OPERATORS = {
        " + ": "+",
        " - ": "-",
        " * ": "*",
        " AND ": "and",
        " OR ": "or",
        " = ": "==",
        " <> ": "!=",
        " < ": "<",
        " <= ": "<=",
        " > ": ">",
        " >= ": ">=",
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
            value["tag"] == "Int" and value["domain"]["kind"] == "int_range",
            "integer range evidence",
        )
        return int(value["domain"]["min"]), int(value["domain"]["max"])

    def row_int(operands, low, high, nullable):
        if family == "mysql":
            storage = {"kind": "my_signed_int"}
        else:
            widths = [INT_BITS.get(o["storage"]["kind"]) for o in operands]
            _need(all(w is not None for w in widths), "integer operand storage")
            storage = {
                "kind": {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"}[
                    max(w for w in widths if w is not None)
                ]
            }
        bits = INT_BITS[storage["kind"]]
        _need(
            -(1 << (bits - 1)) <= low <= high <= (1 << (bits - 1)) - 1,
            "integer result outside its physical range",
        )
        return {
            "tag": "Int",
            "storage": storage,
            "nullable": nullable,
            "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
        }

    def constant_ahead():
        index = cursor
        while index < len(lexical) and lexical[index][0]["role"] == "unary_open":
            index += 1
        return index < len(lexical) and lexical[index][0]["role"] == "anchor_open"

    specialized = [False]

    def row_parse(block, port_kind="stage_port"):
        """Parse one admitted value; a matching scope reads pre-match JOIN ports."""
        role, start = peek(), lexical[cursor][0]["start"]
        if role == "value_scope":
            port = lexical[cursor][0]["subject"]
            _need(port["kind"] == port_kind, "reference port kind")
            _, alias = take("identifier", "value_scope", subject=port)
            original = expression_ref(False)
            take("syntax", "value_qualifier", ".", original)
            seen_expressions.add(original["position"])
            token, name = take("identifier", "value_column")
            expected_ranges.append(("reference", original, start, token["end"]))
            if port_kind == "stage_port":
                row_stage_ports.add(encoded(port).decode())
            return {
                "kind": "reference",
                "expression": original,
                "port": port,
                "name": name,
                "terminal": token["subject"],
                "alias": alias,
            }
        if role == "anchor_open" or (role == "unary_open" and constant_ahead()):
            return {"kind": "constant", "value": scalar(block, positional=False)}
        original = expression_ref(False)
        seen_expressions.add(original["position"])
        if role == "unary_open":
            _, text = take("syntax", "unary_open", subject=original)
            _need(text in {"(+", "(-"}, "unary operator")
            operand = row_parse(block, port_kind)
            closed, _ = take("syntax", "unary_close", ")", original)
            expected_ranges.append(("unary", original, start, closed["end"]))
            return {
                "kind": "sign",
                "expression": original,
                "operator": text[1],
                "operands": [operand],
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
        _need(role in {"binary_open", "comparison_open"}, "row expression node")
        take("syntax", role, "(", original)
        left = row_parse(block, port_kind)
        operator_role = peek()
        _, token = take("syntax", operator_role, subject=original)
        right = row_parse(block, port_kind)
        closing = "binary_close" if role == "binary_open" else "comparison_close"
        closed, _ = take("syntax", closing, ")", original)
        if operator_role == "arithmetic_operator":
            _need(role == "binary_open" and token in ARITHMETIC_TOKENS, "operator")
            kind, enclosure = "arithmetic", "binary"
        elif operator_role == "logical_operator":
            _need(role == "binary_open" and token in LOGICAL_TOKENS, "operator")
            kind, enclosure = "logical", "binary"
        else:
            _need(
                role == "comparison_open"
                and operator_role == "comparison_operator"
                and token in COMPARISON_TOKENS,
                "operator",
            )
            kind, enclosure = "comparison", "comparison"
        expected_ranges.append((enclosure, original, start, closed["end"]))
        return {
            "kind": kind,
            "expression": original,
            "operator": token,
            "operands": [left, right],
        }

    def row_resolve(node, incoming, alias, owner, scopes=None, context=None):
        """Realize one parsed value against its own immediate columns.

        `scopes` names the per-alias pre-match inputs of one JOIN; without it the
        value reads this stage body's single immediate scan.
        """
        if node["kind"] == "constant":
            value = node["value"]
            realization = {"tag": value["tag"], **value_representation(value)}
            for kind, subject, tag in value["requirements"]:
                row_generated.append(
                    (kind, subject, "R04", row_node_premises(tag, (), kind), "checked")
                )
                row_rules[subject["position"]] = "R04"
            return {**realization, "root": value["expression"], "value": value}
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
            _need(within(cause(node["expression"]), cause(owner)))
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
            }
        original = node["expression"]
        kind = "arithmetic" if node["kind"] == "sign" else node["kind"]
        rule = "R06" if kind == "logical" else "R05"
        # One requirement per node in exact rendering order: the node, then the
        # nodes of each operand, so the slot is reserved before descending.
        slot = len(row_generated)
        row_generated.append(None)
        operands = [
            row_resolve(item, incoming, alias, owner, scopes, context)
            for item in node["operands"]
        ]
        tags = tuple(item["tag"] for item in operands)
        # Upstream NULL evidence is preserved, never strengthened here: an operator
        # result is not independently derivable, so it stays None and only a claim
        # of NON_NULL over a nullable operand is rejected later.
        strict = all(o["nullable"] is False for o in operands)
        nullable = None
        if node["kind"] == "sign":
            low, high = row_interval(operands[0])
            if node["operator"] == "-":
                low, high = -high, -low
            result = row_int([operands[0], operands[0]], low, high, nullable)
        elif node["kind"] == "arithmetic":
            (low_l, high_l), (low_r, high_r) = (row_interval(o) for o in operands)
            if node["operator"] == " + ":
                low, high = low_l + low_r, high_l + high_r
            elif node["operator"] == " - ":
                low, high = low_l - high_r, high_l - low_r
            else:
                products = [a * b for a in (low_l, high_l) for b in (low_r, high_r)]
                low, high = min(products), max(products)
            result = row_int(operands, low, high, nullable)
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
        else:
            left, right = operands
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
            result = row_bool(nullable)
        _need(within(cause(original), cause(owner)))
        spelling = (
            node["operator"]
            if node["kind"] in {"sign", "null_test"}
            else ROW_OPERATORS[node["operator"]]
        )
        row_generated[slot] = (
            kind,
            original,
            rule,
            row_node_premises(result["tag"], tags, kind),
            {"operator": spelling},
        )
        # A field sign is a generated arithmetic requirement, but its retained
        # demand is still the R04 literal/unary family, like any authored sign.
        row_rules[original["position"]] = "R04" if node["kind"] == "sign" else rule
        return {
            **result,
            "root": original,
            "operands": [item["root"] for item in operands],
            "kind": kind,
            "strict": strict and node["kind"] != "null_test",
        }

    row_counts = {
        "projection": 0,
        "result": 0,
        "aggregate_projection": 0,
        "window_projection": 0,
        "quotient_field": 0,
        "set_column": 0,
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
        _, spelling = take("syntax", "aggregate_open", subject=subject)
        _need(spelling in AGGREGATE_SPELLINGS, "aggregate spelling")
        distinct, argument = False, None
        if peek() == "aggregate_row_count":
            take("syntax", "aggregate_row_count", "*", subject)
            _need(spelling == "COUNT(", "only a row count has no argument")
        else:
            if peek() == "aggregate_distinct":
                take("syntax", "aggregate_distinct", "DISTINCT ", subject)
                distinct = True
                _need(spelling == "COUNT(", "only count_distinct spells DISTINCT")
            argument = row_parse(block)
        closed, _ = take("syntax", "aggregate_close", ")", subject)
        expected_ranges.append(("aggregate", subject, start, closed["end"]))
        return {
            "aggregate": subject,
            "spelling": spelling,
            "distinct": distinct,
            "argument": argument,
            "function": "count_distinct" if distinct else AGGREGATE_SPELLINGS[spelling],
        }

    def aggregate_realization(function, argument):
        """This result's own domain: a count is not its argument's value range."""
        if function in {"count", "count_distinct"}:
            return {
                "tag": "Int",
                "storage": {"kind": COUNT_STORAGE[family]},
                "nullable": False,
                "domain": {"kind": "int_range", "min": "0", "max": str(COUNT_MAX)},
            }
        _need(argument is not None, "an extreme value needs its own argument")
        assert argument is not None
        # An empty or all-null input has no extreme value, so the result is
        # nullable even over a non-null source column.
        return {
            "tag": argument["tag"],
            "storage": argument["storage"],
            "nullable": True,
            "domain": argument["domain"],
        }

    def window_realization(function, value, default=None):
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
        # A navigation offset or a frame position may address no row at all, so
        # this result gains NULL over a non-null source column unless the
        # occurrence names its own default for that missing row.
        return {
            "tag": value["realization"]["tag"],
            "storage": value["realization"]["storage"],
            "nullable": True
            if default is None
            else bool(value["realization"]["nullable"] or default),
            "domain": value["realization"]["domain"],
        }

    def row_field_realization(field):
        return {"tag": source_type(field)["name"], **field["representation"]}

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

    row_window_owner: dict[str, Any] = {}
    row_window_policies: dict[str, Any] = {}
    row_window_shape: dict[str, tuple[int, int, int]] = {}
    row_window_bags: dict[str, Any] = {}
    row_window_components: set[str] = set()

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
            row_window_owner.setdefault("definition", definition) == definition,
            "one decoded selection owns every window",
        )
        policy = declared["policy"]
        _reference(policy)
        _need(policy["kind"] == "window_policy", "window policy kind")
        key = encoded(origin["window"]).decode()
        _need(
            row_window_policies.setdefault(key, policy) == policy,
            "one window occurrence has one policy",
        )
        _need(
            sum(1 for item in row_window_policies.values() if item == policy) == 1,
            "one policy has one window occurrence",
        )
        arity, components, width = row_window_shape[key]
        inputs = cast(list[Any], declared["inputs"])
        _need(
            type(inputs) is list and len(inputs) == width,
            "a window reads its whole established row shape",
        )
        for item in inputs:
            _reference(item)
            _need(item["kind"] == "stage_port", "window input port kind")
        stage = encoded(origin["stage"]).decode()
        _need(
            encoded(row_window_bags.setdefault(stage, inputs)) == encoded(inputs),
            "one window stage has one input BAG",
        )
        _need(
            encoded(origin["result"]) not in {encoded(item) for item in inputs},
            "a window result is never its own input",
        )
        arguments = cast(list[Any], declared["arguments"])
        uses = cast(list[Any], declared["uses"])
        _need(
            type(arguments) is list and len(arguments) == arity,
            "window argument denominator",
        )
        _need(
            type(uses) is list and len(uses) >= components,
            "window use denominator",
        )
        for item in arguments:
            _reference(item)
            _need(item["kind"] == "window_argument", "window argument kind")
        for item in uses:
            _reference(item)
            _need(item["kind"] == "window_use", "window use kind")
        for item in (*arguments, *uses):
            token = encoded(item).decode()
            _need(
                token not in row_window_components,
                "a window component has one owner",
            )
            row_window_components.add(token)
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
            _need(
                nullable is not False or root["strict"],
                "NON_NULL claimed over a nullable operand",
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
                    counts["aggregate_projection"] + position,
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
            counts["window_projection"] += 1
            _need(encoded(published) == encoded(expected), "window output published")
            return realization
        projection = ref("projection", counts["projection"] + position)
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
            correspondence = {
                "aggregate_transport": aggregate_origin(published, origin),
                **correspondence,
            }
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
        _need(encoded(published) == encoded(expected), "row output correspondence")
        return realization

    def row_select(block, final, cte_terminals):
        """One stage body: parse its columns, bind its scan, then realize them."""
        take("syntax", "select", "SELECT ", block)
        parsed = []
        windows_seen: list[dict[str, Any]] = []
        while True:
            separator = None
            if parsed:
                separator, _ = take("syntax", "separator", ", ")
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
            elif peek() == "aggregate_open":
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
                producer["kind"] in {"select_block", "result_boundary", "set_body"},
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
                    else "result_boundary"
                    if source_body.get("result")
                    else "select_block"
                ),
                "named use must read a complete definition terminal",
            )
            assert source_body is not None
            incoming = source_body["outgoing"]
            scan = {"kind": "named", "body": source_body}
        else:
            _need(producer["kind"] == "select_block", "stage producer kind")
            _, name = take("identifier", "stage_reference", subject=producer)
            source_body = row_ctes.get(name)
            _need(
                source_body is not None
                and source_body is row_bodies[-1]
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
        row_block[0] = block
        determinants = []
        if peek() == "group_by":
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
        else:
            row_generated.append(("stage_use", block, "R03", "naming", None))
            for column in scan["body"]["header"]:
                row_generated.append(("stage_terminal", column, "R03", "naming", None))
        helpers = sum(1 for item in parsed if item["helper"])
        _need(
            all(item["helper"] for item in parsed[len(parsed) - helpers :])
            and (helpers == 0 or not final),
            "hidden ORDER helpers trail the visible columns of a closed stage",
        )
        visible_items = parsed[: len(parsed) - helpers]
        carries = sum(1 for item in visible_items if item["node"]["kind"] == "carry")
        _need(
            all(item["node"]["kind"] == "carry" for item in visible_items[:carries]),
            "carried columns precede computed ones",
        )
        kinds = [item["node"]["kind"] for item in visible_items]
        aggregate_body = "group_key" in kinds or "aggregate" in kinds
        result_body = "result" in kinds
        _need(
            not (aggregate_body and result_body)
            and not (aggregate_body and carries)
            and not (result_body and carries)
            and (not result_body or set(kinds) == {"result"})
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
        for position, item in enumerate(parsed):
            node, export, label = item["node"], item["export"], item["label"]
            _need(final or label == f"c{position}", "stage column label")
            terminal = (
                ref("result_port", row_counts["result"] + position)
                if projection_body
                else export
            )
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
                        ),
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
                                row_counts["aggregate_projection"] + position,
                            ),
                            "R12",
                            [],
                            None,
                        )
                    )
            elif node["kind"] == "aggregate":
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
                        None,
                    )
                )
                argument = None
                if node["argument"] is not None:
                    argument = row_resolve(
                        node["argument"], incoming, alias, node["aggregate"]
                    )
                    _need(
                        "read" in argument and argument["tag"] == "Int",
                        "an aggregate argument is one direct established Int field",
                    )
                realization = aggregate_realization(node["function"], argument)
                read, field, literal, root = None, None, None, None
                origin = {
                    "role": "aggregate_result",
                    "mode": mode,
                    "empty_input": empty_input,
                    "stage": block,
                    "function": node["function"],
                    "determinant": None,
                    "aggregate": node["aggregate"],
                    "arguments": [] if argument is None else [argument["root"]],
                    "inputs": [argument["read"]["terminal"]]
                    if argument is not None
                    else [column["terminal"] for column in incoming],
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
                ports = [
                    window_input(item)
                    for item in node["arguments"]
                    if item["kind"] == "port"
                ]
                value = ports[0] if ports else None
                default = None
                if (
                    function in WINDOW_NAVIGATION_FUNCTIONS
                    and len(node["arguments"]) == 3
                ):
                    third = node["arguments"][2]
                    default = (
                        window_input(third)["realization"]["nullable"]
                        if third["kind"] == "port"
                        else False
                    )
                realization = window_realization(function, value, default)
                read, field, literal, root = None, None, None, None
                origin = {
                    "role": "window_result",
                    "function": function,
                    "selected": True,
                    "window": node["window"],
                    "stage": block,
                    "result": export,
                }
                row_window_shape[encoded(node["window"]).decode()] = (
                    len(node["arguments"]),
                    len(specification["partitions"]) + len(specification["orders"]),
                    len(incoming),
                )
            else:
                row_generated.append(("computed_projection", export, "R05", [], None))
                resolved = row_resolve(node["value"], incoming, alias, export)
                realization = {
                    k: resolved[k] for k in ("tag", "storage", "nullable", "domain")
                }
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
            row_filters.append(predicate)
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
            root = row_resolve(row_parse(block), incoming, alias, predicate)
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
        if projection_body:
            # Hidden helpers are projection-role result ports, never projections.
            row_counts["result"] += len(columns)
            if result_body:
                row_counts["aggregate_projection"] += len(columns) - helpers
            else:
                # A window result carries its own window projection identity.
                row_counts["projection"] += sum(
                    1
                    for item in visible_items
                    if item["node"]["kind"] != "window_result"
                )
        body = {
            "block": block,
            "columns": columns,
            "outgoing": outgoing,
            "projection": projection_body,
            "final": final,
            "scan": scan,
            "header": cte_terminals,
            "deferred": deferred,
            "helpers": helpers,
        }
        row_bodies.append(body)
        _need(len(columns) <= limits["columns"])
        return body

    def result_select(block, final, cte_terminals):
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
            if peek() != "separator":
                break
        from_token, _ = take("syntax", "from", " FROM ")
        producer = from_token["subject"]
        _need(producer["kind"] == "select_block", "result producer kind")
        _, name = take("identifier", "stage_reference", subject=producer)
        source_body = row_ctes.get(name)
        _need(
            source_body is not None
            and source_body is row_bodies[-1]
            and source_body["block"] == producer
            and source_body["projection"]
            and not source_body["final"],
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
                for item, column in zip(parsed, visible, strict=True)
            ),
            "the result tuple is exactly the visible projection, in order",
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
                    read["realization"]["tag"] in ("Int", "Bool", "Text", "Decimal"),
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
        # Independent result-port accounting: every boundary consumes its inputs
        # and re-publishes the visible outputs; the terminal is the last output.
        cursor_position = row_counts["result"]
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
        if cte_terminals is not None:
            _need(cte_terminals == terminals, "declared result terminals")
        row_counts["result"] = cursor_position
        quotient_base = row_counts["quotient_field"]
        if distinct is not None:
            row_counts["quotient_field"] += len(visible)
        row_generated.append(("stage_use", producer, "R03", "naming", None))
        row_generated.extend(
            ("stage_terminal", column, "R03", "naming", None)
            for column in source_body["header"]
        )
        if distinct is not None:
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
                    ("result", {"items": len(order_items)}),
                )
            )
            for entry in order_items:
                evidence = (
                    "result",
                    {
                        "direction": entry["direction"],
                        "nulls": "target_defined",
                        "value_port": entry["port"],
                    },
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
                if entry["read"]["realization"]["nullable"] is not False:
                    row_generated.append(
                        ("order_null_posture", entry["item"], "R19", [], evidence)
                    )
        if limit is not None:
            row_generated.append(
                ("static_limit", limit["limit"], "R21", [], {"value": limit["value"]})
            )
        if not final and (order_ref is not None or limit is not None):
            row_generated.append(
                ("inner_result_boundary", block, "R21", "naming", None)
            )
        for terminal in terminals:
            row_generated.append(
                ("result_terminal_column", terminal, "R03", "naming", None)
            )
        row_generated.append(("read_only_select_bytes", None, "R23", [], None))
        result_nodes[0] += (
            (0 if distinct is None else 1)
            + len(order_items)
            + (0 if limit is None else 1)
        )
        outgoing, columns = [], []
        for position, (item, column) in enumerate(zip(parsed, visible, strict=True)):
            terminal = terminals[position]
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
            "scan": {"kind": "result", "body": source_body},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "result": True,
        }
        row_bodies.append(body)
        return body

    def set_realization(kind, quantifier, reads):
        """Independently derive one SET output's realization from operand reads."""
        tags = {read["realization"]["tag"] for read in reads}
        _need(len(tags) == 1, "SET column logical tags")
        (tag,) = tags
        union_all = (kind, quantifier) == ("union", "all")
        _need(
            tag in {"Int", "Bool", "Text", "Decimal"} or (union_all and tag == "Float"),
            "SET comparison domain",
        )
        first = reads[0]["realization"]
        storage = first["storage"]
        domain = dict(first["domain"])
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
        return {"tag": tag, "storage": storage, "nullable": nullable, "domain": domain}

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
        base = row_counts["result"]
        terminals = [ref("result_port", base + i) for i in range(width)]
        row_counts["result"] += width
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
            "scan": {"kind": "set"},
            "header": cte_terminals,
            "deferred": [],
            "helpers": 0,
            "set": True,
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

    def join_relation(expected_kind):
        """One JOIN input relation, its capture-free alias and pre-match columns."""
        role = peek()
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

    def join_select(join_ref, header):
        """One JOIN occurrence's own generated SELECT, independently reconciled."""
        take("syntax", "select", "SELECT ", join_ref)
        parsed = []
        while True:
            separator = None
            if parsed:
                separator, _ = take("syntax", "separator", ", ")
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
            _need(label == f"c{len(parsed)}", "published JOIN column label")
            parsed.append(
                {
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
            right = join_relation("right")
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
        published = len(left["columns"]) if membership is not None else len(carriers)
        _need(len(parsed) == published, "published JOIN port arity")
        outgoing, columns = [], []
        for position, item in enumerate(parsed):
            side = 0 if position < widths[0] else 1
            carrier = carriers[position]
            _need(
                item["alias"] == inputs[side]["alias"]
                and item["name"] == carrier["name"]
                and item["terminal"] == carrier["terminal"],
                "a published JOIN port must carry its own pre-match column",
            )
            nulled = bool(carrier["nulled"]) or side in nulls
            narrowed = (
                bool(carrier["realization"]["nullable"])
                and not nulled
                and any(carrier is item for item in rejected)
            )
            realization = {
                **carrier["realization"],
                "nullable": (
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
        join_generated(
            join_ref, kind, membership, inputs, equalities, predicate, columns, scopes
        )
        body = {
            "block": join_ref,
            "columns": columns,
            "outgoing": outgoing,
            "projection": False,
            "final": False,
            "scan": {"kind": "join"},
            "header": header,
            "join": True,
            "kind": kind,
            "inputs": inputs,
        }
        row_bodies.append(body)
        _need(len(columns) <= limits["columns"], "JOIN column limit")
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
                in {"select_block", "join", "result_boundary", "set_body"},
                "a generated CTE binds a select block, one JOIN, a result or SET body",
            )
            _need(name == f"p{index}" and name not in row_ctes, "stage CTE name")
            _need(separator is None or separator["subject"] == block, "CTE separator")
            take("syntax", "cte_columns_open", " (", block)
            header = []
            while True:
                terminal_separator = None
                if header:
                    terminal_separator, _ = take("syntax", "terminal_separator", ", ")
                token, text = take("identifier", "terminal_column")
                _need(text == f"c{len(header)}", "declared terminal name")
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
                if peek() != "terminal_separator":
                    break
            take("syntax", "cte_body_open", ") AS (", block)
            row_scopes.append(("cte_definition", block, "R03", "naming", None))
            row_scopes.extend(
                ("terminal_column", terminal, "R03", "naming", None)
                for terminal in header
            )
            row_ctes[name] = (
                join_select(block, header)
                if block["kind"] == "join"
                else result_select(block, False, header)
                if block["kind"] == "result_boundary"
                else set_select(block, False, header)
                if block["kind"] == "set_body"
                else row_select(block, False, header)
            )
            take("syntax", "cte_body_close", ")", block)
            if peek() != "cte_separator":
                break
        final_token, _ = take("syntax", "with_body", " ")
        final_block = final_token["subject"]
        _need(
            final_block["kind"] in {"select_block", "result_boundary", "set_body"},
            "final stage scope",
        )
        if final_block["kind"] == "result_boundary":
            result_select(final_block, True, None)
        elif final_block["kind"] == "set_body":
            set_select(final_block, True, None)
        else:
            row_select(final_block, True, None)

    row_grammar = any(
        interval["role"] == "select" and interval["subject"]["kind"] == "select_block"
        for interval, _ in lexical
    )
    if row_grammar:
        row_driver()
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


def decode_public(data: bytes) -> dict[str, Any]:
    """Validate data only. A decoded document grants no compiler authority."""
    _need(type(data) is bytes and len(data) <= 16 * 1024 * 1024)
    try:
        document: dict[str, Any] = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
        _need(
            type(document) is dict
            and document.get("format") == "pietto.sql-emission.v1"
        )
        status = document.get("status")
        _need(status in {"VERIFIED", "INPUT_REJECTED", "BLOCKED"})
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
                _keys(blocker, ("code", "reason", "subject", "location", "related"))
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
            "parameters": 32768,
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
        _need(bool(sources))
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
                in {"Int", "Bool", "Text", "Decimal", "Float"}
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
        (directory / name).write_text(content, encoding="utf-8")
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
