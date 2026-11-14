"""Admitted row scalars, ordered LET stages, TRUE-only filters and ON context."""

from copy import copy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

import _pietto_sql_emission as probe
import _pietto_sql_float_cells as cells
import _pietto_sql_nullsafe_cells as nullsafe
import _pietto_sql_emission_portable as portable
import _pietto_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_aggregation as grouping
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
    resolved_row_realization,
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import (
    ProjectSQLBoundaryReason,
    ProjectSQLPlan,
)
from pietto._project.project_sql_plan_expressions import ProjectSQLExpressionRole

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


def test_a_mysql_r01_read_yields_to_a_stage_over_rows_without_fields(tmp_path):
    """A MySQL statement with an R01 `Float` `in` read of a let with
    `capture` lines and a capturing let over rows without fields reports the
    stage's refusal alone, at that let's WHERE: the R01 refusal yields to it
    as to any refusal main makes (D77.62, D77.64). Without that let the
    read keeps its own blocker."""
    let_m = ("let m:", "    capture r01o", "    from r01i")
    let_m += ("    where kw == r01o.kw", "    select:", "        v")
    let_e = ("let e:", "    capture r01o", "    from nil", "    where r01o.id > 0")
    let_e += ("    select:", "        k = 1")
    reported = []
    for lets, where in (
        (let_m, "where v in m"),
        (let_e + let_m, "where v in m and exists e"),
    ):
        body = cells.query(*lets, "from r01o", where, "select:", "    id")
        source, contract = cells.world("mysql", body)
        source = (
            "shape Nil:\n    always = check(True)\n"
            'source nil: Nil = mysql.table("nil.locator")\n' + source
        )
        document = json.loads(contract)
        base = document["sources"][0]
        document["sources"].append(
            {
                **base,
                "selector": {**base["selector"], "name": "nil"},
                "relation": {**base["relation"], "name": "phase77 nil"},
                "fields": [],
            }
        )
        _, outcome = probe.build_case(
            tmp_path / str(len(reported)), source, probe.encoded(document).decode()
        )
        lines = source.splitlines()
        public = probe.decode_public(serialize_project_sql_emission(outcome))
        reported.append(
            [
                (b["subject"]["detail"], lines[b["location"]["line"] - 1].strip())
                for b in public["blockers"]
            ]
        )
    assert reported == [
        [("membership_type_pair_not_admitted", "where v in m")],
        [("zero_column_stage_not_admitted_on_target", "where r01o.id > 0")],
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
def test_a_float_world_null_safe_join_condition_keeps_its_refusal(tmp_path, target):
    """A null-safe ON over the S06 Float world (Text keys beside `v`, one
    column selected) is outside every null-safe JOIN cell on both targets."""
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
        *("semi_exists", "semi_exists_ne", "semi_exists_not_ne"),
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


@pytest.mark.parametrize("name", cells.R02_ACCEPTED)
def test_mysql_r02_anti_forms_emit_the_postgresql_statement(tmp_path, name):
    """Phase77 R02: each `not any(...)` form of the candidate emission
    experiment (the Float `==` alone, beside a 64- or a 1000-character key)
    and each program of its class (a binder `let`, operands swapped, `i`'s
    fields renamed, O's fields reordered) emits on MySQL the PostgreSQL
    statement in MySQL spelling, and the live verifier and the pure boundary
    accept both."""
    _, body = cells.R02_ACCEPTED[name]
    emitted = {}
    for target in ("postgres", "mysql"):
        outcome = cells.r02_build(
            tmp_path / target, target, body, controls=name not in cells.R02_FORMS
        )
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
    assert emitted["mysql"].count("NOT EXISTS (SELECT 1 FROM ") == 1


@pytest.mark.parametrize("name", (*cells.R02_REFUSED, *cells.R02_ALSO_REFUSED))
def test_other_mysql_anti_programs_keep_their_refusal(tmp_path, name):
    """Every other program of R02's controls, and seven more, keeps main's one
    PIE-B1003 on MySQL, and still emits on PostgreSQL."""
    body = {**cells.R02_REFUSED, **cells.R02_ALSO_REFUSED}[name]
    postgres = cells.r02_build(tmp_path / "postgres", "postgres", body, controls=True)
    assert postgres.status == "VERIFIED"
    outcome = cells.r02_build(tmp_path / "mysql", "mysql", body, controls=True)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(b["code"], b["subject"]["detail"]) for b in public["blockers"]] == [
        ("PIE-B1003", "comparison_type_pair_not_admitted")
    ]


