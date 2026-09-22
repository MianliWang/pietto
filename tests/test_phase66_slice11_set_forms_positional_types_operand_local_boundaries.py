"""Six SET forms: positional types, operand-local boundaries, sharing and membership.

Every artifact below is produced by the installed emission path from an ordinary
authored project, mostly the very fixtures the target manifest submits. A verdict
is taken from the published status, the emitted bytes and the public document,
never from a production builder deciding that its own output is correct.
"""

from dataclasses import replace
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project import project_sql_emission_sets as setting
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_rendering import render_join_sql
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
    verify_row_bytes,
    verify_row_query,
)

TARGETS = ("postgres", "mysql")
Q = {"postgres": '"', "mysql": "`"}
FORMS = (
    ("union", "all"),
    ("union", "distinct"),
    ("intersect", "all"),
    ("intersect", "distinct"),
    ("except", "all"),
    ("except", "distinct"),
)
SET_KINDS = {"set_operation", "set_operand", "set_column", "set_row_equivalence"}


def emit(target, case, variant):
    item = probe.fixture(target, case, variant)
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case", item["source"], item["contract"], item["policy"]
        )
    return outcome


def emit_source(target, body, *, policy="preserve_literals"):
    base = probe.fixture(target)
    header = base["source"].split("table result:", 1)[0]
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
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case",
            header + body,
            probe.encoded(contract).decode(),
            policy,
        )
    return outcome


def artifact_of(outcome) -> Any:
    assert outcome.artifact is not None
    return outcome.artifact


def sql_of(outcome) -> str:
    return artifact_of(outcome).rendered.sql.decode()


def blockers(outcome) -> list[str]:
    return [item.detail for item in (outcome.blockers or ())]


def public(outcome) -> dict:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def generated(document, kind):
    return [
        item
        for item in document["requirements"]
        if item["denominator"] == "generated" and item["kind"] == kind
    ]


def set_units(outcome) -> list[Any]:
    query = artifact_of(outcome).ast
    return [u for u in query.units if type(u) is setting.SetBody]


def final_statement(sql: str) -> str:
    """The final returning query: the text after the last CTE definition.

    Each CTE is `name (cols) AS (body)`; only a CTE header spells ` AS (`, so the
    balanced body after it ends either at `, ` (another CTE) or at the single
    gap before the final statement.
    """
    if not sql.startswith("WITH "):
        return sql
    position = 0
    while True:
        opening = sql.index(" AS (", position) + 4
        depth, closing = 0, opening
        for index in range(opening, len(sql)):
            if sql[index] == "(":
                depth += 1
            elif sql[index] == ")":
                depth -= 1
                if depth == 0:
                    closing = index
                    break
        if sql[closing + 1 : closing + 3] == ", ":
            position = closing + 1
            continue
        return sql[closing + 2 :]


