"""Unnest reads emitted as one ``JOIN LATERAL ROWS FROM`` right input.

Each Unnest here is grafted onto a real flat PostgreSQL emission by
``_pietto_sql_nested_unnest``: the parent's nested port is S08's Collect of a
real block read, and the JOIN, its inputs, ports, aliases and right binding use
are the flat JOIN's own. Every expected statement is written out.
"""

from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import _pietto_sql_nested_collect as collecting
import _pietto_sql_emission as public
import _pietto_execution_nested_oracle as oracle
import _pietto_sql_nested_unnest as unnesting_cases
from _pietto_plan_nested import nested_plan, sources
from pietto._project import project_sql_emission_joins as joining
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_unnest as unnesting
from pietto._project.project_sql_emission_ast import SQLSymbol
from pietto._project.project_sql_emission import emit_project_sql
from pietto._project.project_sql_emission_rendering import render_join_sql
from pietto._project.project_sql_emission_verification import (
    _unnest_problems,
    verify_row_bytes,
)
from pietto.ast_nodes import AuthoredJoinKind

pytestmark = pytest.mark.ci_workload("general-runtime")

RHS = '"public"."phase66 rhs é"'
LHS = '"public"."phase66 lhs é"'
# The closed Top-K let `top` with the ordinal its Collect reads, and the
# parent's WHERE reading it with `in`.
TOP = (
    f'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
    f'"s0"."order.id" AS "c1" FROM {RHS} AS "s0"), '
    '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
    'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1" FROM "p0" AS "t0" '
    'ORDER BY "t0"."c1" DESC LIMIT 2), '
)
WHERE = (
    '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
    f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
    'WHERE ("s1"."order.id" IN (SELECT "e0"."c0" FROM "p1" AS "e0"))), '
)
GROUP = (
    'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
    'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") '
    'AS "g0" ON TRUE'
)
# The parent's projection: its nested field b is the group c1, c1_0.
PARENT = (
    '"p3" ("c0", "c1", "c1_0") AS (SELECT "t4"."c0" AS "c0", '
    f'"g0"."n" AS "c1", "g0"."a0" AS "c1_0" FROM "p2" AS "t4" {GROUP}), '
)
# The Unnest JOIN: b is withheld, so the published labels are c0 and c2.
UNNEST = (
    '"p4" ("c0", "c2") AS (SELECT "m0"."c0" AS "c0", "m1"."c0" AS "c2" '
    'FROM "p3" AS "m0" {kind} JOIN LATERAL ROWS FROM '
    '(pg_catalog.unnest("m0"."c1_0")) AS "m1" ("c0"){on}) '
)
FINAL = 'SELECT "t0"."c0" AS "a", "t0"."c2" AS "v" FROM "p4" AS "t0"'
ON = ' ON ("m1"."c0" > CAST(1 AS pg_catalog.int8))'
EXPECTED = {
    "cross": TOP + WHERE + PARENT + UNNEST.format(kind="CROSS", on="") + FINAL,
    "inner_on": TOP + WHERE + PARENT + UNNEST.format(kind="INNER", on=ON) + FINAL,
    "left_on": TOP + WHERE + PARENT + UNNEST.format(kind="LEFT", on=ON) + FINAL,
    # The nested field first: the first published item has no separator.
    "left_true_first": (
        TOP + WHERE + '"p3" ("c0", "c0_0", "c1") AS (SELECT "g0"."n" AS "c0", '
        '"g0"."a0" AS "c0_0", "t4"."c0" AS "c1" FROM "p2" AS "t4" '
        f"{GROUP}), "
        '"p4" ("c1", "c2") AS (SELECT "m0"."c1" AS "c1", "m1"."c0" AS "c2" '
        'FROM "p3" AS "m0" LEFT JOIN LATERAL ROWS FROM '
        '(pg_catalog.unnest("m0"."c0_0")) AS "m1" ("c0") '
        "ON CAST(TRUE AS pg_catalog.bool)) "
        'SELECT "t0"."c1" AS "a", "t0"."c2" AS "v" FROM "p4" AS "t0"'
    ),
    # Two children: one call per array, zipped by position in one ROWS FROM.
    "pair": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1", "s0"."order.id" AS "c2" '
        f'FROM {RHS} AS "s0"), '
        '"p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t0"."c2" DESC) AS "c2" '
        'FROM "p0" AS "t0" ORDER BY "t0"."c2" DESC LIMIT 2), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
        'WHERE EXISTS (SELECT 1 FROM "p1" AS "e0")), '
        '"p3" ("c0", "c1", "c1_0", "c1_1") AS (SELECT "t4"."c0" AS "c0", '
        '"g0"."n" AS "c1", "g0"."a0" AS "c1_0", "g0"."a1" AS "c1_1" '
        'FROM "p2" AS "t4" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c2") AS "a0", '
        'ARRAY_AGG("e0"."c1" ORDER BY "e0"."c2") AS "a1" FROM "p1" AS "e0") '
        'AS "g0" ON TRUE), '
        '"p4" ("c0", "c2", "c3") AS (SELECT "m0"."c0" AS "c0", '
        '"m1"."c0" AS "c2", "m1"."c1" AS "c3" FROM "p3" AS "m0" '
        'CROSS JOIN LATERAL ROWS FROM (pg_catalog.unnest("m0"."c1_0"), '
        'pg_catalog.unnest("m0"."c1_1")) AS "m1" ("c0", "c1")) ' + FINAL
    ),
    # The parent's ORDER BY and LIMIT: the JOIN reads its result body, which
    # carries the whole group.
    "ordered_parent": (
        TOP + WHERE + '"p3" ("c0", "c1", "c1_0", "c2") AS (SELECT "t4"."c0" AS "c0", '
        '"g0"."n" AS "c1", "g0"."a0" AS "c1_0", "t4"."c0" AS "c2" '
        f'FROM "p2" AS "t4" {GROUP}), '
        '"p4" ("c0", "c1", "c1_0") AS (SELECT "t2"."c0" AS "c0", '
        '"t2"."c1" AS "c1", "t2"."c1_0" AS "c1_0" FROM "p3" AS "t2" '
        'ORDER BY "t2"."c2" ASC LIMIT 3), '
        '"p5" ("c0", "c2") AS (SELECT "m0"."c0" AS "c0", "m1"."c0" AS "c2" '
        'FROM "p4" AS "m0" CROSS JOIN LATERAL ROWS FROM '
        '(pg_catalog.unnest("m0"."c1_0")) AS "m1" ("c0")) '
        'SELECT "t0"."c0" AS "a", "t0"."c2" AS "v" FROM "p5" AS "t0"'
    ),
    # A later scalar JOIN reads the Unnest JOIN; b stays withheld in both.
    "later_join": (
        TOP
        + WHERE
        + PARENT
        + UNNEST.format(kind="CROSS", on="")[:-1]
        + ', "p5" ("c0", "c2", "c3", "c4") AS (SELECT "m2"."c0" AS "c0", '
        '"m2"."c2" AS "c2", "m3"."order.id" AS "c3", "m3"."key value" AS "c4" '
        f'FROM "p4" AS "m2" LEFT JOIN {RHS} AS "m3" '
        'ON ("m2"."c0" = "m3"."order.id")) '
        'SELECT "t0"."c0" AS "a", "t0"."c2" AS "v", "t0"."c4" AS "w" '
        'FROM "p5" AS "t0"'
    ),
    # Sibling groups: the Unnest reads b's group alone; both stay withheld.
    "siblings": (
        TOP + '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."order.id" AS "c1" FROM {RHS} AS "s1"), '
        '"p3" ("c0", "c1") AS (SELECT "t2"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t2"."c1" ASC) AS "c1" FROM "p2" AS "t2" '
        'ORDER BY "t2"."c1" ASC), '
        '"p4" ("c0", "c1", "c1_0", "c2", "c2_0") AS (SELECT '
        '"s2"."order.id" AS "c0", "g0"."n" AS "c1", "g0"."a0" AS "c1_0", '
        '"g1"."n" AS "c2", "g1"."a0" AS "c2_0" '
        f'FROM {LHS} AS "s2" {GROUP} '
        'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e1"."c0" ORDER BY "e1"."c1") AS "a0" FROM "p3" AS "e1") '
        'AS "g1" ON TRUE), '
        '"p5" ("c0", "c3") AS (SELECT "m0"."c0" AS "c0", "m1"."c0" AS "c3" '
        'FROM "p4" AS "m0" CROSS JOIN LATERAL ROWS FROM '
        '(pg_catalog.unnest("m0"."c1_0")) AS "m1" ("c0")) '
        'SELECT "t0"."c0" AS "a", "t0"."c3" AS "v" FROM "p5" AS "t0"'
    ),
    # The second child reads the query parameter $1: its value is fixed only
    # at binding, and the Unnest reads it like any other child.
    "parameter": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."order.id" AS "c0", '
        '("s0"."order.id" + CAST($1 AS pg_catalog.int8)) AS "c1", '
        f'"s0"."order.id" AS "c2" FROM {RHS} AS "s0"), '
        '"p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t0"."c2" DESC) AS "c2" '
        'FROM "p0" AS "t0" ORDER BY "t0"."c2" DESC LIMIT 2), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
        'WHERE EXISTS (SELECT 1 FROM "p1" AS "e0")), '
        '"p3" ("c0", "c1", "c1_0", "c1_1") AS (SELECT "t4"."c0" AS "c0", '
        '"g0"."n" AS "c1", "g0"."a0" AS "c1_0", "g0"."a1" AS "c1_1" '
        'FROM "p2" AS "t4" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c2") AS "a0", '
        'ARRAY_AGG("e0"."c1" ORDER BY "e0"."c2") AS "a1" FROM "p1" AS "e0") '
        'AS "g0" ON TRUE), '
        '"p4" ("c0", "c2", "c3") AS (SELECT "m0"."c0" AS "c0", '
        '"m1"."c0" AS "c2", "m1"."c1" AS "c3" FROM "p3" AS "m0" '
        'CROSS JOIN LATERAL ROWS FROM (pg_catalog.unnest("m0"."c1_0"), '
        'pg_catalog.unnest("m0"."c1_1")) AS "m1" ("c0", "c1")) ' + FINAL
    ),
}