def test_a_mysql_anti_cell_refused_for_another_reason_keeps_mains_list(tmp_path):
    """Rule two (D77.37): an R02 form whose output label is past 256
    characters reports main's whole blocker list, the comparison's PIE-B1003
    first."""
    _, body = cells.R02_FORMS["r02_anti_float"]
    body = body.replace("        v\n", "        " + "r" * 257 + " = v\n")
    outcome = cells.r02_build(tmp_path, "mysql", body)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [(b["code"], b["subject"]["detail"]) for b in public["blockers"]] == [
        ("PIE-B1003", "comparison_type_pair_not_admitted"),
        ("PIE-B1002", "output_label_unrepresentable"),
    ]


def _forged_anti(directory, monkeypatch, body):
    """A MySQL artifact emitted while the cell law admits every comparison as
    an ANTI cell, and its exported document."""
    with monkeypatch.context() as patch:
        patch.setattr(
            rows,
            "mysql_float_cell",
            lambda request, expression: ("anti", "none", "=="),
        )
        outcome = cells.r02_build(directory, "mysql", body, controls=True)
        artifact = outcome.artifact
        assert outcome.status == "VERIFIED" and artifact is not None
        observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    return artifact, observed.canonical_bytes


@pytest.mark.parametrize(
    "name",
    (
        *("semi_exists", "semi_exists_kw", "semi_exists_not_ne", "semi_exists_ne"),
        *("anti_ne", "anti_not_ne", "anti_same_value", "anti_key_first"),
        *("anti_two_keys", "anti_key_mixed_width", "anti_outer_extra_field"),
        *("anti_key_255", "anti_nullable_key", "anti_int_key", "anti_nonnull_float"),
        *("anti_mixed_float", "anti_same_table", "anti_extra_conjunct"),
        *("anti_inner_extra_test", "anti_as_value", "anti_beside_join"),
        *("anti_upstream", "inner_on_outer_table", "anti_inner_floats"),
        *("anti_inner_key_both_sides", "anti_outer_key_both_sides"),
        "anti_upstream_binder",
    ),
)
def test_a_mysql_anti_comparison_forged_past_its_cell_is_refused(
    tmp_path, monkeypatch, name
):
    """Emission forced to admit an R02 control. The live verifier refuses it
    from its plan, by the emission blockers it derives again and, with those
    bypassed, by its own comparison law; the pure boundary refuses it from
    the document's own structure."""
    from pietto._project import project_sql_emission_verification as verification

    artifact, document = _forged_anti(
        tmp_path, monkeypatch, {**cells.R02_REFUSED, **cells.R02_ALSO_REFUSED}[name]
    )
    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )
    with monkeypatch.context() as patch:
        patch.setattr(verification, "emission_blockers", lambda request: ())
        assert verify_project_sql_emission(artifact, artifact.request).issues == (
            "plan_ast_correspondence",
        )
    refused = pure.parse_emission_observation(document)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "MySQL Float row comparison cell",
    )


@pytest.mark.parametrize(
    "name",
    (
        *("source_only_unread_let", "source_only_unused_window"),
        *("source_only_def_call", "unread_alias_beside_binder", "outer_alias"),
    ),
)
def test_a_forged_anti_source_only_difference_is_refused_live(
    tmp_path, monkeypatch, name
):
    """An unread relation `let`, an unused named window or a def call changes
    the document only in source positions and bytes; emission and the live
    verifier, which read the declaration as written, refuse it."""
    artifact, _ = _forged_anti(
        tmp_path, monkeypatch, {**cells.R02_REFUSED, **cells.R02_ALSO_REFUSED}[name]
    )
    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )


def _anti_inner_on_outer_table(records):
    """`i`'s bound source names `o`'s table."""
    outer, inner = (r["fields"] for r in records if r["ref"][0] == "bound_source")
    inner["name"] = outer["name"]


def _anti_outer_key_nullable(records):
    """`o`'s `kn`, which no form reads, is nullable: O has other carriers."""
    (field,) = (r["fields"] for r in records if r["ref"] == ["bound_field", 2])
    representation = json.loads(field["representation"])
    representation["nullable"] = True
    field["representation"] = json.dumps(
        representation, separators=(",", ":"), sort_keys=True
    )


@pytest.mark.parametrize(
    "tamper",
    (
        # The `==` read as `!=`, which no ANTI cell holds.
        _rewritten("sql_operation", "operator", "!="),
        _anti_inner_on_outer_table,
        _anti_outer_key_nullable,
    ),
)
def test_a_tampered_mysql_anti_cell_document_is_refused(tmp_path, tamper):
    _, body = cells.R02_FORMS["r02_anti_float"]
    artifact = cells.r02_build(tmp_path, "mysql", body).artifact
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


# Programs outside every null-safe JOIN cell that emission, forced past the
# cell law, emits: the pure boundary sees each in the document, except a
# relation alias `let`, an inlined `def` and a source key, which change the
# document only in source positions or not at all.
NULLSAFE_FORGED = (
    *("same_table", "literal_operand", "same_side_operands", "non_null_operand"),
    *("int4_carrier", "text_width_1000", "text_domains_differ"),
    *("unselected_wide_text", "unselected_float"),
    *("select_subset", "select_reordered", "select_repeated"),
    *("relation_alias_let_where", "left_where_is_none", "left_where_other"),
    *("chain_after_left", "chain_before_equality"),
    *("semi_before_join", "anti_before_join", "inner_order_by", "mixed"),
)


