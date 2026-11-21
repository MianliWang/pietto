"""Admitted row expressions, stage bodies and finite target range realization."""

from __future__ import annotations

from collections import Counter
from contextvars import ContextVar
from dataclasses import dataclass, replace
import functools
import json
import math
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_paired as pairing
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_emission_portable_schema import (
    MYSQL_PACKET_FLOOR_CHARACTERS,
)
from pietto.ast_nodes import CallExpr, NameExpr, RelationScalarExpr
from pietto.semantic.model import TypeKind, ValueTypeKind, EffectiveNullability
from pietto.ir.model import SymbolNamespace

__all__: tuple[str, ...] = ()

ARITHMETIC = ("+", "-", "*", "/", "%")
LOGICAL = ("and", "or")
COMPARISONS = {
    "==": " = ",
    "!=": " <> ",
    "<": " < ",
    "<=": " <= ",
    ">": " > ",
    ">=": " >= ",
    "like": " LIKE ",
    "not like": " NOT LIKE ",
}
COMPARABLE = ("Int", "Text", "Decimal", "Timestamp", "Date", "Float")
# One carrier's values order by their exact civil instant or day.
TEMPORAL = ("Timestamp", "Date")
# Rule two (D77.37, owner 2026-11-13T00:20Z): a MySQL statement, or a JOIN
# `on` `same_value` statement of a cell (nullsafe_join_cell), that stays
# refused reports main's whole blocker list. While this is set, emission
# derives as main does: every Phase77 cell is shut, and so is the R01
# refusal of mysql_float_memberships, which as_main_if_refused keeps for a
# statement main emits.
AS_MAIN = ContextVar("as_main", default=False)


def as_main_if_refused(request, derive, refused):
    """``derive()``; when ``refused`` holds of it for a MySQL statement or a
    null-safe JOIN cell, ``derive()`` once more as main (AS_MAIN), unless it
    already is. When main does not refuse it and its plan holds an R01 Float
    membership (mysql_float_memberships), the first derivation stands: that
    refusal."""

    result = derive()
    if (
        AS_MAIN.get()
        or not refused(result)
        or request.family != "mysql"
        and nullsafe_join_cell(request) is None
    ):
        return result
    token = AS_MAIN.set(True)
    try:
        main = derive()
    finally:
        AS_MAIN.reset(token)
    if not refused(main) and mysql_float_memberships(request.plan):
        return result
    return main


FINITE_FLOAT = {"kind": "finite_float", "format": "binary64"}
# percent_rank / cume_dist results (windows.py): finite, in [0, 1].
DISTRIBUTION_FLOAT = {"kind": "float64"}


def float_carrier(realization, family=None, *, distribution=False) -> bool:
    """One reviewed finite binary64 carrier; with a family, that family's storage.

    A Float compares, groups and deduplicates by Python float equality, so
    -0.0 and 0.0 are one value. ``distribution`` also admits a window
    distribution result, for comparisons only.
    """
    storages = (
        ({"kind": "pg_float8"}, {"kind": "my_double"})
        if family is None
        else ({"kind": "pg_float8" if family == "postgres" else "my_double"},)
    )
    domains = (FINITE_FLOAT, DISTRIBUTION_FLOAT) if distribution else (FINITE_FLOAT,)
    return (
        realization.tag == "Float"
        and realization.storage in storages
        and realization.domain in domains
    )


# SQL IN is only emitted for carriers with an established equality operation.
# Other same-canonical semantic values (for example Json or Bytes) stay at the
# project boundary until their physical equality proof is reviewed.
MEMBERSHIP_TYPES = ("Bool", "Int", "Float", "Decimal", "Text", "Timestamp", "UUID")
INT_WIDTHS = {
    "pg_int2": 16,
    "pg_int4": 32,
    "pg_int8": 64,
    "my_smallint": 16,
    "my_int": 32,
    "my_bigint": 64,
    "my_signed_int": 64,
}
BOOL_RESULT = {"postgres": "pg_bool", "mysql": "my_signed_bool"}
NULLABILITY = {
    EffectiveNullability.NON_NULL: False,
    EffectiveNullability.NULLABLE: True,
    EffectiveNullability.UNKNOWN: "unknown",
}


@dataclass(frozen=True, slots=True, eq=False)
class Realization:
    """One value's checked logical tag, physical storage and exact value domain.

    ``binding`` marks a value whose exact domain is fixed only when its query
    parameters are bound; the template keeps the declared carrier (the full
    signed range for Int, an unknown width for Text). ``obligation`` names the
    check this node defers to every binding.
    """

    tag: str
    storage: dict[str, Any]
    nullable: bool | str
    domain: dict[str, Any]
    proven_int_range: tuple[int, int] | None = None
    binding: bool = False
    obligation: str | None = None


INT_RANGE_OBLIGATION = "int_range_representable"
# Phase77 S01/S02: the MySQL project cells whose checked signed 64-bit outcome
# the native qualification paired with PostgreSQL (D77.24 whitelist). Emission
# derives a cell from the plan (the live verifier re-derives emission's
# blockers first), compiled replay from its records and the pure boundary from
# its document; every other MySQL shape keeps its refusal. The plan tables a
# cell's query may hold; any other non-empty one (a header parameter, slot,
# let, window, JOIN, set, VALUES, result, Collect, Unnest, block or capture
# read, or a table a later plan adds) closes its cells.
_MYSQL_CELL_PLAN_TABLES = frozenset(
    {
        "aggregate_projections",
        "aggregates",
        "aggregations",
        "all_exports",
        "blocks",
        "boundaries",
        "demands",
        "exports",
        "expression_sites",
        "expressions",
        "filters",
        "group_keys",
        "input_ports",
        "input_uses",
        "literal_sites",
        "operands",
        "origins",
        "projections",
        "result_exports",
        "result_ports",
        "source_ports",
        "sources",
        "stage_ports",
        "symbols",
    }
)
# R08 (T08-1): the bind-safe slot tables a division cell's query may also
# hold, a literal operand being a slot there.
_MYSQL_SLOT_PLAN_TABLES = frozenset({"literal_slots", "bind_uses"})
# The fields of a cell's authored `query` or `table` that may be set; any
# other one (a `let`, relation alias or window, read or not, a JOIN,
# DISTINCT, ORDER BY, LIMIT, header parameter, or a field a later grammar
# adds) closes its cells, as the plan keeps no trace of an unread one (MC G4
# opens relation aliases and unread windows to a sum's query alone).
_MYSQL_CELL_AUTHORED = frozenset(
    {"span", "name", "from_clause", "where_clause", "group_by_clause", "select_items"}
)
# The aggregates an S02 cell's aggregation may hold beside its sums; MC G7
# counts a conditional sum as a sum (mysql_filtered_sum_cell).
MYSQL_SUM_STAGE_FUNCTIONS = frozenset({"sum", "filtered_sum", "count", "min"})
# MC G1: the storages of an S02 cell sum's field, nullable or not.
MYSQL_SUM_CARRIERS = ({"kind": "my_bigint"}, {"kind": "my_int"})
# MC G2: the storage kinds of an S02 cell's GROUP BY key fields, and of the
# one field that each other aggregate beside its sums reads, by function.
MYSQL_SUM_KEY_KINDS = frozenset({"my_bigint", "my_int", "my_varchar"})
MYSQL_SUM_BESIDE = {
    "count_distinct": MYSQL_SUM_KEY_KINDS,
    "max": frozenset({"my_bigint", "my_int"}),
    "avg": frozenset({"my_bigint", "my_int"}),
}
# MC G3: the plan tables and authored fields that an S02 cell's HAVING,
# ORDER BY, LIMIT and DISTINCT add, and the storage kinds of a GROUP BY key
# that a HAVING line reads (an ORDER BY key reads MYSQL_SUM_KEY_KINDS).
_MYSQL_CLAUSE_PLAN_TABLES = frozenset(
    {
        "distincts",
        "order_expressions",
        "order_items",
        "order_uses",
        "orders",
        "quotient_fields",
        "result_boundaries",
        "result_limits",
    }
)
_MYSQL_CLAUSE_AUTHORED = frozenset(
    {"satisfying_clause", "order_by_clause", "limit_clause", "distinct_clause"}
)
MYSQL_SUM_HAVING_KEY_KINDS = frozenset({"my_bigint", "my_int"})
# MC G5 (lead ruling of 2026-11-21, R-witness): the comparisons by which a
# HAVING line on a sum may read a header parameter, the only ones a G5 form
# witnesses.
MYSQL_SUM_HAVING_PARAMETER_COMPARISONS = frozenset({">", ">="})
# MC G4, item 5: the MySQL carrier of an upstream's value that the query
# reads, by function (a `min` or `max` keeps its field's, but one of a
# SMALLINT or INT is the `my_signed_int` of its SIGNED cast, which is no
# key or `max`, `avg` or `count_distinct` argument storage).
_MYSQL_UPSTREAM_CARRIERS = {
    "sum": "my_signed_int",
    "count": "my_bigint",
    "count_distinct": "my_bigint",
    "avg": "my_double",
}


def mysql_checked_operands(values) -> bool:
    """The operand carrier of a cell: each is a nullable MySQL BIGINT source
    field, the carrier the qualification probed."""

    return bool(values) and all(
        value.tag == "Int"
        and value.storage == {"kind": "my_bigint"}
        and value.nullable is True
        and not value.binding
        for value in values
    )


def mysql_sum_operand(value) -> bool:
    """MC G1: the argument carrier of an S02 cell's sum, a nullable or
    non-null BIGINT or INT source field (MYSQL_SUM_CARRIERS); MC G4, item 5:
    or an upstream's sum (`my_signed_int`, which no source field is)."""

    return (
        value.tag == "Int"
        and value.storage in (*MYSQL_SUM_CARRIERS, {"kind": "my_signed_int"})
        and not value.binding
    )


def mysql_s03_operand(value) -> bool:
    """The argument carrier of a MySQL guarded SUM: a BIGINT or INT, of a
    source field, a count or a guarded SUM, never per binding. S02 narrows it
    to mysql_sum_operand; an S03 form pins each argument's own."""

    return (
        value.tag == "Int"
        and value.storage in (*MYSQL_SUM_CARRIERS, {"kind": "my_signed_int"})
        and not value.binding
    )


def mysql_checked_query(
    plan,
    *,
    aggregate: bool,
    slots: bool = False,
    lets: bool = False,
    clauses: bool = False,
    organized: bool = False,
    parameters: bool = False,
    joins: bool = False,
) -> bool:
    """A cell's query, from the plan and its authored `query` or `table`:
    its non-empty tables are among _MYSQL_CELL_PLAN_TABLES (and, with
    ``slots``, _MYSQL_SLOT_PLAN_TABLES), it reads a
    source of its own module through one WHERE at most, then
    (``aggregate``) one aggregation, then its projection, and as written it
    sets only _MYSQL_CELL_AUTHORED fields.
    With ``lets`` (MC G1) a block of each of its value `let`s may come
    first, and its authored names are those `let`s alone: a relation alias
    leaves no value `let`. Every check is O(1) in the program beside its
    `let`s, its JOINs and the definitions it reads: at most seven more
    blocks, one source and two authored declarations are read. With
    ``clauses`` (MC G3) a HAVING block may follow
    the aggregation, and the query may also hold _MYSQL_CLAUSE_PLAN_TABLES
    and set _MYSQL_CLAUSE_AUTHORED fields, whose law is
    mysql_sum_clauses'. With ``organized`` (MC G4) the source may be
    imported, each definition may also name relation aliases of what its
    FROM reads (_mysql_aliases) and windows that nothing reads, and the
    query may read, in place of the source, one upstream definition
    (_mysql_levels) that reads the source so: a block of each of its own
    `let`s, one WHERE at most, one aggregation at most and its projection,
    as written setting no _MYSQL_CLAUSE_AUTHORED field. With ``parameters``
    (MC G5) the plan may also hold header parameters and the query's own
    definition may declare them, whose law is mysql_sum_placeholders'. With
    ``joins`` (MC G6) the selected definition's rows may come through JOINs
    that keep mysql_join_law instead of from one source; such a query takes
    none of ``slots``, ``clauses``, ``organized`` and ``parameters``, so a
    HAVING, ORDER BY, LIMIT, DISTINCT, relation alias, window, imported
    source, upstream, header parameter or bind-safe slot over JOIN rows
    keeps its refusal. No query is one while emission derives as main
    (AS_MAIN)."""

    from pietto._project.module_catalog import authored_definitions
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    stage = row.ProjectSQLStageKind
    middle = (stage.AGGREGATE,) if aggregate else ()
    # MC G6: JOIN rows take no G3 clause, G4 organization or G5 placeholder.
    joined = bool(joins and plan.joins)
    if joined:
        slots = clauses = organized = parameters = False
    levels = (
        None
        if AS_MAIN.get() or len(plan.blocks) > len(plan.let_values) + 7
        else _mysql_levels(plan)
    )
    selected = plan.scope.selected_owner
    module = plan.scope.completed.semantic_result.modules[selected.module_position]
    if joined and (
        levels is None
        or not mysql_join_law(
            plan,
            authored_definitions(module)[selected.declaration_position],
            module,
        )
    ):
        return False

    def level(position, blocks, owner) -> bool:
        """One definition's blocks and authored body: the selected query's
        last, an upstream's (MC G4) first."""
        assert levels is not None
        upstream = position + 1 < len(levels)
        inners = (
            ((), (stage.AGGREGATE,))
            if upstream
            else (middle, (*middle, stage.SATISFYING))
            if clauses
            else (middle,)
        )
        refs = {_at(block.ref) for block in blocks}
        named = (
            (stage.LET,)
            * sum(_at(value.site.block) in refs for value in plan.let_values)
            if lets
            else ()
        )
        reason = (
            ProjectSQLBoundaryReason.NAMED_INPUT
            if position
            else ProjectSQLBoundaryReason.SOURCE_INPUT
        )
        authored = authored_definitions(
            plan.scope.completed.semantic_result.modules[owner.module_position]
        )[owner.declaration_position]
        return not (
            upstream
            and owner.block_local
            or tuple(block.kind for block in blocks)
            not in tuple(
                shape
                for inner in inners
                for shape in (
                    (*named, *inner, stage.PROJECTION),
                    (*named, stage.WHERE, *inner, stage.PROJECTION),
                )
            )
            or any(
                (
                    # MC G6: every block reads the JOIN chain's one tail.
                    block.boundary is not plan.join_tails[0]
                    if joined
                    else type(block.boundary) is not ProjectSQLBoundary
                    or block.boundary.reason is not reason
                    or position
                    and not _same(block.boundary.use.producer, levels[0][0])
                )
                for block in blocks
            )
            # D77.24: the project folds a relation alias into the plan's
            # FROM and drops an unread alias or window, so only the
            # authored body still shows them; compiled records and the pure
            # document cannot tell them from a direct read.
            or any(
                getattr(authored, name) not in (None, ())
                for name in authored.__dataclass_fields__
                if name not in _MYSQL_CELL_AUTHORED
                and not (clauses and not upstream and name in _MYSQL_CLAUSE_AUTHORED)
                and not (parameters and not upstream and name == "parameters")
                and not (organized and name == "named_windows")
                # MC G6: each JOIN's binding `let x = S` is a naming
                # declaration beside the value `let`s.
                and not (joined and name == "join_clauses")
                and not (
                    lets
                    and name == "naming_declarations"
                    and (
                        _mysql_aliases(plan, authored, refs)
                        if organized
                        else len(authored.naming_declarations)
                        == len(named) + len(getattr(authored, "join_clauses", ()))
                    )
                )
            )
        )

    return not (
        levels is None
        or len(levels) > (2 if organized else 1)
        or levels[-1][1] is not selected
        or any(
            type(value := getattr(plan, name)) is tuple
            and value
            and name not in _MYSQL_CELL_PLAN_TABLES
            and not (slots and name in _MYSQL_SLOT_PLAN_TABLES)
            and not (parameters and name == "parameters")
            and not (lets and name == "let_values")
            and not (clauses and name in _MYSQL_CLAUSE_PLAN_TABLES)
            and not (joined and name in _MYSQL_JOIN_PLAN_TABLES)
            for name in plan.__dataclass_fields__
        )
        # A source imported, under its own name or another, reads as the
        # same records as one declared here.
        or not organized
        and any(binding.module is not module for binding in plan.sources)
        or not all(
            level(position, blocks, owner)
            for position, (_, owner, blocks) in enumerate(levels)
        )
    )


def _at(ref) -> tuple:
    """A plan reference's identity: its kind and position."""

    return getattr(ref, "kind", None), getattr(ref, "position", None)


def _same(left, right) -> bool:
    """Two plan references to one plan item."""

    return _at(left) == _at(right)


def _mysql_levels(plan):
    """MC G4, item 5: the plan's blocks by the definition that holds them,
    in plan order, each as (definition, its declaration, blocks); None when
    a definition's blocks are not contiguous. Linear in the blocks."""

    owners = {_at(item.ref): item.entry.owner for item in plan.bindings.definitions}
    levels: list = []
    for block in plan.blocks:
        if not levels or not _same(levels[-1][0], block.definition):
            if any(_same(item[0], block.definition) for item in levels):
                return None
            levels.append((block.definition, owners.get(_at(block.definition)), []))
        levels[-1][2].append(block)
    if not levels or any(owner is None for _, owner, _ in levels):
        return None
    return tuple((ref, owner, tuple(blocks)) for ref, owner, blocks in levels)


def _mysql_aliases(plan, authored, refs) -> bool:
    """MC G4, item 1: each naming declaration of an authored definition that
    no value `let` of its blocks (``refs``) names is a relation alias whose
    value names the relation that FROM reads, by that name or through such
    an alias; no alias names another one."""

    ports = {port.ref: port for port in plan.stage_ports}
    values = {
        getattr(getattr(ports.get(value.port), "key", None), "name", None)
        for value in plan.let_values
        if _at(value.site.block) in refs
    }
    aliases = {
        item.name: item.expression
        for item in authored.naming_declarations
        if item.name not in values
    }
    read = authored.from_clause.source_name
    named = aliases.get(read)
    base = named.name if type(named) is NameExpr else read
    return (
        len(authored.naming_declarations) - len(aliases) == len(values)
        and base not in aliases
        and all(
            type(value) is NameExpr and value.name == base for value in aliases.values()
        )
    )


# MC G6: the plan tables a query's JOINs add, and the JOIN kinds it may use.
_MYSQL_JOIN_PLAN_TABLES = frozenset(
    {"aggregate_risks", "join_inputs", "join_ports", "join_tails", "joins"}
)
MYSQL_JOIN_KINDS = frozenset({"inner", "left", "right"})
# A read of a stage port as written: of one input, or (MC G6) of a JOIN's.
_MYSQL_READS = (row.ProjectSQLReference, row.ProjectSQLJoinedReference)


def mysql_join_law(plan, authored, module) -> bool:
    """MC G6: the selected `query` or `table` reads a source of its own
    module by name, then one or more JOINs in source order, each a binding
    `let x = S` of such a source S joined by `inner`, `left` or `right join
    x on P`, as the plan holds them: one chain of the selected definition
    with one tail, each JOIN's earlier input the FROM's source or the JOIN
    before it and its joined input a source, and every bound definition but
    the selected one a source. `P` is a conjunction (its top-level `and`s)
    of linking equalities, one at least, an `==` of an Int field read of
    the joined input and one of an earlier input in either order, and, in
    an INNER or LEFT JOIN, literal comparisons, a read of a non-null Int
    field of the joined input, then `>` or `>=`, then an Int literal
    written as a number token. A relationship call reads as its body for
    its linking equalities; a literal of its body, inlined at the call's
    text, is no number token, nor a `def` argument or a `def` body a read or
    literal here. Compiled replay and the pure boundary see no `def` or
    relationship call (D77.24's alias limit). Linear in the JOINs and their
    `on` operations."""

    from pietto import ast_nodes as ast
    from pietto._project.module_catalog import authored_definitions
    from pietto._project.project_sql_emission_joins import (
        EXPECTED_ROWS,
        joined_definitions,
    )
    from pietto.ast_nodes import inlined_arguments

    if type(authored) not in (ast.QueryDef, ast.TableDef):
        return False
    sources = {
        definition.name
        for definition in authored_definitions(module)
        if type(definition) is ast.SourceDef
    }
    lets = {let.name: let for let in authored.naming_declarations}
    clauses = authored.join_clauses
    if (
        authored.from_clause.binding_name is not None
        or authored.from_clause.source_name not in sources
        or len(plan.bindings.definitions) != len(plan.sources) + 1
        or len(plan.join_tails) != 1
        or any(
            clause.kind not in MYSQL_JOIN_KINDS
            or clause.uses_named_input is not True
            or clause.asof
            or clause.traversal_steps
            or clause.source_binding_name is not None
            or clause.target_relation_name != clause.target_binding_name
            or type(getattr(lets.get(clause.target_binding_name), "expression", None))
            is not ast.NameExpr
            or lets[clause.target_binding_name].expression.name not in sources
            for clause in clauses
        )
    ):
        return False
    grouped = joined_definitions(plan)
    joins = tuple(grouped.values())[0] if len(grouped) == 1 else ()
    if (
        not joins
        or len(joins) != len(clauses)
        or plan.join_tails[0].join is not joins[-1].ref
    ):
        return False
    inputs = {item.ref: item for item in plan.join_inputs}
    ports = {port.ref: port for port in plan.join_ports}
    written = _mysql_number_token(plan)
    for index, join in enumerate(joins):
        pair = [inputs[ref] for ref in join.inputs if ref in inputs]
        if (
            str(join.kind) not in MYSQL_JOIN_KINDS
            or join.rows is not EXPECTED_ROWS[join.kind]
            or join.equalities
            or join.on is None
            or len(pair) != 2
            or (pair[0].ordinal, pair[1].ordinal) != (0, 1)
            or pair[0].predecessor is not (joins[index - 1].ref if index else None)
            or (pair[0].producer is None) is not bool(index)
            or pair[1].producer is None
            or pair[1].predecessor is not None
        ):
            return False

        def read(reference):
            """(side, nullable) of an Int field read of one input as written,
            side 1 the joined input; or None."""
            expression = _planned(plan, reference)
            port = ports.get(getattr(expression, "port", None))
            if (
                type(expression) is not row.ProjectSQLMatchReference
                or port is None
                or port.input not in join.inputs
                or inlined_arguments(expression.expression)
                or value_tag(expression) != "Int"
            ):
                return None
            return join.inputs.index(port.input), value_nullable(expression)

        linked, pending = False, [join.on]
        while pending:
            expression = _planned(plan, pending.pop())
            if (
                type(expression) is row.ProjectSQLBinary
                and expression.expression.operator == "and"
            ):
                pending += (expression.left, expression.right)
                continue
            if type(expression) is not row.ProjectSQLComparison:
                return False
            operator = expression.expression.operator
            left, right = read(expression.left), read(expression.right)
            literal = _planned(plan, expression.right)
            if operator == "==" and left and right and {left[0], right[0]} == {0, 1}:
                linked = True
            elif not (
                operator in (">", ">=")
                and str(join.kind) != "right"
                and left == (1, False)
                and type(literal) is row.ProjectSQLLiteral
                and value_tag(literal) == "Int"
                and type(literal.expression.value) is int
                and not inlined_arguments(literal.expression)
                and written(literal.expression.span)
            ):
                return False
        if not linked:
            return False
    return True


def mysql_field_column(column) -> bool:
    """A source field column, read directly or carried by the query's own
    stages, a let value only when it copies a field read, never a literal,
    aggregate or window result."""

    return (
        type(column) is StageColumn
        and column.field is not None
        and column.source_port is not None
        and column.literal is None
        and column.aggregate is None
        and column.window is None
    )


def mysql_field(value) -> bool:
    """A read of a mysql_field_column."""

    return type(value) is SQLStageReference and mysql_field_column(value.column)


def mysql_checked_cell(plan, expression, values) -> bool:
    """S01: a MySQL Int sign, arithmetic or `abs` is in its cell when it is
    the whole value of a SELECT item of the emitted query, its operands are
    source fields (mysql_field) and the query is mysql_checked_query's."""

    site = getattr(expression, "site", None)
    return (
        type(site) is row.ProjectSQLExpressionSite
        and site.role is row.ProjectSQLExpressionRole.SELECT
        and site.occurrence.expression is expression.expression
        and bool(values)
        and all(mysql_field(value) for value in values)
        and mysql_checked_query(plan, aggregate=False)
    )


def mysql_carried_column(column) -> bool:
    """MC G4, item 5: a column that a sum, key or other aggregate may read: a
    mysql_field_column, or a key or aggregate result of an upstream's
    aggregation, read through it (its carrier is its realized one). Only the
    query that reads an upstream has the latter among its inputs."""

    return mysql_field_column(column) or (
        type(column) is StageColumn
        and column.literal is None
        and column.window is None
        and getattr(column.aggregate, "kind", None) in ("group_key", "aggregate_result")
    )


def _mysql_upstream_read(function, origin, storage) -> bool:
    """G4's witnessed two-level reads of an upstream extreme or average."""
    if origin in ("min", "max"):
        return function not in ("count", "count_distinct") and (
            function != "min" or storage == "my_bigint"
        )
    return origin != "avg" or function not in ("min", "count")


def mysql_sum_query(plan, stage, keys, columns) -> bool:
    """S02: an aggregation that can hold a MySQL sum(Int) cell, asked once
    per aggregation ``stage``: the query is mysql_checked_query's, no SELECT
    item of the stage's definition computes over an aggregate result, its
    value `let`s keep MC G1's law (mysql_sum_lets), and S02's own law or MC
    G2's holds of the stage. S02's: one GROUP BY key at most (``keys``), a
    non-null Int source field (mysql_field_column) of any storage, beside
    sums, counts and mins only (MYSQL_SUM_STAGE_FUNCTIONS). G2's: each key a
    source field of MYSQL_SUM_KEY_KINDS storage, nullable or not, and each
    aggregate a sum, count or min or a `count_distinct`, `max` or `avg` of
    one source field read (its realized column in ``columns``) of its
    MYSQL_SUM_BESIDE storage. Its rows may come through JOINs that keep
    mysql_join_law (MC G6), under G2's law alone and with none of G3's
    clauses, G4's organization or G5's placeholders (mysql_checked_query).
    A SMALLINT read, a key of that storage or a `count` or `min` of such a
    field, keeps S02's own cell (mysql_sum_smallint), and MC G3's HAVING,
    ORDER BY, LIMIT and DISTINCT
    keep mysql_sum_clauses' law. MC G4: when the query reads an upstream
    (_mysql_levels), the upstream's aggregation also has a key and a sum and
    the query's own holds a sum; at the query's own aggregation each input
    column is a `let` of the query or one it reads from the upstream, which
    counts as a source field of its realized carrier (mysql_carried_column),
    and an aggregating upstream has a key and a sum, each of its sums is the
    argument of an aggregate of the query or the value of a `let` of it, the
    query reads upstream extremes and averages under _mysql_upstream_read,
    and the query has no WHERE and no HAVING, ORDER BY, LIMIT or DISTINCT.
    MC G5: the query may declare header parameters and hold bind-safe
    slots, placed as mysql_sum_placeholders has them. MC G7: a conditional
    sum counts as a sum (MYSQL_SUM_STAGE_FUNCTIONS), but its query takes none
    of G3's clauses, G4's organization, G5's placeholders or G6's JOINs
    (mysql_checked_query with ``lets`` alone). The scans of the plan's aggregates
    and expressions run only for a query with one or two aggregations."""

    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto.ast_nodes import LetBinding

    if not mysql_checked_query(
        plan,
        aggregate=True,
        slots=True,
        lets=True,
        clauses=True,
        organized=True,
        parameters=True,
        joins=True,
    ):
        return False
    # MC G7: a statement with a conditional sum takes none of G3's clauses,
    # G4's organization, G5's placeholders or G6's JOINs, so each keeps its
    # refusal beside one.
    if any(
        function_name(value.source) == "filtered_sum" for value in plan.aggregates
    ) and not mysql_checked_query(plan, aggregate=True, lets=True):
        return False
    levels = _mysql_levels(plan)
    assert levels is not None
    if not mysql_sum_placeholders(plan, levels):
        return False
    position = next(
        (
            index
            for index, (definition, _, _) in enumerate(levels)
            if _same(definition, stage.definition)
        ),
        None,
    )
    if position is None:
        return False
    refs = [{_at(block.ref) for block in blocks} for _, _, blocks in levels]
    aggregations = [
        next((item for item in plan.aggregations if _at(item.block) in mine), None)
        for mine in refs
    ]

    def functions(aggregation) -> list:
        return [
            function_name(value.source)
            for value in plan.aggregates
            if aggregation is not None and _same(value.aggregation, aggregation.ref)
        ]

    def argument(value):
        """The realized column that ``value``'s one argument reads."""
        arguments = value.arguments
        expression = _planned(plan, arguments[0]) if len(arguments) == 1 else None
        return (
            columns.get(getattr(expression, "port", None))
            if type(expression) in _MYSQL_READS
            else None
        )

    def beside(value) -> bool:
        column = argument(value)
        return (
            column is not None
            and mysql_carried_column(column)
            and not column.realization.binding
            and column.realization.storage.get("kind")
            in MYSQL_SUM_BESIDE.get(function_name(value.source) or "", ())
        )

    own = [value for value in plan.aggregates if _same(value.aggregation, stage.ref)]

    def s02() -> bool:
        return (
            len(keys) <= 1
            and all(
                mysql_carried_column(key)
                and key.realization.tag == "Int"
                and key.realization.nullable is False
                for key in keys
            )
            and all(
                function_name(value.source) in MYSQL_SUM_STAGE_FUNCTIONS
                for value in own
            )
        )

    def g2() -> bool:
        return all(
            mysql_carried_column(key)
            and not key.realization.binding
            and key.realization.storage.get("kind") in MYSQL_SUM_KEY_KINDS
            for key in keys
        ) and all(
            function_name(value.source) in MYSQL_SUM_STAGE_FUNCTIONS or beside(value)
            for value in own
        )

    def upstream() -> bool:
        """MC G4, item 5, at this stage of a two-level query."""
        if len(levels) == 1:
            return True
        if position == 0:
            return (
                bool(keys)
                and "sum" in functions(stage)
                and ("sum" in functions(aggregations[1]))
            )
        ports = {port.ref: port for port in plan.stage_ports}
        if not all(
            mysql_carried_column(column)
            or type(getattr(ports.get(port), "key", None)) is LetBinding
            for port, column in columns.items()
        ):
            return False
        if aggregations[0] is None:
            return True
        if any(
            (operand := argument(value)) is not None
            and not _mysql_upstream_read(
                function_name(value.source),
                getattr(operand.aggregate, "function", None),
                operand.realization.storage.get("kind"),
            )
            for value in own
        ):
            return False
        expressions = {_at(item.ref): item for item in plan.expressions}
        carries = {_at(port.ref): port.source for port in plan.stage_ports}

        def first(port) -> tuple:
            """The query's first port that ``port`` carries, down its `let`
            blocks (each block carries a port at most twice)."""
            for _ in range(2 * len(levels[1][2])):
                source = carries.get(_at(port))
                if _at(source) not in carries:
                    break
                port = source
            return _at(port)

        read = {
            first(getattr(expressions.get(_at(reference)), "port", None))
            for reference in (
                *(argument for value in own for argument in value.arguments),
                *(
                    value.expression
                    for value in plan.let_values
                    if _at(value.site.block) in refs[1]
                ),
            )
        }
        return (
            bool(aggregations[0].keys)
            and "sum" in functions(aggregations[0])
            and all(
                first(port) in read
                for port, column in columns.items()
                if getattr(column.aggregate, "function", None) == "sum"
            )
            and not any(
                block.kind
                in (row.ProjectSQLStageKind.WHERE, row.ProjectSQLStageKind.SATISFYING)
                for block in levels[1][2]
            )
            and not (plan.orders or plan.result_limits or plan.distincts)
        )

    return (
        mysql_sum_lets(plan)
        # MC G6: over JOINs, G2's law alone.
        and ((s02_law := not plan.joins and s02()) or g2())
        and mysql_sum_smallint(plan, keys, columns, s02_law)
        and upstream()
        and (position < len(levels) - 1 or mysql_sum_clauses(plan, columns))
        and not any(
            getattr(getattr(item, "site", None), "role", None)
            is row.ProjectSQLExpressionRole.SELECT
            and _at(item.site.block) in refs[position]
            for item in plan.expressions
        )
    )


def mysql_sum_smallint(plan, keys, columns, own) -> bool:
    """MC G1-G3 (lead ruling of 2026-11-21, S02-SMALLINT): no family form
    witnesses a SMALLINT read beside a widened sum, so an aggregation whose
    GROUP BY key column is of `my_smallint` storage, or that holds a
    `count` or `min` of one field read of that storage (its realized column
    in ``columns``), stays in S02's own cell as main takes it: S02's own
    law holds (``own``) of a query with no value `let`, no MC G3 clause,
    none of MC G4's organization, an upstream included, and no MC G5 header
    parameter or bind-safe slot (mysql_checked_query without MC G1's
    ``lets``, MC G3's ``clauses``, MC G4's ``organized`` and MC G5's
    ``parameters`` and ``slots``), whose every sum is an unconditional
    sum of a nullable BIGINT source field
    (mysql_checked_operands). Linear in the aggregation's values."""

    from pietto._project.project_sql_emission_aggregation import function_name

    def read(value):
        arguments = value.arguments
        expression = _planned(plan, arguments[0]) if len(arguments) == 1 else None
        # MC G6: a read of one input or of a JOIN's (_MYSQL_READS).
        return (
            columns.get(getattr(expression, "port", None))
            if type(expression) in _MYSQL_READS
            else None
        )

    def smallint(column) -> bool:
        return (
            column is not None
            and (column.realization.storage or {}).get("kind") == "my_smallint"
        )

    if not (
        any(smallint(key) for key in keys)
        or any(
            function_name(value.source) in ("count", "min") and smallint(read(value))
            for value in plan.aggregates
        )
    ):
        return True
    return (
        own
        and mysql_checked_query(plan, aggregate=True)
        and all(
            function_name(value.source) not in ("sum", "filtered_sum")
            or (column := read(value)) is not None
            and mysql_field_column(column)
            and mysql_checked_operands((column.realization,))
            for value in plan.aggregates
        )
    )


def mysql_sum_placeholders(plan, levels) -> bool:
    """MC G5: the header parameters and bind-safe slots of an S02 query. Each
    parameter is a Bool, Int, Float or Text, read or not. A read is of no
    Float, in the selected query's WHERE, and every operation over it up to
    the WHERE's predicate has a Bool result, so no value is computed from it
    and no check waits for a bound value; or it is the right side of a HAVING
    line (mysql_sum_clauses). Each bind-safe slot is a WHERE literal of the
    selected query or of an upstream (``levels``) with no aggregation. Linear
    in the plan."""

    if not (plan.parameters or plan.literal_slots):
        return True
    parents = {_at(item.child): item.parent for item in plan.operands}
    where = {
        _at(item.predicate)
        for item in plan.filters
        if getattr(item.site, "role", None) is row.ProjectSQLExpressionRole.WHERE
    }
    selected = {_at(block.ref) for block in levels[-1][2]}
    plain = (
        {_at(block.ref) for block in levels[0][2]}
        if len(levels) == 2
        and not any(
            block.kind is row.ProjectSQLStageKind.AGGREGATE for block in levels[0][2]
        )
        else set()
    )

    def placed(expression, blocks) -> bool:
        site = getattr(expression, "site", None)
        return (
            type(site) is row.ProjectSQLExpressionSite
            and site.role is row.ProjectSQLExpressionRole.WHERE
            and _at(site.block) in blocks
        )

    def guarded(expression) -> bool:
        """Every operation above ``expression`` has a Bool result, up to a
        WHERE predicate."""
        reference = expression.ref
        for _ in range(len(plan.expressions)):
            parent = parents.get(_at(reference))
            if parent is None:
                return _at(reference) in where
            above = _planned(plan, parent)
            if above is None or value_tag(above) != "Bool":
                return False
            reference = parent
        return False

    for expression in plan.expressions:
        if type(expression) is row.ProjectSQLParameterRead and not (
            expression.parameter.tag != "Float"
            and (
                getattr(expression.site, "role", None)
                is row.ProjectSQLExpressionRole.SATISFYING
                or placed(expression, selected)
                and guarded(expression)
            )
        ):
            return False
    uses = {_at(use.slot.ref) for use in plan.bind_uses}
    return (
        all(
            parameter.tag in ("Bool", "Int", "Float", "Text")
            for parameter in plan.parameters
        )
        and uses == {_at(slot.ref) for slot in plan.literal_slots}
        and all(
            type(expression := _planned(plan, use.expression))
            is row.ProjectSQLBoundLiteral
            and placed(expression, selected | plain)
            for use in plan.bind_uses
        )
    )


