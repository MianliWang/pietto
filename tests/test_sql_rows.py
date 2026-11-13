"""Admitted row scalars, ordered LET stages, TRUE-only filters and ON context."""

from copy import copy
from dataclasses import replace
import json

import pytest

import _pietto_sql_emission as probe
import _pietto_sql_float_cells as cells
import _pietto_sql_emission_portable as portable
import _pietto_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission import (
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import (
    RowCarryColumn,
    RowScan,
    RowStageUse,
    RowValueColumn,
    SQLRowQuery,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlan

# The only truth tables this file uses. Never Python `and`/`or` or truthiness.
AND = {
    ("T", "T"): "T",
    ("T", "F"): "F",
    ("T", "N"): "N",
    ("F", "T"): "F",
    ("F", "F"): "F",
    ("F", "N"): "F",
    ("N", "T"): "N",
    ("N", "F"): "F",
    ("N", "N"): "N",
}
OR = {
    ("T", "T"): "T",
    ("T", "F"): "T",
    ("T", "N"): "T",
    ("F", "T"): "T",
    ("F", "F"): "F",
    ("F", "N"): "N",
    ("N", "T"): "T",
    ("N", "F"): "N",
    ("N", "N"): "N",
}
RETENTION = (("true", True), ("false", False), ("unknown", False))


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    cache = {}

    def build(target="postgres", case="T_row_direct", variant="table_preserve"):
        key = target, case, variant
        if key not in cache:
            item = probe.fixture(*key)
            checked, outcome = probe.build_case(
                tmp_path_factory.mktemp("row-emission"),
                item["source"],
                item["contract"],
                item["policy"],
            )
            cache[key] = item, checked, outcome
        return cache[key]

    return build


def row_source(target, body, *, header_only=False):
    """The published base shape and source, with one authored stage body."""
    base = probe.fixture(target, "T_row_direct", "table_preserve")
    head = base["source"].split("table result:", 1)[0]
    return head if header_only else head + "table result:\n" + body


def stage_contract(target):
    return probe.fixture(target, "T_row_direct", "table_preserve")["contract"]


def bind_contract(target):
    """The same contract, with the parameter protocol BIND_SAFE actually needs."""
    return probe.fixture(target, "T_row_direct", "query_bind")["contract"]


# --------------------------------------------------------------------------
# R05/R06 public vertical
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (
        ("T_row_direct", "table_preserve"),
        ("T_row_direct", "query_bind"),
        ("T_row_direct", "empty_preserve"),
        ("U_row_named", "named_preserve"),
        ("U_row_named", "imported_bind"),
        ("U_row_named", "empty_preserve"),
    ),
)
def test_real_row_public_vertical(built, target, case, variant):
    item, checked, outcome = built(target, case, variant)
    assert checked.verified
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert type(artifact.ast) is SQLRowQuery
    assert verify_project_sql_emission(artifact, artifact.request).verified
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in public["columns"]] == list(probe.ROW_LABELS)
    assert [c["logical_type"]["name"] for c in public["columns"]] == list(
        probe.ROW_LOGICAL
    )
    assert public["request"]["literal_policy"] == item["policy"]
    assert artifact.rendered.sql == public["sql"].encode("utf-8")
    # A null test is its own NON_NULL operation; nothing else invents NON_NULL.
    assert public["columns"][probe.ROW_LABELS.index("missing")]["nullable"] is False
    assert public["columns"][probe.ROW_LABELS.index("record_id")]["nullable"] is False
    for label in ("next_id", "twice", "positive", "both"):
        assert public["columns"][probe.ROW_LABELS.index(label)]["nullable"] == "unknown"
    storage = [c["representation"]["storage"]["kind"] for c in public["columns"]]
    if target == "postgres":
        assert storage == ["pg_int4", "pg_int8", "pg_int8"] + ["pg_bool"] * 4
    else:
        assert storage[0] == "my_int"
        assert storage[1:] == ["my_signed_int"] * 2 + ["my_signed_bool"] * 4
    bound = item["policy"] == "bind_safe_literals"
    assert bool(public["parameter_uses"]) is bound
    assert bool(public["fixed_values"]) is bound


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_stage_schedule_is_the_actual_block_schedule(built, target):
    _, checked, outcome = built(target)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    blocks = sorted(plan.blocks, key=lambda block: block.position)
    assert [body.block for body in query.bodies] == blocks
    assert [body.block.kind.value for body in query.bodies] == [
        "let",
        "let",
        "where",
        "projection",
    ]
    assert [body.final for body in query.bodies] == [False, False, False, True]
    # Every body but the selected one is a generated CTE, named by its position.
    names = [b.symbol.name for b in query.bodies[:-1] if b.symbol is not None]
    assert names == ["p0", "p1", "p2"]
    assert query.bodies[-1].symbol is None
    assert type(query.bodies[0].scan) is RowScan
    assert all(type(b.scan) is RowStageUse for b in query.bodies[1:])
    assert query.bodies[0].scan.symbol.name == "s0"
    assert [b.scan.symbol.name for b in query.bodies[1:]] == ["t1", "t2", "t3"]
    # A later stage reads the established stage column, never the source again.
    for body in query.bodies[1:]:
        assert body.scan.body is query.bodies[body.index - 1]
        for column in body.columns:
            if type(column) is RowCarryColumn:
                assert column.read.name.startswith("c")


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_dependent_let_reads_the_established_stage_column(built, target):
    _, _, outcome = built(target)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    first = [c for c in query.bodies[0].columns if type(c) is RowValueColumn]
    second = [c for c in query.bodies[1].columns if type(c) is RowValueColumn]
    assert len(first) == len(second) == 1
    bumped, doubled = first[0].value, second[0].value
    assert type(bumped) is rows.SQLOperation and bumped.kind == "arithmetic"
    assert type(doubled) is rows.SQLOperation and doubled.kind == "arithmetic"
    # `doubled` reads one stage column; it does not re-splice `id + 1`.
    left = doubled.operands[0]
    assert type(left) is rows.SQLStageReference
    assert left.column.name == "c5"
    assert rows.value_nodes(doubled) == (doubled, left, doubled.operands[1])
    quote = '"' if target == "postgres" else "`"
    body = artifact.rendered.sql.decode("utf-8")
    assert body.count(f"{quote}order.id{quote} + ") == 1
    # Both intervals are checked against the actually selected physical type.
    assert bumped.realization.domain == {
        "kind": "int_range",
        "min": "-2147483647",
        "max": "2147483648",
    }
    assert doubled.realization.domain == {
        "kind": "int_range",
        "min": "-4294967294",
        "max": "4294967296",
    }