def cte_bodies(sql: str) -> dict[str, str]:
    bodies = {}
    for match in re.finditer(r"[\"`](p[0-9]+)[\"`] \([^)]*\) AS \(", sql):
        depth, begin = 1, match.end()
        for index in range(begin, len(sql)):
            if sql[index] == "(":
                depth += 1
            elif sql[index] == ")":
                depth -= 1
                if depth == 0:
                    bodies[match.group(1)] = sql[begin:index]
                    break
    return bodies


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind,quantifier", FORMS)
def test_each_form_is_one_explicitly_grouped_native_operation(target, kind, quantifier):
    """R22: the spelled operator over two parenthesized complete operand terminals."""
    outcome = emit(target, "S_set_forms", f"{kind}_{quantifier}")
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    q = Q[target]
    operator = f" {kind.upper()} {quantifier.upper()} "
    final = final_statement(sql)
    assert final.count(operator) == 1 and sql.count(operator) == 1
    left, right = final.split(operator)
    for part in (left, right):
        assert part.startswith("(SELECT ") and part.endswith(")")
        assert f" AS {q}k{q} FROM {q}p" in part
    # Each operand reads its own producer CTE through its own alias, never the
    # scan and never the other operand.
    assert re.search(
        rf"\(SELECT {q}o\d+{q}\.{q}c0{q} AS {q}k{q} FROM {q}p\d+{q} AS {q}o\d+{q}\)",
        left,
    )
    (unit,) = set_units(outcome)
    assert (
        unit.final and unit.kind.value == kind and unit.quantifier.value == quantifier
    )
    assert [o.position for o in unit.operands] == [0, 1]
    assert unit.operands[0].producer is not unit.operands[1].producer
    document = public(outcome)
    (operation,) = generated(document, "set_operation")
    assert operation["evidence"] == [
        {
            "kind": kind,
            "quantifier": quantifier,
            "operands": 2,
            "fold": "source_order_left_fold",
        }
    ]
    assert len(generated(document, "set_operand")) == 2
    assert len(generated(document, "set_row_equivalence")) == (
        0 if (kind, quantifier) == ("union", "all") else 1
    )
    (column,) = document["columns"]
    origin = column["correspondence"]["set_origin"]
    assert origin["kind"] == kind and origin["quantifier"] == quantifier
    assert [o["operand"]["kind"] for o in origin["operands"]] == ["set_operand"] * 2
    assert column["label"] == "k" and column["logical_type"]["name"] == "Int"
    # Both operand keys are nullable, so every form's result is nullable: the
    # INTERSECT narrowing applies only when some operand is non-null.
    assert column["nullable"] is True


@pytest.mark.parametrize("target", TARGETS)
def test_positions_labels_and_arity_are_set_owned(target):
    """Corresponding columns align by position; the first-authored labels win."""
    outcome = emit(target, "S_set_positions", "renamed_labels_union_all")
    assert outcome.status == "VERIFIED", blockers(outcome)
    document = public(outcome)
    assert [c["label"] for c in document["columns"]] == ["k", "t"]
    assert [c["logical_type"]["name"] for c in document["columns"]] == ["Int", "Text"]
    q = Q[target]
    final = final_statement(sql_of(outcome))
    # Both operands label their positional columns with the SET's own labels.
    assert final.count(f" AS {q}k{q}") == 2 and final.count(f" AS {q}t{q}") == 2
    assert "n" not in [c["label"] for c in document["columns"]]
    text = [c for c in document["columns"] if c["label"] == "t"][0]
    assert text["representation"]["domain"]["max_characters"] == 64
    for variant, code in (
        ("arity_mismatch", "PIE-S2342"),
        ("type_mismatch", "PIE-S2343"),
    ):
        rejected = emit(target, "V_set_blocked", variant)
        assert rejected.status == "BLOCKED" and rejected.artifact is None
        assert code in [d.code for d in rejected.diagnostics]
        assert "semantic_result_unsuccessful" in blockers(rejected)


@pytest.mark.parametrize("target", TARGETS)
def test_domains_keep_exact_representations_and_refuse_mismatches(target):
    """C18: no common type, no widening; Float travels only through UNION ALL."""
    decimal = emit(target, "S_set_domains", "decimal_intersect_all")
    assert decimal.status == "VERIFIED", blockers(decimal)
    (column,) = public(decimal)["columns"]
    assert column["logical_type"] == {
        "kind": "builtin",
        "name": "Decimal",
        "parameters": {"precision": 9, "scale": 2},
    }
    big = emit(target, "S_set_domains", "big_int_except_all")
    (column,) = public(big)["columns"]
    assert column["representation"]["domain"]["max"] == "9007199254740993"
    assert column["nullable"] is False
    floats = emit(target, "S_set_domains", "float_union_all")
    assert floats.status == "VERIFIED", blockers(floats)
    (column,) = public(floats)["columns"]
    assert column["logical_type"]["name"] == "Float"
    assert generated(public(floats), "set_row_equivalence") == []
    for kind, quantifier in FORMS[1:]:
        rejected = emit_source(
            target,
            "table a:\n    from rows\n    select:\n        r = ratio\n"
            f"query result:\n    {kind} {quantifier}:\n        from a\n        from a\n",
        )
        assert rejected.status == "BLOCKED" and rejected.artifact is None
        assert "PIE-S2344" in [d.code for d in rejected.diagnostics]
    mismatch = emit(target, "V_set_blocked", "physical_mismatch")
    assert mismatch.status == "BLOCKED" and mismatch.artifact is None
    assert blockers(mismatch) == ["set_column_physical_representation_mismatch"]
    assert [b.code for b in mismatch.blockers] == ["PIE-B1002"]
    assert mismatch.diagnostics == ()