def mysql_sum_clauses(plan, columns) -> bool:
    """MC G3: the HAVING, ORDER BY, LIMIT and DISTINCT of an S02 query, which
    need a GROUP BY key. Each HAVING line compares one output named alone
    with an unsigned Int literal (MYSQL_TYPED_COMPARISONS), the lines joined
    by `and`; the output is a key of MYSQL_SUM_HAVING_KEY_KINDS storage or an
    aggregate other than `avg`, and a line on a sum is its block's only line.
    Each ORDER BY key is an output named alone, a key of MYSQL_SUM_KEY_KINDS
    storage or an aggregate other than `avg`. A LIMIT is at least 1, after an
    ORDER BY whose first key is an aggregate. DISTINCT stands beside no
    `avg`. An output's value is found by following its ports' sources down
    to the aggregation, each step to a lower port (``columns`` realizes a
    key's field). MC G5: a HAVING line on a sum may compare it by `>` or
    `>=` with a non-null Int header parameter instead
    (MYSQL_SUM_HAVING_PARAMETER_COMPARISONS), and beside a header parameter
    read or a bind-safe slot the one HAVING line reads a sum."""

    from pietto._project.project_sql_emission_aggregation import function_name

    satisfying = [
        item
        for item in plan.filters
        if getattr(item.site, "role", None) is row.ProjectSQLExpressionRole.SATISFYING
    ]
    if not (satisfying or plan.orders or plan.result_limits or plan.distincts):
        return True

    def at(ref):
        return getattr(ref, "kind", None), getattr(ref, "position", None)

    steps = {
        at(item.ref): item.source for item in (*plan.stage_ports, *plan.result_ports)
    }
    steps.update((at(item.ref), item.input) for item in plan.aggregate_projections)
    targets = {at(item.result): item for item in (*plan.group_keys, *plan.aggregates)}

    def value(ref, kinds):
        """The key of ``kinds`` storage or the aggregate other than `avg`
        that a read of ``ref`` carries, or None."""
        for _ in range(len(steps) + 1):
            target = targets.get(at(ref))
            if target is not None:
                if type(target) is aggregation.ProjectSQLAggregate:
                    return target if function_name(target.source) != "avg" else None
                column = columns.get(target.input)
                return (
                    target
                    if column is not None
                    and column.realization.storage.get("kind") in kinds
                    else None
                )
            if at(ref) not in steps:
                return None
            ref = steps[at(ref)]
        return None

    pending = [_planned(plan, item.predicate) for item in satisfying]
    read = []
    while pending:
        line = pending.pop()
        if (
            type(line) is row.ProjectSQLBinary
            and getattr(line.expression, "operator", None) == "and"
        ):
            pending += (_planned(plan, line.left), _planned(plan, line.right))
            continue
        left = _planned(plan, getattr(line, "left", None))
        right = _planned(plan, getattr(line, "right", None))
        literal = getattr(getattr(right, "expression", None), "value", None)
        if not (
            type(line) is row.ProjectSQLComparison
            and line.expression.operator in MYSQL_TYPED_COMPARISONS
            and type(left) is aggregation.ProjectSQLResultReference
            and type(left.expression) is NameExpr
            and (
                type(right) is row.ProjectSQLLiteral
                and type(literal) is int
                and literal >= 0
                # MC G5: a non-null Int header parameter, by `>` or `>=`.
                or type(right) is row.ProjectSQLParameterRead
                and right.parameter.tag == "Int"
                and value_nullable(right.parameter) is False
                and line.expression.operator in MYSQL_SUM_HAVING_PARAMETER_COMPARISONS
            )
        ):
            return False
        read.append(value(left.port, MYSQL_SUM_HAVING_KEY_KINDS))
    expressions = {at(item.ref): item for item in plan.order_expressions}
    uses = {at(item.ref): item for item in plan.order_uses}
    keys = []
    for item in sorted(plan.order_items, key=lambda item: item.position):
        expression = expressions.get(at(item.expression))
        use = None if expression is None else uses.get(at(expression.use))
        if (
            expression is None
            or use is None
            or at(item.value) != at(item.expression)
            or type(expression.expression) is not NameExpr
            or expression.operands
            or len(use.ports) != 1
        ):
            return False
        keys.append(value(use.ports[0], MYSQL_SUM_KEY_KINDS))
    sums = [
        target
        for target in read
        if type(target) is aggregation.ProjectSQLAggregate
        and function_name(target.source) == "sum"
    ]
    return (
        bool(plan.group_keys)
        and len(satisfying) <= 1
        and None not in read
        and (not sums or len(read) == 1)
        # MC G5: beside a placeholder, HAVING's one line reads a sum.
        and not (
            read
            and not sums
            and (
                plan.literal_slots
                or any(
                    type(item) is row.ProjectSQLParameterRead
                    for item in plan.expressions
                )
            )
        )
        and len(plan.orders) <= 1
        and None not in keys
        and len(plan.result_limits) <= 1
        and all(
            limit.value >= 1
            and keys
            and type(keys[0]) is aggregation.ProjectSQLAggregate
            for limit in plan.result_limits
        )
        and not (
            plan.distincts
            and any(function_name(item.source) == "avg" for item in plan.aggregates)
        )
    )


def mysql_sum_lets(plan) -> bool:
    """MC G1: each value `let` of an S02 query is read at least once, and
    every read of its name is the whole argument of a `sum` of the query: no
    chain, no GROUP BY key (a key reads its input port, outside the plan's
    expressions), no other reader. A sum's argument is then a source field
    read (mysql_sum_cell) only when the `let` reads one as written. Linear
    in the plan."""

    from pietto._project.project_scalar_namespaces import ProjectJoinedLetOccurrence
    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto.ast_nodes import LetBinding

    if not plan.let_values:
        return True
    ports = {port.ref: port for port in plan.stage_ports}
    # A `let` port's key; over JOINs (MC G6) its joined occurrence.
    named = (LetBinding, ProjectJoinedLetOccurrence)
    if any(
        type(getattr(ports.get(key.input), "key", None)) in named
        for key in plan.group_keys
    ):
        return False
    summed = {
        id(argument)
        for value in plan.aggregates
        if function_name(value.source) == "sum"
        for argument in value.arguments
    }
    read = set()
    for expression in plan.expressions:
        key = getattr(ports.get(getattr(expression, "port", None)), "key", None)
        if type(expression) in _MYSQL_READS and type(key) in named:
            if id(expression.ref) not in summed:
                return False
            read.add(id(key))
    return all(
        id(getattr(ports.get(value.port), "key", None)) in read
        for value in plan.let_values
    )


def mysql_sum_cell(aggregate, argument) -> bool:
    """S02: a sum(Int) of a mysql_sum_query stage is in its cell when it is
    the whole value of a SELECT item (a result fact; its analysis holds the
    item's call itself; over JOINs, MC G6, the item's value is the call)
    over a source field (mysql_field) or, MC G4, a column read from an
    upstream (mysql_carried_column), which a JOIN query never reads."""

    from pietto._project.aggregate_grouped_schema import ProjectAggregateResultFact
    from pietto._project.project_joined_aggregation import (
        ProjectJoinedAggregateOccurrence,
    )

    source = aggregate.source
    return (
        type(source) is ProjectJoinedAggregateOccurrence
        and source.item.expression is source.call
        and mysql_field(argument)
        or type(getattr(source, "fact", None)) is ProjectAggregateResultFact
        and type(argument) is SQLStageReference
        and mysql_carried_column(argument.column)
    )


def mysql_filtered_sum_cell(aggregate, argument, test) -> bool:
    """MC G7: a conditional sum of a mysql_sum_query stage is in its cell as
    a sum is (mysql_sum_cell), its test built by mysql_sum_test."""

    return mysql_sum_cell(aggregate, argument) and mysql_sum_test(test)


def mysql_sum_test(value) -> bool:
    """MC G7: a conditional sum's test as realized, every `def` call inlined:
    `not`, `and` and `or` over these atoms, to any depth: a read of a
    source field (mysql_field) of MySQL Bool storage, its `is None`, and a
    read of a BIGINT or INT source field `>` an Int literal, written `N` or
    `-N`. Linear in the test."""

    if type(value) is SQLStageReference:
        return mysql_field(value) and value.realization.storage == {"kind": "my_bool01"}
    if type(value) is not SQLOperation:
        return False
    operands = value.operands
    if value.kind == "logical":
        return value.original.expression.operator in LOGICAL and all(
            mysql_sum_test(operand) for operand in operands
        )
    if value.kind == "not":
        return mysql_sum_test(operands[0])
    if value.kind == "null_test":
        return (
            value.original.expression.negated is False
            and type(operands[0]) is SQLStageReference
            and mysql_sum_test(operands[0])
        )
    if value.kind != "comparison" or value.original.expression.operator != ">":
        return False
    left, right = operands
    if type(right) is parameters.SQLUnary and right.original.expression.operator == "-":
        right = right.operand
    return (
        mysql_field(left)
        and left.realization.storage in MYSQL_SUM_CARRIERS
        and type(right) is parameters.SQLAnchor
        and type(right.operand) is parameters.SQLLiteral
        and type(right.operand.value) is int
        and right.operand.value >= 0
    )


# Phase77 S15 (template T15-1, D77.24): the carrier of each operand of a
# MySQL `%` cell and of each field read beside one.
MYSQL_REMAINDER_CARRIERS = {
    "Int": {"kind": "my_bigint"},
    "Float": {"kind": "my_double"},
}


def mysql_remainder_operands(tag, values) -> bool:
    """The operand carrier of an S15 cell: two fields of ``tag``'s
    MYSQL_REMAINDER_CARRIERS storage, the carriers the qualification probed."""

    return len(values) == 2 and all(
        value.tag == tag
        and value.storage == MYSQL_REMAINDER_CARRIERS.get(tag)
        and not value.binding
        for value in values
    )


def _planned(plan, reference):
    """The plan expression ``reference`` names, or None."""

    position = getattr(reference, "position", None)
    if type(position) is not int or not 0 <= position < len(plan.expressions):
        return None
    expression = plan.expressions[position]
    return expression if expression.ref is reference else None


def _mysql_read_realization(columns, expression) -> Realization | None:
    """The realization of a direct read, as written, of a source field whose
    realized column (``columns``) is not per binding, or None."""

    from pietto.ast_nodes import inlined_arguments

    column = (
        columns.get(expression.port)
        if type(expression) is row.ProjectSQLReference
        # A `def` argument reads as the field it inlines (D77.24, T15-1).
        and not inlined_arguments(expression.expression)
        else None
    )
    if column is None or not mysql_field_column(column) or column.realization.binding:
        return None
    return column.realization


def _mysql_remainder_read(columns, expression) -> str | None:
    """The tag of a direct read of a source field (_mysql_read_realization)
    whose storage is its tag's MYSQL_REMAINDER_CARRIERS one."""

    realization = _mysql_read_realization(columns, expression)
    return (
        realization.tag
        if realization is not None
        and MYSQL_REMAINDER_CARRIERS.get(realization.tag) == realization.storage
        else None
    )


def _mysql_item_value(plan, item):
    """The plan expression that is, as written, the whole value of SELECT
    item ``item`` and no `def` argument, or None."""

    from pietto.ast_nodes import inlined_arguments

    expression = _planned(plan, getattr(item, "expression", None))
    site = getattr(expression, "site", None)
    if (
        type(site) is row.ProjectSQLExpressionSite
        and site.role is row.ProjectSQLExpressionRole.SELECT
        and site.occurrence.expression is getattr(expression, "expression", None)
        and not inlined_arguments(site.occurrence.expression)
    ):
        return expression
    return None


def mysql_remainder_cells(plan, items, columns) -> frozenset:
    """S15: the `%` cells of a MySQL projection stage, asked once per stage.
    The query is mysql_checked_query's without a WHERE, and each SELECT item
    (``items``, over the realized ``columns``) is, as its whole value, either
    a direct read of a source field of a MYSQL_REMAINDER_CARRIERS carrier or a
    `%` over two such reads of its own tag, none of them a `def` argument;
    one item of any other kind closes every cell of the statement. The work
    is linear in the items."""

    if (
        not mysql_checked_query(plan, aggregate=False)
        or plan.blocks[0].kind is not row.ProjectSQLStageKind.PROJECTION
    ):
        return frozenset()
    cells = set()
    for item in items:
        expression = _mysql_item_value(plan, item)
        if expression is None:
            return frozenset()
        if type(expression) is row.ProjectSQLBinary:
            if expression.expression.operator != "%" or {
                _mysql_remainder_read(columns, _planned(plan, operand))
                for operand in (expression.left, expression.right)
            } != {value_tag(expression)}:
                return frozenset()
            cells.add(expression.ref)
        elif _mysql_remainder_read(columns, expression) is None:
            return frozenset()
    return frozenset(cells)


# Phase77 R08 (template T08-1, D77.24, D77.27): the storages of the field
# operand of a MySQL Int `/` cell and of each field read beside one.
MYSQL_DIVISION_CARRIERS = (
    {"kind": "my_smallint"},
    {"kind": "my_int"},
    {"kind": "my_bigint"},
)


def mysql_division_law(left, right) -> bool:
    """R08's proof (D77.27), read only from the literal operand's own value,
    never from a field's storage, declared domain or premise: shape b, a
    literal dividend of 0 or more over a field; shape c, a field over a
    literal divisor of 2 or more. A field operand has one of
    MYSQL_DIVISION_CARRIERS; a literal is the single `my_signed_int` value an
    Int literal token realizes, under bind-safe the bound one."""

    def literal(value, low) -> bool:
        bounds = proven_int_bounds(value)
        return (
            value.storage == {"kind": "my_signed_int"}
            and not value.binding
            and bounds is not None
            and low <= bounds[0] == bounds[1]
        )

    def field(value) -> bool:
        return (
            value.tag == "Int"
            and value.storage in MYSQL_DIVISION_CARRIERS
            and not value.binding
        )

    return literal(left, 0) and field(right) or field(left) and literal(right, 2)


def _mysql_division_read(columns, expression) -> bool:
    """A direct read of an Int source field (_mysql_read_realization) of a
    MYSQL_DIVISION_CARRIERS storage."""

    realization = _mysql_read_realization(columns, expression)
    return (
        realization is not None
        and realization.tag == "Int"
        and realization.storage in MYSQL_DIVISION_CARRIERS
    )


def _mysql_division_literal(expression, written) -> bool:
    """An Int literal token written in its item (``written``), a bind-safe
    slot or not: never a sign over one, a typed NULL, a header parameter, a
    `def` argument or the body of a `def` call, which inlining puts at the
    call's text."""

    from pietto.ast_nodes import inlined_arguments

    return (
        type(expression) in (row.ProjectSQLLiteral, row.ProjectSQLBoundLiteral)
        and value_tag(expression) == "Int"
        and type(expression.expression.value) is int
        and not inlined_arguments(expression.expression)
        and written(expression.expression.span)
    )


def _mysql_number_token(plan):
    """Whether a span covers, in the trusted source text of the selected
    definition's module, one number token on one line; the text is split
    once, at the first question, into the lines the parser reads: after a
    leading BOM, each ended by LF, CRLF or a lone CR."""

    import re

    result = plan.scope.completed.semantic_result
    path = result.modules[plan.scope.selected_owner.module_position].path

    @functools.cache
    def lines() -> tuple[str, ...]:
        for snapshot in result.trusted_source_snapshots:
            if snapshot.path == path:
                return tuple(
                    re.split(r"\r\n|\r|\n", snapshot.source_text.removeprefix("\ufeff"))
                )
        return ()

    def written(span) -> bool:
        text = lines()
        return (
            span.path == path
            and span.line == span.end_line
            and 0 < span.line <= len(text)
            and re.fullmatch(
                "[0-9](?:_?[0-9])*",
                text[span.line - 1][span.column - 1 : span.end_column - 1],
            )
            is not None
        )

    return written


def mysql_division_cells(plan, items, columns) -> frozenset:
    """R08: the Int `/` cells of a MySQL projection stage (template T08-1),
    asked once per stage. The query is mysql_checked_query's without a WHERE,
    bind-safe slots admitted, and each SELECT item (``items``, over the
    realized ``columns``) is, as its whole value, either a direct read of an
    Int source field of a MYSQL_DIVISION_CARRIERS storage or a `/` of an Int
    literal token and one such read, in either order (shapes b and c, whose
    proof mysql_division_law reads from the literal's value); nothing in one
    comes from a `def`, and one item of any other kind, an S01 or S15 cell
    included, closes every cell of the statement. The work is linear in the
    items and the module's text."""

    if (
        not mysql_checked_query(plan, aggregate=False, slots=True)
        or plan.blocks[0].kind is not row.ProjectSQLStageKind.PROJECTION
    ):
        return frozenset()
    written = _mysql_number_token(plan)
    cells = set()
    for item in items:
        expression = _mysql_item_value(plan, item)
        if expression is None:
            return frozenset()
        if type(expression) is row.ProjectSQLBinary:
            left, right = (
                _planned(plan, operand)
                for operand in (expression.left, expression.right)
            )
            if (
                expression.expression.operator != "/"
                or value_tag(expression) != "Int"
                or not (
                    _mysql_division_literal(left, written)
                    and _mysql_division_read(columns, right)
                    or _mysql_division_read(columns, left)
                    and _mysql_division_literal(right, written)
                )
            ):
                return frozenset()
            cells.add(expression.ref)
        elif not _mysql_division_read(columns, expression):
            return frozenset()
    return frozenset(cells)


# MC E4 (MC.04): the MySQL Float `+`, `-` and `*` of a finite DOUBLE source
# field and a Float literal, in either order, and the unary `-` of such a
# field, as the whole value of a SELECT item of S01's cell query. MySQL's
# DOUBLE operators raise 1690 (SQLSTATE 22003) at overflow as PostgreSQL's
# float8 ones raise 22003, and `*` renders MYSQL_PRODUCT_GUARD (MC.05).
E4_OPERATORS = {"binary": ("+", "-", "*"), "unary": ("-",)}


def mysql_float_literal(value) -> bool:
    """An E4 literal operand: a finite Float literal token, or one `-` over
    one; never a slot, a header parameter, a field or another sign."""
    try:
        nodes = parameters.value_nodes(value)
        signs = nodes[:-2]
        literal = (
            type(nodes[-1]) is parameters.SQLLiteral
            and parameters.tag_of(nodes[-1].original) == "Float"
        )
        signed = all(sign.original.expression.operator == "-" for sign in signs)
    except (AttributeError, IndexError, TypeError, ValueError):
        return False
    return (
        literal
        and signed
        and len(signs) <= 1
        and _float_literal_value(value) is not None
    )


def mysql_float_operands(values) -> bool:
    """The operand carriers of an E4 cell: finite MySQL DOUBLE values that no
    binding proves, the carriers the qualification probed."""
    return bool(values) and all(
        float_carrier(value, "mysql") and not value.binding for value in values
    )


def mysql_float_arithmetic_cell(plan, expression, values) -> bool:
    """E4: a MySQL Float `+`, `-` or `*` is in its cell when one operand is a
    source field (mysql_field) and the other a Float literal
    (mysql_float_literal), in either order, and a unary `-` when its operand
    is a source field; the operation is the whole value of a SELECT item of
    the emitted query, and the query is mysql_checked_query's (one WHERE at
    most, no slot). Its carriers are mysql_float_operands'."""

    site = getattr(expression, "site", None)
    kind = {row.ProjectSQLBinary: "binary", row.ProjectSQLUnary: "unary"}.get(
        type(expression)
    )
    return (
        kind is not None
        and expression.expression.operator in E4_OPERATORS[kind]
        and len(values) == (2 if kind == "binary" else 1)
        and sum(mysql_field(value) for value in values) == 1
        and all(mysql_field(value) or mysql_float_literal(value) for value in values)
        and type(site) is row.ProjectSQLExpressionSite
        and site.role is row.ProjectSQLExpressionRole.SELECT
        and site.occurrence.expression is expression.expression
        and mysql_checked_query(plan, aggregate=False)
    )


# MC.05: MySQL's guarded Float `*`, as (role, text) between the operands x, y,
# x, y, x, y in their written order. A product of two non-zero operands that
# rounds to zero takes the BIGINT branch, which raises 1690 (SQLSTATE 22003)
# where PostgreSQL's float8 `*` raises 22003; MySQL alone returns the zero.
MYSQL_PRODUCT_GUARD = (
    ("product_guard_open", "CASE WHEN ("),
    ("arithmetic_operator", " * "),
    ("product_guard_zero", ") = 0 AND "),
    ("product_guard_and", " <> 0 AND "),
    (
        "product_guard_then",
        " <> 0 THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) ELSE (",
    ),
    ("arithmetic_operator", " * "),
    ("product_guard_close", ") END"),
)


def mysql_guarded_product(family: str, operation) -> bool:
    """Whether one realized operation renders MYSQL_PRODUCT_GUARD: a MySQL
    Float `*` that no literal fold proves, which only an E4 cell admits."""
    return (
        family == "mysql"
        and operation.kind == "arithmetic"
        and operation.original.expression.operator == "*"
        and operation.realization.tag == "Float"
        and any(_float_literal_value(o) is None for o in operation.operands)
    )


# The compiled record kinds a cell's bundle may hold (D77.24 whitelist), the
# source's metadata and any literal or WHERE predicate call included; any
# other kind (a parameter, slot, native use, block, capture or ANY read,
# match, window, JOIN, result but an S02 terminal's (MC G3), set, VALUES,
# table function, Unnest, a legacy scan, or a kind a later format adds)
# closes its cells. A bind-safe slot and its native use close all but R08's
# and an S02 sum's, a header parameter and its reads all but an S02 sum's
# (MC G5; mysql_compiled_cells).
_MYSQL_CELL_RECORDS = frozenset(
    {
        "aggregate",
        "aggregate_value",
        "declaration",
        "entry",
        "expression_context",
        "field",
        "literal",
        "null_literal",
        "operation",
        "output",
        "policy",
        "port",
        "predicate_argument",
        "predicate_call",
        "premise",
        "provider",
        "read",
        "requirement",
        "requirement_link",
        "requirement_origin",
        "row",
        "site",
        "source",
        "source_unique",
        "target",
        "use",
    }
)
# MC E4: each compiled operator of an E4 cell and its operand count.
_E4_COMPILED = {
    ("binary", "+"): 2,
    ("binary", "-"): 2,
    ("binary", "*"): 2,
    ("unary", "-"): 1,
}
_MYSQL_CHECKED_OPERATORS = frozenset(
    {
        ("binary", "+"),
        ("binary", "-"),
        ("binary", "*"),
        ("unary", "+"),
        ("unary", "-"),
        ("scalar_call", "abs"),
    }
)