# --------------------------------------------------------------------------
# Three-valued Bool and TRUE-only filtering
# --------------------------------------------------------------------------


def test_nine_pair_truth_tables_are_explicit_and_complete():
    assert set(AND) == set(OR)
    assert len(AND) == 9
    assert sorted(AND.values()) == sorted(["T", "F", "N", "F", "F", "F", "N", "F", "N"])
    assert sorted(OR.values()) == sorted(["T", "T", "T", "T", "F", "N", "T", "N", "N"])
    # The published manifest oracle must be exactly these tables.
    import _pietto_target_conformance_cases as cases

    short = {"true": "T", "false": "F", "null": "N"}
    assert {
        (short[left], short[right]): short[value]
        for (left, right), value in cases.AND_TABLE.items()
    } == AND
    assert {
        (short[left], short[right]): short[value]
        for (left, right), value in cases.OR_TABLE.items()
    } == OR


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_scalar_boolean_keeps_three_values_without_a_truth_wrapper(tmp_path, target):
    item = probe.fixture(target, "T_row_direct", "truth_table")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    for forbidden in (
        " IS TRUE",
        " IS FALSE",
        "CASE ",
        "COALESCE(",
        " IS NOT DISTINCT",
    ):
        assert forbidden not in sql
    assert sql.count(" AND ") == 5 and sql.count(" OR ") == 5
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["logical_type"]["name"] for c in public["columns"]] == ["Bool"] * 10
    assert [c["label"] for c in public["columns"]] == list(probe.TRUTH_LABELS)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_only_a_predicate_root_consumes_true(built, target):
    _, checked, outcome = built(target)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    predicates = [b.predicate for b in query.bodies if b.predicate is not None]
    assert len(predicates) == 1
    predicate = predicates[0]
    assert (
        tuple(
            (effect.truth.value, effect.retain_row)
            for effect in predicate.original.retention_effects
        )
        == RETENTION
    )
    realization = rows.realization_of(predicate.value, target)
    assert realization.tag == "Bool" and realization.domain == {"kind": "bool01"}
    # An internal Boolean operand keeps its own three-valued result.
    both = next(
        column
        for column in query.bodies[-1].columns
        if type(column) is RowValueColumn and column.label == "both"
    )
    assert type(both.value) is rows.SQLOperation and both.value.kind == "logical"
    assert both.column.realization.nullable == "unknown"
    assert AND[("T", "N")] == "N"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_filter_preserves_bag_multiplicity_of_surviving_rows(built, target):
    _, _, outcome = built(target)
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    assert "DISTINCT" not in sql and "GROUP BY" not in sql
    assert sql.count(" WHERE ") == 1
    import _pietto_target_conformance_cases as cases

    surviving = cases.row_result_rows(target)
    assert len(surviving) == 3
    assert surviving[0] == surviving[1]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "read",
    (
        "cte",
        "inline",
        "order",
        "later",
        "read_only",
        "naming",
        "sql_bytes",
        "artifact_bytes",
    ),
)
def test_a_where_over_rows_without_fields_emits_only_inline_on_postgresql(
    tmp_path, target, read
):
    """A WHERE over a source whose shape has no field carries no column. A
    CTE header cannot be empty and MySQL has no SELECT without a column, so
    only PostgreSQL's inline read of a capturing let writes that stage. The
    stage is refused at its WHERE, several in statement order (the later
    let `a` has the first CTE), only where the statement would otherwise
    verify: an overflow in the select, a missing contract premise and a
    resource limit each keep main's own blocker."""
    cte = "query result:\n    from rows\n    where 1 == 1\n    select:\n        n = count()\n"
    body = {
        "cte": cte,
        "inline": "query result:\n    let e:\n        capture items\n"
        "        from rows\n        where items.id > 0\n        select:\n"
        "            k = 1\n    from items\n    where exists e\n"
        "    select:\n        id\n",
        "order": "query result:\n    let b:\n        from rows2\n"
        "        where 2 == 2\n        select:\n            k = 1\n"
        "    let a:\n        from rows\n        where 1 == 1\n        select:\n"
        "            k = 2\n    from a\n    let r = b\n    cross join r\n"
        "    select:\n        n = count()\n",
        "later": "query result:\n    from rows\n    where 1 == 1\n"
        "    select:\n        k = 9223372036854775807 + 1\n",
    }.get(read, cte)
    refusal = None if read in ("cte", "inline", "order", "later") else read
    source, contract = probe.fieldless_world(target, body, refusal)
    checked, outcome = probe.build_case(tmp_path, source, contract)
    assert checked.verified
    if target == "postgres" and read == "inline":
        assert outcome.status == "VERIFIED" and outcome.artifact is not None
        assert "(SELECT  FROM " in outcome.artifact.rendered.sql.decode("utf-8")
        return
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    lines = source.splitlines()
    zero = ("PIE-B1003", "zero_column_stage_not_admitted_on_target", "select_block")
    assert [
        (
            b["code"],
            b["subject"]["detail"],
            b["subject"]["reference"]["kind"],
            b["location"] and lines[b["location"]["line"] - 1].strip(),
        )
        for b in public["blockers"]
    ] == {
        "order": [(*zero, "where 1 == 1"), (*zero, "where 2 == 2")],
    }.get(read) or [
        {
            "cte": (*zero, "where 1 == 1"),
            "inline": (*zero, "where items.id > 0"),
            "later": (
                "PIE-B1002",
                "arithmetic_outside_physical_range",
                "projection",
                "k = 9223372036854775807 + 1",
            ),
            "read_only": (
                "PIE-B1001",
                "read_only_object_declaration_required",
                "definition",
                None,
            ),
            "naming": (
                "PIE-B1004",
                "identifier_case_declaration_missing",
                "selected_plan",
                None,
            ),
            "sql_bytes": ("PIE-B1007", "sql_byte_limit", "selected_plan", None),
            "artifact_bytes": (
                "PIE-B1007",
                "public_artifact_byte_limit",
                "selected_plan",
                None,
            ),
        }[read]
    ]


