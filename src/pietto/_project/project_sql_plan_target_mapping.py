"""Closed compiler subpropositions; original plan requirements remain mandatory."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_aggregation as agg
from pietto._project import project_sql_plan_windows as win
from pietto._project import project_sql_plan_literals as lit
from pietto._project import project_sql_plan_joins as joins
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
)
from pietto._project.aggregate_grouped_schema import ProjectAggregateExpressionAnalysis
from pietto.ast_nodes import (
    LiteralExpr,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    BetweenExpr,
    IsNullExpr,
    CallExpr,
    NameExpr,
    DottedNameExpr,
)
from pietto.semantic.model import ValueType, TypeKind, ValueTypeKind, ResolvedType
from pietto.semantic.capability_facts import CapabilityDomain as D, CapabilityKey

__all__: tuple[str, ...] = ()


class PropositionKind(StrEnum):
    SOURCE_FAMILY = "source_family"
    TYPE = "compiler_type_identity"
    SCALAR = "compiler_expression_result"
    LITERAL = "compiler_literal_result"
    AGGREGATE = "compiler_aggregate_signature"
    WINDOW = "compiler_window_signature"
    RESIDUAL = "remaining_original_requirement"


class MappingGap(StrEnum):
    SOURCE = "source_locator_connection_and_realization"
    EXPORT = "exact_export_representation_nullability_and_provenance"
    EXPRESSION = "typed_operands_null_comparison_collation_effect_and_lowering"
    STAGE = "exact_stage_value_representation_and_availability"
    FILTER = "sql_true_only_retention_in_original_clause"
    SCOPE = "original_predecessor_inputs_exports_and_evaluation_scope"
    JOIN = "original_join_kind_fields_scope_or_proof_requirement"
    AGGREGATE = "original_group_empty_input_comparison_projection_or_risk"
    WINDOW = "original_window_inputs_policy_projection_and_lowering"
    RESULT = "original_result_boundary_equivalence_order_limit_or_export"
    SET = "original_set_operation_properties_membership_or_positional_types"
    TYPE_UNMODELED = "no_exact_type_catalog_schema"
    SCALAR_UNMODELED = "no_exact_scalar_schema_for_original_typed_expression"
    AGGREGATE_UNMODELED = "no_direct_field_signature_mapping_for_original_argument"
    WINDOW_UNMODELED = "no_exact_window_signature_schema"


K = PropositionKind
F = reports.ProjectSQLDemandFamily
# This closed table is deliberately independent of the report's future taxonomy.
RESIDUALS = MappingProxyType(
    {
        F.SOURCE: MappingGap.SOURCE,
        F.EXPORT: MappingGap.EXPORT,
        F.EXPRESSION: MappingGap.EXPRESSION,
        F.STAGE_VALUE: MappingGap.STAGE,
        F.FILTER: MappingGap.FILTER,
        F.SCOPE: MappingGap.SCOPE,
        F.JOIN: MappingGap.JOIN,
        F.AGGREGATE: MappingGap.AGGREGATE,
        F.WINDOW: MappingGap.WINDOW,
        F.RESULT: MappingGap.RESULT,
        F.SET: MappingGap.SET,
    }
)
LITERAL_GAPS = (
    lit.ProjectSQLLiteralRequirement.DATA_TYPE,
    lit.ProjectSQLLiteralRequirement.NULLABILITY,
    lit.ProjectSQLLiteralRequirement.RANGE_PRECISION,
    lit.ProjectSQLLiteralRequirement.OPERATOR_OPERAND,
    lit.ProjectSQLLiteralRequirement.COLLATION_OVERLOAD,
)


SUPPORTED_SUBKINDS = MappingProxyType(
    {
        "source_realization": (None,),
        "export_representation": (None,),
        "expression": (
            "select",
            "let",
            "where",
            "match",
            "aggregate_argument",
            "satisfying",
            "qualify",
        ),
        "stage_value": ("input", "export"),
        "scope": (
            "projection",
            "let",
            "where",
            "aggregate",
            "satisfying",
            "window",
            "qualify",
        ),
        "result": (
            "result_value_representation",
            "canonical_result_image",
            "result_scope_and_membership",
            "visible_row_quotient",
            "field_equivalence_nulls_and_type_sources",
            "relation_order_scope",
            "order_direction_nulls_and_ties",
            "order_expression_type_and_operands",
            "order_value_use",
            "pending_strict_fd_order_realization",
            "static_row_count_upper_bound",
        ),
        "filter": ("where", "satisfying", "qualify"),
        "fixed_literal_transport": ("Int", "Float", "Bool", "Text"),
        "join": (
            "join_rows",
            "match_input",
            "match_field",
            "output_field",
            "post_match_scope",
            "single_match",
            "relationship_equality",
            "proof_context",
        ),
        "aggregation": (
            "grouping_and_empty_input",
            "group_comparison",
            "aggregate_operation",
            "result_projection",
            "retained_risk",
        ),
        "window": (
            "input_bag_and_result",
            "input_use",
            "frame_modifiers_named_components",
            "result_projection",
            "argument",
        ),
        "set": (
            "set_operation_quantifier_multiplicity_and_membership",
            "set_properties_and_row_domain",
            "set_whole_row_equivalence",
            "set_operand_membership",
            "set_input_type_null_and_representation",
            "set_positional_column_and_value_sources",
        ),
    }
)

SUPPORTED_VARIANTS = (
    sql.ProjectSQLSourceRealizationDemand,
    sql.ProjectSQLExportRepresentationDemand,
    row.ProjectSQLExpressionDemand,
    row.ProjectSQLStageValueDemand,
    row.ProjectSQLFilterDemand,
    row.ProjectSQLScopeDemand,
    joins.ProjectSQLJoinDemand,
    agg.ProjectSQLAggregateDemand,
    win.ProjectSQLWindowDemand,
    results.ProjectSQLResultDemand,
    sets.ProjectSQLSetDemand,
    lit.ProjectSQLLiteralDemand,
)


def _supported_entry(entry):
    return (
        type(entry) is reports.ProjectSQLDemandEntry
        and type(entry.demand) in SUPPORTED_VARIANTS
        and type(entry.family) is F
        and (None if entry.subkind is None else entry.subkind.value)
        in SUPPORTED_SUBKINDS.get(entry.family.value, ())
    )


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLTargetProposition:
    kind: PropositionKind
    witness: sql.ProjectSQLDemand
    key: CapabilityKey | None
    gap: MappingGap | lit.ProjectSQLLiteralRequirement | None


def type_evidence(demand):
    """Read original evidence only; no type resolution or conversion."""
    if type(demand) is sql.ProjectSQLExportRepresentationDemand:
        return demand.logical_type
    if type(demand) is row.ProjectSQLStageValueDemand:
        return demand.type_evidence
    if type(demand) is lit.ProjectSQLLiteralDemand:
        return demand.use.slot.value_type
    if type(demand) is win.ProjectSQLWindowDemand:
        if type(demand.witness) is win.ProjectSQLWindowArgument:
            return demand.witness.value_type
    return None


def _resolved(value):
    if type(value) in (ValueType, ProjectRowField):
        return value.resolved_type
    return value


def _builtin(value) -> str | None:
    if type(value) is ValueType and value.kind is not ValueTypeKind.KNOWN:
        return None
    resolved = _resolved(value)
    if type(resolved) is ResolvedType and resolved.kind is TypeKind.BUILTIN:
        return resolved.name
    if (
        type(resolved) is ProjectResolvedType
        and resolved.kind is ProjectResolvedTypeKind.BUILTIN
    ):
        return resolved.name
    return None


def _type_key(value) -> CapabilityKey | None:
    name = _builtin(value)
    if name is not None:
        return CapabilityKey(
            D.LOGICAL_TYPE, name, "catalog_membership", context="builtin_registry"
        )
    resolved = _resolved(value)
    if type(resolved) not in (ResolvedType, ProjectResolvedType):
        return None
    kind = resolved.kind
    subject = {
        TypeKind.TYPE_ALIAS: "type_alias",
        TypeKind.ENUM: "enum",
        TypeKind.SHAPE: "shape",
        ProjectResolvedTypeKind.TYPE_ALIAS: "type_alias",
        ProjectResolvedTypeKind.ENUM: "enum",
        ProjectResolvedTypeKind.SHAPE: "shape",
    }.get(kind)
    return (
        None
        if subject is None
        else CapabilityKey(
            D.LOGICAL_TYPE, subject, "declaration_kind", context="semantic_model"
        )
    )


def _literal_key(value: ValueType) -> CapabilityKey | None:
    name = _builtin(value)
    if name is None:
        return None
    subject = {
        "Bool": "boolean",
        "Int": "integer",
        "Float": "float",
        "Text": "text",
    }.get(name)
    if subject is None:
        return None
    return CapabilityKey(
        D.LITERAL, subject, "result", (name, value.nullability.value), "expression"
    )


def _scalar_key(demand: row.ProjectSQLExpressionDemand) -> CapabilityKey | None:
    expr = demand.expression
    result = _builtin(demand.value_type)
    operands = tuple(_builtin(value) for value in demand.operand_types)
    if type(expr) is LiteralExpr:
        return _literal_key(demand.value_type)
    if result is None:
        return None
    if type(expr) is ComparisonExpr:
        return CapabilityKey(
            D.COMPARISON,
            "Expression",
            expr.operator,
            ("Expression", result, "unknown"),
            "expression",
        )
    if type(expr) is IsNullExpr:
        return CapabilityKey(
            D.NULL_TEST,
            "Expression",
            "is not null" if expr.negated else "is null",
            (result, "non_null"),
            "expression",
        )
    if type(expr) is BetweenExpr and all(
        v.kind is ValueTypeKind.KNOWN for v in demand.operand_types
    ):
        return CapabilityKey(
            D.COMPARISON,
            "ValueTypeKind.KNOWN",
            "between",
            ("ValueTypeKind.KNOWN", "ValueTypeKind.KNOWN", result, "unknown"),
            "expression",
        )
    if not operands or any(v is None for v in operands):
        return None
    operands = cast(tuple[str, ...], operands)
    if type(expr) is UnaryExpr and len(operands) == 1:
        return CapabilityKey(
            D.UNARY_OPERATOR,
            operands[0],
            expr.operator,
            (result, "preserve_operand"),
            "expression",
        )
    if type(expr) is BinaryExpr and len(operands) == 2:
        return CapabilityKey(
            D.BINARY_OPERATOR,
            operands[0],
            expr.operator,
            (operands[1], result, "unknown"),
            "expression",
        )
    if (
        type(expr) is CallExpr
        and demand.site.role is row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT
    ):
        if type(expr.callee) is NameExpr and expr.callee.name in {
            "lower",
            "trim",
            "len",
            "matches",
        }:
            return CapabilityKey(
                D.SCALAR_FUNCTION,
                operands[0],
                expr.callee.name,
                (*operands[1:], result, "unknown"),
                "expression",
            )
    return None


def aggregate_inputs(demand, expressions):
    """Exact selected aggregate and direct input; complex shapes remain explicit."""
    value = demand.witness
    if type(value) is not agg.ProjectSQLAggregate:
        return None
    source = value.source
    function = (
        source.fact.function
        if isinstance(source, ProjectAggregateExpressionAnalysis)
        else source.function_name
    )
    if not value.arguments:
        return value, function, "0", "no_argument", "NO_ARGUMENT"
    if len(value.arguments) != 1:
        return None
    argument = expressions[value.arguments[0]]
    if type(argument.expression) not in (NameExpr, DottedNameExpr):
        return None
    if isinstance(source, ProjectAggregateExpressionAnalysis):
        # An expanded LET expression is not the direct-field proposition.
        if source.effective_argument is not argument.expression:
            return None
        names = (
            argument.expression.parts
            if type(argument.expression) is DottedNameExpr
            else (argument.expression.name,)
        )
        if len(names) != 1 or names[0] not in source.input_schema.fields:
            return None
    elif len(source.field_dependencies) != 1 or source.field_dependencies[0].let_path:
        return None
    name = _builtin(argument.value_type)
    return None if name is None else (value, function, "1", "direct_field", name)


def _aggregate_key(demand, expressions):
    parts = aggregate_inputs(demand, expressions)
    if parts is None:
        return None
    value, function, arity, shape, argument = parts
    result = _builtin(value.value_type)
    if result is None:
        return None
    return CapabilityKey(
        D.AGGREGATE,
        function,
        "signature",
        (
            arity,
            shape,
            argument,
            result,
            value.value_type.nullability.value,
            "GROUP",
            "aggregate_result",
        ),
        "aggregate_signature",
    )


def _window_key(demand):
    value = demand.witness
    if type(value) is not win.ProjectSQLWindow or value.function.namespace:
        return None
    name = value.function.name
    if name in {"row_number", "rank", "dense_rank", "percent_rank", "cume_dist"}:
        head = (
            "0",
            "no_argument",
            _builtin(value.value_type),
            value.value_type.nullability.value,
        )
    elif name == "ntile":
        head = (
            "1",
            "positive_int_literal",
            _builtin(value.value_type),
            value.value_type.nullability.value,
        )
    elif name in {"lag", "lead"}:
        head = (
            "1..3",
            "bounded_value_optional_offset_default",
            "T",
            "any_nullable_0_2_or_default_omitted_2",
        )
    elif name in {"first_value", "last_value", "nth_value"}:
        head = (
            ("2", "bounded_value_positive_int_literal", "T", "nullable")
            if name == "nth_value"
            else ("1", "bounded_value", "T", "nullable")
        )
    else:
        return None
    if any(v is None for v in head):
        return None
    head = cast(tuple[str, ...], head)
    order = (
        "mandatory_resolved_order"
        if name in {"first_value", "last_value", "nth_value"}
        else "mandatory_local_order"
    )
    return CapabilityKey(
        D.WINDOW_FUNCTION,
        name,
        "signature",
        (*head, "WINDOW", "window_result", order),
        "window_signature",
    )


def build_propositions(
    entry: reports.ProjectSQLDemandEntry, expressions
) -> tuple[ProjectSQLTargetProposition, ...]:
    if not _supported_entry(entry):
        raise ValueError("Target mapping requires a supported original demand.")
    demand, family = entry.demand, entry.family
    items = []

    def add(kind, key, gap=None):
        items.append(ProjectSQLTargetProposition(kind, demand, key, gap))

    if family is F.SOURCE:
        add(K.SOURCE_FAMILY, None)
    if family in {F.EXPORT, F.STAGE_VALUE, F.LITERAL} or (
        family is F.WINDOW and entry.subkind is win.ProjectSQLWindowDemandKind.ARGUMENT
    ):
        key = _type_key(type_evidence(demand))
        add(K.TYPE, key, MappingGap.TYPE_UNMODELED if key is None else None)
    if type(demand) is row.ProjectSQLExpressionDemand:
        key = _scalar_key(demand)
        add(K.SCALAR, key, MappingGap.SCALAR_UNMODELED if key is None else None)
    if (
        family is F.AGGREGATE
        and entry.subkind is agg.ProjectSQLAggregateDemandKind.AGGREGATE_OPERATION
    ):
        key = _aggregate_key(demand, expressions)
        add(K.AGGREGATE, key, MappingGap.AGGREGATE_UNMODELED if key is None else None)
    if (
        family is F.WINDOW
        and entry.subkind is win.ProjectSQLWindowDemandKind.INPUT_BAG_AND_RESULT
    ):
        key = _window_key(demand)
        add(K.WINDOW, key, MappingGap.WINDOW_UNMODELED if key is None else None)
    if type(demand) is lit.ProjectSQLLiteralDemand:
        add(K.LITERAL, _literal_key(demand.use.slot.value_type))
        for requirement in LITERAL_GAPS:
            add(K.RESIDUAL, None, requirement)
    else:
        add(K.RESIDUAL, None, RESIDUALS[family])
    return tuple(items)


def _valid_type_key(key, value):
    resolved = _resolved(value)
    if type(resolved) not in (ResolvedType, ProjectResolvedType):
        return key is None
    if type(value) is ValueType and value.kind is not ValueTypeKind.KNOWN:
        return key is None
    if resolved.kind in (TypeKind.BUILTIN, ProjectResolvedTypeKind.BUILTIN):
        return (
            key is not None
            and key.domain is D.LOGICAL_TYPE
            and key.subject == resolved.name
            and key.operation == "catalog_membership"
            and key.context == "builtin_registry"
            and key.operands == ()
        )
    subject = None
    if resolved.kind in (TypeKind.TYPE_ALIAS, ProjectResolvedTypeKind.TYPE_ALIAS):
        subject = "type_alias"
    elif resolved.kind in (TypeKind.ENUM, ProjectResolvedTypeKind.ENUM):
        subject = "enum"
    elif resolved.kind in (TypeKind.SHAPE, ProjectResolvedTypeKind.SHAPE):
        subject = "shape"
    return (
        key is None
        if subject is None
        else key is not None
        and key.domain is D.LOGICAL_TYPE
        and key.subject == subject
        and key.operation == "declaration_kind"
        and key.context == "semantic_model"
        and key.operands == ()
    )


def _valid_literal_key(key, value):
    subjects = {"Int": "integer", "Bool": "boolean", "Text": "text", "Float": "float"}
    name = _builtin(value)
    if name not in subjects:
        return key is None
    return (
        key is not None
        and key.domain is D.LITERAL
        and key.subject == subjects[name]
        and key.operation == "result"
        and key.context == "expression"
        and key.operands == (name, value.nullability.value)
    )


def _valid_scalar_key(key, demand):
    expression, result = demand.expression, _builtin(demand.value_type)
    values = tuple(_builtin(value) for value in demand.operand_types)
    if type(expression) is LiteralExpr:
        return _valid_literal_key(key, demand.value_type)
    if result is None:
        return key is None
    if type(expression) is ComparisonExpr:
        return (
            key is not None
            and key.domain is D.COMPARISON
            and key.subject == "Expression"
            and key.operation == expression.operator
            and key.operands == ("Expression", result, "unknown")
            and key.context == "expression"
        )
    if type(expression) is IsNullExpr:
        return (
            key is not None
            and key.domain is D.NULL_TEST
            and key.subject == "Expression"
            and key.operation == ("is not null" if expression.negated else "is null")
            and key.operands == (result, "non_null")
            and key.context == "expression"
        )
    if type(expression) is BetweenExpr and all(
        value.kind is ValueTypeKind.KNOWN for value in demand.operand_types
    ):
        return (
            key is not None
            and key.domain is D.COMPARISON
            and key.subject == "ValueTypeKind.KNOWN"
            and key.operation == "between"
            and key.operands
            == ("ValueTypeKind.KNOWN", "ValueTypeKind.KNOWN", result, "unknown")
            and key.context == "expression"
        )
    if not values or None in values:
        return key is None
    if type(expression) is UnaryExpr and len(values) == 1:
        return (
            key is not None
            and key.domain is D.UNARY_OPERATOR
            and key.subject == values[0]
            and key.operation == expression.operator
            and key.operands == (result, "preserve_operand")
            and key.context == "expression"
        )
    if type(expression) is BinaryExpr and len(values) == 2:
        return (
            key is not None
            and key.domain is D.BINARY_OPERATOR
            and key.subject == values[0]
            and key.operation == expression.operator
            and key.operands == (values[1], result, "unknown")
            and key.context == "expression"
        )
    if (
        type(expression) is CallExpr
        and demand.site.role is row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT
        and type(expression.callee) is NameExpr
        and expression.callee.name in {"lower", "trim", "len", "matches"}
    ):
        return (
            key is not None
            and key.domain is D.SCALAR_FUNCTION
            and key.subject == values[0]
            and key.operation == expression.callee.name
            and key.operands == (*values[1:], result, "unknown")
            and key.context == "expression"
        )
    return key is None


def _valid_window_key(key, demand):
    window = demand.witness
    if type(window) is not win.ProjectSQLWindow or window.function.namespace:
        return key is None
    name = window.function.name
    if name in {"row_number", "rank", "dense_rank", "percent_rank", "cume_dist"}:
        prefix = (
            "0",
            "no_argument",
            _builtin(window.value_type),
            window.value_type.nullability.value,
        )
        order = "mandatory_local_order"
    elif name == "ntile":
        prefix = (
            "1",
            "positive_int_literal",
            _builtin(window.value_type),
            window.value_type.nullability.value,
        )
        order = "mandatory_local_order"
    elif name in {"lag", "lead"}:
        prefix = (
            "1..3",
            "bounded_value_optional_offset_default",
            "T",
            "any_nullable_0_2_or_default_omitted_2",
        )
        order = "mandatory_local_order"
    elif name in {"first_value", "last_value", "nth_value"}:
        prefix = (
            ("2", "bounded_value_positive_int_literal", "T", "nullable")
            if name == "nth_value"
            else ("1", "bounded_value", "T", "nullable")
        )
        order = "mandatory_resolved_order"
    else:
        return key is None
    if None in prefix:
        return key is None
    return (
        key is not None
        and key.domain is D.WINDOW_FUNCTION
        and key.subject == name
        and key.operation == "signature"
        and key.context == "window_signature"
        and key.operands == (*prefix, "WINDOW", "window_result", order)
    )


def _valid_aggregate_key(key, demand, expressions):
    value = demand.witness
    if type(value) is not agg.ProjectSQLAggregate:
        return key is None
    source = value.source
    name = (
        source.fact.function
        if isinstance(source, ProjectAggregateExpressionAnalysis)
        else source.function_name
    )
    arity, shape, argument_type = "0", "no_argument", "NO_ARGUMENT"
    if value.arguments:
        if len(value.arguments) != 1:
            return key is None
        argument = expressions[value.arguments[0]]
        expression = argument.expression
        if type(expression) not in (NameExpr, DottedNameExpr):
            return key is None
        if isinstance(source, ProjectAggregateExpressionAnalysis):
            if source.effective_argument is not expression:
                return key is None
            parts = (
                expression.parts
                if type(expression) is DottedNameExpr
                else (expression.name,)
            )
            if len(parts) != 1 or parts[0] not in source.input_schema.fields:
                return key is None
        elif (
            len(source.field_dependencies) != 1 or source.field_dependencies[0].let_path
        ):
            return key is None
        argument_type = _builtin(argument.value_type)
        if argument_type is None:
            return key is None
        arity, shape = "1", "direct_field"
    result_type = _builtin(value.value_type)
    if result_type is None:
        return key is None
    return (
        key is not None
        and key.domain is D.AGGREGATE
        and key.subject == name
        and key.operation == "signature"
        and key.context == "aggregate_signature"
        and key.operands
        == (
            arity,
            shape,
            argument_type,
            result_type,
            value.value_type.nullability.value,
            "GROUP",
            "aggregate_result",
        )
    )


def check_propositions(entry, propositions, expressions) -> bool:
    """Check supplied rows, independently of the mapping classifier/builders."""
    if not _supported_entry(entry):
        return False
    demand, family = entry.demand, entry.family
    expected = []
    if type(demand) is sql.ProjectSQLSourceRealizationDemand:
        expected.append(K.SOURCE_FAMILY)
    if type(demand) in (
        sql.ProjectSQLExportRepresentationDemand,
        row.ProjectSQLStageValueDemand,
        lit.ProjectSQLLiteralDemand,
    ):
        expected.append(K.TYPE)
    if type(demand) is row.ProjectSQLExpressionDemand:
        expected.append(K.SCALAR)
    if (
        type(demand) is agg.ProjectSQLAggregateDemand
        and demand.kind is agg.ProjectSQLAggregateDemandKind.AGGREGATE_OPERATION
    ):
        expected.append(K.AGGREGATE)
    if type(demand) is win.ProjectSQLWindowDemand:
        if demand.kind is win.ProjectSQLWindowDemandKind.INPUT_BAG_AND_RESULT:
            expected.append(K.WINDOW)
        if demand.kind is win.ProjectSQLWindowDemandKind.ARGUMENT:
            expected.append(K.TYPE)
    if type(demand) is lit.ProjectSQLLiteralDemand:
        expected.append(K.LITERAL)
        expected.extend((K.RESIDUAL,) * 5)
    else:
        if family not in RESIDUALS:
            return False
        expected.append(K.RESIDUAL)
    if type(propositions) is not tuple or len(propositions) != len(expected):
        return False
    residual_position = 0
    for value, kind in zip(propositions, expected, strict=True):
        if (
            type(value) is not ProjectSQLTargetProposition
            or value.kind is not kind
            or value.witness is not demand
        ):
            return False
        key = value.key
        if key is not None and (
            type(key) is not CapabilityKey
            or key.dialect is not None
            or key.extension is not None
        ):
            return False
        if key is not None and (
            type(key.domain) is not D
            or type(key.operands) is not tuple
            or any(type(v) is not str for v in key.operands)
            or any(
                v is not None and type(v) is not str
                for v in (
                    key.subject,
                    key.operation,
                    key.context,
                    key.dialect,
                    key.extension,
                )
            )
        ):
            return False
        if kind is K.RESIDUAL:
            gap = (
                LITERAL_GAPS[residual_position]
                if family is F.LITERAL
                else RESIDUALS[family]
            )
            residual_position += 1
            if key is not None or value.gap is not gap:
                return False
            continue
        if kind is K.SOURCE_FAMILY:
            if key is not None or value.gap is not None:
                return False
            continue
        gap = {
            K.TYPE: MappingGap.TYPE_UNMODELED,
            K.SCALAR: MappingGap.SCALAR_UNMODELED,
            K.AGGREGATE: MappingGap.AGGREGATE_UNMODELED,
            K.WINDOW: MappingGap.WINDOW_UNMODELED,
        }.get(kind)
        if value.gap is not (gap if key is None else None):
            return False
        if kind is K.TYPE and not _valid_type_key(key, type_evidence(demand)):
            return False
        if kind is K.SCALAR and not _valid_scalar_key(key, demand):
            return False
        if kind is K.LITERAL and (
            not isinstance(demand, lit.ProjectSQLLiteralDemand)
            or not _valid_literal_key(key, demand.use.slot.value_type)
        ):
            return False
        if kind is K.WINDOW and not _valid_window_key(key, demand):
            return False
        if kind is K.AGGREGATE and not _valid_aggregate_key(key, demand, expressions):
            return False
    return True
