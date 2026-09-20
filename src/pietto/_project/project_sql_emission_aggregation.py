"""Admitted GROUPED/GLOBAL aggregation stages, satisfying and result domains."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_emission_rows as rows
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.aggregate_grouped_schema import ProjectGroupKeyFact
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto.ast_nodes import SourceDef
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueTypeKind

__all__: tuple[str, ...] = ()

# R13's first-version aggregate promise, spelled exactly. Nothing here grants a
# generic inline DISTINCT, an aggregate FILTER, internal ordering or any other
# function: every other retained aggregate keeps its own typed non-support.
SPELLING = {"count": "COUNT", "count_distinct": "COUNT", "min": "MIN", "max": "MAX"}
DISTINCT_FUNCTIONS = frozenset({"count_distinct"})
COUNTING_FUNCTIONS = frozenset({"count", "count_distinct"})
EXTREMA_FUNCTIONS = frozenset({"min", "max"})
# COUNT publishes its own non-null result; R13 declares the signed64 premise, so
# the domain is that premise's bound, never a guess about this input's row count.
COUNT_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
COUNT_MAX = (1 << 63) - 1
# R12 group comparison stays inside the reviewed V01-V04 domains. V05 keeps its
# meaning limits and V06 transport never becomes Float grouping or equality.
GROUPING_TAGS = frozenset({"Int", "Bool", "Text", "Decimal"})
TEXT_DOMAIN_KEYS = ("encoding", "collation", "padding")
DECIMAL_DOMAIN_KEYS = ("precision", "scale")
STAGE_KINDS = ("let", "where", "aggregate", "satisfying", "projection")
# The one admitted stage schedule: ordered LET, one WHERE, the aggregation, its
# own satisfying, then the exact visible projection.
STAGE_ORDER = {kind: position for position, kind in enumerate(STAGE_KINDS)}
OPERATORS = {
    "let": (),
    "where": ("row_filter",),
    "aggregate": ("group_aggregate",),
    "satisfying": ("result_filter",),
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
    argument: Any
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        """Summarize this occurrence; no retained product is formatted."""

        return (
            f"AggregateValueColumn(ordinal={self.ordinal!r}, "
            f"label={_scalar(self.label)}, function={_scalar(self.function)}, "
            f"spelling={_scalar(self.spelling)}, distinct={self.distinct!r}, "
            f"argument={_present(self.argument)}, aggregate=..., "
            "export=..., symbol=..., column=...)"
        )


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
    keys: tuple[AggregateKeyColumn, ...]
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


def stage_schedule_valid(kinds: tuple[str, ...], *, aggregated: bool) -> bool:
    """The exact admitted stage order for one definition, and nothing else."""
    if (
        not kinds
        or kinds[-1] != "projection"
        or set(kinds) - set(STAGE_KINDS)
        or kinds.count("projection") != 1
        or kinds.count("where") > 1
        or kinds.count("aggregate") > 1
        or kinds.count("satisfying") > 1
        or ("aggregate" in kinds) is not aggregated
        or ("satisfying" in kinds and "aggregate" not in kinds)
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
    if isinstance(key, ProjectGroupKeyFact):
        field = key.input_field
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
    return None


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
    if function in COUNTING_FUNCTIONS:
        if tag != "Int" or nullable is not False:
            return None, ("PIE-B1002", "count_result_not_non_null_int")
        return (
            rows.Realization(
                "Int",
                {"kind": COUNT_STORAGE[family]},
                False,
                {"kind": "int_range", "min": "0", "max": str(COUNT_MAX)},
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
        rows.Realization(carrier.tag, carrier.storage, True, carrier.domain),
        None,
    )


def argument_problem(function: str, argument):
    """R13 admits exactly one direct established V01 field per aggregate argument."""
    if type(argument) is not rows.SQLStageReference:
        return "PIE-B1003", "aggregate_argument_not_a_direct_established_field"
    if argument.realization.tag != "Int":
        return "PIE-B1003", function + "_argument_outside_reviewed_int_domain"
    return None


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
    """This stage's own generated nodes: each determinant and each occurrence."""
    total = len(stage.keys)
    for value in stage.values:
        total += 1 if value.argument is None else 1 + value_nodes(value.argument)
    return total


