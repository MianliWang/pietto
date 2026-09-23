"""Closed private schema of `pietto.sql-emission-observation.v1`; data only.

Every record kind lists its exact ordered fields and their closed value types.
Types are a tiny closed vocabulary, never runtime class names:

- ``nat``: JSON integer in ``[0, MAX_NAT]`` (a boolean is never an ordinal);
- ``text`` / ``sql``: JSON string (``sql`` carries the final SQL text);
- ``bool``; ``none`` (a field the admitted domain always leaves empty);
- ``nullable``: ``true``, ``false`` or ``"unknown"``;
- ``data``: bounded JSON with sorted object keys and natural integers;
- ``fixed``: ``{"tag": Bool|Int|Float|Text, "value": ...}`` with Int as
  decimal text and Float as finite binary64 hex (signed zero kept);
- ``plan``: ``{"kind": k, "position": p}``, a retained plan reference or the
  plan scope ``{"kind": "selected_plan", "position": 0}``;
- ``subject``: a ``plan`` object or a local reference;
- ``scope``: ``"statement"``, an owner reference, or ``[owner, site plan ref]``;
- ``@a|b``: local reference ``[kind, index]`` to one of the listed kinds;
- ``?T``: ``T`` or null; ``*T``: list of ``T``.

This module imports nothing from the compiler and is shared by the runtime
exporter and the pure boundary only as constants and primitive encoders.
"""

from __future__ import annotations

import json

__all__: tuple[str, ...] = ()

FORMAT = "pietto.sql-emission-observation.v1"
ROOT = ("artifact", 0)

# Private codec limits (the only limits this format owns).
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
MAX_JSON_VALUES = 1 << 20
MAX_RECORDS = 1 << 17
MAX_EDGES = 1 << 19
MAX_DEPTH = 32
MAX_TEXT_BYTES = 1024 * 1024
MAX_SQL_BYTES = 8 * 1024 * 1024
MAX_NAT = (1 << 31) - 1
MAX_NAT_DIGITS = 10
MAX_INT_TEXT = 20
MAX_FLOAT_TEXT = 32

SCOPE_KIND = "selected_plan"
# The retained Phase65 plan reference kinds, spelled as data.
PLAN_KINDS = frozenset(
    {
        "literal_site",
        "literal_slot",
        "fixed_literal_value",
        "bind_use",
        "set_body",
        "set_operand",
        "set_input",
        "set_column",
        "result_boundary",
        "result_port",
        "distinct",
        "quotient_field",
        "relation_order",
        "order_item",
        "order_expression",
        "order_use",
        "hidden_order_requirement",
        "result_limit",
        "result_export",
        "window",
        "window_use",
        "window_argument",
        "window_policy",
        "window_projection",
        "aggregation",
        "group_key",
        "aggregate",
        "aggregate_projection",
        "aggregate_risk",
        "join",
        "join_input",
        "join_port",
        "relationship_match",
        "join_tail",
        "single_match",
        "single_match_proof",
        "select_block",
        "expression_site",
        "expression",
        "operand",
        "stage_port",
        "let_value",
        "filter",
        "definition",
        "input_use",
        "source_port",
        "input_port",
        "export",
        "projection",
        "boundary",
        "symbol",
        "origin",
        "demand",
    }
)

_VALUE = "@sql_anchor|sql_unary|sql_operation|sql_stage_reference"
_UNIT = "row_body|row_result_body|join_body|set_body"
_PRODUCER = "@bound_source|row_body|row_result_body|set_body|join_body"
_ROW_COLUMN = (
    "*@row_carry_column|row_value_column|aggregate_key_column|"
    "aggregate_value_column|aggregate_projection_column|window_column|"
    "window_projection_column"
)
_QUERY = "@sql_select|sql_row_query|sql_join_query"

