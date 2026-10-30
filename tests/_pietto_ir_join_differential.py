from __future__ import annotations

import argparse
from collections.abc import Mapping
from copy import copy
from dataclasses import asdict, fields as dataclass_fields, replace
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

from _pietto_ir_query_block_differential import _portable_records
from _pietto_ir_project_differential import _relation_value as _base_relation_value
from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_query_block_ir_pure_boundary as pure
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_completion import ProjectEffectiveOutputTerminal
from pietto._project.project_final_outputs import (
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_join_conditions import ProjectJoinCondition
from pietto._project.project_joined_aggregation import (
    ProjectNonConcreteJoinedAggregation,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectNonConcreteJoinedQualify,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteJoinedWindowStage,
    ProjectNonConcreteJoinedWindowStage,
)
from pietto._project.project_ir_joins import ProjectIRNonConcreteJoinRegion
from pietto._project.project_query_block import ProjectNonConcreteQueryBlock
from pietto._project.project_relationship_predicates import (
    ProjectRelationshipPredicateExpression,
)
from pietto._project.project_relationship_uses import (
    ProjectJoinUseIssue,
    ProjectNonConcreteJoinUse,
    ProjectRelationBindingOccurrence,
)
from pietto._project.project_scalar_namespaces import (
    ProjectNonConcreteJoinedNamespaceExpression,
)
from pietto._project.project_scalar_references import ProjectScalarReferenceResolution
from pietto._project.row_expression_type_facts import scalar_field_reference_leaves
from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    current_forward_at_most_one,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_pipeline import build_project_ir_pipeline
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto.ast_nodes import QueryDef
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockTerminal,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    ProjectIRQueryBlockInspectionProduct,
    build_project_query_block_ir_inspection,
    query_project_query_block_outputs,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)

OBSERVATION_FORMAT = "pietto.join-differential.v2"
SEED_ENVIRONMENT = "PIETTO_SLICE15_IRRELEVANT"

PRIMARY_MAIN_SOURCE = """shape CustomerRow:
    id: Int
    customer_key = unique(id)
shape OrderRow:
    id: Int
    customer_id: Int
    product_id: Int
    amount: Int | None
    order_key = unique(id)
shape ReturnRow:
    id: Int
    customer_id: Int
    reason_id: Int
    amount: Int | None
    return_key = unique(id)
source customers: CustomerRow = postgres.table("customers")
source orders: OrderRow = postgres.table("orders")
source returns: ReturnRow = postgres.table("returns")
query orders_by_customer:
    from orders
    group by:
        customer_id
    select:
        customer_id
        total = sum(amount)
        order_count = count()
query orders_by_customer_copy:
    from orders
    group by:
        customer_id
    select:
        customer_id
        total = sum(amount)
query orders_by_customer_product:
    from orders
    group by:
        customer_id
        product_id
    select:
        customer_id
        product_id
        total = sum(amount)
query returns_by_customer:
    from returns
    group by:
        customer_id
    select:
        customer_id
        total = sum(amount)
query returns_by_customer_reason:
    from returns
    group by:
        customer_id
        reason_id
    select:
        customer_id
        reason_id
        return_count = count()
query global_orders:
    from orders
    select:
        total = count()
query global_returns:
    from returns
    select:
        total = count()
relationship customer_orders_raw(customer: CustomerRow, orders: OrderRow):
    customer.id == orders.customer_id
relationship orders_customer_unique_target(orders: OrderRow, customer: CustomerRow):
    orders.customer_id == customer.id
relationship nullable_amounts(orders: OrderRow, returns: ReturnRow):
    orders.amount == returns.amount
relationship composite_raw(orders: OrderRow, returns: ReturnRow):
    orders.customer_id == returns.customer_id and orders.product_id == returns.reason_id
query direct_unique_join:
    from customers
    let coarse_orders = orders_by_customer
    inner join coarse_orders on customers.id == coarse_orders.customer_id
    select:
        id
query explicit_one_join:
    from customers
    let coarse_orders = orders_by_customer
    inner join coarse_orders on customers.id == coarse_orders.customer_id
    select:
        id
query left_one_join:
    from customers
    let coarse_orders = orders_by_customer
    left join coarse_orders on customers.id == coarse_orders.customer_id
    select:
        id
query variant_direct:
    from customers
    let coarse_returns = returns_by_customer
    inner join coarse_returns on customers.id == coarse_returns.customer_id
    select:
        id
query variant_explicit:
    from customers
    let coarse_returns = returns_by_customer
    inner join coarse_returns on customers.id == coarse_returns.customer_id
    select:
        id
query unique_target_inner:
    from orders
    let customer = customers
    inner join customer on orders_customer_unique_target(orders, customer)
    select:
        id
query unique_target_left:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    select:
        id
query fanout_join:
    from customers
    inner join orders on customer_orders_raw(customers, orders)
    select:
        id
query aligned_join:
    from orders_by_customer
    let copy = orders_by_customer_copy
    inner join copy on orders_by_customer.customer_id == copy.customer_id
    select:
        customer_id
query comparable_join:
    from orders_by_customer
    let fine = orders_by_customer_product
    inner join fine on orders_by_customer.customer_id == fine.customer_id
    select:
        customer_id
query chasm_join:
    from customers
    let fine_orders = orders_by_customer_product
    inner join fine_orders on customers.id == fine_orders.customer_id
    let fine_returns = returns_by_customer_reason
    inner join fine_returns on customers.id == fine_returns.customer_id
    select:
        id
query incompatible_join:
    from orders_by_customer_product
    let fine_returns = returns_by_customer_reason
    inner join fine_returns on orders_by_customer_product.customer_id == fine_returns.customer_id
    select:
        customer_id
query reused_join:
    from customers
    let first_orders = orders_by_customer
    inner join first_orders on customers.id == first_orders.customer_id
    let second_orders = orders_by_customer
    inner join second_orders on customers.id == second_orders.customer_id
    select:
        id
query multihop_join:
    from customers
    let coarse_orders = orders_by_customer
    inner join coarse_orders on customers.id == coarse_orders.customer_id
    let coarse_returns = returns_by_customer
    inner join coarse_returns on coarse_orders.customer_id == coarse_returns.customer_id
    select:
        id
query self_fact_join:
    from orders_by_customer
    let parent = orders_by_customer
    left join parent on orders_by_customer.customer_id == parent.customer_id
    select:
        customer_id
query global_join:
    from global_orders
    let counted_returns = global_returns
    inner join counted_returns on global_orders.total == counted_returns.total
    select:
        total
query ambiguous_fact_join:
    from orders_by_customer
    let coarse_returns = returns_by_customer
    inner join coarse_returns on orders_by_customer.customer_id == coarse_returns.customer_id
    select:
        customer_id
query missing_fact_join:
    from orders_by_customer
    let fine_returns = returns_by_customer_reason
    inner join fine_returns
    select:
        customer_id
query bad_relationship_join:
    from customers
    let coarse_returns = returns_by_customer
    inner join coarse_returns on absent_relationship(customers, coarse_returns)
    select:
        id
query bad_role_join:
    from customers
    let coarse_returns = returns_by_customer
    inner join coarse_returns on missing.id == coarse_returns.customer_id
    select:
        id
query nullable_match_join:
    from orders
    let returned = returns
    inner join returned on nullable_amounts(orders, returned)
    select:
        order_id = orders.id
query composite_match_join:
    from orders
    let returned = returns
    inner join returned on composite_raw(orders, returned)
    select:
        order_id = orders.id
query chasm_aggregate_refusal:
    from customers
    let fine_orders = orders_by_customer_product
    inner join fine_orders on customers.id == fine_orders.customer_id
    let fine_returns = returns_by_customer_reason
    inner join fine_returns on customers.id == fine_returns.customer_id
    select:
        orders_total = sum(fine_orders.total)
query predicate_key_inner_outputs:
    from orders
    let customer = customers
    inner join customer on orders_customer_unique_target(orders, customer)
    select:
        order_id = orders.id
        matched_customer_id = customer.id
query predicate_key_left_outputs:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    select:
        order_id = orders.id
        matched_customer_id = customer.id
"""