def blocks_admitted(plan, *, single_input_use: bool = False) -> bool:
    """Every definition's stage schedule and every retained aggregation binding."""
    stages = aggregated_definitions(plan)
    if len(stages) != len(plan.aggregations):
        return False
    named = tuple(
        item
        for item in plan.bindings.definitions
        if type(item.entry.owner.definition) is not SourceDef
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
        stage = stages.get(definition.ref)
        if (
            not stage_schedule_valid(kinds, aggregated=stage is not None)
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
            expected += OPERATORS[block.kind.value]
            if tuple(item.kind.value for item in block.operators) != expected:
                return False
        if stage is None:
            if projections.get(blocks[-1].ref):
                return False
            continue
        if not _stage_bound(stage, blocks[kinds.index("aggregate")], keys, values):
            return False
        items = projections.get(blocks[-1].ref, ())
        if len(items) != len(definition.exports) or any(
            item.aggregation is not stage.ref or item.export is not export.ref
            for item, export in zip(items, definition.exports, strict=True)
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
    """Realize one aggregation: its ordered determinants and its occurrences.

    Every determinant binds the actual pre-aggregate input it already has a port
    for, and every occurrence keeps its own distinct result column even when two
    declarations spell the same aggregate over the same field.
    """
    family = request.family
    columns: list[Any] = []
    key_columns: list[AggregateKeyColumn] = []
    value_columns: list[AggregateValueColumn] = []
    for index, key in enumerate(keys):
        read = available.get(key.input)
        export = exports[index]
        if read is None:
            return (
                None,
                None,
                ("PIE-B1001", "group_key_outside_pre_aggregate_input", key.ref, None),
            )
        if export.source is not key.ref:
            return (
                None,
                None,
                ("PIE-B1001", "group_key_result_port_drift", key.ref, None),
            )
        retained = key_logical(key.source)
        if retained is None:
            return (
                None,
                None,
                ("PIE-B1004", "group_key_logical_type_evidence_missing", key.ref, None),
            )
        if (read.realization.tag, read.realization.nullable) != retained:
            return (
                None,
                None,
                ("PIE-B1002", "group_key_logical_type_or_null_drift", key.ref, None),
            )
        problem = grouping_problem(read.realization)
        if problem is not None:
            return None, None, (*problem, key.ref, None)
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
    for offset, value in enumerate(values):
        index = len(keys) + offset
        export = exports[index]
        if export.source is not value.ref:
            return (
                None,
                None,
                ("PIE-B1001", "aggregate_result_port_drift", value.ref, None),
            )
        function = function_name(value.source)
        location = value.source.item.span
        if function is None or function not in SPELLING:
            return None, None, (*unsupported_function(function), value.ref, location)
        arguments = aggregation.arguments(value.source)
        if len(arguments) != len(value.arguments) or len(arguments) > 1:
            return (
                None,
                None,
                (
                    "PIE-B1003",
                    "aggregate_argument_signature_not_admitted",
                    value.ref,
                    location,
                ),
            )
        argument = None
        if value.arguments:
            argument, problem = rows.build_row_value(
                request,
                available,
                value.arguments[0],
                uses,
                reference_type=reference_type,
            )
            if argument is None:
                assert problem is not None
                return None, None, (*problem, value.ref, location)
            problem = argument_problem(function, argument)
            if problem is not None:
                return None, None, (*problem, value.ref, location)
        elif function != "count":
            return (
                None,
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
            return None, None, (*problem, value.ref, location)
        label = f"c{index}"
        column = AggregateValueColumn(
            index,
            export,
            value,
            function,
            SPELLING[function],
            function in DISTINCT_FUNCTIONS,
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
                    (argument.column.terminal,)
                    if argument is not None
                    else tuple(item.terminal for item in available.values()),
                    aggregate=value,
                    function=function,
                ),
            ),
        )
        columns.append(column)
        value_columns.append(column)
    if len(columns) != len(exports):
        return (
            None,
            None,
            ("PIE-B1001", "aggregate_result_denominator", stage.ref, None),
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
    columns: list[AggregateProjectionColumn] = []
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
