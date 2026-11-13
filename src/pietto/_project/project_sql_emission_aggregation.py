"""Admitted GROUPED/GLOBAL aggregation stages, satisfying and result domains."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_expressions as plan_expressions
from pietto._project import project_sql_emission_nested as collecting
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_unnest as unnesting
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.aggregate_grouped_schema import (
    ProjectComputedGroupKeyFact,
    ProjectGroupKeyFact,
)
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueTypeKind

__all__: tuple[str, ...] = ()

# R13's first-version aggregate promise, spelled exactly. Nothing here grants a
# generic inline DISTINCT, an aggregate FILTER, internal ordering or any other
# function: every other retained aggregate keeps its own typed non-support.
SPELLING = {
    "count": "COUNT",
    "count_distinct": "COUNT",
    "sum": "SUM",
    "avg": "AVG",
    "min": "MIN",
    "max": "MAX",
    "string_agg": "string_agg",
    # PostgreSQL only: SQRT(CAST(VAR_SAMP(x) AS pg_catalog.float8)), the
    # outer SQRT fixed by the function (ROOT_FUNCTIONS); `variance` and
    # `pvariance` are CAST(VAR_SAMP(x) ...) and CAST(VAR_POP(x) ...), `pstdev`
    # SQRT(CAST(VAR_POP(x) ...)).
    "stddev": "VAR_SAMP",
    "variance": "VAR_SAMP",
    "pvariance": "VAR_POP",
    "pstdev": "VAR_POP",
    # PostgreSQL only: PERCENTILE_CONT(fraction) WITHIN GROUP (ORDER BY
    # CAST(x AS pg_catalog.float8)), the fraction 0.5 for `median` and the
    # Float literal of `quantile`, its second argument value, in the
    # `delimiter` slot.
    "median": "PERCENTILE_CONT",
    "quantile": "PERCENTILE_CONT",
    # PostgreSQL only, the conditional count and sum of a group:
    # COUNT(CASE WHEN test THEN 1 END) and COALESCE(CAST(SUM(CASE WHEN test
    # THEN CAST(x AS pg_catalog.int8) END) AS pg_catalog.int8), 0), the test
    # of a sum in the `delimiter` slot.
    "filtered_count": "COUNT",
    "filtered_sum": "SUM",
    # PostgreSQL only: COUNT(DISTINCT CASE WHEN a IS NOT NULL AND b IS NOT NULL
    # THEN ROW(a, b) END), `count_distinct(a, b, ...)`: its first field is the
    # `argument`, the others are `extra_arguments`.
    "count_distinct_tuple": "COUNT",
    # PostgreSQL only, the test of a group: (COUNT(CASE WHEN test THEN 1 END)
    # > 0) and (COUNT(CASE WHEN test THEN NULL ELSE 1 END) = 0).
    "group_any": "COUNT",
    "group_all": "COUNT",
    # PostgreSQL: (ARRAY_AGG(x ORDER BY k ASC, ...))[1], the element
    # wrapping fixed by the function (ORDERED_VALUE_FUNCTIONS); `last` flips
    # every authored direction (`rendered_direction`). MySQL spells them
    # RANKED_SPELLING (`spelling`).
    "first": "ARRAY_AGG",
    "last": "ARRAY_AGG",
}
# Phase77 S13: MySQL writes `first` and `last` as MAX(CASE WHEN <rank> = 1
# THEN x END) over a derived table that numbers the rows of each group with
# ROW_NUMBER() OVER (PARTITION BY <key> ORDER BY <keys>), the primitive whose
# raw MySQL 8.4.12 campaign (wave-b s13, campaign-20261111T1636Z) matched the
# PostgreSQL reference for nullable BIGINT, DOUBLE, binary VARCHAR and DECIMAL
# values only, and only in its own statement shape (`ranked_statement`).
RANKED_SPELLING = "MAX"
# The sample and population variances and deviations: one Int or Float
# argument, a PostgreSQL VAR_SAMP or VAR_POP cast to float8 once.
SPREAD_FUNCTIONS = frozenset({"stddev", "variance", "pvariance", "pstdev"})
# The aggregates whose PostgreSQL rendering wraps the result cast in SQRT( ... ).
ROOT_FUNCTIONS = frozenset({"stddev", "pstdev"})
# Phase77 S05: MySQL spells each of the four as the primitive its raw
# qualification ran over a nullable DOUBLE column, with no cast and no SQRT,
# and only in the cell of mysql_spread_cell.
MYSQL_SPREAD_SPELLING = {
    "stddev": "STDDEV_SAMP",
    "variance": "VAR_SAMP",
    "pvariance": "VAR_POP",
    "pstdev": "STDDEV_POP",
}
# The value at the first or last row of a group's total order: the first
# element of an ordered ARRAY_AGG, which keeps a NULL value.
ORDERED_VALUE_FUNCTIONS = frozenset({"first", "last"})
# The aggregates with an internal ORDER BY.
ORDERED_FUNCTIONS = frozenset({"string_agg", *ORDERED_VALUE_FUNCTIONS})
# The interpolated quantiles, an ordered-set PERCENTILE_CONT.
QUANTILE_FUNCTIONS = frozenset({"median", "quantile"})
# The aggregates of a test of each row, which is their only argument but for a
# conditional sum's (its `delimiter`).
GROUP_TEST_FUNCTIONS = frozenset({"group_any", "group_all"})
FILTERED_FUNCTIONS = frozenset(
    {"filtered_count", "filtered_sum", *GROUP_TEST_FUNCTIONS}
)
TARGET_CHECKED_BINARY64 = rows.TARGET_CHECKED_BINARY64
DISTINCT_FUNCTIONS = frozenset({"count_distinct", "count_distinct_tuple"})
COUNTING_FUNCTIONS = frozenset({"count", "count_distinct", "count_distinct_tuple"})
EXTREMA_FUNCTIONS = frozenset({"min", "max"})
# COUNT publishes its own non-null result; R13 declares the signed64 premise, so
# the domain is that premise's bound, never a guess about this input's row count.
COUNT_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
COUNT_MAX = (1 << 63) - 1
# R12 group comparison stays inside the reviewed V01-V04 domains. V05 keeps its
# meaning limits. A Float group key is admitted only by group_key_problem, which
# PostgreSQL window partitions and string_agg order keys also read (E6).
GROUPING_TAGS = frozenset(
    {"Int", "Bool", "Text", "Decimal", "Timestamp", "Date", "UUID"}
)
TEXT_DOMAIN_KEYS = ("encoding", "collation", "padding")
DECIMAL_DOMAIN_KEYS = ("precision", "scale")
STAGE_KINDS = (
    "let",
    "where",
    "aggregate",
    "satisfying",
    "window",
    "qualify",
    "projection",
)
# The one admitted stage schedule: ordered LET, one WHERE, the aggregation, its
# own satisfying, the window stage, QUALIFY, then the exact visible projection.
STAGE_ORDER = {kind: position for position, kind in enumerate(STAGE_KINDS)}
OPERATORS = {
    "let": (),
    "where": ("row_filter",),
    "aggregate": ("group_aggregate",),
    "satisfying": ("result_filter",),
    "window": ("window_evaluation",),
    "qualify": ("qualify",),
    "projection": ("final_projection",),
}
FIELD_NULLABILITY = {
    ProjectRowFieldNullability.NON_NULL: False,
    ProjectRowFieldNullability.NULLABLE: True,
    ProjectRowFieldNullability.UNKNOWN: "unknown",
}
VALUE_NULLABILITY = {
    EffectiveNullability.NON_NULL: False,
    EffectiveNullability.NULLABLE: True,
    EffectiveNullability.UNKNOWN: "unknown",
}
# Slice8 adds exactly one admitted expression variant: the already-resolved use
# of an aggregate stage result. A scalar call inside an argument stays non-support.
ProjectSQLResultReference = aggregation.ProjectSQLResultReference
# One rule per retained aggregation demand subject: R12 owns grouping, empty
# input, determinant comparison, result projection and the retained risks; R13
# owns the aggregate operation itself.
DEMAND_RULES = {
    "aggregation": "R12",
    "group_key": "R12",
    "aggregate": "R13",
    "aggregate_projection": "R12",
    "aggregate_risk": "R12",
}


REPR_SCALAR_LIMIT = 32


def _scalar(value: Any) -> str:
    """Bound a name-like scalar before it is escaped, never touching objects."""

    if value is None:
        return "None"
    if type(value) is not str:
        return "?"
    if len(value) > REPR_SCALAR_LIMIT:
        return repr(value[:REPR_SCALAR_LIMIT] + "...")
    return repr(value)


def _count(value: Any) -> int | str:
    """An O(1) length for an exact builtin tuple, never a user-defined traversal."""

    return len(value) if type(value) is tuple else "?"


def _present(value: Any) -> str:
    return "none" if value is None else "present"


@dataclass(frozen=True, slots=True, eq=False)
class AggregateOrigin:
    """One transported value's retained aggregate-stage provenance.

    It rides on the stage column, so a grouped value stays distinguishable from a
    source field after any number of carries, named uses or outer JOIN ports.
    """

    kind: str
    aggregation: Any
    result: Any
    inputs: tuple[Any, ...]
    key: Any = None
    aggregate: Any = None
    function: str | None = None

    def __repr__(self) -> str:
        """Summarize this origin in constant work; the shared graph stays opaque."""

        return (
            f"AggregateOrigin(kind={_scalar(self.kind)}, "
            f"function={_scalar(self.function)}, "
            f"inputs=<{_count(self.inputs)}>, aggregation=..., result=..., "
            f"key={_present(self.key)}, aggregate={_present(self.aggregate)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class AggregateKeyColumn:
    """One ordered group determinant, bound to its exact pre-aggregate input."""

    ordinal: int
    export: Any
    key: Any
    input_port: Any
    read: rows.StageColumn
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        """Summarize this determinant; no retained product is formatted."""

        return (
            f"AggregateKeyColumn(ordinal={self.ordinal!r}, "
            f"label={_scalar(self.label)}, key=..., input_port=..., "
            "read=..., symbol=..., column=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class AggregateValueColumn:
    """One aggregate occurrence, its exact argument and its own result port."""

    ordinal: int
    export: Any
    aggregate: Any
    function: str
    spelling: str
    distinct: bool
    argument_cast: str | None
    argument: Any
    symbol: Any
    label: str
    column: rows.StageColumn
    delimiter: Any = None
    order_by: tuple[Any, ...] = ()
    result_cast: str | None = None
    extra_arguments: tuple[Any, ...] = ()

    def __repr__(self) -> str:
        """Summarize this occurrence; no retained product is formatted."""

        return (
            f"AggregateValueColumn(ordinal={self.ordinal!r}, "
            f"label={_scalar(self.label)}, function={_scalar(self.function)}, "
            f"spelling={_scalar(self.spelling)}, distinct={self.distinct!r}, "
            f"argument_cast={_scalar(self.argument_cast)}, "
            f"result_cast={_scalar(self.result_cast)}, "
            f"argument={_present(self.argument)}, aggregate=..., "
            "export=..., symbol=..., column=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class AggregateOrderItem:
    """One authored string_agg ordering key and its realized pre-stage value."""

    value: Any
    direction: str


@dataclass(frozen=True, slots=True, eq=False)
class AggregateProjectionColumn:
    """One canonical visible output reading one established result port."""

    ordinal: int
    export: Any
    projection: Any
    input_port: Any
    read: rows.StageColumn
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        """Summarize this visible output; no retained product is formatted."""

        return (
            f"AggregateProjectionColumn(ordinal={self.ordinal!r}, "
            f"label={_scalar(self.label)}, projection=..., input_port=..., "
            "read=..., symbol=..., column=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class AggregateStage:
    """One realized GROUPED/GLOBAL aggregation over its exact input terminal."""

    aggregation: Any
    keys: tuple[Any, ...]
    values: tuple[AggregateValueColumn, ...]
    mode: str
    empty_input: str

    def __repr__(self) -> str:
        """Summarize this stage in constant work; no child is formatted."""

        return (
            f"AggregateStage(aggregation=..., mode={_scalar(self.mode)}, "
            f"empty_input={_scalar(self.empty_input)}, "
            f"keys=<{_count(self.keys)}>, values=<{_count(self.values)}>)"
        )


def aggregated_definitions(plan) -> dict[Any, Any]:
    """Each definition's single retained aggregation, keyed by definition ref."""
    result: dict[Any, Any] = {}
    for stage in plan.aggregations:
        if stage.definition in result:
            return {}
        result[stage.definition] = stage
    return result


