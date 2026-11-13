"""Actionable public blocker advice; no changes to private blocker identity."""

from __future__ import annotations

from pietto._project.project_sql_emission_ast import PREMISE_VALUES
from pietto._project.project_sql_emission_contract import CODES, RELEASES, canonical

__all__: tuple[str, ...] = ()


def canonical_text(value: object) -> str:
    return canonical(value).decode("utf-8")


def _specific_hint(detail: str, family: str) -> str | None:
    """Concrete contract and source remedies shared by both presentations."""

    for key, values in PREMISE_VALUES.items():
        premise = canonical_text(
            {"key": key, "scope": "statement", "value": values[family]}
        )
        if detail == f"{key}_declaration_missing":
            return f'add {premise} to "environment"'
        if detail in {f"{key}_declaration_mismatch", f"{key}_mismatch"}:
            return f"the reviewed {family} value is {premise}"
    if detail in {
        "row_domain_matches_declaration_required",
        "read_only_object_declaration_required",
    }:
        key = detail.removesuffix("_declaration_required")
        premise = canonical_text({"key": key, "scope": "source", "value": True})
        return f'add {premise} to the source\'s "premises"'
    if detail == "complete_ordered_source_schema_required":
        return (
            'map every field of the source\'s shape once in "fields", in shape'
            " order; related lists the fields left out or out of order"
        )
    if detail == "target_release_not_reviewed":
        return f'the reviewed {family} release is "{RELEASES[family]}"'
    if detail == "order":
        return (
            "without GROUP BY, a key must be an input field, a restated selected"
            " expression or a selected let name, of a type that orders"
        )
    if detail in {
        "arithmetic_outside_physical_range",
        "unary_result_outside_physical_range",
        "abs_result_outside_physical_range",
    }:
        if family == "postgres":
            return (
                "every value of this result lies outside a signed 64-bit"
                " integer, so PostgreSQL's checked bigint operation could only"
                " fail"
            )
        return (
            "an Int field ranges over its whole storage type; its declared"
            " int_range does not narrow that, so the result must fit a signed"
            " 64-bit integer"
        )
    return None