@pytest.mark.parametrize("target", TARGETS)
def test_nesting_is_spelled_never_reassociated(target):
    """A three-operand body folds left explicitly; a nested body is its own CTE."""
    fold = emit(target, "S_set_nesting", "left_fold_except")
    assert fold.status == "VERIFIED", blockers(fold)
    final = final_statement(sql_of(fold))
    assert final.startswith("((SELECT ") and final.count(" EXCEPT DISTINCT ") == 2
    assert re.fullmatch(
        r"\(\(SELECT [^()]*\) EXCEPT DISTINCT \(SELECT [^()]*\)\) EXCEPT DISTINCT \(SELECT [^()]*\)",
        final,
    )
    (unit,) = set_units(fold)
    assert [o.position for o in unit.operands] == [0, 1, 2]
    nested = emit(target, "S_set_nesting", "right_nested_except")
    assert nested.status == "VERIFIED", blockers(nested)
    sql = sql_of(nested)
    inner = [body for body in cte_bodies(sql).values() if " EXCEPT DISTINCT " in body]
    assert len(inner) == 1 and inner[0].startswith("(SELECT ")
    final = final_statement(sql)
    assert final.count(" EXCEPT DISTINCT ") == 1 and not final.startswith("((")
    units = set_units(nested)
    assert len(units) == 2 and not units[0].final and units[1].final
    # The outer right operand reads the nested SET's terminal CTE.
    assert units[1].operands[1].producer is units[0]
    mixed = emit(target, "S_set_nesting", "mixed_union_except")
    assert mixed.status == "VERIFIED", blockers(mixed)
    sql = sql_of(mixed)
    assert " UNION ALL " in sql and final_statement(sql).count(" EXCEPT ALL ") == 1
    assert " UNION ALL " not in final_statement(sql)


@pytest.mark.parametrize("target", TARGETS)
def test_operand_local_boundaries_stay_inside_the_operand(target):
    """C13/C19: ORDER, LIMIT and DISTINCT belong to the operand; the outer
    consumer keeps its own clauses above the SET."""
    q = Q[target]
    ordered = emit(target, "S_set_boundaries", "ordered_operands")
    assert ordered.status == "VERIFIED", blockers(ordered)
    sql = sql_of(ordered)
    limited = [
        name for name, body in cte_bodies(sql).items() if body.endswith(" LIMIT 2")
    ]
    assert len(limited) == 1 and " ORDER BY " in cte_bodies(sql)[limited[0]]
    final = final_statement(sql)
    assert "LIMIT" not in final and "ORDER BY" not in final
    assert final.count(f"FROM {q}{limited[0]}{q} AS") == 2
    zero = emit(target, "S_set_boundaries", "limit_zero_operand")
    assert zero.status == "VERIFIED", blockers(zero)
    assert any(body.endswith(" LIMIT 0") for body in cte_bodies(sql_of(zero)).values())
    document = public(zero)
    assert len(generated(document, "static_limit")) == 1
    distinct = emit(target, "S_set_boundaries", "distinct_operand")
    assert distinct.status == "VERIFIED", blockers(distinct)
    assert "SELECT DISTINCT " in sql_of(distinct)
    assert " UNION ALL " in sql_of(distinct)
    assert "DISTINCT" not in final_statement(sql_of(distinct))
    outer = emit(target, "S_set_boundaries", "outer_consumer")
    assert outer.status == "VERIFIED", blockers(outer)
    sql = sql_of(outer)
    final = final_statement(sql)
    assert final.endswith(" ASC LIMIT 1") and "WHERE" not in final
    union = [body for body in cte_bodies(sql).values() if " UNION ALL " in body]
    assert len(union) == 1 and "WHERE" not in union[0] and "LIMIT" not in union[0]