def stage_schedule_valid(
    kinds: tuple[str, ...], *, aggregated: bool, windowed: bool = False
) -> bool:
    """The exact admitted stage order for one definition, and nothing else."""
    if (
        not kinds
        or kinds[-1] != "projection"
        or set(kinds) - set(STAGE_KINDS)
        or kinds.count("projection") != 1
        or kinds.count("where") > 1
        or kinds.count("aggregate") > 1
        or kinds.count("satisfying") > 1
        or kinds.count("window") > 1
        or kinds.count("qualify") > 1
        or ("aggregate" in kinds) is not aggregated
        or ("window" in kinds) is not windowed
        or ("satisfying" in kinds and "aggregate" not in kinds)
        or ("qualify" in kinds and "window" not in kinds)
    ):
        return False
    positions = [STAGE_ORDER[kind] for kind in kinds]
    return positions == sorted(positions)


def function_name(source) -> str | None:
    """The retained aggregate function identity; never re-read from source text."""
    if isinstance(source, aggregation.ProjectAggregateExpressionAnalysis):
        return aggregation.filtered_function(aggregation.aggregate_call(source)) or (
            source.fact.function
        )
    name = getattr(source, "function_name", None)
    return name if type(name) is str else None


def key_logical(key) -> tuple[str, bool | str] | None:
    """One group determinant's retained logical tag and nullability."""
    if isinstance(key, (ProjectGroupKeyFact, ProjectComputedGroupKeyFact)):
        field = key.key_field
        if field.resolved_type.kind is not ProjectResolvedTypeKind.BUILTIN:
            return None
        nullable = FIELD_NULLABILITY.get(field.nullability)
        return None if nullable is None else (field.resolved_type.name, nullable)
    value_type = key.value_type
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    nullable = VALUE_NULLABILITY.get(value_type.nullability)
    return None if nullable is None else (value_type.resolved_type.name, nullable)


def grouping_problem(realization: rows.Realization):
    """Whether one carrier may be compared as a group determinant at all."""
    if realization.tag not in GROUPING_TAGS:
        return "PIE-B1003", "group_key_type_outside_reviewed_comparison_domain"
    if realization.tag == "Bool" and realization.domain.get("kind") != "bool01":
        return "PIE-B1002", "group_key_outside_bool_domain"
    if realization.tag == "Text" and any(
        realization.domain.get(key) is None for key in TEXT_DOMAIN_KEYS
    ):
        return "PIE-B1004", "group_key_text_comparison_domain_missing"
    if realization.tag == "Decimal" and any(
        realization.domain.get(key) is None for key in DECIMAL_DOMAIN_KEYS
    ):
        return "PIE-B1004", "group_key_decimal_parameters_missing"
    if realization.tag == "Int" and realization.domain.get("kind") != "int_range":
        return "PIE-B1004", "group_key_int_range_evidence_missing"
    if realization.tag == "Timestamp" and (
        realization.storage
        not in (
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "my_datetime", "fractional_seconds": 6},
        )
        or realization.domain != {"kind": "timestamp"}
    ):
        return "PIE-B1002", "group_key_temporal_physical_representation_mismatch"
    if realization.tag == "Date" and (
        realization.storage not in ({"kind": "pg_date"}, {"kind": "my_date"})
        or realization.domain != {"kind": "date"}
    ):
        return "PIE-B1002", "group_key_temporal_physical_representation_mismatch"
    if realization.tag == "UUID" and (
        realization.storage not in ({"kind": "pg_uuid"}, {"kind": "my_uuid_bytes"})
        or realization.domain != {"kind": "uuid", "encoding": "standard_bytes"}
    ):
        return "PIE-B1002", "group_key_uuid_physical_representation_mismatch"
    return None


def group_key_problem(
    realization: rows.Realization,
    *,
    distribution: bool = True,
    float_key_cell: bool = False,
):
    """A GROUP BY key: the grouping law, or a PostgreSQL Float, a window
    distribution result too (E6) unless ``distribution`` is false. Floats group
    by float equality (-0.0 == 0.0); MySQL kept -0.0 and 0.0 in two groups over
    a wide key in the real-database campaign, so its Float keys stay refused
    outside the Phase77 S07 cells (``float_key_cell``, the reader's own
    derivation of rows.MYSQL_FLOAT_KEY_CELLS)."""
    if realization.tag != "Float":
        return grouping_problem(realization)
    if rows.float_carrier(realization, "postgres", distribution=distribution) or (
        float_key_cell and rows.float_carrier(realization, "mysql")
    ):
        return None
    return "PIE-B1003", "group_key_type_outside_reviewed_comparison_domain"


def spelling(family: str, function: str) -> str:
    """One aggregate's emitted function name on one target."""
    if family == "mysql" and function in SPREAD_FUNCTIONS:
        return MYSQL_SPREAD_SPELLING[function]
    if family == "mysql" and function in ORDERED_VALUE_FUNCTIONS:
        return RANKED_SPELLING
    return SPELLING[function]


# The VARCHAR lengths and the DECIMAL the S13 qualification used; others wait
# for the candidate run (F8).
RANKED_VARCHAR_LENGTHS = (32, 64)
RANKED_DECIMAL = {"kind": "my_decimal", "precision": 65, "scale": 30}


def _binary_varchar(realization) -> bool:
    storage, domain = realization.storage, realization.domain
    return (
        storage.get("kind") == "my_varchar"
        and set(storage) == {"kind", "length"}
        and type(storage["length"]) is int
        and storage["length"] in RANKED_VARCHAR_LENGTHS
        and tuple(domain.get(key) for key in TEXT_DOMAIN_KEYS)
        == ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
    )


def ranked_value(realization) -> bool:
    """A MySQL `first` or `last` value whose carrier the qualification saw
    MAX(CASE ...) keep: a nullable BIGINT, DOUBLE, binary VARCHAR(32) or
    VARCHAR(64), or DECIMAL(65,30). A Bool, Date, Timestamp or UUID came back
    with other column metadata."""
    if realization is None or realization.nullable is not True:
        return False
    return (
        realization.tag == "Int"
        and realization.storage == {"kind": "my_bigint"}
        or realization.tag == "Float"
        and rows.float_carrier(realization, "mysql")
        or realization.tag == "Text"
        and _binary_varchar(realization)
        or realization.tag == "Decimal"
        and realization.storage == RANKED_DECIMAL
    )


def ranked_key(realization, *, group: bool = False) -> bool:
    """A MySQL ROW_NUMBER order key of a class the qualification ordered by: a
    BIGINT, or a nullable binary VARCHAR that a WHERE proves never None; with
    ``group``, its PARTITION BY key, a non-null BIGINT."""
    if realization is None:
        return False
    bigint = realization.tag == "Int" and realization.storage == {"kind": "my_bigint"}
    if group:
        return bigint and realization.nullable is False
    return bigint or (
        realization.tag == "Text"
        and realization.nullable is True
        and _binary_varchar(realization)
    )


def _ranked_read(plan, available, ref, reference_type):
    """The realization of the stage column that one aggregate input reads
    directly, without realizing it, or None."""
    expression = _plan_node(plan, ref)
    if expression is None or type(expression) is not reference_type:
        return None
    column = available.get(expression.port)
    return column.realization if type(column) is rows.StageColumn else None


def ranked_inputs(plan, available, keys, values, reference_type) -> bool:
    """Whether every input of one MySQL aggregation is of a class S13
    qualified: at most one non-null BIGINT key, only `first` and `last`, each
    of one `ranked_value` field ordered by `ranked_key` fields, and a field
    that the WHERE compares with a parameter of the key's class."""
    if len(keys) > 1 or not values:
        return False
    for key in keys:
        read = available.get(key.input)
        if type(read) is not rows.StageColumn or not ranked_key(
            read.realization, group=True
        ):
            return False
    origin = _ranked_origin(plan)
    where = _ranked_filter(plan, origin)
    columns = {origin(port): column for port, column in available.items()}
    if where is None or not all(
        type(columns.get(field)) is rows.StageColumn
        and ranked_key(columns[field].realization, group=True)
        for field in where[1]
    ):
        return False
    return all(
        function_name(value.source) in ORDERED_VALUE_FUNCTIONS
        and len(value.arguments) == 1
        and bool(value.order_by)
        and ranked_value(
            _ranked_read(plan, available, value.arguments[0], reference_type)
        )
        and all(
            ranked_key(_ranked_read(plan, available, ref, reference_type))
            for ref in value.order_by
        )
        for value in values
    )


def _non_null_int(value_type) -> bool:
    return (
        value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.resolved_type.name == "Int"
        and value_type.nullability is EffectiveNullability.NON_NULL
    )


def _plan_node(plan, ref):
    position = getattr(ref, "position", None)
    if type(position) is not int or not 0 <= position < len(plan.expressions):
        return None
    node = plan.expressions[position]
    return node if node.ref is ref else None


def _ranked_origin(plan):
    """The input port that a stage port reads, through stage ports."""
    through = {port.ref: port.source for port in plan.stage_ports}

    def origin(ref):
        for _ in range(len(through) + 1):
            if ref not in through:
                return ref
            ref = through[ref]
        return None

    return origin


def _ranked_tests(plan, ref):
    """The tests one `and` tree joins, in order, or None past another node."""
    node = _plan_node(plan, ref)
    if type(node) is not plan_expressions.ProjectSQLBinary:
        return (node,)
    if node.expression.operator != "and":
        return None
    left, right = _ranked_tests(plan, node.left), _ranked_tests(plan, node.right)
    return None if left is None or right is None else left + right