def mysql_compiled_cells(
    records, entry
) -> tuple[frozenset, frozenset, frozenset, frozenset, frozenset]:
    """Compiled replay's S01 operations, S02 aggregate values, S15 `%`, R08
    `/` and MC E4 Float operations in their cells, from the records alone, as
    emission derives them from the plan (mysql_checked_cell, mysql_sum_query,
    mysql_remainder_cells, mysql_division_cells, mysql_float_arithmetic_cell).
    A relation alias or a window,
    read or not, and an imported source leave a direct read's records apart
    from source positions and the source digest, so only emission refuses
    them.

    The entry's terminal is a projection row of its declaration over one
    aggregate of that declaration at most, over one WHERE row of it at most,
    over a source; no other row or aggregate exists and every record is of a
    kind in _MYSQL_CELL_RECORDS. Beside an aggregate (MC G3) the terminal may
    instead be a result record of the declaration over that projection row,
    which may stand over one HAVING row over the aggregate. One pass marks each port that carries a
    source field: a source port, or a port of that WHERE row that reads a
    marked port. An S01 operation is a whole value of the terminal row that
    no other counted record names (a requirement only anchors it, a port
    repeats its row's value), over reads of marked ports. An S02 value is a
    sum over a read of a marked port; the projection row only reads its
    aggregate's ports (or its HAVING row's), S02's own law or MC G2's holds
    of the aggregate, and MC G3's of the HAVING row and the result.
    S02's: one key at most, a read of a marked non-null Int port, and sums,
    counts and mins only (MYSQL_SUM_STAGE_FUNCTIONS). G2's: each key a read
    of a marked port whose field's physical storage is of
    MYSQL_SUM_KEY_KINDS, and each value a sum, count or min or a
    `count_distinct`, `max` or `avg` of one such read of its
    MYSQL_SUM_BESIDE storage. MC G7 counts a conditional sum as a sum: its
    value is one when it reads a marked port and its test is
    mysql_sum_test's, from the records (_mysql_compiled_test), and, as in
    emission (mysql_sum_query), an aggregate beside one at either level
    keeps G2's cell alone: no HAVING row, result record, upstream, JOIN,
    header parameter or bind-safe slot.
    Below its WHERE row, an S02 aggregate may stand over one `let` row of
    its declaration per value `let`, whose ports are marked as the WHERE
    row's are and which keeps MC G1's law (_mysql_compiled_lets). MC G4:
    below them, the projection row of one upstream declaration may stand
    over its own aggregate, WHERE row and `let` rows (one each at most but
    the `let`s), over the source: a plain one's ports are marked as the
    WHERE row's are, and an aggregating one keeps S02's or G2's law with a
    key and a sum, and each of its sums reaches an argument or a `let` value
    of the query, which then has no WHERE row and no clause. Its aggregate
    reads follow _mysql_upstream_read for extremes and averages (upstream_law);
    the query's keys and arguments may read its projected keys and values,
    whose carriers follow their function (storage_kind). MC G6: in place of
    such an upstream, the query's own rows may stand over a chain of JOINs
    of its declaration that keeps _mysql_compiled_joins in place of the
    source, each port of a JOIN marked when its value reads a marked port,
    under G2's law alone and with no HAVING row, result record, header
    parameter or bind-safe slot. Beside a key or a `count` or `min` that
    reads a field of `my_smallint` storage (followed through the chain's
    carries), at the query's aggregate or an upstream's, S02's own law
    holds, the aggregate stands over no `let` row, upstream or JOIN, under
    no HAVING row or result, beside no header parameter or bind-safe slot,
    and its every sum is an unconditional sum of a nullable BIGINT field (mysql_sum_smallint).
    S15 cells need a terminal straight over the source, each of whose values
    is a read of a marked port whose field's physical storage is its tag's
    MYSQL_REMAINDER_CARRIERS one, or a `%` that no other counted record
    names over two such reads of its own tag; any other value closes them.
    R08 cells need the same terminal, each of whose values is a read of a
    marked port whose Int field's physical storage is one of
    MYSQL_DIVISION_CARRIERS, or a `/` that no other counted record names of an
    Int literal record (a sign over one is an operation) and one such read,
    in either order; any other value, or a bind-safe slot of another literal,
    closes them. An E4 operation is, as an S01 one, a whole value of the
    terminal row that no other counted record names: a Float `+`, `-` or `*`
    of one read of a marked port whose field's physical storage is
    `my_double` and one Float literal record (or a `-` operation over one),
    in either order, or a `-` of such a read. A slot or native use record
    closes every other cell outside an aggregate, and a header parameter
    record every cell outside one. MC G5: beside an aggregate, header
    parameters, their reads and bind-safe slots keep placeholders_law, and a
    HAVING line may compare a sum by `>` or `>=` with a non-null Int
    parameter (clauses_law)."""

    empty: tuple[frozenset, frozenset, frozenset, frozenset, frozenset] = (
        frozenset(),
        frozenset(),
        frozenset(),
        frozenset(),
        frozenset(),
    )
    owner = entry.get("declaration")
    terminal = records[entry.get("terminal")]
    # MC G3: ORDER BY, LIMIT and DISTINCT are one result record over the
    # projection row, HAVING a row between it and its aggregate.
    result = satisfying = None
    if terminal.address.kind == "result":
        result, terminal = terminal, records[terminal.get("input")]
    if terminal.address.kind != "row" or terminal.get("stage") != "projection":
        return empty
    chain, current = [terminal], records[terminal.get("input")]
    if current.address.kind == "row" and current.get("stage") == "satisfying":
        satisfying, current = current, records[current.get("input")]
    if current.address.kind == "aggregate":
        chain.append(current)
        current = records[current.get("input")]
    where = None
    if current.address.kind == "row" and current.get("stage") == "where":
        chain.append(current)
        where = current.address
        current = records[current.get("input")]
    lets = []
    while (
        chain[1:2]
        and chain[1].address.kind == "aggregate"
        and current.address.kind == "row"
        and current.get("stage") == "let"
    ):
        chain.append(current)
        lets.append(current.address)
        current = records[current.get("input")]
    # MC G4, item 5: below the query's aggregate, the projection row of one
    # upstream declaration may stand over that declaration's own aggregate
    # (at most), WHERE row (at most) and `let` rows, over the source.
    upper: list = []
    if (
        chain[1:2]
        and chain[1].address.kind == "aggregate"
        and current.address.kind == "row"
        and current.get("stage") == "projection"
        and current.get("owner") != owner
    ):
        upper, current = [current], records[current.get("input")]
        if current.address.kind == "aggregate":
            upper.append(current)
            current = records[current.get("input")]
        if current.address.kind == "row" and current.get("stage") == "where":
            upper.append(current)
            current = records[current.get("input")]
        while current.address.kind == "row" and current.get("stage") == "let":
            upper.append(current)
            current = records[current.get("input")]
    # MC G6: or, in place of an upstream, a chain of the declaration's JOINs.
    joins = []
    while (
        not upper
        and chain[1:2]
        and chain[1].address.kind == "aggregate"
        and current.address.kind == "join"
    ):
        uses = current.get("inputs")
        if not uses or current in joins:
            return empty
        joins.append(current)
        current = records[records[uses[0]].get("producer")]
    clauses = tuple(unit for unit in (satisfying, result) if unit is not None)
    if (
        current.address.kind != "source"
        or any(unit.get("owner") != owner for unit in (*chain, *clauses, *joins))
        or any(unit.get("owner") != upper[0].get("owner") for unit in upper)
        or clauses
        and not (chain[1:2] and chain[1].address.kind == "aggregate")
        # MC G6: no G3 clause over JOIN rows.
        or joins
        and (clauses or not _mysql_compiled_joins(records, joins))
    ):
        return empty
    from pietto._project.project_compiled_schema import Address

    units = {unit.address for unit in (*chain, *upper, *clauses, *joins)}
    # MC G6: the JOINs whose ports carry their inputs' fields.
    joined = {unit.address for unit in joins}
    # A row that carries a field: a WHERE or `let` row, or a plain upstream's
    # projection (MC G4), whose ports are then marked as the WHERE row's are.
    carriers = {
        unit.address
        for unit in (*chain, *upper)
        if unit.address.kind == "row" and unit is not terminal
    }
    inner = upper[1] if upper[1:2] and upper[1].address.kind == "aggregate" else None
    marked, named, slotted = set(), {}, set()
    parameters, reads, held = {}, set(), {}
    for address, record in records.items():
        kind = address.kind
        if kind == "slot":
            slotted.add(record.get("literal"))
            continue
        if kind == "native_use":
            continue
        # MC G5: a header parameter and each read of one.
        if kind == "parameter":
            parameters[address] = record
            continue
        if kind == "parameter_read":
            reads.add(address)
            continue
        if (
            kind not in _MYSQL_CELL_RECORDS
            and kind != "result"
            and not (joined and kind in ("join", "join_value"))
            or kind in {"row", "aggregate", "result", "join"}
            and address not in units
        ):
            return empty
        pending = [] if kind in {"requirement", "port"} else list(record.values)
        while pending:
            item = pending.pop()
            if type(item) is tuple:
                pending.extend(item)
            elif type(item) is Address and item.kind == "operation":
                named.setdefault(item, []).append(address)
            elif type(item) is Address and item.kind in ("parameter_read", "literal"):
                held.setdefault(item, []).append(address)
        if kind == "port":
            port_owner, port_source = record.get("owner"), record.get("source")
            if port_owner.kind == "source" or (
                port_owner in carriers
                and port_source is not None
                and port_source.kind == "read"
                and records[port_source].get("port") in marked
                # MC G6: a JOIN's port carries its input's through its value.
                or port_owner in joined
                and port_source is not None
                and port_source.kind == "join_value"
                and records[records[port_source].get("input")].get("port") in marked
            ):
                marked.add(address)

    def field(address) -> bool:
        return address.kind == "read" and records[address].get("port") in marked

    def carried(address) -> bool:
        """MC G4, item 5: a field read, or a read of an aggregating
        upstream's projected key or value, directly or through the query's
        `let` rows (each step down to a lower unit's port)."""
        if field(address):
            return True
        if address.kind != "read" or inner is None:
            return False
        port = records[records[address].get("port")]
        for _ in range(len(lets) + 1):
            source = port.get("source")
            if port.get("owner") not in lets or getattr(source, "kind", None) != "read":
                break
            port = records[records[source].get("port")]
        source = port.get("source")
        return (
            port.get("owner") == upper[0].address
            and getattr(source, "kind", None) == "read"
            and records[records[source].get("port")].get("owner") == inner.address
        )

    def storage_kind(address) -> object:
        """The physical storage kind of the source field that a read of a
        marked port reads through the chain's carries; MC G4: or the carrier
        of an upstream's value, by its function (a sum's `my_signed_int`, a
        count's `my_bigint`, an `avg`'s `my_double`, a `min` or `max` its
        field's, but the `my_signed_int` of MySQL's SIGNED cast of one of a
        SMALLINT or INT field, no key or `max`, `avg` or `count_distinct`
        argument storage: MC G4, item 5). Each step reads a lower unit's
        port."""
        port = records[address].get("port")
        for _ in range(len(units) + 1):
            if records[port].get("owner").kind == "source":
                break
            source = records[port].get("source")
            # MC G6: a JOIN's port carries its input's through its value.
            if getattr(source, "kind", None) == "join_value":
                source = records[source].get("input")
            if getattr(source, "kind", None) == "aggregate_value":
                value = records[source]
                function, arguments = value.get("function"), value.get("arguments")
                if function in ("min", "max"):
                    kind = (
                        storage_kind(arguments[0])
                        if len(arguments) == 1 and field(arguments[0])
                        else None
                    )
                    return (
                        "my_signed_int" if kind in ("my_smallint", "my_int") else kind
                    )
                return _MYSQL_UPSTREAM_CARRIERS.get(function)
            if getattr(source, "kind", None) != "read":
                return None
            port = records[source].get("port")
        else:
            return None
        try:
            physical = records[records[port].get("source")].get("physical")
            return json.loads(physical)["storage"]["kind"]
        except (KeyError, TypeError, ValueError):
            return None

    def upstream_function(address):
        """Follow a read's carries to the upstream aggregate it reads."""
        port = records[address].get("port") if address.kind == "read" else None
        for _ in range(len(units) + 1):
            if port is None:
                break
            source = records[port].get("source")
            if getattr(source, "kind", None) == "aggregate_value":
                return records[source].get("function")
            if getattr(source, "kind", None) != "read":
                break
            port = records[source].get("port")
        return None

    def smallint(address) -> bool:
        """mysql_sum_smallint's read: of a field of `my_smallint` storage."""
        return field(address) and storage_kind(address) == "my_smallint"

    def nullable_bigint(address) -> bool:
        """S02's own sum argument: a read of a nullable BIGINT field."""
        return (
            field(address)
            and storage_kind(address) == "my_bigint"
            and records[records[address].get("port")].get("logical")
            == ("Int", "nullable")
        )

    def own_law(aggregate, read) -> bool:
        """S02's own law of an aggregate whose keys and arguments are
        ``read``s: one key at most, a non-null Int read, and sums, counts
        and mins only (MYSQL_SUM_STAGE_FUNCTIONS)."""
        keys, values = aggregate.get("keys"), aggregate.get("values")
        return (
            len(keys) <= 1
            and all(
                read(key)
                and records[records[key].get("port")].get("logical")
                == ("Int", "non_null")
                for key in keys
            )
            and all(
                records[value].get("function") in MYSQL_SUM_STAGE_FUNCTIONS
                for value in values
            )
        )

    def law(aggregate, read, *, g2_only=False) -> bool:
        """S02's own law (own_law) or MC G2's of an aggregate whose keys and
        arguments are ``read``s: each key a read of MYSQL_SUM_KEY_KINDS
        storage and each value a sum, count or min or a `count_distinct`,
        `max` or `avg` of one read of its MYSQL_SUM_BESIDE storage.
        ``g2_only`` (MC G6, over JOINs): G2's."""
        keys, values = aggregate.get("keys"), aggregate.get("values")
        return (
            not g2_only
            and own_law(aggregate, read)
            or (
                all(
                    read(key) and storage_kind(key) in MYSQL_SUM_KEY_KINDS
                    for key in keys
                )
                and all(
                    records[value].get("function") in MYSQL_SUM_STAGE_FUNCTIONS
                    or len(arguments := records[value].get("arguments")) == 1
                    and read(arguments[0])
                    and storage_kind(arguments[0])
                    in MYSQL_SUM_BESIDE.get(records[value].get("function"), ())
                    for value in values
                )
            )
        )

    def summed(aggregate, read) -> set:
        """The sums of ``aggregate`` over one ``read`` each."""
        return {
            value
            for value in aggregate.get("values")
            if records[value].get("function") == "sum"
            and len(records[value].get("arguments")) == 1
            and read(records[value].get("arguments")[0])
        }

    def upstream_law(aggregate) -> bool:
        """MC G4, item 5, below the query's ``aggregate``: a plain upstream
        projects field reads and has no `let`; an aggregating one keeps
        S02's or G2's law with a key and a sum and MC G1's `let` law, its
        projection reads its aggregate, and each of its sums reaches, through
        that projection, an argument of ``aggregate`` or the value of one of
        the query's `let`s, carried by its WHERE and `let` rows (the query
        then has neither, nor a clause): a sum that the projection does not
        read reaches none; the query holds a sum and reads an upstream
        extreme or average under _mysql_upstream_read."""
        if not upper:
            return True
        lower = [unit for unit in upper[1:] if unit.address.kind == "row"]
        if not any(
            records[value].get("function") == "sum" for value in aggregate.get("values")
        ):
            return False
        if inner is None:
            return not any(unit.get("stage") == "let" for unit in lower) and all(
                field(value) for value in upper[0].get("values")
            )
        if not (
            law(inner, field)
            and inner.get("keys")
            and summed(inner, field)
            and _mysql_compiled_lets(records, lower, inner)
            and all(
                value.kind == "read"
                and records[records[value].get("port")].get("owner") == inner.address
                for value in upper[0].get("values")
            )
            and where is None
            and not clauses
            and all(
                _mysql_upstream_read(
                    records[value].get("function"), origin, storage_kind(arguments[0])
                )
                for value in aggregate.get("values")
                if len(arguments := records[value].get("arguments")) == 1
                and (origin := upstream_function(arguments[0])) is not None
            )
        ):
            return False
        reads = [
            *(
                argument
                for value in aggregate.get("values")
                for argument in records[value].get("arguments")
            ),
            *(records[records[unit].get("outputs")[-1]].get("source") for unit in lets),
        ]
        ports = set()
        for item in reads:
            port = records[item].get("port") if item.kind == "read" else None
            # Down the query's `let` rows' carries to the upstream's port.
            while port is not None and records[port].get("owner") in lets:
                source = records[port].get("source")
                port = records[source].get("port") if source.kind == "read" else None
            ports.add(port)
        outputs, values = upper[0].get("outputs"), upper[0].get("values")
        if len(outputs) != len(values):
            return False
        reached = set()
        for port, value in zip(outputs, values):
            source = records[records[value].get("port")].get("source")
            if (
                getattr(source, "kind", None) == "aggregate_value"
                and records[source].get("function") == "sum"
            ):
                if port not in ports:
                    return False
                reached.add(source)
        return all(
            value in reached
            for value in inner.get("values")
            if records[value].get("function") == "sum"
        )

    def clauses_law(aggregate) -> bool:
        """MC G3, from the records: over an aggregate with a key, the HAVING
        row carries the aggregate's ports in order, and its predicate is the
        `and` of comparisons (MYSQL_TYPED_COMPARISONS) of a read with an
        unsigned Int literal, the read carrying a key of
        MYSQL_SUM_HAVING_KEY_KINDS storage or a value other than `avg`, one
        on a sum alone. The result's projection reads the projection row,
        its each ordering read carries a key of MYSQL_SUM_KEY_KINDS storage
        or a value other than `avg`, a LIMIT is at least 1 after an ordering
        whose first read carries a value, and DISTINCT stands beside no
        `avg`. A read carries what its port's sources lead to at the
        aggregate."""
        if not clauses:
            return True
        outputs = aggregate.get("outputs")

        def value(address, kinds):
            for _ in range(4):
                if getattr(address, "kind", None) != "read":
                    return None
                port = records[records[address].get("port")]
                address = port.get("source")
                if port.get("owner") == aggregate.address:
                    break
            else:
                return None
            if address in aggregate.get("keys"):
                return address if storage_kind(address) in kinds else None
            if address in aggregate.get("values"):
                function = records[address].get("function")
                return address if function != "avg" else None
            return None

        read, pending = [], []
        if satisfying is not None:
            values = satisfying.get("values")
            if len(values) != len(outputs) or not all(
                item.kind == "read" and records[item].get("port") == port
                for item, port in zip(values, outputs)
            ):
                return False
            pending.append(satisfying.get("predicate"))
        while pending:
            address = pending.pop()
            if getattr(address, "kind", None) != "operation":
                return False
            operation = records[address]
            pair = operation.get("operands")
            if operation.get("operator") == ("binary", "and"):
                pending.extend(pair)
                continue
            if not (
                operation.get("operator") in _MYSQL_TYPED_OPERATORS
                and len(pair) == 2
                and pair[1].kind in ("literal", "parameter_read")
            ):
                return False
            literal = records[pair[1]]
            if pair[1].kind == "parameter_read":
                # MC G5: a non-null Int header parameter, by `>` or `>=`.
                parameter = parameters.get(literal.get("parameter"))
                if (
                    parameter is None
                    or (parameter.get("tag"), parameter.get("nullable"))
                    != ("Int", False)
                    or operation.get("operator")
                    not in {
                        ("comparison", comparison)
                        for comparison in MYSQL_SUM_HAVING_PARAMETER_COMPARISONS
                    }
                ):
                    return False
            elif not (
                literal.get("tag") == "Int"
                and type(number := getattr(literal.get("value"), "value", None)) is int
                and number >= 0
            ):
                return False
            read.append(value(pair[0], MYSQL_SUM_HAVING_KEY_KINDS))
        ordering = () if result is None else result.get("ordering")
        keys = [value(item, MYSQL_SUM_KEY_KINDS) for item, _ in ordering]
        limit = None if result is None else result.get("limit")
        values = aggregate.get("values")
        return (
            bool(aggregate.get("keys"))
            and None not in read
            and (
                len(read) <= 1
                or all(
                    records[item].get("function") != "sum"
                    for item in read
                    if item in values
                )
            )
            # MC G5: beside a placeholder, HAVING's one line reads a sum.
            and not (
                (reads or slotted)
                and read
                and not any(
                    item in values and records[item].get("function") == "sum"
                    for item in read
                )
            )
            and None not in keys
            and all(
                item.kind == "read"
                and records[records[item].get("port")].get("owner") == terminal.address
                for item in (() if result is None else result.get("projection"))
            )
            and (
                limit is None
                or type(limit) is int
                and limit >= 1
                and bool(keys)
                and keys[0] in values
            )
            and not (
                result is not None
                and result.get("distinct") is True
                and any(records[item].get("function") == "avg" for item in values)
            )
        )

    def placeholders_law() -> bool:
        """MC G5: each header parameter is a Bool, Int, Float or Text. A read
        is of no Float and stands in the selected WHERE row's predicate, every
        operation over it a Bool one up to that predicate, or in the HAVING
        row's (clauses_law); each bind-safe slot's literal stands in that
        WHERE row's predicate or a plain upstream's WHERE row's."""
        if not (parameters or slotted):
            return True

        def tree(row, boolean) -> set:
            """``row`` and the operations under its predicate, through Bool
            ones alone when ``boolean``."""
            if row is None:
                return set()
            found, pending = {row.address}, [row.get("predicate")]
            while pending:
                item = pending.pop()
                if getattr(item, "kind", None) != "operation" or item in found:
                    continue
                if boolean and records[item].get("logical")[0] != "Bool":
                    continue
                found.add(item)
                pending.extend(records[item].get("operands"))
            return found

        selected = records[where] if where is not None else None
        plain = next(
            (
                unit
                for unit in upper
                if inner is None
                and unit.address.kind == "row"
                and unit.get("stage") == "where"
            ),
            None,
        )
        allowed = tree(selected, True) | tree(satisfying, False)
        bound = tree(selected, False) | tree(plain, False)
        tags = {address: record.get("tag") for address, record in parameters.items()}
        return (
            set(tags.values()) <= {"Bool", "Int", "Float", "Text"}
            and all(
                tags.get(records[item].get("parameter")) not in (None, "Float")
                and held.get(item)
                and set(held[item]) <= allowed
                for item in reads
            )
            and all(held.get(item) and set(held[item]) <= bound for item in slotted)
        )

    if chain[1:2] and chain[1].address.kind == "aggregate":
        aggregate = chain[1]
        if (
            lets
            and not _mysql_compiled_lets(records, chain[2:], aggregate)
            or not placeholders_law()
            # MC G6: no header parameter or bind-safe slot over JOIN rows.
            or joins
            and (parameters or slotted)
            # MC G7: beside a conditional sum, at either level, G2's cell
            # alone: no clause, upstream, JOIN, parameter or slot.
            or any(
                records[value].get("function") == "filtered_sum"
                for unit in (aggregate, inner)
                if unit is not None
                for value in unit.get("values")
            )
            and bool(clauses or upper or joins or parameters or reads or slotted)
        ):
            return empty
        below = aggregate if satisfying is None else satisfying
        if (
            # MC G6: over JOINs, G2's law alone.
            not law(aggregate, carried, g2_only=bool(joins))
            or not upstream_law(aggregate)
            or not all(
                value.kind == "read"
                and records[records[value].get("port")].get("owner") == below.address
                for value in terminal.get("values")
            )
            or not clauses_law(aggregate)
        ):
            return empty
        # mysql_sum_smallint, from the records: beside a SMALLINT key, or a
        # count or min of one SMALLINT field read, of the query's aggregate
        # or an upstream's, S02's own law holds, no upstream, JOIN, `let`
        # row, HAVING row, result, header parameter or bind-safe slot stands
        # and every sum is an unconditional sum of a nullable BIGINT field.
        items = [
            records[value]
            for unit in (aggregate, inner)
            if unit is not None
            for value in unit.get("values")
        ]
        if (
            any(
                smallint(key)
                for unit in (aggregate, inner)
                if unit is not None
                for key in unit.get("keys")
            )
            or any(
                item.get("function") in ("count", "min")
                and len(item.get("arguments")) == 1
                and smallint(item.get("arguments")[0])
                for item in items
            )
        ) and (
            upper
            or joins
            or lets
            or clauses
            or parameters
            or slotted
            or not own_law(aggregate, field)
            or not all(
                item.get("function") not in ("sum", "filtered_sum")
                or item.get("function") == "sum"
                and len(item.get("arguments")) == 1
                and nullable_bigint(item.get("arguments")[0])
                for item in items
            )
        ):
            return empty
        tested: dict = {}

        def kind(address) -> object:
            return storage_kind(address) if field(address) else None

        return (
            frozenset(),
            frozenset(
                summed(aggregate, carried)
                | (summed(inner, field) if inner is not None else set())
                # MC G7: a conditional sum of a field under a G7 test.
                | {
                    value
                    for value in aggregate.get("values")
                    if records[value].get("function") == "filtered_sum"
                    and len(records[value].get("arguments")) == 2
                    and field(records[value].get("arguments")[0])
                    and _mysql_compiled_test(
                        records, records[value].get("arguments")[1], kind, tested
                    )
                }
            ),
            frozenset(),
            frozenset(),
            frozenset(),
        )

    def physical(address) -> tuple[str, Any] | None:
        """The tag and physical storage of the field a read of a marked port
        reads."""
        if not field(address):
            return None
        source = records[records[address].get("port")].get("source")
        if source is None or source.kind != "field":
            return None
        try:
            storage = json.loads(records[source].get("physical"))["storage"]
            tag = records[source].get("logical")[0]
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        return tag, storage

    def carrier(address) -> str | None:
        """S15: the tag of a read of a marked port whose field's physical
        storage is that tag's MYSQL_REMAINDER_CARRIERS one."""
        read = physical(address)
        if read is None:
            return None
        return read[0] if MYSQL_REMAINDER_CARRIERS.get(read[0]) == read[1] else None

    def division_read(address) -> bool:
        """R08: a read of a marked port of an Int field of a
        MYSQL_DIVISION_CARRIERS storage."""
        read = physical(address)
        return (
            read is not None and read[0] == "Int" and read[1] in MYSQL_DIVISION_CARRIERS
        )

    def literal(address) -> bool:
        """R08: an Int literal token's record."""
        return address.kind == "literal" and records[address].get("tag") == "Int"

    if parameters:
        return empty
    divisions, operands = set(), set()
    for value in terminal.get("values") if where is None else ():
        operation = records[value] if value.kind == "operation" else None
        pair = () if operation is None else operation.get("operands")
        if (
            not division_read(value)
            if operation is None
            else named.get(value) != [terminal.address]
            or operation.get("operator") != ("binary", "/")
            or operation.get("logical")[0] != "Int"
            or len(pair) != 2
            or not (
                literal(pair[0])
                and division_read(pair[1])
                or division_read(pair[0])
                and literal(pair[1])
            )
        ):
            divisions.clear()
            break
        if operation is not None:
            divisions.add(value)
            operands.update(pair)
    if not slotted <= operands:
        divisions.clear()
    if slotted:
        return frozenset(), frozenset(), frozenset(), frozenset(divisions), frozenset()

    remainders = set()
    for value in terminal.get("values") if where is None else ():
        operation = records[value] if value.kind == "operation" else None
        if (
            carrier(value) is None
            if operation is None
            else named.get(value) != [terminal.address]
            or operation.get("operator") != ("binary", "%")
            or {carrier(item) for item in operation.get("operands")}
            != {operation.get("logical")[0]}
            or len(operation.get("operands")) != 2
        ):
            remainders.clear()
            break
        if operation is not None:
            remainders.add(value)

    def double(address) -> bool:
        """E4: a read of a marked port of a `my_double` Float field, the
        port a source port or a WHERE row's port that reads one."""
        if not field(address):
            return False
        source = records[records[address].get("port")].get("source")
        if source is not None and source.kind == "read":
            source = records[records[source].get("port")].get("source")
        if source is None or source.kind != "field":
            return False
        try:
            storage = json.loads(records[source].get("physical"))["storage"]
            tag = records[source].get("logical")[0]
        except (KeyError, IndexError, TypeError, ValueError):
            return False
        return (tag, storage) == ("Float", {"kind": "my_double"})

    def float_literal(address) -> bool:
        """E4: a Float literal record, or a `-` operation over one."""
        record = records[address]
        if (
            address.kind == "operation"
            and record.get("operator") == ("unary", "-")
            and len(record.get("operands")) == 1
        ):
            address = record.get("operands")[0]
        return address.kind == "literal" and records[address].get("tag") == "Float"

    floats = set()
    for value in terminal.get("values"):
        operation = records[value] if value.kind == "operation" else None
        operator = None if operation is None else operation.get("operator")
        operands = () if operation is None else operation.get("operands")
        if (
            operation is not None
            and named.get(value) == [terminal.address]
            and operation.get("logical")[0] == "Float"
            and operator in _E4_COMPILED
            and len(operands) == _E4_COMPILED[operator]
            and sum(double(item) for item in operands) == 1
            and all(double(item) or float_literal(item) for item in operands)
        ):
            floats.add(value)
    return (
        frozenset(
            value
            for value in terminal.get("values")
            if named.get(value) == [terminal.address]
            and records[value].get("operator") in _MYSQL_CHECKED_OPERATORS
            and records[value].get("operands")
            and all(field(item) for item in records[value].get("operands"))
        ),
        frozenset(),
        frozenset(remainders),
        frozenset(divisions),
        frozenset(floats),
    )


def _mysql_compiled_joins(records, joins) -> bool:
    """MC G6, from the records: ``joins``, from the last down, each `inner`,
    `left` or `right`, with no relationship equality, its earlier input
    (ordinal 0) a source for the last one walked and otherwise the next JOIN,
    as mysql_compiled_cells walks them, and its joined input (ordinal 1) a
    source. Its predicate is a
    conjunction (`and` operations) of linking equalities, one at least, an
    `==` of reads of an Int port of each input, and, unless it is a `right`
    JOIN, of `>` or `>=` comparisons of a read of a non-null Int port of the
    joined input with a non-negative Int literal. Linear in the JOINs and
    their predicates."""

    for join in joins:
        uses = tuple(records[use] for use in join.get("inputs"))
        if (
            join.get("kind") not in MYSQL_JOIN_KINDS
            or join.get("equalities")
            or join.get("predicate") is None
            or [use.get("ordinal") for use in uses] != [0, 1]
            or uses[1].get("producer").kind != "source"
        ):
            return False

        def read(address):
            """(side, nullability) of a read of an Int port of one input, side
            1 the joined input; or None."""
            if address.kind != "read":
                return None
            use, port = records[address].get("use"), records[address].get("port")
            logical = records[port].get("logical")
            if use not in join.get("inputs") or port not in records[use].get("ports"):
                return None
            side = join.get("inputs").index(use)
            return (side, logical[1]) if logical[0] == "Int" else None

        linked, pending = False, [join.get("predicate")]
        while pending:
            address = pending.pop()
            if address.kind != "operation":
                return False
            operator = records[address].get("operator")
            operands = records[address].get("operands")
            if operator == ("binary", "and") and len(operands) == 2:
                pending.extend(operands)
                continue
            if operator[0] != "comparison" or len(operands) != 2:
                return False
            left, right = read(operands[0]), read(operands[1])
            if operator[1] == "==" and left and right and {left[0], right[0]} == {0, 1}:
                linked = True
                continue
            literal = records[operands[1]] if operands[1].kind == "literal" else None
            value = (
                None
                if literal is None
                else getattr(literal.get("value"), "value", None)
            )
            if not (
                operator[1] in (">", ">=")
                and join.get("kind") != "right"
                and left == (1, "non_null")
                and literal is not None
                and literal.get("tag") == "Int"
                and type(value) is int
                and value >= 0
            ):
                return False
        if not linked:
            return False
    return True


def _mysql_compiled_test(records, address, kind, tested) -> bool:
    """MC G7, from the records: a conditional sum's test as mysql_sum_test
    reads it, ``kind`` the physical storage kind of the field that a read
    of a marked port reads (None for any other address). ``tested``
    remembers each operation's verdict, False while it is being read, so a
    shared operand is read once and a cycle is refused."""

    if address.kind != "operation":
        return kind(address) == "my_bool01"
    if address in tested:
        return tested[address]
    tested[address] = False
    operation = records[address]
    operator, operands = operation.get("operator"), operation.get("operands")
    if operator in (("binary", "and"), ("binary", "or")):
        verdict = len(operands) == 2 and all(
            _mysql_compiled_test(records, item, kind, tested) for item in operands
        )
    elif operator in (("not", "not"), ("null_test", "is_null")):
        verdict = (
            len(operands) == 1
            and (operator[0] == "not" or operands[0].kind == "read")
            and _mysql_compiled_test(records, operands[0], kind, tested)
        )
    elif operator == ("comparison", ">") and len(operands) == 2:
        left, right = operands
        if (
            right.kind == "operation"
            and records[right].get("operator") == ("unary", "-")
            and len(records[right].get("operands")) == 1
        ):
            right = records[right].get("operands")[0]
        verdict = (
            kind(left) in ("my_bigint", "my_int")
            and right.kind == "literal"
            and records[right].get("tag") == "Int"
            and type(getattr(records[right].get("value"), "value", None)) is int
            and records[right].get("value").value >= 0
        )
    else:
        verdict = False
    tested[address] = verdict
    return verdict


def _mysql_compiled_lets(records, rows, aggregate) -> bool:
    """MC G1, from the records: below ``aggregate`` (``rows``, from it
    down), the last port of each `let` row is its value and every other
    port of a row carries its input's. The ports that a `let` derives, its
    value or a carry of one, are found first from the source up, in chain
    order and so in no record order or numbering. Then every reference to a
    read of one, but a requirement's (which only anchors it), is the source
    of the port that carries it (its row's values repeat its ports'
    sources) or an argument of a sum of ``aggregate``, so a read shared
    with another user counts too, and each value is read at least once so.
    Linear in the records."""

    from pietto._project.project_compiled_schema import Address

    derived, carries, values = {}, set(), set()
    for unit in reversed(rows):
        outputs = unit.get("outputs")
        if unit.get("stage") == "let":
            values.update(outputs[-1:])
            derived.update((value, value) for value in outputs[-1:])
            outputs = outputs[:-1]
        for port in outputs:
            source = records[port].get("source")
            origin = (
                derived.get(records[source].get("port"))
                if getattr(source, "kind", None) == "read"
                else None
            )
            if origin is not None:
                derived[port] = origin
                carries.add(port)
    sums = {
        value
        for value in aggregate.get("values")
        if records[value].get("function") == "sum"
    }
    chain = {unit.address for unit in rows}
    used = set()
    for address, record in records.items():
        if address.kind in ("read", "requirement"):
            continue
        pending = [record.get("predicate")] if address in chain else list(record.values)
        while pending:
            item = pending.pop()
            if type(item) is tuple:
                pending.extend(item)
            elif (
                type(item) is Address
                and item.kind == "read"
                and records[item].get("port") in derived
            ):
                if address in sums and item in record.get("arguments"):
                    used.add(derived[records[item].get("port")])
                elif not (address in carries and record.get("source") == item):
                    return False
    return used == values


# The MySQL project cells of lpad and now() that the Phase77 native
# qualification preregisters, as (name, place, operand kinds). The call is the
# whole value of a SELECT item of the emitted query ("select"), or now() is
# the one argument of the `date_of` that is ("select_date_of"); lpad reads a
# source field or a Text literal with a literal width and fill. Emission, the
# live verifier, compiled replay and the pure boundary each derive a call's
# cell from their own record; every other MySQL lpad and now() is refused.
MYSQL_SCALAR_CELLS = frozenset(
    {
        ("lpad", "select", ("field", "literal", "literal")),
        ("lpad", "select", ("literal", "literal", "literal")),
        ("now", "select", ()),
        ("now", "select_date_of", ()),
    }
)
# Clauses that leave the emitted query outside every cell (Q2).
_MYSQL_CELL_CLAUSES = (
    "distinct_clause",
    "group_by_clause",
    "order_by_clause",
    "limit_clause",
    "satisfying_clause",
    "qualify_clause",
)
# Compiled records whose presence leaves every cell closed: a header parameter
# or its read, a bind-safe slot or native marker (Q3) and an aggregate (Q2).
_MYSQL_CELL_CLOSING_RECORDS = frozenset(
    {"parameter", "parameter_read", "slot", "native_use", "aggregate"}
)
# Compiled units, each owned by one declaration (Q4).
_MYSQL_UNIT_RECORDS = frozenset(
    {
        "scan",
        "row",
        "join",
        "window",
        "result",
        "set",
        "values",
        "table_function",
        "unnest",
    }
)


def mysql_scalar_place(plan, expression):
    """The place of one call in MYSQL_SCALAR_CELLS, from the plan, or None.

    Q1: the call, or the `date_of` that is its only argument, is the whole
    value of a SELECT item of the emitted query. Q2: that query reads a source
    through let, where and window stages only, with no JOIN, aggregate,
    satisfying, QUALIFY, DISTINCT, ORDER BY or LIMIT. Q3: the emitted query
    has no header parameter, no server parameter and no Collect. Q4: it has no
    block read but the one _mysql_capture_read admits. Every check is O(1)
    but one fact per plan, which _reads_captured_field computes once.
    """
    # The plan module stays out of this module's imports: runtime modules
    # load these realizations without it.
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    site = getattr(expression, "site", None)
    if (
        plan.parameters
        or plan.literal_slots
        or plan.bind_uses
        or plan.collects
        or plan.aggregations
        or type(site) is not row.ProjectSQLExpressionSite
        or site.role is not row.ProjectSQLExpressionRole.SELECT
        or site.owner is not plan.scope.selected_owner
    ):
        return None
    index = site.block.position
    block = plan.blocks[index] if 0 <= index < len(plan.blocks) else None
    body = site.owner.definition
    if (
        block is None
        or block.ref is not site.block
        or block.kind is not row.ProjectSQLStageKind.PROJECTION
        or type(block.boundary) is not ProjectSQLBoundary
        or block.boundary.reason is not ProjectSQLBoundaryReason.SOURCE_INPUT
        or any(getattr(body, name, None) is not None for name in _MYSQL_CELL_CLAUSES)
        or getattr(body, "join_clauses", ())
        or getattr(body, "join_filters", ())
        or plan.expression_block_uses
        and not _mysql_capture_read(plan, block)
    ):
        return None
    value = site.occurrence.expression
    if value is expression.expression:
        return "select"
    if (
        type(value) is CallExpr
        and type(value.callee) is NameExpr
        and value.callee.name == "date_of"
        and len(value.arguments) == 1
        and value.arguments[0] is expression.expression
    ):
        return "select_date_of"
    return None


def _mysql_capture_read(plan, block) -> bool:
    """Q4: the plan's one block read is a scalar read of its one capturing
    let and the whole value of a SELECT item of the emitted query, whose
    projection ``block`` is its first stage. The let reads a source directly,
    through a WHERE at most, and reads a captured field; the plan holds no
    other block (so at most three), JOIN, set, values, Unnest or result
    stage. Each check is O(1) but the captured field read, which
    _reads_captured_field answers once per plan."""
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    uses, captures = plan.expression_block_uses, plan.captures
    if len(uses) != 1 or len(captures) != 1 or len(plan.blocks) > 3:
        return False
    capture = captures[0]
    read = capture.read
    found = (
        plan.expressions[read.position]
        if 0 <= read.position < len(plan.expressions)
        else None
    )
    return (
        block.position == 0
        and found is not None
        and found.ref is read
        and type(found.expression) is RelationScalarExpr
        and getattr(found, "use", None) is uses[0].ref
        and found.site.role is row.ProjectSQLExpressionRole.SELECT
        and found.site.owner is plan.scope.selected_owner
        and found.site.occurrence.expression is found.expression
        and not (
            plan.joins
            or plan.set_bodies
            or plan.values_bodies
            or plan.unnests
            or plan.distincts
            or plan.orders
            or plan.result_limits
        )
        and all(
            other is block
            or other.definition is capture.inner
            and other.kind
            in (row.ProjectSQLStageKind.WHERE, row.ProjectSQLStageKind.PROJECTION)
            and type(other.boundary) is ProjectSQLBoundary
            and other.boundary.reason is ProjectSQLBoundaryReason.SOURCE_INPUT
            for other in plan.blocks
        )
        and _reads_captured_field(plan)
    )


@functools.lru_cache(maxsize=1)
def _reads_captured_field(plan) -> bool:
    """Whether an expression of the plan reads a captured field. Every MySQL
    lpad and now() call of one plan asks, so the last plan's answer is kept;
    the cache holds that plan, so its identity is never reused."""

    return any(type(item) is row.ProjectSQLCapturedField for item in plan.expressions)


def mysql_operand_kind(value) -> str:
    """The kind of one operand: "field" for a source field read, directly or
    carried or renamed by the query's own stages (never a let value, literal
    origin, aggregate or window result, or another query's output), "literal"
    for an inline literal, and "other" otherwise."""

    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind

    if type(value) is SQLStageReference:
        column = value.column
        return (
            "field"
            if getattr(column.terminal, "kind", None)
            in {ProjectSQLPlanRefKind.SOURCE_PORT, ProjectSQLPlanRefKind.STAGE_PORT}
            and column.field is not None
            and column.source_port is not None
            and column.literal is None
            and column.aggregate is None
            and column.window is None
            else "other"
        )
    if (
        type(value) is parameters.SQLAnchor
        and type(value.operand) is parameters.SQLLiteral
    ):
        return "literal"
    return "other"


def mysql_scalar_cell(plan, expression, values):
    """The (name, place, operand kinds) cell of one MySQL lpad or now() call,
    or None for any other call and while emission derives as main (AS_MAIN)."""

    symbol = expression.callee_symbol
    if (
        AS_MAIN.get()
        or symbol.namespace is not SymbolNamespace.CALLABLE
        or symbol.name not in {"lpad", "now"}
    ):
        return None
    return (
        symbol.name,
        mysql_scalar_place(plan, expression),
        tuple(mysql_operand_kind(value) for value in values),
    )


def mysql_compiled_scalar_cells(records, entry) -> dict:
    """Compiled replay's cells of the selected entry, from its records alone,
    keyed by operation, as mysql_scalar_cell derives them from the plan.

    Q1: the operation is a whole value of the entry's terminal projection
    row, or the one operand of a `date_of` that is, and no other record names
    either: records may share an operation, which a SELECT item never does.
    A requirement only anchors an operation and a port repeats its row's
    value (ROW_SHAPE), so neither counts. Q2: below that row are, in
    emission's order, its declaration's window at most, one WHERE row at most
    and let rows, then a source; a predicate binds a where or qualify row
    (ROW_PREDICATE), and the order tells a WHERE from a QUALIFY.
    Q2 and Q3: no record is an aggregate, a parameter, its read, a slot or a
    native use. Q4: no expression block use, or one that
    _mysql_compiled_capture_read admits beside a read of a captured field.
    One pass in address order checks the records and marks each port that
    carries a source field: a source port, or a port of the declaration's row
    or window that reads a marked port. An operand is a "field" when it reads
    a marked port and a "literal" when it is a literal record; a port that
    reads a later port stays unmarked, so its reader is "other" and refused.
    """

    owner = entry.get("declaration")
    terminal = records[entry.get("terminal")]
    if (
        terminal.address.kind != "row"
        or terminal.get("stage") != "projection"
        or terminal.get("owner") != owner
    ):
        return {}
    current, stages = records[terminal.get("input")], []
    while current.address.kind == "window" or (
        current.address.kind == "row" and current.get("stage") in {"let", "where"}
    ):
        if current.get("owner") != owner:
            return {}
        stages.append(
            current.get("stage") if current.address.kind == "row" else "window"
        )
        current = records[current.get("input")]
    # Emission's order from the terminal down: a window at most, then a WHERE
    # at most, then lets. A QUALIFY row relabelled where sits over its window.
    for stage in ("window", "where"):
        if stages[:1] == [stage]:
            del stages[0]
    if current.address.kind != "source" or set(stages) - {"let"}:
        return {}
    from pietto._project.project_compiled_schema import Address

    marked, block_reads, captures, owners = set(), [], [], set()
    captured, named = False, {}
    for address, record in records.items():
        kind = address.kind
        if kind in _MYSQL_CELL_CLOSING_RECORDS:
            return {}
        pending = [] if kind in {"requirement", "port"} else list(record.values)
        while pending:
            item = pending.pop()
            if type(item) is tuple:
                pending.extend(item)
            elif type(item) is Address and item.kind == "operation":
                named.setdefault(item, []).append(address)
        if kind == "expression_block_use":
            block_reads.append(record)
        elif kind == "capture_use":
            captures.append(record)
        elif kind in _MYSQL_UNIT_RECORDS:
            owners.add(record.get("owner"))
        elif kind == "read" and record.get("role") == "capture":
            captured = True
        if kind == "port":
            port_owner, port_source = record.get("owner"), record.get("source")
            if port_owner.kind == "source" or (
                port_owner.kind in {"row", "window"}
                and port_source is not None
                and port_source.kind == "read"
                and records[port_owner].get("owner") == owner
                and records[port_source].get("port") in marked
            ):
                marked.add(address)

    def whole(operation, *also) -> bool:
        # Named once by the terminal row and by each of ``also``, and by no
        # other counted record.
        return Counter(named.get(operation, ())) == Counter((terminal.address, *also))

    if block_reads and not (
        captured
        and _mysql_compiled_capture_read(
            records, terminal, block_reads, captures, owners, whole
        )
    ):
        return {}

    def kind(address) -> str:
        if address.kind == "literal":
            return "literal"
        if address.kind == "read" and records[address].get("port") in marked:
            return "field"
        return "other"

    cells: dict = {}
    for value in terminal.get("values"):
        if value.kind != "operation" or not whole(value):
            continue
        operator = records[value].get("operator")
        operands = records[value].get("operands")
        if operator in {("scalar_call", "lpad"), ("scalar_call", "now")}:
            cells[value] = (operator[1], "select", tuple(kind(a) for a in operands))
        elif (
            operator == ("scalar_call", "date_of")
            and len(operands) == 1
            and operands[0].kind == "operation"
            and records[operands[0]].get("operator") == ("scalar_call", "now")
            and named.get(operands[0]) == [value]
        ):
            cells[operands[0]] = ("now", "select_date_of", ())
    return cells


def _mysql_compiled_capture_read(
    records, terminal, block_reads, captures, owners, whole
):
    """Q4 from the records: the one expression block use is a scalar read,
    a whole value of the terminal row that nothing else names (``whole``),
    and the terminal row stands directly over its source; the
    one capture is of that read; the read's producer is the capturing let's
    projection row, over one WHERE row of that let at most, then a source;
    and no unit belongs to a third declaration. (The caller has seen a read
    of a captured field.)"""

    use = block_reads[0]
    producer = records[use.get("producer")]
    if (
        len(block_reads) != 1
        or len(captures) != 1
        or captures[0].get("read") != use.address
        or records[use.get("operation")].get("operator") != ("scalar", "scalar")
        or not whole(use.get("operation"), use.address)
        or terminal.get("input").kind != "source"
        or producer.address.kind != "row"
        or producer.get("stage") != "projection"
    ):
        return False
    let = producer.get("owner")
    below = records[producer.get("input")]
    if (
        below.address.kind == "row"
        and below.get("owner") == let
        and below.get("stage") == "where"
    ):
        below = records[below.get("input")]
    return (
        below.address.kind == "source"
        and let != terminal.get("owner")
        and owners <= {terminal.get("owner"), let}
    )


# The MySQL cells of a Decimal(p, s), Date or Timestamp header parameter (the
# MySQL carriers of HEADER_PHYSICAL) that the Phase77 S09 candidate
# qualification preregisters. A read is the whole value of a SELECT item of
# the emitted query, or the right operand of a comparison whose left operand
# is a field of its source with the parameter's type, which the query's WHERE
# reaches through `and` and `or` alone. The query reads its one source
# directly, through one WHERE at most. Emission and the
# live verifier (plan) and compiled replay (records) each derive the cells
# from their own record; a statement opens its typed declarations only when
# each is read and every read is in a cell. The pure boundary refuses every
# header parameter.
MYSQL_TYPED_COMPARISONS = frozenset({"==", "!=", "<", "<=", ">", ">="})
_MYSQL_TYPED_OPERATORS = frozenset(("comparison", o) for o in MYSQL_TYPED_COMPARISONS)
# Plan fields a cell's plan may fill; every other field must be empty.
_MYSQL_TYPED_PLAN_FIELDS = frozenset(
    {
        "literal_policy",
        "parameters",
        "literal_sites",
        "literal_slots",
        "bind_uses",
        "fixed_envelope",
        "scope",
        "bindings",
        "sources",
        "blocks",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "exports",
        "projections",
        "boundaries",
        "symbols",
        "origins",
        "demands",
        "expression_sites",
        "expressions",
        "operands",
        "stage_ports",
        "filters",
        "result_ports",
        "result_exports",
    }
)
# Compiled record kinds a cell's bundle may hold: its units, values and their
# metadata. Any other unit, read or request leaves every typed read outside
# its cell.
_MYSQL_TYPED_RECORDS = frozenset(
    {
        "entry",
        "target",
        "premise",
        "expression_context",
        "policy",
        "declaration",
        "source",
        "source_unique",
        "provider",
        "field",
        "use",
        "port",
        "literal",
        "null_literal",
        "read",
        "operation",
        "site",
        "slot",
        "native_use",
        "parameter",
        "parameter_read",
        "row",
        "requirement_origin",
        "requirement",
        "requirement_link",
        "output",
    }
)