DISCONNECTED_SOURCE = """shape AuditRow:
    id: Int
source audit_rows: AuditRow = postgres.table("audit_rows")
query audit_result:
    from audit_rows
    select:
        id
"""

PARALLEL_RELATIONSHIP = """relationship customer_returns_coarse_parallel(customer: CustomerRow, returns: ReturnRow):
    customer.id == returns.customer_id
"""

VARIANT_SOURCES = {
    "primary": PRIMARY_MAIN_SOURCE,
    "parallel": PRIMARY_MAIN_SOURCE.replace(
        "query variant_direct:\n",
        PARALLEL_RELATIONSHIP + "query variant_direct:\n",
        1,
    ),
    "no_unique": PRIMARY_MAIN_SOURCE.replace("    customer_key = unique(id)\n", "", 1),
}


def _write_project(root: Path, source: str, *, reverse_creation: bool) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    items = (("main.pietto", source), ("z_disconnected.pietto", DISCONNECTED_SOURCE))
    for name, text in items[::-1] if reverse_creation else items:
        (root / name).write_text(text, encoding="utf-8")
    return root


def _build(
    root: Path, source: str, *, reverse_creation: bool
) -> tuple[
    ProjectSemanticResult,
    ProjectConcreteCompletedSemanticResult,
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockInspectionProduct,
]:
    parsed = project_check.check_project_parse_only(
        _write_project(root, source, reverse_creation=reverse_creation)
    )
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    snapshot = build_project_query_block_ir(completed)
    verified = verify_project_query_block_ir(snapshot)
    assert verified.verified, verified.issues
    bundle = build_project_query_block_ir_analysis_bundle(verified)
    product = build_project_query_block_ir_inspection(bundle)
    assert snapshot.completed is completed
    assert (
        snapshot.base_plan.semantic_facts
        is completed.semantic_result.module_semantic_facts
    )
    assert product.inspection.root is snapshot
    assert product.inspection.analysis_bundle is bundle
    return completed.semantic_result, completed, bundle, product


def _identity_value(identity):
    nominal = identity.identity
    return [
        nominal.module_path,
        identity.module_position,
        identity.declaration_position,
        nominal.namespace.value,
        nominal.declaration_kind.value,
        nominal.declared_name,
    ]


def _owner_value(owner):
    return [owner.identity.module_path, owner.definition.name]


def _span_value(span):
    return [span.path, span.line, span.column, span.end_line, span.end_column]


def _diagnostic_value(diagnostic):
    return [
        diagnostic.code,
        diagnostic.severity.value,
        diagnostic.message,
        _span_value(diagnostic.location),
        diagnostic.suggestion,
    ]


def _factor_value(identity):
    if isinstance(identity, project_grain.ProjectJoinGrainFactorIdentity):
        base = identity.base
        introduction = identity.introduction_use.position
        nulling = [item.position for item in identity.nulling_joins]
        source = (
            None
            if identity.source_factor is None
            else _factor_value(identity.source_factor)
        )
    else:
        base, introduction, nulling, source = identity, None, [], None
    operator = (
        base.operator.position
        if isinstance(base, project_grain.ProjectGroupedGrainFactorIdentity)
        else None
    )
    return [
        base.kind.value,
        _identity_value(base.owner),
        operator,
        introduction,
        nulling,
        source,
    ]


def _relational_value(properties):
    classes = properties.value_classes
    grain = properties.grain
    return {
        "output": properties.output.occurrence.ref.position,
        "fields": [
            [
                field.field_position,
                field.evidence.name,
                field.effective_nullability.value,
            ]
            for field in properties.fields
        ],
        "classes": [
            [member.field_position for member in value.members] for value in classes
        ],
        "keys": [
            [
                [classes.index(value) for value in key.determinants],
                key.strength.value,
                [type(support).__name__ for support in key.supports],
            ]
            for key in properties.keys
        ],
        "fds": [
            [
                [classes.index(value) for value in fact.determinants],
                [classes.index(value) for value in fact.dependents],
                fact.strength.value,
                [type(support).__name__ for support in fact.supports],
            ]
            for fact in properties.fds
        ],
        "grain": {
            "state": grain.state.value,
            "factors": [_factor_value(value.identity) for value in grain.factors],
            "active": [_factor_value(value) for value in grain.active],
            "dependencies": [
                [
                    [_factor_value(value) for value in fact.determinants],
                    [_factor_value(value) for value in fact.dependents],
                ]
                for fact in grain.dependencies
            ],
        },
    }


def _relational_signature(properties):
    classes = properties.value_classes

    def factor(value):
        base = (
            value.base
            if isinstance(value, project_grain.ProjectJoinGrainFactorIdentity)
            else value
        )
        return [
            base.kind.value,
            base.owner.identity.module_path,
            base.owner.identity.declared_name,
            bool(value.nulling_joins)
            if isinstance(value, project_grain.ProjectJoinGrainFactorIdentity)
            else False,
        ]

    return {
        "fields": [
            [field.evidence.name, field.effective_nullability.value]
            for field in properties.fields
        ],
        "classes": [
            [member.field_position for member in value.members] for value in classes
        ],
        "keys": [
            [[classes.index(value) for value in key.determinants], key.strength.value]
            for key in properties.keys
        ],
        "fds": [
            [
                [classes.index(value) for value in fact.determinants],
                [classes.index(value) for value in fact.dependents],
                fact.strength.value,
            ]
            for fact in properties.fds
        ],
        "grain": [
            properties.grain.state.value,
            [factor(value.identity) for value in properties.grain.factors],
            [factor(value) for value in properties.grain.active],
            [
                [
                    [factor(value) for value in fact.determinants],
                    [factor(value) for value in fact.dependents],
                ]
                for fact in properties.grain.dependencies
            ],
        ],
    }


def _binding_value(binding):
    if binding is None:
        return None
    return [
        binding.identity.binding_position,
        binding.name,
        binding.relation_name,
        binding.state.value,
    ]


def _condition_field_value(field):
    return [
        _binding_value(field.binding),
        field.input_field.field_position,
        field.input_field.evidence.name,
        field.nullability.value,
    ]


def _call_value(call):
    return {
        "template": call.template.declaration.name,
        "template_span": _span_value(call.template.declaration.span),
        "call_span": _span_value(call.call.span),
        "ordinal": call.ordinal,
        "arguments": [
            [
                argument.parameter.name,
                argument.relation.name,
                argument.shape.name,
                _span_value(argument.shape.span),
                _span_value(argument.occurrence.span),
            ]
            for argument in call.arguments
        ],
    }