_GROUPS = (
    (
        frozenset(
            {
                "aggregate_projection_denominator",
                "aggregate_projection_drift",
                "capture_outside_read_scope",
                "captured_field_outside_scope",
                "collect_children_drift",
                "collect_order_key_not_visible",
                "collect_ordinal_inside_distinct",
                "collect_read_drift",
                "collect_terminal_without_order",
                "collect_terminal_without_ordinal",
                "distinct_boundary_evidence_missing",
                "distinct_over_nested_group",
                "distinct_tuple_includes_hidden_value",
                "element_read_outside_list_scope",
                "expression_block_producer_not_realized",
                "expression_block_use_outside_scope",
                "inline_let_without_body",
                "inline_read_without_capture",
                "let_export_expression_drift",
                "list_read_outside_stage_scope",
                "match_reference_outside_pre_match_scope",
                "named_producer_not_realized",
                "order_boundary_evidence_missing",
                "order_expression_inventory_drift",
                "order_item_inventory_drift",
                "order_over_nested_group",
                "order_use_inventory_drift",
                "order_value_port_missing",
                "projection_export_conflict",
                "reference_outside_its_admitted_scope",
                "reference_outside_stage_scope",
                "result_boundary_input_drift",
                "result_boundary_output_drift",
                "result_helper_port_not_bound",
                "result_projection_not_a_closed_stage",
                "result_projection_port_drift",
                "result_terminal_denominator",
                "result_terminal_drift",
                "result_visible_tuple_drift",
                "scalar_read_column_not_realized",
                "selected_body_not_last",
                "set_column_inventory_drift",
                "set_inventory_drift",
                "set_operand_inventory_drift",
                "set_operand_terminal_not_bound",
                "set_operand_use_not_bound",
                "set_terminal_denominator",
                "stage_carry_port_drift",
                "stage_export_denominator",
                "stage_export_not_bound",
                "stage_input_not_bound",
                "stage_terminal_denominator",
                "values_column_inventory_drift",
                "values_inventory_drift",
            }
        ),
        "Re-emit from the original checked project and emission contract. If this correspondence "
        "error persists, report its code and detail; do not edit generated SQL or metadata.",
    ),
    (
        frozenset(
            {
                "generated_structure_limit",
                "parameter_occurrence_limit",
                "public_artifact_byte_limit",
                "sql_byte_limit",
            }
        ),
        "Reduce the selected query structure, parameter occurrences or output size to fit the "
        "reviewed emission limits; do not bypass the limit.",
    ),
    (
        frozenset(
            {
                "any_reference_logical_type_or_null_drift",
                "avg_result_logical_type_or_argument_drift",
                "captured_field_logical_type_drift",
                "captured_field_null_drift",
                "comparison_result_not_bool",
                "count_result_not_non_null_int",
                "decimal_result_outside_physical_range",
                "distinct_field_temporal_physical_representation_mismatch",
                "distinct_field_uuid_physical_representation_mismatch",
                "element_read_logical_type_drift",
                "element_read_null_drift",
                "empty_membership_not_non_null_bool",
                "existence_result_not_non_null_bool",
                "extrema_result_logical_type_drift",
                "extrema_result_must_admit_empty_input_null",
                "filtered_count_result_not_non_null_int",
                "filtered_sum_result_not_non_null_int",
                "first_last_result_logical_type_drift",
                "float_result_not_finite",
                "group_test_result_not_non_null_bool",
                "group_key_logical_type_or_null_drift",
                "group_key_outside_bool_domain",
                "group_key_temporal_physical_representation_mismatch",
                "group_key_uuid_physical_representation_mismatch",
                "join_output_nullability_drift",
                "join_port_logical_type_drift",
                "list_operation_type_drift",
                "literal_leaf_representation",
                "logical_operand_outside_bool_domain",
                "lpad_width_outside_physical_range",
                "null_test_result_not_non_null_bool",
                "nullability_mismatch",
                "physical_storage_or_domain_mismatch",
                "pre_match_port_nullability_drift",
                "predicate_root_not_bool",
                "quantile_result_logical_type_or_argument_drift",
                "reference_logical_type_or_null_drift",
                "relation_membership_result_not_nullable_bool",
                "round_result_outside_physical_range",
                "scalar_read_type_mismatch",
                "set_column_logical_type_drift",
                "set_column_nullability_drift",
                "set_column_physical_representation_mismatch",
                "string_agg_result_logical_type_drift",
                "substring_index_outside_physical_range",
                "stddev_result_logical_type_or_argument_drift",
                "variance_result_logical_type_or_argument_drift",
                "pvariance_result_logical_type_or_argument_drift",
                "pstdev_result_logical_type_or_argument_drift",
                "sum_result_logical_type_or_argument_drift",
                "text_length_outside_physical_range",
                "unary_logical_type_mismatch",
                "unary_result_representation",
                "values_cell_representation",
                "window_default_integer_out_of_signed64_range",
                "window_distribution_result_not_float",
                "window_frame_offset_out_of_signed64_range",
                "window_order_comparison_domain_unsupported",
                "window_partition_comparison_domain_unsupported",
                "window_range_boundary_out_of_signed64_range",
                "window_range_key_domain_out_of_storage_range",
                "window_rank_result_not_non_null_int",
                "window_result_logical_type_drift",
                "window_value_domain_out_of_storage_range",
            }
        ),
        "Use an expression whose result fits its actual source carrier, logical type and "
        "nullability. Keep unsupported expressions in check/plan; changing the contract or forcing "
        "a cast does not establish that proof.",
    ),
    (
        frozenset(
            {
                "avg_int_range_evidence_missing",
                "decimal_aggregate_range_proof_missing",
                "decimal_source_carrier_missing",
                "expression_logical_type_evidence_missing",
                "float_aggregate_finite_result_proof_missing",
                "float_carrier_missing",
                "group_key_decimal_parameters_missing",
                "group_key_int_range_evidence_missing",
                "group_key_text_comparison_domain_missing",
                "int_range_proof_missing",
                "join_port_logical_type_evidence_missing",
                "limit_static_evidence_missing",
                "logical_temporal_or_uuid_meaning_missing",
                "logical_type_evidence_missing",
                "lpad_result_bound_missing",
                "match_condition_evidence_missing",
                "match_reference_logical_type_missing",
                "membership_condition_missing",
                "membership_typed_null_context_missing",
                "order_direction_evidence_missing",
                "set_operand_field_representation_missing",
                "substring_result_bound_missing",
                "sum_int_aggregate_range_proof_missing",
                "text_case_result_bound_missing",
                "text_concat_result_bound_missing",
                "text_length_bound_missing",
                "text_replace_result_bound_missing",
                "window_bucket_static_evidence_missing",
                "window_count_parameter_evidence_missing",
                "window_default_static_evidence_missing",
                "window_frame_bound_evidence_missing",
                "window_frame_offset_evidence_missing",
                "window_offset_static_evidence_missing",
                "window_order_direction_evidence_missing",
                "window_policy_evidence_missing",
                "window_position_static_evidence_missing",
                "window_range_arithmetic_evidence_missing",
                "window_result_anchor_missing",
                "window_value_argument_evidence_missing",
            }
        ),
        "Keep this expression in check/plan, or select a direct field with a reviewed carrier: the "
        "compiler lacks the required proof. Do not invent a range, meaning or bound in the "
        "contract.",
    ),
    (
        frozenset(
            {
                "decimal_comparison_parameter_conflict",
                "field_domain_premise_mismatch",
                "inconsistent_declared_scope",
                "mysql_window_count_exceeds_target_resource_limit",
                "predicate_retention_effects_changed",
                "set_column_decimal_parameter_mismatch",
                "set_column_text_domain_mismatch",
                "target_evidence_scope_conflict",
                "text_comparison_domain_conflict",
            }
        ),
        "Make the source and contract describe the same actual carrier and target premises. Keep "
        "incompatible operations separate; do not discard a conflicting requirement to force "
        "emission.",
    ),
    (
        frozenset(
            {
                "negative_original_target_evidence",
                "original_enforcement_not_fulfilled",
                "original_profile_composition_unresolved",
            }
        ),
        "Choose a target whose reviewed capabilities satisfy the original requirement, or keep this "
        "declaration in check/plan. Do not drop the requirement.",
    ),
    (
        frozenset(
            {
                "any_predicate_requires_bool",
                "arithmetic_requires_signed_int_operands",
                "between_type_pair_not_admitted",
                "binary_operator_not_admitted",
                "cast_realization_not_admitted",
                "comparison_operator_not_admitted",
                "comparison_type_pair_not_admitted",
                "conditional_realization_not_admitted",
                "date_trunc_unit_not_a_static_supported_text",
                "decimal_direct_source_operands_required",
                "decimal_scale_mismatch",
                "float_division_not_realized",
                "float_literal_operands_required",
                "float_remainder_exact_binary64_not_realized",
                "like_text_domain_not_admitted",
                "list_operation_operand_not_admitted",
                "literal_type_or_sign_context_not_supported",
                "logical_operands_require_bool",
                "membership_realization_not_admitted",
                "membership_type_pair_not_admitted",
                "operator_not_implemented_in_slice6",
                "relation_membership_width_not_one",
                "round_scale_not_a_static_supported_int",
                "row_expression_not_admitted_in_slice6",
                "scalar_call_signature_not_admitted",
                "scalar_expression_not_in_literal_sign_domain",
                "typed_null_sign_not_admitted",
                "unary_not_requires_bool_operand",
                "unary_operator_not_admitted",
                "unary_sign_requires_int_operand",
            }
        ),
        "Use an already supported scalar form with its reviewed operand carriers, or keep this "
        "expression in check/plan. Do not use a cast or a different contract to force emission.",
    ),
    (
        frozenset(
            {
                "aggregate_argument_not_a_direct_established_field",
                "aggregate_function_not_promised_in_slice8",
                "distinct_field_comparison_domain_unsupported",
                "first_last_order_key_outside_reviewed_order_domain",
                "group_key_type_outside_reviewed_comparison_domain",
                "hidden_strict_fd_order_approved_non_support",
                "non_field_projection_or_later_shape",
                "order_carrier_not_recognized",
                "order_comparison_domain_unsupported",
                "order_expression_requires_established_port",
                "representation_not_in_initial_domain",
                "scalar_meaning_requires_field_projection",
                "set_body_shape_not_admitted",
                "string_agg_argument_requires_postgres_text",
            }
        ),
        "Use a reviewed direct projection or grouping/order/set form with matching carriers, or "
        "keep this declaration in check/plan; do not widen equality or coerce operands to force "
        "emission.",
    ),
    (
        frozenset(
            {
                "full_join_condition_not_an_equality",
                "full_join_condition_not_an_equality_tree",
                "full_join_condition_uses_or",
                "full_join_equality_operand_not_a_direct_field",
                "full_join_equality_outside_reviewed_int_domain",
                "full_join_equality_within_one_input",
                "full_join_requires_cross_input_equality",
                "match_binary_operator_not_admitted",
                "match_comparison_operator_not_admitted",
                "match_condition_not_in_row_domain",
                "mysql_full_join_approved_non_support",
            }
        ),
        "Use the documented JOIN kind and direct equality domain for this target, or keep this JOIN "
        "in check/plan. Arbitrary ON expressions and MySQL FULL JOIN are not admitted.",
    ),
    (
        frozenset(
            {
                "aggregate_composition_not_admitted_on_target",
                "collect_not_admitted_on_target",
                "group_key_type_not_admitted",
                "list_operation_not_admitted_on_target",
                "mysql_correlated_order_or_limit_read_not_admitted",
                "query_parameter_type_not_admitted_on_target",
                "table_function_not_admitted_on_target",
                "unnest_not_admitted_on_target",
                "zero_physical_source_not_admitted_on_target",
            }
        ),
        "Keep this declaration in check/plan or select an artifact using the forms reviewed for the "
        "requested target. Do not relabel the target or source carrier to bypass this refusal.",
    ),
    (
        frozenset(
            {
                "window_argument_role_not_realized_yet",
                "window_default_literal_kind_not_realized_yet",
                "window_frame_unit_not_promised_in_phase66",
                "window_from_last_approved_non_support_in_phase66",
                "window_function_not_promised_in_phase66",
                "window_ignore_nulls_approved_non_support_in_phase66",
                "window_parameter_value_kind_not_realized_yet",
            }
        ),
        "Use the documented window function, argument and frame surface for this target, or keep "
        "this window in check/plan; unsupported modifiers cannot be enabled by a contract premise.",
    ),
    (
        frozenset(
            {
                "active_output_unavailable",
                "call_authority_unavailable",
                "distinct",
                "expression_evidence_unavailable",
                "group",
                "ir_stage",
                "join",
                "limit",
                "qualify",
                "satisfying",
                "semantic_result_unsuccessful",
                "set_operation",
                "static_source_unavailable",
                "window",
            }
        ),
        "Run check --project and resolve the declaration diagnostics or missing planning "
        "prerequisite, then emit again. Keep a still-unsupported declaration in check/plan rather "
        "than fabricating plan evidence.",
    ),
)