def mysql_typed_cells(plan) -> bool:
    """Whether every Decimal, Date and Timestamp header parameter of a
    MySQL plan is read and each read is in its cell, as above; never while
    emission derives as main (AS_MAIN). One pass over the plan's
    expressions and operand edges, then one over the WHERE's `and` and `or`
    nodes."""
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    if AS_MAIN.get():
        return False
    typed = parameters.HEADER_PHYSICAL["mysql"]
    declared = {id(p) for p in plan.parameters if p.tag in typed}
    if not declared:
        return True
    reads = [
        e
        for e in plan.expressions
        if type(e) is row.ProjectSQLParameterRead and e.parameter.tag in typed
    ]
    owner = plan.scope.selected_owner
    body = owner.definition
    stage = row.ProjectSQLStageKind
    if (
        {id(read.parameter) for read in reads} != declared
        or any(
            getattr(plan, name)
            for name in plan.__dataclass_fields__
            if name not in _MYSQL_TYPED_PLAN_FIELDS
        )
        or len(plan.sources) != 1
        or len(plan.bindings.definitions) != 2
        or tuple(block.kind for block in plan.blocks)
        not in ((stage.PROJECTION,), (stage.WHERE, stage.PROJECTION))
        or any(
            type(block.boundary) is not ProjectSQLBoundary
            or block.boundary.reason is not ProjectSQLBoundaryReason.SOURCE_INPUT
            for block in plan.blocks
        )
        or any(getattr(body, name, None) is not None for name in _MYSQL_CELL_CLAUSES)
        or getattr(body, "let_clause", None) is not None
        or getattr(body, "join_clauses", ())
        or getattr(body, "join_filters", ())
        or getattr(body, "named_windows", ())
    ):
        return False
    expressions = plan.expressions

    def at(reference):
        # The expression a reference names, read by its position.
        position = getattr(reference, "position", None)
        found = (
            expressions[position]
            if type(position) is int and 0 <= position < len(expressions)
            else None
        )
        return found if found is not None and found.ref is reference else None

    parents: dict[Any, list[Any]] = {}
    for operand in plan.operands:
        parents.setdefault(operand.child, []).append(operand.parent)
    # The comparisons each WHERE predicate reaches through `and` and `or`
    # alone, every node named once, by its parent; each node is visited once.
    compared = set()
    pending = [(f.predicate, None) for f in plan.filters]
    while pending:
        reference, parent = pending.pop()
        node = at(reference)
        if node is None or parents.get(reference, []) != (
            [] if parent is None else [parent]
        ):
            continue
        if type(node) is row.ProjectSQLBinary and node.expression.operator in (
            "and",
            "or",
        ):
            pending.extend(((node.left, reference), (node.right, reference)))
        elif type(node) is row.ProjectSQLComparison:
            compared.add(reference)
    ports = {p.ref: p for p in plan.stage_ports}
    inputs = {p.ref for p in plan.input_ports}
    projected = {p.expression for p in plan.projections}
    for read in reads:
        site, above = read.site, parents.get(read.ref, [])
        if type(site) is not row.ProjectSQLExpressionSite or site.owner is not owner:
            return False
        if site.role is row.ProjectSQLExpressionRole.SELECT:
            if (
                above
                or read.ref not in projected
                or site.occurrence.expression is not read.expression
            ):
                return False
            continue
        comparison = at(above[0]) if len(above) == 1 else None
        field = at(getattr(comparison, "left", None))
        port = ports.get(getattr(field, "port", None))
        if (
            site.role is not row.ProjectSQLExpressionRole.WHERE
            or above[0] not in compared
            or type(comparison) is not row.ProjectSQLComparison
            or comparison.right is not read.ref
            or comparison.expression.operator not in MYSQL_TYPED_COMPARISONS
            or type(field) is not row.ProjectSQLReference
            or port is None
            or port.kind is not row.ProjectSQLStagePortKind.INPUT
            or port.source not in inputs
            or value_tag(field) != read.parameter.tag
        ):
            return False
    return True


def mysql_compiled_typed_cells(records, entry) -> bool:
    """mysql_typed_cells from the compiled records alone. Each typed read is
    named once (a port repeats its row's value, a native use its occurrence
    and a requirement only anchors it, so none counts): by the entry's
    terminal projection row, or as the right operand of a comparison over a
    read of a source port of the same type, which `and` and `or` operations
    alone lead to the predicate of the one WHERE row under it. Those rows are
    the only ones and stand over the one source; every record kind is one of
    _MYSQL_TYPED_RECORDS. One pass over the records, then one over the
    WHERE's operations."""
    from pietto._project.project_compiled_schema import Address

    typed = parameters.HEADER_PHYSICAL["mysql"]
    named: dict[Any, list[Any]] = {}
    declared, reads, units, kinds = set(), [], [], set()
    for address, record in records.items():
        kind = address.kind
        kinds.add(kind)
        if kind == "parameter" and record.get("tag") in typed:
            declared.add(address)
        elif (
            kind == "parameter_read"
            and records[record.get("parameter")].get("tag") in typed
        ):
            reads.append(address)
        elif kind in ("row", "source"):
            units.append(record)
        if kind in ("requirement", "port", "native_use"):
            continue
        pending = list(record.values)
        while pending:
            item = pending.pop()
            if type(item) is tuple:
                pending.extend(item)
            elif type(item) is Address and item.kind in ("operation", "parameter_read"):
                named.setdefault(item, []).append(address)
    if not declared:
        return True
    owner = entry.get("declaration")
    terminal = records[entry.get("terminal")]
    sources = [u for u in units if u.address.kind == "source"]
    below = [
        u for u in units if u.address.kind == "row" and u.address != terminal.address
    ]
    source = sources[0] if len(sources) == 1 else None
    where = below[0] if below else None
    if (
        not kinds <= _MYSQL_TYPED_RECORDS
        or {records[read].get("parameter") for read in reads} != declared
        or source is None
        or len(below) > 1
        or terminal.address.kind != "row"
        or terminal.get("stage") != "projection"
        or terminal.get("owner") != owner
        or terminal.get("input") != (where or source).address
        or where is not None
        and (
            where.address.kind != "row"
            or where.get("stage") != "where"
            or where.get("owner") != owner
            or where.get("input") != source.address
        )
    ):
        return False
    # The comparisons the WHERE row's predicate reaches through `and` and
    # `or` operations alone, every operation named once, by its parent.
    compared = set()
    pending = [] if where is None else [(where.get("predicate"), where.address)]
    while pending:
        address, parent = pending.pop()
        if (
            type(address) is not Address
            or address.kind != "operation"
            or named.get(address) != [parent]
        ):
            continue
        operator = records[address].get("operator")
        if operator in (("binary", "and"), ("binary", "or")):
            pending.extend(
                (child, address) for child in records[address].get("operands")
            )
        elif operator in _MYSQL_TYPED_OPERATORS:
            compared.add(address)
    for read in reads:
        above = named.get(read, [])
        if above == [terminal.address]:
            continue
        if where is None or len(above) != 1 or above[0] not in compared:
            return False
        operands = records[above[0]].get("operands")
        field = (
            records[operands[0]]
            if len(operands) == 2 and operands[0].kind == "read"
            else None
        )
        port = None if field is None else records[field.get("port")]
        if (
            field is None
            or port is None
            or operands[1] != read
            or field.get("use") != where.get("use")
            or port.get("owner") != source.address
            or port.get("logical")[0]
            != records[records[read].get("parameter")].get("tag")
        ):
            return False
    return True


# Phase77 S03 (project_sql_emission_sum_forms): the plan tables a paired
# statement may hold, and the fields of each of its definitions as written
# that may be set; any other one (WHERE, a `let` block, window, HAVING,
# DISTINCT, ORDER BY, LIMIT, header parameter, JOIN filter, or one a later
# plan or grammar adds) keeps main's refusal. MC s03n: the selected
# definition may also set its HAVING, ORDER BY and (T-1) WHERE, whose plan
# tables it then holds (_MYSQL_S03_CLAUSE_PLAN_TABLES).
_MYSQL_S03_PLAN_TABLES = (_MYSQL_CELL_PLAN_TABLES - {"filters"}) | {
    "aggregate_risks",
    "join_inputs",
    "join_ports",
    "join_tails",
    "joins",
}
_MYSQL_S03_CLAUSE_PLAN_TABLES = frozenset(
    {
        "filters",
        "order_expressions",
        "order_items",
        "order_uses",
        "orders",
        "result_boundaries",
    }
)
_MYSQL_S03_AUTHORED = frozenset(
    {
        "span",
        "name",
        "from_clause",
        "group_by_clause",
        "select_items",
        "join_clauses",
        "naming_declarations",
    }
)
_MYSQL_S03_RECORDS = _MYSQL_CELL_RECORDS | {"join", "join_value"}


def mysql_s03_statement(request) -> bool:
    """S03: whether this MySQL statement, as written over its bound contract,
    is one of the paired sum forms or (MC s03n) one of the neighbours that
    sum_forms.paired opens: its selected definition reads sources, one JOIN
    of two at most, or a chain of up to two more definitions of its module,
    each read by FROM by its own name, the lowest over such sources. Every
    source is declared in the selected module and read by its own name, but
    the selected definition alone may read one through a relation alias
    `let x = S`, its one `let`, or one imported under its own name from the
    module that declares it into a module that imports nothing else but a
    `def` (the authored script holds no imported `def` or relationship, so
    the module's imported relationships are read apart); paired then sees
    which (``organized``:
    D77.24, compiled records and the pure document cannot tell them from a
    direct read). Only the selected definition may set HAVING, ORDER BY and
    WHERE, which paired then reads. Its
    aggregates are the forms' own. Each call indexes the selected module's
    definitions and the bound sources by name, then reads three definitions
    of a few items at most: O(module definitions and bound source fields),
    independent of the statement's sum count. No statement is one while
    emission derives as main (AS_MAIN)."""

    from pietto import ast_nodes as ast
    from pietto._project import project_sql_emission_sum_forms as forms
    from pietto._project.module_catalog import authored_definitions
    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy

    plan = request.plan
    if (
        AS_MAIN.get()
        or request.family != "mysql"
        or any(
            type(value := getattr(plan, name)) is tuple
            and value
            and name not in _MYSQL_S03_PLAN_TABLES
            and name not in _MYSQL_S03_CLAUSE_PLAN_TABLES
            for name in plan.__dataclass_fields__
        )
    ):
        return False
    owner = plan.scope.selected_owner
    module = plan.scope.completed.semantic_result.modules[owner.module_position]
    relations = (
        ast.SourceDef,
        ast.QueryDef,
        ast.TableDef,
        ast.SetRelationDef,
        ast.BlockRelationDef,
    )
    definitions = authored_definitions(module)
    named: dict[str, Any] = {}
    for definition in definitions:
        if type(definition) in relations:
            named[definition.name] = None if definition.name in named else definition
    selected = definitions[owner.declaration_position]
    if type(selected) not in (ast.QueryDef, ast.TableDef):
        return False
    # MC s03n: HAVING's and WHERE's filters and ORDER BY's tables are the
    # selected definition's alone.
    ordered = selected.order_by_clause is not None
    if len(plan.filters) != (selected.satisfying_clause is not None) + (
        selected.where_clause is not None
    ) or any(
        bool(getattr(plan, name)) is not ordered
        for name in _MYSQL_S03_CLAUSE_PLAN_TABLES - {"filters"}
    ):
        return False
    # MC s03n: a source imported under its own name from the module that
    # declares it, which the selected definition alone may read, and the
    # module's one import.
    imported = None
    foreign = [binding for binding in plan.sources if binding.module is not module]
    if foreign:
        parsed = module.parsed_input
        assert parsed is not None
        if parsed.imported_relationships:
            return False
        imports = [
            (
                statement.target,
                item.declaration_kind,
                item.exported_name,
                item.local_name in (None, item.exported_name),
            )
            for statement in (parsed.authored_script or parsed.script).module_statements
            if type(statement) is ast.ImportStatement
            for item in statement.items
        ]
        if len(plan.sources) != 1 or imports != [
            (
                foreign[0].module.path,
                ast.ModuleDeclarationKind.SOURCE,
                foreign[0].declaration.name,
                True,
            )
        ]:
            return False
        imported = foreign[0].declaration.name
    carriers: dict[str, dict[str, str | None]] = {}
    layouts: dict[str, tuple] = {}
    tokens: dict[str, tuple] = {}
    for source in request.sources:
        name = json.loads(source.selector)["name"]
        carriers[name] = (
            {}
            if name in carriers
            else {
                field.name: forms.carrier(field.representation)
                for field in source.fields
            }
        )
        ordered = sorted(source.fields, key=lambda field: field.ordinal)
        layouts[name] = tuple(forms.carrier(field.representation) for field in ordered)
        tokens[name] = tuple(field.name for field in ordered)
    read_sources: set[str] = set()
    organized = None

    def column(side, source, field):
        carrier = carriers.get(source, {}).get(field)
        read_sources.add(source)
        return None if carrier is None else (side, field, carrier)

    def level(definition, upstream, top):
        """One definition's level, its items by output name, and (``top``,
        the selected one) its clauses; None outside the forms' shapes."""
        nonlocal organized
        if type(definition) not in (ast.QueryDef, ast.TableDef) or any(
            getattr(definition, name) not in (None, ())
            for name in definition.__dataclass_fields__
            if name not in _MYSQL_S03_AUTHORED
            and not (
                top and name in ("order_by_clause", "satisfying_clause", "where_clause")
            )
        ):
            return None
        origin = definition.from_clause
        if origin.binding_name is not None:
            return None
        source = origin.source_name
        join, sides = None, None

        def read(expression):
            """A column of this level: a bare name of the upstream's items or
            of the FROM source, or `binding.field` of a JOIN's input."""
            if sides is not None:
                if (
                    type(expression) is not ast.DottedNameExpr
                    or len(expression.parts) != 2
                    or expression.parts[0] not in sides
                ):
                    return None
                side, read_source = sides[expression.parts[0]]
                return column(side, read_source, expression.parts[1])
            if type(expression) is not ast.NameExpr:
                return None
            if upstream is None:
                return column("A", source, expression.name)
            item = upstream[1].get(expression.name)
            return None if item is None else ("U", item, None)

        if upstream is not None:
            if (
                source != upstream[0]
                or definition.join_clauses
                or definition.naming_declarations
            ):
                return None
        elif (
            top
            and not definition.join_clauses
            and len(definition.naming_declarations) == 1
            and imported is None
        ):
            # MC s03n: `let x = S`, `from x`, S a source of the module, not
            # in parentheses.
            (let,) = definition.naming_declarations
            if not (
                type(let) is ast.QueryLetDeclaration
                and type(let.expression) is ast.NameExpr
                and let.name == source
                and let.expression.name != source
                and type(named.get(let.expression.name)) is ast.SourceDef
                and source not in named
                and _ends(let, let.expression)
            ):
                return None
            source, organized = let.expression.name, "alias"
        elif source == imported and top:
            if definition.join_clauses or definition.naming_declarations:
                return None
            organized = "import"
        elif type(named.get(source)) is not ast.SourceDef:
            return None
        elif definition.join_clauses or definition.naming_declarations:
            written = _written_join(
                definition,
                named,
                (ast.AuthoredJoinKind.INNER, ast.AuthoredJoinKind.LEFT),
            )
            if written is None:
                return None
            clause, let, on = written
            sides = {
                source: ("A", source),
                let.name: ("B", let.expression.name),
            }
            assert type(on) is ast.ComparisonExpr and clause.on_clause is not None
            left, right = read(on.left), read(on.right)
            if (
                left is None
                or right is None
                or not _ends(clause.on_clause, on)
                or not _starts(on, on.left)
                or not _ends(on, on.right)
            ):
                return None
            join = (
                str(clause.kind),
                left,
                right,
                layouts.get(source),
                layouts.get(let.expression.name),
                tokens.get(source),
            )
        keys = []
        for key in (
            ()
            if definition.group_by_clause is None
            else definition.group_by_clause.items
        ):
            value = read(key.key)
            if value is None or not _starts(key, key.key) or not _ends(key, key.key):
                return None
            keys.append(value)
        items, outputs = [], {}
        for chosen in definition.select_items:
            expression = chosen.expression
            item = _mysql_s03_item(expression, read, join is None)
            if not _ends(chosen, expression) or (
                chosen.alias is None and not _starts(chosen, expression)
            ):
                item = None
            name = chosen.alias or (
                expression.name
                if type(expression) is ast.NameExpr
                else expression.parts[-1]
                if type(expression) is ast.DottedNameExpr
                else None
            )
            if item is None or name is None or name in outputs:
                return None
            items.append(item)
            outputs[name] = item
        plain = definition.group_by_clause is None and all(
            item[0] == "key" for item in items
        )
        if plain:
            # MC s03n: a plain level, which aggregates nothing and selects
            # each field by its own name (Law C's upstream); compiled
            # records and the pure document hold no such name (D77.24).
            if any(name != item[1][1] for name, item in outputs.items()):
                return None
            items = [("read", item[1]) for item in items]
            outputs = {name: ("read", item[1]) for name, item in outputs.items()}
        clauses = []
        where = definition.where_clause if top else None
        if where is not None:
            # MC s03n's T-1: a WHERE whose one test reads this level's input,
            # written as a conditional sum's test is.
            test = _mysql_s03_test(where.expression, read)
            if test is None or not _ends(where, where.expression):
                return None
            clauses.append(("where", test))
        if top and definition.order_by_clause is not None:
            # MC s03n: an ORDER BY key reads a selected output named alone.
            for entry in definition.order_by_clause.items:
                name = getattr(entry.expression, "name", None)
                if (
                    type(entry.expression) is not ast.NameExpr
                    or entry.direction is not None
                    or not _starts(entry, entry.expression)
                    or not _ends(entry, entry.expression)
                    or name not in outputs
                ):
                    return None
                clauses.append(("order", outputs[name], "asc"))
        having = definition.satisfying_clause if top else None
        if having is not None:
            # MC s03n: one HAVING line comparing a selected output named
            # alone with an Int literal, as written.
            line = having.expression
            name = getattr(getattr(line, "left", None), "name", None)
            if (
                type(line) is not ast.ComparisonExpr
                or type(line.left) is not ast.NameExpr
                or type(line.right) is not ast.LiteralExpr
                or type(line.right.value) is not int
                or not _ends(having, line)
                or not _starts(line, line.left)
                or not _ends(line, line.right)
                or name not in outputs
            ):
                return None
            clauses.append((line.operator, outputs[name], line.right.value))
        level_tuple = (join, None if plain else tuple(keys), tuple(items))
        return level_tuple, outputs, tuple(clauses)

    # The chain by FROM, the selected definition last.
    chain = [selected]
    while len(chain) <= 3 and type(
        below := named.get(chain[-1].from_clause.source_name)
    ) in (ast.QueryDef, ast.TableDef):
        chain.append(below)
    if len(chain) > 3:
        return False
    chain.reverse()
    levels: list = []
    clauses: tuple = ()
    upstream = None
    for position, definition in enumerate(chain):
        found = level(definition, upstream, position + 1 == len(chain))
        if found is None:
            return False
        levels.append(found[0])
        clauses = found[2]
        upstream = (definition.name, found[1])
    functions = sorted(
        "filtered_sum" if item[0] == "fsum" else item[0]
        for current in levels
        for item in current[2]
        if item[0] not in ("key", "read")
    )
    return (
        len(plan.bindings.definitions) == len(read_sources) + len(chain)
        and len(plan.sources) == len(read_sources)
        and sorted(str(function_name(value.source)) for value in plan.aggregates)
        == functions
        and forms.paired(
            tuple(levels),
            plan.literal_policy is ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
            clauses,
            organized,
        )
    )


def _written_join(definition, named, kinds) -> tuple[Any, Any, Any] | None:
    """S03 and MC G8: ``definition``'s one JOIN as written, `let i = S` and
    `KIND join i on X == Y` over its FROM source and another source S of
    ``named`` (its module's relations by name), KIND among ``kinds``, as
    (clause, let, on); None for any other JOIN, `let` or relation alias."""

    from pietto import ast_nodes as ast

    if len(definition.join_clauses) != 1 or len(definition.naming_declarations) != 1:
        return None
    (clause,), (let,) = definition.join_clauses, definition.naming_declarations
    origin = definition.from_clause
    on = None if clause.on_clause is None else clause.on_clause.expression
    if not (
        type(let) is ast.QueryLetDeclaration
        and type(let.expression) is ast.NameExpr
        and type(named.get(let.expression.name)) is ast.SourceDef
        and let.expression.name != origin.source_name
        and let.name != origin.source_name
        and clause.kind in kinds
        and clause.target_relation_name == let.name
        and clause.target_binding_name == let.name
        and clause.source_binding_name is None
        and not clause.traversal_steps
        and clause.uses_named_input is True
        and clause.asof is False
        and type(on) is ast.ComparisonExpr
        and on.operator == "=="
    ):
        return None
    return clause, let, on


def _starts(outer, inner) -> bool:
    """``inner`` starts where ``outer`` does: no parenthesis opens between
    them (D77.24: a parenthesized spelling is no paired form's)."""

    return (outer.span.line, outer.span.column) == (
        inner.span.line,
        inner.span.column,
    )


def _ends(outer, inner) -> bool:
    """``inner`` ends where ``outer`` does: no parenthesis closes between."""

    return (outer.span.end_line, outer.span.end_column) == (
        inner.span.end_line,
        inner.span.end_column,
    )


def _mysql_s03_item(expression, read, conditional):
    """One SELECT item as an S03 item (sum_forms), or None; a parenthesized
    argument, test or operand is none (_starts, _ends), nor a call over two
    lines or with a space at its parentheses."""

    from pietto import ast_nodes as ast

    if type(expression) in (ast.NameExpr, ast.DottedNameExpr):
        value = read(expression)
        return None if value is None else ("key", value)
    if (
        type(expression) is not ast.CallExpr
        or type(expression.callee) is not ast.NameExpr
        or expression.aggregate_order_by
        or len(expression.arguments) > 1
        or expression.span.line != expression.span.end_line
    ):
        return None
    function = expression.callee.name
    if not expression.arguments:
        # MC s03n: `count()` as written, no space in it.
        return (
            ("count", None)
            if function == "count"
            and (expression.span.end_line, expression.span.end_column)
            == (expression.span.line, expression.span.column + len("count()"))
            else None
        )
    argument = expression.arguments[0]
    # `name(` then the argument, then `)`, on one line.
    if (argument.span.line, argument.span.column) != (
        expression.span.line,
        expression.span.column + len(function) + 1,
    ) or (argument.span.end_line, argument.span.end_column + 1) != (
        expression.span.end_line,
        expression.span.end_column,
    ):
        return None
    if function == "sum" and type(argument) is ast.GeneratorExpr:
        test = argument.condition
        if (
            not conditional
            or argument.source != ("group",)
            or argument.source_read is not None
            or test is None
            or not _starts(argument, argument.body)
            or not _ends(argument, test)
        ):
            return None
        parts = _mysql_s03_test(test, read)
        value = read(argument.body)
        return None if value is None or parts is None else ("fsum", value, parts)
    if function in ("sum", "count"):
        value = read(argument)
        return None if value is None else (function, value)
    return None


def _mysql_s03_test(test, read):
    """A conditional sum's test as an S03 test (sum_forms): a read, `not` or
    `is None` of one, a read `>` an Int literal, or (MC s03n) an `and` or
    `or` of two such tests, each written plainly; None for any other."""

    from pietto import ast_nodes as ast

    if type(test) is ast.NameExpr:
        parts = ("is", read(test))
    elif (
        type(test) is ast.UnaryExpr
        and test.operator == "not"
        and _ends(test, test.operand)
    ):
        parts = ("not", read(test.operand))
    elif (
        type(test) is ast.IsNullExpr
        and test.negated is False
        and _starts(test, test.value)
    ):
        parts = ("none", read(test.value))
    elif (
        type(test) is ast.ComparisonExpr
        and test.operator == ">"
        and type(test.right) is ast.LiteralExpr
        and type(test.right.value) is int
        and _starts(test, test.left)
        and _ends(test, test.right)
    ):
        parts = (">", read(test.left), test.right.value)
    elif (
        type(test) is ast.BinaryExpr
        and test.operator in ("and", "or")
        and _starts(test, test.left)
        and _ends(test, test.right)
    ):
        parts = (
            test.operator,
            _mysql_s03_test(test.left, read),
            _mysql_s03_test(test.right, read),
        )
    else:
        return None
    return None if parts[1] is None or parts[2:3] == (None,) else parts


def mysql_s03_compiled(records, entry) -> frozenset:
    """Compiled replay's S03 sums and conditional sums, or else MC G8's sums
    (mysql_g8_compiled): their aggregate_value addresses."""

    return _mysql_s03_compiled(records, entry) or mysql_g8_compiled(records, entry)


def _mysql_s03_compiled(records, entry) -> frozenset:
    """Compiled replay's S03 sums and conditional sums (their aggregate_value
    addresses), from the records alone, as emission derives the statement
    (mysql_s03_statement): every record is of a kind in _MYSQL_S03_RECORDS
    or a result record, and the entry's terminal is a projection row over
    an aggregate of its declaration, over a source, one JOIN of two
    sources, or the projection row of another declaration, which stands so
    in turn, three declarations at most; a declaration's projection row may
    instead stand over a source alone (a plain level, MC s03n). The selected
    declaration alone may add one HAVING row between its aggregate and its
    projection row, one WHERE row between the projection row of the
    declaration below and its aggregate, and one result record over its
    projection row, which holds its ORDER BY and neither DISTINCT nor LIMIT
    (MC s03n). No other row,
    aggregate, result or JOIN exists. An imported source or definition and
    a relation alias leave the same records, so only emission refuses
    them."""

    from pietto._project import project_sql_emission_sum_forms as forms
    from pietto._project.project_compiled_schema import Address

    if any(
        address.kind not in _MYSQL_S03_RECORDS and address.kind != "result"
        for address in records
    ):
        return frozenset()
    units: set = set()
    sums: list = []
    clauses: list = []

    def field(port):
        return port.get("source"), forms.carrier(
            records[port.get("source")].get("physical")
        )

    def operand(address, column, compound=True):
        """A conditional sum's test: a read, `not`, `is None` or `>` literal,
        or (MC s03n) an `and` or `or` of two of them."""
        if address.kind == "read":
            value = column(address)
            return None if value is None else ("is", value)
        operation = records[address]
        if address.kind != "operation":
            return None
        operator, operands = operation.get("operator"), operation.get("operands")
        if (
            compound
            and operator in (("binary", "and"), ("binary", "or"))
            and len(operands) == 2
        ):
            left, right = (operand(item, column, False) for item in operands)
            return None if left is None or right is None else (operator[1], left, right)
        if (
            operator in (("not", "not"), ("null_test", "is_null"))
            and len(operands) == 1
            and operands[0].kind == "read"
        ):
            value = column(operands[0])
            kind = "not" if operator[0] == "not" else "none"
            return None if value is None else (kind, value)
        if (
            operator == ("comparison", ">")
            and len(operands) == 2
            and operands[0].kind == "read"
            and operands[1].kind == "literal"
            and records[operands[1]].get("tag") == "Int"
        ):
            value = column(operands[0])
            literal = records[operands[1]].get("value").value
            return None if value is None else (">", value, literal)
        return None

    def level(row, owner, depth):
        """The level of a projection row of ``owner`` over its aggregate,
        or over a source alone: (level, the row's output ports to their
        items, the level below if any), or None. Only the selected
        declaration's (``depth`` 0) may hold a HAVING row and a WHERE row."""
        if (
            row.address.kind != "row"
            or row.get("stage") != "projection"
            or row.get("predicate") is not None
            or row.get("owner") != owner
            or len(row.get("values")) != len(row.get("outputs"))
        ):
            return None
        units.add(row.address)
        aggregate, satisfying = records[row.get("input")], None
        if (
            depth == 0
            and aggregate.address.kind == "row"
            and aggregate.get("stage") == "satisfying"
            and aggregate.get("owner") == owner
        ):
            satisfying, aggregate = aggregate, records[aggregate.get("input")]
            units.add(satisfying.address)
        if aggregate.address.kind == "source" and satisfying is None:
            # MC s03n: a plain level, which reads the source's fields.
            items, ports = [], {}
            for read, port in zip(row.get("values"), row.get("outputs"), strict=True):
                found = (
                    records[records[read].get("port")] if read.kind == "read" else None
                )
                if found is None or found.get("owner") != aggregate.address:
                    return None
                items.append(("read", ("A", *field(found))))
                ports[port] = items[-1]
            return (None, None, tuple(items)), ports, None
        if aggregate.address.kind != "aggregate" or aggregate.get("owner") != owner:
            return None
        below, where = records[aggregate.get("input")], None
        units.add(aggregate.address)
        if (
            depth == 0
            and below.address.kind == "row"
            and below.get("stage") == "where"
            and below.get("owner") == owner
        ):
            where, below = below, records[below.get("input")]
            units.add(where.address)
        join, upstream, uses = None, None, []

        def side(read):
            """A read of a JOIN input's source port: its side and field."""
            if read.kind != "read":
                return None
            use = records[records[read].get("use")]
            port = records[records[read].get("port")]
            if use not in uses or port.get("owner") != use.get("producer"):
                return None
            return ("AB"[use.get("ordinal")], *field(port))

        def column(read):
            """A read of this level's input: a source, JOIN or upstream port."""
            if read.kind != "read":
                return None
            port = records[records[read].get("port")]
            if below.address.kind == "source":
                if port.get("owner") != below.address:
                    return None
                return ("A", *field(port))
            if below.address.kind == "join":
                value = port.get("source")
                if port.get("owner") != below.address or value.kind != "join_value":
                    return None
                return side(records[value].get("input"))
            assert upstream is not None
            item = upstream[1].get(port.address)
            return None if item is None else ("U", item, None)

        if below.address.kind == "join":
            uses = [records[use] for use in below.get("inputs")]
            predicate = below.get("predicate")
            operands = (
                records[predicate].get("operands")
                if predicate is not None and predicate.kind == "operation"
                else ()
            )
            if (
                below.get("owner") != owner
                or below.get("equalities") != ()
                or [use.get("ordinal") for use in uses] != [0, 1]
                or any(use.get("producer").kind != "source" for use in uses)
                or uses[0].get("producer") == uses[1].get("producer")
                or len(operands) != 2
                or records[predicate].get("operator") != ("comparison", "==")
                or any(item.kind != "read" for item in operands)
            ):
                return None
            units.add(below.address)
            join = (
                below.get("kind"),
                side(operands[0]),
                side(operands[1]),
                *(
                    tuple(
                        forms.carrier(records[field].get("physical"))
                        for field in records[use.get("producer")].get("fields")
                    )
                    for use in uses
                ),
                tuple(records[uses[0].get("producer")].get("fields")),
            )
            if None in join:
                return None
        elif below.address.kind == "row" and below.get("owner") != owner and depth < 2:
            upstream = level(below, below.get("owner"), depth + 1)
            if upstream is None:
                return None
        elif below.address.kind != "source":
            return None
        if where is not None:
            # MC s03n's T-1: the WHERE row carries the ports of the level
            # below in order and tests them as a conditional sum's test.
            if upstream is None:
                return None
            inputs, passed = below.get("outputs"), where.get("values")
            if (
                where.get("predicate") is None
                or len(passed) != len(inputs)
                or len(where.get("outputs")) != len(passed)
                or not all(
                    read.kind == "read" and records[read].get("port") == port
                    for read, port in zip(passed, inputs)
                )
            ):
                return None
            test = operand(where.get("predicate"), column)
            if test is None:
                return None
            clauses.append(("where", test))
            # The aggregate reads the WHERE row's ports, each an item below.
            upstream = (
                upstream[0],
                {
                    port: upstream[1][source]
                    for port, source in zip(where.get("outputs"), inputs, strict=True)
                },
                upstream[2],
            )
        keys = tuple(column(key) for key in aggregate.get("keys"))
        if None in keys:
            return None
        values = {}
        for address in aggregate.get("values"):
            value = records[address]
            function, arguments = value.get("function"), value.get("arguments")
            item = None
            if function == "count" and not arguments:
                # MC s03n: `count()`.
                item = ("count", None)
            elif (
                function in ("sum", "count")
                and len(arguments) == 1
                and arguments[0].kind == "read"
            ):
                item = column(arguments[0])
                item = None if item is None else (function, item)
            elif (
                function == "filtered_sum"
                and len(arguments) == 2
                and arguments[0].kind == "read"
            ):
                x, test = column(arguments[0]), operand(arguments[1], column)
                item = None if x is None or test is None else ("fsum", x, test)
            if item is None:
                return None
            values[address] = item
            if function != "count":
                sums.append(address)
        outputs = {}
        for address in aggregate.get("outputs"):
            source = records[address].get("source")
            if source in values:
                outputs[address] = values[source]
            elif source in aggregate.get("keys"):
                outputs[address] = ("key", keys[aggregate.get("keys").index(source)])
            else:
                return None
        if satisfying is not None:
            # MC s03n: the HAVING row carries the aggregate's ports in order
            # and compares one of them with an Int literal.
            passed, predicate = satisfying.get("values"), satisfying.get("predicate")
            operation = (
                records[predicate]
                if getattr(predicate, "kind", None) == "operation"
                else None
            )
            pair = () if operation is None else operation.get("operands")
            if (
                len(passed) != len(aggregate.get("outputs"))
                or len(satisfying.get("outputs")) != len(passed)
                or not all(
                    read.kind == "read" and records[read].get("port") == port
                    for read, port in zip(passed, aggregate.get("outputs"))
                )
                or operation is None
                or operation.get("operator")[0] != "comparison"
                or len(pair) != 2
                or pair[0].kind != "read"
                or pair[1].kind != "literal"
                or records[pair[1]].get("tag") != "Int"
                or type(number := getattr(records[pair[1]].get("value"), "value", None))
                is not int
            ):
                return None
            # Its predicate reads the aggregate's port, its row the carries.
            read = records[pair[0]].get("port")
            if read not in outputs:
                return None
            clauses.append((operation.get("operator")[1], outputs[read], number))
            outputs = {
                port: outputs[source]
                for port, source in zip(
                    satisfying.get("outputs"), aggregate.get("outputs"), strict=True
                )
            }
        items, ports = [], {}
        for read, port in zip(row.get("values"), row.get("outputs"), strict=True):
            item = (
                outputs.get(records[read].get("port")) if read.kind == "read" else None
            )
            if item is None:
                return None
            items.append(item)
            ports[port] = item
        return (join, keys, tuple(items)), ports, upstream

    terminal, result = records[entry.get("terminal")], None
    if terminal.address.kind == "result":
        # MC s03n: the selected declaration's ORDER BY, with no DISTINCT or
        # LIMIT, over its projection row.
        result, terminal = terminal, records[terminal.get("input")]
        if (
            result.get("owner") != entry.get("declaration")
            or result.get("distinct") is not False
            or result.get("limit") is not None
            or result.get("limit_literal") is not None
        ):
            return frozenset()
        units.add(result.address)
    top = level(terminal, entry.get("declaration"), 0)
    if top is None or any(
        address.kind in {"row", "aggregate", "join", "result"} and address not in units
        for address in records
    ):
        return frozenset()
    levels = []
    current = top
    while current is not None:
        levels.append(current[0])
        current = current[2]
    levels.reverse()
    if result is not None:
        ports = top[1]
        read = [
            ports.get(records[item].get("port")) if item.kind == "read" else None
            for item in result.get("projection")
        ]
        order = [
            (ports.get(records[item].get("port")) if item.kind == "read" else None, way)
            for item, way in result.get("ordering")
        ]
        if (
            None in read
            or any(item is None for item, _ in order)
            or {
                records[item].get("port")
                for item in (
                    *result.get("projection"),
                    *(item for item, _ in result.get("ordering")),
                )
            }
            != set(terminal.get("outputs"))
        ):
            return frozenset()
        levels[-1] = (*levels[-1][:2], tuple(read))
        clauses.extend(("order", item, way) for item, way in order)
    preserve = records[Address("policy", 0)].get("literal_policy") == (
        "preserve_literals"
    )
    return (
        frozenset(sums)
        if forms.paired(tuple(levels), preserve, tuple(clauses))
        else frozenset()
    )