@pytest.mark.parametrize("target", TARGETS)
def test_producers_are_consumed_as_complete_terminals(target):
    """Grouped, GLOBAL, satisfying and window/QUALIFY operands keep their stage;
    a SET output feeds a window consumer as an established port."""
    for variant, token in (
        ("grouped_union", "GROUP BY"),
        ("global_empty_union", "COUNT(*)"),
        ("satisfying_union", "WHERE"),
        ("window_union_distinct", "ROW_NUMBER()"),
    ):
        outcome = emit(target, "S_set_producers", variant)
        assert outcome.status == "VERIFIED", (variant, blockers(outcome))
        sql = sql_of(outcome)
        assert token in sql and token not in final_statement(sql)
    window = emit(target, "S_set_producers", "set_to_window")
    assert window.status == "VERIFIED", blockers(window)
    sql = sql_of(window)
    assert " UNION ALL " in sql and "ROW_NUMBER() OVER (ORDER BY " in sql
    assert " UNION ALL " not in sql[sql.index("ROW_NUMBER") :]


@pytest.mark.parametrize("target", TARGETS)
def test_r03_repeated_union_and_two_facades_execute_through_the_pipeline(target):
    """R03/C19: shared definitions keep one CTE; every use is its own operand."""
    dag = emit(target, "O_named_later", "union_dag")
    assert dag.status == "VERIFIED", blockers(dag)
    units = set_units(dag)
    assert len(units) == 3 and not any(u.final for u in units)
    for unit in units:
        assert unit.operands[0].producer is unit.operands[1].producer
        assert unit.operands[0].operand is not unit.operands[1].operand
    assert units[1].operands[0].producer is units[0]
    assert units[2].operands[0].producer is units[1]
    sql = sql_of(dag)
    assert sql.count(" UNION ALL ") == 3
    facades = emit(target, "O_named_later", "two_facades")
    assert facades.status == "VERIFIED", blockers(facades)
    (unit,) = set_units(facades)
    assert unit.operands[0].producer is unit.operands[1].producer
    left, right = (o.use.original for o in unit.operands)
    assert left is not right and left.binding is not right.binding
    assert left.origin_path is not right.origin_path
    document = public(facades)
    assert [c["label"] for c in document["columns"]] == [
        "TextValue",
        "Key",
        "key",
        "FlagValue",
        "AmountValue",
        "RatioValue",
        "omitted",
    ]
    assert sql_of(facades).count(" UNION ALL ") == 1


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "variant,marker",
    (
        ("semi_except", "EXISTS ("),
        ("anti_except", "NOT EXISTS ("),
        ("semi_intersect", "EXISTS ("),
        ("anti_intersect", "NOT EXISTS ("),
    ),
)
def test_membership_wraps_the_complete_right_set_terminal(target, variant, marker):
    """R11/C09: EXISTS/NOT EXISTS read the SET CTE, never an operand or a scan."""
    outcome = emit(target, "S_set_membership", variant)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert f" WHERE {marker}" in sql
    position = sql.index(marker)
    read = re.search(r"FROM [\"`](p[0-9]+)[\"`]", sql[position:])
    assert read is not None
    body = cte_bodies(sql)[read.group(1)]
    assert " DISTINCT (SELECT " in body and body.startswith("(SELECT ")
    document = public(outcome)
    kinds = {
        r["kind"] for r in document["requirements"] if r["denominator"] == "generated"
    }
    assert {"complete_right_terminal", "membership", "set_row_equivalence"} <= kinds
    assert [c["label"] for c in document["columns"]] == ["a"]
    (unit,) = set_units(outcome)
    (join,) = [u for u in artifact_of(outcome).ast.units if hasattr(u, "membership")]
    assert join.inputs[1].producer is unit