def _ranked_filter(plan, origin):
    """The WHERE of the qualification's class, by the input port each test
    reads: (the fields of its `f is not None` tests, each nullable, and of its
    `f == p` tests, each with a non-null Int header parameter), or None for
    any other test. No WHERE has neither."""
    tests = _ranked_tests(plan, plan.filters[0].predicate) if plan.filters else ()
    if tests is None:
        return None
    tested, compared = [], []
    for node in tests:
        if type(node) is plan_expressions.ProjectSQLIsNull:
            field = _plan_node(plan, node.value)
            if (
                not node.expression.negated
                or type(field) is not plan_expressions.ProjectSQLReference
                or field.value_type.nullability is not EffectiveNullability.NULLABLE
            ):
                return None
            tested.append(origin(field.port))
        elif type(node) is plan_expressions.ProjectSQLComparison:
            field = _plan_node(plan, node.left)
            parameter = _plan_node(plan, node.right)
            if (
                node.expression.operator != "=="
                or type(field) is not plan_expressions.ProjectSQLReference
                or type(parameter) is not plan_expressions.ProjectSQLParameterRead
                or not _non_null_int(parameter.value_type)
            ):
                return None
            compared.append(origin(field.port))
        else:
            return None
    return tested, compared


def ranked_statement(plan) -> bool:
    """Phase77 S13's whitelist of a whole MySQL statement, derived from the
    plan alone: the forms the qualification witnessed and nothing else. One
    query reads one source by its own name, through a WHERE at most, into one
    aggregation, GLOBAL or by one key, and a projection of its bare key and
    then its results, in order; a GROUP BY is ordered by its key ascending, a
    GLOBAL one is not ordered. Every `first` and `last` orders by one authored
    key list, field for field and direction for direction, as the
    qualification ranked each statement. The WHERE (`_ranked_filter`) tests
    each nullable order key of a `first` or `last` at most once for `is not
    None` and compares at most one field, the group key when there is one,
    with the one header parameter, which nothing else reads. The carriers are
    `ranked_inputs`'. False while emission derives as main (rows.AS_MAIN).
    O(1) unless the plan has one aggregation, then linear in the plan
    once."""
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
    )

    if (
        rows.AS_MAIN.get()
        or len(plan.aggregations) != 1
        or len(plan.input_uses) != 1
        or len(plan.blocks) not in {2, 3}
        or len(plan.filters) != len(plan.blocks) - 2
        or len(plan.aggregations[0].keys) > 1
        or any(
            (
                plan.joins,
                plan.captures,
                plan.expression_block_uses,
                plan.collects,
                plan.unnests,
                plan.set_bodies,
                plan.values_bodies,
                plan.windows,
                plan.let_values,
                plan.projections,
                plan.distincts,
                plan.result_limits,
                plan.literal_slots,
                plan.bind_uses,
            )
        )
    ):
        return False
    kinds = tuple(block.kind.value for block in plan.blocks)
    boundary = plan.blocks[0].boundary
    origin = _ranked_origin(plan)
    where = _ranked_filter(plan, origin)
    if (
        kinds not in {("aggregate", "projection"), ("where", "aggregate", "projection")}
        or type(boundary) is not ProjectSQLBoundary
        or boundary.reason is not ProjectSQLBoundaryReason.SOURCE_INPUT
        or where is None
        # A relation alias (`let x = rows`, `from x`) stays on the normalized
        # FROM only: compiled records and observations read as the source's.
        or any(
            type(item.entry.owner.definition) is QueryDef
            and item.entry.owner.definition.from_clause.binding_name is not None
            for item in plan.bindings.definitions
        )
    ):
        return False
    tested, compared = where
    # Each call's authored key list: (input port, else its own ref, direction).
    lists = set()
    for aggregate in plan.aggregates:
        authored = aggregation.aggregate_call(aggregate.source).aggregate_order_by
        lists.add(
            tuple(
                (
                    origin(node.port)
                    if type(node := _plan_node(plan, ref))
                    is plan_expressions.ProjectSQLReference
                    else ref,
                    item.direction or "asc",
                )
                for ref, item in zip(aggregate.order_by, authored, strict=True)
            )
        )
    keys = {field for fields in lists for field, _ in fields}
    if (
        len(lists) != 1
        or len(set(tested)) != len(tested)
        or not keys.issuperset(tested)
        or len(compared) > 1
        or len(compared) != len(plan.parameters)
    ):
        return False
    (stage,) = plan.aggregations
    sources = {port.ref: port.source for port in plan.result_ports}
    sources.update((item.ref, item.input) for item in plan.aggregate_projections)
    sources.update(
        (port.ref, port.source)
        for port in plan.stage_ports
        if port.kind.value == "input"
    )

    def source(ref):
        # Through result, projection and input stage ports, to a result.
        for _ in range(len(sources) + 1):
            if ref not in sources:
                return ref
            ref = sources[ref]
        return None

    # The projection reads every key, then every result, each once, in order.
    projected = [source(item.input) for item in plan.aggregate_projections]
    if len(projected) != len(stage.results) or any(
        read is not result for read, result in zip(projected, stage.results)
    ):
        return False
    if not stage.keys:
        return not plan.orders and not plan.order_items and not plan.order_uses
    if any(
        len(items) != 1
        for items in (plan.group_keys, plan.orders, plan.order_items, plan.order_uses)
    ):
        return False
    ((key,), (item,), (use,)) = (plan.group_keys, plan.order_items, plan.order_uses)
    return (
        item.source.direction.value == "asc"
        and len(use.ports) == 1
        and source(use.ports[0]) is key.result
        and all(field is origin(key.input) for field in compared)
    )


def ranked_layout(stage):
    """MySQL's ranked derived table for one aggregation stage: the columns its
    outer SELECT and GROUP BY read, each once, keys first, and one ROW_NUMBER
    name per `first` or `last`. MySQL compares column names character by
    character without case or accents, so `r<ordinal>` is lengthened by `_`
    past every read name that is not ASCII, then while it is an ASCII read
    name without case. Linear in the stage."""
    listed: dict[str, Any] = {}
    for column in stage.keys:
        listed.setdefault(column.read.name, column.read)
    ordered = tuple(
        column for column in stage.values if column.function in ORDERED_VALUE_FUNCTIONS
    )
    for column in ordered:
        listed.setdefault(column.argument.column.name, column.argument.column)
    folded = {name.casefold() for name in listed if name.isascii()}
    longest = max((len(name) for name in listed if not name.isascii()), default=0)
    ranks = []
    for column in ordered:
        name = f"r{column.ordinal}"
        name += "_" * max(0, longest + 1 - len(name))
        while name.casefold() in folded:
            name += "_"
        ranks.append((column, name))
    return tuple(listed.values()), tuple(ranks)


def ranked_body(family: str, stage) -> bool:
    """Whether a MySQL aggregation body renders its ranked derived table."""
    return (
        family == "mysql"
        and stage is not None
        and any(
            getattr(column, "function", None) in ORDERED_VALUE_FUNCTIONS
            for column in stage.values
        )
    )


def result_value(source):
    """The aggregate result's own retained logical tag and nullability."""
    value_type = aggregation.result_type(source)
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    nullable = VALUE_NULLABILITY.get(value_type.nullability)
    return None if nullable is None else (value_type.resolved_type.name, nullable)


def result_realization(family: str, function: str, argument, retained):
    """One aggregate result's independently established physical realization.

    A counting result is the target's own non-null signed64 count, bounded by
    R13's declared premise rather than by the argument's value range. MIN and MAX
    retain their argument's representation and only gain the possibility of NULL,
    because an empty or all-null input has no extreme value.
    """
    tag, nullable = retained
    if function in ORDERED_VALUE_FUNCTIONS:
        # The value at one row kept as it is: the argument's own carrier, NULL
        # where that value is or, without GROUP BY, for an empty input.
        carrier = None if argument is None else argument.realization
        if (
            family not in {"postgres", "mysql"}
            or carrier is None
            or family == "mysql"
            and not ranked_value(carrier)
            or tag != carrier.tag
            or nullable not in {True, False}
            or (carrier.nullable is not False and nullable is not True)
        ):
            return None, ("PIE-B1002", "first_last_result_logical_type_drift")
        return (
            rows.Realization(
                carrier.tag,
                carrier.storage,
                nullable,
                carrier.domain,
                carrier.proven_int_range,
                binding=carrier.binding,
            ),
            None,
        )
    if function == "string_agg":
        if (
            family != "postgres"
            or argument is None
            or tag != "Text"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "string_agg_result_logical_type_drift")
        return (
            rows.Realization(
                "Text",
                {"kind": "pg_text"},
                True,
                {
                    "kind": "text",
                    "max_characters": None,
                    "encoding": "UTF8",
                    "collation": "C",
                    "padding": "NO PAD",
                },
            ),
            None,
        )
    if function in GROUP_TEST_FUNCTIONS:
        # A count compared with 0: a computed Bool, never NULL.
        if family != "postgres" or tag != "Bool" or nullable is not False:
            return None, ("PIE-B1002", "group_test_result_not_non_null_bool")
        return rows._bool(family, False), None
    if function in FILTERED_FUNCTIONS:
        # A conditional count is the target's own count; a conditional sum
        # narrows to bigint with its checked CAST and is 0 for no match.
        if family != "postgres" or tag != "Int" or nullable is not False:
            return None, ("PIE-B1002", function + "_result_not_non_null_int")
        if function == "filtered_count":
            return (
                rows._checked_int({"kind": "pg_int8"}, 0, COUNT_MAX, False),
                None,
            )
        return rows._checked_int({"kind": "pg_int8"}, *rows.SIGNED64, False), None
    if function in COUNTING_FUNCTIONS:
        if tag != "Int" or nullable is not False:
            return None, ("PIE-B1002", "count_result_not_non_null_int")
        return (
            rows._checked_int({"kind": COUNT_STORAGE[family]}, 0, COUNT_MAX, False),
            None,
        )
    if function in {"sum", "avg"} and float_argument(argument):
        # PostgreSQL's float8 SUM and AVG accumulate in binary64 and raise
        # SQLSTATE 22003 on overflow; an empty or all-null input is NULL.
        if family != "postgres" or tag != "Float" or nullable is not True:
            return None, (
                "PIE-B1002",
                function + "_result_logical_type_or_argument_drift",
            )
        return (
            rows.Realization("Float", {"kind": "pg_float8"}, True, rows.FINITE_FLOAT),
            None,
        )
    if function == "sum":
        # An empty or all-null input sums to NULL; the CAST bounds the rest.
        if (
            family == "postgres"
            and argument is not None
            and argument.realization.tag == "Decimal"
            and tag == "Decimal"
            and nullable is True
        ):
            result = rows.decimal_sum_realization(family, argument.realization, True)
            if result is not None:
                return result, None
            return None, ("PIE-B1004", "decimal_aggregate_range_proof_missing")
        if (
            family != "postgres"
            or argument is None
            or argument.realization.tag != "Int"
            or tag != "Int"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "sum_result_logical_type_or_argument_drift")
        return rows._checked_int({"kind": "pg_int8"}, *rows.SIGNED64, True), None
    if function in SPREAD_FUNCTIONS:
        # A MySQL one (S05) is a DOUBLE of a DOUBLE argument.
        if (
            argument is None
            or tag != "Float"
            or nullable is not True
            or not (
                family == "postgres"
                and argument.realization.tag in {"Int", "Float"}
                or family == "mysql"
                and rows.float_carrier(argument.realization, family)
            )
        ):
            return None, (
                "PIE-B1002",
                function + "_result_logical_type_or_argument_drift",
            )
        return (
            rows.Realization(
                "Float",
                {"kind": "pg_float8" if family == "postgres" else "my_double"},
                True,
                rows.FINITE_FLOAT,
            ),
            None,
        )
    if function in QUANTILE_FUNCTIONS:
        # Between two float8 images of signed 64-bit values, NULL for no value.
        if (
            family != "postgres"
            or argument is None
            or argument.realization.tag != "Int"
            or tag != "Float"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "quantile_result_logical_type_or_argument_drift")
        return (
            rows.Realization("Float", {"kind": "pg_float8"}, True, rows.FINITE_FLOAT),
            None,
        )
    if function == "avg":
        if (
            argument is None
            or argument.realization.tag != "Int"
            or tag != "Float"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "avg_result_logical_type_or_argument_drift")
        return (
            rows.Realization(
                "Float",
                {"kind": "pg_float8" if family == "postgres" else "my_double"},
                True,
                {"kind": "finite_float", "format": "binary64"},
            ),
            None,
        )
    assert function in EXTREMA_FUNCTIONS
    carrier = argument.realization
    if tag != carrier.tag:
        return None, ("PIE-B1002", "extrema_result_logical_type_drift")
    if nullable is not True:
        return None, ("PIE-B1002", "extrema_result_must_admit_empty_input_null")
    return (
        rows.Realization(
            carrier.tag,
            carrier.storage,
            True,
            carrier.domain,
            carrier.proven_int_range,
            # An extreme of a binding-dependent value is fixed only by a binding.
            binding=carrier.binding,
        ),
        None,
    )