def _condition_value(condition):
    return {
        "owner": _owner_value(condition.use.owner),
        "join_position": condition.use.identity.join_position,
        "clause": asdict(condition.use.clause),
        "mode": condition.mode,
        "state": condition.state.value,
        "ready": condition.ready,
        "bindings": [
            _binding_value(binding) for binding in condition.environment.bindings
        ],
        "references": [
            [
                reference.position,
                reference.state.value,
                [_binding_value(binding) for binding in reference.binding_candidates],
                [_condition_field_value(field) for field in reference.candidates],
                asdict(reference.expression),
            ]
            for reference in condition.references
        ],
        "conjuncts": [
            [
                position,
                type(conjunct).__name__,
                asdict(conjunct),
                [
                    reference.position
                    for reference in condition.references
                    if any(
                        reference.expression is leaf
                        for leaf in scalar_field_reference_leaves(conjunct)
                    )
                ],
                [
                    _call_value(call)
                    for call in (
                        ()
                        if condition.environment.predicate_expression is None
                        else condition.environment.predicate_expression.calls
                    )
                    if any(conjunct is item for item in call.mandatory_equalities)
                ],
            ]
            for position, conjunct in enumerate(condition.conjuncts)
        ],
        "equalities": [
            [
                equality.conjunct_position,
                _condition_field_value(equality.left),
                _condition_field_value(equality.right),
                [_call_value(call) for call in equality.calls],
            ]
            for equality in condition.mandatory_equalities
        ],
        "key_matches": [
            [
                _binding_value(proof.binding),
                proof.properties.output.occurrence.ref.position,
                [
                    proof.properties.value_classes.index(value)
                    for value in proof.key.determinants
                ],
                proof.key.strength.value,
                proof.minimum.value,
                proof.maximum.value,
                [equality.conjunct_position for equality in proof.equalities],
            ]
            for proof in condition.key_matches
        ],
        "null_rejections": [
            [
                item.conjunct_position,
                item.reference.position,
                _condition_field_value(item.field),
                item.reason,
            ]
            for item in condition.null_rejections
        ],
        "diagnostics": [_diagnostic_value(item) for item in condition.diagnostics],
    }


def _region(completed, name):
    matches = tuple(
        region
        for region in completed.effective_outputs.current_regions
        if region.ledger.owner.definition.name == name
    )
    assert len(matches) == 1, name
    return matches[0]


def _entry(snapshot, name):
    matches = tuple(
        entry for entry in snapshot.entries if entry.owner.definition.name == name
    )
    assert len(matches) == 1, name
    return matches[0]


def _region_value(region):
    joins = []
    for position, join in enumerate(region.joins):
        assert isinstance(join, ProjectCurrentBinaryJoin)
        assert join.condition is region.operative[position]
        if position:
            assert join.left_input.output is region.joins[position - 1].output
        assert all(
            field.evidence is origin.evidence
            for field, (_, origin) in zip(
                join.output.row_shape.fields, join.field_inputs, strict=True
            )
        )
        joins.append(
            {
                "position": join.use.identity.join_position,
                "kind": join.kind.value,
                "node": join.node.ref.position,
                "inputs": [
                    [
                        use.ref.position,
                        use.output.ref.position,
                        use.slot.ref.position,
                        _identity_value(use.output.producer.anchor.identity),
                    ]
                    for use in join.input_uses
                ],
                "left": _relational_value(join.left_input),
                "right": _relational_value(join.right_input),
                "condition": _condition_value(join.condition),
                "forward_at_most_one": current_forward_at_most_one(join.condition),
                "output": _relational_value(join.properties.relational),
                "field_inputs": [
                    [
                        _binding_value(binding),
                        member.field_position,
                        member.evidence.name,
                    ]
                    for binding, member in join.field_inputs
                ],
                "nulling": [
                    [
                        field.introduction_use.ref.position,
                        [ref.position for ref in field.nulling_joins],
                    ]
                    for field in join.output.row_shape.fields
                ],
                "null_extension": type(join.properties.null_extension).__name__,
                "ordering": type(join.properties.ordering).__name__,
            }
        )
    assert joins
    return {
        "owner": _owner_value(region.ledger.owner),
        "joins": joins,
        "binding_introductions": [
            use.ref.position for use in region.binding_introductions
        ],
        # No JOIN is a relationship path with hidden hops; the reviewed
        # observation keeps the empty list.
        "hidden_introductions": [],
    }


def _region_signature(region):
    return [
        [
            join.kind.value,
            current_forward_at_most_one(join.condition),
            _relational_signature(join.left_input),
            _relational_signature(join.right_input),
            _relational_signature(join.properties.relational),
            type(join.properties.null_extension).__name__,
            type(join.properties.ordering).__name__,
        ]
        for join in region.joins
    ]


def _template_inventory(semantic):
    result = []
    for module in semantic.modules:
        assert module.parsed_input is not None
        for position, template in enumerate(
            module.parsed_input.script.relationship_templates
        ):
            result.append(
                [
                    module.path,
                    position,
                    template.name,
                    [
                        [parameter.name, parameter.shape_name]
                        for parameter in template.parameters
                    ],
                    _span_value(template.span),
                    [type(template.body).__name__, asdict(template.body)],
                ]
            )
    return result


def _aggregation_values(completed):
    values = []
    for tail_position, tail in enumerate(completed.effective_outputs.current_tails):
        for result in tail.window_set.aggregation_set.results:
            values.append(
                {
                    "tail": tail_position,
                    "owner": _owner_value(result.input_filter.entry.owner),
                    "variant": type(result).__name__,
                    "mode": None if result.mode is None else result.mode.value,
                    "reason": None
                    if not hasattr(result, "reason")
                    else result.reason.value,
                    "diagnostics": [
                        _diagnostic_value(item) for item in result.diagnostics
                    ],
                    "linkages": [
                        {
                            "ordinal": link.aggregate.selected_output_ordinal,
                            "function": link.aggregate.function_name,
                            "arguments": [
                                _factor_value(value) for value in link.argument_factors
                            ],
                            "group_protection": [
                                _factor_value(value)
                                for value in link.group_protection_factors
                            ],
                            "computed_keys": [
                                _factor_value(value)
                                for value in link.computed_key_factors
                            ],
                            "seed": [
                                _factor_value(value)
                                for value in link.combined_seed.factors
                            ],
                            "closure": [
                                _factor_value(value) for value in link.closure.factors
                            ],
                            "context": [
                                _factor_value(value)
                                for value in link.contextual_grain.factors
                            ],
                            "final_grain": [
                                _factor_value(value)
                                for value in link.final_grain.active
                            ],
                            "comparison": link.final_comparison.status.value,
                            "exposures": [
                                [
                                    item.join.node.ref.position,
                                    [
                                        _factor_value(value)
                                        for value in item.factor_additions
                                    ],
                                ]
                                for item in link.multiplicity_exposures
                            ],
                            "risks": [risk.value for risk in link.multiplicity_risks],
                            "requirements": [
                                requirement.value for requirement in link.requirements
                            ],
                        }
                        for link in result.grain_linkages
                    ],
                    "pairs": [
                        {
                            "ordinals": [
                                pair.left.aggregate.selected_output_ordinal,
                                pair.right.aggregate.selected_output_ordinal,
                            ],
                            "structural": pair.structural.value,
                            "comparison": pair.grain_comparison.status.value,
                            "common_grain": pair.common_grain.status.value,
                            "candidates": [
                                [
                                    [
                                        _factor_value(value)
                                        for value in candidate.candidate.factors.factors
                                    ],
                                    [
                                        authority.kind.value
                                        for authority in candidate.candidate.authorities
                                    ],
                                ]
                                for candidate in pair.common_grain.candidates
                            ],
                            "chasm_candidates": [
                                pair.common_grain.candidates.index(candidate)
                                for candidate in pair.chasm_candidates
                            ],
                            "risks": [risk.value for risk in pair.multiplicity_risks],
                            "requirements": [
                                requirement.value for requirement in pair.requirements
                            ],
                        }
                        for pair in result.pair_linkages
                    ],
                }
            )
    return values