# --------------------------------------------------------------------------
# Finite range checking
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target,variant,code,detail",
    (
        # Q2: PostgreSQL's checked bigint operators bound these (see below).
        ("mysql", "int_overflow", "PIE-B1002", "arithmetic_outside_physical_range"),
        (
            "mysql",
            "unary_overflow",
            "PIE-B1002",
            "unary_result_outside_physical_range",
        ),
        # Branch B: a MySQL Float `==` whose operands both read rows.
        ("mysql", "float_comparison", "PIE-B1003", "comparison_type_pair_not_admitted"),
        # E4: PostgreSQL emits Float field arithmetic (test_sql_project_scalar_
        # expressions); MySQL keeps it refused.
        ("mysql", "float_arithmetic", "PIE-B1003", "float_literal_operands_required"),
        *(
            (target, variant, code, detail)
            for target in ("postgres", "mysql")
            for variant, code, detail in (
                ("bool_comparison", "PIE-B1003", "comparison_type_pair_not_admitted"),
            )
        ),
        ("mysql", "modulo", "PIE-B1003", "binary_operator_not_admitted"),
    ),
)
def test_row_boundaries_keep_no_usable_partial_sql(
    tmp_path, target, variant, code, detail
):
    item = probe.fixture(target, "V_row_blocked", variant)
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert "sql" not in public and public["artifact"] is None
    assert code in [b["code"] for b in public["blockers"]]
    assert detail in [b["subject"]["detail"] for b in public["blockers"]]


def _float_rows(tmp_path, target, body):
    item = probe.parameterized_fixture(target, body, protocol=False)
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified
    return outcome


FLOAT_COMPARISONS = (
    "query result:\n    from rows\n    where ratio == -0.0\n    select:\n"
    "        r = ratio\n        a = ratio == 0.0\n        b = ratio != 0.0\n"
    "        c = ratio < 1.5\n        d = ratio <= 1.5\n        e = ratio > -0.0\n"
    "        f = ratio >= 0.0\n        g = 0.5 <= ratio <= 10.0\n"
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_float_comparisons_use_one_float_equality(tmp_path, target):
    """F2: every comparison of a finite Float against a literal emits the plain
    SQL operator over the typed binary64 carrier; `-0.0` keeps its own spelling."""
    outcome = _float_rows(tmp_path, target, FLOAT_COMPARISONS)
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    probe.decode_public(serialize_project_sql_emission(outcome))
    if target == "postgres":
        q, zero, neg, one, half, ten = (
            '"',
            "CAST('0.0' AS pg_catalog.float8)",
            "(-CAST('0.0' AS pg_catalog.float8))",
            "CAST('1.5' AS pg_catalog.float8)",
            "CAST('0.5' AS pg_catalog.float8)",
            "CAST('10.0' AS pg_catalog.float8)",
        )
    else:
        q, zero, neg, one, half, ten = (
            "`",
            "CAST(0.0e0 AS DOUBLE)",
            "(-CAST(0.0e0 AS DOUBLE))",
            "CAST(1.5e0 AS DOUBLE)",
            "CAST(0.5e0 AS DOUBLE)",
            "CAST(10.0e0 AS DOUBLE)",
        )
    sql = artifact.rendered.sql.decode("utf-8")
    c = f"{q}t1{q}.{q}c4{q}"
    assert f"WHERE ({q}s0{q}.{q}ratio value{q} = {neg})" in sql
    assert sql.endswith(
        f" SELECT {c} AS {q}r{q}, ({c} = {zero}) AS {q}a{q},"
        f" ({c} <> {zero}) AS {q}b{q}, ({c} < {one}) AS {q}c{q},"
        f" ({c} <= {one}) AS {q}d{q}, ({c} > {neg}) AS {q}e{q},"
        f" ({c} >= {zero}) AS {q}f{q}, ({c} BETWEEN {half} AND {ten}) AS {q}g{q}"
        f" FROM {q}p0{q} AS {q}t1{q}"
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "expression,postgres,mysql",
    (
        # Branch B: MySQL may hash an equality whose operands both read rows.
        ("ratio == ratio", None, "comparison_type_pair_not_admitted"),
        # MySQL's parser turns NOT (x <> y) into x = y.
        ("ratio != ratio", None, "comparison_type_pair_not_admitted"),
        # An ordering inequality is never an equality key.
        ("ratio < ratio", None, None),
        # O2: Float against Int stays refused on both targets.
        (
            "ratio > 1",
            "comparison_type_pair_not_admitted",
            "comparison_type_pair_not_admitted",
        ),
    ),
)
def test_float_comparisons_with_rows_on_both_sides(
    tmp_path, target, expression, postgres, mysql
):
    outcome = _float_rows(
        tmp_path,
        target,
        f"query result:\n    from rows\n    select:\n        x = {expression}\n",
    )
    detail = postgres if target == "postgres" else mysql
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    if detail is None:
        assert outcome.status == "VERIFIED", public["blockers"]
        q = '"' if target == "postgres" else "`"
        column = f"{q}s0{q}.{q}ratio value{q}"
        authored = expression.split()[1]
        operator = {"==": "=", "!=": "<>"}.get(authored, authored)
        assert f"({column} {operator} {column}) AS {q}x{q}" in public["sql"]
        return
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["column"])
        for b in public["blockers"]
    ] == [("PIE-B1003", detail, 9)]


def _mysql_spelling(sql):
    """A PostgreSQL statement in MySQL's quoting, schema and null-safe equality."""
    return (
        sql.replace('"', "`")
        .replace("`public`", "`phase66`")
        .replace(" IS NOT DISTINCT FROM ", " <=> ")
    )


@pytest.mark.parametrize(
    "body",
    (
        *(body for _, _, body in cells.QUALIFIED),
        *cells.SAME_CLASS.values(),
    ),
    ids=(
        *(" ".join((*cell, key or "")).strip() for cell, key, _ in cells.QUALIFIED),
        *cells.SAME_CLASS,
    ),
)
def test_mysql_float_row_cells_emit_the_postgresql_statement(tmp_path, body):
    """Phase77 S06: each form s06-float-b10 judged READY (same row, INNER and
    LEFT JOIN, alone and beside a qualified Text key) and each program of its
    class emits on MySQL the PostgreSQL statement in MySQL spelling, and the
    live verifier and the pure boundary accept both."""
    emitted = {}
    for target in ("postgres", "mysql"):
        outcome = cells.build(tmp_path / target, target, body)
        assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
        artifact = outcome.artifact
        assert artifact is not None
        assert verify_project_sql_emission(artifact, artifact.request).verified
        observed = portable.export_emission_observation(artifact, artifact.request)
        assert observed.canonical_bytes is not None
        assert (
            pure.parse_emission_observation(observed.canonical_bytes).status
            is pure.Status.OK
        )
        emitted[target] = artifact.rendered.sql.decode("utf-8")
    assert emitted["mysql"] == _mysql_spelling(emitted["postgres"])