def rendered_direction(function: str, direction: str) -> tuple[str, str]:
    """The emitted spelling and syntax role of one authored internal order
    direction: `last` is the first element of the reversed order, so each of
    its directions is written flipped, under its own role."""
    if direction not in {"asc", "desc"}:
        raise ValueError("internal order direction")
    if function == "last":
        return (
            " DESC" if direction == "asc" else " ASC",
            "aggregate_order_reversed_direction",
        )
    return " ASC" if direction == "asc" else " DESC", "aggregate_order_direction"


def order_key_problem(function: str, family: str, realization):
    """A string_agg order key compares like a group key, a PostgreSQL Float
    included (E6); a `first` or `last` key orders like a relation ORDER BY key
    (R19)."""
    if function == "string_agg":
        return group_key_problem(realization)
    from pietto._project.project_sql_emission_results import order_admitted

    if family == "mysql":
        # Only the keys the S13 qualification ordered by (`ranked_key`).
        if ranked_key(realization):
            return None
        return "PIE-B1003", "first_last_not_admitted_on_target"
    if order_admitted(family, realization):
        return None
    return "PIE-B1003", "first_last_order_key_outside_reviewed_order_domain"


def float_argument(argument) -> bool:
    """Whether one realized aggregate argument is a Float carrier."""
    return argument is not None and argument.realization.tag == "Float"


def argument_problem(
    function: str, argument, family: str, *, cell: bool = False, ranked=False
):
    """R13 admits one established V01 field per aggregate argument, or one
    admitted row expression, as a LET would lower it. Any other
    argument, such as a bare literal or parameter or an operation that reads no
    field (only a forged compiled input holds one), reads no row and is refused.
    ``cell`` is the caller's own derivation of the S05 cell."""
    direct = type(argument) is rows.SQLStageReference
    if not direct and not (
        type(argument) is rows.SQLOperation
        and any(
            type(node) is rows.SQLStageReference for node in rows.value_nodes(argument)
        )
    ):
        return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
    return resolved_argument_problem(
        function, direct, argument.realization, family, cell=cell, ranked=ranked
    )


def rooted(family: str, function: str) -> bool:
    """Whether the rendering wraps the aggregate in SQRT( ... ): a PostgreSQL
    deviation, the root of its float8 variance."""
    return family == "postgres" and function in ROOT_FUNCTIONS


# Clauses and declarations of the emitted query that leave the S05 cell.
_SPREAD_CELL_CLAUSES = (
    "where_clause",
    "group_by_clause",
    "order_by_clause",
    "limit_clause",
    "satisfying_clause",
    "qualify_clause",
    "let_clause",
    "named_windows",
    "join_clauses",
    "distinct_clause",
    "naming_declarations",
    "join_filters",
)
# Plan inventories that each leave the S05 cell when they hold anything.
_SPREAD_CELL_EMPTY = (
    "parameters",
    "literal_slots",
    "bind_uses",
    "projections",
    "expression_block_uses",
    "captures",
    "let_values",
    "filters",
    "joins",
    "group_keys",
    "aggregate_risks",
    "windows",
    "result_boundaries",
    "distincts",
    "orders",
    "result_limits",
    "set_bodies",
    "values_bodies",
    "collects",
    "unnests",
)


def mysql_spread_cell(plan, aggregate, argument) -> bool:
    """Phase77 S05: whether one MySQL `stddev`, `variance`, `pvariance` or
    `pstdev` is in the one cell whose primitive (`SELECT STDDEV_SAMP(v) FROM
    t` over a nullable DOUBLE column) the raw qualification judged
    CANDIDATE_EMISSION_EXPERIMENT_READY, from the plan.

    The emitted query or table is the plan's only one, written as a plain
    query or table: it reads one source directly, with no `let` (a relation
    one included), clause, window, JOIN or header parameter, and
    selects exactly this aggregate of its one global aggregation, which has
    no key and no other value; the argument is a direct read of a field of
    that source. resolved_argument_problem checks the argument's carrier, a
    nullable MySQL DOUBLE. Every check before the bindings is O(1). No
    aggregate is in it while emission derives as main (rows.AS_MAIN)."""
    from pietto._project.project_sql_plan import (
        ProjectSQLBoundary,
        ProjectSQLBoundaryReason,
        ProjectSQLPlanRefKind,
    )
    from pietto._project.project_sql_plan_expressions import ProjectSQLStageKind

    from pietto._project.module_catalog import authored_definitions

    owner = plan.scope.selected_owner
    body = owner.definition
    module = plan.scope.completed.semantic_result.modules[owner.module_position]
    # Normalization drops each relation `let` (`let x = agg`, read through
    # `from x` or not) from the definition; only the authored one keeps it.
    # An authored block form (`let x:`) has no such field: it leaves too.
    authored = authored_definitions(module)[owner.declaration_position]
    if (
        rows.AS_MAIN.get()
        or type(body) not in {QueryDef, TableDef}
        or getattr(authored, "naming_declarations", None) != ()
        or any(getattr(plan, name) for name in _SPREAD_CELL_EMPTY)
        or any(getattr(body, name, ()) for name in _SPREAD_CELL_CLAUSES)
        or len(body.select_items) != 1
        or len(plan.blocks) != 2
        or len(plan.input_uses) != 1
        or len(plan.exports) != 1
        or len(plan.aggregations) != 1
        or len(plan.aggregates) != 1
        or plan.aggregates[0] is not aggregate
        or len(plan.aggregate_projections) != 1
        or type(argument) is not rows.SQLStageReference
    ):
        return False
    first, last = plan.blocks
    stage = plan.aggregations[0]
    definitions = tuple(
        item
        for item in plan.bindings.definitions
        if type(item.entry.owner.definition) is not SourceDef
    )
    column = argument.column
    return (
        len(definitions) == 1
        and definitions[0].entry.owner is owner
        and first.definition is last.definition is stage.definition
        and first.definition is definitions[0].ref
        and first.kind is ProjectSQLStageKind.AGGREGATE
        and last.kind is ProjectSQLStageKind.PROJECTION
        and stage.block is first.ref
        and type(first.boundary) is ProjectSQLBoundary
        and first.boundary.reason is ProjectSQLBoundaryReason.SOURCE_INPUT
        and first.boundary.use is plan.input_uses[0]
        and stage.mode is ProjectJoinedAggregationMode.GLOBAL
        and stage.aggregates == (aggregate.ref,)
        and not stage.keys
        and getattr(column.terminal, "kind", None) is ProjectSQLPlanRefKind.SOURCE_PORT
        and column.field is not None
        and column.source_port is not None
        and column.literal is None
        and column.aggregate is None
        and column.window is None
    )


def mysql_compiled_spread_cell(records, entry):
    """Compiled replay's mysql_spread_cell, from the records alone: the one
    `aggregate_value` address in the cell, or None.

    The entry requests and retains nothing, and its one export is the
    output of its terminal, a projection row of its declaration without a
    predicate, whose one value reads, through the row's own use, the one
    output of a global aggregate of the same declaration with no key; that
    aggregate reads a source through its own use, and its one value is a
    variance or deviation without an order whose one argument reads a port
    of that source through that use, and the bundle has no header parameter
    record. Every check is O(1). A relation `let` (`let x = t`, read through
    `from x` or not) leaves no record of its own, so these records cannot
    refuse one; the emitter and the live verifier refuse it from the
    authored declaration."""
    from pietto._project.project_compiled_schema import Address

    owner = entry.get("declaration")
    terminal = records.get(entry.get("terminal"))
    if (
        entry.get("requests") != ()
        or entry.get("retained") != ()
        or terminal is None
        or terminal.address.kind != "row"
        or entry.get("exports") != terminal.get("outputs")
        or len(terminal.get("outputs")) != 1
        or terminal.get("stage") != "projection"
        or terminal.get("owner") != owner
        or terminal.get("predicate") is not None
        or len(terminal.get("values")) != 1
        or terminal.get("input").kind != "aggregate"
    ):
        return None
    stage = records[terminal.get("input")]
    selected, source = terminal.get("values")[0], stage.get("input")
    if (
        stage.get("owner") != owner
        or stage.get("mode") != "global"
        or stage.get("keys") != ()
        or len(stage.get("values")) != 1
        or len(stage.get("outputs")) != 1
        or source.kind != "source"
        or selected.kind != "read"
        or records[selected].get("port") != stage.get("outputs")[0]
        or records[selected].get("use") != terminal.get("use")
        or records[terminal.get("use")].get("producer") != stage.address
        or records[stage.get("use")].get("producer") != source
    ):
        return None
    value = records[stage.get("values")[0]]
    arguments = value.get("arguments")
    if (
        value.address.kind != "aggregate_value"
        or value.get("function") not in SPREAD_FUNCTIONS
        or value.get("order_by") != ()
        or len(arguments) != 1
        or arguments[0].kind != "read"
    ):
        return None
    read = records[arguments[0]]
    if (
        read.get("use") != stage.get("use")
        or read.get("role") != "value"
        or records[read.get("port")].get("owner") != source
    ):
        return None
    # Any header parameter record, read or not, leaves the cell.
    if Address("parameter", 0) in records:
        return None
    return value.address


def filtered_problem(function: str, argument, test, family: str):
    """The argument law of a conditional count, ``filtered_count`` over its
    test alone, of a test of the group, ``group_any`` or ``group_all`` over
    its test alone, and of a conditional sum, ``filtered_sum`` of one Int field
    over its test: each a row value that reads a field, the test a Bool.
    A test that reads no field (`if True`) is the same for every row.
    PostgreSQL only: MySQL has no conditional count or test of a group yet,
    and its SUM of an integer is DECIMAL, as for `sum(Int)`."""
    for value in (argument, test):
        if type(value) is not rows.SQLStageReference and not (
            type(value) is rows.SQLOperation
            and any(
                type(node) is rows.SQLStageReference for node in rows.value_nodes(value)
            )
        ):
            return "PIE-B1003", (
                "aggregate_argument_not_a_direct_established_field"
                if value is not test
                else "group_test_reads_no_field"
                if function in GROUP_TEST_FUNCTIONS
                else "conditional_test_reads_no_field"
            )
    if function == "filtered_sum":
        if type(argument) is not rows.SQLStageReference:
            return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
        problem = resolved_argument_problem("sum", True, argument.realization, family)
        if problem is not None:
            return problem
    elif family != "postgres":
        return "PIE-B1003", _target_detail(function)
    if family != "postgres" or rows.realization_of(test, family).tag != "Bool":
        return "PIE-B1003", _domain_detail(function)
    return None