def _input_scope_values(completed):
    values = []
    for scope in completed.effective_outputs.input_scopes:
        bindings = []
        for item in scope.bindings:
            authority = item.authority
            if authority is None:
                bindings.append(
                    [_binding_value(item.binding), None, type(item.blocker).__name__]
                )
            else:
                sites = [
                    index
                    for index, entry in enumerate(scope.available_entries)
                    if entry is authority.entry
                ]
                assert len(sites) == 1
                assert (
                    item.dependency is not None
                    and item.dependency.target is authority.owner
                )
                bindings.append(
                    [
                        _binding_value(item.binding),
                        _owner_value(authority.owner),
                        sites,
                        [
                            [field.field_position, field.evidence.name]
                            for field in authority.fields
                        ],
                    ]
                )
        values.append([_owner_value(scope.ledger.owner), bindings])
    return values


# Closed causal readers reject new fields until their authority is reviewed.
_TERMINAL_FIELDS = {
    ProjectEffectiveOutputCompletionTerminal: "owner base_entry reason blocker dependencies joined_qualify replay_root upstream_entry diagnostics current_region current_inputs output",
    ProjectEffectiveOutputTerminal: "owner fragment reason dependencies joined_completion resolution pending_dependencies pending_entries cycle_blocker output",
    ProjectNonConcreteQueryBlock: "compilation_mode owner_bridge reason relation_fragment verification join_region state row_source",
    ProjectIRNonConcreteJoinRegion: "ledger starting_allocation ending_allocation state blockers",
    ProjectNonConcreteJoinUse: "identity owner clause target_binding state issues",
    ProjectJoinUseIssue: "kind state site causes",
    ProjectRelationBindingOccurrence: "identity owner site name relation_name state target output relation_issues",
    ProjectRelationshipPredicateExpression: "owner context authored expression calls argument_bindings diagnostics failed_calls any_expressions any_bindings parent",
    ProjectJoinCondition: "root ledger use inputs environment mode scope expression conjuncts references mandatory_equalities match_inputs key_matches value_type value_types state ready diagnostics unavailable_diagnostics null_rejections",
    ProjectNonConcreteJoinedNamespaceExpression: "namespace expression resolutions reason blocking_resolutions kernel_value_type value_types diagnostics existence_values predicate_expression value_type",
    ProjectConcreteJoinedQualify: "window_set window_stage kind qualify_clause references hidden_computations predicate_value_type value_types diagnostics retention_effects preservation post_qualify",
    ProjectNonConcreteJoinedQualify: "window_set window_stage reason qualify_clause references hidden_attempts kernel_value_type value_types diagnostics preservation post_qualify",
    ProjectConcreteJoinedWindowStage: "aggregation_set input_aggregation kind named_namespace pre_window computations selected_results post_window preservation diagnostics",
    ProjectNonConcreteJoinedWindowStage: "aggregation_set input_aggregation reason pre_window named_failure attempts diagnostics post_window selected_results",
    ProjectNonConcreteJoinedAggregation: "filter_set input_filter reason mode group_key_results aggregate_results stage_outputs selected_output_issues group_protections grain_linkages pair_linkages grain_blocker satisfying diagnostics post_aggregate",
}


def _require_observed_fields(value, expected):
    actual = tuple(field.name for field in dataclass_fields(value))
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise ValueError(f"Unreviewed JOIN blocker fields: {type(value).__name__}")


def _require_unused(value, *, absent=(), empty=()):
    for name in absent:
        if getattr(value, name) is not None:
            raise ValueError(
                f"Unreviewed JOIN blocker state: {type(value).__name__}.{name}"
            )
    for name in empty:
        item = getattr(value, name)
        if not (type(item) is tuple or isinstance(item, Mapping)) or item:
            raise ValueError(
                f"Unreviewed JOIN blocker state: {type(value).__name__}.{name}"
            )


def _authority_site(value, entries):
    positions = [i for i, item in enumerate(entries) if item is value]
    if len(positions) != 1:
        raise ValueError("JOIN blocker lost one exact retained authority.")
    return positions[0]


def _tail_authorities(completed):
    result = []
    for tail_position, tail in enumerate(completed.effective_outputs.current_tails):
        windows = tail.window_set
        aggregates = windows.aggregation_set
        for position, (qualify, window, aggregate) in enumerate(
            zip(tail.results, windows.results, aggregates.results, strict=True)
        ):
            assert qualify.window_set is windows and qualify.window_stage is window
            assert (
                window.aggregation_set is aggregates
                and window.input_aggregation is aggregate
            )
            result.append((tail_position, position, qualify, window, aggregate))
    return tuple(result)