_GROUPS += (
    (
        frozenset(
            """aggregate_projection_outside_result_scope aggregate_result_denominator
aggregate_result_port_drift any_producer_not_realized any_reference_outside_input_scope
any_reference_outside_lexical_scope group_key_outside_pre_aggregate_input group_key_result_port_drift
join_input_terminal_drift join_input_use_not_bound join_predecessor_not_realized
join_predecessor_port_drift limit_boundary_evidence_missing nested_read_without_group
relationship_equality_not_retained relationship_equality_outside_pre_match_scope
unnest_children_drift unnest_collect_drift unnest_input_use_not_bound unnest_join_ambiguity
unnest_join_kind_drift unnest_source_not_in_left_input unnest_source_not_nested
unnest_withheld_port_drift unnest_without_left_input
window_export_denominator window_order_outside_pre_window_input window_partition_outside_pre_window_input
window_projection_drift window_projection_outside_result_scope window_projection_reads_non_window_port
window_result_port_drift window_value_outside_pre_window_input""".split()
        ),
        "Re-emit from the original checked project and emission contract. If this correspondence error persists, report its code and detail; do not edit generated SQL or metadata.",
    ),
    (
        frozenset(
            """match_condition_root_not_bool postgres_window_structural_argument_out_of_int32_range
relationship_equality_type_pair_drift table_function_binding_unrepresentable""".split()
        ),
        "Use a value within the reviewed logical and physical domain for this operation. Keep unsupported arguments in check/plan; do not change the contract to claim a different carrier.",
    ),
    (
        frozenset(
            """aggregate_argument_signature_not_admitted aggregate_requires_its_authored_argument
distinct_field_equivalence_unsupported sum_avg_result_realization_rule_not_reviewed_in_phase66
window_argument_signature_not_admitted""".split()
        ),
        "Use the reviewed argument and result carrier for the selected aggregate, window or equality operation, or keep this declaration in check/plan.",
    ),
    (
        frozenset(
            """aggregate_result_logical_type_evidence_missing group_key_logical_type_evidence_missing
window_named_declaration_evidence_missing window_result_logical_type_evidence_missing""".split()
        ),
        "Run check --project and retain the source declaration that establishes this type or window. If the compiler still cannot prove it, keep the expression in check/plan; do not fabricate evidence.",
    ),
)

