"""Closed data vocabulary for the private Phase65 SQL-plan observation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

__all__: tuple[str, ...] = ()

FORMAT = "pietto.phase65-sql-plan-observation.v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 32768
MAX_EDGES = 131072
MAX_DEPTH = 64
MAX_TEXT = 262144
MAX_DIGITS = 4096


class Tag(StrEnum):
    ABSENT = "absent"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float_hex"
    TEXT = "text"
    ENUM = "enum"
    REF = "ref"
    SEQUENCE = "sequence"
    MAPPING = "mapping"


@dataclass(frozen=True, slots=True)
class Ref:
    domain: str
    position: int


@dataclass(frozen=True, slots=True)
class Value:
    tag: Tag
    data: None | bool | str | Ref | tuple[Value, ...]


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    value: Value


@dataclass(frozen=True, slots=True)
class Record:
    kind: str
    ref: Ref
    fields: tuple[Field, ...]


@dataclass(frozen=True, slots=True)
class Document:
    format: str
    records: tuple[Record, ...]


@dataclass(frozen=True, slots=True)
class Shape:
    tags: tuple[Tag, ...]
    domains: tuple[str, ...] = ()
    enums: tuple[str, ...] = ()
    items: Shape | None = None
    keys: Shape | None = None


@dataclass(frozen=True, slots=True)
class FieldRule:
    name: str
    shape: Shape


@dataclass(frozen=True, slots=True)
class RecordRule:
    domain: str
    fields: tuple[FieldRule, ...]


# Field shapes are finite; this grammar is private module construction only.
ABSENT = Shape((Tag.ABSENT,))
BOOLEAN = Shape((Tag.BOOLEAN,))
INTEGER = Shape((Tag.INTEGER,))
FLOAT = Shape((Tag.FLOAT,))
TEXT = Shape((Tag.TEXT,))
optional = ABSENT
ANCHOR = Shape(
    (Tag.REF,),
    domains=(
        "project_sql_plan_scope",
        "project_sql_plan_ref",
        "project_sql_port",
        "project_sql_definition",
        "project_sql_source_binding",
        "project_sql_input_use",
        "project_sql_boundary",
        "project_sql_symbol",
        "project_sql_select_block",
        "project_sql_projection",
        "project_sql_origin",
        "project_sql_source_realization_demand",
        "project_sql_export_representation_demand",
        "project_sql_bindings",
        "project_sql_plan",
        "project_sql_expression_site",
        "project_sql_joined_site",
        "project_sql_match_site",
        "project_sql_literal",
        "project_sql_bound_literal",
        "project_sql_reference",
        "project_sql_joined_reference",
        "project_sql_match_reference",
        "project_sql_unary",
        "project_sql_binary",
        "project_sql_comparison",
        "project_sql_is_null",
        "project_sql_between",
        "project_sql_expression_operand",
        "project_sql_stage_port",
        "project_sql_let_value",
        "project_sql_filter",
        "project_sql_expression_demand",
        "project_sql_stage_value_demand",
        "project_sql_filter_demand",
        "project_sql_scope_demand",
        "project_sql_literal_position",
        "project_sql_literal_site",
        "project_sql_literal_slot",
        "project_sql_fixed_literal_value",
        "project_sql_bind_use",
        "project_sql_fixed_envelope",
        "project_sql_literal_demand",
        "project_sql_result_boundary",
        "project_sql_result_port",
        "project_sql_distinct",
        "project_sql_quotient_field",
        "project_sql_order",
        "project_sql_order_item",
        "project_sql_order_expression",
        "project_sql_order_use",
        "project_sql_hidden_order_requirement",
        "project_sql_result_limit",
        "project_sql_result_export",
        "project_sql_result_demand",
        "project_sql_set_body",
        "project_sql_set_operand",
        "project_sql_set_input",
        "project_sql_set_column",
        "project_sql_set_demand",
        "project_sql_join_input",
        "project_sql_join_port",
        "project_sql_relationship_match",
        "project_sql_join",
        "project_sql_join_tail",
        "project_sql_single_match",
        "project_sql_single_match_proof",
        "project_sql_join_demand",
        "project_sql_aggregation_authority",
        "project_sql_aggregation",
        "project_sql_group_key",
        "project_sql_aggregate",
        "project_sql_aggregate_site",
        "project_sql_result_reference",
        "project_sql_aggregate_argument_call",
        "project_sql_aggregate_projection",
        "project_sql_aggregate_risk",
        "project_sql_aggregate_demand",
        "project_sql_window",
        "project_sql_window_use",
        "project_sql_window_argument",
        "project_sql_window_policy",
        "project_sql_qualify_site",
        "project_sql_window_reference",
        "project_sql_window_projection",
        "project_sql_window_demand",
        "project_sql_demand_scope",
        "project_sql_demand_entry",
        "project_sql_demand_link",
        "project_sql_single_match_report",
        "project_sql_hidden_order_report",
        "project_sql_aggregate_evidence_report",
        "project_sql_demand_family_report",
        "project_sql_requirement_summary",
        "project_sql_requirement_report",
        "project_sql_source_position",
        "project_sql_mapped_source",
        "project_sql_source_site",
        "project_sql_source_map_entry",
        "project_sql_source_association",
        "project_sql_legacy_source_position",
        "project_sql_mapped_subject",
        "project_sql_source_link",
        "project_sql_source_map",
        "project_declaration_occurrence",
        "query_def",
        "table_def",
        "set_relation_def",
        "span",
        "project_ir_reused_effective_output",
        "project_existing_effective_output",
        "project_logical_module",
        "source_def",
        "call_expr",
        "project_ir_cross_relation_edge",
        "project_completion_dependency",
        "project_resolved_module_relation_symbol",
        "project_module_origin_path",
        "project_ir_output_field_occurrence",
        "project_module_row_field_identity",
        "project_module_select_fact",
        "select_item",
        "from_clause",
        "project_row_field",
        "project_module_select_expression_fact",
        "name_expr",
        "value_type",
        "literal_expr",
        "project_resolved_type",
        "project_row_schema",
        "project_relation_let_scope_facts",
        "project_module_expression_reference_fact",
        "shape_def",
        "field_def",
        "type_expr",
        "project_ir_logical_operator_occurrence",
        "dotted_name_expr",
        "project_ir_concrete_single_relation_fragment",
        "project_ir_input_slot_occurrence",
        "project_ir_use_occurrence",
        "project_resolved_module_relation_reference",
        "project_declaration_occurrence_identity",
        "project_ir_relation_row_output",
        "resolved_type",
        "project_ir_plan_node_occurrence",
        "project_module_relation_semantic_facts",
        "project_ir_concrete_relation_subject",
        "project_ir_resolved_relation_anchor",
        "project_module_relation_reference",
        "project_ir_output_value_occurrence",
        "project_ir_relation_anchor",
        "project_module_dependency_fact",
        "project_module_reference_occurrence_identity",
        "let_binding",
        "project_module_let_binding_fact",
        "where_clause",
        "project_module_where_fact",
        "binary_expr",
        "comparison_expr",
        "unary_expr",
        "between_expr",
        "is_null_expr",
        "project_joined_row_retention_effect",
        "let_clause",
        "project_ir_completed_query_block_output",
        "project_ir_query_block_relation_input_edge",
        "project_ir_set_operand_input",
        "project_ir_completed_set_operation_output",
        "project_ir_query_block_operator_occurrence",
        "project_ir_query_block_result_properties",
        "project_ir_distinct_comparison",
        "project_ir_query_block_row_output",
        "project_no_join_scalar_expression",
        "project_completed_set_output_field",
        "project_distinct",
        "project_distinct_full_row_uniqueness",
        "project_completed_row_domain",
        "project_relation_ordering",
        "project_relation_order_item",
        "project_relation_order_input",
        "project_relation_limit",
        "project_set_full_row_uniqueness",
        "project_row_equivalence_field",
        "project_distinct_grain_origin",
        "project_set_operation",
        "project_set_column",
        "project_set_operand_use",
        "project_resolved_module_type_reference",
        "project_type_source_resolution_set",
        "project_resolved_set_operand",
        "project_ir_output_determination_result",
        "project_ir_output_relational_properties",
        "project_ir_output_value_class",
        "project_ir_output_value_class_set",
        "project_ir_output_fd_index",
        "project_ir_output_strict_closure",
        "project_ir_output_fd_proof_step",
        "project_ir_output_value_fd",
        "project_ir_output_candidate_key",
        "project_ir_provided_intrinsic_grain",
        "set_operand",
        "distinct_clause",
        "order_by_clause",
        "order_item",
        "limit_clause",
        "set_operation_body",
        "type_argument",
        "project_module_identity",
        "project_completed_effective_output",
        "project_completed_set_output",
        "project_completed_output_field",
        "project_concrete_no_join_replay",
        "project_ir_set_input_use_occurrence",
        "project_ir_query_block_effect_evidence",
        "project_ir_effect_evidence",
        "project_row_equivalence",
        "project_row_equivalence_input",
        "project_distinct_grain_factor_identity",
        "project_set_grain_origin",
        "project_concrete_grain_origin",
        "project_grain_domain_factor",
        "project_source_grain_factor_identity",
        "project_set_grain_factor_identity",
        "project_module_order_reference_fact",
        "project_module_type_reference",
        "project_module_set_operand_reference",
        "project_candidate_key_fact",
        "decimal_precision_scale",
        "project_grain_origin_identity",
        "project_candidate_key_identity",
        "project_row_uniqueness_evidence",
        "project_row_uniqueness_evidence_identity",
        "project_unique_declaration_occurrence",
        "project_exact_row_output_constraint_scope",
        "project_unique_determinant_field",
        "project_unique_declaration_identity",
        "unique_def",
        "project_module_source_field_origin",
        "project_no_join_qualify",
        "project_no_join_qualify_reference_resolution",
        "project_relation_clause_dependency_fact",
        "project_aggregate_grouped_clause_readiness",
        "project_group_key_fact",
        "project_aggregate_expression_analysis",
        "project_grouped_selected_result",
        "project_module_window_output_fact",
        "project_module_clause_dependency_fact",
        "window_computation_input",
        "window_dependency_occurrence",
        "project_ir_query_block_window_policy",
        "project_ir_query_block_aggregate_evaluation_context",
        "project_ir_query_block_window_evidence",
        "project_ir_query_block_scalar_output",
        "project_ir_query_block_grain_origin",
        "project_grouped_grain_factor_identity",
        "project_grain_dependency_fact",
        "project_aggregate_result_fact",
        "satisfying_clause",
        "qualify_clause",
        "group_by_item",
        "window_expr",
        "satisfying_result_predicate_info",
        "window_function_identity",
        "window_input_binding",
        "validated_window_specification",
        "window_order_field_binding",
        "__project_qualify_predicate_analysis",
        "window_spec",
        "window_input_scope",
        "project_row_dependency_node",
        "source_location",
        "resolved_window_specification",
        "window_function_frame_policy",
        "validated_frame_not_applicable",
        "project_ir_stage_field_anchor",
        "project_ir_plan_node_ref",
        "resolved_window_frame",
        "resolved_named_window_template",
        "authored_window_specification",
        "resolved_named_window_use",
        "resolved_window_function_modifiers",
        "validated_frame",
        "window_partition_field_binding",
        "frame_value_window_computation",
        "frame_value_window_semantic_fact",
        "navigation_offset_fact",
        "navigation_default_fact",
        "navigation_window_computation",
        "navigation_window_semantic_fact",
        "window_frame_bound",
        "authored_window_frame",
        "authored_window_null_treatment",
        "resolved_named_window_namespace",
        "project_sql_target_lookup",
        "project_sql_target_aspect",
        "project_sql_target_demand",
        "project_sql_target_summary",
        "target_catalog_residual",
        "project_sql_target_proposition",
        "found",
        "absent",
        "unknown",
        "conflict",
        "capability_key",
        "capability_fact",
        "capability_evidence",
        "canonical_capability_provider_inputs",
        "capability_profile_target",
        "capability_profile_reference",
        "capability_profile_identity",
        "static_capability_profile",
        "capability_profile_base_occurrence",
        "capability_profile_fact_occurrence",
        "capability_profile_composition_success",
        "capability_profile_composition_blocked",
        "effective_capability_profile_fact_occurrence",
        "project_sql_target_assessment",
        "project_sql_target_request",
        "capability_disposition",
        "diagnostic",
        "project_ir_join_input_correspondence",
        "join_clause",
        "join_on_clause",
        "project_join_condition",
        "project_concrete_joined_namespace_expression",
        "project_joined_scalar_namespace",
        "project_scalar_reference_resolution",
        "project_scalar_environment_field",
        "project_ir_composed_join",
        "project_join_condition_field",
        "project_ir_joined_row_field",
        "project_concrete_joined_row_filter",
        "project_ir_single_match_retention",
        "project_single_match_request",
        "project_single_match_assessment",
        "project_relation_binding_occurrence",
        "project_ir_join_row_output",
        "project_concrete_joined_qualify",
        "project_join_grain_factor_identity",
        "project_current_join_grain_witness",
        "project_joined_let_value",
        "project_joined_satisfying_analysis",
        "project_join_condition_reference",
        "project_joined_let_reference_resolution",
        "project_joined_satisfying_output_reference",
        "project_joined_let_occurrence",
        "project_joined_group_key_occurrence",
        "project_joined_aggregate_occurrence",
        "project_joined_stage_output_occurrence",
        "project_joined_group_protection",
        "project_joined_aggregate_grain_linkage",
        "project_joined_aggregate_pair_linkage",
        "project_concrete_joined_aggregation",
        "project_current_binary_join",
        "project_no_join_hidden_window_computation",
        "project_no_join_window_input",
        "project_no_join_hidden_window_input_use",
        "project_ir_provided_evaluation_policy",
        "named_window_declaration",
        "named_window_reference",
        "named_window_base_resolution",
        "composed_named_window_use",
        "named_window_component_provenance",
        "query_block_occurrence",
        "window_expression_semantic_fact",
        "signature_match",
        "nullability_evaluation_match",
        "project_ir_stage_scalar_field_output",
        "named_window_occurrence",
        "project_ir_join_input_use_occurrence",
        "project_non_concrete_join_use",
        "project_scalar_reference_occurrence",
        "project_effective_output_terminal",
        "project_relation_binding_identity",
        "project_ir_use_ref",
        "project_joined_row_field_semantics",
        "project_current_multi_fact_region",
        "project_grain_factor_set",
        "project_fact_contextual_grain",
        "project_fact_grain_comparison",
        "project_common_grain_result",
        "project_join_null_rejection",
        "project_joined_aggregate_field_dependency",
        "window_computation_analysis",
        "window_use_occurrence",
        "window_occurrence_identity",
        "window_result_availability",
        "logical_type_identity",
        "nullability_evaluation_evidence",
        "project_ir_stage_row_field",
        "type_variable_binding",
        "project_join_use_identity",
        "project_concrete_query_block",
        "project_grain_factor_universe",
        "project_fact_grain_determination",
        "project_actual_grain_candidate",
        "project_current_join_properties",
        "project_common_grain_candidate_evidence",
        "nullability_default_evidence",
        "nullability_argument_evidence",
        "project_query_block_owner_bridge",
        "project_grain_dependency_index",
        "project_ir_provided_null_extension",
        "project_ir_join_unavailable_property",
        "project_actual_grain_authority",
        "project_ir_join_match_field_pair",
        "project_directional_relationship_match_guarantee",
        "project_ir_single_match_proof_image",
        "relationship_metadata",
        "project_ir_binary_join_occurrence",
        "project_concrete_join_use",
        "project_relationship_path",
        "project_relationship_path_step",
        "join_traversal_step",
        "project_ir_join_grain_witness",
        "project_single_match_proof",
        "project_relationship_equality_correspondence",
        "project_relationship_direction_identity",
        "project_at_most_one_evidence",
        "project_absent_referential_coverage",
        "relationship_match_clause",
        "project_ir_binary_join_identity",
        "project_concrete_relationship_condition",
        "project_relationship_correspondence_identity",
        "project_relationship_endpoint_field_reference_occurrence",
        "relationship_endpoint",
        "project_traversal_step_use",
        "project_relationship_declaration_identity",
        "project_relationship_endpoint_occurrence",
        "project_relationship_base_match_identity",
        "project_concrete_relationship_subject",
        "project_relationship_endpoint_field_reference_identity",
        "project_traversal_step_use_identity",
        "project_relationship_endpoint_identity",
        "project_relationship_declaration_occurrence",
        "project_ir_property_stage",
        "project_ir_provided_cardinality_upper_bound",
        "project_ir_provided_relation_ordering",
        "project_ir_provided_output_shape",
        "project_ir_provided_bag_multiplicity",
        "project_ir_provided_closed_bindings",
        "project_ir_scalar_field_output",
        "project_ir_row_field",
        "project_ir_field_anchor",
        "authored_window_nth_direction",
        "nth_value_position_fact",
        "project_current_materialized_input",
        "project_current_input_field",
        "project_current_input_grain_authority",
        "capability_profile_composition_blocker",
        "extension_signature_provider_context",
        "extension_signature_requirement_selector_occurrence",
        "extension_signature_provider_selection_occurrence",
        "project_effective_join_input_authority",
        "extension_signature_requirement_selectors",
        "extension_catalog_selection_result",
        "extension_signature_requirement_selector",
        "capability_requirement_collection",
        "extension_catalog_target",
        "declared_extension_catalog_availability",
        "constructed_extension_catalog",
        "extension_catalog_lookup_scope",
        "extension_catalog_availability_declaration",
        "extension_catalog_selection_candidate",
        "capability_requirement_collection_identity",
        "capability_requirement_occurrence",
        "extension_catalog_metadata",
        "postgre_sql_callable_identity",
        "extension_catalog_selection_candidate_identity",
        "extension_catalog_identity",
        "extension_catalog_reference",
        "extension_catalog_source_provenance",
        "extension_catalog_source_occurrence",
        "extension_catalog_type_reference",
        "postgre_sql_operator_identity",
        "postgre_sql_cast_identity",
        "extension_catalog_declaration_type_use",
        "extension_catalog_entry_evidence",
        "postgre_sql_callable_declaration",
        "extension_native_type_catalog_entry",
        "extension_scalar_function_catalog_entry",
        "extension_aggregate_catalog_entry",
        "extension_operator_catalog_entry",
        "extension_cast_catalog_entry",
        "extension_catalog_completeness_claim",
        "type_def",
        "project_module_reference_attribution",
        "project_resolved_nominal_symbol",
        "project_nominal_declaration_identity",
        "import_item",
        "import_statement",
        "export_item",
        "export_statement",
        "project_module_import_attribution",
        "project_module_access_hop",
        "project_module_facade_attribution",
        "project_resolved_imported_binding",
        "project_module_import_occurrence_identity",
        "project_root",
        "project_module_import_request",
        "project_module_facade_occurrence_identity",
        "project_module_export_entry",
        "project_imported_binding_identity",
        "project_module_export_request",
        "project_imported_export_candidate",
        "project_qualify_reference_resolution",
        "project_concrete_window_computation",
        "project_selected_window_result_binding",
        "project_joined_window_input_namespace",
        "project_window_dependency_occurrence",
        "project_joined_window_input_binding",
        "enum_def",
        "ensure_clause",
        "annotation",
        "project_concrete_joined_window_stage",
        "project_window_computation_site",
        "project_joined_window_input_resolution",
        "project_aggregate_selected_result",
        "project_ir_aggregate_evaluation_context",
        "project_refined_match_bounds",
        "project_ir_rebound_existing_output",
    ),
)


def enum(*values):
    return Shape((Tag.ENUM,), enums=values)


def ref(*domains):
    return Shape((Tag.REF,), domains=domains)


def seq(item):
    return Shape((Tag.SEQUENCE,), items=item)


def mapping(key, item):
    return Shape((Tag.MAPPING,), items=item, keys=key)


def union(*items):
    return Shape(
        tuple(dict.fromkeys(t for i in items for t in i.tags)),
        tuple(dict.fromkeys(d for i in items for d in i.domains)),
        tuple(dict.fromkeys(e for i in items for e in i.enums)),
        next((i.items for i in items if i.items is not None), None),
        next((i.keys for i in items if i.keys is not None), None),
    )


RECORD_RULES: Mapping[str, RecordRule] = MappingProxyType(
    {
        "observation": RecordRule(
            "observation",
            (
                FieldRule("plan", ref("project_sql_plan")),
                FieldRule("report", ref("project_sql_requirement_report")),
                FieldRule("source_map", ref("project_sql_source_map")),
                FieldRule(
                    "assessment", union(ABSENT, ref("project_sql_target_assessment"))
                ),
            ),
        ),
        "project_sql_plan_scope": RecordRule(
            "project_sql_plan_scope",
            (FieldRule("selected_owner", ref("project_declaration_occurrence")),),
        ),
        "project_sql_plan_ref": RecordRule(
            "project_sql_plan_ref",
            (
                FieldRule("scope", ref("project_sql_plan_scope")),
                FieldRule(
                    "kind",
                    enum(
                        "literal_site",
                        "literal_slot",
                        "fixed_literal_value",
                        "bind_use",
                        "set_body",
                        "set_operand",
                        "set_input",
                        "set_column",
                        "result_boundary",
                        "result_port",
                        "distinct",
                        "quotient_field",
                        "relation_order",
                        "order_item",
                        "order_expression",
                        "order_use",
                        "hidden_order_requirement",
                        "result_limit",
                        "result_export",
                        "window",
                        "window_use",
                        "window_argument",
                        "window_policy",
                        "window_projection",
                        "aggregation",
                        "group_key",
                        "aggregate",
                        "aggregate_projection",
                        "aggregate_risk",
                        "join",
                        "join_input",
                        "join_port",
                        "relationship_match",
                        "join_tail",
                        "single_match",
                        "single_match_proof",
                        "select_block",
                        "expression_site",
                        "expression",
                        "operand",
                        "stage_port",
                        "let_value",
                        "filter",
                        "definition",
                        "input_use",
                        "source_port",
                        "input_port",
                        "export",
                        "projection",
                        "boundary",
                        "symbol",
                        "origin",
                        "demand",
                    ),
                ),
                FieldRule("position", INTEGER),
            ),
        ),
        "project_sql_port": RecordRule(
            "project_sql_port",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_sql_plan_ref")),
                FieldRule("field", ref("project_ir_output_field_occurrence")),
                FieldRule("identity", ref("project_module_row_field_identity")),
                FieldRule(
                    "producer_port", union(ref("project_sql_plan_ref"), optional)
                ),
            ),
        ),
        "project_sql_definition": RecordRule(
            "project_sql_definition",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "entry",
                    union(
                        ref("project_ir_reused_effective_output"),
                        ref("project_ir_rebound_existing_output"),
                        ref("project_ir_completed_query_block_output"),
                        ref("project_ir_completed_set_operation_output"),
                    ),
                ),
                FieldRule("exports", seq(ref("project_sql_port"))),
            ),
        ),
        "project_sql_source_binding": RecordRule(
            "project_sql_source_binding",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_ir_reused_effective_output")),
                FieldRule("module", ref("project_logical_module")),
                FieldRule("declaration", ref("source_def")),
                FieldRule("connector", ref("call_expr")),
            ),
        ),
        "project_sql_input_use": RecordRule(
            "project_sql_input_use",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("producer", ref("project_sql_plan_ref")),
                FieldRule("consumer", ref("project_sql_plan_ref")),
                FieldRule(
                    "edge",
                    union(
                        ref("project_ir_cross_relation_edge"),
                        ref("project_ir_query_block_relation_input_edge"),
                        ref("project_ir_set_operand_input"),
                        ref("project_ir_join_input_correspondence"),
                    ),
                ),
                FieldRule("dependency", ref("project_completion_dependency")),
                FieldRule("binding", ref("project_resolved_module_relation_symbol")),
                FieldRule("origin_path", ref("project_module_origin_path")),
                FieldRule("ports", seq(ref("project_sql_port"))),
            ),
        ),
        "project_sql_boundary": RecordRule(
            "project_sql_boundary",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("use", ref("project_sql_input_use")),
                FieldRule("reason", enum("source_input", "named_input")),
            ),
        ),
        "project_sql_symbol": RecordRule(
            "project_sql_symbol",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("scope", ref("project_sql_plan_ref")),
                FieldRule("namespace", enum("relation_use", "field_port")),
                FieldRule("position", INTEGER),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("label", TEXT),
            ),
        ),
        "project_sql_select_block": RecordRule(
            "project_sql_select_block",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule(
                    "kind",
                    enum(
                        "let",
                        "where",
                        "projection",
                        "aggregate",
                        "satisfying",
                        "window",
                        "qualify",
                    ),
                ),
                FieldRule("predecessor", ref("project_sql_plan_ref")),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("exports", seq(ref("project_sql_plan_ref"))),
                FieldRule(
                    "selected",
                    union(
                        ref("project_ir_reused_effective_output"),
                        ref("project_ir_rebound_existing_output"),
                        ref("project_ir_completed_query_block_output"),
                        ref("project_ir_completed_set_operation_output"),
                    ),
                ),
                FieldRule(
                    "operators",
                    seq(
                        union(
                            ref("project_ir_logical_operator_occurrence"),
                            ref("project_ir_query_block_operator_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "boundary",
                    union(ref("project_sql_boundary"), ref("project_sql_join_tail")),
                ),
            ),
        ),
        "project_sql_projection": RecordRule(
            "project_sql_projection",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("input_use", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("source_port", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("input_port", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("export", ref("project_sql_plan_ref")),
                FieldRule("semantic", ref("project_module_select_fact")),
                FieldRule("symbol", union(ref("project_sql_symbol"), optional)),
                FieldRule("expression", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                    ),
                ),
            ),
        ),
        "project_sql_origin": RecordRule(
            "project_sql_origin",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "subject",
                    union(ref("project_sql_plan_scope"), ref("project_sql_plan_ref")),
                ),
                FieldRule(
                    "role",
                    enum(
                        "literal_site",
                        "literal_slot",
                        "fixed_literal_value",
                        "bind_use",
                        "set_body",
                        "set_operand",
                        "set_input",
                        "set_column",
                        "result_boundary",
                        "result_port",
                        "distinct",
                        "quotient_field",
                        "relation_order",
                        "order_item",
                        "order_expression",
                        "order_use",
                        "hidden_order_requirement",
                        "result_limit",
                        "result_export",
                        "window",
                        "window_use",
                        "window_argument",
                        "window_policy",
                        "window_projection",
                        "aggregation",
                        "group_key",
                        "aggregate",
                        "aggregate_projection",
                        "aggregate_risk",
                        "join",
                        "join_input",
                        "join_port",
                        "relationship_match",
                        "join_tail",
                        "single_match",
                        "single_match_proof",
                        "expression_site",
                        "expression",
                        "operand",
                        "stage_port",
                        "let_value",
                        "filter",
                        "selected_owner",
                        "definition",
                        "source_descriptor",
                        "input_use",
                        "select_block",
                        "source_port",
                        "input_port",
                        "stage_export",
                        "projection",
                        "export",
                        "boundary",
                        "symbol",
                        "demand",
                    ),
                ),
                FieldRule(
                    "provenance",
                    enum("value", "membership", "type_proof", "generated_structure"),
                ),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "cause",
                    union(
                        ref("set_operation_body"),
                        ref("distinct_clause"),
                        ref("order_by_clause"),
                        ref("limit_clause"),
                        ref("join_on_clause"),
                        ref("source_def"),
                        ref("table_def"),
                        ref("query_def"),
                        ref("set_relation_def"),
                        ref("from_clause"),
                        ref("join_clause"),
                        ref("set_operand"),
                        ref("select_item"),
                        ref("let_binding"),
                        ref("where_clause"),
                        ANCHOR,
                        ref("satisfying_clause"),
                        ref("group_by_item"),
                    ),
                ),
                FieldRule(
                    "evidence",
                    union(
                        union(
                            ref("project_sql_literal_site"),
                            ref("project_sql_literal_slot"),
                            ref("project_sql_fixed_literal_value"),
                            ref("project_sql_bind_use"),
                        ),
                        union(
                            ref("project_sql_set_body"),
                            ref("project_sql_set_operand"),
                            ref("project_sql_set_input"),
                            ref("project_sql_set_column"),
                        ),
                        union(
                            ref("project_sql_result_boundary"),
                            ref("project_sql_result_port"),
                            ref("project_sql_distinct"),
                            ref("project_sql_quotient_field"),
                            ref("project_sql_order"),
                            ref("project_sql_order_item"),
                            ref("project_sql_order_expression"),
                            ref("project_sql_order_use"),
                            ref("project_sql_hidden_order_requirement"),
                            ref("project_sql_result_limit"),
                            ref("project_sql_result_export"),
                        ),
                        union(
                            ref("project_sql_window"),
                            ref("project_sql_window_use"),
                            ref("project_sql_window_argument"),
                            ref("project_sql_window_policy"),
                            ref("project_sql_window_projection"),
                        ),
                        union(
                            ref("project_no_join_qualify"),
                            ref("project_concrete_joined_qualify"),
                        ),
                        union(
                            ref("project_sql_aggregation"),
                            ref("project_sql_group_key"),
                            ref("project_sql_aggregate"),
                            ref("project_sql_aggregate_projection"),
                            ref("project_sql_aggregate_risk"),
                        ),
                        union(
                            ref("project_aggregate_expression_analysis"),
                            ref("project_concrete_joined_namespace_expression"),
                            ref("project_joined_satisfying_analysis"),
                            ref("satisfying_result_predicate_info"),
                        ),
                        union(
                            ref("project_group_key_fact"),
                            ref("project_joined_group_key_occurrence"),
                        ),
                        union(
                            ref("project_aggregate_selected_result"),
                            ref("project_grouped_selected_result"),
                            ref("project_joined_stage_output_occurrence"),
                        ),
                        union(
                            ref("project_joined_group_protection"),
                            ref("project_joined_aggregate_grain_linkage"),
                            ref("project_joined_aggregate_pair_linkage"),
                        ),
                        union(
                            union(
                                ref("project_module_let_binding_fact"),
                                ref("project_module_select_expression_fact"),
                                ref("project_module_where_fact"),
                                ref("project_no_join_scalar_expression"),
                            ),
                            ref("project_joined_let_value"),
                            ref("project_concrete_joined_namespace_expression"),
                            ref("project_join_condition"),
                            union(
                                ref("project_aggregate_expression_analysis"),
                                ref("project_concrete_joined_namespace_expression"),
                                ref("project_joined_satisfying_analysis"),
                                ref("satisfying_result_predicate_info"),
                            ),
                            union(
                                ref("project_no_join_qualify"),
                                ref("project_concrete_joined_qualify"),
                            ),
                        ),
                        union(
                            ref("project_sql_join"),
                            ref("project_sql_join_input"),
                            ref("project_sql_join_port"),
                            ref("project_sql_relationship_match"),
                            ref("project_sql_join_tail"),
                            ref("project_sql_single_match"),
                            ref("project_sql_single_match_proof"),
                        ),
                        ref("project_declaration_occurrence"),
                        union(
                            ref("project_ir_reused_effective_output"),
                            ref("project_ir_rebound_existing_output"),
                            ref("project_ir_completed_query_block_output"),
                            ref("project_ir_completed_set_operation_output"),
                            ANCHOR,
                        ),
                        ref("project_completion_dependency"),
                        ref("project_module_select_fact"),
                        ref("project_ir_output_field_occurrence"),
                        ref("project_module_let_binding_fact"),
                        ref("project_module_where_fact"),
                        ref("project_module_select_expression_fact"),
                        ref("project_no_join_scalar_expression"),
                        ref("value_type"),
                        ref("project_row_field"),
                    ),
                ),
                FieldRule("antecedents", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_source_realization_demand": RecordRule(
            "project_sql_source_realization_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_sql_source_binding")),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_export_representation_demand": RecordRule(
            "project_sql_export_representation_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("field", ref("project_ir_output_field_occurrence")),
                FieldRule("logical_type", ref("project_resolved_type")),
                FieldRule("nullability", enum("non_null", "nullable", "unknown")),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_bindings": RecordRule(
            "project_sql_bindings",
            (
                FieldRule("scope", ref("project_sql_plan_scope")),
                FieldRule("definitions", seq(ref("project_sql_definition"))),
                FieldRule("sources", seq(ref("project_sql_source_binding"))),
                FieldRule("input_uses", seq(ref("project_sql_input_use"))),
                FieldRule("source_ports", seq(ref("project_sql_port"))),
                FieldRule("input_ports", seq(ref("project_sql_port"))),
                FieldRule("all_exports", seq(ref("project_sql_port"))),
                FieldRule("boundaries", seq(ref("project_sql_boundary"))),
                FieldRule("symbols", seq(ref("project_sql_symbol"))),
                FieldRule("origins", seq(ref("project_sql_origin"))),
                FieldRule(
                    "demands",
                    seq(
                        union(
                            ref("project_sql_literal_demand"),
                            ref("project_sql_set_demand"),
                            ref("project_sql_result_demand"),
                            ref("project_sql_source_realization_demand"),
                            ref("project_sql_export_representation_demand"),
                            ref("project_sql_expression_demand"),
                            ref("project_sql_stage_value_demand"),
                            ref("project_sql_filter_demand"),
                            ref("project_sql_scope_demand"),
                            ref("project_sql_join_demand"),
                            ref("project_sql_aggregate_demand"),
                            ref("project_sql_window_demand"),
                        )
                    ),
                ),
            ),
        ),
        "project_sql_plan": RecordRule(
            "project_sql_plan",
            (
                FieldRule(
                    "literal_policy", enum("preserve_literals", "bind_safe_literals")
                ),
                FieldRule("literal_sites", seq(ref("project_sql_literal_site"))),
                FieldRule("literal_slots", seq(ref("project_sql_literal_slot"))),
                FieldRule("bind_uses", seq(ref("project_sql_bind_use"))),
                FieldRule("fixed_envelope", ref("project_sql_fixed_envelope")),
                FieldRule("scope", ref("project_sql_plan_scope")),
                FieldRule("bindings", ref("project_sql_bindings")),
                FieldRule("sources", seq(ref("project_sql_source_binding"))),
                FieldRule("blocks", seq(ref("project_sql_select_block"))),
                FieldRule("input_uses", seq(ref("project_sql_input_use"))),
                FieldRule("source_ports", seq(ref("project_sql_port"))),
                FieldRule("input_ports", seq(ref("project_sql_port"))),
                FieldRule("all_exports", seq(ref("project_sql_port"))),
                FieldRule("exports", seq(ref("project_sql_port"))),
                FieldRule("projections", seq(ref("project_sql_projection"))),
                FieldRule("boundaries", seq(ref("project_sql_boundary"))),
                FieldRule("symbols", seq(ref("project_sql_symbol"))),
                FieldRule("origins", seq(ref("project_sql_origin"))),
                FieldRule(
                    "demands",
                    seq(
                        union(
                            ref("project_sql_literal_demand"),
                            ref("project_sql_set_demand"),
                            ref("project_sql_result_demand"),
                            ref("project_sql_source_realization_demand"),
                            ref("project_sql_export_representation_demand"),
                            ref("project_sql_expression_demand"),
                            ref("project_sql_stage_value_demand"),
                            ref("project_sql_filter_demand"),
                            ref("project_sql_scope_demand"),
                            ref("project_sql_join_demand"),
                            ref("project_sql_aggregate_demand"),
                            ref("project_sql_window_demand"),
                        )
                    ),
                ),
                FieldRule(
                    "expression_sites",
                    seq(
                        union(
                            ref("project_sql_expression_site"),
                            ref("project_sql_joined_site"),
                            ref("project_sql_match_site"),
                            ref("project_sql_aggregate_site"),
                            ref("project_sql_qualify_site"),
                        )
                    ),
                ),
                FieldRule(
                    "expressions",
                    seq(
                        union(
                            ref("project_sql_literal"),
                            ref("project_sql_bound_literal"),
                            ref("project_sql_reference"),
                            ref("project_sql_joined_reference"),
                            ref("project_sql_match_reference"),
                            ref("project_sql_unary"),
                            ref("project_sql_binary"),
                            ref("project_sql_comparison"),
                            ref("project_sql_is_null"),
                            ref("project_sql_between"),
                            ref("project_sql_result_reference"),
                            ref("project_sql_window_reference"),
                            ref("project_sql_aggregate_argument_call"),
                        )
                    ),
                ),
                FieldRule("operands", seq(ref("project_sql_expression_operand"))),
                FieldRule("stage_ports", seq(ref("project_sql_stage_port"))),
                FieldRule("let_values", seq(ref("project_sql_let_value"))),
                FieldRule("filters", seq(ref("project_sql_filter"))),
                FieldRule("joins", seq(ref("project_sql_join"))),
                FieldRule("join_inputs", seq(ref("project_sql_join_input"))),
                FieldRule("join_ports", seq(ref("project_sql_join_port"))),
                FieldRule(
                    "relationship_matches", seq(ref("project_sql_relationship_match"))
                ),
                FieldRule("join_tails", seq(ref("project_sql_join_tail"))),
                FieldRule("single_matches", seq(ref("project_sql_single_match"))),
                FieldRule(
                    "single_match_proofs", seq(ref("project_sql_single_match_proof"))
                ),
                FieldRule("aggregations", seq(ref("project_sql_aggregation"))),
                FieldRule("group_keys", seq(ref("project_sql_group_key"))),
                FieldRule("aggregates", seq(ref("project_sql_aggregate"))),
                FieldRule(
                    "aggregate_projections",
                    seq(ref("project_sql_aggregate_projection")),
                ),
                FieldRule("aggregate_risks", seq(ref("project_sql_aggregate_risk"))),
                FieldRule("windows", seq(ref("project_sql_window"))),
                FieldRule("window_uses", seq(ref("project_sql_window_use"))),
                FieldRule("window_arguments", seq(ref("project_sql_window_argument"))),
                FieldRule("window_policies", seq(ref("project_sql_window_policy"))),
                FieldRule(
                    "window_projections", seq(ref("project_sql_window_projection"))
                ),
                FieldRule("result_boundaries", seq(ref("project_sql_result_boundary"))),
                FieldRule("result_ports", seq(ref("project_sql_result_port"))),
                FieldRule("distincts", seq(ref("project_sql_distinct"))),
                FieldRule("quotient_fields", seq(ref("project_sql_quotient_field"))),
                FieldRule("orders", seq(ref("project_sql_order"))),
                FieldRule("order_items", seq(ref("project_sql_order_item"))),
                FieldRule(
                    "order_expressions", seq(ref("project_sql_order_expression"))
                ),
                FieldRule("order_uses", seq(ref("project_sql_order_use"))),
                FieldRule(
                    "hidden_order_requirements",
                    seq(ref("project_sql_hidden_order_requirement")),
                ),
                FieldRule("result_limits", seq(ref("project_sql_result_limit"))),
                FieldRule("result_exports", seq(ref("project_sql_result_export"))),
                FieldRule("set_bodies", seq(ref("project_sql_set_body"))),
                FieldRule("set_operands", seq(ref("project_sql_set_operand"))),
                FieldRule("set_inputs", seq(ref("project_sql_set_input"))),
                FieldRule("set_columns", seq(ref("project_sql_set_column"))),
            ),
        ),
        "project_sql_expression_site": RecordRule(
            "project_sql_expression_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "match",
                        "let",
                        "where",
                        "select",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                    ),
                ),
                FieldRule("ordinal", INTEGER),
                FieldRule(
                    "occurrence",
                    union(ref("let_binding"), ref("where_clause"), ref("select_item")),
                ),
                FieldRule("input_schema", ref("project_row_schema")),
                FieldRule("let_scope", ref("project_relation_let_scope_facts")),
                FieldRule("let_prefix", seq(ref("let_binding"))),
                FieldRule(
                    "evidence",
                    union(
                        union(
                            ref("project_module_let_binding_fact"),
                            ref("project_module_select_expression_fact"),
                            ref("project_module_where_fact"),
                            ref("project_no_join_scalar_expression"),
                        ),
                        ref("project_joined_let_value"),
                        ref("project_concrete_joined_namespace_expression"),
                        ref("project_join_condition"),
                        union(
                            ref("project_aggregate_expression_analysis"),
                            ref("project_concrete_joined_namespace_expression"),
                            ref("project_joined_satisfying_analysis"),
                            ref("satisfying_result_predicate_info"),
                        ),
                        union(
                            ref("project_no_join_qualify"),
                            ref("project_concrete_joined_qualify"),
                        ),
                    ),
                ),
                FieldRule(
                    "references", seq(ref("project_module_expression_reference_fact"))
                ),
            ),
        ),
        "project_sql_joined_site": RecordRule(
            "project_sql_joined_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "match",
                        "let",
                        "where",
                        "select",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                    ),
                ),
                FieldRule("ordinal", INTEGER),
                FieldRule(
                    "occurrence",
                    union(ref("let_binding"), ref("where_clause"), ref("select_item")),
                ),
                FieldRule("namespace", ref("project_joined_scalar_namespace")),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_joined_let_value"),
                        ref("project_concrete_joined_namespace_expression"),
                    ),
                ),
                FieldRule(
                    "references",
                    seq(
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        )
                    ),
                ),
            ),
        ),
        "project_sql_match_site": RecordRule(
            "project_sql_match_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "match",
                        "let",
                        "where",
                        "select",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                    ),
                ),
                FieldRule("ordinal", INTEGER),
                FieldRule("occurrence", ref("join_on_clause")),
                FieldRule("evidence", ref("project_join_condition")),
                FieldRule("references", seq(ref("project_join_condition_reference"))),
            ),
        ),
        "project_sql_literal": RecordRule(
            "project_sql_literal",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("literal_expr")),
            ),
        ),
        "project_sql_bound_literal": RecordRule(
            "project_sql_bound_literal",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("literal_expr")),
                FieldRule("use", ref("project_sql_bind_use")),
            ),
        ),
        "project_sql_reference": RecordRule(
            "project_sql_reference",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("reference", ref("project_module_expression_reference_fact")),
                FieldRule("port", ref("project_sql_plan_ref")),
                FieldRule("symbol", ref("project_sql_symbol")),
            ),
        ),
        "project_sql_joined_reference": RecordRule(
            "project_sql_joined_reference",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule(
                    "reference",
                    union(
                        ref("project_joined_let_reference_resolution"),
                        ref("project_scalar_reference_resolution"),
                    ),
                ),
                FieldRule("port", ref("project_sql_plan_ref")),
                FieldRule("symbol", ref("project_sql_symbol")),
            ),
        ),
        "project_sql_match_reference": RecordRule(
            "project_sql_match_reference",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("reference", ref("project_join_condition_reference")),
                FieldRule("port", ref("project_sql_plan_ref")),
                FieldRule("symbol", ref("project_sql_symbol")),
            ),
        ),
        "project_sql_unary": RecordRule(
            "project_sql_unary",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("unary_expr")),
                FieldRule("operand", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_binary": RecordRule(
            "project_sql_binary",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("binary_expr")),
                FieldRule("left", ref("project_sql_plan_ref")),
                FieldRule("right", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_comparison": RecordRule(
            "project_sql_comparison",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("comparison_expr")),
                FieldRule("left", ref("project_sql_plan_ref")),
                FieldRule("right", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_is_null": RecordRule(
            "project_sql_is_null",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("is_null_expr")),
                FieldRule("value", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_between": RecordRule(
            "project_sql_between",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("expression", ref("between_expr")),
                FieldRule("value", ref("project_sql_plan_ref")),
                FieldRule("lower", ref("project_sql_plan_ref")),
                FieldRule("upper", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_expression_operand": RecordRule(
            "project_sql_expression_operand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("parent", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("child", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_stage_port": RecordRule(
            "project_sql_stage_port",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("kind", enum("input", "export")),
                FieldRule(
                    "key",
                    union(
                        ref("project_row_field"),
                        ref("let_binding"),
                        ref("project_scalar_environment_field"),
                        ref("project_joined_let_occurrence"),
                        union(
                            union(
                                ref("project_group_key_fact"),
                                ref("project_joined_group_key_occurrence"),
                            ),
                            ref("select_item"),
                        ),
                        union(
                            ref("project_module_window_output_fact"),
                            ref("project_concrete_window_computation"),
                            ref("project_no_join_hidden_window_computation"),
                        ),
                    ),
                ),
                FieldRule("source", ref("project_sql_plan_ref")),
                FieldRule(
                    "type_evidence", union(ref("project_row_field"), ref("value_type"))
                ),
            ),
        ),
        "project_sql_let_value": RecordRule(
            "project_sql_let_value",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                    ),
                ),
                FieldRule("expression", ref("project_sql_plan_ref")),
                FieldRule("port", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_filter": RecordRule(
            "project_sql_filter",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("predicate", ref("project_sql_plan_ref")),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
            ),
        ),
        "project_sql_expression_demand": RecordRule(
            "project_sql_expression_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_match_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("expression", ANCHOR),
                FieldRule("value_type", ref("value_type")),
                FieldRule("operand_types", seq(ref("value_type"))),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_stage_value_demand": RecordRule(
            "project_sql_stage_value_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "type_evidence", union(ref("project_row_field"), ref("value_type"))
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_filter_demand": RecordRule(
            "project_sql_filter_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "site",
                    union(
                        ref("project_sql_expression_site"),
                        ref("project_sql_joined_site"),
                        ref("project_sql_aggregate_site"),
                        ref("project_sql_qualify_site"),
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_scope_demand": RecordRule(
            "project_sql_scope_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("predecessor", ref("project_sql_plan_ref")),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("exports", seq(ref("project_sql_plan_ref"))),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_literal_position": RecordRule(
            "project_sql_literal_position",
            (
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("context", ANCHOR),
                FieldRule("context_ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "select",
                        "let",
                        "where",
                        "on",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                        "window_argument",
                        "window_partition",
                        "window_order",
                        "frame",
                        "relation_order",
                        "limit",
                        "connector",
                        "type_argument",
                        "unknown",
                    ),
                ),
                FieldRule("literal", ref("literal_expr")),
                FieldRule("ancestry", seq(seq(union(ANCHOR, INTEGER)))),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("evidence", ANCHOR),
                FieldRule("expression", union(ref("project_sql_plan_ref"), optional)),
            ),
        ),
        "project_sql_literal_site": RecordRule(
            "project_sql_literal_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("position", ref("project_sql_literal_position")),
                FieldRule("span", ref("span")),
                FieldRule("disposition", enum("bound", "preserved_with_reason")),
                FieldRule(
                    "reason",
                    union(
                        enum(
                            "preserve_policy",
                            "specialized_or_structural_context",
                            "call_argument_subtree",
                            "unknown_extraction_context",
                            "untyped_null",
                            "literal_type_unavailable",
                            "not_an_admitted_builtin",
                            "original_scalar_representation_unavailable",
                            "nonfinite_float",
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "project_sql_literal_slot": RecordRule(
            "project_sql_literal_slot",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("site", ref("project_sql_literal_site")),
                FieldRule("value_type", ref("value_type")),
                FieldRule("tag", enum("Bool", "Int", "Text", "Float")),
            ),
        ),
        "project_sql_fixed_literal_value": RecordRule(
            "project_sql_fixed_literal_value",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("slot", ref("project_sql_literal_slot")),
                FieldRule("tag", enum("Bool", "Int", "Text", "Float")),
                FieldRule("value", union(BOOLEAN, INTEGER, TEXT, FLOAT)),
            ),
        ),
        "project_sql_bind_use": RecordRule(
            "project_sql_bind_use",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("slot", ref("project_sql_literal_slot")),
                FieldRule("expression", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_fixed_envelope": RecordRule(
            "project_sql_fixed_envelope",
            (
                FieldRule("scope", ref("project_sql_plan_scope")),
                FieldRule("policy", enum("preserve_literals", "bind_safe_literals")),
                FieldRule("slots", seq(ref("project_sql_literal_slot"))),
                FieldRule("values", seq(ref("project_sql_fixed_literal_value"))),
            ),
        ),
        "project_sql_literal_demand": RecordRule(
            "project_sql_literal_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("use", ref("project_sql_bind_use")),
                FieldRule("value", ref("project_sql_fixed_literal_value")),
                FieldRule("contexts", seq(ref("project_sql_expression_demand"))),
                FieldRule(
                    "requirements",
                    seq(
                        enum(
                            "exact_data_representation",
                            "original_nullability",
                            "exact_range_and_precision",
                            "typed_operator_and_operand_context",
                            "applicable_collation_and_overload",
                        )
                    ),
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_result_boundary": RecordRule(
            "project_sql_result_boundary",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("kind", enum("distinct", "relation_ordering", "limit")),
                FieldRule("predecessor", ref("project_sql_plan_ref")),
                FieldRule(
                    "operator",
                    union(
                        ref("project_ir_logical_operator_occurrence"),
                        ref("project_ir_query_block_operator_occurrence"),
                    ),
                ),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("outputs", seq(ref("project_sql_plan_ref"))),
                FieldRule(
                    "properties",
                    union(
                        ref("project_ir_query_block_result_properties"),
                        ref("project_ir_property_stage"),
                    ),
                ),
            ),
        ),
        "project_sql_result_port": RecordRule(
            "project_sql_result_port",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("boundary", ref("project_sql_plan_ref")),
                FieldRule("role", enum("projection", "input", "output")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_sql_plan_ref")),
                FieldRule("canonical", union(ref("project_sql_port"), optional)),
                FieldRule("key", ANCHOR),
                FieldRule(
                    "type_evidence", union(ref("project_row_field"), ref("value_type"))
                ),
            ),
        ),
        "project_sql_distinct": RecordRule(
            "project_sql_distinct",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("boundary", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_distinct")),
                FieldRule("comparison", ref("project_ir_distinct_comparison")),
                FieldRule("fields", seq(ref("project_sql_plan_ref"))),
                FieldRule("uniqueness", ref("project_distinct_full_row_uniqueness")),
                FieldRule("input_domain", ref("project_completed_row_domain")),
                FieldRule("origin", ref("project_distinct_grain_origin")),
                FieldRule("global_input", BOOLEAN),
            ),
        ),
        "project_sql_quotient_field": RecordRule(
            "project_sql_quotient_field",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("distinct", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("canonical", ref("project_sql_port")),
                FieldRule("input", ref("project_sql_plan_ref")),
                FieldRule("output", ref("project_sql_plan_ref")),
                FieldRule("equivalence", ref("project_row_equivalence_field")),
            ),
        ),
        "project_sql_order": RecordRule(
            "project_sql_order",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("boundary", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_relation_ordering")),
                FieldRule("items", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_order_item": RecordRule(
            "project_sql_order_item",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("ordering", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_relation_order_item")),
                FieldRule("uses", seq(ref("project_sql_plan_ref"))),
                FieldRule("expression", ref("project_sql_plan_ref")),
                FieldRule("value", ref("project_sql_plan_ref")),
                FieldRule(
                    "determination",
                    union(
                        optional,
                        seq(
                            union(
                                ref("project_relation_order_item"),
                                ref("project_ir_output_determination_result"),
                                seq(ANCHOR),
                            )
                        ),
                    ),
                ),
            ),
        ),
        "project_sql_order_expression": RecordRule(
            "project_sql_order_expression",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("item", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("expression", ANCHOR),
                FieldRule("value_type", ref("value_type")),
                FieldRule("operands", seq(ref("project_sql_plan_ref"))),
                FieldRule("use", union(ref("project_sql_plan_ref"), optional)),
            ),
        ),
        "project_sql_order_use": RecordRule(
            "project_sql_order_use",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("item", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_relation_order_input")),
                FieldRule("scope", ref("project_sql_plan_ref")),
                FieldRule("ports", seq(ref("project_sql_plan_ref"))),
                FieldRule("requirement", union(ref("project_sql_plan_ref"), optional)),
            ),
        ),
        "project_sql_hidden_order_requirement": RecordRule(
            "project_sql_hidden_order_requirement",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("item", ref("project_sql_plan_ref")),
                FieldRule("scope", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_relation_order_item")),
                FieldRule("proof", ref("project_ir_output_determination_result")),
                FieldRule("properties", ref("project_ir_output_relational_properties")),
                FieldRule(
                    "determinants",
                    seq(
                        seq(
                            union(
                                ref("project_ir_output_value_class"),
                                seq(ref("project_sql_plan_ref")),
                            )
                        )
                    ),
                ),
                FieldRule("requested", seq(ref("project_ir_output_value_class"))),
                FieldRule(
                    "input_images",
                    seq(
                        seq(
                            union(
                                ref("project_relation_order_input"),
                                ref("project_sql_plan_ref"),
                            )
                        )
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_sql_result_limit": RecordRule(
            "project_sql_result_limit",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("boundary", ref("project_sql_plan_ref")),
                FieldRule(
                    "source",
                    union(
                        ref("project_relation_limit"),
                        ref("project_ir_provided_cardinality_upper_bound"),
                    ),
                ),
                FieldRule("clause", ref("limit_clause")),
                FieldRule("literal", ref("literal_expr")),
                FieldRule("value", INTEGER),
                FieldRule("row_count_upper_bound", INTEGER),
                FieldRule("maximum", INTEGER),
            ),
        ),
        "project_sql_result_export": RecordRule(
            "project_sql_result_export",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("canonical", ref("project_sql_port")),
                FieldRule("port", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_result_demand": RecordRule(
            "project_sql_result_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "result_scope_and_membership",
                        "result_value_representation",
                        "visible_row_quotient",
                        "field_equivalence_nulls_and_type_sources",
                        "relation_order_scope",
                        "order_direction_nulls_and_ties",
                        "order_expression_type_and_operands",
                        "order_value_use",
                        "pending_strict_fd_order_realization",
                        "static_row_count_upper_bound",
                        "canonical_result_image",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_result_boundary"),
                        ref("project_sql_result_port"),
                        ref("project_sql_distinct"),
                        ref("project_sql_quotient_field"),
                        ref("project_sql_order"),
                        ref("project_sql_order_item"),
                        ref("project_sql_order_expression"),
                        ref("project_sql_order_use"),
                        ref("project_sql_hidden_order_requirement"),
                        ref("project_sql_result_limit"),
                        ref("project_sql_result_export"),
                    ),
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_set_body": RecordRule(
            "project_sql_set_body",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_ir_completed_set_operation_output")),
                FieldRule("operation", ref("project_set_operation")),
                FieldRule("kind", enum("union", "intersect", "except")),
                FieldRule("quantifier", enum("all", "distinct")),
                FieldRule(
                    "multiplicity",
                    enum(
                        "union_all",
                        "union_distinct",
                        "intersect_all",
                        "intersect_distinct",
                        "except_all",
                        "except_distinct",
                    ),
                ),
                FieldRule("requires_equivalence", BOOLEAN),
                FieldRule("full_row_unique", BOOLEAN),
                FieldRule("fold", union(TEXT)),
                FieldRule("operands", seq(ref("project_sql_plan_ref"))),
                FieldRule("columns", seq(ref("project_sql_plan_ref"))),
                FieldRule("outputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("row_domain", ref("project_completed_row_domain")),
                FieldRule(
                    "properties", ref("project_ir_query_block_result_properties")
                ),
                FieldRule(
                    "uniqueness",
                    union(ref("project_set_full_row_uniqueness"), optional),
                ),
            ),
        ),
        "project_sql_set_operand": RecordRule(
            "project_sql_set_operand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("body", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_ir_set_operand_input")),
                FieldRule("use", ref("project_sql_input_use")),
                FieldRule("producer", ref("project_sql_plan_ref")),
                FieldRule("fields", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_set_input": RecordRule(
            "project_sql_set_input",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("operand", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("binding", ref("project_sql_port")),
                FieldRule(
                    "terminal",
                    union(ref("project_sql_port"), ref("project_sql_result_port")),
                ),
                FieldRule("evidence", ref("project_row_equivalence_field")),
            ),
        ),
        "project_sql_set_column": RecordRule(
            "project_sql_set_column",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("body", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_set_column")),
                FieldRule("semantic", ref("project_completed_set_output_field")),
                FieldRule("field", ref("project_ir_output_field_occurrence")),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("value_inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("output", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_set_demand": RecordRule(
            "project_sql_set_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "set_operation_quantifier_multiplicity_and_membership",
                        "set_properties_and_row_domain",
                        "set_whole_row_equivalence",
                        "set_operand_membership",
                        "set_input_type_null_and_representation",
                        "set_positional_column_and_value_sources",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_set_body"),
                        ref("project_sql_set_operand"),
                        ref("project_sql_set_input"),
                        ref("project_sql_set_column"),
                    ),
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_join_input": RecordRule(
            "project_sql_join_input",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("join", ref("project_sql_plan_ref")),
                FieldRule("ordinal", INTEGER),
                FieldRule("source", ref("project_ir_join_input_correspondence")),
                FieldRule("producer", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("predecessor", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("binding_use", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("ports", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_join_port": RecordRule(
            "project_sql_join_port",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("kind", enum("match", "output")),
                FieldRule("position", INTEGER),
                FieldRule("input", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("source", ref("project_sql_plan_ref")),
                FieldRule(
                    "original",
                    union(
                        ref("project_ir_output_field_occurrence"),
                        ref("project_ir_joined_row_field"),
                    ),
                ),
                FieldRule(
                    "field",
                    union(
                        ref("project_ir_output_field_occurrence"),
                        ref("project_ir_joined_row_field"),
                    ),
                ),
                FieldRule(
                    "key",
                    union(
                        ref("project_join_condition_field"),
                        ref("project_ir_output_field_occurrence"),
                        ref("project_ir_joined_row_field"),
                    ),
                ),
                FieldRule("nulling", seq(ref("project_ir_plan_node_ref"))),
            ),
        ),
        "project_sql_relationship_match": RecordRule(
            "project_sql_relationship_match",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("join", ref("project_sql_plan_ref")),
                FieldRule(
                    "source",
                    union(
                        ref("project_ir_join_match_field_pair"),
                        ref("project_relationship_equality_correspondence"),
                    ),
                ),
                FieldRule(
                    "guarantee", ref("project_directional_relationship_match_guarantee")
                ),
                FieldRule("left", ref("project_sql_plan_ref")),
                FieldRule("right", ref("project_sql_plan_ref")),
                FieldRule(
                    "authored_operands",
                    seq(
                        union(ref("project_sql_plan_ref"), ref("project_sql_plan_ref"))
                    ),
                ),
            ),
        ),
        "project_sql_join": RecordRule(
            "project_sql_join",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_ir_composed_join")),
                FieldRule(
                    "kind",
                    enum("inner", "left", "cross", "right", "full", "semi", "anti"),
                ),
                FieldRule(
                    "rows",
                    enum(
                        "matched_pairs",
                        "left_preserved",
                        "cartesian_pairs",
                        "right_preserved",
                        "both_preserved",
                        "left_exists",
                        "left_not_exists",
                    ),
                ),
                FieldRule(
                    "inputs",
                    seq(
                        union(ref("project_sql_plan_ref"), ref("project_sql_plan_ref"))
                    ),
                ),
                FieldRule("outputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("equalities", seq(ref("project_sql_plan_ref"))),
                FieldRule("on", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("site", union(ref("project_sql_match_site"), optional)),
                FieldRule("properties", ref("project_ir_output_relational_properties")),
            ),
        ),
        "project_sql_join_tail": RecordRule(
            "project_sql_join_tail",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("join", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_concrete_joined_row_filter")),
                FieldRule("fields", seq(ref("project_scalar_environment_field"))),
                FieldRule("ports", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_single_match": RecordRule(
            "project_sql_single_match",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("source", ref("project_ir_single_match_retention")),
                FieldRule("request", ref("project_single_match_request")),
                FieldRule("assessment", ref("project_single_match_assessment")),
                FieldRule("joins", seq(ref("project_sql_plan_ref"))),
                FieldRule(
                    "input_pairs",
                    seq(
                        seq(
                            union(
                                ref("project_sql_plan_ref"), ref("project_sql_plan_ref")
                            )
                        )
                    ),
                ),
                FieldRule("proofs", seq(ref("project_sql_plan_ref"))),
                FieldRule("diagnostic", union(ref("diagnostic"), optional)),
                FieldRule("downstream_enforcement_required", BOOLEAN),
            ),
        ),
        "project_sql_single_match_proof": RecordRule(
            "project_sql_single_match_proof",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("obligation", ref("project_sql_plan_ref")),
                FieldRule("parent", union(ref("project_sql_plan_ref"), optional)),
                FieldRule("source", ref("project_ir_single_match_proof_image")),
                FieldRule("joins", seq(ref("project_sql_plan_ref"))),
                FieldRule("producers", seq(ref("project_sql_plan_ref"))),
                FieldRule("children", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_join_demand": RecordRule(
            "project_sql_join_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "join_rows",
                        "match_input",
                        "match_field",
                        "output_field",
                        "relationship_equality",
                        "post_match_scope",
                        "single_match",
                        "proof_context",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_join"),
                        ref("project_sql_join_input"),
                        ref("project_sql_join_port"),
                        ref("project_sql_relationship_match"),
                        ref("project_sql_join_tail"),
                        ref("project_sql_single_match"),
                        ref("project_sql_single_match_proof"),
                    ),
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_aggregation_authority": RecordRule(
            "project_sql_aggregation_authority",
            (
                FieldRule(
                    "source",
                    union(
                        ref("project_aggregate_grouped_clause_readiness"),
                        ref("project_concrete_joined_aggregation"),
                    ),
                ),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule(
                    "context",
                    union(
                        ref("project_ir_aggregate_evaluation_context"),
                        ref("project_ir_query_block_aggregate_evaluation_context"),
                    ),
                ),
                FieldRule("properties", ref("project_ir_output_relational_properties")),
                FieldRule(
                    "keys",
                    seq(
                        union(
                            ref("project_group_key_fact"),
                            ref("project_joined_group_key_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "aggregates",
                    seq(
                        union(
                            ref("project_aggregate_expression_analysis"),
                            ref("project_joined_aggregate_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "key_references",
                    seq(
                        seq(
                            union(
                                ref("project_module_expression_reference_fact"),
                                union(
                                    ref("project_joined_let_reference_resolution"),
                                    ref("project_scalar_reference_resolution"),
                                ),
                                ref("project_relation_clause_dependency_fact"),
                                ref("project_joined_satisfying_output_reference"),
                                ANCHOR,
                            )
                        )
                    ),
                ),
                FieldRule(
                    "argument_references",
                    seq(
                        seq(
                            union(
                                ref("project_module_expression_reference_fact"),
                                union(
                                    ref("project_joined_let_reference_resolution"),
                                    ref("project_scalar_reference_resolution"),
                                ),
                                ref("project_relation_clause_dependency_fact"),
                                ref("project_joined_satisfying_output_reference"),
                                ANCHOR,
                            )
                        )
                    ),
                ),
                FieldRule(
                    "output_keys",
                    seq(
                        union(
                            union(
                                ref("project_group_key_fact"),
                                ref("project_joined_group_key_occurrence"),
                            ),
                            ref("select_item"),
                        )
                    ),
                ),
                FieldRule(
                    "outputs",
                    seq(
                        union(
                            ref("project_aggregate_selected_result"),
                            ref("project_grouped_selected_result"),
                            ref("project_joined_stage_output_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "risks",
                    seq(
                        union(
                            ref("project_joined_group_protection"),
                            ref("project_joined_aggregate_grain_linkage"),
                            ref("project_joined_aggregate_pair_linkage"),
                        )
                    ),
                ),
                FieldRule(
                    "satisfying",
                    union(
                        ref("project_joined_satisfying_analysis"),
                        ref("satisfying_result_predicate_info"),
                        optional,
                    ),
                ),
                FieldRule(
                    "satisfying_references",
                    seq(
                        union(
                            ref("project_module_expression_reference_fact"),
                            union(
                                ref("project_joined_let_reference_resolution"),
                                ref("project_scalar_reference_resolution"),
                            ),
                            ref("project_relation_clause_dependency_fact"),
                            ref("project_joined_satisfying_output_reference"),
                            ANCHOR,
                        )
                    ),
                ),
            ),
        ),
        "project_sql_aggregation": RecordRule(
            "project_sql_aggregation",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("authority", ref("project_sql_aggregation_authority")),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule("keys", seq(ref("project_sql_plan_ref"))),
                FieldRule("aggregates", seq(ref("project_sql_plan_ref"))),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("results", seq(ref("project_sql_plan_ref"))),
                FieldRule("empty_input", enum("no_groups", "one_global_row")),
            ),
        ),
        "project_sql_group_key": RecordRule(
            "project_sql_group_key",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("aggregation", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule(
                    "source",
                    union(
                        ref("project_group_key_fact"),
                        ref("project_joined_group_key_occurrence"),
                    ),
                ),
                FieldRule(
                    "reference",
                    union(
                        ref("project_module_expression_reference_fact"),
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        ),
                        ref("project_relation_clause_dependency_fact"),
                        ref("project_joined_satisfying_output_reference"),
                        ANCHOR,
                    ),
                ),
                FieldRule("input", ref("project_sql_plan_ref")),
                FieldRule("result", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_aggregate": RecordRule(
            "project_sql_aggregate",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("aggregation", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule(
                    "source",
                    union(
                        ref("project_aggregate_expression_analysis"),
                        ref("project_joined_aggregate_occurrence"),
                    ),
                ),
                FieldRule("arguments", seq(ref("project_sql_plan_ref"))),
                FieldRule("result", ref("project_sql_plan_ref")),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_sql_aggregate_site": RecordRule(
            "project_sql_aggregate_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "match",
                        "let",
                        "where",
                        "select",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                    ),
                ),
                FieldRule("ordinal", INTEGER),
                FieldRule(
                    "occurrence", union(ref("select_item"), ref("satisfying_clause"))
                ),
                FieldRule("expression", ANCHOR),
                FieldRule("aggregation", ref("project_sql_plan_ref")),
                FieldRule("authority", ref("project_sql_aggregation_authority")),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_aggregate_expression_analysis"),
                        ref("project_concrete_joined_namespace_expression"),
                        ref("project_joined_satisfying_analysis"),
                        ref("satisfying_result_predicate_info"),
                    ),
                ),
                FieldRule(
                    "references",
                    seq(
                        union(
                            ref("project_module_expression_reference_fact"),
                            union(
                                ref("project_joined_let_reference_resolution"),
                                ref("project_scalar_reference_resolution"),
                            ),
                            ref("project_relation_clause_dependency_fact"),
                            ref("project_joined_satisfying_output_reference"),
                            ANCHOR,
                        )
                    ),
                ),
            ),
        ),
        "project_sql_result_reference": RecordRule(
            "project_sql_result_reference",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("site", ref("project_sql_aggregate_site")),
                FieldRule("expression", ANCHOR),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "reference",
                    union(
                        ref("project_module_expression_reference_fact"),
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        ),
                        ref("project_relation_clause_dependency_fact"),
                        ref("project_joined_satisfying_output_reference"),
                        ANCHOR,
                    ),
                ),
                FieldRule("port", ref("project_sql_plan_ref")),
                FieldRule("symbol", ref("project_sql_symbol")),
            ),
        ),
        "project_sql_aggregate_argument_call": RecordRule(
            "project_sql_aggregate_argument_call",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("site", ref("project_sql_aggregate_site")),
                FieldRule("expression", ref("call_expr")),
                FieldRule("value_type", ref("value_type")),
                FieldRule("arguments", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_aggregate_projection": RecordRule(
            "project_sql_aggregate_projection",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("aggregation", ref("project_sql_plan_ref")),
                FieldRule("semantic", ref("project_module_select_fact")),
                FieldRule(
                    "source",
                    union(
                        ref("project_aggregate_selected_result"),
                        ref("project_grouped_selected_result"),
                        ref("project_joined_stage_output_occurrence"),
                    ),
                ),
                FieldRule("input", ref("project_sql_plan_ref")),
                FieldRule("export", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_aggregate_risk": RecordRule(
            "project_sql_aggregate_risk",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("aggregation", ref("project_sql_plan_ref")),
                FieldRule(
                    "source",
                    union(
                        ref("project_joined_group_protection"),
                        ref("project_joined_aggregate_grain_linkage"),
                        ref("project_joined_aggregate_pair_linkage"),
                    ),
                ),
            ),
        ),
        "project_sql_aggregate_demand": RecordRule(
            "project_sql_aggregate_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "grouping_and_empty_input",
                        "group_comparison",
                        "aggregate_operation",
                        "result_projection",
                        "retained_risk",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_aggregation"),
                        ref("project_sql_group_key"),
                        ref("project_sql_aggregate"),
                        ref("project_sql_aggregate_projection"),
                        ref("project_sql_aggregate_risk"),
                    ),
                ),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_window": RecordRule(
            "project_sql_window",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule(
                    "source",
                    union(
                        ref("project_module_window_output_fact"),
                        ref("project_concrete_window_computation"),
                        ref("project_no_join_hidden_window_computation"),
                    ),
                ),
                FieldRule(
                    "selected",
                    union(
                        union(
                            ref("project_module_window_output_fact"),
                            ref("project_selected_window_result_binding"),
                        ),
                        optional,
                    ),
                ),
                FieldRule("authored", ref("window_expr")),
                FieldRule("effective", ref("window_expr")),
                FieldRule("function", ref("window_function_identity")),
                FieldRule(
                    "context",
                    union(
                        ref("window_computation_input"),
                        ref("project_no_join_window_input"),
                        ref("project_joined_window_input_namespace"),
                    ),
                ),
                FieldRule("inputs", seq(ref("project_sql_plan_ref"))),
                FieldRule("uses", seq(ref("project_sql_plan_ref"))),
                FieldRule("arguments", seq(ref("project_sql_plan_ref"))),
                FieldRule("result", ref("project_sql_plan_ref")),
                FieldRule("value_type", ref("value_type")),
                FieldRule("policy", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_window_use": RecordRule(
            "project_sql_window_use",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("window", ref("project_sql_plan_ref")),
                FieldRule(
                    "source",
                    union(
                        ref("window_dependency_occurrence"),
                        ref("project_window_dependency_occurrence"),
                        ref("project_no_join_hidden_window_input_use"),
                    ),
                ),
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "window_argument",
                        "window_default",
                        "window_partition",
                        "window_order",
                    ),
                ),
                FieldRule("position", INTEGER),
                FieldRule("role_position", INTEGER),
                FieldRule("expression", ANCHOR),
                FieldRule("input", union(ref("project_sql_plan_ref"), optional)),
                FieldRule(
                    "binding",
                    union(
                        ref("window_input_binding"),
                        ref("project_joined_window_input_binding"),
                        optional,
                    ),
                ),
                FieldRule("value_type", union(ref("value_type"), optional)),
            ),
        ),
        "project_sql_window_argument": RecordRule(
            "project_sql_window_argument",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("window", ref("project_sql_plan_ref")),
                FieldRule("position", INTEGER),
                FieldRule(
                    "role", enum("value", "default", "offset", "bucket", "position")
                ),
                FieldRule("expression", ANCHOR),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("use", union(ref("project_sql_plan_ref"), optional)),
            ),
        ),
        "project_sql_window_policy": RecordRule(
            "project_sql_window_policy",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("window", ref("project_sql_plan_ref")),
                FieldRule("specification", ref("validated_window_specification")),
                FieldRule("partitions", seq(ref("window_partition_field_binding"))),
                FieldRule("orders", seq(ref("window_order_field_binding"))),
                FieldRule(
                    "modifiers",
                    union(ref("resolved_window_function_modifiers"), optional),
                ),
                FieldRule(
                    "named_use", union(ref("resolved_named_window_use"), optional)
                ),
                FieldRule(
                    "namespace", union(ref("resolved_named_window_namespace"), optional)
                ),
                FieldRule(
                    "ranking",
                    union(
                        enum(
                            "per_row",
                            "preceding_row_count_plus_one",
                            "preceding_distinct_peer_group_count_plus_one",
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "distribution",
                    union(
                        enum(
                            "percent_rank",
                            "cumulative_distribution",
                            "balanced_buckets",
                        ),
                        optional,
                    ),
                ),
                FieldRule("bucket_count", union(INTEGER, optional)),
                FieldRule(
                    "navigation",
                    union(
                        union(
                            ref("navigation_window_semantic_fact"),
                            ref("navigation_window_computation"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "frame_value",
                    union(
                        union(
                            ref("frame_value_window_semantic_fact"),
                            ref("frame_value_window_computation"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "ir_operator",
                    union(
                        ref("project_ir_logical_operator_occurrence"),
                        ref("project_ir_query_block_operator_occurrence"),
                    ),
                ),
                FieldRule(
                    "ir_policy",
                    union(
                        ref("project_ir_provided_evaluation_policy"),
                        ref("project_ir_query_block_window_policy"),
                        optional,
                    ),
                ),
                FieldRule(
                    "ir_effect",
                    union(
                        ref("project_ir_effect_evidence"),
                        ref("project_ir_query_block_effect_evidence"),
                    ),
                ),
            ),
        ),
        "project_sql_qualify_site": RecordRule(
            "project_sql_qualify_site",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule(
                    "role",
                    enum(
                        "match",
                        "let",
                        "where",
                        "select",
                        "aggregate_argument",
                        "satisfying",
                        "qualify",
                    ),
                ),
                FieldRule("ordinal", INTEGER),
                FieldRule("occurrence", ref("qualify_clause")),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_no_join_qualify"),
                        ref("project_concrete_joined_qualify"),
                    ),
                ),
                FieldRule(
                    "aggregate",
                    union(ref("project_sql_aggregation_authority"), optional),
                ),
                FieldRule(
                    "references",
                    seq(
                        union(
                            ref("project_no_join_qualify_reference_resolution"),
                            ref("project_qualify_reference_resolution"),
                            ref("project_no_join_hidden_window_computation"),
                            ref("project_concrete_window_computation"),
                        )
                    ),
                ),
            ),
        ),
        "project_sql_window_reference": RecordRule(
            "project_sql_window_reference",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("site", ref("project_sql_qualify_site")),
                FieldRule("expression", ANCHOR),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "reference",
                    union(
                        ref("project_no_join_qualify_reference_resolution"),
                        ref("project_qualify_reference_resolution"),
                        ref("project_no_join_hidden_window_computation"),
                        ref("project_concrete_window_computation"),
                    ),
                ),
                FieldRule("port", ref("project_sql_plan_ref")),
                FieldRule("symbol", ref("project_sql_symbol")),
            ),
        ),
        "project_sql_window_projection": RecordRule(
            "project_sql_window_projection",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("window", ref("project_sql_plan_ref")),
                FieldRule("block", ref("project_sql_plan_ref")),
                FieldRule("semantic", ref("project_module_select_fact")),
                FieldRule(
                    "source",
                    union(
                        ref("project_module_window_output_fact"),
                        ref("project_selected_window_result_binding"),
                    ),
                ),
                FieldRule("input", ref("project_sql_plan_ref")),
                FieldRule("export", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_window_demand": RecordRule(
            "project_sql_window_demand",
            (
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "input_bag_and_result",
                        "input_use",
                        "argument",
                        "frame_modifiers_named_components",
                        "result_projection",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_window"),
                        ref("project_sql_window_use"),
                        ref("project_sql_window_argument"),
                        ref("project_sql_window_policy"),
                        ref("project_sql_window_projection"),
                    ),
                ),
                FieldRule("origin", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_demand_scope": RecordRule(
            "project_sql_demand_scope",
            (
                FieldRule("definition", ref("project_sql_plan_ref")),
                FieldRule("stages", seq(ref("project_sql_plan_ref"))),
                FieldRule("input_uses", seq(ref("project_sql_plan_ref"))),
            ),
        ),
        "project_sql_demand_entry": RecordRule(
            "project_sql_demand_entry",
            (
                FieldRule("position", INTEGER),
                FieldRule("ref", ref("project_sql_plan_ref")),
                FieldRule(
                    "demand",
                    union(
                        ref("project_sql_literal_demand"),
                        ref("project_sql_set_demand"),
                        ref("project_sql_result_demand"),
                        ref("project_sql_source_realization_demand"),
                        ref("project_sql_export_representation_demand"),
                        ref("project_sql_expression_demand"),
                        ref("project_sql_stage_value_demand"),
                        ref("project_sql_filter_demand"),
                        ref("project_sql_scope_demand"),
                        ref("project_sql_join_demand"),
                        ref("project_sql_aggregate_demand"),
                        ref("project_sql_window_demand"),
                    ),
                ),
                FieldRule(
                    "family",
                    enum(
                        "source_realization",
                        "export_representation",
                        "expression",
                        "stage_value",
                        "filter",
                        "scope",
                        "join",
                        "aggregation",
                        "window",
                        "result",
                        "set",
                        "fixed_literal_transport",
                    ),
                ),
                FieldRule(
                    "subkind",
                    union(
                        enum(
                            "match",
                            "let",
                            "where",
                            "select",
                            "aggregate_argument",
                            "satisfying",
                            "qualify",
                        ),
                        enum(
                            "let",
                            "where",
                            "projection",
                            "aggregate",
                            "satisfying",
                            "window",
                            "qualify",
                        ),
                        enum("input", "export"),
                        enum(
                            "join_rows",
                            "match_input",
                            "match_field",
                            "output_field",
                            "relationship_equality",
                            "post_match_scope",
                            "single_match",
                            "proof_context",
                        ),
                        enum(
                            "grouping_and_empty_input",
                            "group_comparison",
                            "aggregate_operation",
                            "result_projection",
                            "retained_risk",
                        ),
                        enum(
                            "input_bag_and_result",
                            "input_use",
                            "argument",
                            "frame_modifiers_named_components",
                            "result_projection",
                        ),
                        enum(
                            "result_scope_and_membership",
                            "result_value_representation",
                            "visible_row_quotient",
                            "field_equivalence_nulls_and_type_sources",
                            "relation_order_scope",
                            "order_direction_nulls_and_ties",
                            "order_expression_type_and_operands",
                            "order_value_use",
                            "pending_strict_fd_order_realization",
                            "static_row_count_upper_bound",
                            "canonical_result_image",
                        ),
                        enum(
                            "set_operation_quantifier_multiplicity_and_membership",
                            "set_properties_and_row_domain",
                            "set_whole_row_equivalence",
                            "set_operand_membership",
                            "set_input_type_null_and_representation",
                            "set_positional_column_and_value_sources",
                        ),
                        enum("Bool", "Int", "Text", "Float"),
                        optional,
                    ),
                ),
                FieldRule("subject", ref("project_sql_plan_ref")),
                FieldRule("scope", ref("project_sql_demand_scope")),
                FieldRule("origin", ref("project_sql_origin")),
            ),
        ),
        "project_sql_demand_link": RecordRule(
            "project_sql_demand_link",
            (
                FieldRule("position", INTEGER),
                FieldRule(
                    "kind",
                    enum(
                        "literal_ancestor_context",
                        "single_match_root_proof",
                        "single_match_child_proof",
                    ),
                ),
                FieldRule("source", ref("project_sql_demand_entry")),
                FieldRule("target", ref("project_sql_demand_entry")),
            ),
        ),
        "project_sql_single_match_report": RecordRule(
            "project_sql_single_match_report",
            (
                FieldRule("original", ref("project_sql_single_match")),
                FieldRule("entry", ref("project_sql_demand_entry")),
                FieldRule("proof_entries", seq(ref("project_sql_demand_entry"))),
                FieldRule("state", enum("proved", "legal_unproved", "invalid")),
                FieldRule("enforcement_required", BOOLEAN),
                FieldRule("diagnostic", union(ref("diagnostic"), optional)),
            ),
        ),
        "project_sql_hidden_order_report": RecordRule(
            "project_sql_hidden_order_report",
            (
                FieldRule("original", ref("project_sql_hidden_order_requirement")),
                FieldRule("entry", ref("project_sql_demand_entry")),
                FieldRule("posture", enum("pending_lowering_realization")),
            ),
        ),
        "project_sql_aggregate_evidence_report": RecordRule(
            "project_sql_aggregate_evidence_report",
            (
                FieldRule("original", ref("project_sql_aggregate_risk")),
                FieldRule("entry", ref("project_sql_demand_entry")),
                FieldRule(
                    "kind", enum("group_protection", "grain_linkage", "pair_linkage")
                ),
            ),
        ),
        "project_sql_demand_family_report": RecordRule(
            "project_sql_demand_family_report",
            (
                FieldRule(
                    "family",
                    enum(
                        "source_realization",
                        "export_representation",
                        "expression",
                        "stage_value",
                        "filter",
                        "scope",
                        "join",
                        "aggregation",
                        "window",
                        "result",
                        "set",
                        "fixed_literal_transport",
                    ),
                ),
                FieldRule("entries", seq(ref("project_sql_demand_entry"))),
            ),
        ),
        "project_sql_requirement_summary": RecordRule(
            "project_sql_requirement_summary",
            (
                FieldRule("demand_count", INTEGER),
                FieldRule("families", seq(ref("project_sql_demand_family_report"))),
                FieldRule(
                    "original_proved", seq(ref("project_sql_single_match_report"))
                ),
                FieldRule(
                    "enforcement_required", seq(ref("project_sql_single_match_report"))
                ),
                FieldRule(
                    "pending_realizations", seq(ref("project_sql_hidden_order_report"))
                ),
                FieldRule(
                    "aggregate_evidence",
                    seq(ref("project_sql_aggregate_evidence_report")),
                ),
                FieldRule("target", enum("not_assessed")),
            ),
        ),
        "project_sql_requirement_report": RecordRule(
            "project_sql_requirement_report",
            (
                FieldRule("plan", ref("project_sql_plan")),
                FieldRule("selected_owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "literal_policy", enum("preserve_literals", "bind_safe_literals")
                ),
                FieldRule("envelope", ref("project_sql_fixed_envelope")),
                FieldRule("diagnostics", seq(ref("diagnostic"))),
                FieldRule("input_uses", seq(ref("project_sql_input_use"))),
                FieldRule("entries", seq(ref("project_sql_demand_entry"))),
                FieldRule("links", seq(ref("project_sql_demand_link"))),
                FieldRule(
                    "single_matches", seq(ref("project_sql_single_match_report"))
                ),
                FieldRule(
                    "hidden_realizations", seq(ref("project_sql_hidden_order_report"))
                ),
                FieldRule(
                    "aggregate_evidence",
                    seq(ref("project_sql_aggregate_evidence_report")),
                ),
                FieldRule("summary", ref("project_sql_requirement_summary")),
            ),
        ),
        "project_sql_source_position": RecordRule(
            "project_sql_source_position",
            (
                FieldRule(
                    "original", union(ref("span"), ref("source_location"), optional)
                ),
                FieldRule("path", union(TEXT, optional)),
                FieldRule("line", union(INTEGER, optional)),
                FieldRule("column", union(INTEGER, optional)),
                FieldRule("end_line", union(INTEGER, optional)),
                FieldRule("end_column", union(INTEGER, optional)),
                FieldRule("availability", enum("complete", "partial", "unavailable")),
            ),
        ),
        "project_sql_mapped_source": RecordRule(
            "project_sql_mapped_source",
            (
                FieldRule("position", INTEGER),
                FieldRule("module", ref("project_logical_module")),
            ),
        ),
        "project_sql_source_site": RecordRule(
            "project_sql_source_site",
            (
                FieldRule("position", INTEGER),
                FieldRule("source", ref("project_sql_mapped_source")),
                FieldRule("occurrence", ANCHOR),
                FieldRule("container", ANCHOR),
                FieldRule(
                    "declaration",
                    union(ref("project_declaration_occurrence"), optional),
                ),
                FieldRule("location", ref("project_sql_source_position")),
            ),
        ),
        "project_sql_source_map_entry": RecordRule(
            "project_sql_source_map_entry",
            (
                FieldRule("position", INTEGER),
                FieldRule("original", ref("project_sql_origin")),
                FieldRule(
                    "nature", enum("syntax_correspondence", "generated_structure")
                ),
                FieldRule(
                    "generated_reason",
                    union(
                        enum(
                            "literal_site",
                            "literal_slot",
                            "fixed_literal_value",
                            "bind_use",
                            "set_body",
                            "set_operand",
                            "set_input",
                            "set_column",
                            "result_boundary",
                            "result_port",
                            "distinct",
                            "quotient_field",
                            "relation_order",
                            "order_item",
                            "order_expression",
                            "order_use",
                            "hidden_order_requirement",
                            "result_limit",
                            "result_export",
                            "window",
                            "window_use",
                            "window_argument",
                            "window_policy",
                            "window_projection",
                            "aggregation",
                            "group_key",
                            "aggregate",
                            "aggregate_projection",
                            "aggregate_risk",
                            "join",
                            "join_input",
                            "join_port",
                            "relationship_match",
                            "join_tail",
                            "single_match",
                            "single_match_proof",
                            "expression_site",
                            "expression",
                            "operand",
                            "stage_port",
                            "let_value",
                            "filter",
                            "selected_owner",
                            "definition",
                            "source_descriptor",
                            "input_use",
                            "select_block",
                            "source_port",
                            "input_port",
                            "stage_export",
                            "projection",
                            "export",
                            "boundary",
                            "symbol",
                            "demand",
                        ),
                        optional,
                    ),
                ),
                FieldRule("consuming_definition", ref("project_sql_plan_ref")),
            ),
        ),
        "project_sql_source_association": RecordRule(
            "project_sql_source_association",
            (
                FieldRule("position", INTEGER),
                FieldRule("entry", ref("project_sql_source_map_entry")),
                FieldRule("site", ref("project_sql_source_site")),
                FieldRule(
                    "kind",
                    enum(
                        "authored_cause",
                        "expression_body",
                        "field_declaration",
                        "type_reference",
                        "referenced_declaration",
                        "import_item",
                        "export_item",
                        "source_connector",
                        "effective_to_authored_window",
                        "authored_or_inherited_window_component",
                        "named_window_declaration",
                    ),
                ),
                FieldRule("observed", ANCHOR),
                FieldRule("evidence", ANCHOR),
                FieldRule("path", union(ref("project_module_origin_path"), optional)),
                FieldRule("hop", union(ref("project_module_access_hop"), optional)),
            ),
        ),
        "project_sql_legacy_source_position": RecordRule(
            "project_sql_legacy_source_position",
            (
                FieldRule("position", INTEGER),
                FieldRule("entry", ref("project_sql_source_map_entry")),
                FieldRule("field", ref("project_row_field")),
                FieldRule("location", ref("project_sql_source_position")),
            ),
        ),
        "project_sql_mapped_subject": RecordRule(
            "project_sql_mapped_subject",
            (
                FieldRule(
                    "ref",
                    union(ref("project_sql_plan_scope"), ref("project_sql_plan_ref")),
                ),
                FieldRule("origins", seq(ref("project_sql_source_map_entry"))),
            ),
        ),
        "project_sql_source_link": RecordRule(
            "project_sql_source_link",
            (
                FieldRule("position", INTEGER),
                FieldRule("ordinal", INTEGER),
                FieldRule("origin", ref("project_sql_source_map_entry")),
                FieldRule("kind", enum("origin_ref", "subject_ref")),
                FieldRule(
                    "target",
                    union(
                        ref("project_sql_source_map_entry"),
                        ref("project_sql_mapped_subject"),
                    ),
                ),
            ),
        ),
        "project_sql_source_map": RecordRule(
            "project_sql_source_map",
            (
                FieldRule("plan", ref("project_sql_plan")),
                FieldRule(
                    "literal_policy", enum("preserve_literals", "bind_safe_literals")
                ),
                FieldRule("envelope", ref("project_sql_fixed_envelope")),
                FieldRule("diagnostics", seq(ref("diagnostic"))),
                FieldRule("sources", seq(ref("project_sql_mapped_source"))),
                FieldRule("sites", seq(ref("project_sql_source_site"))),
                FieldRule("entries", seq(ref("project_sql_source_map_entry"))),
                FieldRule("subjects", seq(ref("project_sql_mapped_subject"))),
                FieldRule("associations", seq(ref("project_sql_source_association"))),
                FieldRule(
                    "legacy_positions", seq(ref("project_sql_legacy_source_position"))
                ),
                FieldRule("links", seq(ref("project_sql_source_link"))),
            ),
        ),
        "project_declaration_occurrence": RecordRule(
            "project_declaration_occurrence",
            (
                FieldRule("module_position", INTEGER),
                FieldRule("declaration_position", INTEGER),
                FieldRule(
                    "definition",
                    union(
                        ref("type_def"),
                        ref("enum_def"),
                        ANCHOR,
                        ANCHOR,
                        ref("shape_def"),
                        ref("source_def"),
                        ref("table_def"),
                        ref("query_def"),
                        ref("set_relation_def"),
                    ),
                ),
            ),
        ),
        "query_def": RecordRule(
            "query_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "table_def": RecordRule(
            "table_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "set_relation_def": RecordRule(
            "set_relation_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule(
                    "kind", enum("type", "enum", "shape", "source", "table", "query")
                ),
                FieldRule("body", ref("set_operation_body")),
            ),
        ),
        "span": RecordRule(
            "span",
            (
                FieldRule("path", union(TEXT, optional)),
                FieldRule("line", INTEGER),
                FieldRule("column", INTEGER),
                FieldRule("end_line", INTEGER),
                FieldRule("end_column", INTEGER),
            ),
        ),
        "project_ir_reused_effective_output": RecordRule(
            "project_ir_reused_effective_output",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("semantic_entry", ref("project_existing_effective_output")),
                FieldRule(
                    "operators", seq(ref("project_ir_logical_operator_occurrence"))
                ),
            ),
        ),
        "project_existing_effective_output": RecordRule(
            "project_existing_effective_output",
            (FieldRule("owner", ref("project_declaration_occurrence")),),
        ),
        "project_logical_module": RecordRule(
            "project_logical_module",
            (
                FieldRule(
                    "compilation_mode",
                    enum("legacy_flat", "explicit_modules", "package_root"),
                ),
                FieldRule("path", TEXT),
                FieldRule("position", INTEGER),
            ),
        ),
        "source_def": RecordRule(
            "source_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("shape_name", union(TEXT, optional)),
                FieldRule("connector", ANCHOR),
            ),
        ),
        "call_expr": RecordRule(
            "call_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("callee", union(ref("name_expr"), ref("dotted_name_expr"))),
                FieldRule("arguments", seq(ANCHOR)),
            ),
        ),
        "project_ir_cross_relation_edge": RecordRule(
            "project_ir_cross_relation_edge",
            (
                FieldRule(
                    "producer", ref("project_ir_concrete_single_relation_fragment")
                ),
                FieldRule(
                    "consumer", ref("project_ir_concrete_single_relation_fragment")
                ),
                FieldRule("input_slot", ref("project_ir_input_slot_occurrence")),
                FieldRule("use", ref("project_ir_use_occurrence")),
            ),
        ),
        "project_completion_dependency": RecordRule(
            "project_completion_dependency",
            (
                FieldRule("consumer", ref("project_declaration_occurrence")),
                FieldRule("target", ref("project_declaration_occurrence")),
                FieldRule("dependency_ordinal", INTEGER),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_resolved_module_relation_reference"),
                        ref("project_relation_binding_occurrence"),
                        ref("project_resolved_set_operand"),
                    ),
                ),
            ),
        ),
        "project_resolved_module_relation_symbol": RecordRule(
            "project_resolved_module_relation_symbol",
            (
                FieldRule("local_name", TEXT),
                FieldRule("target_occurrence", ref("project_declaration_occurrence")),
                FieldRule(
                    "local_occurrence",
                    union(ref("project_declaration_occurrence"), optional),
                ),
                FieldRule(
                    "imported_binding",
                    union(ref("project_resolved_imported_binding"), optional),
                ),
            ),
        ),
        "project_module_origin_path": RecordRule(
            "project_module_origin_path",
            (
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("local_name", TEXT),
                FieldRule(
                    "target_occurrence", ref("project_declaration_occurrence_identity")
                ),
                FieldRule(
                    "local_occurrence",
                    union(ref("project_declaration_occurrence_identity"), optional),
                ),
                FieldRule(
                    "import_occurrence",
                    union(ref("project_module_import_occurrence_identity"), optional),
                ),
                FieldRule("hops", seq(ref("project_module_access_hop"))),
            ),
        ),
        "project_ir_output_field_occurrence": RecordRule(
            "project_ir_output_field_occurrence",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("field_position", INTEGER),
                FieldRule("evidence", ref("project_row_field")),
                FieldRule(
                    "effective_nullability", enum("non_null", "nullable", "unknown")
                ),
            ),
        ),
        "project_module_row_field_identity": RecordRule(
            "project_module_row_field_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "kind", enum("shape_field", "source_field", "relation_output")
                ),
                FieldRule("field_position", INTEGER),
                FieldRule("name", TEXT),
            ),
        ),
        "project_module_select_fact": RecordRule(
            "project_module_select_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("output_name", union(TEXT, optional)),
                FieldRule("field", union(ref("project_row_field"), optional)),
                FieldRule(
                    "aggregate_result_fact",
                    union(ref("project_aggregate_result_fact"), optional),
                ),
                FieldRule("references", seq(ANCHOR)),
            ),
        ),
        "select_item": RecordRule(
            "select_item",
            (
                FieldRule("span", ref("span")),
                FieldRule("alias", union(TEXT, optional)),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "from_clause": RecordRule(
            "from_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("source_name", TEXT),
            ),
        ),
        "project_row_field": RecordRule(
            "project_row_field",
            (
                FieldRule("name", TEXT),
                FieldRule("resolved_type", ref("project_resolved_type")),
                FieldRule("nullability", enum("non_null", "nullable", "unknown")),
                FieldRule("field_def", union(ref("field_def"), optional)),
                FieldRule(
                    "result_role",
                    enum(
                        "ordinary_row_value",
                        "group_key",
                        "aggregate_result",
                        "window_result",
                    ),
                ),
            ),
        ),
        "project_module_select_expression_fact": RecordRule(
            "project_module_select_expression_fact",
            (FieldRule("selection", ref("project_module_select_fact")),),
        ),
        "name_expr": RecordRule(
            "name_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "value_type": RecordRule(
            "value_type",
            (
                FieldRule("resolved_type", ref("resolved_type")),
                FieldRule("nullability", enum("non_null", "nullable", "unknown")),
                FieldRule("kind", enum("known", "unknown")),
            ),
        ),
        "literal_expr": RecordRule(
            "literal_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("value", union(TEXT, INTEGER, FLOAT, BOOLEAN, optional)),
            ),
        ),
        "project_resolved_type": RecordRule(
            "project_resolved_type",
            (
                FieldRule("name", TEXT),
                FieldRule("kind", enum("builtin", "type", "enum", "shape", "unknown")),
                FieldRule("symbol", union(ANCHOR, optional)),
            ),
        ),
        "project_row_schema": RecordRule(
            "project_row_schema",
            (
                FieldRule("fields", mapping(TEXT, ref("project_row_field"))),
                FieldRule("is_unknown", BOOLEAN),
            ),
        ),
        "project_relation_let_scope_facts": RecordRule(
            "project_relation_let_scope_facts",
            (
                FieldRule(
                    "status",
                    enum("concrete", "unknown", "deferred", "blocked", "absent"),
                ),
                FieldRule(
                    "reason",
                    enum(
                        "no_let_clause",
                        "upstream_concrete",
                        "upstream_unknown",
                        "upstream_deferred",
                        "upstream_blocked",
                        "let_diagnostics_suppressed",
                        "missing_or_unknown_value_type",
                    ),
                ),
                FieldRule("clause", union(ref("let_clause"), optional)),
                FieldRule("bindings", seq(ref("let_binding"))),
                FieldRule(
                    "definition", union(ref("table_def"), ref("query_def"), optional)
                ),
            ),
        ),
        "project_module_expression_reference_fact": RecordRule(
            "project_module_expression_reference_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "role",
                    union(
                        enum(
                            "relation_input",
                            "let_value",
                            "select_value",
                            "group_key",
                            "satisfying",
                            "grouped_order",
                            "window_partition",
                            "window_order",
                            "window_argument",
                            "window_default",
                        ),
                        enum("where_value"),
                    ),
                ),
                FieldRule("container_ordinal", INTEGER),
                FieldRule("dependency_ordinal", INTEGER),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("local_name", TEXT),
                FieldRule("input_field", union(ref("project_row_field"), optional)),
                FieldRule("let_candidates", seq(ref("let_binding"))),
                FieldRule("selected_output_candidates", seq(ref("select_item"))),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
            ),
        ),
        "shape_def": RecordRule(
            "shape_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "field_def": RecordRule(
            "field_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("type_expr", ref("type_expr")),
            ),
        ),
        "type_expr": RecordRule(
            "type_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("arguments", seq(ref("type_argument"))),
                FieldRule("nullability", enum("implicit", "nullable", "not_null")),
            ),
        ),
        "project_ir_logical_operator_occurrence": RecordRule(
            "project_ir_logical_operator_occurrence",
            (
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
                FieldRule(
                    "kind",
                    enum(
                        "relation_input",
                        "row_filter",
                        "group_aggregate",
                        "result_filter",
                        "window_evaluation",
                        "final_projection",
                        "relation_ordering",
                        "limit",
                    ),
                ),
                FieldRule("evidence", ref("project_module_relation_semantic_facts")),
            ),
        ),
        "dotted_name_expr": RecordRule(
            "dotted_name_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("parts", seq(TEXT)),
            ),
        ),
        "project_ir_concrete_single_relation_fragment": RecordRule(
            "project_ir_concrete_single_relation_fragment",
            (FieldRule("subject", ref("project_ir_concrete_relation_subject")),),
        ),
        "project_ir_input_slot_occurrence": RecordRule(
            "project_ir_input_slot_occurrence", (FieldRule("input_ordinal", INTEGER),)
        ),
        "project_ir_use_occurrence": RecordRule(
            "project_ir_use_occurrence",
            (
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "let_value",
                        "select_value",
                        "group_key",
                        "satisfying",
                        "grouped_order",
                        "window_partition",
                        "window_order",
                        "window_argument",
                        "window_default",
                    ),
                ),
                FieldRule("source_order", INTEGER),
                FieldRule(
                    "anchor", union(ref("project_ir_resolved_relation_anchor"), ANCHOR)
                ),
            ),
        ),
        "project_resolved_module_relation_reference": RecordRule(
            "project_resolved_module_relation_reference",
            (
                FieldRule("reference", ref("project_module_relation_reference")),
                FieldRule(
                    "target_symbol", ref("project_resolved_module_relation_symbol")
                ),
            ),
        ),
        "project_declaration_occurrence_identity": RecordRule(
            "project_declaration_occurrence_identity",
            (
                FieldRule("module_position", INTEGER),
                FieldRule("declaration_position", INTEGER),
            ),
        ),
        "project_ir_relation_row_output": RecordRule(
            "project_ir_relation_row_output",
            (FieldRule("occurrence", ref("project_ir_output_value_occurrence")),),
        ),
        "resolved_type": RecordRule(
            "resolved_type",
            (
                FieldRule("name", TEXT),
                FieldRule(
                    "kind", enum("builtin", "type_alias", "enum", "shape", "unknown")
                ),
                FieldRule("definition", union(ANCHOR, optional)),
            ),
        ),
        "project_ir_plan_node_occurrence": RecordRule(
            "project_ir_plan_node_occurrence",
            (
                FieldRule("ref", ref("project_ir_plan_node_ref")),
                FieldRule("anchor", ref("project_ir_relation_anchor")),
            ),
        ),
        "project_module_relation_semantic_facts": RecordRule(
            "project_module_relation_semantic_facts",
            (FieldRule("owner", ref("project_declaration_occurrence")),),
        ),
        "project_ir_concrete_relation_subject": RecordRule(
            "project_ir_concrete_relation_subject",
            (FieldRule("anchor", ref("project_ir_relation_anchor")),),
        ),
        "project_ir_resolved_relation_anchor": RecordRule(
            "project_ir_resolved_relation_anchor",
            (
                FieldRule("dependency", ref("project_module_dependency_fact")),
                FieldRule(
                    "reference", ref("project_module_reference_occurrence_identity")
                ),
                FieldRule("target", ref("project_declaration_occurrence_identity")),
            ),
        ),
        "project_module_relation_reference": RecordRule(
            "project_module_relation_reference",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("from_clause", ref("from_clause")),
            ),
        ),
        "project_ir_output_value_occurrence": RecordRule(
            "project_ir_output_value_occurrence",
            (
                FieldRule(
                    "anchor",
                    union(
                        ref("project_ir_relation_anchor"),
                        ref("project_ir_field_anchor"),
                        ref("project_ir_stage_field_anchor"),
                    ),
                ),
            ),
        ),
        "project_ir_relation_anchor": RecordRule(
            "project_ir_relation_anchor",
            (FieldRule("identity", ref("project_declaration_occurrence_identity")),),
        ),
        "project_module_dependency_fact": RecordRule(
            "project_module_dependency_fact",
            (
                FieldRule(
                    "kind",
                    enum(
                        "type_reference",
                        "source_shape_reference",
                        "relation_reference",
                        "row_field_reference",
                    ),
                ),
                FieldRule(
                    "reference", ref("project_module_reference_occurrence_identity")
                ),
                FieldRule(
                    "target_declaration",
                    union(ref("project_declaration_occurrence_identity"), optional),
                ),
                FieldRule(
                    "target_row_field",
                    union(ref("project_module_row_field_identity"), optional),
                ),
                FieldRule(
                    "origin_path", union(ref("project_module_origin_path"), optional)
                ),
            ),
        ),
        "project_module_reference_occurrence_identity": RecordRule(
            "project_module_reference_occurrence_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "role",
                    enum(
                        "type_alias_base",
                        "shape_field_type",
                        "source_shape",
                        "relation_from",
                        "row_field",
                    ),
                ),
                FieldRule("member_position", INTEGER),
            ),
        ),
        "let_binding": RecordRule(
            "let_binding",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "project_module_let_binding_fact": RecordRule(
            "project_module_let_binding_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("binding_ordinal", INTEGER),
                FieldRule("binding", ref("let_binding")),
                FieldRule("scope_facts", ref("project_relation_let_scope_facts")),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("references", seq(ANCHOR)),
            ),
        ),
        "where_clause": RecordRule(
            "where_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "project_module_where_fact": RecordRule(
            "project_module_where_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("where_clause")),
                FieldRule("input_schema", ref("project_row_schema")),
                FieldRule("let_scope", ref("project_relation_let_scope_facts")),
                FieldRule("references", seq(ANCHOR)),
            ),
        ),
        "binary_expr": RecordRule(
            "binary_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("left", ANCHOR),
                FieldRule("operator", TEXT),
                FieldRule("right", ANCHOR),
            ),
        ),
        "comparison_expr": RecordRule(
            "comparison_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("left", ANCHOR),
                FieldRule("operator", TEXT),
                FieldRule("right", ANCHOR),
            ),
        ),
        "unary_expr": RecordRule(
            "unary_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("operator", TEXT),
                FieldRule("operand", ANCHOR),
            ),
        ),
        "between_expr": RecordRule(
            "between_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("value", ANCHOR),
                FieldRule("lower", ANCHOR),
                FieldRule("upper", ANCHOR),
                FieldRule("negated", ANCHOR),
            ),
        ),
        "is_null_expr": RecordRule(
            "is_null_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("value", ANCHOR),
                FieldRule("negated", BOOLEAN),
            ),
        ),
        "project_joined_row_retention_effect": RecordRule(
            "project_joined_row_retention_effect",
            (
                FieldRule("truth", enum("true", "false", "unknown")),
                FieldRule("retain_row", BOOLEAN),
            ),
        ),
        "let_clause": RecordRule(
            "let_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("bindings", seq(ref("let_binding"))),
            ),
        ),
        "project_ir_completed_query_block_output": RecordRule(
            "project_ir_completed_query_block_output",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("semantic_entry", ref("project_completed_effective_output")),
                FieldRule(
                    "operators", seq(ref("project_ir_query_block_operator_occurrence"))
                ),
            ),
        ),
        "project_ir_query_block_relation_input_edge": RecordRule(
            "project_ir_query_block_relation_input_edge",
            (
                FieldRule("dependency", ref("project_completion_dependency")),
                FieldRule("producer", ref("project_ir_query_block_result_properties")),
                FieldRule("consumer", ref("project_ir_plan_node_occurrence")),
                FieldRule("input_slot", ref("project_ir_input_slot_occurrence")),
                FieldRule("use", ref("project_ir_use_occurrence")),
            ),
        ),
        "project_ir_set_operand_input": RecordRule(
            "project_ir_set_operand_input",
            (
                FieldRule("source", ref("project_set_operand_use")),
                FieldRule(
                    "producer",
                    union(
                        ref("project_ir_reused_effective_output"),
                        ref("project_ir_rebound_existing_output"),
                        ref("project_ir_completed_query_block_output"),
                        ref("project_ir_completed_set_operation_output"),
                    ),
                ),
                FieldRule("use", ref("project_ir_set_input_use_occurrence")),
            ),
        ),
        "project_ir_completed_set_operation_output": RecordRule(
            "project_ir_completed_set_operation_output",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("semantic_entry", ref("project_completed_set_output")),
            ),
        ),
        "project_ir_query_block_operator_occurrence": RecordRule(
            "project_ir_query_block_operator_occurrence",
            (
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
                FieldRule(
                    "kind",
                    union(
                        enum(
                            "relation_input",
                            "row_filter",
                            "group_aggregate",
                            "result_filter",
                            "window_evaluation",
                            "final_projection",
                            "relation_ordering",
                            "limit",
                        ),
                        enum("qualify", "distinct", "set_operation"),
                    ),
                ),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_concrete_joined_row_filter"),
                        ref("project_concrete_joined_aggregation"),
                        ref("project_joined_satisfying_analysis"),
                        ref("project_ir_query_block_window_evidence"),
                        ref("project_concrete_joined_qualify"),
                        ref("project_concrete_no_join_replay"),
                        ref("project_completed_effective_output"),
                        ref("project_relation_ordering"),
                        ref("project_relation_limit"),
                        ref("project_ir_distinct_comparison"),
                        ref("project_completed_set_output"),
                    ),
                ),
            ),
        ),
        "project_ir_query_block_result_properties": RecordRule(
            "project_ir_query_block_result_properties",
            (
                FieldRule("relational", ref("project_ir_output_relational_properties")),
                FieldRule("multiplicity", enum("bag")),
                FieldRule(
                    "ordering",
                    union(
                        union(
                            ref("project_ir_provided_relation_ordering"),
                            ref("project_relation_ordering"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "cardinality",
                    union(
                        union(
                            ref("project_ir_provided_cardinality_upper_bound"),
                            ref("project_relation_limit"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "effect",
                    union(
                        ref("project_ir_effect_evidence"),
                        ref("project_ir_query_block_effect_evidence"),
                    ),
                ),
            ),
        ),
        "project_ir_distinct_comparison": RecordRule(
            "project_ir_distinct_comparison",
            (
                FieldRule("semantic", ref("project_distinct")),
                FieldRule("input_output", ref("project_ir_query_block_row_output")),
            ),
        ),
        "project_ir_query_block_row_output": RecordRule(
            "project_ir_query_block_row_output",
            (FieldRule("occurrence", ref("project_ir_output_value_occurrence")),),
        ),
        "project_no_join_scalar_expression": RecordRule(
            "project_no_join_scalar_expression",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("expression", ANCHOR),
                FieldRule("status", enum("concrete", "type_non_concrete")),
                FieldRule("value_type", union(ref("value_type"), optional)),
            ),
        ),
        "project_completed_set_output_field": RecordRule(
            "project_completed_set_output_field",
            (
                FieldRule("source", ref("project_set_column")),
                FieldRule("output_position", INTEGER),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("output_name", TEXT),
                FieldRule("identity", ref("project_module_row_field_identity")),
                FieldRule("field", ref("project_row_field")),
                FieldRule("type_sources", seq(ref("project_row_equivalence_field"))),
            ),
        ),
        "project_distinct": RecordRule(
            "project_distinct",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("distinct_clause")),
                FieldRule("fields", seq(ref("project_completed_output_field"))),
                FieldRule("equivalence", ref("project_row_equivalence")),
                FieldRule("input_domain", ref("project_completed_row_domain")),
                FieldRule("global_input", BOOLEAN),
                FieldRule("origin", ref("project_distinct_grain_origin")),
                FieldRule("uniqueness", ref("project_distinct_full_row_uniqueness")),
            ),
        ),
        "project_distinct_full_row_uniqueness": RecordRule(
            "project_distinct_full_row_uniqueness",
            (
                FieldRule("distinct", ref("project_distinct")),
                FieldRule("nulls_equal", BOOLEAN),
            ),
        ),
        "project_completed_row_domain": RecordRule(
            "project_completed_row_domain",
            (
                FieldRule(
                    "kind", enum("preserved", "grouped", "global", "distinct", "set")
                ),
                FieldRule("distinct", union(ref("project_distinct"), optional)),
                FieldRule(
                    "set_origin", union(ref("project_set_grain_origin"), optional)
                ),
                FieldRule(
                    "preserved",
                    union(
                        union(
                            ref("project_ir_provided_intrinsic_grain"),
                            ref("project_completed_row_domain"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "grouped_basis",
                    seq(
                        union(
                            ref("project_joined_group_key_occurrence"),
                            ref("project_relation_clause_dependency_fact"),
                        )
                    ),
                ),
            ),
        ),
        "project_relation_ordering": RecordRule(
            "project_relation_ordering",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("order_by_clause")),
                FieldRule("items", seq(ref("project_relation_order_item"))),
                FieldRule(
                    "inputs",
                    union(seq(seq(ref("project_relation_order_input"))), optional),
                ),
            ),
        ),
        "project_relation_order_item": RecordRule(
            "project_relation_order_item",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("order_by_clause")),
                FieldRule("source_ordinal", INTEGER),
                FieldRule("item", ref("order_item")),
                FieldRule("expression", ANCHOR),
                FieldRule("direction", enum("asc", "desc")),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "source",
                    union(
                        ref("project_concrete_joined_namespace_expression"),
                        ref("project_joined_window_input_binding"),
                        ref("project_selected_window_result_binding"),
                        ref("project_no_join_scalar_expression"),
                        ref("project_module_clause_dependency_fact"),
                        ref("project_module_window_output_fact"),
                    ),
                ),
            ),
        ),
        "project_relation_order_input": RecordRule(
            "project_relation_order_input",
            (
                FieldRule("item", ref("project_relation_order_item")),
                FieldRule("expression", ANCHOR),
                FieldRule("position", INTEGER),
                FieldRule(
                    "resolution",
                    union(
                        ref("project_module_order_reference_fact"),
                        ref("project_scalar_reference_resolution"),
                        ref("project_joined_let_reference_resolution"),
                        ref("project_module_clause_dependency_fact"),
                        ref("project_module_window_output_fact"),
                        ref("project_joined_window_input_binding"),
                        ref("project_selected_window_result_binding"),
                    ),
                ),
                FieldRule("target", ANCHOR),
                FieldRule("determination_target", ANCHOR),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_relation_limit": RecordRule(
            "project_relation_limit",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("limit_clause")),
                FieldRule("literal", ref("literal_expr")),
                FieldRule("value", INTEGER),
                FieldRule("row_count_upper_bound", INTEGER),
            ),
        ),
        "project_set_full_row_uniqueness": RecordRule(
            "project_set_full_row_uniqueness",
            (
                FieldRule("output", ref("project_completed_set_output")),
                FieldRule("nulls_equal", BOOLEAN),
            ),
        ),
        "project_row_equivalence_field": RecordRule(
            "project_row_equivalence_field",
            (
                FieldRule(
                    "selected",
                    union(
                        ref("project_completed_output_field"),
                        ref("project_row_equivalence_input"),
                    ),
                ),
                FieldRule("types", ref("project_type_source_resolution_set")),
                FieldRule(
                    "resolution",
                    union(ref("project_resolved_module_type_reference"), optional),
                ),
                FieldRule("decimal_type_expr", union(ref("type_expr"), optional)),
                FieldRule("decimal", union(ref("decimal_precision_scale"), optional)),
                FieldRule(
                    "reason",
                    union(
                        enum(
                            "unknown_type",
                            "float_equivalence_deferred_to_phase72",
                            "unsupported_type",
                            "decimal_parameters_missing_or_unpropagated",
                            "decimal_parameters_invalid",
                            "type_evidence_mismatch",
                        ),
                        optional,
                    ),
                ),
                FieldRule("parents", seq(ref("project_row_equivalence_field"))),
            ),
        ),
        "project_distinct_grain_origin": RecordRule(
            "project_distinct_grain_origin",
            (
                FieldRule("witness", ref("project_distinct")),
                FieldRule(
                    "kind",
                    enum(
                        "source_row_domain",
                        "grouped_result",
                        "global_aggregate",
                        "distinct_quotient",
                        "set_alternatives",
                        "set_quotient",
                        "set_subset",
                    ),
                ),
                FieldRule(
                    "factor",
                    union(ref("project_distinct_grain_factor_identity"), optional),
                ),
            ),
        ),
        "project_set_operation": RecordRule(
            "project_set_operation",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "multiplicity",
                    enum(
                        "union_all",
                        "union_distinct",
                        "intersect_all",
                        "intersect_distinct",
                        "except_all",
                        "except_distinct",
                    ),
                ),
                FieldRule("requires_equivalence", BOOLEAN),
                FieldRule("full_row_unique", BOOLEAN),
            ),
        ),
        "project_set_column": RecordRule(
            "project_set_column",
            (
                FieldRule("uses", seq(ref("project_set_operand_use"))),
                FieldRule("position", INTEGER),
                FieldRule("kind", enum("union", "intersect", "except")),
                FieldRule("inputs", seq(ref("project_row_equivalence_field"))),
                FieldRule("nullability", enum("non_null", "nullable", "unknown")),
                FieldRule("resolved_type", ref("project_resolved_type")),
            ),
        ),
        "project_set_operand_use": RecordRule(
            "project_set_operand_use",
            (
                FieldRule("resolution", ref("project_resolved_set_operand")),
                FieldRule("dependency", ref("project_completion_dependency")),
                FieldRule("fields", seq(ref("project_row_equivalence_field"))),
            ),
        ),
        "project_resolved_module_type_reference": RecordRule(
            "project_resolved_module_type_reference",
            (
                FieldRule("reference", ref("project_module_type_reference")),
                FieldRule(
                    "direct_kind", enum("builtin", "type", "enum", "shape", "unknown")
                ),
                FieldRule(
                    "direct_symbol",
                    union(ref("project_resolved_nominal_symbol"), optional),
                ),
                FieldRule(
                    "canonical_kind",
                    enum("builtin", "type", "enum", "shape", "unknown"),
                ),
                FieldRule("canonical_name", TEXT),
                FieldRule(
                    "canonical_target_identity",
                    union(ref("project_nominal_declaration_identity"), optional),
                ),
                FieldRule(
                    "alias_chain", seq(ref("project_nominal_declaration_identity"))
                ),
            ),
        ),
        "project_type_source_resolution_set": RecordRule(
            "project_type_source_resolution_set",
            (FieldRule("dependency_order", seq(ref("project_module_identity"))),),
        ),
        "project_resolved_set_operand": RecordRule(
            "project_resolved_set_operand",
            (
                FieldRule("reference", ref("project_module_set_operand_reference")),
                FieldRule(
                    "candidates", seq(ref("project_resolved_module_relation_symbol"))
                ),
            ),
        ),
        "project_ir_output_determination_result": RecordRule(
            "project_ir_output_determination_result",
            (
                FieldRule("seed", ref("project_ir_output_value_class_set")),
                FieldRule("requested", ref("project_ir_output_value_class_set")),
                FieldRule("closure", ref("project_ir_output_strict_closure")),
                FieldRule("status", enum("proven", "not_proven")),
            ),
        ),
        "project_ir_output_relational_properties": RecordRule(
            "project_ir_output_relational_properties",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("fields", seq(ref("project_ir_output_field_occurrence"))),
                FieldRule("value_classes", seq(ref("project_ir_output_value_class"))),
                FieldRule("keys", seq(ref("project_ir_output_candidate_key"))),
                FieldRule("fds", seq(ref("project_ir_output_value_fd"))),
                FieldRule("grain", ref("project_ir_provided_intrinsic_grain")),
            ),
        ),
        "project_ir_output_value_class": RecordRule(
            "project_ir_output_value_class",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("members", seq(ref("project_ir_output_field_occurrence"))),
            ),
        ),
        "project_ir_output_value_class_set": RecordRule(
            "project_ir_output_value_class_set",
            (
                FieldRule("index", ref("project_ir_output_fd_index")),
                FieldRule("classes", seq(ref("project_ir_output_value_class"))),
            ),
        ),
        "project_ir_output_fd_index": RecordRule(
            "project_ir_output_fd_index",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("universe", seq(ref("project_ir_output_value_class"))),
                FieldRule("facts", seq(ref("project_ir_output_value_fd"))),
            ),
        ),
        "project_ir_output_strict_closure": RecordRule(
            "project_ir_output_strict_closure",
            (
                FieldRule("seed", ref("project_ir_output_value_class_set")),
                FieldRule("classes", ref("project_ir_output_value_class_set")),
                FieldRule("witness", seq(ref("project_ir_output_fd_proof_step"))),
            ),
        ),
        "project_ir_output_fd_proof_step": RecordRule(
            "project_ir_output_fd_proof_step",
            (
                FieldRule("fact", ref("project_ir_output_value_fd")),
                FieldRule("derived", seq(ref("project_ir_output_value_class"))),
            ),
        ),
        "project_ir_output_value_fd": RecordRule(
            "project_ir_output_value_fd",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("determinants", seq(ref("project_ir_output_value_class"))),
                FieldRule("dependents", seq(ref("project_ir_output_value_class"))),
                FieldRule("strength", enum("strict", "lax")),
                FieldRule("supports", seq(ANCHOR)),
            ),
        ),
        "project_ir_output_candidate_key": RecordRule(
            "project_ir_output_candidate_key",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("determinants", seq(ref("project_ir_output_value_class"))),
                FieldRule("strength", enum("strict", "lax")),
                FieldRule("supports", seq(ANCHOR)),
            ),
        ),
        "project_ir_provided_intrinsic_grain": RecordRule(
            "project_ir_provided_intrinsic_grain",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_relation_row_output"),
                        ref("project_ir_join_row_output"),
                        ANCHOR,
                    ),
                ),
                FieldRule("state", enum("factorized", "global", "unknown", "conflict")),
                FieldRule("factors", seq(ref("project_grain_domain_factor"))),
                FieldRule(
                    "active",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
                FieldRule("dependencies", seq(ref("project_grain_dependency_fact"))),
                FieldRule("witness", union(ANCHOR, seq(ANCHOR))),
            ),
        ),
        "set_operand": RecordRule(
            "set_operand",
            (
                FieldRule("span", ref("span")),
                FieldRule("relation_name", TEXT),
            ),
        ),
        "distinct_clause": RecordRule(
            "distinct_clause", (FieldRule("span", ref("span")),)
        ),
        "order_by_clause": RecordRule(
            "order_by_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("items", seq(ref("order_item"))),
            ),
        ),
        "order_item": RecordRule(
            "order_item",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
                FieldRule("direction", union(TEXT, optional)),
            ),
        ),
        "limit_clause": RecordRule(
            "limit_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "set_operation_body": RecordRule(
            "set_operation_body",
            (
                FieldRule("span", ref("span")),
                FieldRule("kind", enum("union", "intersect", "except")),
                FieldRule("operator_span", ref("span")),
                FieldRule("quantifier", union(enum("all", "distinct"), optional)),
                FieldRule("quantifier_span", union(ref("span"), optional)),
                FieldRule("operands", seq(ref("set_operand"))),
            ),
        ),
        "type_argument": RecordRule(
            "type_argument",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", union(TEXT, optional)),
                FieldRule("value", ANCHOR),
            ),
        ),
        "project_module_identity": RecordRule(
            "project_module_identity", (FieldRule("path", TEXT),)
        ),
        "project_completed_effective_output": RecordRule(
            "project_completed_effective_output",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "root",
                    union(
                        ref("project_concrete_joined_qualify"),
                        ref("project_concrete_no_join_replay"),
                    ),
                ),
            ),
        ),
        "project_completed_set_output": RecordRule(
            "project_completed_set_output",
            (FieldRule("root", ref("project_set_operation")),),
        ),
        "project_completed_output_field": RecordRule(
            "project_completed_output_field",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("select_fact", ref("project_module_select_fact")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("output_name", TEXT),
                FieldRule("identity", ref("project_module_row_field_identity")),
                FieldRule(
                    "source",
                    union(
                        ref("project_concrete_joined_namespace_expression"),
                        ref("project_joined_stage_output_occurrence"),
                        ref("project_selected_window_result_binding"),
                        ref("project_no_join_scalar_expression"),
                        ANCHOR,
                        ref("project_module_window_output_fact"),
                    ),
                ),
                FieldRule("type_sources", seq(ref("project_row_equivalence_field"))),
                FieldRule("field", ref("project_row_field")),
                FieldRule(
                    "result_role",
                    enum(
                        "ordinary_row_value",
                        "group_key",
                        "aggregate_result",
                        "window_result",
                    ),
                ),
            ),
        ),
        "project_concrete_no_join_replay": RecordRule(
            "project_concrete_no_join_replay",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule("input_schema", ref("project_row_schema")),
            ),
        ),
        "project_ir_set_input_use_occurrence": RecordRule(
            "project_ir_set_input_use_occurrence",
            (
                FieldRule("output", ref("project_ir_output_value_occurrence")),
                FieldRule("slot", ref("project_ir_input_slot_occurrence")),
            ),
        ),
        "project_ir_query_block_effect_evidence": RecordRule(
            "project_ir_query_block_effect_evidence",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_query_block_row_output"),
                        ref("project_ir_query_block_scalar_output"),
                        ref("project_ir_join_row_output"),
                    ),
                ),
                FieldRule("determinism", enum("unknown", "deterministic", "volatile")),
                FieldRule(
                    "error_behavior", enum("unknown", "may_error", "cannot_error")
                ),
                FieldRule(
                    "side_effects",
                    enum("unknown", "has_side_effects", "side_effect_free"),
                ),
                FieldRule(
                    "evaluation_count", enum("unknown", "sensitive", "insensitive")
                ),
            ),
        ),
        "project_ir_effect_evidence": RecordRule(
            "project_ir_effect_evidence",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_scalar_field_output"),
                        ref("project_ir_stage_scalar_field_output"),
                        ref("project_ir_relation_row_output"),
                    ),
                ),
                FieldRule("determinism", enum("unknown", "deterministic", "volatile")),
                FieldRule(
                    "error_behavior", enum("unknown", "may_error", "cannot_error")
                ),
                FieldRule(
                    "side_effects",
                    enum("unknown", "has_side_effects", "side_effect_free"),
                ),
                FieldRule(
                    "evaluation_count", enum("unknown", "sensitive", "insensitive")
                ),
            ),
        ),
        "project_row_equivalence": RecordRule(
            "project_row_equivalence",
            (
                FieldRule("fields", seq(ref("project_completed_output_field"))),
                FieldRule("types", ref("project_type_source_resolution_set")),
                FieldRule("evidence", seq(ref("project_row_equivalence_field"))),
            ),
        ),
        "project_row_equivalence_input": RecordRule(
            "project_row_equivalence_input",
            (
                FieldRule("field_position", INTEGER),
                FieldRule("identity", ref("project_module_row_field_identity")),
                FieldRule("original", ANCHOR),
                FieldRule("type_sources", seq(ref("project_row_equivalence_field"))),
                FieldRule("field", ref("project_row_field")),
            ),
        ),
        "project_distinct_grain_factor_identity": RecordRule(
            "project_distinct_grain_factor_identity",
            (
                FieldRule("origin", ref("project_distinct_grain_origin")),
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "kind",
                    enum(
                        "source_domain", "group_domain", "distinct_domain", "set_domain"
                    ),
                ),
            ),
        ),
        "project_set_grain_origin": RecordRule(
            "project_set_grain_origin",
            (
                FieldRule("witness", ref("project_set_operation")),
                FieldRule("input_domains", seq(ANCHOR)),
                FieldRule(
                    "kind",
                    enum(
                        "source_row_domain",
                        "grouped_result",
                        "global_aggregate",
                        "distinct_quotient",
                        "set_alternatives",
                        "set_quotient",
                        "set_subset",
                    ),
                ),
                FieldRule(
                    "factor", union(ref("project_set_grain_factor_identity"), optional)
                ),
            ),
        ),
        "project_concrete_grain_origin": RecordRule(
            "project_concrete_grain_origin",
            (FieldRule("identity", ref("project_grain_origin_identity")),),
        ),
        "project_grain_domain_factor": RecordRule(
            "project_grain_domain_factor",
            (
                FieldRule(
                    "identity",
                    union(
                        ref("project_source_grain_factor_identity"),
                        ref("project_grouped_grain_factor_identity"),
                        ref("project_distinct_grain_factor_identity"),
                        ref("project_set_grain_factor_identity"),
                        ref("project_join_grain_factor_identity"),
                    ),
                ),
            ),
        ),
        "project_source_grain_factor_identity": RecordRule(
            "project_source_grain_factor_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "kind",
                    enum(
                        "source_domain", "group_domain", "distinct_domain", "set_domain"
                    ),
                ),
            ),
        ),
        "project_set_grain_factor_identity": RecordRule(
            "project_set_grain_factor_identity",
            (
                FieldRule("origin", ref("project_set_grain_origin")),
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "kind",
                    enum(
                        "source_domain", "group_domain", "distinct_domain", "set_domain"
                    ),
                ),
            ),
        ),
        "project_module_order_reference_fact": RecordRule(
            "project_module_order_reference_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("item", ref("order_item")),
                FieldRule("container_ordinal", INTEGER),
                FieldRule("dependency_ordinal", INTEGER),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("local_name", TEXT),
                FieldRule("input_field", union(ref("project_row_field"), optional)),
                FieldRule("let_candidates", seq(ref("let_binding"))),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule("role", enum("order_value")),
            ),
        ),
        "project_module_type_reference": RecordRule(
            "project_module_type_reference",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("role", enum("type_alias_base", "shape_field_type")),
                FieldRule("member_position", INTEGER),
                FieldRule("type_expr", ref("type_expr")),
            ),
        ),
        "project_module_set_operand_reference": RecordRule(
            "project_module_set_operand_reference",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("operand_ordinal", INTEGER),
                FieldRule("operand", ref("set_operand")),
            ),
        ),
        "project_candidate_key_fact": RecordRule(
            "project_candidate_key_fact",
            (
                FieldRule("identity", ref("project_candidate_key_identity")),
                FieldRule("supports", seq(ref("project_row_uniqueness_evidence"))),
            ),
        ),
        "decimal_precision_scale": RecordRule(
            "decimal_precision_scale",
            (
                FieldRule("precision", INTEGER),
                FieldRule("scale", INTEGER),
            ),
        ),
        "project_grain_origin_identity": RecordRule(
            "project_grain_origin_identity",
            (
                FieldRule(
                    "kind",
                    enum(
                        "source_row_domain",
                        "grouped_result",
                        "global_aggregate",
                        "distinct_quotient",
                        "set_alternatives",
                        "set_quotient",
                        "set_subset",
                    ),
                ),
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule("operator", union(ref("project_ir_plan_node_ref"), optional)),
            ),
        ),
        "project_candidate_key_identity": RecordRule(
            "project_candidate_key_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule(
                    "determinants", seq(ref("project_module_row_field_identity"))
                ),
                FieldRule("strength", enum("strict", "lax")),
            ),
        ),
        "project_row_uniqueness_evidence": RecordRule(
            "project_row_uniqueness_evidence",
            (
                FieldRule("identity", ref("project_row_uniqueness_evidence_identity")),
                FieldRule("declaration", ref("project_unique_declaration_occurrence")),
                FieldRule("scope", ref("project_exact_row_output_constraint_scope")),
                FieldRule("determinants", seq(ref("project_unique_determinant_field"))),
                FieldRule("null_policy", enum("nulls_distinct", "nulls_not_distinct")),
                FieldRule("strength", enum("strict", "lax")),
                FieldRule(
                    "origin",
                    enum(
                        "authored_contract",
                        "catalog_constraint",
                        "derived_theorem",
                        "runtime_observation",
                        "unverified_hint",
                    ),
                ),
                FieldRule("trust", enum("trusted", "untrusted", "conflict")),
                FieldRule(
                    "enforcement",
                    enum("model_contract", "catalog_enforced", "runtime_observed"),
                ),
            ),
        ),
        "project_row_uniqueness_evidence_identity": RecordRule(
            "project_row_uniqueness_evidence_identity",
            (
                FieldRule("declaration", ref("project_unique_declaration_identity")),
                FieldRule("source", ref("project_declaration_occurrence_identity")),
            ),
        ),
        "project_unique_declaration_occurrence": RecordRule(
            "project_unique_declaration_occurrence",
            (
                FieldRule("identity", ref("project_unique_declaration_identity")),
                FieldRule("shape_occurrence", ref("project_declaration_occurrence")),
                FieldRule("unique", ref("unique_def")),
            ),
        ),
        "project_exact_row_output_constraint_scope": RecordRule(
            "project_exact_row_output_constraint_scope",
            (
                FieldRule(
                    "kind",
                    enum(
                        "unconditional_on_exact_row_output",
                        "under_predicate",
                        "under_policy",
                        "under_match_context",
                    ),
                ),
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
            ),
        ),
        "project_unique_determinant_field": RecordRule(
            "project_unique_determinant_field",
            (
                FieldRule(
                    "evidence_identity", ref("project_row_uniqueness_evidence_identity")
                ),
                FieldRule("determinant_position", INTEGER),
                FieldRule("field_def", ref("field_def")),
                FieldRule("source_origin", ref("project_module_source_field_origin")),
            ),
        ),
        "project_unique_declaration_identity": RecordRule(
            "project_unique_declaration_identity",
            (
                FieldRule("shape", ref("project_declaration_occurrence_identity")),
                FieldRule("shape_item_position", INTEGER),
            ),
        ),
        "unique_def": RecordRule(
            "unique_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("field_names", seq(TEXT)),
            ),
        ),
        "project_module_source_field_origin": RecordRule(
            "project_module_source_field_origin",
            (
                FieldRule("source_field", ref("project_module_row_field_identity")),
                FieldRule("shape_field", ref("project_module_row_field_identity")),
            ),
        ),
        "project_no_join_qualify": RecordRule(
            "project_no_join_qualify",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("kind", enum("absent", "authored_qualify")),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule("clause", union(ref("qualify_clause"), optional)),
                FieldRule(
                    "references",
                    seq(ref("project_no_join_qualify_reference_resolution")),
                ),
                FieldRule(
                    "predicate",
                    union(ref("__project_qualify_predicate_analysis"), optional),
                ),
            ),
        ),
        "project_no_join_qualify_reference_resolution": RecordRule(
            "project_no_join_qualify_reference_resolution",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule(
                    "target",
                    union(
                        union(
                            ref("window_input_binding"),
                            ref("project_module_window_output_fact"),
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "project_relation_clause_dependency_fact": RecordRule(
            "project_relation_clause_dependency_fact",
            (
                FieldRule(
                    "kind",
                    enum(
                        "group_key_input", "satisfying_output", "grouped_order_output"
                    ),
                ),
                FieldRule(
                    "source_occurrence",
                    union(ref("group_by_item"), ANCHOR, ref("order_item")),
                ),
                FieldRule(
                    "target_occurrence",
                    union(ref("project_group_key_fact"), ref("select_item")),
                ),
                FieldRule("target_field", ref("project_row_field")),
                FieldRule(
                    "aggregate_result_fact",
                    union(ref("project_aggregate_result_fact"), optional),
                ),
            ),
        ),
        "project_aggregate_grouped_clause_readiness": RecordRule(
            "project_aggregate_grouped_clause_readiness",
            (
                FieldRule("definition", union(ref("table_def"), ref("query_def"))),
                FieldRule("status", enum("concrete", "unknown", "deferred", "blocked")),
                FieldRule(
                    "reason",
                    enum(
                        "clauses_ready",
                        "schema_finalization_non_concrete",
                        "unavailable_clause_dependency",
                        "invalid_clause_output_reference",
                        "invalid_clause_expression",
                        "unsupported_clause_family",
                        "missing_required_clause_fact",
                        "conflicting_clause_facts",
                    ),
                ),
                FieldRule(
                    "dependency_facts",
                    seq(ref("project_relation_clause_dependency_fact")),
                ),
                FieldRule("limit_present", BOOLEAN),
                FieldRule(
                    "occurrence_facts",
                    union(
                        seq(ref("project_relation_clause_dependency_fact")), optional
                    ),
                ),
                FieldRule(
                    "satisfying",
                    union(ref("satisfying_result_predicate_info"), optional),
                ),
            ),
        ),
        "project_group_key_fact": RecordRule(
            "project_group_key_fact",
            (
                FieldRule("item", ref("group_by_item")),
                FieldRule(
                    "effective_expression",
                    union(ref("name_expr"), ref("dotted_name_expr")),
                ),
                FieldRule("field_identity", TEXT),
                FieldRule("input_field", ref("project_row_field")),
            ),
        ),
        "project_aggregate_expression_analysis": RecordRule(
            "project_aggregate_expression_analysis",
            (
                FieldRule("definition", union(ref("table_def"), ref("query_def"))),
                FieldRule("item", ref("select_item")),
                FieldRule("field", ref("project_row_field")),
                FieldRule("fact", ref("project_aggregate_result_fact")),
                FieldRule("effective_argument", union(ANCHOR, optional)),
                FieldRule("result_value_type", ref("value_type")),
            ),
        ),
        "project_grouped_selected_result": RecordRule(
            "project_grouped_selected_result",
            (
                FieldRule("field", ref("project_row_field")),
                FieldRule(
                    "aggregate_fact",
                    union(ref("project_aggregate_result_fact"), optional),
                ),
            ),
        ),
        "project_module_window_output_fact": RecordRule(
            "project_module_window_output_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("output_name", union(TEXT, optional)),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule("reason", union(TEXT, optional)),
            ),
        ),
        "project_module_clause_dependency_fact": RecordRule(
            "project_module_clause_dependency_fact",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "let_value",
                        "select_value",
                        "group_key",
                        "satisfying",
                        "grouped_order",
                        "window_partition",
                        "window_order",
                        "window_argument",
                        "window_default",
                    ),
                ),
                FieldRule("source_ordinal", INTEGER),
                FieldRule(
                    "source_occurrence",
                    union(
                        ref("group_by_item"),
                        ref("order_item"),
                        ref("name_expr"),
                        ref("call_expr"),
                    ),
                ),
                FieldRule(
                    "target_occurrences",
                    seq(union(ref("select_item"), ref("group_by_item"))),
                ),
                FieldRule("target_fields", seq(ref("project_row_field"))),
                FieldRule(
                    "aggregate_result_facts", seq(ref("project_aggregate_result_fact"))
                ),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
            ),
        ),
        "window_computation_input": RecordRule(
            "window_computation_input",
            (
                FieldRule("definition", union(ref("table_def"), ref("query_def"))),
                FieldRule("item", ref("select_item")),
                FieldRule("scope", ref("window_input_scope")),
                FieldRule("project_schema", union(ref("project_row_schema"), optional)),
            ),
        ),
        "window_dependency_occurrence": RecordRule(
            "window_dependency_occurrence",
            (
                FieldRule("global_ordinal", INTEGER),
                FieldRule("role_ordinal", INTEGER),
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "window_argument",
                        "window_default",
                        "window_partition",
                        "window_order",
                    ),
                ),
                FieldRule("target", ref("project_row_dependency_node")),
                FieldRule("location", ref("source_location")),
                FieldRule(
                    "target_result_role",
                    union(
                        enum(
                            "ordinary_row_value",
                            "group_key",
                            "aggregate_result",
                            "window_result",
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "computation", union(ref("window_computation_input"), optional)
                ),
                FieldRule("expression", union(ANCHOR, optional)),
                FieldRule("binding", union(ref("window_input_binding"), optional)),
            ),
        ),
        "project_ir_query_block_window_policy": RecordRule(
            "project_ir_query_block_window_policy",
            (
                FieldRule("output", ref("project_ir_query_block_scalar_output")),
                FieldRule(
                    "evidence",
                    union(
                        ref("project_concrete_window_computation"),
                        ref("project_module_window_output_fact"),
                    ),
                ),
                FieldRule("policy", ANCHOR),
            ),
        ),
        "project_ir_query_block_aggregate_evaluation_context": RecordRule(
            "project_ir_query_block_aggregate_evaluation_context",
            (
                FieldRule(
                    "operator",
                    union(
                        ref("project_ir_logical_operator_occurrence"),
                        ref("project_ir_query_block_operator_occurrence"),
                    ),
                ),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule("group_keys", seq(ANCHOR)),
                FieldRule("aggregate_outputs", seq(ANCHOR)),
            ),
        ),
        "project_ir_query_block_window_evidence": RecordRule(
            "project_ir_query_block_window_evidence",
            (
                FieldRule(
                    "selected",
                    seq(
                        union(
                            ref("project_concrete_window_computation"),
                            ref("project_module_window_output_fact"),
                        )
                    ),
                ),
                FieldRule(
                    "hidden",
                    seq(
                        union(
                            ref("project_concrete_window_computation"),
                            ref("project_no_join_hidden_window_computation"),
                        )
                    ),
                ),
            ),
        ),
        "project_ir_query_block_scalar_output": RecordRule(
            "project_ir_query_block_scalar_output",
            (
                FieldRule("occurrence", ref("project_ir_output_value_occurrence")),
                FieldRule("row_output", ref("project_ir_query_block_row_output")),
                FieldRule("field_position", INTEGER),
                FieldRule(
                    "semantic_source",
                    union(
                        ref("project_selected_window_result_binding"),
                        ref("project_module_window_output_fact"),
                        ref("project_completed_output_field"),
                    ),
                ),
                FieldRule(
                    "final_identity",
                    union(ref("project_module_row_field_identity"), optional),
                ),
            ),
        ),
        "project_ir_query_block_grain_origin": RecordRule(
            "project_ir_query_block_grain_origin",
            (
                FieldRule(
                    "kind",
                    enum(
                        "source_row_domain",
                        "grouped_result",
                        "global_aggregate",
                        "distinct_quotient",
                        "set_alternatives",
                        "set_quotient",
                        "set_subset",
                    ),
                ),
                FieldRule(
                    "context",
                    ref("project_ir_query_block_aggregate_evaluation_context"),
                ),
                FieldRule(
                    "factor",
                    union(ref("project_grouped_grain_factor_identity"), optional),
                ),
            ),
        ),
        "project_grouped_grain_factor_identity": RecordRule(
            "project_grouped_grain_factor_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule("operator", ref("project_ir_plan_node_ref")),
                FieldRule(
                    "kind",
                    enum(
                        "source_domain", "group_domain", "distinct_domain", "set_domain"
                    ),
                ),
            ),
        ),
        "project_grain_dependency_fact": RecordRule(
            "project_grain_dependency_fact",
            (
                FieldRule(
                    "determinants",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
                FieldRule(
                    "dependents",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
            ),
        ),
        "project_aggregate_result_fact": RecordRule(
            "project_aggregate_result_fact",
            (
                FieldRule("function", TEXT),
                FieldRule("output_name", TEXT),
                FieldRule("grouped", BOOLEAN),
                FieldRule("argument_count", INTEGER),
                FieldRule("location", ref("source_location")),
            ),
        ),
        "satisfying_clause": RecordRule(
            "satisfying_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "qualify_clause": RecordRule(
            "qualify_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "group_by_item": RecordRule(
            "group_by_item",
            (
                FieldRule("span", ref("span")),
                FieldRule("key", union(ref("name_expr"), ref("dotted_name_expr"))),
            ),
        ),
        "window_expr": RecordRule(
            "window_expr",
            (
                FieldRule("span", ref("span")),
                FieldRule("call", ref("call_expr")),
                FieldRule("spec", ref("window_spec")),
                FieldRule("identity", ref("window_function_identity")),
                FieldRule("use_kind", enum("inline", "named_direct", "named_extended")),
                FieldRule("base", union(ref("named_window_reference"), optional)),
                FieldRule(
                    "nth_direction",
                    union(ref("authored_window_nth_direction"), optional),
                ),
                FieldRule(
                    "null_treatment",
                    union(ref("authored_window_null_treatment"), optional),
                ),
            ),
        ),
        "satisfying_result_predicate_info": RecordRule(
            "satisfying_result_predicate_info",
            (
                FieldRule("clause", ref("satisfying_clause")),
                FieldRule("output_expressions", mapping(TEXT, ANCHOR)),
            ),
        ),
        "window_function_identity": RecordRule(
            "window_function_identity",
            (
                FieldRule("namespace", seq(TEXT)),
                FieldRule("name", TEXT),
                FieldRule("role", enum("window_function")),
            ),
        ),
        "window_input_binding": RecordRule(
            "window_input_binding",
            (
                FieldRule("name", TEXT),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "origin",
                    enum(
                        "upstream_field", "let_binding", "group_key", "aggregate_result"
                    ),
                ),
                FieldRule("target_name", TEXT),
                FieldRule("source_field_name", union(TEXT, optional)),
            ),
        ),
        "validated_window_specification": RecordRule(
            "validated_window_specification",
            (
                FieldRule("resolved", ref("resolved_window_specification")),
                FieldRule("function_identity", ref("window_function_identity")),
                FieldRule("function_policy", ref("window_function_frame_policy")),
                FieldRule("argument_expressions", seq(ANCHOR)),
                FieldRule(
                    "frame",
                    union(
                        ref("validated_frame"), ref("validated_frame_not_applicable")
                    ),
                ),
            ),
        ),
        "window_order_field_binding": RecordRule(
            "window_order_field_binding",
            (
                FieldRule("order_item", ref("order_item")),
                FieldRule("value_type", ref("value_type")),
                FieldRule("effective_direction", TEXT),
            ),
        ),
        "__project_qualify_predicate_analysis": RecordRule(
            "__project_qualify_predicate_analysis",
            (
                FieldRule("clause", ref("qualify_clause")),
                FieldRule(
                    "reason",
                    union(
                        enum(
                            "window_computation_required",
                            "hidden_window_non_concrete",
                            "reference_non_concrete",
                            "scalar_kernel_non_concrete",
                            "known_non_bool_predicate",
                        ),
                        optional,
                    ),
                ),
                FieldRule("kernel_value_type", union(ref("value_type"), optional)),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
            ),
        ),
        "window_spec": RecordRule(
            "window_spec",
            (
                FieldRule("span", ref("span")),
                FieldRule("partition_by", seq(ANCHOR)),
                FieldRule("order_by", seq(ref("order_item"))),
                FieldRule("frame", ref("authored_window_frame")),
            ),
        ),
        "window_input_scope": RecordRule(
            "window_input_scope",
            (
                FieldRule("kind", enum("row", "grouped_result")),
                FieldRule("bindings", seq(ref("window_input_binding"))),
                FieldRule("allows_qualified_fields", BOOLEAN),
                FieldRule("has_valid_group_aggregate", BOOLEAN),
            ),
        ),
        "project_row_dependency_node": RecordRule(
            "project_row_dependency_node",
            (
                FieldRule(
                    "kind",
                    enum(
                        "output_field",
                        "upstream_field",
                        "let_binding",
                        "relation_input",
                    ),
                ),
                FieldRule("name", TEXT),
                FieldRule("relation_name", union(TEXT, optional)),
                FieldRule("output_name", union(TEXT, optional)),
                FieldRule("binding_name", union(TEXT, optional)),
                FieldRule("source_name", union(TEXT, optional)),
                FieldRule("field_name", union(TEXT, optional)),
            ),
        ),
        "source_location": RecordRule(
            "source_location",
            (
                FieldRule("path", union(TEXT, optional)),
                FieldRule("line", INTEGER),
                FieldRule("column", INTEGER),
                FieldRule("end_line", union(INTEGER, optional)),
                FieldRule("end_column", union(INTEGER, optional)),
            ),
        ),
        "resolved_window_specification": RecordRule(
            "resolved_window_specification",
            (
                FieldRule("authored", ref("authored_window_specification")),
                FieldRule("partition_by", seq(ANCHOR)),
                FieldRule("order_by", seq(ref("order_item"))),
                FieldRule(
                    "partition_origin",
                    enum(
                        "locally_authored",
                        "inherited",
                        "effective_default",
                        "not_applicable",
                    ),
                ),
                FieldRule(
                    "ordering_origin",
                    enum(
                        "locally_authored",
                        "inherited",
                        "effective_default",
                        "not_applicable",
                    ),
                ),
                FieldRule("frame", ref("resolved_window_frame")),
            ),
        ),
        "window_function_frame_policy": RecordRule(
            "window_function_frame_policy",
            (
                FieldRule("identity", ref("window_function_identity")),
                FieldRule(
                    "kind",
                    enum("frame_sensitive", "frame_insensitive_explicit_forbidden"),
                ),
            ),
        ),
        "validated_frame_not_applicable": RecordRule(
            "validated_frame_not_applicable",
            (FieldRule("resolved", ref("resolved_window_frame")),),
        ),
        "project_ir_stage_field_anchor": RecordRule(
            "project_ir_stage_field_anchor",
            (
                FieldRule("producer", ref("project_ir_plan_node_occurrence")),
                FieldRule("field_position", INTEGER),
            ),
        ),
        "project_ir_plan_node_ref": RecordRule(
            "project_ir_plan_node_ref", (FieldRule("position", INTEGER),)
        ),
        "resolved_window_frame": RecordRule(
            "resolved_window_frame",
            (
                FieldRule("applicability", enum("applicable", "not_applicable")),
                FieldRule(
                    "origin",
                    enum(
                        "locally_authored",
                        "inherited",
                        "effective_default",
                        "not_applicable",
                    ),
                ),
                FieldRule("authored", ref("authored_window_frame")),
                FieldRule("unit", union(enum("rows", "range", "groups"), optional)),
                FieldRule("start", union(ref("window_frame_bound"), optional)),
                FieldRule("end", union(ref("window_frame_bound"), optional)),
                FieldRule(
                    "exclusion",
                    union(enum("no_others", "current_row", "group", "ties"), optional),
                ),
            ),
        ),
        "resolved_named_window_template": RecordRule(
            "resolved_named_window_template",
            (
                FieldRule("declaration", ref("named_window_declaration")),
                FieldRule("occurrence", ref("named_window_occurrence")),
                FieldRule("base", union(ref("named_window_base_resolution"), optional)),
                FieldRule(
                    "base_template",
                    union(ref("resolved_named_window_template"), optional),
                ),
                FieldRule("partition_by", seq(ANCHOR)),
                FieldRule("order_by", seq(ref("order_item"))),
                FieldRule("frame", union(ref("authored_window_frame"), optional)),
                FieldRule(
                    "partition_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
                FieldRule(
                    "ordering_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
                FieldRule(
                    "frame_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
            ),
        ),
        "authored_window_specification": RecordRule(
            "authored_window_specification",
            (
                FieldRule("span", ref("span")),
                FieldRule("partition_by", seq(ANCHOR)),
                FieldRule("order_by", seq(ref("order_item"))),
                FieldRule("frame", ref("authored_window_frame")),
            ),
        ),
        "resolved_named_window_use": RecordRule(
            "resolved_named_window_use",
            (
                FieldRule("composed", ref("composed_named_window_use")),
                FieldRule("function_identity", ref("window_function_identity")),
                FieldRule("function_policy", ref("window_function_frame_policy")),
                FieldRule("resolved", ref("resolved_window_specification")),
                FieldRule(
                    "partition_provenance", ref("named_window_component_provenance")
                ),
                FieldRule(
                    "ordering_provenance", ref("named_window_component_provenance")
                ),
                FieldRule("frame_provenance", ref("named_window_component_provenance")),
            ),
        ),
        "resolved_window_function_modifiers": RecordRule(
            "resolved_window_function_modifiers",
            (
                FieldRule("identity", ref("window_function_identity")),
                FieldRule(
                    "authored_null_treatment",
                    union(ref("authored_window_null_treatment"), optional),
                ),
                FieldRule(
                    "null_treatment",
                    union(enum("respect_nulls", "ignore_nulls"), optional),
                ),
                FieldRule(
                    "authored_nth_direction",
                    union(ref("authored_window_nth_direction"), optional),
                ),
                FieldRule(
                    "nth_direction", union(enum("from_first", "from_last"), optional)
                ),
            ),
        ),
        "validated_frame": RecordRule(
            "validated_frame",
            (
                FieldRule("resolved", ref("resolved_window_frame")),
                FieldRule(
                    "classification",
                    enum(
                        "structurally_invalid",
                        "guaranteed_nonempty",
                        "possibly_empty",
                        "always_empty",
                    ),
                ),
            ),
        ),
        "window_partition_field_binding": RecordRule(
            "window_partition_field_binding",
            (
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "frame_value_window_computation": RecordRule(
            "frame_value_window_computation",
            (
                FieldRule("expression", ref("window_expr")),
                FieldRule("function", enum("first_value", "last_value", "nth_value")),
                FieldRule(
                    "value_expression",
                    union(
                        ref("name_expr"), ref("dotted_name_expr"), ref("literal_expr")
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "position_fact", union(ref("nth_value_position_fact"), optional)
                ),
                FieldRule("modifiers", ref("resolved_window_function_modifiers")),
                FieldRule("signature_match", ref("signature_match")),
                FieldRule("result", ref("window_result_availability")),
            ),
        ),
        "frame_value_window_semantic_fact": RecordRule(
            "frame_value_window_semantic_fact",
            (
                FieldRule("semantic_fact", ref("window_expression_semantic_fact")),
                FieldRule("function", enum("first_value", "last_value", "nth_value")),
                FieldRule(
                    "value_expression",
                    union(
                        ref("name_expr"), ref("dotted_name_expr"), ref("literal_expr")
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "position_fact", union(ref("nth_value_position_fact"), optional)
                ),
                FieldRule("modifiers", ref("resolved_window_function_modifiers")),
                FieldRule("signature_match", ref("signature_match")),
            ),
        ),
        "navigation_offset_fact": RecordRule(
            "navigation_offset_fact",
            (
                FieldRule("expression", union(ref("literal_expr"), optional)),
                FieldRule("effective_value", INTEGER),
                FieldRule("span", ref("span")),
            ),
        ),
        "navigation_default_fact": RecordRule(
            "navigation_default_fact",
            (
                FieldRule(
                    "expression",
                    union(
                        ref("name_expr"),
                        ref("dotted_name_expr"),
                        ref("literal_expr"),
                        optional,
                    ),
                ),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("always_null", BOOLEAN),
                FieldRule("span", ref("span")),
            ),
        ),
        "navigation_window_computation": RecordRule(
            "navigation_window_computation",
            (
                FieldRule("expression", ref("window_expr")),
                FieldRule("direction", enum("lag", "lead")),
                FieldRule(
                    "value_expression",
                    union(
                        ref("name_expr"), ref("dotted_name_expr"), ref("literal_expr")
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("value_always_null", BOOLEAN),
                FieldRule("modifiers", ref("resolved_window_function_modifiers")),
                FieldRule("offset_fact", ref("navigation_offset_fact")),
                FieldRule("default_fact", ref("navigation_default_fact")),
                FieldRule("signature_match", ref("signature_match")),
                FieldRule("nullability_match", ref("nullability_evaluation_match")),
                FieldRule("result", ref("window_result_availability")),
            ),
        ),
        "navigation_window_semantic_fact": RecordRule(
            "navigation_window_semantic_fact",
            (
                FieldRule("semantic_fact", ref("window_expression_semantic_fact")),
                FieldRule("direction", enum("lag", "lead")),
                FieldRule(
                    "value_expression",
                    union(
                        ref("name_expr"), ref("dotted_name_expr"), ref("literal_expr")
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule("value_always_null", BOOLEAN),
                FieldRule("modifiers", ref("resolved_window_function_modifiers")),
                FieldRule("offset_fact", ref("navigation_offset_fact")),
                FieldRule("default_fact", ref("navigation_default_fact")),
                FieldRule("signature_match", ref("signature_match")),
                FieldRule("nullability_match", ref("nullability_evaluation_match")),
            ),
        ),
        "window_frame_bound": RecordRule(
            "window_frame_bound",
            (
                FieldRule(
                    "kind",
                    enum(
                        "unbounded_preceding",
                        "offset_preceding",
                        "current_row",
                        "offset_following",
                        "unbounded_following",
                    ),
                ),
                FieldRule("offset", union(ANCHOR, optional)),
            ),
        ),
        "authored_window_frame": RecordRule(
            "authored_window_frame",
            (
                FieldRule("kind", enum("omitted", "shorthand", "between")),
                FieldRule("unit", union(enum("rows", "range", "groups"), optional)),
                FieldRule("start", union(ref("window_frame_bound"), optional)),
                FieldRule("end", union(ref("window_frame_bound"), optional)),
                FieldRule(
                    "exclusion",
                    enum("omitted", "no_others", "current_row", "group", "ties"),
                ),
            ),
        ),
        "authored_window_null_treatment": RecordRule(
            "authored_window_null_treatment",
            (
                FieldRule("span", ref("span")),
                FieldRule("kind", enum("respect", "ignore")),
            ),
        ),
        "resolved_named_window_namespace": RecordRule(
            "resolved_named_window_namespace",
            (
                FieldRule("query_block", ref("query_block_occurrence")),
                FieldRule("definition", union(ref("table_def"), ref("query_def"))),
                FieldRule("templates", seq(ref("resolved_named_window_template"))),
                FieldRule("resolution_order", seq(ref("named_window_occurrence"))),
            ),
        ),
        "project_sql_target_lookup": RecordRule(
            "project_sql_target_lookup",
            (
                FieldRule("position", INTEGER),
                FieldRule("request", ref("project_sql_target_request")),
                FieldRule(
                    "kind",
                    enum(
                        "source_family",
                        "compiler_type_identity",
                        "compiler_expression_result",
                        "compiler_literal_result",
                        "compiler_aggregate_signature",
                        "compiler_window_signature",
                        "remaining_original_requirement",
                    ),
                ),
                FieldRule("key", ref("capability_key")),
                FieldRule("inputs", ref("canonical_capability_provider_inputs")),
                FieldRule(
                    "profile_occurrences",
                    seq(ref("effective_capability_profile_fact_occurrence")),
                ),
                FieldRule(
                    "provider_result",
                    union(ref("found"), ref("absent"), ref("unknown"), ref("conflict")),
                ),
                FieldRule(
                    "profile_result",
                    union(ref("found"), ref("absent"), ref("unknown"), ref("conflict")),
                ),
                FieldRule("profile_applicable", BOOLEAN),
            ),
        ),
        "project_sql_target_aspect": RecordRule(
            "project_sql_target_aspect",
            (
                FieldRule("position", INTEGER),
                FieldRule("ordinal", INTEGER),
                FieldRule("entry", ref("project_sql_demand_entry")),
                FieldRule("proposition", ref("project_sql_target_proposition")),
                FieldRule("lookup", union(ref("project_sql_target_lookup"), optional)),
                FieldRule(
                    "outcomes",
                    seq(
                        enum(
                            "satisfied_exact_subproposition",
                            "exact_negative",
                            "complete_provider_domain_absent",
                            "incomplete_lookup_unknown",
                            "conflicting_facts",
                            "unmapped_proposition",
                            "inapplicable_declared_evidence",
                            "explicit_input_unresolved",
                            "not_assessed",
                        )
                    ),
                ),
            ),
        ),
        "project_sql_target_demand": RecordRule(
            "project_sql_target_demand",
            (
                FieldRule("position", INTEGER),
                FieldRule("entry", ref("project_sql_demand_entry")),
                FieldRule("aspects", seq(ref("project_sql_target_aspect"))),
                FieldRule(
                    "posture",
                    enum(
                        "not_assessed",
                        "incomplete_requirement_assessment",
                        "complete_requirements_satisfied",
                    ),
                ),
            ),
        ),
        "project_sql_target_summary": RecordRule(
            "project_sql_target_summary",
            (
                FieldRule("demand_count", INTEGER),
                FieldRule("aspect_count", INTEGER),
                FieldRule("query_count", INTEGER),
                FieldRule(
                    "posture",
                    enum(
                        "not_assessed",
                        "incomplete_requirement_assessment",
                        "complete_requirements_satisfied",
                    ),
                ),
                FieldRule(
                    "categories",
                    mapping(
                        enum(
                            "satisfied_exact_subproposition",
                            "exact_negative",
                            "complete_provider_domain_absent",
                            "incomplete_lookup_unknown",
                            "conflicting_facts",
                            "unmapped_proposition",
                            "inapplicable_declared_evidence",
                            "explicit_input_unresolved",
                            "not_assessed",
                        ),
                        seq(ref("project_sql_target_aspect")),
                    ),
                ),
                FieldRule(
                    "pending_realizations", seq(ref("project_sql_target_aspect"))
                ),
                FieldRule(
                    "original_obligations", ref("project_sql_requirement_summary")
                ),
                FieldRule(
                    "input_issues",
                    seq(
                        enum(
                            "explicit_target_profile_missing",
                            "profile_target_family_or_release_mismatch",
                            "profile_composition_blocked",
                            "no_plan_extension_selector_mapping",
                            "catalog_database_family_or_release_mismatch",
                        )
                    ),
                ),
                FieldRule("catalog_residuals", seq(ref("target_catalog_residual"))),
            ),
        ),
        "target_catalog_residual": RecordRule(
            "target_catalog_residual",
            (
                FieldRule("position", INTEGER),
                FieldRule("context", ref("extension_signature_provider_context")),
                FieldRule("selector", ANCHOR),
                FieldRule("selection", ANCHOR),
                FieldRule(
                    "issues",
                    seq(
                        enum(
                            "explicit_target_profile_missing",
                            "profile_target_family_or_release_mismatch",
                            "profile_composition_blocked",
                            "no_plan_extension_selector_mapping",
                            "catalog_database_family_or_release_mismatch",
                        )
                    ),
                ),
            ),
        ),
        "project_sql_target_proposition": RecordRule(
            "project_sql_target_proposition",
            (
                FieldRule(
                    "kind",
                    enum(
                        "source_family",
                        "compiler_type_identity",
                        "compiler_expression_result",
                        "compiler_literal_result",
                        "compiler_aggregate_signature",
                        "compiler_window_signature",
                        "remaining_original_requirement",
                    ),
                ),
                FieldRule(
                    "witness",
                    union(
                        ref("project_sql_literal_demand"),
                        ref("project_sql_set_demand"),
                        ref("project_sql_result_demand"),
                        ref("project_sql_source_realization_demand"),
                        ref("project_sql_export_representation_demand"),
                        ref("project_sql_expression_demand"),
                        ref("project_sql_stage_value_demand"),
                        ref("project_sql_filter_demand"),
                        ref("project_sql_scope_demand"),
                        ref("project_sql_join_demand"),
                        ref("project_sql_aggregate_demand"),
                        ref("project_sql_window_demand"),
                    ),
                ),
                FieldRule("key", union(ref("capability_key"), optional)),
                FieldRule(
                    "gap",
                    union(
                        enum(
                            "source_locator_connection_and_realization",
                            "exact_export_representation_nullability_and_provenance",
                            "typed_operands_null_comparison_collation_effect_and_lowering",
                            "exact_stage_value_representation_and_availability",
                            "sql_true_only_retention_in_original_clause",
                            "original_predecessor_inputs_exports_and_evaluation_scope",
                            "original_join_kind_fields_scope_or_proof_requirement",
                            "original_group_empty_input_comparison_projection_or_risk",
                            "original_window_inputs_policy_projection_and_lowering",
                            "original_result_boundary_equivalence_order_limit_or_export",
                            "original_set_operation_properties_membership_or_positional_types",
                            "no_exact_type_catalog_schema",
                            "no_exact_scalar_schema_for_original_typed_expression",
                            "no_direct_field_signature_mapping_for_original_argument",
                            "no_exact_window_signature_schema",
                        ),
                        enum(
                            "exact_data_representation",
                            "original_nullability",
                            "exact_range_and_precision",
                            "typed_operator_and_operand_context",
                            "applicable_collation_and_overload",
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "found": RecordRule("found", (FieldRule("fact", ref("capability_fact")),)),
        "absent": RecordRule(
            "absent",
            (
                FieldRule("key", ref("capability_key")),
                FieldRule(
                    "reason",
                    enum(
                        "no_catalog_entry",
                        "not_evidenced",
                        "no_current_result_rule",
                        "unresolved_expression",
                        "null_literal_no_concrete_type",
                        "unknown_nullability",
                        "sql_three_valued_truth",
                        "dialect_lowering_gap",
                        "conflicting_evidence",
                        "extension_catalog_undeclared",
                        "extension_catalog_selection_ambiguous",
                        "extension_catalog_selection_conflict",
                        "extension_catalog_target_mismatch",
                        "extension_catalog_not_provider_eligible",
                        "extension_cataloged_unmodeled",
                        "extension_catalog_completeness_incomplete",
                        "extension_catalog_completeness_conflict",
                        "extension_catalog_completeness_unavailable",
                    ),
                ),
            ),
        ),
        "unknown": RecordRule(
            "unknown",
            (
                FieldRule(
                    "reason",
                    enum(
                        "no_catalog_entry",
                        "not_evidenced",
                        "no_current_result_rule",
                        "unresolved_expression",
                        "null_literal_no_concrete_type",
                        "unknown_nullability",
                        "sql_three_valued_truth",
                        "dialect_lowering_gap",
                        "conflicting_evidence",
                        "extension_catalog_undeclared",
                        "extension_catalog_selection_ambiguous",
                        "extension_catalog_selection_conflict",
                        "extension_catalog_target_mismatch",
                        "extension_catalog_not_provider_eligible",
                        "extension_cataloged_unmodeled",
                        "extension_catalog_completeness_incomplete",
                        "extension_catalog_completeness_conflict",
                        "extension_catalog_completeness_unavailable",
                    ),
                ),
            ),
        ),
        "conflict": RecordRule(
            "conflict",
            (
                FieldRule(
                    "reason",
                    enum(
                        "no_catalog_entry",
                        "not_evidenced",
                        "no_current_result_rule",
                        "unresolved_expression",
                        "null_literal_no_concrete_type",
                        "unknown_nullability",
                        "sql_three_valued_truth",
                        "dialect_lowering_gap",
                        "conflicting_evidence",
                        "extension_catalog_undeclared",
                        "extension_catalog_selection_ambiguous",
                        "extension_catalog_selection_conflict",
                        "extension_catalog_target_mismatch",
                        "extension_catalog_not_provider_eligible",
                        "extension_cataloged_unmodeled",
                        "extension_catalog_completeness_incomplete",
                        "extension_catalog_completeness_conflict",
                        "extension_catalog_completeness_unavailable",
                    ),
                ),
                FieldRule("evidence", seq(ref("capability_fact"))),
            ),
        ),
        "capability_key": RecordRule(
            "capability_key",
            (
                FieldRule(
                    "domain",
                    enum(
                        "logical_type",
                        "literal",
                        "parameter",
                        "scalar_function",
                        "unary_operator",
                        "binary_operator",
                        "comparison",
                        "null_test",
                        "clause",
                        "aggregate",
                        "window_function",
                        "expression_stage",
                        "conversion",
                        "dialect_lowering",
                        "extension_signature",
                    ),
                ),
                FieldRule("subject", union(TEXT, optional)),
                FieldRule("operation", union(TEXT, optional)),
                FieldRule("operands", seq(TEXT)),
                FieldRule("context", union(TEXT, optional)),
                FieldRule("dialect", union(TEXT, optional)),
                FieldRule("extension", union(TEXT, optional)),
            ),
        ),
        "capability_fact": RecordRule(
            "capability_fact",
            (
                FieldRule("key", ref("capability_key")),
                FieldRule("support", enum("supported", "explicitly_unsupported")),
                FieldRule("disposition", ref("capability_disposition")),
                FieldRule("evidence", seq(ref("capability_evidence"))),
            ),
        ),
        "capability_evidence": RecordRule(
            "capability_evidence",
            (
                FieldRule(
                    "source",
                    enum(
                        "grammar_ast",
                        "semantic_catalog",
                        "semantic_procedure",
                        "semantic_model",
                        "ir",
                        "backend",
                        "project",
                        "public",
                        "roadmap",
                        "test",
                        "spec",
                    ),
                ),
                FieldRule("source_path", TEXT),
                FieldRule("source_reference", TEXT),
                FieldRule(
                    "reason",
                    union(
                        enum(
                            "no_catalog_entry",
                            "not_evidenced",
                            "no_current_result_rule",
                            "unresolved_expression",
                            "null_literal_no_concrete_type",
                            "unknown_nullability",
                            "sql_three_valued_truth",
                            "dialect_lowering_gap",
                            "conflicting_evidence",
                            "extension_catalog_undeclared",
                            "extension_catalog_selection_ambiguous",
                            "extension_catalog_selection_conflict",
                            "extension_catalog_target_mismatch",
                            "extension_catalog_not_provider_eligible",
                            "extension_cataloged_unmodeled",
                            "extension_catalog_completeness_incomplete",
                            "extension_catalog_completeness_conflict",
                            "extension_catalog_completeness_unavailable",
                        ),
                        optional,
                    ),
                ),
                FieldRule("dialect", union(TEXT, optional)),
                FieldRule("backend", union(TEXT, optional)),
                FieldRule("extension", union(TEXT, optional)),
            ),
        ),
        "canonical_capability_provider_inputs": RecordRule(
            "canonical_capability_provider_inputs",
            (
                FieldRule("key", ref("capability_key")),
                FieldRule("facts", seq(ref("capability_fact"))),
                FieldRule("domain_complete", BOOLEAN),
                FieldRule(
                    "unknown_reason",
                    union(
                        enum(
                            "no_catalog_entry",
                            "not_evidenced",
                            "no_current_result_rule",
                            "unresolved_expression",
                            "null_literal_no_concrete_type",
                            "unknown_nullability",
                            "sql_three_valued_truth",
                            "dialect_lowering_gap",
                            "conflicting_evidence",
                            "extension_catalog_undeclared",
                            "extension_catalog_selection_ambiguous",
                            "extension_catalog_selection_conflict",
                            "extension_catalog_target_mismatch",
                            "extension_catalog_not_provider_eligible",
                            "extension_cataloged_unmodeled",
                            "extension_catalog_completeness_incomplete",
                            "extension_catalog_completeness_conflict",
                            "extension_catalog_completeness_unavailable",
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "capability_profile_target": RecordRule(
            "capability_profile_target",
            (
                FieldRule("kind", enum("database", "extension")),
                FieldRule("family", TEXT),
                FieldRule("release", TEXT),
                FieldRule("extension_identity", union(TEXT, optional)),
                FieldRule("extension_release", union(TEXT, optional)),
            ),
        ),
        "capability_profile_reference": RecordRule(
            "capability_profile_reference",
            (
                FieldRule("identity", ref("capability_profile_identity")),
                FieldRule("release", TEXT),
            ),
        ),
        "capability_profile_identity": RecordRule(
            "capability_profile_identity",
            (
                FieldRule("namespace", TEXT),
                FieldRule("name", TEXT),
            ),
        ),
        "static_capability_profile": RecordRule(
            "static_capability_profile",
            (
                FieldRule("schema_version", enum("pietto.capability-profile.v1")),
                FieldRule("profile", ref("capability_profile_reference")),
                FieldRule("target", ref("capability_profile_target")),
                FieldRule("kind", enum("base", "overlay")),
                FieldRule(
                    "base_occurrences", seq(ref("capability_profile_base_occurrence"))
                ),
                FieldRule(
                    "capability_occurrences",
                    seq(ref("capability_profile_fact_occurrence")),
                ),
            ),
        ),
        "capability_profile_base_occurrence": RecordRule(
            "capability_profile_base_occurrence",
            (
                FieldRule("owner", ref("capability_profile_reference")),
                FieldRule("position", INTEGER),
                FieldRule("base", ref("capability_profile_reference")),
            ),
        ),
        "capability_profile_fact_occurrence": RecordRule(
            "capability_profile_fact_occurrence",
            (
                FieldRule("owner", ref("capability_profile_reference")),
                FieldRule("position", INTEGER),
                FieldRule("fact", ref("capability_fact")),
            ),
        ),
        "capability_profile_composition_success": RecordRule(
            "capability_profile_composition_success",
            (
                FieldRule("base", ref("static_capability_profile")),
                FieldRule("overlays", seq(ref("static_capability_profile"))),
                FieldRule("dependency_order", seq(ref("static_capability_profile"))),
                FieldRule(
                    "effective_occurrences",
                    seq(ref("effective_capability_profile_fact_occurrence")),
                ),
            ),
        ),
        "capability_profile_composition_blocked": RecordRule(
            "capability_profile_composition_blocked",
            (
                FieldRule("base", ref("static_capability_profile")),
                FieldRule("overlays", seq(ref("static_capability_profile"))),
                FieldRule(
                    "blockers", seq(ref("capability_profile_composition_blocker"))
                ),
            ),
        ),
        "effective_capability_profile_fact_occurrence": RecordRule(
            "effective_capability_profile_fact_occurrence",
            (
                FieldRule("profile", ref("static_capability_profile")),
                FieldRule("occurrence", ref("capability_profile_fact_occurrence")),
            ),
        ),
        "project_sql_target_assessment": RecordRule(
            "project_sql_target_assessment",
            (
                FieldRule("request", ref("project_sql_target_request")),
                FieldRule("report", ref("project_sql_requirement_report")),
                FieldRule("demands", seq(ref("project_sql_target_demand"))),
                FieldRule("aspects", seq(ref("project_sql_target_aspect"))),
                FieldRule("lookups", seq(ref("project_sql_target_lookup"))),
                FieldRule("summary", ref("project_sql_target_summary")),
            ),
        ),
        "project_sql_target_request": RecordRule(
            "project_sql_target_request",
            (
                FieldRule("target", union(ref("capability_profile_target"), optional)),
                FieldRule("base", union(ref("static_capability_profile"), optional)),
                FieldRule("overlays", seq(ref("static_capability_profile"))),
                FieldRule(
                    "composition",
                    union(
                        union(
                            ref("capability_profile_composition_success"),
                            ref("capability_profile_composition_blocked"),
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "catalog_context",
                    union(ref("extension_signature_provider_context"), optional),
                ),
                FieldRule("catalog_residuals", seq(ref("target_catalog_residual"))),
                FieldRule(
                    "issues",
                    seq(
                        enum(
                            "explicit_target_profile_missing",
                            "profile_target_family_or_release_mismatch",
                            "profile_composition_blocked",
                            "no_plan_extension_selector_mapping",
                            "catalog_database_family_or_release_mismatch",
                        )
                    ),
                ),
            ),
        ),
        "capability_disposition": RecordRule(
            "capability_disposition",
            (
                FieldRule("kind", enum("none", "deferred", "out_of_scope")),
                FieldRule("owner", union(TEXT, optional)),
                FieldRule("reason", union(TEXT, optional)),
            ),
        ),
        "diagnostic": RecordRule(
            "diagnostic",
            (
                FieldRule("code", TEXT),
                FieldRule("severity", enum("error", "warning")),
                FieldRule("message", TEXT),
                FieldRule("location", ref("source_location")),
                FieldRule("suggestion", union(TEXT, optional)),
            ),
        ),
        "project_ir_join_input_correspondence": RecordRule(
            "project_ir_join_input_correspondence",
            (
                FieldRule("source", ref("project_ir_join_input_use_occurrence")),
                FieldRule("use", ref("project_ir_join_input_use_occurrence")),
                FieldRule(
                    "producer", union(ref("project_declaration_occurrence"), optional)
                ),
            ),
        ),
        "join_clause": RecordRule(
            "join_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule(
                    "kind",
                    enum("inner", "left", "cross", "right", "full", "semi", "anti"),
                ),
                FieldRule("target_relation_name", TEXT),
                FieldRule("target_binding_name", TEXT),
                FieldRule("source_binding_name", TEXT),
                FieldRule("traversal_steps", seq(ref("join_traversal_step"))),
                FieldRule("on_clause", union(ref("join_on_clause"), optional)),
            ),
        ),
        "join_on_clause": RecordRule(
            "join_on_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "project_join_condition": RecordRule(
            "project_join_condition",
            (
                FieldRule(
                    "use",
                    union(
                        ref("project_concrete_join_use"),
                        ref("project_non_concrete_join_use"),
                    ),
                ),
                FieldRule("mode", TEXT),
                FieldRule("expression", union(ANCHOR, optional)),
                FieldRule("references", seq(ref("project_join_condition_reference"))),
                FieldRule(
                    "base_guarantee",
                    union(
                        ref("project_directional_relationship_match_guarantee"),
                        optional,
                    ),
                ),
                FieldRule(
                    "refinement_guarantee",
                    union(ref("project_refined_match_bounds"), optional),
                ),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("state", enum("ready", "invalid", "unavailable")),
                FieldRule("null_rejections", seq(ref("project_join_null_rejection"))),
            ),
        ),
        "project_concrete_joined_namespace_expression": RecordRule(
            "project_concrete_joined_namespace_expression",
            (
                FieldRule("namespace", ref("project_joined_scalar_namespace")),
                FieldRule("expression", ANCHOR),
                FieldRule(
                    "resolutions",
                    seq(
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        )
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_joined_scalar_namespace": RecordRule(
            "project_joined_scalar_namespace",
            (
                FieldRule("occurrences", seq(ref("project_joined_let_occurrence"))),
                FieldRule("stage", enum("post_join_input", "let_binding", "post_let")),
                FieldRule("binding_ordinal", union(INTEGER, optional)),
                FieldRule("let_values", seq(ref("project_joined_let_value"))),
            ),
        ),
        "project_scalar_reference_resolution": RecordRule(
            "project_scalar_reference_resolution",
            (
                FieldRule("reference", ref("project_scalar_reference_occurrence")),
                FieldRule("candidates", seq(ref("project_scalar_environment_field"))),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule(
                    "target", union(ref("project_scalar_environment_field"), optional)
                ),
            ),
        ),
        "project_scalar_environment_field": RecordRule(
            "project_scalar_environment_field",
            (
                FieldRule(
                    "source_field",
                    union(
                        ref("project_ir_row_field"),
                        ref("project_ir_stage_row_field"),
                        ref("project_ir_joined_row_field"),
                    ),
                ),
                FieldRule("position", INTEGER),
                FieldRule("evidence", ref("project_row_field")),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_ir_composed_join": RecordRule(
            "project_ir_composed_join",
            (
                FieldRule(
                    "source",
                    union(
                        ref("project_current_binary_join"),
                        ref("project_ir_binary_join_occurrence"),
                    ),
                ),
                FieldRule("condition", ref("project_join_condition")),
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
            ),
        ),
        "project_join_condition_field": RecordRule(
            "project_join_condition_field",
            (
                FieldRule("position", INTEGER),
                FieldRule("binding", ref("project_relation_binding_occurrence")),
                FieldRule(
                    "input_field",
                    union(
                        ref("project_ir_output_field_occurrence"),
                        ref("project_current_input_field"),
                    ),
                ),
                FieldRule("nullability", enum("non_null", "nullable", "unknown")),
                FieldRule(
                    "null_extensions",
                    seq(
                        union(
                            ref("project_relationship_path_step"),
                            ref("project_join_use_identity"),
                        )
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_ir_joined_row_field": RecordRule(
            "project_ir_joined_row_field",
            (
                FieldRule("field_position", INTEGER),
                FieldRule("evidence", ref("project_row_field")),
                FieldRule(
                    "introduction_use", ref("project_ir_join_input_use_occurrence")
                ),
                FieldRule("nulling_joins", seq(ref("project_ir_plan_node_ref"))),
                FieldRule(
                    "effective_nullability", enum("non_null", "nullable", "unknown")
                ),
            ),
        ),
        "project_concrete_joined_row_filter": RecordRule(
            "project_concrete_joined_row_filter",
            (
                FieldRule("entry", ref("project_effective_output_terminal")),
                FieldRule("kind", enum("absent", "authored_where")),
                FieldRule("namespace", ref("project_joined_scalar_namespace")),
                FieldRule("where_clause", union(ref("where_clause"), optional)),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
            ),
        ),
        "project_ir_single_match_retention": RecordRule(
            "project_ir_single_match_retention",
            (
                FieldRule("position", INTEGER),
                FieldRule("assessment", ref("project_single_match_assessment")),
                FieldRule(
                    "owner_entry",
                    union(
                        union(
                            ref("project_ir_reused_effective_output"),
                            ref("project_ir_rebound_existing_output"),
                            ref("project_ir_completed_query_block_output"),
                            ref("project_ir_completed_set_operation_output"),
                            ANCHOR,
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "boundaries",
                    seq(
                        union(
                            ref("project_ir_composed_join"),
                            ref("project_ir_binary_join_occurrence"),
                        )
                    ),
                ),
                FieldRule("proofs", seq(ref("project_ir_single_match_proof_image"))),
            ),
        ),
        "project_single_match_request": RecordRule(
            "project_single_match_request",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "use",
                    union(
                        ref("project_concrete_join_use"),
                        ref("project_non_concrete_join_use"),
                    ),
                ),
                FieldRule("scope", enum("direct_binary", "path_hop", "whole_path")),
                FieldRule("unit", enum("actual_matched_bag_occurrence")),
                FieldRule("path", union(ref("project_relationship_path"), optional)),
                FieldRule(
                    "hop",
                    union(
                        ref("project_relationship_path_step"),
                        ref("project_traversal_step_use"),
                        optional,
                    ),
                ),
                FieldRule("condition", union(ref("project_join_condition"), optional)),
                FieldRule(
                    "input_pairs",
                    union(
                        seq(
                            seq(
                                union(
                                    ref("project_ir_join_input_use_occurrence"),
                                    ref("project_ir_join_input_use_occurrence"),
                                )
                            )
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "project_single_match_assessment": RecordRule(
            "project_single_match_assessment",
            (
                FieldRule("request", ref("project_single_match_request")),
                FieldRule("state", enum("proved", "legal_unproved", "invalid")),
                FieldRule("condition", union(ref("project_join_condition"), optional)),
                FieldRule(
                    "joins",
                    seq(
                        union(
                            ref("project_current_binary_join"),
                            ref("project_ir_binary_join_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "input_pairs",
                    seq(
                        seq(
                            union(
                                ref("project_ir_join_input_use_occurrence"),
                                ref("project_ir_join_input_use_occurrence"),
                            )
                        )
                    ),
                ),
                FieldRule("proofs", seq(ref("project_single_match_proof"))),
                FieldRule("problems", seq(TEXT)),
                FieldRule("diagnostic", union(ref("diagnostic"), optional)),
                FieldRule("downstream_enforcement_required", BOOLEAN),
            ),
        ),
        "project_relation_binding_occurrence": RecordRule(
            "project_relation_binding_occurrence",
            (
                FieldRule("identity", ref("project_relation_binding_identity")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("site", union(ref("from_clause"), ref("join_clause"))),
                FieldRule("name", TEXT),
                FieldRule("relation_name", TEXT),
                FieldRule("state", enum("concrete", "unknown", "blocked", "ambiguous")),
                FieldRule(
                    "target",
                    union(ref("project_resolved_module_relation_symbol"), optional),
                ),
            ),
        ),
        "project_ir_join_row_output": RecordRule(
            "project_ir_join_row_output",
            (FieldRule("occurrence", ref("project_ir_output_value_occurrence")),),
        ),
        "project_concrete_joined_qualify": RecordRule(
            "project_concrete_joined_qualify",
            (
                FieldRule("kind", enum("absent", "authored_qualify")),
                FieldRule("qualify_clause", union(ref("qualify_clause"), optional)),
                FieldRule(
                    "references", seq(ref("project_qualify_reference_resolution"))
                ),
                FieldRule(
                    "hidden_computations",
                    seq(ref("project_concrete_window_computation")),
                ),
                FieldRule("predicate_value_type", union(ref("value_type"), optional)),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
            ),
        ),
        "project_join_grain_factor_identity": RecordRule(
            "project_join_grain_factor_identity",
            (
                FieldRule(
                    "base",
                    union(
                        ref("project_source_grain_factor_identity"),
                        ref("project_grouped_grain_factor_identity"),
                        ref("project_distinct_grain_factor_identity"),
                        ref("project_set_grain_factor_identity"),
                    ),
                ),
                FieldRule("introduction_use", ref("project_ir_use_ref")),
                FieldRule("nulling_joins", seq(ref("project_ir_plan_node_ref"))),
                FieldRule(
                    "source_factor",
                    union(ref("project_join_grain_factor_identity"), optional),
                ),
                FieldRule(
                    "kind",
                    enum(
                        "source_domain", "group_domain", "distinct_domain", "set_domain"
                    ),
                ),
            ),
        ),
        "project_current_join_grain_witness": RecordRule(
            "project_current_join_grain_witness",
            (
                FieldRule("condition", ref("project_join_condition")),
                FieldRule("left", ref("project_ir_provided_intrinsic_grain")),
                FieldRule("right", ref("project_ir_provided_intrinsic_grain")),
            ),
        ),
        "project_joined_let_value": RecordRule(
            "project_joined_let_value",
            (
                FieldRule("occurrence", ref("project_joined_let_occurrence")),
                FieldRule("namespace", ref("project_joined_scalar_namespace")),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "resolutions",
                    seq(
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        )
                    ),
                ),
            ),
        ),
        "project_joined_satisfying_analysis": RecordRule(
            "project_joined_satisfying_analysis",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule(
                    "stage_outputs", seq(ref("project_joined_stage_output_occurrence"))
                ),
                FieldRule(
                    "aggregates", seq(ref("project_joined_aggregate_occurrence"))
                ),
                FieldRule("status", enum("concrete", "non_concrete")),
                FieldRule("predicate_value_type", ref("value_type")),
                FieldRule(
                    "references",
                    seq(
                        union(ref("project_joined_satisfying_output_reference"), ANCHOR)
                    ),
                ),
                FieldRule(
                    "retention_effects", seq(ref("project_joined_row_retention_effect"))
                ),
            ),
        ),
        "project_join_condition_reference": RecordRule(
            "project_join_condition_reference",
            (
                FieldRule("position", INTEGER),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule(
                    "binding_candidates",
                    seq(ref("project_relation_binding_occurrence")),
                ),
                FieldRule("candidates", seq(ref("project_join_condition_field"))),
                FieldRule(
                    "state",
                    enum("resolved", "unknown", "forward", "ambiguous", "unavailable"),
                ),
                FieldRule(
                    "target", union(ref("project_join_condition_field"), optional)
                ),
            ),
        ),
        "project_joined_let_reference_resolution": RecordRule(
            "project_joined_let_reference_resolution",
            (
                FieldRule("namespace", ref("project_joined_scalar_namespace")),
                FieldRule("reference", ref("project_scalar_reference_occurrence")),
                FieldRule("target", ref("project_joined_let_value")),
            ),
        ),
        "project_joined_satisfying_output_reference": RecordRule(
            "project_joined_satisfying_output_reference",
            (
                FieldRule("expression", ref("name_expr")),
                FieldRule("output", ref("project_joined_stage_output_occurrence")),
            ),
        ),
        "project_joined_let_occurrence": RecordRule(
            "project_joined_let_occurrence",
            (
                FieldRule("source_ordinal", INTEGER),
                FieldRule("binding", ref("let_binding")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "project_joined_group_key_occurrence": RecordRule(
            "project_joined_group_key_occurrence",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("source_ordinal", INTEGER),
                FieldRule("item", ref("group_by_item")),
                FieldRule(
                    "effective_expression",
                    union(ref("name_expr"), ref("dotted_name_expr")),
                ),
                FieldRule(
                    "resolutions",
                    seq(
                        union(
                            ref("project_joined_let_reference_resolution"),
                            ref("project_scalar_reference_resolution"),
                        )
                    ),
                ),
                FieldRule("field_semantics", ref("project_joined_row_field_semantics")),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_joined_aggregate_occurrence": RecordRule(
            "project_joined_aggregate_occurrence",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("call", ref("call_expr")),
                FieldRule("function_name", TEXT),
                FieldRule(
                    "argument_analysis",
                    union(
                        ref("project_concrete_joined_namespace_expression"), optional
                    ),
                ),
                FieldRule(
                    "field_dependencies",
                    seq(ref("project_joined_aggregate_field_dependency")),
                ),
                FieldRule("result_value_type", ref("value_type")),
            ),
        ),
        "project_joined_stage_output_occurrence": RecordRule(
            "project_joined_stage_output_occurrence",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("output_name", TEXT),
                FieldRule("role", enum("group_key", "aggregate_result")),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "group_key",
                    union(ref("project_joined_group_key_occurrence"), optional),
                ),
                FieldRule(
                    "aggregate",
                    union(ref("project_joined_aggregate_occurrence"), optional),
                ),
            ),
        ),
        "project_joined_group_protection": RecordRule(
            "project_joined_group_protection",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule(
                    "input_properties", ref("project_ir_output_relational_properties")
                ),
                FieldRule(
                    "introduction_use", ref("project_ir_join_input_use_occurrence")
                ),
                FieldRule(
                    "group_keys", seq(ref("project_joined_group_key_occurrence"))
                ),
                FieldRule("seed", ref("project_ir_output_value_class_set")),
                FieldRule("strict_keys", seq(ref("project_ir_output_candidate_key"))),
                FieldRule(
                    "determinations", seq(ref("project_ir_output_determination_result"))
                ),
                FieldRule(
                    "protected_factors",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
            ),
        ),
        "project_joined_aggregate_grain_linkage": RecordRule(
            "project_joined_aggregate_grain_linkage",
            (
                FieldRule("aggregate", ref("project_joined_aggregate_occurrence")),
                FieldRule(
                    "multifact_region",
                    union(ANCHOR, ref("project_current_multi_fact_region")),
                ),
                FieldRule(
                    "argument_factors",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
                FieldRule(
                    "group_protection_factors",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
                FieldRule("combined_seed", ref("project_grain_factor_set")),
                FieldRule("closure", ref("project_grain_factor_set")),
                FieldRule("contextual_grain", ref("project_fact_contextual_grain")),
                FieldRule("final_grain", ref("project_ir_provided_intrinsic_grain")),
                FieldRule("final_comparison", ref("project_fact_grain_comparison")),
                FieldRule("multiplicity_exposures", seq(union(ANCHOR, ANCHOR))),
                FieldRule(
                    "multiplicity_risks",
                    seq(enum("fanout_risk", "cross_fact_multiplication")),
                ),
                FieldRule("requirements", seq(enum("aggregate_algebra_required"))),
            ),
        ),
        "project_joined_aggregate_pair_linkage": RecordRule(
            "project_joined_aggregate_pair_linkage",
            (
                FieldRule("left", ref("project_joined_aggregate_grain_linkage")),
                FieldRule("right", ref("project_joined_aggregate_grain_linkage")),
                FieldRule("grain_comparison", ref("project_fact_grain_comparison")),
                FieldRule("common_grain", ref("project_common_grain_result")),
                FieldRule(
                    "chasm_candidates",
                    seq(ref("project_common_grain_candidate_evidence")),
                ),
                FieldRule(
                    "structural",
                    enum(
                        "exactly_aligned",
                        "structurally_alignable",
                        "reaggregation_required",
                        "ambiguous_path",
                        "insufficient_evidence",
                        "incompatible",
                    ),
                ),
                FieldRule(
                    "finer",
                    union(ref("project_joined_aggregate_grain_linkage"), optional),
                ),
                FieldRule(
                    "multiplicity_risks",
                    seq(enum("fanout_risk", "cross_fact_multiplication")),
                ),
                FieldRule("requirements", seq(enum("aggregate_algebra_required"))),
            ),
        ),
        "project_concrete_joined_aggregation": RecordRule(
            "project_concrete_joined_aggregation",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("mode", enum("absent", "grouped", "global")),
                FieldRule(
                    "group_keys", seq(ref("project_joined_group_key_occurrence"))
                ),
                FieldRule(
                    "aggregates", seq(ref("project_joined_aggregate_occurrence"))
                ),
                FieldRule(
                    "stage_outputs", seq(ref("project_joined_stage_output_occurrence"))
                ),
                FieldRule(
                    "group_protections", seq(ref("project_joined_group_protection"))
                ),
                FieldRule(
                    "grain_linkages", seq(ref("project_joined_aggregate_grain_linkage"))
                ),
                FieldRule(
                    "pair_linkages", seq(ref("project_joined_aggregate_pair_linkage"))
                ),
                FieldRule(
                    "satisfying",
                    union(ref("project_joined_satisfying_analysis"), optional),
                ),
            ),
        ),
        "project_current_binary_join": RecordRule(
            "project_current_binary_join",
            (
                FieldRule("condition", ref("project_join_condition")),
                FieldRule(
                    "use",
                    union(
                        ref("project_concrete_join_use"),
                        ref("project_non_concrete_join_use"),
                    ),
                ),
                FieldRule(
                    "kind",
                    enum("inner", "left", "cross", "right", "full", "semi", "anti"),
                ),
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
            ),
        ),
        "project_no_join_hidden_window_computation": RecordRule(
            "project_no_join_hidden_window_computation",
            (
                FieldRule("expression", ref("window_expr")),
                FieldRule(
                    "analysis",
                    union(ref("window_computation_analysis"), ANCHOR, optional),
                ),
                FieldRule(
                    "input_context",
                    union(ref("project_no_join_window_input"), optional),
                ),
                FieldRule(
                    "input_uses",
                    union(
                        seq(ref("project_no_join_hidden_window_input_use")), optional
                    ),
                ),
            ),
        ),
        "project_no_join_window_input": RecordRule(
            "project_no_join_window_input",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("scope", ref("window_input_scope")),
                FieldRule("input_schema", ref("project_row_schema")),
                FieldRule("base_schema", ref("project_row_schema")),
            ),
        ),
        "project_no_join_hidden_window_input_use": RecordRule(
            "project_no_join_hidden_window_input_use",
            (
                FieldRule("context", ref("project_no_join_window_input")),
                FieldRule("hidden", ref("window_expr")),
                FieldRule("expression", ANCHOR),
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "window_argument",
                        "window_default",
                        "window_partition",
                        "window_order",
                    ),
                ),
                FieldRule("global_ordinal", INTEGER),
                FieldRule("role_ordinal", INTEGER),
                FieldRule("binding", union(ref("window_input_binding"), optional)),
                FieldRule(
                    "target",
                    union(
                        ref("project_row_field"),
                        ref("let_binding"),
                        ref("select_item"),
                        optional,
                    ),
                ),
            ),
        ),
        "project_ir_provided_evaluation_policy": RecordRule(
            "project_ir_provided_evaluation_policy",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_scalar_field_output"),
                        ref("project_ir_stage_scalar_field_output"),
                    ),
                ),
                FieldRule("evidence", ref("project_module_window_output_fact")),
                FieldRule("policy", ref("window_function_frame_policy")),
            ),
        ),
        "named_window_declaration": RecordRule(
            "named_window_declaration",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("base", union(ref("named_window_reference"), optional)),
                FieldRule("spec", union(ref("window_spec"), optional)),
            ),
        ),
        "named_window_reference": RecordRule(
            "named_window_reference",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "named_window_base_resolution": RecordRule(
            "named_window_base_resolution",
            (
                FieldRule(
                    "owner",
                    union(ref("named_window_occurrence"), ref("window_use_occurrence")),
                ),
                FieldRule("reference", ref("named_window_reference")),
                FieldRule("target_declaration", ref("named_window_declaration")),
                FieldRule("target", ref("named_window_occurrence")),
            ),
        ),
        "composed_named_window_use": RecordRule(
            "composed_named_window_use",
            (
                FieldRule("expression", ref("window_expr")),
                FieldRule("occurrence", ref("window_use_occurrence")),
                FieldRule("namespace", ref("resolved_named_window_namespace")),
                FieldRule("base", ref("named_window_base_resolution")),
                FieldRule("target_template", ref("resolved_named_window_template")),
                FieldRule("partition_by", seq(ANCHOR)),
                FieldRule("order_by", seq(ref("order_item"))),
                FieldRule("frame", union(ref("authored_window_frame"), optional)),
                FieldRule(
                    "partition_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
                FieldRule(
                    "ordering_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
                FieldRule(
                    "frame_provenance",
                    union(ref("named_window_component_provenance"), optional),
                ),
            ),
        ),
        "named_window_component_provenance": RecordRule(
            "named_window_component_provenance",
            (
                FieldRule("component", enum("partition", "order", "frame")),
                FieldRule(
                    "origin",
                    enum(
                        "locally_authored",
                        "inherited",
                        "effective_default",
                        "not_applicable",
                    ),
                ),
                FieldRule(
                    "source",
                    union(
                        ref("named_window_occurrence"),
                        ref("window_use_occurrence"),
                        optional,
                    ),
                ),
            ),
        ),
        "query_block_occurrence": RecordRule(
            "query_block_occurrence",
            (
                FieldRule("relation_name", TEXT),
                FieldRule("kind", enum("table", "query")),
                FieldRule("span", ref("span")),
            ),
        ),
        "window_expression_semantic_fact": RecordRule(
            "window_expression_semantic_fact",
            (
                FieldRule("occurrence", ref("window_occurrence_identity")),
                FieldRule("expression", ref("window_expr")),
                FieldRule("identity", ref("window_function_identity")),
                FieldRule("result", ref("window_result_availability")),
                FieldRule("stage", enum("WINDOW")),
            ),
        ),
        "signature_match": RecordRule(
            "signature_match",
            (
                FieldRule("bindings", seq(ref("type_variable_binding"))),
                FieldRule("result_type", ref("logical_type_identity")),
                FieldRule("constraint_evidence", seq(ANCHOR)),
                FieldRule("omitted_positions", seq(INTEGER)),
            ),
        ),
        "nullability_evaluation_match": RecordRule(
            "nullability_evaluation_match",
            (
                FieldRule("value", enum("non_null", "nullable", "unknown")),
                FieldRule("evidence", ref("nullability_evaluation_evidence")),
            ),
        ),
        "project_ir_stage_scalar_field_output": RecordRule(
            "project_ir_stage_scalar_field_output",
            (
                FieldRule("occurrence", ref("project_ir_output_value_occurrence")),
                FieldRule("field", ref("project_ir_stage_row_field")),
            ),
        ),
        "named_window_occurrence": RecordRule(
            "named_window_occurrence",
            (
                FieldRule("query_block", ref("query_block_occurrence")),
                FieldRule("declaration_position", INTEGER),
                FieldRule("span", ref("span")),
            ),
        ),
        "project_ir_join_input_use_occurrence": RecordRule(
            "project_ir_join_input_use_occurrence",
            (
                FieldRule("output", ref("project_ir_output_value_occurrence")),
                FieldRule("slot", ref("project_ir_input_slot_occurrence")),
            ),
        ),
        "project_non_concrete_join_use": RecordRule(
            "project_non_concrete_join_use",
            (
                FieldRule("identity", ref("project_join_use_identity")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("join_clause")),
                FieldRule(
                    "source_binding",
                    union(ref("project_relation_binding_occurrence"), optional),
                ),
                FieldRule("target_binding", ref("project_relation_binding_occurrence")),
                FieldRule("state", enum("concrete", "unknown", "blocked", "ambiguous")),
                FieldRule("step_uses", seq(ref("project_traversal_step_use"))),
                FieldRule("path", union(ref("project_relationship_path"), optional)),
            ),
        ),
        "project_scalar_reference_occurrence": RecordRule(
            "project_scalar_reference_occurrence",
            (
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule("query_block", ref("project_concrete_query_block")),
            ),
        ),
        "project_effective_output_terminal": RecordRule(
            "project_effective_output_terminal",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule(
                    "reason",
                    enum(
                        "dependency_cycle",
                        "upstream_dependency_cycle",
                        "joined_tail_pending",
                        "upstream_effective_output_pending",
                        "joined_completion_non_concrete",
                        "historical_non_concrete",
                        "effective_upstream_join_unsupported",
                    ),
                ),
            ),
        ),
        "project_relation_binding_identity": RecordRule(
            "project_relation_binding_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule("binding_position", INTEGER),
            ),
        ),
        "project_ir_use_ref": RecordRule(
            "project_ir_use_ref", (FieldRule("position", INTEGER),)
        ),
        "project_joined_row_field_semantics": RecordRule(
            "project_joined_row_field_semantics",
            (
                FieldRule("scalar_field", ref("project_scalar_environment_field")),
                FieldRule("joined_field", ref("project_ir_joined_row_field")),
                FieldRule("property_field", ref("project_ir_output_field_occurrence")),
                FieldRule("input_field", ref("project_ir_output_field_occurrence")),
                FieldRule("canonical_field", ref("project_module_row_field_identity")),
                FieldRule(
                    "current_input", union(ref("project_current_input_field"), optional)
                ),
                FieldRule(
                    "source_origin",
                    union(ref("project_module_source_field_origin"), optional),
                ),
                FieldRule("output_attribution", union(ANCHOR, optional)),
                FieldRule(
                    "source_roots",
                    union(seq(ref("project_module_row_field_identity")), optional),
                ),
            ),
        ),
        "project_current_multi_fact_region": RecordRule(
            "project_current_multi_fact_region",
            (
                FieldRule(
                    "actual_candidates", seq(ref("project_actual_grain_candidate"))
                ),
            ),
        ),
        "project_grain_factor_set": RecordRule(
            "project_grain_factor_set",
            (
                FieldRule("universe", ref("project_grain_factor_universe")),
                FieldRule(
                    "factors",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
            ),
        ),
        "project_fact_contextual_grain": RecordRule(
            "project_fact_contextual_grain",
            (
                FieldRule("state", enum("factorized", "global", "unknown", "conflict")),
                FieldRule(
                    "factors",
                    seq(
                        union(
                            ref("project_source_grain_factor_identity"),
                            ref("project_grouped_grain_factor_identity"),
                            ref("project_distinct_grain_factor_identity"),
                            ref("project_set_grain_factor_identity"),
                            ref("project_join_grain_factor_identity"),
                        )
                    ),
                ),
                FieldRule("evidence", ANCHOR),
            ),
        ),
        "project_fact_grain_comparison": RecordRule(
            "project_fact_grain_comparison",
            (
                FieldRule("left", ref("project_fact_contextual_grain")),
                FieldRule("right", ref("project_fact_contextual_grain")),
                FieldRule("left_to_right", ref("project_fact_grain_determination")),
                FieldRule("right_to_left", ref("project_fact_grain_determination")),
                FieldRule(
                    "status",
                    enum(
                        "equal",
                        "left_finer",
                        "right_finer",
                        "incomparable",
                        "unknown",
                        "conflict",
                    ),
                ),
            ),
        ),
        "project_common_grain_result": RecordRule(
            "project_common_grain_result",
            (
                FieldRule(
                    "status", enum("unique", "ambiguous", "none", "unknown", "conflict")
                ),
                FieldRule(
                    "actual_candidates", seq(ref("project_actual_grain_candidate"))
                ),
                FieldRule(
                    "common_candidates",
                    seq(ref("project_common_grain_candidate_evidence")),
                ),
                FieldRule(
                    "candidates", seq(ref("project_common_grain_candidate_evidence"))
                ),
            ),
        ),
        "project_join_null_rejection": RecordRule(
            "project_join_null_rejection",
            (
                FieldRule("condition", ref("project_join_condition")),
                FieldRule("conjunct_position", INTEGER),
                FieldRule("reference", ref("project_join_condition_reference")),
                FieldRule("reason", TEXT),
                FieldRule("field", ref("project_join_condition_field")),
            ),
        ),
        "project_joined_aggregate_field_dependency": RecordRule(
            "project_joined_aggregate_field_dependency",
            (
                FieldRule("input_filter", ref("project_concrete_joined_row_filter")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("item", ref("select_item")),
                FieldRule("reference", ref("project_scalar_reference_occurrence")),
                FieldRule("resolution", ref("project_scalar_reference_resolution")),
                FieldRule("let_path", seq(ref("project_joined_let_value"))),
                FieldRule("field_semantics", ref("project_joined_row_field_semantics")),
            ),
        ),
        "window_computation_analysis": RecordRule(
            "window_computation_analysis",
            (
                FieldRule("expression", ref("window_expr")),
                FieldRule("result", ref("window_result_availability")),
                FieldRule("modifiers", ref("resolved_window_function_modifiers")),
                FieldRule(
                    "ranking_advance_policy",
                    union(
                        enum(
                            "per_row",
                            "preceding_row_count_plus_one",
                            "preceding_distinct_peer_group_count_plus_one",
                        ),
                        optional,
                    ),
                ),
                FieldRule(
                    "distribution_policy",
                    union(
                        enum(
                            "percent_rank",
                            "cumulative_distribution",
                            "balanced_buckets",
                        ),
                        optional,
                    ),
                ),
                FieldRule("bucket_count", union(INTEGER, optional)),
                FieldRule(
                    "partition_bindings", seq(ref("window_partition_field_binding"))
                ),
                FieldRule("order_bindings", seq(ref("window_order_field_binding"))),
                FieldRule(
                    "validated_specification", ref("validated_window_specification")
                ),
                FieldRule(
                    "navigation", union(ref("navigation_window_computation"), optional)
                ),
                FieldRule(
                    "frame_value",
                    union(ref("frame_value_window_computation"), optional),
                ),
                FieldRule(
                    "resolved_named_use",
                    union(ref("resolved_named_window_use"), optional),
                ),
            ),
        ),
        "window_use_occurrence": RecordRule(
            "window_use_occurrence",
            (
                FieldRule("query_block", ref("query_block_occurrence")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("kind", enum("inline", "named_direct", "named_extended")),
                FieldRule("span", ref("span")),
            ),
        ),
        "window_occurrence_identity": RecordRule(
            "window_occurrence_identity",
            (
                FieldRule("relation_name", TEXT),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("span", ref("span")),
            ),
        ),
        "window_result_availability": RecordRule(
            "window_result_availability",
            (
                FieldRule("kind", enum("concrete", "unknown", "deferred", "blocked")),
                FieldRule("value_type", union(ref("value_type"), optional)),
                FieldRule("reason", union(TEXT, optional)),
            ),
        ),
        "logical_type_identity": RecordRule(
            "logical_type_identity",
            (
                FieldRule("name", TEXT),
                FieldRule(
                    "kind", enum("builtin", "type_alias", "enum", "shape", "unknown")
                ),
            ),
        ),
        "nullability_evaluation_evidence": RecordRule(
            "nullability_evaluation_evidence",
            (
                FieldRule(
                    "kind",
                    enum(
                        "non_null",
                        "nullable",
                        "same_as_arg",
                        "any_nullable",
                        "always_nullable",
                        "nullable_if_default_omitted",
                        "any_of",
                    ),
                ),
                FieldRule("value", enum("non_null", "nullable", "unknown")),
                FieldRule("arguments", seq(ref("nullability_argument_evidence"))),
                FieldRule(
                    "default", union(ref("nullability_default_evidence"), optional)
                ),
                FieldRule("children", seq(ref("nullability_evaluation_evidence"))),
            ),
        ),
        "project_ir_stage_row_field": RecordRule(
            "project_ir_stage_row_field",
            (
                FieldRule("field_position", INTEGER),
                FieldRule("evidence", ref("project_row_field")),
            ),
        ),
        "type_variable_binding": RecordRule(
            "type_variable_binding",
            (
                FieldRule("variable_name", TEXT),
                FieldRule("logical_type", ref("logical_type_identity")),
                FieldRule("first_parameter_position", INTEGER),
            ),
        ),
        "project_join_use_identity": RecordRule(
            "project_join_use_identity",
            (
                FieldRule("owner", ref("project_declaration_occurrence_identity")),
                FieldRule("join_position", INTEGER),
            ),
        ),
        "project_concrete_query_block": RecordRule(
            "project_concrete_query_block",
            (
                FieldRule(
                    "compilation_mode",
                    enum("legacy_flat", "explicit_modules", "package_root"),
                ),
                FieldRule("owner_bridge", ref("project_query_block_owner_bridge")),
            ),
        ),
        "project_grain_factor_universe": RecordRule(
            "project_grain_factor_universe",
            (FieldRule("factors", seq(ref("project_grain_domain_factor"))),),
        ),
        "project_fact_grain_determination": RecordRule(
            "project_fact_grain_determination",
            (
                FieldRule("index", ref("project_grain_dependency_index")),
                FieldRule("seed", ref("project_grain_factor_set")),
                FieldRule("requested", ref("project_grain_factor_set")),
                FieldRule("closure", ref("project_grain_factor_set")),
                FieldRule("status", enum("proven", "not_proven")),
            ),
        ),
        "project_actual_grain_candidate": RecordRule(
            "project_actual_grain_candidate",
            (
                FieldRule("factors", ref("project_grain_factor_set")),
                FieldRule("authorities", seq(ref("project_actual_grain_authority"))),
            ),
        ),
        "project_current_join_properties": RecordRule(
            "project_current_join_properties",
            (
                FieldRule("join", ref("project_current_binary_join")),
                FieldRule("relational", ref("project_ir_output_relational_properties")),
                FieldRule(
                    "null_extension",
                    union(
                        ref("project_ir_provided_null_extension"),
                        ref("project_ir_join_unavailable_property"),
                    ),
                ),
                FieldRule("ordering", ref("project_ir_join_unavailable_property")),
            ),
        ),
        "project_common_grain_candidate_evidence": RecordRule(
            "project_common_grain_candidate_evidence",
            (
                FieldRule("candidate", ref("project_actual_grain_candidate")),
                FieldRule("left_to_candidate", ref("project_fact_grain_determination")),
                FieldRule(
                    "right_to_candidate", ref("project_fact_grain_determination")
                ),
            ),
        ),
        "nullability_default_evidence": RecordRule(
            "nullability_default_evidence",
            (
                FieldRule("parameter_position", INTEGER),
                FieldRule("omitted", BOOLEAN),
                FieldRule("contribution", enum("non_null", "nullable", "unknown")),
            ),
        ),
        "nullability_argument_evidence": RecordRule(
            "nullability_argument_evidence",
            (
                FieldRule("parameter_position", INTEGER),
                FieldRule("supplied", BOOLEAN),
                FieldRule(
                    "value", union(enum("non_null", "nullable", "unknown"), optional)
                ),
                FieldRule("contribution", enum("non_null", "nullable", "unknown")),
            ),
        ),
        "project_query_block_owner_bridge": RecordRule(
            "project_query_block_owner_bridge",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("query_block", ref("query_block_occurrence")),
            ),
        ),
        "project_grain_dependency_index": RecordRule(
            "project_grain_dependency_index",
            (
                FieldRule("universe", ref("project_grain_factor_universe")),
                FieldRule("facts", seq(ref("project_grain_dependency_fact"))),
            ),
        ),
        "project_ir_provided_null_extension": RecordRule(
            "project_ir_provided_null_extension",
            (
                FieldRule("output", ref("project_ir_join_row_output")),
                FieldRule("fields", seq(ref("project_ir_joined_row_field"))),
            ),
        ),
        "project_ir_join_unavailable_property": RecordRule(
            "project_ir_join_unavailable_property",
            (
                FieldRule("output", ref("project_ir_join_row_output")),
                FieldRule(
                    "property_slot",
                    enum(
                        "output_shape",
                        "cardinality_bounds",
                        "multiplicity",
                        "relation_result_ordering",
                        "local_grain_evidence",
                        "fact_domains",
                        "free_bindings",
                        "null_extension",
                        "policy_evaluation",
                    ),
                ),
                FieldRule("availability", enum("unknown", "not_applicable")),
            ),
        ),
        "project_actual_grain_authority": RecordRule(
            "project_actual_grain_authority",
            (
                FieldRule(
                    "kind",
                    enum(
                        "fact_locality",
                        "join_left_input",
                        "join_right_input",
                        "join_source_slice",
                        "join_output",
                    ),
                ),
                FieldRule("evidence", seq(ANCHOR)),
            ),
        ),
        "project_ir_join_match_field_pair": RecordRule(
            "project_ir_join_match_field_pair",
            (
                FieldRule(
                    "correspondence",
                    ref("project_relationship_equality_correspondence"),
                ),
                FieldRule("left", ref("project_ir_joined_row_field")),
                FieldRule("right", ref("project_ir_joined_row_field")),
            ),
        ),
        "project_directional_relationship_match_guarantee": RecordRule(
            "project_directional_relationship_match_guarantee",
            (
                FieldRule("direction", ref("project_relationship_direction_identity")),
                FieldRule(
                    "source_output", ref("project_ir_output_relational_properties")
                ),
                FieldRule(
                    "target_output", ref("project_ir_output_relational_properties")
                ),
                FieldRule(
                    "source_matched_classes", seq(ref("project_ir_output_value_class"))
                ),
                FieldRule(
                    "target_matched_classes", seq(ref("project_ir_output_value_class"))
                ),
                FieldRule("minimum", enum("zero_allowed", "at_least_one")),
                FieldRule(
                    "minimum_evidence",
                    union(
                        ANCHOR,
                        enum(
                            "coverage_not_constructible",
                            "source_nullability_not_proven",
                            "target_key_not_proven",
                            "condition_not_proof_capable",
                        ),
                    ),
                ),
                FieldRule(
                    "maximum", enum("at_most_zero", "at_most_one", "unbounded_by_one")
                ),
                FieldRule(
                    "maximum_evidence",
                    union(
                        ref("project_at_most_one_evidence"),
                        enum(
                            "coverage_not_constructible",
                            "source_nullability_not_proven",
                            "target_key_not_proven",
                            "condition_not_proof_capable",
                        ),
                    ),
                ),
                FieldRule(
                    "coverage",
                    union(ANCHOR, ref("project_absent_referential_coverage")),
                ),
            ),
        ),
        "project_ir_single_match_proof_image": RecordRule(
            "project_ir_single_match_proof_image",
            (
                FieldRule("source", ref("project_single_match_proof")),
                FieldRule(
                    "boundaries",
                    seq(
                        union(
                            ref("project_ir_composed_join"),
                            ref("project_ir_binary_join_occurrence"),
                        )
                    ),
                ),
                FieldRule(
                    "producers",
                    seq(
                        union(
                            ref("project_ir_reused_effective_output"),
                            ref("project_ir_rebound_existing_output"),
                            ref("project_ir_completed_query_block_output"),
                            ref("project_ir_completed_set_operation_output"),
                            ANCHOR,
                        )
                    ),
                ),
                FieldRule("premise_nodes", seq(ref("project_ir_plan_node_occurrence"))),
                FieldRule("children", seq(ref("project_ir_single_match_proof_image"))),
            ),
        ),
        "relationship_metadata": RecordRule(
            "relationship_metadata",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule(
                    "endpoints",
                    seq(
                        union(
                            ref("relationship_endpoint"), ref("relationship_endpoint")
                        )
                    ),
                ),
                FieldRule(
                    "base_match", union(ref("relationship_match_clause"), optional)
                ),
            ),
        ),
        "project_ir_binary_join_occurrence": RecordRule(
            "project_ir_binary_join_occurrence",
            (
                FieldRule("identity", ref("project_ir_binary_join_identity")),
                FieldRule("use", ref("project_concrete_join_use")),
                FieldRule("path_step", ref("project_relationship_path_step")),
                FieldRule(
                    "guarantee", ref("project_directional_relationship_match_guarantee")
                ),
                FieldRule("condition", ref("project_concrete_relationship_condition")),
                FieldRule("kind", enum("inner", "left")),
                FieldRule("matches", seq(ref("project_ir_join_match_field_pair"))),
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
            ),
        ),
        "project_concrete_join_use": RecordRule(
            "project_concrete_join_use",
            (
                FieldRule("identity", ref("project_join_use_identity")),
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("clause", ref("join_clause")),
                FieldRule(
                    "kind",
                    enum("inner", "left", "cross", "right", "full", "semi", "anti"),
                ),
                FieldRule("source_binding", ref("project_relation_binding_occurrence")),
                FieldRule("target_binding", ref("project_relation_binding_occurrence")),
                FieldRule(
                    "target_relation", ref("project_resolved_module_relation_symbol")
                ),
                FieldRule("path", ref("project_relationship_path")),
                FieldRule("step_uses", seq(ref("project_traversal_step_use"))),
            ),
        ),
        "project_relationship_path": RecordRule(
            "project_relationship_path",
            (FieldRule("steps", seq(ref("project_relationship_path_step"))),),
        ),
        "project_relationship_path_step": RecordRule(
            "project_relationship_path_step",
            (
                FieldRule("position", INTEGER),
                FieldRule(
                    "guarantee", ref("project_directional_relationship_match_guarantee")
                ),
            ),
        ),
        "join_traversal_step": RecordRule(
            "join_traversal_step",
            (
                FieldRule("span", ref("span")),
                FieldRule("relationship_name", TEXT),
                FieldRule("source_endpoint_role", TEXT),
                FieldRule("target_endpoint_role", TEXT),
            ),
        ),
        "project_ir_join_grain_witness": RecordRule(
            "project_ir_join_grain_witness",
            (
                FieldRule("join", ref("project_ir_binary_join_identity")),
                FieldRule("left", ref("project_ir_provided_intrinsic_grain")),
                FieldRule("right", ref("project_ir_provided_intrinsic_grain")),
            ),
        ),
        "project_single_match_proof": RecordRule(
            "project_single_match_proof",
            (
                FieldRule(
                    "kind",
                    enum(
                        "relationship",
                        "refinement",
                        "whole_path",
                        "right_limit",
                        "right_global",
                    ),
                ),
                FieldRule("roots", seq(ANCHOR)),
            ),
        ),
        "project_relationship_equality_correspondence": RecordRule(
            "project_relationship_equality_correspondence",
            (
                FieldRule(
                    "identity", ref("project_relationship_correspondence_identity")
                ),
                FieldRule("comparison", ref("comparison_expr")),
                FieldRule(
                    "authored_left",
                    ref("project_relationship_endpoint_field_reference_occurrence"),
                ),
                FieldRule(
                    "authored_right",
                    ref("project_relationship_endpoint_field_reference_occurrence"),
                ),
                FieldRule(
                    "endpoint_zero",
                    ref("project_relationship_endpoint_field_reference_occurrence"),
                ),
                FieldRule(
                    "endpoint_one",
                    ref("project_relationship_endpoint_field_reference_occurrence"),
                ),
                FieldRule(
                    "semantics", enum("standard_equality_true_only_null_rejecting")
                ),
            ),
        ),
        "project_relationship_direction_identity": RecordRule(
            "project_relationship_direction_identity",
            (
                FieldRule(
                    "declaration", ref("project_relationship_declaration_identity")
                ),
                FieldRule("source", ref("project_relationship_endpoint_occurrence")),
                FieldRule("target", ref("project_relationship_endpoint_occurrence")),
            ),
        ),
        "project_at_most_one_evidence": RecordRule(
            "project_at_most_one_evidence",
            (
                FieldRule("direction", ref("project_relationship_direction_identity")),
                FieldRule("target_keys", seq(ref("project_ir_output_candidate_key"))),
                FieldRule(
                    "target_matched_classes", seq(ref("project_ir_output_value_class"))
                ),
                FieldRule(
                    "correspondences",
                    seq(ref("project_relationship_equality_correspondence")),
                ),
            ),
        ),
        "project_absent_referential_coverage": RecordRule(
            "project_absent_referential_coverage",
            (
                FieldRule("direction", ref("project_relationship_direction_identity")),
                FieldRule(
                    "state",
                    enum("concrete", "not_constructible_from_current_authored_source"),
                ),
            ),
        ),
        "relationship_match_clause": RecordRule(
            "relationship_match_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "project_ir_binary_join_identity": RecordRule(
            "project_ir_binary_join_identity",
            (
                FieldRule("use", ref("project_join_use_identity")),
                FieldRule("path_step_position", INTEGER),
            ),
        ),
        "project_concrete_relationship_condition": RecordRule(
            "project_concrete_relationship_condition",
            (
                FieldRule("identity", ref("project_relationship_base_match_identity")),
                FieldRule("relationship", ref("project_concrete_relationship_subject")),
                FieldRule("clause", ref("relationship_match_clause")),
                FieldRule(
                    "scope",
                    enum(
                        "relationship_base_match",
                        "join_local_on_refinement",
                        "post_join_filter",
                        "generic_join_match",
                    ),
                ),
                FieldRule(
                    "correspondences",
                    seq(ref("project_relationship_equality_correspondence")),
                ),
            ),
        ),
        "project_relationship_correspondence_identity": RecordRule(
            "project_relationship_correspondence_identity",
            (
                FieldRule(
                    "base_match", ref("project_relationship_base_match_identity")
                ),
                FieldRule("conjunct_position", INTEGER),
            ),
        ),
        "project_relationship_endpoint_field_reference_occurrence": RecordRule(
            "project_relationship_endpoint_field_reference_occurrence",
            (
                FieldRule(
                    "identity",
                    ref("project_relationship_endpoint_field_reference_identity"),
                ),
                FieldRule("expression", ref("dotted_name_expr")),
                FieldRule("endpoint", ref("project_relationship_endpoint_occurrence")),
                FieldRule("field_identity", ref("project_module_row_field_identity")),
                FieldRule("semantic_field", ref("project_row_field")),
                FieldRule(
                    "constraint_scope", ref("project_exact_row_output_constraint_scope")
                ),
            ),
        ),
        "relationship_endpoint": RecordRule(
            "relationship_endpoint",
            (
                FieldRule("span", ref("span")),
                FieldRule("local_name", TEXT),
                FieldRule("relation_name", TEXT),
            ),
        ),
        "project_traversal_step_use": RecordRule(
            "project_traversal_step_use",
            (
                FieldRule("identity", ref("project_traversal_step_use_identity")),
                FieldRule("step", ref("join_traversal_step")),
                FieldRule("state", enum("concrete", "unknown", "blocked", "ambiguous")),
                FieldRule(
                    "relationships",
                    seq(union(ref("project_concrete_relationship_subject"), ANCHOR)),
                ),
                FieldRule(
                    "directions",
                    seq(ref("project_directional_relationship_match_guarantee")),
                ),
                FieldRule("issues", seq(ANCHOR)),
            ),
        ),
        "project_relationship_declaration_identity": RecordRule(
            "project_relationship_declaration_identity",
            (
                FieldRule("module", ref("project_module_identity")),
                FieldRule("module_position", INTEGER),
                FieldRule("relationship_position", INTEGER),
            ),
        ),
        "project_relationship_endpoint_occurrence": RecordRule(
            "project_relationship_endpoint_occurrence",
            (
                FieldRule("identity", ref("project_relationship_endpoint_identity")),
                FieldRule("endpoint", ref("relationship_endpoint")),
                FieldRule(
                    "target",
                    union(ref("project_resolved_module_relation_symbol"), optional),
                ),
            ),
        ),
        "project_relationship_base_match_identity": RecordRule(
            "project_relationship_base_match_identity",
            (
                FieldRule(
                    "declaration", ref("project_relationship_declaration_identity")
                ),
            ),
        ),
        "project_concrete_relationship_subject": RecordRule(
            "project_concrete_relationship_subject",
            (
                FieldRule(
                    "occurrence", ref("project_relationship_declaration_occurrence")
                ),
            ),
        ),
        "project_relationship_endpoint_field_reference_identity": RecordRule(
            "project_relationship_endpoint_field_reference_identity",
            (
                FieldRule(
                    "correspondence",
                    ref("project_relationship_correspondence_identity"),
                ),
                FieldRule("operand_position", INTEGER),
            ),
        ),
        "project_traversal_step_use_identity": RecordRule(
            "project_traversal_step_use_identity",
            (
                FieldRule("join", ref("project_join_use_identity")),
                FieldRule("step_position", INTEGER),
            ),
        ),
        "project_relationship_endpoint_identity": RecordRule(
            "project_relationship_endpoint_identity",
            (
                FieldRule(
                    "declaration", ref("project_relationship_declaration_identity")
                ),
                FieldRule("endpoint_position", INTEGER),
            ),
        ),
        "project_relationship_declaration_occurrence": RecordRule(
            "project_relationship_declaration_occurrence",
            (
                FieldRule("identity", ref("project_relationship_declaration_identity")),
                FieldRule("module", ref("project_logical_module")),
                FieldRule("relationship", ref("relationship_metadata")),
                FieldRule(
                    "endpoints",
                    seq(
                        union(
                            ref("project_relationship_endpoint_occurrence"),
                            ref("project_relationship_endpoint_occurrence"),
                        )
                    ),
                ),
            ),
        ),
        "project_ir_property_stage": RecordRule(
            "project_ir_property_stage",
            (
                FieldRule(
                    "provided",
                    seq(
                        union(
                            ref("project_ir_provided_output_shape"),
                            ref("project_ir_provided_bag_multiplicity"),
                            ref("project_ir_provided_closed_bindings"),
                            ref("project_ir_provided_relation_ordering"),
                            ANCHOR,
                            ref("project_ir_provided_cardinality_upper_bound"),
                            ref("project_ir_provided_evaluation_policy"),
                            ANCHOR,
                        )
                    ),
                ),
                FieldRule("required", seq(ANCHOR)),
                FieldRule("effects", seq(ref("project_ir_effect_evidence"))),
            ),
        ),
        "project_ir_provided_relation_ordering": RecordRule(
            "project_ir_provided_relation_ordering",
            (
                FieldRule("output", ref("project_ir_relation_row_output")),
                FieldRule("evidence", ref("project_module_relation_semantic_facts")),
                FieldRule("items", seq(ref("order_item"))),
            ),
        ),
        "project_ir_provided_cardinality_upper_bound": RecordRule(
            "project_ir_provided_cardinality_upper_bound",
            (
                FieldRule("output", ref("project_ir_relation_row_output")),
                FieldRule("evidence", ref("project_module_relation_semantic_facts")),
                FieldRule("upper_bound", INTEGER),
            ),
        ),
        "project_ir_provided_output_shape": RecordRule(
            "project_ir_provided_output_shape",
            (
                FieldRule(
                    "output",
                    union(
                        ref("project_ir_scalar_field_output"),
                        ref("project_ir_stage_scalar_field_output"),
                        ref("project_ir_relation_row_output"),
                    ),
                ),
            ),
        ),
        "project_ir_provided_bag_multiplicity": RecordRule(
            "project_ir_provided_bag_multiplicity",
            (FieldRule("output", ref("project_ir_relation_row_output")),),
        ),
        "project_ir_provided_closed_bindings": RecordRule(
            "project_ir_provided_closed_bindings",
            (FieldRule("output", ref("project_ir_relation_row_output")),),
        ),
        "project_ir_scalar_field_output": RecordRule(
            "project_ir_scalar_field_output",
            (
                FieldRule("occurrence", ref("project_ir_output_value_occurrence")),
                FieldRule("field", ref("project_ir_row_field")),
            ),
        ),
        "project_ir_row_field": RecordRule(
            "project_ir_row_field",
            (
                FieldRule("anchor", ref("project_ir_field_anchor")),
                FieldRule("evidence", ref("project_row_field")),
            ),
        ),
        "project_ir_field_anchor": RecordRule(
            "project_ir_field_anchor",
            (FieldRule("identity", ref("project_module_row_field_identity")),),
        ),
        "authored_window_nth_direction": RecordRule(
            "authored_window_nth_direction",
            (
                FieldRule("span", ref("span")),
                FieldRule("kind", enum("first", "last")),
            ),
        ),
        "nth_value_position_fact": RecordRule(
            "nth_value_position_fact",
            (
                FieldRule("expression", ref("literal_expr")),
                FieldRule("effective_value", INTEGER),
            ),
        ),
        "project_current_materialized_input": RecordRule(
            "project_current_materialized_input",
            (
                FieldRule("authority", ANCHOR),
                FieldRule(
                    "incoming",
                    union(ref("project_ir_output_relational_properties"), optional),
                ),
                FieldRule("node", ref("project_ir_plan_node_occurrence")),
                FieldRule("occurrence", ref("project_ir_output_value_occurrence")),
            ),
        ),
        "project_current_input_field": RecordRule(
            "project_current_input_field",
            (
                FieldRule("authority", ANCHOR),
                FieldRule("field_position", INTEGER),
                FieldRule("identity", ref("project_module_row_field_identity")),
                FieldRule("evidence", ref("project_row_field")),
                FieldRule("original", ANCHOR),
                FieldRule(
                    "effective_nullability", enum("non_null", "nullable", "unknown")
                ),
            ),
        ),
        "project_current_input_grain_authority": RecordRule(
            "project_current_input_grain_authority",
            (
                FieldRule("source", ref("project_effective_join_input_authority")),
                FieldRule("incoming", ref("project_ir_provided_intrinsic_grain")),
                FieldRule("context", union(ANCHOR, optional)),
            ),
        ),
        "capability_profile_composition_blocker": RecordRule(
            "capability_profile_composition_blocker",
            (
                FieldRule(
                    "kind",
                    enum(
                        "invalid_base_kind",
                        "invalid_overlay_kind",
                        "duplicate_profile_reference",
                        "unresolved_base",
                        "ambiguous_base_reference",
                        "cycle",
                        "chain_not_rooted",
                        "target_family_mismatch",
                        "target_release_mismatch",
                        "schema_version_mismatch",
                        "exact_duplicate_capability_fact",
                    ),
                ),
                FieldRule("profiles", seq(ref("static_capability_profile"))),
                FieldRule(
                    "base_occurrences", seq(ref("capability_profile_base_occurrence"))
                ),
                FieldRule(
                    "fact_occurrences", seq(ref("capability_profile_fact_occurrence"))
                ),
                FieldRule("reference_chain", seq(ref("capability_profile_reference"))),
            ),
        ),
        "extension_signature_provider_context": RecordRule(
            "extension_signature_provider_context",
            (
                FieldRule(
                    "selectors", ref("extension_signature_requirement_selectors")
                ),
                FieldRule(
                    "selections",
                    seq(ref("extension_signature_provider_selection_occurrence")),
                ),
            ),
        ),
        "extension_signature_requirement_selector_occurrence": RecordRule(
            "extension_signature_requirement_selector_occurrence",
            (
                FieldRule("requirement_position", INTEGER),
                FieldRule("selector", ref("extension_signature_requirement_selector")),
            ),
        ),
        "extension_signature_provider_selection_occurrence": RecordRule(
            "extension_signature_provider_selection_occurrence",
            (
                FieldRule("requirement_position", INTEGER),
                FieldRule("selection", ref("extension_catalog_selection_result")),
            ),
        ),
        "project_effective_join_input_authority": RecordRule(
            "project_effective_join_input_authority",
            (
                FieldRule(
                    "entry",
                    union(
                        ref("project_existing_effective_output"),
                        ref("project_completed_effective_output"),
                        ref("project_completed_set_output"),
                    ),
                ),
            ),
        ),
        "extension_signature_requirement_selectors": RecordRule(
            "extension_signature_requirement_selectors",
            (
                FieldRule("requirements", ref("capability_requirement_collection")),
                FieldRule(
                    "occurrences",
                    seq(ref("extension_signature_requirement_selector_occurrence")),
                ),
            ),
        ),
        "extension_catalog_selection_result": RecordRule(
            "extension_catalog_selection_result",
            (
                FieldRule(
                    "outcome", enum("undeclared", "selected", "ambiguous", "conflict")
                ),
                FieldRule("requested_target", ref("extension_catalog_target")),
                FieldRule("active_project", union(ref("project_root"), optional)),
                FieldRule(
                    "availability", ref("declared_extension_catalog_availability")
                ),
                FieldRule(
                    "applicable_declarations",
                    seq(ref("extension_catalog_availability_declaration")),
                ),
                FieldRule(
                    "excluded_project_declarations",
                    seq(ref("extension_catalog_availability_declaration")),
                ),
                FieldRule(
                    "target_declarations",
                    seq(ref("extension_catalog_availability_declaration")),
                ),
                FieldRule(
                    "candidates", seq(ref("extension_catalog_selection_candidate"))
                ),
                FieldRule(
                    "selected_catalog",
                    union(ref("constructed_extension_catalog"), optional),
                ),
            ),
        ),
        "extension_signature_requirement_selector": RecordRule(
            "extension_signature_requirement_selector",
            (FieldRule("scope", ref("extension_catalog_lookup_scope")),),
        ),
        "capability_requirement_collection": RecordRule(
            "capability_requirement_collection",
            (
                FieldRule(
                    "identity", ref("capability_requirement_collection_identity")
                ),
                FieldRule("occurrences", seq(ref("capability_requirement_occurrence"))),
            ),
        ),
        "extension_catalog_target": RecordRule(
            "extension_catalog_target",
            (
                FieldRule("database_family", TEXT),
                FieldRule("database_release", TEXT),
                FieldRule("extension_identity", TEXT),
                FieldRule("extension_release", TEXT),
            ),
        ),
        "declared_extension_catalog_availability": RecordRule(
            "declared_extension_catalog_availability",
            (
                FieldRule(
                    "declarations",
                    seq(ref("extension_catalog_availability_declaration")),
                ),
            ),
        ),
        "constructed_extension_catalog": RecordRule(
            "constructed_extension_catalog",
            (
                FieldRule("metadata", ref("extension_catalog_metadata")),
                FieldRule(
                    "entries",
                    seq(
                        union(
                            ref("extension_native_type_catalog_entry"),
                            ref("extension_scalar_function_catalog_entry"),
                            ref("extension_aggregate_catalog_entry"),
                            ref("extension_operator_catalog_entry"),
                            ref("extension_cast_catalog_entry"),
                        )
                    ),
                ),
                FieldRule(
                    "completeness_claims",
                    seq(ref("extension_catalog_completeness_claim")),
                ),
                FieldRule("content_sha256", TEXT),
            ),
        ),
        "extension_catalog_lookup_scope": RecordRule(
            "extension_catalog_lookup_scope",
            (
                FieldRule(
                    "family",
                    enum(
                        "native_type",
                        "scalar_function",
                        "aggregate",
                        "operator",
                        "cast",
                    ),
                ),
                FieldRule(
                    "identity",
                    union(
                        ref("extension_catalog_type_reference"),
                        ref("postgre_sql_callable_identity"),
                        ref("postgre_sql_operator_identity"),
                        ref("postgre_sql_cast_identity"),
                    ),
                ),
            ),
        ),
        "extension_catalog_availability_declaration": RecordRule(
            "extension_catalog_availability_declaration",
            (
                FieldRule("owner", enum("compiler", "project")),
                FieldRule("position", INTEGER),
                FieldRule("catalog", ref("constructed_extension_catalog")),
                FieldRule("project", union(ref("project_root"), optional)),
            ),
        ),
        "extension_catalog_selection_candidate": RecordRule(
            "extension_catalog_selection_candidate",
            (
                FieldRule(
                    "identity", ref("extension_catalog_selection_candidate_identity")
                ),
                FieldRule("catalog", ref("constructed_extension_catalog")),
                FieldRule(
                    "declarations",
                    seq(ref("extension_catalog_availability_declaration")),
                ),
            ),
        ),
        "capability_requirement_collection_identity": RecordRule(
            "capability_requirement_collection_identity",
            (
                FieldRule("namespace", TEXT),
                FieldRule("name", TEXT),
            ),
        ),
        "capability_requirement_occurrence": RecordRule(
            "capability_requirement_occurrence",
            (
                FieldRule("owner", ref("capability_requirement_collection_identity")),
                FieldRule("position", INTEGER),
                FieldRule("key", ref("capability_key")),
            ),
        ),
        "extension_catalog_metadata": RecordRule(
            "extension_catalog_metadata",
            (
                FieldRule("schema_version", enum("pietto.extension-catalog.v1")),
                FieldRule("catalog", ref("extension_catalog_reference")),
                FieldRule("target", ref("extension_catalog_target")),
                FieldRule(
                    "source_occurrences",
                    seq(ref("extension_catalog_source_occurrence")),
                ),
            ),
        ),
        "postgre_sql_callable_identity": RecordRule(
            "postgre_sql_callable_identity",
            (
                FieldRule("sql_name", TEXT),
                FieldRule("input_types", seq(ref("extension_catalog_type_reference"))),
            ),
        ),
        "extension_catalog_selection_candidate_identity": RecordRule(
            "extension_catalog_selection_candidate_identity",
            (
                FieldRule("reference", ref("extension_catalog_reference")),
                FieldRule("target", ref("extension_catalog_target")),
                FieldRule("content_sha256", TEXT),
            ),
        ),
        "extension_catalog_identity": RecordRule(
            "extension_catalog_identity",
            (
                FieldRule("namespace", TEXT),
                FieldRule("name", TEXT),
            ),
        ),
        "extension_catalog_reference": RecordRule(
            "extension_catalog_reference",
            (
                FieldRule("identity", ref("extension_catalog_identity")),
                FieldRule("release", TEXT),
            ),
        ),
        "extension_catalog_source_provenance": RecordRule(
            "extension_catalog_source_provenance",
            (
                FieldRule("source_authority", TEXT),
                FieldRule("source_revision", TEXT),
                FieldRule("source_locator", TEXT),
                FieldRule("curation", TEXT),
            ),
        ),
        "extension_catalog_source_occurrence": RecordRule(
            "extension_catalog_source_occurrence",
            (
                FieldRule("owner", ref("extension_catalog_reference")),
                FieldRule("position", INTEGER),
                FieldRule("provenance", ref("extension_catalog_source_provenance")),
            ),
        ),
        "extension_catalog_type_reference": RecordRule(
            "extension_catalog_type_reference",
            (
                FieldRule(
                    "kind",
                    enum("pietto_logical", "postgres_builtin", "extension_native"),
                ),
                FieldRule(
                    "logical_type", union(ref("logical_type_identity"), optional)
                ),
                FieldRule("physical_name", union(TEXT, optional)),
                FieldRule("extension_identity", union(TEXT, optional)),
            ),
        ),
        "postgre_sql_operator_identity": RecordRule(
            "postgre_sql_operator_identity",
            (
                FieldRule("operator_name", TEXT),
                FieldRule("arity", enum("unary", "binary")),
                FieldRule(
                    "operand_types", seq(ref("extension_catalog_type_reference"))
                ),
            ),
        ),
        "postgre_sql_cast_identity": RecordRule(
            "postgre_sql_cast_identity",
            (
                FieldRule("source_type", ref("extension_catalog_type_reference")),
                FieldRule("target_type", ref("extension_catalog_type_reference")),
            ),
        ),
        "extension_catalog_declaration_type_use": RecordRule(
            "extension_catalog_declaration_type_use",
            (
                FieldRule("kind", enum("exact", "unmodeled")),
                FieldRule(
                    "exact_type",
                    union(ref("extension_catalog_type_reference"), optional),
                ),
                FieldRule("source_spelling", union(TEXT, optional)),
                FieldRule(
                    "unmodeled_reasons",
                    seq(
                        enum(
                            "unsupported_type_form",
                            "default_arguments",
                            "variadic_arguments",
                            "polymorphic_or_pseudo_type",
                            "set_returning",
                            "table_or_composite_return",
                            "ordered_set_or_hypothetical_set_aggregate",
                            "direct_arguments",
                        )
                    ),
                ),
            ),
        ),
        "extension_catalog_entry_evidence": RecordRule(
            "extension_catalog_entry_evidence",
            (
                FieldRule(
                    "matchability", enum("exact_matchable", "cataloged_unmodeled")
                ),
                FieldRule(
                    "exposure",
                    enum(
                        "direct_sql_surface", "implementation_support", "unclassified"
                    ),
                ),
                FieldRule(
                    "unmodeled_reasons",
                    seq(
                        enum(
                            "unsupported_type_form",
                            "default_arguments",
                            "variadic_arguments",
                            "polymorphic_or_pseudo_type",
                            "set_returning",
                            "table_or_composite_return",
                            "ordered_set_or_hypothetical_set_aggregate",
                            "direct_arguments",
                        )
                    ),
                ),
                FieldRule("source_positions", seq(INTEGER)),
            ),
        ),
        "postgre_sql_callable_declaration": RecordRule(
            "postgre_sql_callable_declaration",
            (
                FieldRule("sql_name", TEXT),
                FieldRule(
                    "input_types", seq(ref("extension_catalog_declaration_type_use"))
                ),
                FieldRule(
                    "identity", union(ref("postgre_sql_callable_identity"), optional)
                ),
            ),
        ),
        "extension_native_type_catalog_entry": RecordRule(
            "extension_native_type_catalog_entry",
            (
                FieldRule("type_identity", ref("extension_catalog_type_reference")),
                FieldRule(
                    "logical_mapping",
                    union(ref("extension_catalog_type_reference"), optional),
                ),
                FieldRule("evidence", ref("extension_catalog_entry_evidence")),
            ),
        ),
        "extension_scalar_function_catalog_entry": RecordRule(
            "extension_scalar_function_catalog_entry",
            (
                FieldRule("declaration", ref("postgre_sql_callable_declaration")),
                FieldRule("result_type", ref("extension_catalog_declaration_type_use")),
                FieldRule(
                    "null_call_behavior",
                    enum("unknown", "called_on_null_input", "strict"),
                ),
                FieldRule(
                    "volatility", enum("unknown", "immutable", "stable", "volatile")
                ),
                FieldRule(
                    "parallel_safety", enum("unknown", "unsafe", "restricted", "safe")
                ),
                FieldRule("has_default_arguments", BOOLEAN),
                FieldRule("is_variadic", BOOLEAN),
                FieldRule("returns_set", BOOLEAN),
                FieldRule("has_polymorphic_or_pseudo_types", BOOLEAN),
                FieldRule("evidence", ref("extension_catalog_entry_evidence")),
            ),
        ),
        "extension_aggregate_catalog_entry": RecordRule(
            "extension_aggregate_catalog_entry",
            (
                FieldRule("kind", enum("ordinary", "ordered_set", "hypothetical_set")),
                FieldRule("declaration", ref("postgre_sql_callable_declaration")),
                FieldRule("result_type", ref("extension_catalog_declaration_type_use")),
                FieldRule(
                    "parallel_safety", enum("unknown", "unsafe", "restricted", "safe")
                ),
                FieldRule("has_direct_arguments", BOOLEAN),
                FieldRule("is_variadic", BOOLEAN),
                FieldRule("evidence", ref("extension_catalog_entry_evidence")),
            ),
        ),
        "extension_operator_catalog_entry": RecordRule(
            "extension_operator_catalog_entry",
            (
                FieldRule("operator_name", TEXT),
                FieldRule("arity", enum("unary", "binary")),
                FieldRule(
                    "operand_types", seq(ref("extension_catalog_declaration_type_use"))
                ),
                FieldRule(
                    "identity", union(ref("postgre_sql_operator_identity"), optional)
                ),
                FieldRule("result_type", ref("extension_catalog_declaration_type_use")),
                FieldRule("evidence", ref("extension_catalog_entry_evidence")),
            ),
        ),
        "extension_cast_catalog_entry": RecordRule(
            "extension_cast_catalog_entry",
            (
                FieldRule("source_type", ref("extension_catalog_declaration_type_use")),
                FieldRule("target_type", ref("extension_catalog_declaration_type_use")),
                FieldRule(
                    "identity", union(ref("postgre_sql_cast_identity"), optional)
                ),
                FieldRule(
                    "context",
                    enum("unknown", "explicit_only", "assignment", "implicit"),
                ),
                FieldRule("method", enum("unknown", "function", "binary", "inout")),
                FieldRule("evidence", ref("extension_catalog_entry_evidence")),
            ),
        ),
        "extension_catalog_completeness_claim": RecordRule(
            "extension_catalog_completeness_claim",
            (
                FieldRule("scope", ref("extension_catalog_lookup_scope")),
                FieldRule("kind", enum("complete", "incomplete")),
                FieldRule("source_positions", seq(INTEGER)),
            ),
        ),
        "type_def": RecordRule(
            "type_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("base", ref("type_expr")),
                FieldRule("ensures", seq(ref("ensure_clause"))),
            ),
        ),
        "project_module_reference_attribution": RecordRule(
            "project_module_reference_attribution",
            (
                FieldRule(
                    "identity", ref("project_module_reference_occurrence_identity")
                ),
                FieldRule("owner_occurrence", ref("project_declaration_occurrence")),
                FieldRule(
                    "site",
                    union(
                        ref("type_expr"),
                        ref("source_def"),
                        ref("from_clause"),
                        ref("select_item"),
                    ),
                ),
            ),
        ),
        "project_resolved_nominal_symbol": RecordRule(
            "project_resolved_nominal_symbol",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("local_name", TEXT),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
                FieldRule("target_occurrence", ref("project_declaration_occurrence")),
                FieldRule(
                    "local_occurrence",
                    union(ref("project_declaration_occurrence"), optional),
                ),
                FieldRule(
                    "imported_binding",
                    union(ref("project_resolved_imported_binding"), optional),
                ),
            ),
        ),
        "project_nominal_declaration_identity": RecordRule(
            "project_nominal_declaration_identity",
            (
                FieldRule("module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("declared_name", TEXT),
            ),
        ),
        "import_item": RecordRule(
            "import_item",
            (
                FieldRule("span", ref("span")),
                FieldRule(
                    "declaration_kind",
                    enum("type", "enum", "shape", "source", "table", "query"),
                ),
                FieldRule("exported_name", TEXT),
                FieldRule("local_name", union(TEXT, optional)),
                FieldRule("declaration_kind_span", ref("span")),
                FieldRule("exported_name_span", ref("span")),
                FieldRule("local_name_span", union(ref("span"), optional)),
            ),
        ),
        "import_statement": RecordRule(
            "import_statement",
            (
                FieldRule("span", ref("span")),
                FieldRule("target", TEXT),
                FieldRule("target_span", ref("span")),
                FieldRule("items", seq(ref("import_item"))),
            ),
        ),
        "export_item": RecordRule(
            "export_item",
            (
                FieldRule("span", ref("span")),
                FieldRule(
                    "declaration_kind",
                    enum("type", "enum", "shape", "source", "table", "query"),
                ),
                FieldRule("local_name", TEXT),
                FieldRule("declaration_kind_span", ref("span")),
                FieldRule("local_name_span", ref("span")),
            ),
        ),
        "export_statement": RecordRule(
            "export_statement",
            (
                FieldRule("span", ref("span")),
                FieldRule("items", seq(ref("export_item"))),
            ),
        ),
        "project_module_import_attribution": RecordRule(
            "project_module_import_attribution",
            (
                FieldRule("identity", ref("project_module_import_occurrence_identity")),
                FieldRule("request", ref("project_module_import_request")),
            ),
        ),
        "project_module_access_hop": RecordRule(
            "project_module_access_hop",
            (
                FieldRule(
                    "import_occurrence",
                    ref("project_module_import_occurrence_identity"),
                ),
                FieldRule(
                    "facade_occurrence",
                    ref("project_module_facade_occurrence_identity"),
                ),
                FieldRule(
                    "facade_origin", enum("local_declaration", "explicit_reexport")
                ),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
            ),
        ),
        "project_module_facade_attribution": RecordRule(
            "project_module_facade_attribution",
            (
                FieldRule("identity", ref("project_module_facade_occurrence_identity")),
                FieldRule("origin", enum("local_declaration", "explicit_reexport")),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
                FieldRule(
                    "target_occurrence", ref("project_declaration_occurrence_identity")
                ),
                FieldRule("entry", ref("project_module_export_entry")),
            ),
        ),
        "project_resolved_imported_binding": RecordRule(
            "project_resolved_imported_binding",
            (
                FieldRule("identity", ref("project_imported_binding_identity")),
                FieldRule("target_module_path", TEXT),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
                FieldRule("request", ref("project_module_import_request")),
                FieldRule("resolved_entry", ref("project_module_export_entry")),
            ),
        ),
        "project_module_import_occurrence_identity": RecordRule(
            "project_module_import_occurrence_identity",
            (
                FieldRule("binding_identity", ref("project_imported_binding_identity")),
                FieldRule("target_module_path", TEXT),
                FieldRule("exported_name", TEXT),
                FieldRule("module_statement_position", INTEGER),
                FieldRule("item_position", INTEGER),
            ),
        ),
        "project_root": RecordRule("project_root", (FieldRule("path", TEXT),)),
        "project_module_import_request": RecordRule(
            "project_module_import_request",
            (
                FieldRule("identity", ref("project_imported_binding_identity")),
                FieldRule("target_module_path", TEXT),
                FieldRule("exported_name", TEXT),
                FieldRule("module_statement_position", INTEGER),
                FieldRule("item_position", INTEGER),
                FieldRule("source_statement", ref("import_statement")),
                FieldRule("source_item", ref("import_item")),
            ),
        ),
        "project_module_facade_occurrence_identity": RecordRule(
            "project_module_facade_occurrence_identity",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("exposed_name", TEXT),
                FieldRule("module_statement_position", INTEGER),
                FieldRule("item_position", INTEGER),
            ),
        ),
        "project_module_export_entry": RecordRule(
            "project_module_export_entry",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("exposed_name", TEXT),
                FieldRule("origin", enum("local_declaration", "explicit_reexport")),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
                FieldRule("request", ref("project_module_export_request")),
                FieldRule(
                    "resolved_from",
                    union(
                        ref("project_declaration_occurrence"),
                        ref("project_imported_export_candidate"),
                    ),
                ),
            ),
        ),
        "project_imported_binding_identity": RecordRule(
            "project_imported_binding_identity",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("local_binding_name", TEXT),
            ),
        ),
        "project_module_export_request": RecordRule(
            "project_module_export_request",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("local_name", TEXT),
                FieldRule("module_statement_position", INTEGER),
                FieldRule("item_position", INTEGER),
                FieldRule("source_item", ref("export_item")),
            ),
        ),
        "project_imported_export_candidate": RecordRule(
            "project_imported_export_candidate",
            (
                FieldRule("owning_module_path", TEXT),
                FieldRule("namespace", enum("type", "relation", "callable")),
                FieldRule(
                    "declaration_kind",
                    enum(
                        "type",
                        "enum",
                        "shape",
                        "source",
                        "table",
                        "query",
                        "constraint",
                        "derive",
                    ),
                ),
                FieldRule("local_binding_name", TEXT),
                FieldRule(
                    "target_identity", ref("project_nominal_declaration_identity")
                ),
                FieldRule("proof", enum("explicit_named_import")),
                FieldRule("module_statement_position", INTEGER),
                FieldRule("item_position", INTEGER),
                FieldRule("source_span", ref("span")),
            ),
        ),
        "project_qualify_reference_resolution": RecordRule(
            "project_qualify_reference_resolution",
            (
                FieldRule("stage", ref("project_concrete_joined_window_stage")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule(
                    "candidates",
                    seq(
                        union(
                            ref("project_joined_window_input_binding"),
                            ref("project_selected_window_result_binding"),
                        )
                    ),
                ),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule(
                    "target",
                    union(
                        union(
                            ref("project_joined_window_input_binding"),
                            ref("project_selected_window_result_binding"),
                        ),
                        optional,
                    ),
                ),
            ),
        ),
        "project_concrete_window_computation": RecordRule(
            "project_concrete_window_computation",
            (
                FieldRule("site", ref("project_window_computation_site")),
                FieldRule(
                    "input_namespace", ref("project_joined_window_input_namespace")
                ),
                FieldRule(
                    "resolutions", seq(ref("project_joined_window_input_resolution"))
                ),
                FieldRule("analysis", ref("window_computation_analysis")),
                FieldRule(
                    "dependencies", seq(ref("project_window_dependency_occurrence"))
                ),
            ),
        ),
        "project_selected_window_result_binding": RecordRule(
            "project_selected_window_result_binding",
            (
                FieldRule("computation", ref("project_concrete_window_computation")),
                FieldRule("item", ref("select_item")),
                FieldRule("selected_output_ordinal", INTEGER),
                FieldRule("output_name", TEXT),
                FieldRule("occurrence", ref("window_occurrence_identity")),
                FieldRule("value_type", ref("value_type")),
            ),
        ),
        "project_joined_window_input_namespace": RecordRule(
            "project_joined_window_input_namespace",
            (
                FieldRule("aggregation", ref("project_concrete_joined_aggregation")),
                FieldRule("bindings", seq(ref("project_joined_window_input_binding"))),
            ),
        ),
        "project_window_dependency_occurrence": RecordRule(
            "project_window_dependency_occurrence",
            (
                FieldRule("site", ref("project_window_computation_site")),
                FieldRule("global_ordinal", INTEGER),
                FieldRule("role_ordinal", INTEGER),
                FieldRule(
                    "role",
                    enum(
                        "relation_input",
                        "window_argument",
                        "window_default",
                        "window_partition",
                        "window_order",
                    ),
                ),
                FieldRule("expression", ANCHOR),
                FieldRule(
                    "target",
                    union(
                        ref("project_joined_window_input_namespace"),
                        ref("project_joined_window_input_binding"),
                    ),
                ),
                FieldRule("location", ref("source_location")),
            ),
        ),
        "project_joined_window_input_binding": RecordRule(
            "project_joined_window_input_binding",
            (
                FieldRule("aggregation", ref("project_concrete_joined_aggregation")),
                FieldRule("name", TEXT),
                FieldRule("qualifier", union(TEXT, optional)),
                FieldRule(
                    "kind",
                    enum(
                        "joined_field",
                        "field_backed_let",
                        "group_key",
                        "aggregate_result",
                        "group_key_backed_let",
                    ),
                ),
                FieldRule("value_type", ref("value_type")),
                FieldRule(
                    "joined_field",
                    union(ref("project_joined_row_field_semantics"), optional),
                ),
                FieldRule(
                    "let_value", union(ref("project_joined_let_value"), optional)
                ),
                FieldRule(
                    "stage_output",
                    union(ref("project_joined_stage_output_occurrence"), optional),
                ),
            ),
        ),
        "enum_def": RecordRule(
            "enum_def",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
                FieldRule("members", seq(TEXT)),
            ),
        ),
        "ensure_clause": RecordRule(
            "ensure_clause",
            (
                FieldRule("span", ref("span")),
                FieldRule("expression", ANCHOR),
            ),
        ),
        "annotation": RecordRule(
            "annotation",
            (
                FieldRule("span", ref("span")),
                FieldRule("name", TEXT),
            ),
        ),
        "project_concrete_joined_window_stage": RecordRule(
            "project_concrete_joined_window_stage",
            (
                FieldRule(
                    "input_aggregation", ref("project_concrete_joined_aggregation")
                ),
                FieldRule("kind", enum("absent", "window_evaluation")),
                FieldRule("named_namespace", ref("resolved_named_window_namespace")),
                FieldRule(
                    "computations", seq(ref("project_concrete_window_computation"))
                ),
                FieldRule(
                    "selected_results",
                    seq(ref("project_selected_window_result_binding")),
                ),
            ),
        ),
        "project_window_computation_site": RecordRule(
            "project_window_computation_site",
            (
                FieldRule("kind", enum("selected_output", "hidden_inline")),
                FieldRule(
                    "root",
                    union(
                        ref("project_concrete_joined_aggregation"),
                        ref("project_concrete_joined_window_stage"),
                    ),
                ),
                FieldRule("expression", ref("window_expr")),
                FieldRule("item", union(ref("select_item"), optional)),
                FieldRule("selected_output_ordinal", union(INTEGER, optional)),
                FieldRule(
                    "occurrence", union(ref("window_occurrence_identity"), optional)
                ),
            ),
        ),
        "project_joined_window_input_resolution": RecordRule(
            "project_joined_window_input_resolution",
            (
                FieldRule("namespace", ref("project_joined_window_input_namespace")),
                FieldRule(
                    "expression", union(ref("name_expr"), ref("dotted_name_expr"))
                ),
                FieldRule(
                    "candidates", seq(ref("project_joined_window_input_binding"))
                ),
                FieldRule(
                    "status",
                    enum(
                        "concrete",
                        "unknown",
                        "deferred",
                        "blocked",
                        "absent",
                        "ambiguous",
                    ),
                ),
                FieldRule(
                    "target",
                    union(ref("project_joined_window_input_binding"), optional),
                ),
            ),
        ),
        "project_aggregate_selected_result": RecordRule(
            "project_aggregate_selected_result",
            (
                FieldRule("field", ref("project_row_field")),
                FieldRule("fact", ref("project_aggregate_result_fact")),
            ),
        ),
        "project_ir_aggregate_evaluation_context": RecordRule(
            "project_ir_aggregate_evaluation_context",
            (
                FieldRule("operator", ref("project_ir_logical_operator_occurrence")),
                FieldRule("input_row_output", ref("project_ir_relation_row_output")),
                FieldRule("result_row_output", ref("project_ir_relation_row_output")),
                FieldRule(
                    "semantic_facts", ref("project_module_relation_semantic_facts")
                ),
                FieldRule(
                    "readiness", ref("project_aggregate_grouped_clause_readiness")
                ),
                FieldRule("group_keys", seq(ref("group_by_item"))),
                FieldRule(
                    "aggregate_results", seq(ref("project_aggregate_result_fact"))
                ),
                FieldRule("let_scope", ref("project_relation_let_scope_facts")),
                FieldRule(
                    "input_closed_bindings", ref("project_ir_provided_closed_bindings")
                ),
                FieldRule(
                    "result_closed_bindings", ref("project_ir_provided_closed_bindings")
                ),
                FieldRule("input_effect", ref("project_ir_effect_evidence")),
                FieldRule("result_effect", ref("project_ir_effect_evidence")),
            ),
        ),
        "project_refined_match_bounds": RecordRule(
            "project_refined_match_bounds",
            (
                FieldRule(
                    "base", ref("project_directional_relationship_match_guarantee")
                ),
                FieldRule("minimum", enum("zero_allowed", "at_least_one")),
                FieldRule(
                    "maximum", enum("at_most_zero", "at_most_one", "unbounded_by_one")
                ),
                FieldRule(
                    "maximum_evidence",
                    union(
                        ref("project_at_most_one_evidence"),
                        enum(
                            "coverage_not_constructible",
                            "source_nullability_not_proven",
                            "target_key_not_proven",
                            "condition_not_proof_capable",
                        ),
                    ),
                ),
            ),
        ),
        "project_ir_rebound_existing_output": RecordRule(
            "project_ir_rebound_existing_output",
            (
                FieldRule("owner", ref("project_declaration_occurrence")),
                FieldRule("semantic_entry", ref("project_existing_effective_output")),
                FieldRule(
                    "relation_input", ref("project_ir_query_block_relation_input_edge")
                ),
                FieldRule(
                    "operators", seq(ref("project_ir_logical_operator_occurrence"))
                ),
                FieldRule(
                    "original_operators",
                    seq(ref("project_ir_logical_operator_occurrence")),
                ),
            ),
        ),
    }
)