def _terminal_graph(root, completed):
    # The tuple edges retain every occurrence, including shared and cyclic causes.
    retained = []
    nodes = []
    aggregations = tuple(
        result
        for tail in completed.effective_outputs.current_tails
        for result in tail.window_set.aggregation_set.results
    )

    tails = _tail_authorities(completed)
    completion = completed.effective_outputs.base

    def tail_site(value, column):
        sites = [row for row in tails if row[column] is value]
        if len(sites) != 1:
            raise ValueError("JOIN blocker lost one exact current tail.")
        return sites[0]

    def visit(value):
        if value is None:
            return None
        for position, item in enumerate(retained):
            if value is item:
                return position
        position = len(retained)
        retained.append(value)
        node: dict[str, object] = {"variant": type(value).__name__}
        nodes.append(node)
        if type(value) is not tuple:
            expected = _TERMINAL_FIELDS.get(type(value))
            if expected is None:
                raise TypeError(f"Unreviewed JOIN blocker: {type(value).__name__}")
            _require_observed_fields(value, expected.split())
        if type(value) is tuple:
            node["items"] = [visit(item) for item in value]
        elif type(value) is ProjectEffectiveOutputCompletionTerminal:
            _require_unused(value, absent=("replay_root", "upstream_entry", "output"))
            assert value.dependencies is value.base_entry.dependencies
            regions = completed.effective_outputs.current_regions
            scopes = completed.effective_outputs.input_scopes
            region_sites = [
                i for i, item in enumerate(regions) if item is value.current_region
            ]
            scope_sites = [
                i for i, item in enumerate(scopes) if item is value.current_inputs
            ]
            assert len(region_sites) == (value.current_region is not None)
            assert len(scope_sites) == (value.current_inputs is not None)
            assert value.base_entry.owner is value.owner
            node.update(
                owner=_owner_value(value.owner),
                identity=_identity_value(value.owner),
                base_owner=_identity_value(value.base_entry.owner),
                base_entry_site=_authority_site(value.base_entry, completion.entries),
                dependencies=[
                    _authority_site(item, completion.dependencies)
                    for item in value.dependencies
                ],
                joined_qualify=visit(value.joined_qualify),
                region_sites=region_sites,
                input_scope_sites=scope_sites,
                reason=value.reason.value,
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                blocker=visit(value.blocker),
            )
        elif type(value) is ProjectEffectiveOutputTerminal:
            _require_unused(value, absent=("resolution", "output"))
            facts = value.fragment.semantic_facts
            assert facts.owner is value.owner
            node.update(
                owner=_owner_value(value.owner),
                reason=value.reason.value,
                semantic_state=[facts.state.status.value, facts.state.reason.value],
                fragment_site=_authority_site(
                    value.fragment, completion.plan.fragments
                ),
                dependencies=[
                    _authority_site(item, completion.dependencies)
                    for item in value.dependencies
                ],
                pending_dependencies=[
                    _authority_site(item, completion.dependencies)
                    for item in value.pending_dependencies
                ],
                helper_diagnostics=[
                    _diagnostic_value(item) for item in facts.helper_diagnostics
                ],
                joined_completion=visit(value.joined_completion),
                pending_entries=visit(value.pending_entries),
                cycle_blocker=visit(value.cycle_blocker),
            )
        elif type(value) is ProjectNonConcreteQueryBlock:
            _require_unused(value, absent=("relation_fragment", "row_source"))
            assert value.verification is not None
            assert value.verification is completion.verification
            node.update(
                compilation_mode=value.compilation_mode.value,
                verification=value.verification.status.value,
                owner=_owner_value(value.owner_bridge.owner),
                reason=value.reason.value,
                state=value.state.value,
                join_region=visit(value.join_region),
            )
        elif type(value) is ProjectIRNonConcreteJoinRegion:
            node.update(
                region_site=_authority_site(
                    value, completion.verification.root.join_regions.regions
                ),
                ledger_site=_authority_site(
                    value.ledger, completed.roots.join_conditions.uses.ledgers
                ),
                owner=_owner_value(value.ledger.owner),
                state=value.state.value,
                blockers=visit(value.blockers),
                zero_allocation=value.starting_allocation is value.ending_allocation,
            )
        elif type(value) is ProjectNonConcreteJoinUse:
            node.update(
                owner=_owner_value(value.owner),
                join_position=value.identity.join_position,
                state=value.state.value,
                clause=asdict(value.clause),
                # No JOIN use has a source binding, steps, a direct result or
                # a path; the reviewed observation keeps their empty values.
                source=None,
                target=_binding_value(value.target_binding),
                source_ref=None,
                target_ref=visit(value.target_binding),
                issues=visit(value.issues),
                steps=visit(()),
                direct_result=None,
                path=None,
            )
        elif type(value) is ProjectJoinUseIssue:
            node.update(
                kind=value.kind.value,
                state=value.state.value,
                site=asdict(value.site),
                causes=visit(value.causes),
            )
        elif type(value) is ProjectRelationBindingOccurrence:
            node.update(
                owner=_owner_value(value.owner),
                binding=_binding_value(value),
                site=asdict(value.site),
                target=None
                if value.target is None
                else _identity_value(value.target.target_occurrence),
                output=None
                if value.output is None
                else _relational_value(value.output),
                relation_issues=visit(value.relation_issues),
            )
        elif type(value) is ProjectJoinCondition:
            _require_unused(value.environment, empty=("existence_values",))
            predicate = value.environment.predicate_expression
            assert predicate is not None
            assert predicate.owner is value.use.owner
            assert predicate.context is value.use.clause.on_clause
            assert value.use.clause.on_clause is not None
            assert predicate.authored is value.use.clause.on_clause.expression
            assert predicate.expression is value.expression
            assert value.mode == "M3" and not value.ready
            # Its unavailable-input diagnostics are some of its diagnostics.
            assert all(
                any(item is diagnostic for diagnostic in value.diagnostics)
                for item in value.unavailable_diagnostics
            )
            assert value.environment.root is value.root
            assert value.environment.ledger is value.ledger
            assert (
                value.environment.use is value.use
                and value.environment.inputs is value.inputs
            )
            assert value.inputs is not None
            node.update(
                condition=_condition_value(value),
                predicate_expression=visit(predicate),
                condition_site=_authority_site(
                    value, completed.roots.join_conditions.entries
                ),
                ledger_site=_authority_site(value.ledger, value.root.uses.ledgers),
                input_scope_site=_authority_site(
                    value.inputs.scope, completed.effective_outputs.input_scopes
                ),
                scope=None if value.scope is None else value.scope.value,
                expression=None
                if value.expression is None
                else asdict(value.expression),
                match_inputs=[
                    [_binding_value(binding), _relational_value(properties)]
                    for binding, properties in value.match_inputs
                ],
                value_type=None
                if value.value_type is None
                else asdict(value.value_type),
                value_types=[
                    [asdict(expression), asdict(value_type)]
                    for expression, value_type in value.value_types.items()
                ],
            )
        elif type(value) is ProjectRelationshipPredicateExpression:
            # No reviewed case rejects a declared call; an empty `failed_calls`
            # adds nothing to the reviewed observation bytes.
            _require_unused(
                value,
                absent=("parent",),
                empty=(
                    "calls",
                    "argument_bindings",
                    "failed_calls",
                    "any_expressions",
                    "any_bindings",
                ),
            )
            node.update(
                owner=_owner_value(value.owner),
                predicate_site=_authority_site(
                    value, completed.roots.join_conditions.predicate_expressions
                ),
                context=asdict(value.context),
                authored=asdict(value.authored),
                expression=asdict(value.expression),
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                calls=[],
                argument_bindings=[],
                any_expressions=[],
                any_bindings=[],
                parent=None,
            )
        elif type(value) is ProjectNonConcreteJoinedNamespaceExpression:
            _require_unused(
                value,
                absent=("kernel_value_type", "predicate_expression", "value_type"),
                empty=("value_types", "existence_values"),
            )
            environment = value.namespace.binding_environment
            resolutions = []
            for resolution in value.resolutions:
                if type(resolution) is not ProjectScalarReferenceResolution:
                    raise TypeError("JOIN review requires an exact scalar resolution.")
                candidates = []
                for candidate in resolution.candidates:
                    bindings = [
                        binding
                        for binding in environment.bindings
                        if any(candidate is field for field in binding.fields)
                    ]
                    assert len(bindings) == 1
                    source = candidate.source_field
                    if type(source) is not ProjectIRJoinedRowField:
                        raise TypeError("JOIN blocker candidate lost its joined field.")
                    candidates.append(
                        {
                            "position": candidate.position,
                            "name": candidate.evidence.name,
                            "binding": _binding_value(bindings[0].binding),
                            "introduction": source.introduction_use.ref.position,
                            "nulling": [ref.position for ref in source.nulling_joins],
                            "nullability": source.effective_nullability.value,
                        }
                    )
                resolutions.append(
                    {
                        "reference": asdict(resolution.reference.expression),
                        "status": resolution.status.value,
                        "candidates": candidates,
                        "target": None
                        if resolution.target is None
                        else resolution.candidates.index(resolution.target),
                    }
                )
            node.update(
                owner=_owner_value(environment.ledger.owner),
                namespace_stage=value.namespace.stage.value,
                region_site=_authority_site(
                    environment.region, completed.effective_outputs.current_regions
                ),
                reason=value.reason.value,
                expression=asdict(value.expression),
                resolutions=resolutions,
                blocking_resolutions=[
                    value.resolutions.index(item) for item in value.blocking_resolutions
                ],
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
            )
        elif type(value) is ProjectConcreteJoinedQualify:
            _require_unused(
                value,
                absent=("qualify_clause", "predicate_value_type"),
                empty=(
                    "references",
                    "hidden_computations",
                    "value_types",
                    "retention_effects",
                ),
            )
            if value.kind.value != "absent":
                raise ValueError("JOIN review requires an absent concrete QUALIFY.")
            row = tail_site(value, 2)
            window = value.window_stage
            _require_observed_fields(
                window, _TERMINAL_FIELDS[ProjectConcreteJoinedWindowStage].split()
            )
            _require_unused(window, empty=("computations", "selected_results"))
            if window.kind.value != "absent":
                raise ValueError(
                    "JOIN review requires an absent concrete window stage."
                )
            assert window.pre_window.aggregation is row[4]
            assert window.post_window.pre_window is window.pre_window
            assert window.post_window.selected_results is window.selected_results
            assert window.preservation.aggregation is row[4]
            assert (
                window.named_namespace.definition
                is row[4].input_filter.entry.owner.definition
            )
            assert (
                window.named_namespace.query_block
                is row[
                    4
                ].input_filter.namespace.binding_environment.scalar_environment.query_block.owner_bridge.query_block
            )
            _require_unused(
                window.named_namespace,
                empty=("declarations", "templates", "resolution_order"),
            )
            witness = value.preservation
            post = value.post_qualify
            assert witness.window_stage is window
            assert witness.window_preservation is window.preservation
            assert (
                witness.input_filter_preservation
                is window.preservation.input_filter_preservation
            )
            assert witness.selected_results is window.selected_results
            assert post.window_stage is window and post.preservation is witness
            assert (
                post.post_window is window.post_window
                and post.selected_results is window.selected_results
            )
            node.update(
                owner=_owner_value(row[4].input_filter.entry.owner),
                tail_site=list(row[:2]),
                window_variant=type(window).__name__,
                window_kind=window.kind.value,
                aggregation=_authority_site(row[4], aggregations),
                kind=value.kind.value,
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                window_diagnostics=[
                    _diagnostic_value(item) for item in window.diagnostics
                ],
                preservation=[
                    witness.filters_rows,
                    witness.multiplicity.value,
                    witness.establishes_relation_order,
                ],
            )
        elif type(value) is ProjectNonConcreteJoinedQualify:
            _require_unused(
                value,
                absent=(
                    "qualify_clause",
                    "kernel_value_type",
                    "preservation",
                    "post_qualify",
                ),
                empty=("references", "value_types"),
            )
            row = tail_site(value, 2)
            node.update(
                owner=_owner_value(row[4].input_filter.entry.owner),
                tail_site=list(row[:2]),
                reason=value.reason.value,
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                window_stage=visit(value.window_stage),
                hidden_attempts=visit(value.hidden_attempts),
            )
        elif type(value) is ProjectNonConcreteJoinedWindowStage:
            _require_unused(
                value, absent=("pre_window", "post_window"), empty=("selected_results",)
            )
            row = tail_site(value, 3)
            node.update(
                tail_site=list(row[:2]),
                reason=value.reason.value,
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                input_aggregation=visit(value.input_aggregation),
                attempts=visit(value.attempts),
                named_failure=visit(value.named_failure),
            )
        elif type(value) is ProjectNonConcreteJoinedAggregation:
            _require_unused(
                value,
                absent=("grain_blocker", "post_aggregate"),
                empty=("group_key_results", "group_protections"),
            )
            row = tail_site(value, 4)
            assert value.filter_set is row[3].aggregation_set.filter_set
            assert value.input_filter is value.filter_set.results[row[1]]
            definition = value.input_filter.entry.owner.definition
            assert type(definition) is QueryDef
            if value.satisfying is not None or definition.satisfying_clause is not None:
                raise ValueError("Unreviewed JOIN blocker satisfying authority.")
            aggregate_sites = [
                [
                    i
                    for i, link in enumerate(value.grain_linkages)
                    if link.aggregate is aggregate
                ]
                for aggregate in value.aggregate_results
            ]
            assert all(len(sites) == 1 for sites in aggregate_sites)
            assert len(aggregate_sites) == len(value.grain_linkages)
            for item in value.stage_outputs:
                assert item.input_filter is value.input_filter
                assert (
                    item.item is definition.select_items[item.selected_output_ordinal]
                )
                _require_unused(item, absent=("group_key",))
                assert item.aggregate is not None
                _authority_site(item.aggregate, value.aggregate_results)
            sites = [i for i, item in enumerate(aggregations) if item is value]
            assert len(sites) == 1
            node.update(
                reason=value.reason.value,
                diagnostics=[_diagnostic_value(item) for item in value.diagnostics],
                aggregation=sites[0],
                tail_site=list(row[:2]),
                mode=None if value.mode is None else value.mode.value,
                aggregate_result_linkages=aggregate_sites,
                stage_outputs=[
                    [
                        item.selected_output_ordinal,
                        item.output_name,
                        item.role.value,
                        asdict(item.value_type),
                        asdict(item.item),
                        _authority_site(item.aggregate, value.aggregate_results),
                    ]
                    for item in value.stage_outputs
                ],
                pair_linkages=list(range(len(value.pair_linkages))),
                selected_output_issues=visit(value.selected_output_issues),
            )
        else:
            raise TypeError(f"Unreviewed JOIN blocker: {type(value).__name__}")
        return position

    root_position = visit(root)
    return {"root": root_position, "nodes": nodes}