def _target_detail(function: str) -> str:
    return (
        "group_test_not_admitted_on_target"
        if function in GROUP_TEST_FUNCTIONS
        else "conditional_count_not_admitted_on_target"
    )


def _domain_detail(function: str) -> str:
    return (
        "group_test_argument_outside_reviewed_bool_domain"
        if function in GROUP_TEST_FUNCTIONS
        else function + "_argument_outside_reviewed_int_domain"
    )


def resolved_filtered_problem(function: str, inputs, family: str):
    """`filtered_problem` over already-resolved inputs, each an (address
    kind, realization) pair, as a compiled input holds them."""
    if len(inputs) != (2 if function == "filtered_sum" else 1) or any(
        kind not in {"read", "operation"} for kind, _ in inputs
    ):
        return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
    if function == "filtered_sum":
        kind, realization = inputs[0]
        if kind != "read":
            return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
        problem = resolved_argument_problem("sum", True, realization, family)
        if problem is not None:
            return problem
    elif family != "postgres":
        return "PIE-B1003", _target_detail(function)
    test = inputs[-1][1]
    if family != "postgres" or test is None or test.tag != "Bool":
        return "PIE-B1003", _domain_detail(function)
    return None


def signature_arity(function: str, count: int) -> bool:
    """Whether an aggregate takes this many argument values: a `string_agg`,
    a `quantile` or a conditional sum two, a conditional count or a test of
    the group one, a distinct-tuple count two or more, any other at most one."""
    if function == "count_distinct_tuple":
        return count > 1
    if function in {"string_agg", "quantile", "filtered_sum"}:
        return count == 2
    if function in {"filtered_count", "group_any", "group_all"}:
        return count == 1
    return count <= 1


def string_agg_argument_problem(argument):
    """Require the reviewed PostgreSQL Text profile without a width fiction."""
    realization = (
        argument
        if type(argument) is rows.Realization
        else rows.realization_of(argument, "postgres")
    )
    if (
        realization.tag != "Text"
        or realization.storage != {"kind": "pg_text"}
        or tuple(realization.domain.get(key) for key in TEXT_DOMAIN_KEYS)
        != ("UTF8", "C", "NO PAD")
    ):
        return "PIE-B1003", "string_agg_argument_requires_postgres_text"
    return None


def resolved_argument_problem(
    function: str,
    direct_reference: bool,
    realization,
    family: str,
    *,
    cell: bool = False,
    ranked=False,
):
    """The same R13 argument law for an already-resolved input port.

    MIN/MAX of one Timestamp or Date carrier keep its exact value and type on
    both targets (MySQL: DATETIME(6) or DATE, microseconds kept).
    Both targets count and compare a Text, Bool, Float or Decimal carrier by
    the group-key law, as COUNT(DISTINCT x), MIN and MAX compare like GROUP BY,
    except a MySQL Float (`mysql_float_argument_problem`).
    A port that is not a direct reference is a row operation, judged by its
    carrier as a direct one is: each caller refuses any other argument first.
    ``cell`` is the caller's own derivation of the S05 cell."""
    if function == "count_distinct_tuple":
        # Each field of a PostgreSQL distinct-tuple count is an established
        # direct field that `count_distinct(x)` counts, compared field by field
        # in an anonymous record with that type's equality.
        if family != "postgres":
            return "PIE-B1003", "count_distinct_tuple_not_admitted_on_target"
        if not direct_reference:
            return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
        function = "count_distinct"
    if function in ORDERED_VALUE_FUNCTIONS:
        # ARRAY_AGG keeps one row's value of any admitted carrier exactly;
        # MySQL's ranked MAX(CASE ...) only a qualified one, in a statement
        # its caller found `ranked` (Phase77 S13).
        if family != "postgres" and not (
            family == "mysql" and ranked and ranked_value(realization)
        ):
            return "PIE-B1003", "first_last_not_admitted_on_target"
        if not direct_reference or realization is None:
            return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
        return None
    if realization is None:
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function == "avg" and realization.tag == "Int":
        if rows.proven_int_bounds(realization) is None:
            return "PIE-B1004", "avg_int_range_evidence_missing"
        return None
    if function in SPREAD_FUNCTIONS:
        # PostgreSQL VAR_SAMP and VAR_POP of any signed 64-bit integer are
        # numeric below 2^128, so their float8 cast is finite; of a finite
        # double they raise SQLSTATE 22003 on overflow. MySQL computes BIGINT
        # in DOUBLE.
        if realization.tag == "Int":
            if family == "postgres" and realization.storage.get("kind") in {
                "pg_int2",
                "pg_int4",
                "pg_int8",
            }:
                return None
            return "PIE-B1003", function + "_int_not_admitted_on_target"
        if realization.tag == "Float":
            if family == "postgres" and rows.float_carrier(realization, family):
                return None
            # MySQL raised 22003 (1690) for each overflowing Float variance
            # and deviation the raw qualification ran, over one direct
            # nullable DOUBLE field, and only in that cell.
            if (
                family == "mysql"
                and cell
                and direct_reference
                and rows.float_carrier(realization, family)
                and realization.nullable is True
            ):
                return None
            return "PIE-B1004", "float_aggregate_finite_result_proof_missing"
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function in QUANTILE_FUNCTIONS:
        # PostgreSQL PERCENTILE_CONT interpolates float8 images: of signed
        # 64-bit values it stays finite, but between two finite Floats more
        # than the largest float8 apart it returns an infinity unchecked.
        # MySQL has no interpolated percentile.
        if family != "postgres":
            return "PIE-B1003", "quantile_not_admitted_on_target"
        if realization.tag == "Int" and realization.storage.get("kind") in {
            "pg_int2",
            "pg_int4",
            "pg_int8",
        }:
            return None
        if realization.tag == "Float":
            return "PIE-B1004", "float_aggregate_finite_result_proof_missing"
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function == "sum" and realization.tag == "Int":
        # PostgreSQL sums exactly and narrows to bigint with its checked CAST;
        # MySQL's CAST(DECIMAL AS SIGNED) would clamp an out-of-range sum.
        if family == "postgres":
            return None
        return "PIE-B1004", "sum_int_aggregate_range_proof_missing"
    if function == "sum" and realization.tag == "Decimal":
        if (
            direct_reference
            and rows.decimal_sum_realization(family, realization, True) is not None
        ):
            return None
        return "PIE-B1004", "decimal_aggregate_range_proof_missing"
    # Only a sum or an average has a range or finite-result proof to supply;
    # any other function outside the reviewed Int domain is refused below.
    if function in {"sum", "avg"} and realization.tag == "Decimal":
        return "PIE-B1004", "decimal_aggregate_range_proof_missing"
    if function in {"sum", "avg"} and realization.tag == "Float":
        if family == "postgres" and rows.float_carrier(realization, family):
            return None
        return "PIE-B1004", "float_aggregate_finite_result_proof_missing"
    if (
        function in COUNTING_FUNCTIONS
        and realization.tag in {"Text", "Bool", "Float", "Decimal"}
        or function in EXTREMA_FUNCTIONS
        and realization.tag in {"Float", "Decimal"}
    ):
        if family == "mysql" and realization.tag == "Float":
            return mysql_float_argument_problem(function, realization)
        return group_key_problem(realization, distribution=False)
    if function in COUNTING_FUNCTIONS and realization.tag in {
        "Timestamp",
        "Date",
        "UUID",
    }:
        return grouping_problem(realization)
    if function in EXTREMA_FUNCTIONS and realization.tag in {"Timestamp", "Date"}:
        return grouping_problem(realization)
    if realization.tag != "Int":
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function in {"count", "count_distinct", "min", "max"}:
        return None
    return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"


def mysql_float_argument_problem(function: str, realization):
    """COUNT reads no value, and MIN and MAX compare DOUBLE values by real
    value, so -0.0 and 0.0 tie and the extreme is some member, as on
    PostgreSQL. COUNT(DISTINCT) deduplicates, and MySQL kept -0.0 and 0.0
    apart in deduplication beside a wide key, so it stays refused."""
    if function != "count_distinct" and rows.float_carrier(realization, "mysql"):
        return None
    return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"


def argument_cast(family: str, function: str, argument) -> str | None:
    """One target-native binary64 input for the reviewed AVG(Int) operation,
    or the bigint input of a PostgreSQL SUM(Int) or the float8 order of a
    PostgreSQL PERCENTILE_CONT; a PostgreSQL float8 SUM or AVG input is
    already binary64."""
    if function in QUANTILE_FUNCTIONS:
        if family != "postgres" or argument is None:
            raise ValueError(
                "PERCENTILE_CONT input cast requires a PostgreSQL argument"
            )
        return "pg_catalog.float8"
    if function == "filtered_sum":
        function = "sum"
    if function not in {"avg", "sum"}:
        return None
    if family == "postgres" and float_argument(argument):
        return None
    if argument is None:
        raise ValueError("AVG or SUM input cast requires its proven Int argument")
    if argument.realization.tag == "Decimal" and function == "sum":
        return None
    if argument.realization.tag != "Int":
        raise ValueError("AVG or SUM input cast requires its proven Int argument")
    if function == "sum":
        return result_cast(family, function, argument)
    return "pg_catalog.float8" if family == "postgres" else "DOUBLE"


def result_cast(family: str, function: str, argument) -> str | None:
    """Q1: PostgreSQL SUM(Int) accumulates exactly and its result is narrowed
    to bigint by a checked CAST, which refuses an out-of-range sum with
    SQLSTATE 22003 instead of returning a wrong value. A PostgreSQL VAR_SAMP
    or VAR_POP is cast to float8 once, under the fixed SQRT of a deviation; a
    MySQL variance or deviation of a DOUBLE (S05) is not cast."""
    if function in SPREAD_FUNCTIONS:
        if family == "postgres" and argument is not None:
            return "pg_catalog.float8"
        if family == "mysql" and float_argument(argument):
            return None
        raise ValueError("variance result cast requires its admitted argument")
    if function == "filtered_sum":
        function = "sum"
    if function != "sum" or family == "postgres" and float_argument(argument):
        return None
    if family != "postgres" or argument is None:
        raise ValueError("SUM result cast requires a PostgreSQL Int argument")
    if argument.realization.tag == "Decimal":
        result = rows.decimal_sum_realization(family, argument.realization, True)
        if result is None:
            raise ValueError("SUM result cast requires a qualified PostgreSQL Decimal")
        return "pg_catalog.numeric(%d, %d)" % (
            result.storage["precision"],
            result.storage["scale"],
        )
    if argument.realization.tag != "Int":
        raise ValueError("SUM result cast requires a PostgreSQL Int argument")
    return "pg_catalog.int8"