def _mysql_g8_shapes(order, item) -> bool:
    """MC G8: the per-order level's shapes as written, the style page's: the
    FROM source's three fields and one key, `unique` of its first field, and
    the joined source's two fields and nothing else (the carriers are the
    contract's)."""

    from pietto import ast_nodes as ast

    return (
        type(order) is ast.ShapeDef
        and type(item) is ast.ShapeDef
        and len(order.items) == 4
        and len(order.fields) == 3
        and len(order.uniques) == 1
        and order.uniques[0].field_names == (order.fields[0].name,)
        and len(item.items) == len(item.fields) == 2
    )


def mysql_g8_compiled(records, entry) -> frozenset:
    """Compiled replay's MC G8 sums (their aggregate_value addresses), from
    the records alone, as emission derives the statement
    (mysql_g8_statement): every record is of a kind in _MYSQL_S03_RECORDS,
    and the entry's terminal stands over one chain of rows and aggregates,
    each declaration a run of `let`, WHERE, aggregate and projection units
    over the projection row of the declaration below, the lowest over a
    source or one JOIN of two sources; no other row, aggregate or JOIN
    exists. A port is followed by what its read reads: a source or joined
    field, an item of the level below, a `let` value, a key or an aggregate
    of its declaration; each `let` keeps MC G1's law (_mysql_compiled_lets),
    and each sum of an aggregate level is read by that level's projection.
    An imported source or definition, a relation alias, an unread window
    and a read qualified by a definition's name leave the same records, so
    only emission refuses them. Linear in the records."""

    from pietto._project import project_sql_emission_levels as levels_law
    from pietto._project import project_sql_emission_sum_forms as forms

    empty: frozenset = frozenset()
    if any(address.kind not in _MYSQL_S03_RECORDS for address in records):
        return empty
    chain = []
    current = records[entry.get("terminal")]
    while current.address.kind in ("row", "aggregate") and len(chain) < len(records):
        chain.append(current)
        current = records[current.get("input")]
    chain.reverse()
    units = {unit.address for unit in chain}
    if current.address.kind == "join":
        units.add(current.address)
    elif current.address.kind != "source":
        return empty
    if any(
        address.kind in ("row", "aggregate", "join") and address not in units
        for address in records
    ):
        return empty
    groups: list[list] = []
    for unit in chain:
        if groups and groups[-1][0].get("owner") == unit.get("owner"):
            groups[-1].append(unit)
        else:
            groups.append([unit])

    def field(port, side):
        source = records[port.get("source")]
        return (side, source.get("ordinal"), forms.carrier(source.get("physical")))

    levels = []
    sums: list = []
    lower: tuple = ()
    for index, group in enumerate(groups):
        kinds = tuple(
            "aggregate" if unit.address.kind == "aggregate" else unit.get("stage")
            for unit in group
        )
        lets = kinds.count("let")
        if kinds[lets:] not in (
            ("projection",),
            ("where", "projection"),
            ("aggregate", "projection"),
            ("where", "aggregate", "projection"),
        ) or any(
            unit.address.kind == "row"
            and (unit.get("predicate") is not None) is not (kind == "where")
            for unit, kind in zip(group, kinds, strict=True)
        ):
            return empty
        below = records[group[0].get("input")]
        meaning: dict = {}
        join = None
        if index:
            if below.address != lower[0]:
                return empty
            meaning = {port: ("U", position) for position, port in enumerate(lower[1])}
        elif below.address.kind == "source":
            meaning = {
                port: field(records[port], "A")
                for port in records
                if port.kind == "port" and records[port].get("owner") == below.address
            }
        else:
            uses = [records[use] for use in below.get("inputs")]
            predicate = below.get("predicate")
            operands = (
                records[predicate].get("operands")
                if predicate is not None and predicate.kind == "operation"
                else ()
            )
            if (
                below.get("equalities") != ()
                or [use.get("ordinal") for use in uses] != [0, 1]
                or any(use.get("producer").kind != "source" for use in uses)
                or uses[0].get("producer") == uses[1].get("producer")
                or len(operands) != 2
                or records[predicate].get("operator") != ("comparison", "==")
                or any(item.kind != "read" for item in operands)
            ):
                return empty

            def side(read, uses=uses):
                """A read of a JOIN input's source port: its side and field."""
                use = records[records[read].get("use")]
                port = records[records[read].get("port")]
                if use not in uses or port.get("owner") != use.get("producer"):
                    return None
                return field(port, "AB"[use.get("ordinal")])

            for port in records:
                value = records[port].get("source") if port.kind == "port" else None
                if (
                    value is not None
                    and records[port].get("owner") == below.address
                    and value.kind == "join_value"
                ):
                    meaning[port] = side(records[value].get("input"))
            # The style page's keys: `unique` of the FROM source's first
            # field, and none of the joined source.
            if [
                (
                    record.get("source"),
                    tuple(
                        records[port].get("ordinal") for port in record.get("fields")
                    ),
                )
                for address, record in records.items()
                if address.kind == "source_unique"
            ] != [(uses[0].get("producer"), (0,))]:
                return empty
            join = (
                below.get("kind"),
                side(operands[0]),
                side(operands[1]),
                *(
                    tuple(
                        forms.carrier(records[item].get("physical"))
                        for item in records[use.get("producer")].get("fields")
                    )
                    for use in uses
                ),
            )

        def read(address, meaning=meaning):
            """A read as the column it reads, or None."""
            if getattr(address, "kind", None) != "read":
                return None
            return meaning.get(records[address].get("port"))

        level_lets: list = []
        keys: list = []
        values: list = []
        items: list = []
        projected: set = set()
        for unit in group:
            outputs = unit.get("outputs")
            if unit.address.kind == "aggregate":
                keys = [read(key) for key in unit.get("keys")]
                for address in unit.get("values"):
                    value = records[address]
                    arguments = value.get("arguments")
                    if value.get("order_by") or len(arguments) > 1:
                        return empty
                    item = (
                        value.get("function"),
                        read(arguments[0]) if arguments else None,
                    )
                    if arguments and item[1] is None:
                        return empty
                    values.append(item)
                    if item[0] == "sum":
                        sums.append(address)
                for port in outputs:
                    source = records[port].get("source")
                    if source in unit.get("keys"):
                        meaning[port] = ("K", unit.get("keys").index(source))
                    elif source in unit.get("values"):
                        meaning[port] = ("V", unit.get("values").index(source))
                    else:
                        return empty
                continue
            if len(unit.get("values")) != len(outputs):
                return empty
            for position, (address, port) in enumerate(
                zip(unit.get("values"), outputs, strict=True)
            ):
                found = read(address)
                if found is None:
                    return empty
                if unit.get("stage") == "let" and position == len(outputs) - 1:
                    if found[0] == "L":
                        return empty
                    meaning[port] = ("L", len(level_lets))
                    level_lets.append(found)
                elif unit.get("stage") != "projection":
                    meaning[port] = found
                elif "aggregate" in kinds:
                    if found[0] not in ("K", "V"):
                        return empty
                    if found[0] == "V":
                        projected.add(found[1])
                    items.append(
                        ("read", keys[found[1]])
                        if found[0] == "K"
                        else values[found[1]]
                    )
                else:
                    items.append(("read", found))
        # MC G1: each `let` of an aggregate level read only by its sums, in
        # its WHERE as anywhere else; each sum read by its level's
        # projection, so that the law sees it.
        if (
            None in keys
            or any(
                item[0] == "sum" and position not in projected
                for position, item in enumerate(values)
            )
            or any(item[1] is None and item != ("count", None) for item in items)
            or level_lets
            and (
                "aggregate" not in kinds
                or not _mysql_compiled_lets(
                    records,
                    group[kinds.index("aggregate") - 1 :: -1],
                    group[kinds.index("aggregate")],
                )
            )
        ):
            return empty
        lower = (group[-1].address, group[-1].get("outputs"))
        levels.append(
            (join, "where" in kinds, tuple(level_lets), tuple(keys), tuple(items))
        )
    return frozenset(sums) if levels_law.chain(tuple(levels)) else empty


# MC G8 (project_sql_emission_levels): the plan tables a chain of levels may
# hold, a WHERE, value `let`s and the per-order JOIN among them, and the
# fields of each of its definitions as written that may be set.
_MYSQL_G8_PLAN_TABLES = _MYSQL_S03_PLAN_TABLES | {"filters", "let_values"}
_MYSQL_G8_AUTHORED = _MYSQL_S03_AUTHORED | {"where_clause"}


def mysql_g8_statement(request) -> bool:
    """MC G8: whether this MySQL statement is a chain of levels
    (levels.chain), from its plan and bound contract: the selected definition
    reads by FROM one definition of its module by its own name, and so on
    down to one of its sources (or two, by the per-order level's JOIN); each
    definition is a run of `let`, WHERE, aggregate and projection blocks over
    its one input, sets only _MYSQL_G8_AUTHORED fields as written, and every
    `let` of the statement is a value `let` read only as the whole argument
    of a `sum` (mysql_sum_lets). An imported source or definition, a
    relation alias read by FROM, an unread window and a read qualified by a
    definition's name keep main's refusal (D77.24). Linear in the plan and the module's
    definitions. No statement is one while emission derives as main
    (AS_MAIN)."""

    from pietto import ast_nodes as ast
    from pietto._project import project_sql_emission_levels as levels_law
    from pietto._project import project_sql_emission_sum_forms as forms
    from pietto._project.module_catalog import authored_definitions
    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    plan = request.plan
    if (
        AS_MAIN.get()
        or request.family != "mysql"
        or not plan.blocks
        or any(
            type(value := getattr(plan, name)) is tuple
            and value
            and name not in _MYSQL_G8_PLAN_TABLES
            for name in plan.__dataclass_fields__
        )
        or not mysql_sum_lets(plan)
    ):
        return False
    owner = plan.scope.selected_owner
    module = plan.scope.completed.semantic_result.modules[owner.module_position]
    if any(binding.module is not module for binding in plan.sources):
        return False
    stage = row.ProjectSQLStageKind
    groups: list[list] = []
    for block in plan.blocks:
        if groups and groups[-1][0].definition is block.definition:
            groups[-1].append(block)
        else:
            groups.append([block])
    # The chain as written, top first, by name in the selected module.
    definitions = authored_definitions(module)
    named: dict[Any, Any] = {}
    for definition in definitions:
        name = getattr(definition, "name", None)
        named[name] = None if name in named else definition
    written: list[Any] = []
    current: Any = definitions[owner.declaration_position]
    while type(current) in (ast.QueryDef, ast.TableDef) and len(written) < len(groups):
        if current.from_clause.binding_name is not None or any(
            getattr(current, name) not in (None, ())
            for name in current.__dataclass_fields__
            if name not in _MYSQL_G8_AUTHORED
        ):
            return False
        written.append(current)
        current = named.get(current.from_clause.source_name)
    route = bool(written) and bool(written[-1].join_clauses)
    joined = (
        _written_join(written[-1], named, (ast.AuthoredJoinKind.LEFT,))
        if route
        else None
    )
    if (
        type(current) is not ast.SourceDef
        or len(written) != len(groups)
        or any(definition.join_clauses for definition in written[:-1])
        or route
        and (
            joined is None
            or not _mysql_g8_shapes(
                named.get(current.shape_name),
                named.get(
                    getattr(named.get(joined[1].expression.name), "shape_name", None)
                ),
            )
        )
        or sum(len(definition.naming_declarations) for definition in written)
        != len(plan.let_values) + route
    ):
        return False
    carriers: dict[Any, dict[str, tuple[int, str | None]]] = {}
    for source in request.sources:
        name = json.loads(source.selector)["name"]
        carriers[name] = (
            {}
            if name in carriers
            else {
                field.name: (field.ordinal, forms.carrier(field.representation))
                for field in source.fields
            }
        )
    bindings: dict[Any, Any] = {binding.ref: binding for binding in plan.sources}
    stages: dict[Any, Any] = {port.ref: port for port in plan.stage_ports}
    inputs: dict[Any, Any] = {port.ref: port for port in plan.input_ports}
    sources: dict[Any, Any] = {port.ref: port for port in plan.source_ports}
    joins: dict[Any, Any] = {port.ref: port for port in plan.join_ports}
    join_inputs: dict[Any, Any] = {item.ref: item for item in plan.join_inputs}
    lets: dict[Any, Any] = {value.port: value for value in plan.let_values}
    keys: dict[Any, Any] = {key.ref: key for key in plan.group_keys}
    aggregates: dict[Any, Any] = {value.ref: value for value in plan.aggregates}

    # A read qualified by a definition's name, in an item, `let`, WHERE or
    # key of a level above the bottom, is G4's (D77.24): only the bottom's
    # reads of its sources may be qualified.
    bottom = {block.ref for block in groups[0]}
    if any(
        type(expression) is row.ProjectSQLReference
        and type(expression.expression) is ast.DottedNameExpr
        and getattr(stages.get(expression.port), "block", None) not in bottom
        for expression in plan.expressions
    ) or any(
        type(getattr(key.source.item, "key", None)) is ast.DottedNameExpr
        and getattr(stages.get(key.input), "block", None) not in bottom
        for key in plan.group_keys
    ):
        return False

    def field(port, side):
        """A source port as a column of ``side``."""
        binding = bindings.get(getattr(port, "owner", None))
        if binding is None:
            return None
        ordinal, carrier = carriers.get(binding.declaration.name, {}).get(
            port.identity.name, (None, None)
        )
        return None if carrier is None else (side, ordinal, carrier)

    def origin(ref):
        """The input port, `let` value, key or aggregate a stage port carries."""
        while ref in stages and ref not in lets:
            ref = stages[ref].source
        return ref

    def operand(ref, owned):
        """The expression ``ref`` as a read of a column, or None."""
        expression: Any = _planned(plan, ref)
        if type(expression) not in (
            row.ProjectSQLReference,
            row.ProjectSQLJoinedReference,
        ):
            return None
        return owned(origin(expression.port))

    chain = []
    exports: dict = {}
    for index, blocks in enumerate(groups):
        boundary = blocks[0].boundary
        kinds = tuple(block.kind for block in blocks)
        lowest = index == 0
        if any(block.boundary is not boundary for block in blocks):
            return False
        if route and lowest:
            if kinds != (stage.AGGREGATE, stage.PROJECTION) or len(plan.joins) != 1:
                return False
        elif (
            type(boundary) is not ProjectSQLBoundary
            or boundary.reason
            is not (
                ProjectSQLBoundaryReason.SOURCE_INPUT
                if lowest
                else ProjectSQLBoundaryReason.NAMED_INPUT
            )
            or (
                boundary.use.producer not in bindings
                if lowest
                else boundary.use.producer is not groups[index - 1][0].definition
            )
            or kinds
            not in {
                (*(stage.LET,) * kinds.count(stage.LET), *middle, stage.PROJECTION)
                for middle in (
                    (),
                    (stage.WHERE,),
                    (stage.AGGREGATE,),
                    (stage.WHERE, stage.AGGREGATE),
                )
            }
        ):
            return False
        names = [
            value
            for block in blocks
            if block.kind is stage.LET
            for value in plan.let_values
            if stages.get(value.port) is not None
            and stages[value.port].block is block.ref
        ]

        def owned(ref, boundary=boundary, names=names, lowest=lowest):
            """A column this level reads: an input, JOIN or `let` port."""
            if ref in lets:
                value = lets[ref]
                return ("L", names.index(value)) if value in names else None
            if ref in joins and route and lowest:
                port: Any = joins[ref]
                if port.input is None:
                    port = joins.get(port.source)
                item = join_inputs.get(getattr(port, "input", None))
                if item is None:
                    return None
                return field(sources.get(port.source), "AB"[item.ordinal])
            port = inputs.get(ref)
            if port is None or port not in getattr(
                getattr(boundary, "use", None), "ports", ()
            ):
                return None
            if lowest:
                return field(sources.get(port.producer_port), "A")
            return exports.get(port.producer_port)

        level_lets = []
        for value in names:
            column = operand(value.expression, owned)
            if column is None or column[0] == "L":
                return False
            level_lets.append(column)
        projection = blocks[-1]
        items = []
        level_keys: tuple = ()
        join = None
        if stage.AGGREGATE in kinds:
            aggregation = next(
                (
                    item
                    for item in plan.aggregations
                    if item.block is blocks[kinds.index(stage.AGGREGATE)].ref
                ),
                None,
            )
            if aggregation is None:
                return False
            level_keys = tuple(
                owned(origin(keys[key].input)) if key in keys else None
                for key in aggregation.keys
            )
            values = {}
            for ref in aggregation.aggregates:
                value = aggregates.get(ref)
                if value is None or value.order_by or len(value.arguments) > 1:
                    return False
                function = function_name(value.source)
                values[value.ref] = (
                    function,
                    operand(value.arguments[0], owned) if value.arguments else None,
                )
                if value.arguments and values[value.ref][1] is None:
                    return False
            projections = {
                item.export: item.input
                for item in plan.aggregate_projections
                if item.block is projection.ref
            }
            for export in projection.exports:
                found = origin(projections.get(export))
                if found in keys:
                    position = aggregation.keys.index(found)
                    items.append(("read", level_keys[position]))
                elif found in values:
                    items.append(values[found])
                else:
                    return False
        else:
            projections = {
                item.export: item.expression
                for item in plan.projections
                if item.block is projection.ref
            }
            for export in projection.exports:
                column = (
                    operand(projections[export], owned)
                    if export in projections
                    else None
                )
                if column is None:
                    return False
                items.append(("read", column))
        if route and lowest:
            on = _planned(plan, plan.joins[0].on)
            join_item = join_inputs.get(plan.joins[0].inputs[0])
            joined_item = join_inputs.get(plan.joins[0].inputs[1])
            if (
                plan.joins[0].equalities
                or type(on) is not row.ProjectSQLComparison
                or on.expression.operator != "=="
                or join_item is None
                or joined_item is None
            ):
                return False
            ends = []
            for side in (on.left, on.right):
                read = _planned(plan, side)
                port: Any = joins.get(getattr(read, "port", None))
                item = join_inputs.get(getattr(port, "input", None))
                ends.append(
                    None
                    if item is None
                    else field(sources.get(port.source), "AB"[item.ordinal])
                )
            layouts = []
            for item in (join_item, joined_item):
                binding = bindings.get(item.producer)
                fields = carriers.get(
                    getattr(getattr(binding, "declaration", None), "name", None), {}
                )
                layouts.append(tuple(carrier for _, carrier in sorted(fields.values())))
            join = (
                str(plan.joins[0].kind),
                ends[0],
                ends[1],
                layouts[0],
                layouts[1],
            )
        if None in level_keys or any(
            item[1] is None and item != ("count", None) for item in items
        ):
            return False
        exports = {
            export: ("U", position)
            for position, export in enumerate(projection.exports)
        }
        chain.append(
            (join, stage.WHERE in kinds, tuple(level_lets), level_keys, tuple(items))
        )
    return levels_law.chain(tuple(chain))


TEXT_WIDTH_OBLIGATION = "text_result_width"
TEXT_PROFILE = {
    "postgres": ("UTF8", "C", "NO PAD"),
    "mysql": ("utf8mb4", "utf8mb4_0900_bin", "NO PAD"),
}


@dataclass(frozen=True, slots=True, eq=False)
class SQLParameterRead:
    """One header-parameter read rendered as a typed native placeholder."""

    original: Any
    use: Any
    physical_type: str
    realization: Realization


def parameter_realization(
    family: str,
    tag: str,
    nullable: bool,
    *,
    bound: bool = False,
    value=None,
    decimal: tuple[int, int] | None = None,
) -> Realization:
    """One read's image: the declared carrier for the unbound template, or the
    exact domain of a bound value. NULL has no value, so any domain holds; the
    narrowest one (Int 0..0, Text width 0) keeps every downstream law exact.

    A Decimal, Date, Timestamp or UUID read has its source carrier, bound or
    not: a Decimal the declared (precision, scale) as ``decimal``, which a
    bound value fits exactly; it has no binding obligation."""
    storage = {"kind": parameters.parameter_physical(family, tag)}
    if storage["kind"] is None:
        raise ValueError("query parameter type")
    if tag in parameters.PARAMETER_VALUE_TYPES:
        if bound and not (
            value is None or parameters.parameter_valid(tag, value, family, decimal)
        ):
            raise ValueError("query parameter value")
        if tag == "Decimal":
            if decimal is None:
                raise ValueError("query parameter type")
            precision, scale = decimal
            domain = {"kind": "decimal", "precision": precision, "scale": scale}
            storage = {**storage, "precision": precision, "scale": scale}
        elif tag == "Timestamp":
            domain = {"kind": "timestamp"}
            storage = {**storage, "fractional_seconds": 6}
        elif tag == "Date":
            domain = {"kind": "date"}
        else:
            domain = {"kind": "uuid", "encoding": "standard_bytes"}
        return Realization(tag, storage, nullable, domain)
    if bound and tag in ("Int", "Text"):
        if value is not None and not parameters.value_valid(tag, value, family):
            raise ValueError("query parameter value")
        if tag == "Int":
            exact = 0 if value is None else value
            return Realization(
                tag,
                storage,
                nullable,
                {"kind": "int_range", "min": str(exact), "max": str(exact)},
                (exact, exact),
            )
        encoding, collation, padding = TEXT_PROFILE[family]
        return Realization(
            tag,
            storage,
            nullable,
            {
                "kind": "text",
                "max_characters": 0 if value is None else len(value),
                "encoding": encoding,
                "collation": collation,
                "padding": padding,
            },
        )
    if tag == "Bool":
        return Realization(tag, storage, nullable, {"kind": "bool01"})
    if tag == "Float":
        return Realization(
            tag, storage, nullable, {"kind": "finite_float", "format": "binary64"}
        )
    if tag == "Int":
        low, high = -(1 << 63), (1 << 63) - 1
        return Realization(
            tag,
            storage,
            nullable,
            {"kind": "int_range", "min": str(low), "max": str(high)},
            (low, high),
            binding=True,
        )
    if tag != "Text":
        raise ValueError("query parameter type")
    encoding, collation, padding = TEXT_PROFILE[family]
    return Realization(
        tag,
        storage,
        nullable,
        {
            "kind": "text",
            "max_characters": None,
            "encoding": encoding,
            "collation": collation,
            "padding": padding,
        },
        binding=True,
    )


def deferred_int(storage: dict[str, Any] | None, nullable) -> Realization | None:
    """An Int result whose range is proved only at binding, within its carrier."""
    if storage is None:
        return None
    limits = signed_range(storage)
    if limits is None:
        return None
    low, high = limits
    return Realization(
        "Int",
        storage,
        nullable,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
        binding=True,
        obligation=INT_RANGE_OBLIGATION,
    )


@dataclass(frozen=True, slots=True, eq=False)
class StageColumn:
    """A scan column an expression may read, with its terminal and retained origin."""

    position: int
    name: str
    terminal: Any
    realization: Realization
    field: Any = None
    source_port: Any = None
    literal: Any = None
    scope: Any = None
    aggregate: Any = None
    """One grouped determinant or aggregate result this value ultimately is."""
    window: Any = None
    """One window occurrence result this value ultimately is."""


@dataclass(frozen=True, slots=True, eq=False)
class SQLStageReference:
    original: Any
    port: Any
    column: StageColumn
    realization: Realization
    scope: Any = None
    """The relation alias this reference reads, when its body has more than one."""


@dataclass(frozen=True, slots=True, eq=False)
class SQLOperation:
    original: Any
    kind: str
    operands: tuple[Any, ...]
    realization: Realization


@dataclass(frozen=True, slots=True, eq=False)
class SQLBlockTarget:
    """One expression block use's realized producer and its generated alias.

    ``producer`` is the producer definition's terminal unit, or the bound
    source when the producer is a source; ``source`` is then its plan binding.
    """

    use: Any
    producer: Any
    source: Any
    symbol: Any


@dataclass(frozen=True, slots=True, eq=False)
class SQLCaptureScope:
    """The outer row one capture record reads at its let's single read.

    ``alias`` is the reading body's own FROM alias and ``reads`` are that
    body's stage columns of the captured input's fields, in capture order.
    """

    capture: Any
    alias: Any
    reads: tuple[StageColumn, ...]


@dataclass(frozen=True, slots=True, eq=False)
class SQLCapturedReference:
    """One captured field read: ``<outer alias>.<outer column>`` (correlation)."""

    original: Any
    capture: Any
    column: StageColumn
    realization: Realization
    scope: Any


@dataclass(frozen=True, slots=True, eq=False)
class SQLBlockRead:
    """A read of one whole producer through one expression block use.

    ``exists``: ``EXISTS (SELECT 1 FROM p AS e)``. ``scalar``: ``(SELECT e.c
    FROM p AS e)`` of output ``column``, NULL when ``p`` has no row.
    ``in``/``not_in``: the three-valued ``(v [NOT] IN (SELECT e.c FROM p AS e))``
    of its one operand ``v`` over the producer's one output column ``c``.
    """

    original: Any
    target: SQLBlockTarget
    realization: Realization
    kind: str = "exists"
    column: int | None = None
    operands: tuple[Any, ...] = ()
    predicate: Any = None


@dataclass(frozen=True, slots=True, eq=False)
class SQLListOperation:
    """A list operation of one row (S06) over the carrier of its collected
    list (``pg_column_arrays_v1``: the count column, then one array per child
    field). `len` reads the count; `sum` and `any` read the element rows of
    the arrays, zipped by position, as an Unnest does::

        CASE WHEN m."xs" IS NULL THEN NULL ELSE COALESCE((SELECT
            CAST(SUM(CAST(<body> AS pg_catalog.int8)) AS pg_catalog.int8)
            FROM ROWS FROM (pg_catalog.unnest(m."a"), ...) AS "l" ("c0", ...)
            [WHERE <test>]), 0) END
        CASE WHEN m."xs" IS NULL THEN NULL ELSE EXISTS (SELECT 1 FROM ROWS
            FROM (...) AS "l<k>" (...) WHERE <test>) END

    A NULL count is a missing container (G1-03); `[]` counts 0 with NULL
    arrays, which unnest to no row; a NULL body or test adds no sample and no
    match (C2). ``operation`` is `len`, `sum` or `any`; ``port`` the read
    input port; ``read`` the input's NestedRead there, ``symbol`` the element
    rows' alias (None for `len`), ``operands`` the realized body and test.
    """

    original: Any
    operation: str
    port: Any
    read: Any
    symbol: Any
    operands: tuple[Any, ...]
    realization: Realization


LIST_FUNCTION = "pg_catalog.unnest"
LIST_ALIAS = "l"


def list_node_count(node: SQLListOperation) -> int:
    """The count read of a `len`; for `sum` and `any` also each array call
    and each element column alias."""
    return 1 if node.symbol is None else 1 + 2 * len(node.read.arrays)


def list_element_column(operation: SQLListOperation, position: int) -> StageColumn:
    """The element column ``c<position>`` of one list operation's rows."""
    from pietto._project import project_sql_emission_nested as collecting

    group = collecting.original_group(operation.read.group)
    if group is None or not 0 <= position < len(group.collect.children):
        raise ValueError("list element outside its collected children")
    child = group.lateral.target.producer.columns[position].column
    return replace(
        child,
        position=position,
        name=f"c{position}",
        terminal=group.collect.children[position],
        scope=operation.symbol,
    )


def _list_operation(request, columns, expression, tag, nullable, uses, reference_type):
    """Realize one list operation over the NestedRead at its port."""
    from pietto._project import project_sql_emission_unnest as unnesting
    from pietto._project.project_sql_emission_ast import SQLSymbol

    family = request.family
    if family != "postgres":
        return None, ("PIE-B1003", "list_operation_not_admitted_on_target")
    read = columns.get(expression.port)
    if type(read) is not unnesting.NestedRead or not read.arrays:
        return None, ("PIE-B1001", "list_read_outside_stage_scope")
    if expression.operation == "len":
        if tag != "Int" or expression.body is not None or expression.condition:
            return None, ("PIE-B1002", "list_operation_type_drift")
        realization = _checked_int({"kind": "pg_int8"}, 0, SIGNED64[1], nullable)
        if realization is None:
            return None, ("PIE-B1002", "list_operation_type_drift")
        return (
            SQLListOperation(
                expression, "len", expression.port, read, None, (), realization
            ),
            None,
        )
    realization = (
        _bool(family, nullable)
        if expression.operation == "any"
        else _checked_int({"kind": "pg_int8"}, *SIGNED64, nullable)
    )
    if realization is None:
        return None, ("PIE-B1002", "list_operation_type_drift")
    operation = SQLListOperation(
        expression,
        expression.operation,
        expression.port,
        read,
        # One name serves every list operation: each is its own scalar
        # subquery and none holds another, so the innermost `l` is its own.
        SQLSymbol(0, expression.ref, LIST_ALIAS),
        (),
        realization,
    )
    scoped = {**columns, (expression.ref, "list"): operation}
    operands = []
    for position, child in enumerate((expression.body, expression.condition)):
        if child is None:
            continue
        value, problem = build_row_value(
            request, scoped, child, uses, reference_type=reference_type
        )
        if problem is not None:
            return None, problem
        realized = realization_of(value, family)
        expected = "Int" if expression.operation == "sum" and position == 0 else "Bool"
        if realized.tag != expected or (
            expected == "Bool" and realized.domain.get("kind") != "bool01"
        ):
            return None, ("PIE-B1003", "list_operation_operand_not_admitted")
        operands.append(value)
    if (
        expression.operation not in {"sum", "any"}
        or tag != ("Bool" if expression.operation == "any" else "Int")
        or expression.body is None
        or (expression.operation == "any" and expression.condition is not None)
    ):
        return None, ("PIE-B1002", "list_operation_type_drift")
    return replace(operation, operands=tuple(operands)), None


def _element_reference(columns, expression, tag, nullable):
    operation = columns.get((expression.operation, "list"))
    return element_reference(expression, operation, expression.position, tag, nullable)


def element_reference(original, operation, position, tag, nullable):
    """``"l"."c<j>"``: one child field of its list operation's element, typed
    as the collected let's field (a nullable read may widen a column)."""
    if type(operation) is not SQLListOperation or operation.symbol is None:
        return None, ("PIE-B1001", "element_read_outside_list_scope")
    column = list_element_column(operation, position)
    realization = column.realization
    if realization.tag != tag:
        return None, ("PIE-B1002", "element_read_logical_type_drift")
    if realization.nullable != nullable:
        if nullable is not True:
            return None, ("PIE-B1002", "element_read_null_drift")
        realization = replace(realization, nullable=True)
    return (
        SQLStageReference(
            original, operation.original.ref, column, realization, operation.symbol
        ),
        None,
    )


def any_column(request, target: SQLBlockTarget, position: int) -> StageColumn | None:
    """Read one actual producer field under this lexical ANY input alias."""
    if type(position) is not int or position < 0:
        return None
    if target.source is None:
        read = block_column(target, position)
        if read is None:
            return None
        return replace(
            target.producer.columns[position].column,
            name=read[0],
            scope=target.symbol,
        )
    definitions = tuple(
        item
        for item in request.plan.bindings.definitions
        if item.ref is target.use.producer
    )
    fields = tuple(
        field for field in target.producer.fields if field.ordinal == position
    )
    if (
        len(definitions) != 1
        or len(fields) != 1
        or position >= len(definitions[0].exports)
    ):
        return None
    realization = field_realization(fields[0])
    if realization is None:
        return None
    port = definitions[0].exports[position].ref
    return StageColumn(
        position,
        fields[0].column,
        port,
        realization,
        field=fields[0],
        source_port=port,
        scope=target.symbol,
    )


def block_column(target: SQLBlockTarget, column: int) -> tuple[str, Realization] | None:
    """The rendered name and realization of one producer output a scalar reads."""
    if target.source is not None:
        fields = tuple(f for f in target.producer.fields if f.ordinal == column)
        realization = None if len(fields) != 1 else field_realization(fields[0])
        return None if realization is None else (fields[0].column, realization)
    producer = target.producer
    if producer.symbol is None and not producer.final:
        # A capturing let's inline body: its derived-table columns are its labels.
        if not 0 <= column < len(producer.columns):
            return None
        return producer.columns[column].label, producer.columns[
            column
        ].column.realization
    if not 0 <= column < len(producer.cte_columns) or len(producer.columns) != len(
        producer.cte_columns
    ):
        return None
    return producer.cte_columns[column].name, producer.columns[
        column
    ].column.realization


def scalar_read_realization(read: Realization) -> Realization:
    """A scalar read keeps its column's carrier and is NULL for no row."""
    return Realization(read.tag, read.storage, True, read.domain, read.proven_int_range)


def block_read_column(target: SQLBlockTarget) -> tuple[str, Realization] | None:
    """The name and realization of the one output column a membership read
    compares with, or None when the producer has not exactly one column."""
    if target.source is not None:
        width = len(target.producer.fields)
    else:
        width = len(target.producer.columns)
    return block_column(target, 0) if width == 1 else None


def signed_range(storage) -> tuple[int, int] | None:
    bits = INT_WIDTHS.get(storage["kind"])
    if bits is None:
        return None
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def int_bounds(realization: Realization) -> tuple[int, int] | None:
    domain = realization.domain
    if realization.tag != "Int" or domain.get("kind") != "int_range":
        return None
    return int(domain["min"]), int(domain["max"])


def proven_int_bounds(realization: Realization) -> tuple[int, int] | None:
    if realization.tag != "Int" or realization.proven_int_range is None:
        return None
    low, high = realization.proven_int_range
    if type(low) is not int or type(high) is not int or low > high:
        return None
    return low, high


def source_realization(realization: Realization) -> Realization | None:
    """Keep result-domain requirements; source Int proof is its signed carrier."""
    if realization.tag != "Int":
        return realization
    bounds = signed_range(realization.storage)
    if bounds is None:
        return None
    return Realization(
        realization.tag,
        realization.storage,
        realization.nullable,
        realization.domain,
        bounds,
    )


def value_tag(expression) -> str | None:
    """Read the retained logical builtin name; never infer one."""
    value_type = expression.value_type
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    return value_type.resolved_type.name


def value_nullable(expression) -> bool | str | None:
    return NULLABILITY.get(expression.value_type.nullability)


def field_realization(field) -> Realization | None:
    """The physical realization the accepted contract already fixed for one field."""
    value = json.loads(field.representation)
    logical = field.field.evidence.resolved_type
    if logical.kind is not ProjectResolvedTypeKind.BUILTIN:
        return None
    return source_realization(
        Realization(logical.name, value["storage"], value["nullable"], value["domain"])
    )


def constant_realization(value, family: str) -> Realization:
    if type(value) is parameters.SQLNull:
        value_type = value.original.value_type
        if (
            value_type.kind is not ValueTypeKind.KNOWN
            or value_type.resolved_type.kind is not TypeKind.BUILTIN
            or value_type.nullability is not EffectiveNullability.NULLABLE
        ):
            raise ValueError("compiled typed NULL requires a known nullable builtin")
        return Realization(
            value_type.resolved_type.name,
            {"kind": "typed_null"},
            True,
            {"kind": "typed_null"},
        )
    described = parameters.representation(value, family)
    tag = parameters.tag_of(value.original)
    assert tag is not None
    result = parameters.result_value(value)
    return Realization(
        tag,
        described["storage"],
        described["nullable"],
        described["domain"],
        (result, result) if tag == "Int" and type(result) is int else None,
    )


def _arithmetic_storage(family: str, left: Realization, right: Realization):
    """The target's own documented signed integer result type; never a blanket CAST."""
    if family == "mysql":
        return {"kind": "my_signed_int"}
    left_bits = INT_WIDTHS.get(left.storage["kind"])
    right_bits = INT_WIDTHS.get(right.storage["kind"])
    if left_bits is None or right_bits is None:
        return None
    return {16: {"kind": "pg_int2"}, 32: {"kind": "pg_int4"}, 64: {"kind": "pg_int8"}}[
        max(left_bits, right_bits)
    ]


def _interval(operator: str, left: tuple[int, int], right: tuple[int, int]):
    if operator == "+":
        return left[0] + right[0], left[1] + right[1]
    if operator == "-":
        return left[0] - right[1], left[1] - right[0]
    products = [a * b for a in left for b in right]
    return min(products), max(products)


def _text_domain(realization: Realization):
    return tuple(
        realization.domain.get(key) for key in ("encoding", "collation", "padding")
    )


def _decimal_domain(realization: Realization):
    return tuple(realization.domain.get(key) for key in ("precision", "scale"))


def _typed_null(realization: Realization) -> bool:
    return (
        realization.nullable is True
        and realization.storage == {"kind": "typed_null"}
        and realization.domain == {"kind": "typed_null"}
    )