def _forged_nullsafe(directory, monkeypatch, source, contract):
    """The artifact and its document when emission admits every `same_value`
    call of a JOIN `on`, as if its cell law were bypassed."""
    from pietto._project import project_sql_plan_expressions as plan_rows

    with monkeypatch.context() as patch:
        patch.setattr(
            rows,
            "nullsafe_join_calls",
            lambda request: frozenset(
                e.ref
                for e in request.plan.expressions
                if type(e) is plan_rows.ProjectSQLScalarCall
                and e.callee_symbol.name == "same_value"
            ),
        )
        outcome = nullsafe.build(directory, source, contract)
        artifact = outcome.artifact
        assert outcome.status == "VERIFIED" and artifact is not None
        observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    return artifact, observed.canonical_bytes


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("name", NULLSAFE_FORGED)
def test_a_null_safe_join_condition_forged_past_its_cell_is_refused(
    tmp_path, monkeypatch, target, name
):
    """Emission forced to admit a JOIN `on` `same_value` outside every cell.
    The live verifier refuses it by the emission blockers it derives again
    (nullsafe_join_cell, as emission calls it); the pure boundary refuses it
    from the document's own structure, by the cell table it restates."""
    artifact, document = _forged_nullsafe(
        tmp_path, monkeypatch, *nullsafe.refused(target)[name]
    )
    assert verify_project_sql_emission(artifact, artifact.request).issues == (
        "plan_ast_correspondence",
    )
    refused = pure.parse_emission_observation(document)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "null-safe JOIN condition cell",
    )


def test_the_pure_null_safe_join_tables_restate_emissions():
    assert pure._NULLSAFE_JOIN_STRUCTURES == rows.NULLSAFE_JOIN_STRUCTURES
    assert pure._NULLSAFE_JOIN_CARRIERS == rows.NULLSAFE_JOIN_CARRIERS
    assert pure._NULLSAFE_JOIN_CELLS == rows.NULLSAFE_JOIN_CELLS
    assert all(
        pure._nullsafe_join_fields(*cell[0:1], *cell[2:])
        == rows.nullsafe_join_fields(*cell[0:1], *cell[2:])
        for cell in rows.NULLSAFE_JOIN_CELLS
    )


def _narrowed(records):
    """An INNER S1 document whose left `v` column claims non-null."""
    fields = {tuple(r["ref"]): r["fields"] for r in records}
    (join,) = (r["fields"] for r in records if r["ref"][0] == "join_body")
    column = fields[tuple(fields[tuple(join["columns"][1])]["column"])]
    fields[tuple(column["realization"])]["nullable"] = False


def _same_side(records):
    """The ON's right operand reads the left input's `v`."""
    fields = {tuple(r["ref"]): r["fields"] for r in records}
    (join,) = (r["fields"] for r in records if r["ref"][0] == "join_body")
    left, right = (
        fields[tuple(operand)]
        for operand in fields[tuple(join["predicate"])]["operands"]
    )
    right["column"], right["scope"] = left["column"], left["scope"]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "tamper",
    (_rewritten("join_body", "join_kind", "full"), _narrowed, _same_side),
    ids=("full", "narrowed", "same_side"),
)
def test_a_tampered_null_safe_join_document_is_refused(tmp_path, target, tamper):
    artifact = nullsafe.cell(tmp_path, target, "inner", "S1", "int").artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    document = json.loads(observed.canonical_bytes)
    tamper(document["records"])
    refused = pure.parse_emission_observation(json.dumps(document))
    assert refused.status is pure.Status.INVALID_RELATION
    assert refused.detail == "null-safe JOIN condition cell"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_typed_division_is_postgres_only_at_the_project_row_boundary(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "modulo")
    # R08 opens a MySQL field over a literal of 2 or more only.
    source = item["source"].replace("rest = id % 2", "half = id / 1")
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


# --------------------------------------------------------------------------
# Phase77 S01: MySQL checked Int in its cells
# --------------------------------------------------------------------------

