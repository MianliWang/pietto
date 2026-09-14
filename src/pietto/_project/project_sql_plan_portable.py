"""Rooted Phase65 observation encoding and independent runtime correspondence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Never
from collections import deque
from collections.abc import Mapping
from enum import Enum
from math import isfinite

from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_source_maps as maps
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project import project_sql_plan_portable_schema as schema
from pietto._project import project_sql_plan_pure_boundary as pure
from pietto._project.project_sql_plan_verification import ProjectSQLPlanVerification


# Runtime carrier imports.
from pietto._project import project_sql_plan_expressions as project_sql_plan_expressions
from pietto._project import project_sql_plan_literals as project_sql_plan_literals
from pietto._project import project_sql_plan_results as project_sql_plan_results
from pietto._project import project_sql_plan_sets as project_sql_plan_sets
from pietto._project import project_sql_plan_joins as project_sql_plan_joins
from pietto._project import project_sql_plan_aggregation as project_sql_plan_aggregation
from pietto._project import project_sql_plan_windows as project_sql_plan_windows
from pietto._project import module_catalog as module_catalog
from pietto import ast_nodes as ast_nodes
from pietto._project import project_query_block_ir as project_query_block_ir
from pietto._project import project_completion as project_completion
from pietto._project import module_carrier as module_carrier
from pietto._project import project_ir_composition as project_ir_composition
from pietto._project import module_relation_resolution as module_relation_resolution
from pietto._project import module_attribution as module_attribution
from pietto._project import (
    project_ir_relational_properties as project_ir_relational_properties,
)
from pietto._project import (
    module_semantic_fact_preservation as module_semantic_fact_preservation,
)
from pietto._project import model as project_model
from pietto.semantic import model as semantic_model
from pietto._project import let_scope_facts as let_scope_facts
from pietto._project import project_ir_operators as project_ir_operators
from pietto._project import project_ir_construction as project_ir_construction
from pietto._project import project_ir as project_ir
from pietto._project import project_ir_properties as project_ir_properties
from pietto._project import project_joined_row_filter as project_joined_row_filter
from pietto._project import project_final_outputs as project_final_outputs
from pietto._project import project_row_equivalence as project_row_equivalence
from pietto._project import project_grain as project_grain
from pietto._project import project_set_operations as project_set_operations
from pietto._project import module_resolution as module_resolution
from pietto._project import project_row_keys as project_row_keys
from pietto._project import (
    project_relationship_conditions as project_relationship_conditions,
)
from pietto._project import (
    aggregate_grouped_clause_facts as aggregate_grouped_clause_facts,
)
from pietto._project import aggregate_grouped_schema as aggregate_grouped_schema
from pietto._project import window_semantics as project_window_semantics
from pietto import _window_identity as _window_identity
from pietto.semantic import window_input_analysis as window_input_analysis
from pietto.semantic import window_semantics as semantic_window_semantics
from pietto._project import project_joined_qualify as project_joined_qualify
from pietto._project import row_dependency_graph as row_dependency_graph
from pietto import errors as errors
from pietto._project import (
    project_sql_plan_target_mapping as project_sql_plan_target_mapping,
)
from pietto.semantic import capability_lookup as capability_lookup
from pietto.semantic import capability_facts as capability_facts
from pietto.semantic import capability_providers as capability_providers
from pietto.semantic import capability_profiles as capability_profiles
from pietto.semantic import capability_composition as capability_composition
from pietto._project import (
    project_query_block_ir_algebra as project_query_block_ir_algebra,
)
from pietto._project import project_join_conditions as project_join_conditions
from pietto._project import project_scalar_namespaces as project_scalar_namespaces
from pietto._project import project_scalar_references as project_scalar_references
from pietto._project import project_single_match as project_single_match
from pietto._project import project_relationship_uses as project_relationship_uses
from pietto._project import project_current_joins as project_current_joins
from pietto._project import project_joined_aggregation as project_joined_aggregation
from pietto.semantic import generic_compatibility as generic_compatibility
from pietto.semantic import nullability_formulas as nullability_formulas
from pietto._project import project_joined_row_semantics as project_joined_row_semantics
from pietto._project import project_multifact as project_multifact
from pietto._project import project_query_block as project_query_block
from pietto._project import project_ir_joins as project_ir_joins
from pietto._project import (
    project_relationship_match_guarantees as project_relationship_match_guarantees,
)
from pietto._project import project_relationship_paths as project_relationship_paths
from pietto._project import project_relationships as project_relationships
from pietto._project import project_current_join_inputs as project_current_join_inputs
from pietto._project import extension_signature_provider as extension_signature_provider
from pietto.semantic import (
    extension_signature_requirements as extension_signature_requirements,
)
from pietto._project import (
    extension_catalog_availability as extension_catalog_availability,
)
from pietto.semantic import extension_catalog as extension_catalog
from pietto._project import module_bindings as module_bindings
from pietto._project import module_exports as module_exports
from pietto._project import project_joined_windows as project_joined_windows
from pietto._project import (
    project_ir_evaluation_context as project_ir_evaluation_context,
)
# End runtime carrier imports.

__all__: tuple[str, ...] = ()
_INTEGER_BOUND = 10**schema.MAX_DIGITS


class RuntimeIssue(StrEnum):
    INVALID_REQUEST = "invalid_runtime_request"
    UNSUPPORTED_VALUE = "unsupported_transport_value"
    RESOURCE_LIMIT = "transport_resource_limit"
    CORRESPONDENCE = "runtime_document_correspondence"


class TransportError(ValueError):
    def __init__(self, issue: RuntimeIssue):
        self.issue = issue
        super().__init__(
            "Portable observation requires supported, current verified inputs."
        )


@dataclass(frozen=True, slots=True, eq=False)
class _Context:
    verification: ProjectSQLPlanVerification
    report: reports.ProjectSQLRequirementVerification
    source_map: maps.ProjectSQLSourceMapVerification
    assessment: targets.ProjectSQLTargetAssessmentVerification | None


@dataclass(frozen=True, slots=True, eq=False, init=False)
class ProjectSQLPlanPortable:
    context: _Context
    document: schema.Document
    canonical_bytes: bytes
    bindings: tuple[tuple[schema.Ref, object], ...]

    def __init__(self) -> Never:
        raise TypeError("Portable observations require rooted construction.")


@dataclass(frozen=True, slots=True, eq=False)
class ProjectSQLPlanPortableVerification:
    product: ProjectSQLPlanPortable
    verification: ProjectSQLPlanVerification
    assessment: targets.ProjectSQLTargetAssessmentVerification | None
    issues: tuple[RuntimeIssue, ...]

    @property
    def verified(self) -> bool:
        return not self.issues


def _context(verification, report, source_map, assessment):
    if type(verification) is not ProjectSQLPlanVerification:
        raise TransportError(RuntimeIssue.INVALID_REQUEST)
    if (
        report is None
        and type(assessment) is targets.ProjectSQLTargetAssessmentVerification
    ):
        report = assessment.assessment.report_verification
    if report is None:
        value = reports.build_project_sql_requirement_report(verification)
        report = reports.verify_project_sql_requirement_report(value, verification)
    if source_map is None:
        value = maps.build_project_sql_source_map(verification)
        source_map = maps.verify_project_sql_source_map(value, verification)
    context = _Context(verification, report, source_map, assessment)
    _check_context(context, verification, assessment)
    return context


def _check_context(context, verification, assessment):
    if (
        type(context) is not _Context
        or context.verification is not verification
        or context.assessment is not assessment
    ):
        raise TransportError(RuntimeIssue.INVALID_REQUEST)
    report, source_map = context.report, context.source_map
    if (
        type(report) is not reports.ProjectSQLRequirementVerification
        or report.source_verification is not verification
        or not report.verified
        or not reports.verify_project_sql_requirement_report(
            report.report, verification
        ).verified
    ):
        raise TransportError(RuntimeIssue.INVALID_REQUEST)
    if (
        type(source_map) is not maps.ProjectSQLSourceMapVerification
        or source_map.source_verification is not verification
        or not source_map.verified
        or not maps.verify_project_sql_source_map(
            source_map.source_map, verification
        ).verified
    ):
        raise TransportError(RuntimeIssue.INVALID_REQUEST)
    if assessment is not None:
        if (
            type(assessment) is not targets.ProjectSQLTargetAssessmentVerification
            or assessment.source_verification is not verification
            or not assessment.verified
            or not targets.verify_project_sql_target_assessment(
                assessment.assessment, verification, assessment.request
            ).verified
        ):
            raise TransportError(RuntimeIssue.INVALID_REQUEST)


def build_project_sql_plan_portable(
    verification: ProjectSQLPlanVerification,
    *,
    report: reports.ProjectSQLRequirementVerification | None = None,
    source_map: maps.ProjectSQLSourceMapVerification | None = None,
    assessment: targets.ProjectSQLTargetAssessmentVerification | None = None,
) -> ProjectSQLPlanPortable:
    try:
        context = _context(verification, report, source_map, assessment)
        document, bindings = _encode_context(context)
        outcome = pure.evaluate_project_sql_plan_document(document)
        if outcome.status is pure.Status.RESOURCE_LIMIT:
            raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
        if outcome.status is not pure.Status.OK or outcome.canonical_bytes is None:
            raise TransportError(RuntimeIssue.UNSUPPORTED_VALUE)
        product = object.__new__(ProjectSQLPlanPortable)
        for name, value in (
            ("context", context),
            ("document", document),
            ("canonical_bytes", outcome.canonical_bytes),
            ("bindings", bindings),
        ):
            object.__setattr__(product, name, value)
        if not _corresponds(product):
            raise TransportError(RuntimeIssue.CORRESPONDENCE)
        return product
    except TransportError:
        raise
    except (MemoryError, RecursionError, OverflowError):
        raise TransportError(RuntimeIssue.RESOURCE_LIMIT) from None
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        raise TransportError(RuntimeIssue.INVALID_REQUEST) from None


def verify_project_sql_plan_portable(
    product, verification, *, assessment=None
) -> ProjectSQLPlanPortableVerification:
    issues = ()
    try:
        if type(product) is not ProjectSQLPlanPortable:
            raise TransportError(RuntimeIssue.INVALID_REQUEST)
        _check_context(product.context, verification, assessment)
        outcome = pure.evaluate_project_sql_plan_document(product.document)
        if (
            outcome.status is not pure.Status.OK
            or outcome.canonical_bytes != product.canonical_bytes
            or not _corresponds(product)
        ):
            issues = (RuntimeIssue.CORRESPONDENCE,)
    except TransportError as error:
        issues = (error.issue,)
    except (
        AttributeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        MemoryError,
        RecursionError,
        OverflowError,
    ):
        issues = (RuntimeIssue.CORRESPONDENCE,)
    return ProjectSQLPlanPortableVerification(product, verification, assessment, issues)


def _fields(value: Any) -> tuple[str, tuple[tuple[str, Any], ...]]:
    if type(value) is _Context:
        return "observation", (
            ("plan", value.verification.plan),
            ("report", value.report.report),
            ("source_map", value.source_map.source_map),
            (
                "assessment",
                None if value.assessment is None else value.assessment.assessment,
            ),
        )
    kind = _ADAPTERS.get(type(value))
    if kind is None:
        raise TransportError(RuntimeIssue.UNSUPPORTED_VALUE)

    def retained(name):
        if (
            name == "operators"
            and type(value) is project_query_block_ir.ProjectIRReusedEffectiveOutput
        ):
            return value.semantic_entry.fragment.logical_stage.operators
        if type(value) is project_query_block_ir.ProjectIRReboundExistingOutput:
            if name == "operators":
                return value.rebuilt_fragment.logical_stage.operators
            if name == "original_operators":
                return value.semantic_entry.fragment.logical_stage.operators
        return getattr(value, name)

    return kind, tuple(
        (field.name, retained(field.name)) for field in schema.RECORD_RULES[kind].fields
    )


def _encode_context(context):
    pending = deque()
    identities = {}
    counts = {}
    bindings = []
    value_count = 0
    text_bytes = 0
    edge_count = 0

    def reference(value):
        previous = identities.get(id(value))
        if previous is not None:
            return previous
        kind, _ = _fields(value)
        domain = schema.RECORD_RULES[kind].domain
        ref = schema.Ref(domain, counts.get(domain, 0))
        counts[domain] = ref.position + 1
        identities[id(value)] = ref
        bindings.append((ref, value))
        if len(bindings) > schema.MAX_RECORDS:
            raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
        pending.append((ref, value))
        return ref

    def encode(value, depth=0):
        nonlocal value_count, text_bytes, edge_count
        value_count += 1
        if value_count > schema.MAX_EDGES * 8:
            raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
        if depth > schema.MAX_DEPTH:
            raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
        if value is None:
            return schema.Value(schema.Tag.ABSENT, None)
        if type(value) is bool:
            return schema.Value(schema.Tag.BOOLEAN, value)
        if type(value) is int:
            if abs(value) >= _INTEGER_BOUND:
                raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
            return schema.Value(schema.Tag.INTEGER, str(value))
        if type(value) is float:
            if not isfinite(value):
                raise TransportError(RuntimeIssue.UNSUPPORTED_VALUE)
            return schema.Value(schema.Tag.FLOAT, value.hex())
        if type(value) is str:
            if len(value) > schema.MAX_TEXT:
                raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
            text_bytes += len(value.encode("utf-8"))
            if text_bytes > schema.MAX_BYTES:
                raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
            return schema.Value(schema.Tag.TEXT, value)
        if type(value) in _ENUMS:
            return schema.Value(schema.Tag.ENUM, value.value)
        if type(value) is tuple:
            if len(value) > schema.MAX_EDGES:
                raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
            return schema.Value(
                schema.Tag.SEQUENCE, tuple(encode(item, depth + 1) for item in value)
            )
        if isinstance(value, Mapping):
            if len(value) > schema.MAX_EDGES:
                raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
            return schema.Value(
                schema.Tag.MAPPING,
                tuple(
                    schema.Value(
                        schema.Tag.SEQUENCE,
                        (encode(key, depth + 1), encode(item, depth + 1)),
                    )
                    for key, item in value.items()
                ),
            )
        edge_count += 1
        if edge_count > schema.MAX_EDGES:
            raise TransportError(RuntimeIssue.RESOURCE_LIMIT)
        return schema.Value(schema.Tag.REF, reference(value))

    reference(context)
    records = []
    while pending:
        ref, value = pending.popleft()
        kind, fields = _fields(value)
        records.append(
            schema.Record(
                kind,
                ref,
                tuple(schema.Field(name, encode(item)) for name, item in fields),
            )
        )
    return schema.Document(schema.FORMAT, tuple(records)), tuple(bindings)


def _corresponds(product):
    """Check each declared field against original objects; never re-encode roots."""
    records = product.document.records
    if len(records) != len(product.bindings) or not records:
        return False
    by_ref = dict(product.bindings)
    by_object = {id(value): ref for ref, value in product.bindings}
    if len(by_ref) != len(records) or len(by_object) != len(records):
        return False
    if product.bindings[0][1] is not product.context:
        return False
    reached = {records[0].ref}

    def matches(original, field):
        tag, data = field.tag, field.data
        if tag is schema.Tag.REF:
            if by_ref.get(data) is not original or by_object.get(id(original)) != data:
                return False
            reached.add(data)
            return True
        if tag is schema.Tag.ABSENT:
            return original is None and data is None
        if tag is schema.Tag.BOOLEAN:
            return type(original) is bool and data is original
        if tag is schema.Tag.INTEGER:
            return type(original) is int and pure._integer(data) == original
        if tag is schema.Tag.FLOAT:
            return type(original) is float and original.hex() == data
        if tag is schema.Tag.TEXT:
            return type(original) is str and original == data
        if tag is schema.Tag.ENUM:
            return type(original) in _ENUMS and original.value == data
        if tag is schema.Tag.SEQUENCE:
            return (
                type(original) is tuple
                and len(original) == len(data)
                and all(matches(a, b) for a, b in zip(original, data, strict=True))
            )
        if tag is schema.Tag.MAPPING:
            return (
                isinstance(original, Mapping)
                and len(original) == len(data)
                and all(
                    matches((key, value), pair)
                    for (key, value), pair in zip(original.items(), data, strict=True)
                )
            )
        return False

    for record, (ref, original) in zip(records, product.bindings, strict=True):
        kind, fields = _fields(original)
        if (
            record.ref != ref
            or record.kind != kind
            or len(record.fields) != len(fields)
        ):
            return False
        for actual, (name, value) in zip(record.fields, fields, strict=True):
            if actual.name != name or not matches(value, actual.value):
                return False
    return reached == set(by_ref)


# Exact runtime class and field projection; unknown variants fail closed.

_ADAPTERS: Mapping[type, str] = {
    plans.ProjectSQLPlanScope: "project_sql_plan_scope",
    plans.ProjectSQLPlanRef: "project_sql_plan_ref",
    plans.ProjectSQLPort: "project_sql_port",
    plans.ProjectSQLDefinition: "project_sql_definition",
    plans.ProjectSQLSourceBinding: "project_sql_source_binding",
    plans.ProjectSQLInputUse: "project_sql_input_use",
    plans.ProjectSQLBoundary: "project_sql_boundary",
    plans.ProjectSQLSymbol: "project_sql_symbol",
    plans.ProjectSQLSelectBlock: "project_sql_select_block",
    plans.ProjectSQLProjection: "project_sql_projection",
    plans.ProjectSQLOrigin: "project_sql_origin",
    plans.ProjectSQLSourceRealizationDemand: "project_sql_source_realization_demand",
    plans.ProjectSQLExportRepresentationDemand: "project_sql_export_representation_demand",
    plans.ProjectSQLBindings: "project_sql_bindings",
    plans.ProjectSQLPlan: "project_sql_plan",
    project_sql_plan_expressions.ProjectSQLExpressionSite: "project_sql_expression_site",
    project_sql_plan_expressions.ProjectSQLJoinedSite: "project_sql_joined_site",
    project_sql_plan_expressions.ProjectSQLMatchSite: "project_sql_match_site",
    project_sql_plan_expressions.ProjectSQLLiteral: "project_sql_literal",
    project_sql_plan_expressions.ProjectSQLBoundLiteral: "project_sql_bound_literal",
    project_sql_plan_expressions.ProjectSQLReference: "project_sql_reference",
    project_sql_plan_expressions.ProjectSQLJoinedReference: "project_sql_joined_reference",
    project_sql_plan_expressions.ProjectSQLMatchReference: "project_sql_match_reference",
    project_sql_plan_expressions.ProjectSQLUnary: "project_sql_unary",
    project_sql_plan_expressions.ProjectSQLBinary: "project_sql_binary",
    project_sql_plan_expressions.ProjectSQLComparison: "project_sql_comparison",
    project_sql_plan_expressions.ProjectSQLIsNull: "project_sql_is_null",
    project_sql_plan_expressions.ProjectSQLBetween: "project_sql_between",
    project_sql_plan_expressions.ProjectSQLExpressionOperand: "project_sql_expression_operand",
    project_sql_plan_expressions.ProjectSQLStagePort: "project_sql_stage_port",
    project_sql_plan_expressions.ProjectSQLLetValue: "project_sql_let_value",
    project_sql_plan_expressions.ProjectSQLFilter: "project_sql_filter",
    project_sql_plan_expressions.ProjectSQLExpressionDemand: "project_sql_expression_demand",
    project_sql_plan_expressions.ProjectSQLStageValueDemand: "project_sql_stage_value_demand",
    project_sql_plan_expressions.ProjectSQLFilterDemand: "project_sql_filter_demand",
    project_sql_plan_expressions.ProjectSQLScopeDemand: "project_sql_scope_demand",
    project_sql_plan_literals.ProjectSQLLiteralPosition: "project_sql_literal_position",
    project_sql_plan_literals.ProjectSQLLiteralSite: "project_sql_literal_site",
    project_sql_plan_literals.ProjectSQLLiteralSlot: "project_sql_literal_slot",
    project_sql_plan_literals.ProjectSQLFixedLiteralValue: "project_sql_fixed_literal_value",
    project_sql_plan_literals.ProjectSQLBindUse: "project_sql_bind_use",
    project_sql_plan_literals.ProjectSQLFixedEnvelope: "project_sql_fixed_envelope",
    project_sql_plan_literals.ProjectSQLLiteralDemand: "project_sql_literal_demand",
    project_sql_plan_results.ProjectSQLResultBoundary: "project_sql_result_boundary",
    project_sql_plan_results.ProjectSQLResultPort: "project_sql_result_port",
    project_sql_plan_results.ProjectSQLDistinct: "project_sql_distinct",
    project_sql_plan_results.ProjectSQLQuotientField: "project_sql_quotient_field",
    project_sql_plan_results.ProjectSQLOrder: "project_sql_order",
    project_sql_plan_results.ProjectSQLOrderItem: "project_sql_order_item",
    project_sql_plan_results.ProjectSQLOrderExpression: "project_sql_order_expression",
    project_sql_plan_results.ProjectSQLOrderUse: "project_sql_order_use",
    project_sql_plan_results.ProjectSQLHiddenOrderRequirement: "project_sql_hidden_order_requirement",
    project_sql_plan_results.ProjectSQLResultLimit: "project_sql_result_limit",
    project_sql_plan_results.ProjectSQLResultExport: "project_sql_result_export",
    project_sql_plan_results.ProjectSQLResultDemand: "project_sql_result_demand",
    project_sql_plan_sets.ProjectSQLSetBody: "project_sql_set_body",
    project_sql_plan_sets.ProjectSQLSetOperand: "project_sql_set_operand",
    project_sql_plan_sets.ProjectSQLSetInput: "project_sql_set_input",
    project_sql_plan_sets.ProjectSQLSetColumn: "project_sql_set_column",
    project_sql_plan_sets.ProjectSQLSetDemand: "project_sql_set_demand",
    project_sql_plan_joins.ProjectSQLJoinInput: "project_sql_join_input",
    project_sql_plan_joins.ProjectSQLJoinPort: "project_sql_join_port",
    project_sql_plan_joins.ProjectSQLRelationshipMatch: "project_sql_relationship_match",
    project_sql_plan_joins.ProjectSQLJoin: "project_sql_join",
    project_sql_plan_joins.ProjectSQLJoinTail: "project_sql_join_tail",
    project_sql_plan_joins.ProjectSQLSingleMatch: "project_sql_single_match",
    project_sql_plan_joins.ProjectSQLSingleMatchProof: "project_sql_single_match_proof",
    project_sql_plan_joins.ProjectSQLJoinDemand: "project_sql_join_demand",
    project_sql_plan_aggregation.ProjectSQLAggregationAuthority: "project_sql_aggregation_authority",
    project_sql_plan_aggregation.ProjectSQLAggregation: "project_sql_aggregation",
    project_sql_plan_aggregation.ProjectSQLGroupKey: "project_sql_group_key",
    project_sql_plan_aggregation.ProjectSQLAggregate: "project_sql_aggregate",
    project_sql_plan_aggregation.ProjectSQLAggregateSite: "project_sql_aggregate_site",
    project_sql_plan_aggregation.ProjectSQLResultReference: "project_sql_result_reference",
    project_sql_plan_aggregation.ProjectSQLAggregateArgumentCall: "project_sql_aggregate_argument_call",
    project_sql_plan_aggregation.ProjectSQLAggregateProjection: "project_sql_aggregate_projection",
    project_sql_plan_aggregation.ProjectSQLAggregateRisk: "project_sql_aggregate_risk",
    project_sql_plan_aggregation.ProjectSQLAggregateDemand: "project_sql_aggregate_demand",
    project_sql_plan_windows.ProjectSQLWindow: "project_sql_window",
    project_sql_plan_windows.ProjectSQLWindowUse: "project_sql_window_use",
    project_sql_plan_windows.ProjectSQLWindowArgument: "project_sql_window_argument",
    project_sql_plan_windows.ProjectSQLWindowPolicy: "project_sql_window_policy",
    project_sql_plan_windows.ProjectSQLQualifySite: "project_sql_qualify_site",
    project_sql_plan_windows.ProjectSQLWindowReference: "project_sql_window_reference",
    project_sql_plan_windows.ProjectSQLWindowProjection: "project_sql_window_projection",
    project_sql_plan_windows.ProjectSQLWindowDemand: "project_sql_window_demand",
    reports.ProjectSQLDemandScope: "project_sql_demand_scope",
    reports.ProjectSQLDemandEntry: "project_sql_demand_entry",
    reports.ProjectSQLDemandLink: "project_sql_demand_link",
    reports.ProjectSQLSingleMatchReport: "project_sql_single_match_report",
    reports.ProjectSQLHiddenOrderReport: "project_sql_hidden_order_report",
    reports.ProjectSQLAggregateEvidenceReport: "project_sql_aggregate_evidence_report",
    reports.ProjectSQLDemandFamilyReport: "project_sql_demand_family_report",
    reports.ProjectSQLRequirementSummary: "project_sql_requirement_summary",
    reports.ProjectSQLRequirementReport: "project_sql_requirement_report",
    maps.ProjectSQLSourcePosition: "project_sql_source_position",
    maps.ProjectSQLMappedSource: "project_sql_mapped_source",
    maps.ProjectSQLSourceSite: "project_sql_source_site",
    maps.ProjectSQLSourceMapEntry: "project_sql_source_map_entry",
    maps.ProjectSQLSourceAssociation: "project_sql_source_association",
    maps.ProjectSQLLegacySourcePosition: "project_sql_legacy_source_position",
    maps.ProjectSQLMappedSubject: "project_sql_mapped_subject",
    maps.ProjectSQLSourceLink: "project_sql_source_link",
    maps.ProjectSQLSourceMap: "project_sql_source_map",
    module_catalog.ProjectDeclarationOccurrence: "project_declaration_occurrence",
    ast_nodes.QueryDef: "query_def",
    ast_nodes.TableDef: "table_def",
    ast_nodes.SetRelationDef: "set_relation_def",
    ast_nodes.Span: "span",
    project_query_block_ir.ProjectIRReusedEffectiveOutput: "project_ir_reused_effective_output",
    project_completion.ProjectExistingEffectiveOutput: "project_existing_effective_output",
    module_carrier.ProjectLogicalModule: "project_logical_module",
    ast_nodes.SourceDef: "source_def",
    ast_nodes.CallExpr: "call_expr",
    project_ir_composition.ProjectIRCrossRelationEdge: "project_ir_cross_relation_edge",
    project_completion.ProjectCompletionDependency: "project_completion_dependency",
    module_relation_resolution.ProjectResolvedModuleRelationSymbol: "project_resolved_module_relation_symbol",
    module_attribution.ProjectModuleOriginPath: "project_module_origin_path",
    project_ir_relational_properties.ProjectIROutputFieldOccurrence: "project_ir_output_field_occurrence",
    module_attribution.ProjectModuleRowFieldIdentity: "project_module_row_field_identity",
    module_semantic_fact_preservation.ProjectModuleSelectFact: "project_module_select_fact",
    ast_nodes.SelectItem: "select_item",
    ast_nodes.FromClause: "from_clause",
    project_model.ProjectRowField: "project_row_field",
    module_semantic_fact_preservation.ProjectModuleSelectExpressionFact: "project_module_select_expression_fact",
    ast_nodes.NameExpr: "name_expr",
    semantic_model.ValueType: "value_type",
    ast_nodes.LiteralExpr: "literal_expr",
    project_model.ProjectResolvedType: "project_resolved_type",
    project_model.ProjectRowSchema: "project_row_schema",
    let_scope_facts.ProjectRelationLetScopeFacts: "project_relation_let_scope_facts",
    module_semantic_fact_preservation.ProjectModuleExpressionReferenceFact: "project_module_expression_reference_fact",
    ast_nodes.ShapeDef: "shape_def",
    ast_nodes.FieldDef: "field_def",
    ast_nodes.TypeExpr: "type_expr",
    project_ir_operators.ProjectIRLogicalOperatorOccurrence: "project_ir_logical_operator_occurrence",
    ast_nodes.DottedNameExpr: "dotted_name_expr",
    project_ir_construction.ProjectIRConcreteSingleRelationFragment: "project_ir_concrete_single_relation_fragment",
    project_ir.ProjectIRInputSlotOccurrence: "project_ir_input_slot_occurrence",
    project_ir.ProjectIRUseOccurrence: "project_ir_use_occurrence",
    module_relation_resolution.ProjectResolvedModuleRelationReference: "project_resolved_module_relation_reference",
    module_attribution.ProjectDeclarationOccurrenceIdentity: "project_declaration_occurrence_identity",
    project_ir_properties.ProjectIRRelationRowOutput: "project_ir_relation_row_output",
    semantic_model.ResolvedType: "resolved_type",
    project_ir.ProjectIRPlanNodeOccurrence: "project_ir_plan_node_occurrence",
    module_semantic_fact_preservation.ProjectModuleRelationSemanticFacts: "project_module_relation_semantic_facts",
    project_ir.ProjectIRConcreteRelationSubject: "project_ir_concrete_relation_subject",
    project_ir.ProjectIRResolvedRelationAnchor: "project_ir_resolved_relation_anchor",
    module_relation_resolution.ProjectModuleRelationReference: "project_module_relation_reference",
    project_ir.ProjectIROutputValueOccurrence: "project_ir_output_value_occurrence",
    project_ir.ProjectIRRelationAnchor: "project_ir_relation_anchor",
    module_attribution.ProjectModuleDependencyFact: "project_module_dependency_fact",
    module_attribution.ProjectModuleReferenceOccurrenceIdentity: "project_module_reference_occurrence_identity",
    ast_nodes.LetBinding: "let_binding",
    module_semantic_fact_preservation.ProjectModuleLetBindingFact: "project_module_let_binding_fact",
    ast_nodes.WhereClause: "where_clause",
    module_semantic_fact_preservation.ProjectModuleWhereFact: "project_module_where_fact",
    ast_nodes.BinaryExpr: "binary_expr",
    ast_nodes.ComparisonExpr: "comparison_expr",
    ast_nodes.UnaryExpr: "unary_expr",
    ast_nodes.BetweenExpr: "between_expr",
    ast_nodes.IsNullExpr: "is_null_expr",
    project_joined_row_filter.ProjectJoinedRowRetentionEffect: "project_joined_row_retention_effect",
    ast_nodes.LetClause: "let_clause",
    project_query_block_ir.ProjectIRCompletedQueryBlockOutput: "project_ir_completed_query_block_output",
    project_query_block_ir.ProjectIRQueryBlockRelationInputEdge: "project_ir_query_block_relation_input_edge",
    project_query_block_ir.ProjectIRSetOperandInput: "project_ir_set_operand_input",
    project_query_block_ir.ProjectIRCompletedSetOperationOutput: "project_ir_completed_set_operation_output",
    project_query_block_ir.ProjectIRQueryBlockOperatorOccurrence: "project_ir_query_block_operator_occurrence",
    project_query_block_ir.ProjectIRQueryBlockResultProperties: "project_ir_query_block_result_properties",
    project_query_block_ir.ProjectIRDistinctComparison: "project_ir_distinct_comparison",
    project_query_block_ir.ProjectIRQueryBlockRowOutput: "project_ir_query_block_row_output",
    project_final_outputs.ProjectNoJoinScalarExpression: "project_no_join_scalar_expression",
    project_final_outputs.ProjectCompletedSetOutputField: "project_completed_set_output_field",
    project_final_outputs.ProjectDistinct: "project_distinct",
    project_final_outputs.ProjectDistinctFullRowUniqueness: "project_distinct_full_row_uniqueness",
    project_final_outputs.ProjectCompletedRowDomain: "project_completed_row_domain",
    project_final_outputs.ProjectRelationOrdering: "project_relation_ordering",
    project_final_outputs.ProjectRelationOrderItem: "project_relation_order_item",
    project_final_outputs.ProjectRelationOrderInput: "project_relation_order_input",
    project_final_outputs.ProjectRelationLimit: "project_relation_limit",
    project_final_outputs.ProjectSetFullRowUniqueness: "project_set_full_row_uniqueness",
    project_row_equivalence.ProjectRowEquivalenceField: "project_row_equivalence_field",
    project_grain.ProjectDistinctGrainOrigin: "project_distinct_grain_origin",
    project_set_operations.ProjectSetOperation: "project_set_operation",
    project_set_operations.ProjectSetColumn: "project_set_column",
    project_set_operations.ProjectSetOperandUse: "project_set_operand_use",
    module_resolution.ProjectResolvedModuleTypeReference: "project_resolved_module_type_reference",
    module_resolution.ProjectTypeSourceResolutionSet: "project_type_source_resolution_set",
    module_relation_resolution.ProjectResolvedSetOperand: "project_resolved_set_operand",
    project_ir_relational_properties.ProjectIROutputDeterminationResult: "project_ir_output_determination_result",
    project_ir_relational_properties.ProjectIROutputRelationalProperties: "project_ir_output_relational_properties",
    project_ir_relational_properties.ProjectIROutputValueClass: "project_ir_output_value_class",
    project_ir_relational_properties.ProjectIROutputValueClassSet: "project_ir_output_value_class_set",
    project_ir_relational_properties.ProjectIROutputFDIndex: "project_ir_output_fd_index",
    project_ir_relational_properties.ProjectIROutputStrictClosure: "project_ir_output_strict_closure",
    project_ir_relational_properties.ProjectIROutputFDProofStep: "project_ir_output_fd_proof_step",
    project_ir_relational_properties.ProjectIROutputValueFD: "project_ir_output_value_fd",
    project_ir_relational_properties.ProjectIROutputCandidateKey: "project_ir_output_candidate_key",
    project_ir_relational_properties.ProjectIRProvidedIntrinsicGrain: "project_ir_provided_intrinsic_grain",
    ast_nodes.SetOperand: "set_operand",
    ast_nodes.DistinctClause: "distinct_clause",
    ast_nodes.OrderByClause: "order_by_clause",
    ast_nodes.OrderItem: "order_item",
    ast_nodes.LimitClause: "limit_clause",
    ast_nodes.SetOperationBody: "set_operation_body",
    ast_nodes.TypeArgument: "type_argument",
    module_carrier.ProjectModuleIdentity: "project_module_identity",
    project_final_outputs.ProjectCompletedEffectiveOutput: "project_completed_effective_output",
    project_final_outputs.ProjectCompletedSetOutput: "project_completed_set_output",
    project_final_outputs.ProjectCompletedOutputField: "project_completed_output_field",
    project_final_outputs.ProjectConcreteNoJoinReplay: "project_concrete_no_join_replay",
    project_ir.ProjectIRSetInputUseOccurrence: "project_ir_set_input_use_occurrence",
    project_query_block_ir.ProjectIRQueryBlockEffectEvidence: "project_ir_query_block_effect_evidence",
    project_ir_properties.ProjectIREffectEvidence: "project_ir_effect_evidence",
    project_row_equivalence.ProjectRowEquivalence: "project_row_equivalence",
    project_row_equivalence.ProjectRowEquivalenceInput: "project_row_equivalence_input",
    project_grain.ProjectDistinctGrainFactorIdentity: "project_distinct_grain_factor_identity",
    project_grain.ProjectSetGrainOrigin: "project_set_grain_origin",
    project_grain.ProjectConcreteGrainOrigin: "project_concrete_grain_origin",
    project_grain.ProjectGrainDomainFactor: "project_grain_domain_factor",
    project_grain.ProjectSourceGrainFactorIdentity: "project_source_grain_factor_identity",
    project_grain.ProjectSetGrainFactorIdentity: "project_set_grain_factor_identity",
    module_semantic_fact_preservation.ProjectModuleOrderReferenceFact: "project_module_order_reference_fact",
    module_resolution.ProjectModuleTypeReference: "project_module_type_reference",
    module_relation_resolution.ProjectModuleSetOperandReference: "project_module_set_operand_reference",
    project_row_keys.ProjectCandidateKeyFact: "project_candidate_key_fact",
    semantic_model.DecimalPrecisionScale: "decimal_precision_scale",
    project_grain.ProjectGrainOriginIdentity: "project_grain_origin_identity",
    project_row_keys.ProjectCandidateKeyIdentity: "project_candidate_key_identity",
    project_row_keys.ProjectRowUniquenessEvidence: "project_row_uniqueness_evidence",
    project_row_keys.ProjectRowUniquenessEvidenceIdentity: "project_row_uniqueness_evidence_identity",
    project_row_keys.ProjectUniqueDeclarationOccurrence: "project_unique_declaration_occurrence",
    project_relationship_conditions.ProjectExactRowOutputConstraintScope: "project_exact_row_output_constraint_scope",
    project_row_keys.ProjectUniqueDeterminantField: "project_unique_determinant_field",
    project_row_keys.ProjectUniqueDeclarationIdentity: "project_unique_declaration_identity",
    ast_nodes.UniqueDef: "unique_def",
    module_attribution.ProjectModuleSourceFieldOrigin: "project_module_source_field_origin",
    project_final_outputs.ProjectNoJoinQualify: "project_no_join_qualify",
    project_final_outputs.ProjectNoJoinQualifyReferenceResolution: "project_no_join_qualify_reference_resolution",
    aggregate_grouped_clause_facts.ProjectRelationClauseDependencyFact: "project_relation_clause_dependency_fact",
    aggregate_grouped_clause_facts.ProjectAggregateGroupedClauseReadiness: "project_aggregate_grouped_clause_readiness",
    aggregate_grouped_schema.ProjectGroupKeyFact: "project_group_key_fact",
    aggregate_grouped_schema.ProjectAggregateExpressionAnalysis: "project_aggregate_expression_analysis",
    aggregate_grouped_schema.ProjectGroupedSelectedResult: "project_grouped_selected_result",
    module_semantic_fact_preservation.ProjectModuleWindowOutputFact: "project_module_window_output_fact",
    module_semantic_fact_preservation.ProjectModuleClauseDependencyFact: "project_module_clause_dependency_fact",
    project_window_semantics.WindowComputationInput: "window_computation_input",
    project_window_semantics.WindowDependencyOccurrence: "window_dependency_occurrence",
    project_query_block_ir.ProjectIRQueryBlockWindowPolicy: "project_ir_query_block_window_policy",
    project_query_block_ir.ProjectIRQueryBlockAggregateEvaluationContext: "project_ir_query_block_aggregate_evaluation_context",
    project_query_block_ir.ProjectIRQueryBlockWindowEvidence: "project_ir_query_block_window_evidence",
    project_query_block_ir.ProjectIRQueryBlockScalarOutput: "project_ir_query_block_scalar_output",
    project_query_block_ir.ProjectIRQueryBlockGrainOrigin: "project_ir_query_block_grain_origin",
    project_grain.ProjectGroupedGrainFactorIdentity: "project_grouped_grain_factor_identity",
    project_grain.ProjectGrainDependencyFact: "project_grain_dependency_fact",
    project_model.ProjectAggregateResultFact: "project_aggregate_result_fact",
    ast_nodes.SatisfyingClause: "satisfying_clause",
    ast_nodes.QualifyClause: "qualify_clause",
    ast_nodes.GroupByItem: "group_by_item",
    ast_nodes.WindowExpr: "window_expr",
    semantic_model.SatisfyingResultPredicateInfo: "satisfying_result_predicate_info",
    _window_identity.WindowFunctionIdentity: "window_function_identity",
    window_input_analysis.WindowInputBinding: "window_input_binding",
    semantic_window_semantics.ValidatedWindowSpecification: "validated_window_specification",
    semantic_window_semantics.WindowOrderFieldBinding: "window_order_field_binding",
    project_joined_qualify._ProjectQualifyPredicateAnalysis: "__project_qualify_predicate_analysis",
    ast_nodes.WindowSpec: "window_spec",
    window_input_analysis.WindowInputScope: "window_input_scope",
    row_dependency_graph.ProjectRowDependencyNode: "project_row_dependency_node",
    errors.SourceLocation: "source_location",
    semantic_window_semantics.ResolvedWindowSpecification: "resolved_window_specification",
    semantic_window_semantics.WindowFunctionFramePolicy: "window_function_frame_policy",
    semantic_window_semantics.ValidatedFrameNotApplicable: "validated_frame_not_applicable",
    project_ir.ProjectIRStageFieldAnchor: "project_ir_stage_field_anchor",
    project_ir.ProjectIRPlanNodeRef: "project_ir_plan_node_ref",
    semantic_window_semantics.ResolvedWindowFrame: "resolved_window_frame",
    semantic_window_semantics.ResolvedNamedWindowTemplate: "resolved_named_window_template",
    semantic_window_semantics.AuthoredWindowSpecification: "authored_window_specification",
    semantic_window_semantics.ResolvedNamedWindowUse: "resolved_named_window_use",
    semantic_window_semantics.ResolvedWindowFunctionModifiers: "resolved_window_function_modifiers",
    semantic_window_semantics.ValidatedFrame: "validated_frame",
    semantic_window_semantics.WindowPartitionFieldBinding: "window_partition_field_binding",
    semantic_window_semantics.FrameValueWindowComputation: "frame_value_window_computation",
    semantic_window_semantics.FrameValueWindowSemanticFact: "frame_value_window_semantic_fact",
    semantic_window_semantics.NavigationOffsetFact: "navigation_offset_fact",
    semantic_window_semantics.NavigationDefaultFact: "navigation_default_fact",
    semantic_window_semantics.NavigationWindowComputation: "navigation_window_computation",
    semantic_window_semantics.NavigationWindowSemanticFact: "navigation_window_semantic_fact",
    ast_nodes.WindowFrameBound: "window_frame_bound",
    ast_nodes.AuthoredWindowFrame: "authored_window_frame",
    ast_nodes.AuthoredWindowNullTreatment: "authored_window_null_treatment",
    semantic_window_semantics.ResolvedNamedWindowNamespace: "resolved_named_window_namespace",
    targets.ProjectSQLTargetLookup: "project_sql_target_lookup",
    targets.ProjectSQLTargetAspect: "project_sql_target_aspect",
    targets.ProjectSQLTargetDemand: "project_sql_target_demand",
    targets.ProjectSQLTargetSummary: "project_sql_target_summary",
    targets.TargetCatalogResidual: "target_catalog_residual",
    project_sql_plan_target_mapping.ProjectSQLTargetProposition: "project_sql_target_proposition",
    capability_lookup.Found: "found",
    capability_lookup.Absent: "absent",
    capability_lookup.Unknown: "unknown",
    capability_lookup.Conflict: "conflict",
    capability_facts.CapabilityKey: "capability_key",
    capability_facts.CapabilityFact: "capability_fact",
    capability_facts.CapabilityEvidence: "capability_evidence",
    capability_providers.CanonicalCapabilityProviderInputs: "canonical_capability_provider_inputs",
    capability_profiles.CapabilityProfileTarget: "capability_profile_target",
    capability_profiles.CapabilityProfileReference: "capability_profile_reference",
    capability_profiles.CapabilityProfileIdentity: "capability_profile_identity",
    capability_profiles.StaticCapabilityProfile: "static_capability_profile",
    capability_profiles.CapabilityProfileBaseOccurrence: "capability_profile_base_occurrence",
    capability_profiles.CapabilityProfileFactOccurrence: "capability_profile_fact_occurrence",
    capability_composition.CapabilityProfileCompositionSuccess: "capability_profile_composition_success",
    capability_composition.CapabilityProfileCompositionBlocked: "capability_profile_composition_blocked",
    capability_composition.EffectiveCapabilityProfileFactOccurrence: "effective_capability_profile_fact_occurrence",
    targets.ProjectSQLTargetAssessment: "project_sql_target_assessment",
    targets.ProjectSQLTargetRequest: "project_sql_target_request",
    capability_facts.CapabilityDisposition: "capability_disposition",
    errors.Diagnostic: "diagnostic",
    project_query_block_ir_algebra.ProjectIRJoinInputCorrespondence: "project_ir_join_input_correspondence",
    ast_nodes.JoinClause: "join_clause",
    ast_nodes.JoinOnClause: "join_on_clause",
    project_join_conditions.ProjectJoinCondition: "project_join_condition",
    project_scalar_namespaces.ProjectConcreteJoinedNamespaceExpression: "project_concrete_joined_namespace_expression",
    project_scalar_namespaces.ProjectJoinedScalarNamespace: "project_joined_scalar_namespace",
    project_scalar_references.ProjectScalarReferenceResolution: "project_scalar_reference_resolution",
    project_scalar_references.ProjectScalarEnvironmentField: "project_scalar_environment_field",
    project_query_block_ir_algebra.ProjectIRComposedJoin: "project_ir_composed_join",
    project_join_conditions.ProjectJoinConditionField: "project_join_condition_field",
    project_ir_properties.ProjectIRJoinedRowField: "project_ir_joined_row_field",
    project_joined_row_filter.ProjectConcreteJoinedRowFilter: "project_concrete_joined_row_filter",
    project_query_block_ir.ProjectIRSingleMatchRetention: "project_ir_single_match_retention",
    project_single_match.ProjectSingleMatchRequest: "project_single_match_request",
    project_single_match.ProjectSingleMatchAssessment: "project_single_match_assessment",
    project_relationship_uses.ProjectRelationBindingOccurrence: "project_relation_binding_occurrence",
    project_ir_properties.ProjectIRJoinRowOutput: "project_ir_join_row_output",
    project_joined_qualify.ProjectConcreteJoinedQualify: "project_concrete_joined_qualify",
    project_grain.ProjectJoinGrainFactorIdentity: "project_join_grain_factor_identity",
    project_current_joins.ProjectCurrentJoinGrainWitness: "project_current_join_grain_witness",
    project_scalar_namespaces.ProjectJoinedLetValue: "project_joined_let_value",
    project_joined_aggregation.ProjectJoinedSatisfyingAnalysis: "project_joined_satisfying_analysis",
    project_join_conditions.ProjectJoinConditionReference: "project_join_condition_reference",
    project_scalar_namespaces.ProjectJoinedLetReferenceResolution: "project_joined_let_reference_resolution",
    project_joined_aggregation.ProjectJoinedSatisfyingOutputReference: "project_joined_satisfying_output_reference",
    project_scalar_namespaces.ProjectJoinedLetOccurrence: "project_joined_let_occurrence",
    project_joined_aggregation.ProjectJoinedGroupKeyOccurrence: "project_joined_group_key_occurrence",
    project_joined_aggregation.ProjectJoinedAggregateOccurrence: "project_joined_aggregate_occurrence",
    project_joined_aggregation.ProjectJoinedStageOutputOccurrence: "project_joined_stage_output_occurrence",
    project_joined_aggregation.ProjectJoinedGroupProtection: "project_joined_group_protection",
    project_joined_aggregation.ProjectJoinedAggregateGrainLinkage: "project_joined_aggregate_grain_linkage",
    project_joined_aggregation.ProjectJoinedAggregatePairLinkage: "project_joined_aggregate_pair_linkage",
    project_joined_aggregation.ProjectConcreteJoinedAggregation: "project_concrete_joined_aggregation",
    project_current_joins.ProjectCurrentBinaryJoin: "project_current_binary_join",
    project_final_outputs.ProjectNoJoinHiddenWindowComputation: "project_no_join_hidden_window_computation",
    project_final_outputs.ProjectNoJoinWindowInput: "project_no_join_window_input",
    project_final_outputs.ProjectNoJoinHiddenWindowInputUse: "project_no_join_hidden_window_input_use",
    project_ir_properties.ProjectIRProvidedEvaluationPolicy: "project_ir_provided_evaluation_policy",
    ast_nodes.NamedWindowDeclaration: "named_window_declaration",
    ast_nodes.NamedWindowReference: "named_window_reference",
    semantic_window_semantics.NamedWindowBaseResolution: "named_window_base_resolution",
    semantic_window_semantics.ComposedNamedWindowUse: "composed_named_window_use",
    semantic_window_semantics.NamedWindowComponentProvenance: "named_window_component_provenance",
    semantic_window_semantics.QueryBlockOccurrence: "query_block_occurrence",
    semantic_window_semantics.WindowExpressionSemanticFact: "window_expression_semantic_fact",
    generic_compatibility.SignatureMatch: "signature_match",
    nullability_formulas.NullabilityEvaluationMatch: "nullability_evaluation_match",
    project_ir_properties.ProjectIRStageScalarFieldOutput: "project_ir_stage_scalar_field_output",
    semantic_window_semantics.NamedWindowOccurrence: "named_window_occurrence",
    project_ir.ProjectIRJoinInputUseOccurrence: "project_ir_join_input_use_occurrence",
    project_relationship_uses.ProjectNonConcreteJoinUse: "project_non_concrete_join_use",
    project_scalar_references.ProjectScalarReferenceOccurrence: "project_scalar_reference_occurrence",
    project_completion.ProjectEffectiveOutputTerminal: "project_effective_output_terminal",
    project_relationship_uses.ProjectRelationBindingIdentity: "project_relation_binding_identity",
    project_ir.ProjectIRUseRef: "project_ir_use_ref",
    project_joined_row_semantics.ProjectJoinedRowFieldSemantics: "project_joined_row_field_semantics",
    project_multifact.ProjectCurrentMultiFactRegion: "project_current_multi_fact_region",
    project_grain.ProjectGrainFactorSet: "project_grain_factor_set",
    project_multifact.ProjectFactContextualGrain: "project_fact_contextual_grain",
    project_multifact.ProjectFactGrainComparison: "project_fact_grain_comparison",
    project_multifact.ProjectCommonGrainResult: "project_common_grain_result",
    project_join_conditions.ProjectJoinNullRejection: "project_join_null_rejection",
    project_joined_aggregation.ProjectJoinedAggregateFieldDependency: "project_joined_aggregate_field_dependency",
    semantic_window_semantics.WindowComputationAnalysis: "window_computation_analysis",
    semantic_window_semantics.WindowUseOccurrence: "window_use_occurrence",
    semantic_window_semantics.WindowOccurrenceIdentity: "window_occurrence_identity",
    semantic_window_semantics.WindowResultAvailability: "window_result_availability",
    generic_compatibility.LogicalTypeIdentity: "logical_type_identity",
    nullability_formulas.NullabilityEvaluationEvidence: "nullability_evaluation_evidence",
    project_ir_properties.ProjectIRStageRowField: "project_ir_stage_row_field",
    generic_compatibility.TypeVariableBinding: "type_variable_binding",
    project_relationship_uses.ProjectJoinUseIdentity: "project_join_use_identity",
    project_query_block.ProjectConcreteQueryBlock: "project_concrete_query_block",
    project_grain.ProjectGrainFactorUniverse: "project_grain_factor_universe",
    project_multifact.ProjectFactGrainDetermination: "project_fact_grain_determination",
    project_multifact.ProjectActualGrainCandidate: "project_actual_grain_candidate",
    project_current_joins.ProjectCurrentJoinProperties: "project_current_join_properties",
    project_multifact.ProjectCommonGrainCandidateEvidence: "project_common_grain_candidate_evidence",
    nullability_formulas.NullabilityDefaultEvidence: "nullability_default_evidence",
    nullability_formulas.NullabilityArgumentEvidence: "nullability_argument_evidence",
    project_query_block.ProjectQueryBlockOwnerBridge: "project_query_block_owner_bridge",
    project_grain.ProjectGrainDependencyIndex: "project_grain_dependency_index",
    project_ir_properties.ProjectIRProvidedNullExtension: "project_ir_provided_null_extension",
    project_ir_joins.ProjectIRJoinUnavailableProperty: "project_ir_join_unavailable_property",
    project_multifact.ProjectActualGrainAuthority: "project_actual_grain_authority",
    project_ir_joins.ProjectIRJoinMatchFieldPair: "project_ir_join_match_field_pair",
    project_relationship_match_guarantees.ProjectDirectionalRelationshipMatchGuarantee: "project_directional_relationship_match_guarantee",
    project_query_block_ir.ProjectIRSingleMatchProofImage: "project_ir_single_match_proof_image",
    ast_nodes.RelationshipMetadata: "relationship_metadata",
    project_ir_joins.ProjectIRBinaryJoinOccurrence: "project_ir_binary_join_occurrence",
    project_relationship_uses.ProjectConcreteJoinUse: "project_concrete_join_use",
    project_relationship_paths.ProjectRelationshipPath: "project_relationship_path",
    project_relationship_paths.ProjectRelationshipPathStep: "project_relationship_path_step",
    ast_nodes.JoinTraversalStep: "join_traversal_step",
    project_ir_joins.ProjectIRJoinGrainWitness: "project_ir_join_grain_witness",
    project_single_match.ProjectSingleMatchProof: "project_single_match_proof",
    project_relationship_conditions.ProjectRelationshipEqualityCorrespondence: "project_relationship_equality_correspondence",
    project_relationship_match_guarantees.ProjectRelationshipDirectionIdentity: "project_relationship_direction_identity",
    project_relationship_match_guarantees.ProjectAtMostOneEvidence: "project_at_most_one_evidence",
    project_relationship_match_guarantees.ProjectAbsentReferentialCoverage: "project_absent_referential_coverage",
    ast_nodes.RelationshipMatchClause: "relationship_match_clause",
    project_ir_joins.ProjectIRBinaryJoinIdentity: "project_ir_binary_join_identity",
    project_relationship_conditions.ProjectConcreteRelationshipCondition: "project_concrete_relationship_condition",
    project_relationship_conditions.ProjectRelationshipCorrespondenceIdentity: "project_relationship_correspondence_identity",
    project_relationship_conditions.ProjectRelationshipEndpointFieldReferenceOccurrence: "project_relationship_endpoint_field_reference_occurrence",
    ast_nodes.RelationshipEndpoint: "relationship_endpoint",
    project_relationship_uses.ProjectTraversalStepUse: "project_traversal_step_use",
    project_relationships.ProjectRelationshipDeclarationIdentity: "project_relationship_declaration_identity",
    project_relationships.ProjectRelationshipEndpointOccurrence: "project_relationship_endpoint_occurrence",
    project_relationship_conditions.ProjectRelationshipBaseMatchIdentity: "project_relationship_base_match_identity",
    project_relationships.ProjectConcreteRelationshipSubject: "project_concrete_relationship_subject",
    project_relationship_conditions.ProjectRelationshipEndpointFieldReferenceIdentity: "project_relationship_endpoint_field_reference_identity",
    project_relationship_uses.ProjectTraversalStepUseIdentity: "project_traversal_step_use_identity",
    project_relationships.ProjectRelationshipEndpointIdentity: "project_relationship_endpoint_identity",
    project_relationships.ProjectRelationshipDeclarationOccurrence: "project_relationship_declaration_occurrence",
    project_ir_properties.ProjectIRPropertyStage: "project_ir_property_stage",
    project_ir_properties.ProjectIRProvidedCardinalityUpperBound: "project_ir_provided_cardinality_upper_bound",
    project_ir_properties.ProjectIRProvidedRelationOrdering: "project_ir_provided_relation_ordering",
    project_ir_properties.ProjectIRProvidedOutputShape: "project_ir_provided_output_shape",
    project_ir_properties.ProjectIRProvidedBagMultiplicity: "project_ir_provided_bag_multiplicity",
    project_ir_properties.ProjectIRProvidedClosedBindings: "project_ir_provided_closed_bindings",
    project_ir_properties.ProjectIRScalarFieldOutput: "project_ir_scalar_field_output",
    project_ir_properties.ProjectIRRowField: "project_ir_row_field",
    project_ir.ProjectIRFieldAnchor: "project_ir_field_anchor",
    ast_nodes.AuthoredWindowNthDirection: "authored_window_nth_direction",
    semantic_window_semantics.NthValuePositionFact: "nth_value_position_fact",
    project_current_join_inputs.ProjectCurrentMaterializedInput: "project_current_materialized_input",
    project_current_join_inputs.ProjectCurrentInputField: "project_current_input_field",
    project_final_outputs.ProjectCurrentInputGrainAuthority: "project_current_input_grain_authority",
    capability_composition.CapabilityProfileCompositionBlocker: "capability_profile_composition_blocker",
    extension_signature_provider.ExtensionSignatureProviderContext: "extension_signature_provider_context",
    extension_signature_requirements.ExtensionSignatureRequirementSelectorOccurrence: "extension_signature_requirement_selector_occurrence",
    extension_signature_provider.ExtensionSignatureProviderSelectionOccurrence: "extension_signature_provider_selection_occurrence",
    project_final_outputs.ProjectEffectiveJoinInputAuthority: "project_effective_join_input_authority",
    extension_signature_requirements.ExtensionSignatureRequirementSelectors: "extension_signature_requirement_selectors",
    extension_catalog_availability.ExtensionCatalogSelectionResult: "extension_catalog_selection_result",
    extension_signature_requirements.ExtensionSignatureRequirementSelector: "extension_signature_requirement_selector",
    capability_profiles.CapabilityRequirementCollection: "capability_requirement_collection",
    extension_catalog.ExtensionCatalogTarget: "extension_catalog_target",
    extension_catalog_availability.DeclaredExtensionCatalogAvailability: "declared_extension_catalog_availability",
    extension_catalog.ConstructedExtensionCatalog: "constructed_extension_catalog",
    extension_catalog.ExtensionCatalogLookupScope: "extension_catalog_lookup_scope",
    extension_catalog_availability.ExtensionCatalogAvailabilityDeclaration: "extension_catalog_availability_declaration",
    extension_catalog_availability.ExtensionCatalogSelectionCandidate: "extension_catalog_selection_candidate",
    capability_profiles.CapabilityRequirementCollectionIdentity: "capability_requirement_collection_identity",
    capability_profiles.CapabilityRequirementOccurrence: "capability_requirement_occurrence",
    extension_catalog.ExtensionCatalogMetadata: "extension_catalog_metadata",
    extension_catalog.PostgreSQLCallableIdentity: "postgre_sql_callable_identity",
    extension_catalog_availability.ExtensionCatalogSelectionCandidateIdentity: "extension_catalog_selection_candidate_identity",
    extension_catalog.ExtensionCatalogIdentity: "extension_catalog_identity",
    extension_catalog.ExtensionCatalogReference: "extension_catalog_reference",
    extension_catalog.ExtensionCatalogSourceProvenance: "extension_catalog_source_provenance",
    extension_catalog.ExtensionCatalogSourceOccurrence: "extension_catalog_source_occurrence",
    extension_catalog.ExtensionCatalogTypeReference: "extension_catalog_type_reference",
    extension_catalog.PostgreSQLOperatorIdentity: "postgre_sql_operator_identity",
    extension_catalog.PostgreSQLCastIdentity: "postgre_sql_cast_identity",
    extension_catalog.ExtensionCatalogDeclarationTypeUse: "extension_catalog_declaration_type_use",
    extension_catalog.ExtensionCatalogEntryEvidence: "extension_catalog_entry_evidence",
    extension_catalog.PostgreSQLCallableDeclaration: "postgre_sql_callable_declaration",
    extension_catalog.ExtensionNativeTypeCatalogEntry: "extension_native_type_catalog_entry",
    extension_catalog.ExtensionScalarFunctionCatalogEntry: "extension_scalar_function_catalog_entry",
    extension_catalog.ExtensionAggregateCatalogEntry: "extension_aggregate_catalog_entry",
    extension_catalog.ExtensionOperatorCatalogEntry: "extension_operator_catalog_entry",
    extension_catalog.ExtensionCastCatalogEntry: "extension_cast_catalog_entry",
    extension_catalog.ExtensionCatalogCompletenessClaim: "extension_catalog_completeness_claim",
    ast_nodes.TypeDef: "type_def",
    module_attribution.ProjectModuleReferenceAttribution: "project_module_reference_attribution",
    module_resolution.ProjectResolvedNominalSymbol: "project_resolved_nominal_symbol",
    module_catalog.ProjectNominalDeclarationIdentity: "project_nominal_declaration_identity",
    ast_nodes.ImportItem: "import_item",
    ast_nodes.ImportStatement: "import_statement",
    ast_nodes.ExportItem: "export_item",
    ast_nodes.ExportStatement: "export_statement",
    module_attribution.ProjectModuleImportAttribution: "project_module_import_attribution",
    module_attribution.ProjectModuleAccessHop: "project_module_access_hop",
    module_attribution.ProjectModuleFacadeAttribution: "project_module_facade_attribution",
    module_bindings.ProjectResolvedImportedBinding: "project_resolved_imported_binding",
    module_attribution.ProjectModuleImportOccurrenceIdentity: "project_module_import_occurrence_identity",
    project_model.ProjectRoot: "project_root",
    module_bindings.ProjectModuleImportRequest: "project_module_import_request",
    module_attribution.ProjectModuleFacadeOccurrenceIdentity: "project_module_facade_occurrence_identity",
    module_exports.ProjectModuleExportEntry: "project_module_export_entry",
    module_bindings.ProjectImportedBindingIdentity: "project_imported_binding_identity",
    module_exports.ProjectModuleExportRequest: "project_module_export_request",
    module_exports.ProjectImportedExportCandidate: "project_imported_export_candidate",
    project_joined_qualify.ProjectQualifyReferenceResolution: "project_qualify_reference_resolution",
    project_joined_windows.ProjectConcreteWindowComputation: "project_concrete_window_computation",
    project_joined_windows.ProjectSelectedWindowResultBinding: "project_selected_window_result_binding",
    project_joined_windows.ProjectJoinedWindowInputNamespace: "project_joined_window_input_namespace",
    project_joined_windows.ProjectWindowDependencyOccurrence: "project_window_dependency_occurrence",
    project_joined_windows.ProjectJoinedWindowInputBinding: "project_joined_window_input_binding",
    ast_nodes.EnumDef: "enum_def",
    ast_nodes.EnsureClause: "ensure_clause",
    ast_nodes.Annotation: "annotation",
    project_joined_windows.ProjectConcreteJoinedWindowStage: "project_concrete_joined_window_stage",
    project_joined_windows.ProjectWindowComputationSite: "project_window_computation_site",
    project_joined_windows.ProjectJoinedWindowInputResolution: "project_joined_window_input_resolution",
    aggregate_grouped_schema.ProjectAggregateSelectedResult: "project_aggregate_selected_result",
    project_ir_evaluation_context.ProjectIRAggregateEvaluationContext: "project_ir_aggregate_evaluation_context",
    project_relationship_match_guarantees.ProjectRefinedMatchBounds: "project_refined_match_bounds",
    project_query_block_ir.ProjectIRReboundExistingOutput: "project_ir_rebound_existing_output",
}

_ENUMS: tuple[type[Enum], ...] = (
    plans.ProjectSQLPlanRefKind,
    plans.ProjectSQLBoundaryReason,
    plans.ProjectSQLSymbolNamespace,
    project_sql_plan_expressions.ProjectSQLStageKind,
    plans.ProjectSQLOriginRole,
    plans.ProjectSQLOriginProvenance,
    project_model.ProjectRowFieldNullability,
    project_sql_plan_literals.ProjectSQLLiteralPolicy,
    project_sql_plan_expressions.ProjectSQLExpressionRole,
    project_sql_plan_expressions.ProjectSQLStagePortKind,
    project_sql_plan_literals.ProjectSQLLiteralRole,
    project_sql_plan_literals.ProjectSQLLiteralDisposition,
    project_sql_plan_literals.ProjectSQLLiteralReason,
    project_sql_plan_literals.ProjectSQLLiteralTag,
    project_sql_plan_literals.ProjectSQLLiteralRequirement,
    project_sql_plan_results.ProjectSQLResultKind,
    project_sql_plan_results.ProjectSQLResultPortRole,
    project_sql_plan_results.ProjectSQLResultDemandKind,
    ast_nodes.SetOperationKind,
    ast_nodes.SetOperationQuantifier,
    project_set_operations.ProjectSetMultiplicityLaw,
    project_sql_plan_sets.ProjectSQLSetDemandKind,
    project_sql_plan_joins.ProjectSQLJoinPortKind,
    ast_nodes.AuthoredJoinKind,
    project_sql_plan_joins.ProjectSQLJoinRows,
    project_sql_plan_joins.ProjectSQLJoinDemandKind,
    project_joined_aggregation.ProjectJoinedAggregationMode,
    project_sql_plan_aggregation.ProjectSQLAggregateEmptyInput,
    project_sql_plan_aggregation.ProjectSQLAggregateDemandKind,
    project_window_semantics.WindowDependencyRole,
    project_sql_plan_windows.ProjectSQLWindowArgumentRole,
    semantic_window_semantics.RankingAdvancePolicy,
    semantic_window_semantics.DistributionWindowPolicy,
    project_sql_plan_windows.ProjectSQLWindowDemandKind,
    reports.ProjectSQLDemandFamily,
    reports.ProjectSQLDemandLinkKind,
    project_single_match.ProjectSingleMatchState,
    reports.ProjectSQLRealizationPosture,
    reports.ProjectSQLAggregateEvidenceKind,
    reports.ProjectSQLReportTargetPosture,
    maps.ProjectSQLPositionAvailability,
    maps.ProjectSQLSourceNature,
    maps.ProjectSQLSourceAssociationKind,
    maps.ProjectSQLSourceEndpointKind,
    ast_nodes.ModuleDeclarationKind,
    module_carrier.ProjectCompilationMode,
    project_model.ProjectSymbolNamespace,
    project_model.ProjectSymbolKind,
    module_attribution.ProjectModuleRowFieldKind,
    project_model.ProjectRowResultRole,
    semantic_model.EffectiveNullability,
    semantic_model.ValueTypeKind,
    project_model.ProjectResolvedTypeKind,
    let_scope_facts.ProjectLetScopeFactsStatus,
    let_scope_facts.ProjectLetScopeFactsReason,
    module_semantic_fact_preservation.ProjectModuleFactOccurrenceRole,
    module_semantic_fact_preservation.ProjectModuleWhereReferenceRole,
    module_semantic_fact_preservation.ProjectModuleCandidateBucketStatus,
    ast_nodes.Nullability,
    project_ir_operators.ProjectIRLogicalOperatorKind,
    semantic_model.TypeKind,
    module_attribution.ProjectModuleDependencyKind,
    module_attribution.ProjectModuleReferenceRole,
    project_joined_row_filter.ProjectSQLPredicateTruth,
    project_query_block_ir.ProjectIRQueryBlockOperatorExtensionKind,
    project_joined_row_filter.ProjectJoinedRowMultiplicity,
    project_final_outputs.ProjectNoJoinScalarStatus,
    project_final_outputs.ProjectCompletedRowDomainKind,
    project_final_outputs.ProjectRelationOrderDirection,
    project_row_equivalence.ProjectRowEquivalenceReason,
    project_grain.ProjectGrainOriginKind,
    project_ir_relational_properties.ProjectIROutputDeterminationStatus,
    project_row_keys.ProjectRowUniquenessStrength,
    project_grain.ProjectGrainBasisState,
    project_ir_properties.ProjectIRDeterminismEvidence,
    project_ir_properties.ProjectIRErrorBehaviorEvidence,
    project_ir_properties.ProjectIRSideEffectEvidence,
    project_ir_properties.ProjectIREvaluationCountEvidence,
    project_grain.ProjectGrainFactorKind,
    module_semantic_fact_preservation.ProjectModuleOrderReferenceRole,
    module_resolution.ProjectModuleTypeReferenceRole,
    project_row_keys.ProjectUniqueNullPolicy,
    project_row_keys.ProjectConstraintEvidenceOrigin,
    project_row_keys.ProjectConstraintEvidenceTrust,
    project_row_keys.ProjectConstraintEnforcementPosture,
    project_relationship_conditions.ProjectRelationshipConstraintScopeKind,
    project_final_outputs.ProjectNoJoinQualifyKind,
    aggregate_grouped_clause_facts.ProjectRelationClauseDependencyKind,
    aggregate_grouped_clause_facts.ProjectAggregateGroupedClauseReadinessStatus,
    aggregate_grouped_clause_facts.ProjectAggregateGroupedClauseReadinessReason,
    ast_nodes.WindowUseKind,
    _window_identity.WindowFunctionRole,
    window_input_analysis.WindowInputOriginKind,
    project_joined_qualify._ProjectQualifyPredicateNonConcreteReason,
    window_input_analysis.WindowInputScopeKind,
    row_dependency_graph.ProjectRowDependencyNodeKind,
    semantic_window_semantics.WindowComponentOrigin,
    semantic_window_semantics.WindowFunctionFramePolicyKind,
    semantic_window_semantics.WindowFrameApplicability,
    ast_nodes.WindowFrameUnit,
    semantic_window_semantics.WindowFrameExclusion,
    semantic_window_semantics.WindowNullTreatment,
    semantic_window_semantics.WindowNthDirection,
    semantic_window_semantics.WindowFrameEmptinessClassification,
    semantic_window_semantics.FrameValueFunctionKind,
    semantic_window_semantics.NavigationDirection,
    ast_nodes.WindowFrameBoundKind,
    ast_nodes.AuthoredWindowFrameKind,
    ast_nodes.AuthoredWindowFrameExclusion,
    ast_nodes.WindowNullTreatmentKind,
    project_sql_plan_target_mapping.PropositionKind,
    targets.AspectOutcome,
    targets.AssessmentPosture,
    targets.TargetInputIssue,
    project_sql_plan_target_mapping.MappingGap,
    capability_facts.CapabilityReasonCode,
    capability_facts.CapabilityDomain,
    capability_facts.CapabilitySupport,
    capability_facts.CapabilityEvidenceSource,
    capability_profiles.CapabilityProfileTargetKind,
    capability_profiles.CapabilityProfileSchemaVersion,
    capability_profiles.CapabilityProfileKind,
    capability_facts.CapabilityDispositionKind,
    errors.Severity,
    project_join_conditions.ProjectJoinConditionState,
    project_scalar_namespaces.ProjectScalarNamespaceStage,
    project_joined_row_filter.ProjectJoinedRowFilterKind,
    project_single_match.ProjectSingleMatchScope,
    project_single_match.ProjectSingleMatchUnit,
    project_relationship_uses.ProjectJoinUseState,
    project_joined_qualify.ProjectJoinedQualifyStageKind,
    project_joined_aggregation.ProjectJoinedSatisfyingStatus,
    project_join_conditions.ProjectJoinReferenceState,
    project_joined_aggregation.ProjectJoinedStageOutputRole,
    project_multifact.ProjectMultiFactMultiplicityRisk,
    project_multifact.ProjectMultiFactRequirement,
    project_multifact.ProjectMultiFactStructuralAlignment,
    semantic_window_semantics.NamedWindowComponentKind,
    semantic_window_semantics.QueryBlockKind,
    semantic_window_semantics.WindowExpressionStage,
    project_completion.ProjectEffectiveOutputTerminalReason,
    project_ir_relational_properties.ProjectIRGrainComparisonStatus,
    project_multifact.ProjectCommonGrainStatus,
    semantic_window_semantics.WindowResultAvailabilityKind,
    nullability_formulas.NullabilityFormulaKind,
    project_ir_relational_properties.ProjectIRGrainDirectionStatus,
    project_ir_properties.ProjectIRProvidedPropertySlot,
    project_ir_properties.ProjectIRPropertyAvailability,
    project_multifact.ProjectActualGrainAuthorityKind,
    project_relationship_match_guarantees.ProjectRelationshipMinimumBound,
    project_relationship_match_guarantees.ProjectMatchGuaranteeFallbackReason,
    project_relationship_match_guarantees.ProjectRelationshipMaximumBound,
    project_ir_joins.ProjectIRBinaryJoinKind,
    project_single_match.ProjectSingleMatchProofKind,
    project_relationship_conditions.ProjectRelationshipEqualitySemantics,
    project_relationship_match_guarantees.ProjectReferentialCoverageState,
    project_relationship_conditions.ProjectRelationshipConditionScope,
    ast_nodes.WindowNthDirectionKind,
    capability_composition.CapabilityProfileCompositionBlockerKind,
    extension_catalog_availability.ExtensionCatalogSelectionOutcome,
    extension_catalog.ExtensionCatalogEntryFamily,
    extension_catalog_availability.ExtensionCatalogAvailabilityOwner,
    extension_catalog.ExtensionCatalogSchemaVersion,
    extension_catalog.ExtensionCatalogTypeReferenceKind,
    extension_catalog.PostgreSQLOperatorArity,
    extension_catalog.ExtensionCatalogDeclarationTypeUseKind,
    extension_catalog.ExtensionCatalogUnmodeledReason,
    extension_catalog.ExtensionCatalogMatchability,
    extension_catalog.ExtensionCatalogExposure,
    extension_catalog.PostgreSQLNullCallBehavior,
    extension_catalog.PostgreSQLVolatility,
    extension_catalog.PostgreSQLParallelSafety,
    extension_catalog.PostgreSQLAggregateKind,
    extension_catalog.PostgreSQLCastContext,
    extension_catalog.PostgreSQLCastMethod,
    extension_catalog.ExtensionCatalogCompletenessClaimKind,
    module_exports.ProjectModuleExportEntryOrigin,
    module_exports.ProjectImportedBindingCandidateProof,
    project_joined_windows.ProjectJoinedWindowInputBindingKind,
    project_joined_windows.ProjectJoinedWindowStageKind,
    project_joined_windows.ProjectWindowComputationSiteKind,
)