def _analysis_observation(completed, bundle, product):
    snapshot = bundle.verification.root
    assert product.inspection.root is snapshot
    entries = []
    for entry in snapshot.entries:
        record = {
            "owner": _owner_value(entry.owner),
            "identity": _identity_value(entry.owner),
            "variant": type(entry).__name__,
        }
        if isinstance(entry, ProjectIRQueryBlockTerminal):
            sites = [
                index
                for index, blocker in enumerate(product.inspection.terminal_blockers)
                if blocker is entry.blocker
            ]
            assert sites
            record.update(
                reason=entry.reason.value,
                blocker_kind=type(entry.blocker).__name__,
                blocker_sites=sites,
                zero_allocation=entry.starting_allocation is entry.ending_allocation,
                semantic_terminal=_terminal_graph(entry.blocker, completed),
                owner_diagnostic_sites=[
                    index
                    for index, diagnostic in enumerate(completed.diagnostics)
                    if diagnostic.location.path == entry.owner.identity.module_path
                    and entry.owner.definition.span.line
                    <= diagnostic.location.line
                    <= entry.owner.definition.span.end_line
                ],
            )
        else:
            record.update(
                output=entry.active_output.occurrence.ref.position,
                properties=_relational_value(entry.active_properties.relational),
                multiplicity=entry.active_properties.multiplicity.value,
                ordering=None
                if entry.active_properties.ordering is None
                else type(entry.active_properties.ordering).__name__,
                cardinality=None
                if entry.active_properties.cardinality is None
                else type(entry.active_properties.cardinality).__name__,
                effect=[
                    entry.active_properties.effect.determinism.value,
                    entry.active_properties.effect.error_behavior.value,
                    entry.active_properties.effect.side_effects.value,
                    entry.active_properties.effect.evaluation_count.value,
                ],
            )
        entries.append(record)
    regions = completed.effective_outputs.current_regions
    assert regions
    return {
        "templates": _template_inventory(completed.semantic_result),
        "owners": entries,
        "dependencies": [
            [
                _owner_value(item.consumer),
                _owner_value(item.target),
                item.dependency_ordinal,
                type(item.evidence).__name__,
            ]
            for item in snapshot.dependencies
        ],
        "schedule": [_owner_value(owner) for owner in snapshot.schedule],
        "conditions": [
            _condition_value(item) for item in completed.roots.join_conditions.entries
        ],
        "regions": [_region_value(region) for region in regions],
        "input_scopes": _input_scope_values(completed),
        "readiness": [
            [_owner_value(region.ledger.owner), type(ready).__name__]
            for region, ready in zip(
                regions, completed.effective_outputs.current_readiness, strict=True
            )
        ],
        "tails": [
            {
                "site": list(row[:2]),
                "owner": _owner_value(row[4].input_filter.entry.owner),
                "qualify": type(row[2]).__name__,
                "window": type(row[3]).__name__,
                "aggregation": position,
            }
            for position, row in enumerate(_tail_authorities(completed))
        ],
        "aggregations": _aggregation_values(completed),
        "diagnostics": [_diagnostic_value(item) for item in completed.diagnostics],
        "verification": [
            bundle.verification.status.value,
            [item.kind.value for item in bundle.verification.issues],
        ],
        "portable_records": _portable_records(product.document),
        "canonical_bytes": product.canonical_bytes.decode("utf-8"),
    }