def aggregate_evidence(function: str, argument_tag: str | None) -> tuple[str, ...]:
    """R13's evidence beyond the rule, from the function and its argument's
    tag: a checked bigint sum, or a binary64 sum, average, variance or
    deviation the target checks."""
    if function in {"sum", "filtered_sum"} and argument_tag == "Int":
        return (rows.TARGET_CHECKED_SIGNED64,)
    if function == "sum" and argument_tag == "Decimal":
        return (rows.TARGET_CHECKED_DECIMAL,)
    if function in {"sum", "avg", *SPREAD_FUNCTIONS} and argument_tag == "Float":
        return (TARGET_CHECKED_BINARY64,)
    return ()


def _input_terminals(value) -> tuple[Any, ...]:
    """Preserve each established pre-aggregate input occurrence in source order."""
    return tuple(
        node.column.terminal
        for node in rows.value_nodes(value)
        if type(node) is rows.SQLStageReference
    )


def unsupported_function(function: str | None):
    """The exact typed blocker one non-promised aggregate keeps, in place."""
    if function in {"sum", "avg"}:
        return (
            "PIE-B1003",
            "sum_avg_result_realization_rule_not_reviewed_in_phase66",
        )
    return "PIE-B1003", "aggregate_function_not_promised_in_slice8"


def demand_rule(entry) -> str | None:
    """Rule attribution for the retained aggregation demand families."""
    if entry.family.value != "aggregation":
        return None
    return DEMAND_RULES.get(entry.subject.kind.value, "R12")


def node_count(stage: AggregateStage, value_nodes) -> int:
    """This stage's own generated nodes: each determinant and each occurrence;
    a nested determinant is one per carrier."""
    total = sum(len(getattr(key, "carriers", (None,))) for key in stage.keys)
    for value in stage.values:
        total += 1
        if value.argument is not None:
            total += value_nodes(value.argument)
        if value.delimiter is not None:
            total += value_nodes(value.delimiter)
        total += sum(value_nodes(extra) for extra in value.extra_arguments)
        total += sum(value_nodes(order.value) for order in value.order_by)
    return total


def blocks_admitted(plan, *, single_input_use: bool = False) -> bool:
    """Every definition's stage schedule and every retained aggregation binding."""
    stages = aggregated_definitions(plan)
    if len(stages) != len(plan.aggregations):
        return False
    # A SET definition owns no stage block and one input use per operand; its
    # own admission belongs to the SET owner.
    sets = {body.definition for body in plan.set_bodies} | {
        body.definition for body in plan.values_bodies
    }
    # An Unnest is realized by its exact JOIN input, not a separate stage body.
    sets |= {value.definition for value in plan.unnests}
    named = tuple(
        item
        for item in plan.bindings.definitions
        if type(item.entry.owner.definition) is not SourceDef and item.ref not in sets
    )
    blocks_by_definition: dict[Any, list[Any]] = {}
    for block in plan.blocks:
        blocks_by_definition.setdefault(block.definition, []).append(block)
    if set(blocks_by_definition) != {item.ref for item in named}:
        return False
    if any(
        risk.aggregation not in {s.ref for s in plan.aggregations}
        for risk in plan.aggregate_risks
    ):
        return False
    joined = {join.definition for join in plan.joins}
    keys = _grouped(plan.group_keys, "aggregation")
    values = _grouped(plan.aggregates, "aggregation")
    projections = _grouped(plan.aggregate_projections, "block")
    scalar_projections = _grouped(plan.projections, "block")
    for definition in named:
        blocks = sorted(blocks_by_definition[definition.ref], key=lambda b: b.position)
        kinds = tuple(block.kind.value for block in blocks)
        windowed = "window" in kinds
        stage = stages.get(definition.ref)
        if (
            not stage_schedule_valid(
                kinds, aggregated=stage is not None, windowed=windowed
            )
            or tuple(block.position for block in blocks) != tuple(range(len(blocks)))
            or (
                single_input_use
                and sum(use.consumer is definition.ref for use in plan.input_uses) != 1
            )
        ):
            return False
        for position, block in enumerate(blocks):
            # A joined definition reads its own JOIN tail, so only an ordinary
            # first stage declares the relation input operator.
            expected = (
                ("relation_input",)
                if position == 0 and definition.ref not in joined
                else ()
            )
            operators = OPERATORS.get(block.kind.value)
            if operators is None:
                return False
            expected += operators
            if tuple(item.kind.value for item in block.operators) != expected:
                return False
        if stage is None:
            if projections.get(blocks[-1].ref):
                return False
            continue
        if not _stage_bound(stage, blocks[kinds.index("aggregate")], keys, values):
            return False
        items = projections.get(blocks[-1].ref, ())
        # A windowed body's visible projection mixes this aggregation's results
        # with its own window results, so each aggregate projection is checked
        # against the export it actually claims rather than by position.
        claimed = {item.export: item for item in items}
        if len(claimed) != len(items) or any(
            item.aggregation is not stage.ref for item in items
        ):
            return False
        scalar_items = scalar_projections.get(blocks[-1].ref, ())
        for item in scalar_items:
            if item.export in claimed:
                return False
            claimed[item.export] = item
        if not windowed and (
            len(claimed) != len(definition.exports)
            or any(export.ref not in claimed for export in definition.exports)
        ):
            return False
    return True


def _grouped(items, attribute: str) -> dict[Any, list[Any]]:
    result: dict[Any, list[Any]] = {}
    for item in items:
        result.setdefault(getattr(item, attribute), []).append(item)
    return result


def _stage_bound(stage, block, keys, values) -> bool:
    """One aggregation's complete ordered determinants, occurrences and ports."""
    ordered_keys = sorted(keys.get(stage.ref, ()), key=lambda item: item.position)
    ordered_values = sorted(values.get(stage.ref, ()), key=lambda item: item.position)
    grouped = stage.mode is ProjectJoinedAggregationMode.GROUPED
    return not (
        stage.block is not block.ref
        or tuple(block.inputs) != tuple(stage.inputs)
        or tuple(block.exports) != tuple(stage.results)
        or tuple(item.position for item in ordered_keys)
        != tuple(range(len(ordered_keys)))
        or tuple(item.position for item in ordered_values)
        != tuple(range(len(ordered_values)))
        or tuple(item.ref for item in ordered_keys) != tuple(stage.keys)
        or tuple(item.ref for item in ordered_values) != tuple(stage.aggregates)
        or tuple(stage.results)
        != (
            *(item.result for item in ordered_keys),
            *(item.result for item in ordered_values),
        )
        or grouped is not bool(ordered_keys)
        or not ordered_values
        or stage.empty_input.value != ("no_groups" if grouped else "one_global_row")
        or stage.mode
        not in {
            ProjectJoinedAggregationMode.GROUPED,
            ProjectJoinedAggregationMode.GLOBAL,
        }
    )