@pytest.mark.parametrize("target", TARGETS)
def test_a_right_operand_substitution_is_rejected(target):
    """The right side bound to an operand's producer instead of the SET terminal
    is a terminal drift, and LIMIT 0 on the left never erases it."""
    outcome = emit(target, "S_set_membership", "semi_except")
    artifact = artifact_of(outcome)
    query = artifact.ast
    units = list(query.units)
    (unit,) = [u for u in units if type(u) is setting.SetBody]
    (join,) = [u for u in units if hasattr(u, "membership")]
    right = join.inputs[1]
    operand = unit.operands[0]
    shortcut = replace(
        join,
        inputs=(
            join.inputs[0],
            replace(
                right,
                producer=operand.producer,
                columns=tuple(
                    replace(column, terminal=read.terminal)
                    for column, read in zip(right.columns, operand.columns, strict=True)
                ),
            ),
        ),
    )
    units[units.index(join)] = shortcut
    assert not verify_row_query(artifact.request, replace(query, units=tuple(units)))


@pytest.mark.parametrize("target", TARGETS)
def test_fixed_literals_in_a_shared_operand_keep_one_occurrence(target):
    """I: one rendered producer, one slot, one server occurrence, two uses."""
    bind = emit(target, "S_set_literals", "bind")
    assert bind.status == "VERIFIED", blockers(bind)
    document = public(bind)
    assert len(document["fixed_values"]) == 1
    assert [u["slot"] for u in document["parameter_uses"]] == [0]
    assert [u["server_index"] for u in document["parameter_uses"]] == [1]
    sql = sql_of(bind)
    assert sql.count("$1" if target == "postgres" else "?") == 1
    assert sql.count(" UNION ALL ") == 1
    preserve = emit(target, "S_set_literals", "preserve")
    assert preserve.status == "VERIFIED", blockers(preserve)
    assert public(preserve)["parameter_uses"] == []
    assert sql_of(preserve).count("CAST(1 AS") == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "kind_changed",
        "quantifier_changed",
        "operands_reordered",
        "operand_dropped",
        "operand_duplicated",
        "column_positions_swapped",
        "right_operand_replaced_by_source",
        "realization_nullable_strengthened",
        "realization_tag_changed",
        "terminal_substituted",
        "final_flag_flipped",
    ],
)
def test_plan_ast_corruptions_are_rejected_independently(mutation):
    """Every mutation contradicts the retained plan; the verifier catches it."""
    outcome = emit("postgres", "S_set_positions", "two_column_except_all")
    artifact = artifact_of(outcome)
    request, query = artifact.request, artifact.ast
    units = list(query.units)
    (unit,) = [u for u in units if type(u) is setting.SetBody]
    first, second = unit.operands
    from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

    if mutation == "kind_changed":
        changed = replace(unit, kind=SetOperationKind.INTERSECT)
    elif mutation == "quantifier_changed":
        changed = replace(unit, quantifier=SetOperationQuantifier.DISTINCT)
    elif mutation == "operands_reordered":
        changed = replace(
            unit,
            operands=(replace(second, position=0), replace(first, position=1)),
        )
    elif mutation == "operand_dropped":
        changed = replace(unit, operands=(first,))
    elif mutation == "operand_duplicated":
        changed = replace(unit, operands=(first, second, second))
    elif mutation == "column_positions_swapped":
        a, b = unit.columns
        changed = replace(unit, columns=(replace(b, ordinal=0), replace(a, ordinal=1)))
    elif mutation == "right_operand_replaced_by_source":
        other = emit("postgres", "S_set_forms", "union_all")
        source_operand = [o for o in set_units(other)[0].operands if o.source is None][
            0
        ]
        changed = replace(
            unit, operands=(first, replace(second, columns=source_operand.columns))
        )
    elif mutation == "realization_nullable_strengthened":
        a, b = unit.columns
        changed = replace(
            unit,
            columns=(replace(a, realization=replace(a.realization, nullable=False)), b),
        )
    elif mutation == "realization_tag_changed":
        a, b = unit.columns
        changed = replace(
            unit, columns=(a, replace(b, realization=replace(b.realization, tag="Int")))
        )
    elif mutation == "terminal_substituted":
        a, b = unit.columns
        changed = replace(unit, columns=(replace(a, output=b.output), b))
    else:
        assert mutation == "final_flag_flipped"
        changed = replace(unit, final=False)
    units[units.index(unit)] = changed
    grafted = replace(query, units=tuple(units))
    assert not verify_row_query(request, grafted)
    checked = verify_project_sql_emission(replace(artifact, ast=grafted), request)
    assert not checked.verified and "plan_ast_correspondence" in checked.issues


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    [
        "operator_swapped",
        "quantifier_dropped",
        "parenthesis_removed",
        "operand_alias_swapped",
        "fold_flattened",
    ],
)
def test_rendered_byte_corruptions_are_rejected(target, mutation):
    """The byte verifier re-derives every SET token; substrings prove nothing."""
    outcome = emit(target, "S_set_nesting", "left_fold_except")
    artifact = artifact_of(outcome)
    rendered = artifact.rendered
    sql = rendered.sql.decode()
    q = Q[target]
    if mutation == "operator_swapped":
        corrupted = sql.replace(" EXCEPT DISTINCT ", " INTERSECT DISTINCT ", 1)
    elif mutation == "quantifier_dropped":
        corrupted = sql.replace(" EXCEPT DISTINCT ", " EXCEPT          ", 1)
    elif mutation == "parenthesis_removed":
        corrupted = sql.replace("((SELECT ", "( SELECT ", 1)
    elif mutation == "operand_alias_swapped":
        corrupted = sql.replace(f"{q}o0{q}", f"{q}o9{q}")
    else:
        assert mutation == "fold_flattened"
        final = final_statement(sql)
        flattened = (
            final[1:].replace(")) EXCEPT DISTINCT (", ") EXCEPT DISTINCT (", 1) + " "
        )
        corrupted = sql.replace(final, flattened, 1)
    assert corrupted != sql
    changed = replace(rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    checked = verify_project_sql_emission(
        replace(artifact, rendered=changed), artifact.request
    )
    assert not checked.verified and "sql_bytes_or_ranges" in checked.issues


@pytest.mark.parametrize("target", TARGETS)
def test_rendering_is_deterministic_and_publicly_decodable(target):
    outcome = emit(target, "S_set_forms", "except_all")
    artifact = artifact_of(outcome)
    again = render_join_sql(artifact.ast)
    assert again.sql == artifact.rendered.sql
    assert verify_row_bytes(artifact.ast, again)
    document = public(outcome)
    decoded = probe.decode_public(serialize_project_sql_emission(outcome))
    assert decoded["sql"] == document["sql"] == artifact.rendered.sql.decode()
    kinds = {
        r["kind"] for r in document["requirements"] if r["denominator"] == "generated"
    }
    assert SET_KINDS <= kinds
    for item in document["requirements"]:
        if item["denominator"] == "generated" and item["kind"] in SET_KINDS:
            assert item["rule"] == "R22"
            assert item["subject"]["kind"] in {"set_body", "set_operand", "set_column"}
        if item["denominator"] == "original" and item["kind"] == "set":
            assert item["rule"] == "R22"
    roles = [r["role"] for r in document["ranges"]]
    assert "set_operator" in roles and "set_operand_open" in roles
    assert roles.index("set_operand_open") < roles.index("set_operator")


def test_set_unit_repr_is_bounded():
    outcome = emit("postgres", "S_set_forms", "union_all")
    (unit,) = set_units(outcome)
    for value in (unit, unit.operands[0], unit.columns[0]):
        text = repr(value)
        assert len(text) < 512 and "ProjectSQL" not in text