@pytest.mark.parametrize("shape", ("unnest_cross", "unnest_inner", "unnest_left"))
def test_real_source_unnest_emits_the_admitted_flat_postgres_path(
    tmp_path: Path, shape: str
) -> None:
    """The source plan, rather than a graft, owns S13 admission and emission."""
    outcome = emit_project_sql(
        nested_plan(tmp_path / shape, sources(shape)),
        collecting.contract("postgres").encode(),
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None, [
        (blocker.code, blocker.detail) for blocker in outcome.blockers
    ]
    sql = outcome.artifact.rendered.sql.decode()
    assert sql.count("JOIN LATERAL ROWS FROM (") == 1
    assert sql.count("pg_catalog.unnest(") == 2
    assert "ARRAY_AGG(" in sql and "ORDINALITY" not in sql


def _build(tmp_path: Path, case: str):
    return unnesting_cases.build(tmp_path / case, case)


def _rows(grafted):
    return grafted.unit.inputs[1].producer


def test_unnest_nodes_are_private_frozen_values() -> None:
    assert unnesting.__all__ == ()
    for node in (
        unnesting.NestedRead,
        unnesting.UnnestColumn,
        unnesting.UnnestRows,
        unnesting.WithheldPort,
    ):
        params = getattr(node, "__dataclass_params__")
        assert (params.frozen, params.eq) == (True, False)
        assert "__slots__" in vars(node)
    assert unnesting.FUNCTION == "pg_catalog.unnest"
    assert unnesting.KINDS == {
        AuthoredJoinKind.CROSS,
        AuthoredJoinKind.INNER,
        AuthoredJoinKind.LEFT,
    }


@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_unnest_reads_render_one_rows_from_right_input(
    tmp_path: Path, case: str
) -> None:
    grafted = _build(tmp_path / "first", case)
    rendered = grafted.render()
    sql = rendered.sql.decode()
    assert sql == EXPECTED[case]
    # Results are bound first, so a failing assertion never renders the plan.
    verified = verify_row_bytes(grafted.query, rendered)
    problems = _unnest_problems(grafted.request, grafted.unit, grafted.unnest)
    assert verified and problems == ()
    # The record carries no definition or semantic fact: emission reads
    # neither.
    assert grafted.unnest.definition is None and grafted.unnest.semantic is None
    # One single-argument call per child; no ordinality and no COALESCE.
    children = len(grafted.unnest.outputs)
    assert sql.count("pg_catalog.unnest(") == children
    assert sql.count("ROWS FROM (") == 1
    assert "ORDINALITY" not in sql and "COALESCE" not in sql
    again = _build(tmp_path / "second", case)
    assert again.render().sql == rendered.sql


def test_nested_ports_stay_withheld_through_a_later_join(tmp_path: Path) -> None:
    grafted = _build(tmp_path, "later_join")
    first, later = (u for u in grafted.query.units if type(u) is joining.JoinBody)
    assert first is grafted.unit
    for unit in (first, later):
        held = unit.columns[1]
        assert type(held) is unnesting.WithheldPort
        assert held.position == 1
        assert held.port.ref is unit.join.outputs[1]
        assert all(
            type(c) is joining.JoinColumn and c.label == f"c{i}"
            for i, c in enumerate(unit.columns)
            if i != 1
        )
    assert [s.name for s in first.cte_columns] == ["c0", "c2"]
    assert [s.name for s in later.cte_columns] == ["c0", "c2", "c3", "c4"]
    assert later.inputs[0].producer is first
    siblings = _build(tmp_path / "siblings", "siblings")
    held = [type(c) is unnesting.WithheldPort for c in siblings.unit.columns]
    assert held == [False, True, True, False]


@pytest.mark.parametrize(
    ("case", "nullable"),
    (
        ("cross", ((False, False),)),
        ("inner_on", ((False, False),)),
        # LEFT keeps the child's pre-match realization; its output gains NULL.
        ("left_on", ((False, True),)),
        ("pair", ((False, False), (True, True))),
    ),
)
def test_each_element_keeps_its_child_terminal_realization(
    tmp_path: Path, case: str, nullable
) -> None:
    grafted = _build(tmp_path, case)
    left, right = grafted.unit.inputs
    (lateral,) = grafted.unit.inputs[0].producer.laterals
    children = [c.column.realization for c in lateral.target.producer.columns]
    split = len(left.ports)
    for j, (child, element, read) in enumerate(
        zip(children, _rows(grafted).columns, right.columns, strict=True)
    ):
        output = grafted.unit.columns[split + j].column.realization
        assert child.tag == "Int" and child.storage == {"kind": "pg_int8"}
        for realization in (element.column.realization, read.realization):
            assert (
                realization.tag,
                realization.storage,
                realization.nullable,
                realization.domain,
                realization.proven_int_range,
            ) == (
                child.tag,
                child.storage,
                child.nullable,
                child.domain,
                child.proven_int_range,
            )
        assert (output.storage, output.domain) == (child.storage, child.domain)
        assert (child.nullable, output.nullable) == nullable[j]


def test_a_child_fixed_at_binding_is_read_by_the_pre_match_port_law(
    tmp_path: Path,
) -> None:
    grafted = _build(tmp_path, "parameter")
    _, right = grafted.unit.inputs
    (lateral,) = grafted.unit.inputs[0].producer.laterals
    child = lateral.target.producer.columns[1].column.realization
    element = _rows(grafted).columns[1].column.realization
    read = right.columns[1].realization
    # The element is the child's own realization, marks included.
    deferred = (True, "int_range_representable")
    assert (child.binding, child.obligation) == deferred
    assert (element.binding, element.obligation) == deferred
    # The right input reads it as every JOIN input reads its producer: the
    # pre-match port realization, which carries no binding mark.
    assert (read.binding, read.obligation) == (False, None)
    assert (read.tag, read.storage, read.nullable, read.domain) == (
        child.tag,
        child.storage,
        child.nullable,
        child.domain,
    )
    problems = _unnest_problems(grafted.request, grafted.unit, grafted.unnest)
    assert problems == ()


def test_node_count_counts_the_frame_and_four_per_child(tmp_path: Path) -> None:
    for case, children in (("cross", 1), ("pair", 2)):
        grafted = _build(tmp_path, case)
        sql = grafted.render().sql.decode()
        # ROWS FROM's open and close, alias and column list; per child the
        # call, its scope, its array and its column alias.
        calls = sql.count("pg_catalog.unnest(")
        assert calls == children
        assert unnesting.node_count(_rows(grafted)) == 4 + 4 * calls


def _with_rows(grafted, unit=None, **changes):
    unit = grafted.unit if unit is None else unit
    left, right = unit.inputs
    item = replace(right.producer, **changes)
    return replace(unit, inputs=(left, replace(right, producer=item)))


def _with_record(grafted, **changes):
    """The record changed as the plan would carry it: the Unnest rows read
    the changed record too."""
    record = replace(grafted.unnest, **changes)
    return _with_rows(grafted, unnest=record), record


def _with_element(grafted, index, **changes):
    item = _rows(grafted)
    element = item.columns[index]
    changed = replace(element, column=replace(element.column, **changes))
    columns = tuple(changed if c is element else c for c in item.columns)
    return _with_rows(grafted, columns=columns)


def _with_left(grafted, index, entry):
    left, right = grafted.unit.inputs
    columns = tuple(entry if i == index else c for i, c in enumerate(left.columns))
    return replace(grafted.unit, inputs=(replace(left, columns=columns), right))


def _with_published(grafted, index, column):
    unit = grafted.unit
    columns = tuple(column if i == index else c for i, c in enumerate(unit.columns))
    return replace(unit, columns=columns)


def _realization(grafted, **changes):
    element = _rows(grafted).columns[0].column
    return _with_element(
        grafted, 0, realization=replace(element.realization, **changes)
    )


# Each corruption: the stand-in it lands in and the one rule it breaks.
CORRUPTIONS = {
    "mysql_family": ("cross", "unnest_target"),
    "later_join_record": ("later_join", "unnest_join"),
    "right_join_record": ("cross", "unnest_join"),
    "full_join_record": ("cross", "unnest_join"),
    "semi_membership": ("cross", "unnest_join"),
    "flat_right_input": ("cross", "unnest_input"),
    "other_record_in_rows": ("cross", "unnest_input"),
    "input_is_left": ("cross", "unnest_input"),
    "scope_is_right_alias": ("cross", "unnest_scope"),
    "scope_is_third_alias": ("cross", "unnest_scope"),
    "source_is_scalar": ("cross", "unnest_source"),
    "sibling_group": ("siblings", "unnest_source"),
    "other_collect": ("cross", "unnest_source"),
    "arrays_swapped": ("pair", "unnest_arrays"),
    "array_dropped": ("pair", "unnest_arrays"),
    "array_duplicated": ("pair", "unnest_arrays"),
    "count_as_array": ("cross", "unnest_arrays"),
    "element_renamed": ("cross", "unnest_columns"),
    "element_dropped": ("pair", "unnest_columns"),
    "element_int4": ("cross", "unnest_realization"),
    "element_nullable": ("cross", "unnest_realization"),
    "element_domain": ("cross", "unnest_realization"),
    "read_keeps_binding": ("parameter", "unnest_realization"),
    "read_int4": ("cross", "unnest_realization"),
    "outputs_reordered": ("pair", "unnest_outputs"),
    "outputs_truncated": ("pair", "unnest_outputs"),
    "scalar_withheld": ("cross", "unnest_withheld"),
    "nested_published": ("cross", "unnest_withheld"),
    "withheld_other_port": ("cross", "unnest_withheld"),
}


def _corrupted(tmp_path: Path, corruption: str):
    """One valid-looking Unnest change: (request, unit, record)."""
    case, _ = CORRUPTIONS[corruption]
    grafted = _build(tmp_path, case)
    request, unit, record = grafted.request, grafted.unit, grafted.unnest
    left, right = unit.inputs
    item = right.producer
    flat = next(u for u in grafted.flat.ast.units if type(u) is joining.JoinBody)
    if corruption == "mysql_family":
        request = SimpleNamespace(family="mysql", plan=request.plan)
    elif corruption == "later_join_record":
        later = next(
            u
            for u in grafted.query.units
            if type(u) is joining.JoinBody and u is not unit
        )
        unit = replace(unit, join=later.join)
    elif corruption in ("right_join_record", "full_join_record"):
        other = unnesting_cases.other_join(
            tmp_path / "other", corruption.split("_", 1)[0]
        )
        assert other.kind in (AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL)
        unit, record = _with_record(grafted, join=other.ref)
        unit = replace(unit, join=other)
    elif corruption == "semi_membership":
        unit = replace(unit, membership="exists", sentinel=unit.join.ref)
    elif corruption == "flat_right_input":
        unit = replace(unit, inputs=(left, flat.inputs[1]))
    elif corruption == "other_record_in_rows":
        unit = _with_rows(grafted, unnest=replace(record))
    elif corruption == "input_is_left":
        unit, record = _with_record(grafted, input=left.original.ref)
    elif corruption == "scope_is_right_alias":
        unit = _with_rows(grafted, scope=right.symbol)
    elif corruption == "scope_is_third_alias":
        unit = _with_rows(grafted, scope=SQLSymbol(0, left.original.ref, "m9"))
    elif corruption == "source_is_scalar":
        unit, record = _with_record(grafted, source=left.ports[0])
    elif corruption == "sibling_group":
        sibling = left.producer.columns[2]
        unit = _with_left(grafted, 1, replace(left.columns[1], group=sibling))
    elif corruption == "other_collect":
        unit, record = _with_record(grafted, collect=collecting._CollectRef(9))
    elif corruption == "arrays_swapped":
        unit = _with_rows(grafted, arrays=item.arrays[::-1])
    elif corruption == "array_dropped":
        unit = _with_rows(grafted, arrays=item.arrays[:1])
    elif corruption == "array_duplicated":
        unit = _with_rows(grafted, arrays=(item.arrays[0], item.arrays[0]))
    elif corruption == "count_as_array":
        unit = _with_rows(grafted, arrays=(left.columns[1].count,))
    elif corruption == "element_renamed":
        unit = _with_element(grafted, 0, name="x")
    elif corruption == "element_dropped":
        unit = _with_rows(grafted, columns=item.columns[:1])
    elif corruption == "element_int4":
        unit = _realization(grafted, storage={"kind": "pg_int4"})
    elif corruption == "element_nullable":
        unit = _realization(grafted, nullable=True)
    elif corruption == "element_domain":
        unit = _realization(
            grafted, domain={"kind": "int_range", "min": "0", "max": "1"}
        )
    elif corruption in ("read_keeps_binding", "read_int4"):
        read = right.columns[-1]
        changed = (
            replace(
                read.realization, binding=True, obligation="int_range_representable"
            )
            if corruption == "read_keeps_binding"
            else replace(read.realization, storage={"kind": "pg_int4"})
        )
        columns = (*right.columns[:-1], replace(read, realization=changed))
        unit = replace(unit, inputs=(left, replace(right, columns=columns)))
    elif corruption == "outputs_reordered":
        unit, record = _with_record(grafted, outputs=record.outputs[::-1])
    elif corruption == "outputs_truncated":
        unit, record = _with_record(grafted, outputs=record.outputs[:1])
    elif corruption == "scalar_withheld":
        unit = _with_published(
            grafted, 0, unnesting.WithheldPort(0, unit.columns[0].port)
        )
        unit = replace(unit, cte_columns=unit.cte_columns[1:])
    elif corruption == "nested_published":
        unit = _with_published(grafted, 1, flat.columns[1])
        unit = replace(unit, cte_columns=flat.cte_columns)
    else:
        assert corruption == "withheld_other_port"
        unit = _with_published(
            grafted, 1, unnesting.WithheldPort(1, unit.columns[0].port)
        )
    return request, unit, record


@pytest.mark.parametrize("corruption", sorted(CORRUPTIONS))
def test_every_unnest_corruption_breaks_one_named_rule(
    tmp_path: Path, corruption: str
) -> None:
    _, expected = CORRUPTIONS[corruption]
    request, unit, record = _corrupted(tmp_path, corruption)
    problems = _unnest_problems(request, unit, record)
    assert problems == (expected,)


BYTE_CORRUPTIONS = {
    "unqualified": ("cross", "pg_catalog.unnest(", "unnest("),
    "two_arguments": (
        "pair",
        'pg_catalog.unnest("m0"."c1_0"), pg_catalog.unnest("m0"."c1_1")',
        'pg_catalog.unnest("m0"."c1_0", "m0"."c1_1")',
    ),
    "ordinality": ("cross", ' AS "m1" ("c0")', ' WITH ORDINALITY AS "m1" ("c0")'),
    "no_lateral": ("cross", " JOIN LATERAL ROWS FROM (", " JOIN ROWS FROM ("),
    "no_column_list": ("cross", ' AS "m1" ("c0")', ' AS "m1"'),
    "renamed_column": ("cross", ' AS "m1" ("c0")', ' AS "m1" ("v")'),
    "array_renamed": ("cross", '"m0"."c1_0"))', '"m0"."c1"))'),
    "withheld_selected": (
        "cross",
        '"m0"."c0" AS "c0", "m1"."c0" AS "c2"',
        '"m0"."c0" AS "c0", "m0"."c1" AS "c1", "m1"."c0" AS "c2"',
    ),
    "withheld_header": ("cross", '"p4" ("c0", "c2")', '"p4" ("c0", "c1", "c2")'),
    "left_as_cross": ("left_on", " LEFT JOIN LATERAL ROWS", " CROSS JOIN LATERAL ROWS"),
    "left_as_inner": ("left_on", " LEFT JOIN LATERAL ROWS", " INNER JOIN LATERAL ROWS"),
    "cross_as_left": ("cross", " CROSS JOIN LATERAL ROWS", " LEFT JOIN LATERAL ROWS"),
    # ON moved out of the LEFT JOIN.
    "on_as_where": ("left_on", '("c0") ON (', '("c0") WHERE ('),
}


@pytest.mark.parametrize("corruption", sorted(BYTE_CORRUPTIONS))
def test_unnest_bytes_that_differ_from_their_nodes_are_refused(
    tmp_path: Path, corruption: str
) -> None:
    case, before, after = BYTE_CORRUPTIONS[corruption]
    grafted = _build(tmp_path, case)
    rendered = grafted.render()
    sql = rendered.sql.decode()
    assert sql.count(before) == 1
    changed = sql.replace(before, after).encode("utf-8")
    verified = verify_row_bytes(grafted.query, replace(rendered, sql=changed))
    assert not verified


def test_an_unnest_outside_its_join_shape_is_never_verified(tmp_path: Path) -> None:
    """Bytes rendered faithfully from an Unnest node in a JOIN shape it never
    has are still refused: RIGHT or FULL, a membership wrapper, or the left."""
    grafted = _build(tmp_path, "left_on")
    unit = grafted.unit
    left, right = unit.inputs
    changes = {
        "RIGHT JOIN LATERAL ROWS FROM": replace(
            unit, join=replace(unit.join, kind=AuthoredJoinKind.RIGHT)
        ),
        "FULL JOIN LATERAL ROWS FROM": replace(
            unit, join=replace(unit.join, kind=AuthoredJoinKind.FULL)
        ),
        "WHERE EXISTS (SELECT 1 FROM LATERAL ROWS FROM": replace(
            unit, membership="exists", sentinel=unit.join.ref
        ),
        'FROM LATERAL ROWS FROM (pg_catalog.unnest("m0"."c1_0")) AS "m0"': replace(
            unit, inputs=(replace(left, producer=right.producer), right)
        ),
    }
    for spelling, changed in changes.items():
        units = tuple(changed if u is unit else u for u in grafted.query.units)
        query = replace(grafted.query, units=units)
        rendered = render_join_sql(query)
        assert spelling in rendered.sql.decode()
        verified = verify_row_bytes(query, rendered)
        assert not verified


def test_realize_unnest_refuses_every_drift(tmp_path: Path) -> None:
    grafted = _build(tmp_path / "cross", "cross")
    left, right = grafted.unit.inputs
    terminals = tuple(b.terminal.ref for b in right.use.bindings)
    record = grafted.unnest

    def realize(changed=record, *, kind=AuthoredJoinKind.CROSS, entries=None):
        reading = left if entries is None else replace(left, columns=entries)
        return unnesting.realize_unnest(
            changed, reading, kind=kind, terminals=terminals
        )

    group = left.columns[1].group
    count_only, problem = unnesting.nested_read(
        replace(group, carriers=group.carriers[:1]),
        position=1,
        port=left.columns[1].port,
        scope=left.symbol,
    )
    assert problem is None and count_only is not None
    assert (count_only.arrays, len(count_only.children)) == ((), 1)
    refused = {
        "unnest_join_kind_drift": (
            realize(kind=AuthoredJoinKind.RIGHT),
            realize(kind=AuthoredJoinKind.FULL),
            realize(kind=AuthoredJoinKind.SEMI),
        ),
        "unnest_source_not_in_left_input": (
            realize(replace(record, source=right.ports[0])),
        ),
        "unnest_source_not_nested": (realize(replace(record, source=left.ports[0])),),
        "unnest_collect_drift": (
            realize(replace(record, collect=collecting._CollectRef(9))),
        ),
        "unnest_children_drift": (
            realize(replace(record, outputs=())),
            realize(replace(record, outputs=record.outputs * 2)),
            realize(entries=(left.columns[0], count_only)),
        ),
    }
    for detail, outcomes in refused.items():
        for built, problem in outcomes:
            assert built is None
            assert problem == ("PIE-B1001", detail, record.ref, None)
    built, problem = realize()
    assert problem is None and type(built) is unnesting.UnnestRows
    assert built.scope is left.symbol and built.arrays == ("c1_0",)


def test_nested_read_refuses_a_column_without_a_group(tmp_path: Path) -> None:
    grafted = _build(tmp_path, "ordered_parent")
    left = grafted.unit.inputs[0]
    producer = left.producer
    assert type(producer) is resulting.RowResultBody
    port = left.columns[1].port
    built, problem = unnesting.nested_read(
        producer.columns[0], position=0, port=port, scope=left.symbol
    )
    assert built is None
    assert problem == ("PIE-B1001", "nested_read_without_group", port.ref, None)
    # A result group carries the projection's Collect group under its labels.
    read = left.columns[1]
    assert type(read.group) is resulting.ResultGroupColumn
    assert (read.count, read.arrays) == ("c1", ("c1_0",))


@pytest.fixture(scope="module")
def public_unnest_documents(tmp_path_factory):
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    root = tmp_path_factory.mktemp("public-unnest")
    result = {}
    for name in ("U1_cross", "U2_inner_true", "U4_left_true"):
        program = oracle.program(name)
        outcome = collecting.wired_outcome(
            root / name, dict(program.files), collecting.oracle_contract()
        )
        assert outcome.status == "VERIFIED", [
            (b.code, b.detail) for b in outcome.blockers
        ]
        result[name] = json.loads(serialize_project_sql_emission(outcome))
    return result


@pytest.mark.parametrize("name", ("U1_cross", "U2_inner_true", "U4_left_true"))
def test_real_unnest_public_document_is_independently_decoded(
    public_unnest_documents, name
):
    document = public_unnest_documents[name]
    assert public.decode_public(json.dumps(document).encode()) == document
    assert [column["label"] for column in document["columns"]] == [
        "id",
        "v",
        "k",
        "flag",
        "note",
    ]
    assert all(
        column["logical_type"]["kind"] == "builtin" for column in document["columns"]
    )


@pytest.mark.parametrize("name", ("U1_cross", "U2_inner_true", "U4_left_true"))
@pytest.mark.parametrize(
    "damage",
    ("array", "scope", "function", "child_export", "hidden_header", "final_origin"),
)
def test_real_unnest_public_reader_rejects_correspondence_damage(
    public_unnest_documents, name, damage
):
    original = public_unnest_documents[name]
    document = deepcopy(original)
    if damage in {"array", "scope", "function"}:
        role = {
            "array": "unnest_array",
            "scope": "unnest_scope",
            "function": "unnest_function",
        }[damage]
        interval = next(item for item in document["ranges"] if item["role"] == role)
        raw = document["sql"].encode()
        old = raw[interval["start"] : interval["end"]]
        new = {"array": b'"c1_1"', "scope": b'"m1"', "function": b"pg_catalog.abs___("}[
            damage
        ]
        assert len(old) == len(new)
        document["sql"] = (
            raw[: interval["start"]] + new + raw[interval["end"] :]
        ).decode()
    elif damage == "child_export":
        interval = next(
            item for item in document["ranges"] if item["role"] == "unnest_column"
        )
        interval["subject"] = {"kind": "export", "position": 1}
    elif damage == "hidden_header":
        interval = next(
            item
            for item in document["ranges"]
            if item["role"] == "terminal_column"
            and item["subject"]["kind"] == "join_port"
        )
        interval["subject"] = {
            "kind": "join_port",
            "position": interval["subject"]["position"] + 1,
        }
    else:
        document["columns"][1]["correspondence"]["computed_origin"]["field"] = 0
    assert document != original
    with pytest.raises(ValueError):
        public.decode_public(json.dumps(document).encode())


def test_unnest_left_public_reader_requires_null_extension(public_unnest_documents):
    document = deepcopy(public_unnest_documents["U4_left_true"])
    removed = next(
        item
        for item in document["requirements"]
        if item["denominator"] == "generated" and item["kind"] == "null_extension"
    )
    document["requirements"].remove(removed)
    generated = [
        item for item in document["requirements"] if item["denominator"] == "generated"
    ]
    for ordinal, item in enumerate(generated):
        if item["subject"] == {"kind": item["kind"], "position": item["ordinal"]}:
            item["subject"]["position"] = ordinal
        item["ordinal"] = ordinal
    with pytest.raises(ValueError):
        public.decode_public(json.dumps(document).encode())


def test_real_unnest_refuses_an_extra_collection_inventory(tmp_path):
    program = oracle.program("U1_cross")
    files = dict(program.files)
    text = files["main.pietto"]
    start = text.index("    let recent:")
    stop = text.index("    from customers", start)
    extra = text[start:stop].replace("let recent:", "let extra:", 1)
    text = text[:stop] + extra + text[stop:]
    text = text.replace(
        "        recent = collect recent\n",
        "        recent = collect recent\n        extra = collect extra\n",
        1,
    )
    files["main.pietto"] = text
    outcome = collecting.wired_outcome(
        tmp_path / "extra", files, collecting.oracle_contract()
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert any(
        blocker.detail == "unnest_not_admitted_on_target"
        for blocker in outcome.blockers
    )