RECORDS: dict[str, tuple[tuple[str, str], ...]] = {
    "artifact": (
        ("request", "@request"),
        ("ast", _QUERY),
        ("rendered", "@rendered"),
        ("original_requirements", "*@original_requirement"),
        ("generated_requirements", "*@generated_requirement"),
        ("fixed_values", "*@fixed_value"),
        ("parameter_uses", "*@native_use"),
        ("diagnostics", "data"),
    ),
    "request": (
        ("family", "text"),
        ("release", "text"),
        ("accepted_bytes", "text"),
        ("normalized_bytes", "text"),
        ("owner", "@owner"),
        ("literal_policy", "text"),
        ("modules", "data"),
        ("target_request", "data"),
        ("sources", "*@bound_source"),
        ("premises", "*@premise"),
        ("definitions", "*@scope_definition"),
        ("uses", "*@scope_use"),
        ("input_blockers", "data"),
    ),
    "owner": (("module", "text"), ("kind", "text"), ("name", "text")),
    "bound_source": (
        ("owner", "@owner"),
        ("selector", "text"),
        ("namespace", "text"),
        ("name", "text"),
        ("fields", "*@bound_field"),
        ("position", "nat"),
    ),
    "bound_field": (
        ("ordinal", "nat"),
        ("name", "text"),
        ("column", "text"),
        ("representation", "text"),
        ("logical", "data"),
        ("nullability", "text"),
        ("decimal", "data"),
    ),
    "premise": (
        ("position", "nat"),
        ("key", "text"),
        ("scope", "scope"),
        ("value", "text"),
    ),
    "scope_definition": (("original", "plan"), ("terminals", "*plan")),
    "scope_use": (
        ("original", "plan"),
        ("producer", "@scope_definition"),
        ("consumer", "@scope_definition"),
        ("bindings", "*@terminal_binding"),
    ),
    "terminal_binding": (
        ("canonical", "plan"),
        ("terminal", "plan"),
        ("input_port", "plan"),
    ),
    "sql_symbol": (("position", "nat"), ("binding", "plan"), ("name", "text")),
    "sql_select": (
        ("request", "@request"),
        ("scan", "@sql_scan|sql_named_use"),
        ("columns", "*@sql_column|sql_literal_column"),
        ("definition", "@scope_definition"),
        ("ctes", "*@sql_cte"),
    ),
    "sql_cte": (
        ("definition", "@scope_definition"),
        ("symbol", "@sql_symbol"),
        ("columns", "*@sql_symbol"),
        ("body", "@sql_select"),
    ),
    "sql_scan": (
        ("source", "plan"),
        ("realization", "@bound_source"),
        ("use", "plan"),
        ("symbol", "@sql_symbol"),
        ("binding", "@scope_use"),
    ),
    "sql_named_use": (
        ("cte", "@sql_cte"),
        ("use", "plan"),
        ("symbol", "@sql_symbol"),
        ("binding", "@scope_use"),
    ),
    "sql_column": (
        ("ordinal", "nat"),
        ("scan", "@sql_scan|sql_named_use"),
        ("source_field", "@bound_field"),
        ("source_port", "plan"),
        ("input_port", "plan"),
        ("export", "plan"),
        ("projection", "plan"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("producer", "@terminal_binding"),
        ("origin", "@sql_scan"),
    ),
    "sql_literal_column": (
        ("ordinal", "nat"),
        ("scan", "@sql_scan|sql_named_use"),
        ("export", "plan"),
        ("projection", "plan"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("origin", "@literal_origin"),
        ("value", "?@sql_anchor|sql_unary"),
        ("producer", "?@terminal_binding"),
    ),
    "literal_origin": (
        ("value", "@sql_anchor|sql_unary"),
        ("export", "plan"),
        ("terminal", "plan"),
    ),
    "sql_unary": (
        ("original", "plan"),
        ("operator", "text"),
        ("operand", "@sql_anchor|sql_unary"),
    ),
    "sql_anchor": (
        ("original", "plan"),
        ("tag", "text"),
        ("physical_type", "text"),
        ("operand", "@sql_literal|sql_parameter"),
    ),
    "sql_literal": (("original", "plan"), ("site", "plan"), ("value", "fixed")),
    "sql_parameter": (
        ("original", "plan"),
        ("site", "plan"),
        ("fixed", "@fixed_value"),
        ("use", "@native_use"),
    ),
    "native_use": (
        ("ordinal", "nat"),
        ("original", "plan"),
        ("slot", "plan"),
        ("physical_type", "text"),
        ("server_index", "nat"),
    ),
    "fixed_value": (
        ("ref", "plan"),
        ("slot", "plan"),
        ("site", "plan"),
        ("value", "fixed"),
    ),
    "sql_row_query": (
        ("request", "@request"),
        ("bodies", "*@row_body|row_result_body"),
        ("nodes", "nat"),
    ),
    "sql_join_query": (
        ("request", "@request"),
        ("units", "*@" + _UNIT),
        ("nodes", "nat"),
    ),
    "row_body": (
        ("definition", "@scope_definition"),
        ("block", "plan"),
        ("block_kind", "text"),
        ("index", "nat"),
        ("scan", "@row_scan|row_named_use|row_stage_use|row_join_use"),
        ("columns", _ROW_COLUMN),
        ("terminals", "*plan"),
        ("predicate", "?@row_predicate"),
        ("final", "bool"),
        ("symbol", "?@sql_symbol"),
        ("cte_columns", "*@sql_symbol"),
        ("aggregation", "?@aggregate_stage"),
        ("window", "?@window_stage"),
    ),
    "row_scan": (
        ("source", "plan"),
        ("realization", "@bound_source"),
        ("use", "plan"),
        ("symbol", "@sql_symbol"),
        ("binding", "@scope_use"),
    ),
    "row_named_use": (
        ("body", "@row_body|row_result_body|set_body"),
        ("use", "plan"),
        ("symbol", "@sql_symbol"),
        ("binding", "@scope_use"),
    ),
    "row_stage_use": (
        ("body", "@row_body"),
        ("block", "plan"),
        ("symbol", "@sql_symbol"),
    ),
    "row_join_use": (
        ("body", "@join_body"),
        ("tail", "plan"),
        ("symbol", "@sql_symbol"),
    ),
    "row_carry_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("input_port", "plan"),
        ("read", "@stage_column"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "row_value_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("projection", "?plan"),
        ("site", "plan"),
        ("expression", "plan"),
        ("value", _VALUE),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
        ("link", "?@terminal_binding"),
    ),
    "row_predicate": (
        ("original", "plan"),
        ("expression", "plan"),
        ("value", _VALUE),
    ),
    "realization": (
        ("tag", "text"),
        ("storage", "data"),
        ("nullable", "nullable"),
        ("domain", "data"),
    ),
    "stage_column": (
        ("position", "nat"),
        ("name", "text"),
        ("terminal", "plan"),
        ("realization", "@realization"),
        ("field", "?@bound_field"),
        ("source_port", "?plan"),
        ("literal", "?@literal_origin"),
        ("scope", "?@sql_symbol"),
        ("aggregate", "?@aggregate_origin"),
        ("window", "?@window_origin"),
    ),
    "sql_stage_reference": (
        ("original", "plan"),
        ("port", "plan"),
        ("column", "@stage_column"),
        ("realization", "@realization"),
        ("scope", "?@sql_symbol"),
    ),
    "sql_operation": (
        ("original", "plan"),
        ("kind", "text"),
        ("operator", "text"),
        ("operands", "*" + _VALUE),
        ("realization", "@realization"),
    ),
    "join_body": (
        ("join", "plan"),
        ("join_kind", "text"),
        ("on", "?plan"),
        ("index", "nat"),
        ("inputs", "*@join_input"),
        ("equalities", "*@join_equality"),
        ("predicate", "?" + _VALUE),
        ("columns", "*@join_column"),
        ("symbol", "@sql_symbol"),
        ("cte_columns", "*@sql_symbol"),
        ("membership", "?text"),
        ("sentinel", "?plan"),
    ),
    "join_input": (
        ("original", "plan"),
        ("ordinal", "nat"),
        ("use", "?@scope_use"),
        ("producer", _PRODUCER),
        ("symbol", "@sql_symbol"),
        ("columns", "*@stage_column"),
        ("ports", "*plan"),
        ("source", "?plan"),
    ),
    "join_equality": (
        ("original", "plan"),
        ("left", "@stage_column"),
        ("right", "@stage_column"),
        ("left_port", "plan"),
        ("right_port", "plan"),
        ("left_scope", "@sql_symbol"),
        ("right_scope", "@sql_symbol"),
    ),
    "join_column": (
        ("position", "nat"),
        ("port", "plan"),
        ("nulling", "data"),
        ("match", "plan"),
        ("label", "text"),
        ("symbol", "@sql_symbol"),
        ("column", "@stage_column"),
        ("scope", "@sql_symbol"),
        ("read", "@stage_column"),
    ),
    "aggregate_stage": (
        ("aggregation", "plan"),
        ("keys", "*@aggregate_key_column"),
        ("values", "*@aggregate_value_column"),
        ("mode", "text"),
        ("empty_input", "text"),
    ),
    "aggregate_key_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("key", "plan"),
        ("input_port", "plan"),
        ("read", "@stage_column"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "aggregate_value_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("aggregate", "plan"),
        ("function", "text"),
        ("spelling", "text"),
        ("distinct", "bool"),
        ("argument", "?" + _VALUE),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "aggregate_projection_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("projection", "plan"),
        ("input_port", "plan"),
        ("read", "@stage_column"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "aggregate_origin": (
        ("kind", "text"),
        ("aggregation", "plan"),
        ("result", "plan"),
        ("inputs", "*plan"),
        ("key", "?plan"),
        ("aggregate", "?plan"),
        ("function", "?text"),
    ),
    "window_stage": (
        ("ref", "plan"),
        ("definitions", "*@window_definition"),
        ("columns", "*@window_column"),
    ),
    "window_definition": (
        ("index", "nat"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("specification", "@window_specification"),
        ("named_use", "plan"),
    ),
    "window_specification": (
        ("partitions", "*@window_partition"),
        ("orders", "*@window_order_item"),
        ("frame", "?@window_frame"),
        ("symbol", "?@sql_symbol"),
        ("parent", "none"),
    ),
    "window_partition": (("binding", "data"), ("read", "@stage_column")),
    "window_order_item": (
        ("position", "nat"),
        ("read", "@stage_column"),
        ("direction", "text"),
        ("nulls", "none"),
        ("binding", "data"),
    ),
    "window_frame": (
        ("unit", "text"),
        ("start", "data"),
        ("end", "data"),
        ("exclusion", "?text"),
    ),
    "window_argument": (
        ("position", "nat"),
        ("role", "text"),
        ("read", "?@stage_column"),
        ("literal", "?text"),
    ),
    "window_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("window", "plan"),
        ("function", "text"),
        ("arguments", "*@window_argument"),
        ("specification", "@window_specification"),
        ("inputs", "*plan"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
        ("selected", "bool"),
    ),
    "window_projection_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("projection", "plan"),
        ("input_port", "plan"),
        ("read", "@stage_column"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "window_origin": (
        ("kind", "text"),
        ("window", "plan"),
        ("result", "plan"),
        ("inputs", "*plan"),
        ("function", "?text"),
        ("selected", "bool"),
        ("definition", "none"),
        ("policy", "plan"),
    ),
    "row_result_body": (
        ("definition", "@scope_definition"),
        ("boundaries", "*plan"),
        ("index", "nat"),
        ("scan", "@row_result_use"),
        ("columns", "*@result_column"),
        ("terminals", "*plan"),
        ("distinct", "?@result_distinct"),
        ("order", "?@result_order"),
        ("limit", "?@result_limit"),
        ("final", "bool"),
        ("symbol", "?@sql_symbol"),
        ("cte_columns", "*@sql_symbol"),
        ("predicate", "none"),
        ("aggregation", "none"),
        ("window", "none"),
    ),
    "row_result_use": (
        ("body", "@row_body"),
        ("boundary", "plan"),
        ("symbol", "@sql_symbol"),
    ),
    "result_column": (
        ("ordinal", "nat"),
        ("export", "plan"),
        ("projection_port", "plan"),
        ("read", "@stage_column"),
        ("output", "plan"),
        ("stages", "*@result_stage"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "result_stage": (
        ("boundary", "plan"),
        ("input_port", "plan"),
        ("output_port", "plan"),
        ("quotient_field", "?plan"),
    ),
    "result_distinct": (
        ("distinct", "plan"),
        ("boundary", "plan"),
        ("fields", "*plan"),
    ),
    "result_order": (
        ("order", "plan"),
        ("boundary", "plan"),
        ("carrier", "text"),
        ("items", "*@result_order_item"),
    ),
    "result_order_item": (
        ("position", "nat"),
        ("item", "plan"),
        ("expression", "plan"),
        ("use", "plan"),
        ("port", "plan"),
        ("read", "@stage_column"),
        ("direction", "text"),
        ("nulls", "none"),
        ("carrier", "text"),
    ),
    "result_limit": (("limit", "plan"), ("boundary", "plan"), ("value", "nat")),
    "set_body": (
        ("definition", "@scope_definition"),
        ("body", "plan"),
        ("index", "nat"),
        ("kind", "text"),
        ("quantifier", "text"),
        ("requires_equivalence", "bool"),
        ("fold", "text"),
        ("operands", "*@set_operand_body"),
        ("columns", "*@set_column"),
        ("terminals", "*plan"),
        ("final", "bool"),
        ("symbol", "?@sql_symbol"),
        ("cte_columns", "*@sql_symbol"),
        ("predicate", "none"),
        ("aggregation", "none"),
        ("window", "none"),
    ),
    "set_operand_body": (
        ("position", "nat"),
        ("operand", "plan"),
        ("use", "@scope_use"),
        ("producer", _PRODUCER),
        ("source", "?plan"),
        ("symbol", "@sql_symbol"),
        ("columns", "*@stage_column"),
        ("inputs", "*plan"),
    ),
    "set_column": (
        ("ordinal", "nat"),
        ("source", "plan"),
        ("export", "plan"),
        ("output", "plan"),
        ("inputs", "*@stage_column"),
        ("realization", "@realization"),
        ("symbol", "@sql_symbol"),
        ("label", "text"),
        ("column", "@stage_column"),
    ),
    "rendered": (
        ("ast", _QUERY),
        ("sql", "sql"),
        ("events", "*@event"),
        ("expression_ranges", "*@event"),
    ),
    "event": (
        ("kind", "text"),
        ("role", "text"),
        ("subject", "plan"),
        ("start", "nat"),
        ("end", "nat"),
        ("origins", "*@origin"),
    ),
    "origin": (
        ("ref", "plan"),
        ("position", "nat"),
        ("role", "text"),
        ("nature", "text"),
        ("generated_reason", "?text"),
        ("consuming_definition", "plan"),
        ("associations", "*@association"),
    ),
    "association": (
        ("position", "nat"),
        ("kind", "text"),
        ("source", "text"),
        ("site", "nat"),
        ("location", "data"),
        ("path", "data"),
        ("hop", "data"),
    ),
    "original_requirement": (
        ("entry", "plan"),
        ("family", "text"),
        ("subkind", "?text"),
        ("subject", "plan"),
        ("rule", "text"),
        ("evidence", "data"),
    ),
    "generated_requirement": (
        ("kind", "text"),
        ("subject", "subject"),
        ("rule", "text"),
        ("premises", "*@premise"),
    ),
}

# Fields read as retained upstream evidence through a runtime object rather than
# as that object's own field of the same name and type.
DERIVED: dict[str, frozenset[str]] = {
    "artifact": frozenset({"diagnostics"}),
    "request": frozenset(
        {
            "owner",
            "literal_policy",
            "modules",
            "target_request",
            "definitions",
            "uses",
            "input_blockers",
        }
    ),
    "owner": frozenset({"module", "kind", "name"}),
    "bound_field": frozenset({"logical", "nullability", "decimal"}),
    "sql_unary": frozenset({"operator"}),
    "sql_anchor": frozenset({"tag"}),
    "sql_literal": frozenset({"value"}),
    "fixed_value": frozenset({"site", "value"}),
    "row_body": frozenset({"block_kind"}),
    "sql_operation": frozenset({"operator"}),
    "join_body": frozenset({"join_kind", "on"}),
    "join_column": frozenset({"nulling"}),
    "window_definition": frozenset({"named_use"}),
    "window_partition": frozenset({"binding", "read"}),
    "window_order_item": frozenset({"binding"}),
    "set_body": frozenset({"requires_equivalence", "fold"}),
    "origin": frozenset({"role", "associations"}),
    "association": frozenset({"source", "site", "location", "path", "hop"}),
    "original_requirement": frozenset({"family", "subkind", "subject", "evidence"}),
}
# Runtime-only fields of emission-owned objects that are deliberately not
# transported: verification invocation roots, private caches and upstream
# semantic evidence whose consumed facts are carried by derived fields.
CUTOFF: dict[str, frozenset[str]] = {
    "request": frozenset(
        {"verification", "layout", "report", "source_map", "assessment", "_accepted"}
    ),
    "bound_field": frozenset({"field", "resolution", "decimal_expression"}),
}

RULES = frozenset(f"R{number:02d}" for number in range(1, 27))
TAGS = ("Bool", "Int", "Float", "Text")
FAMILIES = {"postgres": "18.6", "mysql": "8.4.12"}
QUOTES = {"postgres": '"', "mysql": "`"}
PHYSICAL = {
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
}
ANCHOR_SUFFIX = {
    "pg_bool": " AS pg_catalog.bool)",
    "pg_int8": " AS pg_catalog.int8)",
    "pg_float8": " AS pg_catalog.float8)",
    "pg_text": ' AS pg_catalog.text) COLLATE "C"',
    "my_signed_bool": " AS SIGNED)",
    "my_signed_int": " AS SIGNED)",
    "my_double": " AS DOUBLE)",
    "my_utf8mb4_text": " AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin",
}
OPERATORS = {
    "sign": ("+", "-"),
    "arithmetic": ("+", "-", "*"),
    "logical": ("and", "or"),
    "comparison": ("==", "!=", "<", "<=", ">", ">="),
    "null_test": ("is null", "is not null"),
}
COMPARISON_SPELLING = {
    "==": " = ",
    "!=": " <> ",
    "<": " < ",
    "<=": " <= ",
    ">": " > ",
    ">=": " >= ",
}
SET_KINDS = {"union": "UNION", "intersect": "INTERSECT", "except": "EXCEPT"}
SET_QUANTIFIERS = {"all": "ALL", "distinct": "DISTINCT"}
JOIN_SPELLING = {
    "cross": " CROSS JOIN ",
    "inner": " INNER JOIN ",
    "left": " LEFT JOIN ",
    "right": " RIGHT JOIN ",
    "full": " FULL JOIN ",
}
MEMBERSHIP_SPELLING = {"exists": " WHERE EXISTS (", "not_exists": " WHERE NOT EXISTS ("}
DIRECTIONS = {"asc": " ASC", "desc": " DESC"}
CARRIERS = frozenset({"ordinary", "rebound", "completed"})
AGGREGATE_SPELLING = {"COUNT", "MIN", "MAX"}
WINDOW_SPELLING = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
    "first_value": "FIRST_VALUE",
    "last_value": "LAST_VALUE",
    "nth_value": "NTH_VALUE",
}
FRAME_UNITS = {"rows": "ROWS", "range": "RANGE", "groups": "GROUPS"}
FRAME_BOUNDS = {
    "unbounded_preceding": "UNBOUNDED PRECEDING",
    "current_row": "CURRENT ROW",
    "unbounded_following": "UNBOUNDED FOLLOWING",
}
FRAME_OFFSETS = {"offset_preceding": "PRECEDING", "offset_following": "FOLLOWING"}
EXCLUSIONS = {
    "no_others": None,
    "current_row": " EXCLUDE CURRENT ROW",
    "group": " EXCLUDE GROUP",
    "ties": " EXCLUDE TIES",
}
# Syntax roles whose spelling is one closed constant.
SYNTAX = {
    "select": "SELECT ",
    "separator": ", ",
    "qualifier": ".",
    "alias": " AS ",
    "from": " FROM ",
    "with": "WITH ",
    "cte_separator": ", ",
    "cte_columns_open": " (",
    "terminal_separator": ", ",
    "cte_body_open": ") AS (",
    "cte_body_close": ")",
    "with_body": " ",
    "unary_close": ")",
    "anchor_open": "CAST(",
    "value_qualifier": ".",
    "is_null_open": "(",
    "is_null_close": ")",
    "binary_open": "(",
    "binary_close": ")",
    "comparison_open": "(",
    "comparison_close": ")",
    "aggregate_row_count": "*",
    "aggregate_distinct": "DISTINCT ",
    "aggregate_close": ")",
    "window_partition": "PARTITION BY ",
    "window_partition_separator": ", ",
    "window_partition_qualifier": ".",
    "window_spec_separator": " ",
    "window_order": "ORDER BY ",
    "window_order_separator": ", ",
    "window_order_qualifier": ".",
    "window_frame_separator": " ",
    "window_frame_and": " AND ",
    "window_clause": " WINDOW ",
    "window_clause_separator": ", ",
    "window_definition_as": " AS ",
    "window_spec_open": "(",
    "window_spec_close": ")",
    "window_argument_separator": ", ",
    "window_argument_qualifier": ".",
    "window_close": ")",
    "window_over": " OVER ",
    "carry_qualifier": ".",
    "group_key_qualifier": ".",
    "result_qualifier": ".",
    "window_result_qualifier": ".",
    "group_by": " GROUP BY ",
    "group_separator": ", ",
    "grouping_qualifier": ".",
    "where": " WHERE ",
    "satisfying": " WHERE ",
    "distinct": "DISTINCT ",
    "result_carry_qualifier": ".",
    "order_by": " ORDER BY ",
    "order_separator": ", ",
    "order_qualifier": ".",
    "limit": " LIMIT ",
    "set_operand_open": "(",
    "set_input_qualifier": ".",
    "set_qualifier": ".",
    "set_alias": " AS ",
    "set_operand_close": ")",
    "set_fold_open": "(",
    "set_fold_close": ")",
    "join_qualifier": ".",
    "join_alias": " AS ",
    "equality_separator": " AND ",
    "equality_open": "(",
    "equality_qualifier": ".",
    "equality_operator": " = ",
    "equality_close": ")",
    "condition_separator": " AND ",
    "join_column_qualifier": ".",
    "join_on": " ON ",
    "membership_select": "SELECT ",
    "membership_from": " FROM ",
    "correlation": " WHERE ",
    "membership_close": ")",
}
# Expression overlay role -> (first token role(s), last token role(s)).
OVERLAYS = {
    "unary": (("unary_open",), ("unary_close",)),
    "anchor": (("anchor_open",), ("anchor_close",)),
    "reference": (("value_scope",), ("value_column",)),
    "binary": (("binary_open",), ("binary_close",)),
    "comparison": (("comparison_open",), ("comparison_close",)),
    "is_null": (("is_null_open",), ("is_null_close",)),
    "aggregate": (("aggregate_open",), ("aggregate_close",)),
    "window": (("window_open",), ("window_spec_close", "window_reference")),
    "window_specification": (("window_spec_open",), ("window_spec_close",)),
    "grouping": (("grouping_scope",), ("grouping_column",)),
    "order_item": (("order_scope",), ("order_direction",)),
    "relationship_equality": (("equality_open",), ("equality_close",)),
}


def fixed_wire(tag: str, value: object) -> dict[str, object]:
    """The exact typed wire form of one fixed Bool/Int/Float/Text value."""

    if tag == "Int":
        value = str(value)
    elif tag == "Float":
        value = value.hex()  # type: ignore[attr-defined]
    return {"tag": tag, "value": value}


def literal_token(tag: str, value: object, family: str) -> str:
    """The emitted SQL lexeme of one inline fixed literal leaf."""

    if tag == "Bool":
        return "TRUE" if value else "FALSE"
    if tag == "Int":
        return str(value)
    if tag == "Float":
        text = repr(value)
        if family == "postgres":
            return "'" + text + "'"
        return text if "e" in text else text + "e0"
    assert isinstance(value, str)
    if family == "postgres":
        return "E'" + "".join("\\" + format(b, "03o") for b in value.encode()) + "'"
    return "X'" + value.encode().hex() + "'"


def quoted(name: str, family: str) -> str:
    quote = QUOTES[family]
    return quote + name.replace(quote, quote * 2) + quote


def set_spelling(kind: str, quantifier: str) -> str:
    return " " + SET_KINDS[kind] + " " + SET_QUANTIFIERS[quantifier] + " "


def canonical_bytes(document: object) -> bytes:
    """The one canonical encoding: compact UTF-8 JSON and one final LF."""

    return (
        json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