_ACTIONS = {
    "join_input_source_field_not_bound": "Map every field of the JOIN input shape in the emission contract, in shape order, using its actual physical column.",
    "join_input_field_representation_missing": "Use a source shape with an admitted representation for every JOIN input field; omitting an unsupported field only in SELECT does not establish that representation.",
    "mysql_bool_window_result_representation_not_supported_in_phase66": "Keep this Bool window result in check/plan; the current MySQL window path does not establish its required Bool representation.",
    "mysql_window_integer_result_origin_not_supported_in_phase66": "Use a reviewed direct-source Int argument for this MySQL window, or keep the computed argument in check/plan; its result carrier has not been established.",
    "unnest_child_leaf_not_admitted": "Use an admitted Int, Bool or bounded Text collection child for Unnest; wider child types remain outside this execution/emission path.",
    "source_mapping_missing": "Add the selected source's exact module/kind/name selector and actual physical relation to the emission contract.",
    "source_family_mismatch": "Use a dialect and contract target matching the actual selected sources; do not relabel a source from another database family.",
    "source_identifier_unrepresentable": "Map the source to its actual physical relation using identifiers supported by the requested target; do not substitute a different relation.",
    "column_identifier_unrepresentable_or_colliding": "Map each source field to its actual physical column, using distinct target-representable identifiers; do not invent columns or aliases in the contract.",
    "output_label_unrepresentable": "Choose a projection label within the requested target's identifier limits.",
    "validated_decimal_parameters_missing": "Declare this field, or the type alias it uses, as Decimal(p, s) with the precision and scale of its column, such as Decimal(12, 2); a plain Decimal has none to match the contract.",
    "set_row_equivalence_domain_unsupported": "Use Int, Bool, Text, Decimal or Float with exact matching carriers. On MySQL a Float set, a window distribution result included, is limited to UNION ALL, and Timestamp to UNION ALL/DISTINCT; keep other unreviewed set carriers in check --project.",
    "conditional_count_not_admitted_on_target": "MySQL has no conditional count yet; emit with --dialect postgres.",
    "conditional_test_reads_no_field": "Test a field of the member, such as `if o.paid`: a test that reads no field is the same for every row.",
    "group_test_not_admitted_on_target": "MySQL has no group any or all yet; emit with --dialect postgres.",
    "group_test_reads_no_field": "Test a field of the member, such as `any(o.paid for o in group)`: a test that reads no field is the same for every row.",
    "join_shape_not_admitted_in_slice7": "Use the admitted JOIN shape and scalar SELECT projection, or keep this query in check/plan; complex ON, joined LET and WHERE sites remain separately restricted.",
    "scalar_projection_requires_later_slice": "Use an admitted scalar SELECT projection; keep other unsupported expression sites in check/plan.",
    "offset_range_requires_exactly_one_order_key": "Use exactly one reviewed ORDER key for an offset RANGE frame, or keep this frame in check/plan.",
    "offset_range_requires_a_non_null_order_key": "Use a non-null signed-Int ORDER key for an offset RANGE frame; do not declare a nullable source non-null in the contract.",
    "offset_range_requires_a_signed_int_order_key": "Use a signed-Int ORDER key for an offset RANGE frame, or keep the frame in check/plan.",
    "count_distinct_tuple_not_admitted_on_target": "Emit this count_distinct of several columns for PostgreSQL, or keep it in check/plan: a project's MySQL emission has no COUNT(DISTINCT a, b) yet (a single file emits it).",
    "first_last_not_admitted_on_target": "Emit this first or last for PostgreSQL, or keep it in check/plan: this first or last form is not admitted on MySQL yet.",
    "quantile_not_admitted_on_target": "Emit this median or quantile for PostgreSQL, or keep it in check/plan: MySQL has no interpolated percentile.",
    "stddev_int_not_admitted_on_target": "Emit this Int stddev for PostgreSQL, or keep it in check/plan: MySQL computes an integer deviation in DOUBLE, which loses Int accuracy; casting the input does not restore it.",
    "variance_int_not_admitted_on_target": "Emit this Int variance for PostgreSQL, or keep it in check/plan: MySQL computes an integer variance in DOUBLE, which loses Int accuracy; casting the input does not restore it.",
    "pvariance_int_not_admitted_on_target": "Emit this Int pvariance for PostgreSQL, or keep it in check/plan: MySQL computes an integer variance in DOUBLE, which loses Int accuracy; casting the input does not restore it.",
    "pstdev_int_not_admitted_on_target": "Emit this Int pstdev for PostgreSQL, or keep it in check/plan: MySQL computes an integer deviation in DOUBLE, which loses Int accuracy; casting the input does not restore it.",
    "window_aggregate_approved_non_support_on_mysql": "Emit this aggregate window for PostgreSQL, or keep it in check/plan: a project's MySQL aggregate window awaits its real-database differential.",
}
for _details, _action in _GROUPS:
    for _detail in _details:
        assert _detail not in _ACTIONS, _detail
        _ACTIONS[_detail] = _action


