"""Admitted GROUPED/GLOBAL aggregation stages, satisfying and result domains."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_emission_nested as collecting
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_unnest as unnesting
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.aggregate_grouped_schema import (
    ProjectComputedGroupKeyFact,
    ProjectGroupKeyFact,
)
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto.ast_nodes import SourceDef
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
    # outer SQRT fixed by the function (ROOT_FUNCTIONS).
    "stddev": "VAR_SAMP",
    # PostgreSQL only: PERCENTILE_CONT(fraction) WITHIN GROUP (ORDER BY
    # CAST(x AS pg_catalog.float8)), the fraction 0.5 for `median` and the
    # Float literal of `quantile`, its second argument value, in the
    # `delimiter` slot.
    "median": "PERCENTILE_CONT",
    "quantile": "PERCENTILE_CONT",
}
# The aggregates whose rendering wraps the result (cast) in SQRT( ... ).
ROOT_FUNCTIONS = frozenset({"stddev"})
# The interpolated quantiles, an ordered-set PERCENTILE_CONT.
QUANTILE_FUNCTIONS = frozenset({"median", "quantile"})
# Evidence that a binary64 result is finite because the target refuses an
# overflowing accumulation (SQLSTATE 22003) instead of returning inf or NULL.
TARGET_CHECKED_BINARY64 = "target_checked_binary64_overflow"
DISTINCT_FUNCTIONS = frozenset({"count_distinct"})
COUNTING_FUNCTIONS = frozenset({"count", "count_distinct"})
EXTREMA_FUNCTIONS = frozenset({"min", "max"})
# COUNT publishes its own non-null result; R13 declares the signed64 premise, so
# the domain is that premise's bound, never a guess about this input's row count.
COUNT_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
COUNT_MAX = (1 << 63) - 1
# R12 group comparison stays inside the reviewed V01-V04 domains. V05 keeps its
# meaning limits. A Float group key is admitted only by group_key_problem, so
# window partitions and string_agg order, which read this table, exclude Float.
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
        return source.fact.function
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


def group_key_problem(realization: rows.Realization):
    """A GROUP BY key: the grouping law, or a PostgreSQL finite Float. Floats group
    by float equality (-0.0 == 0.0); MySQL kept -0.0 and 0.0 in two groups over
    a wide key in the real-database campaign, so its Float keys stay refused."""
    if realization.tag != "Float":
        return grouping_problem(realization)
    if rows.float_carrier(realization, "postgres"):
        return None
    return "PIE-B1003", "group_key_type_outside_reviewed_comparison_domain"


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
            family != "postgres"
            or argument is None
            or argument.realization.tag != "Int"
            or tag != "Int"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "sum_result_logical_type_or_argument_drift")
        return rows._checked_int({"kind": "pg_int8"}, *rows.SIGNED64, True), None
    if function == "stddev":
        if (
            family != "postgres"
            or argument is None
            or argument.realization.tag not in {"Int", "Float"}
            or tag != "Float"
            or nullable is not True
        ):
            return None, ("PIE-B1002", "stddev_result_logical_type_or_argument_drift")
        return (
            rows.Realization("Float", {"kind": "pg_float8"}, True, rows.FINITE_FLOAT),
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


def float_argument(argument) -> bool:
    """Whether one realized aggregate argument is a Float carrier."""
    return argument is not None and argument.realization.tag == "Float"


def argument_problem(function: str, argument, family: str):
    """R13 admits one established V01 field per aggregate argument, or on
    PostgreSQL one admitted row expression, as a LET would lower it. Any other
    argument, such as a bare literal or parameter or an operation that reads no
    field (only a forged compiled input holds one), reads no row and is refused."""
    direct = type(argument) is rows.SQLStageReference
    if not direct and not (
        type(argument) is rows.SQLOperation
        and any(
            type(node) is rows.SQLStageReference for node in rows.value_nodes(argument)
        )
    ):
        return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
    return resolved_argument_problem(function, direct, argument.realization, family)


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
    function: str, direct_reference: bool, realization, family: str
):
    """The same R13 argument law for an already-resolved input port.

    PostgreSQL MIN/MAX of one Timestamp or Date carrier keep its exact value;
    the MySQL result's fractional seconds and metadata are not yet reviewed.
    PostgreSQL counts and compares a Text, Bool, Float or Decimal carrier by
    the group-key law, as COUNT(DISTINCT x), MIN and MAX compare like GROUP BY;
    MySQL keeps them, and a row expression argument, until a differential.
    A port that is not a direct reference is a row operation: each caller
    refuses any other argument first."""
    if not direct_reference and family != "postgres":
        return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
    if realization is None:
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function == "avg" and realization.tag == "Int":
        if rows.proven_int_bounds(realization) is None:
            return "PIE-B1004", "avg_int_range_evidence_missing"
        return None
    if function == "stddev":
        # PostgreSQL VAR_SAMP of any signed 64-bit integer is exact numeric
        # below 2^128, so its float8 cast is finite; of a finite double it
        # raises SQLSTATE 22003 on overflow. MySQL computes BIGINT in DOUBLE.
        if realization.tag == "Int":
            if family == "postgres" and realization.storage.get("kind") in {
                "pg_int2",
                "pg_int4",
                "pg_int8",
            }:
                return None
            return "PIE-B1003", "stddev_int_not_admitted_on_target"
        if realization.tag == "Float":
            if family == "postgres" and rows.float_carrier(realization, family):
                return None
            return "PIE-B1004", "float_aggregate_finite_result_proof_missing"
        return "PIE-B1003", "stddev_argument_outside_reviewed_int_domain"
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
    # Only a sum or an average has a range or finite-result proof to supply;
    # any other function outside the reviewed Int domain is refused below.
    if function in {"sum", "avg"} and realization.tag == "Decimal":
        return "PIE-B1004", "decimal_aggregate_range_proof_missing"
    if function in {"sum", "avg"} and realization.tag == "Float":
        if family == "postgres" and rows.float_carrier(realization, family):
            return None
        return "PIE-B1004", "float_aggregate_finite_result_proof_missing"
    if family == "postgres" and (
        function in COUNTING_FUNCTIONS
        and realization.tag in {"Text", "Bool", "Float", "Decimal"}
        or function in EXTREMA_FUNCTIONS
        and realization.tag in {"Float", "Decimal"}
    ):
        return group_key_problem(realization)
    if function in COUNTING_FUNCTIONS and realization.tag in {
        "Timestamp",
        "Date",
        "UUID",
    }:
        return grouping_problem(realization)
    if (
        function in EXTREMA_FUNCTIONS
        and family == "postgres"
        and realization.tag in {"Timestamp", "Date"}
    ):
        return grouping_problem(realization)
    if realization.tag != "Int":
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    if function in {"count", "count_distinct", "min", "max"}:
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
    if function not in {"avg", "sum"}:
        return None
    if family == "postgres" and float_argument(argument):
        return None
    if argument is None or argument.realization.tag != "Int":
        raise ValueError("AVG or SUM input cast requires its proven Int argument")
    if function == "sum":
        return result_cast(family, function, argument)
    return "pg_catalog.float8" if family == "postgres" else "DOUBLE"


def result_cast(family: str, function: str, argument) -> str | None:
    """Q1: PostgreSQL SUM(Int) accumulates exactly and its result is narrowed
    to bigint by a checked CAST, which refuses an out-of-range sum with
    SQLSTATE 22003 instead of returning a wrong value. A PostgreSQL VAR_SAMP
    is cast to float8 once, under its fixed SQRT."""
    if function == "stddev":
        if family != "postgres" or argument is None:
            raise ValueError("VAR_SAMP result cast requires a PostgreSQL argument")
        return "pg_catalog.float8"
    if function != "sum" or family == "postgres" and float_argument(argument):
        return None
    if family != "postgres" or argument is None or argument.realization.tag != "Int":
        raise ValueError("SUM result cast requires a PostgreSQL Int argument")
    return "pg_catalog.int8"


def aggregate_evidence(function: str, argument_tag: str | None) -> tuple[str, ...]:
    """R13's evidence beyond the rule, from the function and its argument's
    tag: a checked bigint sum, or a binary64 sum, average or deviation the
    target checks."""
    if function == "sum" and argument_tag == "Int":
        return (rows.TARGET_CHECKED_SIGNED64,)
    if function in {"sum", "avg", "stddev"} and argument_tag == "Float":
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
        if not windowed and (
            len(items) != len(definition.exports)
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
):
    """Realize one aggregation: its ordered determinants and its occurrences,
    or every problem refusing it: a determinant's first, or each occurrence's.

    Every determinant binds the actual pre-aggregate input it already has a port
    for, and every occurrence keeps its own distinct result column even when two
    declarations spell the same aggregate over the same field.
    """
    family = request.family
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
        problem = group_key_problem(read.realization)
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
        if function is None or function not in SPELLING:
            return None, (*unsupported_function(function), value.ref, location)
        arguments = aggregation.arguments(value.source)
        ordered = value.source.item.expression.aggregate_order_by
        if (
            len(arguments) != len(value.arguments)
            or len(ordered) != len(value.order_by)
            or (function == "string_agg") is not bool(ordered)
            or (len(arguments) == 2) is not (function in {"string_agg", "quantile"})
            or len(arguments) > 2
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
        order_by = ()
        if function == "string_agg":
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
                problem = grouping_problem(rows.realization_of(current, family))
                if problem is not None:
                    return None, (*problem, value.ref, location)
                orders.append(
                    AggregateOrderItem(
                        current, "asc" if item.direction is None else item.direction
                    )
                )
            order_by = tuple(orders)
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
            problem = argument_problem(function, argument, request.family)
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
            SPELLING[function],
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
                        for current in (argument, delimiter)
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


def build_compiled_stage(plan, record, arguments):
    """Realize resolved aggregate inputs with the same R12/R13 laws."""
    from pietto._project.project_compiled_schema import Address, CompiledError
    from pietto._project.project_sql_emission_ast import SQLSymbol

    records = plan.ir.completed.root.records
    facts = {f.address: f for f in plan.ir.completed.facts}
    stage = CompiledAggregateSubject(plan.references[record.address])
    keys: list[Any] = []
    values: list[AggregateValueColumn] = []
    columns: list[Any] = []
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
                or group_key_problem(argument.realization) is not None
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
                        grouping_problem(rows.realization_of(order.value, "postgres"))
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
                    function, argument, records[Address("target", 0)].get("family")
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
                SPELLING[function],
                function in DISTINCT_FUNCTIONS,
                argument_cast(
                    records[Address("target", 0)].get("family"), function, argument
                ),
                argument,
                symbol,
                port.identity.name,
                terminal,
                None if not delimiters else delimiters[0],
                order_by,
                result_cast(
                    records[Address("target", 0)].get("family"), function, argument
                ),
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