def _allocation(coordinates=(0, 0, 0, 0)):
    node, output, slot, use = coordinates
    return ProjectIRAllocationState(
        scope=ProjectIRSnapshotScope(),
        next_plan_node_position=node,
        next_output_value_position=output,
        next_input_slot_position=slot,
        next_use_position=use,
    )


def _shifted_base(semantic):
    normal = build_project_ir_pipeline(
        semantic_result=semantic, allocation=_allocation()
    )
    shifted = build_project_ir_pipeline(
        semantic_result=semantic, allocation=_allocation((7, 11, 5, 5))
    )
    assert normal.canonical_bytes is not None and shifted.canonical_bytes is not None
    left, right = (
        normal.project_plan.structural_stage,
        shifted.project_plan.structural_stage,
    )
    assert left.scope is not right.scope
    assert left.nodes[0].ref != right.nodes[0].ref
    assert normal.canonical_bytes != shifted.canonical_bytes

    def semantics(result):
        return [
            [
                _base_relation_value(fragment),
                [operator.kind.value for operator in fragment.logical_stage.operators],
            ]
            for fragment in result.project_plan.fragments
        ]

    normal_semantic, shifted_semantic = semantics(normal), semantics(shifted)
    assert normal_semantic == shifted_semantic
    for before, after in zip(
        normal.project_plan.fragments, shifted.project_plan.fragments, strict=True
    ):
        assert before.semantic_facts is after.semantic_facts
        assert all(
            left.evidence is right.evidence
            for left, right in zip(
                before.logical_stage.operators,
                after.logical_stage.operators,
                strict=True,
            )
        )

    def first(stage):
        return [
            stage.nodes[0].ref.position,
            stage.outputs[0].ref.position,
            stage.input_slots[0].ref.position,
            stage.uses[0].ref.position,
        ]

    return {
        "kind": "base_plan_allocation",
        "normal_semantic": normal_semantic,
        "semantic": shifted_semantic,
        "starting_coordinates": [7, 11, 5, 5],
        "normal_first_coordinates": first(left),
        "first_coordinates": first(right),
        "normal_canonical_bytes": normal.canonical_bytes.decode("utf-8"),
        "canonical_bytes": shifted.canonical_bytes.decode("utf-8"),
        "independent_scopes": True,
        "verification": [
            normal.verification.status.value,
            shifted.verification.status.value,
        ],
    }


def _metamorphic_observation(primary, parallel, no_unique):
    direct = _region(primary, "direct_unique_join")
    explicit = _region(primary, "explicit_one_join")
    assert _region_signature(direct) == _region_signature(explicit)
    assert direct.joins[0].condition is not explicit.joins[0].condition
    assert direct.joins[0].input_uses[1] is not explicit.joins[0].input_uses[1]
    before = {
        region.ledger.owner.definition.name: _region_signature(region)
        for region in primary.effective_outputs.current_regions
    }
    after = {
        region.ledger.owner.definition.name: _region_signature(region)
        for region in parallel.effective_outputs.current_regions
    }
    assert before == after
    original = _region(primary, "unique_target_inner").joins[0]
    removed = _region(no_unique, "unique_target_inner").joins[0]
    unique_transition = [
        current_forward_at_most_one(original.condition),
        current_forward_at_most_one(removed.condition),
    ]
    assert unique_transition == [True, False]
    multi = _region(primary, "multihop_join")
    assert len(multi.joins) == 2
    assert multi.joins[1].left_input.output is multi.joins[0].output
    reused = _region(primary, "reused_join")
    assert len(reused.joins) == 2
    assert reused.input_scope is not None
    assert reused.input_scope.bindings[1].authority is not None
    assert reused.input_scope.bindings[2].authority is not None
    assert (
        reused.input_scope.bindings[1].authority.entry
        is reused.input_scope.bindings[2].authority.entry
    )
    assert reused.joins[0].input_uses[1] is not reused.joins[1].input_uses[1]
    self_region = _region(primary, "self_fact_join")
    self_join = self_region.joins[0]
    assert self_region.input_scope is not None
    assert self_region.input_scope.bindings[0].authority is not None
    assert self_region.input_scope.bindings[1].authority is not None
    assert (
        self_region.input_scope.bindings[0].authority.entry
        is self_region.input_scope.bindings[1].authority.entry
    )
    assert self_join.input_uses[0] is not self_join.input_uses[1]
    nullable = _region(primary, "nullable_match_join").joins[0].condition
    composite = _region(primary, "composite_match_join").joins[0].condition
    assert len(nullable.mandatory_equalities) == 1
    assert len(composite.mandatory_equalities) == 2
    assert all(
        equality.calls
        for equality in (
            *nullable.mandatory_equalities,
            *composite.mandatory_equalities,
        )
    )
    return {
        "independent_explicit_joins": [
            _region_signature(direct),
            _region_signature(explicit),
            True,
            True,
        ],
        "parallel_unused_template": {
            "selected_regions_unchanged": before == after,
            "primary_templates": len(_template_inventory(primary.semantic_result)),
            "parallel_templates": len(_template_inventory(parallel.semantic_result)),
        },
        "unique_transition": [
            unique_transition,
            _relational_value(original.properties.relational),
            _relational_value(removed.properties.relational),
        ],
        "inner_vs_left": [
            _region_signature(explicit),
            _region_signature(_region(primary, "left_one_join")),
        ],
        "explicit_chain": [
            len(multi.joins),
            [join.use.identity.join_position for join in multi.joins],
            multi.joins[1].left_input.output is multi.joins[0].output,
        ],
        "role_playing": {
            "reused_right_uses": [
                join.input_uses[1].ref.position for join in reused.joins
            ],
            "reused_same_producer": True,
            "self_uses": [use.ref.position for use in self_join.input_uses],
        },
        "unbounded_source_input": _region_signature(_region(primary, "fanout_join")),
        "independent_grouped_inputs": _region_signature(_region(primary, "chasm_join")),
        "coarse_fine_inputs": _region_signature(_region(primary, "comparable_join")),
        "ordered_equalities": [_condition_value(nullable), _condition_value(composite)],
    }