def typed_null_decimal(realization: Realization) -> bool:
    """A Decimal typed NULL (`abs(None)`) has no precision for an output type."""
    return realization.tag == "Decimal" and _typed_null(realization)


def _concrete_values(values):
    """Return one established carrier, while retaining typed NULL's tag check."""
    concrete = tuple(value for value in values if not _typed_null(value))
    if not concrete:
        return None
    first = concrete[0]
    if any(value.tag != first.tag for value in values):
        return None
    return first


def _membership_carrier_matches(first: Realization, value: Realization) -> bool:
    if _typed_null(value):
        return value.tag == first.tag
    if value.tag != first.tag:
        return False
    if first.tag == "Int":
        return (
            first.storage.get("kind") in INT_WIDTHS
            and value.storage.get("kind") in INT_WIDTHS
            and int_bounds(first) is not None
            and int_bounds(value) is not None
        )
    if first.tag == "Text":
        return (
            _text_result(
                "postgres", first, first.nullable, first.domain.get("max_characters")
            )
            is not None
            and _text_result(
                "postgres", value, value.nullable, value.domain.get("max_characters")
            )
            is not None
            and _text_domain(first) == _text_domain(value)
        ) or (
            _text_result(
                "mysql", first, first.nullable, first.domain.get("max_characters")
            )
            is not None
            and _text_result(
                "mysql", value, value.nullable, value.domain.get("max_characters")
            )
            is not None
            and _text_domain(first) == _text_domain(value)
        )
    if first.tag == "Decimal":
        return first.storage == value.storage and _decimal_domain(
            first
        ) == _decimal_domain(value)
    if first.tag == "Bool":
        return first.domain == value.domain == {"kind": "bool01"} and (
            first.storage == value.storage == {"kind": "pg_bool"}
            or first.storage
            in (
                {"kind": "my_bool01"},
                {"kind": "my_signed_bool"},
            )
            and value.storage
            in (
                {"kind": "my_bool01"},
                {"kind": "my_signed_bool"},
            )
        )
    if first.tag == "Float":
        return first.storage == value.storage and first.domain == value.domain == {
            "kind": "finite_float",
            "format": "binary64",
        }
    return first.storage == value.storage and first.domain == value.domain


def _text_result(family, value, nullable, maximum):
    """Preserve the one admitted text profile with an explicit result bound."""
    expected = (
        ("UTF8", "C", "NO PAD")
        if family == "postgres"
        else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
    )
    domain = value.domain
    if value.binding and maximum is None:
        return _binding_text_result(family, value, nullable, expected)
    if (
        value.tag != "Text"
        or type(maximum) is not int
        or maximum < 0
        or set(domain) != {"kind", "max_characters", "encoding", "collation", "padding"}
        or domain["kind"] != "text"
        or type(domain["max_characters"]) is not int
        or domain["max_characters"] < 0
        or _text_domain(value) != expected
    ):
        return None
    if family == "postgres":
        if value.storage != {"kind": "pg_text"}:
            return None
        storage = {"kind": "pg_text"}
    elif family == "mysql":
        if maximum > 16383 or not (
            value.storage == {"kind": "my_utf8mb4_text"}
            or (
                value.storage.get("kind") == "my_varchar"
                and set(value.storage) == {"kind", "length"}
                and type(value.storage["length"]) is int
                and domain["max_characters"] <= value.storage["length"] <= 16383
            )
        ):
            return None
        storage = {"kind": "my_varchar", "length": maximum}
    else:
        return None
    return Realization(
        "Text",
        storage,
        nullable,
        {
            "kind": "text",
            "max_characters": maximum,
            "encoding": expected[0],
            "collation": expected[1],
            "padding": expected[2],
        },
    )


def _binding_text_result(family, value, nullable, expected):
    """A Text result whose width each binding fixes and checks (MySQL caps it)."""
    domain = value.domain
    if (
        value.tag != "Text"
        or set(domain) != {"kind", "max_characters", "encoding", "collation", "padding"}
        or domain["kind"] != "text"
        or domain["max_characters"] is not None
        or _text_domain(value) != expected
        or value.storage
        not in (
            ({"kind": "pg_text"},)
            if family == "postgres"
            else (
                {"kind": "my_utf8mb4_text"},
                {"kind": "my_varchar", "length": None},
            )
        )
    ):
        return None
    return Realization(
        "Text",
        {"kind": "pg_text"}
        if family == "postgres"
        else {"kind": "my_varchar", "length": None},
        nullable,
        dict(domain),
        binding=True,
        obligation=TEXT_WIDTH_OBLIGATION,
    )


def _text_carrier_result(family, values, nullable, maximum=None):
    """Keep one Text profile while deriving an explicitly bounded result carrier."""
    carrier = _concrete_values(values)
    if carrier is None or carrier.tag != "Text":
        return None
    if maximum is None and any(value.binding for value in values):
        # A binding fixes the width; every branch keeps the one Text profile.
        if any(
            not _typed_null(value)
            and (
                _text_domain(value) != _text_domain(carrier)
                or _text_result(
                    family,
                    value,
                    value.nullable,
                    None if value.binding else value.domain.get("max_characters"),
                )
                is None
            )
            for value in values
        ):
            return None
        return _binding_text_result(
            family,
            next(value for value in values if value.binding),
            nullable,
            TEXT_PROFILE.get(family),
        )
    widths = []
    for value in values:
        if _typed_null(value):
            if value.tag != "Text":
                return None
            continue
        width = value.domain.get("max_characters")
        if (
            value.tag != "Text"
            or _text_domain(value) != _text_domain(carrier)
            or _text_result(family, value, value.nullable, width) is None
        ):
            return None
        widths.append(width)
    if not widths:
        return None
    result_width = max(widths) if maximum is None else maximum
    return _text_result(family, carrier, nullable, result_width)


def _int_carrier_result(family, values, nullable, preserve_input=False):
    """Join proved signed ranges without selecting a cross-target storage family."""
    carrier = _concrete_values(values)
    kinds = {
        "postgres": {"pg_int2", "pg_int4", "pg_int8"},
        "mysql": {"my_smallint", "my_int", "my_bigint", "my_signed_int"},
    }.get(family)
    if carrier is None or carrier.tag != "Int" or kinds is None:
        return None
    bounds = []
    for value in values:
        if _typed_null(value):
            if value.tag != "Int":
                return None
            continue
        current = proven_int_bounds(value)
        if (
            value.tag != "Int"
            or set(value.storage) != {"kind"}
            or value.storage["kind"] not in kinds
            or current is None
        ):
            return None
        bounds.append((value, current))
    if not bounds:
        return None
    binding = any(value.binding for value in values)
    if preserve_input and not _typed_null(values[0]):
        value, _ = bounds[0]
        return Realization(
            "Int",
            value.storage,
            nullable,
            value.domain,
            value.proven_int_range,
            binding=binding,
        )
    low = min(current[0] for _, current in bounds)
    high = max(current[1] for _, current in bounds)
    storage = (
        {"kind": "my_signed_int"}
        if family == "mysql"
        else {
            16: {"kind": "pg_int2"},
            32: {"kind": "pg_int4"},
            64: {"kind": "pg_int8"},
        }[max(INT_WIDTHS[value.storage["kind"]] for value, _ in bounds)]
    )
    checked = _checked_int(storage, low, high, nullable)
    return None if checked is None else replace(checked, binding=binding)


def _bool_carrier_result(family, values, nullable, preserve_input=False):
    """Admit only the selected target's Bool source and literal carriers."""
    carrier = _concrete_values(values)
    allowed = (
        ({"kind": "pg_bool"},)
        if family == "postgres"
        else ({"kind": "my_bool01"}, {"kind": "my_signed_bool"})
        if family == "mysql"
        else ()
    )
    if carrier is None or carrier.tag != "Bool" or not allowed:
        return None
    for value in values:
        if _typed_null(value):
            if value.tag != "Bool":
                return None
            continue
        if (
            value.tag != "Bool"
            or value.storage not in allowed
            or value.domain != {"kind": "bool01"}
        ):
            return None
    if preserve_input and not _typed_null(values[0]):
        return Realization("Bool", values[0].storage, nullable, values[0].domain)
    return _bool(family, nullable)


CHILD_FIELDS = {
    row.ProjectSQLUnary: ("operand",),
    row.ProjectSQLBinary: ("left", "right"),
    row.ProjectSQLComparison: ("left", "right"),
    row.ProjectSQLIsNull: ("value",),
    row.ProjectSQLBetween: ("value", "lower", "upper"),
    row.ProjectSQLConditional: ("when_true", "condition", "when_false"),
    row.ProjectSQLMembership: ("value", "options"),
    row.ProjectSQLCast: ("value",),
    row.ProjectSQLRelationMembership: ("value",),
    row.ProjectSQLAny: ("predicate",),
}


def rendered_operand_order(kind, count):
    if kind == "conditional" and count == 3:
        return (1, 0, 2)
    return tuple(range(count))


def tree_nodes(plan, reference):
    """Preorder original nodes of one authored tree, following its operand links."""
    return _tree_nodes(plan, reference, render_order=False)


def rendered_tree_nodes(plan, reference):
    """Preorder original nodes in the order the SQL renderer visits them."""
    return _tree_nodes(plan, reference, render_order=True)


def _tree_nodes(plan, reference, *, render_order):
    result = []
    pending = [(reference, False)]
    active = set()
    while pending:
        current, leaving = pending.pop()
        if leaving:
            active.remove(id(current))
            continue
        position = getattr(current, "position", None)
        if type(position) is not int or not 0 <= position < len(plan.expressions):
            raise ValueError("expression reference outside the current plan")
        expression = plan.expressions[position]
        if expression.ref is not current or id(current) in active:
            raise ValueError("expression reference identity or cycle")
        active.add(id(current))
        pending.append((current, True))
        result.append(expression)
        if type(expression) is row.ProjectSQLScalarCall:
            children = expression.arguments
        elif type(expression) is row.ProjectSQLListOperation:
            children = tuple(
                child
                for child in (expression.body, expression.condition)
                if child is not None
            )
        elif type(expression) is row.ProjectSQLMembership:
            children = (expression.value, *expression.options)
        else:
            fields = CHILD_FIELDS.get(type(expression), ())
            children = tuple(getattr(expression, name) for name in fields)
            if render_order:
                children = tuple(
                    children[i]
                    for i in rendered_operand_order(
                        "conditional"
                        if type(expression) is row.ProjectSQLConditional
                        else "",
                        len(children),
                    )
                )
        pending.extend((child, False) for child in reversed(children))
    return tuple(result)


def rendered_constant_chains(plan, reference):
    """Every maximal literal/sign chain in SQL rendering order."""
    return _constant_chains(rendered_tree_nodes(plan, reference), plan)


def _constant_chains(expressions, plan):
    result = []
    position = 0
    while position < len(expressions):
        expression = expressions[position]
        chain = parameters.original_chain(plan, expression.ref)
        if chain is None:
            position += 1
            continue
        signs, leaf = chain
        result.append((position + len(signs), expression.ref, leaf))
        position += len(signs) + 1
    return tuple(result)


type ReferenceNode = (
    type[row.ProjectSQLReference]
    | type[row.ProjectSQLJoinedReference]
    | type[row.ProjectSQLMatchReference]
    | type[aggregation.ProjectSQLResultReference]
    | type[plan_windows.ProjectSQLWindowReference]
)