def blocker_suggestion(code: str, detail: str, family: str | None) -> str:
    if code not in CODES or family not in {None, "postgres", "mysql"}:
        raise ValueError("invalid blocker suggestion context")
    families = ("postgres", "mysql") if family is None else (family,)
    hints = [_specific_hint(detail, target) for target in families]
    if all(hint is not None for hint in hints):
        if len(set(hints)) == 1:
            return str(hints[0])
        return "; ".join(
            f"{target}: {hint}" for target, hint in zip(families, hints, strict=True)
        )
    if code == "PIE-B1008":
        return "Re-emit from the original checked project and contract. If artifact integrity still fails, report this code and detail; do not edit generated SQL, ranges or requirements."
    if detail in _ACTIONS:
        return _ACTIONS[detail]
    if detail in {
        f"{name}_argument_outside_reviewed_int_domain"
        for name in (
            "sum",
            "avg",
            "count",
            "count_distinct",
            "min",
            "max",
            "stddev",
            "variance",
            "pvariance",
            "pstdev",
            "median",
            "quantile",
            "filtered_count",
            "filtered_sum",
        )
    } | {"group_test_argument_outside_reviewed_bool_domain"}:
        return "Use the aggregate's reviewed direct argument carrier, or keep it in check/plan; do not coerce its input to force emission."
    if detail in {
        f"window_frame_{unit}_approved_non_support_on_{target}"
        for unit in ("rows", "range", "groups")
        for target in ("postgres", "mysql")
    }:
        return "Use a frame unit reviewed for the requested target, or keep this window in check/plan."
    if detail in {
        f"window_frame_exclusion_approved_non_support_on_{target}"
        for target in ("postgres", "mysql")
    }:
        return "Use NO OTHERS or an exclusion reviewed for the requested target, or keep this window in check/plan."
    raise ValueError(f"unclassified blocker suggestion: {code}/{detail}")