def _terminal_observer_controls(bundle):
    snapshot = bundle.verification.root
    completed = snapshot.completed
    projection = _entry(snapshot, "ambiguous_fact_join").blocker
    namespace = projection.blocker
    aggregate_terminal = _entry(snapshot, "chasm_aggregate_refusal").blocker
    qualify_blocker = aggregate_terminal.joined_qualify
    shared = _terminal_graph((namespace, namespace), completed)
    missing = _entry(snapshot, "missing_fact_join").blocker
    issue = missing.joined_completion.join_region.blockers[0].issues[0]
    cyclic = copy(issue)
    object.__setattr__(cyclic, "causes", (cyclic, cyclic))
    cycle = _terminal_graph(cyclic, completed)
    rejections = []
    try:
        _terminal_graph(object(), completed)
    except TypeError as error:
        rejections.append(["unknown_type", type(error).__name__])
    else:
        raise AssertionError("JOIN observer admitted an unknown type.")
    try:
        _require_observed_fields(
            projection,
            [
                field.name
                for field in dataclass_fields(projection)
                if field.name != "joined_qualify"
            ],
        )
    except ValueError as error:
        rejections.append(["omitted_field", type(error).__name__])
    else:
        raise AssertionError("JOIN observer admitted an omitted causal field.")
    for label, original, field, replacement in (
        ("terminal_upstream", projection, "upstream_entry", object()),
        ("namespace_kernel", namespace, "kernel_value_type", object()),
        ("namespace_types", namespace, "value_types", {object(): object()}),
        ("namespace_any", namespace, "existence_values", (object(),)),
        ("namespace_predicate", namespace, "predicate_expression", object()),
        ("qualify_references", projection.joined_qualify, "references", (object(),)),
        ("qualify_kernel", projection.joined_qualify, "predicate_value_type", object()),
        (
            "qualify_types",
            projection.joined_qualify,
            "value_types",
            {object(): object()},
        ),
        ("blocked_qualify_kernel", qualify_blocker, "kernel_value_type", object()),
        ("blocked_qualify_references", qualify_blocker, "references", (object(),)),
        ("blocked_qualify_types", qualify_blocker, "value_types", {object(): object()}),
    ):
        damaged = copy(original)
        object.__setattr__(damaged, field, replacement)
        try:
            _terminal_graph(damaged, completed)
        except ValueError as error:
            rejections.append([label, type(error).__name__])
        else:
            raise AssertionError(f"JOIN observer ignored {label}.")
    return {"shared": shared, "cycle": cycle, "rejections": rejections}


def _negative_observation(primary, foreign, bundle):
    invalid = copy(bundle.verification)
    object.__setattr__(invalid, "status", ProjectIRQueryBlockVerificationStatus.INVALID)
    invalid_bundle = copy(bundle)
    object.__setattr__(invalid_bundle, "verification", invalid)
    try:
        build_project_query_block_ir_inspection(invalid_bundle)
    except ValueError:
        non_verified = "rejected"
    else:
        raise AssertionError("Non-verified current bundle was admitted")
    try:
        query_project_query_block_outputs(
            primary.inspection, foreign.inspection.combined_outputs[0].ref
        )
    except ValueError:
        foreign_ref = "rejected"
    else:
        raise AssertionError("Foreign current output reference was admitted")
    document = primary.document
    node = next(
        i
        for i, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.NODE
    )
    owner = next(
        i
        for i, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    )
    records = list(document.records)
    records[node], records[owner] = records[owner], records[node]
    reordered = replace(document, records=tuple(records))
    use_position = next(
        i
        for i, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.USE
    )
    use = document.records[use_position]
    fields = tuple(
        replace(
            field,
            value=pure.project_query_block_ir_pure_ref(
                pure.ProjectQueryBlockIRPortableRef(
                    domain=pure.ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE,
                    position=10**6,
                )
            ),
        )
        if field.key == "output"
        else field
        for field in use.fields
    )
    changed = replace(use, fields=fields)
    dangling = replace(
        document,
        records=tuple(
            changed if record is use else record for record in document.records
        ),
    )
    outcomes = []
    for label, malformed in (
        ("unknown_format", replace(document, format_marker="untrusted\nformat")),
        ("section_order", reordered),
        ("dangling_ref", dangling),
    ):
        result = pure.evaluate_project_query_block_ir_document(malformed)
        assert result.status is not pure.ProjectQueryBlockIRPureStatus.OK
        assert result.canonical_bytes is None
        outcomes.append(
            [label, result.status.value, result.record_position, result.field_position]
        )
    return {
        "non_verified_admission": non_verified,
        "cross_snapshot_ref": foreign_ref,
        "pure_rejections": outcomes,
        "terminal_observer_controls": _terminal_observer_controls(bundle),
    }


def _construction(root: Path, *, reverse_operation_order: bool):
    specifications = (
        ("primary-normal", "primary", False),
        ("primary-reverse", "primary", True),
        ("parallel", "parallel", False),
        ("no-unique", "no_unique", True),
    )
    built = {}
    for name, variant, reverse_creation in (
        specifications[::-1] if reverse_operation_order else specifications
    ):
        built[name] = _build(
            root / name, VARIANT_SOURCES[variant], reverse_creation=reverse_creation
        )
    semantic, normal, bundle, product = built["primary-normal"]
    _, reverse, reverse_bundle, reverse_product = built["primary-reverse"]
    primary = _analysis_observation(normal, bundle, product)
    assert primary == _analysis_observation(reverse, reverse_bundle, reverse_product)
    assert (
        bundle.verification.root.base_plan.structural_stage.scope
        is not reverse_bundle.verification.root.base_plan.structural_stage.scope
    )
    assert product.document == reverse_product.document
    assert product.canonical_bytes == reverse_product.canonical_bytes
    _, parallel, parallel_bundle, parallel_product = built["parallel"]
    _, no_unique, no_unique_bundle, no_unique_product = built["no-unique"]
    for name in ("missing_fact_join", "bad_relationship_join", "bad_role_join"):
        assert isinstance(
            _entry(bundle.verification.root, name), ProjectIRQueryBlockTerminal
        ), name
    value = {
        "primary": primary,
        "parallel": _analysis_observation(parallel, parallel_bundle, parallel_product),
        "no_unique": _analysis_observation(
            no_unique, no_unique_bundle, no_unique_product
        ),
        "shifted": _shifted_base(semantic),
        "metamorphic": _metamorphic_observation(normal, parallel, no_unique),
        "negative": _negative_observation(product, reverse_product, bundle),
    }
    scopes = tuple(
        item[2].verification.root.base_plan.structural_stage.scope
        for item in built.values()
    )
    assert all(
        left is not right for i, left in enumerate(scopes) for right in scopes[i + 1 :]
    )
    return value, scopes


def observation(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    first, first_scopes = _construction(
        workspace / "forward", reverse_operation_order=False
    )
    second, second_scopes = _construction(
        workspace / "reverse", reverse_operation_order=True
    )
    assert first == second
    assert all(left is not right for left in first_scopes for right in second_scopes)
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_identities_distinct": True,
        **first,
    }


def render(value: object, workspace: Path) -> bytes:
    document = (
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    assert str(workspace).encode() not in document
    assert os.getcwd().encode() not in document
    irrelevant = os.environ.get(SEED_ENVIRONMENT)
    if irrelevant is not None:
        assert irrelevant.encode() not in document
    assert b"0x" not in document and b".venv" not in document
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args(argv)
    sys.stdout.buffer.write(
        render(observation(arguments.workspace), arguments.workspace)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