@pytest.mark.parametrize("name", sorted(cells.REFUSED))
def test_other_mysql_float_row_comparisons_keep_their_refusal(tmp_path, name):
    """Every other program keeps main's PIE-B1003 detail on MySQL at each such
    comparison, and still emits on PostgreSQL."""
    body, expected = cells.REFUSED[name]
    assert cells.build(tmp_path / "postgres", "postgres", body).status == "VERIFIED"
    outcome = cells.build(tmp_path / "mysql", "mysql", body)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(b["code"], b["subject"]["detail"]) for b in public["blockers"]] == expected


def test_a_mysql_float_row_cell_refused_for_another_reason_keeps_mains_list(
    tmp_path,
):
    """Rule two (D77.37): a cell's statement that an output label past 256
    characters refuses reports main's whole blocker list, the comparison's
    PIE-B1003 first, as main `a015afcf` does."""
    body = cells.query(
        "from f6s", "select:", "    id", "    " + "r" * 257 + " = f1 == f2"
    )
    outcome = cells.build(tmp_path, "mysql", body)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [(b["code"], b["subject"]["detail"]) for b in public["blockers"]] == [
        ("PIE-B1003", "comparison_type_pair_not_admitted"),
        ("PIE-B1002", "output_label_unrepresentable"),
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_null_safe_join_condition_has_no_form_on_either_target(tmp_path, target):
    """The qualification's null-safe JOIN matched, but `same_value` in an ON
    has no PostgreSQL form, so MySQL opens none either."""
    body = cells.query(
        "from f6o",
        "inner join f6i on same_value(f6i.v, f6o.v)",
        "select:",
        "    v = f6o.v",
    )
    outcome = cells.build(tmp_path, target, body)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "BLOCKED"
    assert ("PIE-B1003", "match_condition_not_in_row_domain") in [
        (b["code"], b["subject"]["detail"]) for b in public["blockers"]
    ]


@pytest.mark.parametrize(
    "name",
    (
        *("same_field", "float_item", "key_first", "same_table", "upstream_query"),
        *("same_value_same_field", "same_value_float_item"),
        *("join_same_side", "key_same_side", "mixed_key_widths"),
        # Carriers outside the cell: an operand, a key, a source's fields.
        *("non_null_operand", "nullable_key", "int_key", "key_width_255"),
        *("unselected_key_same_row", "unselected_wide_text"),
        *("unselected_nullable_float", "reordered_fields", "same_row_table_joined"),
        # Forms outside the cell table the pure boundary restates.
        *("not_equal", "inner_not_equal"),
        # A Float read inside `any(...)` reads a row too.
        *("semi_exists", "anti_not_exists", "semi_exists_ne", "semi_exists_not_ne"),
    ),
)
def test_a_mysql_float_row_comparison_forged_past_its_cell_is_refused(
    tmp_path, monkeypatch, name
):
    """Emission forced to admit a program outside every cell. The live
    verifier refuses it from its plan, by the emission blockers it derives
    again and, with those bypassed, by its own comparison law; both call
    mysql_float_cell, as emission does. The pure boundary refuses it from the
    document's own structure, by the cell table it restates."""
    from pietto._project import project_sql_emission_verification as verification

    with monkeypatch.context() as patch:
        patch.setattr(
            rows,
            "mysql_float_cell",
            lambda request, expression: ("same_row", "select", "=="),
        )
        outcome = cells.build(tmp_path, "mysql", cells.REFUSED[name][0])
        artifact = outcome.artifact
        assert outcome.status == "VERIFIED" and artifact is not None
        observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )
    with monkeypatch.context() as patch:
        patch.setattr(verification, "emission_blockers", lambda request: ())
        assert verify_project_sql_emission(artifact, artifact.request).issues == (
            "plan_ast_correspondence",
        )
    refused = pure.parse_emission_observation(observed.canonical_bytes)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "MySQL Float row comparison cell",
    )
    assert pure._MYSQL_FLOAT_ROW_CELLS == rows.MYSQL_FLOAT_ROW_CELLS
    assert pure._MYSQL_FLOAT_CELL_TABLES == rows.MYSQL_FLOAT_CELL_TABLES


def _rewritten(kind, field, value):
    """Rewrite the one ``kind`` record whose ``field`` is INNER or `==`."""

    def tamper(records):
        (record,) = (
            r
            for r in records
            if r["ref"][0] == kind and r["fields"].get(field) in ("inner", "==")
        )
        record["fields"][field] = value

    return tamper


def _crossed_on_fields(records):
    """Each Float column the ON compares claims the other input's field."""
    fields = {tuple(r["ref"]): r["fields"] for r in records}
    (join,) = (r["fields"] for r in records if r["ref"][0] == "join_body")
    left, right = (
        fields[tuple(fields[tuple(operand)]["column"])]
        for operand in fields[tuple(join["predicate"])]["operands"]
    )
    left["field"], right["field"] = right["field"], left["field"]