def build_row_value(
    request,
    columns,
    reference,
    uses,
    *,
    reference_type: ReferenceNode = row.ProjectSQLReference,
    mysql_cells: frozenset = frozenset(),
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    """Realize one admitted tree; return (value, None) or (None, (code, detail)).
    ``mysql_cells`` are the stage's S15 and R08 cells (mysql_remainder_cells,
    mysql_division_cells), each the whole value of an item, so no nested
    value takes them."""
    plan = request.plan
    family = request.family
    position = getattr(reference, "position", None)
    if type(position) is not int or not 0 <= position < len(plan.expressions):
        return None, ("PIE-B1008", "expression_reference_outside_plan")
    expression = plan.expressions[position]
    if expression.ref is not reference:
        return None, ("PIE-B1008", "expression_reference_identity")
    chain = parameters.original_chain(plan, reference)
    if chain is not None:
        problem = parameters.chain_problem(plan, reference, family)
        if problem is not None:
            return None, problem
        return parameters.build_value(plan, reference, family, uses), None
    if type(expression) is row.ProjectSQLParameterRead:
        use = parameters.take_use(uses, expression.ref)
        if use is None or use.parameter is not expression.parameter:
            return None, ("PIE-B1008", "native_occurrence_allocation")
        nullable = value_nullable(expression)
        if type(nullable) is not bool:
            return None, ("PIE-B1004", "expression_logical_type_evidence_missing")
        return (
            SQLParameterRead(
                expression,
                use,
                use.physical_type,
                parameter_realization(
                    family,
                    expression.parameter.tag,
                    nullable,
                    decimal=expression.parameter.decimal,
                ),
            ),
            None,
        )
    tag, nullable = value_tag(expression), value_nullable(expression)
    if tag is None or nullable is None:
        return None, ("PIE-B1004", "expression_logical_type_evidence_missing")
    if (
        type(expression) is reference_type
        or type(expression) is plan_windows.ProjectSQLWindowReference
    ):
        # A QUALIFY reference is always a read of an established window result
        # port, whatever reference kind the surrounding stage uses.
        column = columns.get(expression.port)
        if column is None:
            return None, ("PIE-B1001", "reference_outside_stage_scope")
        if column.realization.tag != tag or column.realization.nullable != nullable:
            return None, ("PIE-B1002", "reference_logical_type_or_null_drift")
        return (
            SQLStageReference(
                expression,
                expression.port,
                column,
                column.realization,
                getattr(column, "scope", None),
            ),
            None,
        )
    if type(expression) in {
        row.ProjectSQLReference,
        row.ProjectSQLJoinedReference,
        row.ProjectSQLMatchReference,
        aggregation.ProjectSQLResultReference,
        plan_windows.ProjectSQLWindowReference,
    }:
        return None, ("PIE-B1001", "reference_outside_its_admitted_scope")
    if type(expression) is row.ProjectSQLUnary:
        if expression.expression.operator == "not":
            operand, problem = build_row_value(
                request,
                columns,
                expression.operand,
                uses,
                reference_type=reference_type,
            )
            if problem is not None:
                return None, problem
            inner = realization_of(operand, family)
            if (
                tag != "Bool"
                or inner.tag != "Bool"
                or inner.domain.get("kind") != "bool01"
            ):
                return None, ("PIE-B1003", "unary_not_requires_bool_operand")
            return SQLOperation(
                expression, "not", (operand,), _bool(family, nullable)
            ), None
        if expression.expression.operator not in {"+", "-"}:
            return None, ("PIE-B1003", "unary_operator_not_admitted")
        operand, problem = build_row_value(
            request, columns, expression.operand, uses, reference_type=reference_type
        )
        if problem is not None:
            return None, problem
        inner = realization_of(operand, family)
        if tag == inner.tag == "Decimal" and (
            # This reader's own S17 pairing check.
            family == "postgres" or pairing.project_form(request) is not None
        ):
            if _decimal_parameters(family, inner) is None:
                return None, ("PIE-B1004", "decimal_source_carrier_missing")
            return SQLOperation(
                expression, "sign", (operand,), replace(inner, nullable=nullable)
            ), None
        if tag == "Float":
            checked = float_sign(
                family,
                inner,
                nullable,
                family == "mysql"
                and mysql_float_arithmetic_cell(request.plan, expression, (operand,)),
            )
            if checked is None:
                return None, ("PIE-B1003", "unary_sign_requires_int_operand")
            return SQLOperation(expression, "sign", (operand,), checked), None
        if tag != "Int" or inner.tag != "Int":
            return None, ("PIE-B1003", "unary_sign_requires_int_operand")
        bounds = proven_int_bounds(inner)
        if bounds is None:
            return None, ("PIE-B1004", "int_range_proof_missing")
        low, high = (
            (-bounds[1], -bounds[0])
            if (expression.expression.operator == "-")
            else bounds
        )
        checked = _unary_int(
            family,
            inner,
            low,
            high,
            nullable,
            family == "mysql"
            and mysql_checked_cell(request.plan, expression, (operand,)),
        )
        if checked is None:
            return None, ("PIE-B1002", "unary_result_outside_physical_range")
        return SQLOperation(expression, "sign", (operand,), checked), None
    if type(expression) is row.ProjectSQLIsNull:
        operand, problem = build_row_value(
            request, columns, expression.value, uses, reference_type=reference_type
        )
        if problem is not None:
            return None, problem
        if tag != "Bool" or nullable is not False:
            return None, ("PIE-B1002", "null_test_result_not_non_null_bool")
        return (
            SQLOperation(expression, "null_test", (operand,), _bool(family, nullable)),
            None,
        )
    if type(expression) is row.ProjectSQLBinary:
        return _binary(
            request,
            columns,
            expression,
            tag,
            nullable,
            uses,
            reference_type,
            expression.ref in mysql_cells,
        )
    if type(expression) is row.ProjectSQLComparison:
        return _comparison(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLBetween:
        return _between(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) in {
        row.ProjectSQLScalarCall,
        aggregation.ProjectSQLAggregateArgumentCall,
    }:
        return _scalar_call(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLConditional:
        return _conditional(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLMembership:
        return _membership(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLCast:
        return _cast(request, columns, expression, tag, nullable, uses, reference_type)
    if type(expression) is row.ProjectSQLCapturedField:
        # An inline let's scope carries each capture record's outer row; a
        # captured field may be typed wider (nullable) than the outer column.
        scope = columns.get(expression.capture)
        if (
            type(scope) is not SQLCaptureScope
            or scope.capture.ref is not expression.capture
            or expression.position not in scope.capture.edge.fields
        ):
            return None, ("PIE-B1001", "captured_field_outside_scope")
        column = scope.reads[scope.capture.edge.fields.index(expression.position)]
        realization = column.realization
        if realization.tag != tag:
            return None, ("PIE-B1002", "captured_field_logical_type_drift")
        if realization.nullable != nullable:
            if nullable is not True or realization.nullable is not False:
                return None, ("PIE-B1002", "captured_field_null_drift")
            realization = replace(realization, nullable=True)
        return (
            SQLCapturedReference(
                expression, scope.capture, column, realization, scope.alias
            ),
            None,
        )
    if type(expression) is row.ProjectSQLAnyReference:
        if expression.use is None:
            column = columns.get(expression.port)
        else:
            target = columns.get(expression.use)
            if (
                type(target) is not SQLBlockTarget
                or columns.get((expression.use, "any")) is not target.symbol
                or expression.position is None
            ):
                return None, ("PIE-B1001", "any_reference_outside_lexical_scope")
            column = any_column(request, target, expression.position)
        if type(column) is not StageColumn:
            return None, ("PIE-B1001", "any_reference_outside_input_scope")
        if column.realization.tag != tag or column.realization.nullable != nullable:
            return None, ("PIE-B1002", "any_reference_logical_type_or_null_drift")
        return SQLStageReference(
            expression,
            expression.port or column.terminal,
            column,
            column.realization,
            column.scope,
        ), None
    if type(expression) in (row.ProjectSQLRelationExists, row.ProjectSQLAny):
        # The stage scope carries each readable block target under its own
        # expression block use; existence is never NULL.
        target = columns.get(expression.use)
        if type(target) is not SQLBlockTarget or target.use.ref is not expression.use:
            return None, ("PIE-B1001", "expression_block_use_outside_scope")
        if tag != "Bool" or nullable is not False:
            return None, ("PIE-B1002", "existence_result_not_non_null_bool")
        predicate = None
        if type(expression) is row.ProjectSQLAny:
            scoped = {**columns, (expression.use, "any"): target.symbol}
            predicate, problem = build_row_value(
                request,
                scoped,
                expression.predicate,
                uses,
                reference_type=reference_type,
            )
            if problem is not None:
                return None, problem
            if realization_of(predicate, family).tag != "Bool":
                return None, ("PIE-B1003", "any_predicate_requires_bool")
        return SQLBlockRead(
            expression, target, _bool(family, False), predicate=predicate
        ), None
    if type(expression) is row.ProjectSQLRelationScalar:
        # One named output of the read producer; no row reads NULL, and more
        # than one row is the database's own runtime error.
        target = columns.get(expression.use)
        if type(target) is not SQLBlockTarget or target.use.ref is not expression.use:
            return None, ("PIE-B1001", "expression_block_use_outside_scope")
        column = target.use.edge.column
        read = None if column is None else block_column(target, column)
        if read is None:
            return None, ("PIE-B1001", "scalar_read_column_not_realized")
        realization = scalar_read_realization(read[1])
        if realization.tag != tag or nullable is not True:
            return None, ("PIE-B1002", "scalar_read_type_mismatch")
        return SQLBlockRead(expression, target, realization, "scalar", column), None
    if type(expression) is row.ProjectSQLRelationMembership:
        return _relation_membership(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLListOperation:
        return _list_operation(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLElementReference:
        return _element_reference(columns, expression, tag, nullable)
    return None, ("PIE-B1003", "row_expression_not_admitted_in_slice6")


def _bool(family: str, nullable: bool | str) -> Realization:
    return Realization(
        "Bool", {"kind": BOOL_RESULT[family]}, nullable, {"kind": "bool01"}
    )


def _checked_int(storage, low, high, nullable) -> Realization | None:
    if storage is None:
        return None
    limits = signed_range(storage)
    if limits is None or low < limits[0] or high > limits[1]:
        return None
    return Realization(
        "Int",
        storage,
        nullable,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
    )


NARROW_PG_INTS = ("pg_int2", "pg_int4")
INT8_WIDEN = ("CAST(", " AS pg_catalog.int8)")
SIGNED64 = (-(1 << 63), (1 << 63) - 1)
# Evidence that a bigint result's range is not proved statically: the target's
# checked signed 64-bit operation or narrowing refuses an out-of-range value
# with SQLSTATE 22003 and never returns a wrapped one.
TARGET_CHECKED_SIGNED64 = "target_checked_signed64_narrowing"
# The carrier of such a result on each target.
CHECKED_INT_STORAGE = {
    "postgres": {"kind": "pg_int8"},
    "mysql": {"kind": "my_signed_int"},
}
TARGET_CHECKED_DECIMAL = "target_checked_decimal_overflow"
# Evidence that a binary64 result is finite because the target refuses an
# overflowing operation or accumulation (SQLSTATE 22003) instead of returning
# an infinity or a wrong value.
TARGET_CHECKED_BINARY64 = "target_checked_binary64_overflow"


def _target_checked_int(
    family, storage, low, high, nullable, mysql_operands=()
) -> Realization | None:
    """PostgreSQL computes a bigint operation with its checked operators, so a
    range that meets signed 64 bits is admitted, clipped to it. A range wholly
    outside it stays refused: such an operation could only fail. An admitted
    one may still fail while planning, wherever PostgreSQL folds operands it
    reduces to constants (a constant condition or COALESCE argument, a bound
    value), even in a branch no row takes. MySQL's BIGINT operators raise
    1690 (SQLSTATE 22003) the same way, admitted only in an S01 cell, whose
    ``mysql_operands`` the caller passes (mysql_checked_operands)."""
    if family == "mysql":
        # Its storage is always my_signed_int (_arithmetic_storage).
        if not mysql_checked_operands(mysql_operands):
            return None
    elif family != "postgres" or storage != {"kind": "pg_int8"}:
        return None
    if high < SIGNED64[0] or low > SIGNED64[1]:
        return None
    return _checked_int(
        storage, max(low, SIGNED64[0]), min(high, SIGNED64[1]), nullable
    )


def target_checked(family: str, operation) -> bool:
    """Whether one realized Int sign, arithmetic or `abs` relies on the
    target's checked signed 64-bit operation: its exact range, recomputed from
    its operands, leaves signed 64 bits."""
    result = operation.realization
    if (
        result.tag != "Int"
        or result.binding
        or result.storage != CHECKED_INT_STORAGE.get(family)
    ):
        return False
    bounds: list[tuple[int, int]] = []
    for operand in operation.operands:
        interval = proven_int_bounds(realization_of(operand, family))
        if interval is None:
            return False
        bounds.append(interval)
    if operation.kind == "arithmetic" and len(bounds) == 2:
        if operation.original.expression.operator in {"/", "%"}:
            return False
        low, high = _interval(
            operation.original.expression.operator, bounds[0], bounds[1]
        )
    elif operation.kind == "sign" and len(bounds) == 1:
        low, high = bounds[0]
        if operation.original.expression.operator == "-":
            low, high = -high, -low
    elif (
        operation.kind == "scalar_call"
        and operation.original.callee_symbol.name == "abs"
        and len(bounds) == 1
    ):
        low, high = bounds[0]
        low, high = max(low, -high, 0), max(-low, high)
    else:
        return False
    return low < SIGNED64[0] or high > SIGNED64[1]


def checked_evidence(family: str, operation) -> tuple[str, ...]:
    """The overflow evidence of one realized operation: a checked bigint
    range, or a Float `+`, `-` or `*` that no literal fold proves finite,
    bounded by the target's checked float8 or DOUBLE operator (E4; on MySQL
    only in an MC E4 cell)."""
    if target_checked(family, operation):
        return (TARGET_CHECKED_SIGNED64,)
    if (
        operation.kind == "arithmetic"
        and operation.original.expression.operator != "%"
        and operation.realization.tag == "Float"
        and any(_float_literal_value(o) is None for o in operation.operands)
    ):
        return (TARGET_CHECKED_BINARY64,)
    return ()


def _widened_int(family, storage, low, high, nullable) -> Realization | None:
    """PostgreSQL computes an int2/int4 operation whose exact range leaves that
    type in bigint (its first operand CAST to pg_catalog.int8). A narrow
    operation's exact range always fits bigint, so this proof is static."""
    if family != "postgres" or storage is None:
        return None
    if storage["kind"] not in NARROW_PG_INTS:
        return None
    return _checked_int({"kind": "pg_int8"}, low, high, nullable)


def int8_widened(family: str, operation) -> bool:
    """Whether one realized Int operation is computed in bigint over narrow
    PostgreSQL operands: its rendering CASTs the first operand to int8."""
    result = operation.realization
    return (
        family == "postgres"
        and (
            operation.kind in ("sign", "arithmetic")
            or operation.kind == "scalar_call"
            and operation.original.callee_symbol.name == "abs"
        )
        and result.tag == "Int"
        and result.storage == {"kind": "pg_int8"}
        and bool(operation.operands)
        and all(
            realization_of(operand, family).storage.get("kind") in NARROW_PG_INTS
            for operand in operation.operands
        )
    )


def float_sign(family, inner, nullable, mysql_float=False) -> Realization | None:
    """E4: a PostgreSQL unary `-` or `+` of a finite float8 value flips or
    keeps its sign bit exactly (float8um/float8up), so it never fails; so
    does MySQL's unary `-` of a DOUBLE in an MC E4 cell (``mysql_float``,
    whose caller derives it, mysql_float_arithmetic_cell)."""
    if not (
        family == "postgres"
        and float_carrier(inner, family)
        or family == "mysql"
        and mysql_float
        and mysql_float_operands((inner,))
    ):
        return None
    return Realization(
        "Float",
        {"kind": "pg_float8" if family == "postgres" else "my_double"},
        nullable,
        FINITE_FLOAT,
    )


def _unary_int(
    family, inner, low, high, nullable, mysql_checked=False
) -> Realization | None:
    """A one-operand Int result of range ``low``..``high`` in the operand's
    own signed integer type (unary `+`/`-` and `abs`), or bigint over a
    narrow PostgreSQL operand, proved per binding for a query parameter
    operand that no static type holds. ``mysql_checked`` marks an S01 cell."""
    storage = _arithmetic_storage(family, inner, inner)
    checked = _checked_int(storage, low, high, nullable)
    if checked is None:
        checked = _widened_int(family, storage, low, high, nullable)
    if checked is None and inner.binding:
        return deferred_int(storage, nullable)
    if checked is None:
        return _target_checked_int(
            family,
            storage,
            low,
            high,
            nullable,
            (inner,) if mysql_checked else (),
        )
    return replace(checked, binding=inner.binding)


def _decimal_parameters(family: str, value: Realization) -> tuple[int, int] | None:
    """Read one qualified Decimal carrier; no target default selects a result."""

    expected = "pg_numeric" if family == "postgres" else "my_decimal"
    storage, domain = value.storage, value.domain
    if value.tag != "Decimal" or storage.get("kind") != expected:
        return None
    precision, scale = storage.get("precision"), storage.get("scale")
    if (
        type(precision) is not int
        or type(scale) is not int
        or not 0 <= scale <= precision <= 65
        or domain != {"kind": "decimal", "precision": precision, "scale": scale}
    ):
        return None
    return precision, scale


def decimal_operand_parameters(
    family: str, value: Realization, origin: str | None
) -> tuple[int, int] | None:
    """One independently classified E9 carrier; a default never promotes it."""

    if origin in {"decimal", "decimal_parameter"}:
        return _decimal_parameters(family, value)
    if origin not in {"int", "int_literal", "int_parameter"} or value.tag != "Int":
        return None
    bounds = proven_int_bounds(value)
    if bounds is None or value.storage.get("kind") not in INT_WIDTHS:
        return None
    physical = signed_range(value.storage)
    if physical is None or not physical[0] <= bounds[0] <= bounds[1] <= physical[1]:
        return None
    if origin == "int_literal":
        low, high = bounds
        if low != high:
            return None
        return max(1, len(str(abs(low)))), 0
    return {16: (5, 0), 32: (10, 0), 64: (19, 0)}[INT_WIDTHS[value.storage["kind"]]]


def decimal_sum_realization(
    family: str, value: Realization, nullable: bool | str
) -> Realization | None:
    """A PostgreSQL Decimal sum is exact in this carrier or the target rejects it."""

    parameters_ = _decimal_parameters(family, value)
    if family != "postgres" or parameters_ is None:
        return None
    precision, scale = parameters_
    result_precision = precision + 19
    if result_precision > 65 or scale > 30:
        return None
    return Realization(
        "Decimal",
        {"kind": "pg_numeric", "precision": result_precision, "scale": scale},
        nullable,
        {"kind": "decimal", "precision": result_precision, "scale": scale},
    )


def _float_literal_value(value) -> float | None:
    """Return one exact finite Float literal/sign value, never a field value."""

    try:
        nodes = parameters.value_nodes(value)
        leaf = nodes[-1]
        if (
            type(leaf) not in {parameters.SQLLiteral, parameters.SQLParameter}
            or parameters.tag_of(leaf.original) != "Float"
        ):
            return None
        result = parameters.result_value(value)
    except (AttributeError, IndexError, TypeError, ValueError):
        return None
    return result if type(result) is float and math.isfinite(result) else None


def decimal_operand_origin(value, family: str) -> str | None:
    """The E9 operand class retained by the row tree, never an inferred value."""

    realization = realization_of(value, family)
    if realization.tag == "Decimal":
        if type(value) is SQLParameterRead:
            return "decimal_parameter"
        if (
            type(value) is SQLStageReference
            and value.column.field is not None
            and value.column.source_port is not None
            or family == "postgres"
            and type(value) in {SQLStageReference, SQLOperation}
            and _decimal_parameters(family, realization) is not None
        ):
            return "decimal"
        return None
    if realization.tag != "Int":
        return None
    static = _static_literal_value(value)
    if static is not None and static[0] == "Int" and type(static[1]) is int:
        return "int_literal"
    if type(value) is SQLParameterRead:
        return "int_parameter"
    if (
        type(value) is SQLStageReference
        and value.column.field is not None
        and value.column.source_port is not None
        or family == "postgres"
        and type(value) in {SQLStageReference, SQLOperation}
        and proven_int_bounds(realization) is not None
    ):
        return "int"
    return None


def _operands(
    request, columns, refs, uses, reference_type
) -> tuple[tuple[Any, ...], None] | tuple[None, tuple[str, str]]:
    values = []
    for reference in refs:
        value, problem = build_row_value(
            request, columns, reference, uses, reference_type=reference_type
        )
        if value is None:
            assert problem is not None
            return None, problem
        values.append(value)
    return tuple(values), None


def _binary(
    request, columns, expression, tag, nullable, uses, reference_type, cell
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    operator = expression.expression.operator
    if operator not in (*ARITHMETIC, *LOGICAL):
        return None, ("PIE-B1003", "binary_operator_not_admitted")
    values, problem = _operands(
        request, columns, (expression.left, expression.right), uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    left, right = (realization_of(value, request.family) for value in values)
    float_left, float_right = (_float_literal_value(value) for value in values)
    checked, problem = resolved_binary_realization(
        request.family,
        operator,
        tag,
        nullable,
        left,
        right,
        direct_decimal_sources=all(
            type(value) is SQLStageReference
            and value.column.field is not None
            and value.column.source_port is not None
            for value in values
        ),
        decimal_operand_origins=tuple(
            decimal_operand_origin(value, request.family) for value in values
        ),
        float_values=(
            None
            if float_left is None or float_right is None
            else (float_left, float_right)
        ),
        mysql_checked=request.family == "mysql"
        and mysql_checked_cell(request.plan, expression, values),
        mysql_remainder=cell,
        mysql_division=cell,
        mysql_float=request.family == "mysql"
        and mysql_float_arithmetic_cell(request.plan, expression, values),
        # This reader's own S17 pairing check.
        paired=tag == "Decimal" and pairing.project_form(request) is not None,
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(
        expression, "logical" if operator in LOGICAL else "arithmetic", values, checked
    ), None


def resolved_binary_realization(
    family,
    operator,
    tag,
    nullable,
    left,
    right,
    *,
    direct_decimal_sources: bool = False,
    decimal_operand_origins: tuple[str | None, ...] | None = None,
    float_values: tuple[float, float] | None = None,
    mysql_checked: bool = False,
    mysql_remainder: bool = False,
    mysql_division: bool = False,
    mysql_float: bool = False,
    paired: bool = False,
):
    """Original range/domain law over resolved operands; no name resolution.
    ``mysql_checked`` marks an S01 cell (mysql_checked_cell),
    ``mysql_remainder`` an S15 one (mysql_remainder_cells),
    ``mysql_division`` an R08 one (mysql_division_cells) and ``mysql_float``
    an MC E4 one (mysql_float_arithmetic_cell). MySQL takes
    Decimal and Int, Decimal of another scale and Decimal times Int as
    PostgreSQL does only in a statement its reader pairs with an S17 form
    (``paired``, `project_sql_emission_paired`)."""
    # S15: a MySQL `%` cell over two fields of its tag's carrier; MySQL
    # returns NULL for a zero divisor, so the result is never non-null.
    remainder = (
        mysql_remainder
        and family == "mysql"
        and operator == "%"
        and nullable is not False
        and mysql_remainder_operands(tag, (left, right))
    )
    # R08: a MySQL Int `/` cell whose literal operand proves it (D77.27);
    # MySQL returns NULL for a zero divisor, as for S15.
    division = (
        mysql_division
        and family == "mysql"
        and operator == "/"
        and tag == "Int"
        and nullable is not False
        and mysql_division_law(left, right)
    )
    if operator in LOGICAL:
        if tag != "Bool" or left.tag != "Bool" or right.tag != "Bool":
            return None, ("PIE-B1003", "logical_operands_require_bool")
        if left.domain.get("kind") != "bool01" or right.domain.get("kind") != "bool01":
            return None, ("PIE-B1002", "logical_operand_outside_bool_domain")
        return _bool(family, nullable), None
    if operator not in ARITHMETIC:
        return None, ("PIE-B1003", "binary_operator_not_admitted")
    if tag == "Decimal" and {left.tag, right.tag} <= {"Decimal", "Int"}:
        if decimal_operand_origins is None:
            decimal_operand_origins = (
                ("decimal", "decimal") if direct_decimal_sources else (None, None)
            )
        if len(decimal_operand_origins) != 2 or any(
            origin is None for origin in decimal_operand_origins
        ):
            return None, ("PIE-B1003", "decimal_direct_source_operands_required")
        left_parameters = decimal_operand_parameters(
            family, left, decimal_operand_origins[0]
        )
        right_parameters = decimal_operand_parameters(
            family, right, decimal_operand_origins[1]
        )
        if left_parameters is None or right_parameters is None:
            return None, ("PIE-B1004", "decimal_source_carrier_missing")
        left_precision, left_scale = left_parameters
        right_precision, right_scale = right_parameters
        if operator in {"+", "-"}:
            if (
                left.tag == right.tag == "Decimal"
                and "decimal_parameter" in decimal_operand_origins
                and left_scale == right_scale
            ):
                return None, ("PIE-B1003", "decimal_direct_source_operands_required")
            mysql = family != "postgres" and not paired
            if mysql and "Int" in {left.tag, right.tag}:
                return None, ("PIE-B1003", "arithmetic_requires_signed_int_operands")
            if mysql and left_scale != right_scale:
                return None, ("PIE-B1003", "decimal_scale_mismatch")
            scale = max(left_scale, right_scale)
            precision = (
                max(left_precision - left_scale, right_precision - right_scale)
                + 1
                + scale
            )
        elif operator == "*" and {left.tag, right.tag} == {"Decimal", "Int"}:
            if family != "postgres" and not paired:
                return None, ("PIE-B1003", "binary_operator_not_admitted")
            # |d| < 10**(p-s), |int64| < 10**19: the product needs at most
            # p+19 digits and retains s fractional digits, without rounding.
            precision, scale = (
                left_parameters if left.tag == "Decimal" else right_parameters
            )
            precision += 19
        elif operator == "*" and "decimal_parameter" in decimal_operand_origins:
            return None, ("PIE-B1003", "decimal_direct_source_operands_required")
        elif (
            operator == "*"
            and left.tag == right.tag == "Decimal"
            and "decimal_parameter" not in decimal_operand_origins
        ):
            scale = left_scale + right_scale
            precision = left_precision + right_precision
        else:
            return None, ("PIE-B1003", "binary_operator_not_admitted")
        if precision > 65 or scale > 30:
            return None, ("PIE-B1002", "decimal_result_outside_physical_range")
        storage = {
            "kind": "pg_numeric" if family == "postgres" else "my_decimal",
            "precision": precision,
            "scale": scale,
        }
        return (
            Realization(
                "Decimal",
                storage,
                nullable,
                {"kind": "decimal", "precision": precision, "scale": scale},
            ),
            None,
        )
    if tag == left.tag == right.tag == "Float":
        if remainder:
            return Realization(
                "Float", {"kind": "my_double"}, nullable, FINITE_FLOAT
            ), None
        if operator == "%":
            if not (
                family == "postgres"
                and float_carrier(left, family)
                and float_carrier(right, family)
            ):
                return None, (
                    "PIE-B1003",
                    "float_remainder_exact_binary64_not_realized",
                )
            return (
                Realization(
                    "Float",
                    {"kind": "pg_float8"},
                    nullable,
                    FINITE_FLOAT,
                ),
                None,
            )
        if operator == "/":
            if not (
                family == "postgres"
                and float_carrier(left, family)
                and float_carrier(right, family)
            ):
                return None, ("PIE-B1003", "float_division_not_realized")
            return (
                Realization(
                    "Float",
                    {"kind": "pg_float8"},
                    nullable,
                    FINITE_FLOAT,
                ),
                None,
            )
        if float_values is not None:
            left_value, right_value = float_values
            result = {
                "+": left_value + right_value,
                "-": left_value - right_value,
                "*": left_value * right_value,
            }[operator]
            # PostgreSQL's float8 `*` also fails a product of two non-zero
            # values that rounds to zero (22003 underflow); MySQL returns 0.0.
            if not math.isfinite(result) or (
                operator == "*" and result == 0.0 and 0.0 not in float_values
            ):
                return None, ("PIE-B1002", "float_result_not_finite")
        elif not (
            family == "postgres"
            and float_carrier(left, family)
            and float_carrier(right, family)
            or family == "mysql"
            and mysql_float
            and mysql_float_operands((left, right))
        ):
            return None, ("PIE-B1003", "float_literal_operands_required")
        # Without a literal fold PostgreSQL's checked float8 operator, or in
        # an E4 cell MySQL's DOUBLE one (`*` guarded), bounds the result
        # (SQLSTATE 22003, TARGET_CHECKED_BINARY64).
        return (
            Realization(
                "Float",
                {"kind": "pg_float8" if family == "postgres" else "my_double"},
                nullable,
                {"kind": "finite_float", "format": "binary64"},
            ),
            None,
        )
    if tag != "Int" or left.tag != "Int" or right.tag != "Int":
        return None, ("PIE-B1003", "arithmetic_requires_signed_int_operands")
    if operator in {"/", "%"}:
        if remainder or division:
            # |l % r| < |r|; MySQL's `MIN % -1` is 0. R08's |l DIV r| is at
            # most |l| < 2**63, or |l| / 2.
            return (
                Realization(
                    "Int",
                    {"kind": "my_bigint"},
                    nullable,
                    {
                        "kind": "int_range",
                        "min": str(SIGNED64[0]),
                        "max": str(SIGNED64[1]),
                    },
                    SIGNED64,
                ),
                None,
            )
        if family != "postgres":
            return None, ("PIE-B1003", "binary_operator_not_admitted")
        # PostgreSQL's int8 operators preserve the value or raise; no MySQL
        # NULL-on-zero path is admitted by this PostgreSQL-first slice.
        return (
            Realization(
                "Int",
                {"kind": "pg_int8"},
                nullable,
                {"kind": "int_range", "min": str(SIGNED64[0]), "max": str(SIGNED64[1])},
                SIGNED64,
            ),
            None,
        )
    if _typed_null(left) is not _typed_null(right):
        return _null_int_arithmetic(
            family, right if _typed_null(left) else left, nullable
        )
    left_bounds, right_bounds = proven_int_bounds(left), proven_int_bounds(right)
    if left_bounds is None or right_bounds is None:
        return None, ("PIE-B1004", "int_range_proof_missing")
    low, high = _interval(operator, left_bounds, right_bounds)
    storage = _arithmetic_storage(family, left, right)
    binding = left.binding or right.binding
    checked = _checked_int(storage, low, high, nullable)
    if checked is None:
        checked = _widened_int(family, storage, low, high, nullable)
    if checked is None and binding:
        checked = deferred_int(storage, nullable)
    elif checked is not None:
        checked = replace(checked, binding=binding)
    else:
        checked = _target_checked_int(
            family,
            storage,
            low,
            high,
            nullable,
            (left, right) if mysql_checked else (),
        )
    if checked is None:
        return None, ("PIE-B1002", "arithmetic_outside_physical_range")
    return checked, None


def _null_int_arithmetic(family, other: Realization, nullable):
    """Int arithmetic with one typed NULL operand is NULL on every row. Its
    rendering CASTs the NULL to the target's Int carrier (`null_cast`), which
    types the result beside any integer operand, and no row has a value for
    a range to bound: the result claims the single value 0, which holds for
    no row, so no operation over it is held to the other operand's range."""
    if _arithmetic_storage(family, other, other) is None:
        return None, ("PIE-B1002", "arithmetic_outside_physical_range")
    return _checked_int(
        {"kind": parameters.PHYSICAL[family]["Int"]}, 0, 0, nullable
    ), None


def null_cast(operation, position: int) -> bool:
    """Whether operand ``position`` of one realized operation is the typed
    NULL of Int arithmetic (D-12), which its rendering CASTs to the target's
    Int carrier: a bare NULL takes the type the target chooses, and MySQL
    types `n + NULL` as DOUBLE."""
    return (
        operation.kind == "arithmetic"
        and operation.realization.tag == "Int"
        and type(operation.operands[position]) is parameters.SQLNull
    )


def null_cast_close(family: str) -> str:
    return parameters.anchor_suffix(parameters.PHYSICAL[family]["Int"])


def _comparison(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    operator = expression.expression.operator
    if operator not in COMPARISONS:
        return None, ("PIE-B1003", "comparison_operator_not_admitted")
    values, problem = _operands(
        request, columns, (expression.left, expression.right), uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    left, right = (realization_of(value, request.family) for value in values)
    if operator in {"like", "not like"}:
        checked, problem = resolved_like_realization(
            request.family, tag, nullable, left, right
        )
    else:
        rows_both_sides = all(_reads_row(value) for value in values)
        checked, problem = resolved_comparison_realization(
            request.family,
            tag,
            nullable,
            left,
            right,
            operator,
            rows_both_sides=rows_both_sides,
            float_cell=mysql_float_cell(request, expression)
            if request.family == "mysql"
            and rows_both_sides
            and left.tag == "Float"
            and operator in ("==", "!=")
            else None,
        )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "comparison", values, checked), None


def _between(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    values, problem = _operands(
        request,
        columns,
        (expression.value, expression.lower, expression.upper),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_between_realization(
        request.family, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "between", values, checked), None


def _reads_row(value) -> bool:
    """A field, captured outer field or block read; a literal or a header
    parameter reads no row."""
    return any(
        type(node) in {SQLStageReference, SQLCapturedReference, SQLBlockRead}
        for node in value_nodes(value)
    )


# The MySQL project Float comparisons of two row reads that the Phase77 S06
# native qualification (s06-float-b10) judged READY, as (shape, place, form).
# Same row: `==`, `!=`, `not (!=)`, `same_value` or `not same_value(...)` of
# two nullable Float fields of one source, as the whole value of a SELECT item
# ("select") or the whole WHERE ("where"). JOIN: an INNER `==` or `not (!=)`,
# or a LEFT `==`, of a nullable Float field of each of two sources as the
# whole ON ("none") or before `and` one `==` of two Text keys ("text"); an ON
# `same_value` has no PostgreSQL form. ANTI (Phase77 R02, the anti_not_exists
# shape s06-float-b10 and its candidate emission experiment matched): the
# whole WHERE is `not any(P for z in I)`, P a `==` of a nullable Float field
# of I and one of the outer source O, alone ("none") or before `and` one `==`
# of a Text key of each ("text"). Emission and the live verifier call
# mysql_float_cell on their plan; compiled replay (records) and the pure
# boundary (document) each derive the cell from their own input. Every other
# MySQL Float comparison of two row reads keeps its refusal. A relation alias
# `let` (read or not; ANTI admits only one that is its binder), an unused
# named window and an inlined `def` change the records and the document only
# in source positions and source bytes, so only emission and the live
# verifier see and refuse them.
_SAME_ROW_FORMS = ("==", "!=", "not !=", "same_value", "not same_value")
MYSQL_FLOAT_ROW_CELLS = frozenset(
    {
        *(
            ("same_row", place, form)
            for place in ("select", "where")
            for form in _SAME_ROW_FORMS
        ),
        *(
            (kind, key, form)
            for kind, form in (
                ("inner", "=="),
                ("inner", "not !="),
                ("left", "=="),
                ("anti", "=="),
            )
            for key in ("none", "text")
        ),
    }
)
# The qualified Text key widths: the NOT NULL VARCHAR(64) `kn` and
# VARCHAR(1000) `kw` of `f6o` and `f6i`.
MYSQL_FLOAT_CELL_KEY_WIDTHS = (64, 1000)
# The fields of each source of a cell, selected or not, as carriers
# (mysql_float_cell_carrier) in declaration order, which the CTE of a WHERE or
# JOIN cell writes: exactly those of the qualification's tables, `f6s`
# (id, f1, f2) for a same-row cell and `f6o` and `f6i` (id, v, kn, kw) for a
# JOIN cell. A source of any other fields or order is never a cell. ANTI
# checks O only, its fields in any order (the R02 whitelist); I's other fields
# never reach the SQL.
MYSQL_FLOAT_CELL_TABLES = {
    "same_row": ("int", "float", "float"),
    "inner": ("int", "float", 64, 1000),
    "left": ("int", "float", 64, 1000),
    "anti": ("int", "float", 64, 1000),
}
# The plan parts a cell's plan may hold; every other part is empty.
_MYSQL_FLOAT_PLAN_PARTS = frozenset(
    {
        "literal_sites",
        "sources",
        "blocks",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "exports",
        "projections",
        "boundaries",
        "symbols",
        "origins",
        "demands",
        "expression_sites",
        "expressions",
        "operands",
        "stage_ports",
        "filters",
        "result_ports",
        "result_exports",
        "joins",
        "join_inputs",
        "join_ports",
        "join_tails",
        "expression_block_uses",
    }
)


def mysql_float_cell_carrier(representation) -> str | int | None:
    """The carrier of a field whose contract representation the
    qualification's tables held: "float" for the nullable binary64 DOUBLE,
    "int" for a non-null BIGINT Int, the width for a NOT NULL
    binary-collation VARCHAR(64) or (1000); else None."""
    try:
        value = json.loads(representation)
    except (TypeError, ValueError):
        return None
    if type(value) is not dict:
        return None
    if value == {
        "domain": FINITE_FLOAT,
        "nullable": True,
        "storage": {"kind": "my_double"},
    }:
        return "float"
    domain = value.get("domain")
    if (
        value.get("storage") == {"kind": "my_bigint"}
        and value.get("nullable") is False
        and type(domain) is dict
        and domain.get("kind") == "int_range"
    ):
        return "int"
    for width in MYSQL_FLOAT_CELL_KEY_WIDTHS:
        if value == {
            "domain": {
                "collation": "utf8mb4_0900_bin",
                "encoding": "utf8mb4",
                "kind": "text",
                "max_characters": width,
                "padding": "NO PAD",
            },
            "nullable": False,
            "storage": {"kind": "my_varchar", "length": width},
        }:
            return width
    return None


def mysql_float_cell_items(cell) -> tuple[str, ...]:
    """The carriers the other SELECT items of ``cell`` may read directly, as
    in the qualified statements: a non-null BIGINT id beside a SELECT item
    cell, also the nullable DOUBLE values beside a WHERE or a JOIN."""
    return ("int",) if cell[1] == "select" else ("int", "float")


def _unit_query(plan, joined: bool):
    """The frame every Phase77 statement cell shares, as (at, kind): ``at``
    gives the plan expression a ref names (or None), ``kind`` the JOIN kind
    ("inner", "left" or "right"; None without a JOIN). The plan holds its
    sources and one query only (_MYSQL_FLOAT_PLAN_PARTS), with at most nine
    expressions beside its SELECT items, so each plan is scanned for a
    bounded number of calls; ``joined``: one projection over one JOIN of two
    different sources, read directly, with no retained equality and no
    expression block; else one source under a projection, or under a WHERE
    and a projection, and a second source only for the WHERE's expression
    block. None otherwise."""
    import dataclasses

    from pietto._project.project_sql_plan_joins import ProjectSQLJoinTail
    from pietto.ast_nodes import AuthoredJoinKind

    expressions, blocks, joins = plan.expressions, plan.blocks, plan.joins
    uses = plan.expression_block_uses
    if (
        len(expressions) > len(plan.projections) + 9
        or len(joins) != joined
        or joins
        and uses
        or len(plan.filters) > (0 if joins else 1)
        or not 0 < len(blocks) <= (1 if joins else 2)
        or len(plan.sources) != (2 if joins or uses else 1)
        or any(
            getattr(plan, item.name)
            for item in dataclasses.fields(plan)
            if item.name not in _MYSQL_FLOAT_PLAN_PARTS
            and type(getattr(plan, item.name)) is tuple
        )
    ):
        return None

    def at(ref):
        position = getattr(ref, "position", None)
        found = (
            expressions[position]
            if type(position) is int and 0 <= position < len(expressions)
            else None
        )
        return found if found is not None and found.ref is ref else None

    if not joins:
        return at, None
    join, inputs = joins[0], plan.join_inputs
    kind = {
        AuthoredJoinKind.INNER: "inner",
        AuthoredJoinKind.LEFT: "left",
        AuthoredJoinKind.RIGHT: "right",
    }.get(join.kind)
    sources = tuple(source.ref for source in plan.sources)
    if (
        kind is None
        or join.equalities
        or len(inputs) != 2
        or inputs[0].producer is inputs[1].producer
        or any(
            item.predecessor is not None
            or not any(item.producer is source for source in sources)
            for item in inputs
        )
        or blocks[0].kind is not row.ProjectSQLStageKind.PROJECTION
        or type(blocks[0].boundary) is not ProjectSQLJoinTail
    ):
        return None
    return at, kind


def _unit_written(plan, anti: bool = False) -> bool:
    """The selected query as written declares no `let` (a relation alias
    such as `let i = f6i`, read or not, which the plan resolves to its
    source) and no named window, and no plan expression comes from an
    inlined `def`. With ``anti`` (an R02 ANTI cell) it may declare one
    alias: the one its WHERE's `not any(...)` reads as its binder."""
    from pietto._project.module_catalog import authored_definitions
    from pietto.ast_nodes import (
        AnyExpr,
        QueryDef,
        TableDef,
        UnaryExpr,
        inlined_arguments,
    )

    owner = plan.scope.selected_owner
    written = authored_definitions(
        plan.scope.completed.semantic_result.modules[owner.module_position]
    )[owner.declaration_position]
    if type(written) not in {TableDef, QueryDef}:
        return False
    lets, tree = (
        written.naming_declarations,
        getattr(written.where_clause, "expression", None),
    )
    # The plan's `any(...)` names the source an alias resolves to; the binder
    # an ANTI `let` must be is the one its WHERE names as written.
    binder = (
        tree.operand.relation_name
        if anti
        and type(tree) is UnaryExpr
        and tree.operator == "not"
        and type(tree.operand) is AnyExpr
        else None
    )
    return not (
        written.named_windows
        or any(inlined_arguments(item.expression) for item in plan.expressions)
        or lets
        and (len(lets) != 1 or lets[0].name != binder)
    )


def _mysql_float_shape(plan, expression):
    """The structural cell of ``expression`` from the plan, with the reference
    expressions it reads: (cell, operands, keys, selected), or None.

    The frame is _unit_query's. Same row: the tree is the whole WHERE or the
    whole value of one SELECT item, and every other SELECT item is a field
    reference. JOIN: an INNER or LEFT JOIN under one projection of joined
    references; the whole ON is the tree, or `and` of the tree and a `==` of
    two references (``keys``). ANTI: one source under a WHERE and a
    projection of field references; the whole WHERE is `not` over one
    `any(...)` that reads the plan's one expression block use, whose
    predicate is the tree, or `and` of the tree and a `==` of two references
    (``keys``). The tree is ``expression`` (`==`, `!=` or `same_value` of two
    references) or `not` over it, the plan holds no other expression, and
    the query is as _unit_written requires (ANTI: with its binder alias).
    """
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    frame = _unit_query(plan, len(plan.joins) == 1)
    if frame is None:
        return None
    at, kind = frame
    expressions, blocks = plan.expressions, plan.blocks
    joins, uses = plan.joins, plan.expression_block_uses
    roots = tuple(at(item.expression) for item in plan.projections)
    keys, parts, shape = (), 0, ("same_row", "select")
    if joins:
        if kind not in ("inner", "left"):
            return None
        reference, items, root = (
            row.ProjectSQLMatchReference,
            row.ProjectSQLJoinedReference,
            at(joins[0].on),
        )
    else:
        stages = (
            (row.ProjectSQLStageKind.WHERE, row.ProjectSQLStageKind.PROJECTION)
            if plan.filters
            else (row.ProjectSQLStageKind.PROJECTION,)
        )
        if tuple(block.kind for block in blocks) != stages or any(
            type(block.boundary) is not ProjectSQLBoundary
            or block.boundary.reason is not ProjectSQLBoundaryReason.SOURCE_INPUT
            for block in blocks
        ):
            return None
        reference = items = row.ProjectSQLReference
        if plan.filters:
            root, shape = at(plan.filters[0].predicate), ("same_row", "where")
        else:
            trees = tuple(value for value in roots if type(value) is not items)
            if len(trees) != 1:
                return None
            root, shape = trees[0], ("same_row", "select")
        if uses:
            exists = (
                at(root.operand)
                if type(root) is row.ProjectSQLUnary
                and root.expression.operator == "not"
                else None
            )
            if not plan.filters or type(exists) is not row.ProjectSQLAny:
                return None
            root, reference, kind, parts = (
                at(exists.predicate),
                row.ProjectSQLAnyReference,
                "anti",
                2,
            )
    if joins or uses:
        place = "none"
        if type(root) is row.ProjectSQLBinary and root.expression.operator == "and":
            key = at(root.right)
            if (
                type(key) is not row.ProjectSQLComparison
                or key.expression.operator != "=="
            ):
                return None
            keys = (at(key.left), at(key.right))
            if any(type(side) is not reference for side in keys):
                return None
            root, place, parts = at(root.left), "text", parts + 4
        shape = (kind, place)
    node, negated = root, False
    if type(root) is row.ProjectSQLUnary and root.expression.operator == "not":
        node, negated = at(root.operand), True
    if node is not expression:
        return None
    if type(node) is row.ProjectSQLComparison and node.expression.operator in (
        "==",
        "!=",
    ):
        form, operands = node.expression.operator, (node.left, node.right)
    elif (
        type(node) is row.ProjectSQLScalarCall
        and node.callee_symbol.namespace is SymbolNamespace.CALLABLE
        and node.callee_symbol.name == "same_value"
        and len(node.arguments) == 2
    ):
        form, operands = "same_value", node.arguments
    else:
        return None
    operands = tuple(at(item) for item in operands)
    selected = tuple(value for value in roots if type(value) is items)
    if (
        any(type(item) is not reference for item in operands)
        or len(expressions) != len(selected) + 3 + negated + parts
        or not _unit_written(plan, anti=bool(uses))
    ):
        return None
    cell = (*shape, "not " + form if negated else form)
    return cell, operands, keys, selected


def _mysql_float_field(request, ref):
    """The source port and contract field a reference port reads directly:
    stage, JOIN and input ports lead to one source port, at most four steps
    away (a projection after a WHERE). None otherwise."""
    plan = request.plan
    for _ in range(5):
        for port in plan.source_ports:
            if port.ref is ref:
                fields = tuple(
                    field
                    for source in request.sources
                    for field in source.fields
                    if field.field is port.field
                )
                return (port, fields[0]) if len(fields) == 1 else None
        step = None
        for item in (*plan.stage_ports, *plan.join_ports):
            if item.ref is ref:
                step = item.source
        for item in plan.input_ports:
            if item.ref is ref:
                step = item.producer_port
        if step is None:
            return None
        ref = step
    return None


def mysql_float_cell(request, expression):
    """The cell of one MySQL Float comparison or `same_value` call of two row
    reads, from the plan (_mysql_float_shape) and the contract fields its
    references read: two different qualified Float fields, of different JOIN
    inputs over two different tables in a JOIN cell, whose Text key compares
    qualified keys of one width of different inputs, and other SELECT items
    that read a carrier mysql_float_cell_items admits; each source has the
    fields of a qualification table (MYSQL_FLOAT_CELL_TABLES). None outside
    every cell, and while emission derives as main (AS_MAIN). ANTI: each
    `==` reads a field of the binder source I and one of the outer source O,
    and only O's fields are checked, in any order. A JOIN `on` `same_value`
    call of a null-safe JOIN cell has that cell (nullsafe_join_cell), of any
    carrier: resolved_comparison_realization admits it for two Float
    operands only, through float_carrier."""
    nullsafe = nullsafe_join_cell(request)
    if nullsafe is not None and expression.ref in nullsafe[1]:
        return nullsafe[0]
    shape = None if AS_MAIN.get() else _mysql_float_shape(request.plan, expression)
    if shape is None:
        return None
    cell, operands, keys, selected = shape
    plan = request.plan
    binder = plan.expression_block_uses[0] if cell[0] == "anti" else None
    exports = tuple(
        item.exports
        for item in plan.bindings.definitions
        if binder is not None and item.ref is binder.producer
    )

    def read_port(item):
        # A binder field reads I's export at its position, as any_column does.
        if type(item) is not row.ProjectSQLAnyReference or item.use is None:
            return item.port
        if (
            len(exports) != 1
            or item.position is None
            or item.position >= len(exports[0])
        ):
            return None
        return exports[0][item.position].ref

    found = tuple(
        _mysql_float_field(request, read_port(item))
        for item in (*operands, *keys, *selected)
    )
    reads = tuple(item for item in found if item is not None)
    if len(reads) != len(found):
        return None
    ports = tuple(port for port, _ in reads)
    carriers = tuple(
        mysql_float_cell_carrier(field.representation) for _, field in reads
    )
    owners = tuple(port.owner for port in ports)
    sources = tuple(
        source
        for source in request.sources
        if any(source.owner is item.source.owner for item in request.plan.sources)
    )
    tables = {(source.namespace, source.name) for source in sources}
    allowed = mysql_float_cell_items(cell)
    checked = tuple(
        source
        for source in sources
        if binder is None
        or not any(
            item.ref is binder.producer and item.source.owner is source.owner
            for item in plan.sources
        )
    )
    table = MYSQL_FLOAT_CELL_TABLES[cell[0]]

    def held(source):
        found = tuple(mysql_float_cell_carrier(f.representation) for f in source.fields)
        # ANTI: O's fields in any order (the R02 whitelist).
        return found if binder is None else Counter(found)

    if (
        # Only a plan source with no contract source, or one source read
        # twice (a relation alias `let`, which _mysql_float_shape refuses).
        len(sources) != len(request.plan.sources)
        or any(
            held(source) != (table if binder is None else Counter(table))
            for source in checked
        )
        or carriers[:2] != ("float", "float")
        or ports[0] is ports[1]
        or any(carrier not in allowed for carrier in carriers[2 + len(keys) :])
        or cell[0] != "same_row"
        and (owners[0] is owners[1] or len(tables) != 2)
        or keys
        and (
            carriers[2] != carriers[3]
            or carriers[2] not in MYSQL_FLOAT_CELL_KEY_WIDTHS
            or owners[2] is owners[3]
        )
    ):
        return None
    return cell


# Phase77 S07 (D77.39): the MySQL Float GROUP BY statements of the S07
# native qualification judged CANDIDATE_EMISSION_EXPERIMENT_READY
# (reauthor/s07, the paired forms group.* over h, f, hh, ff, hnh and fnf), as
# (template, key carriers in order). Each reads one source directly, groups
# by the keys and selects them in that order, then `count()`. A carrier is
# the fixture column's whole realization (MYSQL_FLOAT_KEY_CARRIERS).
# Emission and the live verifier call mysql_float_key_cell on their plan;
# compiled replay (records) and the pure boundary (document) each derive the
# cell from their own input. Every other MySQL Float key keeps its refusal: a
# wide or other Text key, other carriers, keys or order, another select item
# or clause, a let, a named window, a header parameter, a `def` call, another
# upstream query, every DISTINCT and UNION DISTINCT (the raw campaign showed
# no on-disk deduplication for them, PRIMITIVE_OBSERVATION_ONLY), and the
# count_distinct, window and distribution forms that D77.39 keeps refused.
# A relation alias `let` (read or not), an unused named window and an
# inlined `def` change the records and the document only in source positions
# and source bytes, so only emission and the live verifier see and refuse
# them.
_MYSQL_FLOAT_KEY_SETS = (
    ("H",),
    ("F",),
    ("H", "H"),
    ("F", "F"),
    ("H", "N", "H"),
    ("F", "N", "F"),
)
MYSQL_FLOAT_KEY_CELLS = frozenset(("group", keys) for keys in _MYSQL_FLOAT_KEY_SETS)
# (tag, contract representation) of each S07 key carrier: "F" the nullable
# and "H" the non-null finite binary64 DOUBLE, "N" the NOT NULL utf8mb4_0900_bin
# VARCHAR(64). The wide VARCHAR(1000) key stays refused (D77.08).
MYSQL_FLOAT_KEY_CARRIERS = {
    "F": (
        "Float",
        {"domain": FINITE_FLOAT, "nullable": True, "storage": {"kind": "my_double"}},
    ),
    "H": (
        "Float",
        {"domain": FINITE_FLOAT, "nullable": False, "storage": {"kind": "my_double"}},
    ),
    "N": (
        "Text",
        {
            "domain": {
                "collation": "utf8mb4_0900_bin",
                "encoding": "utf8mb4",
                "kind": "text",
                "max_characters": 64,
                "padding": "NO PAD",
            },
            "nullable": False,
            "storage": {"kind": "my_varchar", "length": 64},
        },
    ),
}
# The plan parts a cell's plan may hold; every other part is empty.
_MYSQL_FLOAT_KEY_PARTS = frozenset(
    {
        "literal_sites",
        "sources",
        "blocks",
        "input_uses",
        "source_ports",
        "input_ports",
        "all_exports",
        "exports",
        "boundaries",
        "symbols",
        "origins",
        "demands",
        "stage_ports",
        "result_ports",
        "result_exports",
        "aggregations",
        "group_keys",
        "aggregates",
        "aggregate_projections",
    }
)


def mysql_float_key_carrier(tag, representation) -> str | None:
    """The S07 carrier symbol of a field of logical ``tag`` whose contract
    representation is exactly one of MYSQL_FLOAT_KEY_CARRIERS; else None."""
    try:
        value = json.loads(representation)
    except (TypeError, ValueError):
        return None
    for symbol, carrier in MYSQL_FLOAT_KEY_CARRIERS.items():
        if carrier == (tag, value):
            return symbol
    return None


def mysql_float_key_cell(request):
    """The S07 cell (MYSQL_FLOAT_KEY_CELLS) of the statement, from the plan,
    the contract fields its keys read and the declarations as written; None
    outside every cell and while emission derives as main (AS_MAIN).

    The plan holds only a cell's parts (_MYSQL_FLOAT_KEY_PARTS), one source,
    and an aggregate block over it and a projection: one GROUP BY of one to
    three keys and one `count()` with no argument, selected as the keys in
    their GROUP BY order and then the count. Each key reads a different
    contract field directly, whose carrier (mysql_float_key_carrier) gives
    the cell. As written, the one declaration of the statement is a table
    or query with no `let` and no named window, and no select item calls a
    `def` (inlined_arguments).
    """
    if AS_MAIN.get():
        return None
    import dataclasses

    from pietto._project.module_catalog import authored_definitions
    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )
    from pietto.ast_nodes import QueryDef, SourceDef, TableDef, inlined_arguments

    plan = request.plan
    if not plan.aggregations or any(
        getattr(plan, item.name)
        for item in dataclasses.fields(plan)
        if item.name not in _MYSQL_FLOAT_KEY_PARTS
        and type(getattr(plan, item.name)) is tuple
    ):
        return None
    blocks = plan.blocks
    named = tuple(
        item.entry.owner
        for item in plan.bindings.definitions
        if type(item.entry.owner.definition) is not SourceDef
    )
    if (
        len(plan.sources) != 1
        or len(plan.input_uses) != 1
        or len(named) != 1
        or tuple(block.kind for block in blocks)
        != (row.ProjectSQLStageKind.AGGREGATE, row.ProjectSQLStageKind.PROJECTION)
        or any(
            type(block.boundary) is not ProjectSQLBoundary
            or block.boundary.reason is not ProjectSQLBoundaryReason.SOURCE_INPUT
            for block in blocks
        )
    ):
        return None
    keys, aggregates = plan.group_keys, plan.aggregates
    # Each select item reads, through its projection port, one aggregate
    # result: the keys in their GROUP BY order, then the count.
    ports = {port.ref: port.source for port in plan.stage_ports}
    if (
        not 0 < len(keys) <= 3
        or len(plan.aggregations) != 1
        or len(aggregates) != 1
        or aggregates[0].arguments
        or aggregates[0].order_by
        or function_name(aggregates[0].source) != "count"
        or len(plan.aggregate_projections) != len(keys) + 1
        or any(
            ports.get(projection.input) is not result
            for projection, result in zip(
                plan.aggregate_projections,
                (*(key.result for key in keys), aggregates[0].result),
                strict=True,
            )
        )
    ):
        return None
    found = tuple(_mysql_float_field(request, key.input) for key in keys)
    fields = tuple(item[1] for item in found if item is not None)
    if len(fields) != len(keys) or len({id(field) for field in fields}) != len(fields):
        return None
    (owner,) = named
    written = authored_definitions(
        plan.scope.completed.semantic_result.modules[owner.module_position]
    )[owner.declaration_position]
    if (
        type(written) not in {TableDef, QueryDef}
        or written.naming_declarations
        or written.named_windows
        or written.let_clause is not None
        or any(
            inlined_arguments(projection.semantic.item.expression)
            for projection in plan.aggregate_projections
        )
    ):
        return None
    cell = (
        "group",
        tuple(
            mysql_float_key_carrier(
                getattr(field.field.evidence.resolved_type, "name", None),
                field.representation,
            )
            for field in fields
        ),
    )
    return cell if cell in MYSQL_FLOAT_KEY_CELLS else None


def mysql_float_key_admitted(request, realization) -> bool:
    """Whether a MySQL Float GROUP BY key of the statement emits: its carrier
    is the finite binary64 DOUBLE and the statement is an S07 cell
    (mysql_float_key_cell)."""
    return (
        request.family == "mysql"
        and float_carrier(realization, "mysql")
        and mysql_float_key_cell(request) is not None
    )


# A JOIN `on` `same_value` statement that the Phase77 S06 null-safe JOIN
# native qualification (PostgreSQL 18.6, MySQL 8.4.12) judged READY (unit C,
# D77.41, D77.52): one INNER, LEFT or RIGHT JOIN of two sources over
# different tables, read directly, that declare no key and hold exactly
# `id` (a non-null BIGINT Int), `v` and, by structure, `k` (a non-null
# BIGINT Int) or `w`; `v` and `w` are nullable on both sides with one
# carrier of NULLSAFE_JOIN_CARRIERS; the whole ON is one of the seven
# structures below over `o`, the preserved side (INNER: the left input),
# and `i`, the other, each operand the field at that position of that side;
# the SELECT items read every field of the left input, then of the right,
# in order, and the query holds nothing else (_unit_query, _unit_written).
# A MySQL Float cell (D77.77, after D77.52 O7) is its `same_value`
# calls' Float row cell too (mysql_float_cell). Emission and the live
# verifier call nullsafe_join_cell on their plan; compiled replay (records)
# and the pure boundary (document) each derive the cell from their own input.
NULLSAFE_JOIN_STRUCTURES = {
    ("same_value", ("o", 1), ("i", 1)): "S1",
    ("same_value", ("i", 1), ("o", 1)): "S1r",
    ("and", ("same_value", ("o", 1), ("i", 1)), ("==", ("o", 2), ("i", 2))): "S2",
    ("and", ("==", ("o", 2), ("i", 2)), ("same_value", ("o", 1), ("i", 1))): "S2r",
    (
        "and",
        ("same_value", ("o", 1), ("i", 1)),
        ("same_value", ("o", 2), ("i", 2)),
    ): "S3",
    ("not", ("same_value", ("o", 1), ("i", 1))): "S4",
    ("or", ("same_value", ("o", 1), ("i", 1)), ("==", ("o", 2), ("i", 2))): "S5",
}
# The third field of each source by structure: `k` an Int key, `w` a value.
NULLSAFE_JOIN_THIRD = {"S2": "k", "S2r": "k", "S3": "w", "S5": "k"}
_SAFE_INT = {
    "kind": "int_range",
    "min": "-9007199254740993",
    "max": "9007199254740993",
}
# Each carrier's contract storage and domain, as the qualification's tables.
NULLSAFE_JOIN_CARRIERS = {
    "postgres": {
        "int": ({"kind": "pg_int8"}, _SAFE_INT),
        "text": (
            {"kind": "pg_text"},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "UTF8",
                "collation": "C",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "pg_numeric", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "pg_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": ({"kind": "pg_uuid"}, {"kind": "uuid", "encoding": "standard_bytes"}),
        "float": ({"kind": "pg_float8"}, FINITE_FLOAT),
    },
    "mysql": {
        "int": ({"kind": "my_bigint"}, _SAFE_INT),
        "text": (
            {"kind": "my_varchar", "length": 64},
            {
                "kind": "text",
                "max_characters": 64,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        ),
        "decimal": (
            {"kind": "my_decimal", "precision": 12, "scale": 2},
            {"kind": "decimal", "precision": 12, "scale": 2},
        ),
        "date": ({"kind": "my_date"}, {"kind": "date"}),
        "timestamp": (
            {"kind": "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "uuid": (
            {"kind": "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
        "float": ({"kind": "my_double"}, FINITE_FLOAT),
    },
}
NULLSAFE_JOIN_CELLS = frozenset(
    (family, kind, structure, carrier)
    for family, carriers in NULLSAFE_JOIN_CARRIERS.items()
    for kind in ("inner", "left", "right")
    for structure in NULLSAFE_JOIN_STRUCTURES.values()
    for carrier in carriers
)


def nullsafe_join_fields(family, structure, carrier):
    """The contract representations of each source's fields in a cell."""
    storage, domain = NULLSAFE_JOIN_CARRIERS[family][carrier]
    key = {
        "domain": _SAFE_INT,
        "nullable": False,
        "storage": NULLSAFE_JOIN_CARRIERS[family]["int"][0],
    }
    value = {"domain": domain, "nullable": True, "storage": storage}
    third = NULLSAFE_JOIN_THIRD.get(structure, "")
    return (key, value, *({"k": (key,), "w": (value,)}.get(third, ())))


def nullsafe_join_cell(request):
    """The cell (family, kind, structure, carrier) of a JOIN `on` `same_value`
    statement, with its `same_value` calls: (cell, calls), from the plan, the
    contract fields its references read and its sources hold, and the query
    as written. None outside NULLSAFE_JOIN_CELLS, and while emission derives
    as main (AS_MAIN)."""
    plan = request.plan
    frame = None if AS_MAIN.get() else _unit_query(plan, True)
    if frame is None:
        return None
    at, kind = frame
    join, inputs = plan.joins[0], plan.join_inputs
    found = tuple(
        next((s for s in request.sources if s.owner is p.source.owner), None)
        for producer in (inputs[0].producer, inputs[1].producer)
        for p in plan.sources
        if p.ref is producer
    )
    sources = tuple(s for s in found if s is not None)
    ports = tuple(
        tuple(port for port in plan.source_ports if port.owner is producer)
        for producer in (inputs[0].producer, inputs[1].producer)
    )
    if (
        len(found) != 2
        or len(sources) != 2
        or (sources[0].namespace, sources[0].name)
        == (sources[1].namespace, sources[1].name)
        or any(
            definition.entry.active_properties.relational.keys
            for definition in plan.bindings.definitions
            if any(definition.entry.owner is s.owner for s in sources)
        )
    ):
        return None
    sides = {"o": 1, "i": 0} if kind == "right" else {"o": 0, "i": 1}
    seen, calls = set(), []

    def signature(node):
        if node is None or node.ref in seen:
            return None
        seen.add(node.ref)
        if type(node) is row.ProjectSQLBinary and node.expression.operator in (
            "and",
            "or",
        ):
            return (
                node.expression.operator,
                signature(at(node.left)),
                signature(at(node.right)),
            )
        if type(node) is row.ProjectSQLUnary and node.expression.operator == "not":
            return ("not", signature(at(node.operand)))
        if type(node) is row.ProjectSQLComparison and node.expression.operator == "==":
            token, operands = "==", (node.left, node.right)
        elif (
            type(node) is row.ProjectSQLScalarCall
            and node.callee_symbol.namespace is SymbolNamespace.CALLABLE
            and node.callee_symbol.name == "same_value"
            and len(node.arguments) == 2
        ):
            token, operands = "same_value", node.arguments
            calls.append(node.ref)
        else:
            return None
        return (token, *(read(at(item)) for item in operands))

    def read(node):
        if node is None or node.ref in seen:
            return None
        seen.add(node.ref)
        found = (
            _mysql_float_field(request, node.port)
            if type(node) is row.ProjectSQLMatchReference
            else None
        )
        for side, index in sides.items():
            if found is not None and found[0] in ports[index]:
                return (side, ports[index].index(found[0]))
        return None

    structure = NULLSAFE_JOIN_STRUCTURES.get(signature(at(join.on)))
    selected = tuple(at(item.expression) for item in plan.projections)
    reads = tuple(
        _mysql_float_field(request, item.port)
        if type(item) is row.ProjectSQLJoinedReference
        else None
        for item in selected
    )
    written = tuple(
        tuple(json.loads(field.representation) for field in source.fields)
        for source in sources
    )
    carrier = next(
        (
            name
            for name, (storage, domain) in NULLSAFE_JOIN_CARRIERS.get(
                request.family, {}
            ).items()
            if len(written[0]) > 1
            and written[0][1]
            == {"domain": domain, "nullable": True, "storage": storage}
        ),
        None,
    )
    if (
        structure is None
        or carrier is None
        or len(plan.expressions) != len(selected) + len(seen)
        or None in reads
        or tuple(item[0] for item in reads if item is not None)
        != (*ports[0], *ports[1])
        or any(
            item != nullsafe_join_fields(request.family, structure, carrier)
            for item in written
        )
        or (request.family, kind, structure, carrier) not in NULLSAFE_JOIN_CELLS
        or not _unit_written(plan)
    ):
        return None
    return (request.family, kind, structure, carrier), frozenset(calls)


def nullsafe_join_calls(request) -> frozenset:
    """The JOIN `on` `same_value` calls emission admits (nullsafe_join_cell);
    empty outside every cell and while emission derives as main."""
    cell = nullsafe_join_cell(request)
    return frozenset() if cell is None else cell[1]


def resolved_comparison_realization(
    family,
    tag,
    nullable,
    left,
    right,
    operator: str | None = None,
    *,
    rows_both_sides: bool,
    float_cell=None,
):
    """Original comparison-domain law over already resolved physical inputs.

    ``rows_both_sides`` is required: MySQL picks its own join and semijoin
    plans for a Float ``==`` whose operands both read rows, and a semijoin
    forced to materialize over a wide key returned outer rows twice (Phase72
    B10, reproduced by the Phase77 S06 campaign), so it stays refused there
    outside the qualified cells (MYSQL_FLOAT_ROW_CELLS, or a JOIN `on`
    `same_value` call's NULLSAFE_JOIN_CELLS cell, of any carrier, which the
    two float_carrier checks narrow to Float; ``float_cell``). So
    does ``!=``: MySQL's parser turns ``NOT (x <> y)``, also through De
    Morgan, into the equality ``x = y``.
    """
    if tag != "Bool":
        return None, ("PIE-B1002", "comparison_result_not_bool")
    if left.tag != right.tag:
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag == "UUID":
        # A UUID orders by its 16 bytes as unsigned big-endian values: the
        # order of PostgreSQL's uuid_cmp and of MySQL's BINARY(16) comparison.
        if left.storage != right.storage or left.domain != right.domain:
            return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
        return _bool(family, nullable), None
    if left.tag not in COMPARABLE:
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag in TEMPORAL and (
        left.storage != right.storage or left.domain != right.domain
    ):
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag == "Float" and (
        not float_carrier(left, family, distribution=True)
        or not float_carrier(right, family, distribution=True)
        or family == "mysql"
        and operator in {"==", "!="}
        and rows_both_sides
        and not (
            (float_cell in MYSQL_FLOAT_ROW_CELLS or float_cell in NULLSAFE_JOIN_CELLS)
            and float_carrier(left, family)
            and float_carrier(right, family)
        )
    ):
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag == "Text" and _text_domain(left) != _text_domain(right):
        return None, ("PIE-B1005", "text_comparison_domain_conflict")
    if left.tag == "Decimal" and (
        _decimal_domain(left) != _decimal_domain(right)
        or None in _decimal_domain(left)
        or left.storage != right.storage
    ):
        return None, ("PIE-B1005", "decimal_comparison_parameter_conflict")
    return _bool(family, nullable), None


def resolved_like_realization(family, tag, nullable, left, right):
    if (
        tag != "Bool"
        or left.tag != "Text"
        or right.tag != "Text"
        or _text_domain(left) != _text_domain(right)
    ):
        return None, ("PIE-B1003", "like_text_domain_not_admitted")
    return _bool(family, nullable), None


def resolved_between_realization(family, tag, nullable, values):
    """The comparison-domain law applied to each ordered BETWEEN operand."""
    if len(values) != 3:
        return None, ("PIE-B1008", "between_operand_arity")
    first, lower, upper = values
    if (
        first.tag not in COMPARABLE
        and first.tag != "UUID"
        or any(value.tag != first.tag for value in (lower, upper))
    ):
        return None, ("PIE-B1003", "between_type_pair_not_admitted")
    for bound in (lower, upper):
        # A chain is two inequalities, never an equality key.
        checked, problem = resolved_comparison_realization(
            family, tag, nullable, first, bound, rows_both_sides=False
        )
        if checked is None:
            return None, problem
    return _bool(family, nullable), None


def _scalar_call(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    values, problem = _operands(
        request, columns, expression.arguments, uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    rows_both_sides = all(_reads_row(value) for value in values)
    checked, problem = resolved_scalar_call_realization(
        request.family,
        expression.callee_symbol,
        tag,
        nullable,
        realized,
        static_values=tuple(_static_literal_value(value) for value in values),
        rows_both_sides=rows_both_sides,
        float_cell=mysql_float_cell(request, expression)
        if request.family == "mysql"
        and rows_both_sides
        and expression.callee_symbol.name == "same_value"
        else None,
        cell=mysql_scalar_cell(request.plan, expression, values)
        if request.family == "mysql"
        else None,
        mysql_checked=request.family == "mysql"
        and mysql_checked_cell(request.plan, expression, values),
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "scalar_call", values, checked), None


def _conditional(request, columns, expression, tag, nullable, uses, reference_type):
    values, problem = _operands(
        request,
        columns,
        (expression.condition, expression.when_true, expression.when_false),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    values = (values[1], values[0], values[2])
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_conditional_realization(
        request.family, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "conditional", values, checked), None


def resolved_conditional_realization(family, tag, nullable, values):
    if len(values) != 3:
        return None, ("PIE-B1008", "conditional_operand_arity")
    when_true, condition, when_false = values
    carrier = _concrete_values((when_true, when_false))
    if (
        condition.tag != "Bool"
        or condition.domain.get("kind") != "bool01"
        or carrier is None
        or carrier.tag != tag
    ):
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Text":
        result = _text_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Int":
        result = _int_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Bool":
        result = _bool_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    # A Date one (so `max(a, b)` of two Date values) is PostgreSQL only until
    # MySQL has its own differential.
    if tag not in {"Decimal", "Float", "Timestamp", "UUID"} and (
        tag != "Date" or family != "postgres"
    ):
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if any(
        branch.tag != carrier.tag
        or (
            not _typed_null(branch)
            and (branch.storage != carrier.storage or branch.domain != carrier.domain)
        )
        for branch in (when_true, when_false)
    ):
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    return Realization(tag, carrier.storage, nullable, carrier.domain), None


def _membership(request, columns, expression, tag, nullable, uses, reference_type):
    values, problem = _operands(
        request,
        columns,
        (expression.value, *expression.options),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_membership_realization(
        request.family,
        tag,
        nullable,
        realized,
        row_option_pair=_reads_row(values[0])
        and any(_reads_row(value) for value in values[1:]),
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "membership", values, checked), None


def _relation_membership(
    request, columns, expression, tag, nullable, uses, reference_type
):
    """``v [NOT] IN`` one whole producer's one column, under the literal-list
    carrier rule; never folded into options, SEMI/ANTI or COALESCE."""
    target = columns.get(expression.use)
    if type(target) is not SQLBlockTarget or target.use.ref is not expression.use:
        return None, ("PIE-B1001", "expression_block_use_outside_scope")
    column = block_read_column(target) if target.use.edge.column == 0 else None
    if column is None:
        return None, ("PIE-B1003", "relation_membership_width_not_one")
    value, problem = build_row_value(
        request, columns, expression.value, uses, reference_type=reference_type
    )
    if problem is not None:
        return None, problem
    left = realization_of(value, request.family)
    if left.tag != column[1].tag:
        return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    if tag != "Bool" or nullable is not True:
        return None, ("PIE-B1002", "relation_membership_result_not_nullable_bool")
    checked, problem = resolved_membership_realization(
        request.family, tag, nullable, (left, column[1]), row_option_pair=False
    )
    if checked is None:
        assert problem is not None
        return None, problem
    kind = "not_in" if expression.expression.negated else "in"
    return SQLBlockRead(expression, target, checked, kind, 0, (value,)), None


def mysql_float_memberships(plan) -> tuple:
    """R01 (D77.28, PL.13): the plan's Float `in` and `not in` reads of a let
    with capture lines outside a SELECT item, which MySQL emission refuses
    with PIE-B1003 `membership_type_pair_not_admitted`. On MySQL 8.4.12 such
    a read in a WHERE, flattened into a materialized semijoin beside a
    VARCHAR(1000) key, returned the outer rows of `-0.0` and `0.0` twice (the
    R01 cells, Freeze 3); every key, operator and nullability is refused. A
    SELECT item, and every read of a let without capture lines, emit as
    before. The semantic layer admits a relation read only in a WHERE or a
    SELECT item."""
    inline = {capture.inner for capture in plan.captures}
    producers = {use.ref: use.producer for use in plan.expression_block_uses}
    return tuple(
        expression
        for expression in plan.expressions
        if type(expression) is row.ProjectSQLRelationMembership
        and producers.get(expression.use) in inline
        and getattr(expression.site, "role", None)
        is not row.ProjectSQLExpressionRole.SELECT
        and plan.expressions[expression.value.position].value_type.resolved_type.name
        == "Float"
    )


def resolved_membership_realization(
    family, tag, nullable, values, *, row_option_pair: bool
):
    """``row_option_pair`` is required: the value and a literal-list option
    both read rows. Each option stands for a Float ``==``, which the comparison
    law refuses on MySQL when both operands read rows. A relation read has no
    option and passes False."""
    if not values or tag != "Bool":
        return None, ("PIE-B1003", "membership_realization_not_admitted")
    first = _concrete_values(values)
    if first is None and all(_typed_null(value) for value in values):
        return None, ("PIE-B1004", "membership_typed_null_context_missing")
    # Operands of two carriers, such as the Decimal and Int a check accepts,
    # are a pair emission does not admit, as for `amount == 1`.
    if first is None or first.tag not in MEMBERSHIP_TYPES:
        return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    if len(values) == 1:
        # The semantic layer has already checked the left operand.  The empty
        # list is a target-independent Boolean constant, even for NULL lhs.
        if nullable is not False:
            return None, ("PIE-B1002", "empty_membership_not_non_null_bool")
        return _bool(family, False), None
    for option in values[1:]:
        # Membership is the adopted same-canonical-type operation.  Requiring
        # the exact checked carrier preserves that contract without silently
        # narrowing it to the older comparison subset.
        if not _membership_carrier_matches(first, option):
            return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    if family == "mysql" and first.tag == "Float" and row_option_pair:
        return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    return _bool(family, nullable), None


def _cast(request, columns, expression, tag, nullable, uses, reference_type):
    value, problem = build_row_value(
        request, columns, expression.value, uses, reference_type=reference_type
    )
    if problem is not None:
        return None, problem
    checked, problem = resolved_cast_realization(
        request.family, tag, nullable, realization_of(value, request.family)
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "cast", (value,), checked), None


def resolved_cast_realization(family, tag, nullable, value):
    if value.tag != "Int" or proven_int_bounds(value) is None:
        return None, ("PIE-B1003", "cast_realization_not_admitted")
    if tag == "Text":
        if family != "postgres":
            return None, ("PIE-B1003", "cast_realization_not_admitted")
        return (
            Realization(
                "Text",
                {"kind": "pg_text"},
                nullable,
                {
                    "kind": "text",
                    "max_characters": 20,
                    "encoding": "UTF8",
                    "collation": "C",
                    "padding": "NO PAD",
                },
            ),
            None,
        )
    if tag != "Float":
        return None, ("PIE-B1003", "cast_realization_not_admitted")
    return Realization(
        "Float",
        {"kind": "pg_float8" if family == "postgres" else "my_double"},
        nullable,
        {"kind": "finite_float", "format": "binary64"},
    ), None


def _static_literal_value(value):
    """A literal or carried literal-only LET, never an inferred value range."""
    candidate = value
    if type(value) is SQLStageReference:
        origin = value.column.literal
        if origin is None:
            return None
        candidate = origin.value
    try:
        leaf = parameters.value_nodes(candidate)[-1]
        if type(leaf) not in {parameters.SQLLiteral, parameters.SQLParameter}:
            return None
        tag = parameters.tag_of(leaf.original)
        result = parameters.result_value(candidate)
    except (AttributeError, IndexError, TypeError, ValueError):
        return None
    return (tag, result) if tag is not None else None


def _mysql_cell_admits(family, cell) -> bool:
    """PostgreSQL, or a MySQL call whose cell is in MYSQL_SCALAR_CELLS."""

    return family == "postgres" or family == "mysql" and cell in MYSQL_SCALAR_CELLS


def resolved_scalar_call_realization(
    family,
    symbol,
    tag,
    nullable,
    values,
    *,
    static_values=None,
    rows_both_sides=True,
    float_cell=None,
    cell=None,
    mysql_checked=False,
):
    """Admit only a canonical builtin identity with its proved physical result.

    ``rows_both_sides`` is the comparison law's row-read fact (default: the
    refusing one) and ``float_cell`` its MySQL Float cell; `same_value` is
    admitted exactly where `==` is, except in a JOIN `on`, where it opens
    only in a null-safe JOIN cell (nullsafe_join_cell) and only over one
    field of each side. ``cell`` is a MySQL lpad or now() call's cell
    (mysql_scalar_cell). ``mysql_checked`` marks an S01 cell
    (mysql_checked_cell) of `abs`.
    """
    if symbol.namespace is SymbolNamespace.CALLABLE and symbol.name == "now":
        # The statement's start as a UTC microsecond civil Timestamp, on
        # PostgreSQL and in a MySQL project's cells (MYSQL_SCALAR_CELLS).
        if (
            not _mysql_cell_admits(family, cell)
            or values
            or tag != "Timestamp"
            or nullable
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        return (
            Realization(
                "Timestamp",
                {
                    "kind": {"postgres": "pg_timestamp", "mysql": "my_datetime"}[
                        family
                    ],
                    "fractional_seconds": 6,
                },
                False,
                {"kind": "timestamp"},
            ),
            None,
        )
    if symbol.namespace is not SymbolNamespace.CALLABLE or not values:
        return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
    name = symbol.name
    value = values[0]
    static_values = (None,) * len(values) if static_values is None else static_values
    if name == "round":
        if family != "postgres" or value.tag != tag:
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if tag == "Float" and len(values) == 1:
            if value.storage == {"kind": "pg_float8"} and value.domain == {
                "kind": "finite_float",
                "format": "binary64",
            }:
                return Realization(tag, value.storage, nullable, value.domain), None
            return None, ("PIE-B1004", "float_carrier_missing")
        if tag != "Decimal" or len(values) not in {1, 2}:
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        parameters = _decimal_parameters(family, value)
        if parameters is None:
            return None, ("PIE-B1004", "decimal_source_carrier_missing")
        precision, scale = parameters
        result_digits = 0
        if len(values) == 2:
            scale_literal = static_values[1] if len(static_values) > 1 else None
            if (
                values[1].tag != "Int"
                or type(scale_literal) is not tuple
                or scale_literal[0] != "Int"
                or type(scale_literal[1]) is not int
                or not -30 <= scale_literal[1] <= 30
            ):
                return None, ("PIE-B1003", "round_scale_not_a_static_supported_int")
            result_digits = scale_literal[1]
        result_scale = min(scale, max(result_digits, 0))
        result_precision = (
            precision
            if result_digits >= scale
            else precision - scale + 1 + result_scale
        )
        if not (
            1 <= result_precision <= 65
            and 0 <= result_scale <= min(result_precision, 30)
        ):
            return None, ("PIE-B1002", "round_result_outside_physical_range")
        return (
            Realization(
                "Decimal",
                {
                    "kind": "pg_numeric",
                    "precision": result_precision,
                    "scale": result_scale,
                },
                nullable,
                {
                    "kind": "decimal",
                    "precision": result_precision,
                    "scale": result_scale,
                },
            ),
            None,
        )
    if name == "date_trunc":
        if family != "postgres" or len(values) != 2 or values[0].tag != "Text":
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        unit_literal = static_values[0] if static_values else None
        temporal = values[1]
        if (
            type(unit_literal) is not tuple
            or unit_literal[0] != "Text"
            or type(unit_literal[1]) is not str
            or unit_literal[1]
            not in (
                {"year", "month", "day"}
                if tag == "Date"
                else {"year", "month", "day", "hour", "minute"}
            )
        ):
            return None, ("PIE-B1003", "date_trunc_unit_not_a_static_supported_text")
        if (
            tag == "Date"
            and temporal.tag == "Date"
            and (
                temporal.storage == {"kind": "pg_date"}
                and temporal.domain == {"kind": "date"}
            )
        ):
            return Realization(tag, temporal.storage, nullable, temporal.domain), None
        if (
            tag == "Timestamp"
            and temporal.tag == "Timestamp"
            and (
                temporal.storage == {"kind": "pg_timestamp", "fractional_seconds": 6}
                and temporal.domain == {"kind": "timestamp"}
            )
        ):
            return Realization(tag, temporal.storage, nullable, temporal.domain), None
        return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
    if name == "trim" and len(values) == 1 and tag == "Text":
        result = _text_result(
            family, value, nullable, value.domain.get("max_characters")
        )
        if result is not None:
            return result, None
    if name in {"lower", "upper"} and len(values) == 1 and tag == "Text":
        result = _text_result(
            family, value, nullable, value.domain.get("max_characters")
        )
        if result is not None:
            return result, None
        return None, ("PIE-B1004", "text_case_result_bound_missing")
    if name == "len" and len(values) == 1 and value.tag == "Text" and tag == "Int":
        maximum = value.domain.get("max_characters")
        if type(maximum) is not int or maximum < 0:
            return None, ("PIE-B1004", "text_length_bound_missing")
        storage = {"kind": "pg_int8" if family == "postgres" else "my_bigint"}
        checked = _checked_int(storage, 0, maximum, nullable)
        if checked is None:
            return None, ("PIE-B1002", "text_length_outside_physical_range")
        proof = signed_range(storage)
        assert proof is not None
        return (
            Realization(
                checked.tag,
                checked.storage,
                checked.nullable,
                checked.domain,
                proof,
            ),
            None,
        )
    if name == "substr" and tag == "Text":
        if not (
            len(values) == 3
            and value.tag == "Text"
            and values[1].tag == values[2].tag == "Int"
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        start, count = proven_int_bounds(values[1]), proven_int_bounds(values[2])
        maximum = value.domain.get("max_characters")
        if (
            start is None
            or count is None
            or count[0] < 0
            or count[1] < 0
            or type(maximum) is not int
        ):
            return None, ("PIE-B1004", "substring_result_bound_missing")
        if family == "postgres" and not all(
            -(1 << 31) <= bound <= (1 << 31) - 1 for bound in (*start, *count)
        ):
            return None, ("PIE-B1002", "substring_index_outside_physical_range")
        result = _text_result(family, value, nullable, min(maximum, count[1]))
        if result is not None:
            return result, None
    if name == "replace":
        if len(values) != 3 or tag != "Text":
            return None, ("PIE-B1004", "text_replace_result_bound_missing")
        text, needle, replacement = values
        if any(
            item.tag != "Text" or _text_domain(item) != _text_domain(text)
            for item in values[1:]
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        input_maximum = text.domain.get("max_characters")
        replacement_maximum = replacement.domain.get("max_characters")
        if type(input_maximum) is not int or type(replacement_maximum) is not int:
            return None, ("PIE-B1004", "text_replace_result_bound_missing")
        result = _text_result(
            family,
            text,
            nullable,
            input_maximum * max(1, replacement_maximum),
        )
        if result is not None:
            return result, None
    if name == "lpad":
        # Never truncates, so as wide as the text or the width; PostgreSQL
        # lpad() takes an int4 width. A MySQL project only in its cells
        # (MYSQL_SCALAR_CELLS), whose width literal is from 0 to 256.
        if not _mysql_cell_admits(family, cell) or len(values) != 3 or tag != "Text":
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        text, width, fill = values
        fill_literal = static_values[2]
        if (
            width.tag != "Int"
            or fill.tag != "Text"
            or _text_domain(fill) != _text_domain(text)
            or type(fill_literal) is not tuple
            or fill_literal[0] != "Text"
            or type(fill_literal[1]) is not str
            or len(fill_literal[1]) != 1
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        bounds = proven_int_bounds(width)
        maximum = text.domain.get("max_characters")
        if family == "mysql" and (
            bounds is None
            or type(maximum) is not int
            or not 0 <= bounds[0] <= bounds[1] <= MYSQL_PACKET_FLOOR_CHARACTERS
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if bounds is None or type(maximum) is not int:
            return None, ("PIE-B1004", "lpad_result_bound_missing")
        if not all(-(1 << 31) <= bound <= (1 << 31) - 1 for bound in bounds):
            return None, ("PIE-B1002", "lpad_width_outside_physical_range")
        result = _text_result(family, text, nullable, max(maximum, bounds[1]))
        if result is not None:
            return result, None
    if (
        name == "add_months"
        and family == "postgres"
        and len(values) == 2
        and tag == "Date"
        and value.storage == {"kind": "pg_date"}
        and value.domain == {"kind": "date"}
        and values[1].tag == "Int"
        and not _typed_null(values[1])
    ):
        # A date plus months, clamped to the end of a shorter month; MySQL
        # project SQL refuses it.
        return Realization("Date", value.storage, nullable, value.domain), None
    if name == "concat":
        # NULL when any argument is; otherwise as wide as all of them. MySQL
        # types a CONCAT from storage lengths and a literal's UTF-8 bytes, not
        # from these widths, so MySQL project SQL refuses it.
        concrete = tuple(item for item in values if not _typed_null(item))
        if (
            family != "postgres"
            or len(values) < 2
            or tag != "Text"
            or not concrete
            or any(item.tag != "Text" for item in values)
            or any(_text_domain(item) != _text_domain(concrete[0]) for item in concrete)
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        widths = tuple(item.domain.get("max_characters") for item in concrete)
        if any(type(width) is not int for width in widths):
            return None, ("PIE-B1004", "text_concat_result_bound_missing")
        result = _text_carrier_result(family, values, nullable, sum(widths))
        if result is not None:
            return result, None
    if name == "same_value" and len(values) == 2:
        # NULL-safe equality of two operands that `==` compares; never NULL.
        if nullable is not False:
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        left, right = values
        return resolved_comparison_realization(
            family,
            tag,
            nullable,
            left,
            right,
            "==",
            rows_both_sides=rows_both_sides,
            float_cell=float_cell,
        )
    if (
        name in {"contains", "starts_with", "ends_with"}
        and len(values) == 2
        and tag == "Bool"
    ):
        left, right = values
        if left.tag == right.tag == "Text" and _text_domain(left) == _text_domain(
            right
        ):
            return _bool(family, nullable), None
    if (name == "coalesce" and len(values) >= 2) or (
        name == "nullif" and len(values) == 2
    ):
        carrier = _concrete_values(values)
        if carrier is not None and carrier.tag == tag == "Text":
            result = _text_carrier_result(
                family,
                values,
                nullable,
                None if name == "coalesce" else values[0].domain.get("max_characters"),
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if carrier is not None and carrier.tag == tag == "Int":
            result = _int_carrier_result(
                family, values, nullable, preserve_input=name == "nullif"
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if carrier is not None and carrier.tag == tag == "Bool":
            result = _bool_carrier_result(
                family, values, nullable, preserve_input=name == "nullif"
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if (
            carrier is not None
            and tag in {"Decimal", "Float", "Timestamp", "UUID"}
            and all(
                item.tag == carrier.tag
                and (
                    _typed_null(item)
                    or (
                        item.storage == carrier.storage
                        and item.domain == carrier.domain
                    )
                )
                for item in values[1:]
            )
            and values[0].tag == carrier.tag
            and tag == carrier.tag
        ):
            return Realization(tag, carrier.storage, nullable, carrier.domain), None
    if name == "abs" and len(values) == 1 and value.tag == tag == "Int":
        bounds = proven_int_bounds(value)
        if bounds is None:
            return None, ("PIE-B1004", "int_range_proof_missing")
        low, high = bounds
        checked = _unary_int(
            family,
            value,
            max(low, -high, 0),
            max(-low, high),
            nullable,
            mysql_checked,
        )
        if checked is None:
            return None, ("PIE-B1002", "abs_result_outside_physical_range")
        return checked, None
    if name == "abs" and len(values) == 1 and value.tag == tag in {"Decimal", "Float"}:
        return Realization(tag, value.storage, nullable, value.domain), None
    if (
        name == "date_of"
        and len(values) == 1
        and value.tag == "Timestamp"
        and (
            _typed_null(value)
            or (
                value.storage
                == {
                    "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                }
                and value.domain == {"kind": "timestamp"}
            )
        )
        and tag == "Date"
    ):
        return (
            Realization(
                "Date",
                {"kind": "pg_date" if family == "postgres" else "my_date"},
                nullable,
                {"kind": "date"},
            ),
            None,
        )
    if (
        name == "sign"
        and len(values) == 1
        and value.tag in {"Int", "Decimal"}
        and tag == "Int"
    ):
        checked = _checked_int(
            {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
            -1,
            1,
            nullable,
        )
        if checked is not None:
            return checked, None
    if (
        name in {"year", "month", "day", "hour", "minute"}
        and len(values) == 1
        and (
            (
                value.tag == "Timestamp"
                and value.storage
                == {
                    "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                }
                and value.domain == {"kind": "timestamp"}
            )
            or (
                name in {"year", "month", "day"}
                and value.tag == "Date"
                and value.storage
                == {"kind": "pg_date" if family == "postgres" else "my_date"}
                and value.domain == {"kind": "date"}
            )
        )
        and tag == "Int"
    ):
        bounds = {
            "year": (1000, 9999),
            "month": (1, 12),
            "day": (1, 31),
            "hour": (0, 23),
            "minute": (0, 59),
        }[name]
        checked = _checked_int(
            {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
            *bounds,
            nullable,
        )
        if checked is not None:
            return checked, None
    return None, ("PIE-B1003", "scalar_call_signature_not_admitted")


def block_read_operands(node: SQLBlockRead, family: str) -> tuple[Realization, ...]:
    """The compared realizations of a membership read; none for the others."""
    if node.kind not in ("in", "not_in"):
        return ()
    column = block_read_column(node.target)
    if column is None or len(node.operands) != 1:
        raise ValueError("membership read operands")
    return realization_of(node.operands[0], family), column[1]


def realization_of(value, family: str) -> Realization:
    if type(value) in {
        SQLStageReference,
        SQLOperation,
        SQLParameterRead,
        SQLBlockRead,
        SQLCapturedReference,
        SQLListOperation,
    }:
        return value.realization
    return constant_realization(value, family)


def value_nodes(value) -> tuple[Any, ...]:
    """Preorder image of one admitted tree; constant chains stay a single leaf."""
    return _value_nodes(value, render_order=False)


def rendered_value_nodes(value) -> tuple[Any, ...]:
    """Preorder image of one admitted tree in SQL rendering order."""
    return _value_nodes(value, render_order=True)


def _value_nodes(value, *, render_order) -> tuple[Any, ...]:
    if type(value) in {SQLStageReference, SQLCapturedReference}:
        return (value,)
    if type(value) is SQLBlockRead:
        # A membership read renders its operand before the read relation.
        return (
            value,
            *(
                node
                for operand in (
                    *value.operands,
                    *((value.predicate,) if value.predicate is not None else ()),
                )
                for node in _value_nodes(operand, render_order=render_order)
            ),
        )
    if type(value) is SQLListOperation:
        return (
            value,
            *(
                node
                for operand in value.operands
                for node in _value_nodes(operand, render_order=render_order)
            ),
        )
    if type(value) is SQLOperation:
        result: list[Any] = [value]
        operands = (
            tuple(
                value.operands[i]
                for i in rendered_operand_order(value.kind, len(value.operands))
            )
            if render_order
            else value.operands
        )
        for operand in operands:
            result.extend(_value_nodes(operand, render_order=render_order))
        return tuple(result)
    return (value,)


def operand_refs(value) -> tuple[Any, ...]:
    if type(value) is SQLBlockRead:
        return tuple(
            root_expression(operand).ref
            for operand in (
                *value.operands,
                *((value.predicate,) if value.predicate is not None else ()),
            )
        )
    if type(value) in (SQLOperation, SQLListOperation):
        return tuple(root_expression(operand).ref for operand in value.operands)
    return ()


def root_expression(value):
    if type(value) in {
        SQLStageReference,
        SQLOperation,
        SQLParameterRead,
        SQLBlockRead,
        SQLCapturedReference,
        SQLListOperation,
    }:
        return value.original
    return parameters.value_nodes(value)[0].original


def requirement_kind(node) -> str:
    if type(node) is SQLStageReference:
        return "reference"
    if type(node) is SQLParameterRead:
        return "query_parameter"
    if type(node) is SQLBlockRead:
        return "relation_membership" if node.kind in ("in", "not_in") else node.kind
    if type(node) is SQLCapturedReference:
        return "capture"
    if type(node) is SQLListOperation:
        return "list_operation"
    assert type(node) is SQLOperation
    return {
        "sign": "arithmetic",
        "arithmetic": "arithmetic",
        "logical": "logical",
        "comparison": "comparison",
        "between": "between",
        "scalar_call": "scalar_call",
        "conditional": "conditional",
        "membership": "membership",
        "cast": "cast",
        "not": "not",
        "null_test": "null_test",
    }[node.kind]


REQUIREMENT_RULES = {
    "query_parameter": "R04",
    "reference": "R05",
    "arithmetic": "R05",
    "comparison": "R05",
    "between": "R05",
    "scalar_call": "R05",
    "conditional": "R05",
    "membership": "R05",
    "cast": "R05",
    "not": "R06",
    "null_test": "R05",
    "logical": "R06",
    # A block read wraps one complete producer terminal like SEMI/ANTI.
    "exists": "R11",
    "scalar": "R11",
    "relation_membership": "R11",
    # A captured field is the outer correlation of an inline read.
    "capture": "R11",
    # A list operation reads its own row's collected list (S06): a scalar of
    # the row, never a semi-join (G1-02).
    "list_operation": "R05",
}


# Retained expression demands of these kinds belong to R05; the compiled replay
# attributes its operation records by the same roles.
R05_OPERATIONS = {
    row.ProjectSQLComparison: "comparison",
    row.ProjectSQLBetween: "between",
    row.ProjectSQLIsNull: "null_test",
    row.ProjectSQLConditional: "conditional",
    row.ProjectSQLMembership: "membership",
    row.ProjectSQLCast: "cast",
}


def demand_rule(plan, entry) -> str | None:
    """Slice6 rule attribution for the retained expression/filter demand families."""
    if entry.family.value == "filter":
        return "R06"
    if entry.family.value != "expression":
        return None
    expression = plan.expressions[entry.subject.position]
    if type(expression) is row.ProjectSQLBinary:
        return "R06" if expression.expression.operator in LOGICAL else "R05"
    if type(expression) in R05_OPERATIONS:
        return "R05"
    if type(expression) in {
        row.ProjectSQLRelationExists,
        row.ProjectSQLAny,
        row.ProjectSQLRelationScalar,
        row.ProjectSQLRelationMembership,
    }:
        return "R11"
    return None


def match_applicability(request):
    """Check retained ON trees against the same scalar domain; never build JOIN SQL."""
    plan = request.plan
    problems = []
    sites = {
        site.ref
        for site in plan.expression_sites
        if type(site) is row.ProjectSQLMatchSite
    }
    children = {}
    for operand in plan.operands:
        children.setdefault(operand.parent, []).append(operand.child)
    inside_any = set()
    pending = [
        expression.predicate
        for expression in plan.expressions
        if type(expression) is row.ProjectSQLAny
    ]
    while pending:
        reference = pending.pop()
        if reference not in inside_any:
            inside_any.add(reference)
            pending.extend(children.get(reference, ()))
    for expression in plan.expressions:
        if expression.site.ref not in sites or expression.ref in inside_any:
            continue
        problem = _match_node(plan, expression)
        if problem is not None:
            problems.append((*problem, expression.ref, expression.site.occurrence.span))
    return tuple(problems)


def _match_node(plan, expression):
    if type(expression) in (row.ProjectSQLAny, row.ProjectSQLAnyReference):
        return None
    if type(expression) is row.ProjectSQLMatchReference:
        ports = {port.ref: port for port in plan.join_ports}
        port = ports.get(expression.port)
        if port is None or port.block is not expression.site.block:
            return ("PIE-B1001", "match_reference_outside_pre_match_scope")
        if value_tag(expression) is None:
            return ("PIE-B1004", "match_reference_logical_type_missing")
        return None
    if type(expression) is row.ProjectSQLComparison:
        if expression.expression.operator not in COMPARISONS:
            return ("PIE-B1003", "match_comparison_operator_not_admitted")
        return None
    if type(expression) is row.ProjectSQLBinary:
        if expression.expression.operator not in LOGICAL:
            return ("PIE-B1003", "match_binary_operator_not_admitted")
        return None
    if type(expression) in {row.ProjectSQLIsNull, row.ProjectSQLLiteral}:
        return None
    return ("PIE-B1003", "match_condition_not_in_row_domain")
