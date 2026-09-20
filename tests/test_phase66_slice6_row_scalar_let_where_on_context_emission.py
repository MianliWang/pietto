"""Admitted row scalars, ordered LET stages, TRUE-only filters and ON context."""

from copy import copy
from dataclasses import replace
import json

import pytest

import _pietto_phase66_sql_emission_probe as probe
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
        assert storage == ["pg_int8"] * 3 + ["pg_bool"] * 4
    else:
        assert storage[0] == "my_bigint"
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
        "min": "-9007199254740992",
        "max": "9007199254740994",
    }
    assert doubled.realization.domain == {
        "kind": "int_range",
        "min": "-18014398509481984",
        "max": "18014398509481988",
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


# --------------------------------------------------------------------------
# Finite range checking
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "variant,code,detail",
    (
        ("int_overflow", "PIE-B1002", "arithmetic_outside_physical_range"),
        ("unary_overflow", "PIE-B1002", "unary_result_outside_physical_range"),
        ("float_arithmetic", "PIE-B1003", "arithmetic_requires_signed_int_operands"),
        ("float_comparison", "PIE-B1003", "comparison_type_pair_not_admitted"),
        ("bool_comparison", "PIE-B1003", "comparison_type_pair_not_admitted"),
        ("modulo", "PIE-B1003", "binary_operator_not_admitted"),
        ("between", "PIE-B1003", "scalar_projection_requires_later_slice"),
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


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_overflowing_intermediate_is_rejected_beneath_a_false_filter(
    tmp_path, target
):
    """A filter that can never retain a row still cannot license an overflow."""
    item = probe.fixture(target, "V_row_blocked", "int_overflow")
    source = item["source"].replace(
        "    select:\n", "    where id > 0 and id < 0\n    select:\n"
    )
    source = source.replace("        big = id + 1\n", "        big = (id + 1) - 1\n")
    _, outcome = probe.build_case(tmp_path, source, item["contract"], item["policy"])
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert "PIE-B1002" in [b["code"] for b in public["blockers"]]
    assert "arithmetic_outside_physical_range" in [
        b["subject"]["detail"] for b in public["blockers"]
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_bounded_field_and_constant_arithmetic_is_admitted(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    select:\n"
        "        constant = 2 * 3\n"
        "        bounded = id - 1\n"
        "        negated = -id\n",
    )
    _, outcome = probe.build_case(
        tmp_path, source, stage_contract(target), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["logical_type"]["name"] for c in public["columns"]] == ["Int"] * 3
    domains = [c["representation"]["domain"] for c in public["columns"]]
    assert domains[0] == {"kind": "int_range", "min": "6", "max": "6"}
    assert domains[1]["min"] == "-9007199254740994"
    assert domains[2] == {
        "kind": "int_range",
        "min": "-9007199254740993",
        "max": "9007199254740993",
    }
    # The authored tree survives even where the interval is a single value.
    assert "2" in public["sql"] and "3" in public["sql"]


# --------------------------------------------------------------------------
# Repeated reads, omitted-but-required values and comparison premises
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_repeated_let_reads_are_column_reads_not_new_occurrences(tmp_path, target):
    source = row_source(
        target,
        "    from rows\n    let:\n        bumped = id + 1\n"
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
        "    from rows\n    let:\n        hidden = id + 1\n"
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
        "    from rows\n    let:\n        bumped = id + 7\n"
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
        "    from rows\n    let:\n        bumped = id + 1\n"
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
        + f'source unused: Row is {target}.table("opaque.unused")\n'
        + "table result:\n    from rows\n    let:\n        bumped = id + 1\n"
        "    where id > 0\n    select:\n        kept = bumped\n"
    )
    _, outcome = probe.build_case(
        tmp_path, source, probe.encoded(contract).decode(), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in public["columns"]] == ["kept"]