@pytest.mark.parametrize(
    "join,tamper",
    (
        # An INNER `not (!=)` read as a LEFT JOIN, which only `==` qualifies.
        (
            "inner join f6i on not (f6i.v != f6o.v)",
            _rewritten("join_body", "join_kind", "left"),
        ),
        # A LEFT `==` read as `!=`.
        (
            "left join f6i on f6i.v == f6o.v",
            _rewritten("sql_operation", "operator", "!="),
        ),
        # An ON that reads no column of each input's own scan.
        ("inner join f6i on f6i.v == f6o.v", _crossed_on_fields),
    ),
)
def test_a_tampered_mysql_float_cell_document_is_refused(tmp_path, join, tamper):
    body = cells.query("from f6o", join, "select:", "    oid = f6o.id")
    artifact = cells.build(tmp_path, "mysql", body).artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    document = json.loads(observed.canonical_bytes)
    tamper(document["records"])
    refused = pure.parse_emission_observation(json.dumps(document))
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "MySQL Float row comparison cell",
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_typed_division_is_postgres_only_at_the_project_row_boundary(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "modulo")
    source = item["source"].replace("rest = id % 2", "half = id / 2")
    assert source != item["source"]
    checked, outcome = probe.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified
    if target == "postgres":
        assert outcome.status == "VERIFIED"
        assert outcome.artifact is not None
        assert " / " in outcome.artifact.rendered.sql.decode("utf-8")
        return
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert ("PIE-B1003", "binary_operator_not_admitted") in [
        (blocker["code"], blocker["subject"]["detail"])
        for blocker in public["blockers"]
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_typed_remainder_is_postgres_only_at_the_project_row_boundary(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "modulo")
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified
    if target == "postgres":
        assert outcome.status == "VERIFIED" and outcome.artifact is not None
        assert " % " in outcome.artifact.rendered.sql.decode("utf-8")
        return
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert ("PIE-B1003", "binary_operator_not_admitted") in [
        (blocker["code"], blocker["subject"]["detail"])
        for blocker in public["blockers"]
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_between_preserves_ordered_three_operand_realization(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "between")
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    query = artifact.ast
    assert isinstance(query, SQLRowQuery)
    sql = artifact.rendered.sql.decode("utf-8")
    assert " BETWEEN " in sql and " AND " in sql
    between = next(
        value
        for body in query.bodies
        for column in body.columns
        if type(column) is RowValueColumn
        for value in (column.value,)
        if type(value) is rows.SQLOperation and value.kind == "between"
    )
    assert len(between.operands) == 3
    assert between.realization.tag == "Bool"


CHECKED = {"overflow": "target_checked_signed64_narrowing"}


@pytest.mark.parametrize(
    "target,expression",
    (
        ("postgres", "(id * 0 + 9223372036854775807) + 1"),
        ("mysql", "(id + 1) - 1"),
    ),
)
def test_an_overflowing_intermediate_is_rejected_beneath_a_false_filter(
    tmp_path, target, expression
):
    """A filter that can never retain a row still cannot license an overflow:
    on MySQL one that may happen, on PostgreSQL one that always happens, which
    planning would otherwise raise however the filter runs."""
    item = probe.fixture(target, "V_row_blocked", "int_overflow")
    source = item["source"].replace(
        "    select:\n", "    where id > 0 and id < 0\n    select:\n"
    )
    source = source.replace("        big = id + 1\n", f"        big = {expression}\n")
    _, outcome = probe.build_case(tmp_path, source, item["contract"], item["policy"])
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [(b["code"], b["subject"]["detail"]) for b in public["blockers"]] == [
        ("PIE-B1002", "arithmetic_outside_physical_range")
    ]


@pytest.mark.parametrize(
    "variant,label,sql,low,high,operators",
    (
        (
            "int_overflow",
            "big",
            '("s0"."order.id" + CAST(1 AS pg_catalog.int8))',
            -(2**63) + 1,
            2**63 - 1,
            [{"operator": "+"}],
        ),
        (
            "unary_overflow",
            "negated",
            '(-"s0"."order.id")',
            -(2**63) + 1,
            2**63 - 1,
            [{"operator": "-"}],
        ),
        (
            "abs",
            "magnitude",
            'abs("s0"."order.id")',
            0,
            2**63 - 1,
            [{"callable": "abs", "namespace": "callable"}],
        ),
        (
            "nested",
            "big",
            '((("s0"."order.id" + CAST(1 AS pg_catalog.int8))'
            ' - CAST(1 AS pg_catalog.int8)) * "s0"."order.id")',
            -(2**63),
            2**63 - 1,
            [{"operator": "*"}, {"operator": "+"}],
        ),
        (
            "folded",
            "big",
            "((CASE WHEN CAST(TRUE AS pg_catalog.bool)"
            " THEN CAST(9223372036854775807 AS pg_catalog.int8)"
            " ELSE CAST(0 AS pg_catalog.int8) END) + CAST(1 AS pg_catalog.int8))",
            1,
            2**63 - 1,
            [{"operator": "+"}],
        ),
    ),
)
def test_postgresql_checks_a_bigint_result_that_may_leave_signed_64(
    tmp_path, variant, label, sql, low, high, operators
):
    """Q2: a bigint operation whose exact range meets but leaves signed 64 bits
    is emitted unchanged; PostgreSQL's checked operator refuses a value outside
    them (SQLSTATE 22003), so the result keeps the part of its range inside
    them and its requirement says so. `(id + 1) - 1` is checked once, by its
    `+`: the `-` brings it back inside. A conditional's range spans both
    branches, so one with a constant condition is admitted too, though
    PostgreSQL folds it while planning and may raise the error then."""
    item = probe.fixture("postgres", "V_row_blocked", "int_overflow")
    source = item["source"]
    if variant == "unary_overflow":
        source = probe.fixture("postgres", "V_row_blocked", variant)["source"]
    elif variant == "abs":
        source = source.replace("big = id + 1", "magnitude = abs(id)")
    elif variant == "nested":
        source = source.replace("big = id + 1", "big = ((id + 1) - 1) * id")
    elif variant == "folded":
        source = source.replace(
            "big = id + 1", "big = (9223372036854775807 if True else 0) + 1"
        )
    _, outcome = probe.build_case(tmp_path, source, item["contract"], item["policy"])
    assert outcome.status == "VERIFIED", outcome.blockers
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["sql"] == (
        f'SELECT {sql} AS "{label}" FROM "public"."phase66 source é" AS "s0"'
    )
    assert [c["representation"] for c in public["columns"]] == [
        {
            "storage": {"kind": "pg_int8"},
            # A binary result keeps its semantic UNKNOWN nullability.
            "nullable": "unknown" if label == "big" else False,
            "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
        }
    ]
    assert [
        (r["rule"], r["evidence"])
        for r in public["requirements"]
        if r["denominator"] == "generated" and CHECKED in r["evidence"]
    ] == [("R05", [spelling, CHECKED]) for spelling in operators]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_bounded_field_and_constant_arithmetic_is_admitted(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    select:\n"
        "        constant = 2 * 3\n"
        "        bounded = id - 1\n"
        "        negated = -(id + 0)\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["logical_type"]["name"] for c in public["columns"]] == ["Int"] * 3
    domains = [c["representation"]["domain"] for c in public["columns"]]
    assert domains[0] == {"kind": "int_range", "min": "6", "max": "6"}
    assert domains[1]["min"] == "-2147483649"
    assert domains[2] == {
        "kind": "int_range",
        "min": "-2147483647",
        "max": "2147483648",
    }
    # The authored tree survives even where the interval is a single value.
    assert "2" in public["sql"] and "3" in public["sql"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_int_arithmetic_with_a_typed_null_casts_it_to_the_int_carrier(tmp_path, target):
    """Int arithmetic with a `None` operand is NULL in every row (D-12): the
    NULL is CAST to the target's Int carrier, as a bare NULL takes the type
    the target chooses (MySQL types `n + NULL` as DOUBLE), and the result in
    that carrier claims the single value 0, which no row has, so a sign over
    it is held to no range of the other operand."""
    source = row_source(
        target,
        "    from rows\n    select:\n"
        "        plus = id + None\n"
        "        times = None * 2\n"
        "        negated = -(id + None)\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "VERIFIED", public
    assert [c["logical_type"]["name"] for c in public["columns"]] == ["Int"] * 3
    carrier = "pg_int8" if target == "postgres" else "my_signed_int"
    assert [c["representation"]["storage"] for c in public["columns"]] == [
        {"kind": carrier}
    ] * 3
    assert all(c["representation"]["nullable"] for c in public["columns"])
    assert [c["representation"]["domain"] for c in public["columns"]] == [
        {"kind": "int_range", "min": "0", "max": "0"}
    ] * 3
    if target == "postgres":
        assert (
            '("s0"."order.id" + CAST(NULL AS pg_catalog.int8)) AS "plus"'
            in public["sql"]
        )
        assert (
            "(CAST(NULL AS pg_catalog.int8) * CAST(2 AS pg_catalog.int8))"
            in public["sql"]
        )
    else:
        assert " + CAST(NULL AS SIGNED)) AS `plus`" in public["sql"]
        assert "(CAST(NULL AS SIGNED) * CAST(2 AS SIGNED)) AS `times`" in public["sql"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "value,detail",
    (
        ("None", "expression_evidence_unavailable"),
        ("-None", "expression_evidence_unavailable"),
        ("None - 2.5", "float_literal_operands_required"),
        ("(None + money) + 1.5", "decimal_direct_source_operands_required"),
        ("sign(None + ratio)", "float_literal_operands_required"),
        ("id + (-None)", "expression_evidence_unavailable"),
        ("(None + None) + id", "expression_evidence_unavailable"),
        ("same_value(coalesce(None, None), id)", "expression_evidence_unavailable"),
        ("coalesce(None, None) == id", "expression_evidence_unavailable"),
    ),
)
def test_an_always_null_value_outside_the_row_boundary_names_its_rule(
    tmp_path, target, value, detail
):
    """An untyped NULL output, Float arithmetic with a NULL, a NULL number of
    another type beside a Float and an untyped NULL beside a typed value pass
    check (D-12), those with an untyped part with its emission warning, and
    stay blocked with the rule they miss, never with a bare PIE-S2333."""
    source = row_source(
        target, f"    from rows\n    select:\n        id\n        value = {value}\n"
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "BLOCKED" and public["artifact"] is None
    untyped = detail == "expression_evidence_unavailable"
    assert [d["code"] for d in public["diagnostics"]] == ["PIE-S2385"] * untyped
    assert ("PIE-B1003", detail) in [
        (blocker["code"], blocker["subject"]["detail"])
        for blocker in public["blockers"]
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_abs_keeps_the_unary_range_proof_and_its_argument_carrier(tmp_path, target):
    """`abs` of an Int has the range unary `-` proves, in the same integer
    type; of a Float or a Decimal it keeps the argument's carrier."""
    source = row_source(
        target,
        "    from rows\n    select:\n"
        "        widened = abs(id + 0)\n"
        "        ratio_size = abs(ratio)\n"
        "        money_size = abs(money)\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    pg = target == "postgres"
    assert [
        (c["logical_type"]["name"], c["representation"]) for c in public["columns"]
    ] == [
        (
            "Int",
            {
                "storage": {"kind": "pg_int8" if pg else "my_signed_int"},
                "nullable": "unknown",
                "domain": {"kind": "int_range", "min": "0", "max": "2147483648"},
            },
        ),
        (
            "Float",
            {
                "storage": {"kind": "pg_float8" if pg else "my_double"},
                "nullable": False,
                "domain": {"kind": "finite_float", "format": "binary64"},
            },
        ),
        (
            "Decimal",
            {
                "storage": {
                    "kind": "pg_numeric" if pg else "my_decimal",
                    "precision": 9,
                    "scale": 2,
                },
                "nullable": False,
                "domain": {"kind": "decimal", "precision": 9, "scale": 2},
            },
        ),
    ]
    assert public["sql"] == (
        'SELECT abs(("s0"."order.id" + CAST(0 AS pg_catalog.int8))) AS "widened", '
        'abs("s0"."ratio value") AS "ratio_size", '
        'abs("s0"."amount value") AS "money_size" '
        'FROM "public"."phase66 safe int source" AS "s0"'
        if pg
        else "SELECT ABS((`s0`.`order.id` + CAST(0 AS SIGNED))) AS `widened`, "
        "ABS(`s0`.`ratio value`) AS `ratio_size`, "
        "ABS(`s0`.`amount value`) AS `money_size` "
        "FROM `phase66`.`phase66 safe int source` AS `s0`"
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_abs_and_unary_minus_of_an_int_are_blocked_only_past_signed_64(
    tmp_path, target
):
    """An int4 `-` or `abs` whose magnitude leaves int4 is computed in bigint
    on PostgreSQL (its operand CAST to pg_catalog.int8) and as signed 64-bit
    on MySQL; over a signed 64-bit source MySQL refuses it."""
    source = row_source(
        target,
        "    from rows\n    select:\n        negated = -id\n        magnitude = abs(id)\n",
    )
    _, outcome = probe.build_case(
        tmp_path / "int4", source, stage_contract(target), "preserve_literals"
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    assert [c["representation"]["domain"] for c in public["columns"]] == [
        {"kind": "int_range", "min": "-2147483647", "max": "2147483648"},
        {"kind": "int_range", "min": "0", "max": "2147483648"},
    ]
    assert [c["representation"]["storage"] for c in public["columns"]] == [
        {"kind": "pg_int8" if target == "postgres" else "my_signed_int"}
    ] * 2
    assert public["sql"] == (
        'SELECT (-CAST("s0"."order.id" AS pg_catalog.int8)) AS "negated", '
        'abs(CAST("s0"."order.id" AS pg_catalog.int8)) AS "magnitude" '
        'FROM "public"."phase66 safe int source" AS "s0"'
        if target == "postgres"
        else "SELECT (-`s0`.`order.id`) AS `negated`, "
        "ABS(`s0`.`order.id`) AS `magnitude` "
        "FROM `phase66`.`phase66 safe int source` AS `s0`"
    )
    item = probe.fixture(target, "V_row_blocked", "unary_overflow")
    wide = item["source"].replace("negated = -id", "magnitude = abs(id)")
    assert wide != item["source"]
    _, outcome = probe.build_case(
        tmp_path / "int8", wide, item["contract"], item["policy"]
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    if target == "postgres":
        # Q2: PostgreSQL's checked bigint abs bounds it (see the checked
        # bigint test); MySQL keeps the static signed 64-bit proof.
        assert outcome.status == "VERIFIED"
        return
    assert outcome.status == "BLOCKED" and public["artifact"] is None
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"])
        for b in public["blockers"]
    ] == [("PIE-B1002", "abs_result_outside_physical_range", 11)]
    assert public["blockers"][0]["location"]["column"] == 9


# --------------------------------------------------------------------------
# Repeated reads, omitted-but-required values and comparison premises
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_repeated_let_reads_are_column_reads_not_new_occurrences(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    let bumped = id + 1\n"
        "    select:\n        a = bumped\n        b = bumped\n        c = bumped\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, bind_contract(target), "bind_safe_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    # One authored literal, one slot, one native use: three reads are not three.
    assert len(public["fixed_values"]) == 1
    assert len(public["parameter_uses"]) == 1
    assert [c["label"] for c in public["columns"]] == ["a", "b", "c"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_required_but_unprojected_let_is_retained(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    let hidden = id + 1\n"
        "    where hidden > 0\n    select:\n        kept = id\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    assert [b.block.kind.value for b in query.bodies] == ["let", "where", "projection"]
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in public["columns"]] == ["kept"]
    # The unprojected value is still computed and carried to its consumer.
    assert query.bodies[0].columns[-1].label == "c5"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_admitted_text_and_decimal_comparisons_keep_their_premises(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    select:\n"
        "        same_text = text == text\n"
        "        same_money = money == money\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["logical_type"]["name"] for c in public["columns"]] == ["Bool", "Bool"]
    encodings = {
        p["key"] for p in public["request"]["contract"]["environment"] if "key" in p
    }
    assert "client_encoding" in encodings


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_violated_text_premise_blocks_the_comparison(tmp_path, target):
    contract = json.loads(stage_contract(target))
    description = contract["sources"][0]
    # Two Text fields whose declared collations differ cannot be compared.
    description["fields"][2]["representation"]["domain"]["collation"] = (
        "und-x-icu" if target == "postgres" else "utf8mb4_general_ci"
    )
    source = row_source(
        target, "    from rows\n    select:\n        same_text = text == text\n"
    )
    _, outcome = probe.build_case(
        tmp_path, source, probe.encoded(contract).decode(), "preserve_literals"
    )
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["status"] == "BLOCKED" and outcome.artifact is None
    assert public["blockers"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_parameters_bind_in_select_let_and_where(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    let bumped = id + 7\n"
        "    where id > 11\n    select:\n        kept = bumped\n        literal = 13\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, bind_contract(target), "bind_safe_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [v["value"] for v in public["fixed_values"]] == ["7", "11", "13"]
    assert [u["slot"] for u in public["parameter_uses"]] == [0, 1, 2]
    marker = "$" if target == "postgres" else "?"
    assert public["sql"].count(marker) == 3


# --------------------------------------------------------------------------
# ON/MATCH context, now carried by whole JOIN emission
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_match_context_is_checked_and_its_join_now_emits(tmp_path, target):
    # This input's only remaining restriction was the JOIN family, so it is no
    # longer blocked. Every expectation below is taken from the real emitter and
    # the published bytes, never from the fixture's own migration table.
    item = probe.fixture(target, "V_row_blocked", "match_join")
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    # Bounded scalar comparisons only: an assertion message here must never
    # format the private emission graph.
    assert checked.verified
    assert outcome.status == "VERIFIED", outcome.status
    assert type(outcome.artifact).__name__ == "EmissionArtifact"

    # The independent consumer decodes the actual serialized bytes.
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["status"] == "VERIFIED", public["status"]
    assert "sql" in public and "blockers" not in public
    assert [column["label"] for column in public["columns"]] == ["record_id"]

    # The published SQL really carries the JOIN and the retained MATCH condition.
    kinds = {requirement["kind"] for requirement in public["requirements"]}
    assert "match_condition" in kinds
    assert {"join", "join_input", "join_output", "join_use"} <= kinds
    quote = '"' if target == "postgres" else "`"
    assert public["sql"].startswith(f"WITH {quote}p0{quote} ")
    assert f"{quote}m0{quote}" in public["sql"]

    # The retained MATCH condition is still a real pre-match site, and the
    # separate foreign-port control below still proves it is this site's own port.
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    assert any(
        type(site).__name__ == "ProjectSQLMatchSite" for site in plan.expression_sites
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_foreign_match_port_is_rejected_by_the_applicability_check(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "match_join")
    checked, _ = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    from pietto._project import project_sql_plan_expressions as nodes

    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    sites = {
        site.ref
        for site in plan.expression_sites
        if type(site) is nodes.ProjectSQLMatchSite
    }
    references = [
        expression
        for expression in plan.expressions
        if type(expression) is nodes.ProjectSQLMatchReference
        and expression.site.ref in sites
    ]
    assert references, "the fixture must retain a real pre-match reference"
    # The retained ON condition is applicable as authored.
    assert rows.match_applicability(checked) == ()
    # A foreign port keeps the same reference spelling, symbol and logical type,
    # and is still rejected because it is not this site's own pre-match port.
    original = references[0]
    foreign = graft(original, port=plan.sources[0].ref)
    assert foreign.expression is original.expression
    assert foreign.symbol is original.symbol
    changed = graft(
        plan,
        expressions=tuple(foreign if e is original else e for e in plan.expressions),
    )
    problems = rows.match_applicability(graft(checked, plan=changed))
    assert [(code, detail) for code, detail, _, _ in problems] == [
        ("PIE-B1001", "match_reference_outside_pre_match_scope")
    ]
    assert problems[0][2] is foreign.ref


# --------------------------------------------------------------------------
# Corruption witnesses against the independent verifier and consumer
# --------------------------------------------------------------------------


def row_artifact(built, target="postgres"):
    _, _, outcome = built(target)
    artifact = outcome.artifact
    assert artifact is not None
    assert type(artifact.ast) is SQLRowQuery
    return outcome, artifact


@pytest.mark.parametrize(
    "mutation",
    (
        "operator",
        "operand_order",
        "stage_binding",
        "carry_column",
        "predicate_root",
        "generated_requirement",
        "original_requirement",
        "both_requirements",
        "parameter",
        "range",
    ),
)
def test_row_correspondence_corruptions_are_rejected(built, mutation):
    outcome, artifact = row_artifact(built)
    query = artifact.ast
    assert type(query) is SQLRowQuery
    final = query.bodies[-1]
    if mutation == "operator":
        column = next(
            c for c in final.columns if type(c) is RowValueColumn and c.label == "both"
        )
        changed_value = graft(column.value, kind="comparison")
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=(
                    *query.bodies[:-1],
                    replace(
                        final,
                        columns=tuple(
                            replace(c, value=changed_value) if c is column else c
                            for c in final.columns
                        ),
                    ),
                ),
            ),
        )
    elif mutation == "operand_order":
        column = next(
            c
            for c in final.columns
            if type(c) is RowValueColumn and c.label == "positive"
        )
        swapped = graft(column.value, operands=tuple(reversed(column.value.operands)))
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=(
                    *query.bodies[:-1],
                    replace(
                        final,
                        columns=tuple(
                            replace(c, value=swapped) if c is column else c
                            for c in final.columns
                        ),
                    ),
                ),
            ),
        )
    elif mutation == "stage_binding":
        # A superficially consistent rebinding: same name, same type, other port.
        column = next(
            c
            for c in final.columns
            if type(c) is RowValueColumn and c.label == "record_id"
        )
        reference = column.value
        assert type(reference) is rows.SQLStageReference
        other = next(
            c
            for c in query.bodies[-2].columns
            if c.export.ref is not reference.port
            and c.column.realization.tag == reference.realization.tag
        )
        moved = graft(reference, port=other.export.ref)
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=(
                    *query.bodies[:-1],
                    replace(
                        final,
                        columns=tuple(
                            replace(c, value=moved) if c is column else c
                            for c in final.columns
                        ),
                    ),
                ),
            ),
        )
    elif mutation == "carry_column":
        body = query.bodies[1]
        carried = [c for c in body.columns if type(c) is RowCarryColumn]
        swapped = (carried[1], carried[0], *carried[2:])
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=(
                    query.bodies[0],
                    replace(
                        body,
                        columns=(*swapped, *body.columns[len(carried) :]),
                    ),
                    *query.bodies[2:],
                ),
            ),
        )
    elif mutation == "predicate_root":
        body = next(b for b in query.bodies if b.predicate is not None)
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=tuple(
                    replace(b, predicate=None) if b is body else b for b in query.bodies
                ),
            ),
        )
    elif mutation == "generated_requirement":
        changed = replace(
            artifact, generated_requirements=artifact.generated_requirements[1:]
        )
    elif mutation == "original_requirement":
        changed = replace(
            artifact, original_requirements=artifact.original_requirements[1:]
        )
    elif mutation == "both_requirements":
        changed = replace(artifact, original_requirements=(), generated_requirements=())
    elif mutation == "parameter":
        changed = replace(artifact, fixed_values=(1,))
    else:
        column = next(
            c for c in final.columns if type(c) is RowValueColumn and c.label == "twice"
        )
        widened = graft(
            column.value,
            realization=replace(
                column.value.realization,
                domain={"kind": "int_range", "min": "0", "max": "1"},
            ),
        )
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=(
                    *query.bodies[:-1],
                    replace(
                        final,
                        columns=tuple(
                            replace(c, value=widened) if c is column else c
                            for c in final.columns
                        ),
                    ),
                ),
            ),
        )
    assert not verify_project_sql_emission(changed, artifact.request).verified
    public = probe.decode_public(
        serialize_project_sql_emission(replace(outcome, artifact=changed))
    )
    assert public["status"] == "BLOCKED"
    assert public["blockers"][0]["code"] == "PIE-B1008"


@pytest.mark.parametrize(
    "mutation", ("operator_token", "reference_column", "label", "where_clause")
)
def test_row_public_byte_corruptions_are_rejected(built, mutation):
    _, _, outcome = built()
    data = serialize_project_sql_emission(outcome)
    document = json.loads(data)
    sql = document["sql"]
    if mutation == "operator_token":
        document["sql"] = sql.replace(" AND ", " OR ", 1)
    elif mutation == "reference_column":
        document["sql"] = sql.replace('"c0" AS "record_id"', '"c1" AS "record_id"', 1)
    elif mutation == "label":
        document["sql"] = sql.replace('AS "record_id"', 'AS "renamed"', 1)
    else:
        document["sql"] = sql.replace(" WHERE ", " where ", 1)
    assert document["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_adding_a_valid_stage_does_not_weaken_unrelated_source_checks(tmp_path, target):
    """A new LET/filter must not make a malformed unrelated field acceptable."""
    contract = json.loads(stage_contract(target))
    contract["sources"][0]["fields"][4]["representation"]["domain"] = {
        "kind": "int_range",
        "min": "0",
        "max": "1",
    }
    source = row_source(
        target,
        "    from rows\n    let bumped = id + 1\n"
        "    where id > 0\n    select:\n        kept = bumped\n        ratio\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, probe.encoded(contract).decode(), "preserve_literals"
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_unrelated_unused_source_description_is_not_over_rejected(tmp_path, target):
    contract = json.loads(stage_contract(target))
    extra = json.loads(json.dumps(contract["sources"][0]))
    extra["selector"]["name"] = "unused"
    extra["relation"]["name"] = "phase66 unused"
    contract["sources"].append(extra)
    header = row_source(target, "", header_only=True)
    source = (
        header
        + f'source unused: Row = {target}.table("opaque.unused")\n'
        + "table result:\n    from rows\n    let bumped = id + 1\n"
        "    where id > 0\n    select:\n        kept = bumped\n"
    )
    _, outcome = probe.build_case(
        tmp_path, source, probe.encoded(contract).decode(), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in public["columns"]] == ["kept"]