def build_stage(
    request,
    stage,
    exports,
    available,
    keys,
    values,
    uses,
    *,
    reference_type,
    symbol,
    ranked=False,
):
    """Realize one aggregation: its ordered determinants and its occurrences,
    or every problem refusing it: a determinant's first, or each occurrence's.
    `ranked` is a MySQL statement `ranked_statement` admits; it stays ranked
    only when every key and every `first` or `last` reads a qualified carrier
    (`ranked_inputs`), else each refusal is the one before Phase77 S13.

    Every determinant binds the actual pre-aggregate input it already has a port
    for, and every occurrence keeps its own distinct result column even when two
    declarations spell the same aggregate over the same field.
    """
    family = request.family
    ranked = ranked and ranked_inputs(
        request.plan, available, keys, values, reference_type
    )
    columns: list[Any] = []
    key_columns: list[Any] = []
    value_columns: list[AggregateValueColumn] = []
    for index, key in enumerate(keys):
        read = available.get(key.input)
        export = exports[index]
        if read is None:
            return (
                None,
                None,
                (
                    (
                        "PIE-B1001",
                        "group_key_outside_pre_aggregate_input",
                        key.ref,
                        None,
                    ),
                ),
            )
        if export.source is not key.ref:
            return (
                None,
                None,
                (("PIE-B1001", "group_key_result_port_drift", key.ref, None),),
            )
        if type(read) is unnesting.NestedRead:
            # A nested key (D73.05) groups by its count and every child array:
            # PostgreSQL compares array elements by their decoded values.
            if family != "postgres":
                return (
                    None,
                    None,
                    (
                        (
                            "PIE-B1003",
                            "group_key_type_not_admitted",
                            key.ref,
                            getattr(getattr(key.source, "item", None), "span", None),
                        ),
                    ),
                )
            group = collecting.carry_group(
                read, export=export, position=index, final=False, terminal=export
            )
            columns.append(group)
            key_columns.append(group)
            continue
        retained = key_logical(key.source)
        if retained is None:
            return (
                None,
                None,
                (
                    (
                        "PIE-B1004",
                        "group_key_logical_type_evidence_missing",
                        key.ref,
                        None,
                    ),
                ),
            )
        if (read.realization.tag, read.realization.nullable) != retained:
            return (
                None,
                None,
                (("PIE-B1002", "group_key_logical_type_or_null_drift", key.ref, None),),
            )
        problem = group_key_problem(
            read.realization,
            float_key_cell=rows.mysql_float_key_admitted(request, read.realization),
        )
        if problem is not None:
            item = getattr(key.source, "item", None)
            return None, None, ((*problem, key.ref, getattr(item, "span", None)),)
        label = f"c{index}"
        column = AggregateKeyColumn(
            index,
            export,
            key,
            key.input,
            read,
            symbol(index + 1, export.ref, label),
            label,
            replace(
                read,
                position=index,
                name=label,
                terminal=export.ref,
                scope=None,
                aggregate=AggregateOrigin(
                    "group_key", stage, export.ref, (read.terminal,), key=key
                ),
            ),
        )
        columns.append(column)
        key_columns.append(column)

    def value_column(offset, value):
        """One occurrence's column, or the first problem refusing it."""
        index = len(keys) + offset
        export = exports[index]
        if export.source is not value.ref:
            return (
                None,
                ("PIE-B1001", "aggregate_result_port_drift", value.ref, None),
            )
        function = function_name(value.source)
        location = value.source.item.span
        arguments = aggregation.arguments(value.source)
        if function == "count_distinct" and len(arguments) > 1:
            function = "count_distinct_tuple"
        if function is None or function not in SPELLING:
            return None, (*unsupported_function(function), value.ref, location)
        ordered = aggregation.aggregate_call(value.source).aggregate_order_by
        if (
            len(arguments) != len(value.arguments)
            or len(ordered) != len(value.order_by)
            or (function in ORDERED_FUNCTIONS) is not bool(ordered)
            or not signature_arity(function, len(arguments))
        ):
            return (
                None,
                (
                    "PIE-B1003",
                    "aggregate_argument_signature_not_admitted",
                    value.ref,
                    location,
                ),
            )
        argument = None
        delimiter = None
        extra_arguments = ()
        if function == "count_distinct_tuple":
            if family != "postgres":
                return (
                    None,
                    (
                        "PIE-B1003",
                        "count_distinct_tuple_not_admitted_on_target",
                        value.ref,
                        location,
                    ),
                )
            realized = []
            for argument_ref in value.arguments:
                current, problem = rows.build_row_value(
                    request,
                    available,
                    argument_ref,
                    uses,
                    reference_type=reference_type,
                )
                if current is None:
                    assert problem is not None
                    return None, (*problem, value.ref, location)
                problem = argument_problem(function, current, family)
                if problem is not None:
                    return None, (*problem, value.ref, location)
                realized.append(current)
            argument, *rest = realized
            extra_arguments = tuple(rest)
        elif function == "string_agg":
            if family != "postgres":
                return (
                    None,
                    (*unsupported_function(function), value.ref, location),
                )
            realized = []
            for argument_ref in value.arguments:
                current, problem = rows.build_row_value(
                    request,
                    available,
                    argument_ref,
                    uses,
                    reference_type=reference_type,
                )
                if current is None:
                    assert problem is not None
                    return None, (*problem, value.ref, location)
                problem = string_agg_argument_problem(current)
                if problem is not None:
                    return None, (*problem, value.ref, location)
                realized.append(current)
            argument, delimiter = realized
        elif value.arguments:
            argument, problem = rows.build_row_value(
                request,
                available,
                value.arguments[0],
                uses,
                reference_type=reference_type,
            )
            if argument is None:
                assert problem is not None
                return None, (*problem, value.ref, location)
            if function in FILTERED_FUNCTIONS:
                test = argument
                if function == "filtered_sum":
                    test, problem = rows.build_row_value(
                        request,
                        available,
                        value.arguments[1],
                        uses,
                        reference_type=reference_type,
                    )
                    if test is None:
                        assert problem is not None
                        return None, (*problem, value.ref, location)
                    delimiter = test
                problem = filtered_problem(function, argument, test, request.family)
            else:
                problem = argument_problem(
                    function,
                    argument,
                    request.family,
                    cell=family == "mysql"
                    and function in SPREAD_FUNCTIONS
                    and mysql_spread_cell(request.plan, value, argument),
                    ranked=ranked,
                )
            if problem is not None:
                return None, (*problem, value.ref, location)
            if function == "quantile":
                # Its fraction, a Float literal from 0.0 to 1.0, reads no row.
                delimiter, problem = rows.build_row_value(
                    request,
                    available,
                    value.arguments[1],
                    uses,
                    reference_type=reference_type,
                )
                if delimiter is None:
                    assert problem is not None
                    return None, (*problem, value.ref, location)
                if (
                    _input_terminals(delimiter)
                    or rows.realization_of(delimiter, family).tag != "Float"
                ):
                    return (
                        None,
                        (
                            "PIE-B1003",
                            "aggregate_argument_signature_not_admitted",
                            value.ref,
                            location,
                        ),
                    )
        elif function != "count":
            return (
                None,
                (
                    "PIE-B1003",
                    "aggregate_requires_its_authored_argument",
                    value.ref,
                    location,
                ),
            )
        orders = []
        for item, order_ref in zip(ordered, value.order_by, strict=True):
            current, problem = rows.build_row_value(
                request,
                available,
                order_ref,
                uses,
                reference_type=reference_type,
            )
            if current is None:
                assert problem is not None
                return None, (*problem, value.ref, location)
            problem = order_key_problem(
                function, family, rows.realization_of(current, family)
            )
            if problem is not None:
                return None, (*problem, value.ref, location)
            orders.append(
                AggregateOrderItem(
                    current, "asc" if item.direction is None else item.direction
                )
            )
        order_by = tuple(orders)
        retained = result_value(value.source)
        if retained is None:
            return (
                None,
                (
                    "PIE-B1004",
                    "aggregate_result_logical_type_evidence_missing",
                    value.ref,
                    location,
                ),
            )
        realization, problem = result_realization(family, function, argument, retained)
        if realization is None:
            assert problem is not None
            return None, (*problem, value.ref, location)
        label = f"c{index}"
        column = AggregateValueColumn(
            index,
            export,
            value,
            function,
            spelling(family, function),
            function in DISTINCT_FUNCTIONS,
            argument_cast(family, function, argument),
            argument,
            symbol(index + 1, export.ref, label),
            label,
            rows.StageColumn(
                index,
                label,
                export.ref,
                realization,
                aggregate=AggregateOrigin(
                    "aggregate_result",
                    stage,
                    export.ref,
                    # A row count has no scalar argument and still consumes the
                    # complete input BAG, so its dependency is that whole input.
                    tuple(
                        terminal
                        for current in (argument, delimiter, *extra_arguments)
                        if current is not None
                        for terminal in _input_terminals(current)
                    )
                    + tuple(
                        terminal
                        for order in order_by
                        for terminal in _input_terminals(order.value)
                    )
                    if argument is not None
                    else tuple(
                        item.group.column.terminal
                        if type(item) is unnesting.NestedRead
                        else item.terminal
                        for item in available.values()
                    ),
                    aggregate=value,
                    function=function,
                ),
            ),
            delimiter,
            order_by,
            result_cast(family, function, argument),
            extra_arguments,
        )
        return column, None

    problems = []
    for offset, value in enumerate(values):
        column, problem = value_column(offset, value)
        if column is None:
            problems.append(problem)
            continue
        columns.append(column)
        value_columns.append(column)
    if problems:
        # Each occurrence is refused at its own place, in select order.
        return None, None, tuple(problems)
    if len(columns) != len(exports):
        return (
            None,
            None,
            (("PIE-B1001", "aggregate_result_denominator", stage.ref, None),),
        )
    return (
        tuple(columns),
        AggregateStage(
            stage,
            tuple(key_columns),
            tuple(value_columns),
            stage.mode.value,
            stage.empty_input.value,
        ),
        None,
    )


def build_projections(
    request, stage, block, exports, terminals, available, projections, final, *, symbol
):
    """Realize the exact visible projection of one aggregation's result ports."""
    columns: list[Any] = []
    if len(projections) != len(exports) or len(terminals) != len(exports):
        return None, ("PIE-B1001", "aggregate_projection_denominator", block.ref, None)
    for position, (projection, export, terminal) in enumerate(
        zip(projections, exports, terminals, strict=True)
    ):
        if (
            projection.block is not block.ref
            or projection.aggregation is not stage.ref
            or projection.export is not export.ref
        ):
            return None, (
                "PIE-B1001",
                "aggregate_projection_drift",
                projection.ref,
                None,
            )
        read = available.get(projection.input)
        if read is None:
            return None, (
                "PIE-B1001",
                "aggregate_projection_outside_result_scope",
                projection.ref,
                None,
            )
        if type(read) is unnesting.NestedRead:
            columns.append(
                collecting.carry_group(
                    read,
                    export=export,
                    position=position,
                    final=final,
                    terminal=terminal,
                )
            )
            continue
        label = export.identity.name if final else f"c{position}"
        columns.append(
            AggregateProjectionColumn(
                position,
                export,
                projection,
                projection.input,
                read,
                symbol(position + 1, export.ref, label),
                label,
                replace(read, position=position, name=label, terminal=terminal.ref),
            )
        )
    return tuple(columns), None


def plan_projection_type():
    """The retained aggregate projection type, for exact dispatch by identity."""

    return aggregation.ProjectSQLAggregateProjection


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregateSubject:
    ref: Any


# Compiled units, each a record of one of these kinds: a ranked statement has
# a WHERE row at most, one aggregate, its projection row and, by a key, its
# ordered result, and no other unit or relation read.
_RANKED_UNIT_RECORDS = frozenset(
    {
        "scan",
        "row",
        "join",
        "window",
        "aggregate",
        "result",
        "set",
        "values",
        "table_function",
        "unnest",
        "expression_block_use",
        "capture_use",
        "any_filter",
        "any_value",
        "predicate_call",
        "match_use",
        "slot",
    }
)


def _compiled_reads(records, addresses, consumer, ports=None) -> bool:
    """Whether each address is a value read by the ``consumer`` unit through
    its own input use (of one of ``ports``)."""
    return type(addresses) is tuple and all(
        address.kind == "read"
        and records[address].get("role") == "value"
        and records[records[address].get("use")].get("consumer") == consumer.address
        and records[records[address].get("use")].get("producer")
        == consumer.get("input")
        and (ports is None or records[address].get("port") in ports)
        for address in addresses
    )


def _ranked_compiled_filter(records, address, where, seen):
    """`_ranked_filter` over records, each operation and parameter read once:
    (the source ports of its `is not None` tests, each nullable, and the
    source ports read by its `f == p` tests, each with a non-null Int
    parameter), or None."""
    if address in seen or address.kind != "operation":
        return None
    seen.add(address)
    operator, operands = (
        records[address].get("operator"),
        records[address].get("operands"),
    )
    if operator == ("binary", "and"):
        if len(operands) != 2:
            return None
        left, right = (
            _ranked_compiled_filter(records, operand, where, seen)
            for operand in operands
        )
        if left is None or right is None:
            return None
        return left[0] + right[0], left[1] + right[1]
    if (
        operator not in {("null_test", "is_not_null"), ("comparison", "==")}
        or len(operands) != (1 if operator[0] == "null_test" else 2)
        or not _compiled_reads(records, operands[:1], where)
    ):
        return None
    port = records[records[operands[0]].get("port")]
    if len(operands) == 1:
        return ((port.address,), ()) if port.get("logical")[1] == "nullable" else None
    right = operands[1]
    if right in seen or right.kind != "parameter_read":
        return None
    seen.add(right)
    parameter = records[records[right].get("parameter")]
    if (parameter.get("tag"), parameter.get("nullable")) != ("Int", False):
        return None
    return (), (port,)


def _compiled_bigint(records, port) -> bool:
    """Whether a source port reads a non-null BIGINT field, by its record."""
    physical = records[port.get("source")].get("physical")
    if type(physical) is not str:
        return False
    described = json.loads(physical)
    return (
        described.get("storage") == {"kind": "my_bigint"}
        and described.get("nullable") is False
    )