# The public nullability of each cell body's columns.
S01_NULLABLE = {
    "s01_families": [
        False,
        "unknown",
        "unknown",
        "unknown",
        True,
        True,
        True,
        "unknown",
    ],
    "s01_where": ["unknown"],
    "s01_table": ["unknown"],
    "s01_beside_field": [True, True],
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("cell", sorted(S01_NULLABLE))
def test_mysql_checked_int_cells_emit_and_every_reader_accepts(tmp_path, cell, target):
    """S01: a MySQL project emits `+`, `-`, `*`, unary `-` and `abs` over
    nullable BIGINT source fields as the whole value of a SELECT item of a
    query that reads its source through a WHERE at most: MySQL's BIGINT
    operators raise 1690 (SQLSTATE 22003) outside signed 64 bits, as
    PostgreSQL's raise 22003. The result is a nullable Int over all of signed
    64 bits. Both families emit the pinned SQL, PostgreSQL's unchanged, and
    every reader accepts it."""
    checked, outcome = probe.numeric_world(tmp_path, target, probe.NUMERIC_CELLS[cell])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert (
        outcome.artifact.rendered.sql.decode() == probe.NUMERIC_CELL_SQL[cell, target]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert [column["nullable"] for column in document["columns"]] == (
        S01_NULLABLE[cell]
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "spelling", [name for name in probe.NUMERIC_SPELLINGS if name.startswith("s01")]
)
def test_mysql_checked_int_spellings_emit_the_direct_sql(tmp_path, spelling, target):
    """A `def` that inlines to the operation (its parameters swapped or not),
    a `def` calling one, an identity `def` around an operand or the whole
    operation, parentheses and reads qualified by the source's own name
    change nothing: each emits `s = a + b`'s SQL. The plan holds the inlined
    operation, so no reader sees the `def`."""
    _, outcome = probe.numeric_world(
        tmp_path / "spelled", target, probe.NUMERIC_SPELLINGS[spelling]
    )
    _, direct = probe.numeric_world(
        tmp_path / "direct",
        target,
        "query result:\n    from rows\n    select:\n        s = a + b\n",
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert direct.artifact is not None
    assert outcome.artifact.rendered.sql == direct.artifact.rendered.sql


def numeric_blockers(outcome):
    """The public blockers as (code, detail, line, column)."""
    return [
        (
            blocker["code"],
            blocker["subject"]["detail"],
            blocker["location"]["line"],
            blocker["location"]["column"],
        )
        for blocker in json.loads(serialize_project_sql_emission(outcome))["blockers"]
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "shape", [name for name in probe.NUMERIC_REFUSALS if not name.startswith("sum_")]
)
def test_mysql_checked_int_outside_its_cells_keeps_its_refusal(tmp_path, shape, policy):
    """Every other MySQL Int operation that may leave signed 64 bits keeps
    the refusal main reports, object for object: a non-null or narrow
    operand, a literal, a nested operation, a `let` (a value, a carried
    field or a relation alias, `let x = rows` before `from x`, its chains
    and one that nothing reads, or a window nothing reads), WHERE, ORDER BY,
    LIMIT, DISTINCT, a header parameter read or not, an imported source, an
    upstream query, JOIN or set operand; a cell beside another refused form
    keeps its own refusal too (owner 2026-11-13T00:20Z). PostgreSQL emits
    each as before."""
    body = probe.NUMERIC_REFUSALS[shape]
    _, outcome = probe.numeric_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert numeric_blockers(outcome) == probe.NUMERIC_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.numeric_world(tmp_path / "postgres", "postgres", body, policy)
    assert postgres.status == "VERIFIED", postgres.blockers


def test_a_refused_mysql_cell_query_reports_main_blockers_from_any_check(
    tmp_path, monkeypatch
):
    """A refused statement reports main's blockers whichever check refuses
    it: emission_blockers, which plain verification and guarded preparation
    also read, and a later check of the emission (here plan correspondence),
    each derive them again with every cell shut."""
    from pietto._project import project_sql_emission as emission

    seen = []
    blockers = emission.emission_blockers
    monkeypatch.setattr(
        emission,
        "emission_blockers",
        lambda request: seen.append(blockers(request)) or seen[-1],
    )
    probe.numeric_world(
        tmp_path / "beside", "mysql", probe.NUMERIC_REFUSALS["beside_literal_operand"]
    )
    assert [(b.code, b.location.line) for b in seen[0]] == [
        ("PIE-B1002", 12),
        ("PIE-B1002", 13),
    ]
    monkeypatch.setattr(emission, "verify_row_query", lambda request, query: False)
    _, outcome = probe.numeric_world(
        tmp_path / "late", "mysql", probe.NUMERIC_SPELLINGS["s01_parenthesized"]
    )
    assert numeric_blockers(outcome) == [
        ("PIE-B1002", "arithmetic_outside_physical_range", 12, 9)
    ]


def test_a_bind_safe_literal_leaves_the_mysql_checked_int_cell(tmp_path):
    """Under bind_safe_literals a WHERE literal becomes a bind-safe `?`, which
    no cell holds: the query keeps main's refusal."""
    _, outcome = probe.numeric_world(
        tmp_path, "mysql", probe.NUMERIC_CELLS["s01_where"], "bind_safe_literals"
    )
    assert numeric_blockers(outcome) == [
        ("PIE-B1002", "arithmetic_outside_physical_range", 13, 9)
    ]


@pytest.mark.parametrize(
    "body",
    (
        "query result:\n    from rows\n    where id > -1\n    select:\n"
        '        s = a + b\n        t = -1\n        u = "x"\n        v = 1.5\n'
        "        w = True\n",
        "query result:\n    from rows\n    where id in (-1, 2)\n    group by k\n"
        "    select:\n        k\n        x = sum(a)\n",
        "query result:\n    from rows\n    select:\n        s = a + b\n"
        "        t = coalesce(a, None)\n",
    ),
)
def test_every_reader_accepts_a_mysql_numeric_cell_beside_literals(tmp_path, body):
    """A cell's query may hold literals of any kind beside it, a negative one
    and None included, in its WHERE or its other SELECT items: emission verifies it
    and every reader, whose cell laws admit only listed record kinds,
    accepts it."""
    _, outcome = probe.numeric_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)


def _plan_with(plan, **tables):
    """A copy of a closed plan with some tables replaced."""
    edited = copy(plan)
    for name, value in tables.items():
        object.__setattr__(edited, name, value)
    return edited


def _column_edit(**changes):
    """An edit of the S01 cell's first operand column."""

    def edit(plan, expression, values):
        column = replace(values[0].column, **changes)
        return plan, expression, (replace(values[0], column=column), *values[1:])

    return edit


def _boundary_edit(boundary):
    def edit(plan, expression, values):
        block = replace(plan.blocks[0], boundary=boundary(plan.blocks[0].boundary))
        return _plan_with(plan, blocks=(block, *plan.blocks[1:])), expression, values

    return edit


def _site_edit(site):
    def edit(plan, expression, values):
        return plan, replace(expression, site=site(expression.site)), values

    return edit


def _operand_edit(**changes):
    def edit(plan, expression, values):
        realization = replace(values[0].realization, **changes)
        return plan, expression, (replace(values[0], realization=realization),)

    return edit


# D77.24: each edit of a native S01 cell's input that only one check of the
# emission law refuses, whatever other rule also refuses the shape it stands
# for; the operand edits reach mysql_checked_operands, which compiled
# semantics shares.
S01_LAW_EDITS = {
    "plan_table": lambda plan, expression, values: (
        _plan_with(plan, windows=(None,)),
        expression,
        values,
    ),
    "boundary_type": _boundary_edit(lambda boundary: None),
    "boundary_reason": _boundary_edit(
        lambda boundary: replace(boundary, reason=ProjectSQLBoundaryReason.NAMED_INPUT)
    ),
    "site_type": _site_edit(
        lambda site: SimpleNamespace(role=site.role, occurrence=site.occurrence)
    ),
    "site_role": _site_edit(
        lambda site: replace(site, role=ProjectSQLExpressionRole.WHERE)
    ),
    "no_operand": lambda plan, expression, values: (plan, expression, ()),
    "computed_operand": lambda plan, expression, values: (
        plan,
        expression,
        (expression, *values[1:]),
    ),
    "column_not_field": _column_edit(field=None),
    "column_not_source": _column_edit(source_port=None),
    "column_literal": _column_edit(literal=object()),
    "column_aggregate": _column_edit(aggregate=object()),
    "column_window": _column_edit(window=object()),
}
S01_OPERAND_EDITS = {
    "operand_tag": {"tag": "Decimal"},
    "operand_binding": {"binding": True},
}


@pytest.mark.parametrize("edit", sorted(S01_LAW_EDITS))
def test_the_mysql_checked_int_cell_law_refuses_each_edited_input(tmp_path, edit):
    """The S01 law emission asks of each MySQL Int operation holds the
    native `s = a + b` cell and refuses the cell once one of its inputs
    changes: a plan table no cell holds, an input that is not the source, a
    site that is not a SELECT item's, no or a computed operand, or an
    operand column that is no source field."""
    plan, expression, values = probe.numeric_law_inputs(
        tmp_path, probe.NUMERIC_CELLS["s01_where"]
    )["mysql_checked_cell"]
    assert rows.mysql_checked_cell(plan, expression, values) is True
    assert rows.mysql_checked_cell(*S01_LAW_EDITS[edit](plan, expression, values)) is (
        False
    )


@pytest.mark.parametrize("edit", sorted(S01_OPERAND_EDITS))
def test_the_mysql_checked_operand_law_refuses_each_edited_carrier(tmp_path, edit):
    """A cell's operands are nullable BIGINT Int values that no binding
    proves: another tag, a binding or no operand at all leaves the cell, and
    MySQL's target-checked operation is then refused."""
    _, _, values = probe.numeric_law_inputs(tmp_path, probe.NUMERIC_CELLS["s01_where"])[
        "mysql_checked_cell"
    ]
    carriers = tuple(value.realization for value in values)
    assert rows.mysql_checked_operands(carriers) is True
    edited = (replace(carriers[0], **S01_OPERAND_EDITS[edit]), *carriers[1:])
    assert rows.mysql_checked_operands(edited) is False
    assert rows.mysql_checked_operands(()) is False
    full = rows.SIGNED64[0] * 2, rows.SIGNED64[1] * 2
    storage = {"kind": "my_signed_int"}
    assert rows._target_checked_int("mysql", storage, *full, True, carriers)
    assert rows._target_checked_int("mysql", storage, *full, True) is None
    # Plain and compiled verification's own law: only a cell's operation
    # (its caller marks it) relies on MySQL's checked BIGINT operator.
    checked = resolved_row_realization(
        "mysql", "binary", "+", "Int", "unknown", carriers, mysql_checked=True
    )
    assert checked.storage == storage and checked.proven_int_range == rows.SIGNED64
    with pytest.raises(ValueError, match="outside its physical range"):
        resolved_row_realization("mysql", "binary", "+", "Int", "unknown", carriers)


def _key_edit(**changes):
    def edit(plan, keys):
        return plan, (replace(keys[0], **changes), *keys[1:])

    return edit


def _source_edit(**changes):
    def edit(aggregate, argument):
        source = replace(aggregate.source, **changes)
        return replace(aggregate, source=source), argument

    return edit


# D77.24: each edit of a native S02 cell's input that only one check of the
# emission law refuses, whatever other rule also refuses the shape it stands
# for.
S02_QUERY_EDITS = {
    "key_not_field": _key_edit(field=None),
    "key_not_int": lambda plan, keys: (
        plan,
        (replace(keys[0], realization=replace(keys[0].realization, tag="Text")),),
    ),
    "select_expression": lambda plan, keys: (
        _plan_with(
            plan,
            expressions=(
                *plan.expressions,
                SimpleNamespace(
                    site=SimpleNamespace(role=ProjectSQLExpressionRole.SELECT)
                ),
            ),
        ),
        keys,
    ),
}
S02_CELL_EDITS = {
    "fact": _source_edit(fact=None),
    "computed_argument": lambda aggregate, argument: (aggregate, aggregate),
}


@pytest.mark.parametrize(
    "edit", [*sorted(S02_QUERY_EDITS), *sorted(S02_CELL_EDITS), "result_carrier"]
)
def test_the_mysql_sum_cell_law_refuses_each_edited_input(tmp_path, edit):
    """The S02 laws emission asks of a MySQL aggregation and of each of its
    sums hold the native `group by k` cell and refuse it once one input
    changes: a key that is no non-null Int source field, a SELECT item that
    computes, a sum whose fact is no result fact, or a computed argument;
    and the sum result law refuses an INT argument (S03 sums a non-null
    BIGINT count, so the cell laws, not the result law, pin the carrier)."""
    seen = probe.numeric_law_inputs(tmp_path, probe.NUMERIC_CELLS["s02_grouped"])
    plan, keys = seen["mysql_sum_query"]
    aggregate, argument = seen["mysql_sum_cell"]
    assert keys and rows.mysql_sum_query(plan, keys) is True
    assert rows.mysql_sum_cell(aggregate, argument) is True
    if edit in S02_QUERY_EDITS:
        assert rows.mysql_sum_query(*S02_QUERY_EDITS[edit](plan, keys)) is False
    elif edit in S02_CELL_EDITS:
        assert rows.mysql_sum_cell(*S02_CELL_EDITS[edit](aggregate, argument)) is (
            False
        )
    else:
        assert grouping.result_realization("mysql", "sum", argument, ("Int", True))[0]
        narrow = SimpleNamespace(
            realization=replace(argument.realization, storage={"kind": "my_int"})
        )
        assert grouping.result_realization("mysql", "sum", narrow, ("Int", True)) == (
            None,
            ("PIE-B1002", "sum_result_logical_type_or_argument_drift"),
        )


# --------------------------------------------------------------------------
# Phase77 S15: MySQL Int % and Float % in their cell (template T15-1)
# --------------------------------------------------------------------------

_INT64_DOMAIN = {
    "kind": "int_range",
    "min": str(-(1 << 63)),
    "max": str((1 << 63) - 1),
}


def test_mysql_remainder_cells_realize_their_carriers(tmp_path):
    """An Int `%` cell is a `my_bigint` over all of signed 64 bits and a Float
    one a finite `my_double`; MySQL returns NULL for a zero divisor, so both
    are of unknown nullability. Neither carries R13 evidence; the field reads
    beside them keep their source carriers."""
    _, outcome = probe.remainder_world(
        tmp_path, "mysql", probe.REMAINDER_CELLS["s15_mod_cells"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert [
        (column["label"], column["representation"]) for column in document["columns"]
    ] == [
        (
            "id",
            {
                "storage": {"kind": "my_bigint"},
                "nullable": False,
                "domain": _INT64_DOMAIN,
            },
        ),
        (
            "a",
            {
                "storage": {"kind": "my_bigint"},
                "nullable": True,
                "domain": _INT64_DOMAIN,
            },
        ),
        (
            "x",
            {
                "storage": {"kind": "my_double"},
                "nullable": True,
                "domain": rows.FINITE_FLOAT,
            },
        ),
        (
            "r",
            {
                "storage": {"kind": "my_bigint"},
                "nullable": "unknown",
                "domain": _INT64_DOMAIN,
            },
        ),
        (
            "m",
            {
                "storage": {"kind": "my_double"},
                "nullable": "unknown",
                "domain": rows.FINITE_FLOAT,
            },
        ),
    ]
    assert not [
        item
        for item in document["requirements"]
        if any("target_checked" in str(part) for part in item["evidence"])
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.REMAINDER_REFUSALS))
def test_mysql_remainder_outside_its_cell_keeps_main_refusal(tmp_path, shape, policy):
    """Every other MySQL `%` keeps main's refusal, the whole statement's
    blockers object for object (owner 2026-11-13T00:20Z): a `%` beside an S01
    cell, `abs`, a comparison, an `Int /` or a `Float /`, under a WHERE
    without a literal, beside a direct read of a DECIMAL, text or `INT`
    field, over an `INT` operand or a literal, nested, or through a `def`
    (as the cell, an argument or an item beside it)."""
    _, outcome = probe.remainder_world(
        tmp_path, "mysql", probe.REMAINDER_REFUSALS[shape], policy, side=True
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert numeric_blockers(outcome) == probe.REMAINDER_REFUSAL_BLOCKERS[shape]


def test_a_refused_mysql_remainder_query_reports_main_blockers_from_a_later_check(
    tmp_path, monkeypatch
):
    """A statement of S15 cells that a check after the emission blockers
    refuses (here plan correspondence) reports main's blockers at its Int
    and its Float `%`, derived again with every cell shut (D77.37)."""
    from pietto._project import project_sql_emission as emission

    monkeypatch.setattr(emission, "verify_row_query", lambda request, query: False)
    _, outcome = probe.remainder_world(
        tmp_path, "mysql", probe.REMAINDER_CELLS["s15_mod_cells"]
    )
    assert numeric_blockers(outcome) == [
        ("PIE-B1003", "binary_operator_not_admitted", 18, 9),
        ("PIE-B1003", "float_remainder_exact_binary64_not_realized", 19, 9),
    ]


def test_mysql_remainder_cells_are_derived_once_per_projection(tmp_path, monkeypatch):
    """Emission and its verification ask for a projection's S15 cells a fixed
    number of times however many cells it holds, and the per-item check runs
    exactly twice as often for twice the items (P76-PERF-2)."""
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    counts = {}
    for count in (1, 20, 40):
        cells, reads = [], []
        with monkeypatch.context() as patch:
            for name, calls in (
                ("mysql_remainder_cells", cells),
                ("_mysql_remainder_read", reads),
            ):
                patch.setattr(
                    rows,
                    name,
                    lambda *args, _law=getattr(rows, name), _calls=calls: (
                        _calls.append(args) or _law(*args)
                    ),
                )
            body = "table result:\n    from nums\n    select:\n" + "".join(
                f"        r{index} = a % b\n" for index in range(count)
            )
            _, outcome = probe.remainder_world(tmp_path / str(count), "mysql", body)
            emitted = len(cells), len(reads)
            assert outcome.artifact is not None, outcome.blockers
            assert verify_project_sql_emission(
                outcome.artifact, outcome.artifact.request
            ).verified
        counts[count] = (emitted, (len(cells) - emitted[0], len(reads) - emitted[1]))
    assert counts[1][0][0] == counts[40][0][0] > 0
    assert counts[1][1][0] == counts[40][1][0] > 0
    assert counts[40][0][1] == 2 * counts[20][0][1] > 0
    assert counts[40][1][1] == 2 * counts[20][1][1] > 0


# --------------------------------------------------------------------------
# Phase77 R08: MySQL Int / in its cell (template T08-1)
# --------------------------------------------------------------------------


def test_mysql_division_cells_realize_their_carrier(tmp_path):
    """An Int `/` cell is a `my_bigint` over all of signed 64 bits; MySQL
    returns NULL for a zero divisor, so it is of unknown nullability, and it
    carries no R13 evidence. The field reads beside it keep their carriers."""
    _, outcome = probe.division_world(
        tmp_path, "mysql", probe.DIVISION_CELLS["r08_literal_cells"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    cell = {"storage": {"kind": "my_bigint"}, "nullable": "unknown"}
    field = {"storage": {"kind": "my_bigint"}, "nullable": False}
    assert [
        (column["label"], column["representation"]) for column in document["columns"]
    ] == [
        (label, {**(cell if label.startswith("q") else field), "domain": _INT64_DOMAIN})
        for label in ("id", "d", "q1", "q2", "q3", "q4")
    ]
    assert not [
        item
        for item in document["requirements"]
        if any("target_checked" in str(part) for part in item["evidence"])
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.DIVISION_REFUSALS))
def test_mysql_division_outside_its_cell_keeps_main_refusal(tmp_path, shape, policy):
    """Every other MySQL `/` keeps main's refusal (owner 2026-11-13T00:20Z),
    the whole statement's blockers in order, compared here as (code, detail,
    line, column) only: a field over a
    field whatever its storage, declared domain or `value_domain` premise
    (which PostgreSQL takes), a literal divisor below 2 or under a sign, a
    literal over a literal, a nested, signed, `abs` or header-parameter
    operand, an operand of a `def`, a cell under another operation, in a
    WHERE or `let`, beside an item of another kind (an S01 or S15 cell
    included), under a WHERE, and read through an upstream definition or a
    JOIN."""
    premise = probe.DIVISION_PREMISES.get(shape)
    body = probe.DIVISION_REFUSALS[shape]
    _, outcome = probe.division_world(tmp_path, "mysql", body, policy, premise)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert numeric_blockers(outcome) == probe.DIVISION_REFUSAL_BLOCKERS.get(
        shape, [("PIE-B1003", "binary_operator_not_admitted", 14, 9)]
    )
    if premise is not None:
        _, outcome = probe.division_world(
            tmp_path / "pg", "postgres", body, policy, premise
        )
        assert outcome.status == "VERIFIED", outcome.blockers


def test_mysql_division_literals_are_read_on_the_lines_the_parser_reads(tmp_path):
    """A lone CR ends a line, as for the parser: after one, a `def` body
    keeps main's refusal although the next line holds a number token at its
    columns, and literals written in their items open their cells."""
    head = "def two() -> Int:\r    return 2\n" + probe.DIVISION_SELECT + "        id\n"
    _, outcome = probe.division_world(
        tmp_path / "def",
        "mysql",
        head + "        q = b / two()\n        r = b / 10000\n#               10000\n",
    )
    assert numeric_blockers(outcome) == [
        ("PIE-B1003", "binary_operator_not_admitted", line, 9) for line in (16, 17)
    ]
    _, outcome = probe.division_world(
        tmp_path / "written", "mysql", head + "        q = b / 2\n        r = b / 3\n"
    )
    assert outcome.status == "VERIFIED", outcome.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_refused_mysql_division_query_reports_main_blockers_from_a_later_check(
    tmp_path, monkeypatch, policy
):
    """A statement of R08 cells that a check after the emission blockers
    refuses (here plan correspondence) reports main's blocker at each `/`,
    derived again with every cell shut (D77.37, rows.AS_MAIN)."""
    from pietto._project import project_sql_emission as emission

    monkeypatch.setattr(emission, "verify_row_query", lambda request, query: False)
    _, outcome = probe.division_world(
        tmp_path, "mysql", probe.DIVISION_CELLS["r08_literal_cells"], policy
    )
    assert numeric_blockers(outcome) == [
        ("PIE-B1003", "binary_operator_not_admitted", line, 9)
        for line in (15, 16, 17, 18)
    ]


def test_mysql_division_cells_are_derived_once_per_projection(tmp_path, monkeypatch):
    """Emission and its verification ask for a projection's R08 cells a fixed
    number of times however many cells it holds, and the per-item check runs
    exactly twice as often for twice the items (P76-PERF-2)."""
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    counts = {}
    for count in (1, 20, 40):
        cells, reads = [], []
        with monkeypatch.context() as patch:
            for name, calls in (
                ("mysql_division_cells", cells),
                ("_mysql_division_read", reads),
            ):
                patch.setattr(
                    rows,
                    name,
                    lambda *args, _law=getattr(rows, name), _calls=calls: (
                        _calls.append(args) or _law(*args)
                    ),
                )
            body = probe.DIVISION_SELECT + "".join(
                f"        q{index} = b / 2\n" for index in range(count)
            )
            _, outcome = probe.division_world(tmp_path / str(count), "mysql", body)
            emitted = len(cells), len(reads)
            assert outcome.artifact is not None, outcome.blockers
            assert verify_project_sql_emission(
                outcome.artifact, outcome.artifact.request
            ).verified
        counts[count] = (emitted, (len(cells) - emitted[0], len(reads) - emitted[1]))
    assert counts[1][0][0] == counts[40][0][0] > 0
    assert counts[1][1][0] == counts[40][1][0] > 0
    assert counts[40][0][1] == 2 * counts[20][0][1] > 0
    assert counts[40][1][1] == 2 * counts[20][1][1] > 0