def ranked_records(records, entry, only=None):
    """Compiled replay's `ranked_statement`, from the records alone: the
    address of the one aggregate of a qualified statement, or None.

    The entry's terminal is, by one key, a result ordered by that key
    ascending, without DISTINCT or LIMIT, over the projection row, or,
    GLOBAL, the projection row itself; the projection reads each aggregate
    output and, by a key, the key once more for the order. The aggregate reads
    a source, or a WHERE row over a source whose predicate is
    `_ranked_compiled_filter`'s: it tests each nullable order key at most
    once for `is not None` and compares at most one field, the key or, GLOBAL,
    a non-null BIGINT field, with the one parameter, which nothing else reads.
    The aggregate computes only `first` and `last`, each of one read ordered
    by the same reads in the same directions. No other unit, relation read or
    operation is in the records, and every unit is the entry declaration's. A
    relation alias leaves no record, so this reads it as the source it names.
    O(1) unless
    the terminal leads to one aggregate (``only``, when given), then linear
    in the records once."""
    owner, terminal = entry.get("declaration"), records[entry.get("terminal")]
    result = terminal if terminal.address.kind == "result" else None
    projection = records[result.get("input")] if result is not None else terminal
    if (
        entry.get("requests") != ()
        or entry.get("retained") != ()
        or projection.address.kind != "row"
        or projection.get("stage") != "projection"
        or projection.get("predicate") is not None
        or projection.get("input").kind != "aggregate"
    ):
        return None
    aggregate = records[projection.get("input")]
    if only is not None and aggregate.address != only:
        return None
    where = records[aggregate.get("input")]
    source = records[where.get("input")] if where.address.kind == "row" else where
    units = [
        u for u in (result, projection, aggregate, where) if u not in (None, source)
    ]
    keys, values = aggregate.get("keys"), aggregate.get("values")
    outputs = aggregate.get("outputs")
    if (
        source.address.kind != "source"
        or where is not source
        and (
            where.get("stage") != "where"
            or where.get("predicate") is None
            or not _compiled_reads(records, where.get("values"), where)
        )
        or any(unit.get("owner") != owner for unit in units)
        or len(keys) > 1
        or aggregate.get("mode") != ("grouped" if keys else "global")
        or not _compiled_reads(records, keys, aggregate)
        or not values
        or len(outputs) != len(keys) + len(values)
        or not _compiled_reads(
            records,
            projection.get("values")[: len(outputs)],
            projection,
            outputs,
        )
        or tuple(
            records[read].get("port")
            for read in projection.get("values")[: len(outputs)]
        )
        != outputs
    ):
        return None
    for value in values:
        record = records[value]
        if (
            value.kind != "aggregate_value"
            or record.get("function") not in ORDERED_VALUE_FUNCTIONS
            or not _compiled_reads(records, record.get("arguments"), aggregate)
            or len(record.get("arguments")) != 1
            or not record.get("order_by")
            or not _compiled_reads(
                records,
                tuple(records[item].get("value") for item in record.get("order_by")),
                aggregate,
            )
        ):
            return None
    if keys:
        if result is None:
            return None
        extra = projection.get("values")[len(outputs) :]
        ordering = result.get("ordering")
        if (
            result.get("distinct") is not False
            or result.get("limit") is not None
            or result.get("limit_literal") is not None
            or len(extra) != 1
            or not _compiled_reads(records, extra, projection, outputs[:1])
            or not _compiled_reads(
                records,
                result.get("projection"),
                result,
                projection.get("outputs")[: len(outputs)],
            )
            or len(ordering) != 1
            or ordering[0][1] != "asc"
            or not _compiled_reads(
                records, ordering[0][:1], result, projection.get("outputs")
            )
            or records[records[ordering[0][0]].get("port")].get("source") != extra[0]
        ):
            return None
    elif result is not None or len(projection.get("values")) != len(outputs):
        return None
    seen: set = set()
    found = (
        ((), ())
        if where is source
        else _ranked_compiled_filter(records, where.get("predicate"), where, seen)
    )
    if found is None:
        return None
    tested, compared = found

    def origin(read):
        # The source port an aggregate read reads, through the WHERE row.
        port = records[read].get("port")
        if where is source:
            return port
        return records[records[port].get("source")].get("port")

    lists = {
        tuple(
            (origin(records[item].get("value")), records[item].get("direction"))
            for item in records[value].get("order_by")
        )
        for value in values
    }
    order = {port for fields in lists for port, _ in fields}
    if (
        len(lists) != 1
        or len(set(tested)) != len(tested)
        or not order.issuperset(tested)
        or len(compared) > 1
        or len(compared) != sum(address.kind == "parameter" for address in records)
        or any(
            port.address != origin(keys[0])
            if keys
            else not _compiled_bigint(records, port)
            for port in compared
        )
    ):
        return None
    counted = sum(
        address.kind in _RANKED_UNIT_RECORDS
        or address.kind in {"operation", "parameter_read", "source"}
        for address in records
    )
    if counted != len(units) + 1 + len(seen):
        return None
    return aggregate.address


def _ranked_compiled_stage(records, record, arguments) -> bool:
    """A compiled MySQL aggregation that `ranked_records` names, by at most
    one non-null BIGINT key read (`ranked_inputs` over resolved inputs)."""
    keys = [
        argument
        for address, (argument, _, _) in zip(
            record.get("outputs"), arguments, strict=True
        )
        if records[records[address].get("source")].address.kind == "read"
    ]
    return all(
        type(key) is rows.SQLStageReference and ranked_key(key.realization, group=True)
        for key in keys
    )


def build_compiled_stage(plan, record, arguments):
    """Realize resolved aggregate inputs with the same R12/R13 laws."""
    from pietto._project.project_compiled_schema import Address, CompiledError
    from pietto._project.project_completed_semantics import (
        compiled_float_key_admitted,
    )
    from pietto._project.project_sql_emission_ast import SQLSymbol

    records = plan.ir.completed.root.records
    facts = {f.address: f for f in plan.ir.completed.facts}
    family = records[Address("target", 0)].get("family")
    cell = (
        mysql_compiled_spread_cell(
            records, records[plan.ir.completed.root.description.query]
        )
        if family == "mysql"
        else None
    )
    stage = CompiledAggregateSubject(plan.references[record.address])
    keys: list[Any] = []
    values: list[AggregateValueColumn] = []
    columns: list[Any] = []
    ranked = None
    for index, (address, supplied) in enumerate(
        zip(record.get("outputs"), arguments, strict=True)
    ):
        port = plan.ports[address]
        expression = records[records[address].get("source")]
        subject = CompiledAggregateSubject(plan.references[expression.address])
        symbol = SQLSymbol(index, port.ref, port.identity.name)
        argument, delimiters, order_by_values = supplied
        if expression.address.kind == "read" and type(argument) is unnesting.NestedRead:
            if delimiters or order_by_values:
                raise CompiledError("COMPILED_GROUP_KEY")
            column = collecting.carry_group(
                argument, export=port, position=index, final=False, terminal=port
            )
            keys.append(column)
            columns.append(column)
            continue
        if expression.address.kind == "read":
            if (
                type(argument) is not rows.SQLStageReference
                or group_key_problem(
                    argument.realization,
                    float_key_cell=compiled_float_key_admitted(
                        records, argument.realization
                    ),
                )
                is not None
                or delimiters
                or order_by_values
            ):
                raise CompiledError("COMPILED_GROUP_KEY")
            read = argument.column
            column = AggregateKeyColumn(
                index,
                port,
                subject,
                argument.port,
                read,
                symbol,
                port.identity.name,
                replace(
                    read,
                    position=index,
                    name=port.identity.name,
                    terminal=port.ref,
                    scope=None,
                    aggregate=AggregateOrigin(
                        "group_key", stage, port.ref, (read.terminal,), key=subject
                    ),
                ),
            )
            keys.append(column)
        else:
            order_by = tuple(
                AggregateOrderItem(value, direction)
                for value, direction in order_by_values
            )
            function = expression.get("function")
            if function not in SPELLING or (argument is None and function != "count"):
                raise CompiledError("COMPILED_AGGREGATE_SIGNATURE")
            if function == "string_agg":
                if (
                    len(delimiters) != 1
                    or not order_by
                    or string_agg_argument_problem(argument) is not None
                    or string_agg_argument_problem(delimiters[0]) is not None
                    or any(
                        group_key_problem(rows.realization_of(order.value, "postgres"))
                        is not None
                        or order.direction not in {"asc", "desc"}
                        for order in order_by
                    )
                ):
                    raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            elif function in FILTERED_FUNCTIONS:
                # A conditional sum's second argument value is its test.
                if (
                    argument is None
                    or len(delimiters) != (function == "filtered_sum")
                    or filtered_problem(
                        function,
                        argument,
                        delimiters[0] if delimiters else argument,
                        records[Address("target", 0)].get("family"),
                    )
                    is not None
                ):
                    raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            elif function == "count_distinct_tuple":
                # Every field of a distinct-tuple count, the first included.
                if (
                    not delimiters
                    or order_by
                    or any(
                        argument_problem(
                            function,
                            member,
                            records[Address("target", 0)].get("family"),
                        )
                        is not None
                        for member in (argument, *delimiters)
                    )
                ):
                    raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            elif function in ORDERED_VALUE_FUNCTIONS:
                # A MySQL `first` or `last` is ranked only in the statement
                # `ranked_records` names, by a non-null BIGINT key at most.
                if ranked is None:
                    ranked = (
                        family == "mysql"
                        and ranked_records(
                            records,
                            records[plan.ir.completed.root.description.query],
                            record.address,
                        )
                        is not None
                        and _ranked_compiled_stage(records, record, arguments)
                    )
                if (
                    delimiters
                    or not order_by
                    or argument_problem(function, argument, family, ranked=ranked)
                    is not None
                    or any(
                        order_key_problem(
                            function, family, rows.realization_of(order.value, family)
                        )
                        is not None
                        or order.direction not in {"asc", "desc"}
                        for order in order_by
                    )
                ):
                    raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            elif len(delimiters) != (function == "quantile") or any(
                _input_terminals(fraction)
                or rows.realization_of(
                    fraction, records[Address("target", 0)].get("family")
                ).tag
                != "Float"
                for fraction in delimiters
            ):
                # Only a `quantile` has a second argument value: its fraction.
                raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            elif (
                argument is not None
                and argument_problem(
                    function, argument, family, cell=expression.address == cell
                )
                is not None
            ):
                raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
            fact = facts[address]
            expected, problem = result_realization(
                records[Address("target", 0)].get("family"),
                function,
                argument,
                (
                    fact.value_type.resolved_type.name,
                    rows.NULLABILITY[fact.value_type.nullability],
                ),
            )
            if (
                problem is not None
                or expected is None
                or (expected.tag, expected.storage, expected.nullable, expected.domain)
                != (
                    fact.realization.tag,
                    fact.realization.storage,
                    fact.realization.nullable,
                    fact.realization.domain,
                )
            ):
                raise CompiledError("COMPILED_AGGREGATE_REALIZATION")
            inputs = (
                tuple(
                    terminal
                    for current in (argument, *delimiters)
                    if current is not None
                    for terminal in _input_terminals(current)
                )
                + tuple(
                    terminal
                    for order in order_by
                    for terminal in _input_terminals(order.value)
                )
                if argument is not None
                else tuple(
                    plan.references[p] for p in records[record.get("use")].get("ports")
                )
            )
            terminal = rows.StageColumn(
                index,
                port.identity.name,
                port.ref,
                fact.realization,
                aggregate=AggregateOrigin(
                    "aggregate_result",
                    stage,
                    port.ref,
                    inputs,
                    aggregate=subject,
                    function=function,
                ),
            )
            column = AggregateValueColumn(
                index,
                port,
                subject,
                function,
                spelling(family, function),
                function in DISTINCT_FUNCTIONS,
                argument_cast(
                    records[Address("target", 0)].get("family"), function, argument
                ),
                argument,
                symbol,
                port.identity.name,
                terminal,
                None
                if not delimiters or function == "count_distinct_tuple"
                else delimiters[0],
                order_by,
                result_cast(
                    records[Address("target", 0)].get("family"), function, argument
                ),
                tuple(delimiters) if function == "count_distinct_tuple" else (),
            )
            values.append(column)
        columns.append(column)
    mode = record.get("mode")
    if mode not in ("grouped", "global") or bool(keys) is not (mode == "grouped"):
        raise CompiledError("COMPILED_AGGREGATE_MODE")
    return tuple(columns), AggregateStage(
        stage,
        tuple(keys),
        tuple(values),
        mode,
        "no_groups" if mode == "grouped" else "one_global_row",
    )
